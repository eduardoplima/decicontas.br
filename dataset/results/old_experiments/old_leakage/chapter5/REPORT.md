# Capítulo 5 — Números reproduzíveis (gold corrigido)

Documento auto-contido: todas as tabelas aparecem inline. Os CSVs ao lado deste arquivo são as fontes canônicas (uma por bloco), geradas por `research.release.chapter5_numbers`. Cada bloco abaixo corresponde a um item do checklist do capítulo.

## Pipeline de métricas (correções aplicadas)

Esta versão dos números incorpora as duas correções priorizadas no `METRICS_AUDIT.md`:

1. **Matching pred↔gold bipartido por IoU descendente** (`research.ner_metrics.bipartite_greedy_match`). Cada predição casa com no máximo um gold e vice-versa, eliminando a divergência anterior entre `calculate_metrics` (que tinha `break` após o primeiro match) e o bootstrap (que contava todos os pares sobrepostos). Esta única função é agora a fonte para `calculate_metrics`, `evaluate_bio_results` e `compute_doc_level_counts` — `matched ≤ min(|pred|, |gold|)` por construção, e P/R sempre em [0, 1].

2. **Token F1 de supervisionados via spaCy.** As predições BIO dos supervisionados (token-level `\S+`) são reconvertidas para spans caractere-level via `bio_to_char_spans`, depois pontuadas por `calculate_metrics` (que tokeniza com `pt_core_news_sm`). Resultado: supervisionados e LLMs compartilham o mesmo tokenizador de avaliação, tornando o token F1 da Tabela C diretamente comparável entre paradigmas.

### Comparativo antes × depois — Span F1 (14 modelos)

| model                |   span F1 antes |   span F1 depois |   Δ span F1 |
|:---------------------|----------------:|-----------------:|------------:|
| GPT-4 Turbo          |          0.7599 |           0.7321 |     -0.0278 |
| GPT-5.4-mini         |          0.7574 |           0.7269 |     -0.0305 |
| GPT-4o               |          0.7515 |           0.7237 |     -0.0278 |
| GPT-5.4-nano         |          0.7490 |           0.7229 |     -0.0261 |
| GPT-4.1-mini         |          0.7345 |           0.7108 |     -0.0237 |
| GPT-3.5              |          0.7323 |           0.7065 |     -0.0258 |
| GPT-4.1              |          0.7264 |           0.7052 |     -0.0212 |
| Gemini-2.5-flash     |          0.7100 |           0.6867 |     -0.0233 |
| BERTimbau-base       |          0.6896 |           0.6786 |     -0.0110 |
| DeepSeek-V3          |          0.6704 |           0.6459 |     -0.0245 |
| Legal-BERTimbau-base |          0.6051 |           0.6021 |     -0.0030 |
| BERTimbau-large      |          0.6049 |           0.6018 |     -0.0031 |
| BiLSTM-CRF           |          0.5926 |           0.5926 |     -0.0000 |
| GPT-4.1-nano         |          0.4424 |           0.4186 |     -0.0238 |

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
| Pares significativos a 5% (de 91)  | 61.0000 |  54.0000 | -7.0000 |
| Menor Δ detectável (significativo) |  0.0337 |   0.0364 |  0.0027 |

### Comparativo antes × depois — FC vs JSON Schema (8 experimentos)

| model        | method           |   span F1 antes |   span F1 depois |   Δ span F1 |
|:-------------|:-----------------|----------------:|-----------------:|------------:|
| gpt-3.5      | function_calling |          0.7276 |           0.7065 |     -0.0211 |
| gpt-3.5      | json_schema      |          0.6734 |           0.6498 |     -0.0236 |
| gpt-4o       | function_calling |          0.7500 |           0.7237 |     -0.0263 |
| gpt-4o       | json_schema      |          0.6715 |           0.6556 |     -0.0159 |
| gpt-5.4-mini | function_calling |          0.7566 |           0.7269 |     -0.0297 |
| gpt-5.4-mini | json_schema      |          0.5650 |           0.5357 |     -0.0293 |
| gpt-5.4-nano | function_calling |          0.7482 |           0.7229 |     -0.0253 |
| gpt-5.4-nano | json_schema      |          0.7087 |           0.6784 |     -0.0303 |

### Comparativo antes × depois — Técnicas de prompting (16 experimentos)

| model            | technique        |   span F1 antes |   span F1 depois |   Δ span F1 |
|:-----------------|:-----------------|----------------:|-----------------:|------------:|
| gpt-5.4-nano     | cot              |          0.7613 |           0.7333 |     -0.0280 |
| gpt-5.4-mini     | few_shot         |          0.7566 |           0.7269 |     -0.0297 |
| gpt-5.4-nano     | few_shot         |          0.7482 |           0.7229 |     -0.0253 |
| gemini-2.5-flash | cot              |          0.7346 |           0.7118 |     -0.0228 |
| gpt-5.4-mini     | cot              |          0.7348 |           0.7072 |     -0.0276 |
| gemini-2.5-flash | two_stage        |          0.7253 |           0.7025 |     -0.0228 |
| gpt-5.4-nano     | two_stage        |          0.7196 |           0.6914 |     -0.0282 |
| gemini-2.5-flash | dynamic_few_shot |          0.7085 |           0.6879 |     -0.0206 |
| gemini-2.5-flash | few_shot         |          0.7093 |           0.6867 |     -0.0226 |
| deepseek-v3      | two_stage        |          0.6954 |           0.6718 |     -0.0236 |
| gpt-5.4-nano     | dynamic_few_shot |          0.6925 |           0.6687 |     -0.0238 |
| gpt-5.4-mini     | two_stage        |          0.6798 |           0.6556 |     -0.0242 |
| gpt-5.4-mini     | dynamic_few_shot |          0.6800 |           0.6546 |     -0.0254 |
| deepseek-v3      | few_shot         |          0.6685 |           0.6459 |     -0.0226 |
| deepseek-v3      | dynamic_few_shot |          0.5584 |           0.5373 |     -0.0211 |
| deepseek-v3      | cot              |          0.5250 |           0.5123 |     -0.0127 |

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
| gpt-4-turbo                                        | GPT-4 Turbo          |     0.8096 |           0.7682 |            0.8188 |         0.8006 |    0.7321 |          0.7139 |           0.6721 |        0.8039 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         |     0.7931 |           0.7583 |            0.8167 |         0.7708 |    0.7269 |          0.7006 |           0.6806 |        0.7800 |
| gpt-4o                                             | GPT-4o               |     0.8038 |           0.7655 |            0.8216 |         0.7867 |    0.7237 |          0.7014 |           0.6654 |        0.7930 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         |     0.7876 |           0.7556 |            0.8141 |         0.7628 |    0.7229 |          0.6997 |           0.6704 |        0.7843 |
| gpt-41-mini                                        | GPT-4.1-mini         |     0.7915 |           0.7479 |            0.7956 |         0.7874 |    0.7108 |          0.6878 |           0.6498 |        0.7843 |
| gpt-35                                             | GPT-3.5              |     0.7891 |           0.7477 |            0.8052 |         0.7735 |    0.7065 |          0.6811 |           0.6502 |        0.7734 |
| gpt-41                                             | GPT-4.1              |     0.7945 |           0.7546 |            0.7795 |         0.8102 |    0.7052 |          0.6877 |           0.6321 |        0.7974 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     |     0.7614 |           0.7332 |            0.7508 |         0.7724 |    0.6867 |          0.6707 |           0.6189 |        0.7712 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |     0.7683 |           0.6318 |            0.9506 |         0.6447 |    0.6786 |          0.5801 |           0.7994 |        0.5895 |
| deepseek-v3_few_shot                               | DeepSeek-V3          |     0.7422 |           0.6793 |            0.7499 |         0.7347 |    0.6459 |          0.6002 |           0.5700 |        0.7451 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |     0.6855 |           0.4242 |            0.9474 |         0.5371 |    0.6021 |          0.4058 |           0.8223 |        0.4749 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |     0.6820 |           0.5103 |            0.9607 |         0.5287 |    0.6018 |          0.4778 |           0.8285 |        0.4726 |
| bilstm-crf__supervised                             | BiLSTM-CRF           |     0.7307 |           0.5638 |            0.8455 |         0.6434 |    0.5926 |          0.5004 |           0.7742 |        0.4800 |
| gpt-41-nano                                        | GPT-4.1-nano         |     0.5738 |           0.4793 |            0.5752 |         0.5725 |    0.4186 |          0.3725 |           0.3426 |        0.5381 |

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
| few-shot           |                 0.7647 |                0.0699 |                0.5738 |                0.8096 |                0.6779 |               0.0945 |               0.4186 |               0.7321 |
| supervised         |                 0.7167 |                0.0410 |                0.6820 |                0.7683 |                0.6188 |               0.0401 |               0.5926 |               0.6786 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.7836 |      0.6737 |         0.3226 |          0.5405 |
| BERTimbau-large      |  0.7178 |      0.6452 |         0.2034 |          0.3448 |
| BiLSTM-CRF           |  0.6534 |      0.6887 |         0.2466 |          0.4130 |
| DeepSeek-V3          |  0.7668 |      0.5942 |         0.5207 |          0.5191 |
| GPT-3.5              |  0.7865 |      0.6331 |         0.6429 |          0.6620 |
| GPT-4 Turbo          |  0.8118 |      0.6414 |         0.6525 |          0.7500 |
| GPT-4.1              |  0.7864 |      0.6313 |         0.5850 |          0.7481 |
| GPT-4.1-mini         |  0.7790 |      0.6528 |         0.6154 |          0.7040 |
| GPT-4.1-nano         |  0.7075 |      0.2548 |         0.0753 |          0.4526 |
| GPT-4o               |  0.8081 |      0.6312 |         0.6714 |          0.6950 |
| GPT-5.4-mini         |  0.8074 |      0.6618 |         0.6714 |          0.6619 |
| GPT-5.4-nano         |  0.7838 |      0.6813 |         0.6429 |          0.6906 |
| Gemini-2.5-flash     |  0.7877 |      0.5882 |         0.6241 |          0.6825 |
| Legal-BERTimbau-base |  0.7548 |      0.6243 |         0.0727 |          0.1714 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                              | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:---------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4-turbo                                        | GPT-4 Turbo          | MULTA         |      0.7817 |   0.8443 | 0.8118 |       179 |          212 |          229 |
| gpt-4-turbo                                        | GPT-4 Turbo          | OBRIGACAO     |      0.5849 |   0.7099 | 0.6414 |        93 |          131 |          159 |
| gpt-4-turbo                                        | GPT-4 Turbo          | RECOMENDACAO  |      0.5227 |   0.8679 | 0.6525 |        46 |           53 |           88 |
| gpt-4-turbo                                        | GPT-4 Turbo          | RESSARCIMENTO |      0.6986 |   0.8095 | 0.7500 |        51 |           63 |           73 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         | MULTA         |      0.7945 |   0.8208 | 0.8074 |       174 |          212 |          219 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         | OBRIGACAO     |      0.6319 |   0.6947 | 0.6618 |        91 |          131 |          144 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         | RECOMENDACAO  |      0.5402 |   0.8868 | 0.6714 |        47 |           53 |           87 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         | RESSARCIMENTO |      0.6053 |   0.7302 | 0.6619 |        46 |           63 |           76 |
| gpt-4o                                             | GPT-4o               | MULTA         |      0.7749 |   0.8443 | 0.8081 |       179 |          212 |          231 |
| gpt-4o                                             | GPT-4o               | OBRIGACAO     |      0.5894 |   0.6794 | 0.6312 |        89 |          131 |          151 |
| gpt-4o                                             | GPT-4o               | RECOMENDACAO  |      0.5402 |   0.8868 | 0.6714 |        47 |           53 |           87 |
| gpt-4o                                             | GPT-4o               | RESSARCIMENTO |      0.6282 |   0.7778 | 0.6950 |        49 |           63 |           78 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         | MULTA         |      0.7500 |   0.8208 | 0.7838 |       174 |          212 |          232 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         | OBRIGACAO     |      0.6549 |   0.7099 | 0.6813 |        93 |          131 |          142 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         | RECOMENDACAO  |      0.5172 |   0.8491 | 0.6429 |        45 |           53 |           87 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         | RESSARCIMENTO |      0.6316 |   0.7619 | 0.6906 |        48 |           63 |           76 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | MULTA         |      0.7965 |   0.7173 | 0.7548 |       137 |          191 |          172 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | OBRIGACAO     |      0.9818 |   0.4576 | 0.6243 |        54 |          118 |           55 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | RECOMENDACAO  |      0.2857 |   0.0417 | 0.0727 |         2 |           48 |            7 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base | RESSARCIMENTO |      0.7500 |   0.0968 | 0.1714 |         6 |           62 |            8 |
| gpt-41-mini                                        | GPT-4.1-mini         | MULTA         |      0.7265 |   0.8396 | 0.7790 |       178 |          212 |          245 |
| gpt-41-mini                                        | GPT-4.1-mini         | OBRIGACAO     |      0.5987 |   0.7176 | 0.6528 |        94 |          131 |          157 |
| gpt-41-mini                                        | GPT-4.1-mini         | RECOMENDACAO  |      0.4889 |   0.8302 | 0.6154 |        44 |           53 |           90 |
| gpt-41-mini                                        | GPT-4.1-mini         | RESSARCIMENTO |      0.7097 |   0.6984 | 0.7040 |        44 |           63 |           62 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | MULTA         |      0.8218 |   0.7487 | 0.7836 |       143 |          191 |          174 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | OBRIGACAO     |      0.8889 |   0.5424 | 0.6737 |        64 |          118 |           72 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | RECOMENDACAO  |      0.7143 |   0.2083 | 0.3226 |        10 |           48 |           14 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       | RESSARCIMENTO |      0.6122 |   0.4839 | 0.5405 |        30 |           62 |           49 |
| gpt-35                                             | GPT-3.5              | MULTA         |      0.7511 |   0.8255 | 0.7865 |       175 |          212 |          233 |
| gpt-35                                             | GPT-3.5              | OBRIGACAO     |      0.5986 |   0.6718 | 0.6331 |        88 |          131 |          147 |
| gpt-35                                             | GPT-3.5              | RECOMENDACAO  |      0.5172 |   0.8491 | 0.6429 |        45 |           53 |           87 |
| gpt-35                                             | GPT-3.5              | RESSARCIMENTO |      0.5949 |   0.7460 | 0.6620 |        47 |           63 |           79 |
| gpt-41                                             | GPT-4.1              | MULTA         |      0.7588 |   0.8160 | 0.7864 |       173 |          212 |          228 |
| gpt-41                                             | GPT-4.1              | OBRIGACAO     |      0.5344 |   0.7710 | 0.6313 |       101 |          131 |          189 |
| gpt-41                                             | GPT-4.1              | RECOMENDACAO  |      0.4574 |   0.8113 | 0.5850 |        43 |           53 |           94 |
| gpt-41                                             | GPT-4.1              | RESSARCIMENTO |      0.7206 |   0.7778 | 0.7481 |        49 |           63 |           68 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | MULTA         |      0.8667 |   0.6126 | 0.7178 |       117 |          191 |          135 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | OBRIGACAO     |      0.8824 |   0.5085 | 0.6452 |        60 |          118 |           68 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | RECOMENDACAO  |      0.5455 |   0.1250 | 0.2034 |         6 |           48 |           11 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      | RESSARCIMENTO |      0.6000 |   0.2419 | 0.3448 |        15 |           62 |           25 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     | MULTA         |      0.7877 |   0.7877 | 0.7877 |       167 |          212 |          212 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     | OBRIGACAO     |      0.4785 |   0.7634 | 0.5882 |       100 |          131 |          209 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     | RECOMENDACAO  |      0.5000 |   0.8302 | 0.6241 |        44 |           53 |           88 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     | RESSARCIMENTO |      0.6825 |   0.6825 | 0.6825 |        43 |           63 |           63 |
| deepseek-v3_few_shot                               | DeepSeek-V3          | MULTA         |      0.7308 |   0.8066 | 0.7668 |       171 |          212 |          234 |
| deepseek-v3_few_shot                               | DeepSeek-V3          | OBRIGACAO     |      0.5110 |   0.7099 | 0.5942 |        93 |          131 |          182 |
| deepseek-v3_few_shot                               | DeepSeek-V3          | RECOMENDACAO  |      0.3793 |   0.8302 | 0.5207 |        44 |           53 |          116 |
| deepseek-v3_few_shot                               | DeepSeek-V3          | RESSARCIMENTO |      0.5000 |   0.5397 | 0.5191 |        34 |           63 |           68 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | MULTA         |      0.7986 |   0.5529 | 0.6534 |       115 |          208 |          144 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | OBRIGACAO     |      0.8488 |   0.5794 | 0.6887 |        73 |          126 |           86 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | RECOMENDACAO  |      0.4500 |   0.1698 | 0.2466 |         9 |           53 |           20 |
| bilstm-crf__supervised                             | BiLSTM-CRF           | RESSARCIMENTO |      0.6552 |   0.3016 | 0.4130 |        19 |           63 |           29 |
| gpt-41-nano                                        | GPT-4.1-nano         | MULTA         |      0.6812 |   0.7358 | 0.7075 |       156 |          212 |          229 |
| gpt-41-nano                                        | GPT-4.1-nano         | OBRIGACAO     |      0.1860 |   0.4046 | 0.2548 |        53 |          131 |          285 |
| gpt-41-nano                                        | GPT-4.1-nano         | RECOMENDACAO  |      0.0526 |   0.1321 | 0.0753 |         7 |           53 |          133 |
| gpt-41-nano                                        | GPT-4.1-nano         | RESSARCIMENTO |      0.4189 |   0.4921 | 0.4526 |        31 |           63 |           74 |

## E. Custo-benefício

Os JSONs de predição não armazenam contagens de tokens da API; o template abaixo reporta caracteres médios e estimativa aproximada de tokens (≈ 4 chars/token), com colunas em branco para as tarifas USD/1M de cada provedor — preencher manualmente consultando o histórico de billing.

| model                     | display          |   n_docs |   mean_input_chars |   mean_output_chars |   approx_mean_input_tokens |   approx_mean_output_tokens |   total_input_chars |   total_output_chars |   input_cost_per_1M_USD |   output_cost_per_1M_USD |   estimated_total_cost_USD |
|:--------------------------|:-----------------|---------:|-------------------:|--------------------:|---------------------------:|----------------------------:|--------------------:|---------------------:|------------------------:|-------------------------:|---------------------------:|
| gpt-4-turbo               | GPT-4 Turbo      |      861 |           876.3670 |            284.7747 |                   219.0918 |                     71.1937 |              754552 |               245191 |                     nan |                      nan |                        nan |
| gpt-5.4-mini_few_shot     | GPT-5.4-mini     |      861 |           876.3705 |            281.0360 |                   219.0926 |                     70.2590 |              754555 |               241972 |                     nan |                      nan |                        nan |
| gpt-4o                    | GPT-4o           |      861 |           876.3670 |            281.4448 |                   219.0918 |                     70.3612 |              754552 |               242324 |                     nan |                      nan |                        nan |
| gpt-5.4-nano_few_shot     | GPT-5.4-nano     |      861 |           876.3705 |            281.5226 |                   219.0926 |                     70.3807 |              754555 |               242391 |                     nan |                      nan |                        nan |
| gpt-41-mini               | GPT-4.1-mini     |      861 |           876.3670 |            290.6655 |                   219.0918 |                     72.6664 |              754552 |               250263 |                     nan |                      nan |                        nan |
| gpt-35                    | GPT-3.5          |      861 |           876.3670 |            282.4123 |                   219.0918 |                     70.6031 |              754552 |               243157 |                     nan |                      nan |                        nan |
| gpt-41                    | GPT-4.1          |      861 |           876.3670 |            298.5145 |                   219.0918 |                     74.6286 |              754552 |               257021 |                     nan |                      nan |                        nan |
| gemini-2.5-flash_few_shot | Gemini-2.5-flash |      861 |           876.3705 |            295.8688 |                   219.0926 |                     73.9672 |              754555 |               254743 |                     nan |                      nan |                        nan |
| deepseek-v3_few_shot      | DeepSeek-V3      |      861 |           876.3705 |            291.6957 |                   219.0926 |                     72.9239 |              754555 |               251150 |                     nan |                      nan |                        nan |
| gpt-41-nano               | GPT-4.1-nano     |      861 |           876.3670 |            312.9861 |                   219.0918 |                     78.2465 |              754552 |               269481 |                     nan |                      nan |                        nan |

## F. Function calling vs JSON schema

**Métricas overall:**

| model        | method           |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:-------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| gpt-3.5      | function_calling |     0.7891 |    0.7065 |          0.6811 |           0.6502 |        0.7734 |
| gpt-3.5      | json_schema      |     0.7363 |    0.6498 |          0.6112 |           0.6068 |        0.6993 |
| gpt-4o       | function_calling |     0.8038 |    0.7237 |          0.7014 |           0.6654 |        0.7930 |
| gpt-4o       | json_schema      |     0.7434 |    0.6556 |          0.6073 |           0.6257 |        0.6885 |
| gpt-5.4-mini | function_calling |     0.7931 |    0.7269 |          0.7006 |           0.6806 |        0.7800 |
| gpt-5.4-mini | json_schema      |     0.5814 |    0.5357 |          0.4952 |           0.6294 |        0.4662 |
| gpt-5.4-nano | function_calling |     0.7876 |    0.7229 |          0.6997 |           0.6704 |        0.7843 |
| gpt-5.4-nano | json_schema      |     0.7552 |    0.6784 |          0.6380 |           0.6457 |        0.7146 |

**Δ por modelo (FC − JS):**

| model        |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:-------------|-----------------:|----------------:|-----------------------:|--------------------:|
| gpt-3.5      |           0.0527 |          0.0567 |                 0.0434 |              0.0741 |
| gpt-4o       |           0.0604 |          0.0681 |                 0.0397 |              0.1046 |
| gpt-5.4-mini |           0.2117 |          0.1912 |                 0.0512 |              0.3137 |
| gpt-5.4-nano |           0.0324 |          0.0445 |                 0.0247 |              0.0697 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model        | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:-------------|:-----------------|--------:|------------:|---------------:|----------------:|
| gpt-3.5      | function_calling |  0.7865 |      0.6331 |         0.6429 |          0.6620 |
| gpt-3.5      | json_schema      |  0.7575 |      0.5776 |         0.4965 |          0.6131 |
| gpt-4o       | function_calling |  0.8081 |      0.6312 |         0.6714 |          0.6950 |
| gpt-4o       | json_schema      |  0.7757 |      0.5891 |         0.5714 |          0.4928 |
| gpt-5.4-mini | function_calling |  0.8074 |      0.6618 |         0.6714 |          0.6619 |
| gpt-5.4-mini | json_schema      |  0.6471 |      0.3627 |         0.3800 |          0.5909 |
| gpt-5.4-nano | function_calling |  0.7838 |      0.6813 |         0.6429 |          0.6906 |
| gpt-5.4-nano | json_schema      |  0.7755 |      0.6166 |         0.5180 |          0.6418 |

**Span Precision (modelo+método × entidade):**

| model        | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:-------------|:-----------------|--------:|------------:|---------------:|----------------:|
| gpt-3.5      | function_calling |  0.7511 |      0.5986 |         0.5172 |          0.5949 |
| gpt-3.5      | json_schema      |  0.7421 |      0.5479 |         0.3977 |          0.5676 |
| gpt-4o       | function_calling |  0.7749 |      0.5894 |         0.5402 |          0.6282 |
| gpt-4o       | json_schema      |  0.7685 |      0.5984 |         0.4598 |          0.4533 |
| gpt-5.4-mini | function_calling |  0.7945 |      0.6319 |         0.5402 |          0.6053 |
| gpt-5.4-mini | json_schema      |  0.7469 |      0.5645 |         0.4043 |          0.5652 |
| gpt-5.4-nano | function_calling |  0.7500 |      0.6549 |         0.5172 |          0.6316 |
| gpt-5.4-nano | json_schema      |  0.7467 |      0.6393 |         0.4186 |          0.6056 |

**Span Recall (modelo+método × entidade):**

| model        | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:-------------|:-----------------|--------:|------------:|---------------:|----------------:|
| gpt-3.5      | function_calling |  0.8255 |      0.6718 |         0.8491 |          0.7460 |
| gpt-3.5      | json_schema      |  0.7736 |      0.6107 |         0.6604 |          0.6667 |
| gpt-4o       | function_calling |  0.8443 |      0.6794 |         0.8868 |          0.7778 |
| gpt-4o       | json_schema      |  0.7830 |      0.5802 |         0.7547 |          0.5397 |
| gpt-5.4-mini | function_calling |  0.8208 |      0.6947 |         0.8868 |          0.7302 |
| gpt-5.4-mini | json_schema      |  0.5708 |      0.2672 |         0.3585 |          0.6190 |
| gpt-5.4-nano | function_calling |  0.8208 |      0.7099 |         0.8491 |          0.7619 |
| gpt-5.4-nano | json_schema      |  0.8066 |      0.5954 |         0.6792 |          0.6825 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model            | technique        |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:-----------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v3      | cot              |     0.6017 |    0.5123 |          0.4012 |           0.5021 |        0.5229 |
| deepseek-v3      | dynamic_few_shot |     0.6789 |    0.5373 |          0.5020 |           0.4397 |        0.6906 |
| deepseek-v3      | few_shot         |     0.7422 |    0.6459 |          0.6002 |           0.5700 |        0.7451 |
| deepseek-v3      | two_stage        |     0.7678 |    0.6718 |          0.6253 |           0.6003 |        0.7625 |
| gemini-2.5-flash | cot              |     0.7752 |    0.7118 |          0.7063 |           0.6471 |        0.7908 |
| gemini-2.5-flash | dynamic_few_shot |     0.7799 |    0.6879 |          0.6607 |           0.6181 |        0.7756 |
| gemini-2.5-flash | few_shot         |     0.7614 |    0.6867 |          0.6707 |           0.6189 |        0.7712 |
| gemini-2.5-flash | two_stage        |     0.7740 |    0.7025 |          0.6903 |           0.6377 |        0.7821 |
| gpt-5.4-mini     | cot              |     0.7928 |    0.7072 |          0.6782 |           0.6610 |        0.7603 |
| gpt-5.4-mini     | dynamic_few_shot |     0.7532 |    0.6546 |          0.6189 |           0.6071 |        0.7102 |
| gpt-5.4-mini     | few_shot         |     0.7931 |    0.7269 |          0.7006 |           0.6806 |        0.7800 |
| gpt-5.4-mini     | two_stage        |     0.7452 |    0.6556 |          0.6164 |           0.6275 |        0.6863 |
| gpt-5.4-nano     | cot              |     0.7996 |    0.7333 |          0.7025 |           0.6953 |        0.7756 |
| gpt-5.4-nano     | dynamic_few_shot |     0.7417 |    0.6687 |          0.6467 |           0.6301 |        0.7124 |
| gpt-5.4-nano     | few_shot         |     0.7876 |    0.7229 |          0.6997 |           0.6704 |        0.7843 |
| gpt-5.4-nano     | two_stage        |     0.7607 |    0.6914 |          0.6613 |           0.6569 |        0.7298 |

**Span F1 pivotado (modelo × técnica):**

| model            |    cot |   dynamic_few_shot |   few_shot |   two_stage |
|:-----------------|-------:|-------------------:|-----------:|------------:|
| deepseek-v3      | 0.5123 |             0.5373 |     0.6459 |      0.6718 |
| gemini-2.5-flash | 0.7118 |             0.6879 |     0.6867 |      0.7025 |
| gpt-5.4-mini     | 0.7072 |             0.6546 |     0.7269 |      0.6556 |
| gpt-5.4-nano     | 0.7333 |             0.6687 |     0.7229 |      0.6914 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique        | token_f1           | token_f1.1           | token_f1.2         | token_f1.3         | span_f1            | span_f1.1            | span_f1.2          | span_f1.3          |
|:-----------------|:-------------------|:---------------------|:-------------------|:-------------------|:-------------------|:---------------------|:-------------------|:-------------------|
| nan              | mean               | std                  | min                | max                | mean               | std                  | min                | max                |
| cot              | 0.7423066935080604 | 0.0943188107712375   | 0.6016746411483254 | 0.7996283155938503 | 0.6661240273896539 | 0.10319514575776269  | 0.512273212379936  | 0.7332646755921729 |
| dynamic_few_shot | 0.738419546973941  | 0.042782849336040187 | 0.6789044101042037 | 0.7799064813612158 | 0.6371352428111325 | 0.06794984531301622  | 0.5372881355932203 | 0.6879227053140097 |
| few_shot         | 0.7710998741138096 | 0.02368865516707095  | 0.7422330016994175 | 0.7931040276914287 | 0.6955998502510572 | 0.037747362669320196 | 0.6458923512747876 | 0.7269035532994924 |
| two_stage        | 0.7619453027944786 | 0.01238847589637472  | 0.7452459586302799 | 0.7740383072925021 | 0.6803326615530103 | 0.020840579473605455 | 0.6555671175858481 | 0.7025440313111546 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model            | technique        |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:-----------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v3      | cot              |  0.7040 |      0.3731 |         0.1600 |          0.3677 |
| deepseek-v3      | dynamic_few_shot |  0.7419 |      0.4011 |         0.3243 |          0.5405 |
| deepseek-v3      | few_shot         |  0.7668 |      0.5942 |         0.5207 |          0.5191 |
| deepseek-v3      | two_stage        |  0.7785 |      0.6483 |         0.5422 |          0.5324 |
| gemini-2.5-flash | cot              |  0.7981 |      0.6012 |         0.6479 |          0.7778 |
| gemini-2.5-flash | dynamic_few_shot |  0.7981 |      0.6006 |         0.5823 |          0.6617 |
| gemini-2.5-flash | few_shot         |  0.7877 |      0.5882 |         0.6241 |          0.6825 |
| gemini-2.5-flash | two_stage        |  0.8113 |      0.5783 |         0.6571 |          0.7143 |
| gpt-5.4-mini     | cot              |  0.7606 |      0.7050 |         0.6331 |          0.6143 |
| gpt-5.4-mini     | dynamic_few_shot |  0.7394 |      0.6061 |         0.5833 |          0.5468 |
| gpt-5.4-mini     | few_shot         |  0.8074 |      0.6618 |         0.6714 |          0.6619 |
| gpt-5.4-mini     | two_stage        |  0.7610 |      0.5759 |         0.5468 |          0.5821 |
| gpt-5.4-nano     | cot              |  0.8167 |      0.6743 |         0.6429 |          0.6763 |
| gpt-5.4-nano     | dynamic_few_shot |  0.7404 |      0.5932 |         0.5915 |          0.6615 |
| gpt-5.4-nano     | few_shot         |  0.7838 |      0.6813 |         0.6429 |          0.6906 |
| gpt-5.4-nano     | two_stage        |  0.7846 |      0.5992 |         0.5286 |          0.7328 |

**Span Precision por entidade (mesmo eixo):**

| model            | technique        |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:-----------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v3      | cot              |  0.6709 |      0.5806 |         0.2727 |          0.2562 |
| deepseek-v3      | dynamic_few_shot |  0.6867 |      0.3211 |         0.2130 |          0.4706 |
| deepseek-v3      | few_shot         |  0.7308 |      0.5110 |         0.3793 |          0.5000 |
| deepseek-v3      | two_stage        |  0.7404 |      0.5912 |         0.3982 |          0.4868 |
| gemini-2.5-flash | cot              |  0.7944 |      0.5026 |         0.5169 |          0.7778 |
| gemini-2.5-flash | dynamic_few_shot |  0.7854 |      0.5165 |         0.4381 |          0.6286 |
| gemini-2.5-flash | few_shot         |  0.7877 |      0.4785 |         0.5000 |          0.6825 |
| gemini-2.5-flash | two_stage        |  0.8113 |      0.4776 |         0.5287 |          0.7143 |
| gpt-5.4-mini     | cot              |  0.7234 |      0.7077 |         0.5116 |          0.5584 |
| gpt-5.4-mini     | dynamic_few_shot |  0.7004 |      0.6015 |         0.4615 |          0.5000 |
| gpt-5.4-mini     | few_shot         |  0.7945 |      0.6319 |         0.5402 |          0.6053 |
| gpt-5.4-mini     | two_stage        |  0.7489 |      0.5873 |         0.4419 |          0.5493 |
| gpt-5.4-nano     | cot              |  0.8037 |      0.6769 |         0.5172 |          0.6184 |
| gpt-5.4-nano     | dynamic_few_shot |  0.7100 |      0.5909 |         0.4719 |          0.6418 |
| gpt-5.4-nano     | few_shot         |  0.7500 |      0.6549 |         0.5172 |          0.6316 |
| gpt-5.4-nano     | two_stage        |  0.7555 |      0.6111 |         0.4253 |          0.7059 |

**Span Recall por entidade:**

| model            | technique        |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:-----------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v3      | cot              |  0.7406 |      0.2748 |         0.1132 |          0.6508 |
| deepseek-v3      | dynamic_few_shot |  0.8066 |      0.5344 |         0.6792 |          0.6349 |
| deepseek-v3      | few_shot         |  0.8066 |      0.7099 |         0.8302 |          0.5397 |
| deepseek-v3      | two_stage        |  0.8208 |      0.7176 |         0.8491 |          0.5873 |
| gemini-2.5-flash | cot              |  0.8019 |      0.7481 |         0.8679 |          0.7778 |
| gemini-2.5-flash | dynamic_few_shot |  0.8113 |      0.7176 |         0.8679 |          0.6984 |
| gemini-2.5-flash | few_shot         |  0.7877 |      0.7634 |         0.8302 |          0.6825 |
| gemini-2.5-flash | two_stage        |  0.8113 |      0.7328 |         0.8679 |          0.7143 |
| gpt-5.4-mini     | cot              |  0.8019 |      0.7023 |         0.8302 |          0.6825 |
| gpt-5.4-mini     | dynamic_few_shot |  0.7830 |      0.6107 |         0.7925 |          0.6032 |
| gpt-5.4-mini     | few_shot         |  0.8208 |      0.6947 |         0.8868 |          0.7302 |
| gpt-5.4-mini     | two_stage        |  0.7736 |      0.5649 |         0.7170 |          0.6190 |
| gpt-5.4-nano     | cot              |  0.8302 |      0.6718 |         0.8491 |          0.7460 |
| gpt-5.4-nano     | dynamic_few_shot |  0.7736 |      0.5954 |         0.7925 |          0.6825 |
| gpt-5.4-nano     | few_shot         |  0.8208 |      0.7099 |         0.8491 |          0.7619 |
| gpt-5.4-nano     | two_stage        |  0.8160 |      0.5878 |         0.6981 |          0.7619 |

## I. Análise de erros do melhor modelo

**Melhor modelo identificado por span F1: GPT-4 Turbo.**

**Contagens por tipo de erro:**

| kind       |   count |
|:-----------|--------:|
| exact      |     383 |
| FP         |     103 |
| FN         |      60 |
| boundary   |      59 |
| type_error |       4 |

**Matriz rótulo × tipo de erro:**

| label         |   FN |   FP |   boundary |   exact |   type_error |
|:--------------|-----:|-----:|-----------:|--------:|-------------:|
| MULTA         |   27 |    9 |         15 |     190 |            1 |
| OBRIGACAO     |   26 |   47 |         21 |      93 |            1 |
| RECOMENDACAO  |    6 |   38 |          2 |      48 |            0 |
| RESSARCIMENTO |    1 |    9 |         21 |      52 |            2 |

**Pares de tipo errado (gold → pred):**

| label         | pred_label   |   count |
|:--------------|:-------------|--------:|
| MULTA         | OBRIGACAO    |       1 |
| OBRIGACAO     | MULTA        |       1 |
| RESSARCIMENTO | MULTA        |       2 |

**Histograma de IoU para erros de fronteira:**

|   bin_low |   bin_high |   count |
|----------:|-----------:|--------:|
|    0.0000 |     0.2000 | 10.0000 |
|    0.2000 |     0.4000 | 34.0000 |
|    0.4000 |     0.5000 | 15.0000 |
|    0.5000 |     0.7000 |  0.0000 |
|    0.7000 |     0.9000 |  0.0000 |
|    0.9000 |     1.0000 |  0.0000 |

## J. Significância estatística (bootstrap pareado)

**Item 41 — N de reamostragens**: 10.000.

**Item 42 — IC 95% por modelo:**

| model                                              | display              |   span_f1_point |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:---------------------------------------------------|:---------------------|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| gpt-4-turbo                                        | GPT-4 Turbo          |          0.7321 |         0.7324 |        0.0218 |     0.6881 |     0.7744 |     0.0863 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         |          0.7269 |         0.7274 |        0.0236 |     0.6795 |     0.7731 |     0.0936 |
| gpt-4o                                             | GPT-4o               |          0.7237 |         0.7240 |        0.0228 |     0.6790 |     0.7673 |     0.0882 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         |          0.7229 |         0.7232 |        0.0224 |     0.6791 |     0.7657 |     0.0866 |
| gpt-41-mini                                        | GPT-4.1-mini         |          0.7108 |         0.7110 |        0.0222 |     0.6674 |     0.7547 |     0.0873 |
| gpt-35                                             | GPT-3.5              |          0.7065 |         0.7066 |        0.0239 |     0.6593 |     0.7531 |     0.0937 |
| gpt-41                                             | GPT-4.1              |          0.7052 |         0.7053 |        0.0213 |     0.6635 |     0.7465 |     0.0831 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     |          0.6867 |         0.6868 |        0.0214 |     0.6436 |     0.7279 |     0.0844 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |          0.6786 |         0.6783 |        0.0273 |     0.6243 |     0.7300 |     0.1057 |
| deepseek-v3_few_shot                               | DeepSeek-V3          |          0.6459 |         0.6459 |        0.0232 |     0.5996 |     0.6901 |     0.0905 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |          0.6021 |         0.6016 |        0.0303 |     0.5410 |     0.6593 |     0.1183 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |          0.6018 |         0.6012 |        0.0314 |     0.5383 |     0.6616 |     0.1232 |
| bilstm-crf__supervised                             | BiLSTM-CRF           |          0.5926 |         0.5925 |        0.0329 |     0.5269 |     0.6569 |     0.1300 |
| gpt-41-nano                                        | GPT-4.1-nano         |          0.4186 |         0.4185 |        0.0222 |     0.3757 |     0.4617 |     0.0860 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                           | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:--------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| gpt-4-turbo                                       | gpt-41-nano                                       | GPT-4 Turbo          | GPT-4.1-nano         | 0.7321 | 0.4186 |    0.3139 |     0.2718 |     0.3577 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-4-turbo                                       | bilstm-crf__supervised                            | GPT-4 Turbo          | BiLSTM-CRF           | 0.7321 | 0.5926 |    0.1399 |     0.0782 |     0.2018 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-4-turbo                                       | rufimelo_Legal-BERTimbau-base__supervised         | GPT-4 Turbo          | Legal-BERTimbau-base | 0.7321 | 0.6021 |    0.1308 |     0.0784 |     0.1848 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-5.4-mini_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised         | GPT-5.4-mini         | Legal-BERTimbau-base | 0.7269 | 0.6021 |    0.1258 |     0.0709 |     0.1802 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-4-turbo                                       | deepseek-v3_few_shot                              | GPT-4 Turbo          | DeepSeek-V3          | 0.7321 | 0.6459 |    0.0865 |     0.0515 |     0.1218 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                            | BERTimbau-base       | BiLSTM-CRF           | 0.6786 | 0.5926 |    0.0857 |     0.0304 |     0.1438 |    0.0020 | True             |   0.0120 |         0.0240 | True            | True                  |            12 |
| rufimelo_Legal-BERTimbau-base__supervised         | neuralmind_bert-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbau-base       | 0.6021 | 0.6786 |   -0.0766 |    -0.1175 |    -0.0375 |    0.0002 | True             |   0.0014 |         0.0024 | True            | True                  |            12 |
| gpt-4-turbo                                       | neuralmind_bert-base-portuguese-cased__supervised | GPT-4 Turbo          | BERTimbau-base       | 0.7321 | 0.6786 |    0.0541 |     0.0080 |     0.1021 |    0.0200 | True             |   0.0800 |         0.2400 | False           | False                 |            12 |
| gpt-4-turbo                                       | gemini-2.5-flash_few_shot                         | GPT-4 Turbo          | Gemini-2.5-flash     | 0.7321 | 0.6867 |    0.0456 |     0.0155 |     0.0749 |    0.0042 | True             |   0.0210 |         0.0504 | True            | False                 |            12 |
| gpt-4-turbo                                       | gpt-4o                                            | GPT-4 Turbo          | GPT-4o               | 0.7321 | 0.7237 |    0.0084 |    -0.0231 |     0.0415 |    0.6130 | False            |   1.0000 |         1.0000 | False           | False                 |            12 |
| gpt-4-turbo                                       | gpt-5.4-mini_few_shot                             | GPT-4 Turbo          | GPT-5.4-mini         | 0.7321 | 0.7269 |    0.0050 |    -0.0328 |     0.0450 |    0.8116 | False            |   1.0000 |         1.0000 | False           | False                 |            12 |
| gpt-5.4-mini_few_shot                             | gpt-4o                                            | GPT-5.4-mini         | GPT-4o               | 0.7269 | 0.7237 |    0.0034 |    -0.0279 |     0.0351 |    0.8452 | False            |   1.0000 |         1.0000 | False           | False                 |            12 |

**Itens 47–48 — Resumo:**

| metric                         | value                            |
|:-------------------------------|:---------------------------------|
| resampling_unit                | document                         |
| n_docs_resampled               | 861                              |
| n_total_pairs                  | 91                               |
| n_significant_5pct_uncorrected | 54                               |
| highlighted_family_size        | 12                               |
| highlighted_n_sig_uncorrected  | 9                                |
| highlighted_n_sig_holm         | 8                                |
| highlighted_n_sig_bonferroni   | 7                                |
| smallest_significant_abs_diff  | 0.03636858879090947              |
| smallest_significant_pair      | GPT-5.4-nano vs Gemini-2.5-flash |

**p48a — Correção para múltiplas comparações.** A família reportada são os pares destacados acima; `p_holm`/`p_bonferroni` controlam o erro familiar (FWER) e `sig_holm_5pct` substitui a coluna 'Sig.' não corrigida da Tabela 13. Diferenças marginais tendem a não sobreviver, reforçando a leitura de saturação.

**Tabela completa dos 91 pares (ordenada por |Δ|):**

| model_a                                            | model_b                                            | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:---------------------------------------------------|:---------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| gpt-4-turbo                                        | gpt-41-nano                                        | GPT-4 Turbo          | GPT-4.1-nano         | 0.7321 | 0.4186 |    0.3139 |     0.2718 |     0.3577 |    0.0000 | True             |
| gpt-5.4-mini_few_shot                              | gpt-41-nano                                        | GPT-5.4-mini         | GPT-4.1-nano         | 0.7269 | 0.4186 |    0.3089 |     0.2635 |     0.3559 |    0.0000 | True             |
| gpt-4o                                             | gpt-41-nano                                        | GPT-4o               | GPT-4.1-nano         | 0.7237 | 0.4186 |    0.3055 |     0.2665 |     0.3462 |    0.0000 | True             |
| gpt-5.4-nano_few_shot                              | gpt-41-nano                                        | GPT-5.4-nano         | GPT-4.1-nano         | 0.7229 | 0.4186 |    0.3047 |     0.2609 |     0.3488 |    0.0000 | True             |
| gpt-41-mini                                        | gpt-41-nano                                        | GPT-4.1-mini         | GPT-4.1-nano         | 0.7108 | 0.4186 |    0.2925 |     0.2508 |     0.3364 |    0.0000 | True             |
| gpt-35                                             | gpt-41-nano                                        | GPT-3.5              | GPT-4.1-nano         | 0.7065 | 0.4186 |    0.2881 |     0.2450 |     0.3327 |    0.0000 | True             |
| gpt-41                                             | gpt-41-nano                                        | GPT-4.1              | GPT-4.1-nano         | 0.7052 | 0.4186 |    0.2868 |     0.2444 |     0.3301 |    0.0000 | True             |
| gemini-2.5-flash_few_shot                          | gpt-41-nano                                        | Gemini-2.5-flash     | GPT-4.1-nano         | 0.6867 | 0.4186 |    0.2683 |     0.2236 |     0.3132 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised  | gpt-41-nano                                        | BERTimbau-base       | GPT-4.1-nano         | 0.6786 | 0.4186 |    0.2598 |     0.2102 |     0.3086 |    0.0000 | True             |
| deepseek-v3_few_shot                               | gpt-41-nano                                        | DeepSeek-V3          | GPT-4.1-nano         | 0.6459 | 0.4186 |    0.2274 |     0.1843 |     0.2720 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | gpt-41-nano                                        | Legal-BERTimbau-base | GPT-4.1-nano         | 0.6021 | 0.4186 |    0.1831 |     0.1295 |     0.2354 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised | gpt-41-nano                                        | BERTimbau-large      | GPT-4.1-nano         | 0.6018 | 0.4186 |    0.1827 |     0.1252 |     0.2386 |    0.0000 | True             |
| bilstm-crf__supervised                             | gpt-41-nano                                        | BiLSTM-CRF           | GPT-4.1-nano         | 0.5926 | 0.4186 |    0.1740 |     0.1105 |     0.2370 |    0.0000 | True             |
| gpt-4-turbo                                        | bilstm-crf__supervised                             | GPT-4 Turbo          | BiLSTM-CRF           | 0.7321 | 0.5926 |    0.1399 |     0.0782 |     0.2018 |    0.0000 | True             |
| gpt-5.4-mini_few_shot                              | bilstm-crf__supervised                             | GPT-5.4-mini         | BiLSTM-CRF           | 0.7269 | 0.5926 |    0.1349 |     0.0682 |     0.2008 |    0.0002 | True             |
| gpt-4o                                             | bilstm-crf__supervised                             | GPT-4o               | BiLSTM-CRF           | 0.7237 | 0.5926 |    0.1315 |     0.0687 |     0.1930 |    0.0000 | True             |
| gpt-4-turbo                                        | neuralmind_bert-large-portuguese-cased__supervised | GPT-4 Turbo          | BERTimbau-large      | 0.7321 | 0.6018 |    0.1312 |     0.0759 |     0.1898 |    0.0000 | True             |
| gpt-4-turbo                                        | rufimelo_Legal-BERTimbau-base__supervised          | GPT-4 Turbo          | Legal-BERTimbau-base | 0.7321 | 0.6021 |    0.1308 |     0.0784 |     0.1848 |    0.0000 | True             |
| gpt-5.4-nano_few_shot                              | bilstm-crf__supervised                             | GPT-5.4-nano         | BiLSTM-CRF           | 0.7229 | 0.5926 |    0.1306 |     0.0665 |     0.1938 |    0.0000 | True             |
| gpt-5.4-mini_few_shot                              | neuralmind_bert-large-portuguese-cased__supervised | GPT-5.4-mini         | BERTimbau-large      | 0.7269 | 0.6018 |    0.1262 |     0.0647 |     0.1885 |    0.0002 | True             |
| gpt-5.4-mini_few_shot                              | rufimelo_Legal-BERTimbau-base__supervised          | GPT-5.4-mini         | Legal-BERTimbau-base | 0.7269 | 0.6021 |    0.1258 |     0.0709 |     0.1802 |    0.0000 | True             |
| gpt-4o                                             | neuralmind_bert-large-portuguese-cased__supervised | GPT-4o               | BERTimbau-large      | 0.7237 | 0.6018 |    0.1228 |     0.0692 |     0.1793 |    0.0000 | True             |
| gpt-4o                                             | rufimelo_Legal-BERTimbau-base__supervised          | GPT-4o               | Legal-BERTimbau-base | 0.7237 | 0.6021 |    0.1224 |     0.0708 |     0.1771 |    0.0000 | True             |
| gpt-5.4-nano_few_shot                              | neuralmind_bert-large-portuguese-cased__supervised | GPT-5.4-nano         | BERTimbau-large      | 0.7229 | 0.6018 |    0.1219 |     0.0682 |     0.1786 |    0.0000 | True             |
| gpt-5.4-nano_few_shot                              | rufimelo_Legal-BERTimbau-base__supervised          | GPT-5.4-nano         | Legal-BERTimbau-base | 0.7229 | 0.6021 |    0.1216 |     0.0708 |     0.1736 |    0.0000 | True             |
| gpt-41-mini                                        | bilstm-crf__supervised                             | GPT-4.1-mini         | BiLSTM-CRF           | 0.7108 | 0.5926 |    0.1184 |     0.0589 |     0.1784 |    0.0000 | True             |
| gpt-35                                             | bilstm-crf__supervised                             | GPT-3.5              | BiLSTM-CRF           | 0.7065 | 0.5926 |    0.1141 |     0.0490 |     0.1777 |    0.0006 | True             |
| gpt-41                                             | bilstm-crf__supervised                             | GPT-4.1              | BiLSTM-CRF           | 0.7052 | 0.5926 |    0.1128 |     0.0493 |     0.1754 |    0.0004 | True             |
| gpt-41-mini                                        | neuralmind_bert-large-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbau-large      | 0.7108 | 0.6018 |    0.1097 |     0.0589 |     0.1642 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | gpt-41-mini                                        | Legal-BERTimbau-base | GPT-4.1-mini         | 0.6021 | 0.7108 |   -0.1093 |    -0.1617 |    -0.0592 |    0.0000 | True             |
| gpt-35                                             | neuralmind_bert-large-portuguese-cased__supervised | GPT-3.5              | BERTimbau-large      | 0.7065 | 0.6018 |    0.1054 |     0.0494 |     0.1638 |    0.0002 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | gpt-35                                             | Legal-BERTimbau-base | GPT-3.5              | 0.6021 | 0.7065 |   -0.1050 |    -0.1594 |    -0.0517 |    0.0000 | True             |
| gpt-41                                             | neuralmind_bert-large-portuguese-cased__supervised | GPT-4.1              | BERTimbau-large      | 0.7052 | 0.6018 |    0.1041 |     0.0480 |     0.1634 |    0.0004 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | gpt-41                                             | Legal-BERTimbau-base | GPT-4.1              | 0.6021 | 0.7052 |   -0.1037 |    -0.1588 |    -0.0512 |    0.0002 | True             |
| gemini-2.5-flash_few_shot                          | bilstm-crf__supervised                             | Gemini-2.5-flash     | BiLSTM-CRF           | 0.6867 | 0.5926 |    0.0943 |     0.0307 |     0.1582 |    0.0032 | True             |
| gpt-4-turbo                                        | deepseek-v3_few_shot                               | GPT-4 Turbo          | DeepSeek-V3          | 0.7321 | 0.6459 |    0.0865 |     0.0515 |     0.1218 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised  | bilstm-crf__supervised                             | BERTimbau-base       | BiLSTM-CRF           | 0.6786 | 0.5926 |    0.0857 |     0.0304 |     0.1438 |    0.0020 | True             |
| neuralmind_bert-large-portuguese-cased__supervised | gemini-2.5-flash_few_shot                          | BERTimbau-large      | Gemini-2.5-flash     | 0.6018 | 0.6867 |   -0.0856 |    -0.1468 |    -0.0293 |    0.0026 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | gemini-2.5-flash_few_shot                          | Legal-BERTimbau-base | Gemini-2.5-flash     | 0.6021 | 0.6867 |   -0.0852 |    -0.1405 |    -0.0327 |    0.0012 | True             |
| gpt-5.4-mini_few_shot                              | deepseek-v3_few_shot                               | GPT-5.4-mini         | DeepSeek-V3          | 0.7269 | 0.6459 |    0.0815 |     0.0364 |     0.1249 |    0.0008 | True             |
| gpt-4o                                             | deepseek-v3_few_shot                               | GPT-4o               | DeepSeek-V3          | 0.7237 | 0.6459 |    0.0781 |     0.0421 |     0.1146 |    0.0000 | True             |
| gpt-5.4-nano_few_shot                              | deepseek-v3_few_shot                               | GPT-5.4-nano         | DeepSeek-V3          | 0.7229 | 0.6459 |    0.0773 |     0.0376 |     0.1168 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised  | neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-base       | BERTimbau-large      | 0.6786 | 0.6018 |    0.0770 |     0.0352 |     0.1214 |    0.0002 | True             |
| rufimelo_Legal-BERTimbau-base__supervised          | neuralmind_bert-base-portuguese-cased__supervised  | Legal-BERTimbau-base | BERTimbau-base       | 0.6021 | 0.6786 |   -0.0766 |    -0.1175 |    -0.0375 |    0.0002 | True             |
| gpt-41-mini                                        | deepseek-v3_few_shot                               | GPT-4.1-mini         | DeepSeek-V3          | 0.7108 | 0.6459 |    0.0650 |     0.0321 |     0.0976 |    0.0006 | True             |
| gpt-35                                             | deepseek-v3_few_shot                               | GPT-3.5              | DeepSeek-V3          | 0.7065 | 0.6459 |    0.0607 |     0.0192 |     0.1017 |    0.0044 | True             |
| gpt-41                                             | deepseek-v3_few_shot                               | GPT-4.1              | DeepSeek-V3          | 0.7052 | 0.6459 |    0.0594 |     0.0231 |     0.0955 |    0.0014 | True             |
| gpt-4-turbo                                        | neuralmind_bert-base-portuguese-cased__supervised  | GPT-4 Turbo          | BERTimbau-base       | 0.7321 | 0.6786 |    0.0541 |     0.0080 |     0.1021 |    0.0200 | True             |
| deepseek-v3_few_shot                               | bilstm-crf__supervised                             | DeepSeek-V3          | BiLSTM-CRF           | 0.6459 | 0.5926 |    0.0534 |    -0.0081 |     0.1152 |    0.0926 | False            |
| gpt-5.4-mini_few_shot                              | neuralmind_bert-base-portuguese-cased__supervised  | GPT-5.4-mini         | BERTimbau-base       | 0.7269 | 0.6786 |    0.0491 |    -0.0020 |     0.0997 |    0.0580 | False            |
| gpt-4o                                             | neuralmind_bert-base-portuguese-cased__supervised  | GPT-4o               | BERTimbau-base       | 0.7237 | 0.6786 |    0.0458 |     0.0010 |     0.0917 |    0.0442 | True             |
| gpt-4-turbo                                        | gemini-2.5-flash_few_shot                          | GPT-4 Turbo          | Gemini-2.5-flash     | 0.7321 | 0.6867 |    0.0456 |     0.0155 |     0.0749 |    0.0042 | True             |
| gpt-5.4-nano_few_shot                              | neuralmind_bert-base-portuguese-cased__supervised  | GPT-5.4-nano         | BERTimbau-base       | 0.7229 | 0.6786 |    0.0449 |     0.0002 |     0.0900 |    0.0492 | True             |
| neuralmind_bert-large-portuguese-cased__supervised | deepseek-v3_few_shot                               | BERTimbau-large      | DeepSeek-V3          | 0.6018 | 0.6459 |   -0.0447 |    -0.1034 |     0.0113 |    0.1204 | False            |
| rufimelo_Legal-BERTimbau-base__supervised          | deepseek-v3_few_shot                               | Legal-BERTimbau-base | DeepSeek-V3          | 0.6021 | 0.6459 |   -0.0443 |    -0.0985 |     0.0081 |    0.1022 | False            |
| gemini-2.5-flash_few_shot                          | deepseek-v3_few_shot                               | Gemini-2.5-flash     | DeepSeek-V3          | 0.6867 | 0.6459 |    0.0409 |     0.0053 |     0.0771 |    0.0218 | True             |
| gpt-5.4-mini_few_shot                              | gemini-2.5-flash_few_shot                          | GPT-5.4-mini         | Gemini-2.5-flash     | 0.7269 | 0.6867 |    0.0406 |    -0.0014 |     0.0808 |    0.0574 | False            |
| gpt-4o                                             | gemini-2.5-flash_few_shot                          | GPT-4o               | Gemini-2.5-flash     | 0.7237 | 0.6867 |    0.0372 |     0.0017 |     0.0701 |    0.0408 | True             |
| gpt-5.4-nano_few_shot                              | gemini-2.5-flash_few_shot                          | GPT-5.4-nano         | Gemini-2.5-flash     | 0.7229 | 0.6867 |    0.0364 |     0.0007 |     0.0698 |    0.0458 | True             |
| gpt-41-mini                                        | neuralmind_bert-base-portuguese-cased__supervised  | GPT-4.1-mini         | BERTimbau-base       | 0.7108 | 0.6786 |    0.0327 |    -0.0121 |     0.0781 |    0.1510 | False            |
| neuralmind_bert-base-portuguese-cased__supervised  | deepseek-v3_few_shot                               | BERTimbau-base       | DeepSeek-V3          | 0.6786 | 0.6459 |    0.0323 |    -0.0182 |     0.0828 |    0.2042 | False            |
| neuralmind_bert-base-portuguese-cased__supervised  | gpt-35                                             | BERTimbau-base       | GPT-3.5              | 0.6786 | 0.7065 |   -0.0284 |    -0.0751 |     0.0171 |    0.2252 | False            |
| gpt-4-turbo                                        | gpt-41                                             | GPT-4 Turbo          | GPT-4.1              | 0.7321 | 0.7052 |    0.0271 |    -0.0007 |     0.0555 |    0.0562 | False            |
| neuralmind_bert-base-portuguese-cased__supervised  | gpt-41                                             | BERTimbau-base       | GPT-4.1              | 0.6786 | 0.7052 |   -0.0270 |    -0.0741 |     0.0202 |    0.2640 | False            |
| gpt-4-turbo                                        | gpt-35                                             | GPT-4 Turbo          | GPT-3.5              | 0.7321 | 0.7065 |    0.0258 |    -0.0102 |     0.0627 |    0.1712 | False            |
| gpt-41-mini                                        | gemini-2.5-flash_few_shot                          | GPT-4.1-mini         | Gemini-2.5-flash     | 0.7108 | 0.6867 |    0.0242 |    -0.0094 |     0.0559 |    0.1562 | False            |
| gpt-5.4-mini_few_shot                              | gpt-41                                             | GPT-5.4-mini         | GPT-4.1              | 0.7269 | 0.7052 |    0.0221 |    -0.0177 |     0.0590 |    0.2686 | False            |
| gpt-4-turbo                                        | gpt-41-mini                                        | GPT-4 Turbo          | GPT-4.1-mini         | 0.7321 | 0.7108 |    0.0214 |    -0.0110 |     0.0547 |    0.1938 | False            |
| gpt-5.4-mini_few_shot                              | gpt-35                                             | GPT-5.4-mini         | GPT-3.5              | 0.7269 | 0.7065 |    0.0208 |    -0.0096 |     0.0543 |    0.1918 | False            |
| gpt-35                                             | gemini-2.5-flash_few_shot                          | GPT-3.5              | Gemini-2.5-flash     | 0.7065 | 0.6867 |    0.0198 |    -0.0192 |     0.0576 |    0.3122 | False            |
| gpt-4o                                             | gpt-41                                             | GPT-4o               | GPT-4.1              | 0.7237 | 0.7052 |    0.0187 |    -0.0147 |     0.0515 |    0.2724 | False            |
| gpt-41                                             | gemini-2.5-flash_few_shot                          | GPT-4.1              | Gemini-2.5-flash     | 0.7052 | 0.6867 |    0.0185 |    -0.0138 |     0.0500 |    0.2616 | False            |
| gpt-5.4-nano_few_shot                              | gpt-41                                             | GPT-5.4-nano         | GPT-4.1              | 0.7229 | 0.7052 |    0.0179 |    -0.0165 |     0.0523 |    0.3066 | False            |
| gpt-4o                                             | gpt-35                                             | GPT-4o               | GPT-3.5              | 0.7237 | 0.7065 |    0.0174 |    -0.0076 |     0.0434 |    0.1822 | False            |
| gpt-5.4-nano_few_shot                              | gpt-35                                             | GPT-5.4-nano         | GPT-3.5              | 0.7229 | 0.7065 |    0.0165 |    -0.0102 |     0.0437 |    0.2284 | False            |
| gpt-5.4-mini_few_shot                              | gpt-41-mini                                        | GPT-5.4-mini         | GPT-4.1-mini         | 0.7269 | 0.7108 |    0.0164 |    -0.0261 |     0.0576 |    0.4304 | False            |
| gpt-4o                                             | gpt-41-mini                                        | GPT-4o               | GPT-4.1-mini         | 0.7237 | 0.7108 |    0.0131 |    -0.0206 |     0.0468 |    0.4470 | False            |
| gpt-5.4-nano_few_shot                              | gpt-41-mini                                        | GPT-5.4-nano         | GPT-4.1-mini         | 0.7229 | 0.7108 |    0.0122 |    -0.0221 |     0.0469 |    0.4808 | False            |
| gpt-4-turbo                                        | gpt-5.4-nano_few_shot                              | GPT-4 Turbo          | GPT-5.4-nano         | 0.7321 | 0.7229 |    0.0092 |    -0.0201 |     0.0405 |    0.5636 | False            |
| rufimelo_Legal-BERTimbau-base__supervised          | bilstm-crf__supervised                             | Legal-BERTimbau-base | BiLSTM-CRF           | 0.6021 | 0.5926 |    0.0091 |    -0.0485 |     0.0673 |    0.7680 | False            |
| neuralmind_bert-large-portuguese-cased__supervised | bilstm-crf__supervised                             | BERTimbau-large      | BiLSTM-CRF           | 0.6018 | 0.5926 |    0.0087 |    -0.0493 |     0.0671 |    0.7856 | False            |
| neuralmind_bert-base-portuguese-cased__supervised  | gemini-2.5-flash_few_shot                          | BERTimbau-base       | Gemini-2.5-flash     | 0.6786 | 0.6867 |   -0.0086 |    -0.0601 |     0.0416 |    0.7496 | False            |
| gpt-4-turbo                                        | gpt-4o                                             | GPT-4 Turbo          | GPT-4o               | 0.7321 | 0.7237 |    0.0084 |    -0.0231 |     0.0415 |    0.6130 | False            |
| gpt-41-mini                                        | gpt-41                                             | GPT-4.1-mini         | GPT-4.1              | 0.7108 | 0.7052 |    0.0057 |    -0.0262 |     0.0374 |    0.7304 | False            |
| gpt-4-turbo                                        | gpt-5.4-mini_few_shot                              | GPT-4 Turbo          | GPT-5.4-mini         | 0.7321 | 0.7269 |    0.0050 |    -0.0328 |     0.0450 |    0.8116 | False            |
| gpt-41-mini                                        | gpt-35                                             | GPT-4.1-mini         | GPT-3.5              | 0.7108 | 0.7065 |    0.0043 |    -0.0305 |     0.0381 |    0.8024 | False            |
| gpt-5.4-mini_few_shot                              | gpt-5.4-nano_few_shot                              | GPT-5.4-mini         | GPT-5.4-nano         | 0.7269 | 0.7229 |    0.0042 |    -0.0225 |     0.0327 |    0.7732 | False            |
| gpt-5.4-mini_few_shot                              | gpt-4o                                             | GPT-5.4-mini         | GPT-4o               | 0.7269 | 0.7237 |    0.0034 |    -0.0279 |     0.0351 |    0.8452 | False            |
| gpt-35                                             | gpt-41                                             | GPT-3.5              | GPT-4.1              | 0.7065 | 0.7052 |    0.0013 |    -0.0319 |     0.0346 |    0.9376 | False            |
| gpt-4o                                             | gpt-5.4-nano_few_shot                              | GPT-4o               | GPT-5.4-nano         | 0.7237 | 0.7229 |    0.0008 |    -0.0244 |     0.0266 |    0.9524 | False            |
| rufimelo_Legal-BERTimbau-base__supervised          | neuralmind_bert-large-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbau-large      | 0.6021 | 0.6018 |    0.0004 |    -0.0401 |     0.0430 |    0.9960 | False            |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.7143 | 0.6786 | 0.6511 |  0.5962 |
| BERTimbau-large      | 0.6170 | 0.6018 | 0.5866 |  0.5410 |
| BiLSTM-CRF           | 0.6365 | 0.5926 | 0.5405 |  0.4280 |
| DeepSeek-V3          | 0.6856 | 0.6459 | 0.5911 |  0.0793 |
| GPT-3.5              | 0.7502 | 0.7065 | 0.6488 |  0.1075 |
| GPT-4 Turbo          | 0.7698 | 0.7321 | 0.6567 |  0.1052 |
| GPT-4.1              | 0.7437 | 0.7052 | 0.6551 |  0.1272 |
| GPT-4.1-mini         | 0.7483 | 0.7108 | 0.6338 |  0.0849 |
| GPT-4.1-nano         | 0.4627 | 0.4186 | 0.3475 |  0.0593 |
| GPT-4o               | 0.7594 | 0.7237 | 0.6640 |  0.0915 |
| GPT-5.4-mini         | 0.7574 | 0.7269 | 0.6660 |  0.1096 |
| GPT-5.4-nano         | 0.7590 | 0.7229 | 0.6647 |  0.1205 |
| Gemini-2.5-flash     | 0.7177 | 0.6867 | 0.6421 |  0.1222 |
| Legal-BERTimbau-base | 0.6112 | 0.6021 | 0.5779 |  0.5083 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5):

| iou_threshold   |   spearman_vs_0.5 |
|:----------------|------------------:|
| 0.3             |            0.9648 |
| 0.5             |            1.0000 |
| 0.7             |            0.8989 |
| exact           |           -0.2615 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                              | display              |   n_docs_full |   n_docs_informative |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:---------------------------------------------------|:---------------------|--------------:|---------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| gpt-41                                             | GPT-4.1              |           861 |                  232 |         0.7052 |                0.7896 |          0.0844 |                0.6321 |                       0.7821 |                 0.1499 |             0.7974 |                    0.7974 |
| gpt-4-turbo                                        | GPT-4 Turbo          |           861 |                  232 |         0.7321 |                0.7893 |          0.0572 |                0.6721 |                       0.7752 |                 0.1031 |             0.8039 |                    0.8039 |
| gpt-4o                                             | GPT-4o               |           861 |                  232 |         0.7237 |                0.7778 |          0.0541 |                0.6654 |                       0.7631 |                 0.0977 |             0.7930 |                    0.7930 |
| gpt-5.4-mini_few_shot                              | GPT-5.4-mini         |           861 |                  232 |         0.7269 |                0.7741 |          0.0472 |                0.6806 |                       0.7682 |                 0.0876 |             0.7800 |                    0.7800 |
| gpt-5.4-nano_few_shot                              | GPT-5.4-nano         |           861 |                  232 |         0.7229 |                0.7734 |          0.0505 |                0.6704 |                       0.7627 |                 0.0923 |             0.7843 |                    0.7843 |
| gpt-41-mini                                        | GPT-4.1-mini         |           861 |                  232 |         0.7108 |                0.7643 |          0.0536 |                0.6498 |                       0.7453 |                 0.0955 |             0.7843 |                    0.7843 |
| gpt-35                                             | GPT-3.5              |           861 |                  232 |         0.7065 |                0.7610 |          0.0545 |                0.6502 |                       0.7489 |                 0.0988 |             0.7734 |                    0.7734 |
| gemini-2.5-flash_few_shot                          | Gemini-2.5-flash     |           861 |                  232 |         0.6867 |                0.7329 |          0.0462 |                0.6189 |                       0.6982 |                 0.0793 |             0.7712 |                    0.7712 |
| deepseek-v3_few_shot                               | DeepSeek-V3          |           861 |                  232 |         0.6459 |                0.7177 |          0.0718 |                0.5700 |                       0.6923 |                 0.1223 |             0.7451 |                    0.7451 |
| neuralmind_bert-base-portuguese-cased__supervised  | BERTimbau-base       |           861 |                  232 |         0.6786 |                0.6890 |          0.0104 |                0.7994 |                       0.8289 |                 0.0295 |             0.5895 |                    0.5895 |
| rufimelo_Legal-BERTimbau-base__supervised          | Legal-BERTimbau-base |           861 |                  232 |         0.6021 |                0.6123 |          0.0102 |                0.8223 |                       0.8615 |                 0.0392 |             0.4749 |                    0.4749 |
| neuralmind_bert-large-portuguese-cased__supervised | BERTimbau-large      |           861 |                  232 |         0.6018 |                0.6111 |          0.0093 |                0.8285 |                       0.8646 |                 0.0362 |             0.4726 |                    0.4726 |
| bilstm-crf__supervised                             | BiLSTM-CRF           |           861 |                  232 |         0.5926 |                0.6076 |          0.0150 |                0.7742 |                       0.8276 |                 0.0534 |             0.4800 |                    0.4800 |
| gpt-41-nano                                        | GPT-4.1-nano         |           861 |                  232 |         0.4186 |                0.4764 |          0.0577 |                0.3426 |                       0.4273 |                 0.0848 |             0.5381 |                    0.5381 |

## M. Taxa de falha de alinhamento string→offset (p34)

As predições dos LLMs são strings (não offsets); são localizadas no texto-fonte por correspondência difusa (rapidfuzz `partial_ratio`, janela 500 / passo 100 / `min_score` 80). Strings que nenhuma janela casa nesse piso são descartadas silenciosamente na pontuação — a taxa de falha abaixo quantifica quantas predições nunca chegam à métrica:

| model                     | display          |   n_pred_strings |   n_aligned |   n_failed |   failure_rate |
|:--------------------------|:-----------------|-----------------:|------------:|-----------:|---------------:|
| gpt-41-nano               | GPT-4.1-nano     |              753 |         721 |         32 |         0.0425 |
| gpt-41-mini               | GPT-4.1-mini     |              562 |         554 |          8 |         0.0142 |
| gpt-4o                    | GPT-4o           |              554 |         547 |          7 |         0.0126 |
| gpt-5.4-nano_few_shot     | GPT-5.4-nano     |              539 |         537 |          2 |         0.0037 |
| gpt-4-turbo               | GPT-4 Turbo      |              551 |         549 |          2 |         0.0036 |
| gpt-5.4-mini_few_shot     | GPT-5.4-mini     |              527 |         526 |          1 |         0.0019 |
| deepseek-v3_few_shot      | DeepSeek-V3      |              601 |         600 |          1 |         0.0017 |
| gpt-35                    | GPT-3.5          |              546 |         546 |          0 |         0.0000 |
| gpt-41                    | GPT-4.1          |              579 |         579 |          0 |         0.0000 |
| gemini-2.5-flash_few_shot | Gemini-2.5-flash |              572 |         572 |          0 |         0.0000 |

## Nota — Token F1 do GPT-4-turbo (canônico)

Valor canônico após correção: **0.8096** (reportar como `0,8096` ou 80.96\% conforme convenção da seção).
