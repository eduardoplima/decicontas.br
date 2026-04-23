"""Top-level pytest fixtures for the backend test suite.

Scope split:
  - ``tmp_env`` patches env vars for the whole session so importing
    ``tools.utils`` and ``app.config`` does not require a real ``.env``.
  - ``in_memory_engine`` / ``db_session`` give a fresh SQLite database per test.
  - ``mock_llm`` replaces the LangChain chat model at the ``tools.*`` boundary;
    tests should never hit a real LLM.
  - ``frozen_time`` is a thin passthrough for ``freezegun.freeze_time``.
"""

from __future__ import annotations

from typing import Any, Iterator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True, scope="session")
def tmp_env() -> Iterator[None]:
    """Populate env vars needed to import tools/ and backend/app/ without .env."""
    mp = pytest.MonkeyPatch()
    mp.setenv("SQL_SERVER_HOST", "localhost")
    mp.setenv("SQL_SERVER_USER", "test")
    mp.setenv("SQL_SERVER_PASS", "test")
    mp.setenv("SQL_SERVER_PORT", "1433")
    mp.setenv("SQL_SERVER_DB_PROCESSOS", "processo_test")
    mp.setenv("SQL_SERVER_DB_DECISOES", "BdDIP_test")
    mp.setenv("SQL_SERVER_DB_SIAI", "BdSIAI_test")
    mp.setenv("AZURE_OPENAI_API_KEY", "test-key")
    mp.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com")
    mp.setenv("OPENAI_API_VERSION", "2024-01-01")
    mp.setenv("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")
    mp.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    try:
        yield
    finally:
        mp.undo()


@pytest.fixture
def in_memory_engine() -> Engine:
    """Fresh in-memory SQLite engine with all ``tools.models`` metadata applied."""
    from tools.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_engine: Engine) -> Iterator[Session]:
    """Session inside an outer transaction; rolled back on teardown."""
    connection = in_memory_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def mock_llm() -> MagicMock:
    """MagicMock standing in for AzureChatOpenAI. ``.invoke(...)`` returns an empty NERDecisao."""
    from tools.schema import NERDecisao

    llm = MagicMock()
    llm.invoke.return_value = NERDecisao()
    return llm


@pytest.fixture
def frozen_time() -> Any:
    """Re-export of ``freezegun.freeze_time`` for discoverability via the fixture name."""
    from freezegun import freeze_time

    return freeze_time
