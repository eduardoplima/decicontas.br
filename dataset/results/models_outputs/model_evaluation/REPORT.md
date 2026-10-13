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
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |     0.8582 |           0.8206 |            0.8468 |         0.8698 |    0.8109 |          0.7837 |           0.7787 |        0.8458 |
| gpt-4.1_few_shot                                       | GPT-4.1              |     0.8341 |           0.8065 |            0.7929 |         0.8797 |    0.7645 |          0.7424 |           0.6827 |        0.8685 |
| gpt-5.1_few_shot                                       | GPT-5.1              |     0.8083 |           0.7812 |            0.7560 |         0.8683 |    0.7458 |          0.7322 |           0.6574 |        0.8617 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.7824 |           0.6861 |            0.9600 |         0.6602 |    0.7391 |          0.6603 |           0.8475 |        0.6553 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |     0.8156 |           0.7853 |            0.7558 |         0.8858 |    0.7343 |          0.7175 |           0.6266 |        0.8866 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.7815 |           0.6765 |            0.9444 |         0.6666 |    0.7248 |          0.6457 |           0.7786 |        0.6780 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.7726 |           0.6444 |            0.9434 |         0.6542 |    0.7217 |          0.6220 |           0.7898 |        0.6644 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.7051 |           0.5313 |            0.9662 |         0.5551 |    0.7044 |          0.5555 |           0.9011 |        0.5782 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.7508 |           0.5847 |            0.9473 |         0.6219 |    0.7018 |          0.5656 |           0.8101 |        0.6190 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.7255 |           0.5177 |            0.9670 |         0.5805 |    0.6866 |          0.5063 |           0.8547 |        0.5737 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.7305 |           0.5559 |            0.9629 |         0.5884 |    0.6773 |          0.5384 |           0.8173 |        0.5782 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.7250 |           0.6182 |            0.9306 |         0.5939 |    0.6767 |          0.6113 |           0.7599 |        0.6100 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.7833 |           0.7682 |            0.7081 |         0.8763 |    0.6760 |          0.6700 |           0.5516 |        0.8730 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.7448 |           0.6117 |            0.8728 |         0.6496 |    0.6735 |          0.6009 |           0.7774 |        0.5941 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7372 |           0.6920 |            0.7148 |         0.7611 |    0.6595 |          0.6147 |           0.5800 |        0.7642 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.5368 |           0.2862 |            0.9751 |         0.3703 |    0.5008 |          0.2836 |           0.8196 |        0.3605 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.6071 |           0.5462 |            0.5818 |         0.6348 |    0.4640 |          0.4391 |           0.3788 |        0.5986 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.5998 |           0.6709 |            0.4440 |         0.9237 |    0.4595 |          0.5942 |           0.3069 |        0.9138 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4121 |           0.3040 |            0.7593 |         0.2828 |    0.3590 |          0.2874 |           0.6120 |        0.2540 |

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
| few-shot           |                 0.7173 |                0.1480 |                0.4121 |                0.8582 |                0.6304 |               0.1613 |               0.3590 |               0.8109 |
| supervised         |                 0.7255 |                0.0712 |                0.5368 |                0.7824 |                0.6807 |               0.0671 |               0.5008 |               0.7391 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.8109 |      0.7230 |         0.2500 |          0.7040 |
| BERTimbau-large      |  0.8253 |      0.7175 |         0.3953 |          0.6446 |
| BERTimbauLaw         |  0.8165 |      0.6927 |         0.0000 |          0.5161 |
| BiLSTM-CRF           |  0.7570 |      0.6834 |         0.4000 |          0.5631 |
| DeepSeek-V4-Flash    |  0.8916 |      0.7398 |         0.7101 |          0.7934 |
| GPT-4.1              |  0.8546 |      0.6547 |         0.7083 |          0.7519 |
| GPT-4.1-mini         |  0.8497 |      0.5946 |         0.6759 |          0.7500 |
| GPT-4.1-nano         |  0.7136 |      0.2864 |         0.1477 |          0.6087 |
| GPT-5-mini           |  0.7932 |      0.2371 |         0.6282 |          0.7183 |
| GPT-5.1              |  0.8481 |      0.6053 |         0.7143 |          0.7612 |
| GPT-5.2              |  0.8059 |      0.5105 |         0.7059 |          0.6577 |
| GovBERT-BR           |  0.8011 |      0.7016 |         0.0000 |          0.7193 |
| JurisBERT            |  0.7455 |      0.6765 |         0.3457 |          0.6777 |
| Legal-BERT-STF       |  0.7716 |      0.7071 |         0.1091 |          0.5660 |
| Legal-BERTimbau-base |  0.7742 |      0.7429 |         0.0727 |          0.6727 |
| LegalBERTPT-br       |  0.6814 |      0.4528 |         0.0000 |          0.0000 |
| LegalBert-pt         |  0.8074 |      0.7570 |         0.3768 |          0.7000 |
| Llama-3.3-70B        |  0.4286 |      0.3939 |         0.2963 |          0.0308 |
| Qwen2.5-72B          |  0.8287 |      0.5392 |         0.3851 |          0.7059 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                                  | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:-------------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4.1_few_shot                                       | GPT-4.1              | MULTA         |      0.7828 |   0.9409 | 0.8546 |       191 |          203 |          244 |
| gpt-4.1_few_shot                                       | GPT-4.1              | OBRIGACAO     |      0.5871 |   0.7398 | 0.6547 |        91 |          123 |          155 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RECOMENDACAO  |      0.5543 |   0.9808 | 0.7083 |        51 |           52 |           92 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RESSARCIMENTO |      0.7143 |   0.7937 | 0.7519 |        50 |           63 |           70 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | MULTA         |      0.7617 |   0.9606 | 0.8497 |       195 |          203 |          256 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | OBRIGACAO     |      0.4714 |   0.8049 | 0.5946 |        99 |          123 |          210 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RECOMENDACAO  |      0.5269 |   0.9423 | 0.6759 |        49 |           52 |           93 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RESSARCIMENTO |      0.7385 |   0.7619 | 0.7500 |        48 |           63 |           65 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | MULTA         |      0.6816 |   0.7488 | 0.7136 |       152 |          203 |          223 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | OBRIGACAO     |      0.2073 |   0.4634 | 0.2864 |        57 |          123 |          275 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RECOMENDACAO  |      0.1048 |   0.2500 | 0.1477 |        13 |           52 |          124 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RESSARCIMENTO |      0.5600 |   0.6667 | 0.6087 |        42 |           63 |           75 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | MULTA         |      0.6992 |   0.9163 | 0.7932 |       186 |          203 |          266 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | OBRIGACAO     |      0.1354 |   0.9512 | 0.2371 |       117 |          123 |          864 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RECOMENDACAO  |      0.4712 |   0.9423 | 0.6282 |        49 |           52 |          104 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RESSARCIMENTO |      0.6456 |   0.8095 | 0.7183 |        51 |           63 |           79 |
| gpt-5.1_few_shot                                       | GPT-5.1              | MULTA         |      0.7857 |   0.9212 | 0.8481 |       187 |          203 |          238 |
| gpt-5.1_few_shot                                       | GPT-5.1              | OBRIGACAO     |      0.5083 |   0.7480 | 0.6053 |        92 |          123 |          181 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RECOMENDACAO  |      0.5682 |   0.9615 | 0.7143 |        50 |           52 |           88 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RESSARCIMENTO |      0.7183 |   0.8095 | 0.7612 |        51 |           63 |           71 |
| gpt-5.2_few_shot                                       | GPT-5.2              | MULTA         |      0.7048 |   0.9409 | 0.8059 |       191 |          203 |          271 |
| gpt-5.2_few_shot                                       | GPT-5.2              | OBRIGACAO     |      0.3774 |   0.7886 | 0.5105 |        97 |          123 |          257 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RECOMENDACAO  |      0.5714 |   0.9231 | 0.7059 |        48 |           52 |           84 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RESSARCIMENTO |      0.5698 |   0.7778 | 0.6577 |        49 |           63 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | MULTA         |      0.8726 |   0.9113 | 0.8916 |       185 |          203 |          212 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | OBRIGACAO     |      0.7398 |   0.7398 | 0.7398 |        91 |          123 |          123 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RECOMENDACAO  |      0.5698 |   0.9423 | 0.7101 |        49 |           52 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RESSARCIMENTO |      0.8276 |   0.7619 | 0.7934 |        48 |           63 |           58 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | MULTA         |      0.7792 |   0.2956 | 0.4286 |        60 |          203 |           77 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | OBRIGACAO     |      0.5200 |   0.3171 | 0.3939 |        39 |          123 |           75 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RECOMENDACAO  |      0.4138 |   0.2308 | 0.2963 |        12 |           52 |           29 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RESSARCIMENTO |      0.5000 |   0.0159 | 0.0308 |         1 |           63 |            2 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | MULTA         |      0.7817 |   0.8818 | 0.8287 |       179 |          203 |          229 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | OBRIGACAO     |      0.4647 |   0.6423 | 0.5392 |        79 |          123 |          170 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RECOMENDACAO  |      0.2844 |   0.5962 | 0.3851 |        31 |           52 |          109 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RESSARCIMENTO |      0.6575 |   0.7619 | 0.7059 |        48 |           63 |           73 |
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
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.2255 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.8500 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            49.1285 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                             5.8505 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            14.3678 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            16.0113 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.8511 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.8656 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            14.1930 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            15.8776 |

## F. Function calling vs JSON schema

**Métricas overall:**

| model             | method           |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | function_calling |     0.8629 |    0.8161 |          0.7883 |           0.7845 |        0.8503 |
| deepseek-v4-flash | json_schema      |     0.8512 |    0.8000 |          0.7642 |           0.7722 |        0.8299 |
| gpt-4.1           | function_calling |     0.8333 |    0.7763 |          0.7516 |           0.6960 |        0.8776 |
| gpt-4.1           | json_schema      |     0.8450 |    0.7737 |          0.7502 |           0.6976 |        0.8685 |

**Δ por modelo (FC − JS):**

| model             |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:------------------|-----------------:|----------------:|-----------------------:|--------------------:|
| deepseek-v4-flash |           0.0118 |          0.0161 |                 0.0124 |              0.0204 |
| gpt-4.1           |          -0.0117 |          0.0026 |                -0.0016 |              0.0091 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9029 |      0.7368 |         0.7101 |          0.8033 |
| deepseek-v4-flash | json_schema      |  0.8937 |      0.7309 |         0.6615 |          0.7705 |
| gpt-4.1           | function_calling |  0.8655 |      0.6764 |         0.7183 |          0.7463 |
| gpt-4.1           | json_schema      |  0.8591 |      0.6716 |         0.7183 |          0.7519 |

**Span Precision (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8900 |      0.7339 |         0.5698 |          0.8305 |
| deepseek-v4-flash | json_schema      |  0.8768 |      0.7222 |         0.5513 |          0.7966 |
| gpt-4.1           | function_calling |  0.7942 |      0.6118 |         0.5667 |          0.7042 |
| gpt-4.1           | json_schema      |  0.7869 |      0.6207 |         0.5667 |          0.7143 |

**Span Recall (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9163 |      0.7398 |         0.9423 |          0.7778 |
| deepseek-v4-flash | json_schema      |  0.9113 |      0.7398 |         0.8269 |          0.7460 |
| gpt-4.1           | function_calling |  0.9507 |      0.7561 |         0.9808 |          0.7937 |
| gpt-4.1           | json_schema      |  0.9458 |      0.7317 |         0.9808 |          0.7937 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model             | technique   |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | cot         |     0.8495 |    0.7527 |          0.7179 |           0.6615 |        0.8730 |
| deepseek-v4-flash | few_shot    |     0.8582 |    0.8109 |          0.7837 |           0.7787 |        0.8458 |
| deepseek-v4-flash | two_stage   |     0.8608 |    0.8126 |          0.7806 |           0.7780 |        0.8503 |
| gpt-4.1           | cot         |     0.8279 |    0.7662 |          0.7450 |           0.6826 |        0.8730 |
| gpt-4.1           | few_shot    |     0.8341 |    0.7645 |          0.7424 |           0.6827 |        0.8685 |
| gpt-4.1           | two_stage   |     0.8362 |    0.7751 |          0.7519 |           0.6955 |        0.8753 |
| gpt-5.2           | cot         |     0.8144 |    0.7199 |          0.7322 |           0.5997 |        0.9002 |
| gpt-5.2           | few_shot    |     0.7833 |    0.6760 |          0.6700 |           0.5516 |        0.8730 |
| gpt-5.2           | two_stage   |     0.8152 |    0.7324 |          0.7239 |           0.6250 |        0.8844 |
| llama-3.3-70b     | cot         |     0.3090 |    0.2679 |          0.2017 |           0.6303 |        0.1701 |
| llama-3.3-70b     | few_shot    |     0.4121 |    0.3590 |          0.2874 |           0.6120 |        0.2540 |
| llama-3.3-70b     | two_stage   |     0.1722 |    0.1355 |          0.1237 |           0.5574 |        0.0771 |
| qwen2.5-72b       | cot         |     0.7710 |    0.6782 |          0.6278 |           0.5883 |        0.8005 |
| qwen2.5-72b       | few_shot    |     0.7372 |    0.6595 |          0.6147 |           0.5800 |        0.7642 |
| qwen2.5-72b       | two_stage   |     0.7603 |    0.6753 |          0.6204 |           0.6036 |        0.7664 |

**Span F1 pivotado (modelo × técnica):**

| model             |    cot |   few_shot |   two_stage |
|:------------------|-------:|-----------:|------------:|
| deepseek-v4-flash | 0.7527 |     0.8109 |      0.8126 |
| gpt-4.1           | 0.7662 |     0.7645 |      0.7751 |
| gpt-5.2           | 0.7199 |     0.6760 |      0.7324 |
| llama-3.3-70b     | 0.2679 |     0.3590 |      0.1355 |
| qwen2.5-72b       | 0.6782 |     0.6595 |      0.6753 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique   | token_f1           | token_f1.1          | token_f1.2          | token_f1.3         | span_f1            | span_f1.1          | span_f1.2           | span_f1.3          |
|:------------|:-------------------|:--------------------|:--------------------|:-------------------|:-------------------|:-------------------|:--------------------|:-------------------|
| nan         | mean               | std                 | min                 | max                | mean               | std                | min                 | max                |
| cot         | 0.7143538578719015 | 0.22842559702563064 | 0.30897431724227725 | 0.8495299028595951 | 0.6369526908774199 | 0.2091032949763975 | 0.26785714285714285 | 0.7661691542288556 |
| few_shot    | 0.7249607947981642 | 0.1810418305776049  | 0.4120588148279637  | 0.8581557442717513 | 0.653967556497254  | 0.1763289423368148 | 0.3589743589743589  | 0.8108695652173912 |
| two_stage   | 0.6889482757043968 | 0.2912451213309452  | 0.17219457260144586 | 0.8608133606327031 | 0.6261690648870253 | 0.2790261067963767 | 0.13545816733067728 | 0.8125677139761647 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9095 |      0.7132 |         0.4785 |          0.7705 |
| deepseek-v4-flash | few_shot    |  0.8916 |      0.7398 |         0.7101 |          0.7934 |
| deepseek-v4-flash | two_stage   |  0.8916 |      0.7667 |         0.7101 |          0.7538 |
| gpt-4.1           | cot         |  0.8604 |      0.6528 |         0.7092 |          0.7576 |
| gpt-4.1           | few_shot    |  0.8546 |      0.6547 |         0.7083 |          0.7519 |
| gpt-4.1           | two_stage   |  0.8629 |      0.6739 |         0.7133 |          0.7576 |
| gpt-5.2           | cot         |  0.8578 |      0.5233 |         0.7194 |          0.8281 |
| gpt-5.2           | few_shot    |  0.8059 |      0.5105 |         0.7059 |          0.6577 |
| gpt-5.2           | two_stage   |  0.8470 |      0.5757 |         0.7194 |          0.7536 |
| llama-3.3-70b     | cot         |  0.3454 |      0.2971 |         0.1644 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.4286 |      0.3939 |         0.2963 |          0.0308 |
| llama-3.3-70b     | two_stage   |  0.1478 |      0.1497 |         0.1667 |          0.0308 |
| qwen2.5-72b       | cot         |  0.8519 |      0.5714 |         0.3827 |          0.7050 |
| qwen2.5-72b       | few_shot    |  0.8287 |      0.5392 |         0.3851 |          0.7059 |
| qwen2.5-72b       | two_stage   |  0.8392 |      0.5744 |         0.4110 |          0.6569 |

**Span Precision por entidade (mesmo eixo):**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.8802 |      0.6510 |         0.3185 |          0.7966 |
| deepseek-v4-flash | few_shot    |  0.8726 |      0.7398 |         0.5698 |          0.8276 |
| deepseek-v4-flash | two_stage   |  0.8726 |      0.7863 |         0.5698 |          0.7313 |
| gpt-4.1           | cot         |  0.7925 |      0.5697 |         0.5618 |          0.7246 |
| gpt-4.1           | few_shot    |  0.7828 |      0.5871 |         0.5543 |          0.7143 |
| gpt-4.1           | two_stage   |  0.7934 |      0.6078 |         0.5604 |          0.7246 |
| gpt-5.2           | cot         |  0.7814 |      0.3840 |         0.5747 |          0.8154 |
| gpt-5.2           | few_shot    |  0.7048 |      0.3774 |         0.5714 |          0.5698 |
| gpt-5.2           | two_stage   |  0.7702 |      0.4533 |         0.5747 |          0.6933 |
| llama-3.3-70b     | cot         |  0.9348 |      0.5000 |         0.2857 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.7792 |      0.5200 |         0.4138 |          0.5000 |
| llama-3.3-70b     | two_stage   |  0.6296 |      0.4583 |         0.6250 |          0.5000 |
| qwen2.5-72b       | cot         |  0.7924 |      0.4831 |         0.2818 |          0.6447 |
| qwen2.5-72b       | few_shot    |  0.7817 |      0.4647 |         0.2844 |          0.6575 |
| qwen2.5-72b       | two_stage   |  0.7965 |      0.5000 |         0.3191 |          0.6081 |

**Span Recall por entidade:**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9409 |      0.7886 |         0.9615 |          0.7460 |
| deepseek-v4-flash | few_shot    |  0.9113 |      0.7398 |         0.9423 |          0.7619 |
| deepseek-v4-flash | two_stage   |  0.9113 |      0.7480 |         0.9423 |          0.7778 |
| gpt-4.1           | cot         |  0.9409 |      0.7642 |         0.9615 |          0.7937 |
| gpt-4.1           | few_shot    |  0.9409 |      0.7398 |         0.9808 |          0.7937 |
| gpt-4.1           | two_stage   |  0.9458 |      0.7561 |         0.9808 |          0.7937 |
| gpt-5.2           | cot         |  0.9507 |      0.8211 |         0.9615 |          0.8413 |
| gpt-5.2           | few_shot    |  0.9409 |      0.7886 |         0.9231 |          0.7778 |
| gpt-5.2           | two_stage   |  0.9409 |      0.7886 |         0.9615 |          0.8254 |
| llama-3.3-70b     | cot         |  0.2118 |      0.2114 |         0.1154 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.2956 |      0.3171 |         0.2308 |          0.0159 |
| llama-3.3-70b     | two_stage   |  0.0837 |      0.0894 |         0.0962 |          0.0159 |
| qwen2.5-72b       | cot         |  0.9212 |      0.6992 |         0.5962 |          0.7778 |
| qwen2.5-72b       | few_shot    |  0.8818 |      0.6423 |         0.5962 |          0.7619 |
| qwen2.5-72b       | two_stage   |  0.8867 |      0.6748 |         0.5769 |          0.7143 |

## I. Análise de erros do melhor modelo

**Melhor modelo identificado por span F1: DeepSeek-V4-Flash.**

**Contagens por tipo de erro:**

| kind       |   count |
|:-----------|--------:|
| match      |     373 |
| FP         |      64 |
| FN_no_pred |      38 |
| boundary   |      38 |
| FN_overlap |      30 |
| type_error |       4 |

**Matriz rótulo × tipo de erro:**

| label         |   FN_no_pred |   FN_overlap |   FP |   boundary |   match |   type_error |
|:--------------|-------------:|-------------:|-----:|-----------:|--------:|-------------:|
| MULTA         |            6 |           12 |    6 |         11 |     185 |            0 |
| OBRIGACAO     |           22 |           10 |   20 |         12 |      91 |            0 |
| RECOMENDACAO  |            3 |            0 |   36 |          0 |      49 |            0 |
| RESSARCIMENTO |            7 |            8 |    2 |         15 |      48 |            4 |

**Pares de tipo errado (gold → pred):**

| label         | pred_label   |   count |
|:--------------|:-------------|--------:|
| RESSARCIMENTO | MULTA        |       4 |

**Histograma de IoU para erros de fronteira:**

|   bin_low |   bin_high |   count |
|----------:|-----------:|--------:|
|    0.0000 |     0.2000 |  4.0000 |
|    0.2000 |     0.4000 | 21.0000 |
|    0.4000 |     0.5000 | 13.0000 |
|    0.5000 |     0.7000 |  0.0000 |
|    0.7000 |     0.9000 |  0.0000 |
|    0.9000 |     1.0000 |  0.0000 |

## J. Significância estatística (bootstrap pareado)

**Item 41 — N de reamostragens**: 10.000.

**Item 42 — IC 95% por modelo:**

| model                                                  | display              |   span_f1_point |   span_f1_micro |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:-------------------------------------------------------|:---------------------|----------------:|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |          0.7837 |          0.8109 |         0.7826 |        0.0216 |     0.7386 |     0.8234 |     0.0849 |
| gpt-4.1_few_shot                                       | GPT-4.1              |          0.7424 |          0.7645 |         0.7414 |        0.0224 |     0.6964 |     0.7843 |     0.0879 |
| gpt-5.1_few_shot                                       | GPT-5.1              |          0.7322 |          0.7458 |         0.7311 |        0.0223 |     0.6871 |     0.7737 |     0.0866 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |          0.7175 |          0.7343 |         0.7166 |        0.0224 |     0.6717 |     0.7598 |     0.0881 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.6700 |          0.6760 |         0.6691 |        0.0239 |     0.6208 |     0.7143 |     0.0934 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.6603 |          0.7391 |         0.6587 |        0.0274 |     0.6040 |     0.7112 |     0.1072 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.6457 |          0.7248 |         0.6453 |        0.0274 |     0.5923 |     0.6988 |     0.1065 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.6220 |          0.7217 |         0.6213 |        0.0268 |     0.5695 |     0.6742 |     0.1047 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.6147 |          0.6595 |         0.6138 |        0.0236 |     0.5671 |     0.6588 |     0.0917 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.6113 |          0.6767 |         0.6109 |        0.0284 |     0.5560 |     0.6667 |     0.1108 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.6009 |          0.6735 |         0.6002 |        0.0291 |     0.5424 |     0.6572 |     0.1148 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.5942 |          0.4595 |         0.5932 |        0.0202 |     0.5520 |     0.6314 |     0.0794 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.5656 |          0.7018 |         0.5653 |        0.0239 |     0.5187 |     0.6126 |     0.0939 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.5555 |          0.7044 |         0.5551 |        0.0207 |     0.5134 |     0.5948 |     0.0814 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.5384 |          0.6773 |         0.5372 |        0.0269 |     0.4835 |     0.5895 |     0.1060 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.5063 |          0.6866 |         0.5060 |        0.0245 |     0.4568 |     0.5521 |     0.0953 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.4391 |          0.4640 |         0.4394 |        0.0240 |     0.3916 |     0.4869 |     0.0954 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2874 |          0.3590 |         0.2871 |        0.0276 |     0.2330 |     0.3418 |     0.1088 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.2836 |          0.5008 |         0.2836 |        0.0190 |     0.2456 |     0.3206 |     0.0751 |

**Itens 43–46 — Pares destacados:**

| model_a                                            | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm_all |   p_bonferroni_all |   p_bh_all | sig_holm_all_5pct   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:---------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|-------------:|-------------------:|-----------:|:--------------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                         | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7837 | 0.6220 |    0.1613 |     0.1036 |     0.2163 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash | BERTimbau-large   | 0.7837 | 0.6457 |    0.1372 |     0.0750 |     0.1978 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7837 | 0.6603 |    0.1239 |     0.0655 |     0.1834 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |   0.0016 |         0.0024 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.6220 | 0.5063 |    0.1154 |     0.0618 |     0.1699 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-4.1_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1           | LegalBert-pt      | 0.7424 | 0.6603 |    0.0827 |     0.0264 |     0.1409 |    0.0048 | True             |       0.2784 |             0.8208 |     0.0072 | False               |   0.0288 |         0.0576 | True            | False                 |            12 |
| gpt-4.1_few_shot                                   | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7424 | 0.6700 |    0.0723 |     0.0389 |     0.1089 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| bilstm-crf__supervised                             | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF        | LegalBert-pt      | 0.6009 | 0.6603 |   -0.0585 |    -0.1272 |     0.0104 |    0.0964 | False            |       1.0000 |             1.0000 |     0.1202 | False               |   0.3856 |         1.0000 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7424 | 0.7837 |   -0.0412 |    -0.0700 |    -0.0134 |    0.0018 | True             |       0.1188 |             0.3078 |     0.0029 | False               |   0.0126 |         0.0216 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.6220 | 0.6603 |   -0.0374 |    -0.0955 |     0.0220 |    0.2194 | False            |       1.0000 |             1.0000 |     0.2570 | False               |   0.6582 |         1.0000 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7424 | 0.7175 |    0.0248 |     0.0005 |     0.0510 |    0.0458 | True             |       1.0000 |             1.0000 |     0.0593 | False               |   0.2290 |         0.5496 | False           | False                 |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base    | BERTimbau-large   | 0.6220 | 0.6457 |   -0.0240 |    -0.0701 |     0.0215 |    0.2954 | False            |       1.0000 |             1.0000 |     0.3323 | False               |   0.6582 |         1.0000 | False           | False                 |            12 |
| neuralmind_bert-large-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large   | LegalBert-pt      | 0.6457 | 0.6603 |   -0.0134 |    -0.0716 |     0.0473 |    0.6440 | False            |       1.0000 |             1.0000 |     0.6756 | False               |   0.6582 |         1.0000 | False           | False                 |            12 |

**Itens 47–48 — Resumo:**

| metric                         | value                   |
|:-------------------------------|:------------------------|
| resampling_unit                | document                |
| n_docs_resampled               | 861                     |
| n_total_pairs                  | 171                     |
| n_significant_5pct_uncorrected | 133                     |
| n_sig_holm_all                 | 99                      |
| n_sig_bonferroni_all           | 96                      |
| n_sig_bh_all                   | 128                     |
| highlighted_family_size        | 12                      |
| highlighted_n_sig_uncorrected  | 8                       |
| highlighted_n_sig_holm         | 7                       |
| highlighted_n_sig_bonferroni   | 6                       |
| highlighted_n_sig_holm_all     | 5                       |
| smallest_significant_abs_diff  | 0.024783537259267553    |
| smallest_significant_pair      | GPT-4.1 vs GPT-4.1-mini |
| leader_model                   | DeepSeek-V4-Flash       |
| leader_group_size_holm         | 3                       |

**p48a — Correção para múltiplas comparações.** A família inferencial é o conjunto completo dos pares (`p_holm_all`, `p_bonferroni_all`, `p_bh_all`), pré-especificado por construção; os pares destacados acima são uma seleção para leitura e herdam esses valores. As colunas `p_holm`/`p_bonferroni` (correção restrita aos destacados) são mantidas apenas como referência.

**Grupo do líder (DS-p.55a).** Comparações líder × demais modelos, com o `p_holm` da família completa de pares; `in_leader_group=True` marca os modelos estatisticamente indistinguíveis do líder a 5% — a fonte do marcador (†) na tabela geral de resultados:

| model                                                  | display              |   span_f1 |   diff_vs_leader |    p_raw |   p_holm | in_leader_group   |
|:-------------------------------------------------------|:---------------------|----------:|-----------------:|---------:|---------:|:------------------|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |    0.7837 |           0.0000 | nan      | nan      | True              |
| gpt-4.1_few_shot                                       | GPT-4.1              |    0.7424 |           0.0412 |   0.0018 |   0.1188 | True              |
| gpt-5.1_few_shot                                       | GPT-5.1              |    0.7322 |           0.0515 |   0.0024 |   0.1560 | True              |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |    0.7175 |           0.0659 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.6700 |           0.1135 |   0.0000 |   0.0000 | False             |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.6603 |           0.1239 |   0.0002 |   0.0168 | False             |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.6457 |           0.1372 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.6220 |           0.1613 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.6147 |           0.1687 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.6113 |           0.1717 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.6009 |           0.1823 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.5942 |           0.1894 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.5656 |           0.2173 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.5555 |           0.2275 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.5384 |           0.2454 |   0.0000 |   0.0000 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.5063 |           0.2766 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.4391 |           0.3431 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2874 |           0.4954 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.2836 |           0.4990 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm_all |   p_bonferroni_all |   p_bh_all | sig_holm_all_5pct   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|-------------:|-------------------:|-----------:|:--------------------|
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7837 | 0.2836 |    0.4990 |     0.4439 |     0.5517 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7837 | 0.2874 |    0.4954 |     0.4301 |     0.5570 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7424 | 0.2836 |    0.4578 |     0.4065 |     0.5081 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7424 | 0.2874 |    0.4543 |     0.3898 |     0.5178 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.7322 | 0.2836 |    0.4475 |     0.3952 |     0.4989 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.7322 | 0.2874 |    0.4440 |     0.3754 |     0.5086 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.7175 | 0.2836 |    0.4331 |     0.3797 |     0.4853 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.7175 | 0.2874 |    0.4295 |     0.3606 |     0.4948 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.6700 | 0.2836 |    0.3855 |     0.3277 |     0.4420 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.6700 | 0.2874 |    0.3820 |     0.3113 |     0.4505 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.6603 | 0.2836 |    0.3751 |     0.3156 |     0.4303 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2874 | 0.6603 |   -0.3716 |    -0.4459 |    -0.2964 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.6457 | 0.2836 |    0.3617 |     0.3082 |     0.4148 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2874 | 0.6457 |   -0.3582 |    -0.4266 |    -0.2891 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.4391 | 0.7837 |   -0.3431 |    -0.4004 |    -0.2849 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.6220 | 0.2836 |    0.3377 |     0.2860 |     0.3904 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2874 | 0.6220 |   -0.3342 |    -0.3982 |    -0.2683 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.6147 | 0.2836 |    0.3303 |     0.2696 |     0.3882 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.6113 | 0.2836 |    0.3273 |     0.2766 |     0.3780 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2874 | 0.6147 |   -0.3267 |    -0.3986 |    -0.2532 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2874 | 0.6113 |   -0.3238 |    -0.3877 |    -0.2593 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.6009 | 0.2836 |    0.3166 |     0.2615 |     0.3714 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2874 | 0.6009 |   -0.3131 |    -0.3804 |    -0.2435 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.5942 | 0.2836 |    0.3096 |     0.2534 |     0.3633 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.5942 | 0.2874 |    0.3060 |     0.2369 |     0.3724 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7424 | 0.4391 |    0.3020 |     0.2468 |     0.3568 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.4391 | 0.7322 |   -0.2917 |    -0.3477 |    -0.2354 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.5656 | 0.2836 |    0.2817 |     0.2360 |     0.3279 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2874 | 0.5656 |   -0.2781 |    -0.3428 |    -0.2110 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.7175 | 0.4391 |    0.2772 |     0.2237 |     0.3307 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7837 | 0.5063 |    0.2766 |     0.2186 |     0.3351 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.2836 | 0.5555 |   -0.2715 |    -0.3078 |    -0.2349 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2874 | 0.5555 |   -0.2680 |    -0.3270 |    -0.2069 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.2836 | 0.5384 |   -0.2536 |    -0.3061 |    -0.2026 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2874 | 0.5384 |   -0.2501 |    -0.3186 |    -0.1791 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7837 | 0.5384 |    0.2454 |     0.1883 |     0.3012 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7424 | 0.5063 |    0.2355 |     0.1774 |     0.2950 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.4391 | 0.6700 |   -0.2297 |    -0.2775 |    -0.1811 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7837 | 0.5555 |    0.2275 |     0.1753 |     0.2796 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.7322 | 0.5063 |    0.2251 |     0.1668 |     0.2849 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.5063 | 0.2836 |    0.2224 |     0.1798 |     0.2638 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.4391 | 0.6603 |   -0.2193 |    -0.2776 |    -0.1586 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2874 | 0.5063 |   -0.2188 |    -0.2838 |    -0.1524 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7837 | 0.5656 |    0.2173 |     0.1631 |     0.2692 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.7175 | 0.5063 |    0.2107 |     0.1504 |     0.2712 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.4391 | 0.6457 |   -0.2059 |    -0.2691 |    -0.1423 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7424 | 0.5384 |    0.2042 |     0.1471 |     0.2616 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.7322 | 0.5384 |    0.1939 |     0.1350 |     0.2525 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.5942 | 0.7837 |   -0.1894 |    -0.2245 |    -0.1545 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7424 | 0.5555 |    0.1863 |     0.1359 |     0.2364 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7837 | 0.6009 |    0.1823 |     0.1202 |     0.2441 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.4391 | 0.6220 |   -0.1819 |    -0.2415 |    -0.1221 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.7175 | 0.5384 |    0.1794 |     0.1224 |     0.2361 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7424 | 0.5656 |    0.1762 |     0.1193 |     0.2300 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.7322 | 0.5555 |    0.1760 |     0.1237 |     0.2267 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.4391 | 0.6147 |   -0.1744 |    -0.2296 |    -0.1194 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7837 | 0.6113 |    0.1717 |     0.1109 |     0.2323 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.4391 | 0.6113 |   -0.1715 |    -0.2381 |    -0.1027 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7837 | 0.6147 |    0.1687 |     0.1278 |     0.2126 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.7322 | 0.5656 |    0.1658 |     0.1076 |     0.2208 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.6700 | 0.5063 |    0.1631 |     0.1029 |     0.2235 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.7175 | 0.5555 |    0.1615 |     0.1087 |     0.2119 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7837 | 0.6220 |    0.1613 |     0.1036 |     0.2163 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.4391 | 0.6009 |   -0.1608 |    -0.2278 |    -0.0924 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.4391 | 0.2836 |    0.1559 |     0.1013 |     0.2120 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.4391 | 0.5942 |   -0.1537 |    -0.2060 |    -0.1011 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.5063 | 0.6603 |   -0.1528 |    -0.2130 |    -0.0910 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.4391 | 0.2874 |    0.1523 |     0.0804 |     0.2217 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.7175 | 0.5656 |    0.1514 |     0.0960 |     0.2030 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7424 | 0.5942 |    0.1483 |     0.1148 |     0.1824 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7424 | 0.6009 |    0.1412 |     0.0788 |     0.2036 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.6457 | 0.5063 |    0.1394 |     0.0839 |     0.1964 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.5942 | 0.7322 |   -0.1379 |    -0.1735 |    -0.1037 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7837 | 0.6457 |    0.1372 |     0.0750 |     0.1978 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.6700 | 0.5384 |    0.1319 |     0.0727 |     0.1908 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.7322 | 0.6009 |    0.1309 |     0.0657 |     0.1950 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7424 | 0.6113 |    0.1305 |     0.0686 |     0.1930 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7424 | 0.6147 |    0.1276 |     0.0852 |     0.1697 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.4391 | 0.5656 |   -0.1258 |    -0.1857 |    -0.0662 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7837 | 0.6603 |    0.1239 |     0.0655 |     0.1834 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.7175 | 0.5942 |    0.1235 |     0.0911 |     0.1571 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.6603 | 0.5384 |    0.1215 |     0.0638 |     0.1799 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.7322 | 0.6113 |    0.1202 |     0.0571 |     0.1829 |    0.0004 | True             |       0.0300 |             0.0684 |     0.0007 | True                |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7424 | 0.6220 |    0.1201 |     0.0627 |     0.1755 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.7322 | 0.6147 |    0.1172 |     0.0745 |     0.1614 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.7175 | 0.6009 |    0.1164 |     0.0499 |     0.1809 |    0.0008 | True             |       0.0576 |             0.1368 |     0.0014 | False               |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.4391 | 0.5555 |   -0.1156 |    -0.1687 |    -0.0606 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.6220 | 0.5063 |    0.1154 |     0.0618 |     0.1699 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.6700 | 0.5555 |    0.1140 |     0.0606 |     0.1674 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.6700 | 0.7837 |   -0.1135 |    -0.1551 |    -0.0738 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.7322 | 0.6220 |    0.1098 |     0.0520 |     0.1660 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.6457 | 0.5384 |    0.1081 |     0.0464 |     0.1718 |    0.0010 | True             |       0.0700 |             0.1710 |     0.0017 | False               |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.6147 | 0.5063 |    0.1079 |     0.0444 |     0.1706 |    0.0008 | True             |       0.0576 |             0.1368 |     0.0014 | False               |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.7175 | 0.6113 |    0.1057 |     0.0457 |     0.1669 |    0.0012 | True             |       0.0828 |             0.2052 |     0.0020 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.6113 | 0.5063 |    0.1049 |     0.0527 |     0.1558 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.6700 | 0.5656 |    0.1038 |     0.0459 |     0.1578 |    0.0004 | True             |       0.0300 |             0.0684 |     0.0007 | True                |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.6603 | 0.5555 |    0.1036 |     0.0508 |     0.1546 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.7175 | 0.6147 |    0.1028 |     0.0628 |     0.1428 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.4391 | 0.5384 |   -0.0978 |    -0.1628 |    -0.0321 |    0.0052 | True             |       0.2964 |             0.8892 |     0.0077 | False               |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7424 | 0.6457 |    0.0961 |     0.0350 |     0.1566 |    0.0026 | True             |       0.1664 |             0.4446 |     0.0041 | False               |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.7175 | 0.6220 |    0.0953 |     0.0396 |     0.1505 |    0.0016 | True             |       0.1072 |             0.2736 |     0.0026 | False               |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.6009 | 0.5063 |    0.0943 |     0.0333 |     0.1544 |    0.0030 | True             |       0.1860 |             0.5130 |     0.0047 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.5656 | 0.6603 |   -0.0934 |    -0.1493 |    -0.0352 |    0.0012 | True             |       0.0828 |             0.2052 |     0.0020 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.6457 | 0.5555 |    0.0902 |     0.0413 |     0.1401 |    0.0006 | True             |       0.0438 |             0.1026 |     0.0010 | True                |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.5942 | 0.5063 |    0.0872 |     0.0259 |     0.1485 |    0.0038 | True             |       0.2318 |             0.6498 |     0.0059 | False               |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.7322 | 0.6457 |    0.0858 |     0.0260 |     0.1455 |    0.0056 | True             |       0.3136 |             0.9576 |     0.0083 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.6220 | 0.5384 |    0.0841 |     0.0289 |     0.1416 |    0.0044 | True             |       0.2640 |             0.7524 |     0.0067 | False               |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7424 | 0.6603 |    0.0827 |     0.0264 |     0.1409 |    0.0048 | True             |       0.2784 |             0.8208 |     0.0072 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.5656 | 0.6457 |   -0.0801 |    -0.1375 |    -0.0239 |    0.0046 | True             |       0.2714 |             0.7866 |     0.0070 | False               |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.6147 | 0.5384 |    0.0766 |     0.0123 |     0.1408 |    0.0202 | True             |       1.0000 |             1.0000 |     0.0283 | False               |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.5942 | 0.6700 |   -0.0759 |    -0.1094 |    -0.0409 |    0.0002 | True             |       0.0168 |             0.0342 |     0.0004 | True                |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.6113 | 0.5384 |    0.0737 |     0.0152 |     0.1330 |    0.0152 | True             |       0.8056 |             1.0000 |     0.0218 | False               |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.7322 | 0.6603 |    0.0724 |     0.0160 |     0.1303 |    0.0118 | True             |       0.6372 |             1.0000 |     0.0171 | False               |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7424 | 0.6700 |    0.0723 |     0.0389 |     0.1089 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.7175 | 0.6457 |    0.0713 |     0.0104 |     0.1320 |    0.0224 | True             |       1.0000 |             1.0000 |     0.0309 | False               |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.6700 | 0.6009 |    0.0689 |     0.0013 |     0.1371 |    0.0454 | True             |       1.0000 |             1.0000 |     0.0593 | False               |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.4391 | 0.5063 |   -0.0665 |    -0.1213 |    -0.0105 |    0.0206 | True             |       1.0000 |             1.0000 |     0.0286 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.6220 | 0.5555 |    0.0662 |     0.0194 |     0.1137 |    0.0074 | True             |       0.4070 |             1.0000 |     0.0108 | False               |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.7175 | 0.7837 |   -0.0659 |    -0.0984 |    -0.0347 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.5942 | 0.6603 |   -0.0656 |    -0.1214 |    -0.0081 |    0.0258 | True             |       1.0000 |             1.0000 |     0.0353 | False               |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.6009 | 0.5384 |    0.0630 |     0.0000 |     0.1264 |    0.0500 | True             |       1.0000 |             1.0000 |     0.0643 | False               |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.7322 | 0.6700 |    0.0620 |     0.0280 |     0.0985 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.5656 | 0.5063 |    0.0593 |     0.0069 |     0.1131 |    0.0260 | True             |       1.0000 |             1.0000 |     0.0353 | False               |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.6147 | 0.5555 |    0.0588 |     0.0017 |     0.1148 |    0.0440 | True             |       1.0000 |             1.0000 |     0.0579 | False               |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.6009 | 0.6603 |   -0.0585 |    -0.1272 |     0.0104 |    0.0964 | False            |       1.0000 |             1.0000 |     0.1202 | False               |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.6700 | 0.6113 |    0.0582 |    -0.0049 |     0.1201 |    0.0704 | False            |       1.0000 |             1.0000 |     0.0892 | False               |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.7175 | 0.6603 |    0.0579 |     0.0035 |     0.1146 |    0.0386 | True             |       1.0000 |             1.0000 |     0.0512 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.5656 | 0.6220 |   -0.0560 |    -0.1029 |    -0.0112 |    0.0154 | True             |       0.8056 |             1.0000 |     0.0219 | False               |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.5942 | 0.5384 |    0.0560 |    -0.0041 |     0.1145 |    0.0662 | False            |       1.0000 |             1.0000 |     0.0845 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.6113 | 0.5555 |    0.0558 |     0.0055 |     0.1084 |    0.0298 | True             |       1.0000 |             1.0000 |     0.0398 | False               |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.6700 | 0.6147 |    0.0553 |     0.0099 |     0.1006 |    0.0174 | True             |       0.8874 |             1.0000 |     0.0246 | False               |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.5942 | 0.6457 |   -0.0522 |    -0.1134 |     0.0079 |    0.0906 | False            |       1.0000 |             1.0000 |     0.1139 | False               |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.7322 | 0.7837 |   -0.0515 |    -0.0852 |    -0.0180 |    0.0024 | True             |       0.1560 |             0.4104 |     0.0038 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.5063 | 0.5555 |   -0.0491 |    -0.0941 |    -0.0051 |    0.0282 | True             |       1.0000 |             1.0000 |     0.0380 | False               |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.6147 | 0.5656 |    0.0486 |    -0.0119 |     0.1062 |    0.1092 | False            |       1.0000 |             1.0000 |     0.1343 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.6113 | 0.6603 |   -0.0478 |    -0.1139 |     0.0191 |    0.1628 | False            |       1.0000 |             1.0000 |     0.1933 | False               |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.6700 | 0.6220 |    0.0478 |    -0.0123 |     0.1071 |    0.1218 | False            |       1.0000 |             1.0000 |     0.1477 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.7175 | 0.6700 |    0.0475 |     0.0150 |     0.0830 |    0.0028 | True             |       0.1764 |             0.4788 |     0.0044 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.5656 | 0.6113 |   -0.0456 |    -0.1025 |     0.0117 |    0.1234 | False            |       1.0000 |             1.0000 |     0.1486 | False               |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.6009 | 0.5555 |    0.0451 |    -0.0078 |     0.0979 |    0.0970 | False            |       1.0000 |             1.0000 |     0.1202 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.6457 | 0.6009 |    0.0451 |    -0.0108 |     0.1016 |    0.1114 | False            |       1.0000 |             1.0000 |     0.1361 | False               |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.6147 | 0.6603 |   -0.0449 |    -0.1069 |     0.0189 |    0.1666 | False            |       1.0000 |             1.0000 |     0.1965 | False               |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7424 | 0.7837 |   -0.0412 |    -0.0700 |    -0.0134 |    0.0018 | True             |       0.1188 |             0.3078 |     0.0029 | False               |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.5942 | 0.5555 |    0.0381 |    -0.0120 |     0.0897 |    0.1378 | False            |       1.0000 |             1.0000 |     0.1648 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.6220 | 0.6603 |   -0.0374 |    -0.0955 |     0.0220 |    0.2194 | False            |       1.0000 |             1.0000 |     0.2570 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.5656 | 0.6009 |   -0.0350 |    -0.0992 |     0.0298 |    0.2842 | False            |       1.0000 |             1.0000 |     0.3218 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.6457 | 0.6113 |    0.0344 |    -0.0216 |     0.0915 |    0.2404 | False            |       1.0000 |             1.0000 |     0.2796 | False               |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.6147 | 0.6457 |   -0.0315 |    -0.0970 |     0.0326 |    0.3526 | False            |       1.0000 |             1.0000 |     0.3890 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.5063 | 0.5384 |   -0.0312 |    -0.0881 |     0.0231 |    0.2642 | False            |       1.0000 |             1.0000 |     0.3053 | False               |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.5942 | 0.6220 |   -0.0281 |    -0.0887 |     0.0302 |    0.3616 | False            |       1.0000 |             1.0000 |     0.3964 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.5656 | 0.5384 |    0.0281 |    -0.0235 |     0.0795 |    0.2746 | False            |       1.0000 |             1.0000 |     0.3130 | False               |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.5942 | 0.5656 |    0.0279 |    -0.0298 |     0.0832 |    0.3316 | False            |       1.0000 |             1.0000 |     0.3682 | False               |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7424 | 0.7175 |    0.0248 |     0.0005 |     0.0510 |    0.0458 | True             |       1.0000 |             1.0000 |     0.0593 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.6220 | 0.6457 |   -0.0240 |    -0.0701 |     0.0215 |    0.2954 | False            |       1.0000 |             1.0000 |     0.3323 | False               |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.6700 | 0.6457 |    0.0238 |    -0.0394 |     0.0868 |    0.4640 | False            |       1.0000 |             1.0000 |     0.5020 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.6220 | 0.6009 |    0.0211 |    -0.0417 |     0.0844 |    0.5204 | False            |       1.0000 |             1.0000 |     0.5562 | False               |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.5942 | 0.6147 |   -0.0207 |    -0.0609 |     0.0207 |    0.3154 | False            |       1.0000 |             1.0000 |     0.3525 | False               |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.5384 | 0.5555 |   -0.0179 |    -0.0671 |     0.0321 |    0.4668 | False            |       1.0000 |             1.0000 |     0.5020 | False               |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.5942 | 0.6113 |   -0.0177 |    -0.0808 |     0.0450 |    0.5852 | False            |       1.0000 |             1.0000 |     0.6215 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.7175 | 0.7322 |   -0.0145 |    -0.0408 |     0.0102 |    0.2708 | False            |       1.0000 |             1.0000 |     0.3108 | False               |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.6147 | 0.6009 |    0.0136 |    -0.0617 |     0.0867 |    0.7220 | False            |       1.0000 |             1.0000 |     0.7483 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.6457 | 0.6603 |   -0.0134 |    -0.0716 |     0.0473 |    0.6440 | False            |       1.0000 |             1.0000 |     0.6756 | False               |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.6009 | 0.6113 |   -0.0107 |    -0.0745 |     0.0525 |    0.7416 | False            |       1.0000 |             1.0000 |     0.7594 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.6220 | 0.6113 |    0.0104 |    -0.0395 |     0.0598 |    0.6898 | False            |       1.0000 |             1.0000 |     0.7192 | False               |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.6700 | 0.6603 |    0.0104 |    -0.0477 |     0.0694 |    0.7302 | False            |       1.0000 |             1.0000 |     0.7522 | False               |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7424 | 0.7322 |    0.0103 |    -0.0130 |     0.0338 |    0.3798 | False            |       1.0000 |             1.0000 |     0.4137 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.5656 | 0.5555 |    0.0102 |    -0.0303 |     0.0519 |    0.6290 | False            |       1.0000 |             1.0000 |     0.6639 | False               |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.6147 | 0.6220 |   -0.0075 |    -0.0717 |     0.0564 |    0.8352 | False            |       1.0000 |             1.0000 |     0.8451 | False               |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.5942 | 0.6009 |   -0.0071 |    -0.0729 |     0.0594 |    0.8306 | False            |       1.0000 |             1.0000 |     0.8451 | False               |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2874 | 0.2836 |    0.0036 |    -0.0511 |     0.0604 |    0.9084 | False            |       1.0000 |             1.0000 |     0.9137 | False               |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.6147 | 0.6113 |    0.0029 |    -0.0662 |     0.0701 |    0.9310 | False            |       1.0000 |             1.0000 |     0.9310 | False               |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 **macro** por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0); o micro está em `K_iou_sensitivity_wide_micro.csv`:

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.6544 | 0.6220 | 0.5862 |  0.5242 |
| BERTimbau-large      | 0.6757 | 0.6457 | 0.6059 |  0.5431 |
| BERTimbauLaw         | 0.5225 | 0.5063 | 0.4673 |  0.4188 |
| BiLSTM-CRF           | 0.6383 | 0.6009 | 0.5414 |  0.3786 |
| DeepSeek-V4-Flash    | 0.8246 | 0.7837 | 0.7449 |  0.3753 |
| GPT-4.1              | 0.7891 | 0.7424 | 0.6863 |  0.2992 |
| GPT-4.1-mini         | 0.7563 | 0.7175 | 0.6639 |  0.3086 |
| GPT-4.1-nano         | 0.4939 | 0.4391 | 0.3804 |  0.1158 |
| GPT-5-mini           | 0.6173 | 0.5942 | 0.5645 |  0.1525 |
| GPT-5.1              | 0.7631 | 0.7322 | 0.6782 |  0.3160 |
| GPT-5.2              | 0.7054 | 0.6700 | 0.6169 |  0.2409 |
| GovBERT-BR           | 0.5626 | 0.5555 | 0.5155 |  0.4635 |
| JurisBERT            | 0.6482 | 0.6113 | 0.5657 |  0.4932 |
| Legal-BERT-STF       | 0.5671 | 0.5384 | 0.5233 |  0.4715 |
| Legal-BERTimbau-base | 0.5822 | 0.5656 | 0.5349 |  0.4569 |
| LegalBERTPT-br       | 0.2919 | 0.2836 | 0.2763 |  0.2680 |
| LegalBert-pt         | 0.6999 | 0.6603 | 0.6319 |  0.5734 |
| Llama-3.3-70B        | 0.3067 | 0.2874 | 0.2564 |  0.0705 |
| Qwen2.5-72B          | 0.6528 | 0.6147 | 0.5731 |  0.2803 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5, no macro e no micro):

| iou_threshold   |   spearman_macro_vs_0.5 |   spearman_micro_vs_0.5 |
|:----------------|------------------------:|------------------------:|
| 0.3             |                  0.9982 |                  0.9509 |
| 0.5             |                  1.0000 |                  1.0000 |
| 0.7             |                  0.9930 |                  0.9860 |
| exact           |                  0.2123 |                  0.4439 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_macro_full |   span_f1_macro_informative |   delta_span_f1_macro |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------------:|----------------------------:|----------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  231 |               0.7837 |                      0.8518 |                0.0681 |         0.8109 |                0.8585 |          0.0476 |                0.7787 |                       0.8715 |                 0.0928 |             0.8458 |                    0.8458 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  231 |               0.7424 |                      0.8337 |                0.0914 |         0.7645 |                0.8290 |          0.0645 |                0.6827 |                       0.7930 |                 0.1103 |             0.8685 |                    0.8685 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  231 |               0.7322 |                      0.8247 |                0.0925 |         0.7458 |                0.8181 |          0.0723 |                0.6574 |                       0.7787 |                 0.1212 |             0.8617 |                    0.8617 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  231 |               0.7175 |                      0.8093 |                0.0918 |         0.7343 |                0.8137 |          0.0795 |                0.6266 |                       0.7519 |                 0.1253 |             0.8866 |                    0.8866 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  231 |               0.6700 |                      0.7701 |                0.1000 |         0.6760 |                0.7624 |          0.0863 |                0.5516 |                       0.6766 |                 0.1250 |             0.8730 |                    0.8730 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  231 |               0.5942 |                      0.7239 |                0.1297 |         0.4595 |                0.6700 |          0.2105 |                0.3069 |                       0.5289 |                 0.2219 |             0.9138 |                    0.9138 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  231 |               0.6147 |                      0.6800 |                0.0653 |         0.6595 |                0.7232 |          0.0637 |                0.5800 |                       0.6864 |                 0.1063 |             0.7642 |                    0.7642 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  231 |               0.6603 |                      0.6691 |                0.0088 |         0.7391 |                0.7477 |          0.0086 |                0.8475 |                       0.8705 |                 0.0230 |             0.6553 |                    0.6553 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  231 |               0.6457 |                      0.6681 |                0.0224 |         0.7248 |                0.7419 |          0.0171 |                0.7786 |                       0.8192 |                 0.0405 |             0.6780 |                    0.6780 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  231 |               0.6220 |                      0.6389 |                0.0170 |         0.7217 |                0.7380 |          0.0164 |                0.7898 |                       0.8300 |                 0.0403 |             0.6644 |                    0.6644 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  231 |               0.6009 |                      0.6330 |                0.0321 |         0.6735 |                0.6977 |          0.0242 |                0.7774 |                       0.8452 |                 0.0677 |             0.5941 |                    0.5941 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  231 |               0.6113 |                      0.6326 |                0.0213 |         0.6767 |                0.6933 |          0.0166 |                0.7599 |                       0.8030 |                 0.0431 |             0.6100 |                    0.6100 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  231 |               0.5656 |                      0.5715 |                0.0059 |         0.7018 |                0.7091 |          0.0073 |                0.8101 |                       0.8298 |                 0.0197 |             0.6190 |                    0.6190 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  231 |               0.5555 |                      0.5598 |                0.0043 |         0.7044 |                0.7083 |          0.0039 |                0.9011 |                       0.9140 |                 0.0129 |             0.5782 |                    0.5782 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  231 |               0.5384 |                      0.5423 |                0.0038 |         0.6773 |                0.6827 |          0.0054 |                0.8173 |                       0.8333 |                 0.0160 |             0.5782 |                    0.5782 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  231 |               0.5063 |                      0.5085 |                0.0021 |         0.6866 |                0.6903 |          0.0037 |                0.8547 |                       0.8664 |                 0.0117 |             0.5737 |                    0.5737 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |           861 |                  231 |               0.4391 |                      0.4755 |                0.0363 |         0.4640 |                0.5202 |          0.0562 |                0.3788 |                       0.4599 |                 0.0812 |             0.5986 |                    0.5986 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |           861 |                  231 |               0.2874 |                      0.3049 |                0.0175 |         0.3590 |                0.3702 |          0.0113 |                0.6120 |                       0.6829 |                 0.0709 |             0.2540 |                    0.2540 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  231 |               0.2836 |                      0.2850 |                0.0014 |         0.5008 |                0.5032 |          0.0024 |                0.8196 |                       0.8325 |                 0.0129 |             0.3605 |                    0.3605 |

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
