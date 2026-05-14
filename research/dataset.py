import pandas as pd

from .fewshot import FEWSHOT_DATASET_IDS


def translate_golden(annotation):
    DICT_LABELS = {
        "MULTA_FIXA": "MULTA",
        "MULTA_PERCENTUAL": "MULTA",
        "OBRIGACAO_MULTA": "OBRIGACAO",
    }

    def translate_spans(value_dict):
        return {
            "start": value_dict["start"],
            "end": value_dict["end"],
            "text": value_dict["text"],
            "labels": [
                DICT_LABELS.get(value_dict["labels"][0], value_dict["labels"][0])
            ],
        }

    for a in annotation:
        if "result" in a.keys() and a["result"] != []:
            for r in a["result"]:
                r["value"] = translate_spans(r["value"])

    return annotation


DEFAULT_DATASET_PATH = "dataset/labeled_data/decicontas.json"


def get_decicontas_df(include_fewshot=False, path: str | None = None):
    """
    Returns a DataFrame containing the decicontas dataset.

    By default, excludes examples used as few-shots in the LLM prompts to
    avoid evaluation leakage. Pass ``include_fewshot=True`` to keep them.

    Pass ``path`` to read from a different dataset file (e.g.
    ``dataset/release/decicontas-861-corrected/decicontas.json`` for the
    cleanlab-corrected version). Defaults to the master Label Studio export.
    """

    df = pd.read_json(path or DEFAULT_DATASET_PATH)
    if not include_fewshot:
        df = df[~df["id"].isin(FEWSHOT_DATASET_IDS)].reset_index(drop=True)
    return df
