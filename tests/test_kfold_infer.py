"""Turning word-level BIO predictions into character spans (research.kfold.infer)."""

from __future__ import annotations

from research.kfold.infer import bio_to_char_spans


def test_spans_carry_character_offsets_and_text():
    text = "aplicar  multa de R$ 100,00 ao gestor; recomendar ao órgão"
    tags = ["O", "B-MULTA", "I-MULTA", "I-MULTA", "I-MULTA", "O", "O", "B-RECOMENDACAO", "I-RECOMENDACAO", "I-RECOMENDACAO"]
    spans = bio_to_char_spans(text, tags)
    assert [(s["label"], s["text"]) for s in spans] == [
        ("MULTA", "multa de R$ 100,00"),
        ("RECOMENDACAO", "recomendar ao órgão"),
    ]
    assert all(text[s["start"]:s["end"]] == s["text"] for s in spans)
    assert (spans[0]["token_start"], spans[0]["token_end"]) == (1, 5)


def test_a_leading_inside_tag_without_begin_is_not_a_span():
    # strict IOB2, as in the evaluation decoder
    assert bio_to_char_spans("a b c", ["I-MULTA", "I-MULTA", "O"]) == []
