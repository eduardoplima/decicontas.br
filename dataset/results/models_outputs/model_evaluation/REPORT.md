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
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.7415 |           0.6378 |            0.9467 |         0.6094 |    0.6945 |          0.6275 |           0.8185 |        0.6032 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.7318 |           0.6299 |            0.9420 |         0.5983 |    0.6743 |          0.6103 |           0.7719 |        0.5986 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.6863 |           0.5308 |            0.9409 |         0.5402 |    0.6594 |          0.5435 |           0.8259 |        0.5488 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.6896 |           0.5581 |            0.9448 |         0.5429 |    0.6531 |          0.5497 |           0.8163 |        0.5442 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.7720 |           0.6425 |            0.8621 |         0.6991 |    0.6492 |          0.5698 |           0.7678 |        0.5624 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7177 |           0.6752 |            0.7026 |         0.7334 |    0.6243 |          0.5853 |           0.5491 |        0.7234 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.6739 |           0.5610 |            0.9389 |         0.5256 |    0.6237 |          0.5526 |           0.7429 |        0.5374 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.7515 |           0.7207 |            0.6901 |         0.8250 |    0.6198 |          0.5945 |           0.5057 |        0.8005 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.6430 |           0.4690 |            0.9499 |         0.4860 |    0.6061 |          0.4730 |           0.8333 |        0.4762 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.6405 |           0.4521 |            0.9591 |         0.4807 |    0.5980 |          0.4504 |           0.8306 |        0.4671 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.5852 |           0.4076 |            0.9707 |         0.4189 |    0.5600 |          0.4157 |           0.8708 |        0.4127 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.5945 |           0.3653 |            0.9791 |         0.4269 |    0.5471 |          0.3693 |           0.8026 |        0.4150 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.5809 |           0.5079 |            0.5644 |         0.5984 |    0.4341 |          0.3953 |           0.3544 |        0.5601 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.5694 |           0.6332 |            0.4274 |         0.8526 |    0.4162 |          0.5310 |           0.2780 |        0.8277 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4090 |           0.3009 |            0.7560 |         0.2804 |    0.3558 |          0.2856 |           0.6066 |        0.2517 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                                  | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                         |
|:-------------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:-----------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                                 | BiLSTM-CRF           |         0.6425 |        0.1017 |        0.5138 |        0.7536 | 0.5138; 0.7283; 0.5714; 0.7536; 0.6456 |          0.7651 |         0.0674 |         0.6598 |         0.8451 | 0.6598; 0.7902; 0.7614; 0.8451; 0.7691 | {"hidden_dim": 256, "dropout": 0.3, "lr": 0.003}                                               |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |         0.6966 |        0.0671 |        0.6176 |        0.8031 | 0.6885; 0.6957; 0.6782; 0.8031; 0.6176 |          0.7384 |         0.0580 |         0.6588 |         0.8012 | 0.7493; 0.8012; 0.7024; 0.7804; 0.6588 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1}      |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |         0.5989 |        0.1010 |        0.4800 |        0.7350 | 0.5950; 0.6556; 0.4800; 0.7350; 0.5289 |          0.6348 |         0.0932 |         0.5382 |         0.7325 | 0.6502; 0.7325; 0.5385; 0.7145; 0.5382 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 2e-05, "warmup_ratio": 0.1}     |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |         0.5890 |        0.1460 |        0.3778 |        0.7642 | 0.3778; 0.6776; 0.5814; 0.7642; 0.5440 |          0.6169 |         0.1541 |         0.3813 |         0.7593 | 0.3813; 0.7406; 0.6431; 0.7593; 0.5604 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.1}              |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |         0.6297 |        0.0474 |        0.5810 |        0.6992 | 0.6195; 0.5960; 0.5810; 0.6992; 0.6531 |          0.6722 |         0.0503 |         0.5976 |         0.7348 | 0.6709; 0.7348; 0.5976; 0.6956; 0.6621 | {"model_name": "alfaneo/jurisbert-base-portuguese-uncased", "lr": 3e-05, "warmup_ratio": 0.1}  |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |         0.6479 |        0.0730 |        0.5484 |        0.7385 | 0.6050; 0.6772; 0.6705; 0.7385; 0.5484 |          0.6815 |         0.0810 |         0.5541 |         0.7636 | 0.6702; 0.7636; 0.6820; 0.7376; 0.5541 | {"model_name": "alfaneo/bertimbaulaw-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1} |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |         0.6751 |        0.0390 |        0.6303 |        0.7164 | 0.6667; 0.7164; 0.6477; 0.7143; 0.6303 |          0.7294 |         0.0477 |         0.6755 |         0.7986 | 0.7521; 0.7986; 0.6755; 0.7198; 0.7010 | {"model_name": "raquelsilveira/legalbertpt_fp", "lr": 5e-05, "warmup_ratio": 0.0}              |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |         0.5384 |        0.1089 |        0.4272 |        0.6596 | 0.4272; 0.6596; 0.4533; 0.6476; 0.5041 |          0.5806 |         0.1038 |         0.4901 |         0.7254 | 0.4901; 0.7254; 0.5046; 0.6545; 0.5283 | {"model_name": "ulysses-camara/legal-bert-pt-br", "lr": 5e-05, "warmup_ratio": 0.0}            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |         0.6581 |        0.0807 |        0.5789 |        0.7752 | 0.5789; 0.6915; 0.5875; 0.7752; 0.6573 |          0.6770 |         0.0843 |         0.6036 |         0.7849 | 0.6036; 0.7849; 0.6042; 0.7478; 0.6444 | {"model_name": "dominguesm/legal-bert-base-cased-ptbr", "lr": 5e-05, "warmup_ratio": 0.1}      |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |         0.5436 |        0.0952 |        0.4490 |        0.6936 | 0.4490; 0.6936; 0.5000; 0.5000; 0.5755 |          0.5701 |         0.0943 |         0.4902 |         0.7196 | 0.4902; 0.7196; 0.5141; 0.5211; 0.6057 | {"model_name": "dccmpmgfinalisticas/GovBERT-BR", "lr": 5e-05, "warmup_ratio": 0.0}             |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.6949 |                0.1438 |                0.4090 |                0.8335 |                0.5955 |               0.1540 |               0.3558 |               0.7696 |
| supervised         |                 0.6758 |                0.0616 |                0.5852 |                0.7720 |                0.6265 |               0.0485 |               0.5471 |               0.6945 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.7568 |      0.7363 |         0.3896 |          0.6271 |
| BERTimbau-large      |  0.7345 |      0.6383 |         0.1818 |          0.2469 |
| BERTimbauLaw         |  0.7663 |      0.6632 |         0.2400 |          0.5294 |
| BiLSTM-CRF           |  0.7507 |      0.6761 |         0.3333 |          0.5192 |
| DeepSeek-V4-Flash    |  0.8434 |      0.7154 |         0.6667 |          0.7438 |
| GPT-4.1              |  0.8098 |      0.6547 |         0.6667 |          0.7368 |
| GPT-4.1-mini         |  0.7930 |      0.5886 |         0.6345 |          0.7188 |
| GPT-4.1-nano         |  0.6854 |      0.2864 |         0.1023 |          0.5072 |
| GPT-5-mini           |  0.7036 |      0.2249 |         0.5897 |          0.6056 |
| GPT-5.1              |  0.7846 |      0.6053 |         0.6429 |          0.7313 |
| GPT-5.2              |  0.7553 |      0.4895 |         0.5294 |          0.6040 |
| GovBERT-BR           |  0.6687 |      0.6034 |         0.0000 |          0.3908 |
| JurisBERT            |  0.6842 |      0.6526 |         0.2703 |          0.6034 |
| Legal-BERT-STF       |  0.7579 |      0.6561 |         0.1639 |          0.5962 |
| Legal-BERTimbau-base |  0.7308 |      0.6102 |         0.1290 |          0.4222 |
| LegalBERTPT-br       |  0.6540 |      0.6298 |         0.0741 |          0.1194 |
| LegalBert-pt         |  0.7553 |      0.6509 |         0.3797 |          0.6552 |
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
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | MULTA         |      0.8261 |   0.6552 | 0.7308 |       133 |          203 |          161 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | OBRIGACAO     |      1.0000 |   0.4390 | 0.6102 |        54 |          123 |           54 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RECOMENDACAO  |      0.4000 |   0.0769 | 0.1290 |         4 |           52 |           10 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RESSARCIMENTO |      0.7037 |   0.3016 | 0.4222 |        19 |           63 |           27 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | MULTA         |      0.8383 |   0.6897 | 0.7568 |       140 |          203 |          167 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | OBRIGACAO     |      0.9487 |   0.6016 | 0.7363 |        74 |          123 |           78 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RECOMENDACAO  |      0.6000 |   0.2885 | 0.3896 |        15 |           52 |           25 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RESSARCIMENTO |      0.6727 |   0.5873 | 0.6271 |        37 |           63 |           55 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | MULTA         |      0.8609 |   0.6404 | 0.7345 |       130 |          203 |          151 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | OBRIGACAO     |      0.9231 |   0.4878 | 0.6383 |        60 |          123 |           65 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RECOMENDACAO  |      0.4286 |   0.1154 | 0.1818 |         6 |           52 |           14 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RESSARCIMENTO |      0.5556 |   0.1587 | 0.2469 |        10 |           63 |           18 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | MULTA         |      0.8701 |   0.6601 | 0.7507 |       134 |          203 |          154 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | OBRIGACAO     |      0.8000 |   0.5854 | 0.6761 |        72 |          123 |           90 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RECOMENDACAO  |      0.3947 |   0.2885 | 0.3333 |        15 |           52 |           38 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RESSARCIMENTO |      0.6585 |   0.4286 | 0.5192 |        27 |           63 |           41 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | MULTA         |      0.7345 |   0.6404 | 0.6842 |       130 |          203 |          177 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | OBRIGACAO     |      0.9254 |   0.5041 | 0.6526 |        62 |          123 |           67 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RECOMENDACAO  |      0.4545 |   0.1923 | 0.2703 |        10 |           52 |           22 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RESSARCIMENTO |      0.6604 |   0.5556 | 0.6034 |        35 |           63 |           53 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | MULTA         |      0.8545 |   0.6946 | 0.7663 |       141 |          203 |          165 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | OBRIGACAO     |      0.9403 |   0.5122 | 0.6632 |        63 |          123 |           67 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RECOMENDACAO  |      0.3913 |   0.1731 | 0.2400 |         9 |           52 |           23 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RESSARCIMENTO |      0.6923 |   0.4286 | 0.5294 |        27 |           63 |           39 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | MULTA         |      0.8208 |   0.6995 | 0.7553 |       142 |          203 |          173 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | OBRIGACAO     |      0.7753 |   0.5610 | 0.6509 |        69 |          123 |           89 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RECOMENDACAO  |      0.5556 |   0.2885 | 0.3797 |        15 |           52 |           27 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RESSARCIMENTO |      0.7170 |   0.6032 | 0.6552 |        38 |           63 |           53 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | MULTA         |      0.7317 |   0.5911 | 0.6540 |       120 |          203 |          164 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | OBRIGACAO     |      0.9828 |   0.4634 | 0.6298 |        57 |          123 |           58 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RECOMENDACAO  |      1.0000 |   0.0385 | 0.0741 |         2 |           52 |            2 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RESSARCIMENTO |      1.0000 |   0.0635 | 0.1194 |         4 |           63 |            4 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | MULTA         |      0.8136 |   0.7094 | 0.7579 |       144 |          203 |          177 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | OBRIGACAO     |      0.9394 |   0.5041 | 0.6561 |        62 |          123 |           66 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RECOMENDACAO  |      0.5556 |   0.0962 | 0.1639 |         5 |           52 |            9 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RESSARCIMENTO |      0.7561 |   0.4921 | 0.5962 |        31 |           63 |           41 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | MULTA         |      0.8605 |   0.5468 | 0.6687 |       111 |          203 |          129 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | OBRIGACAO     |      0.9643 |   0.4390 | 0.6034 |        54 |          123 |           56 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           52 |            0 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RESSARCIMENTO |      0.7083 |   0.2698 | 0.3908 |        17 |           63 |           24 |

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
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.6275 |          0.6945 |         0.6268 |        0.0290 |     0.5707 |     0.6832 |     0.1125 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.6103 |          0.6743 |         0.6093 |        0.0303 |     0.5490 |     0.6676 |     0.1186 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.5945 |          0.6198 |         0.5946 |        0.0259 |     0.5430 |     0.6447 |     0.1017 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.5853 |          0.6243 |         0.5848 |        0.0232 |     0.5394 |     0.6293 |     0.0899 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.5698 |          0.6492 |         0.5694 |        0.0300 |     0.5113 |     0.6283 |     0.1170 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.5526 |          0.6237 |         0.5519 |        0.0304 |     0.4917 |     0.6116 |     0.1199 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.5497 |          0.6531 |         0.5491 |        0.0300 |     0.4898 |     0.6086 |     0.1188 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.5435 |          0.6594 |         0.5428 |        0.0291 |     0.4868 |     0.6012 |     0.1144 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.5310 |          0.4162 |         0.5309 |        0.0228 |     0.4846 |     0.5744 |     0.0898 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.4730 |          0.6061 |         0.4715 |        0.0291 |     0.4149 |     0.5293 |     0.1144 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.4504 |          0.5980 |         0.4498 |        0.0304 |     0.3912 |     0.5102 |     0.1191 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.4157 |          0.5600 |         0.4158 |        0.0273 |     0.3629 |     0.4692 |     0.1063 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.3953 |          0.4341 |         0.3958 |        0.0251 |     0.3464 |     0.4458 |     0.0994 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.3693 |          0.5471 |         0.3685 |        0.0286 |     0.3137 |     0.4255 |     0.1118 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2856 |          0.3558 |         0.2853 |        0.0275 |     0.2312 |     0.3396 |     0.1084 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                        | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash | Llama-3.3-70B     | 0.7423 | 0.2856 |    0.4566 |     0.3947 |     0.5160 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-5.2           | Llama-3.3-70B     | 0.5945 | 0.2856 |    0.3092 |     0.2380 |     0.3791 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| llama-3.3-70b_few_shot                            | qwen2.5-72b_few_shot                                   | Llama-3.3-70B     | Qwen2.5-72B       | 0.2856 | 0.5853 |   -0.2995 |    -0.3687 |    -0.2295 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1-mini_few_shot                             | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini      | GPT-4.1-nano      | 0.6837 | 0.3953 |    0.2876 |     0.2304 |     0.3432 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-5.2           | DeepSeek-V4-Flash | 0.5945 | 0.7423 |   -0.1474 |    -0.1958 |    -0.1001 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7423 | 0.6103 |    0.1326 |     0.0733 |     0.1939 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7170 | 0.5945 |    0.1221 |     0.0803 |     0.1652 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7423 | 0.6275 |    0.1151 |     0.0553 |     0.1748 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-5.1           | GPT-5.2           | 0.6910 | 0.5945 |    0.0959 |     0.0526 |     0.1402 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.6275 | 0.5497 |    0.0777 |     0.0282 |     0.1285 |    0.0026 | True             |   0.0208 |         0.0442 | True            | True                  |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                                 | BERTimbau-base    | BiLSTM-CRF        | 0.6275 | 0.5698 |    0.0574 |    -0.0051 |     0.1193 |    0.0710 | False            |   0.3600 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7170 | 0.6837 |    0.0332 |     0.0082 |     0.0604 |    0.0084 | True             |   0.0588 |         0.1428 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2           | BERTimbau-base    | 0.5945 | 0.6275 |   -0.0323 |    -0.1055 |     0.0399 |    0.3786 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7170 | 0.7423 |   -0.0253 |    -0.0517 |     0.0009 |    0.0600 | False            |   0.3600 |         1.0000 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.6275 | 0.6103 |    0.0175 |    -0.0362 |     0.0753 |    0.5486 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2           | LegalBert-pt      | 0.5945 | 0.6103 |   -0.0148 |    -0.0849 |     0.0563 |    0.6810 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-5.2           | Qwen2.5-72B       | 0.5945 | 0.5853 |    0.0097 |    -0.0371 |     0.0569 |    0.6816 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |

**Itens 47–48 — Resumo:**

| metric                         | value                   |
|:-------------------------------|:------------------------|
| resampling_unit                | document                |
| n_docs_resampled               | 861                     |
| n_total_pairs                  | 171                     |
| n_significant_5pct_uncorrected | 130                     |
| highlighted_family_size        | 17                      |
| highlighted_n_sig_uncorrected  | 11                      |
| highlighted_n_sig_holm         | 10                      |
| highlighted_n_sig_bonferroni   | 10                      |
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
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.6275 |           0.1151 |   0.0000 |   0.0000 | False             |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.6103 |           0.1326 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.5945 |           0.1474 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.5853 |           0.1571 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.5698 |           0.1725 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.5526 |           0.1900 |   0.0000 |   0.0000 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.5497 |           0.1928 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.5435 |           0.1991 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.5310 |           0.2110 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.4730 |           0.2704 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.4504 |           0.2922 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.4157 |           0.3262 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.3953 |           0.3461 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.3693 |           0.3734 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2856 |           0.4566 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7423 | 0.2856 |    0.4566 |     0.3947 |     0.5160 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7170 | 0.2856 |    0.4313 |     0.3692 |     0.4925 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.6910 | 0.2856 |    0.4051 |     0.3395 |     0.4679 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.6837 | 0.2856 |    0.3980 |     0.3325 |     0.4608 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7423 | 0.3693 |    0.3734 |     0.2999 |     0.4402 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7170 | 0.3693 |    0.3481 |     0.2772 |     0.4128 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.3953 | 0.7423 |   -0.3461 |    -0.4053 |    -0.2853 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2856 | 0.6275 |   -0.3415 |    -0.4091 |    -0.2731 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7423 | 0.4157 |    0.3262 |     0.2617 |     0.3881 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2856 | 0.6103 |   -0.3240 |    -0.3953 |    -0.2505 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.6910 | 0.3693 |    0.3220 |     0.2507 |     0.3869 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7170 | 0.3953 |    0.3208 |     0.2614 |     0.3780 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.6837 | 0.3693 |    0.3149 |     0.2423 |     0.3808 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.5945 | 0.2856 |    0.3092 |     0.2380 |     0.3791 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7170 | 0.4157 |    0.3009 |     0.2403 |     0.3597 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2856 | 0.5853 |   -0.2995 |    -0.3687 |    -0.2295 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.3953 | 0.6910 |   -0.2947 |    -0.3514 |    -0.2366 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7423 | 0.4504 |    0.2922 |     0.2279 |     0.3547 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.6837 | 0.3953 |    0.2876 |     0.2304 |     0.3432 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2856 | 0.5698 |   -0.2841 |    -0.3498 |    -0.2174 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.6910 | 0.4157 |    0.2747 |     0.2098 |     0.3358 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7423 | 0.4730 |    0.2704 |     0.2049 |     0.3339 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.6837 | 0.4157 |    0.2676 |     0.2025 |     0.3291 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7170 | 0.4504 |    0.2668 |     0.2016 |     0.3290 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2856 | 0.5526 |   -0.2665 |    -0.3332 |    -0.2002 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2856 | 0.5497 |   -0.2638 |    -0.3334 |    -0.1915 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.6275 | 0.3693 |    0.2583 |     0.1946 |     0.3212 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2856 | 0.5435 |   -0.2574 |    -0.3210 |    -0.1925 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.5310 | 0.2856 |    0.2456 |     0.1786 |     0.3116 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7170 | 0.4730 |    0.2451 |     0.1800 |     0.3089 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.6103 | 0.3693 |    0.2408 |     0.1790 |     0.3007 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.6910 | 0.4504 |    0.2407 |     0.1741 |     0.3040 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.6837 | 0.4504 |    0.2336 |     0.1656 |     0.2985 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.3953 | 0.6275 |   -0.2310 |    -0.2976 |    -0.1646 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.5945 | 0.3693 |    0.2261 |     0.1532 |     0.2952 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.6910 | 0.4730 |    0.2189 |     0.1523 |     0.2840 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.5853 | 0.3693 |    0.2163 |     0.1457 |     0.2836 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.3953 | 0.6103 |   -0.2135 |    -0.2790 |    -0.1470 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.6837 | 0.4730 |    0.2118 |     0.1467 |     0.2752 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.6275 | 0.4157 |    0.2111 |     0.1480 |     0.2752 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.5310 | 0.7423 |   -0.2110 |    -0.2537 |    -0.1688 |    0.0000 | True             |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.5698 | 0.3693 |    0.2009 |     0.1404 |     0.2603 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7423 | 0.5435 |    0.1991 |     0.1376 |     0.2578 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.3953 | 0.5945 |   -0.1987 |    -0.2456 |    -0.1508 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.6103 | 0.4157 |    0.1936 |     0.1278 |     0.2577 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7423 | 0.5497 |    0.1928 |     0.1313 |     0.2534 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7423 | 0.5526 |    0.1900 |     0.1266 |     0.2532 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.3953 | 0.5853 |   -0.1890 |    -0.2426 |    -0.1348 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2856 | 0.4730 |   -0.1862 |    -0.2541 |    -0.1185 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7170 | 0.5310 |    0.1857 |     0.1460 |     0.2257 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.5526 | 0.3693 |    0.1834 |     0.1138 |     0.2481 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.5497 | 0.3693 |    0.1806 |     0.1153 |     0.2418 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.5945 | 0.4157 |    0.1788 |     0.1145 |     0.2424 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.6275 | 0.4504 |    0.1771 |     0.1233 |     0.2314 |    0.0000 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.3693 | 0.5435 |   -0.1743 |    -0.2380 |    -0.1078 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7170 | 0.5435 |    0.1738 |     0.1123 |     0.2325 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.3953 | 0.5698 |   -0.1736 |    -0.2484 |    -0.0983 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7423 | 0.5698 |    0.1725 |     0.1094 |     0.2339 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.5853 | 0.4157 |    0.1691 |     0.1031 |     0.2338 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7170 | 0.5497 |    0.1675 |     0.1043 |     0.2299 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7170 | 0.5526 |    0.1647 |     0.1029 |     0.2254 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2856 | 0.4504 |   -0.1644 |    -0.2327 |    -0.0954 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.5310 | 0.3693 |    0.1624 |     0.0917 |     0.2273 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.5310 | 0.6910 |   -0.1596 |    -0.2027 |    -0.1178 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.4504 | 0.6103 |   -0.1596 |    -0.2252 |    -0.0912 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7423 | 0.5853 |    0.1571 |     0.1131 |     0.2028 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.3953 | 0.5526 |   -0.1561 |    -0.2295 |    -0.0815 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.4730 | 0.6275 |   -0.1553 |    -0.2089 |    -0.1034 |    0.0000 | True             |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.5698 | 0.4157 |    0.1536 |     0.0972 |     0.2094 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.3953 | 0.5497 |   -0.1533 |    -0.2242 |    -0.0806 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.6837 | 0.5310 |    0.1525 |     0.1135 |     0.1928 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.6910 | 0.5435 |    0.1477 |     0.0829 |     0.2088 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.5945 | 0.7423 |   -0.1474 |    -0.1958 |    -0.1001 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7170 | 0.5698 |    0.1472 |     0.0857 |     0.2083 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.3953 | 0.5435 |   -0.1470 |    -0.2145 |    -0.0797 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.5945 | 0.4504 |    0.1448 |     0.0713 |     0.2158 |    0.0006 | True             |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.6910 | 0.5497 |    0.1413 |     0.0775 |     0.2041 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.6837 | 0.5435 |    0.1406 |     0.0777 |     0.2001 |    0.0002 | True             |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.6910 | 0.5526 |    0.1386 |     0.0752 |     0.2009 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.4730 | 0.6103 |   -0.1378 |    -0.2044 |    -0.0691 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.5526 | 0.4157 |    0.1361 |     0.0730 |     0.1988 |    0.0002 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.3953 | 0.5310 |   -0.1351 |    -0.1868 |    -0.0814 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.5853 | 0.4504 |    0.1351 |     0.0599 |     0.2090 |    0.0012 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.6837 | 0.5497 |    0.1342 |     0.0706 |     0.1963 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.5497 | 0.4157 |    0.1334 |     0.0677 |     0.1977 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7423 | 0.6103 |    0.1326 |     0.0733 |     0.1939 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7170 | 0.5853 |    0.1318 |     0.0892 |     0.1751 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.6837 | 0.5526 |    0.1315 |     0.0682 |     0.1933 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2856 | 0.4157 |   -0.1304 |    -0.1931 |    -0.0661 |    0.0000 | True             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.5435 | 0.4157 |    0.1270 |     0.0700 |     0.1863 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.5945 | 0.4730 |    0.1230 |     0.0461 |     0.1978 |    0.0026 | True             |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7170 | 0.5945 |    0.1221 |     0.0803 |     0.1652 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.6910 | 0.5698 |    0.1211 |     0.0544 |     0.1857 |    0.0004 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.4504 | 0.5698 |   -0.1196 |    -0.1795 |    -0.0596 |    0.0002 | True             |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.5310 | 0.4157 |    0.1151 |     0.0515 |     0.1777 |    0.0002 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7423 | 0.6275 |    0.1151 |     0.0553 |     0.1748 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.6837 | 0.5698 |    0.1140 |     0.0475 |     0.1787 |    0.0010 | True             |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.5853 | 0.4730 |    0.1133 |     0.0410 |     0.1853 |    0.0034 | True             |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.3953 | 0.2856 |    0.1105 |     0.0386 |     0.1805 |    0.0022 | True             |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7170 | 0.6103 |    0.1073 |     0.0487 |     0.1678 |    0.0014 | True             |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.6910 | 0.5853 |    0.1056 |     0.0618 |     0.1498 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.4730 | 0.3693 |    0.1031 |     0.0376 |     0.1669 |    0.0026 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.4504 | 0.5526 |   -0.1021 |    -0.1592 |    -0.0432 |    0.0016 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.4504 | 0.5497 |   -0.0994 |    -0.1497 |    -0.0488 |    0.0002 | True             |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.6837 | 0.5853 |    0.0985 |     0.0595 |     0.1384 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.4730 | 0.5698 |   -0.0979 |    -0.1590 |    -0.0370 |    0.0010 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.5310 | 0.6275 |   -0.0959 |    -0.1633 |    -0.0312 |    0.0038 | True             |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.6910 | 0.5945 |    0.0959 |     0.0526 |     0.1402 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.4504 | 0.5435 |   -0.0930 |    -0.1421 |    -0.0424 |    0.0004 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7170 | 0.6275 |    0.0898 |     0.0304 |     0.1480 |    0.0034 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.6837 | 0.5945 |    0.0888 |     0.0463 |     0.1328 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.6275 | 0.5435 |    0.0840 |     0.0361 |     0.1326 |    0.0002 | True             |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2856 | 0.3693 |   -0.0831 |    -0.1535 |    -0.0146 |    0.0194 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.4504 | 0.3693 |    0.0813 |     0.0154 |     0.1452 |    0.0162 | True             |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.6910 | 0.6103 |    0.0812 |     0.0190 |     0.1445 |    0.0112 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.5310 | 0.4504 |    0.0811 |     0.0148 |     0.1469 |    0.0170 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.4730 | 0.5526 |   -0.0803 |    -0.1393 |    -0.0210 |    0.0054 | True             |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.5310 | 0.6103 |   -0.0784 |    -0.1470 |    -0.0088 |    0.0284 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.6275 | 0.5497 |    0.0777 |     0.0282 |     0.1285 |    0.0026 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.4730 | 0.5497 |   -0.0776 |    -0.1275 |    -0.0284 |    0.0020 | True             |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.3953 | 0.4730 |   -0.0757 |    -0.1490 |    -0.0004 |    0.0492 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.6275 | 0.5526 |    0.0749 |     0.0166 |     0.1338 |    0.0110 | True             |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.6837 | 0.6103 |    0.0741 |     0.0105 |     0.1370 |    0.0180 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.4730 | 0.5435 |   -0.0712 |    -0.1204 |    -0.0235 |    0.0020 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.6103 | 0.5435 |    0.0665 |    -0.0026 |     0.1329 |    0.0592 | False            |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.5310 | 0.5945 |   -0.0637 |    -0.1049 |    -0.0223 |    0.0024 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.6910 | 0.6275 |    0.0637 |     0.0015 |     0.1250 |    0.0440 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.5497 | 0.6103 |   -0.0602 |    -0.1239 |     0.0049 |    0.0712 | False            |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.5310 | 0.4730 |    0.0593 |    -0.0131 |     0.1278 |    0.1082 | False            |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.6837 | 0.7423 |   -0.0585 |    -0.0912 |    -0.0270 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.5526 | 0.6103 |   -0.0574 |    -0.1233 |     0.0119 |    0.1048 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.6275 | 0.5698 |    0.0574 |    -0.0051 |     0.1193 |    0.0710 | False            |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.6837 | 0.6275 |    0.0566 |    -0.0042 |     0.1158 |    0.0698 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.4730 | 0.4157 |    0.0558 |    -0.0054 |     0.1160 |    0.0738 | False            |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.3953 | 0.4504 |   -0.0539 |    -0.1249 |     0.0171 |    0.1372 | False            |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.5310 | 0.5853 |   -0.0539 |    -0.1001 |    -0.0064 |    0.0262 | True             |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.5945 | 0.5435 |    0.0518 |    -0.0221 |     0.1221 |    0.1650 | False            |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.6910 | 0.7423 |   -0.0514 |    -0.0856 |    -0.0177 |    0.0026 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.3693 | 0.4157 |   -0.0473 |    -0.0950 |     0.0055 |    0.0768 | False            |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.5945 | 0.5497 |    0.0454 |    -0.0290 |     0.1176 |    0.2268 | False            |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.5945 | 0.5526 |    0.0427 |    -0.0317 |     0.1164 |    0.2556 | False            |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.5853 | 0.5435 |    0.0421 |    -0.0302 |     0.1107 |    0.2450 | False            |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.5853 | 0.6275 |   -0.0420 |    -0.1114 |     0.0275 |    0.2470 | False            |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.5698 | 0.6103 |   -0.0399 |    -0.1030 |     0.0246 |    0.2250 | False            |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.5310 | 0.5698 |   -0.0385 |    -0.1083 |     0.0290 |    0.2694 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.5853 | 0.5497 |    0.0357 |    -0.0328 |     0.1024 |    0.3078 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.4504 | 0.4157 |    0.0340 |    -0.0250 |     0.0939 |    0.2606 | False            |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7170 | 0.6837 |    0.0332 |     0.0082 |     0.0604 |    0.0084 | True             |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.5853 | 0.5526 |    0.0330 |    -0.0398 |     0.1062 |    0.3834 | False            |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.5945 | 0.6275 |   -0.0323 |    -0.1055 |     0.0399 |    0.3786 | False            |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.3953 | 0.3693 |    0.0273 |    -0.0373 |     0.0905 |    0.4064 | False            |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.5698 | 0.5435 |    0.0266 |    -0.0291 |     0.0835 |    0.3628 | False            |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7170 | 0.6910 |    0.0261 |    -0.0016 |     0.0545 |    0.0636 | False            |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7170 | 0.7423 |   -0.0253 |    -0.0517 |     0.0009 |    0.0600 | False            |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.5945 | 0.5698 |    0.0252 |    -0.0498 |     0.0993 |    0.5074 | False            |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.5853 | 0.6103 |   -0.0245 |    -0.0946 |     0.0463 |    0.4944 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.4730 | 0.4504 |    0.0218 |    -0.0375 |     0.0795 |    0.4542 | False            |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.5310 | 0.5526 |   -0.0210 |    -0.0910 |     0.0488 |    0.5612 | False            |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.5698 | 0.5497 |    0.0203 |    -0.0432 |     0.0855 |    0.5328 | False            |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.3953 | 0.4157 |   -0.0199 |    -0.0805 |     0.0415 |    0.5126 | False            |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.5310 | 0.5497 |   -0.0182 |    -0.0884 |     0.0493 |    0.6112 | False            |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.5698 | 0.5526 |    0.0175 |    -0.0435 |     0.0801 |    0.5892 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.6275 | 0.6103 |    0.0175 |    -0.0362 |     0.0753 |    0.5486 | False            |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.5853 | 0.5698 |    0.0154 |    -0.0602 |     0.0900 |    0.6954 | False            |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.5945 | 0.6103 |   -0.0148 |    -0.0849 |     0.0563 |    0.6810 | False            |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.5310 | 0.5435 |   -0.0119 |    -0.0803 |     0.0534 |    0.7428 | False            |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.5945 | 0.5853 |    0.0097 |    -0.0371 |     0.0569 |    0.6816 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.5526 | 0.5435 |    0.0091 |    -0.0368 |     0.0553 |    0.6940 | False            |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.6837 | 0.6910 |   -0.0071 |    -0.0384 |     0.0236 |    0.6618 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.5497 | 0.5435 |    0.0064 |    -0.0436 |     0.0566 |    0.8052 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.5526 | 0.5497 |    0.0027 |    -0.0560 |     0.0610 |    0.9264 | False            |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.7232 | 0.6945 | 0.6684 |  0.5875 |
| BERTimbau-large      | 0.6125 | 0.5980 | 0.5893 |  0.5341 |
| BERTimbauLaw         | 0.6667 | 0.6531 | 0.6313 |  0.5769 |
| BiLSTM-CRF           | 0.7094 | 0.6492 | 0.5916 |  0.5000 |
| DeepSeek-V4-Flash    | 0.8152 | 0.7696 | 0.7217 |  0.3174 |
| GPT-4.1              | 0.7784 | 0.7365 | 0.6766 |  0.2236 |
| GPT-4.1-mini         | 0.7343 | 0.6986 | 0.6366 |  0.2047 |
| GPT-4.1-nano         | 0.4921 | 0.4341 | 0.3779 |  0.1265 |
| GPT-5-mini           | 0.4356 | 0.4162 | 0.3922 |  0.0832 |
| GPT-5.1              | 0.7321 | 0.7046 | 0.6555 |  0.2375 |
| GPT-5.2              | 0.6620 | 0.6198 | 0.5654 |  0.1686 |
| GovBERT-BR           | 0.5662 | 0.5600 | 0.5415 |  0.4923 |
| JurisBERT            | 0.6526 | 0.6237 | 0.5895 |  0.5000 |
| Legal-BERT-STF       | 0.6730 | 0.6594 | 0.6185 |  0.5477 |
| Legal-BERTimbau-base | 0.6205 | 0.6061 | 0.5830 |  0.5253 |
| LegalBERTPT-br       | 0.5590 | 0.5471 | 0.5232 |  0.4843 |
| LegalBert-pt         | 0.6922 | 0.6743 | 0.6539 |  0.5594 |
| Llama-3.3-70B        | 0.3910 | 0.3558 | 0.3173 |  0.0513 |
| Qwen2.5-72B          | 0.6556 | 0.6243 | 0.5773 |  0.2290 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5):

| iou_threshold   |   spearman_vs_0.5 |
|:----------------|------------------:|
| 0.3             |            0.9825 |
| 0.5             |            1.0000 |
| 0.7             |            0.9667 |
| exact           |            0.3352 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  231 |         0.7696 |                0.8147 |          0.0452 |                0.7390 |                       0.8271 |                 0.0881 |             0.8027 |                    0.8027 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  231 |         0.7365 |                0.7987 |          0.0622 |                0.6578 |                       0.7640 |                 0.1062 |             0.8367 |                    0.8367 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  231 |         0.6986 |                0.7742 |          0.0756 |                0.5962 |                       0.7154 |                 0.1192 |             0.8435 |                    0.8435 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  231 |         0.7046 |                0.7729 |          0.0683 |                0.6211 |                       0.7357 |                 0.1145 |             0.8141 |                    0.8141 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  231 |         0.6945 |                0.7084 |          0.0139 |                0.8185 |                       0.8581 |                 0.0396 |             0.6032 |                    0.6032 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  231 |         0.6198 |                0.6990 |          0.0792 |                0.5057 |                       0.6204 |                 0.1147 |             0.8005 |                    0.8005 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  231 |         0.6743 |                0.6884 |          0.0141 |                0.7719 |                       0.8098 |                 0.0379 |             0.5986 |                    0.5986 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  231 |         0.6243 |                0.6845 |          0.0603 |                0.5491 |                       0.6497 |                 0.1006 |             0.7234 |                    0.7234 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  231 |         0.6492 |                0.6739 |          0.0247 |                0.7678 |                       0.8407 |                 0.0729 |             0.5624 |                    0.5624 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  231 |         0.6594 |                0.6685 |          0.0091 |                0.8259 |                       0.8551 |                 0.0292 |             0.5488 |                    0.5488 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  231 |         0.6531 |                0.6667 |          0.0136 |                0.8163 |                       0.8602 |                 0.0439 |             0.5442 |                    0.5442 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  231 |         0.6237 |                0.6380 |          0.0143 |                0.7429 |                       0.7848 |                 0.0418 |             0.5374 |                    0.5374 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  231 |         0.6061 |                0.6140 |          0.0080 |                0.8333 |                       0.8642 |                 0.0309 |             0.4762 |                    0.4762 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  231 |         0.5980 |                0.6086 |          0.0106 |                0.8306 |                       0.8729 |                 0.0422 |             0.4671 |                    0.4671 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  231 |         0.4162 |                0.6068 |          0.1906 |                0.2780 |                       0.4790 |                 0.2010 |             0.8277 |                    0.8277 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  231 |         0.5600 |                0.5617 |          0.0017 |                0.8708 |                       0.8792 |                 0.0084 |             0.4127 |                    0.4127 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  231 |         0.5471 |                0.5504 |          0.0033 |                0.8026 |                       0.8170 |                 0.0143 |             0.4150 |                    0.4150 |
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
