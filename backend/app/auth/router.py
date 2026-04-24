"""Auth router: login, refresh (rotates), logout, me.

All endpoints are under ``/api/v1/auth``. JSON in/out. Error detail strings
are English (developer-facing); the frontend localizes to Portuguese.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import schemas, service
from app.deps import get_current_user, get_db_session
from tools.models import RoleEnum, UserORM


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenPair)
def login(
    body: schemas.LoginRequest,
    session: Session = Depends(get_db_session),
) -> schemas.TokenPair:
    user = service.authenticate_user(session, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    access, refresh = service.issue_token_pair(session, user)
    return schemas.TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(
    body: schemas.RefreshRequest,
    session: Session = Depends(get_db_session),
) -> schemas.TokenPair:
    _, access, new_refresh = service.rotate_refresh_token(session, body.refresh_token)
    return schemas.TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: schemas.RefreshRequest,
    session: Session = Depends(get_db_session),
) -> None:
    service.logout(session, body.refresh_token)


@router.get("/me", response_model=schemas.UserOut)
def me(user: UserORM = Depends(get_current_user)) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.IdUsuario,
        username=user.NomeUsuario,
        email=user.Email,
        role=user.Papel.value if isinstance(user.Papel, RoleEnum) else str(user.Papel),
        is_active=user.Ativo,
    )
