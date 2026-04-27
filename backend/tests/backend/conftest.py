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

    # Register staging ORMs on the same ``Base`` so their tables are included
    # in ``create_all`` — review tests need them.
    import tools.etl.staging  # noqa: F401

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
                NomeUsuario=username,
                Email=email or f"{username}@example.com",
                SenhaHash=hash_password(password),
                Papel=RoleEnum(role),
                Ativo=is_active,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return {
                "id": user.IdUsuario,
                "username": user.NomeUsuario,
                "password": password,
                "role": role,
                "is_active": is_active,
            }
        finally:
            session.close()

    return _factory


@pytest.fixture
def authenticated_client(api_client, make_user):
    """Factory: make_user + /auth/login + return (client, user_dict, headers).

    The returned client reuses ``api_client`` (same DB), but carries a default
    ``Authorization: Bearer`` header so tests don't have to attach it per call.
    """
    import httpx

    def _factory(
        *,
        username: str = "reviewer",
        role: str = "reviewer",
        password: str = "password123",
    ):
        user = make_user(username=username, role=role, password=password)
        resp = api_client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        api_client.headers["Authorization"] = f"Bearer {token}"
        return api_client, user, {"Authorization": f"Bearer {token}"}

    return _factory


@pytest.fixture
def make_staging_obrigacao(test_session_factory):
    """Factory: insert an ``Obrigacao`` final row (and optionally an
    ``ObrigacaoStaging`` audit row) with sensible defaults.

    Under the inverted-semantics model, the *pending* item under review is the
    final-table row; the staging table is the audit trail. Default status is
    ``"pending"`` → no audit row is created. ``"approved"`` / ``"rejected"``
    → also creates a linked audit row.

    Returns a dict where ``id`` is ``IdObrigacao`` (the final-table id) — that's
    the id every review endpoint accepts.
    """

    def _factory(
        *,
        descricao: str = "adotar providências corretivas no prazo de 90 dias",
        id_processo: int = 541094,
        id_composicao_pauta: int = 7001,
        id_voto_pauta: int = 9001,
        id_ner_obrigacao: int | None = None,
        status: str = "pending",
        claimed_by: str | None = None,
        claimed_at=None,
        reviewer: str | None = None,
        review_notes: str | None = None,
    ) -> dict:
        from tools.etl.staging import ObrigacaoStagingORM, ReviewStatus
        from tools.models import ObrigacaoORM

        s = test_session_factory()
        try:
            final = ObrigacaoORM(
                IdProcesso=id_processo,
                IdComposicaoPauta=id_composicao_pauta,
                IdVotoPauta=id_voto_pauta,
                DescricaoObrigacao=descricao,
                OrgaoResponsavel="PREFEITURA MUNICIPAL DE EXEMPLO",
                ReservadoPor=claimed_by,
                DataReserva=claimed_at,
            )
            s.add(final)
            s.flush()

            review_status = ReviewStatus(status)
            if review_status != ReviewStatus.pending:
                from datetime import datetime as _dt

                audit = ObrigacaoStagingORM(
                    IdObrigacao=final.IdObrigacao,
                    IdNerObrigacao=id_ner_obrigacao,
                    IdProcesso=id_processo,
                    IdComposicaoPauta=id_composicao_pauta,
                    IdVotoPauta=id_voto_pauta,
                    DescricaoObrigacao=descricao,
                    Status=review_status,
                    Revisor=reviewer,
                    DataRevisao=_dt.utcnow() if reviewer else None,
                    ObservacoesRevisao=review_notes,
                )
                s.add(audit)
            s.commit()
            s.refresh(final)
            return {
                "id": final.IdObrigacao,
                "id_processo": final.IdProcesso,
                "id_composicao_pauta": final.IdComposicaoPauta,
                "id_voto_pauta": final.IdVotoPauta,
                "descricao": final.DescricaoObrigacao,
            }
        finally:
            s.close()

    return _factory


@pytest.fixture
def make_staging_recomendacao(test_session_factory):
    def _factory(
        *,
        descricao: str = "aperfeiçoar controles internos",
        id_processo: int = 541094,
        id_composicao_pauta: int = 7001,
        id_voto_pauta: int = 9001,
        id_ner_recomendacao: int | None = None,
        status: str = "pending",
        claimed_by: str | None = None,
        claimed_at=None,
        reviewer: str | None = None,
        review_notes: str | None = None,
    ) -> dict:
        from tools.etl.staging import RecomendacaoStagingORM, ReviewStatus
        from tools.models import RecomendacaoORM

        s = test_session_factory()
        try:
            final = RecomendacaoORM(
                IdProcesso=id_processo,
                IdComposicaoPauta=id_composicao_pauta,
                IdVotoPauta=id_voto_pauta,
                DescricaoRecomendacao=descricao,
                OrgaoResponsavel="SECRETARIA MUNICIPAL DE EXEMPLO",
                ReservadoPor=claimed_by,
                DataReserva=claimed_at,
            )
            s.add(final)
            s.flush()

            review_status = ReviewStatus(status)
            if review_status != ReviewStatus.pending:
                from datetime import datetime as _dt

                audit = RecomendacaoStagingORM(
                    IdRecomendacao=final.IdRecomendacao,
                    IdNerRecomendacao=id_ner_recomendacao,
                    IdProcesso=id_processo,
                    IdComposicaoPauta=id_composicao_pauta,
                    IdVotoPauta=id_voto_pauta,
                    DescricaoRecomendacao=descricao,
                    Status=review_status,
                    Revisor=reviewer,
                    DataRevisao=_dt.utcnow() if reviewer else None,
                    ObservacoesRevisao=review_notes,
                )
                s.add(audit)
            s.commit()
            s.refresh(final)
            return {
                "id": final.IdRecomendacao,
                "id_processo": final.IdProcesso,
                "id_composicao_pauta": final.IdComposicaoPauta,
                "id_voto_pauta": final.IdVotoPauta,
                "descricao": final.DescricaoRecomendacao,
            }
        finally:
            s.close()

    return _factory
