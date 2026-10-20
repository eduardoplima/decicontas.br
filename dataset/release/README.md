# DeciContas — Brazilian Audit-Court NER Release

This bundle contains two versions of the DeciContas dataset, a Portuguese
named-entity-recognition corpus drawn from rulings of the Court of Audit
of Rio Grande do Norte (TCE/RN). Four entity classes are annotated:
**MULTA** (fines), **OBRIGACAO** (obligations), **RESSARCIMENTO**
(refunds), and **RECOMENDACAO** (recommendations).

## Versions

- **`decicontas-before-correction/`** — the canonical 861-document split
  (5 documents used as few-shot examples in LLM prompts have been removed
  to avoid evaluation contamination). Annotations are the original gold
  labels from the Label Studio export, within the annotation scope below.
- **`decicontas/`** — the same 861 documents with
  reviewer-validated corrections applied. The corrections were sourced
  from a Cleanlab error-detection pass: every group flagged by the
  ensemble with confidence ≥ 0.95 was reviewed entity-by-entity in a
  custom admin UI; groups below that threshold were left at the
  original gold annotation. The divergences between that audited annotation and the two
  independent annotators were then adjudicated and the decisions applied
  as a second pass (see below).

## Annotation scope

Entities are deliberations addressed to the audited bodies. Recommendations
and notices that a ruling addresses to the Tribunal's own units — the
external-control secretariat (SECEX) or the legal counsel (CONJU) — are
internal management acts that the CGAD sub-registries do not record, so
neither version annotates them (`research/annotation_scope.py`).

## Formats

Each version ships in four formats:

| File | Format | Notes |
| --- | --- | --- |
| `decicontas.json` | Pretty-printed JSON array | One object per document with `text`, `tokens`, `ner_tags` (BIO strings), `token_offsets` (char start/end), and `entities` (reconstructed character spans). |
| `decicontas.jsonl` | JSON Lines, HuggingFace-compatible | Plus integer `ner_tag_ids` and a sibling `dataset_info.json` declaring the `ClassLabel` features. Load with `datasets.load_dataset("json", data_files=...)`. |
| `decicontas.conll` | CoNLL-2003 four-column | `token -X- _ TAG`. Documents separated by blank lines and a `# id = N` header (each document is treated as one sentence — the source decisions are unsegmented). |
| `brat/` | BRAT standoff | One `.txt` (raw text) and `.ann` (`T<n>\tLABEL start end\tsnippet`) per document, keyed by `document_id`. |

The BIO label set is fixed:

```
['O', 'B-MULTA', 'B-OBRIGACAO', 'B-RESSARCIMENTO', 'B-RECOMENDACAO', 'I-MULTA', 'I-OBRIGACAO', 'I-RESSARCIMENTO', 'I-RECOMENDACAO']
```

(see `decicontas-before-correction/dataset_info.json` for the exact integer encoding).

## Tokenisation

Whitespace tokenisation (`re.compile(r"\S+")`) — the same tokeniser
used for the Cleanlab analysis and the supervised cross-validation
experiments. Character offsets in `token_offsets`, `entities`, and the
BRAT `.ann` files are positions in the document's `text` (UTF-8).

## Corrections file applied

- Source: `dataset/errors/dataset-corrections.json`
- Schema version: `2`
- Generated at: `2026-05-05T18:16:47.908806+00:00`
- Groups reviewed (ensemble confidence ≥ 0.95): `567` of `794`
- Decisions: `6` accept · `544` reject · `17` custom
- Token-level overrides applied: `4199`

The remaining `227` groups fell below the 0.95 ensemble-confidence
threshold and were not reviewed; they keep their original gold labels in
`decicontas/`.

## Statistics

### Before corrections (`decicontas-before-correction/`)

```
documents:                861
documents with entity:    196
tokens:                   116844
characters:               754555
entities per label:       {'MULTA': 202, 'OBRIGACAO': 119, 'RESSARCIMENTO': 62, 'RECOMENDACAO': 21}
documents per label:      {'MULTA': 139, 'OBRIGACAO': 88, 'RESSARCIMENTO': 56, 'RECOMENDACAO': 16}
```

### After corrections (`decicontas/`)

```
documents:                861
documents with entity:    223
tokens:                   116844
characters:               754555
entities per label:       {'MULTA': 209, 'OBRIGACAO': 122, 'RESSARCIMENTO': 66, 'RECOMENDACAO': 32}
documents per label:      {'MULTA': 144, 'OBRIGACAO': 100, 'RESSARCIMENTO': 59, 'RECOMENDACAO': 27}
```

## Adjudication file applied

`dataset/errors/adjudication-decisions.json` (generated 2026-10-20T06:48:55+00:00) was applied as a second
pass on top of the Cleanlab review: 163 of
167 divergences between annotator 1 and the two independent
annotators (`dataset/annotators/`) decided, 2419 token
overrides; entities {'MULTA': 203, 'OBRIGACAO': 123, 'RESSARCIMENTO': 63, 'RECOMENDACAO': 22} -> {'MULTA': 209, 'OBRIGACAO': 122, 'RESSARCIMENTO': 66, 'RECOMENDACAO': 32}
before the annotation-scope filter.

## Reproducibility

Re-run `uv run python -m research.release.export_dataset` from the
repository root. Outputs are deterministic (documents sorted by
`document_id`; no run-time timestamps embedded in any artefact). The
`MANIFEST.json` next to this README lists the SHA256 of every released
file.

## Citation

If you use this dataset, please cite the accompanying dissertation. A
BibTeX entry will be added here on publication.
