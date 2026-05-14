"""Aggregate counts for the DeciContas release tables.

A single utility per stat — kept boring on purpose so the LaTeX numbers
are easy to audit against the JSON outputs.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from research.dataset_io import Document, ENTITY_LABELS


def count_entities(documents: Iterable[Document]) -> dict[str, int]:
    """Number of entity spans per label."""
    counter: Counter[str] = Counter()
    for doc in documents:
        for span in doc.ner_spans:
            counter[span.label] += 1
    return {label: counter.get(label, 0) for label in ENTITY_LABELS}


def count_docs_with_entity(documents: Iterable[Document]) -> dict[str, int]:
    """Number of distinct documents containing at least one span of each label."""
    seen: dict[str, set[int]] = {label: set() for label in ENTITY_LABELS}
    for doc in documents:
        for span in doc.ner_spans:
            if span.label in seen:
                seen[span.label].add(doc.document_id)
    return {label: len(ids) for label, ids in seen.items()}


def count_docs_with_any_entity(documents: Iterable[Document]) -> int:
    return sum(1 for doc in documents if doc.ner_spans)


def total_tokens(documents: Iterable[Document]) -> int:
    return sum(len(doc.tokens) for doc in documents)


def total_chars(documents: Iterable[Document]) -> int:
    return sum(len(doc.text) for doc in documents)


def write_latex_table(
    before: dict[str, int],
    after: dict[str, int],
    out_path,
    *,
    decided_groups: int,
    total_groups: int,
) -> None:
    """Write the dissertation table comparing entity counts pre/post correction."""
    rows: list[str] = []
    total_before = sum(before.values())
    total_after = sum(after.values())
    for label in ENTITY_LABELS:
        b = before.get(label, 0)
        a = after.get(label, 0)
        delta = a - b
        sign = "+" if delta > 0 else ("" if delta == 0 else "-")
        delta_str = f"{sign}{abs(delta)}" if delta != 0 else "0"
        rows.append(f"    {label:<14} & {b:>4} & {a:>4} & {delta_str:>5} \\\\")
    delta_total = total_after - total_before
    sign_total = "+" if delta_total > 0 else ("" if delta_total == 0 else "-")
    delta_total_str = (
        f"{sign_total}{abs(delta_total)}" if delta_total != 0 else "0"
    )
    body = "\n".join(rows)
    tex = (
        "% Auto-gerado por tools/release/export_dataset.py — NÃO EDITAR À MÃO\n"
        "\\begin{table}[ht]\n"
        "  \\centering\\small\n"
        "  \\caption{Distribuição de entidades no dataset DeciContas-861 antes e depois "
        f"da revisão Cleanlab. Foram revisados e aplicados os {decided_groups} grupos "
        f"do total de {total_groups} flagados pelo ensemble com confiança $\\geq 0{{,}}95$; "
        f"os {total_groups - decided_groups} grupos abaixo desse limiar foram mantidos na "
        "anotação original.}\n"
        "  \\label{tab:dataset-corrections}\n"
        "  \\begin{tabular}{lrrr}\n"
        "    \\hline\n"
        "    \\textbf{Classe} & \\textbf{Antes} & \\textbf{Depois} & \\textbf{$\\Delta$} \\\\\n"
        "    \\hline\n"
        f"{body}\n"
        "    \\hline\n"
        f"    Total          & {total_before:>4} & {total_after:>4} & {delta_total_str:>5} \\\\\n"
        "    \\hline\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )
    from pathlib import Path

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(tex, encoding="utf-8")
