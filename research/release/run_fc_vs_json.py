"""Function-calling vs json_schema controlled sub-experiment (Cap. 5 §5.2.1, p51b).

Runs the few-shot NER over the master corpus for a small set of models with TWO
structured-output methods — ``function_calling`` (FC) and strict ``json_schema``
(JS) — using the SAME prompt and the SAME ``NERDecisao`` schema, so the only
difference is the decoding mechanism. Writes the per-(model, method) result JSONs
in the layout ``rescore_experiments`` / ``chapter5_numbers`` expect:

    <cycle>/experiments/function_calling_json_schema/models_results_decicontas_<key>_fc.json
    <cycle>/experiments/function_calling_json_schema/models_results_decicontas_<key>_json.json

p51b context: ``research.schema.NERDecisao`` now declares its lists as
``List[...] = Field(default_factory=list)`` (not ``Optional[...]``), so FC and JS
see identical required/optional fields — this script measures whether the json_schema
penalty persists once the schema is equivalent.

Run:
    uv run python -m research.release.run_fc_vs_json --limit 5      # smoke
    uv run python -m research.release.run_fc_vs_json                 # full
"""

from __future__ import annotations

import argparse
import json
import logging

from research.release import paths
from research.release.run_llm_inference import (
    MODEL_REGISTRY,
    _load_env,
    load_corpus,
    run_model_technique,
)

logger = logging.getLogger("research.release.run_fc_vs_json")

DEFAULT_MODELS = ["deepseek-v4-flash", "gpt-4.1"]
METHODS = [("function_calling", "fc"), ("json_schema", "json")]


def run(models: list[str], limit: int | None) -> None:
    _load_env()
    out_dir = paths.RAW_EXPERIMENTS_DIR / "function_calling_json_schema"
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = load_corpus(limit)
    logger.info("FC-vs-JS over %d docs into %s", len(texts), out_dir)
    for key in models:
        cfg = MODEL_REGISTRY[key]
        for method, suffix in METHODS:
            logger.info("running %s / %s (few_shot)", key, method)
            records = run_model_technique(
                key,
                cfg.get("openrouter"),
                "few_shot",
                texts,
                structured=method,
                provider_order=cfg.get("provider_order"),
                azure_deployment=cfg.get("azure_foundry"),
                reasoning=cfg.get("reasoning", False),
            )
            path = out_dir / f"models_results_decicontas_{key}_{suffix}.json"
            path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("wrote %s", path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, choices=list(MODEL_REGISTRY))
    parser.add_argument("--limit", type=int, default=None, help="Smoke mode: first N docs.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(args.models, args.limit)


if __name__ == "__main__":
    main()
