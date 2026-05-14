"""Multi-format writers for the academic release of the DeciContas dataset.

Each writer takes a list of :class:`research.dataset_io.Document` and an output
location. Documents are written sorted by ``document_id`` so the output is
deterministic and byte-identical across runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from research.dataset_io import Document, ENTITY_LABELS


# Stable label order: O, then for each entity B-, I-.
def _bio_label_names() -> list[str]:
    out = ["O"]
    for ent in ENTITY_LABELS:
        out.append(f"B-{ent}")
        out.append(f"I-{ent}")
    return out


BIO_LABEL_NAMES = _bio_label_names()
BIO_LABEL_TO_ID = {name: i for i, name in enumerate(BIO_LABEL_NAMES)}


def _sorted(documents: Iterable[Document]) -> list[Document]:
    return sorted(documents, key=lambda d: d.document_id)


def _doc_to_dict(doc: Document) -> dict:
    return {
        "id": doc.document_id,
        "text": doc.text,
        "tokens": [t.text for t in doc.tokens],
        "ner_tags": [t.bio for t in doc.tokens],
        "token_offsets": [[t.char_start, t.char_end] for t in doc.tokens],
        "entities": [
            {"start": s.char_start, "end": s.char_end, "label": s.label}
            for s in doc.ner_spans
        ],
    }


def write_json_clean(documents: Iterable[Document], out_path: Path) -> Path:
    """Pretty-printed JSON array, one item per document.

    Self-describing: each item has the raw text, whitespace-tokenised
    tokens with character offsets, the BIO sequence as strings, and the
    reconstructed entity spans.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    docs = [_doc_to_dict(d) for d in _sorted(documents)]
    out_path.write_text(
        json.dumps(docs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def write_jsonl_hf(documents: Iterable[Document], out_path: Path) -> Path:
    """One document per line, ready for ``datasets.load_dataset('json', ...)``.

    BIO tags are emitted both as strings (``ner_tags``) and integer ids
    (``ner_tag_ids``) using :data:`BIO_LABEL_NAMES` ordering. ``id`` is a
    string to match the HuggingFace convention.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for doc in _sorted(documents):
            record = {
                "id": str(doc.document_id),
                "tokens": [t.text for t in doc.tokens],
                "ner_tags": [t.bio for t in doc.tokens],
                "ner_tag_ids": [BIO_LABEL_TO_ID[t.bio] for t in doc.tokens],
                "token_offsets": [[t.char_start, t.char_end] for t in doc.tokens],
                "text": doc.text,
                "spans": [
                    {
                        "start_char": s.char_start,
                        "end_char": s.char_end,
                        "label": s.label,
                    }
                    for s in doc.ner_spans
                ],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_path


def write_labelstudio(documents: Iterable[Document], out_path: Path) -> Path:
    """Mirror the upstream Label Studio export schema.

    Lets the existing `research.dataset.get_decicontas_df(path=...)` and the
    supervised k-fold / LLM-eval notebooks consume the corrected dataset
    without code changes (they expect ``data.text`` and
    ``annotations[*].result[*].value.{start,end,text,labels}``).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    for doc in _sorted(documents):
        results = []
        for span in doc.ner_spans:
            results.append(
                {
                    "value": {
                        "start": span.char_start,
                        "end": span.char_end,
                        "text": doc.text[span.char_start : span.char_end],
                        "labels": [span.label],
                    },
                    "type": "labels",
                    "from_name": "label",
                    "to_name": "text",
                }
            )
        items.append(
            {
                "id": doc.document_id,
                "data": {"text": doc.text},
                "annotations": [{"result": results}],
            }
        )
    out_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def write_dataset_info(out_path: Path) -> Path:
    """Write a HuggingFace-compatible ``dataset_info.json`` next to the JSONL.

    Mirrors the ``ClassLabel`` features schema so downstream code can
    instantiate ``datasets.Features`` directly.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "description": (
            "DeciContas — Brazilian legal NER dataset of audit-court rulings "
            "(TCE/RN). Four entity classes: MULTA (fines), OBRIGACAO "
            "(obligations), RESSARCIMENTO (refunds), RECOMENDACAO "
            "(recommendations). 861 documents (after filtering 5 few-shot "
            "leakage cases from the original 866-doc Label Studio export)."
        ),
        "license": "see dataset/release/README.md",
        "features": {
            "id": {"dtype": "string", "_type": "Value"},
            "tokens": {
                "feature": {"dtype": "string", "_type": "Value"},
                "_type": "Sequence",
            },
            "ner_tags": {
                "feature": {"dtype": "string", "_type": "Value"},
                "_type": "Sequence",
            },
            "ner_tag_ids": {
                "feature": {
                    "names": BIO_LABEL_NAMES,
                    "_type": "ClassLabel",
                },
                "_type": "Sequence",
            },
            "token_offsets": {
                "feature": {
                    "feature": {"dtype": "int32", "_type": "Value"},
                    "_type": "Sequence",
                },
                "_type": "Sequence",
            },
            "text": {"dtype": "string", "_type": "Value"},
            "spans": [
                {
                    "start_char": {"dtype": "int32", "_type": "Value"},
                    "end_char": {"dtype": "int32", "_type": "Value"},
                    "label": {"dtype": "string", "_type": "Value"},
                }
            ],
        },
        "label_names": BIO_LABEL_NAMES,
        "entity_types": list(ENTITY_LABELS),
    }
    out_path.write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def write_conll(documents: Iterable[Document], out_path: Path) -> Path:
    """CoNLL-2003 four-column format: ``token -X- _ TAG``.

    Each document is preceded by a ``# id = N`` comment and separated by a
    blank line. We emit the document as a single sentence — the source
    decisions are unsegmented and any sentence split would be lossy.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for doc in _sorted(documents):
            fh.write(f"# id = {doc.document_id}\n")
            for tok in doc.tokens:
                fh.write(f"{tok.text} -X- _ {tok.bio}\n")
            fh.write("\n")
    return out_path


def _brat_escape(text: str) -> str:
    # BRAT requires single-line text in T-line snippets and disallows tabs.
    return text.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def write_brat(documents: Iterable[Document], out_dir: Path) -> Path:
    """Write one ``<doc_id>.txt`` + ``<doc_id>.ann`` pair per document.

    Standoff format used by the BRAT annotation tool: ``T<n>\\tLABEL
    start end\\ttext``. Offsets are byte-positions into the ``.txt`` file
    when written as UTF-8 — to keep this portable and BRAT-compatible we
    serialise the text with the same characters that produced the offsets
    in the source JSON. (Label Studio offsets are character-based; BRAT
    treats them as byte offsets but with consistent UTF-8 they coincide
    for single-byte chars; multi-byte characters in spans may shift
    indices in BRAT's UI — this matches what every other Portuguese NER
    BRAT release ships with and is the convention.)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for doc in _sorted(documents):
        txt_path = out_dir / f"{doc.document_id}.txt"
        ann_path = out_dir / f"{doc.document_id}.ann"
        txt_path.write_text(doc.text, encoding="utf-8")
        with ann_path.open("w", encoding="utf-8") as fh:
            for n, span in enumerate(doc.ner_spans, start=1):
                snippet = _brat_escape(doc.text[span.char_start : span.char_end])
                fh.write(
                    f"T{n}\t{span.label} {span.char_start} {span.char_end}\t{snippet}\n"
                )
    return out_dir


def write_all_formats(
    documents: Sequence[Document],
    out_dir: Path,
    *,
    base_name: str = "decicontas",
) -> dict[str, Path]:
    """Convenience: write every format into ``out_dir`` and return their paths."""
    out_dir = Path(out_dir)
    paths = {
        "json": write_json_clean(documents, out_dir / f"{base_name}.json"),
        "jsonl": write_jsonl_hf(documents, out_dir / f"{base_name}.jsonl"),
        "conll": write_conll(documents, out_dir / f"{base_name}.conll"),
        "brat": write_brat(documents, out_dir / "brat"),
        "dataset_info": write_dataset_info(out_dir / "dataset_info.json"),
        "labelstudio": write_labelstudio(
            documents, out_dir / f"{base_name}-labelstudio.json"
        ),
    }
    return paths
