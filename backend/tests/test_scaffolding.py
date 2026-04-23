"""Smoke tests: the suite can import ``tools.*`` and the fixtures work."""

from __future__ import annotations

import sys

from sqlalchemy.engine import Engine


TOOLS_MODULES = (
    "tools.schema",
    "tools.models",
    "tools.utils",
    "tools.prompt",
    "tools.fewshot",
    "tools.dataset",
)


def _never_call_create_engine(*_args, **_kwargs):  # pragma: no cover
    raise AssertionError("create_engine should not run during import")


def test_imports_work(mocker) -> None:
    """Every ``tools.*`` module imports cleanly, and importing them does not
    open a database connection or construct an LLM client.

    Encodes the ``tools/CLAUDE.md`` rule:
    "No LLM clients or DB engines instantiated at import time. Factory
    functions only, so tests and the backend can import without side effects."
    """
    for name in list(sys.modules):
        if name == "tools" or name.startswith("tools."):
            del sys.modules[name]

    pymssql_connect = mocker.patch("pymssql.connect")
    azure_ctor = mocker.patch(
        "langchain_openai.AzureChatOpenAI.__init__", return_value=None
    )
    create_engine_spy = mocker.patch(
        "sqlalchemy.create_engine", wraps=_never_call_create_engine
    )

    for name in TOOLS_MODULES:
        __import__(name)

    assert not pymssql_connect.called, (
        "pymssql.connect was invoked during import — move it behind a factory."
    )
    assert not azure_ctor.called, (
        "AzureChatOpenAI was instantiated during import — move it behind a factory."
    )
    assert not create_engine_spy.called, (
        "sqlalchemy.create_engine was invoked during import — move it behind a factory."
    )


def test_in_memory_engine_fixture(in_memory_engine: Engine) -> None:
    """Sanity check: the in-memory engine has ``tools.models`` metadata applied."""
    from sqlalchemy import inspect

    from tools.models import Base

    declared = set(Base.metadata.tables)
    reflected = set(inspect(in_memory_engine).get_table_names())
    assert declared & reflected, "Expected tools.models.Base tables on the engine."
