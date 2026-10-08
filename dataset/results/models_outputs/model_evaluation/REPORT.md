# Avaliação de modelos — números reproduzíveis (gold corrigido)

Documento auto-contido: todas as tabelas aparecem inline. Os CSVs ao lado deste arquivo são as fontes canônicas (uma por bloco), geradas por `research.release.evaluation_numbers`. Cada bloco abaixo corresponde a um bloco da avaliação.

## Pipeline de métricas (correções aplicadas)

Esta versão dos números incorpora quatro correções no pipeline de avaliação:

1. **Matching pred↔gold bipartido por IoU descendente** (`research.ner_metrics.bipartite_greedy_match`). Cada predição casa com no máximo um gold e vice-versa, eliminando a divergência anterior entre `calculate_metrics` (que tinha `break` após o primeiro match) e o bootstrap (que contava todos os pares sobrepostos). Esta única função é agora a fonte para `calculate_metrics`, `evaluate_bio_results` e `compute_doc_level_counts` — `matched ≤ min(|pred|, |gold|)` por construção, e P/R sempre em [0, 1].

2. **Unidade única de span: índices de token.** Todas as predições, generativas e BIO, são convertidas para spans em índices de token sobre a tokenização canônica `\S+` de `research.dataset_io` antes do emparelhamento, e o gold é convertido junto. A relocalização difusa das strings emitidas pelos LLMs permanece; o que mudou é a unidade em que se pontua. O spaCy saiu do caminho de métricas: o token F1 era calculado sobre `pt_core_news_sm` no caminho generativo e sobre a tokenização canônica no caminho BIO. O efeito maior aparece na correspondência exata, que antes media se a borda direita estimada pelo modelo caía por acaso em fronteira de token.

3. **Gold supervisionado completo e entrada sem truncamento.** Todos os modelos são pontuados contra o gold canônico completo, e não contra o `true_labels` do próprio modelo. Os encoders processam documentos longos em janelas deslizantes de 512 subpalavras com sobreposição de 320, e o BiLSTM-CRF aceita até 1.100 tokens; nenhum documento é truncado (`check_alignment`).

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
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.7824 |           0.6861 |            0.9600 |         0.6602 |    0.7391 |          0.6603 |           0.8475 |        0.6553 |
| gpt-4.1_few_shot                                       | GPT-4.1              |     0.8167 |           0.7902 |            0.7840 |         0.8522 |    0.7365 |          0.7170 |           0.6578 |        0.8367 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.7815 |           0.6765 |            0.9444 |         0.6666 |    0.7248 |          0.6457 |           0.7786 |        0.6780 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.7726 |           0.6444 |            0.9434 |         0.6542 |    0.7217 |          0.6220 |           0.7898 |        0.6644 |
| gpt-5.1_few_shot                                       | GPT-5.1              |     0.7817 |           0.7549 |            0.7420 |         0.8259 |    0.7046 |          0.6910 |           0.6211 |        0.8141 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.7051 |           0.5313 |            0.9662 |         0.5551 |    0.7044 |          0.5555 |           0.9011 |        0.5782 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.7508 |           0.5847 |            0.9473 |         0.6219 |    0.7018 |          0.5656 |           0.8101 |        0.6190 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |     0.7937 |           0.7639 |            0.7445 |         0.8499 |    0.6986 |          0.6837 |           0.5962 |        0.8435 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.7255 |           0.5177 |            0.9670 |         0.5805 |    0.6866 |          0.5063 |           0.8547 |        0.5737 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.7305 |           0.5559 |            0.9629 |         0.5884 |    0.6773 |          0.5384 |           0.8173 |        0.5782 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.7250 |           0.6182 |            0.9306 |         0.5939 |    0.6767 |          0.6113 |           0.7599 |        0.6100 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.7448 |           0.6117 |            0.8728 |         0.6496 |    0.6735 |          0.6009 |           0.7774 |        0.5941 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7177 |           0.6752 |            0.7026 |         0.7334 |    0.6243 |          0.5853 |           0.5491 |        0.7234 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.7515 |           0.7207 |            0.6901 |         0.8250 |    0.6198 |          0.5945 |           0.5057 |        0.8005 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.5368 |           0.2862 |            0.9751 |         0.3703 |    0.5008 |          0.2836 |           0.8196 |        0.3605 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.5809 |           0.5079 |            0.5644 |         0.5984 |    0.4341 |          0.3953 |           0.3544 |        0.5601 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.5694 |           0.6332 |            0.4274 |         0.8526 |    0.4162 |          0.5310 |           0.2780 |        0.8277 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4090 |           0.3009 |            0.7560 |         0.2804 |    0.3558 |          0.2856 |           0.6066 |        0.2517 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                                  | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                                        |
|:-------------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:--------------------------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                                 | BiLSTM-CRF           |         0.6675 |        0.1074 |        0.5441 |        0.7846 | 0.6074; 0.7761; 0.6250; 0.7846; 0.5441 |          0.7330 |         0.0858 |         0.6089 |         0.8427 | 0.7037; 0.8427; 0.7454; 0.7644; 0.6089 | {"hidden_dim": 256, "dropout": 0.5, "lr": 0.003, "max_len": 1100}                                             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |         0.7244 |        0.0395 |        0.6917 |        0.7903 | 0.6917; 0.7228; 0.6961; 0.7903; 0.7209 |          0.7707 |         0.0431 |         0.7086 |         0.8191 | 0.7690; 0.8191; 0.7086; 0.7547; 0.8021 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}      |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |         0.7256 |        0.0666 |        0.6667 |        0.8345 | 0.6667; 0.7379; 0.6813; 0.8345; 0.7079 |          0.7757 |         0.0699 |         0.6836 |         0.8318 | 0.6836; 0.8249; 0.7170; 0.8318; 0.8211 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 3e-05, "warmup_ratio": 0.0, "stride": 320}     |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |         0.7059 |        0.0490 |        0.6404 |        0.7759 | 0.6885; 0.7172; 0.6404; 0.7759; 0.7073 |          0.7502 |         0.0443 |         0.6770 |         0.7916 | 0.7618; 0.7916; 0.6770; 0.7457; 0.7748 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}              |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |         0.6768 |        0.0700 |        0.5946 |        0.7436 | 0.6080; 0.7122; 0.5946; 0.7258; 0.7436 |          0.7186 |         0.0675 |         0.6427 |         0.8074 | 0.6610; 0.8074; 0.6427; 0.7294; 0.7527 | {"model_name": "alfaneo/jurisbert-base-portuguese-uncased", "lr": 3e-05, "warmup_ratio": 0.0, "stride": 320}  |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |         0.6830 |        0.0841 |        0.5875 |        0.7692 | 0.5981; 0.7374; 0.5875; 0.7692; 0.7226 |          0.7159 |         0.0797 |         0.6273 |         0.8060 | 0.6273; 0.8060; 0.6394; 0.7344; 0.7727 | {"model_name": "alfaneo/bertimbaulaw-base-portuguese-cased", "lr": 3e-05, "warmup_ratio": 0.1, "stride": 320} |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |         0.7377 |        0.0362 |        0.6838 |        0.7833 | 0.6838; 0.7404; 0.7513; 0.7833; 0.7297 |          0.7792 |         0.0274 |         0.7610 |         0.8271 | 0.7610; 0.8271; 0.7621; 0.7744; 0.7715 | {"model_name": "raquelsilveira/legalbertpt_fp", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}              |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |         0.5064 |        0.0930 |        0.4272 |        0.6275 | 0.4272; 0.4605; 0.4324; 0.6275; 0.5846 |          0.5374 |         0.0649 |         0.4818 |         0.6240 | 0.4844; 0.5082; 0.4818; 0.6240; 0.5885 | {"model_name": "ulysses-camara/legal-bert-pt-br", "lr": 3e-05, "warmup_ratio": 0.1, "stride": 320}            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |         0.6673 |        0.0945 |        0.5243 |        0.7417 | 0.5243; 0.7299; 0.6163; 0.7241; 0.7417 |          0.7112 |         0.1152 |         0.5576 |         0.8507 | 0.5576; 0.8507; 0.6482; 0.7105; 0.7892 | {"model_name": "dominguesm/legal-bert-base-cased-ptbr", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}      |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |         0.7036 |        0.0634 |        0.6435 |        0.7759 | 0.6435; 0.7650; 0.6474; 0.7759; 0.6861 |          0.7023 |         0.0501 |         0.6521 |         0.7696 | 0.7029; 0.7696; 0.6557; 0.7312; 0.6521 | {"model_name": "dccmpmgfinalisticas/GovBERT-BR", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}             |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.6949 |                0.1438 |                0.4090 |                0.8335 |                0.5955 |               0.1540 |               0.3558 |               0.7696 |
| supervised         |                 0.7255 |                0.0712 |                0.5368 |                0.7824 |                0.6807 |               0.0671 |               0.5008 |               0.7391 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.8109 |      0.7230 |         0.2500 |          0.7040 |
| BERTimbau-large      |  0.8253 |      0.7175 |         0.3953 |          0.6446 |
| BERTimbauLaw         |  0.8165 |      0.6927 |         0.0000 |          0.5161 |
| BiLSTM-CRF           |  0.7570 |      0.6834 |         0.4000 |          0.5631 |
| DeepSeek-V4-Flash    |  0.8434 |      0.7154 |         0.6667 |          0.7438 |
| GPT-4.1              |  0.8098 |      0.6547 |         0.6667 |          0.7368 |
| GPT-4.1-mini         |  0.7930 |      0.5886 |         0.6345 |          0.7188 |
| GPT-4.1-nano         |  0.6854 |      0.2864 |         0.1023 |          0.5072 |
| GPT-5-mini           |  0.7036 |      0.2249 |         0.5897 |          0.6056 |
| GPT-5.1              |  0.7846 |      0.6053 |         0.6429 |          0.7313 |
| GPT-5.2              |  0.7553 |      0.4895 |         0.5294 |          0.6040 |
| GovBERT-BR           |  0.8011 |      0.7016 |         0.0000 |          0.7193 |
| JurisBERT            |  0.7455 |      0.6765 |         0.3457 |          0.6777 |
| Legal-BERT-STF       |  0.7716 |      0.7071 |         0.1091 |          0.5660 |
| Legal-BERTimbau-base |  0.7742 |      0.7429 |         0.0727 |          0.6727 |
| LegalBERTPT-br       |  0.6814 |      0.4528 |         0.0000 |          0.0000 |
| LegalBert-pt         |  0.8074 |      0.7570 |         0.3768 |          0.7000 |
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
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | MULTA         |      0.7800 |   0.7685 | 0.7742 |       156 |          203 |          200 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | OBRIGACAO     |      0.8966 |   0.6341 | 0.7429 |        78 |          123 |           87 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RECOMENDACAO  |      0.6667 |   0.0385 | 0.0727 |         2 |           52 |            3 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RESSARCIMENTO |      0.7872 |   0.5873 | 0.6727 |        37 |           63 |           47 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | MULTA         |      0.8191 |   0.8030 | 0.8109 |       163 |          203 |          199 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | OBRIGACAO     |      0.8556 |   0.6260 | 0.7230 |        77 |          123 |           90 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RECOMENDACAO  |      0.4500 |   0.1731 | 0.2500 |         9 |           52 |           20 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RESSARCIMENTO |      0.7097 |   0.6984 | 0.7040 |        44 |           63 |           62 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | MULTA         |      0.8490 |   0.8030 | 0.8253 |       163 |          203 |          192 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | OBRIGACAO     |      0.8000 |   0.6504 | 0.7175 |        80 |          123 |          100 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RECOMENDACAO  |      0.5000 |   0.3269 | 0.3953 |        17 |           52 |           34 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RESSARCIMENTO |      0.6724 |   0.6190 | 0.6446 |        39 |           63 |           58 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | MULTA         |      0.7872 |   0.7291 | 0.7570 |       148 |          203 |          188 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | OBRIGACAO     |      0.8947 |   0.5528 | 0.6834 |        68 |          123 |           76 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RECOMENDACAO  |      0.5152 |   0.3269 | 0.4000 |        17 |           52 |           33 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RESSARCIMENTO |      0.7250 |   0.4603 | 0.5631 |        29 |           63 |           40 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | MULTA         |      0.7796 |   0.7143 | 0.7455 |       145 |          203 |          186 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | OBRIGACAO     |      0.8519 |   0.5610 | 0.6765 |        69 |          123 |           81 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RECOMENDACAO  |      0.4828 |   0.2692 | 0.3457 |        14 |           52 |           29 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RESSARCIMENTO |      0.7069 |   0.6508 | 0.6777 |        41 |           63 |           58 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | MULTA         |      0.8587 |   0.7783 | 0.8165 |       158 |          203 |          184 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | OBRIGACAO     |      0.8659 |   0.5772 | 0.6927 |        71 |          123 |           82 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           52 |            0 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RESSARCIMENTO |      0.8000 |   0.3810 | 0.5161 |        24 |           63 |           30 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | MULTA         |      0.8693 |   0.7537 | 0.8074 |       153 |          203 |          176 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | OBRIGACAO     |      0.8901 |   0.6585 | 0.7570 |        81 |          123 |           91 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RECOMENDACAO  |      0.7647 |   0.2500 | 0.3768 |        13 |           52 |           17 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RESSARCIMENTO |      0.7368 |   0.6667 | 0.7000 |        42 |           63 |           57 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | MULTA         |      0.7785 |   0.6059 | 0.6814 |       123 |          203 |          158 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | OBRIGACAO     |      1.0000 |   0.2927 | 0.4528 |        36 |          123 |           36 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           52 |            0 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RESSARCIMENTO |      0.0000 |   0.0000 | 0.0000 |         0 |           63 |            0 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | MULTA         |      0.7958 |   0.7488 | 0.7716 |       152 |          203 |          191 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | OBRIGACAO     |      0.9333 |   0.5691 | 0.7071 |        70 |          123 |           75 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RECOMENDACAO  |      1.0000 |   0.0577 | 0.1091 |         3 |           52 |            3 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RESSARCIMENTO |      0.6977 |   0.4762 | 0.5660 |        30 |           63 |           43 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | MULTA         |      0.8963 |   0.7241 | 0.8011 |       147 |          203 |          164 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | OBRIGACAO     |      0.9853 |   0.5447 | 0.7016 |        67 |          123 |           68 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           52 |            0 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RESSARCIMENTO |      0.8039 |   0.6508 | 0.7193 |        41 |           63 |           51 |

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
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.6603 |          0.7391 |         0.6587 |        0.0274 |     0.6040 |     0.7112 |     0.1072 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.6457 |          0.7248 |         0.6453 |        0.0274 |     0.5923 |     0.6988 |     0.1065 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.6220 |          0.7217 |         0.6213 |        0.0268 |     0.5695 |     0.6742 |     0.1047 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.6113 |          0.6767 |         0.6109 |        0.0284 |     0.5560 |     0.6667 |     0.1108 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.6009 |          0.6735 |         0.6002 |        0.0291 |     0.5424 |     0.6572 |     0.1148 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.5945 |          0.6198 |         0.5946 |        0.0259 |     0.5430 |     0.6447 |     0.1017 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.5853 |          0.6243 |         0.5848 |        0.0232 |     0.5394 |     0.6293 |     0.0899 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.5656 |          0.7018 |         0.5653 |        0.0239 |     0.5187 |     0.6126 |     0.0939 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.5555 |          0.7044 |         0.5551 |        0.0207 |     0.5134 |     0.5948 |     0.0814 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.5384 |          0.6773 |         0.5372 |        0.0269 |     0.4835 |     0.5895 |     0.1060 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.5310 |          0.4162 |         0.5309 |        0.0228 |     0.4846 |     0.5744 |     0.0898 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.5063 |          0.6866 |         0.5060 |        0.0245 |     0.4568 |     0.5521 |     0.0953 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.3953 |          0.4341 |         0.3958 |        0.0251 |     0.3464 |     0.4458 |     0.0994 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2856 |          0.3558 |         0.2853 |        0.0275 |     0.2312 |     0.3396 |     0.1084 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.2836 |          0.5008 |         0.2836 |        0.0190 |     0.2456 |     0.3206 |     0.0751 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                        | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash | Llama-3.3-70B     | 0.7423 | 0.2856 |    0.4566 |     0.3947 |     0.5160 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-5.2           | Llama-3.3-70B     | 0.5945 | 0.2856 |    0.3092 |     0.2380 |     0.3791 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| llama-3.3-70b_few_shot                            | qwen2.5-72b_few_shot                                   | Llama-3.3-70B     | Qwen2.5-72B       | 0.2856 | 0.5853 |   -0.2995 |    -0.3687 |    -0.2295 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1-mini_few_shot                             | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini      | GPT-4.1-nano      | 0.6837 | 0.3953 |    0.2876 |     0.2304 |     0.3432 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-5.2           | DeepSeek-V4-Flash | 0.5945 | 0.7423 |   -0.1474 |    -0.1958 |    -0.1001 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7170 | 0.5945 |    0.1221 |     0.0803 |     0.1652 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7423 | 0.6220 |    0.1206 |     0.0642 |     0.1765 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.6220 | 0.5063 |    0.1154 |     0.0618 |     0.1699 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-5.1           | GPT-5.2           | 0.6910 | 0.5945 |    0.0959 |     0.0526 |     0.1402 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7423 | 0.6603 |    0.0832 |     0.0211 |     0.1457 |    0.0082 | True             |   0.0656 |         0.1394 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2           | LegalBert-pt      | 0.5945 | 0.6603 |   -0.0642 |    -0.1304 |     0.0008 |    0.0522 | False            |   0.3132 |         0.8874 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.6220 | 0.6603 |   -0.0374 |    -0.0955 |     0.0220 |    0.2194 | False            |   0.8776 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7170 | 0.6837 |    0.0332 |     0.0082 |     0.0604 |    0.0084 | True             |   0.0656 |         0.1428 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2           | BERTimbau-base    | 0.5945 | 0.6220 |   -0.0268 |    -0.0950 |     0.0396 |    0.4372 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7170 | 0.7423 |   -0.0253 |    -0.0517 |     0.0009 |    0.0600 | False            |   0.3132 |         1.0000 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                                 | BERTimbau-base    | BiLSTM-CRF        | 0.6220 | 0.6009 |    0.0211 |    -0.0417 |     0.0844 |    0.5204 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-5.2           | Qwen2.5-72B       | 0.5945 | 0.5853 |    0.0097 |    -0.0371 |     0.0569 |    0.6816 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |

**Itens 47–48 — Resumo:**

| metric                         | value                   |
|:-------------------------------|:------------------------|
| resampling_unit                | document                |
| n_docs_resampled               | 861                     |
| n_total_pairs                  | 171                     |
| n_significant_5pct_uncorrected | 125                     |
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
| gpt-5.1_few_shot                                       | GPT-5.1              |    0.6910 |           0.0514 |   0.0026 |   0.0078 | False             |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |    0.6837 |           0.0585 |   0.0000 |   0.0000 | False             |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.6603 |           0.0832 |   0.0082 |   0.0164 | False             |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.6457 |           0.0966 |   0.0012 |   0.0048 | False             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.6220 |           0.1206 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.6113 |           0.1310 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.6009 |           0.1417 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.5945 |           0.1474 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.5853 |           0.1571 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.5656 |           0.1766 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.5555 |           0.1868 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.5384 |           0.2047 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.5310 |           0.2110 |   0.0000 |   0.0000 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.5063 |           0.2360 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.3953 |           0.3461 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2856 |           0.4566 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.2836 |           0.4583 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7423 | 0.2836 |    0.4583 |     0.4068 |     0.5087 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7423 | 0.2856 |    0.4566 |     0.3947 |     0.5160 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7170 | 0.2836 |    0.4330 |     0.3835 |     0.4810 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7170 | 0.2856 |    0.4313 |     0.3692 |     0.4925 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.6910 | 0.2836 |    0.4069 |     0.3558 |     0.4555 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.6910 | 0.2856 |    0.4051 |     0.3395 |     0.4679 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.6837 | 0.2836 |    0.3998 |     0.3483 |     0.4487 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.6837 | 0.2856 |    0.3980 |     0.3325 |     0.4608 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.6603 | 0.2836 |    0.3751 |     0.3156 |     0.4303 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2856 | 0.6603 |   -0.3734 |    -0.4476 |    -0.2978 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.6457 | 0.2836 |    0.3617 |     0.3082 |     0.4148 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2856 | 0.6457 |   -0.3600 |    -0.4286 |    -0.2910 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.3953 | 0.7423 |   -0.3461 |    -0.4053 |    -0.2853 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.6220 | 0.2836 |    0.3377 |     0.2860 |     0.3904 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2856 | 0.6220 |   -0.3360 |    -0.4004 |    -0.2697 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.6113 | 0.2836 |    0.3273 |     0.2766 |     0.3780 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2856 | 0.6113 |   -0.3256 |    -0.3898 |    -0.2613 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7170 | 0.3953 |    0.3208 |     0.2614 |     0.3780 |    0.0000 | True             |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.6009 | 0.2836 |    0.3166 |     0.2615 |     0.3714 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2856 | 0.6009 |   -0.3149 |    -0.3819 |    -0.2459 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.5945 | 0.2836 |    0.3110 |     0.2531 |     0.3670 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.5945 | 0.2856 |    0.3092 |     0.2380 |     0.3791 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.5853 | 0.2836 |    0.3012 |     0.2439 |     0.3575 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2856 | 0.5853 |   -0.2995 |    -0.3687 |    -0.2295 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.3953 | 0.6910 |   -0.2947 |    -0.3514 |    -0.2366 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.6837 | 0.3953 |    0.2876 |     0.2304 |     0.3432 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.5656 | 0.2836 |    0.2817 |     0.2360 |     0.3279 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2856 | 0.5656 |   -0.2799 |    -0.3445 |    -0.2131 |    0.0000 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.2836 | 0.5555 |   -0.2715 |    -0.3078 |    -0.2349 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2856 | 0.5555 |   -0.2698 |    -0.3286 |    -0.2085 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.3953 | 0.6603 |   -0.2629 |    -0.3255 |    -0.1984 |    0.0000 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.2836 | 0.5384 |   -0.2536 |    -0.3061 |    -0.2026 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2856 | 0.5384 |   -0.2519 |    -0.3202 |    -0.1807 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.3953 | 0.6457 |   -0.2495 |    -0.3145 |    -0.1834 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.5310 | 0.2836 |    0.2473 |     0.1922 |     0.3003 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.5310 | 0.2856 |    0.2456 |     0.1786 |     0.3116 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7423 | 0.5063 |    0.2360 |     0.1822 |     0.2894 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.3953 | 0.6220 |   -0.2255 |    -0.2880 |    -0.1632 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.5063 | 0.2836 |    0.2224 |     0.1798 |     0.2638 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2856 | 0.5063 |   -0.2206 |    -0.2855 |    -0.1551 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.3953 | 0.6113 |   -0.2151 |    -0.2823 |    -0.1469 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.5310 | 0.7423 |   -0.2110 |    -0.2537 |    -0.1688 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7170 | 0.5063 |    0.2107 |     0.1558 |     0.2650 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7423 | 0.5384 |    0.2047 |     0.1429 |     0.2660 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.3953 | 0.6009 |   -0.2044 |    -0.2710 |    -0.1353 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.3953 | 0.5945 |   -0.1987 |    -0.2456 |    -0.1508 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.3953 | 0.5853 |   -0.1890 |    -0.2426 |    -0.1348 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7423 | 0.5555 |    0.1868 |     0.1358 |     0.2393 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7170 | 0.5310 |    0.1857 |     0.1460 |     0.2257 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.6910 | 0.5063 |    0.1845 |     0.1302 |     0.2387 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7170 | 0.5384 |    0.1794 |     0.1176 |     0.2398 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.6837 | 0.5063 |    0.1774 |     0.1205 |     0.2331 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7423 | 0.5656 |    0.1766 |     0.1213 |     0.2299 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.3953 | 0.5656 |   -0.1695 |    -0.2320 |    -0.1066 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7170 | 0.5555 |    0.1615 |     0.1109 |     0.2121 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.5310 | 0.6910 |   -0.1596 |    -0.2027 |    -0.1178 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.3953 | 0.5555 |   -0.1593 |    -0.2145 |    -0.1031 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7423 | 0.5853 |    0.1571 |     0.1131 |     0.2028 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.6910 | 0.5384 |    0.1533 |     0.0933 |     0.2138 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.5063 | 0.6603 |   -0.1528 |    -0.2130 |    -0.0910 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.6837 | 0.5310 |    0.1525 |     0.1135 |     0.1928 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7170 | 0.5656 |    0.1513 |     0.0941 |     0.2065 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.5945 | 0.7423 |   -0.1474 |    -0.1958 |    -0.1001 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.6837 | 0.5384 |    0.1462 |     0.0860 |     0.2060 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7423 | 0.6009 |    0.1417 |     0.0821 |     0.1999 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.3953 | 0.5384 |   -0.1414 |    -0.2109 |    -0.0714 |    0.0002 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.6457 | 0.5063 |    0.1394 |     0.0839 |     0.1964 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.6910 | 0.5555 |    0.1354 |     0.0845 |     0.1858 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.3953 | 0.5310 |   -0.1351 |    -0.1868 |    -0.0814 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7170 | 0.5853 |    0.1318 |     0.0892 |     0.1751 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7423 | 0.6113 |    0.1310 |     0.0745 |     0.1892 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.6837 | 0.5555 |    0.1283 |     0.0777 |     0.1791 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.5310 | 0.6603 |   -0.1278 |    -0.1926 |    -0.0629 |    0.0004 | True             |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.6910 | 0.5656 |    0.1252 |     0.0682 |     0.1814 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7170 | 0.5945 |    0.1221 |     0.0803 |     0.1652 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.6603 | 0.5384 |    0.1215 |     0.0638 |     0.1799 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7423 | 0.6220 |    0.1206 |     0.0642 |     0.1765 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.6837 | 0.5656 |    0.1181 |     0.0640 |     0.1706 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7170 | 0.6009 |    0.1164 |     0.0560 |     0.1763 |    0.0002 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.6220 | 0.5063 |    0.1154 |     0.0618 |     0.1699 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.5310 | 0.6457 |   -0.1144 |    -0.1771 |    -0.0516 |    0.0002 | True             |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.3953 | 0.2836 |    0.1122 |     0.0591 |     0.1678 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.3953 | 0.2856 |    0.1105 |     0.0386 |     0.1805 |    0.0022 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.3953 | 0.5063 |   -0.1101 |    -0.1643 |    -0.0534 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.6457 | 0.5384 |    0.1081 |     0.0464 |     0.1718 |    0.0010 | True             |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7170 | 0.6113 |    0.1057 |     0.0465 |     0.1648 |    0.0006 | True             |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.6910 | 0.5853 |    0.1056 |     0.0618 |     0.1498 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.6113 | 0.5063 |    0.1049 |     0.0527 |     0.1558 |    0.0002 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.6603 | 0.5555 |    0.1036 |     0.0508 |     0.1546 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.6837 | 0.5853 |    0.0985 |     0.0595 |     0.1384 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7423 | 0.6457 |    0.0966 |     0.0360 |     0.1571 |    0.0012 | True             |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.6910 | 0.5945 |    0.0959 |     0.0526 |     0.1402 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7170 | 0.6220 |    0.0953 |     0.0378 |     0.1522 |    0.0020 | True             |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.6009 | 0.5063 |    0.0943 |     0.0333 |     0.1544 |    0.0030 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.5656 | 0.6603 |   -0.0934 |    -0.1493 |    -0.0352 |    0.0012 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.5310 | 0.6220 |   -0.0904 |    -0.1549 |    -0.0271 |    0.0052 | True             |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.6910 | 0.6009 |    0.0902 |     0.0274 |     0.1513 |    0.0064 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.6457 | 0.5555 |    0.0902 |     0.0413 |     0.1401 |    0.0006 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.6837 | 0.5945 |    0.0888 |     0.0463 |     0.1328 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.5945 | 0.5063 |    0.0886 |     0.0346 |     0.1425 |    0.0010 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.6220 | 0.5384 |    0.0841 |     0.0289 |     0.1416 |    0.0044 | True             |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7423 | 0.6603 |    0.0832 |     0.0211 |     0.1457 |    0.0082 | True             |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.6837 | 0.6009 |    0.0831 |     0.0178 |     0.1461 |    0.0132 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.5656 | 0.6457 |   -0.0801 |    -0.1375 |    -0.0239 |    0.0046 | True             |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.5310 | 0.6113 |   -0.0800 |    -0.1417 |    -0.0191 |    0.0140 | True             |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.6910 | 0.6113 |    0.0796 |     0.0197 |     0.1392 |    0.0108 | True             |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.5853 | 0.5063 |    0.0789 |     0.0194 |     0.1386 |    0.0096 | True             |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.5853 | 0.6603 |   -0.0739 |    -0.1392 |    -0.0080 |    0.0296 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.6113 | 0.5384 |    0.0737 |     0.0152 |     0.1330 |    0.0152 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.6837 | 0.6113 |    0.0725 |     0.0157 |     0.1302 |    0.0136 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7170 | 0.6457 |    0.0713 |     0.0102 |     0.1313 |    0.0220 | True             |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.5310 | 0.6009 |   -0.0693 |    -0.1321 |    -0.0052 |    0.0332 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.6910 | 0.6220 |    0.0692 |     0.0111 |     0.1262 |    0.0212 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.6220 | 0.5555 |    0.0662 |     0.0194 |     0.1137 |    0.0074 | True             |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.5945 | 0.6603 |   -0.0642 |    -0.1304 |     0.0008 |    0.0522 | False            |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.5310 | 0.5945 |   -0.0637 |    -0.1049 |    -0.0223 |    0.0024 | True             |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.6009 | 0.5384 |    0.0630 |     0.0000 |     0.1264 |    0.0500 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.6837 | 0.6220 |    0.0621 |     0.0058 |     0.1180 |    0.0292 | True             |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.5853 | 0.6457 |   -0.0605 |    -0.1246 |     0.0040 |    0.0676 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.5656 | 0.5063 |    0.0593 |     0.0069 |     0.1131 |    0.0260 | True             |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.6837 | 0.7423 |   -0.0585 |    -0.0912 |    -0.0270 |    0.0000 | True             |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.6009 | 0.6603 |   -0.0585 |    -0.1272 |     0.0104 |    0.0964 | False            |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7170 | 0.6603 |    0.0579 |    -0.0014 |     0.1197 |    0.0566 | False            |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.5945 | 0.5384 |    0.0574 |    -0.0124 |     0.1250 |    0.1086 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.5656 | 0.6220 |   -0.0560 |    -0.1029 |    -0.0112 |    0.0154 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.6113 | 0.5555 |    0.0558 |     0.0055 |     0.1084 |    0.0298 | True             |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.5310 | 0.5853 |   -0.0539 |    -0.1001 |    -0.0064 |    0.0262 | True             |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.6910 | 0.7423 |   -0.0514 |    -0.0856 |    -0.0177 |    0.0026 | True             |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.5945 | 0.6457 |   -0.0508 |    -0.1169 |     0.0149 |    0.1298 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.5063 | 0.5555 |   -0.0491 |    -0.0941 |    -0.0051 |    0.0282 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.6113 | 0.6603 |   -0.0478 |    -0.1139 |     0.0191 |    0.1628 | False            |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.5853 | 0.5384 |    0.0476 |    -0.0172 |     0.1139 |    0.1578 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.5656 | 0.6113 |   -0.0456 |    -0.1025 |     0.0117 |    0.1234 | False            |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.6910 | 0.6457 |    0.0451 |    -0.0144 |     0.1045 |    0.1432 | False            |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.6009 | 0.5555 |    0.0451 |    -0.0078 |     0.0979 |    0.0970 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.6457 | 0.6009 |    0.0451 |    -0.0108 |     0.1016 |    0.1114 | False            |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.5945 | 0.5555 |    0.0395 |    -0.0182 |     0.0959 |    0.1746 | False            |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.6837 | 0.6457 |    0.0380 |    -0.0223 |     0.0986 |    0.2142 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.6220 | 0.6603 |   -0.0374 |    -0.0955 |     0.0220 |    0.2194 | False            |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.5853 | 0.6220 |   -0.0365 |    -0.0993 |     0.0271 |    0.2672 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.5656 | 0.6009 |   -0.0350 |    -0.0992 |     0.0298 |    0.2842 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.6457 | 0.6113 |    0.0344 |    -0.0216 |     0.0915 |    0.2404 | False            |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.5310 | 0.5656 |   -0.0344 |    -0.0967 |     0.0273 |    0.2748 | False            |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7170 | 0.6837 |    0.0332 |     0.0082 |     0.0604 |    0.0084 | True             |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.6910 | 0.6603 |    0.0318 |    -0.0282 |     0.0927 |    0.2998 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.5063 | 0.5384 |   -0.0312 |    -0.0881 |     0.0231 |    0.2642 | False            |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.5853 | 0.5555 |    0.0297 |    -0.0271 |     0.0867 |    0.3008 | False            |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.5945 | 0.5656 |    0.0293 |    -0.0325 |     0.0890 |    0.3440 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.5656 | 0.5384 |    0.0281 |    -0.0235 |     0.0795 |    0.2746 | False            |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.5945 | 0.6220 |   -0.0268 |    -0.0950 |     0.0396 |    0.4372 | False            |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7170 | 0.6910 |    0.0261 |    -0.0016 |     0.0545 |    0.0636 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.5853 | 0.6113 |   -0.0261 |    -0.0928 |     0.0393 |    0.4504 | False            |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7170 | 0.7423 |   -0.0253 |    -0.0517 |     0.0009 |    0.0600 | False            |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.5310 | 0.5063 |    0.0249 |    -0.0300 |     0.0804 |    0.3746 | False            |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.6837 | 0.6603 |    0.0247 |    -0.0342 |     0.0851 |    0.4166 | False            |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.5310 | 0.5555 |   -0.0242 |    -0.0809 |     0.0304 |    0.3958 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.6220 | 0.6457 |   -0.0240 |    -0.0701 |     0.0215 |    0.2954 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.6220 | 0.6009 |    0.0211 |    -0.0417 |     0.0844 |    0.5204 | False            |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.5853 | 0.5656 |    0.0196 |    -0.0408 |     0.0780 |    0.5200 | False            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.5384 | 0.5555 |   -0.0179 |    -0.0671 |     0.0321 |    0.4668 | False            |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.5945 | 0.6113 |   -0.0163 |    -0.0828 |     0.0488 |    0.6292 | False            |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.5853 | 0.6009 |   -0.0154 |    -0.0881 |     0.0564 |    0.6904 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.6457 | 0.6603 |   -0.0134 |    -0.0716 |     0.0473 |    0.6440 | False            |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.6009 | 0.6113 |   -0.0107 |    -0.0745 |     0.0525 |    0.7416 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.6220 | 0.6113 |    0.0104 |    -0.0395 |     0.0598 |    0.6898 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.5656 | 0.5555 |    0.0102 |    -0.0303 |     0.0519 |    0.6290 | False            |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.5945 | 0.5853 |    0.0097 |    -0.0371 |     0.0569 |    0.6816 | False            |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.6837 | 0.6910 |   -0.0071 |    -0.0384 |     0.0236 |    0.6618 | False            |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.5310 | 0.5384 |   -0.0063 |    -0.0754 |     0.0608 |    0.8752 | False            |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.5945 | 0.6009 |   -0.0057 |    -0.0759 |     0.0644 |    0.8702 | False            |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2856 | 0.2836 |    0.0018 |    -0.0528 |     0.0587 |    0.9646 | False            |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.7488 | 0.7217 | 0.6847 |  0.6182 |
| BERTimbau-large      | 0.7442 | 0.7248 | 0.6836 |  0.6085 |
| BERTimbauLaw         | 0.6947 | 0.6866 | 0.6486 |  0.5807 |
| BiLSTM-CRF           | 0.7198 | 0.6735 | 0.6041 |  0.4499 |
| DeepSeek-V4-Flash    | 0.8152 | 0.7696 | 0.7217 |  0.3174 |
| GPT-4.1              | 0.7784 | 0.7365 | 0.6766 |  0.2236 |
| GPT-4.1-mini         | 0.7343 | 0.6986 | 0.6366 |  0.2047 |
| GPT-4.1-nano         | 0.4921 | 0.4341 | 0.3779 |  0.1265 |
| GPT-5-mini           | 0.4356 | 0.4162 | 0.3922 |  0.0832 |
| GPT-5.1              | 0.7321 | 0.7046 | 0.6555 |  0.2375 |
| GPT-5.2              | 0.6620 | 0.6198 | 0.5654 |  0.1686 |
| GovBERT-BR           | 0.7127 | 0.7044 | 0.6713 |  0.6077 |
| JurisBERT            | 0.7119 | 0.6767 | 0.6365 |  0.5585 |
| Legal-BERT-STF       | 0.7012 | 0.6773 | 0.6534 |  0.5870 |
| Legal-BERTimbau-base | 0.7224 | 0.7018 | 0.6658 |  0.5758 |
| LegalBERTPT-br       | 0.5197 | 0.5008 | 0.4882 |  0.4693 |
| LegalBert-pt         | 0.7698 | 0.7391 | 0.7084 |  0.6445 |
| Llama-3.3-70B        | 0.3910 | 0.3558 | 0.3173 |  0.0513 |
| Qwen2.5-72B          | 0.6556 | 0.6243 | 0.5773 |  0.2290 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5):

| iou_threshold   |   spearman_vs_0.5 |
|:----------------|------------------:|
| 0.3             |            0.9544 |
| 0.5             |            1.0000 |
| 0.7             |            0.9789 |
| exact           |            0.6123 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  231 |         0.7696 |                0.8147 |          0.0452 |                0.7390 |                       0.8271 |                 0.0881 |             0.8027 |                    0.8027 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  231 |         0.7365 |                0.7987 |          0.0622 |                0.6578 |                       0.7640 |                 0.1062 |             0.8367 |                    0.8367 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  231 |         0.6986 |                0.7742 |          0.0756 |                0.5962 |                       0.7154 |                 0.1192 |             0.8435 |                    0.8435 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  231 |         0.7046 |                0.7729 |          0.0683 |                0.6211 |                       0.7357 |                 0.1145 |             0.8141 |                    0.8141 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  231 |         0.7391 |                0.7477 |          0.0086 |                0.8475 |                       0.8705 |                 0.0230 |             0.6553 |                    0.6553 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  231 |         0.7248 |                0.7419 |          0.0171 |                0.7786 |                       0.8192 |                 0.0405 |             0.6780 |                    0.6780 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  231 |         0.7217 |                0.7380 |          0.0164 |                0.7898 |                       0.8300 |                 0.0403 |             0.6644 |                    0.6644 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  231 |         0.7018 |                0.7091 |          0.0073 |                0.8101 |                       0.8298 |                 0.0197 |             0.6190 |                    0.6190 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  231 |         0.7044 |                0.7083 |          0.0039 |                0.9011 |                       0.9140 |                 0.0129 |             0.5782 |                    0.5782 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  231 |         0.6198 |                0.6990 |          0.0792 |                0.5057 |                       0.6204 |                 0.1147 |             0.8005 |                    0.8005 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  231 |         0.6735 |                0.6977 |          0.0242 |                0.7774 |                       0.8452 |                 0.0677 |             0.5941 |                    0.5941 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  231 |         0.6767 |                0.6933 |          0.0166 |                0.7599 |                       0.8030 |                 0.0431 |             0.6100 |                    0.6100 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  231 |         0.6866 |                0.6903 |          0.0037 |                0.8547 |                       0.8664 |                 0.0117 |             0.5737 |                    0.5737 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  231 |         0.6243 |                0.6845 |          0.0603 |                0.5491 |                       0.6497 |                 0.1006 |             0.7234 |                    0.7234 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  231 |         0.6773 |                0.6827 |          0.0054 |                0.8173 |                       0.8333 |                 0.0160 |             0.5782 |                    0.5782 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  231 |         0.4162 |                0.6068 |          0.1906 |                0.2780 |                       0.4790 |                 0.2010 |             0.8277 |                    0.8277 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  231 |         0.5008 |                0.5032 |          0.0024 |                0.8196 |                       0.8325 |                 0.0129 |             0.3605 |                    0.3605 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |           861 |                  231 |         0.4341 |                0.4867 |          0.0526 |                0.3544 |                       0.4303 |                 0.0759 |             0.5601 |                    0.5601 |
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
