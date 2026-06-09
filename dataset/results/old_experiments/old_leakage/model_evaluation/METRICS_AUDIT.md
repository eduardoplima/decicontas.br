# Auditoria do código de métricas

Varredura focada em encontrar falhas no cálculo das métricas reportadas (token F1, span F1, IoU, bootstrap). Cada item indica gravidade, arquivo e linha, descrição, impacto empírico medido e a sugestão de correção.

Os arquivos auditados:
- `tools/ner_metrics.py` (498 linhas)
- `tools/release/bootstrap_significance.py` (689 linhas)
- `tools/release/chapter5_numbers.py` (981 linhas)
- `backend/scripts/supervised_kfold/metrics.py` (30 linhas)

---

## 🔴 ALTA — Comparação token-F1 entre LLM e supervisionado é incomensurável

**Onde:** `tools/ner_metrics.py:205-233` (LLM, via spaCy) vs `tools/ner_metrics.py:362-400` e `tools/release/chapter5_numbers.py:_per_entity_metrics_bio` (supervisionado, via `\S+`).

**Problema:** Token F1 de LLMs é computado sobre tokens spaCy `pt_core_news_sm`; token F1 de supervisionados é computado sobre tokens whitespace `\S+`. Os dois esquemas têm contagens de tokens **diferentes** para o mesmo documento (`pt_core_news_sm` quebra pontuação, contrações, hífens; `\S+` não). Isso significa que precisão/revocação/F1 de token usam **denominadores diferentes** entre LLM e supervisionado e **não podem ser comparados diretamente** na Tabela 5.1.

**Impacto:** O atual leaderboard mistura supervisionados com token F1 entre 0.72 e 0.86 contra LLMs com 0.57 a 0.81. Boa parte dessa diferença pode ser tokenização, não modelo.

**Empírico:** verificável diferença sistemática quando o mesmo BIO é tokenizado pelos dois métodos. Difere em cada doc; aproximadamente 5–15 % a mais de tokens em spaCy.

**Sugestão:** (a) reportar token F1 sempre via spaCy (rotando supervisionados por `bio_to_char_spans`+`calculate_metrics`, que `full_evaluation` em `ner_metrics.py:423` já faz); ou (b) abandonar token F1 do leaderboard principal e manter apenas span F1, que é tokenizer-agnóstico.

---

## 🔴 ALTA — Matching assimétrico entre `calculate_metrics` e `compute_doc_level_counts`

**Onde:**
- `tools/ner_metrics.py:244-254` (LLM): cada `pred` casa com no máximo **um** `gold` (há `break` no loop interno após primeira correspondência IoU≥threshold).
- `tools/release/bootstrap_significance.py:271-279` (bootstrap): conta **todos** os pares `(pred, gold)` com IoU≥threshold (sem `break`).

```python
# calculate_metrics:
for pi, p in enumerate(pred_spans):
    for gi, g in enumerate(gold_spans):
        if compute_iou_score(...) > 0:
            label_metrics[p[2]]["matched"] += 1
            matched_pairs.add((pi, gi))
            break                    # <-- 1 pred ↛ múltiplos golds

# bootstrap compute_doc_level_counts:
for ps in pred:
    for gs in gold:
        if iou >= iou_threshold:
            matches += 1             # <-- conta todos os pares
```

**Problema:** Para um doc com 1 `pred` que sobrepõe 2 `golds` distintos, ambos com IoU≥0.5 (ex.: gold spans aninhados/sobrepostos), o `calculate_metrics` conta **1** match enquanto o bootstrap conta **2**. O notebook `statistical_significance.ipynb` afirma que ambos são consistentes (e que `f1_from_sums` reproduz o F1 corpus-level de `calculate_metrics`); o **código contradiz a documentação**.

**Impacto empírico (medido):** No GPT-4 Turbo (corrigido) há 1 doc multi-match em 861. Diferença em F1 < 1e-6 (não detectável a 4 casas decimais). Em modelos com mais sobreposições poderia bater. Sem efeito reportável para os números atuais, mas **a divergência semântica é real** e pode surpreender ao depurar ou estender para datasets com aninhamento real.

**Sugestão:** unificar — preferível fazer matching **bipartido por IoU descendente** (Hungarian/greedy) e reusar a mesma função em ambos os pipelines. Se quiser preservar a semântica atual do bootstrap, alinhar `calculate_metrics` (remover o `break`).

---

## 🟡 MÉDIA — `convert_pred_to_golden_format` descarta predições silenciosamente

**Onde:** `tools/ner_metrics.py:118-163` e a cópia local em `tools/release/bootstrap_significance.py:99-148`.

**Problema:** O alinhamento por janela deslizante exige `fuzz.partial_ratio(span_text, window) >= min_score=80`. Predições que o LLM gerou parafraseadas, com ortografia levemente diferente do texto-fonte, ou em texto com OCR ruim, **caem silenciosamente** abaixo do limiar e somem do conjunto avaliado. Isso enviesa **para baixo** o desempenho LLM (penalizando dois caminhos: pred descartada → recall cai; e qualquer pred ruim que fica → precisão cai).

**Impacto empírico:** Para GPT-4 Turbo, **2/551 = 0,36%** das predições foram descartadas pelo alinhador. Em modelos mais fracos ou em respostas mais parafraseadas a taxa pode ser maior; vale auditar por modelo.

**Sugestão:**
1. Logar (ou retornar) o número de predições não-alinhadas por documento — hoje é zero observabilidade.
2. Considerar relaxar o limiar para `>= 70` ou usar `token_set_ratio` em vez de `partial_ratio` para tolerância a reordenação.
3. Tirar predições não-alinhadas do `total_pred` em vez de descartar (alternativamente contar como FP, registrando como erro do modelo).

**Drift adicional:** as duas cópias de `convert_pred_to_golden_format` divergem em uma linha (`range(0, len(text), step_size)` vs `range(0, max(1, len(text)-1), step_size)`). Não afeta resultados práticos, mas é dívida — extrair para função única.

---

## 🟡 MÉDIA — `alignment_mode="expand"` cria fronteiras inconsistentes entre métricas

**Onde:** `tools/ner_metrics.py:220, 227`.

**Problema:** Para construir BIO em nível de token (token F1), o pipeline expande a span ao token spaCy mais próximo:
```python
cs = doc.char_span(start, end, label=label, alignment_mode="expand")
```
Já o span F1 (IoU agregado) é calculado sobre os offsets **originais** char-level (`label_metrics` usa `gold_spans = [(a["start"], a["end"], ...)]`).

Resultado: token F1 e span F1 não usam as mesmas fronteiras dentro do mesmo modelo. Para spans que terminam no meio de um token spaCy, o token F1 incluirá silenciosamente o token completo.

**Impacto:** mais visível em entidades curtas (ex.: anotações que cortam dentro de "R\$ 10.000,00"). Para o corpus em questão a maior parte das entidades é grande (frases inteiras), então o efeito é pequeno. Mas existe.

**Sugestão:** documentar a escolha explicitamente na seção de metodologia, ou trocar para `alignment_mode="contract"` para uma semântica mais estrita (que pode descartar tokens parciais).

---

## 🟡 MÉDIA — Token F1 colapsa B-/I- e exclui tokens (O, O)

**Onde:** `tools/ner_metrics.py:232-262, 367-406`.

**Problema:** Antes do `precision_recall_fscore_support`, o pipeline faz duas modificações ao tag-stream:
1. `_strip_bio` colapsa `B-MULTA` e `I-MULTA` em `MULTA` (token F1 ignora distinção de fronteira).
2. `if t != "O" or p != "O": flat_true.append(t); flat_pred.append(p)` filtra pares `(O, O)`.

Isso é equivalente a F1 micro sobre rótulos não-O com tokens "verdadeiramente O" descartados — válido matematicamente, mas **não é** o que `seqeval` chama de token F1 (que mantém B-/I- e inclui ou não o O, conforme modo). É legítimo, mas precisa ser explicado.

**Impacto:** um modelo que erra fronteira (B vs I) mas acerta o tipo de entidade não é penalizado no token F1 — e isto, sim, fica acoberto se a metodologia disser apenas "token F1".

**Sugestão:** registrar na metodologia a definição exata: "F1 micro sobre os rótulos de tipo de entidade (Multa, Obrigação, Recomendação, Ressarcimento), agregado por token, com o prefixo BIO removido".

---

## 🟢 BAIXA — `extract_spans_from_bio` descarta `I-X` órfãos silenciosamente

**Onde:** `tools/ner_metrics.py:58-79`.

**Problema:**
```python
elif tag.startswith("I-") and start is not None and tag[2:] == label:
    continue
else:
    if start is not None:
        spans.append((start, j, label))
        start, label = None, None
```
Um `I-X` órfão (sem `B-X` precedente do mesmo tipo) cai no `else` e fecha qualquer span aberto, mas **não é incluído** como entidade. Isso difere do `seqeval mode="default"` (IOB1), que aceita `I-X` órfão como início de span.

**Impacto:** se o modelo supervisionado emite uma sequência `O O I-MULTA O`, esse `I-MULTA` é silenciosamente apagado. Para BERT/BiLSTM-CRF essa situação é rara (CRF garante consistência), mas LLMs traduzindo BIO podem emitir.

**Sugestão:** documentar e/ou alinhar com seqeval (uma flag `tolerate_orphan_i: bool = False`).

---

## 🟢 BAIXA — `evaluate_results` muta o DataFrame de entrada

**Onde:** `tools/ner_metrics.py:348`.

```python
df_results["pred_as_golden"] = df_results.apply(...)
```

Atribui coluna no DataFrame do chamador. Se o chamador reusa o mesmo `df` para múltiplas métricas com `pred_as_golden` recomputado, o estado fica grudado. Não afeta números reportados, mas é fonte de bugs em código exploratório.

**Sugestão:** `df_results = df_results.copy()` no início.

---

## 🟢 BAIXA — `compute_iou_score` zera quando rótulos diferem

**Onde:** `tools/ner_metrics.py:55`.

```python
return 1.0 if (iou >= threshold and label_a == label_b) else 0.0
```

A função conflate "sem sobreposição" com "sobreposição correta mas rótulo errado" — ambas retornam 0. Não é bug para F1 (correto: type-error é miss + falso positivo), mas qualquer análise que tente diferenciar "erro de fronteira" de "erro de tipo" precisa de outra função (já reimplementei isso em `chapter5_numbers.py:_classify_pair`).

**Sugestão:** manter assim para P/R/F1, mas exportar `compute_iou_raw(span_a, span_b) -> float` separado para análise de erros.

---

## 🟢 BAIXA — Bootstrap usa `seed=42` em todas as chamadas; checagem de paridade entre runs

**Onde:** `tools/release/bootstrap_significance.py:296-313, 316-348`.

`bootstrap_ci_f1` e `paired_bootstrap_diff` recebem o mesmo `seed=42` por padrão. Para o **paired bootstrap**, isso é o **comportamento correto**: todos os pares são reamostrados com os MESMOS índices de doc, garantindo pareamento. ✓

Para o **individual CI**, cada modelo usa o mesmo seed, então cada modelo é avaliado nos mesmos índices reamostrados — isso reduz variância entre modelos mas não introduz viés. ✓

**Não é bug.** Anotando para evitar reincidência da pergunta.

---

## ⚠️ Item adicional — `_per_entity_metrics_bio` em `chapter5_numbers.py` usa max-end como tamanho

**Onde:** `tools/release/chapter5_numbers.py:225-244`.

```python
ends = [s[1] for s in gold_spans] + [s[1] for s in pred_spans]
max_tok = max(ends) if ends else 0
true_bio = ["O"] * max_tok
```

Reconstrói BIO até a posição do último span. Tokens de "padding O" antes/depois do último span ficam de fora.

**Não afeta F1** porque a filtragem `(O, O)` remove esses pares de qualquer forma. Mas se alguém adicionar uma métrica que dependa da contagem total de tokens (ex.: accuracy), os números ficarão errados.

**Sugestão:** se for adicionar accuracy ou metric com `O` como classe positiva, usar o tamanho real da sequência BIO original (`len(rec["true_labels"][i])`), não `max(ends)`.

---

## Resumo executivo

| # | Gravidade | Item | Impacto nos números atuais |
|---|---|---|---|
| 1 | 🔴 ALTA | Token F1 entre LLM (spaCy) e supervisionado (`\S+`) usa tokenizadores diferentes | Comparações token-F1 LLM ↔ supervisionado **incomensuráveis** na Tabela 5.1 |
| 2 | 🔴 ALTA | Matching pred-gold assimétrico entre `calculate_metrics` e `compute_doc_level_counts` | < 1e-6 hoje, mas semantically inconsistent |
| 3 | 🟡 MED | Fuzzy alignment descarta predições silenciosamente | 0.36 % no GPT-4 Turbo; pode ser maior em modelos fracos |
| 4 | 🟡 MED | `alignment_mode="expand"` ↔ char offsets originais | Pequeno; varia por entidade curta |
| 5 | 🟡 MED | Token F1 = micro F1 com B-/I- colapsado e (O,O) filtrado | É escolha de design, mas precisa estar na metodologia |
| 6 | 🟢 BAIXA | `I-X` órfão silenciosamente descartado | Raro com supervisionado |
| 7 | 🟢 BAIXA | `evaluate_results` muta input df | Sem impacto numérico |
| 8 | 🟢 BAIXA | `compute_iou_score` mistura miss e wrong-label | Sem impacto em F1 |

**Recomendação prioritária para a tese:** corrigir #1 — passar todos os modelos pelo mesmo pipeline tokenizador (spaCy via `full_evaluation`/`bio_to_char_spans`) — ou retirar o token F1 da tabela principal e manter apenas span F1 com nota explicativa. Sem essa unificação, qualquer afirmação do tipo "supervisionados têm token F1 mais alto, mas LLMs têm span F1 mais alto" mistura dois efeitos: qualidade do modelo e diferença de tokenização.
