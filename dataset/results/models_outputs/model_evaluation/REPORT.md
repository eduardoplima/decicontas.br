# Avaliação de modelos — números reproduzíveis (gold corrigido)

Documento auto-contido: todas as tabelas aparecem inline. Os CSVs ao lado deste arquivo são as fontes canônicas (uma por bloco), geradas por `research.release.evaluation_numbers`. Cada bloco abaixo corresponde a um bloco da avaliação.

## Pipeline de métricas (correções aplicadas)

Esta versão dos números incorpora quatro correções no pipeline de avaliação:

1. **Matching pred↔gold bipartido por IoU descendente** (`research.ner_metrics.bipartite_greedy_match`). Cada predição casa com no máximo um gold e vice-versa, eliminando a divergência anterior entre `calculate_metrics` (que tinha `break` após o primeiro match) e o bootstrap (que contava todos os pares sobrepostos). Esta única função é agora a fonte para `calculate_metrics`, `evaluate_bio_results` e `compute_doc_level_counts` — `matched ≤ min(|pred|, |gold|)` por construção, e P/R sempre em [0, 1].

2. **Unidade única de span: índices de token.** Todas as predições, generativas e BIO, são convertidas para spans em índices de token sobre a tokenização canônica `\S+` de `research.dataset_io` antes do emparelhamento, e o gold é convertido junto. A relocalização difusa das strings emitidas pelos LLMs permanece; o que mudou é a unidade em que se pontua. O spaCy saiu do caminho de métricas: o token F1 era calculado sobre `pt_core_news_sm` no caminho generativo e sobre a tokenização canônica no caminho BIO. O efeito maior aparece na correspondência exata, que antes media se a borda direita estimada pelo modelo caía por acaso em fronteira de token.

3. **Gold supervisionado não truncado.** O gold dos supervisionados vinha do próprio `true_labels` do modelo, cortado no limite de subwords do encoder. Entre 7 e 29 documentos por modelo perdiam a cauda, e as entidades além do corte sumiam do denominador — 40 delas no BERTimbau-base — enquanto os LLMs eram avaliados contra o gold inteiro. Agora todos são pontuados contra o gold canônico completo, e o que o encoder não pôde ver conta como perda de revocação.

4. **Gold canônico íntegro.** As decisões `reject` do cleanlab deixaram de ser aplicadas (um `reject` é, por definição, operação nula) e o BIO passou a ser re-derivado dos spans reconstruídos. Antes disso o release publicava 459 entidades no campo `entities` e apenas 442 sob IOB2 estrito em `ner_tags`, e trazia fragmentos espúrios de até um caractere.

## A. Caracterização do corpus

| metric              |   before |   after |   delta |
|:--------------------|---------:|--------:|--------:|
| total_docs          |      861 |     861 |       0 |
| docs_with_entity    |      229 |     231 |       2 |
| docs_without_entity |      632 |     630 |      -2 |
| total_entities      |      439 |     441 |       2 |
| MULTA               |      202 |     203 |       1 |
| OBRIGACAO           |      119 |     123 |       4 |
| RECOMENDACAO        |       56 |      52 |      -4 |
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
| MULTA         |      202 |     203 |       1 |
| OBRIGACAO     |      119 |     123 |       4 |
| RECOMENDACAO  |       56 |      52 |      -4 |
| RESSARCIMENTO |       62 |      63 |       1 |

**Matriz de transições rótulo observado × rótulo sugerido** (população: os tokens sinalizados pelo ensemble em `erros_anotacao_decicontas.csv` — a lista de trabalho da revisão):

| label_original   |   B-OBRIGACAO |   B-RECOMENDACAO |   I-MULTA |   I-OBRIGACAO |   I-RECOMENDACAO |   I-RESSARCIMENTO |   O |
|:-----------------|--------------:|-----------------:|----------:|--------------:|-----------------:|------------------:|----:|
| B-MULTA          |             3 |                4 |         6 |             2 |                0 |                 0 |   5 |
| B-OBRIGACAO      |             0 |                4 |         0 |            25 |                0 |                 0 |   3 |
| B-RECOMENDACAO   |             0 |                0 |         0 |             0 |               22 |                 0 |   5 |
| B-RESSARCIMENTO  |             0 |                0 |         0 |             0 |                0 |                35 |   1 |
| I-MULTA          |           192 |              164 |         0 |            72 |                6 |               105 | 108 |
| I-OBRIGACAO      |           219 |              241 |        23 |             0 |                7 |                51 | 213 |
| I-RECOMENDACAO   |            45 |               42 |         0 |            58 |                0 |                 0 |  77 |
| I-RESSARCIMENTO  |            39 |               27 |        54 |            28 |                0 |                 0 | 132 |
| O                |           417 |              412 |       387 |           640 |              547 |               229 |   0 |

## C. Resultados gerais (modelos × métricas)

| model                                                  | display              |   token_f1 |   token_f1_macro |   token_precision |   token_recall |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:-------------------------------------------------------|:---------------------|-----------:|-----------------:|------------------:|---------------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |     0.8335 |           0.7961 |            0.8336 |         0.8334 |    0.7696 |          0.7423 |           0.7390 |        0.8027 |
| gpt-4.1_few_shot                                       | GPT-4.1              |     0.8167 |           0.7902 |            0.7840 |         0.8522 |    0.7365 |          0.7170 |           0.6578 |        0.8367 |
| gpt-5.1_few_shot                                       | GPT-5.1              |     0.7817 |           0.7549 |            0.7420 |         0.8259 |    0.7046 |          0.6910 |           0.6211 |        0.8141 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |     0.7937 |           0.7639 |            0.7445 |         0.8499 |    0.6986 |          0.6837 |           0.5962 |        0.8435 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.7434 |           0.6506 |            0.9323 |         0.6181 |    0.6809 |          0.6189 |           0.7634 |        0.6145 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.7145 |           0.6303 |            0.9440 |         0.5747 |    0.6649 |          0.6045 |           0.7701 |        0.5850 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.7137 |           0.5935 |            0.9510 |         0.5712 |    0.6640 |          0.5692 |           0.8058 |        0.5646 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.7073 |           0.5508 |            0.9243 |         0.5728 |    0.6504 |          0.5320 |           0.7507 |        0.5737 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.6744 |           0.5648 |            0.9440 |         0.5246 |    0.6281 |          0.5619 |           0.7469 |        0.5420 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7177 |           0.6752 |            0.7026 |         0.7334 |    0.6243 |          0.5853 |           0.5491 |        0.7234 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.7515 |           0.7207 |            0.6901 |         0.8250 |    0.6198 |          0.5945 |           0.5057 |        0.8005 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.7079 |           0.5542 |            0.8438 |         0.6096 |    0.6028 |          0.5085 |           0.7778 |        0.4921 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.6286 |           0.3942 |            0.9467 |         0.4705 |    0.5798 |          0.3922 |           0.8182 |        0.4490 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.6286 |           0.4759 |            0.9585 |         0.4676 |    0.5794 |          0.4615 |           0.8243 |        0.4467 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.5422 |           0.4054 |            0.9700 |         0.3762 |    0.5213 |          0.4113 |           0.8594 |        0.3741 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.5226 |           0.3328 |            0.9718 |         0.3574 |    0.4781 |          0.3303 |           0.7182 |        0.3583 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.5809 |           0.5079 |            0.5644 |         0.5984 |    0.4341 |          0.3953 |           0.3544 |        0.5601 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.5694 |           0.6332 |            0.4274 |         0.8526 |    0.4162 |          0.5310 |           0.2780 |        0.8277 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4090 |           0.3009 |            0.7560 |         0.2804 |    0.3558 |          0.2856 |           0.6066 |        0.2517 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                                  | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                         |
|:-------------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:-----------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                                 | BiLSTM-CRF           |         0.6027 |        0.0947 |        0.5042 |        0.7538 | 0.5739; 0.6243; 0.5574; 0.7538; 0.5042 |          0.6958 |         0.1203 |         0.4842 |         0.7783 | 0.7271; 0.7608; 0.7286; 0.7783; 0.4842 | {"hidden_dim": 256, "dropout": 0.3, "lr": 0.003}                                               |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |         0.6659 |        0.0261 |        0.6316 |        0.7040 | 0.7040; 0.6700; 0.6316; 0.6667; 0.6575 |          0.7104 |         0.0610 |         0.6473 |         0.7895 | 0.7597; 0.7895; 0.6473; 0.6704; 0.6853 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1}      |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |         0.5551 |        0.1654 |        0.2892 |        0.6964 | 0.2892; 0.6813; 0.5166; 0.6964; 0.5921 |          0.5984 |         0.1748 |         0.3215 |         0.7625 | 0.3215; 0.7625; 0.5392; 0.6980; 0.6706 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 2e-05, "warmup_ratio": 0.1}     |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |         0.5711 |        0.1470 |        0.3600 |        0.7563 | 0.3600; 0.6364; 0.5161; 0.7563; 0.5865 |          0.6106 |         0.1434 |         0.3919 |         0.7657 | 0.3919; 0.7042; 0.5719; 0.7657; 0.6194 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.1}              |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |         0.6326 |        0.0667 |        0.5650 |        0.7419 | 0.6066; 0.6396; 0.5650; 0.7419; 0.6099 |          0.6696 |         0.0646 |         0.6000 |         0.7511 | 0.6318; 0.7511; 0.6000; 0.7241; 0.6410 | {"model_name": "alfaneo/jurisbert-base-portuguese-uncased", "lr": 3e-05, "warmup_ratio": 0.1}  |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |         0.6640 |        0.0743 |        0.5812 |        0.7820 | 0.5812; 0.6768; 0.6437; 0.7820; 0.6364 |          0.7091 |         0.0627 |         0.6338 |         0.7809 | 0.6338; 0.7620; 0.6635; 0.7809; 0.7054 | {"model_name": "alfaneo/bertimbaulaw-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1} |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |         0.6857 |        0.0436 |        0.6220 |        0.7368 | 0.7068; 0.6667; 0.6961; 0.7368; 0.6220 |          0.7423 |         0.0370 |         0.6907 |         0.7797 | 0.7772; 0.7797; 0.7313; 0.7328; 0.6907 | {"model_name": "raquelsilveira/legalbertpt_fp", "lr": 5e-05, "warmup_ratio": 0.0}              |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |         0.4145 |        0.2416 |        0.0000 |        0.6337 | 0.4554; 0.6337; 0.4872; 0.0000; 0.4962 |          0.4638 |         0.2749 |         0.0000 |         0.7344 | 0.4966; 0.7344; 0.5455; 0.0000; 0.5427 | {"model_name": "ulysses-camara/legal-bert-pt-br", "lr": 5e-05, "warmup_ratio": 0.0}            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |         0.6561 |        0.0703 |        0.5683 |        0.7647 | 0.6573; 0.6484; 0.5683; 0.7647; 0.6418 |          0.7082 |         0.0590 |         0.6343 |         0.7655 | 0.7655; 0.7363; 0.6559; 0.7491; 0.6343 | {"model_name": "dominguesm/legal-bert-base-cased-ptbr", "lr": 5e-05, "warmup_ratio": 0.1}      |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |         0.4826 |        0.1642 |        0.2750 |        0.6667 | 0.3636; 0.6667; 0.4967; 0.2750; 0.6111 |          0.5055 |         0.1789 |         0.2621 |         0.6914 | 0.3877; 0.6914; 0.5436; 0.2621; 0.6427 | {"model_name": "dccmpmgfinalisticas/GovBERT-BR", "lr": 5e-05, "warmup_ratio": 0.0}             |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.6949 |                0.1438 |                0.4090 |                0.8335 |                0.5955 |               0.1540 |               0.3558 |               0.7696 |
| supervised         |                 0.6583 |                0.0762 |                0.5226 |                0.7434 |                0.6050 |               0.0665 |               0.4781 |               0.6809 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.7639 |      0.6564 |         0.3030 |          0.5536 |
| BERTimbau-large      |  0.6864 |      0.6283 |         0.1905 |          0.3409 |
| BERTimbauLaw         |  0.7374 |      0.6633 |         0.3902 |          0.6271 |
| BiLSTM-CRF           |  0.6628 |      0.7081 |         0.2500 |          0.4130 |
| DeepSeek-V4-Flash    |  0.8434 |      0.7154 |         0.6667 |          0.7438 |
| GPT-4.1              |  0.8098 |      0.6547 |         0.6667 |          0.7368 |
| GPT-4.1-mini         |  0.7930 |      0.5886 |         0.6345 |          0.7188 |
| GPT-4.1-nano         |  0.6854 |      0.2864 |         0.1023 |          0.5072 |
| GPT-5-mini           |  0.7036 |      0.2249 |         0.5897 |          0.6056 |
| GPT-5.1              |  0.7846 |      0.6053 |         0.6429 |          0.7313 |
| GPT-5.2              |  0.7553 |      0.4895 |         0.5294 |          0.6040 |
| GovBERT-BR           |  0.5752 |      0.6087 |         0.0000 |          0.4615 |
| JurisBERT            |  0.6684 |      0.6455 |         0.2286 |          0.7049 |
| Legal-BERT-STF       |  0.7532 |      0.6832 |         0.1875 |          0.5042 |
| Legal-BERTimbau-base |  0.7253 |      0.6067 |         0.0678 |          0.1690 |
| LegalBERTPT-br       |  0.5831 |      0.5269 |         0.0741 |          0.1370 |
| LegalBert-pt         |  0.7592 |      0.6698 |         0.4250 |          0.6218 |
| Llama-3.3-70B        |  0.4214 |      0.3939 |         0.2963 |          0.0308 |
| Qwen2.5-72B          |  0.7731 |      0.5188 |         0.3727 |          0.6765 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                                  | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:-------------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4.1_few_shot                                       | GPT-4.1              | MULTA         |      0.7418 |   0.8916 | 0.8098 |       181 |          203 |          244 |
| gpt-4.1_few_shot                                       | GPT-4.1              | OBRIGACAO     |      0.5871 |   0.7398 | 0.6547 |        91 |          123 |          155 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RECOMENDACAO  |      0.5217 |   0.9231 | 0.6667 |        48 |           52 |           92 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RESSARCIMENTO |      0.7000 |   0.7778 | 0.7368 |        49 |           63 |           70 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | MULTA         |      0.7109 |   0.8966 | 0.7930 |       182 |          203 |          256 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | OBRIGACAO     |      0.4667 |   0.7967 | 0.5886 |        98 |          123 |          210 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RECOMENDACAO  |      0.4946 |   0.8846 | 0.6345 |        46 |           52 |           93 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RESSARCIMENTO |      0.7077 |   0.7302 | 0.7188 |        46 |           63 |           65 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | MULTA         |      0.6547 |   0.7192 | 0.6854 |       146 |          203 |          223 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | OBRIGACAO     |      0.2073 |   0.4634 | 0.2864 |        57 |          123 |          275 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RECOMENDACAO  |      0.0726 |   0.1731 | 0.1023 |         9 |           52 |          124 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RESSARCIMENTO |      0.4667 |   0.5556 | 0.5072 |        35 |           63 |           75 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | MULTA         |      0.6203 |   0.8128 | 0.7036 |       165 |          203 |          266 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | OBRIGACAO     |      0.1285 |   0.9024 | 0.2249 |       111 |          123 |          864 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RECOMENDACAO  |      0.4423 |   0.8846 | 0.5897 |        46 |           52 |          104 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RESSARCIMENTO |      0.5443 |   0.6825 | 0.6056 |        43 |           63 |           79 |
| gpt-5.1_few_shot                                       | GPT-5.1              | MULTA         |      0.7269 |   0.8522 | 0.7846 |       173 |          203 |          238 |
| gpt-5.1_few_shot                                       | GPT-5.1              | OBRIGACAO     |      0.5083 |   0.7480 | 0.6053 |        92 |          123 |          181 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RECOMENDACAO  |      0.5114 |   0.8654 | 0.6429 |        45 |           52 |           88 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RESSARCIMENTO |      0.6901 |   0.7778 | 0.7313 |        49 |           63 |           71 |
| gpt-5.2_few_shot                                       | GPT-5.2              | MULTA         |      0.6605 |   0.8818 | 0.7553 |       179 |          203 |          271 |
| gpt-5.2_few_shot                                       | GPT-5.2              | OBRIGACAO     |      0.3619 |   0.7561 | 0.4895 |        93 |          123 |          257 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RECOMENDACAO  |      0.4286 |   0.6923 | 0.5294 |        36 |           52 |           84 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RESSARCIMENTO |      0.5233 |   0.7143 | 0.6040 |        45 |           63 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | MULTA         |      0.8255 |   0.8621 | 0.8434 |       175 |          203 |          212 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | OBRIGACAO     |      0.7154 |   0.7154 | 0.7154 |        88 |          123 |          123 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RECOMENDACAO  |      0.5349 |   0.8846 | 0.6667 |        46 |           52 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RESSARCIMENTO |      0.7759 |   0.7143 | 0.7438 |        45 |           63 |           58 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | MULTA         |      0.7662 |   0.2906 | 0.4214 |        59 |          203 |           77 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | OBRIGACAO     |      0.5200 |   0.3171 | 0.3939 |        39 |          123 |           75 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RECOMENDACAO  |      0.4138 |   0.2308 | 0.2963 |        12 |           52 |           29 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RESSARCIMENTO |      0.5000 |   0.0159 | 0.0308 |         1 |           63 |            2 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | MULTA         |      0.7293 |   0.8227 | 0.7731 |       167 |          203 |          229 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | OBRIGACAO     |      0.4471 |   0.6179 | 0.5188 |        76 |          123 |          170 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RECOMENDACAO  |      0.2752 |   0.5769 | 0.3727 |        30 |           52 |          109 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RESSARCIMENTO |      0.6301 |   0.7302 | 0.6765 |        46 |           63 |           73 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | MULTA         |      0.7907 |   0.6700 | 0.7253 |       136 |          203 |          172 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | OBRIGACAO     |      0.9818 |   0.4390 | 0.6067 |        54 |          123 |           55 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RECOMENDACAO  |      0.2857 |   0.0385 | 0.0678 |         2 |           52 |            7 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RESSARCIMENTO |      0.7500 |   0.0952 | 0.1690 |         6 |           63 |            8 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | MULTA         |      0.8276 |   0.7094 | 0.7639 |       144 |          203 |          174 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | OBRIGACAO     |      0.8889 |   0.5203 | 0.6564 |        64 |          123 |           72 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RECOMENDACAO  |      0.7143 |   0.1923 | 0.3030 |        10 |           52 |           14 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RESSARCIMENTO |      0.6327 |   0.4921 | 0.5536 |        31 |           63 |           49 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | MULTA         |      0.8593 |   0.5714 | 0.6864 |       116 |          203 |          135 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | OBRIGACAO     |      0.8824 |   0.4878 | 0.6283 |        60 |          123 |           68 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RECOMENDACAO  |      0.5455 |   0.1154 | 0.1905 |         6 |           52 |           11 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RESSARCIMENTO |      0.6000 |   0.2381 | 0.3409 |        15 |           63 |           25 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | MULTA         |      0.7986 |   0.5665 | 0.6628 |       115 |          203 |          144 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | OBRIGACAO     |      0.8605 |   0.6016 | 0.7081 |        74 |          123 |           86 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RECOMENDACAO  |      0.4500 |   0.1731 | 0.2500 |         9 |           52 |           20 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RESSARCIMENTO |      0.6552 |   0.3016 | 0.4130 |        19 |           63 |           29 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | MULTA         |      0.7175 |   0.6256 | 0.6684 |       127 |          203 |          177 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | OBRIGACAO     |      0.9242 |   0.4959 | 0.6455 |        61 |          123 |           66 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RECOMENDACAO  |      0.4444 |   0.1538 | 0.2286 |         8 |           52 |           18 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RESSARCIMENTO |      0.7288 |   0.6825 | 0.7049 |        43 |           63 |           59 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | MULTA         |      0.7989 |   0.6847 | 0.7374 |       139 |          203 |          174 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | OBRIGACAO     |      0.8684 |   0.5366 | 0.6633 |        66 |          123 |           76 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RECOMENDACAO  |      0.5333 |   0.3077 | 0.3902 |        16 |           52 |           30 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RESSARCIMENTO |      0.6727 |   0.5873 | 0.6271 |        37 |           63 |           55 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | MULTA         |      0.8101 |   0.7143 | 0.7592 |       145 |          203 |          179 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | OBRIGACAO     |      0.7826 |   0.5854 | 0.6698 |        72 |          123 |           92 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RECOMENDACAO  |      0.6071 |   0.3269 | 0.4250 |        17 |           52 |           28 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RESSARCIMENTO |      0.6607 |   0.5873 | 0.6218 |        37 |           63 |           56 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | MULTA         |      0.6524 |   0.5271 | 0.5831 |       107 |          203 |          164 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | OBRIGACAO     |      1.0000 |   0.3577 | 0.5269 |        44 |          123 |           44 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RECOMENDACAO  |      1.0000 |   0.0385 | 0.0741 |         2 |           52 |            2 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RESSARCIMENTO |      0.5000 |   0.0794 | 0.1370 |         5 |           63 |           10 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | MULTA         |      0.7789 |   0.7291 | 0.7532 |       148 |          203 |          190 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | OBRIGACAO     |      0.8734 |   0.5610 | 0.6832 |        69 |          123 |           79 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RECOMENDACAO  |      0.5000 |   0.1154 | 0.1875 |         6 |           52 |           12 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RESSARCIMENTO |      0.5357 |   0.4762 | 0.5042 |        30 |           63 |           56 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | MULTA         |      0.8544 |   0.4335 | 0.5752 |        88 |          203 |          103 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | OBRIGACAO     |      0.9180 |   0.4553 | 0.6087 |        56 |          123 |           61 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           52 |            0 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RESSARCIMENTO |      0.7500 |   0.3333 | 0.4615 |        21 |           63 |           28 |

## E. Custo-benefício

Os JSONs de predição não armazenam contagens de tokens da API; o template abaixo reporta caracteres médios e estimativa aproximada de tokens (≈ 4 chars/token), com colunas em branco para as tarifas USD/1M de cada provedor — preencher manualmente consultando o histórico de billing.

| model                      | display           |   n_docs |   mean_input_chars |   mean_output_chars |   approx_mean_input_tokens |   approx_mean_output_tokens |   total_input_chars |   total_output_chars |   input_cost_per_1M_USD |   output_cost_per_1M_USD |   estimated_total_cost_USD |
|:---------------------------|:------------------|---------:|-------------------:|--------------------:|---------------------------:|----------------------------:|--------------------:|---------------------:|------------------------:|-------------------------:|---------------------------:|
| gpt-4.1_few_shot           | GPT-4.1           |      861 |           875.6760 |            297.6911 |                   218.9190 |                     74.4228 |              753957 |               256312 |                     nan |                      nan |                        nan |
| gpt-4.1-mini_few_shot      | GPT-4.1-mini      |      861 |           875.6760 |            304.5436 |                   218.9190 |                     76.1359 |              753957 |               262212 |                     nan |                      nan |                        nan |
| gpt-4.1-nano_few_shot      | GPT-4.1-nano      |      861 |           875.6760 |            307.9501 |                   218.9190 |                     76.9875 |              753957 |               265145 |                     nan |                      nan |                        nan |
| gpt-5-mini_few_shot        | GPT-5-mini        |      861 |           875.6760 |            509.2195 |                   218.9190 |                    127.3049 |              753957 |               438438 |                     nan |                      nan |                        nan |
| gpt-5.1_few_shot           | GPT-5.1           |      861 |           875.6760 |            296.4111 |                   218.9190 |                     74.1028 |              753957 |               255210 |                     nan |                      nan |                        nan |
| gpt-5.2_few_shot           | GPT-5.2           |      861 |           875.6760 |            326.8026 |                   218.9190 |                     81.7006 |              753957 |               281377 |                     nan |                      nan |                        nan |
| deepseek-v4-flash_few_shot | DeepSeek-V4-Flash |      861 |           875.6760 |            274.0755 |                   218.9190 |                     68.5189 |              753957 |               235979 |                     nan |                      nan |                        nan |
| llama-3.3-70b_few_shot     | Llama-3.3-70B     |      861 |           875.6760 |            150.4925 |                   218.9190 |                     37.6231 |              753957 |               129574 |                     nan |                      nan |                        nan |
| qwen2.5-72b_few_shot       | Qwen2.5-72B       |      861 |           875.6760 |            296.9373 |                   218.9190 |                     74.2343 |              753957 |               255663 |                     nan |                      nan |                        nan |

## F. Function calling vs JSON schema

**Métricas overall:**

| model             | method           |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | function_calling |     0.8397 |    0.7769 |          0.7469 |           0.7469 |        0.8095 |
| deepseek-v4-flash | json_schema      |     0.8310 |    0.7650 |          0.7280 |           0.7384 |        0.7937 |
| gpt-4.1           | function_calling |     0.8143 |    0.7422 |          0.7220 |           0.6655 |        0.8390 |
| gpt-4.1           | json_schema      |     0.8227 |    0.7313 |          0.7049 |           0.6594 |        0.8209 |

**Δ por modelo (FC − JS):**

| model             |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:------------------|-----------------:|----------------:|-----------------------:|--------------------:|
| deepseek-v4-flash |           0.0086 |          0.0119 |                 0.0085 |              0.0159 |
| gpt-4.1           |          -0.0085 |          0.0109 |                 0.0061 |              0.0181 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8544 |      0.7287 |         0.6667 |          0.7377 |
| deepseek-v4-flash | json_schema      |  0.8454 |      0.7309 |         0.6308 |          0.7049 |
| gpt-4.1           | function_calling |  0.8117 |      0.6691 |         0.6761 |          0.7313 |
| gpt-4.1           | json_schema      |  0.8054 |      0.6716 |         0.6056 |          0.7368 |

**Span Precision (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8421 |      0.7258 |         0.5349 |          0.7627 |
| deepseek-v4-flash | json_schema      |  0.8294 |      0.7222 |         0.5256 |          0.7288 |
| gpt-4.1           | function_calling |  0.7449 |      0.6053 |         0.5333 |          0.6901 |
| gpt-4.1           | json_schema      |  0.7377 |      0.6207 |         0.4778 |          0.7000 |

**Span Recall (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8670 |      0.7317 |         0.8846 |          0.7143 |
| deepseek-v4-flash | json_schema      |  0.8621 |      0.7398 |         0.7885 |          0.6825 |
| gpt-4.1           | function_calling |  0.8916 |      0.7480 |         0.9231 |          0.7778 |
| gpt-4.1           | json_schema      |  0.8867 |      0.7317 |         0.8269 |          0.7778 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model             | technique   |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | cot         |     0.8296 |    0.7155 |          0.6806 |           0.6289 |        0.8299 |
| deepseek-v4-flash | few_shot    |     0.8335 |    0.7696 |          0.7423 |           0.7390 |        0.8027 |
| deepseek-v4-flash | two_stage   |     0.8322 |    0.7692 |          0.7334 |           0.7365 |        0.8050 |
| gpt-4.1           | cot         |     0.8128 |    0.7363 |          0.7182 |           0.6560 |        0.8390 |
| gpt-4.1           | few_shot    |     0.8167 |    0.7365 |          0.7170 |           0.6578 |        0.8367 |
| gpt-4.1           | two_stage   |     0.8204 |    0.7450 |          0.7253 |           0.6685 |        0.8413 |
| gpt-5.2           | cot         |     0.7937 |    0.6908 |          0.7038 |           0.5755 |        0.8639 |
| gpt-5.2           | few_shot    |     0.7515 |    0.6198 |          0.5945 |           0.5057 |        0.8005 |
| gpt-5.2           | two_stage   |     0.7830 |    0.6685 |          0.6381 |           0.5705 |        0.8073 |
| llama-3.3-70b     | cot         |     0.3057 |    0.2643 |          0.1997 |           0.6218 |        0.1678 |
| llama-3.3-70b     | few_shot    |     0.4090 |    0.3558 |          0.2856 |           0.6066 |        0.2517 |
| llama-3.3-70b     | two_stage   |     0.1696 |    0.1315 |          0.1154 |           0.5410 |        0.0748 |
| qwen2.5-72b       | cot         |     0.7534 |    0.6475 |          0.6022 |           0.5617 |        0.7642 |
| qwen2.5-72b       | few_shot    |     0.7177 |    0.6243 |          0.5853 |           0.5491 |        0.7234 |
| qwen2.5-72b       | two_stage   |     0.7419 |    0.6394 |          0.5874 |           0.5714 |        0.7256 |

**Span F1 pivotado (modelo × técnica):**

| model             |    cot |   few_shot |   two_stage |
|:------------------|-------:|-----------:|------------:|
| deepseek-v4-flash | 0.7155 |     0.7696 |      0.7692 |
| gpt-4.1           | 0.7363 |     0.7365 |      0.7450 |
| gpt-5.2           | 0.6908 |     0.6198 |      0.6685 |
| llama-3.3-70b     | 0.2643 |     0.3558 |      0.1315 |
| qwen2.5-72b       | 0.6475 |     0.6243 |      0.6394 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique   | token_f1           | token_f1.1          | token_f1.2          | token_f1.3         | span_f1            | span_f1.1           | span_f1.2           | span_f1.3          |
|:------------|:-------------------|:--------------------|:--------------------|:-------------------|:-------------------|:--------------------|:--------------------|:-------------------|
| nan         | mean               | std                 | min                 | max                | mean               | std                 | min                 | max                |
| cot         | 0.6990277113401667 | 0.2217071125876835  | 0.3056922224756443  | 0.8295863131692284 | 0.6108888340138181 | 0.19656323852847388 | 0.2642857142857143  | 0.7363184079601991 |
| few_shot    | 0.7056914764518479 | 0.17240971462222462 | 0.4090397488300456  | 0.8335160596093718 | 0.6211939011439622 | 0.16261709688499038 | 0.3557692307692307  | 0.7695652173913043 |
| two_stage   | 0.6694442739073965 | 0.2816232299402566  | 0.16964188329394655 | 0.8322383187104673 | 0.5907180065589496 | 0.26219820327993754 | 0.13147410358565736 | 0.7692307692307693 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.8524 |      0.7059 |         0.4593 |          0.7049 |
| deepseek-v4-flash | few_shot    |  0.8434 |      0.7154 |         0.6667 |          0.7438 |
| deepseek-v4-flash | two_stage   |  0.8482 |      0.7417 |         0.6667 |          0.6769 |
| gpt-4.1           | cot         |  0.8108 |      0.6528 |         0.6667 |          0.7424 |
| gpt-4.1           | few_shot    |  0.8098 |      0.6547 |         0.6667 |          0.7368 |
| gpt-4.1           | two_stage   |  0.8135 |      0.6739 |         0.6713 |          0.7424 |
| gpt-5.2           | cot         |  0.8044 |      0.5233 |         0.6906 |          0.7969 |
| gpt-5.2           | few_shot    |  0.7553 |      0.4895 |         0.5294 |          0.6040 |
| gpt-5.2           | two_stage   |  0.7894 |      0.5638 |         0.5036 |          0.6957 |
| llama-3.3-70b     | cot         |  0.3373 |      0.2971 |         0.1644 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.4214 |      0.3939 |         0.2963 |          0.0308 |
| llama-3.3-70b     | two_stage   |  0.1478 |      0.1497 |         0.1333 |          0.0308 |
| qwen2.5-72b       | cot         |  0.8018 |      0.5581 |         0.3580 |          0.6906 |
| qwen2.5-72b       | few_shot    |  0.7731 |      0.5188 |         0.3727 |          0.6765 |
| qwen2.5-72b       | two_stage   |  0.7925 |      0.5467 |         0.3973 |          0.6131 |

**Span Precision por entidade (mesmo eixo):**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.8249 |      0.6443 |         0.3057 |          0.7288 |
| deepseek-v4-flash | few_shot    |  0.8255 |      0.7154 |         0.5349 |          0.7759 |
| deepseek-v4-flash | two_stage   |  0.8302 |      0.7607 |         0.5349 |          0.6567 |
| gpt-4.1           | cot         |  0.7469 |      0.5697 |         0.5281 |          0.7101 |
| gpt-4.1           | few_shot    |  0.7418 |      0.5871 |         0.5217 |          0.7000 |
| gpt-4.1           | two_stage   |  0.7479 |      0.6078 |         0.5275 |          0.7101 |
| gpt-5.2           | cot         |  0.7328 |      0.3840 |         0.5517 |          0.7846 |
| gpt-5.2           | few_shot    |  0.6605 |      0.3619 |         0.4286 |          0.5233 |
| gpt-5.2           | two_stage   |  0.7177 |      0.4439 |         0.4023 |          0.6400 |
| llama-3.3-70b     | cot         |  0.9130 |      0.5000 |         0.2857 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.7662 |      0.5200 |         0.4138 |          0.5000 |
| llama-3.3-70b     | two_stage   |  0.6296 |      0.4583 |         0.5000 |          0.5000 |
| qwen2.5-72b       | cot         |  0.7458 |      0.4719 |         0.2636 |          0.6316 |
| qwen2.5-72b       | few_shot    |  0.7293 |      0.4471 |         0.2752 |          0.6301 |
| qwen2.5-72b       | two_stage   |  0.7522 |      0.4759 |         0.3085 |          0.5676 |

**Span Recall por entidade:**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.8818 |      0.7805 |         0.9231 |          0.6825 |
| deepseek-v4-flash | few_shot    |  0.8621 |      0.7154 |         0.8846 |          0.7143 |
| deepseek-v4-flash | two_stage   |  0.8670 |      0.7236 |         0.8846 |          0.6984 |
| gpt-4.1           | cot         |  0.8867 |      0.7642 |         0.9038 |          0.7778 |
| gpt-4.1           | few_shot    |  0.8916 |      0.7398 |         0.9231 |          0.7778 |
| gpt-4.1           | two_stage   |  0.8916 |      0.7561 |         0.9231 |          0.7778 |
| gpt-5.2           | cot         |  0.8916 |      0.8211 |         0.9231 |          0.8095 |
| gpt-5.2           | few_shot    |  0.8818 |      0.7561 |         0.6923 |          0.7143 |
| gpt-5.2           | two_stage   |  0.8768 |      0.7724 |         0.6731 |          0.7619 |
| llama-3.3-70b     | cot         |  0.2069 |      0.2114 |         0.1154 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.2906 |      0.3171 |         0.2308 |          0.0159 |
| llama-3.3-70b     | two_stage   |  0.0837 |      0.0894 |         0.0769 |          0.0159 |
| qwen2.5-72b       | cot         |  0.8670 |      0.6829 |         0.5577 |          0.7619 |
| qwen2.5-72b       | few_shot    |  0.8227 |      0.6179 |         0.5769 |          0.7302 |
| qwen2.5-72b       | two_stage   |  0.8374 |      0.6423 |         0.5577 |          0.6667 |

## I. Análise de erros do melhor modelo

**Melhor modelo identificado por span F1: DeepSeek-V4-Flash.**

**Contagens por tipo de erro:**

| kind       |   count |
|:-----------|--------:|
| exact      |     365 |
| FP         |      64 |
| FN         |      60 |
| boundary   |      46 |
| type_error |       4 |

**Matriz rótulo × tipo de erro:**

| label         |   FN |   FP |   boundary |   exact |   type_error |
|:--------------|-----:|-----:|-----------:|--------:|-------------:|
| MULTA         |   24 |    6 |         10 |     183 |            0 |
| OBRIGACAO     |   24 |   20 |         15 |      88 |            0 |
| RECOMENDACAO  |    5 |   36 |          1 |      48 |            0 |
| RESSARCIMENTO |    7 |    2 |         20 |      46 |            4 |

**Pares de tipo errado (gold → pred):**

| label         | pred_label   |   count |
|:--------------|:-------------|--------:|
| RESSARCIMENTO | MULTA        |       4 |

**Histograma de IoU para erros de fronteira:**

|   bin_low |   bin_high |   count |
|----------:|-----------:|--------:|
|    0.0000 |     0.2000 |  4.0000 |
|    0.2000 |     0.4000 | 31.0000 |
|    0.4000 |     0.5000 | 11.0000 |
|    0.5000 |     0.7000 |  0.0000 |
|    0.7000 |     0.9000 |  0.0000 |
|    0.9000 |     1.0000 |  0.0000 |

## J. Significância estatística (bootstrap pareado)

**Item 41 — N de reamostragens**: 10.000.

**Item 42 — IC 95% por modelo:**

| model                                                  | display              |   span_f1_point |   span_f1_micro |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:-------------------------------------------------------|:---------------------|----------------:|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |          0.7423 |          0.7696 |         0.7419 |        0.0231 |     0.6963 |     0.7872 |     0.0908 |
| gpt-4.1_few_shot                                       | GPT-4.1              |          0.7170 |          0.7365 |         0.7166 |        0.0226 |     0.6719 |     0.7611 |     0.0892 |
| gpt-5.1_few_shot                                       | GPT-5.1              |          0.6910 |          0.7046 |         0.6905 |        0.0225 |     0.6460 |     0.7343 |     0.0883 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |          0.6837 |          0.6986 |         0.6834 |        0.0224 |     0.6388 |     0.7270 |     0.0881 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.6189 |          0.6809 |         0.6185 |        0.0298 |     0.5591 |     0.6761 |     0.1170 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.6045 |          0.6649 |         0.6042 |        0.0299 |     0.5466 |     0.6629 |     0.1163 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.5945 |          0.6198 |         0.5946 |        0.0259 |     0.5430 |     0.6447 |     0.1017 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.5853 |          0.6243 |         0.5848 |        0.0232 |     0.5394 |     0.6293 |     0.0899 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.5692 |          0.6640 |         0.5683 |        0.0302 |     0.5096 |     0.6273 |     0.1178 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.5619 |          0.6281 |         0.5615 |        0.0298 |     0.5029 |     0.6197 |     0.1168 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.5320 |          0.6504 |         0.5320 |        0.0289 |     0.4758 |     0.5887 |     0.1129 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.5310 |          0.4162 |         0.5309 |        0.0228 |     0.4846 |     0.5744 |     0.0898 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.5085 |          0.6028 |         0.5078 |        0.0316 |     0.4471 |     0.5705 |     0.1234 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.4615 |          0.5794 |         0.4609 |        0.0317 |     0.3988 |     0.5233 |     0.1244 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.4113 |          0.5213 |         0.4111 |        0.0274 |     0.3566 |     0.4638 |     0.1072 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.3953 |          0.4341 |         0.3958 |        0.0251 |     0.3464 |     0.4458 |     0.0994 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.3922 |          0.5798 |         0.3916 |        0.0279 |     0.3386 |     0.4481 |     0.1095 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.3303 |          0.4781 |         0.3291 |        0.0293 |     0.2736 |     0.3889 |     0.1153 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2856 |          0.3558 |         0.2853 |        0.0275 |     0.2312 |     0.3396 |     0.1084 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                        | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash | Llama-3.3-70B     | 0.7423 | 0.2856 |    0.4566 |     0.3947 |     0.5160 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-5.2           | Llama-3.3-70B     | 0.5945 | 0.2856 |    0.3092 |     0.2380 |     0.3791 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| llama-3.3-70b_few_shot                            | qwen2.5-72b_few_shot                                   | Llama-3.3-70B     | Qwen2.5-72B       | 0.2856 | 0.5853 |   -0.2995 |    -0.3687 |    -0.2295 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1-mini_few_shot                             | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini      | GPT-4.1-nano      | 0.6837 | 0.3953 |    0.2876 |     0.2304 |     0.3432 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7423 | 0.5692 |    0.1736 |     0.1111 |     0.2373 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-5.2           | DeepSeek-V4-Flash | 0.5945 | 0.7423 |   -0.1474 |    -0.1958 |    -0.1001 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7423 | 0.6189 |    0.1235 |     0.0633 |     0.1835 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7170 | 0.5945 |    0.1221 |     0.0803 |     0.1652 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-5.1           | GPT-5.2           | 0.6910 | 0.5945 |    0.0959 |     0.0526 |     0.1402 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                                 | BERTimbau-base    | BiLSTM-CRF        | 0.5692 | 0.5085 |    0.0605 |    -0.0177 |     0.1355 |    0.1254 | False            |   0.5990 |         1.0000 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.5692 | 0.6189 |   -0.0501 |    -0.0996 |    -0.0001 |    0.0490 | True             |   0.3430 |         0.8330 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.5692 | 0.6045 |   -0.0359 |    -0.0832 |     0.0101 |    0.1198 | False            |   0.5990 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7170 | 0.6837 |    0.0332 |     0.0082 |     0.0604 |    0.0084 | True             |   0.0672 |         0.1428 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2           | BERTimbau-base    | 0.5945 | 0.5692 |    0.0262 |    -0.0477 |     0.1000 |    0.4842 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7170 | 0.7423 |   -0.0253 |    -0.0517 |     0.0009 |    0.0600 | False            |   0.3600 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2           | LegalBert-pt      | 0.5945 | 0.6189 |   -0.0239 |    -0.0941 |     0.0468 |    0.5160 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-5.2           | Qwen2.5-72B       | 0.5945 | 0.5853 |    0.0097 |    -0.0371 |     0.0569 |    0.6816 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |

**Itens 47–48 — Resumo:**

| metric                         | value                   |
|:-------------------------------|:------------------------|
| resampling_unit                | document                |
| n_docs_resampled               | 861                     |
| n_total_pairs                  | 171                     |
| n_significant_5pct_uncorrected | 133                     |
| highlighted_family_size        | 17                      |
| highlighted_n_sig_uncorrected  | 11                      |
| highlighted_n_sig_holm         | 9                       |
| highlighted_n_sig_bonferroni   | 9                       |
| smallest_significant_abs_diff  | 0.03323759526790254     |
| smallest_significant_pair      | GPT-4.1 vs GPT-4.1-mini |
| leader_model                   | DeepSeek-V4-Flash       |
| leader_group_size_holm         | 2                       |

**p48a — Correção para múltiplas comparações.** A família reportada são os pares destacados acima; `p_holm`/`p_bonferroni` controlam o erro familiar (FWER) e `sig_holm_5pct` substitui a coluna 'Sig.' não corrigida da Tabela 13. Diferenças marginais tendem a não sobreviver, reforçando a leitura de saturação.

**Grupo do líder (DS-p.55a).** Família: as comparações líder × demais modelos, com correção de Holm; `in_leader_group=True` marca os modelos estatisticamente indistinguíveis do líder a 5% — a fonte do marcador (†) na tabela geral de resultados:

| model                                                  | display              |   span_f1 |   diff_vs_leader |    p_raw |   p_holm | in_leader_group   |
|:-------------------------------------------------------|:---------------------|----------:|-----------------:|---------:|---------:|:------------------|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |    0.7423 |           0.0000 | nan      | nan      | True              |
| gpt-4.1_few_shot                                       | GPT-4.1              |    0.7170 |           0.0253 |   0.0600 |   0.0600 | True              |
| gpt-5.1_few_shot                                       | GPT-5.1              |    0.6910 |           0.0514 |   0.0026 |   0.0052 | False             |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |    0.6837 |           0.0585 |   0.0000 |   0.0000 | False             |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.6189 |           0.1235 |   0.0000 |   0.0000 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.6045 |           0.1377 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.5945 |           0.1474 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.5853 |           0.1571 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.5692 |           0.1736 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.5619 |           0.1804 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.5320 |           0.2099 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.5310 |           0.2110 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.5085 |           0.2341 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.4615 |           0.2810 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.4113 |           0.3308 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.3953 |           0.3461 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.3922 |           0.3503 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.3303 |           0.4128 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2856 |           0.4566 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7423 | 0.2856 |    0.4566 |     0.3947 |     0.5160 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7170 | 0.2856 |    0.4313 |     0.3692 |     0.4925 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7423 | 0.3303 |    0.4128 |     0.3383 |     0.4788 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.6910 | 0.2856 |    0.4051 |     0.3395 |     0.4679 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.6837 | 0.2856 |    0.3980 |     0.3325 |     0.4608 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7170 | 0.3303 |    0.3875 |     0.3162 |     0.4522 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.6910 | 0.3303 |    0.3613 |     0.2893 |     0.4256 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.6837 | 0.3303 |    0.3542 |     0.2796 |     0.4207 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7423 | 0.3922 |    0.3503 |     0.2892 |     0.4102 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.3953 | 0.7423 |   -0.3461 |    -0.4053 |    -0.2853 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2856 | 0.6189 |   -0.3331 |    -0.4043 |    -0.2598 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7423 | 0.4113 |    0.3308 |     0.2675 |     0.3910 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7170 | 0.3922 |    0.3250 |     0.2650 |     0.3834 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7170 | 0.3953 |    0.3208 |     0.2614 |     0.3780 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2856 | 0.6045 |   -0.3189 |    -0.3856 |    -0.2501 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.5945 | 0.2856 |    0.3092 |     0.2380 |     0.3791 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7170 | 0.4113 |    0.3055 |     0.2459 |     0.3635 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2856 | 0.5853 |   -0.2995 |    -0.3687 |    -0.2295 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.6910 | 0.3922 |    0.2988 |     0.2358 |     0.3600 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.3953 | 0.6910 |   -0.2947 |    -0.3514 |    -0.2366 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.6837 | 0.3922 |    0.2917 |     0.2313 |     0.3489 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.6189 | 0.3303 |    0.2893 |     0.2249 |     0.3520 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.6837 | 0.3953 |    0.2876 |     0.2304 |     0.3432 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2856 | 0.5692 |   -0.2830 |    -0.3537 |    -0.2100 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7423 | 0.4615 |    0.2810 |     0.2140 |     0.3479 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.6910 | 0.4113 |    0.2794 |     0.2160 |     0.3406 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2856 | 0.5619 |   -0.2762 |    -0.3448 |    -0.2075 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.6045 | 0.3303 |    0.2751 |     0.2110 |     0.3390 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.6837 | 0.4113 |    0.2723 |     0.2107 |     0.3339 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.5945 | 0.3303 |    0.2654 |     0.1898 |     0.3362 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.5853 | 0.3303 |    0.2557 |     0.1830 |     0.3250 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7170 | 0.4615 |    0.2557 |     0.1902 |     0.3199 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2856 | 0.5320 |   -0.2466 |    -0.3122 |    -0.1791 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.5310 | 0.2856 |    0.2456 |     0.1786 |     0.3116 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.5692 | 0.3303 |    0.2392 |     0.1770 |     0.3027 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7423 | 0.5085 |    0.2341 |     0.1632 |     0.3036 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.5619 | 0.3303 |    0.2324 |     0.1637 |     0.2970 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.6910 | 0.4615 |    0.2295 |     0.1624 |     0.2943 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.3922 | 0.6189 |   -0.2268 |    -0.2866 |    -0.1659 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.3953 | 0.6189 |   -0.2226 |    -0.2897 |    -0.1558 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2856 | 0.5085 |   -0.2225 |    -0.2926 |    -0.1547 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.6837 | 0.4615 |    0.2224 |     0.1546 |     0.2887 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.3922 | 0.6045 |   -0.2126 |    -0.2672 |    -0.1576 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.5310 | 0.7423 |   -0.2110 |    -0.2537 |    -0.1688 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7423 | 0.5320 |    0.2099 |     0.1482 |     0.2682 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7170 | 0.5085 |    0.2088 |     0.1391 |     0.2764 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.3953 | 0.6045 |   -0.2084 |    -0.2751 |    -0.1418 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.6189 | 0.4113 |    0.2074 |     0.1445 |     0.2702 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.5945 | 0.3922 |    0.2029 |     0.1362 |     0.2675 |    0.0000 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.3303 | 0.5320 |   -0.2028 |    -0.2686 |    -0.1345 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.5310 | 0.3303 |    0.2017 |     0.1305 |     0.2697 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.3953 | 0.5945 |   -0.1987 |    -0.2456 |    -0.1508 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.5853 | 0.3922 |    0.1932 |     0.1276 |     0.2566 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.6045 | 0.4113 |    0.1932 |     0.1356 |     0.2521 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.3953 | 0.5853 |   -0.1890 |    -0.2426 |    -0.1348 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7170 | 0.5310 |    0.1857 |     0.1460 |     0.2257 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7170 | 0.5320 |    0.1846 |     0.1220 |     0.2446 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.5945 | 0.4113 |    0.1835 |     0.1221 |     0.2454 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.6910 | 0.5085 |    0.1827 |     0.1117 |     0.2516 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7423 | 0.5619 |    0.1804 |     0.1177 |     0.2442 |    0.0000 | True             |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.5085 | 0.3303 |    0.1787 |     0.1059 |     0.2512 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.3922 | 0.5692 |   -0.1767 |    -0.2388 |    -0.1117 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2856 | 0.4615 |   -0.1756 |    -0.2451 |    -0.1035 |    0.0002 | True             |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.6837 | 0.5085 |    0.1756 |     0.1051 |     0.2442 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.5853 | 0.4113 |    0.1737 |     0.1095 |     0.2377 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7423 | 0.5692 |    0.1736 |     0.1111 |     0.2373 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.3953 | 0.5692 |   -0.1725 |    -0.2426 |    -0.1013 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.3922 | 0.5619 |   -0.1699 |    -0.2223 |    -0.1161 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.3953 | 0.5619 |   -0.1657 |    -0.2355 |    -0.0961 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.5310 | 0.6910 |   -0.1596 |    -0.2027 |    -0.1178 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.6910 | 0.5320 |    0.1585 |     0.0928 |     0.2212 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.4615 | 0.6189 |   -0.1575 |    -0.2217 |    -0.0908 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.5692 | 0.4113 |    0.1572 |     0.0997 |     0.2164 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7423 | 0.5853 |    0.1571 |     0.1131 |     0.2028 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7170 | 0.5619 |    0.1551 |     0.0926 |     0.2165 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.6837 | 0.5310 |    0.1525 |     0.1135 |     0.1928 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.6837 | 0.5320 |    0.1514 |     0.0885 |     0.2125 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.5619 | 0.4113 |    0.1505 |     0.0903 |     0.2115 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7170 | 0.5692 |    0.1483 |     0.0861 |     0.2090 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.5945 | 0.7423 |   -0.1474 |    -0.1958 |    -0.1001 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.4615 | 0.6045 |   -0.1433 |    -0.1988 |    -0.0899 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.3922 | 0.5320 |   -0.1403 |    -0.1981 |    -0.0826 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.5310 | 0.3922 |    0.1393 |     0.0753 |     0.1997 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7423 | 0.6045 |    0.1377 |     0.0800 |     0.1968 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.3953 | 0.5320 |   -0.1361 |    -0.2037 |    -0.0685 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.3953 | 0.5310 |   -0.1351 |    -0.1868 |    -0.0814 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.5945 | 0.4615 |    0.1336 |     0.0621 |     0.2048 |    0.0008 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.4615 | 0.3303 |    0.1318 |     0.0620 |     0.1998 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7170 | 0.5853 |    0.1318 |     0.0892 |     0.1751 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.6910 | 0.5619 |    0.1289 |     0.0637 |     0.1910 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2856 | 0.4113 |   -0.1258 |    -0.1904 |    -0.0594 |    0.0004 | True             |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.5853 | 0.4615 |    0.1239 |     0.0501 |     0.1979 |    0.0004 | True             |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7423 | 0.6189 |    0.1235 |     0.0633 |     0.1835 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.6910 | 0.5692 |    0.1221 |     0.0581 |     0.1856 |    0.0002 | True             |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7170 | 0.5945 |    0.1221 |     0.0803 |     0.1652 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.6837 | 0.5619 |    0.1218 |     0.0588 |     0.1850 |    0.0006 | True             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.5320 | 0.4113 |    0.1209 |     0.0606 |     0.1807 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.5310 | 0.4113 |    0.1198 |     0.0578 |     0.1812 |    0.0002 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.3922 | 0.5085 |   -0.1162 |    -0.1832 |    -0.0459 |    0.0020 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.6837 | 0.5692 |    0.1150 |     0.0520 |     0.1765 |    0.0004 | True             |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7170 | 0.6045 |    0.1124 |     0.0562 |     0.1689 |    0.0002 | True             |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.3953 | 0.5085 |   -0.1120 |    -0.1893 |    -0.0343 |    0.0040 | True             |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.5085 | 0.6189 |   -0.1106 |    -0.1862 |    -0.0317 |    0.0080 | True             |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.3953 | 0.2856 |    0.1105 |     0.0386 |     0.1805 |    0.0022 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.5692 | 0.4615 |    0.1074 |     0.0495 |     0.1677 |    0.0002 | True             |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2856 | 0.3922 |   -0.1063 |    -0.1755 |    -0.0369 |    0.0028 | True             |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.6910 | 0.5853 |    0.1056 |     0.0618 |     0.1498 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.4615 | 0.5619 |   -0.1006 |    -0.1600 |    -0.0419 |    0.0010 | True             |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.6837 | 0.5853 |    0.0985 |     0.0595 |     0.1384 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7170 | 0.6189 |    0.0982 |     0.0387 |     0.1579 |    0.0010 | True             |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.5085 | 0.4113 |    0.0967 |     0.0283 |     0.1680 |    0.0060 | True             |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.5085 | 0.6045 |   -0.0964 |    -0.1614 |    -0.0307 |    0.0060 | True             |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.6910 | 0.5945 |    0.0959 |     0.0526 |     0.1402 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.6837 | 0.5945 |    0.0888 |     0.0463 |     0.1328 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.5310 | 0.6189 |   -0.0876 |    -0.1562 |    -0.0191 |    0.0122 | True             |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.5945 | 0.5085 |    0.0867 |     0.0079 |     0.1642 |    0.0322 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.6189 | 0.5320 |    0.0865 |     0.0230 |     0.1489 |    0.0070 | True             |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.6910 | 0.6045 |    0.0862 |     0.0244 |     0.1473 |    0.0074 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.3303 | 0.4113 |   -0.0819 |    -0.1322 |    -0.0280 |    0.0032 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.6837 | 0.6045 |    0.0791 |     0.0204 |     0.1363 |    0.0062 | True             |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.5853 | 0.5085 |    0.0770 |    -0.0020 |     0.1559 |    0.0568 | False            |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.5310 | 0.6045 |   -0.0734 |    -0.1379 |    -0.0095 |    0.0244 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.6045 | 0.5320 |    0.0723 |     0.0252 |     0.1202 |    0.0026 | True             |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.6910 | 0.6189 |    0.0720 |     0.0105 |     0.1340 |    0.0214 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.4615 | 0.5320 |   -0.0710 |    -0.1361 |    -0.0066 |    0.0316 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.5310 | 0.4615 |    0.0699 |     0.0016 |     0.1386 |    0.0438 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.3922 | 0.4615 |   -0.0693 |    -0.1305 |    -0.0050 |    0.0352 | True             |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.3953 | 0.3303 |    0.0667 |    -0.0017 |     0.1338 |    0.0558 | False            |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.3953 | 0.4615 |   -0.0651 |    -0.1328 |     0.0040 |    0.0646 | False            |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.6837 | 0.6189 |    0.0649 |     0.0024 |     0.1272 |    0.0426 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.5310 | 0.5945 |   -0.0637 |    -0.1049 |    -0.0223 |    0.0024 | True             |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.5945 | 0.5320 |    0.0626 |    -0.0091 |     0.1314 |    0.0854 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.3922 | 0.3303 |    0.0625 |    -0.0089 |     0.1323 |    0.0792 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.5692 | 0.5085 |    0.0605 |    -0.0177 |     0.1355 |    0.1254 | False            |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.6837 | 0.7423 |   -0.0585 |    -0.0912 |    -0.0270 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.5619 | 0.6189 |   -0.0569 |    -0.1208 |     0.0083 |    0.0838 | False            |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.5310 | 0.5853 |   -0.0539 |    -0.1001 |    -0.0064 |    0.0262 | True             |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.5085 | 0.5619 |   -0.0537 |    -0.1105 |     0.0041 |    0.0672 | False            |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.5853 | 0.5320 |    0.0529 |    -0.0176 |     0.1223 |    0.1422 | False            |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.6910 | 0.7423 |   -0.0514 |    -0.0856 |    -0.0177 |    0.0026 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.5692 | 0.6189 |   -0.0501 |    -0.0996 |    -0.0001 |    0.0490 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.4615 | 0.4113 |    0.0499 |    -0.0008 |     0.1023 |    0.0544 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.4615 | 0.5085 |   -0.0469 |    -0.1170 |     0.0217 |    0.1812 | False            |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2856 | 0.3303 |   -0.0438 |    -0.1198 |     0.0292 |    0.2428 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.5619 | 0.6045 |   -0.0427 |    -0.0885 |     0.0017 |    0.0576 | False            |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.5310 | 0.5692 |   -0.0375 |    -0.1073 |     0.0314 |    0.2916 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.5692 | 0.5320 |    0.0364 |    -0.0272 |     0.0998 |    0.2640 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.5692 | 0.6045 |   -0.0359 |    -0.0832 |     0.0101 |    0.1198 | False            |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.5853 | 0.6189 |   -0.0336 |    -0.1004 |     0.0331 |    0.3336 | False            |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7170 | 0.6837 |    0.0332 |     0.0082 |     0.0604 |    0.0084 | True             |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.5945 | 0.5619 |    0.0330 |    -0.0404 |     0.1054 |    0.3634 | False            |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.5310 | 0.5619 |   -0.0307 |    -0.0997 |     0.0383 |    0.3796 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.5619 | 0.5320 |    0.0296 |    -0.0178 |     0.0765 |    0.2208 | False            |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.5945 | 0.5692 |    0.0262 |    -0.0477 |     0.1000 |    0.4842 | False            |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7170 | 0.6910 |    0.0261 |    -0.0016 |     0.0545 |    0.0636 | False            |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7170 | 0.7423 |   -0.0253 |    -0.0517 |     0.0009 |    0.0600 | False            |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.5085 | 0.5320 |   -0.0241 |    -0.0822 |     0.0351 |    0.4106 | False            |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.5945 | 0.6189 |   -0.0239 |    -0.0941 |     0.0468 |    0.5160 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.5853 | 0.5619 |    0.0233 |    -0.0457 |     0.0931 |    0.5212 | False            |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.5310 | 0.5085 |    0.0231 |    -0.0482 |     0.0928 |    0.5168 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.3922 | 0.4113 |   -0.0195 |    -0.0806 |     0.0453 |    0.5380 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.5853 | 0.6045 |   -0.0194 |    -0.0862 |     0.0476 |    0.5710 | False            |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.5853 | 0.5692 |    0.0165 |    -0.0524 |     0.0839 |    0.6314 | False            |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.3953 | 0.4113 |   -0.0153 |    -0.0746 |     0.0453 |    0.6128 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.6045 | 0.6189 |   -0.0142 |    -0.0652 |     0.0370 |    0.5864 | False            |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.5945 | 0.5853 |    0.0097 |    -0.0371 |     0.0569 |    0.6816 | False            |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.5945 | 0.6045 |   -0.0097 |    -0.0802 |     0.0595 |    0.7920 | False            |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.6837 | 0.6910 |   -0.0071 |    -0.0384 |     0.0236 |    0.6618 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.5692 | 0.5619 |    0.0068 |    -0.0564 |     0.0705 |    0.8276 | False            |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.3953 | 0.3922 |    0.0042 |    -0.0586 |     0.0669 |    0.8874 | False            |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.5310 | 0.5320 |   -0.0011 |    -0.0699 |     0.0646 |    0.9896 | False            |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.6907 | 0.6640 | 0.6347 |  0.5733 |
| BERTimbau-large      | 0.5941 | 0.5794 | 0.5676 |  0.5206 |
| BERTimbauLaw         | 0.6907 | 0.6649 | 0.6340 |  0.5619 |
| BiLSTM-CRF           | 0.6444 | 0.6028 | 0.5556 |  0.4389 |
| DeepSeek-V4-Flash    | 0.8152 | 0.7696 | 0.7217 |  0.3174 |
| GPT-4.1              | 0.7784 | 0.7365 | 0.6766 |  0.2236 |
| GPT-4.1-mini         | 0.7343 | 0.6986 | 0.6366 |  0.2047 |
| GPT-4.1-nano         | 0.4921 | 0.4341 | 0.3779 |  0.1265 |
| GPT-5-mini           | 0.4356 | 0.4162 | 0.3922 |  0.0832 |
| GPT-5.1              | 0.7321 | 0.7046 | 0.6555 |  0.2375 |
| GPT-5.2              | 0.6620 | 0.6198 | 0.5654 |  0.1686 |
| GovBERT-BR           | 0.5245 | 0.5213 | 0.4992 |  0.4550 |
| JurisBERT            | 0.6518 | 0.6281 | 0.5940 |  0.4967 |
| Legal-BERT-STF       | 0.6632 | 0.6504 | 0.6093 |  0.5398 |
| Legal-BERTimbau-base | 0.5857 | 0.5798 | 0.5652 |  0.4949 |
| LegalBERTPT-br       | 0.4992 | 0.4781 | 0.4539 |  0.4024 |
| LegalBert-pt         | 0.7010 | 0.6809 | 0.6683 |  0.5779 |
| Llama-3.3-70B        | 0.3910 | 0.3558 | 0.3173 |  0.0513 |
| Qwen2.5-72B          | 0.6556 | 0.6243 | 0.5773 |  0.2290 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5):

| iou_threshold   |   spearman_vs_0.5 |
|:----------------|------------------:|
| 0.3             |            0.9895 |
| 0.5             |            1.0000 |
| 0.7             |            0.9789 |
| exact           |            0.3281 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  231 |         0.7696 |                0.8147 |          0.0452 |                0.7390 |                       0.8271 |                 0.0881 |             0.8027 |                    0.8027 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  231 |         0.7365 |                0.7987 |          0.0622 |                0.6578 |                       0.7640 |                 0.1062 |             0.8367 |                    0.8367 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  231 |         0.6986 |                0.7742 |          0.0756 |                0.5962 |                       0.7154 |                 0.1192 |             0.8435 |                    0.8435 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  231 |         0.7046 |                0.7729 |          0.0683 |                0.6211 |                       0.7357 |                 0.1145 |             0.8141 |                    0.8141 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  231 |         0.6198 |                0.6990 |          0.0792 |                0.5057 |                       0.6204 |                 0.1147 |             0.8005 |                    0.8005 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  231 |         0.6809 |                0.6976 |          0.0167 |                0.7634 |                       0.8065 |                 0.0432 |             0.6145 |                    0.6145 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  231 |         0.6243 |                0.6845 |          0.0603 |                0.5491 |                       0.6497 |                 0.1006 |             0.7234 |                    0.7234 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  231 |         0.6649 |                0.6807 |          0.0158 |                0.7701 |                       0.8139 |                 0.0437 |             0.5850 |                    0.5850 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  231 |         0.6640 |                0.6739 |          0.0099 |                0.8058 |                       0.8356 |                 0.0297 |             0.5646 |                    0.5646 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  231 |         0.6504 |                0.6614 |          0.0111 |                0.7507 |                       0.7809 |                 0.0301 |             0.5737 |                    0.5737 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  231 |         0.6281 |                0.6408 |          0.0126 |                0.7469 |                       0.7836 |                 0.0367 |             0.5420 |                    0.5420 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  231 |         0.6028 |                0.6182 |          0.0155 |                0.7778 |                       0.8314 |                 0.0536 |             0.4921 |                    0.4921 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  231 |         0.4162 |                0.6068 |          0.1906 |                0.2780 |                       0.4790 |                 0.2010 |             0.8277 |                    0.8277 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  231 |         0.5798 |                0.5893 |          0.0095 |                0.8182 |                       0.8571 |                 0.0390 |             0.4490 |                    0.4490 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  231 |         0.5794 |                0.5881 |          0.0086 |                0.8243 |                       0.8603 |                 0.0360 |             0.4467 |                    0.4467 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  231 |         0.5213 |                0.5222 |          0.0008 |                0.8594 |                       0.8639 |                 0.0045 |             0.3741 |                    0.3741 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |           861 |                  231 |         0.4341 |                0.4867 |          0.0526 |                0.3544 |                       0.4303 |                 0.0759 |             0.5601 |                    0.5601 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  231 |         0.4781 |                0.4788 |          0.0007 |                0.7182 |                       0.7215 |                 0.0033 |             0.3583 |                    0.3583 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |           861 |                  231 |         0.3558 |                0.3669 |          0.0112 |                0.6066 |                       0.6768 |                 0.0703 |             0.2517 |                    0.2517 |

## M. Taxa de falha de alinhamento string→offset (p34)

As predições dos LLMs são strings (não offsets); são localizadas no texto-fonte por correspondência difusa (rapidfuzz `partial_ratio`, janela 500 / passo 100 / `min_score` 80). Strings que nenhuma janela casa nesse piso são descartadas silenciosamente na pontuação — a taxa de falha abaixo quantifica quantas predições nunca chegam à métrica:

| model                      | display           |   n_pred_strings |   n_aligned |   n_failed |   failure_rate |   n_dropped_no_token |
|:---------------------------|:------------------|-----------------:|------------:|-----------:|---------------:|---------------------:|
| gpt-4.1-nano_few_shot      | GPT-4.1-nano      |              707 |         697 |         10 |         0.0141 |                    0 |
| qwen2.5-72b_few_shot       | Qwen2.5-72B       |              584 |         581 |          3 |         0.0051 |                    0 |
| gpt-5-mini_few_shot        | GPT-5-mini        |             1315 |        1313 |          2 |         0.0015 |                    0 |
| gpt-4.1_few_shot           | GPT-4.1           |              561 |         561 |          0 |         0.0000 |                    0 |
| gpt-4.1-mini_few_shot      | GPT-4.1-mini      |              624 |         624 |          0 |         0.0000 |                    0 |
| gpt-5.1_few_shot           | GPT-5.1           |              578 |         578 |          0 |         0.0000 |                    0 |
| gpt-5.2_few_shot           | GPT-5.2           |              698 |         698 |          0 |         0.0000 |                    0 |
| deepseek-v4-flash_few_shot | DeepSeek-V4-Flash |              479 |         479 |          0 |         0.0000 |                    0 |
| llama-3.3-70b_few_shot     | Llama-3.3-70B     |              183 |         183 |          0 |         0.0000 |                    0 |
