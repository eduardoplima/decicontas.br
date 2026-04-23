"""Characterization tests for pure-function and connection-building helpers in ``tools.utils``.

Pipeline functions are intentionally out of scope — they need a real LLM and MSSQL.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tools.utils import DB_DECISOES, DB_PROCESSOS, DB_SIAI, safe_int


# ======================================================================
# safe_int
# ======================================================================


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (pd.NA, None),
        (np.nan, None),
        (float("nan"), None),
        ("", None),
        ("   ", None),
        ("123", 123),
        ("123.9", 123),
        ("abc", None),
        (42, 42),
        (42.0, 42),
        (42.9, 42),
    ],
)
def test_safe_int_characterization(value, expected) -> None:
    assert safe_int(value) == expected


def test_safe_int_returns_none_for_arbitrary_object() -> None:
    class Weird:
        pass

    assert safe_int(Weird()) is None


def test_safe_int_passes_booleans_through_as_ints() -> None:
    """``bool`` is a subclass of ``int``; safe_int does not special-case it.

    Documenting, not endorsing: callers are expected to pass pandas ID columns,
    so this edge case is outside the stated domain but worth locking in.
    """
    assert safe_int(True) == 1
    assert safe_int(False) == 0


# ======================================================================
# get_connection / get_session
# ======================================================================


@pytest.mark.parametrize(
    "db_name", [DB_PROCESSOS, DB_DECISOES, DB_SIAI, "custom_db"]
)
def test_get_connection_builds_mssql_pymssql_url(mocker, db_name: str) -> None:
    create_engine = mocker.patch("tools.utils.create_engine")
    from tools.utils import get_connection

    get_connection(db_name)

    url = create_engine.call_args.args[0]
    assert url.startswith("mssql+pymssql://")
    assert url.endswith(f"/{db_name}")


def test_get_connection_injects_env_credentials(mocker, monkeypatch) -> None:
    monkeypatch.setenv("SQL_SERVER_HOST", "example.internal")
    monkeypatch.setenv("SQL_SERVER_USER", "auditor")
    monkeypatch.setenv("SQL_SERVER_PASS", "s3cret")
    create_engine = mocker.patch("tools.utils.create_engine")
    from tools.utils import get_connection

    get_connection("BdDIP")

    url = create_engine.call_args.args[0]
    assert "auditor:s3cret@example.internal" in url


def test_get_session_delegates_to_get_connection(mocker) -> None:
    create_engine = mocker.patch("tools.utils.create_engine")
    fake_engine = create_engine.return_value
    sessionmaker = mocker.patch("tools.utils.sessionmaker")
    session_factory = sessionmaker.return_value
    from tools.utils import get_session

    get_session("BdDIP")

    sessionmaker.assert_called_once_with(
        autocommit=False, autoflush=False, bind=fake_engine
    )
    session_factory.assert_called_once_with()
