"""Headless, resumable LLM inference runner for the NER experiments.

Reproducible counterpart to the inference cells of ``notebooks/ner_llm.ipynb``.
Runs few-shot (+ prompting techniques) NER over the 866-document master corpus
for a set of OpenRouter models and writes per-(model, technique) result JSONs in
the exact layout the downstream rescoring/scoring pipeline expects.

Added so the three open-weight models (Llama 3.3 70B, Qwen2.5-72B, gpt-oss-120b)
can be run without the exploratory notebook (p55c — anchor the narrative on
open-weight models).

Layout produced (866 rows, master order, ``text`` stored stripped so it matches
the corrected-gold lookup in ``rescore_llms``/``rescore_experiments``):
  - ``few_shot`` → BOTH ``dataset/results/output/`` (feeds the leaderboard via
    ``rescore_llms``) and ``dataset/experiments/prompt_engineering/`` (feeds
    Block H via ``rescore_experiments``).
  - ``cot`` / ``dynamic_few_shot`` / ``two_stage`` →
    ``dataset/experiments/prompt_engineering/`` only.

The 5 few-shot-leakage documents are kept in the output (866 rows in master
order) and dropped downstream by ``FEWSHOT_RESULT_POSITIONS``.

Env: ``OPENROUTER_API_KEY`` (all models); ``OPENAI_API_KEY`` (only for
``dynamic_few_shot`` embeddings). Fails fast if a required key is missing.

Run (smoke first):
    uv run python -m research.release.run_llm_inference --limit 5
    uv run python -m research.release.run_llm_inference            # full corpus
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from research.fewshot import FEWSHOT_RESULT_POSITIONS, TOOL_USE_EXAMPLES
from research.prompt import FEW_SHOT_NER_PROMPT, generate_few_shot_ner_prompts
from research.prompt_engineering import (
    DocumentClassification,
    generate_prompt_for_technique,
    make_embeddings_model,
    two_stage_ner,
)
from research.release import paths
from research.schema import NERDecisao

logger = logging.getLogger("research.release.run_llm_inference")

REPO_ROOT = paths.REPO_ROOT
CORPUS_PATH = paths.LABELED_CORPUS
OUTPUT_DIR = paths.RAW_OUTPUT_DIR  # cycle-specific (DECICONTAS_CYCLE)
PROMPT_ENG_DIR = paths.RAW_PROMPT_ENG_DIR  # cycle-specific

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# NEW-CYCLE (new_clean) registry. Per-model config keyed by short name.
# Routing: ``azure_foundry`` (deployment on the Brazil AI Foundry resource, served
# via {base}/openai/v1) or ``openrouter`` (OpenRouter model id). ``reasoning``
# (gpt-5.x) → ``max_completion_tokens`` instead of ``max_tokens`` (smoke F5).
# ``structured`` = structured-output method. ``stem`` = leaderboard filename stem
# (``<key>_few_shot``, consistent in this cycle). ``block_h`` models also run
# cot/two_stage. Decision: the 7 Azure-BR run few_shot ONLY; llama/qwen keep the
# full 3 regimes (already produced clean, NOT re-run — resume skips them).
MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    # --- Azure AI Foundry (Brazil), few_shot leaderboard only ---
    "gpt-4.1": {"azure_foundry": "gpt-4.1", "structured": "function_calling",
                "stem": "gpt-4.1_few_shot", "block_h": True},
    "gpt-4.1-mini": {"azure_foundry": "gpt-4.1-mini", "structured": "function_calling",
                     "stem": "gpt-4.1-mini_few_shot", "block_h": False},
    "gpt-4.1-nano": {"azure_foundry": "gpt-4.1-nano", "structured": "function_calling",
                     "stem": "gpt-4.1-nano_few_shot", "block_h": False},
    "gpt-5-mini": {"azure_foundry": "gpt-5-mini", "structured": "function_calling",
                   "reasoning": True, "stem": "gpt-5-mini_few_shot", "block_h": False},
    "gpt-5.1": {"azure_foundry": "gpt-5.1", "structured": "function_calling",
                "reasoning": True, "stem": "gpt-5.1_few_shot", "block_h": False},
    "gpt-5.2": {"azure_foundry": "gpt-5.2", "structured": "function_calling",
                "reasoning": True, "stem": "gpt-5.2_few_shot", "block_h": True},
    "deepseek-v4-flash": {"azure_foundry": "DeepSeek-V4-Flash", "structured": "function_calling",
                          "stem": "deepseek-v4-flash_few_shot", "block_h": True},
    # --- OpenRouter open-weight (already produced clean; kept for registry,
    #     resume skips them since the 866-row files exist) ---
    "llama-3.3-70b": {"openrouter": "meta-llama/llama-3.3-70b-instruct",
                      "provider_order": ["Fireworks", "Together", "DeepInfra"],
                      "structured": "function_calling",
                      "stem": "llama-3.3-70b_few_shot", "block_h": True},
    "qwen2.5-72b": {"openrouter": "qwen/qwen-2.5-72b-instruct", "structured": "function_calling",
                    "stem": "qwen2.5-72b_few_shot", "block_h": True},
}

# The 7 Brazil Azure deployments — convenience subset for --models (the only
# inference to actually run this cycle).
AZURE_BR_MODELS = [
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    "gpt-5-mini", "gpt-5.1", "gpt-5.2", "deepseek-v4-flash",
]

# Techniques run by default. ``dynamic_few_shot`` is intentionally excluded — the
# user flagged a design error in it and will revisit later; it stays selectable via
# ``--techniques`` (and only then touches the embeddings path / OPENAI_API_KEY).
DEFAULT_TECHNIQUES = ["few_shot", "cot", "two_stage"]
ALL_TECHNIQUES = ["few_shot", "cot", "dynamic_few_shot", "two_stage"]

MAX_RETRIES = 10
# If the first N docs of a combo all hard-fail, treat the model as down and
# abort that combo (the run loop then continues to the next model).
CIRCUIT_BREAKER_PROBE = 15
# Latency breaker: if the first LATENCY_PROBE docs take longer than
# LATENCY_MAX_SECONDS in total (rate-limited to a crawl, even if calls succeed),
# abort the combo and move on. Healthy models do these in a few seconds each.
LATENCY_PROBE = 3
LATENCY_MAX_SECONDS = 90.0


# ----- OpenRouter client (ported from notebooks/ner_llm.ipynb cell 4) -------


def make_llm(
    model_id: str | None = None,
    *,
    provider_order: list[str] | None = None,
    azure_deployment: str | None = None,
    reasoning: bool = False,
    **kwargs: Any,
):
    """Build the chat LLM. With ``azure_deployment`` set, routes to the Azure AI
    Foundry OpenAI-compatible endpoint (``{base}/openai/v1`` with the Azure
    api-key; the deployment name is sent as the OpenAI ``model`` field — this is
    the Brazil-region resource, a ``services.ai.azure.com`` Foundry endpoint).
    Otherwise routes to OpenRouter. ``reasoning`` models (gpt-5.x) use
    ``max_completion_tokens`` instead of ``max_tokens``. ``provider_order`` pins
    OpenRouter to tool-capable upstreams."""
    if azure_deployment:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        az_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not (endpoint and az_key):
            raise RuntimeError(
                "Azure env vars not set (AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY)"
            )
        host = urlparse(endpoint)
        base = f"{host.scheme}://{host.hostname}"  # strip any path/query
        kwargs.setdefault("max_completion_tokens" if reasoning else "max_tokens", 4096)
        return ChatOpenAI(
            model=azure_deployment,
            openai_api_key=az_key,
            openai_api_base=f"{base}/openai/v1",
            **kwargs,
        )
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    kwargs.setdefault("max_tokens", 4096)
    extra_body = kwargs.pop("model_kwargs", {}).get("extra_body", {})
    if model_id and "deepseek" in model_id:
        extra_body["provider"] = {"order": ["DeepSeek"]}
    elif provider_order:
        extra_body["provider"] = {"order": list(provider_order)}
    return ChatOpenAI(
        model=model_id,
        openai_api_key=api_key,
        openai_api_base=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/decicontas",
            "X-Title": "decicontas-ner",
        },
        model_kwargs={"extra_body": extra_body} if extra_body else {},
        **kwargs,
    )


def make_extractor(
    model_id: str | None = None,
    structured: str = "function_calling",
    provider_order: list[str] | None = None,
    azure_deployment: str | None = None,
    reasoning: bool = False,
):
    """LLM that returns a validated :class:`NERDecisao`. ``structured`` selects
    the structured-output method (``function_calling`` or ``json_mode``)."""
    llm = make_llm(
        model_id, provider_order=provider_order, azure_deployment=azure_deployment,
        reasoning=reasoning,
    )
    if structured == "json_mode":
        llm = llm.bind(response_format={"type": "json_object"})
        return llm.with_structured_output(NERDecisao, method="json_mode", include_raw=False)
    if structured == "json_schema":
        # strict Structured Outputs (constrained decoding) — the FC-vs-JS "JS" arm
        return llm.with_structured_output(NERDecisao, method="json_schema", include_raw=False)
    return llm.with_structured_output(NERDecisao, include_raw=False, method="function_calling")


def make_classifier(
    model_id: str | None = None,
    structured: str = "function_calling",
    provider_order: list[str] | None = None,
    azure_deployment: str | None = None,
    reasoning: bool = False,
):
    """LLM that returns a :class:`DocumentClassification` (two-stage stage 1)."""
    llm = make_llm(
        model_id, provider_order=provider_order, azure_deployment=azure_deployment,
        reasoning=reasoning,
    )
    if structured == "json_mode":
        llm = llm.bind(response_format={"type": "json_object"})
        return llm.with_structured_output(
            DocumentClassification, method="json_mode", include_raw=False
        )
    return llm.with_structured_output(
        DocumentClassification, include_raw=False, method="function_calling"
    )


# ----- dynamic few-shot with cached example embeddings ----------------------


class _DynamicSelector:
    """Caches the 12 few-shot example embeddings once and selects the top-k per
    document — avoids re-embedding the example pool on every call (which
    ``prompt_engineering.dynamic_few_shot_selection`` does)."""

    def __init__(self, k: int = 5):
        self.k = k
        self.emb = make_embeddings_model()
        self.examples = TOOL_USE_EXAMPLES
        self._example_embs = np.array(
            self.emb.embed_documents([ex[0] for ex in self.examples])
        )

    def prompt(self, text: str):
        q = np.array(self.emb.embed_query(text))
        denom = np.linalg.norm(self._example_embs, axis=1) * np.linalg.norm(q)
        sims = (self._example_embs @ q) / np.where(denom == 0, 1.0, denom)
        top_k = np.argsort(sims)[-self.k :][::-1]
        msgs: list[Any] = []
        for i in top_k:
            ex = self.examples[i]
            msgs.append(HumanMessage(content=ex[0]))
            msgs.append(AIMessage(content=json.dumps(ex[1].model_dump(), ensure_ascii=False)))
        return FEW_SHOT_NER_PROMPT.invoke(dict(text=text, examples=msgs))


# ----- corpus ---------------------------------------------------------------


def load_corpus(limit: int | None = None) -> list[str]:
    """Stripped document texts in master (866) order. ``text`` lives under
    ``row['data']['text']`` in the Label Studio export."""
    docs = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    texts = [(d["data"]["text"] or "").strip() for d in docs]
    return texts[:limit] if limit else texts


# ----- single-document inference per technique ------------------------------


def _infer_one(technique: str, text: str, extractor, classifier, selector) -> NERDecisao | None:
    if technique == "few_shot":
        return extractor.invoke(generate_few_shot_ner_prompts(text))
    if technique == "cot":
        return extractor.invoke(generate_prompt_for_technique(text, "cot"))
    if technique == "dynamic_few_shot":
        return extractor.invoke(selector.prompt(text))
    if technique == "two_stage":
        return two_stage_ner(classifier, extractor, text, generate_few_shot_ner_prompts)
    raise ValueError(f"unknown technique: {technique}")


def _pred_dict(result: NERDecisao | None) -> dict[str, Any]:
    return (result if isinstance(result, NERDecisao) else NERDecisao()).model_dump()


def run_model_technique(
    key: str,
    model_id: str | None,
    technique: str,
    texts: list[str],
    *,
    structured: str,
    provider_order: list[str] | None,
    azure_deployment: str | None,
    reasoning: bool = False,
    selector: _DynamicSelector | None = None,
    max_probe_seconds: float = LATENCY_MAX_SECONDS,
) -> list[dict[str, Any]]:
    """Run one (model, technique) over ``texts`` with retry/backoff, mirroring
    the notebook loop. Returns 866 records (or ``len(texts)`` in smoke mode)."""
    extractor = make_extractor(
        model_id, structured=structured, provider_order=provider_order,
        azure_deployment=azure_deployment, reasoning=reasoning,
    )
    classifier = (
        make_classifier(
            model_id, structured=structured, provider_order=provider_order,
            azure_deployment=azure_deployment, reasoning=reasoning,
        )
        if technique == "two_stage"
        else None
    )
    records: list[dict[str, Any]] = []
    errors = 0
    hard_failures = 0  # docs where every retry raised (vs. a valid empty extraction)
    processed = 0  # docs actually sent to the API (excludes skipped few-shot)
    fewshot_set = set(FEWSHOT_RESULT_POSITIONS)
    combo_start = time.monotonic()
    for index, text in enumerate(texts):
        # The 5 few-shot exemplar docs are in the model's own prompt — never send
        # them to the API. Keep an empty placeholder so the 866-row layout (and the
        # downstream positional fewshot-drop) stays intact.
        if index in fewshot_set:
            records.append(
                {
                    "index": index,
                    "text": text,
                    "pred": _pred_dict(None),
                    "golden": [],
                    "model": key,
                    "technique": technique,
                }
            )
            continue
        result: NERDecisao | None = None
        succeeded = False
        for attempt in range(MAX_RETRIES):
            try:
                result = _infer_one(technique, text, extractor, classifier, selector)
                succeeded = True
                break
            except ValidationError:
                errors += 1
                time.sleep(2)
            except Exception as exc:  # noqa: BLE001 — transient API errors, back off
                errors += 1
                logger.debug("%s/%s doc %d attempt %d: %s", key, technique, index, attempt, exc)
                time.sleep(5 * (attempt + 1))
        if not succeeded:
            hard_failures += 1
        processed += 1  # API-attempted docs (excludes skipped few-shot positions)
        # Breakers count PROCESSED docs (robust to the few-shot skip).
        # Latency: the first LATENCY_PROBE docs took too long overall (rate-limited
        # to a crawl, even though calls may succeed) — skip model.
        if processed == LATENCY_PROBE and max_probe_seconds > 0:
            elapsed = time.monotonic() - combo_start
            if elapsed > max_probe_seconds:
                raise RuntimeError(
                    f"{key}/{technique}: first {LATENCY_PROBE} docs took {elapsed:.0f}s "
                    f"(> {max_probe_seconds:.0f}s) — too slow (rate-limited); skipping model"
                )
        # Circuit-breaker: if the first CIRCUIT_BREAKER_PROBE processed docs ALL
        # hard-fail, the model is down — abort fast instead of grinding the corpus.
        if processed == CIRCUIT_BREAKER_PROBE and hard_failures == CIRCUIT_BREAKER_PROBE:
            raise RuntimeError(
                f"{key}/{technique}: first {CIRCUIT_BREAKER_PROBE} docs all failed "
                f"after {MAX_RETRIES} retries each — model appears unavailable; aborting combo"
            )
        records.append(
            {
                "index": index,
                "text": text,
                "pred": _pred_dict(result),
                "golden": [],  # rescore_* injects corrected gold by stripped text
                "model": key,
                "technique": technique,
            }
        )
    if errors:
        logger.warning("%s/%s finished with %d retries/errors", key, technique, errors)
    return records


def _targets(key: str, technique: str, cfg: dict[str, Any]) -> list[Path]:
    """Output file paths for a (model, technique).

    - ``few_shot`` → the leaderboard file ``output/<stem>.json`` (consumed by
      ``rescore_llms``); for Block H models also the
      ``experiments/prompt_engineering/<key>_few_shot.json`` copy.
    - ``cot`` / ``two_stage`` (Block H only) →
      ``experiments/prompt_engineering/<key>_<technique>.json``.

    For Block H models ``stem == f"{key}_few_shot"``, so the two few_shot paths
    share a filename (output/ and prompt_engineering/).
    """
    fn = lambda stem: f"models_results_decicontas_{stem}.json"  # noqa: E731
    if technique == "few_shot":
        paths = [OUTPUT_DIR / fn(cfg["stem"])]
        if cfg["block_h"]:
            paths.append(PROMPT_ENG_DIR / fn(f"{key}_few_shot"))
        return paths
    return [PROMPT_ENG_DIR / fn(f"{key}_{technique}")]


def _already_done(key: str, technique: str, cfg: dict[str, Any], n_expected: int) -> bool:
    """Resume: skip if every target file already has >= n_expected rows."""
    for p in _targets(key, technique, cfg):
        if not p.exists():
            return False
        try:
            if len(json.loads(p.read_text(encoding="utf-8"))) < n_expected:
                return False
        except Exception:  # noqa: BLE001
            return False
    return True


def _write(records: list[dict[str, Any]], key: str, technique: str, cfg: dict[str, Any]) -> None:
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    for p in _targets(key, technique, cfg):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload, encoding="utf-8")
        logger.info("wrote %s", p)


def _load_env() -> None:
    """Best-effort: load a repo-root ``.env`` so OPENROUTER_API_KEY /
    OPENAI_API_KEY can live there instead of the shell environment."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env")


def run(
    models: list[str],
    techniques: list[str],
    *,
    limit: int | None,
    structured: str | None,
    force: bool,
    max_probe_seconds: float = LATENCY_MAX_SECONDS,
) -> None:
    """``structured=None`` uses each model's registry default; a value overrides
    it for all models (escape hatch). ``max_probe_seconds<=0`` disables the
    latency breaker."""
    _load_env()
    if "dynamic_few_shot" in techniques:
        logger.warning(
            "dynamic_few_shot is deferred (known design issue) and needs OPENAI_API_KEY; "
            "running it only because it was passed explicitly."
        )
    texts = load_corpus(limit)
    logger.info("corpus: %d docs (limit=%s)", len(texts), limit)
    # Build the dynamic selector once (embeds the example pool a single time).
    selector = _DynamicSelector() if "dynamic_few_shot" in techniques else None
    n_expected = len(texts)
    for key in models:
        cfg = MODEL_REGISTRY[key]
        model_id = cfg.get("openrouter")
        azure_deployment = cfg.get("azure_foundry")
        route = azure_deployment or model_id
        method = structured or cfg.get("structured", "function_calling")
        provider_order = cfg.get("provider_order")
        reasoning = cfg.get("reasoning", False)
        for technique in techniques:
            # cot/two_stage only apply to Block H models; few_shot to everyone.
            if technique != "few_shot" and not cfg["block_h"]:
                continue
            if not force and limit is None and _already_done(key, technique, cfg, n_expected):
                logger.info("[skip] %s/%s already complete", key, technique)
                continue
            logger.info(
                "running %s (%s) / %s over %d docs [%s]",
                key, route, technique, len(texts), method,
            )
            # Isolate failures per (model, technique): a model that is down /
            # rate-limited to death is logged and skipped so the rest of the
            # queue still runs. Resume (≥866-row files) preserves finished combos.
            try:
                records = run_model_technique(
                    key,
                    model_id,
                    technique,
                    texts,
                    structured=method,
                    provider_order=provider_order,
                    azure_deployment=azure_deployment,
                    reasoning=reasoning,
                    selector=selector,
                    max_probe_seconds=max_probe_seconds,
                )
                _write(records, key, technique, cfg)
            except Exception as exc:  # noqa: BLE001 — keep the queue going
                logger.warning("skipping %s/%s: %s", key, technique, exc)
                continue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(MODEL_REGISTRY),
        choices=list(MODEL_REGISTRY),
        help="Short model keys to run (default: all registered models).",
    )
    parser.add_argument(
        "--techniques",
        nargs="+",
        default=DEFAULT_TECHNIQUES,
        choices=ALL_TECHNIQUES,
        help="Regimes to run (default: few_shot cot two_stage). "
        "dynamic_few_shot is deferred — selectable but not default.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Smoke mode: only the first N docs."
    )
    parser.add_argument(
        "--structured",
        choices=["function_calling", "json_mode", "json_schema"],
        default=None,
        help="Override the structured-output method for ALL models "
        "(default: each model's registry-configured method).",
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-run even if a complete file exists."
    )
    parser.add_argument(
        "--max-probe-seconds",
        type=float,
        default=LATENCY_MAX_SECONDS,
        help=f"Skip a model if its first {LATENCY_PROBE} docs take longer than this "
        f"(rate-limit guard; default {LATENCY_MAX_SECONDS:.0f}s; 0 disables).",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(
        args.models,
        args.techniques,
        limit=args.limit,
        structured=args.structured,
        force=args.force,
        max_probe_seconds=args.max_probe_seconds,
    )


if __name__ == "__main__":
    main()
