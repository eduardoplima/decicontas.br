"""Fixtures for ``tests/tools/etl``.

Overrides ``in_memory_engine`` so the staging tables are always registered on
whatever ``tools.models.Base`` is live in ``sys.modules`` when the fixture runs.
``test_scaffolding.py::test_imports_work`` deletes ``tools.*`` from
``sys.modules`` and re-imports a subset, which can leave previously-imported
staging ORM classes bound to a stale ``Base``. Forcing a fresh import here
keeps this subdirectory's tests order-independent.
"""

from __future__ import annotations

import importlib
import sys
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@pytest.fixture
def in_memory_engine() -> Iterator[Engine]:
    for name in list(sys.modules):
        if name == "tools.etl.staging" or name == "tools.models":
            del sys.modules[name]

    import tools.models as tools_models

    importlib.import_module("tools.etl.staging")

    engine = create_engine("sqlite:///:memory:")
    tools_models.Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
