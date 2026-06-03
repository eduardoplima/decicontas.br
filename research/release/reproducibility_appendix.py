"""Reproducibility appendix for the evaluated models (p41a / p55c).

The raw API responses were not persisted, so the exact provider-side dated
snapshot (e.g. ``gpt-4-turbo-2024-04-09``), the call parameters
(``temperature``/``top_p``/``seed``) and the access date are **not**
recoverable from the artefacts in this repository. What *is* derivable from
the code/config is recorded here; everything that is not is marked explicitly
as ``NÃO PERSISTIDO`` rather than guessed.

Sources (transcribed verbatim, cited so they can be re-checked):
  * ``notebooks/ner_llm.ipynb`` cell 4 — ``AZURE_DEPLOYMENTS``, ``make_llm``
    (``max_tokens=4096``; no temperature/top_p/seed set), ``make_extractor``
    (``function_calling`` for all models except GPT-3.5 which uses
    ``json_mode``), and the provider/model table.
  * ``research.release.bootstrap_significance.MODELS`` / ``DISPLAY_NAMES`` —
    the authoritative list of evaluated models and their display names.
  * Supervised k-fold training configs live in
    ``dataset/results/supervised_kfold_corrected/summary/cv_*.json``.

Run:
    uv run python -m research.release.reproducibility_appendix
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from research.release.bootstrap_significance import DISPLAY_NAMES

from research.release import paths

REPO_ROOT = paths.REPO_ROOT
OUTPUT_DIR = paths.REPRODUCIBILITY_DIR  # cycle-specific

logger = logging.getLogger("research.release.reproducibility_appendix")

NOT_PERSISTED = "NÃO PERSISTIDO"

# NEW-CYCLE per-model facts. For the Brazil Azure deployments the served
# ``model`` field IS returned (dated snapshot) — so unlike the old cycle these
# are persisted. Azure-BR served via the Foundry OpenAI-compatible endpoint
# ({base}/openai/v1); gpt-5.x are reasoning models (max_completion_tokens).
_LLM: list[dict[str, str]] = [
    {"key": "gpt-4.1_few_shot", "routed_id": "Azure deployment gpt-4.1",
     "access": "Azure AI Foundry (Brazil)", "context": "1M",
     "snapshot": "gpt-4.1-2025-04-14", "structured": "function_calling"},
    {"key": "gpt-4.1-mini_few_shot", "routed_id": "Azure deployment gpt-4.1-mini",
     "access": "Azure AI Foundry (Brazil)", "context": "1M",
     "snapshot": "gpt-4.1-mini-2025-04-14", "structured": "function_calling"},
    {"key": "gpt-4.1-nano_few_shot", "routed_id": "Azure deployment gpt-4.1-nano",
     "access": "Azure AI Foundry (Brazil)", "context": "1M",
     "snapshot": "gpt-4.1-nano-2025-04-14", "structured": "function_calling"},
    {"key": "gpt-5-mini_few_shot", "routed_id": "Azure deployment gpt-5-mini",
     "access": "Azure AI Foundry (Brazil; reasoning)", "context": "—",
     "snapshot": "gpt-5-mini-2025-08-07", "structured": "function_calling"},
    {"key": "gpt-5.1_few_shot", "routed_id": "Azure deployment gpt-5.1",
     "access": "Azure AI Foundry (Brazil; reasoning)", "context": "—",
     "snapshot": "gpt-5.1-2025-11-13", "structured": "function_calling"},
    {"key": "gpt-5.2_few_shot", "routed_id": "Azure deployment gpt-5.2",
     "access": "Azure AI Foundry (Brazil; reasoning)", "context": "—",
     "snapshot": "gpt-5.2-2025-12-11", "structured": "function_calling"},
    {"key": "deepseek-v4-flash_few_shot", "routed_id": "Azure deployment DeepSeek-V4-Flash",
     "access": "Azure AI Foundry (Brazil)", "context": "1M",
     "snapshot": "DeepSeek-V4-Flash (open weights, MIT)", "structured": "function_calling"},
    {"key": "llama-3.3-70b_few_shot", "routed_id": "meta-llama/llama-3.3-70b-instruct",
     "access": "OpenRouter (provider: Fireworks/Together/DeepInfra)", "context": "131K",
     "snapshot": NOT_PERSISTED, "structured": "function_calling"},
    {"key": "qwen2.5-72b_few_shot", "routed_id": "qwen/qwen-2.5-72b-instruct",
     "access": "OpenRouter", "context": "32K", "snapshot": NOT_PERSISTED,
     "structured": "function_calling"},
]

# Supervised baselines: the "snapshot" is the Hugging Face model name (pinned),
# and training hyperparameters are persisted in the k-fold cv_*.json configs.
_SUPERVISED: list[dict[str, str]] = [
    {"key": "neuralmind_bert-base-portuguese-cased__supervised",
     "routed_id": "neuralmind/bert-base-portuguese-cased"},
    {"key": "neuralmind_bert-large-portuguese-cased__supervised",
     "routed_id": "neuralmind/bert-large-portuguese-cased"},
    {"key": "rufimelo_Legal-BERTimbau-base__supervised",
     "routed_id": "rufimelo/Legal-BERTimbau-base"},
    {"key": "bilstm-crf__supervised", "routed_id": "arquitetura local (BiLSTM-CRF)"},
]


def build_table() -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for m in _LLM:
        rows.append(
            {
                "modelo": DISPLAY_NAMES.get(m["key"], m["key"]),
                "chave_resultado": m["key"],
                "paradigma": "LLM few-shot",
                "id_roteado": m["routed_id"],
                "acesso": m["access"],
                "saida_estruturada": m.get(
                    "structured", "json_mode" if m["key"] == "gpt-35" else "function_calling"
                ),
                "max_tokens": "4096",
                "context_window": m["context"],
                "snapshot_datado": m["snapshot"],
                "temperature": NOT_PERSISTED,
                "top_p": NOT_PERSISTED,
                "seed": NOT_PERSISTED,
                "data_acesso": NOT_PERSISTED,
            }
        )
    for m in _SUPERVISED:
        rows.append(
            {
                "modelo": DISPLAY_NAMES.get(m["key"], m["key"]),
                "chave_resultado": m["key"],
                "paradigma": "supervisionado",
                "id_roteado": m["routed_id"],
                "acesso": "treino local (k-fold)",
                "saida_estruturada": "BIO token-classification",
                "max_tokens": "—",
                "context_window": "—",
                "snapshot_datado": (
                    "nome HF (pino)" if "/" in m["routed_id"] else "código local"
                ),
                "temperature": "—",
                "top_p": "—",
                "seed": "ver cv_*.json (config)",
                "data_acesso": "—",
            }
        )
    return pd.DataFrame(rows)


_GAPS_MD = f"""# Lacunas de reprodutibilidade (modelos LLM)

As respostas cruas das APIs **não foram persistidas** (os JSONs de predição
guardam apenas a saída estruturada). Portanto, os itens abaixo **não são
recuperáveis** a partir deste repositório e aparecem como `{NOT_PERSISTED}` na
tabela `N_model_reproducibility.csv`:

- **Snapshot datado exato** do provedor (ex.: `gpt-4-turbo-2024-04-09`). O
  acesso via OpenRouter/Azure resolvia o modelo para o snapshot servido no
  momento da execução, que não foi registrado. Exceção: `deepseek-v3` está
  fixado em `deepseek/deepseek-chat-v3-0324` (pino datado no próprio código).
- **Parâmetros de chamada** `temperature`, `top_p`, `seed`. O código
  (`notebooks/ner_llm.ipynb`, cell 4, `make_llm`) define apenas
  `max_tokens=4096`; os demais usaram os defaults do SDK e não foram fixados,
  logo não são reconstrutíveis com certeza.
- **Data de acesso** de cada execução (não registrada por modelo).

O que **é** derivável do código/config (e está na tabela): a forma de acesso
(OpenRouter vs Azure e o respectivo *deployment*), o id de modelo roteado, o
método de saída estruturada (`function_calling`, exceto GPT-3.5 em `json_mode`),
`max_tokens=4096`, e a janela de contexto declarada na tabela do notebook.

**Observação de fidelidade:** há inconsistência de nomenclatura entre a tabela
de provedores do notebook (que lista famílias `gpt-5`/`gpt-4.1`) e o
`AZURE_DEPLOYMENTS` (que define *deployments* `gpt-5.4*`). A coluna `id_roteado`
reproduz o que está literalmente no `AZURE_DEPLOYMENTS`/tabela; a resolução
provedor→snapshot não foi persistida.

Os baselines **supervisionados** são totalmente reproduzíveis: o "snapshot" é o
nome do modelo no Hugging Face (pino por nome) e os hiperparâmetros de treino
estão em `dataset/results/supervised_kfold_corrected/summary/cv_*.json`.
"""


def _to_latex(df: pd.DataFrame) -> str:
    cols = ["modelo", "id_roteado", "acesso", "saida_estruturada", "snapshot_datado"]
    sub = df[cols]
    body = []
    for _, r in sub.iterrows():
        cells = [str(r[c]).replace("_", r"\_").replace("&", r"\&") for c in cols]
        body.append("        " + " & ".join(cells) + r" \\")
    return (
        "\\begin{table}[ht]\n    \\centering\n"
        "    \\caption{Identificadores e configuração de chamada dos modelos "
        "avaliados (derivável do código). Itens marcados NÃO PERSISTIDO não "
        "constam dos artefatos; ver apêndice de lacunas.}\n"
        "    \\label{tab:reprodutibilidade_modelos}\n    \\scriptsize\n"
        "    \\begin{tabular}{lllll}\n        \\hline\n"
        "        \\textbf{Modelo} & \\textbf{ID roteado} & \\textbf{Acesso} & "
        "\\textbf{Saída} & \\textbf{Snapshot} \\\\\n        \\hline\n"
        + "\n".join(body)
        + "\n        \\hline\n    \\end{tabular}\n\\end{table}\n"
    )


def run(output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = build_table()
    df.to_csv(output_dir / "N_model_reproducibility.csv", index=False)
    (output_dir / "table_model_reproducibility.tex").write_text(
        _to_latex(df), encoding="utf-8"
    )
    (output_dir / "REPRODUCIBILITY_GAPS.md").write_text(_GAPS_MD, encoding="utf-8")
    logger.info("wrote %s", output_dir / "N_model_reproducibility.csv")
    logger.info("wrote %s", output_dir / "table_model_reproducibility.tex")
    logger.info("wrote %s", output_dir / "REPRODUCIBILITY_GAPS.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run()


if __name__ == "__main__":
    main()
