"""Characterization tests for ``tools.prompt_engineering`` techniques.

Goal: catch accidental deletion / regression of each prompt or helper, not to
over-specify wording. Distinguishing markers only.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from tools.prompt_engineering import (
    TECHNIQUE_PROMPTS,
    VERIFICATION_PROMPT,
    dynamic_few_shot_selection,
    generate_prompt_for_technique,
    self_consistency_ner,
    two_stage_ner,
)
from tools.schema import NERDecisao, NERMulta


INPUT = "Acórdão nº 0001/2024. Texto de teste."


def _system_text(prompt_value) -> str:
    return prompt_value.to_messages()[0].content


# ======================================================================
# One test per technique that has a dedicated system prompt
# ======================================================================


def test_cot_prompt_mentions_reasoning_steps() -> None:
    system = _system_text(generate_prompt_for_technique(INPUT, "cot"))
    assert "RACIOCINE" in system
    assert "passo a passo" in system


def test_negative_examples_prompt_flags_what_not_to_extract() -> None:
    system = _system_text(generate_prompt_for_technique(INPUT, "negative_examples"))
    assert "NÃO" in system
    assert "OBRIGACAO" in system
    assert "MULTA" in system


def test_role_prompt_declares_auditor() -> None:
    system = _system_text(generate_prompt_for_technique(INPUT, "role_prompting"))
    assert "Auditor" in system


def test_definitions_prompt_defines_all_four_entities() -> None:
    system = _system_text(generate_prompt_for_technique(INPUT, "definitions"))
    for label in ("MULTA", "OBRIGAÇÃO", "RECOMENDAÇÃO", "RESSARCIMENTO"):
        assert label in system, f"Definition missing for {label}"


def test_technique_prompts_registry_covers_known_techniques() -> None:
    expected = {
        "few_shot",
        "cot",
        "negative_examples",
        "role_prompting",
        "definitions",
    }
    assert expected <= set(TECHNIQUE_PROMPTS)


# ======================================================================
# two_stage_ner
# ======================================================================


def test_two_stage_skips_extractor_when_classifier_reports_nothing() -> None:
    classifier = MagicMock()
    classifier.invoke.return_value = MagicMock(
        tem_multa=False,
        tem_obrigacao=False,
        tem_recomendacao=False,
        tem_ressarcimento=False,
    )
    extractor = MagicMock()

    result = two_stage_ner(classifier, extractor, INPUT, prompt_fn=lambda t: t)

    assert result is None
    extractor.invoke.assert_not_called()


def test_two_stage_zeroes_unclassified_entities() -> None:
    classifier = MagicMock()
    classifier.invoke.return_value = MagicMock(
        tem_multa=True,
        tem_obrigacao=False,
        tem_recomendacao=False,
        tem_ressarcimento=False,
    )
    extractor = MagicMock()
    extractor.invoke.return_value = NERDecisao(
        multas=[NERMulta(descricao_multa="...")],
        obrigacoes=[],
        ressarcimentos=[],
        recomendacoes=[],
    )

    result = two_stage_ner(classifier, extractor, INPUT, prompt_fn=lambda t: t)

    assert len(result.multas) == 1
    assert result.obrigacoes == []
    assert result.ressarcimentos == []
    assert result.recomendacoes == []


# ======================================================================
# Self-refinement / verification
# ======================================================================


def test_verification_prompt_carries_text_and_initial_extraction() -> None:
    populated = VERIFICATION_PROMPT.invoke(
        {"text": INPUT, "initial_extraction": '{"multas": []}'}
    )
    joined = " ".join(m.content for m in populated.to_messages())
    assert INPUT in joined
    assert '"multas": []' in joined


# ======================================================================
# Dynamic few-shot
# ======================================================================


def test_dynamic_few_shot_selection_returns_top_k_by_cosine_similarity() -> None:
    all_examples = [(f"text_{i}", NERDecisao()) for i in range(5)]
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [1.0, 0.0]
    # Vector 0 is most similar to the query, 4 is least similar.
    embeddings.embed_documents.return_value = [
        [1.0, 0.0],
        [0.9, 0.1],
        [0.5, 0.5],
        [0.1, 0.9],
        [0.0, 1.0],
    ]

    selected = dynamic_few_shot_selection(
        "input_text", all_examples, embeddings, k=2
    )

    assert [s[0] for s in selected] == ["text_0", "text_1"]


# ======================================================================
# Self-consistency
# ======================================================================


def test_self_consistency_keeps_spans_over_threshold() -> None:
    """Three runs, threshold = n/2 = 1.5 — only spans seen in 2+ runs survive."""
    llm = MagicMock()
    llm.invoke.side_effect = [
        NERDecisao(multas=[NERMulta(descricao_multa="A")]),
        NERDecisao(multas=[NERMulta(descricao_multa="A")]),
        NERDecisao(multas=[NERMulta(descricao_multa="B")]),
    ]

    out = self_consistency_ner(llm, prompt_fn=lambda t: t, text=INPUT, n_runs=3)

    assert len(out["multas"]) == 1
    assert "A" in out["multas"][0]
    assert "B" not in out["multas"][0]
