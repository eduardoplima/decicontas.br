"""Rescore stored LLM predictions against the cleanlab-corrected gold.

The LLM result JSONs under ``dataset/results/output/`` carry both the
model's raw prediction (``pred``) and the gold spans they were scored
against (``golden``). Predictions are character-offset spans, so they
remain valid against any new gold annotation — we just swap the
``golden`` field for the corrected version (matched by document id) and
recompute span/token F1 via :func:`research.ner_metrics.evaluate_results`.

This avoids re-running any LLM API calls. Supervised baseline JSONs
(BIO sequences keyed by token, depending on the supervised pipeline's
own tokeniser) are NOT handled here — those need a proper retrain on
the corrected labels via the supervised k-fold orchestrator.

Outputs go to ``dataset/results/output_corrected/`` and a markdown
summary table to ``dataset/results/supervised_kfold_corrected/summary/
llm_rescored.md`` (created if missing).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from research.ner_metrics import evaluate_results


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "dataset" / "results" / "output"
DEFAULT_CORRECTED_JSON = (
    REPO_ROOT / "dataset" / "release" / "decicontas-861-corrected" / "decicontas.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dataset" / "results" / "output_corrected"


logger = logging.getLogger("research.release.rescore_llms")


def _is_llm_result(data) -> bool:
    """LLM result files are arrays of per-doc records with ``pred``/``golden``;
    supervised files are a one-element array with BIO ``true_labels``."""
    return (
        isinstance(data, list)
        and data
        and isinstance(data[0], dict)
        and "pred" in data[0]
        and "golden" in data[0]
    )


def _build_corrected_gold_lookup(corrected_path: Path) -> dict[str, list[dict]]:
    """``{stripped_text: [{start,end,text,labels},...]}`` from the corrected JSON.

    The LLM result files store ``text`` stripped (no trailing whitespace),
    while the master Label Studio export keeps the source whitespace; we
    key by stripped text so both align. Multi-doc collisions on stripped
    text would be ambiguous — fail loudly if it happens.
    """
    docs = json.loads(Path(corrected_path).read_text(encoding="utf-8"))
    lookup: dict[str, list[dict]] = {}
    for doc in docs:
        stripped = doc["text"].strip()
        if stripped in lookup:
            raise RuntimeError(
                f"text collision after strip on doc {doc['id']}; rescore key is ambiguous"
            )
        lookup[stripped] = [
            {
                "start": int(e["start"]),
                "end": int(e["end"]),
                "text": doc["text"][int(e["start"]) : int(e["end"])],
                "labels": [e["label"]],
            }
            for e in doc.get("entities", [])
        ]
    return lookup


def rescore_file(
    in_path: Path,
    out_path: Path,
    corrected_lookup: dict[str, list[dict]],
) -> dict | None:
    """Rewrite one result JSON with corrected gold and return its metrics.

    Returns ``None`` for non-LLM files (skipped).
    """
    data = json.loads(in_path.read_text(encoding="utf-8"))
    if not _is_llm_result(data):
        logger.info("skipping non-LLM file: %s", in_path.name)
        return None

    miss = 0
    for entry in data:
        text_key = (entry.get("text") or "").strip()
        new_gold = corrected_lookup.get(text_key)
        if new_gold is None:
            miss += 1
            continue
        entry["golden"] = new_gold

    if miss:
        logger.warning("%s: %d/%d entries had no corrected gold match", in_path.name, miss, len(data))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    df = pd.DataFrame(data)
    metrics_flat = evaluate_results(df)
    return metrics_flat


def rescore_all(
    input_dir: Path = DEFAULT_INPUT_DIR,
    corrected_path: Path = DEFAULT_CORRECTED_JSON,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, dict]:
    lookup = _build_corrected_gold_lookup(corrected_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, dict] = {}
    for in_path in sorted(input_dir.glob("models_results_decicontas_*.json")):
        out_path = output_dir / in_path.name
        logger.info("rescoring %s", in_path.name)
        metrics = rescore_file(in_path, out_path, lookup)
        if metrics is None:
            continue
        # Stem ``models_results_decicontas_<model>`` -> ``<model>``
        model_key = in_path.stem.replace("models_results_decicontas_", "")
        summaries[model_key] = metrics
        logger.info(
            "  span F1=%.4f token F1=%.4f", metrics["span_f1"], metrics["token_f1"]
        )
    return summaries


def write_summary_md(summaries: dict[str, dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(summaries.items(), key=lambda kv: -kv[1]["span_f1"])
    lines = [
        "# LLM rescoring against cleanlab-corrected gold\n",
        "Predictions unchanged; only the gold labels (`golden`) were swapped for the\n"
        "corrected version produced by `research.release.export_dataset`.\n",
        "| Model | Span F1 | Span P | Span R | Token F1 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for model, m in rows:
        lines.append(
            f"| {model} | {m['span_f1']:.4f} | {m['span_precision']:.4f} | "
            f"{m['span_recall']:.4f} | {m['token_f1']:.4f} |"
        )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--corrected", type=Path, default=DEFAULT_CORRECTED_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    summaries = rescore_all(args.input_dir, args.corrected, args.output_dir)
    summary_md = args.output_dir / "summary.md"
    write_summary_md(summaries, summary_md)
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
