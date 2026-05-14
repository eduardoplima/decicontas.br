"""Academic release pipeline for the DeciContas dataset.

Produces, from the canonical Label Studio export plus the cleanlab
correction file, a publishable bundle of NER datasets in JSON, JSONL
(HuggingFace ``datasets``-compatible), CoNLL-2003 BIO, and BRAT standoff
formats — both pre- and post-correction.

Entry point: ``python -m research.release.export_dataset``.
"""
