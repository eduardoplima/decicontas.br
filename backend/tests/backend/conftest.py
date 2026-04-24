"""Fixtures for FastAPI-level tests in ``backend/tests/backend/``.

Rebuilds ``tools.*`` and ``app.*`` in ``sys.modules`` so the FastAPI app and
the in-memory SQLite engine both see the same ``tools.models.Base``. Required
because ``tests/test_scaffolding.py::test_imports_work`` purges ``tools.*``
and otherwise leaves ``app.*`` (imported during collection) bound to an
orphaned ``Base`` object.
"""

from __future__ import annotations

import sys
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def in_memory_engine() -> Iterator[Engine]:
    for name in list(sys.modules):
        if (
            name == "tools"
            or name.startswith("tools.")
            or name == "app"
            or name.startswith("app.")
        ):
            sys.modules.pop(name, None)

    import tools.models as tools_models

    # StaticPool keeps a single connection alive for the whole engine — required
    # because ``:memory:`` gives each SQLite connection its own empty database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tools_models.Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session_factory(in_memory_engine: Engine):
    return sessionmaker(bind=in_memory_engine, autocommit=False, autoflush=False)


@pytest.fixture
def api_client(test_session_factory) -> Iterator[TestClient]:
    from app.deps import get_db_session
    from app.main import app

    def _override_db():
        s = test_session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(test_session_factory):
    """Factory: create a ``UserORM`` in the test DB and return a dict with
    ``id``, ``username``, ``password`` (plaintext for login calls), and ``role``.
    """

    def _factory(
        *,
        username: str = "reviewer",
        email: str | None = None,
        password: str = "password123",
        role: str = "reviewer",
        is_active: bool = True,
    ) -> dict:
        from app.auth.security import hash_password
        from tools.models import RoleEnum, UserORM

        session = test_session_factory()
        try:
            user = UserORM(
                username=username,
                email=email or f"{username}@example.com",
                hashed_password=hash_password(password),
                role=RoleEnum(role),
                is_active=is_active,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return {
                "id": user.id,
                "username": user.username,
                "password": password,
                "role": role,
                "is_active": is_active,
            }
        finally:
            session.close()

    return _factory
