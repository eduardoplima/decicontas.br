"""An adjudication file is an optional second corrections pass in the release export."""

from __future__ import annotations

import json
import pathlib

from research.dataset_io import token_offsets
from research.release.export_dataset import build_bundles, export_release

LABELED = pathlib.Path(__file__).parent / "fixtures" / "labeled_sample.json"


def _empty_corrections(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "dataset-corrections.json"
    path.write_text(json.dumps({"version": "2", "token_changes": [], "summary": {}}), encoding="utf-8")
    return path


def _adjudication(tmp_path: pathlib.Path) -> pathlib.Path:
    """Adds a two-token RECOMENDACAO at the start of document 2."""
    changes = [
        {"document_id": 2, "token_idx_in_doc": 0, "label_final": "B-RECOMENDACAO", "decision": "accept", "group_id": "2:add:0-2"},
        {"document_id": 2, "token_idx_in_doc": 1, "label_final": "I-RECOMENDACAO", "decision": "accept", "group_id": "2:add:0-2"},
    ]
    path = tmp_path / "adjudication-decisions.json"
    path.write_text(
        json.dumps({"version": "2", "generated_at": "2026-10-18T00:00:00+00:00", "token_changes": changes,
                    "summary": {"items_total": 1, "items_decided": 1, "token_changes": 2}}),
        encoding="utf-8",
    )
    return path


def test_the_adjudication_pass_adds_the_span_only_when_given(tmp_path):
    corrections = _empty_corrections(tmp_path)
    plain = build_bundles(LABELED, corrections)
    with_adj = build_bundles(LABELED, corrections, adjudication_path=_adjudication(tmp_path))
    doc2 = {d.document_id: d for d in with_adj.after}[2]
    offsets = token_offsets(doc2.text)
    assert (doc2.ner_spans[0].char_start, doc2.ner_spans[0].char_end, doc2.ner_spans[0].label) == (offsets[0][0], offsets[1][1], "RECOMENDACAO")
    assert len(doc2.ner_spans) == len({d.document_id: d for d in plain.after}[2].ner_spans) + 1
    assert [len(d.ner_spans) for d in with_adj.before] == [len(d.ner_spans) for d in plain.before]


def test_export_mentions_the_adjudication_only_when_applied(tmp_path):
    corrections = _empty_corrections(tmp_path)
    export_release(labeled_path=LABELED, corrections_path=corrections, release_dir=tmp_path / "plain")
    assert "adjudication" not in (tmp_path / "plain" / "README.md").read_text(encoding="utf-8").lower()
    assert "adjudication_source" not in json.loads((tmp_path / "plain" / "MANIFEST.json").read_text(encoding="utf-8"))

    adjudication = _adjudication(tmp_path)
    export_release(labeled_path=LABELED, corrections_path=corrections, release_dir=tmp_path / "adj", adjudication_path=adjudication)
    readme = (tmp_path / "adj" / "README.md").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "adj" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert "Adjudication" in readme and "2 token" in readme
    assert manifest["adjudication_source"].endswith("adjudication-decisions.json")
    assert manifest["adjudication_generated_at"] == "2026-10-18T00:00:00+00:00"
