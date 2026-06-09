# Capítulo 5 — Números reproduzíveis (gold corrigido)

Documento auto-contido: todas as tabelas aparecem inline. Os CSVs ao lado deste arquivo são as fontes canônicas (uma por bloco), geradas por `research.release.chapter5_numbers`. Cada bloco abaixo corresponde a um item do checklist do capítulo.

## Pipeline de métricas (correções aplicadas)

Esta versão dos números incorpora as duas correções priorizadas no `METRICS_AUDIT.md`:

1. **Matching pred↔gold bipartido por IoU descendente** (`research.ner_metrics.bipartite_greedy_match`). Cada predição casa com no máximo um gold e vice-versa, eliminando a divergência anterior entre `calculate_metrics` (que tinha `break` após o primeiro match) e o bootstrap (que contava todos os pares sobrepostos). Esta única função é agora a fonte para `calculate_metrics`, `evaluate_bio_results` e `compute_doc_level_counts` — `matched ≤ min(|pred|, |gold|)` por construção, e P/R sempre em [0, 1].

2. **Token F1 de supervisionados via spaCy.** As predições BIO dos supervisionados (token-level `\S+`) são reconvertidas para spans caractere-level via `bio_to_char_spans`, depois pontuadas por `calculate_metrics` (que tokeniza com `pt_core_news_sm`). Resultado: supervisionados e LLMs compartilham o mesmo tokenizador de avaliação, tornando o token F1 da Tabela C diretamente comparável entre paradigmas.

### Comparativo antes × depois — Span F1 (14 modelos)

| model                |   span F1 antes |   span F1 depois |   Δ span F1 |
|:---------------------|----------------:|-----------------:|------------:|
| BERTimbau-base       |          0.6896 |           0.6786 |     -0.0110 |
| Legal-BERTimbau-base |          0.6051 |           0.6021 |     -0.0030 |
| BERTimbau-large      |          0.6049 |           0.6018 |     -0.0031 |
| BiLSTM-CRF           |          0.5926 |           0.5926 |     -0.0000 |

### Comparativo antes × depois — Token F1 supervisionados (efeito da unificação do tokenizador)

| model                |   token F1 antes (\S+) |   token F1 depois (spaCy) |   Δ token F1 |
|:---------------------|-----------------------:|--------------------------:|-------------:|
| BERTimbau-base       |                 0.7642 |                    0.7683 |       0.0041 |
| Legal-BERTimbau-base |                 0.6679 |                    0.6855 |       0.0176 |
| BERTimbau-large      |                 0.6514 |                    0.6820 |       0.0306 |
| BiLSTM-CRF           |                 0.7191 |                    0.7307 |       0.0116 |

### Comparativo antes × depois — Significância (bootstrap pareado)

| métrica                            |   antes |   depois |       Δ |
|:-----------------------------------|--------:|---------:|--------:|
| Pares significativos a 5% (de 91)  | 61.0000 |  56.0000 | -5.0000 |
| Menor Δ detectável (significativo) |  0.0337 |   0.0306 | -0.0031 |

### Comparativo antes × depois — FC vs JSON Schema (8 experimentos)



### Comparativo antes × depois — Técnicas de prompting (16 experimentos)



## A. Caracterização do corpus

| metric              |   before |   after |   delta |
|:--------------------|---------:|--------:|--------:|
| total_docs          |      861 |     861 |       0 |
| docs_with_entity    |      229 |     232 |       3 |
| docs_without_entity |      632 |     629 |      -3 |
| total_entities      |      439 |     459 |      20 |
| MULTA               |      202 |     212 |      10 |
| OBRIGACAO           |      119 |     131 |      12 |
| RECOMENDACAO        |       56 |      53 |      -3 |
| RESSARCIMENTO       |       62 |      63 |       1 |

## B. Auditoria Cleanlab

Dos **567** grupos com confiança ≥ 0,95 inspecionados (anotador único), apenas os marcados como `accept`/`custom` resultaram em alteração; os `reject` permaneceram no gold. As contagens de grupo abaixo respondem ao volume de intervenção (aceitos × rejeitados); as contagens de token são a granularidade fina dentro dos grupos decididos.

**Resumo das decisões (grupo) e contagens de tokens:**

| metric                         |     value |
|:-------------------------------|----------:|
| groups_total                   |  794.0000 |
| groups_decided_>=0.95          |  567.0000 |
| groups_below_threshold         |  227.0000 |
| groups_accept                  |    6.0000 |
| groups_custom                  |   17.0000 |
| groups_reject                  |  544.0000 |
| groups_altered (accept+custom) |   23.0000 |
| groups_acceptance_rate         |    0.0406 |
| groups_rejection_rate          |    0.9594 |
| token_changes                  | 4199.0000 |
| token_decision_accept          |  183.0000 |
| token_decision_reject          | 3238.0000 |
| token_decision_custom          |  778.0000 |

**Distribuição de `label_final` (rótulos para os quais os tokens foram migrados):**

| label_final     |   count |
|:----------------|--------:|
| B-MULTA         |      16 |
| B-OBRIGACAO     |      35 |
| B-RECOMENDACAO  |      21 |
| B-RESSARCIMENTO |      32 |
| I-MULTA         |     554 |
| I-OBRIGACAO     |    1130 |
| I-RECOMENDACAO  |     236 |
| I-RESSARCIMENTO |     334 |
| O               |    1841 |

**Saldo líquido por classe:**

| label         |   before |   after |   delta |
|:--------------|---------:|--------:|--------:|
| MULTA         |      202 |     212 |      10 |
| OBRIGACAO     |      119 |     131 |      12 |
| RECOMENDACAO  |       56 |      53 |      -3 |
| RESSARCIMENTO |       62 |      63 |       1 |

## C. Resultados gerais (14 modelos × 6 métricas)

| model                                              | display              |   token_f1 |   token_f1_macro |   token_precision |   token_recall |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:---------------------------------------------------|:---------------------|-----------:|-----------------:|------------------:|---------------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    |     0.7668 |           0.7268 |            0.8223 |         0.7183 |    0.7241 |          0.7007 |           0.7338 |        0.7146 |
| gpt-4.1_few_shot                                   | GPT-4.1              |     0.7999 |           0.7577 |            0.7898 |         0.8102 |    0.7151 |          0.6939 |           0.6512 |        0.7930 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         |     0.7841 |           0.7439 |            0.7713 |         0.7972 |    0.6983 |          0.6779 |           0.6185 |        0.8017 |
| gpt-5.1_few_shot                                   | GPT-5.1              |     0.7700 |           0.7365 |            0.7492 |         0.7919 |    0.6847 |          0.6745 |           0.6142 |        0.7734 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |     0.7683 |           0.6318 |            0.9506 |         0.6447 |    0.6786 |          0.5801 |           0.7994 |        0.5895 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          |     0.7023 |           0.6582 |            0.7121 |         0.6928 |    0.6135 |          0.5778 |           0.5491 |        0.6950 |
| gpt-5.2_few_shot                                   | GPT-5.2              |     0.7415 |           0.7024 |            0.6952 |         0.7945 |    0.6067 |          0.5852 |           0.5029 |        0.7647 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |     0.6855 |           0.4242 |            0.9474 |         0.5371 |    0.6021 |          0.4058 |           0.8223 |        0.4749 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |     0.6820 |           0.5103 |            0.9607 |         0.5287 |    0.6018 |          0.4778 |           0.8285 |        0.4726 |
| bilstm-crf__supervised                             | BiLSTM-CRF           |     0.7307 |           0.5638 |            0.8455 |         0.6434 |    0.5926 |          0.5004 |           0.7742 |        0.4800 |
| gpt-5-mini_few_shot                                | GPT-5-mini           |     0.5721 |           0.6215 |            0.4423 |         0.8097 |    0.4097 |          0.5242 |           0.2765 |        0.7908 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         |     0.5636 |           0.4765 |            0.6006 |         0.5309 |    0.4011 |          0.3651 |           0.3460 |        0.4771 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        |     0.4023 |           0.2789 |            0.7545 |         0.2743 |    0.3396 |          0.2734 |           0.5956 |        0.2375 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                              | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                     |
|:---------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:-------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                             | BiLSTM-CRF           |         0.5910 |        0.0518 |        0.5455 |        0.6761 | 0.5690; 0.6023; 0.5622; 0.6761; 0.5455 |          0.7191 |         0.0956 |         0.5531 |         0.7932 | 0.7400; 0.7716; 0.7376; 0.7932; 0.5531 | {"hidden_dim": 256, "dropout": 0.3, "lr": 0.003}                                           |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |         0.6753 |        0.0475 |        0.6071 |        0.7218 | 0.6984; 0.7035; 0.6456; 0.6071; 0.7218 |          0.7642 |         0.0475 |         0.7148 |         0.8261 | 0.7756; 0.8261; 0.7148; 0.7182; 0.7863 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1}  |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |         0.5712 |        0.1687 |        0.2857 |        0.7191 | 0.2857; 0.7191; 0.5652; 0.6387; 0.6475 |          0.6514 |         0.1939 |         0.3323 |         0.8035 | 0.3323; 0.8035; 0.6045; 0.7442; 0.7724 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 2e-05, "warmup_ratio": 0.1} |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |         0.5885 |        0.1394 |        0.3564 |        0.6984 | 0.3564; 0.6744; 0.5634; 0.6984; 0.6500 |          0.6679 |         0.1561 |         0.4115 |         0.8146 | 0.4115; 0.7469; 0.6413; 0.8146; 0.7252 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.1}          |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.6781 |                0.1357 |                0.4023 |                0.7999 |                0.5770 |               0.1519 |               0.3396 |               0.7241 |
| supervised         |                 0.7167 |                0.0410 |                0.6820 |                0.7683 |                0.6188 |               0.0401 |               0.5926 |               0.6786 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.7836 |      0.6737 |         0.3226 |          0.5405 |
| BERTimbau-large      |  0.7178 |      0.6452 |         0.2034 |          0.3448 |
| BiLSTM-CRF           |  0.6534 |      0.6887 |         0.2466 |          0.4130 |
| DeepSeek-V4-Flash    |  0.7737 |      0.7078 |         0.6212 |          0.7000 |
| GPT-4.1              |  0.7859 |      0.6503 |         0.5931 |          0.7463 |
| GPT-4.1-mini         |  0.7828 |      0.6115 |         0.5986 |          0.7188 |
| GPT-4.1-nano         |  0.6618 |      0.2251 |         0.0848 |          0.4885 |
| GPT-5-mini           |  0.6820 |      0.2231 |         0.5860 |          0.6056 |
| GPT-5.1              |  0.7600 |      0.5833 |         0.6383 |          0.7164 |
| GPT-5.2              |  0.7371 |      0.4742 |         0.5255 |          0.6040 |
| Legal-BERTimbau-base |  0.7548 |      0.6243 |         0.0727 |          0.1714 |
| Llama-3.3-70B        |  0.4014 |      0.3689 |         0.2927 |          0.0308 |
| Qwen2.5-72B          |  0.7528 |      0.5116 |         0.3704 |          0.6765 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                              | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:---------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4.1_few_shot                                   | GPT-4.1              | MULTA         |      0.7386 |   0.8396 | 0.7859 |       178 |          212 |          241 |
| gpt-4.1_few_shot                                   | GPT-4.1              | OBRIGACAO     |      0.6000 |   0.7099 | 0.6503 |        93 |          131 |          155 |
| gpt-4.1_few_shot                                   | GPT-4.1              | RECOMENDACAO  |      0.4674 |   0.8113 | 0.5931 |        43 |           53 |           92 |
| gpt-4.1_few_shot                                   | GPT-4.1              | RESSARCIMENTO |      0.7042 |   0.7937 | 0.7463 |        50 |           63 |           71 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         | MULTA         |      0.7194 |   0.8585 | 0.7828 |       182 |          212 |          253 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         | OBRIGACAO     |      0.5246 |   0.7328 | 0.6115 |        96 |          131 |          183 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         | RECOMENDACAO  |      0.4681 |   0.8302 | 0.5986 |        44 |           53 |           94 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         | RESSARCIMENTO |      0.7077 |   0.7302 | 0.7188 |        46 |           63 |           65 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         | MULTA         |      0.6782 |   0.6462 | 0.6618 |       137 |          212 |          202 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         | OBRIGACAO     |      0.1713 |   0.3282 | 0.2251 |        43 |          131 |          251 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         | RECOMENDACAO  |      0.0625 |   0.1321 | 0.0848 |         7 |           53 |          112 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         | RESSARCIMENTO |      0.4706 |   0.5079 | 0.4885 |        32 |           63 |           68 |
| gpt-5-mini_few_shot                                | GPT-5-mini           | MULTA         |      0.6128 |   0.7689 | 0.6820 |       163 |          212 |          266 |
| gpt-5-mini_few_shot                                | GPT-5-mini           | OBRIGACAO     |      0.1285 |   0.8473 | 0.2231 |       111 |          131 |          864 |
| gpt-5-mini_few_shot                                | GPT-5-mini           | RECOMENDACAO  |      0.4423 |   0.8679 | 0.5860 |        46 |           53 |          104 |
| gpt-5-mini_few_shot                                | GPT-5-mini           | RESSARCIMENTO |      0.5443 |   0.6825 | 0.6056 |        43 |           63 |           79 |
| gpt-5.1_few_shot                                   | GPT-5.1              | MULTA         |      0.7185 |   0.8066 | 0.7600 |       171 |          212 |          238 |
| gpt-5.1_few_shot                                   | GPT-5.1              | OBRIGACAO     |      0.5028 |   0.6947 | 0.5833 |        91 |          131 |          181 |
| gpt-5.1_few_shot                                   | GPT-5.1              | RECOMENDACAO  |      0.5114 |   0.8491 | 0.6383 |        45 |           53 |           88 |
| gpt-5.1_few_shot                                   | GPT-5.1              | RESSARCIMENTO |      0.6761 |   0.7619 | 0.7164 |        48 |           63 |           71 |
| gpt-5.2_few_shot                                   | GPT-5.2              | MULTA         |      0.6568 |   0.8396 | 0.7371 |       178 |          212 |          271 |
| gpt-5.2_few_shot                                   | GPT-5.2              | OBRIGACAO     |      0.3580 |   0.7023 | 0.4742 |        92 |          131 |          257 |
| gpt-5.2_few_shot                                   | GPT-5.2              | RECOMENDACAO  |      0.4286 |   0.6792 | 0.5255 |        36 |           53 |           84 |
| gpt-5.2_few_shot                                   | GPT-5.2              | RESSARCIMENTO |      0.5233 |   0.7143 | 0.6040 |        45 |           63 |           86 |
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    | MULTA         |      0.7990 |   0.7500 | 0.7737 |       159 |          212 |          199 |
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    | OBRIGACAO     |      0.7679 |   0.6565 | 0.7078 |        86 |          131 |          112 |
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    | RECOMENDACAO  |      0.5190 |   0.7736 | 0.6212 |        41 |           53 |           79 |
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    | RESSARCIMENTO |      0.7368 |   0.6667 | 0.7000 |        42 |           63 |           57 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        | MULTA         |      0.7532 |   0.2736 | 0.4014 |        58 |          212 |           77 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        | OBRIGACAO     |      0.5067 |   0.2901 | 0.3689 |        38 |          131 |           75 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        | RECOMENDACAO  |      0.4138 |   0.2264 | 0.2927 |        12 |           53 |           29 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        | RESSARCIMENTO |      0.5000 |   0.0159 | 0.0308 |         1 |           63 |            2 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          | MULTA         |      0.7249 |   0.7830 | 0.7528 |       166 |          212 |          229 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          | OBRIGACAO     |      0.4529 |   0.5878 | 0.5116 |        77 |          131 |          170 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          | RECOMENDACAO  |      0.2752 |   0.5660 | 0.3704 |        30 |           53 |          109 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          | RESSARCIMENTO |      0.6301 |   0.7302 | 0.6765 |        46 |           63 |           73 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | MULTA         |      0.7965 |   0.7173 | 0.7548 |       137 |          191 |          172 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | OBRIGACAO     |      0.9818 |   0.4576 | 0.6243 |        54 |          118 |           55 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | RECOMENDACAO  |      0.2857 |   0.0417 | 0.0727 |         2 |           48 |            7 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | RESSARCIMENTO |      0.7500 |   0.0968 | 0.1714 |         6 |           62 |            8 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | MULTA         |      0.8218 |   0.7487 | 0.7836 |       143 |          191 |          174 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | OBRIGACAO     |      0.8889 |   0.5424 | 0.6737 |        64 |          118 |           72 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | RECOMENDACAO  |      0.7143 |   0.2083 | 0.3226 |        10 |           48 |           14 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | RESSARCIMENTO |      0.6122 |   0.4839 | 0.5405 |        30 |           62 |           49 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | MULTA         |      0.8667 |   0.6126 | 0.7178 |       117 |          191 |          135 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | OBRIGACAO     |      0.8824 |   0.5085 | 0.6452 |        60 |          118 |           68 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | RECOMENDACAO  |      0.5455 |   0.1250 | 0.2034 |         6 |           48 |           11 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | RESSARCIMENTO |      0.6000 |   0.2419 | 0.3448 |        15 |           62 |           25 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | MULTA         |      0.7986 |   0.5529 | 0.6534 |       115 |          208 |          144 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | OBRIGACAO     |      0.8488 |   0.5794 | 0.6887 |        73 |          126 |           86 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | RECOMENDACAO  |      0.4500 |   0.1698 | 0.2466 |         9 |           53 |           20 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | RESSARCIMENTO |      0.6552 |   0.3016 | 0.4130 |        19 |           63 |           29 |

## E. Custo-benefício

Os JSONs de predição não armazenam contagens de tokens da API; o template abaixo reporta caracteres médios e estimativa aproximada de tokens (≈ 4 chars/token), com colunas em branco para as tarifas USD/1M de cada provedor — preencher manualmente consultando o histórico de billing.

| model                      | display           |   n_docs |   mean_input_chars |   mean_output_chars |   approx_mean_input_tokens |   approx_mean_output_tokens |   total_input_chars |   total_output_chars |   input_cost_per_1M_USD |   output_cost_per_1M_USD |   estimated_total_cost_USD |
|:---------------------------|:------------------|---------:|-------------------:|--------------------:|---------------------------:|----------------------------:|--------------------:|---------------------:|------------------------:|-------------------------:|---------------------------:|
| gpt-4.1_few_shot           | GPT-4.1           |      861 |           875.6760 |            295.2602 |                   218.9190 |                     73.8150 |              753957 |               254219 |                     nan |                      nan |                        nan |
| gpt-4.1-mini_few_shot      | GPT-4.1-mini      |      861 |           875.6760 |            296.7085 |                   218.9190 |                     74.1771 |              753957 |               255466 |                     nan |                      nan |                        nan |
| gpt-4.1-nano_few_shot      | GPT-4.1-nano      |      861 |           875.6760 |            293.5470 |                   218.9190 |                     73.3868 |              753957 |               252744 |                     nan |                      nan |                        nan |
| gpt-5-mini_few_shot        | GPT-5-mini        |      861 |           875.6760 |            509.2195 |                   218.9190 |                    127.3049 |              753957 |               438438 |                     nan |                      nan |                        nan |
| gpt-5.1_few_shot           | GPT-5.1           |      861 |           875.6760 |            296.4111 |                   218.9190 |                     74.1028 |              753957 |               255210 |                     nan |                      nan |                        nan |
| gpt-5.2_few_shot           | GPT-5.2           |      861 |           875.6760 |            326.8026 |                   218.9190 |                     81.7006 |              753957 |               281377 |                     nan |                      nan |                        nan |
| deepseek-v4-flash_few_shot | DeepSeek-V4-Flash |      861 |           875.6760 |            303.4506 |                   218.9190 |                     75.8627 |              753957 |               261271 |                     nan |                      nan |                        nan |
| llama-3.3-70b_few_shot     | Llama-3.3-70B     |      861 |           875.6760 |            150.4925 |                   218.9190 |                     37.6231 |              753957 |               129574 |                     nan |                      nan |                        nan |
| qwen2.5-72b_few_shot       | Qwen2.5-72B       |      861 |           875.6760 |            296.9373 |                   218.9190 |                     74.2343 |              753957 |               255663 |                     nan |                      nan |                        nan |

## F. Function calling vs JSON schema

**Métricas overall:**

| model             | method           |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | function_calling |     0.7793 |    0.7231 |          0.6898 |           0.7208 |        0.7255 |
| deepseek-v4-flash | json_schema      |     0.7841 |    0.6926 |          0.6683 |           0.6538 |        0.7364 |
| gpt-4.1           | function_calling |     0.7737 |    0.6742 |          0.6531 |           0.5963 |        0.7756 |
| gpt-4.1           | json_schema      |     0.7804 |    0.6885 |          0.6539 |           0.6321 |        0.7560 |

**Δ por modelo (FC − JS):**

| model             |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:------------------|-----------------:|----------------:|-----------------------:|--------------------:|
| deepseek-v4-flash |          -0.0048 |          0.0305 |                 0.0670 |             -0.0109 |
| gpt-4.1           |          -0.0067 |         -0.0142 |                -0.0357 |              0.0196 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8010 |      0.6770 |         0.5600 |          0.7213 |
| deepseek-v4-flash | json_schema      |  0.7742 |      0.6121 |         0.6202 |          0.6667 |
| gpt-4.1           | function_calling |  0.7586 |      0.5986 |         0.5333 |          0.7218 |
| gpt-4.1           | json_schema      |  0.7868 |      0.6081 |         0.5442 |          0.6767 |

**Span Precision (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8146 |      0.6905 |         0.4861 |          0.7458 |
| deepseek-v4-flash | json_schema      |  0.7568 |      0.5733 |         0.5263 |          0.6377 |
| gpt-4.1           | function_calling |  0.6984 |      0.5399 |         0.3929 |          0.6857 |
| gpt-4.1           | json_schema      |  0.7366 |      0.5845 |         0.4255 |          0.6429 |

**Span Recall (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.7877 |      0.6641 |         0.6604 |          0.6984 |
| deepseek-v4-flash | json_schema      |  0.7925 |      0.6565 |         0.7547 |          0.6984 |
| gpt-4.1           | function_calling |  0.8302 |      0.6718 |         0.8302 |          0.7619 |
| gpt-4.1           | json_schema      |  0.8443 |      0.6336 |         0.7547 |          0.7143 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model             | technique   |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | cot         |     0.7718 |    0.6905 |          0.6600 |           0.6500 |        0.7364 |
| deepseek-v4-flash | few_shot    |     0.7668 |    0.7241 |          0.7007 |           0.7338 |        0.7146 |
| deepseek-v4-flash | two_stage   |     0.7881 |    0.6732 |          0.6270 |           0.6688 |        0.6776 |
| gpt-4.1           | cot         |     0.7866 |    0.6919 |          0.6869 |           0.6110 |        0.7974 |
| gpt-4.1           | few_shot    |     0.7999 |    0.7151 |          0.6939 |           0.6512 |        0.7930 |
| gpt-4.1           | two_stage   |     0.7873 |    0.6922 |          0.6675 |           0.6182 |        0.7865 |
| gpt-5.2           | cot         |     0.7846 |    0.6762 |          0.6938 |           0.5725 |        0.8257 |
| gpt-5.2           | few_shot    |     0.7415 |    0.6067 |          0.5852 |           0.5029 |        0.7647 |
| gpt-5.2           | two_stage   |     0.7731 |    0.6574 |          0.6279 |           0.5705 |        0.7756 |
| llama-3.3-70b     | cot         |     0.3050 |    0.2526 |          0.1902 |           0.6134 |        0.1590 |
| llama-3.3-70b     | few_shot    |     0.4023 |    0.3396 |          0.2734 |           0.5956 |        0.2375 |
| llama-3.3-70b     | two_stage   |     0.1545 |    0.1231 |          0.1094 |           0.5246 |        0.0697 |
| qwen2.5-72b       | cot         |     0.7362 |    0.6346 |          0.5909 |           0.5600 |        0.7320 |
| qwen2.5-72b       | few_shot    |     0.7023 |    0.6135 |          0.5778 |           0.5491 |        0.6950 |
| qwen2.5-72b       | two_stage   |     0.7225 |    0.6261 |          0.5778 |           0.5696 |        0.6950 |

**Span F1 pivotado (modelo × técnica):**

| model             |    cot |   few_shot |   two_stage |
|:------------------|-------:|-----------:|------------:|
| deepseek-v4-flash | 0.6905 |     0.7241 |      0.6732 |
| gpt-4.1           | 0.6919 |     0.7151 |      0.6922 |
| gpt-5.2           | 0.6762 |     0.6067 |      0.6574 |
| llama-3.3-70b     | 0.2526 |     0.3396 |      0.1231 |
| qwen2.5-72b       | 0.6346 |     0.6135 |      0.6261 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique   | token_f1           | token_f1.1          | token_f1.2          | token_f1.3         | span_f1            | span_f1.1           | span_f1.2           | span_f1.3          |
|:------------|:-------------------|:--------------------|:--------------------|:-------------------|:-------------------|:--------------------|:--------------------|:-------------------|
| nan         | mean               | std                 | min                 | max                | mean               | std                 | min                 | max                |
| cot         | 0.6768375277466712 | 0.208851163708848   | 0.30499119510079636 | 0.7866466664538985 | 0.5891420017802755 | 0.18955836989842076 | 0.25259515570934254 | 0.6918714555765596 |
| few_shot    | 0.6825672875819438 | 0.16068533712541852 | 0.402299676607977   | 0.7998903597168701 | 0.5997912971906733 | 0.1554824313998018  | 0.3395638629283489  | 0.7240618101545254 |
| two_stage   | 0.6451104047601652 | 0.27555885289162035 | 0.15450922509225093 | 0.7880774140131783 | 0.554401623334142  | 0.24233192539405599 | 0.12307692307692308 | 0.6922339405560882 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.7778 |      0.6298 |         0.5775 |          0.6552 |
| deepseek-v4-flash | few_shot    |  0.7737 |      0.7078 |         0.6212 |          0.7000 |
| deepseek-v4-flash | two_stage   |  0.7767 |      0.6241 |         0.5120 |          0.5950 |
| gpt-4.1           | cot         |  0.7876 |      0.5505 |         0.6483 |          0.7612 |
| gpt-4.1           | few_shot    |  0.7859 |      0.6503 |         0.5931 |          0.7463 |
| gpt-4.1           | two_stage   |  0.7904 |      0.5986 |         0.5443 |          0.7368 |
| gpt-5.2           | cot         |  0.7800 |      0.5127 |         0.6857 |          0.7969 |
| gpt-5.2           | few_shot    |  0.7371 |      0.4742 |         0.5255 |          0.6040 |
| gpt-5.2           | two_stage   |  0.7739 |      0.5565 |         0.5000 |          0.6812 |
| llama-3.3-70b     | cot         |  0.3256 |      0.2732 |         0.1622 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.4014 |      0.3689 |         0.2927 |          0.0308 |
| llama-3.3-70b     | two_stage   |  0.1339 |      0.1419 |         0.1311 |          0.0308 |
| qwen2.5-72b       | cot         |  0.7812 |      0.5502 |         0.3558 |          0.6763 |
| qwen2.5-72b       | few_shot    |  0.7528 |      0.5116 |         0.3704 |          0.6765 |
| qwen2.5-72b       | two_stage   |  0.7717 |      0.5320 |         0.3946 |          0.6131 |

**Span Precision por entidade (mesmo eixo):**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.7636 |      0.5759 |         0.4607 |          0.7170 |
| deepseek-v4-flash | few_shot    |  0.7990 |      0.7679 |         0.5190 |          0.7368 |
| deepseek-v4-flash | two_stage   |  0.8000 |      0.6148 |         0.4444 |          0.6207 |
| gpt-4.1           | cot         |  0.7417 |      0.4592 |         0.5109 |          0.7183 |
| gpt-4.1           | few_shot    |  0.7386 |      0.6000 |         0.4674 |          0.7042 |
| gpt-4.1           | two_stage   |  0.7358 |      0.5399 |         0.4095 |          0.7000 |
| gpt-5.2           | cot         |  0.7247 |      0.3840 |         0.5517 |          0.7846 |
| gpt-5.2           | few_shot    |  0.6568 |      0.3580 |         0.4286 |          0.5233 |
| gpt-5.2           | two_stage   |  0.7177 |      0.4486 |         0.4023 |          0.6267 |
| llama-3.3-70b     | cot         |  0.9130 |      0.4808 |         0.2857 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.7532 |      0.5067 |         0.4138 |          0.5000 |
| llama-3.3-70b     | two_stage   |  0.5926 |      0.4583 |         0.5000 |          0.5000 |
| qwen2.5-72b       | cot         |  0.7415 |      0.4775 |         0.2636 |          0.6184 |
| qwen2.5-72b       | few_shot    |  0.7249 |      0.4529 |         0.2752 |          0.6301 |
| qwen2.5-72b       | two_stage   |  0.7478 |      0.4759 |         0.3085 |          0.5676 |

**Span Recall por entidade:**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.7925 |      0.6947 |         0.7736 |          0.6032 |
| deepseek-v4-flash | few_shot    |  0.7500 |      0.6565 |         0.7736 |          0.6667 |
| deepseek-v4-flash | two_stage   |  0.7547 |      0.6336 |         0.6038 |          0.5714 |
| gpt-4.1           | cot         |  0.8396 |      0.6870 |         0.8868 |          0.8095 |
| gpt-4.1           | few_shot    |  0.8396 |      0.7099 |         0.8113 |          0.7937 |
| gpt-4.1           | two_stage   |  0.8538 |      0.6718 |         0.8113 |          0.7778 |
| gpt-5.2           | cot         |  0.8443 |      0.7710 |         0.9057 |          0.8095 |
| gpt-5.2           | few_shot    |  0.8396 |      0.7023 |         0.6792 |          0.7143 |
| gpt-5.2           | two_stage   |  0.8396 |      0.7328 |         0.6604 |          0.7460 |
| llama-3.3-70b     | cot         |  0.1981 |      0.1908 |         0.1132 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.2736 |      0.2901 |         0.2264 |          0.0159 |
| llama-3.3-70b     | two_stage   |  0.0755 |      0.0840 |         0.0755 |          0.0159 |
| qwen2.5-72b       | cot         |  0.8255 |      0.6489 |         0.5472 |          0.7460 |
| qwen2.5-72b       | few_shot    |  0.7830 |      0.5878 |         0.5660 |          0.7302 |
| qwen2.5-72b       | two_stage   |  0.7972 |      0.6031 |         0.5472 |          0.6667 |

## I. Análise de erros do melhor modelo

**Melhor modelo identificado por span F1: DeepSeek-V4-Flash.**

**Contagens por tipo de erro:**

| kind       |   count |
|:-----------|--------:|
| exact      |     338 |
| FN         |     103 |
| FP         |      61 |
| boundary   |      44 |
| type_error |       4 |

**Matriz rótulo × tipo de erro:**

| label         |   FN |   FP |   boundary |   exact |   type_error |
|:--------------|-----:|-----:|-----------:|--------:|-------------:|
| MULTA         |   43 |    5 |         14 |     167 |            2 |
| OBRIGACAO     |   41 |   20 |          7 |      86 |            0 |
| RECOMENDACAO  |   10 |   33 |          2 |      43 |            0 |
| RESSARCIMENTO |    9 |    3 |         21 |      42 |            2 |

**Pares de tipo errado (gold → pred):**

| label         | pred_label    |   count |
|:--------------|:--------------|--------:|
| MULTA         | OBRIGACAO     |       1 |
| MULTA         | RESSARCIMENTO |       1 |
| RESSARCIMENTO | MULTA         |       2 |

**Histograma de IoU para erros de fronteira:**

|   bin_low |   bin_high |   count |
|----------:|-----------:|--------:|
|    0.0000 |     0.2000 |  7.0000 |
|    0.2000 |     0.4000 | 25.0000 |
|    0.4000 |     0.5000 | 12.0000 |
|    0.5000 |     0.7000 |  0.0000 |
|    0.7000 |     0.9000 |  0.0000 |
|    0.9000 |     1.0000 |  0.0000 |

## J. Significância estatística (bootstrap pareado)

**Item 41 — N de reamostragens**: 10.000.

**Item 42 — IC 95% por modelo:**

| model                                              | display              |   span_f1_point |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:---------------------------------------------------|:---------------------|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    |          0.7241 |         0.7245 |        0.0261 |     0.6724 |     0.7743 |     0.1019 |
| gpt-4.1_few_shot                                   | GPT-4.1              |          0.7151 |         0.7153 |        0.0222 |     0.6712 |     0.7583 |     0.0871 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         |          0.6983 |         0.6984 |        0.0215 |     0.6556 |     0.7406 |     0.0850 |
| gpt-5.1_few_shot                                   | GPT-5.1              |          0.6847 |         0.6847 |        0.0222 |     0.6405 |     0.7276 |     0.0871 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |          0.6786 |         0.6783 |        0.0273 |     0.6243 |     0.7300 |     0.1057 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          |          0.6135 |         0.6137 |        0.0217 |     0.5703 |     0.6561 |     0.0858 |
| gpt-5.2_few_shot                                   | GPT-5.2              |          0.6067 |         0.6068 |        0.0215 |     0.5635 |     0.6478 |     0.0843 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |          0.6021 |         0.6016 |        0.0303 |     0.5410 |     0.6593 |     0.1183 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |          0.6018 |         0.6012 |        0.0314 |     0.5383 |     0.6616 |     0.1232 |
| bilstm-crf__supervised                             | BiLSTM-CRF           |          0.5926 |         0.5925 |        0.0329 |     0.5269 |     0.6569 |     0.1300 |
| gpt-5-mini_few_shot                                | GPT-5-mini           |          0.4097 |         0.4094 |        0.0176 |     0.3746 |     0.4431 |     0.0685 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         |          0.4011 |         0.4012 |        0.0230 |     0.3559 |     0.4466 |     0.0907 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        |          0.3396 |         0.3397 |        0.0325 |     0.2764 |     0.4045 |     0.1281 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                           | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:--------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                        | llama-3.3-70b_few_shot                            | DeepSeek-V4-Flash | Llama-3.3-70B     | 0.7241 | 0.3396 |    0.3847 |     0.3171 |     0.4524 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-4.1-mini_few_shot                             | gpt-4.1-nano_few_shot                             | GPT-4.1-mini      | GPT-4.1-nano      | 0.6983 | 0.4011 |    0.2972 |     0.2510 |     0.3434 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| llama-3.3-70b_few_shot                            | qwen2.5-72b_few_shot                              | Llama-3.3-70B     | Qwen2.5-72B       | 0.3396 | 0.6135 |   -0.2740 |    -0.3410 |    -0.2053 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-5.2_few_shot                                  | llama-3.3-70b_few_shot                            | GPT-5.2           | Llama-3.3-70B     | 0.6067 | 0.3396 |    0.2671 |     0.1969 |     0.3361 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-5.2_few_shot                                  | deepseek-v4-flash_few_shot                        | GPT-5.2           | DeepSeek-V4-Flash | 0.6067 | 0.7241 |   -0.1177 |    -0.1681 |    -0.0656 |    0.0004 | True             |   0.0024 |         0.0048 | True            | True                  |            12 |
| gpt-4.1_few_shot                                  | gpt-5.2_few_shot                                  | GPT-4.1           | GPT-5.2           | 0.7151 | 0.6067 |    0.1085 |     0.0767 |     0.1421 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                            | BERTimbau-base    | BiLSTM-CRF        | 0.6786 | 0.5926 |    0.0857 |     0.0304 |     0.1438 |    0.0020 | True             |   0.0100 |         0.0240 | True            | True                  |            12 |
| gpt-5.1_few_shot                                  | gpt-5.2_few_shot                                  | GPT-5.1           | GPT-5.2           | 0.6847 | 0.6067 |    0.0779 |     0.0460 |     0.1104 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-5.2_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised | GPT-5.2           | BERTimbau-base    | 0.6067 | 0.6786 |   -0.0715 |    -0.1174 |    -0.0240 |    0.0036 | True             |   0.0144 |         0.0432 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                        | neuralmind_bert-base-portuguese-cased__supervised | DeepSeek-V4-Flash | BERTimbau-base    | 0.7241 | 0.6786 |    0.0462 |    -0.0133 |     0.1035 |    0.1264 | False            |   0.3792 |         1.0000 | False           | False                 |            12 |
| gpt-4.1_few_shot                                  | gpt-4.1-mini_few_shot                             | GPT-4.1           | GPT-4.1-mini      | 0.7151 | 0.6983 |    0.0169 |    -0.0066 |     0.0405 |    0.1626 | False            |   0.3792 |         1.0000 | False           | False                 |            12 |
| gpt-5.2_few_shot                                  | qwen2.5-72b_few_shot                              | GPT-5.2           | Qwen2.5-72B       | 0.6067 | 0.6135 |   -0.0069 |    -0.0478 |     0.0341 |    0.7308 | False            |   0.7308 |         1.0000 | False           | False                 |            12 |

**Itens 47–48 — Resumo:**

| metric                         | value                |
|:-------------------------------|:---------------------|
| resampling_unit                | document             |
| n_docs_resampled               | 861                  |
| n_total_pairs                  | 78                   |
| n_significant_5pct_uncorrected | 56                   |
| highlighted_family_size        | 12                   |
| highlighted_n_sig_uncorrected  | 9                    |
| highlighted_n_sig_holm         | 9                    |
| highlighted_n_sig_bonferroni   | 9                    |
| smallest_significant_abs_diff  | 0.030599881277950196 |
| smallest_significant_pair      | GPT-4.1 vs GPT-5.1   |

**p48a — Correção para múltiplas comparações.** A família reportada são os pares destacados acima; `p_holm`/`p_bonferroni` controlam o erro familiar (FWER) e `sig_holm_5pct` substitui a coluna 'Sig.' não corrigida da Tabela 13. Diferenças marginais tendem a não sobreviver, reforçando a leitura de saturação.

**Tabela completa dos 91 pares (ordenada por |Δ|):**

| model_a                                            | model_b                                            | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:---------------------------------------------------|:---------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| deepseek-v4-flash_few_shot                         | llama-3.3-70b_few_shot                             | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7241 | 0.3396 |    0.3847 |     0.3171 |     0.4524 |    0.0000 | True             |
| gpt-4.1_few_shot                                   | llama-3.3-70b_few_shot                             | GPT-4.1              | Llama-3.3-70B        | 0.7151 | 0.3396 |    0.3756 |     0.3097 |     0.4408 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                              | llama-3.3-70b_few_shot                             | GPT-4.1-mini         | Llama-3.3-70B        | 0.6983 | 0.3396 |    0.3587 |     0.2918 |     0.4244 |    0.0000 | True             |
| gpt-5.1_few_shot                                   | llama-3.3-70b_few_shot                             | GPT-5.1              | Llama-3.3-70B        | 0.6847 | 0.3396 |    0.3450 |     0.2772 |     0.4101 |    0.0000 | True             |
| llama-3.3-70b_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised  | Llama-3.3-70B        | BERTimbau-base       | 0.3396 | 0.6786 |   -0.3385 |    -0.4049 |    -0.2706 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | deepseek-v4-flash_few_shot                         | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.4011 | 0.7241 |   -0.3233 |    -0.3743 |    -0.2729 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | deepseek-v4-flash_few_shot                         | GPT-5-mini           | DeepSeek-V4-Flash    | 0.4097 | 0.7241 |   -0.3150 |    -0.3667 |    -0.2651 |    0.0000 | True             |
| gpt-4.1_few_shot                                   | gpt-4.1-nano_few_shot                              | GPT-4.1              | GPT-4.1-nano         | 0.7151 | 0.4011 |    0.3141 |     0.2657 |     0.3628 |    0.0000 | True             |
| gpt-4.1_few_shot                                   | gpt-5-mini_few_shot                                | GPT-4.1              | GPT-5-mini           | 0.7151 | 0.4097 |    0.3059 |     0.2631 |     0.3486 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                              | gpt-4.1-nano_few_shot                              | GPT-4.1-mini         | GPT-4.1-nano         | 0.6983 | 0.4011 |    0.2972 |     0.2510 |     0.3434 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                              | gpt-5-mini_few_shot                                | GPT-4.1-mini         | GPT-5-mini           | 0.6983 | 0.4097 |    0.2890 |     0.2497 |     0.3293 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | gpt-5.1_few_shot                                   | GPT-4.1-nano         | GPT-5.1              | 0.4011 | 0.6847 |   -0.2835 |    -0.3334 |    -0.2326 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | neuralmind_bert-base-portuguese-cased__supervised  | GPT-4.1-nano         | BERTimbau-base       | 0.4011 | 0.6786 |   -0.2771 |    -0.3276 |    -0.2262 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | gpt-5.1_few_shot                                   | GPT-5-mini           | GPT-5.1              | 0.4097 | 0.6847 |   -0.2753 |    -0.3180 |    -0.2337 |    0.0000 | True             |
| llama-3.3-70b_few_shot                             | qwen2.5-72b_few_shot                               | Llama-3.3-70B        | Qwen2.5-72B          | 0.3396 | 0.6135 |   -0.2740 |    -0.3410 |    -0.2053 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | neuralmind_bert-base-portuguese-cased__supervised  | GPT-5-mini           | BERTimbau-base       | 0.4097 | 0.6786 |   -0.2688 |    -0.3261 |    -0.2122 |    0.0000 | True             |
| gpt-5.2_few_shot                                   | llama-3.3-70b_few_shot                             | GPT-5.2              | Llama-3.3-70B        | 0.6067 | 0.3396 |    0.2671 |     0.1969 |     0.3361 |    0.0000 | True             |
| llama-3.3-70b_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised          | Llama-3.3-70B        | Legal-BERTimbau-base | 0.3396 | 0.6021 |   -0.2619 |    -0.3289 |    -0.1944 |    0.0000 | True             |
| llama-3.3-70b_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbau-large      | 0.3396 | 0.6018 |   -0.2615 |    -0.3298 |    -0.1916 |    0.0000 | True             |
| llama-3.3-70b_few_shot                             | bilstm-crf__supervised                             | Llama-3.3-70B        | BiLSTM-CRF           | 0.3396 | 0.5926 |   -0.2528 |    -0.3200 |    -0.1843 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | qwen2.5-72b_few_shot                               | GPT-4.1-nano         | Qwen2.5-72B          | 0.4011 | 0.6135 |   -0.2125 |    -0.2557 |    -0.1693 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | gpt-5.2_few_shot                                   | GPT-4.1-nano         | GPT-5.2              | 0.4011 | 0.6067 |   -0.2056 |    -0.2537 |    -0.1585 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | qwen2.5-72b_few_shot                               | GPT-5-mini           | Qwen2.5-72B          | 0.4097 | 0.6135 |   -0.2043 |    -0.2483 |    -0.1596 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | rufimelo_Legal-BERTimbau-base__supervised          | GPT-4.1-nano         | Legal-BERTimbau-base | 0.4011 | 0.6021 |   -0.2004 |    -0.2547 |    -0.1461 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | neuralmind_bert-large-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbau-large      | 0.4011 | 0.6018 |   -0.2001 |    -0.2589 |    -0.1407 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | gpt-5.2_few_shot                                   | GPT-5-mini           | GPT-5.2              | 0.4097 | 0.6067 |   -0.1974 |    -0.2365 |    -0.1587 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | rufimelo_Legal-BERTimbau-base__supervised          | GPT-5-mini           | Legal-BERTimbau-base | 0.4097 | 0.6021 |   -0.1922 |    -0.2519 |    -0.1315 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | neuralmind_bert-large-portuguese-cased__supervised | GPT-5-mini           | BERTimbau-large      | 0.4097 | 0.6018 |   -0.1918 |    -0.2553 |    -0.1275 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                              | bilstm-crf__supervised                             | GPT-4.1-nano         | BiLSTM-CRF           | 0.4011 | 0.5926 |   -0.1914 |    -0.2585 |    -0.1234 |    0.0000 | True             |
| gpt-5-mini_few_shot                                | bilstm-crf__supervised                             | GPT-5-mini           | BiLSTM-CRF           | 0.4097 | 0.5926 |   -0.1831 |    -0.2533 |    -0.1140 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                         | bilstm-crf__supervised                             | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7241 | 0.5926 |    0.1319 |     0.0596 |     0.2037 |    0.0010 | True             |
| deepseek-v4-flash_few_shot                         | neuralmind_bert-large-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7241 | 0.6018 |    0.1232 |     0.0575 |     0.1895 |    0.0002 | True             |
| deepseek-v4-flash_few_shot                         | rufimelo_Legal-BERTimbau-base__supervised          | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7241 | 0.6021 |    0.1228 |     0.0620 |     0.1849 |    0.0002 | True             |
| gpt-4.1_few_shot                                   | bilstm-crf__supervised                             | GPT-4.1              | BiLSTM-CRF           | 0.7151 | 0.5926 |    0.1228 |     0.0601 |     0.1858 |    0.0000 | True             |
| gpt-5.2_few_shot                                   | deepseek-v4-flash_few_shot                         | GPT-5.2              | DeepSeek-V4-Flash    | 0.6067 | 0.7241 |   -0.1177 |    -0.1681 |    -0.0656 |    0.0004 | True             |
| gpt-4.1_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised | GPT-4.1              | BERTimbau-large      | 0.7151 | 0.6018 |    0.1141 |     0.0585 |     0.1724 |    0.0000 | True             |
| gpt-4.1_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised          | GPT-4.1              | Legal-BERTimbau-base | 0.7151 | 0.6021 |    0.1137 |     0.0585 |     0.1705 |    0.0002 | True             |
| deepseek-v4-flash_few_shot                         | qwen2.5-72b_few_shot                               | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7241 | 0.6135 |    0.1107 |     0.0625 |     0.1583 |    0.0000 | True             |
| gpt-4.1_few_shot                                   | gpt-5.2_few_shot                                   | GPT-4.1              | GPT-5.2              | 0.7151 | 0.6067 |    0.1085 |     0.0767 |     0.1421 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                              | bilstm-crf__supervised                             | GPT-4.1-mini         | BiLSTM-CRF           | 0.6983 | 0.5926 |    0.1059 |     0.0445 |     0.1669 |    0.0006 | True             |
| gpt-4.1_few_shot                                   | qwen2.5-72b_few_shot                               | GPT-4.1              | Qwen2.5-72B          | 0.7151 | 0.6135 |    0.1016 |     0.0579 |     0.1442 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                              | neuralmind_bert-large-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbau-large      | 0.6983 | 0.6018 |    0.0972 |     0.0438 |     0.1523 |    0.0004 | True             |
| gpt-4.1-mini_few_shot                              | rufimelo_Legal-BERTimbau-base__supervised          | GPT-4.1-mini         | Legal-BERTimbau-base | 0.6983 | 0.6021 |    0.0968 |     0.0441 |     0.1510 |    0.0004 | True             |
| gpt-5.1_few_shot                                   | bilstm-crf__supervised                             | GPT-5.1              | BiLSTM-CRF           | 0.6847 | 0.5926 |    0.0922 |     0.0285 |     0.1562 |    0.0040 | True             |
| gpt-4.1-mini_few_shot                              | gpt-5.2_few_shot                                   | GPT-4.1-mini         | GPT-5.2              | 0.6983 | 0.6067 |    0.0916 |     0.0618 |     0.1226 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised  | bilstm-crf__supervised                             | BERTimbau-base       | BiLSTM-CRF           | 0.6786 | 0.5926 |    0.0857 |     0.0304 |     0.1438 |    0.0020 | True             |
| gpt-4.1-mini_few_shot                              | qwen2.5-72b_few_shot                               | GPT-4.1-mini         | Qwen2.5-72B          | 0.6983 | 0.6135 |    0.0847 |     0.0453 |     0.1240 |    0.0000 | True             |
| gpt-5.1_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised | GPT-5.1              | BERTimbau-large      | 0.6847 | 0.6018 |    0.0835 |     0.0283 |     0.1407 |    0.0022 | True             |
| gpt-5.1_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised          | GPT-5.1              | Legal-BERTimbau-base | 0.6847 | 0.6021 |    0.0831 |     0.0258 |     0.1416 |    0.0064 | True             |
| gpt-5.1_few_shot                                   | gpt-5.2_few_shot                                   | GPT-5.1              | GPT-5.2              | 0.6847 | 0.6067 |    0.0779 |     0.0460 |     0.1104 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised  | neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-base       | BERTimbau-large      | 0.6786 | 0.6018 |    0.0770 |     0.0352 |     0.1214 |    0.0002 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | neuralmind_bert-base-portuguese-cased__supervised  | Legal-BERTimbau-base | BERTimbau-base       | 0.6021 | 0.6786 |   -0.0766 |    -0.1175 |    -0.0375 |    0.0002 | True             |
| gpt-5.2_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised  | GPT-5.2              | BERTimbau-base       | 0.6067 | 0.6786 |   -0.0715 |    -0.1174 |    -0.0240 |    0.0036 | True             |
| gpt-5.1_few_shot                                   | qwen2.5-72b_few_shot                               | GPT-5.1              | Qwen2.5-72B          | 0.6847 | 0.6135 |    0.0710 |     0.0268 |     0.1144 |    0.0026 | True             |
| gpt-5-mini_few_shot                                | llama-3.3-70b_few_shot                             | GPT-5-mini           | Llama-3.3-70B        | 0.4097 | 0.3396 |    0.0697 |    -0.0043 |     0.1424 |    0.0646 | False            |
| qwen2.5-72b_few_shot                               | neuralmind_bert-base-portuguese-cased__supervised  | Qwen2.5-72B          | BERTimbau-base       | 0.6135 | 0.6786 |   -0.0645 |    -0.1163 |    -0.0128 |    0.0150 | True             |
| gpt-4.1-nano_few_shot                              | llama-3.3-70b_few_shot                             | GPT-4.1-nano         | Llama-3.3-70B        | 0.4011 | 0.3396 |    0.0615 |    -0.0071 |     0.1269 |    0.0764 | False            |
| deepseek-v4-flash_few_shot                         | neuralmind_bert-base-portuguese-cased__supervised  | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7241 | 0.6786 |    0.0462 |    -0.0133 |     0.1035 |    0.1264 | False            |
| gpt-5.1_few_shot                                   | deepseek-v4-flash_few_shot                         | GPT-5.1              | DeepSeek-V4-Flash    | 0.6847 | 0.7241 |   -0.0398 |    -0.0913 |     0.0123 |    0.1362 | False            |
| gpt-4.1_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised  | GPT-4.1              | BERTimbau-base       | 0.7151 | 0.6786 |    0.0370 |    -0.0092 |     0.0846 |    0.1176 | False            |
| gpt-4.1_few_shot                                   | gpt-5.1_few_shot                                   | GPT-4.1              | GPT-5.1              | 0.7151 | 0.6847 |    0.0306 |     0.0042 |     0.0577 |    0.0228 | True             |
| gpt-4.1-mini_few_shot                              | deepseek-v4-flash_few_shot                         | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.6983 | 0.7241 |   -0.0260 |    -0.0753 |     0.0255 |    0.3066 | False            |
| qwen2.5-72b_few_shot                               | bilstm-crf__supervised                             | Qwen2.5-72B          | BiLSTM-CRF           | 0.6135 | 0.5926 |    0.0212 |    -0.0479 |     0.0909 |    0.5464 | False            |
| gpt-4.1-mini_few_shot                              | neuralmind_bert-base-portuguese-cased__supervised  | GPT-4.1-mini         | BERTimbau-base       | 0.6983 | 0.6786 |    0.0202 |    -0.0243 |     0.0648 |    0.3834 | False            |
| gpt-4.1_few_shot                                   | gpt-4.1-mini_few_shot                              | GPT-4.1              | GPT-4.1-mini         | 0.7151 | 0.6983 |    0.0169 |    -0.0066 |     0.0405 |    0.1626 | False            |
| gpt-5.2_few_shot                                   | bilstm-crf__supervised                             | GPT-5.2              | BiLSTM-CRF           | 0.6067 | 0.5926 |    0.0142 |    -0.0507 |     0.0786 |    0.6680 | False            |
| gpt-4.1-mini_few_shot                              | gpt-5.1_few_shot                                   | GPT-4.1-mini         | GPT-5.1              | 0.6983 | 0.6847 |    0.0137 |    -0.0125 |     0.0403 |    0.3068 | False            |
| qwen2.5-72b_few_shot                               | neuralmind_bert-large-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbau-large      | 0.6135 | 0.6018 |    0.0125 |    -0.0512 |     0.0779 |    0.7014 | False            |
| qwen2.5-72b_few_shot                               | rufimelo_Legal-BERTimbau-base__supervised          | Qwen2.5-72B          | Legal-BERTimbau-base | 0.6135 | 0.6021 |    0.0121 |    -0.0465 |     0.0711 |    0.6876 | False            |
| gpt-4.1_few_shot                                   | deepseek-v4-flash_few_shot                         | GPT-4.1              | DeepSeek-V4-Flash    | 0.7151 | 0.7241 |   -0.0092 |    -0.0591 |     0.0416 |    0.7238 | False            |
| rufimelo_Legal-BERTimbau-base__supervised          | bilstm-crf__supervised                             | Legal-BERTimbau-base | BiLSTM-CRF           | 0.6021 | 0.5926 |    0.0091 |    -0.0485 |     0.0673 |    0.7680 | False            |
| neuralmind_bert-large-portuguese-cased__supervised | bilstm-crf__supervised                             | BERTimbau-large      | BiLSTM-CRF           | 0.6018 | 0.5926 |    0.0087 |    -0.0493 |     0.0671 |    0.7856 | False            |
| gpt-4.1-nano_few_shot                              | gpt-5-mini_few_shot                                | GPT-4.1-nano         | GPT-5-mini           | 0.4011 | 0.4097 |   -0.0082 |    -0.0565 |     0.0399 |    0.7372 | False            |
| gpt-5.2_few_shot                                   | qwen2.5-72b_few_shot                               | GPT-5.2              | Qwen2.5-72B          | 0.6067 | 0.6135 |   -0.0069 |    -0.0478 |     0.0341 |    0.7308 | False            |
| gpt-5.1_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised  | GPT-5.1              | BERTimbau-base       | 0.6847 | 0.6786 |    0.0064 |    -0.0409 |     0.0538 |    0.7944 | False            |
| gpt-5.2_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised | GPT-5.2              | BERTimbau-large      | 0.6067 | 0.6018 |    0.0056 |    -0.0502 |     0.0632 |    0.8608 | False            |
| gpt-5.2_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised          | GPT-5.2              | Legal-BERTimbau-base | 0.6067 | 0.6021 |    0.0052 |    -0.0498 |     0.0609 |    0.8628 | False            |
| rufimelo_Legal-BERTimbau-base__supervised          | neuralmind_bert-large-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbau-large      | 0.6021 | 0.6018 |    0.0004 |    -0.0401 |     0.0430 |    0.9960 | False            |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.7143 | 0.6786 | 0.6511 |  0.5962 |
| BERTimbau-large      | 0.6170 | 0.6018 | 0.5866 |  0.5410 |
| BiLSTM-CRF           | 0.6365 | 0.5926 | 0.5405 |  0.4280 |
| DeepSeek-V4-Flash    | 0.7550 | 0.7241 | 0.6645 |  0.0728 |
| GPT-4.1              | 0.7583 | 0.7151 | 0.6523 |  0.1218 |
| GPT-4.1-mini         | 0.7362 | 0.6983 | 0.6357 |  0.0854 |
| GPT-4.1-nano         | 0.4762 | 0.4011 | 0.3370 |  0.0531 |
| GPT-5-mini           | 0.4289 | 0.4097 | 0.3837 |  0.0711 |
| GPT-5.1              | 0.7213 | 0.6847 | 0.6384 |  0.1813 |
| GPT-5.2              | 0.6517 | 0.6067 | 0.5532 |  0.1504 |
| Legal-BERTimbau-base | 0.6112 | 0.6021 | 0.5779 |  0.5083 |
| Llama-3.3-70B        | 0.3801 | 0.3396 | 0.2991 |  0.0062 |
| Qwen2.5-72B          | 0.6423 | 0.6135 | 0.5596 |  0.1365 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5):

| iou_threshold   |   spearman_vs_0.5 |
|:----------------|------------------:|
| 0.3             |            0.9615 |
| 0.5             |            1.0000 |
| 0.7             |            0.9286 |
| exact           |            0.2253 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                              | display              |   n_docs_full |   n_docs_informative |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:---------------------------------------------------|:---------------------|--------------:|---------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| gpt-4.1_few_shot                                   | GPT-4.1              |           861 |                  232 |         0.7151 |                0.7753 |          0.0602 |                0.6512 |                       0.7583 |                 0.1072 |             0.7930 |                    0.7930 |
| gpt-4.1-mini_few_shot                              | GPT-4.1-mini         |           861 |                  232 |         0.6983 |                0.7667 |          0.0684 |                0.6185 |                       0.7345 |                 0.1160 |             0.8017 |                    0.8017 |
| deepseek-v4-flash_few_shot                         | DeepSeek-V4-Flash    |           861 |                  232 |         0.7241 |                0.7610 |          0.0370 |                0.7338 |                       0.8139 |                 0.0801 |             0.7146 |                    0.7146 |
| gpt-5.1_few_shot                                   | GPT-5.1              |           861 |                  232 |         0.6847 |                0.7497 |          0.0651 |                0.6142 |                       0.7275 |                 0.1133 |             0.7734 |                    0.7734 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |           861 |                  232 |         0.6786 |                0.6890 |          0.0104 |                0.7994 |                       0.8289 |                 0.0295 |             0.5895 |                    0.5895 |
| gpt-5.2_few_shot                                   | GPT-5.2              |           861 |                  232 |         0.6067 |                0.6829 |          0.0761 |                0.5029 |                       0.6169 |                 0.1140 |             0.7647 |                    0.7647 |
| qwen2.5-72b_few_shot                               | Qwen2.5-72B          |           861 |                  232 |         0.6135 |                0.6709 |          0.0574 |                0.5491 |                       0.6484 |                 0.0993 |             0.6950 |                    0.6950 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |           861 |                  232 |         0.6021 |                0.6123 |          0.0102 |                0.8223 |                       0.8615 |                 0.0392 |             0.4749 |                    0.4749 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |           861 |                  232 |         0.6018 |                0.6111 |          0.0093 |                0.8285 |                       0.8646 |                 0.0362 |             0.4726 |                    0.4726 |
| bilstm-crf__supervised                             | BiLSTM-CRF           |           861 |                  232 |         0.5926 |                0.6076 |          0.0150 |                0.7742 |                       0.8276 |                 0.0534 |             0.4800 |                    0.4800 |
| gpt-5-mini_few_shot                                | GPT-5-mini           |           861 |                  232 |         0.4097 |                0.5941 |          0.1844 |                0.2765 |                       0.4758 |                 0.1993 |             0.7908 |                    0.7908 |
| gpt-4.1-nano_few_shot                              | GPT-4.1-nano         |           861 |                  232 |         0.4011 |                0.4474 |          0.0463 |                0.3460 |                       0.4212 |                 0.0752 |             0.4771 |                    0.4771 |
| llama-3.3-70b_few_shot                             | Llama-3.3-70B        |           861 |                  232 |         0.3396 |                0.3499 |          0.0104 |                0.5956 |                       0.6646 |                 0.0690 |             0.2375 |                    0.2375 |

## M. Taxa de falha de alinhamento string→offset (p34)

As predições dos LLMs são strings (não offsets); são localizadas no texto-fonte por correspondência difusa (rapidfuzz `partial_ratio`, janela 500 / passo 100 / `min_score` 80). Strings que nenhuma janela casa nesse piso são descartadas silenciosamente na pontuação — a taxa de falha abaixo quantifica quantas predições nunca chegam à métrica:

| model                      | display           |   n_pred_strings |   n_aligned |   n_failed |   failure_rate |
|:---------------------------|:------------------|-----------------:|------------:|-----------:|---------------:|
| deepseek-v4-flash_few_shot | DeepSeek-V4-Flash |              522 |         447 |         75 |         0.1437 |
| gpt-4.1-nano_few_shot      | GPT-4.1-nano      |              671 |         633 |         38 |         0.0566 |
| gpt-4.1-mini_few_shot      | GPT-4.1-mini      |              601 |         595 |          6 |         0.0100 |
| qwen2.5-72b_few_shot       | Qwen2.5-72B       |              584 |         581 |          3 |         0.0051 |
| gpt-4.1_few_shot           | GPT-4.1           |              560 |         559 |          1 |         0.0018 |
| gpt-5-mini_few_shot        | GPT-5-mini        |             1315 |        1313 |          2 |         0.0015 |
| gpt-5.1_few_shot           | GPT-5.1           |              578 |         578 |          0 |         0.0000 |
| gpt-5.2_few_shot           | GPT-5.2           |              698 |         698 |          0 |         0.0000 |
| llama-3.3-70b_few_shot     | Llama-3.3-70B     |              183 |         183 |          0 |         0.0000 |

## Nota — Token F1 do GPT-4-turbo (canônico)
