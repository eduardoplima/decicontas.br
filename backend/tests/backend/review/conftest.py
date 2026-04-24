"""Review-specific fixtures.

``_load_texto_acordao`` hits MSSQL in production. In tests we stub it to
return ``None`` by default so the detail endpoint doesn't try to reach a real
database. Tests that want a specific value override it with ``mocker.patch``.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _stub_texto_acordao(mocker):
    return mocker.patch("app.review.service._load_texto_acordao", return_value=None)
