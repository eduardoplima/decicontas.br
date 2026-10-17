"""Applying the person map to the artefacts (tools.review.apply_map)."""

from __future__ import annotations

import json

import pandas as pd

from research.dataset_io import token_offsets
from tools.review.apply_map import (
    PersonMap,
    pseudonymise_errors,
    pseudonymise_record,
    pseudonymise_task,
)

TEXT = "multa ao Sr. Teobaldo Quaresma Lins, no valor de R$ 100,00, e intimação de TEOBALDO LINS."
MAP = {
    "seed": 1,
    "tokens": {"teobaldo": "Otávio", "quaresma": "Moreira", "lins": "Ramos"},
    "persons": [
        {
            "id": "teobaldo-quaresma-lins",
            "canonical": "Teobaldo Quaresma Lins",
            "tokens": ["teobaldo", "quaresma", "lins"],
            "gender": "M",
            "mentions": [{"doc_id": 7, "text": "Teobaldo Quaresma Lins", "start": 13, "end": 35}],
        }
    ],
}


def _pm() -> PersonMap:
    return PersonMap(MAP, corpus={7: TEXT})


def test_locate_finds_every_occurrence_even_in_a_shifted_copy_of_the_text():
    pm = _pm()
    shifted = "\n" + TEXT
    spans = pm.locate(shifted, 7)
    assert [(m["start"], m["end"]) for m in spans] == [(14, 36)]
    assert pm.doc_for_text(TEXT) == 7 and pm.doc_for_text("other") is None


def test_task_offsets_and_value_text_follow_the_new_text():
    pm = _pm()
    task = {
        "id": 7,
        "data": {"text": TEXT},
        "annotations": [
            {"result": [{"value": {"start": 0, "end": 35, "text": TEXT[:35], "labels": ["MULTA"]}}]}
        ],
        "predictions": [],
    }
    n = pseudonymise_task(task, pm, 7)
    new = task["data"]["text"]
    value = task["annotations"][0]["result"][0]["value"]
    assert n == 5 and "Luciano" not in new and "SANTOS" not in new
    assert len(token_offsets(new)) == len(token_offsets(TEXT))
    assert new[value["start"] : value["end"]] == value["text"]
    assert value["text"].startswith("multa ao Sr. ") and value["text"].endswith("Ramos")


def test_record_golden_and_pred_strings_follow_the_new_text():
    pm = _pm()
    rec = {
        "index": 6,
        "text": TEXT,
        "golden": [{"start": 0, "end": 35, "labels": ["MULTA"], "text": TEXT[:35]}],
        "pred": {"multas": [{"descricao_multa": "multa ao Sr. Teobaldo Quaresma Lins, no valor de R$ 100,00"}], "obrigacoes": []},
    }
    pseudonymise_record(rec, pm, 7)
    g = rec["golden"][0]
    assert rec["text"][g["start"] : g["end"]].endswith("Ramos")
    assert g["text"] == rec["text"][g["start"] : g["end"]]
    assert rec["pred"]["multas"][0]["descricao_multa"] in rec["text"]


def test_a_paraphrased_prediction_gets_the_document_replacements_token_by_token():
    pm = _pm()
    rec = {"index": 6, "text": TEXT, "golden": [], "pred": {"multas": [{"descricao_multa": "multa ao Sr. Teobaldo Lins, no valor de R$ 100,00"}]}}
    pseudonymise_record(rec, pm, 7)
    assert rec["pred"]["multas"][0]["descricao_multa"] == "multa ao Sr. Otávio Ramos, no valor de R$ 100,00"


def test_errors_frame_token_and_context_stay_consistent():
    pm = _pm()
    df = pd.DataFrame(
        {
            "token": ["Lins,", "para"],
            "label_original": ["I-MULTA", "O"],
            "label_sugerido": ["O", "O"],
            "confianca": [0.9, 0.8],
            "sentenca_idx": [0, 0],
            "contexto": ["Sr. Teobaldo Quaresma Lins, no valor", "no valor de R$"],
        }
    )
    out = pseudonymise_errors(df, pm, {0: 7})
    assert list(out["token"]) == ["Ramos,", "para"]
    assert out["contexto"][0] == "Sr. Otávio Moreira Ramos, no valor"


def test_pred_strings_drop_names_copied_from_other_documents_unless_ambiguous():
    data = json.loads(json.dumps(MAP))
    data["persons"][0]["mentions"][0]["ambiguous"] = False
    data["persons"].append(
        {"id": "x", "canonical": "Zacarias Mendes Pontes", "tokens": ["zacarias", "mendes", "pontes"], "gender": "M",
         "mentions": [{"doc_id": 9, "text": "Zacarias Mendes Pontes", "start": 0, "end": 22, "ambiguous": True}]}
    )
    data["tokens"].update({"zacarias": "Ivo", "mendes": "Prado", "pontes": "Serra"})
    pm = PersonMap(data, corpus={7: TEXT, 9: "Zacarias Mendes Pontes e outros."})
    rec = {"index": 6, "text": TEXT, "golden": [], "pred": {"multas": [{"descricao_multa": "multa a Teobaldo Quaresma Lins e a Zacarias Mendes Pontes"}]}}
    pseudonymise_record(rec, pm, 8)  # document 8 has no marked person
    assert rec["pred"]["multas"][0]["descricao_multa"] == "multa a Otávio Moreira Ramos e a Zacarias Mendes Pontes"


def test_free_text_replaces_names_of_any_mapped_person():
    pm = _pm()
    new, n = pm.free_text("exemplo: condenar Teobaldo Quaresma Lins ao ressarcimento")
    assert n == 3 and "Otávio Moreira Ramos" in new
