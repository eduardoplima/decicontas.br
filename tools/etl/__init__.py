"""ETL layer: staging tables and text-alignment helpers for the review UI.

Kept in ``tools/`` (not ``backend/app/``) because the stage-2 pipelines in
``tools/utils.py`` write to staging, and the span-matching helper is pure and
has no web-framework dependencies.
"""

from tools.etl.pipeline import (
    ExtractionFilters,
    ExtractionReport,
    enqueue_obrigacao_extraction,
    enqueue_recomendacao_extraction,
)
from tools.etl.staging import (
    ObrigacaoStagingORM,
    RecomendacaoStagingORM,
    ReviewStatus,
)
from tools.etl.text_alignment import (
    SpanMatchStatus,
    find_span_in_text,
    find_span_with_status,
)

__all__ = [
    "ExtractionFilters",
    "ExtractionReport",
    "ObrigacaoStagingORM",
    "RecomendacaoStagingORM",
    "ReviewStatus",
    "SpanMatchStatus",
    "enqueue_obrigacao_extraction",
    "enqueue_recomendacao_extraction",
    "find_span_in_text",
    "find_span_with_status",
]
