"""Latência de inferência por documento: LLMs (Azure) e supervisionados (local).

Mede, sobre a mesma amostra de documentos sorteada com semente fixa, o tempo de
parede de uma inferência por documento:

* **LLMs** --- ``deepseek-v4-flash`` e ``gpt-4.1`` no Azure AI Foundry (Brazil),
  com a mesma configuração da rodada canônica (\\ *few-shot*, ``function_calling``,
  ``temperature=0``, ``seed=1007``). As chamadas são sequenciais e a primeira de
  cada modelo é descartada como aquecimento. Registra também os *tokens* e o
  ``finish_reason`` de cada chamada.
* **Supervisionados** --- ``legalbert-pt-fp`` (tamanho *base*) e
  ``bertimbau-large``, com as janelas deslizantes do protocolo (512 subpalavras,
  sobreposição 320) e a fusão por documento. A latência de inferência não
  depende dos pesos aprendidos, só da arquitetura e do número de janelas, então
  o *encoder* é carregado com a cabeça de classificação recém-inicializada, sem
  retreino. Mede em MPS (Apple Silicon) e em CPU.

Saída: ``dataset/results/models_outputs/latency/{llm,supervised}_latency.csv``.

Uso:
    uv run python scripts/measure_latency.py --part llm          # chamadas pagas ao Azure
    uv run python scripts/measure_latency.py --part supervised   # local
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np

from research.fewshot import FEWSHOT_RESULT_POSITIONS
from research.release import paths
from research.release.check_alignment import master_to_release_index

N_DOCS = 50
SEED = 1007
OUT_DIR = paths.RESULTS_ROOT / "latency"
LLMS = {"deepseek-v4-flash": "DeepSeek-V4-Flash", "gpt-4.1": "gpt-4.1"}
ENCODERS = {
    "legalbert-pt-fp": "raquelsilveira/legalbertpt_fp",
    "bertimbau-large": "neuralmind/bert-large-portuguese-cased",
}


def sample_positions() -> list[int]:
    """Master positions (866-row layout) of the sampled documents, few-shot excluded."""
    rng = np.random.default_rng(SEED)
    pool = [p for p in range(866) if p not in set(FEWSHOT_RESULT_POSITIONS)]
    return sorted(int(p) for p in rng.choice(pool, size=N_DOCS, replace=False))


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"gravado {path} ({len(rows)} linhas)")


def measure_llm() -> None:
    from dotenv import load_dotenv

    from research.release.run_llm_inference import _infer_one, load_corpus, make_extractor

    load_dotenv(paths.REPO_ROOT / ".env")
    texts = load_corpus()
    positions = sample_positions()
    rows: list[dict] = []
    for key, deployment in LLMS.items():
        extractor = make_extractor(
            None, structured="function_calling", azure_deployment=deployment,
            temperature=0, seed=SEED, include_raw=True,
        )
        _infer_one("few_shot", texts[positions[0]], extractor, None, None)  # aquecimento
        for pos in positions:
            for attempt in range(3):
                t0 = time.perf_counter()
                try:
                    _, meta = _infer_one("few_shot", texts[pos], extractor, None, None)
                except Exception as exc:  # noqa: BLE001 — erro transitório da API
                    print(f"{key} doc {pos} tentativa {attempt}: {exc}")
                    time.sleep(5)
                    continue
                elapsed = time.perf_counter() - t0
                meta = meta or {}
                rows.append(
                    {
                        "model": key,
                        "position": pos,
                        "seconds": round(elapsed, 4),
                        "attempts": attempt + 1,
                        "prompt_tokens": meta.get("prompt_tokens"),
                        "completion_tokens": meta.get("completion_tokens"),
                        "finish_reason": meta.get("finish_reason"),
                    }
                )
                break
        done = [r["seconds"] for r in rows if r["model"] == key]
        print(f"{key}: {len(done)} docs, mediana {np.median(done):.2f}s")
    _write(OUT_DIR / "llm_latency.csv", rows)


def measure_supervised() -> None:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    from research.kfold.data import label_set, load_bio_samples
    from research.kfold.train_bert import BertConfig
    from research.kfold.windows import build_windows, merge_window_predictions

    samples = load_bio_samples()
    _, label2id, id2label = label_set(samples)
    m2r = master_to_release_index()
    docs = [samples[m2r[p]] for p in sample_positions()]
    cfg = BertConfig()
    devices = (["mps"] if torch.backends.mps.is_available() else []) + ["cpu"]
    rows: list[dict] = []
    for key, name in ENCODERS.items():
        tokenizer = AutoTokenizer.from_pretrained(name)
        model = AutoModelForTokenClassification.from_pretrained(
            name, num_labels=len(label2id), id2label=id2label, label2id=label2id,
            ignore_mismatched_sizes=True,
        ).eval()
        for device in devices:
            model.to(device)

            def infer(doc, model=model, device=device):
                windows = build_windows(
                    doc["tokens"], doc["labels"], tokenizer, label2id,
                    max_length=cfg.max_length, stride=cfg.stride, doc_idx=0,
                )
                per_window = []
                with torch.no_grad():
                    for w in windows:
                        ids = torch.tensor([w.input_ids], device=device)
                        mask = torch.tensor([w.attention_mask], device=device)
                        logits = model(input_ids=ids, attention_mask=mask).logits
                        pred = logits.argmax(-1)[0].tolist()
                        per_window.append(
                            (w.word_ids, [id2label[p] for p in pred[: len(w.word_ids)]])
                        )
                if device == "mps":
                    torch.mps.synchronize()
                merge_window_predictions(len(doc["tokens"]), per_window)
                return len(windows)

            infer(docs[0])  # aquecimento
            for pos, doc in zip(sample_positions(), docs):
                t0 = time.perf_counter()
                n_windows = infer(doc)
                rows.append(
                    {
                        "model": key,
                        "device": device,
                        "position": pos,
                        "seconds": round(time.perf_counter() - t0, 4),
                        "n_windows": n_windows,
                        "n_words": len(doc["tokens"]),
                    }
                )
            done = [r["seconds"] for r in rows if r["model"] == key and r["device"] == device]
            print(f"{key}/{device}: mediana {np.median(done) * 1000:.0f} ms")
        del model
    _write(OUT_DIR / "supervised_latency.csv", rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--part", choices=["llm", "supervised"], required=True)
    args = ap.parse_args()
    measure_llm() if args.part == "llm" else measure_supervised()


if __name__ == "__main__":
    main()
