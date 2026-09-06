"""Unit tests for research.release.annotator_agreement on synthetic data."""

from __future__ import annotations

import pytest


# ----- Agreement coefficients -----------------------------------------------


def test_cohen_kappa_perfect_and_chance():
    from research.release.annotator_agreement import cohen_kappa

    assert cohen_kappa(["A", "B", "A"], ["A", "B", "A"]) == pytest.approx(1.0)
    # Known worked example: po = 0.7, pe = 0.5 -> kappa = 0.4.
    y1 = ["A"] * 5 + ["B"] * 5
    y2 = ["A", "A", "A", "A", "B", "A", "A", "B", "B", "B"]
    assert cohen_kappa(y1, y2) == pytest.approx(0.4)


def test_cohen_kappa_requires_alignment():
    from research.release.annotator_agreement import cohen_kappa

    with pytest.raises(ValueError):
        cohen_kappa(["A"], ["A", "B"])


def test_fleiss_kappa_known_value():
    from research.release.annotator_agreement import fleiss_kappa

    # Two annotators reduce Fleiss to Scott's pi; with identical sequences
    # agreement is perfect regardless of the number of annotators.
    seqs = [["A", "B", "A", "O"]] * 3
    assert fleiss_kappa(seqs) == pytest.approx(1.0)
    # Hand-computed 3-annotator example over 4 items and 2 categories:
    # items with counts (3,0), (2,1), (2,1), (0,3).
    seqs = [
        ["A", "A", "B", "B"],
        ["A", "A", "A", "B"],
        ["A", "B", "A", "B"],
    ]
    # P_bar = mean(1, 1/3, 1/3, 1) = 2/3 ; p_A = 7/12, p_B = 5/12
    # P_e = (7/12)^2 + (5/12)^2 = 74/144 ; kappa = (2/3 - 74/144)/(1 - 74/144)
    expected = (2 / 3 - 74 / 144) / (1 - 74 / 144)
    assert fleiss_kappa(seqs) == pytest.approx(expected)


# ----- Span-level agreement ---------------------------------------------------


def _docs(spans_a, spans_b):
    """Two single-document annotator dicts over the same synthetic text.

    Span comparisons run in whitespace token units, so the fixtures have to
    carry ``token_spans`` exactly as :func:`load_annotator` builds them.
    """
    from research.release.annotator_agreement import _to_token_spans

    # 100 tokens at 4-char stride, so the fixtures' largest offset (320) still
    # lands inside the text. A span past the last token has no token range and
    # is dropped, which silently turned the presence cases into no-ops.
    text = " ".join(["tok"] * 100)
    return (
        {
            1: {
                "text": text,
                "spans": spans_a,
                "token_spans": _to_token_spans(text, spans_a),
            }
        },
        {
            1: {
                "text": text,
                "spans": spans_b,
                "token_spans": _to_token_spans(text, spans_b),
            }
        },
    )


def test_pairwise_span_f1_symmetric():
    from research.release.annotator_agreement import pairwise_span_prf

    spans_a = [(0, 20, "MULTA"), (30, 60, "OBRIGACAO")]
    spans_b = [(2, 20, "MULTA"), (100, 120, "RECOMENDACAO")]
    a, b = _docs(spans_a, spans_b)
    p_ab, r_ab, f_ab = pairwise_span_prf(a, b, [1])
    p_ba, r_ba, f_ba = pairwise_span_prf(b, a, [1])
    assert f_ab == pytest.approx(f_ba)
    assert p_ab == pytest.approx(r_ba)
    assert r_ab == pytest.approx(p_ba)
    # One match out of 2 vs 2 spans -> P = R = 0.5 -> F1 = 0.5.
    assert f_ab == pytest.approx(0.5)


def test_pairwise_span_f1_label_filter():
    from research.release.annotator_agreement import pairwise_span_prf

    spans = [(0, 20, "MULTA"), (30, 60, "OBRIGACAO")]
    a, b = _docs(spans, spans)
    _, _, f_multa = pairwise_span_prf(a, b, [1], label="MULTA")
    _, _, f_rec = pairwise_span_prf(a, b, [1], label="RECOMENDACAO")
    assert f_multa == pytest.approx(1.0)
    assert f_rec == 0.0  # no spans of that class on either side


# ----- Divergence typology ---------------------------------------------------


def test_divergence_typology_classifies_each_kind():
    from research.release.annotator_agreement import divergence_typology

    spans_a = [
        (0, 20, "MULTA"),  # agreement (IoU 1.0, same label)
        (30, 60, "MULTA"),  # class confusion (IoU 1.0, other label in B)
        (100, 140, "OBRIGACAO"),  # boundary (same label, IoU < 0.5)
        (200, 220, "RECOMENDACAO"),  # presence: only in A
    ]
    spans_b = [
        (0, 20, "MULTA"),
        (30, 60, "RESSARCIMENTO"),
        (100, 112, "OBRIGACAO"),  # IoU = 12/40 = 0.3 with A's span
        (300, 320, "MULTA"),  # presence: only in B
    ]
    a, b = _docs(spans_a, spans_b)
    counts, confusion = divergence_typology(a, b, [1])
    assert counts == {
        "agreement": 1,
        "class_confusion": 1,
        "boundary": 1,
        "presence_only_a": 1,
        "presence_only_b": 1,
    }
    assert confusion == {("MULTA", "RESSARCIMENTO"): 1}


# ----- Token projection -------------------------------------------------------


def test_token_labels_projection():
    from research.release.annotator_agreement import token_labels

    text = "aplico multa de mil reais ao gestor"
    # "multa de mil" -> chars 7..19
    labels = token_labels(text, [(7, 19, "MULTA")])
    assert labels == ["O", "MULTA", "MULTA", "MULTA", "O", "O", "O"]


# ----- Loader validation ------------------------------------------------------


def test_load_annotator_and_alignment(tmp_path):
    import json

    from research.release.annotator_agreement import load_annotator

    rec = {
        "id": 7,
        "text": "recomendo cautela ao gestor",
        "spans": [{"start": 0, "end": 17, "label": "RECOMENDACAO"}],
    }
    path = tmp_path / "anotadorX.jsonl"
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    docs = load_annotator(path)
    assert docs[7]["spans"] == [(0, 17, "RECOMENDACAO")]


def test_load_study_real_files_align():
    """The shipped annotator files must satisfy every loader invariant."""
    from research.release import paths
    from research.release.annotator_agreement import load_study

    if not paths.ANNOTATORS_DIR.exists():  # pragma: no cover
        pytest.skip("annotator files not present")
    data, ids = load_study()
    assert len(ids) == 861
    assert set(data) == {"anotador1", "anotador2", "anotador3"}
