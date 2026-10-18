"""Divergence items between annotator 1 (gold) and annotators 2/3 (tools.adjudication.divergences)."""

from __future__ import annotations

import json

from research.dataset_io import token_offsets
from tools.adjudication.divergences import (
    DocView,
    build_all,
    build_items,
    default_decision,
    load_annotators,
)

# fmt: off
WORDS = [
    "ACORDAM", "os", "Conselheiros,", "julgar:", "a)", "multa", "de", "R$", "1.000,00", "ao",      # 0-9
    "gestor;", "b)", "obrigação", "de", "fazer", "x;", "c)", "ressarcimento", "de", "R$",          # 10-19
    "50,00;", "d)", "recomende", "à", "SECEX", "que", "acompanhe;", "e)", "recomendação", "ao",   # 20-29
    "órgão", "para", "cumprir", "a", "lei.",                                                       # 30-34
]
# fmt: on
TEXT = " ".join(WORDS)
MULTA = (5, 11, "MULTA")


def view(a1, a2, a3, doc_id=7) -> DocView:
    return DocView(doc_id, TEXT, token_offsets(TEXT), {"A1": sorted(a1), "A2": sorted(a2), "A3": sorted(a3)})


def test_a_span_only_one_annotator_marked_is_an_add_item_without_replacements():
    items = build_items(view([MULTA], [MULTA, (28, 35, "RECOMENDACAO")], [MULTA]))
    assert [(i.id, i.kind, i.sources, i.label) for i in items] == [("7:add:28-35", "add", ["A2"], "RECOMENDACAO")]
    (c,) = items[0].candidates
    assert (c.source, c.start, c.end, c.label, c.replaces, c.also_adds) == ("A2", 28, 35, "RECOMENDACAO", [], [])
    assert not items[0].in_scope_clause


def test_matching_extras_of_both_annotators_form_one_item_with_two_candidates():
    items = build_items(view([MULTA], [MULTA, (28, 35, "RECOMENDACAO")], [MULTA, (29, 35, "RECOMENDACAO")]))
    (item,) = items
    assert item.id == "7:add:28-35" and item.sources == ["A2", "A3"] and item.label == "RECOMENDACAO"
    assert [(c.source, c.start, c.end) for c in item.candidates] == [("A2", 28, 35), ("A3", 29, 35)]
    assert default_decision(item) == {"action": "include", "source": "A2", "start": 28, "end": 35, "label": "RECOMENDACAO"}


def test_extras_with_different_labels_have_no_label_and_no_default():
    (item,) = build_items(view([MULTA], [MULTA, (28, 35, "RECOMENDACAO")], [MULTA, (28, 35, "OBRIGACAO")]))
    assert item.label is None and item.sources == ["A2", "A3"]
    assert default_decision(item) is None


def test_boundary_differences_at_iou_above_half_are_not_items():
    assert build_items(view([MULTA], [(5, 10, "MULTA")], [MULTA])) == []


def test_gold_span_missed_by_both_is_gold_only_with_partial_overlaps_listed():
    gold_obr = (12, 16, "OBRIGACAO")
    items = build_items(view([MULTA, gold_obr], [MULTA, (15, 16, "OBRIGACAO")], [MULTA]))
    kinds = {i.id: i for i in items}
    only = kinds["7:gold:12-16"]
    assert only.kind == "gold_only" and only.label == "OBRIGACAO" and only.sources == []
    assert only.overlaps == [{"source": "A2", "start": 15, "end": 16, "label": "OBRIGACAO", "iou": 0.25}]
    add = kinds["7:add:15-16"]
    assert add.candidates[0].replaces == [{"start": 12, "end": 16, "label": "OBRIGACAO", "iou": 0.25}]
    assert default_decision(add) is None


def test_gold_span_missed_by_only_one_annotator_is_not_an_item():
    gold_obr = (12, 16, "OBRIGACAO")
    assert build_items(view([MULTA, gold_obr], [MULTA], [MULTA, gold_obr])) == []


def test_same_span_with_another_label_is_a_label_item():
    (item,) = build_items(
        view([MULTA, (17, 21, "RESSARCIMENTO")], [MULTA, (17, 21, "MULTA")], [MULTA, (17, 21, "RESSARCIMENTO")])
    )
    assert item.id == "7:label:17-21" and item.kind == "label" and item.label == "RESSARCIMENTO"
    assert item.sources == ["A2"]
    assert item.labels == {"A1": "RESSARCIMENTO", "A2": "MULTA", "A3": "RESSARCIMENTO"}
    assert [(c.source, c.start, c.end) for c in item.candidates] == [("A1", 17, 21)]


def test_segmenting_a_gold_span_yields_add_items_that_replace_it_and_a_gold_only_item():
    items = build_items(view([(0, 16, "MULTA")], [(5, 9, "MULTA"), (10, 16, "MULTA")], []))
    ids = sorted(i.id for i in items)
    assert ids == ["7:add:10-16", "7:add:5-9", "7:gold:0-16"]
    for item in items:
        if item.kind == "add":
            assert [r["start"] for r in item.candidates[0].replaces] == [0]
            assert item.candidates[0].also_adds == []
        else:
            assert [(o["source"], o["start"]) for o in item.overlaps] == [("A2", 5), ("A2", 10)]


def test_the_matched_half_of_a_split_is_re_added_when_the_other_half_replaces_the_gold():
    (item,) = build_items(view([(5, 16, "MULTA")], [(5, 11, "MULTA"), (12, 16, "MULTA")], [(5, 16, "MULTA")]))
    assert item.id == "7:add:12-16"
    assert item.candidates[0].replaces == [{"start": 5, "end": 16, "label": "MULTA", "iou": 4 / 11}]
    assert item.candidates[0].also_adds == [(5, 11, "MULTA")]


def test_spans_inside_a_court_unit_clause_are_flagged_and_never_pre_marked():
    rec = (22, 27, "RECOMENDACAO")
    (item,) = build_items(view([MULTA], [MULTA, rec], [MULTA, rec]))
    assert item.in_scope_clause and item.sources == ["A2", "A3"]
    assert default_decision(item) is None


def test_build_all_keeps_only_documents_with_items():
    docs = {
        1: view([MULTA], [MULTA], [MULTA], doc_id=1),
        2: view([MULTA], [MULTA, (28, 35, "RECOMENDACAO")], [MULTA], doc_id=2),
    }
    items = build_all(docs)
    assert list(items) == [2] and [i.id for i in items[2]] == ["2:add:28-35"]


def test_load_annotators_collapses_labels_and_projects_token_spans(tmp_path):
    def record(spans):
        return json.dumps({"id": 3, "text": TEXT, "spans": [{"start": s, "end": e, "label": lab} for s, e, lab in spans]})

    offs = token_offsets(TEXT)
    char = (offs[5][0], offs[10][1])
    (tmp_path / "anotador1.jsonl").write_text(record([(*char, "MULTA_FIXA")]) + "\n", encoding="utf-8")
    (tmp_path / "anotador2.jsonl").write_text(record([(*char, "MULTA")]) + "\n", encoding="utf-8")
    (tmp_path / "anotador3.jsonl").write_text(record([]) + "\n", encoding="utf-8")
    docs = load_annotators(tmp_path)
    assert list(docs) == [3] and docs[3].spans == {"A1": [MULTA], "A2": [MULTA], "A3": []}
    assert docs[3].offsets == offs
