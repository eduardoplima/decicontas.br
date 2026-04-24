"""Fixtures for ETL tests.

Overrides ``get_arq_pool`` with an ``AsyncMock`` so router tests don't need
a real Redis. Worker-task tests call the task functions directly (no arq
runtime) so they don't need the pool at all.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def arq_pool(api_client):
    """Inject an ``AsyncMock`` as the ARQ pool for router tests."""
    from app.deps import get_arq_pool
    from app.main import app

    pool = AsyncMock()
    app.dependency_overrides[get_arq_pool] = lambda: pool
    try:
        yield pool
    finally:
        app.dependency_overrides.pop(get_arq_pool, None)
