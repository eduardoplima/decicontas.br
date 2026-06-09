"""CLI entry point for the DeciContas academic release.

Run from the repository root::

    uv run python -m research.release.export_dataset

Inputs:
    dataset/labeled_data/decicontas.json
    dataset/errors/dataset-corrections.json

Outputs:
    dataset/release/decicontas-before-correction/{decicontas.{json,jsonl,conll},brat/,dataset_info.json}
    dataset/release/decicontas/...                 (same layout)
    dataset/release/README.md
    dataset/release/MANIFEST.json                  (sha256 of every artefact)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

from research.dataset_io import load_dataset
from research.release.apply_corrections import apply_corrections, load_corrections
from research.release.exporters import write_all_formats
from research.release.stats import (
    count_docs_with_any_entity,
    count_docs_with_entity,
    count_entities,
    total_chars,
    total_tokens,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABELED = REPO_ROOT / "dataset" / "labeled_data" / "decicontas.json"
DEFAULT_CORRECTIONS = REPO_ROOT / "dataset" / "errors" / "dataset-corrections.json"
DEFAULT_RELEASE_DIR = REPO_ROOT / "dataset" / "release"


logger = logging.getLogger("research.release.export_dataset")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def _summarise_corrections(corrections_path: Path) -> dict:
    payload = json.loads(corrections_path.read_text(encoding="utf-8"))
    summary = payload.get("summary") or {}
    return {
        "version": payload.get("version"),
        "generated_at": payload.get("generated_at"),
        "groups_total": summary.get("groups_total"),
        "groups_decided": summary.get("groups_decided"),
        "accept": summary.get("accept"),
        "reject": summary.get("reject"),
        "custom": summary.get("custom"),
        "token_changes": summary.get("token_changes"),
    }


def _stats_block(documents) -> dict:
    return {
        "documents": len(documents),
        "documents_with_entity": count_docs_with_any_entity(documents),
        "tokens": total_tokens(documents),
        "characters": total_chars(documents),
        "entities_per_label": count_entities(documents),
        "documents_per_label": count_docs_with_entity(documents),
    }


def _readme_text(
    *,
    corrections_meta: dict,
    stats_before: dict,
    stats_after: dict,
) -> str:
    return f"""# DeciContas — Brazilian Audit-Court NER Release

This bundle contains two versions of the DeciContas dataset, a Portuguese
named-entity-recognition corpus drawn from rulings of the Court of Audit
of Rio Grande do Norte (TCE/RN). Four entity classes are annotated:
**MULTA** (fines), **OBRIGACAO** (obligations), **RESSARCIMENTO**
(refunds), and **RECOMENDACAO** (recommendations).

## Versions

- **`decicontas-before-correction/`** — the canonical 861-document split
  (5 documents used as few-shot examples in LLM prompts have been removed
  to avoid evaluation contamination). Annotations are the original gold
  labels from the Label Studio export.
- **`decicontas/`** — the same 861 documents with
  reviewer-validated corrections applied. The corrections were sourced
  from a Cleanlab error-detection pass: every group flagged by the
  ensemble with confidence ≥ 0.95 was reviewed entity-by-entity in a
  custom admin UI; groups below that threshold were left at the
  original gold annotation.

## Formats

Each version ships in four formats:

| File | Format | Notes |
| --- | --- | --- |
| `decicontas.json` | Pretty-printed JSON array | One object per document with `text`, `tokens`, `ner_tags` (BIO strings), `token_offsets` (char start/end), and `entities` (reconstructed character spans). |
| `decicontas.jsonl` | JSON Lines, HuggingFace-compatible | Plus integer `ner_tag_ids` and a sibling `dataset_info.json` declaring the `ClassLabel` features. Load with `datasets.load_dataset("json", data_files=...)`. |
| `decicontas.conll` | CoNLL-2003 four-column | `token -X- _ TAG`. Documents separated by blank lines and a `# id = N` header (each document is treated as one sentence — the source decisions are unsegmented). |
| `brat/` | BRAT standoff | One `.txt` (raw text) and `.ann` (`T<n>\\tLABEL start end\\tsnippet`) per document, keyed by `document_id`. |

The BIO label set is fixed:

```
{["O"] + [f"B-{e}" for e in ["MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO"]] + [f"I-{e}" for e in ["MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO"]]}
```

(see `decicontas-before-correction/dataset_info.json` for the exact integer encoding).

## Tokenisation

Whitespace tokenisation (`re.compile(r"\\S+")`) — the same tokeniser
used for the Cleanlab analysis and the supervised cross-validation
experiments. Character offsets in `token_offsets`, `entities`, and the
BRAT `.ann` files are positions in the document's `text` (UTF-8).

## Corrections file applied

- Source: `dataset/errors/dataset-corrections.json`
- Schema version: `{corrections_meta.get('version')}`
- Generated at: `{corrections_meta.get('generated_at')}`
- Groups reviewed (ensemble confidence ≥ 0.95): `{corrections_meta.get('groups_decided')}` of `{corrections_meta.get('groups_total')}`
- Decisions: `{corrections_meta.get('accept')}` accept · `{corrections_meta.get('reject')}` reject · `{corrections_meta.get('custom')}` custom
- Token-level overrides applied: `{corrections_meta.get('token_changes')}`

The remaining `{(corrections_meta.get('groups_total') or 0) - (corrections_meta.get('groups_decided') or 0)}` groups fell below the 0.95 ensemble-confidence
threshold and were not reviewed; they keep their original gold labels in
`decicontas/`.

## Statistics

### Before corrections (`decicontas-before-correction/`)

```
documents:                {stats_before['documents']}
documents with entity:    {stats_before['documents_with_entity']}
tokens:                   {stats_before['tokens']}
characters:               {stats_before['characters']}
entities per label:       {stats_before['entities_per_label']}
documents per label:      {stats_before['documents_per_label']}
```

### After corrections (`decicontas/`)

```
documents:                {stats_after['documents']}
documents with entity:    {stats_after['documents_with_entity']}
tokens:                   {stats_after['tokens']}
characters:               {stats_after['characters']}
entities per label:       {stats_after['entities_per_label']}
documents per label:      {stats_after['documents_per_label']}
```

## Reproducibility

Re-run `uv run python -m research.release.export_dataset` from the
repository root. Outputs are deterministic (documents sorted by
`document_id`; no run-time timestamps embedded in any artefact). The
`MANIFEST.json` next to this README lists the SHA256 of every released
file.

## Citation

If you use this dataset, please cite the accompanying dissertation. A
BibTeX entry will be added here on publication.
"""


def export_release(
    *,
    labeled_path: Path = DEFAULT_LABELED,
    corrections_path: Path = DEFAULT_CORRECTIONS,
    release_dir: Path = DEFAULT_RELEASE_DIR,
) -> dict:
    logger.info("loading master dataset from %s", labeled_path)
    dataset = load_dataset(labeled_path, exclude_fewshot=True)
    documents = dataset.documents
    logger.info("loaded %d docs (after few-shot filter)", len(documents))

    logger.info("loading corrections from %s", corrections_path)
    overrides = load_corrections(corrections_path)
    corrections_meta = _summarise_corrections(corrections_path)
    logger.info(
        "applying %d token-level overrides from %d decided groups",
        len(overrides),
        corrections_meta.get("groups_decided") or 0,
    )
    corrected_documents = apply_corrections(documents, overrides)

    before_dir = release_dir / "decicontas-before-correction"
    after_dir = release_dir / "decicontas"
    logger.info("writing pre-correction bundle to %s", before_dir)
    write_all_formats(documents, before_dir)
    logger.info("writing post-correction bundle to %s", after_dir)
    write_all_formats(corrected_documents, after_dir)

    stats_before = _stats_block(documents)
    stats_after = _stats_block(corrected_documents)

    readme_path = release_dir / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(
        _readme_text(
            corrections_meta=corrections_meta,
            stats_before=stats_before,
            stats_after=stats_after,
        ),
        encoding="utf-8",
    )
    logger.info("wrote %s", readme_path)

    # Manifest with sha256 for every released file (excluding the manifest itself).
    manifest_path = release_dir / "MANIFEST.json"
    files = [
        p for p in _walk_files(release_dir) if p.resolve() != manifest_path.resolve()
    ]
    manifest = {
        "release": "decicontas",
        "labeled_source": str(labeled_path.relative_to(REPO_ROOT)),
        "corrections_source": str(corrections_path.relative_to(REPO_ROOT)),
        "corrections_version": corrections_meta.get("version"),
        "corrections_generated_at": corrections_meta.get("generated_at"),
        "files": [
            {
                "path": str(p.relative_to(release_dir)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": _sha256(p),
            }
            for p in files
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote manifest %s (%d files)", manifest_path, len(files))

    return {
        "stats_before": stats_before,
        "stats_after": stats_after,
        "corrections_meta": corrections_meta,
        "manifest": manifest_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labeled", type=Path, default=DEFAULT_LABELED)
    parser.add_argument("--corrections", type=Path, default=DEFAULT_CORRECTIONS)
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = export_release(
        labeled_path=args.labeled,
        corrections_path=args.corrections,
        release_dir=args.release_dir,
    )
    print(json.dumps(
        {
            "before": result["stats_before"]["entities_per_label"],
            "after": result["stats_after"]["entities_per_label"],
            "decided_groups": result["corrections_meta"].get("groups_decided"),
            "total_groups": result["corrections_meta"].get("groups_total"),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
