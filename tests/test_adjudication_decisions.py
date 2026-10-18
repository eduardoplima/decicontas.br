"""From adjudication decisions to a token-level corrections file (tools.adjudication.decisions)."""

from __future__ import annotations

import json

import pytest
from tests.adjudication_fixture import MULTA, TEXT, WORDS, char_span, view

from research.dataset_io import build_document
from research.release.apply_corrections import apply_corrections, check_bio_matches_spans, load_corrections
from tools.adjudication.divergences import build_all, build_items
from tools.adjudication.decisions import (
    ConflictError,
    bio_from_spans,
    build_decisions_file,
    doc_changes,
    final_spans,
    resolve,
    token_changes_for_doc,
    verify_gold_alignment,
)
from tools.adjudication.state import AdjudicationState

N = len(WORDS)
REC = (28, 35, "RECOMENDACAO")


def _changes(doc, decisions):
    items = build_items(doc)
    resolved = resolve(items, decisions)
    final, owners = final_spans(doc.spans["A1"], items, resolved)
    return final, token_changes_for_doc(doc.doc_id, doc.spans["A1"], final, N, owners, resolved, "2026-10-18T00:00:00+00:00")


def test_including_a_span_writes_b_and_i_tags_owned_by_the_item():
    doc = view([MULTA], [MULTA, REC], [MULTA])
    final, changes = _changes(doc, {"7:add:28-35": {"action": "include", "source": "A2", "start": 28, "end": 35, "label": "RECOMENDACAO", "decided_at": "t"}})
    assert final == [MULTA, REC]
    assert [(c["token_idx_in_doc"], c["label_final"]) for c in changes] == [(28, "B-RECOMENDACAO")] + [(i, "I-RECOMENDACAO") for i in range(29, 35)]
    assert {(c["document_id"], c["group_id"], c["decision"], c["decided_by"], c["decided_at"]) for c in changes} == {(7, "7:add:28-35", "accept", "author", "t")}


def test_removing_and_relabelling_gold_spans():
    gold_obr, gold_res = (12, 16, "OBRIGACAO"), (17, 21, "RESSARCIMENTO")
    doc = view([MULTA, gold_obr, gold_res], [MULTA, (17, 21, "MULTA")], [MULTA, (17, 21, "MULTA")])
    final, changes = _changes(doc, {"7:gold:12-16": {"action": "remove", "decided_at": "t"}, "7:label:17-21": {"action": "relabel", "label": "MULTA", "decided_at": "t"}})
    assert final == [MULTA, (17, 21, "MULTA")]
    assert [(c["token_idx_in_doc"], c["label_final"], c["group_id"]) for c in changes] == (
        [(i, "O", "7:gold:12-16") for i in range(12, 16)] + [(17, "B-MULTA", "7:label:17-21")] + [(i, "I-MULTA", "7:label:17-21") for i in range(18, 21)]
    )


def test_including_a_segment_replaces_the_gold_span_and_re_adds_the_matched_half():
    doc = view([(5, 16, "MULTA")], [(5, 11, "MULTA"), (12, 16, "MULTA")], [(5, 16, "MULTA")])
    final, changes = _changes(doc, {"7:add:12-16": {"action": "include", "source": "A2", "start": 12, "end": 16, "label": "MULTA", "decided_at": "t"}})
    assert final == [(5, 11, "MULTA"), (12, 16, "MULTA")]
    assert [(c["token_idx_in_doc"], c["label_final"]) for c in changes] == [(11, "O"), (12, "B-MULTA")]
    assert {c["group_id"] for c in changes} == {"7:add:12-16"}


def test_an_explicit_keep_is_overridden_when_the_span_is_replaced():
    doc = view([(0, 16, "MULTA")], [(5, 9, "MULTA"), (10, 16, "MULTA")], [])
    items = build_items(doc)
    resolved = resolve(items, {"7:gold:0-16": {"action": "keep", "decided_at": "t"}, "7:add:5-9": {"action": "include", "source": "A2", "start": 5, "end": 9, "label": "MULTA", "decided_at": "t"}})
    assert resolved["7:gold:0-16"] == {"action": "replaced", "replaced_by": "7:add:5-9", "explicit": False}
    final, owners = final_spans(doc.spans["A1"], items, resolved)
    assert final == [(5, 9, "MULTA")]
    assert owners[0] == "7:add:5-9" and owners[12] == "7:add:5-9"


def test_two_overlapping_included_spans_raise_a_conflict():
    doc = view([MULTA], [MULTA, (28, 32, "RECOMENDACAO")], [MULTA, (31, 35, "OBRIGACAO")])
    items = build_items(doc)
    assert sorted(i.id for i in items) == ["7:add:28-32", "7:add:31-35"]
    resolved = resolve(items, {i.id: {"action": "include", "source": i.sources[0], "start": i.candidates[0].start, "end": i.candidates[0].end, "label": i.label, "decided_at": "t"} for i in items})
    with pytest.raises(ConflictError) as exc:
        final_spans(doc.spans["A1"], items, resolved)
    assert exc.value.conflicts == [("7:add:28-32", "7:add:31-35")]


def test_doc_changes_list_the_net_effect_with_excerpts():
    gold_obr, gold_res = (12, 16, "OBRIGACAO"), (17, 21, "RESSARCIMENTO")
    doc = view([MULTA, gold_obr, gold_res], [MULTA, (17, 21, "MULTA"), REC], [MULTA, (17, 21, "MULTA"), REC])
    items = build_items(doc)
    resolved = resolve(items, {"7:gold:12-16": {"action": "remove", "decided_at": "t"}, "7:label:17-21": {"action": "relabel", "label": "MULTA", "decided_at": "t"}})
    changes = doc_changes(doc, items, resolved)
    assert [(c["change"], c["start"], c["end"], c["label"], c["old_label"], c["item"], c["explicit"]) for c in changes] == [
        ("removed", 12, 16, "OBRIGACAO", None, "7:gold:12-16", True),
        ("relabelled", 17, 21, "MULTA", "RESSARCIMENTO", "7:label:17-21", True),
        ("added", 28, 35, "RECOMENDACAO", None, "7:add:28-35", False),
    ]
    assert changes[0]["excerpt"] == "obrigação de fazer x;" and changes[2]["doc_id"] == 7
    assert (changes[2]["char_start"], changes[2]["char_end"]) == char_span(28, 35)


def test_bio_from_spans():
    assert bio_from_spans([(1, 3, "MULTA")], 4) == ["O", "B-MULTA", "I-MULTA", "O"]


def _decision_file(tmp_path, docs, decisions, release=None):
    state = AdjudicationState(tmp_path / "state.json", docs, build_all(docs))
    for item_id, rec in decisions.items():
        state.decide(item_id, rec["action"], source=rec.get("source"), label=rec.get("label"))
    return build_decisions_file(state, gold_release=release)


def test_the_file_round_trips_through_apply_corrections(tmp_path):
    docs = {7: view([(5, 16, "MULTA"), (17, 21, "RESSARCIMENTO")], [(5, 11, "MULTA"), (12, 16, "MULTA"), REC], [(17, 21, "MULTA"), REC])}
    payload = _decision_file(tmp_path, docs, {
        "7:add:12-16": {"action": "include", "source": "A2"},
        "7:label:17-21": {"action": "relabel", "label": "MULTA"},
    })
    out = tmp_path / "adjudication-decisions.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    cs, ce = char_span(5, 16)
    rs, re_ = char_span(17, 21)
    document = build_document(7, TEXT, [{"start": cs, "end": ce, "labels": ["MULTA"]}, {"start": rs, "end": re_, "labels": ["RESSARCIMENTO"]}])
    (corrected,) = apply_corrections([document], load_corrections(out))
    spans = sorted((s.char_start, s.char_end, s.label) for s in corrected.ner_spans)
    assert spans == sorted([(*char_span(5, 11), "MULTA"), (*char_span(12, 16), "MULTA"), (*char_span(17, 21), "MULTA"), (*char_span(28, 35), "RECOMENDACAO")])
    assert check_bio_matches_spans([corrected]) == []
    assert payload["version"] == "2" and payload["summary"]["token_changes"] == len(payload["token_changes"])


def test_summary_counts_and_scope(tmp_path):
    scoped = (22, 27, "RECOMENDACAO")
    docs = {
        7: view([MULTA, (12, 16, "OBRIGACAO")], [MULTA, REC, scoped], [MULTA, REC, scoped]),
        8: view([MULTA], [MULTA], [MULTA], doc_id=8),
    }
    payload = _decision_file(tmp_path, docs, {"7:add:22-27": {"action": "include", "source": "A3"}, "7:gold:12-16": {"action": "remove"}})
    s = payload["summary"]
    assert s["items_total"] == 3 and s["items_decided"] == 3 and s["items_pending"] == 0
    assert s["include"] == 2 and s["remove"] == 1 and s["in_scope_included"] == 1
    assert s["entities_before"] == {"MULTA": 2, "OBRIGACAO": 1, "RESSARCIMENTO": 0, "RECOMENDACAO": 0}
    assert s["entities_after"] == {"MULTA": 2, "OBRIGACAO": 0, "RESSARCIMENTO": 0, "RECOMENDACAO": 1}
    assert s["added_per_label"] == {"RECOMENDACAO": 2} and s["removed_per_label"] == {"OBRIGACAO": 1}
    by_group = {c["group_id"]: c["decided_by"] for c in payload["token_changes"]}
    assert by_group == {"7:add:28-35": "default", "7:add:22-27": "author", "7:gold:12-16": "author"}


def test_gold_alignment_is_verified_against_the_release(tmp_path):
    docs = {7: view([MULTA], [MULTA], [MULTA])}
    cs, ce = char_span(5, 11)
    release = tmp_path / "decicontas.json"
    release.write_text(json.dumps([{"id": 7, "text": TEXT, "entities": [{"start": cs, "end": ce, "label": "MULTA"}]}]), encoding="utf-8")
    assert verify_gold_alignment(docs, release) == []
    release.write_text(json.dumps([{"id": 7, "text": TEXT, "entities": []}]), encoding="utf-8")
    assert verify_gold_alignment(docs, release) == [7]
    with pytest.raises(ValueError):
        _decision_file(tmp_path, {7: view([MULTA], [MULTA, REC], [MULTA, REC])}, {}, release=release)
