"""Sonda 1 chamada por modelo e salva os metadados servidos como parâmetros.

Envia um prompt mínimo a cada LLM do ``MODEL_REGISTRY`` e lê os metadados da resposta
(snapshot servido, ``system_fingerprint``, uso de tokens, ``finish_reason``; e o provider
efetivo, para os modelos via OpenRouter). Aditivo e read-only sobre os artefatos canônicos
— grava apenas dois arquivos novos em ``.../reproducibility/``.

RESSALVAS (registradas na saída):
  * É o que é servido NA DATA DA SONDA — deployments Azure podem auto-atualizar, então pode
    não coincidir com o snapshot servido nas execuções originais do experimento.
  * ``temperature``/``top_p``/``seed`` NÃO são ecoados na resposta (são defaults do SDK) e,
    portanto, não são recuperáveis por esta sonda.

Uso:
    uv run python scripts/probe_llm_metadata.py
"""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from research.release.run_llm_inference import MODEL_REGISTRY, _load_env, make_llm

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "dataset" / "results" / "models_outputs" / "reproducibility"
NA = "não consta"
PROMPT = "Responda apenas: ok"


def _openrouter_provider(gen_id: str, api_key: str) -> dict[str, Any]:
    """Best-effort: consulta /api/v1/generation?id= para o provider real + custo."""
    if not gen_id:
        return {}
    url = f"https://openrouter.ai/api/v1/generation?id={gen_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("data", {}) or {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def probe(key: str, cfg: dict[str, Any], probe_ts: str) -> dict[str, Any]:
    import os

    is_azure = "azure_foundry" in cfg
    id_pedido = cfg.get("azure_foundry") or cfg.get("openrouter")
    rec: dict[str, Any] = {
        "chave": key,
        "acesso": "Azure AI Foundry (Brazil)" if is_azure else "OpenRouter",
        "id_pedido": id_pedido,
        "reasoning": bool(cfg.get("reasoning", False)),
        "data_sonda_utc": probe_ts,
    }
    try:
        llm = make_llm(
            model_id=cfg.get("openrouter"),
            azure_deployment=cfg.get("azure_foundry"),
            provider_order=cfg.get("provider_order"),
            reasoning=cfg.get("reasoning", False),
        )
        msg = llm.invoke([HumanMessage(content=PROMPT)])
        rm: dict[str, Any] = dict(msg.response_metadata or {})
        um: dict[str, Any] = dict(msg.usage_metadata or {}) if getattr(msg, "usage_metadata", None) else {}
        tok = rm.get("token_usage") or {}

        gen_id = rm.get("id") or getattr(msg, "id", None) or ""
        provider_info: dict[str, Any] = {}
        if not is_azure:
            provider_info = _openrouter_provider(gen_id, os.getenv("OPENROUTER_API_KEY", ""))

        rec.update({
            "snapshot_servido": rm.get("model_name") or NA,
            "system_fingerprint": rm.get("system_fingerprint") or NA,
            "provider": provider_info.get("provider_name") or (NA if not is_azure else "—"),
            "finish_reason": rm.get("finish_reason") or NA,
            "prompt_tokens": tok.get("prompt_tokens", um.get("input_tokens", NA)),
            "completion_tokens": tok.get("completion_tokens", um.get("output_tokens", NA)),
            "generation_id": gen_id or NA,
            "resposta": (msg.content or "")[:60],
            # Amostragem NÃO ecoada na resposta. O código não passou nenhum, então
            # vale o default da API OpenAI-compatível (padrão da literatura):
            # temperature=1.0, top_p=1.0, sem seed. Reasoning (gpt-5.x) ignora/fixa
            # temperature e top_p internamente.
            "temperature": ("1.0 nominal — reasoning ignora (omitido no código)"
                            if cfg.get("reasoning") else "1.0 (default API; omitido no código)"),
            "top_p": ("1.0 nominal — reasoning ignora (omitido no código)"
                      if cfg.get("reasoning") else "1.0 (default API; omitido no código)"),
            "seed": "não fixado (sem seed; não determinístico)",
            "_raw_response_metadata": rm,
            "_raw_usage_metadata": um,
            "_openrouter_generation": provider_info,
            "erro": None,
        })
        print(f"[ok] {key:18} snapshot={rec['snapshot_servido']} provider={rec['provider']} "
              f"tokens={rec['prompt_tokens']}/{rec['completion_tokens']}")
    except Exception as e:  # noqa: BLE001 — resiliente por modelo
        rec.update({k: NA for k in ("snapshot_servido", "system_fingerprint", "provider",
                                    "finish_reason", "prompt_tokens", "completion_tokens",
                                    "generation_id", "resposta")})
        rec["erro"] = f"{type(e).__name__}: {e}"
        print(f"[ERRO] {key:18} {rec['erro']}")
    return rec


def main() -> None:
    _load_env()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    probe_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    records = [probe(key, cfg, probe_ts) for key, cfg in MODEL_REGISTRY.items()]

    json_path = OUT_DIR / "probed_llm_metadata.json"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    flat_cols = ["chave", "acesso", "id_pedido", "reasoning", "snapshot_servido",
                 "system_fingerprint", "provider", "prompt_tokens", "completion_tokens",
                 "finish_reason", "temperature", "top_p", "seed", "data_sonda_utc", "erro"]
    csv_path = OUT_DIR / "probed_llm_metadata.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flat_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)

    print(f"\n[salvo] {csv_path}\n[salvo] {json_path}")
    ok = sum(1 for r in records if not r["erro"])
    print(f"[resumo] {ok}/{len(records)} modelos sondados com sucesso")


if __name__ == "__main__":
    main()
