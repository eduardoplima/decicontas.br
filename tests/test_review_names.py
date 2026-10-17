"""Mentions carry only the name: vocatives and role words are stripped (tools.review.names)."""

from __future__ import annotations

from tools.review.grouping import group_mentions
from tools.review.names import strip_role_prefix


def test_role_words_and_honorifics_are_stripped_from_the_front():
    assert strip_role_prefix("Prefeito Fulano de Tal") == ("Fulano de Tal", 9)
    assert strip_role_prefix("Recorrente Fulano de Tal") == ("Fulano de Tal", 11)
    assert strip_role_prefix("Ex-Prefeita Sra. Maria Costa") == ("Maria Costa", 17)
    assert strip_role_prefix("Senhor Prefeito, Sr. João Silva") == ("João Silva", 21)
    assert strip_role_prefix("Conselheiro Relator Rogério Valença Dias") == ("Rogério Valença Dias", 20)


def test_names_without_a_prefix_are_untouched():
    assert strip_role_prefix("Fulano de Tal") == ("Fulano de Tal", 0)
    assert strip_role_prefix("OLEGÁRIO VALENÇA DA SERRA") == ("OLEGÁRIO VALENÇA DA SERRA", 0)


def test_the_same_person_under_two_vocatives_is_one_group():
    mentions = [
        {"id": "1:0", "doc_id": 1, "text": strip_role_prefix("Prefeito Fulano de Tal")[0]},
        {"id": "2:0", "doc_id": 2, "text": strip_role_prefix("Recorrente FULANO DE TAL")[0]},
    ]
    assert len(group_mentions(mentions)) == 1


def test_honorifics_with_ordinal_marks_and_superlatives_are_dropped():
    assert strip_role_prefix("Sr.ª Clementina Barroso Fontoura") == ("Clementina Barroso Fontoura", 5)
    assert strip_role_prefix("Excelentíssimo Senhor Olegário Valença da Serra") == ("Olegário Valença da Serra", 22)
