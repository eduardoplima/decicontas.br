"""Annotation scope: clause detection, the release rule and the scoring filter."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from research.annotation_scope import (
    apply_scope,
    clause_regions,
    filter_frame,
    filter_spans,
    internal_unit_clauses,
    mask_bio,
)
from research.dataset_io import (
    Document,
    NerSpan,
    Token,
    char_span_to_token_span,
    token_offsets,
    tokenize,
)
from research.release import paths

SECEX_SENTENCE = (
    "Recomendar à Secretaria de Controle Externo – SECEX desta Corte de Contas que adote "
    "procedimentos com vistas a impedir a consumação de prescrição."
)


def _doc(doc_id: int, text: str, spans: list[tuple[int, int, str]]) -> Document:
    tokens = [
        Token(text=t.text, char_start=t.char_start, char_end=t.char_end, bio="O")
        for t in tokenize(text)
    ]
    ner = [NerSpan(char_start=s, char_end=e, label=lab) for s, e, lab in spans]
    for sp in ner:
        first = True
        for tok in tokens:
            if tok.char_start < sp.char_end and tok.char_end > sp.char_start:
                tok.bio = ("B-" if first else "I-") + sp.label
                first = False
    return Document(document_id=doc_id, text=text, tokens=tokens, ner_spans=ner)


# ----- clause detection ------------------------------------------------------


def test_clause_runs_from_the_verb_to_the_end_of_the_sentence():
    text = "Julgar irregulares as contas. " + SECEX_SENTENCE + " Aplicar multa ao gestor."
    (clause,) = internal_unit_clauses(text)
    assert text[clause[0]:clause[1]] == SECEX_SENTENCE


def test_clause_detection_is_case_insensitive():
    assert len(internal_unit_clauses("RECOMENDAÇÃO À SECRETARIA DE CONTROLE EXTERNO para que adote X.")) == 1


def test_clause_ends_at_a_semicolon():
    text = "a) recomendar à SECEX que adote X; b) aplicar multa ao gestor."
    (clause,) = internal_unit_clauses(text)
    assert text[clause[0]:clause[1]] == "recomendar à SECEX que adote X;"


def test_clause_without_terminator_runs_to_the_end_of_the_text():
    text = "Recomendar à SECEX que adote X"
    assert internal_unit_clauses(text) == [(0, len(text))]


def test_addressee_must_follow_the_verb_within_sixty_characters():
    near = "recomendar" + " a" * 29 + " SECEX."
    far = "recomendar" + " a" * 31 + " SECEX."
    assert len(internal_unit_clauses(near)) == 1
    assert internal_unit_clauses(far) == []


def test_a_sentence_break_between_verb_and_addressee_blocks_the_match():
    assert internal_unit_clauses("O relator recomenda. A SECEX informou o débito.") == []


def test_notice_to_the_legal_counsel_is_detected():
    assert len(internal_unit_clauses("pela cientificação da Consultoria Jurídica – CONJU deste Tribunal.")) == 1


def test_recommendation_to_an_audited_body_is_not_detected():
    assert internal_unit_clauses("Recomendar ao Prefeito do Município que adote X.") == []


def test_unit_names_must_be_whole_words():
    assert internal_unit_clauses("nos termos da Recomendação Conjunta de 14/06/2014.") == []


def test_regions_cover_the_clause_tokens():
    text = "Multa. recomendar à SECEX que adote X. Fim."
    (region,) = clause_regions(text)
    tokens = [text[s:e] for s, e in token_offsets(text)]
    assert tokens[region[0]:region[1]] == ["recomendar", "à", "SECEX", "que", "adote", "X."]


# ----- release rule ----------------------------------------------------------


def test_entities_inside_a_clause_are_dropped_and_the_rest_kept():
    text = "Aplicar multa ao gestor. " + SECEX_SENTENCE
    start = text.index("Recomendar")
    doc = _doc(7, text, [(0, 23, "MULTA"), (start, len(text) - 1, "RECOMENDACAO")])
    tags = [t.bio for t in doc.tokens]
    (out,) = apply_scope([doc])
    assert [t.bio for t in doc.tokens] == tags
    assert [(s.char_start, s.char_end, s.label) for s in out.ner_spans] == [(0, 23, "MULTA")]
    assert {t.bio for t in out.tokens if t.char_start >= start} == {"O"}
    assert apply_scope([out])[0] is out


def test_an_entity_that_only_overlaps_a_clause_is_kept():
    text = "Aplicar multa ao gestor e " + SECEX_SENTENCE.lower()
    doc = _doc(1, text, [(0, len(text) - 1, "MULTA")])
    assert apply_scope([doc])[0] is doc


# ----- scoring filter --------------------------------------------------------


def test_filter_drops_spans_touching_a_region_whatever_the_label():
    regions = [(10, 20)]
    spans = [
        {"start": 0, "end": 5, "labels": ["MULTA"]},
        {"start": 8, "end": 12, "labels": ["OBRIGACAO"]},
        {"start": 12, "end": 18, "labels": ["RECOMENDACAO"]},
        {"start": 20, "end": 25, "labels": ["MULTA"]},
    ]
    kept, n = filter_spans(spans, regions)
    assert kept == [spans[0], spans[3]] and n == 2
    assert filter_spans(kept, regions) == (kept, 0)


def test_filter_accepts_token_tuples():
    kept, n = filter_spans([(0, 4, "MULTA"), (9, 11, "RECOMENDACAO")], [(10, 20)])
    assert kept == [(0, 4, "MULTA")] and n == 1


def test_mask_bio_blanks_only_the_spans_that_touch_a_region():
    tags = ["B-MULTA", "I-MULTA", "O", "B-RECOMENDACAO", "I-RECOMENDACAO", "O", "I-OBRIGACAO"]
    assert mask_bio(tags, [(4, 5)]) == ["B-MULTA", "I-MULTA", "O", "O", "O", "O", "I-OBRIGACAO"]
    assert mask_bio(tags, []) == tags


TEXT = "Aplicar multa ao gestor. Recomendar à SECEX desta Corte que adote X."
(REGION,) = clause_regions(TEXT)
MULTA = {"start": 0, "end": 4, "labels": ["MULTA"]}
SECEX_PRED = {"start": REGION[0], "end": REGION[1], "labels": ["RECOMENDACAO"]}


def test_frame_filter_drops_the_clause_prediction_and_keeps_the_rest():
    df = pd.DataFrame([{"text": TEXT, "golden": [MULTA], "pred_as_golden": [MULTA, SECEX_PRED]}])
    out = filter_frame(df)
    assert out.loc[0, "pred_as_golden"] == [MULTA]
    assert df.loc[0, "pred_as_golden"] == [MULTA, SECEX_PRED]
    assert out.attrs["scope_filter"] == {"n_dropped": 1, "n_dropped_on_gold": 0}


def test_supervised_fold_metrics_ignore_predictions_on_a_clause():
    from research.kfold.metrics import evaluate_oof

    n = len(token_offsets(TEXT))
    true = ["B-MULTA", "I-MULTA", "I-MULTA", "I-MULTA"] + ["O"] * (n - 4)
    pred = list(true)
    pred[REGION[0]] = "B-RECOMENDACAO"
    for i in range(REGION[0] + 1, REGION[1]):
        pred[i] = "I-RECOMENDACAO"
    sample = {"text": TEXT, "token_offsets": [{"start": s, "end": e} for s, e in token_offsets(TEXT)]}
    metrics = evaluate_oof([sample], [0], [true], [pred])
    assert metrics["span_precision"] == 1.0
    assert metrics["span_f1"] == 1.0


def test_bootstrap_frames_are_filtered_by_master_position():
    from research.release.bootstrap_significance import apply_scope_filter

    df = pd.DataFrame(
        [
            {"golden": [], "pred_as_golden": [{"start": 0, "end": 2, "labels": ["MULTA"]}]},
            {"golden": [], "pred_as_golden": [{"start": 3, "end": 6, "labels": ["RECOMENDACAO"]}]},
        ]
    )
    out = apply_scope_filter(df, {1: [(2, 5)]})
    assert out.loc[0, "pred_as_golden"] == [{"start": 0, "end": 2, "labels": ["MULTA"]}]
    assert out.loc[1, "pred_as_golden"] == []


# ----- the released corpus ---------------------------------------------------


def _release(path):
    if not path.exists():
        pytest.skip(f"{path} not available")
    return json.loads(path.read_text(encoding="utf-8"))


def test_clause_documents_carry_a_single_clause():
    clauses = [internal_unit_clauses(d["text"]) for d in _release(paths.CORRECTED_GOLD_JSON)]
    clauses = [c for c in clauses if c]
    assert len(clauses) == 58
    assert all(len(c) == 1 for c in clauses)


def test_no_released_entity_touches_a_clause():
    for path in (paths.CORRECTED_GOLD_JSON, paths.RELEASE_PRE_DIR / "decicontas.json"):
        for d in _release(path):
            offsets = [tuple(o) for o in d["token_offsets"]]
            regions = clause_regions(d["text"], offsets)
            for e in d["entities"]:
                tok = char_span_to_token_span(e["start"], e["end"], offsets)
                assert not any(tok[0] < r1 and tok[1] > r0 for r0, r1 in regions), (path.name, d["id"], e)
