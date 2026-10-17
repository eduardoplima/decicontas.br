"""Token-preserving pseudonymisation of person names (tools.review.pseudonymise)."""

from __future__ import annotations

from research.dataset_io import token_offsets
from tools.review.pseudonymise import (
    build_token_map,
    infer_gender,
    normalise_token,
    pseudonymise_string,
    pseudonymise_text,
    render_like,
)

PERSONS = [
    {"id": "teobaldo-quaresma-lins", "canonical": "Teobaldo Quaresma Lins", "tokens": ["teobaldo", "quaresma", "lins"], "gender": "M",
     "mentions": [{"id": "7:0", "doc_id": 7, "text": "Teobaldo Quaresma Lins"}, {"id": "7:1", "doc_id": 7, "text": "TEOBALDO LINS"}]},
    {"id": "maria-de-lourdes-costa", "canonical": "Maria de Lourdes Costa", "tokens": ["maria", "lourdes", "costa"], "gender": "F",
     "mentions": [{"id": "7:2", "doc_id": 7, "text": "Maria de Lourdes Costa"}]},
]
TEXT = ("multa ao Sr. Teobaldo Quaresma Lins, no valor de R$ 100,00, e ressarcimento pela Sra. Maria de Lourdes Costa; "
        "intimação de TEOBALDO LINS e de Teobaldo Quaresma Lins Filho.")
MENTIONS = [
    {"doc_id": 7, "text": "Teobaldo Quaresma Lins", "start": TEXT.index("Teobaldo Quaresma Lins"), "end": TEXT.index("Teobaldo Quaresma Lins") + 20},
    {"doc_id": 7, "text": "Maria de Lourdes Costa", "start": TEXT.index("Maria de Lourdes"), "end": TEXT.index("Maria de Lourdes") + 22},
]


def _map():
    return build_token_map(PERSONS, seed=1007)


def test_token_map_covers_every_name_token_with_single_word_pseudonyms():
    tmap = _map()
    assert set(tmap) == {"teobaldo", "quaresma", "lins", "maria", "lourdes", "costa"}
    assert all(" " not in v and "-" not in v for v in tmap.values())
    assert all(normalise_token(v) not in tmap for v in tmap.values())  # never a real token
    assert all(len(k) == len(v) for k, v in tmap.items())  # character offsets are preserved
    assert build_token_map(PERSONS, seed=1007) == tmap  # deterministic


def test_excluded_vocabulary_is_never_used_as_a_pseudonym():
    tmap = _map()
    taken = {normalise_token(v) for v in tmap.values()}
    again = build_token_map(PERSONS, seed=1007, exclude=taken)
    assert not taken & {normalise_token(v) for v in again.values()}


def test_render_like_keeps_the_case_pattern():
    assert render_like("Moreira", "SILVA") == "MOREIRA"
    assert render_like("Moreira", "Silva") == "Moreira"
    assert render_like("moreira", "Silva") == "Moreira"


def test_text_keeps_its_token_count_and_replaces_every_occurrence():
    tmap = _map()
    new, remap, n = pseudonymise_text(TEXT, PERSONS, tmap, MENTIONS)
    assert len(token_offsets(new)) == len(token_offsets(TEXT))
    for real in ("Teobaldo", "Quaresma", "Lins", "LINS", "TEOBALDO", "Maria", "Lourdes", "Costa"):
        assert real not in new
    assert " de " in new and "Sr. " in new and "Sra. " in new and " Filho." in new
    assert n >= 4  # the two detected mentions plus the undetected repeats


def test_offsets_are_remapped_at_token_boundaries():
    tmap = _map()
    new, remap, _ = pseudonymise_text(TEXT, PERSONS, tmap, MENTIONS)
    s, e = TEXT.index("multa"), TEXT.index("100,00") + 6
    ns, ne = remap(s, e)
    assert new[ns:ne].startswith("multa ao Sr. ") and new[ns:ne].endswith("R$ 100,00")
    s2 = MENTIONS[1]["start"]
    ns2, ne2 = remap(s2, MENTIONS[1]["end"])
    assert new[ns2:ne2].split()[1] == "de" and len(new[ns2:ne2].split()) == 4


def test_a_span_ending_before_the_comma_of_a_replaced_name_still_ends_before_it():
    tmap = _map()
    new, remap, _ = pseudonymise_text(TEXT, PERSONS, tmap, MENTIONS)
    end = TEXT.index("Lins,") + 4  # right after "Lins", before the comma
    ns, ne = remap(0, end)
    assert new[ne] == "," and new[ns:ne].endswith(tmap["lins"])


def test_pred_strings_follow_the_same_map():
    tmap = _map()
    new, _, _ = pseudonymise_text(TEXT, PERSONS, tmap, MENTIONS)
    pred = pseudonymise_string("multa ao Sr. Teobaldo Quaresma Lins, no valor de R$ 100,00", PERSONS, tmap, MENTIONS)
    assert pred in new
    assert pseudonymise_string("ressarcimento pela Sra. Maria de Lourdes Costa", PERSONS, tmap, MENTIONS) in new


def test_unrelated_tokens_and_lone_surnames_are_left_alone():
    tmap = _map()
    text = "A empresa Lins Construções Ltda. e o bairro de Santa Maria."
    new, _, n = pseudonymise_text(text, PERSONS, tmap, [])
    assert new == text and n == 0


def test_gender_falls_back_to_the_first_name_ending():
    assert infer_gender("Andreazza Fernandes", None) == "F"
    assert infer_gender("Airton Dias", None) == "M"
    assert infer_gender("Airton Dias", "F") == "F"
