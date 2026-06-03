"""Análise de sensibilidade dos pesos do ensemble Cleanlab (p37, Seção 4.3.1).

Objetivo
--------
Mostrar empiricamente se o conjunto sinalizado pela auditoria Cleanlab é ROBUSTO à
escolha dos pesos do ensemble (referência ``w_linear=0,3``, ``w_transformer=0,7``).
A análise é **puramente aditiva e read-only** sobre os artefatos canônicos: NÃO altera
``dataset-corrections.json``, os releases, nem o corpus.

Método (fiel ao notebook ``notebooks/aed_decicontas.ipynb``)
------------------------------------------------------------
1. Reconstrói a sequência exata de tokens/BIO via ``research.dataset.get_decicontas_df``
   + tokenização ``re.finditer(r'\\S+')`` (igual ao notebook e a ``research/dataset_io``).
   Valida o sistema de coordenadas contra o JSON canônico (``document_id`` == id do
   Label Studio; ``token_idx_in_doc`` == posição ``\\S+``). Se não alinhar, ABORTA.
2. Re-gera as probabilidades out-of-fold (seed=43, 5-fold) dos dois modelos e as
   guarda em cache (.npy). Em execuções seguintes, carrega o cache (não retreina).
     - linear: SGDClassifier(log_loss) sobre embeddings do BERTimbau-Large (StratifiedKFold);
     - transformer: BERTimbau-Base fine-tuned p/ token-classification (KFold por sentença).
   ATENÇÃO: o fine-tuning em MPS não é bit-determinístico; o re-run de 0,3/0,7 não
   reproduz exatamente o conjunto canônico (drift reportado).
3. Recombina sob 4 esquemas de peso e reaplica EXATAMENTE a mesma chamada
   ``find_label_issues(..., return_indices_ranked_by='self_confidence')``. A única coisa
   que varia entre esquemas é o vetor de pesos.
4. Conjunto de referência ≥0,95: tomado DIRETAMENTE do artefato canônico
   (``dataset-corrections.json`` — os 566 ``group_id`` decididos têm fronteiras exatas),
   evitando reconstruir agregação/corte (mais fiel). Para cada esquema, mede quantos
   desses grupos PERMANECEM SINALIZADOS (contêm ≥1 token sinalizado na sua faixa).
5. Mapeia os 22 grupos efetivamente acatados (accept+custom) e mede quantos reaparecem.

Saídas em ``dataset/errors/sensitivity/``: ``weight_sensitivity.csv``, ``p37_snippet.tex``,
``versions.txt``. Cache em ``dataset/errors/oof_cache/``.

Uso:
    uv run python scripts/cleanlab_weight_sensitivity.py            # usa cache se houver
    uv run python scripts/cleanlab_weight_sensitivity.py --retrain  # força re-treino
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import re
import sys
from pathlib import Path

# Igual ao notebook (cell 1): remove o teto de alocação do MPS antes de importar torch.
os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
ERRORS_DIR = REPO / "dataset" / "errors"
CACHE_DIR = ERRORS_DIR / "oof_cache"
OUT_DIR = ERRORS_DIR / "sensitivity"
CORRECTIONS_JSON = ERRORS_DIR / "dataset-corrections.json"
CANON_CSV = ERRORS_DIR / "erros_anotacao_decicontas.csv"

RANDOM_SEED = 43          # seed REAL da auditoria (não 1007, que é do k-fold supervisionado)
NUM_FOLDS_CV = 5
EFFECTIVE_MAX_LENGTH = 512
TOKEN_RE = re.compile(r"\S+")

# Esquemas de peso (w_linear/SGD, w_transformer). A ÚNICA coisa que varia.
WEIGHT_SCHEMES = [
    ("ref_0.3_0.7", 0.3, 0.7),
    ("iguais_0.5_0.5", 0.5, 0.5),
    ("so_transformer_0.0_1.0", 0.0, 1.0),
    ("so_linear_1.0_0.0", 1.0, 0.0),
]
REF_SCHEME = "ref_0.3_0.7"


# --------------------------------------------------------------------------- #
# 1. Sequência de tokens (fiel ao notebook) + validação de coordenadas
# --------------------------------------------------------------------------- #
def build_token_sequence():
    from research.dataset import get_decicontas_df

    df = get_decicontas_df()  # 861 docs, few-shot filtrado, reset_index

    sentencas: list[list[tuple[str, str]]] = []
    ls_ids: list[int] = []
    for _, row in df.iterrows():
        text = row["data"]["text"]
        spans = _extract_spans(row["annotations"])
        tokens, tags = _spans_to_bio(text, spans)
        if tokens:
            sentencas.append(list(zip(tokens, tags)))
            ls_ids.append(int(row["id"]))

    todos_tokens: list[str] = []
    todos_labels: list[str] = []
    ids_sentenca: list[int] = []
    for i, sent in enumerate(sentencas):
        for tok, tag in sent:
            todos_tokens.append(tok)
            todos_labels.append(tag)
            ids_sentenca.append(i)

    global_offset = np.zeros(len(sentencas), dtype=int)
    acc = 0
    for i, sent in enumerate(sentencas):
        global_offset[i] = acc
        acc += len(sent)

    id_to_sentidx = {lid: i for i, lid in enumerate(ls_ids)}
    return {
        "sentencas": sentencas,
        "ls_ids": ls_ids,
        "id_to_sentidx": id_to_sentidx,
        "todos_tokens": todos_tokens,
        "todos_labels": todos_labels,
        "ids_sentenca": np.asarray(ids_sentenca),
        "global_offset": global_offset,
        "n_tokens": len(todos_tokens),
    }


def _extract_spans(annotations):
    dict_labels = {"MULTA_FIXA": "MULTA", "MULTA_PERCENTUAL": "MULTA", "OBRIGACAO_MULTA": "OBRIGACAO"}
    spans = []
    for annot in annotations:
        for result in annot.get("result", []):
            val = result.get("value", {})
            if "start" in val and "end" in val and "labels" in val:
                label = dict_labels.get(val["labels"][0], val["labels"][0])
                spans.append({"start": val["start"], "end": val["end"], "label": label})
    spans.sort(key=lambda s: s["start"])
    return spans


def _spans_to_bio(text, spans):
    tokens, offsets = [], []
    for m in TOKEN_RE.finditer(text):
        tokens.append(m.group())
        offsets.append((m.start(), m.end()))
    tags = ["O"] * len(tokens)
    for span in spans:
        first = True
        for idx, (a, b) in enumerate(offsets):
            if a < span["end"] and b > span["start"]:
                tags[idx] = f"B-{span['label']}" if first else f"I-{span['label']}"
                first = False
    return tokens, tags


def validate_coordinates(seq) -> None:
    """Confirma que (document_id, token_idx_in_doc) do JSON mapeia para a nossa
    sequência. ABORTA se a fidelidade não se sustentar."""
    d = json.loads(CORRECTIONS_JSON.read_text(encoding="utf-8"))
    rows = pd.read_csv(CANON_CSV)
    id2s = seq["id_to_sentidx"]
    sentencas = seq["sentencas"]
    ok_tok = bad_tok = 0
    for t in d["token_changes"]:
        rid = t.get("row_id")
        if rid is None or rid >= len(rows):
            continue
        si = id2s.get(t["document_id"])
        tix = t["token_idx_in_doc"]
        if si is None or tix >= len(sentencas[si]):
            bad_tok += 1
            continue
        if sentencas[si][tix][0] == str(rows.iloc[rid]["token"]):
            ok_tok += 1
        else:
            bad_tok += 1
    total = ok_tok + bad_tok
    rate = ok_tok / total if total else 0.0
    print(f"[validação] coordenadas JSON↔sequência: {ok_tok}/{total} ok ({rate:.4f})")
    if rate < 0.999:
        sys.exit(
            f"ABORTANDO: alinhamento de coordenadas falhou ({rate:.4f} < 0.999). "
            "A reprodução não é fiel — não vou aproximar em silêncio."
        )


# --------------------------------------------------------------------------- #
# 2. Probabilidades out-of-fold (com cache)
# --------------------------------------------------------------------------- #
def get_oof_probs(seq, retrain: bool):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p_sgd_f = CACHE_DIR / "P_linear_sgd.npy"
    p_tr_f = CACHE_DIR / "P_transformer.npy"
    meta_f = CACHE_DIR / "meta.json"

    if not retrain and p_sgd_f.exists() and p_tr_f.exists() and meta_f.exists():
        meta = json.loads(meta_f.read_text())
        if meta.get("n_tokens") == seq["n_tokens"]:
            print(f"[cache] carregando probabilidades OOF de {CACHE_DIR}")
            return np.load(p_sgd_f), np.load(p_tr_f), meta["classes"]
        print("[cache] n_tokens divergente — re-gerando")

    print("[treino] regenerando probabilidades OOF (seed=43, 5-fold) — pode levar ~15-20 min")
    p_sgd, p_tr, classes = _regenerate(seq)
    np.save(p_sgd_f, p_sgd)
    np.save(p_tr_f, p_tr)
    meta_f.write_text(json.dumps({"n_tokens": seq["n_tokens"], "classes": classes, "seed": RANDOM_SEED}))
    _write_versions()
    return p_sgd, p_tr, classes


def _regenerate(seq):
    import torch
    from sklearn.linear_model import SGDClassifier
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import LabelEncoder
    from transformers import AutoModel, AutoTokenizer, set_seed

    set_seed(RANDOM_SEED)
    sentencas = seq["sentencas"]
    todos_labels = seq["todos_labels"]
    device = torch.device("cuda" if torch.cuda.is_available()
                          else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[treino] device={device}")

    label_encoder = LabelEncoder()
    labels_cod = label_encoder.fit_transform(todos_labels)
    num_classes = len(label_encoder.classes_)
    classes = list(label_encoder.classes_)

    # --- modelo 1: embeddings BERTimbau-Large -> SGDClassifier --------------- #
    p_sgd_cache = CACHE_DIR / "P_linear_sgd.npy"
    if p_sgd_cache.exists() and np.load(p_sgd_cache).shape == (len(todos_labels), num_classes):
        print("[treino] reusando P_sgd em cache (pula embeddings + SGD)")
        return np.load(p_sgd_cache), _train_transformer(
            seq, sentencas, todos_labels, classes, num_classes, device
        ), classes

    tok_l = AutoTokenizer.from_pretrained("neuralmind/bert-large-portuguese-cased")
    enc_l = AutoModel.from_pretrained("neuralmind/bert-large-portuguese-cased").to(device).eval()
    feats = []
    for sent in sentencas:
        textos = [t for t, _ in sent]
        inputs = tok_l(textos, is_split_into_words=True, return_tensors="pt",
                       padding="longest", truncation=True, max_length=EFFECTIVE_MAX_LENGTH).to(device)
        word_ids = inputs.word_ids()
        with torch.no_grad():
            hidden = enc_l(**inputs).last_hidden_state
        buckets: list[list] = [[] for _ in range(len(textos))]
        for sub_idx, wid in enumerate(word_ids):
            if wid is not None:
                buckets[wid].append(hidden[0, sub_idx, :])
        for wid in range(len(textos)):
            if buckets[wid]:
                feats.append(torch.mean(torch.stack(buckets[wid]), dim=0).cpu().numpy())
            else:
                feats.append(np.zeros(enc_l.config.hidden_size))
    feats = np.asarray(feats)
    print(f"[treino] features SGD: {feats.shape}")

    p_sgd = np.zeros((len(feats), num_classes))
    skf = StratifiedKFold(n_splits=NUM_FOLDS_CV, shuffle=True, random_state=RANDOM_SEED)
    for k, (tr, va) in enumerate(skf.split(feats, labels_cod)):
        clf = SGDClassifier(loss="log_loss", penalty="l2", alpha=0.0001, max_iter=1000,
                            tol=1e-3, random_state=RANDOM_SEED, class_weight="balanced",
                            learning_rate="optimal", early_stopping=True,
                            n_iter_no_change=10, validation_fraction=0.1)
        clf.fit(feats[tr], labels_cod[tr])
        p_sgd[va] = clf.predict_proba(feats[va])
        print(f"[treino] SGD fold {k + 1}/{NUM_FOLDS_CV} ok")
    del enc_l, feats
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    np.save(p_sgd_cache, p_sgd)  # cache parcial: poupa embeddings caros em retries

    p_tr = _train_transformer(seq, sentencas, todos_labels, classes, num_classes, device)
    return p_sgd, p_tr, classes


def _train_transformer(seq, sentencas, todos_labels, classes, num_classes, device):
    """Modelo 2: BERTimbau-Base fine-tuned (token classification), OOF por KFold de
    sentença. Probabilidade do primeiro subword de cada token, reordenada p/ ``classes``."""
    import torch
    from sklearn.model_selection import KFold
    from transformers import (
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        Trainer,
        TrainingArguments,
    )
    from datasets import Dataset

    label_list = sorted(set(todos_labels))
    label2id = {lab: i for i, lab in enumerate(label_list)}
    id2label = {i: lab for lab, i in label2id.items()}
    toks_by_sent = [[t for t, _ in s] for s in sentencas]
    tags_by_sent = [[label2id[tag] for _, tag in s] for s in sentencas]
    ft_tok = AutoTokenizer.from_pretrained("neuralmind/bert-base-portuguese-cased")

    def align(tokens, tags):
        enc = ft_tok(tokens, is_split_into_words=True, truncation=True,
                     max_length=EFFECTIVE_MAX_LENGTH, padding=False)
        out, prev = [], None
        for wid in enc.word_ids():
            if wid is None:
                out.append(-100)
            elif wid != prev:
                out.append(tags[wid])
            else:
                name = id2label[tags[wid]]
                out.append(label2id["I-" + name[2:]] if name.startswith("B-") else tags[wid])
            prev = wid
        enc["labels"] = out
        return enc

    p_tr = np.zeros((len(todos_labels), num_classes))
    kf = KFold(n_splits=NUM_FOLDS_CV, shuffle=True, random_state=RANDOM_SEED)
    collator = DataCollatorForTokenClassification(ft_tok, padding=True)
    for k, (tr_s, va_s) in enumerate(kf.split(np.arange(len(sentencas)))):
        tr_d = {"input_ids": [], "attention_mask": [], "labels": []}
        va_d = {"input_ids": [], "attention_mask": [], "labels": []}
        va_word_ids = []
        for sid in tr_s:
            e = align(toks_by_sent[sid], tags_by_sent[sid])
            for key in tr_d:
                tr_d[key].append(e[key])
        for sid in va_s:
            e = align(toks_by_sent[sid], tags_by_sent[sid])
            for key in va_d:
                va_d[key].append(e[key])
            va_word_ids.append(ft_tok(toks_by_sent[sid], is_split_into_words=True,
                                      truncation=True, max_length=EFFECTIVE_MAX_LENGTH).word_ids())
        model = AutoModelForTokenClassification.from_pretrained(
            "neuralmind/bert-base-portuguese-cased", num_labels=num_classes,
            id2label=id2label, label2id=label2id)
        args = TrainingArguments(
            output_dir=str(REPO / f"dataset/results/ner_fold_{k}"),
            num_train_epochs=5, per_device_train_batch_size=2, gradient_accumulation_steps=8,
            per_device_eval_batch_size=4, learning_rate=3e-5, weight_decay=0.01,
            warmup_ratio=0.1, logging_steps=50, eval_strategy="epoch", save_strategy="no",
            report_to="none", seed=RANDOM_SEED, fp16=torch.cuda.is_available())
        trainer = Trainer(model=model, args=args, train_dataset=Dataset.from_dict(tr_d),
                          eval_dataset=Dataset.from_dict(va_d), data_collator=collator)
        trainer.train()
        logits = trainer.predict(Dataset.from_dict(va_d)).predictions
        for local, gsid in enumerate(va_s):
            wids = va_word_ids[local]
            probs = torch.softmax(torch.tensor(logits[local]), dim=-1).numpy()
            n_orig = len(toks_by_sent[gsid])
            tok_probs = np.zeros((n_orig, num_classes))
            prev = None
            for sub_idx, wid in enumerate(wids):
                if wid is not None and sub_idx < len(probs) and wid != prev:
                    tok_probs[wid] = probs[sub_idx]
                prev = wid
            off = int(seq["global_offset"][gsid])
            for pos in range(n_orig):
                fi = off + pos
                if fi < len(p_tr):
                    for cls_idx, cls_name in enumerate(label_list):
                        p_tr[fi, classes.index(cls_name)] = tok_probs[pos, cls_idx]
        del model, trainer
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        print(f"[treino] transformer fold {k + 1}/{NUM_FOLDS_CV} ok")
    return p_tr


def _write_versions():
    import cleanlab
    import sklearn
    import torch
    import transformers
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "versions.txt").write_text(
        f"python={platform.python_version()}\nplatform={platform.platform()}\n"
        f"seed={RANDOM_SEED}\nnumpy={np.__version__}\nsklearn={sklearn.__version__}\n"
        f"torch={torch.__version__}\ntransformers={transformers.__version__}\n"
        f"cleanlab={cleanlab.__version__}\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# 3-5. Flagging por esquema + métricas de robustez
# --------------------------------------------------------------------------- #
def _ensemble(p_sgd, p_tr, w_sgd, w_tr):
    ens = w_sgd * p_sgd + w_tr * p_tr
    s = ens.sum(axis=1, keepdims=True)
    s[s == 0] = 1
    return ens / s


def flag_tokens(ens, labels_cod) -> set[int]:
    """find_label_issues (default ``prune_by_noise_rate``) ∩ sugerido≠original — o
    conjunto OPERACIONAL da auditoria (tamanho variável conforme os pesos)."""
    from cleanlab.filter import find_label_issues

    issues = find_label_issues(labels=labels_cod, pred_probs=ens,
                               return_indices_ranked_by="self_confidence")
    arg = ens.argmax(axis=1)
    return {int(i) for i in issues if arg[i] != labels_cod[i]}


def topn_suspicious(ens, labels_cod, n) -> set[int]:
    """Teste CONTROLADO POR TAMANHO: ranqueia os candidatos (sugerido≠original) pela
    self-confidence (prob. do rótulo dado, ascendente = mais suspeito) e devolve os N
    mais suspeitos. Com N fixo entre esquemas, a sobreposição reflete concordância de
    RANKING, isolando o efeito do tamanho do corte do ``find_label_issues``."""
    self_conf = ens[np.arange(len(labels_cod)), labels_cod]
    arg = ens.argmax(axis=1)
    cand = np.where(arg != labels_cod)[0]
    order = cand[np.argsort(self_conf[cand], kind="stable")]
    return {int(i) for i in order[:n]}


def load_reference_groups(seq):
    """Grupos canônicos a partir do artefato. Retorna (decididos, alterados), cada
    um {group_id: set(global_idx na faixa)}."""
    d = json.loads(CORRECTIONS_JSON.read_text(encoding="utf-8"))
    id2s = seq["id_to_sentidx"]
    offs = seq["global_offset"]
    sentencas = seq["sentencas"]
    decided: dict[str, set[int]] = {}
    altered_ids: set[str] = set()
    for t in d["token_changes"]:
        gid = t["group_id"]
        if gid not in decided:
            doc, rng = gid.split(":")
            a, b = (int(x) for x in rng.split("-"))
            si = id2s.get(int(doc))
            if si is None:
                continue
            n = len(sentencas[si])
            decided[gid] = {int(offs[si]) + p for p in range(a, min(b, n - 1) + 1)}
        if t["decision"] in ("accept", "custom"):
            altered_ids.add(gid)
    altered = {gid: decided[gid] for gid in altered_ids if gid in decided}
    return decided, altered


def overlap_groups(groups: dict[str, set[int]], flagged: set[int]) -> int:
    """Nº de grupos que permanecem sinalizados (≥1 token sinalizado na sua faixa)."""
    return sum(1 for rng in groups.values() if rng & flagged)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--retrain", action="store_true", help="força re-treino (ignora cache)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seq = build_token_sequence()
    print(f"[dados] {len(seq['sentencas'])} docs, {seq['n_tokens']} tokens")
    validate_coordinates(seq)

    p_sgd, p_tr, classes = get_oof_probs(seq, retrain=args.retrain)
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder().fit(seq["todos_labels"])
    labels_cod = le.transform(seq["todos_labels"])
    assert list(le.classes_) == classes, "ordem de classes divergente do cache"

    decided, altered = load_reference_groups(seq)
    print(f"[ref] grupos decididos (≥0,95): {len(decided)} | alterados: {len(altered)}")

    n_canon = sum(1 for _ in CANON_CSV.open(encoding="utf-8")) - 1  # tamanho do corte real
    print(f"[ref] tamanho do conjunto canônico (CSV): {n_canon}")

    flagged_by_scheme: dict[str, set[int]] = {}   # operacional (find_label_issues)
    topn_by_scheme: dict[str, set[int]] = {}       # controlado por tamanho (top-N)
    for name, w_sgd, w_tr in WEIGHT_SCHEMES:
        ens = _ensemble(p_sgd, p_tr, w_sgd, w_tr)
        flagged_by_scheme[name] = flag_tokens(ens, labels_cod)
        topn_by_scheme[name] = topn_suspicious(ens, labels_cod, n_canon)
        print(f"[flag] {name}: operacional={len(flagged_by_scheme[name])} | top-{n_canon} (controlado)")

    ref_op = flagged_by_scheme[REF_SCHEME]
    ref_tn = topn_by_scheme[REF_SCHEME]
    n_dec, n_alt = len(decided), len(altered)
    records = []
    for name, w_sgd, w_tr in WEIGHT_SCHEMES:
        op, tn = flagged_by_scheme[name], topn_by_scheme[name]
        op_i, op_u = len(op & ref_op), len(op | ref_op)
        tn_i = len(tn & ref_tn)
        records.append({
            "scheme": name, "w_linear": w_sgd, "w_transformer": w_tr,
            "n_flagged_op": len(op),
            "op_overlap_pct": round(100 * op_i / len(ref_op), 1) if ref_op else 0.0,
            "op_jaccard": round(op_i / op_u, 4) if op_u else 0.0,
            "op_decided_pct": round(100 * overlap_groups(decided, op) / n_dec, 1) if n_dec else 0.0,
            "op_altered": f"{overlap_groups(altered, op)}/{n_alt}",
            "ctrl_overlap_pct": round(100 * tn_i / len(ref_tn), 1) if ref_tn else 0.0,
            "ctrl_decided_pct": round(100 * overlap_groups(decided, tn) / n_dec, 1) if n_dec else 0.0,
            "ctrl_altered": f"{overlap_groups(altered, tn)}/{n_alt}",
        })
    df_out = pd.DataFrame(records)

    # AMBOS alternativos (0,5/0,5 E transformer) — CONTROLADO POR TAMANHO (top-N)
    a, b = topn_by_scheme["iguais_0.5_0.5"], topn_by_scheme["so_transformer_0.0_1.0"]
    dec_both = sum(1 for rng in decided.values() if (rng & a) and (rng & b))
    alt_both = sum(1 for rng in altered.values() if (rng & a) and (rng & b))
    pct_both = round(100 * dec_both / n_dec, 1) if n_dec else 0.0

    csv_path = OUT_DIR / "weight_sensitivity.csv"
    df_out.to_csv(csv_path, index=False)
    print("\n===== TABELA DE SENSIBILIDADE (op=operacional | ctrl=controlado por tamanho) =====")
    print(df_out.to_string(index=False))
    print(f"\n[controlado, top-{n_canon}] grupos ≥0,95 cobertos em AMBOS (0,5/0,5 E transformer): "
          f"{dec_both}/{n_dec} ({pct_both}%) | alterados em ambos: {alt_both}/{n_alt}")
    print(f"[salvo] {csv_path}")

    ctrl_min = df_out[~df_out.scheme.str.startswith("ref")]["ctrl_decided_pct"].min()
    _emit_statement(df_out, pct_both, alt_both, n_alt, ctrl_min)
    _emit_latex(pct_both, alt_both, n_dec, n_alt, ctrl_min)


def _vir(x) -> str:
    return str(x).replace(".", "{,}")


def _is_robust(ctrl_min, alt_both, n_alt) -> bool:
    return ctrl_min >= 85.0 and (alt_both / n_alt if n_alt else 0) >= 0.85


def _emit_latex(pct_both, alt_both, n_dec, n_alt, ctrl_min) -> None:
    """Gera trecho HONESTO conforme o veredito (controlado por tamanho)."""
    if _is_robust(ctrl_min, alt_both, n_alt):
        snippet = (
            "Para confirmar empiricamente essa independência, a sinaliza\\c{c}\\~ao foi recomputada "
            "sob dois esquemas alternativos de pondera\\c{c}\\~ao --- pesos iguais "
            "($w_{\\text{linear}} = w_{\\text{transformer}} = 0{,}5$) e apenas o modelo "
            "\\textit{transformer} ($w_{\\text{transformer}} = 1{,}0$) ---, controlando o tamanho "
            "do conjunto sinalizado. Das " + str(n_dec) + " sinaliza\\c{c}\\~oes de alta confian\\c{c}a "
            "($\\textit{score} \\geq 0{,}95$) inspecionadas, " + _vir(pct_both) + "\\% permanecem "
            "sinalizadas em ambos os esquemas, e " + str(alt_both) + " das " + str(n_alt) +
            " corre\\c{c}\\~oes efetivamente acatadas reaparecem em todos eles, confirmando que o "
            "resultado da auditoria n\\~ao depende da escolha de $0{,}3/0{,}7$.\n"
        )
    else:
        snippet = (
            "% ACHADO: a sinaliza\\c{c}\\~ao mostrou-se SENS\\'IVEL aos pesos do ensemble "
            "(n\\~ao afirmar robustez). Trecho honesto abaixo.\n"
            "Uma an\\'alise de sensibilidade recomputou a sinaliza\\c{c}\\~ao sob esquemas "
            "alternativos de pondera\\c{c}\\~ao --- pesos iguais ($0{,}5/0{,}5$) e apenas o modelo "
            "\\textit{transformer} ($1{,}0$) ---, controlando o tamanho do conjunto. Apenas "
            + _vir(pct_both) + "\\% das " + str(n_dec) + " sinaliza\\c{c}\\~oes de alta confian\\c{c}a "
            "inspecionadas permanecem entre as mais suspeitas em ambos os esquemas, indicando que o "
            "\\emph{conjunto} sinalizado depende da pondera\\c{c}\\~ao adotada. As " + str(alt_both) +
            " das " + str(n_alt) + " corre\\c{c}\\~oes efetivamente acatadas que reaparecem sugerem "
            "maior estabilidade das corre\\c{c}\\~oes de fato aplicadas, ainda que o procedimento de "
            "sinaliza\\c{c}\\~ao, isoladamente, n\\~ao seja invariante \\`a escolha de $0{,}3/0{,}7$.\n"
        )
    (OUT_DIR / "p37_snippet.tex").write_text(snippet, encoding="utf-8")
    print(f"[salvo] {OUT_DIR / 'p37_snippet.tex'} (robusto={_is_robust(ctrl_min, alt_both, n_alt)})")


def _emit_statement(df, pct_both, alt_both, n_alt, ctrl_min) -> None:
    robust = _is_robust(ctrl_min, alt_both, n_alt)
    verdict = (
        "Os números (controlados por tamanho) SUSTENTAM a robustez: alta sobreposição do "
        "conjunto inspecionado sob os esquemas alternativos."
        if robust else
        "ATENÇÃO: mesmo controlando o tamanho do corte, a sobreposição NÃO é alta — a "
        "sinalização é SENSÍVEL aos pesos. Reportar como achado; NÃO afirmar robustez."
    )
    (OUT_DIR / "statement.txt").write_text(
        f"min(ctrl_decided_pct) entre alternativos = {ctrl_min}%\n"
        f"grupos decididos cobertos em ambos (controlado) = {pct_both}%\n"
        f"alterados retidos em ambos = {alt_both}/{n_alt}\n{verdict}\n", encoding="utf-8")
    print("\n===== STATEMENT =====")
    print(verdict)


if __name__ == "__main__":
    main()
