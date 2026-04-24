"""ETL layer: staging tables and text-alignment helpers for the review UI.

Kept in ``tools/`` (not ``backend/app/``) because the stage-2 pipelines in
``tools/utils.py`` write to staging, and the span-matching helper is pure and
has no web-framework dependencies.
"""

from tools.etl.staging import (
    ObrigacaoStagingORM,
    RecomendacaoStagingORM,
    ReviewStatus,
)
from tools.etl.text_alignment import find_span_in_text

__all__ = [
    "ObrigacaoStagingORM",
    "RecomendacaoStagingORM",
    "ReviewStatus",
    "find_span_in_text",
]
