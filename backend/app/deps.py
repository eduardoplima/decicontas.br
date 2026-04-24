"""FastAPI dependencies.

``get_current_user`` reads the access token from ``Authorization: Bearer …``.
Migrating to HTTP-only cookies is deferred to a later PR (see
``backend/CLAUDE.md`` "Auth").

The auth layer is pluggable: when we migrate to OIDC against the TCE SSO, only
``get_current_user`` changes — the rest of the app depends on the returned
``UserORM`` shape, not on how it was authenticated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import decode_token
from tools.models import RoleEnum, UserORM
from tools.utils import DB_DECISOES, get_connection

if TYPE_CHECKING:
    from arq.connections import ArqRedis


_bearer = HTTPBearer(auto_error=True)


def get_db_session() -> Iterator[Session]:
    """Yield a SQLAlchemy session bound to ``DB_DECISOES``.

    Tests override this dependency with an in-memory SQLite session via
    ``app.dependency_overrides``.
    """
    session_factory = sessionmaker(bind=get_connection(DB_DECISOES))
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_db_session),
) -> UserORM:
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired access token",
        ) from exc

    user = session.get(UserORM, int(payload["sub"]))
    if user is None or not user.Ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found or inactive",
        )
    return user


async def get_arq_pool(request: Request) -> "ArqRedis":
    """Yield the ARQ connection pool attached to the app during lifespan.

    Tests override this dependency with an ``AsyncMock`` so no Redis process
    is required. Production: 503 if the pool never connected (REDIS_URL
    unset or initial connect failed).
    """
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="background worker unavailable — REDIS_URL not configured",
        )
    return pool


def require_role(role: str | RoleEnum) -> Callable[[UserORM], UserORM]:
    required = role.value if isinstance(role, RoleEnum) else str(role)

    def _dependency(user: UserORM = Depends(get_current_user)) -> UserORM:
        user_role = (
            user.Papel.value if isinstance(user.Papel, RoleEnum) else str(user.Papel)
        )
        if user_role != required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{required}' required",
            )
        return user

    return _dependency
