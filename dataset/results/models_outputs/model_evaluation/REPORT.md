# Avaliação de modelos — números reproduzíveis (gold corrigido)

Documento auto-contido: todas as tabelas aparecem inline. Os CSVs ao lado deste arquivo são as fontes canônicas (uma por bloco), geradas por `research.release.evaluation_numbers`. Cada bloco abaixo corresponde a um bloco da avaliação.

## Pipeline de métricas (correções aplicadas)

Esta versão dos números incorpora quatro correções no pipeline de avaliação:

1. **Matching pred↔gold bipartido por IoU descendente** (`research.ner_metrics.bipartite_greedy_match`). Cada predição casa com no máximo um gold e vice-versa, eliminando a divergência anterior entre `calculate_metrics` (que tinha `break` após o primeiro match) e o bootstrap (que contava todos os pares sobrepostos). Esta única função é agora a fonte para `calculate_metrics`, `evaluate_bio_results` e `compute_doc_level_counts` — `matched ≤ min(|pred|, |gold|)` por construção, e P/R sempre em [0, 1].

2. **Unidade única de span: índices de token.** Todas as predições, generativas e BIO, são convertidas para spans em índices de token sobre a tokenização canônica `\S+` de `research.dataset_io` antes do emparelhamento, e o gold é convertido junto. A relocalização difusa das strings emitidas pelos LLMs permanece; o que mudou é a unidade em que se pontua. O spaCy saiu do caminho de métricas: o token F1 era calculado sobre `pt_core_news_sm` no caminho generativo e sobre a tokenização canônica no caminho BIO. O efeito maior aparece na correspondência exata, que antes media se a borda direita estimada pelo modelo caía por acaso em fronteira de token.

3. **Gold supervisionado completo e entrada sem truncamento.** Todos os modelos são pontuados contra o gold canônico completo, e não contra o `true_labels` do próprio modelo. Os encoders processam documentos longos em janelas deslizantes de 512 subpalavras com sobreposição de 320, e o BiLSTM-CRF aceita até 1.100 tokens; nenhum documento é truncado (`check_alignment`).

4. **Gold canônico íntegro.** As decisões `reject` do cleanlab deixaram de ser aplicadas (um `reject` é, por definição, operação nula) e o BIO passou a ser re-derivado dos spans reconstruídos. Antes disso o release publicava 459 entidades no campo `entities` e apenas 442 sob IOB2 estrito em `ner_tags`, e trazia fragmentos espúrios de até um caractere.

5. **Escopo da anotação.** Deliberações dirigidas a unidades do próprio Tribunal (recomendações e cientificações à SECEX ou à CONJU) não são entidades: o gold não as anota e as predições que caem sobre elas são descartadas antes da pontuação, para todos os modelos (`research.annotation_scope`; contagens em `C_scope_filter.csv`).

## A. Caracterização do corpus

`before` é a anotação original; `after` é o padrão-ouro publicado, após a auditoria Cleanlab (bloco B) e a adjudicação das divergências entre anotadores (`dataset/errors/adjudication-decisions.json`).

| metric              |   before |   after |   delta |
|:--------------------|---------:|--------:|--------:|
| total_docs          |      861 |     861 |       0 |
| docs_with_entity    |      196 |     223 |      27 |
| docs_without_entity |      665 |     638 |     -27 |
| total_entities      |      404 |     429 |      25 |
| MULTA               |      202 |     209 |       7 |
| OBRIGACAO           |      119 |     122 |       3 |
| RECOMENDACAO        |       21 |      32 |      11 |
| RESSARCIMENTO       |       62 |      66 |       4 |

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

**Saldo líquido por classe (auditoria Cleanlab e adjudicação somadas):**

| label         |   before |   after |   delta |
|:--------------|---------:|--------:|--------:|
| MULTA         |      202 |     209 |       7 |
| OBRIGACAO     |      119 |     122 |       3 |
| RECOMENDACAO  |       21 |      32 |      11 |
| RESSARCIMENTO |       62 |      66 |       4 |

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
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |     0.9138 |           0.8874 |            0.9362 |         0.8924 |    0.8779 |          0.8705 |           0.8842 |        0.8718 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.8821 |           0.8542 |            0.9704 |         0.8086 |    0.8353 |          0.8210 |           0.8432 |        0.8275 |
| gpt-4.1_few_shot                                       | GPT-4.1              |     0.8863 |           0.8720 |            0.8728 |         0.9002 |    0.8210 |          0.8228 |           0.7599 |        0.8928 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.8739 |           0.8492 |            0.9727 |         0.7933 |    0.8203 |          0.8126 |           0.8321 |        0.8089 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.8686 |           0.8126 |            0.9740 |         0.7838 |    0.8115 |          0.7777 |           0.8313 |        0.7925 |
| gpt-5.1_few_shot                                       | GPT-5.1              |     0.8587 |           0.8464 |            0.8293 |         0.8903 |    0.7992 |          0.8111 |           0.7280 |        0.8858 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.8253 |           0.6502 |            0.9763 |         0.7148 |    0.7903 |          0.6435 |           0.8687 |        0.7249 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |     0.8649 |           0.8310 |            0.8279 |         0.9055 |    0.7811 |          0.7707 |           0.6861 |        0.9068 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.8568 |           0.7111 |            0.9652 |         0.7702 |    0.7761 |          0.6712 |           0.7807 |        0.7716 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.8119 |           0.6449 |            0.9704 |         0.6978 |    0.7569 |          0.6253 |           0.8184 |        0.7040 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.8128 |           0.7039 |            0.9751 |         0.6969 |    0.7503 |          0.7022 |           0.7857 |        0.7179 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.8130 |           0.7236 |            0.9640 |         0.7029 |    0.7473 |          0.6814 |           0.7764 |        0.7203 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.7741 |           0.6019 |            0.9807 |         0.6394 |    0.7454 |          0.5854 |           0.8529 |        0.6620 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.8343 |           0.8404 |            0.7753 |         0.9032 |    0.7244 |          0.7548 |           0.6031 |        0.9068 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.8303 |           0.6794 |            0.9209 |         0.7559 |    0.7211 |          0.6213 |           0.8278 |        0.6387 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7917 |           0.7457 |            0.7834 |         0.8001 |    0.7169 |          0.6639 |           0.6365 |        0.8205 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.6434 |           0.5621 |            0.6275 |         0.6601 |    0.5000 |          0.4513 |           0.4108 |        0.6387 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.6237 |           0.7111 |            0.4687 |         0.9318 |    0.4688 |          0.6291 |           0.3145 |        0.9207 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4250 |           0.2959 |            0.8309 |         0.2855 |    0.3639 |          0.2667 |           0.6730 |        0.2494 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                                  | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                                        |
|:-------------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:--------------------------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                                 | BiLSTM-CRF           |         0.7282 |        0.0943 |        0.6092 |        0.8661 | 0.7241; 0.7541; 0.6092; 0.8661; 0.6875 |          0.8301 |         0.0473 |         0.7510 |         0.8679 | 0.8274; 0.8640; 0.7510; 0.8403; 0.8679 | {"hidden_dim": 256, "dropout": 0.3, "lr": 0.003, "max_len": 1100}                                             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |         0.8122 |        0.0473 |        0.7465 |        0.8521 | 0.7788; 0.8515; 0.7465; 0.8321; 0.8521 |          0.8651 |         0.0293 |         0.8285 |         0.8994 | 0.8285; 0.8994; 0.8555; 0.8515; 0.8905 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}      |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |         0.8258 |        0.0357 |        0.7867 |        0.8788 | 0.8413; 0.8177; 0.7867; 0.8788; 0.8046 |          0.8766 |         0.0263 |         0.8552 |         0.9202 | 0.9202; 0.8764; 0.8566; 0.8744; 0.8552 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}     |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |         0.7867 |        0.0693 |        0.7048 |        0.8525 | 0.8525; 0.8041; 0.7048; 0.8489; 0.7234 |          0.8591 |         0.0246 |         0.8303 |         0.8934 | 0.8934; 0.8672; 0.8303; 0.8637; 0.8410 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}              |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |         0.7462 |        0.0454 |        0.7009 |        0.8000 | 0.7009; 0.7843; 0.7035; 0.8000; 0.7425 |          0.8097 |         0.0456 |         0.7682 |         0.8659 | 0.7752; 0.8659; 0.7682; 0.8515; 0.7877 | {"model_name": "alfaneo/jurisbert-base-portuguese-uncased", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}  |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |         0.7928 |        0.0694 |        0.7213 |        0.8976 | 0.7387; 0.8041; 0.7213; 0.8976; 0.8023 |          0.8237 |         0.0438 |         0.7574 |         0.8642 | 0.8041; 0.8642; 0.7574; 0.8361; 0.8568 | {"model_name": "alfaneo/bertimbaulaw-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320} |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |         0.8386 |        0.0511 |        0.7735 |        0.9147 | 0.8226; 0.8333; 0.8491; 0.9147; 0.7735 |          0.8809 |         0.0104 |         0.8708 |         0.8952 | 0.8713; 0.8952; 0.8867; 0.8804; 0.8708 | {"model_name": "raquelsilveira/legalbertpt_fp", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}              |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |         0.7534 |        0.0871 |        0.6011 |        0.8173 | 0.7840; 0.8173; 0.6011; 0.7970; 0.7674 |          0.8114 |         0.0893 |         0.6599 |         0.8947 | 0.8473; 0.8947; 0.6599; 0.8170; 0.8379 | {"model_name": "ulysses-camara/legal-bert-pt-br", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |         0.7570 |        0.0588 |        0.6593 |        0.8118 | 0.7603; 0.7925; 0.6593; 0.7611; 0.8118 |          0.8091 |         0.0787 |         0.7060 |         0.8848 | 0.8548; 0.8848; 0.7060; 0.7443; 0.8554 | {"model_name": "dominguesm/legal-bert-base-cased-ptbr", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}      |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |         0.7489 |        0.0618 |        0.6797 |        0.8333 | 0.7455; 0.7835; 0.7027; 0.8333; 0.6797 |          0.7726 |         0.0672 |         0.6753 |         0.8453 | 0.8068; 0.8453; 0.7354; 0.8003; 0.6753 | {"model_name": "dccmpmgfinalisticas/GovBERT-BR", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}             |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.7602 |                0.1625 |                0.4250 |                0.9138 |                0.6726 |               0.1814 |               0.3639 |               0.8779 |
| supervised         |                 0.8349 |                0.0344 |                0.7741 |                0.8821 |                0.7754 |               0.0376 |               0.7211 |               0.8353 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.8284 |      0.8245 |         0.6667 |          0.7910 |
| BERTimbau-large      |  0.8281 |      0.8417 |         0.8214 |          0.7591 |
| BERTimbauLaw         |  0.8542 |      0.7983 |         0.1714 |          0.7500 |
| BiLSTM-CRF           |  0.7532 |      0.8000 |         0.3500 |          0.5818 |
| DeepSeek-V4-Flash    |  0.9074 |      0.8490 |         0.9032 |          0.8226 |
| GPT-4.1              |  0.8653 |      0.7509 |         0.8955 |          0.7794 |
| GPT-4.1-mini         |  0.8602 |      0.6767 |         0.7826 |          0.7634 |
| GPT-4.1-nano         |  0.7269 |      0.3439 |         0.1103 |          0.6241 |
| GPT-5-mini           |  0.8084 |      0.2421 |         0.7073 |          0.7586 |
| GPT-5.1              |  0.8635 |      0.6865 |         0.9062 |          0.7883 |
| GPT-5.2              |  0.8208 |      0.5805 |         0.9206 |          0.6974 |
| GovBERT-BR           |  0.7990 |      0.7788 |         0.0606 |          0.7031 |
| JurisBERT            |  0.7892 |      0.7373 |         0.4583 |          0.7407 |
| Legal-BERT-STF       |  0.8173 |      0.7623 |         0.2222 |          0.6992 |
| Legal-BERTimbau-base |  0.8293 |      0.7923 |         0.3500 |          0.7133 |
| LegalBERTPT-br       |  0.7547 |      0.7807 |         0.5116 |          0.7619 |
| LegalBert-pt         |  0.8607 |      0.8127 |         0.7869 |          0.8235 |
| Llama-3.3-70B        |  0.4196 |      0.4264 |         0.1622 |          0.0588 |
| Qwen2.5-72B          |  0.8402 |      0.6254 |         0.4561 |          0.7338 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                                  | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:-------------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4.1_few_shot                                       | GPT-4.1              | MULTA         |      0.8033 |   0.9378 | 0.8653 |       196 |          209 |          244 |
| gpt-4.1_few_shot                                       | GPT-4.1              | OBRIGACAO     |      0.6710 |   0.8525 | 0.7509 |       104 |          122 |          155 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RECOMENDACAO  |      0.8571 |   0.9375 | 0.8955 |        30 |           32 |           35 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RESSARCIMENTO |      0.7571 |   0.8030 | 0.7794 |        53 |           66 |           70 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | MULTA         |      0.7812 |   0.9569 | 0.8602 |       200 |          209 |          256 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | OBRIGACAO     |      0.5359 |   0.9180 | 0.6767 |       112 |          122 |          209 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RECOMENDACAO  |      0.7297 |   0.8438 | 0.7826 |        27 |           32 |           37 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RESSARCIMENTO |      0.7692 |   0.7576 | 0.7634 |        50 |           66 |           65 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | MULTA         |      0.7040 |   0.7512 | 0.7269 |       157 |          209 |          223 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | OBRIGACAO     |      0.2539 |   0.5328 | 0.3439 |        65 |          122 |          256 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RECOMENDACAO  |      0.0708 |   0.2500 | 0.1103 |         8 |           32 |          113 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RESSARCIMENTO |      0.5867 |   0.6667 | 0.6241 |        44 |           66 |           75 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | MULTA         |      0.7218 |   0.9187 | 0.8084 |       192 |          209 |          266 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | OBRIGACAO     |      0.1382 |   0.9754 | 0.2421 |       119 |          122 |          861 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RECOMENDACAO  |      0.5800 |   0.9062 | 0.7073 |        29 |           32 |           50 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RESSARCIMENTO |      0.6962 |   0.8333 | 0.7586 |        55 |           66 |           79 |
| gpt-5.1_few_shot                                       | GPT-5.1              | MULTA         |      0.8109 |   0.9234 | 0.8635 |       193 |          209 |          238 |
| gpt-5.1_few_shot                                       | GPT-5.1              | OBRIGACAO     |      0.5746 |   0.8525 | 0.6865 |       104 |          122 |          181 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RECOMENDACAO  |      0.9062 |   0.9062 | 0.9062 |        29 |           32 |           32 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RESSARCIMENTO |      0.7606 |   0.8182 | 0.7883 |        54 |           66 |           71 |
| gpt-5.2_few_shot                                       | GPT-5.2              | MULTA         |      0.7269 |   0.9426 | 0.8208 |       197 |          209 |          271 |
| gpt-5.2_few_shot                                       | GPT-5.2              | OBRIGACAO     |      0.4280 |   0.9016 | 0.5805 |       110 |          122 |          257 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RECOMENDACAO  |      0.9355 |   0.9062 | 0.9206 |        29 |           32 |           31 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RESSARCIMENTO |      0.6163 |   0.8030 | 0.6974 |        53 |           66 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | MULTA         |      0.9009 |   0.9139 | 0.9074 |       191 |          209 |          212 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | OBRIGACAO     |      0.8455 |   0.8525 | 0.8490 |       104 |          122 |          123 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RECOMENDACAO  |      0.9333 |   0.8750 | 0.9032 |        28 |           32 |           30 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RESSARCIMENTO |      0.8793 |   0.7727 | 0.8226 |        51 |           66 |           58 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | MULTA         |      0.7792 |   0.2871 | 0.4196 |        60 |          209 |           77 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | OBRIGACAO     |      0.5600 |   0.3443 | 0.4264 |        42 |          122 |           75 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RECOMENDACAO  |      0.6000 |   0.0938 | 0.1622 |         3 |           32 |            5 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RESSARCIMENTO |      1.0000 |   0.0303 | 0.0588 |         2 |           66 |            2 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | MULTA         |      0.8035 |   0.8804 | 0.8402 |       184 |          209 |          229 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | OBRIGACAO     |      0.5385 |   0.7459 | 0.6254 |        91 |          122 |          169 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RECOMENDACAO  |      0.3171 |   0.8125 | 0.4561 |        26 |           32 |           82 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RESSARCIMENTO |      0.6986 |   0.7727 | 0.7338 |        51 |           66 |           73 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | MULTA         |      0.8458 |   0.8134 | 0.8293 |       170 |          209 |          201 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | OBRIGACAO     |      0.7464 |   0.8443 | 0.7923 |       103 |          122 |          138 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RECOMENDACAO  |      0.8750 |   0.2188 | 0.3500 |         7 |           32 |            8 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RESSARCIMENTO |      0.6623 |   0.7727 | 0.7133 |        51 |           66 |           77 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | MULTA         |      0.8492 |   0.8086 | 0.8284 |       169 |          209 |          199 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | OBRIGACAO     |      0.8211 |   0.8279 | 0.8245 |       101 |          122 |          123 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RECOMENDACAO  |      0.8947 |   0.5312 | 0.6667 |        17 |           32 |           19 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RESSARCIMENTO |      0.7794 |   0.8030 | 0.7910 |        53 |           66 |           68 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | MULTA         |      0.8382 |   0.8182 | 0.8281 |       171 |          209 |          204 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | OBRIGACAO     |      0.8559 |   0.8279 | 0.8417 |       101 |          122 |          118 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RECOMENDACAO  |      0.9583 |   0.7188 | 0.8214 |        23 |           32 |           24 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RESSARCIMENTO |      0.7324 |   0.7879 | 0.7591 |        52 |           66 |           71 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | MULTA         |      0.8239 |   0.6938 | 0.7532 |       145 |          209 |          176 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | OBRIGACAO     |      0.8738 |   0.7377 | 0.8000 |        90 |          122 |          103 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RECOMENDACAO  |      0.8750 |   0.2188 | 0.3500 |         7 |           32 |            8 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RESSARCIMENTO |      0.7273 |   0.4848 | 0.5818 |        32 |           66 |           44 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | MULTA         |      0.8090 |   0.7703 | 0.7892 |       161 |          209 |          199 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | OBRIGACAO     |      0.7632 |   0.7131 | 0.7373 |        87 |          122 |          114 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RECOMENDACAO  |      0.6875 |   0.3438 | 0.4583 |        11 |           32 |           16 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RESSARCIMENTO |      0.7246 |   0.7576 | 0.7407 |        50 |           66 |           69 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | MULTA         |      0.9176 |   0.7990 | 0.8542 |       167 |          209 |          182 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | OBRIGACAO     |      0.8378 |   0.7623 | 0.7983 |        93 |          122 |          111 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RECOMENDACAO  |      1.0000 |   0.0938 | 0.1714 |         3 |           32 |            3 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RESSARCIMENTO |      0.7742 |   0.7273 | 0.7500 |        48 |           66 |           62 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | MULTA         |      0.8964 |   0.8278 | 0.8607 |       173 |          209 |          193 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | OBRIGACAO     |      0.7907 |   0.8361 | 0.8127 |       102 |          122 |          129 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RECOMENDACAO  |      0.8276 |   0.7500 | 0.7869 |        24 |           32 |           29 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RESSARCIMENTO |      0.8000 |   0.8485 | 0.8235 |        56 |           66 |           70 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | MULTA         |      0.7442 |   0.7656 | 0.7547 |       160 |          209 |          215 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | OBRIGACAO     |      0.8396 |   0.7295 | 0.7807 |        89 |          122 |          106 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RECOMENDACAO  |      1.0000 |   0.3438 | 0.5116 |        11 |           32 |           11 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RESSARCIMENTO |      0.8000 |   0.7273 | 0.7619 |        48 |           66 |           60 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | MULTA         |      0.8213 |   0.8134 | 0.8173 |       170 |          209 |          207 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | OBRIGACAO     |      0.8416 |   0.6967 | 0.7623 |        85 |          122 |          101 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RECOMENDACAO  |      1.0000 |   0.1250 | 0.2222 |         4 |           32 |            4 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RESSARCIMENTO |      0.7544 |   0.6515 | 0.6992 |        43 |           66 |           57 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | MULTA         |      0.8533 |   0.7512 | 0.7990 |       157 |          209 |          184 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | OBRIGACAO     |      0.9419 |   0.6639 | 0.7788 |        81 |          122 |           86 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RECOMENDACAO  |      1.0000 |   0.0312 | 0.0606 |         1 |           32 |            1 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RESSARCIMENTO |      0.7258 |   0.6818 | 0.7031 |        45 |           66 |           62 |

## E. Custo-benefício

Custo de inferência por documento a partir das contagens de tokens registradas pela API (`meta`), aos preços de tabela do Azure (Global Standard, Brazil South, API de preços de varejo, consulta em 2026-10-11). Sem `meta`, o modelo fica sem custo. `no_cache` cobra todo o prompt pela tarifa de entrada; `cached` estima o prefixo comum (instruções e exemplos) pela tarifa de cache. Supervisionados: minutos por partição (treino e inferência) em Apple Silicon local.

| model                                                  | display              | paradigm   |   n_docs |   n_docs_with_tokens |   mean_prompt_tokens |   mean_completion_tokens |   shared_prefix_tokens |   price_input_per_1M |   price_cached_per_1M |   price_output_per_1M |   cost_per_doc_no_cache |   cost_corpus_no_cache |   cost_per_doc_cached |   cost_corpus_cached | price_date   |   minutes_per_fold_train_and_infer |
|:-------------------------------------------------------|:---------------------|:-----------|---------:|---------------------:|---------------------:|-------------------------:|-----------------------:|---------------------:|----------------------:|----------------------:|------------------------:|-----------------------:|----------------------:|---------------------:|:-------------|-----------------------------------:|
| gpt-4.1_few_shot                                       | GPT-4.1              | LLM        |      861 |             861.0000 |            9044.8630 |                  81.1301 |              8876.0000 |               2.0000 |                0.5000 |                8.0000 |                  0.0187 |                16.1341 |                0.0054 |               4.6707 | 2026-10-11   |                           nan      |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | LLM        |      861 |             861.0000 |            9044.8630 |                  82.9675 |              8876.0000 |               0.4000 |                0.1000 |                1.6000 |                  0.0038 |                 3.2293 |                0.0011 |               0.9367 | 2026-10-11   |                           nan      |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | LLM        |      861 |             861.0000 |            9044.8630 |                  82.9350 |              8876.0000 |               0.1000 |                0.0250 |                0.4000 |                  0.0009 |                 0.8073 |                0.0003 |               0.2342 | 2026-10-11   |                           nan      |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | LLM        |      861 |               0.0000 |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                           nan      |
| gpt-5.1_few_shot                                       | GPT-5.1              | LLM        |      861 |               0.0000 |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                           nan      |
| gpt-5.2_few_shot                                       | GPT-5.2              | LLM        |      861 |               0.0000 |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                           nan      |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | LLM        |      861 |             861.0000 |           11606.4437 |                 103.5958 |             11411.0000 |               0.1900 |                0.0280 |                0.5100 |                  0.0023 |                 1.9442 |                0.0004 |               0.3526 | 2026-10-11   |                           nan      |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | LLM        |      861 |               0.0000 |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                           nan      |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | LLM        |      861 |               0.0000 |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                           nan      |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.2845 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            17.0170 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            47.2912 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                             8.3254 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            13.8741 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.3325 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.9287 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            18.0454 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.7596 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.7311 |

## F. Function calling vs JSON schema

**Métricas overall:**

| model             | method           |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | function_calling |     0.9187 |    0.8837 |          0.8749 |           0.8910 |        0.8765 |
| deepseek-v4-flash | json_schema      |     0.9096 |    0.8702 |          0.8608 |           0.8732 |        0.8671 |
| gpt-4.1           | function_calling |     0.8856 |    0.8341 |          0.8367 |           0.7756 |        0.9021 |
| gpt-4.1           | json_schema      |     0.8981 |    0.8317 |          0.8359 |           0.7785 |        0.8928 |

**Δ por modelo (FC − JS):**

| model             |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:------------------|-----------------:|----------------:|-----------------------:|--------------------:|
| deepseek-v4-flash |           0.0091 |          0.0135 |                 0.0178 |              0.0093 |
| gpt-4.1           |          -0.0125 |          0.0023 |                -0.0029 |              0.0093 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9187 |      0.8455 |         0.9032 |          0.8320 |
| deepseek-v4-flash | json_schema      |  0.9095 |      0.8306 |         0.9032 |          0.8000 |
| gpt-4.1           | function_calling |  0.8761 |      0.7737 |         0.9231 |          0.7737 |
| gpt-4.1           | json_schema      |  0.8698 |      0.7715 |         0.9231 |          0.7794 |

**Span Precision (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9187 |      0.8387 |         0.9333 |          0.8814 |
| deepseek-v4-flash | json_schema      |  0.9052 |      0.8175 |         0.9333 |          0.8475 |
| gpt-4.1           | function_calling |  0.8148 |      0.6974 |         0.9091 |          0.7465 |
| gpt-4.1           | json_schema      |  0.8074 |      0.7103 |         0.9091 |          0.7571 |

**Span Recall (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9187 |      0.8525 |         0.8750 |          0.7879 |
| deepseek-v4-flash | json_schema      |  0.9139 |      0.8443 |         0.8750 |          0.7576 |
| gpt-4.1           | function_calling |  0.9474 |      0.8689 |         0.9375 |          0.8030 |
| gpt-4.1           | json_schema      |  0.9426 |      0.8443 |         0.9375 |          0.8030 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model             | technique   |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | cot         |     0.9026 |    0.8287 |          0.7648 |           0.7663 |        0.9021 |
| deepseek-v4-flash | few_shot    |     0.9138 |    0.8779 |          0.8705 |           0.8842 |        0.8718 |
| deepseek-v4-flash | two_stage   |     0.9128 |    0.8725 |          0.8615 |           0.8756 |        0.8695 |
| gpt-4.1           | cot         |     0.8808 |    0.8239 |          0.8313 |           0.7598 |        0.8998 |
| gpt-4.1           | few_shot    |     0.8863 |    0.8210 |          0.8228 |           0.7599 |        0.8928 |
| gpt-4.1           | two_stage   |     0.8882 |    0.8328 |          0.8347 |           0.7751 |        0.8998 |
| gpt-5.2           | cot         |     0.8638 |    0.7710 |          0.8112 |           0.6584 |        0.9301 |
| gpt-5.2           | few_shot    |     0.8343 |    0.7244 |          0.7548 |           0.6031 |        0.9068 |
| gpt-5.2           | two_stage   |     0.8634 |    0.7803 |          0.8022 |           0.6849 |        0.9068 |
| llama-3.3-70b     | cot         |     0.3033 |    0.2594 |          0.1590 |           0.6699 |        0.1608 |
| llama-3.3-70b     | few_shot    |     0.4250 |    0.3639 |          0.2667 |           0.6730 |        0.2494 |
| llama-3.3-70b     | two_stage   |     0.1707 |    0.1443 |          0.1359 |           0.6250 |        0.0816 |
| qwen2.5-72b       | cot         |     0.8272 |    0.7390 |          0.6804 |           0.6490 |        0.8578 |
| qwen2.5-72b       | few_shot    |     0.7917 |    0.7169 |          0.6639 |           0.6365 |        0.8205 |
| qwen2.5-72b       | two_stage   |     0.8157 |    0.7360 |          0.6830 |           0.6642 |        0.8252 |

**Span F1 pivotado (modelo × técnica):**

| model             |    cot |   few_shot |   two_stage |
|:------------------|-------:|-----------:|------------:|
| deepseek-v4-flash | 0.8287 |     0.8779 |      0.8725 |
| gpt-4.1           | 0.8239 |     0.8210 |      0.8328 |
| gpt-5.2           | 0.7710 |     0.7244 |      0.7803 |
| llama-3.3-70b     | 0.2594 |     0.3639 |      0.1443 |
| qwen2.5-72b       | 0.7390 |     0.7169 |      0.7360 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique   | token_f1           | token_f1.1          | token_f1.2          | token_f1.3         | span_f1            | span_f1.1           | span_f1.2           | span_f1.3          |
|:------------|:-------------------|:--------------------|:--------------------|:-------------------|:-------------------|:--------------------|:--------------------|:-------------------|
| nan         | mean               | std                 | min                 | max                | mean               | std                 | min                 | max                |
| cot         | 0.7555601425124395 | 0.2543140554759454  | 0.303311607084074   | 0.9026392018023817 | 0.6843937371363374 | 0.24051368534337597 | 0.2593984962406015  | 0.8286937901498929 |
| few_shot    | 0.7702066458678389 | 0.1986583553378734  | 0.4249586528341603  | 0.9138034462073102 | 0.7008372832088667 | 0.2000708313917981  | 0.3639455782312925  | 0.8779342723004695 |
| two_stage   | 0.7301597917797482 | 0.31478827475090404 | 0.17072549233737397 | 0.9128190243194494 | 0.6731892469667505 | 0.30013288589651926 | 0.14432989690721648 | 0.8725146198830408 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9296 |      0.8118 |         0.5179 |          0.8000 |
| deepseek-v4-flash | few_shot    |  0.9074 |      0.8490 |         0.9032 |          0.8226 |
| deepseek-v4-flash | two_stage   |  0.9074 |      0.8536 |         0.9032 |          0.7820 |
| gpt-4.1           | cot         |  0.8711 |      0.7456 |         0.9231 |          0.7852 |
| gpt-4.1           | few_shot    |  0.8653 |      0.7509 |         0.8955 |          0.7794 |
| gpt-4.1           | two_stage   |  0.8736 |      0.7709 |         0.9091 |          0.7852 |
| gpt-5.2           | cot         |  0.8772 |      0.5922 |         0.9206 |          0.8550 |
| gpt-5.2           | few_shot    |  0.8208 |      0.5805 |         0.9206 |          0.6974 |
| gpt-5.2           | two_stage   |  0.8534 |      0.6548 |         0.9206 |          0.7801 |
| llama-3.3-70b     | cot         |  0.3373 |      0.2989 |         0.0000 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.4196 |      0.4264 |         0.1622 |          0.0588 |
| llama-3.3-70b     | two_stage   |  0.1525 |      0.1655 |         0.1667 |          0.0588 |
| qwen2.5-72b       | cot         |  0.8629 |      0.6577 |         0.4685 |          0.7324 |
| qwen2.5-72b       | few_shot    |  0.8402 |      0.6254 |         0.4561 |          0.7338 |
| qwen2.5-72b       | two_stage   |  0.8552 |      0.6458 |         0.5455 |          0.6857 |

**Span Precision por entidade (mesmo eixo):**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9124 |      0.7383 |         0.3625 |          0.8475 |
| deepseek-v4-flash | few_shot    |  0.9009 |      0.8455 |         0.9333 |          0.8793 |
| deepseek-v4-flash | two_stage   |  0.9009 |      0.8718 |         0.9333 |          0.7761 |
| gpt-4.1           | cot         |  0.8133 |      0.6485 |         0.9091 |          0.7681 |
| gpt-4.1           | few_shot    |  0.8033 |      0.6710 |         0.8571 |          0.7571 |
| gpt-4.1           | two_stage   |  0.8140 |      0.6928 |         0.8824 |          0.7681 |
| gpt-5.2           | cot         |  0.8097 |      0.4335 |         0.9355 |          0.8615 |
| gpt-5.2           | few_shot    |  0.7269 |      0.4280 |         0.9355 |          0.6163 |
| gpt-5.2           | two_stage   |  0.7863 |      0.5140 |         0.9355 |          0.7333 |
| llama-3.3-70b     | cot         |  0.9348 |      0.5000 |         0.0000 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.7792 |      0.5600 |         0.6000 |          1.0000 |
| llama-3.3-70b     | two_stage   |  0.6667 |      0.5217 |         0.7500 |          1.0000 |
| qwen2.5-72b       | cot         |  0.8136 |      0.5568 |         0.3291 |          0.6842 |
| qwen2.5-72b       | few_shot    |  0.8035 |      0.5385 |         0.3171 |          0.6986 |
| qwen2.5-72b       | two_stage   |  0.8230 |      0.5602 |         0.4030 |          0.6486 |

**Span Recall por entidade:**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9474 |      0.9016 |         0.9062 |          0.7576 |
| deepseek-v4-flash | few_shot    |  0.9139 |      0.8525 |         0.8750 |          0.7727 |
| deepseek-v4-flash | two_stage   |  0.9139 |      0.8361 |         0.8750 |          0.7879 |
| gpt-4.1           | cot         |  0.9378 |      0.8770 |         0.9375 |          0.8030 |
| gpt-4.1           | few_shot    |  0.9378 |      0.8525 |         0.9375 |          0.8030 |
| gpt-4.1           | two_stage   |  0.9426 |      0.8689 |         0.9375 |          0.8030 |
| gpt-5.2           | cot         |  0.9569 |      0.9344 |         0.9062 |          0.8485 |
| gpt-5.2           | few_shot    |  0.9426 |      0.9016 |         0.9062 |          0.8030 |
| gpt-5.2           | two_stage   |  0.9330 |      0.9016 |         0.9062 |          0.8333 |
| llama-3.3-70b     | cot         |  0.2057 |      0.2131 |         0.0000 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.2871 |      0.3443 |         0.0938 |          0.0303 |
| llama-3.3-70b     | two_stage   |  0.0861 |      0.0984 |         0.0938 |          0.0303 |
| qwen2.5-72b       | cot         |  0.9187 |      0.8033 |         0.8125 |          0.7879 |
| qwen2.5-72b       | few_shot    |  0.8804 |      0.7459 |         0.8125 |          0.7727 |
| qwen2.5-72b       | two_stage   |  0.8900 |      0.7623 |         0.8438 |          0.7273 |

## I. Análise de erros do melhor modelo

**Melhor modelo identificado por span F1: DeepSeek-V4-Flash.**

**Contagens por tipo de erro:**

| kind       |   count |
|:-----------|--------:|
| match      |     374 |
| boundary   |      37 |
| FN_overlap |      29 |
| FN_no_pred |      26 |
| FP         |       8 |
| type_error |       4 |

**Matriz rótulo × tipo de erro:**

| label         |   FN_no_pred |   FN_overlap |   FP |   boundary |   match |   type_error |
|:--------------|-------------:|-------------:|-----:|-----------:|--------:|-------------:|
| MULTA         |            6 |           12 |    1 |         11 |     191 |            0 |
| OBRIGACAO     |            8 |           10 |    6 |         12 |     104 |            0 |
| RECOMENDACAO  |            4 |            0 |    1 |          1 |      28 |            0 |
| RESSARCIMENTO |            8 |            7 |    0 |         13 |      51 |            4 |

**Pares de tipo errado (gold → pred):**

| label         | pred_label   |   count |
|:--------------|:-------------|--------:|
| RESSARCIMENTO | MULTA        |       4 |

**Histograma de IoU para erros de fronteira:**

|   bin_low |   bin_high |   count |
|----------:|-----------:|--------:|
|    0.0000 |     0.2000 |  3.0000 |
|    0.2000 |     0.4000 | 20.0000 |
|    0.4000 |     0.5000 | 14.0000 |
|    0.5000 |     0.7000 |  0.0000 |
|    0.7000 |     0.9000 |  0.0000 |
|    0.9000 |     1.0000 |  0.0000 |

## J. Significância estatística (bootstrap pareado)

**Item 41 — N de reamostragens**: 10.000.

**Item 42 — IC 95% por modelo:**

| model                                                  | display              |   span_f1_point |   span_f1_micro |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:-------------------------------------------------------|:---------------------|----------------:|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |          0.8705 |          0.8779 |         0.8696 |        0.0203 |     0.8285 |     0.9068 |     0.0784 |
| gpt-4.1_few_shot                                       | GPT-4.1              |          0.8228 |          0.8210 |         0.8220 |        0.0217 |     0.7781 |     0.8627 |     0.0846 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.8210 |          0.8353 |         0.8205 |        0.0236 |     0.7722 |     0.8645 |     0.0923 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.8126 |          0.8203 |         0.8116 |        0.0250 |     0.7596 |     0.8584 |     0.0988 |
| gpt-5.1_few_shot                                       | GPT-5.1              |          0.8111 |          0.7992 |         0.8102 |        0.0213 |     0.7673 |     0.8506 |     0.0833 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.7777 |          0.8115 |         0.7758 |        0.0290 |     0.7153 |     0.8289 |     0.1136 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |          0.7707 |          0.7811 |         0.7694 |        0.0250 |     0.7179 |     0.8162 |     0.0983 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.7548 |          0.7244 |         0.7543 |        0.0220 |     0.7095 |     0.7955 |     0.0860 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.7022 |          0.7503 |         0.7000 |        0.0335 |     0.6314 |     0.7619 |     0.1305 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.6814 |          0.7473 |         0.6788 |        0.0349 |     0.6086 |     0.7456 |     0.1370 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.6712 |          0.7761 |         0.6693 |        0.0315 |     0.6048 |     0.7279 |     0.1231 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.6639 |          0.7169 |         0.6628 |        0.0245 |     0.6134 |     0.7091 |     0.0957 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.6435 |          0.7903 |         0.6425 |        0.0290 |     0.5884 |     0.7010 |     0.1126 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.6291 |          0.4688 |         0.6280 |        0.0218 |     0.5839 |     0.6687 |     0.0848 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.6253 |          0.7569 |         0.6229 |        0.0340 |     0.5576 |     0.6912 |     0.1336 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.6213 |          0.7211 |         0.6188 |        0.0350 |     0.5482 |     0.6844 |     0.1362 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.5854 |          0.7454 |         0.5842 |        0.0238 |     0.5376 |     0.6309 |     0.0933 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.4513 |          0.5000 |         0.4516 |        0.0235 |     0.4043 |     0.4979 |     0.0936 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2667 |          0.3639 |         0.2662 |        0.0303 |     0.2103 |     0.3290 |     0.1187 |

**Itens 43–46 — Pares destacados:**

| model_a                                            | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm_all |   p_bonferroni_all |   p_bh_all | sig_holm_all_5pct   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:---------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|-------------:|-------------------:|-----------:|:--------------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| bilstm-crf__supervised                             | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF        | LegalBert-pt      | 0.6213 | 0.8210 |   -0.2017 |    -0.2737 |    -0.1330 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.7777 | 0.6435 |    0.1333 |     0.0632 |     0.1982 |    0.0002 | True             |       0.0154 |             0.0342 |     0.0004 | True                |   0.0020 |         0.0024 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.8705 | 0.7777 |    0.0938 |     0.0321 |     0.1598 |    0.0020 | True             |       0.1260 |             0.3420 |     0.0031 | False               |   0.0160 |         0.0240 | True            | True                  |            12 |
| gpt-4.1_few_shot                                   | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.8228 | 0.7548 |    0.0678 |     0.0306 |     0.1068 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash | BERTimbau-large   | 0.8705 | 0.8126 |    0.0580 |     0.0015 |     0.1145 |    0.0452 | True             |       1.0000 |             1.0000 |     0.0634 | False               |   0.2712 |         0.5424 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.8228 | 0.7707 |    0.0526 |     0.0187 |     0.0897 |    0.0010 | True             |       0.0710 |             0.1710 |     0.0017 | False               |   0.0090 |         0.0120 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.8705 | 0.8210 |    0.0491 |    -0.0040 |     0.1031 |    0.0700 | False            |       1.0000 |             1.0000 |     0.0935 | False               |   0.2900 |         0.8400 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.8228 | 0.8705 |   -0.0476 |    -0.0800 |    -0.0164 |    0.0024 | True             |       0.1488 |             0.4104 |     0.0037 | False               |   0.0168 |         0.0288 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.7777 | 0.8210 |   -0.0447 |    -0.0959 |     0.0013 |    0.0580 | False            |       1.0000 |             1.0000 |     0.0793 | False               |   0.2900 |         0.6960 | False           | False                 |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base    | BERTimbau-large   | 0.7777 | 0.8126 |   -0.0358 |    -0.0830 |     0.0077 |    0.1156 | False            |       1.0000 |             1.0000 |     0.1464 | False               |   0.3468 |         1.0000 | False           | False                 |            12 |
| neuralmind_bert-large-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large   | LegalBert-pt      | 0.8126 | 0.8210 |   -0.0089 |    -0.0563 |     0.0383 |    0.7042 | False            |       1.0000 |             1.0000 |     0.7433 | False               |   1.0000 |         1.0000 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1           | LegalBert-pt      | 0.8228 | 0.8210 |    0.0015 |    -0.0507 |     0.0536 |    0.9584 | False            |       1.0000 |             1.0000 |     0.9584 | False               |   1.0000 |         1.0000 | False           | False                 |            12 |

**Itens 47–48 — Resumo:**

| metric                         | value                   |
|:-------------------------------|:------------------------|
| resampling_unit                | document                |
| n_docs_resampled               | 861                     |
| n_total_pairs                  | 171                     |
| n_significant_5pct_uncorrected | 124                     |
| n_sig_holm_all                 | 100                     |
| n_sig_bonferroni_all           | 97                      |
| n_sig_bh_all                   | 120                     |
| highlighted_family_size        | 12                      |
| highlighted_n_sig_uncorrected  | 7                       |
| highlighted_n_sig_holm         | 6                       |
| highlighted_n_sig_bonferroni   | 6                       |
| highlighted_n_sig_holm_all     | 3                       |
| smallest_significant_abs_diff  | 0.04080132418983096     |
| smallest_significant_pair      | GPT-4.1-mini vs GPT-5.1 |
| leader_model                   | DeepSeek-V4-Flash       |
| leader_group_size_holm         | 6                       |

**p48a — Correção para múltiplas comparações.** A família inferencial é o conjunto completo dos pares (`p_holm_all`, `p_bonferroni_all`, `p_bh_all`), pré-especificado por construção; os pares destacados acima são uma seleção para leitura e herdam esses valores. As colunas `p_holm`/`p_bonferroni` (correção restrita aos destacados) são mantidas apenas como referência.

**Grupo do líder (DS-p.55a).** Comparações líder × demais modelos, com o `p_holm` da família completa de pares; `in_leader_group=True` marca os modelos estatisticamente indistinguíveis do líder a 5% — a fonte do marcador (†) na tabela geral de resultados:

| model                                                  | display              |   span_f1 |   diff_vs_leader |    p_raw |   p_holm | in_leader_group   |
|:-------------------------------------------------------|:---------------------|----------:|-----------------:|---------:|---------:|:------------------|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |    0.8705 |           0.0000 | nan      | nan      | True              |
| gpt-4.1_few_shot                                       | GPT-4.1              |    0.8228 |           0.0476 |   0.0024 |   0.1488 | True              |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.8210 |           0.0491 |   0.0700 |   1.0000 | True              |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.8126 |           0.0580 |   0.0452 |   1.0000 | True              |
| gpt-5.1_few_shot                                       | GPT-5.1              |    0.8111 |           0.0594 |   0.0010 |   0.0710 | True              |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.7777 |           0.0938 |   0.0020 |   0.1260 | True              |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |    0.7707 |           0.1002 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.7548 |           0.1153 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.7022 |           0.1696 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.6814 |           0.1908 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.6712 |           0.2003 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.6639 |           0.2068 |   0.0000 |   0.0000 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.6435 |           0.2271 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.6291 |           0.2416 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.6253 |           0.2467 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.6213 |           0.2508 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.5854 |           0.2854 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.4513 |           0.4180 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2667 |           0.6034 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm_all |   p_bonferroni_all |   p_bh_all | sig_holm_all_5pct   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|-------------:|-------------------:|-----------:|:--------------------|
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.8705 | 0.2667 |    0.6034 |     0.5310 |     0.6684 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.8228 | 0.2667 |    0.5558 |     0.4815 |     0.6240 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2667 | 0.8210 |   -0.5543 |    -0.6250 |    -0.4758 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2667 | 0.8126 |   -0.5454 |    -0.6171 |    -0.4689 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.8111 | 0.2667 |    0.5440 |     0.4688 |     0.6120 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2667 | 0.7777 |   -0.5096 |    -0.5873 |    -0.4257 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.7707 | 0.2667 |    0.5032 |     0.4173 |     0.5804 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.7548 | 0.2667 |    0.4880 |     0.4143 |     0.5573 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2667 | 0.7022 |   -0.4338 |    -0.5197 |    -0.3436 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.4513 | 0.8705 |   -0.4180 |    -0.4735 |    -0.3629 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2667 | 0.6814 |   -0.4126 |    -0.5027 |    -0.3130 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2667 | 0.6712 |   -0.4031 |    -0.4822 |    -0.3173 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2667 | 0.6639 |   -0.3966 |    -0.4712 |    -0.3136 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2667 | 0.6435 |   -0.3763 |    -0.4585 |    -0.2939 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.8228 | 0.4513 |    0.3704 |     0.3176 |     0.4239 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.4513 | 0.8210 |   -0.3689 |    -0.4238 |    -0.3139 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.6291 | 0.2667 |    0.3617 |     0.2820 |     0.4341 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.4513 | 0.8126 |   -0.3600 |    -0.4108 |    -0.3080 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.4513 | 0.8111 |   -0.3586 |    -0.4132 |    -0.3046 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2667 | 0.6253 |   -0.3566 |    -0.4454 |    -0.2669 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2667 | 0.6213 |   -0.3525 |    -0.4332 |    -0.2663 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.4513 | 0.7777 |   -0.3242 |    -0.3858 |    -0.2599 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2667 | 0.5854 |   -0.3180 |    -0.3910 |    -0.2400 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.7707 | 0.4513 |    0.3178 |     0.2654 |     0.3721 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.4513 | 0.7548 |   -0.3026 |    -0.3498 |    -0.2567 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.8705 | 0.5854 |    0.2854 |     0.2304 |     0.3393 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.8705 | 0.6213 |    0.2508 |     0.1823 |     0.3220 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.4513 | 0.7022 |   -0.2484 |    -0.3115 |    -0.1791 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.8705 | 0.6253 |    0.2467 |     0.1751 |     0.3151 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.6291 | 0.8705 |   -0.2416 |    -0.2852 |    -0.2003 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.8228 | 0.5854 |    0.2379 |     0.1859 |     0.2890 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.8210 | 0.5854 |    0.2363 |     0.1907 |     0.2815 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.8126 | 0.5854 |    0.2274 |     0.1775 |     0.2754 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.4513 | 0.6814 |   -0.2272 |    -0.2976 |    -0.1545 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.8705 | 0.6435 |    0.2271 |     0.1623 |     0.2862 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.8111 | 0.5854 |    0.2260 |     0.1715 |     0.2797 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.4513 | 0.6712 |   -0.2177 |    -0.2791 |    -0.1546 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.4513 | 0.6639 |   -0.2112 |    -0.2658 |    -0.1583 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.8705 | 0.6639 |    0.2068 |     0.1621 |     0.2536 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.8228 | 0.6213 |    0.2033 |     0.1332 |     0.2753 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.6213 | 0.8210 |   -0.2017 |    -0.2737 |    -0.1330 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.8705 | 0.6712 |    0.2003 |     0.1373 |     0.2676 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.8228 | 0.6253 |    0.1992 |     0.1253 |     0.2691 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.8210 | 0.6253 |    0.1976 |     0.1293 |     0.2655 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.8228 | 0.6291 |    0.1941 |     0.1526 |     0.2374 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.8126 | 0.6213 |    0.1928 |     0.1253 |     0.2636 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.6291 | 0.8210 |   -0.1925 |    -0.2493 |    -0.1371 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.7777 | 0.5854 |    0.1917 |     0.1368 |     0.2464 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.8111 | 0.6213 |    0.1915 |     0.1202 |     0.2647 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.4513 | 0.6435 |   -0.1909 |    -0.2621 |    -0.1236 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.8705 | 0.6814 |    0.1908 |     0.1255 |     0.2609 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.8126 | 0.6253 |    0.1888 |     0.1197 |     0.2559 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.8111 | 0.6253 |    0.1874 |     0.1128 |     0.2590 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.4513 | 0.2667 |    0.1854 |     0.1070 |     0.2577 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.7707 | 0.5854 |    0.1852 |     0.1290 |     0.2393 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.6291 | 0.8126 |   -0.1836 |    -0.2413 |    -0.1254 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.6291 | 0.8111 |   -0.1823 |    -0.2242 |    -0.1433 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.8228 | 0.6435 |    0.1795 |     0.1099 |     0.2418 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.6435 | 0.8210 |   -0.1780 |    -0.2359 |    -0.1148 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.4513 | 0.6291 |   -0.1763 |    -0.2324 |    -0.1207 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.4513 | 0.6253 |   -0.1712 |    -0.2489 |    -0.0966 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.7548 | 0.5854 |    0.1701 |     0.1138 |     0.2249 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.8705 | 0.7022 |    0.1696 |     0.1037 |     0.2418 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.8126 | 0.6435 |    0.1691 |     0.1013 |     0.2301 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.8111 | 0.6435 |    0.1677 |     0.0981 |     0.2295 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.4513 | 0.6213 |   -0.1671 |    -0.2365 |    -0.0981 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.8228 | 0.6639 |    0.1592 |     0.1141 |     0.2051 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.6639 | 0.8210 |   -0.1577 |    -0.2159 |    -0.0996 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.7777 | 0.6213 |    0.1571 |     0.0868 |     0.2311 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.7777 | 0.6253 |    0.1530 |     0.0849 |     0.2221 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.8228 | 0.6712 |    0.1527 |     0.0876 |     0.2209 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.6712 | 0.8210 |   -0.1512 |    -0.2114 |    -0.0966 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.7707 | 0.6213 |    0.1507 |     0.0705 |     0.2309 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.6639 | 0.8126 |   -0.1488 |    -0.2090 |    -0.0862 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.6291 | 0.7777 |   -0.1479 |    -0.2084 |    -0.0856 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.8111 | 0.6639 |    0.1474 |     0.1027 |     0.1928 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.7707 | 0.6253 |    0.1466 |     0.0693 |     0.2197 |    0.0004 | True             |       0.0296 |             0.0684 |     0.0007 | True                |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.8228 | 0.6814 |    0.1433 |     0.0763 |     0.2129 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.6712 | 0.8126 |   -0.1423 |    -0.2051 |    -0.0815 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.6814 | 0.8210 |   -0.1417 |    -0.2061 |    -0.0801 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.7707 | 0.6291 |    0.1415 |     0.0968 |     0.1857 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.8111 | 0.6712 |    0.1409 |     0.0772 |     0.2079 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.7548 | 0.6213 |    0.1355 |     0.0601 |     0.2120 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.7777 | 0.6435 |    0.1333 |     0.0632 |     0.1982 |    0.0002 | True             |       0.0154 |             0.0342 |     0.0004 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.8126 | 0.6814 |    0.1328 |     0.0734 |     0.1943 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.4513 | 0.5854 |   -0.1326 |    -0.1842 |    -0.0808 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.8111 | 0.6814 |    0.1314 |     0.0628 |     0.2030 |    0.0002 | True             |       0.0154 |             0.0342 |     0.0004 | True                |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.7548 | 0.6253 |    0.1314 |     0.0591 |     0.2007 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.7707 | 0.6435 |    0.1269 |     0.0558 |     0.1907 |    0.0014 | True             |       0.0910 |             0.2394 |     0.0022 | False               |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.6291 | 0.7548 |   -0.1263 |    -0.1655 |    -0.0870 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.8228 | 0.7022 |    0.1220 |     0.0526 |     0.1953 |    0.0002 | True             |       0.0154 |             0.0342 |     0.0004 | True                |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.8210 | 0.7022 |    0.1205 |     0.0585 |     0.1869 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.7022 | 0.5854 |    0.1159 |     0.0367 |     0.1864 |    0.0048 | True             |       0.2880 |             0.8208 |     0.0073 | False               |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.7548 | 0.8705 |   -0.1153 |    -0.1565 |    -0.0757 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.6639 | 0.7777 |   -0.1130 |    -0.1796 |    -0.0441 |    0.0012 | True             |       0.0816 |             0.2052 |     0.0019 | False               |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.7548 | 0.6435 |    0.1117 |     0.0462 |     0.1716 |    0.0016 | True             |       0.1024 |             0.2736 |     0.0025 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.8126 | 0.7022 |    0.1116 |     0.0552 |     0.1728 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.8111 | 0.7022 |    0.1102 |     0.0427 |     0.1817 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.7707 | 0.6639 |    0.1066 |     0.0591 |     0.1520 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.6712 | 0.7777 |   -0.1065 |    -0.1716 |    -0.0442 |    0.0012 | True             |       0.0816 |             0.2052 |     0.0019 | False               |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.7707 | 0.8705 |   -0.1002 |    -0.1445 |    -0.0590 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.7707 | 0.6712 |    0.1001 |     0.0308 |     0.1695 |    0.0052 | True             |       0.3068 |             0.8892 |     0.0079 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.7777 | 0.6814 |    0.0970 |     0.0478 |     0.1509 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.6814 | 0.5854 |    0.0946 |     0.0387 |     0.1491 |    0.0012 | True             |       0.0816 |             0.2052 |     0.0019 | False               |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.8705 | 0.7777 |    0.0938 |     0.0321 |     0.1598 |    0.0020 | True             |       0.1260 |             0.3420 |     0.0031 | False               |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.7548 | 0.6639 |    0.0915 |     0.0444 |     0.1381 |    0.0004 | True             |       0.0296 |             0.0684 |     0.0007 | True                |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.7707 | 0.6814 |    0.0906 |     0.0229 |     0.1604 |    0.0068 | True             |       0.3944 |             1.0000 |     0.0102 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.6712 | 0.5854 |    0.0851 |     0.0355 |     0.1338 |    0.0010 | True             |       0.0710 |             0.1710 |     0.0017 | False               |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.7548 | 0.6712 |    0.0850 |     0.0219 |     0.1520 |    0.0090 | True             |       0.5130 |             1.0000 |     0.0134 | False               |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.6213 | 0.7022 |   -0.0813 |    -0.1570 |    -0.0005 |    0.0486 | True             |       1.0000 |             1.0000 |     0.0676 | False               |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.6639 | 0.5854 |    0.0786 |     0.0181 |     0.1375 |    0.0112 | True             |       0.6160 |             1.0000 |     0.0164 | False               |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.7022 | 0.6253 |    0.0772 |     0.0204 |     0.1395 |    0.0042 | True             |       0.2562 |             0.7182 |     0.0065 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.7777 | 0.7022 |    0.0758 |     0.0055 |     0.1481 |    0.0378 | True             |       1.0000 |             1.0000 |     0.0534 | False               |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.7548 | 0.6814 |    0.0755 |     0.0068 |     0.1460 |    0.0314 | True             |       1.0000 |             1.0000 |     0.0451 | False               |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.6291 | 0.7022 |   -0.0721 |    -0.1459 |     0.0046 |    0.0634 | False            |       1.0000 |             1.0000 |     0.0860 | False               |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.7707 | 0.7022 |    0.0694 |    -0.0037 |     0.1453 |    0.0640 | False            |       1.0000 |             1.0000 |     0.0862 | False               |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.8228 | 0.7548 |    0.0678 |     0.0306 |     0.1068 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.7548 | 0.8210 |   -0.0662 |    -0.1173 |    -0.0153 |    0.0126 | True             |       0.6804 |             1.0000 |     0.0183 | False               |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.6213 | 0.6814 |   -0.0600 |    -0.1328 |     0.0122 |    0.1032 | False            |       1.0000 |             1.0000 |     0.1337 | False               |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.8111 | 0.8705 |   -0.0594 |    -0.0942 |    -0.0246 |    0.0010 | True             |       0.0710 |             0.1710 |     0.0017 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.6435 | 0.5854 |    0.0583 |    -0.0046 |     0.1241 |    0.0734 | False            |       1.0000 |             1.0000 |     0.0973 | False               |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.8705 | 0.8126 |    0.0580 |     0.0015 |     0.1145 |    0.0452 | True             |       1.0000 |             1.0000 |     0.0634 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.6435 | 0.7022 |   -0.0575 |    -0.1250 |     0.0147 |    0.1098 | False            |       1.0000 |             1.0000 |     0.1401 | False               |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.7548 | 0.8126 |   -0.0573 |    -0.1072 |    -0.0050 |    0.0322 | True             |       1.0000 |             1.0000 |     0.0459 | False               |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.8111 | 0.7548 |    0.0560 |     0.0220 |     0.0928 |    0.0006 | True             |       0.0432 |             0.1026 |     0.0010 | True                |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.6814 | 0.6253 |    0.0559 |    -0.0064 |     0.1228 |    0.0764 | False            |       1.0000 |             1.0000 |     0.1005 | False               |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.7548 | 0.7022 |    0.0542 |    -0.0104 |     0.1241 |    0.1078 | False            |       1.0000 |             1.0000 |     0.1386 | False               |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.8228 | 0.7707 |    0.0526 |     0.0187 |     0.0897 |    0.0010 | True             |       0.0710 |             0.1710 |     0.0017 | False               |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.7707 | 0.8210 |   -0.0511 |    -0.1037 |    -0.0001 |    0.0492 | True             |       1.0000 |             1.0000 |     0.0678 | False               |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.6291 | 0.6814 |   -0.0508 |    -0.1203 |     0.0188 |    0.1564 | False            |       1.0000 |             1.0000 |     0.1910 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.6712 | 0.6213 |    0.0505 |    -0.0162 |     0.1154 |    0.1306 | False            |       1.0000 |             1.0000 |     0.1630 | False               |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.8705 | 0.8210 |    0.0491 |    -0.0040 |     0.1031 |    0.0700 | False            |       1.0000 |             1.0000 |     0.0935 | False               |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.8228 | 0.8705 |   -0.0476 |    -0.0800 |    -0.0164 |    0.0024 | True             |       0.1488 |             0.4104 |     0.0037 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.6712 | 0.6253 |    0.0465 |    -0.0397 |     0.1267 |    0.2742 | False            |       1.0000 |             1.0000 |     0.3279 | False               |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.8228 | 0.7777 |    0.0462 |    -0.0165 |     0.1127 |    0.1544 | False            |       1.0000 |             1.0000 |     0.1899 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.7777 | 0.8210 |   -0.0447 |    -0.0959 |     0.0013 |    0.0580 | False            |       1.0000 |             1.0000 |     0.0793 | False               |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.6639 | 0.6213 |    0.0440 |    -0.0371 |     0.1235 |    0.2612 | False            |       1.0000 |             1.0000 |     0.3145 | False               |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.6291 | 0.5854 |    0.0438 |    -0.0129 |     0.1010 |    0.1278 | False            |       1.0000 |             1.0000 |     0.1607 | False               |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.7707 | 0.8126 |   -0.0422 |    -0.0970 |     0.0138 |    0.1432 | False            |       1.0000 |             1.0000 |     0.1774 | False               |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.6291 | 0.6712 |   -0.0413 |    -0.1088 |     0.0288 |    0.2500 | False            |       1.0000 |             1.0000 |     0.3032 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.7707 | 0.8111 |   -0.0408 |    -0.0762 |    -0.0084 |    0.0102 | True             |       0.5712 |             1.0000 |     0.0150 | False               |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.6639 | 0.6253 |    0.0399 |    -0.0379 |     0.1143 |    0.3060 | False            |       1.0000 |             1.0000 |     0.3560 | False               |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.6253 | 0.5854 |    0.0387 |    -0.0325 |     0.1139 |    0.3054 | False            |       1.0000 |             1.0000 |     0.3560 | False               |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.6639 | 0.7022 |   -0.0372 |    -0.1134 |     0.0416 |    0.3480 | False            |       1.0000 |             1.0000 |     0.3994 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.6814 | 0.6435 |    0.0363 |    -0.0376 |     0.1077 |    0.3310 | False            |       1.0000 |             1.0000 |     0.3824 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.7777 | 0.8126 |   -0.0358 |    -0.0830 |     0.0077 |    0.1156 | False            |       1.0000 |             1.0000 |     0.1464 | False               |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.6291 | 0.6639 |   -0.0348 |    -0.0761 |     0.0081 |    0.1004 | False            |       1.0000 |             1.0000 |     0.1311 | False               |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.6213 | 0.5854 |    0.0346 |    -0.0286 |     0.0975 |    0.2894 | False            |       1.0000 |             1.0000 |     0.3413 | False               |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.8111 | 0.7777 |    0.0344 |    -0.0263 |     0.0994 |    0.2814 | False            |       1.0000 |             1.0000 |     0.3342 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.6712 | 0.7022 |   -0.0307 |    -0.1000 |     0.0427 |    0.3930 | False            |       1.0000 |             1.0000 |     0.4451 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.6712 | 0.6435 |    0.0268 |    -0.0292 |     0.0856 |    0.3686 | False            |       1.0000 |             1.0000 |     0.4202 | False               |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.6213 | 0.6435 |   -0.0238 |    -0.1099 |     0.0553 |    0.5788 | False            |       1.0000 |             1.0000 |     0.6284 | False               |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.7548 | 0.7777 |   -0.0216 |    -0.0780 |     0.0399 |    0.4662 | False            |       1.0000 |             1.0000 |     0.5177 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.6814 | 0.7022 |   -0.0212 |    -0.0960 |     0.0597 |    0.5770 | False            |       1.0000 |             1.0000 |     0.6284 | False               |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.6639 | 0.6435 |    0.0203 |    -0.0536 |     0.0878 |    0.5648 | False            |       1.0000 |             1.0000 |     0.6231 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.6435 | 0.6253 |    0.0197 |    -0.0537 |     0.0902 |    0.5806 | False            |       1.0000 |             1.0000 |     0.6284 | False               |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.6639 | 0.6814 |   -0.0160 |    -0.0885 |     0.0555 |    0.6554 | False            |       1.0000 |             1.0000 |     0.7049 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.7707 | 0.7548 |    0.0152 |    -0.0255 |     0.0571 |    0.4656 | False            |       1.0000 |             1.0000 |     0.5177 | False               |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.6291 | 0.6435 |   -0.0146 |    -0.0846 |     0.0493 |    0.6942 | False            |       1.0000 |             1.0000 |     0.7373 | False               |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.8228 | 0.8111 |    0.0118 |    -0.0160 |     0.0411 |    0.4092 | False            |       1.0000 |             1.0000 |     0.4603 | False               |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.8228 | 0.8126 |    0.0104 |    -0.0442 |     0.0660 |    0.7164 | False            |       1.0000 |             1.0000 |     0.7516 | False               |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.8111 | 0.8210 |   -0.0103 |    -0.0600 |     0.0393 |    0.6762 | False            |       1.0000 |             1.0000 |     0.7227 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.6712 | 0.6814 |   -0.0095 |    -0.0752 |     0.0579 |    0.7696 | False            |       1.0000 |             1.0000 |     0.8024 | False               |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.6291 | 0.6213 |    0.0092 |    -0.0677 |     0.0871 |    0.8168 | False            |       1.0000 |             1.0000 |     0.8465 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.8126 | 0.8210 |   -0.0089 |    -0.0563 |     0.0383 |    0.7042 | False            |       1.0000 |             1.0000 |     0.7433 | False               |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.6639 | 0.6712 |   -0.0065 |    -0.0764 |     0.0640 |    0.8512 | False            |       1.0000 |             1.0000 |     0.8716 | False               |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.7707 | 0.7777 |   -0.0064 |    -0.0696 |     0.0615 |    0.8422 | False            |       1.0000 |             1.0000 |     0.8676 | False               |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.6291 | 0.6253 |    0.0051 |    -0.0701 |     0.0769 |    0.8814 | False            |       1.0000 |             1.0000 |     0.8971 | False               |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.6213 | 0.6253 |   -0.0041 |    -0.0833 |     0.0747 |    0.9170 | False            |       1.0000 |             1.0000 |     0.9279 | False               |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.8228 | 0.8210 |    0.0015 |    -0.0507 |     0.0536 |    0.9584 | False            |       1.0000 |             1.0000 |     0.9584 | False               |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.8111 | 0.8126 |   -0.0014 |    -0.0552 |     0.0546 |    0.9390 | False            |       1.0000 |             1.0000 |     0.9445 | False               |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 **macro** por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0); o micro está em `K_iou_sensitivity_wide_micro.csv`:

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.8142 | 0.7777 | 0.7310 |  0.6651 |
| BERTimbau-large      | 0.8467 | 0.8126 | 0.7652 |  0.6664 |
| BERTimbauLaw         | 0.6759 | 0.6435 | 0.5965 |  0.5264 |
| BiLSTM-CRF           | 0.6778 | 0.6213 | 0.5517 |  0.4457 |
| DeepSeek-V4-Flash    | 0.9109 | 0.8705 | 0.8243 |  0.4210 |
| GPT-4.1              | 0.8689 | 0.8228 | 0.7564 |  0.3132 |
| GPT-4.1-mini         | 0.8099 | 0.7707 | 0.7105 |  0.2753 |
| GPT-4.1-nano         | 0.5082 | 0.4513 | 0.3909 |  0.1256 |
| GPT-5-mini           | 0.6518 | 0.6291 | 0.5927 |  0.1780 |
| GPT-5.1              | 0.8416 | 0.8111 | 0.7455 |  0.3542 |
| GPT-5.2              | 0.7897 | 0.7548 | 0.6942 |  0.2747 |
| GovBERT-BR           | 0.6202 | 0.5854 | 0.5509 |  0.4972 |
| JurisBERT            | 0.7453 | 0.6814 | 0.6372 |  0.5440 |
| Legal-BERT-STF       | 0.6547 | 0.6253 | 0.5949 |  0.5223 |
| Legal-BERTimbau-base | 0.6962 | 0.6712 | 0.6258 |  0.5327 |
| LegalBERTPT-br       | 0.7322 | 0.7022 | 0.6519 |  0.5684 |
| LegalBert-pt         | 0.8466 | 0.8210 | 0.7745 |  0.6855 |
| Llama-3.3-70B        | 0.2858 | 0.2667 | 0.2346 |  0.0690 |
| Qwen2.5-72B          | 0.7032 | 0.6639 | 0.6198 |  0.2965 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5, no macro e no micro):

| iou_threshold   |   spearman_macro_vs_0.5 |   spearman_micro_vs_0.5 |
|:----------------|------------------------:|------------------------:|
| 0.3             |                  0.9825 |                  0.9667 |
| 0.5             |                  1.0000 |                  1.0000 |
| 0.7             |                  0.9930 |                  0.9860 |
| exact           |                  0.3965 |                  0.5930 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 638 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 223 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_macro_full |   span_f1_macro_informative |   delta_span_f1_macro |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------------:|----------------------------:|----------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  223 |               0.8705 |                      0.8756 |                0.0051 |         0.8779 |                0.8810 |          0.0031 |                0.8842 |                       0.8905 |                 0.0063 |             0.8718 |                    0.8718 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  223 |               0.8228 |                      0.8600 |                0.0372 |         0.8210 |                0.8492 |          0.0282 |                0.7599 |                       0.8097 |                 0.0498 |             0.8928 |                    0.8928 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  223 |               0.8111 |                      0.8516 |                0.0404 |         0.7992 |                0.8398 |          0.0406 |                0.7280 |                       0.7983 |                 0.0703 |             0.8858 |                    0.8858 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  223 |               0.8210 |                      0.8316 |                0.0106 |         0.8353 |                0.8422 |          0.0069 |                0.8432 |                       0.8575 |                 0.0143 |             0.8275 |                    0.8275 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  223 |               0.7707 |                      0.8238 |                0.0530 |         0.7811 |                0.8330 |          0.0519 |                0.6861 |                       0.7703 |                 0.0842 |             0.9068 |                    0.9068 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  223 |               0.8126 |                      0.8203 |                0.0077 |         0.8203 |                0.8282 |          0.0078 |                0.8321 |                       0.8484 |                 0.0163 |             0.8089 |                    0.8089 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  223 |               0.7548 |                      0.8001 |                0.0453 |         0.7244 |                0.7819 |          0.0575 |                0.6031 |                       0.6873 |                 0.0842 |             0.9068 |                    0.9068 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  223 |               0.7777 |                      0.7882 |                0.0106 |         0.8115 |                0.8193 |          0.0078 |                0.8313 |                       0.8479 |                 0.0166 |             0.7925 |                    0.7925 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  223 |               0.6291 |                      0.7478 |                0.1187 |         0.4688 |                0.6948 |          0.2260 |                0.3145 |                       0.5579 |                 0.2434 |             0.9207 |                    0.9207 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  223 |               0.6639 |                      0.7370 |                0.0731 |         0.7169 |                0.7694 |          0.0525 |                0.6365 |                       0.7243 |                 0.0878 |             0.8205 |                    0.8205 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  223 |               0.7022 |                      0.7071 |                0.0049 |         0.7503 |                0.7558 |          0.0055 |                0.7857 |                       0.7979 |                 0.0122 |             0.7179 |                    0.7179 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  223 |               0.6814 |                      0.6876 |                0.0062 |         0.7473 |                0.7518 |          0.0045 |                0.7764 |                       0.7863 |                 0.0099 |             0.7203 |                    0.7203 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  223 |               0.6712 |                      0.6836 |                0.0123 |         0.7761 |                0.7862 |          0.0101 |                0.7807 |                       0.8015 |                 0.0208 |             0.7716 |                    0.7716 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  223 |               0.6435 |                      0.6484 |                0.0049 |         0.7903 |                0.7954 |          0.0051 |                0.8687 |                       0.8810 |                 0.0123 |             0.7249 |                    0.7249 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  223 |               0.6253 |                      0.6291 |                0.0039 |         0.7569 |                0.7607 |          0.0038 |                0.8184 |                       0.8274 |                 0.0090 |             0.7040 |                    0.7040 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  223 |               0.6213 |                      0.6253 |                0.0041 |         0.7211 |                0.7249 |          0.0038 |                0.8278 |                       0.8379 |                 0.0101 |             0.6387 |                    0.6387 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  223 |               0.5854 |                      0.5887 |                0.0033 |         0.7454 |                0.7484 |          0.0029 |                0.8529 |                       0.8606 |                 0.0078 |             0.6620 |                    0.6620 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |           861 |                  223 |               0.4513 |                      0.4866 |                0.0353 |         0.5000 |                0.5552 |          0.0552 |                0.4108 |                       0.4910 |                 0.0802 |             0.6387 |                    0.6387 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |           861 |                  223 |               0.2667 |                      0.2694 |                0.0027 |         0.3639 |                0.3658 |          0.0019 |                0.6730 |                       0.6859 |                 0.0129 |             0.2494 |                    0.2494 |

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
