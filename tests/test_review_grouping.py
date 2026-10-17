"""Grouping of person mentions across spellings (tools.review.grouping)."""

from __future__ import annotations

from tools.review.grouping import group_mentions, normalise_tokens


def _m(doc_id: int, text: str, mid: str | None = None) -> dict:
    return {"id": mid or f"{doc_id}:{text}", "doc_id": doc_id, "text": text}


def test_normalise_strips_case_accents_and_particles():
    assert normalise_tokens("José da Silva SANTOS") == ["jose", "silva", "santos"]
    assert normalise_tokens("Maria de Lourdes dos Anjos") == ["maria", "lourdes", "anjos"]


def test_same_person_in_different_spellings_falls_in_one_group():
    groups = group_mentions(
        [_m(1, "Ubirajara Fontoura Valença"), _m(2, "UBIRAJARA VALENÇA"), _m(3, "Ubirajara Valença")]
    )
    assert len(groups) == 1
    assert groups[0]["canonical"] == "Ubirajara Fontoura Valença"
    assert sorted(m["text"] for m in groups[0]["mentions"]) == [
        "UBIRAJARA VALENÇA", "Ubirajara Fontoura Valença", "Ubirajara Valença",
    ]


def test_partial_form_joins_the_longer_name_that_contains_it():
    groups = group_mentions([_m(1, "Teobaldo Quaresma Lins"), _m(2, "Teobaldo Lins")])
    assert len(groups) == 1


def test_homonyms_with_different_surnames_stay_apart():
    groups = group_mentions([_m(1, "Teobaldo Quaresma Lins"), _m(2, "Teobaldo Pereira")])
    assert len(groups) == 2


def test_single_token_mention_joins_only_an_unambiguous_person():
    one = group_mentions([_m(1, "Dorotéia Vilanova"), _m(1, "Dorotéia")])
    assert len(one) == 1
    two = group_mentions([_m(1, "Dorotéia Vilanova"), _m(2, "Dorotéia Medeiros"), _m(3, "Dorotéia")])
    assert len(two) == 3


def test_manual_merge_and_split_override_the_heuristics():
    mentions = [_m(1, "Ana Paula Costa", "a"), _m(2, "Beatriz Lima", "b"), _m(3, "Ana Paula Costa", "c")]
    merged = group_mentions(mentions, merges=[["a", "b"]])
    assert len(merged) == 1
    split = group_mentions(mentions, splits=[["c"]])
    assert len(split) == 3
