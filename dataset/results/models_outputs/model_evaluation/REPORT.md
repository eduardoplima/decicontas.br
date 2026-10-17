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

| metric              |   before |   after |   delta |
|:--------------------|---------:|--------:|--------:|
| total_docs          |      861 |     861 |       0 |
| docs_with_entity    |      196 |     202 |       6 |
| docs_without_entity |      665 |     659 |      -6 |
| total_entities      |      404 |     411 |       7 |
| MULTA               |      202 |     203 |       1 |
| OBRIGACAO           |      119 |     123 |       4 |
| RECOMENDACAO        |       21 |      22 |       1 |
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
| RECOMENDACAO  |       21 |      22 |       1 |
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
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |     0.8690 |           0.8304 |            0.8699 |         0.8681 |    0.8249 |          0.7985 |           0.8132 |        0.8370 |
| gpt-4.1_few_shot                                       | GPT-4.1              |     0.8411 |           0.8115 |            0.8100 |         0.8747 |    0.7716 |          0.7495 |           0.7004 |        0.8589 |
| gpt-5.1_few_shot                                       | GPT-5.1              |     0.8159 |           0.7937 |            0.7709 |         0.8666 |    0.7524 |          0.7481 |           0.6724 |        0.8540 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.7959 |           0.6287 |            0.9599 |         0.6798 |    0.7513 |          0.6133 |           0.8232 |        0.6910 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.8130 |           0.6271 |            0.8914 |         0.7472 |    0.7433 |          0.5673 |           0.8249 |        0.6764 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |     0.8249 |           0.7857 |            0.7726 |         0.8848 |    0.7403 |          0.7185 |           0.6384 |        0.8808 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.7968 |           0.6333 |            0.9600 |         0.6811 |    0.7348 |          0.6047 |           0.7845 |        0.6910 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.7498 |           0.5341 |            0.9625 |         0.6142 |    0.7280 |          0.5236 |           0.8529 |        0.6350 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.7749 |           0.5731 |            0.9634 |         0.6481 |    0.7275 |          0.5516 |           0.8114 |        0.6594 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.7610 |           0.5485 |            0.9588 |         0.6309 |    0.7255 |          0.5270 |           0.8376 |        0.6399 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.7482 |           0.5522 |            0.9495 |         0.6174 |    0.7106 |          0.5386 |           0.7952 |        0.6423 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.7467 |           0.5476 |            0.9543 |         0.6133 |    0.7099 |          0.5315 |           0.7970 |        0.6399 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.7503 |           0.5452 |            0.9560 |         0.6174 |    0.7094 |          0.5301 |           0.8075 |        0.6326 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.7341 |           0.5242 |            0.9681 |         0.5913 |    0.6904 |          0.5176 |           0.7900 |        0.6131 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.7905 |           0.7859 |            0.7193 |         0.8773 |    0.6780 |          0.6917 |           0.5550 |        0.8710 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7491 |           0.6912 |            0.7248 |         0.7751 |    0.6722 |          0.6055 |           0.5859 |        0.7883 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.6225 |           0.5431 |            0.5939 |         0.6540 |    0.4805 |          0.4354 |           0.3883 |        0.6302 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.6007 |           0.6704 |            0.4446 |         0.9255 |    0.4499 |          0.5832 |           0.2986 |        0.9124 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4160 |           0.2819 |            0.7861 |         0.2828 |    0.3579 |          0.2504 |           0.6415 |        0.2482 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                                  | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                                        |
|:-------------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:--------------------------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                                 | BiLSTM-CRF           |         0.7226 |        0.1332 |        0.5057 |        0.8265 | 0.5057; 0.8265; 0.6851; 0.8130; 0.7826 |          0.7905 |         0.1219 |         0.5760 |         0.8711 | 0.5760; 0.8711; 0.8093; 0.8494; 0.8466 | {"hidden_dim": 128, "dropout": 0.5, "lr": 0.003, "max_len": 1100}                                             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |         0.7206 |        0.0836 |        0.5870 |        0.8148 | 0.5870; 0.7551; 0.7200; 0.8148; 0.7260 |          0.7335 |         0.0923 |         0.5843 |         0.8360 | 0.5843; 0.8360; 0.7296; 0.7544; 0.7631 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 3e-05, "warmup_ratio": 0.1, "stride": 320}      |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |         0.7398 |        0.0479 |        0.6702 |        0.7867 | 0.7188; 0.7426; 0.6702; 0.7810; 0.7867 |          0.7935 |         0.0574 |         0.7288 |         0.8562 | 0.8271; 0.8562; 0.7364; 0.7288; 0.8191 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 3e-05, "warmup_ratio": 0.1, "stride": 320}     |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |         0.7067 |        0.0900 |        0.5918 |        0.8182 | 0.5918; 0.7653; 0.6489; 0.8182; 0.7092 |          0.7371 |         0.0842 |         0.6145 |         0.8414 | 0.6145; 0.8414; 0.7226; 0.7825; 0.7244 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}              |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |         0.7106 |        0.0833 |        0.6168 |        0.7863 | 0.6168; 0.7411; 0.6264; 0.7863; 0.7826 |          0.7379 |         0.0701 |         0.6472 |         0.8192 | 0.6472; 0.8192; 0.6848; 0.7735; 0.7647 | {"model_name": "alfaneo/jurisbert-base-portuguese-uncased", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}  |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |         0.7292 |        0.0646 |        0.6857 |        0.8393 | 0.6857; 0.7347; 0.6885; 0.8393; 0.6977 |          0.7551 |         0.0631 |         0.6664 |         0.8172 | 0.7295; 0.8172; 0.7482; 0.8141; 0.6664 | {"model_name": "alfaneo/bertimbaulaw-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320} |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |         0.7520 |        0.0626 |        0.6786 |        0.8448 | 0.6786; 0.7633; 0.7135; 0.8448; 0.7600 |          0.7913 |         0.0540 |         0.7248 |         0.8683 | 0.7647; 0.8683; 0.7248; 0.8149; 0.7837 | {"model_name": "raquelsilveira/legalbertpt_fp", "lr": 5e-05, "warmup_ratio": 0.1, "stride": 320}              |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |         0.6935 |        0.0826 |        0.5902 |        0.8214 | 0.6833; 0.6915; 0.6809; 0.8214; 0.5902 |          0.7305 |         0.0802 |         0.5873 |         0.7757 | 0.7757; 0.7588; 0.7638; 0.7665; 0.5873 | {"model_name": "ulysses-camara/legal-bert-pt-br", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |         0.7256 |        0.0727 |        0.6435 |        0.7965 | 0.6435; 0.7900; 0.6554; 0.7965; 0.7429 |          0.7640 |         0.0727 |         0.6967 |         0.8819 | 0.6967; 0.8819; 0.7119; 0.7674; 0.7619 | {"model_name": "dominguesm/legal-bert-base-cased-ptbr", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}      |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |         0.7183 |        0.0793 |        0.6250 |        0.8393 | 0.6780; 0.7182; 0.6250; 0.8393; 0.7308 |          0.7502 |         0.0429 |         0.6747 |         0.7825 | 0.7674; 0.7626; 0.6747; 0.7640; 0.7825 | {"model_name": "dccmpmgfinalisticas/GovBERT-BR", "lr": 5e-05, "warmup_ratio": 0.0, "stride": 320}             |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.7255 |                0.1495 |                0.4160 |                0.8690 |                0.6364 |               0.1650 |               0.3579 |               0.8249 |
| supervised         |                 0.7671 |                0.0266 |                0.7341 |                0.8130 |                0.7231 |               0.0182 |               0.6904 |               0.7513 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.8184 |      0.7236 |         0.0000 |          0.5524 |
| BERTimbau-large      |  0.7873 |      0.7393 |         0.2308 |          0.6614 |
| BERTimbauLaw         |  0.8083 |      0.7308 |         0.0000 |          0.5688 |
| BiLSTM-CRF           |  0.8394 |      0.7091 |         0.0714 |          0.6491 |
| DeepSeek-V4-Flash    |  0.8916 |      0.7398 |         0.7692 |          0.7934 |
| GPT-4.1              |  0.8546 |      0.6547 |         0.7368 |          0.7519 |
| GPT-4.1-mini         |  0.8497 |      0.5964 |         0.6780 |          0.7500 |
| GPT-4.1-nano         |  0.7136 |      0.3008 |         0.1185 |          0.6087 |
| GPT-5-mini           |  0.7932 |      0.2378 |         0.5833 |          0.7183 |
| GPT-5.1              |  0.8481 |      0.6053 |         0.7778 |          0.7612 |
| GPT-5.2              |  0.8059 |      0.5105 |         0.7925 |          0.6577 |
| GovBERT-BR           |  0.7600 |      0.7000 |         0.0000 |          0.6942 |
| JurisBERT            |  0.7857 |      0.6570 |         0.0000 |          0.6833 |
| Legal-BERT-STF       |  0.8010 |      0.7343 |         0.0870 |          0.5841 |
| Legal-BERTimbau-base |  0.7581 |      0.7374 |         0.0000 |          0.6250 |
| LegalBERTPT-br       |  0.7588 |      0.7150 |         0.0870 |          0.5098 |
| LegalBert-pt         |  0.7938 |      0.7373 |         0.1600 |          0.7619 |
| Llama-3.3-70B        |  0.4286 |      0.3939 |         0.1481 |          0.0308 |
| Qwen2.5-72B          |  0.8287 |      0.5411 |         0.3462 |          0.7059 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                                  | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:-------------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4.1_few_shot                                       | GPT-4.1              | MULTA         |      0.7828 |   0.9409 | 0.8546 |       191 |          203 |          244 |
| gpt-4.1_few_shot                                       | GPT-4.1              | OBRIGACAO     |      0.5871 |   0.7398 | 0.6547 |        91 |          123 |          155 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RECOMENDACAO  |      0.6000 |   0.9545 | 0.7368 |        21 |           22 |           35 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RESSARCIMENTO |      0.7143 |   0.7937 | 0.7519 |        50 |           63 |           70 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | MULTA         |      0.7617 |   0.9606 | 0.8497 |       195 |          203 |          256 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | OBRIGACAO     |      0.4737 |   0.8049 | 0.5964 |        99 |          123 |          209 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RECOMENDACAO  |      0.5405 |   0.9091 | 0.6780 |        20 |           22 |           37 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RESSARCIMENTO |      0.7385 |   0.7619 | 0.7500 |        48 |           63 |           65 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | MULTA         |      0.6816 |   0.7488 | 0.7136 |       152 |          203 |          223 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | OBRIGACAO     |      0.2227 |   0.4634 | 0.3008 |        57 |          123 |          256 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RECOMENDACAO  |      0.0708 |   0.3636 | 0.1185 |         8 |           22 |          113 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RESSARCIMENTO |      0.5600 |   0.6667 | 0.6087 |        42 |           63 |           75 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | MULTA         |      0.6992 |   0.9163 | 0.7932 |       186 |          203 |          266 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | OBRIGACAO     |      0.1359 |   0.9512 | 0.2378 |       117 |          123 |          861 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RECOMENDACAO  |      0.4200 |   0.9545 | 0.5833 |        21 |           22 |           50 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RESSARCIMENTO |      0.6456 |   0.8095 | 0.7183 |        51 |           63 |           79 |
| gpt-5.1_few_shot                                       | GPT-5.1              | MULTA         |      0.7857 |   0.9212 | 0.8481 |       187 |          203 |          238 |
| gpt-5.1_few_shot                                       | GPT-5.1              | OBRIGACAO     |      0.5083 |   0.7480 | 0.6053 |        92 |          123 |          181 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RECOMENDACAO  |      0.6562 |   0.9545 | 0.7778 |        21 |           22 |           32 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RESSARCIMENTO |      0.7183 |   0.8095 | 0.7612 |        51 |           63 |           71 |
| gpt-5.2_few_shot                                       | GPT-5.2              | MULTA         |      0.7048 |   0.9409 | 0.8059 |       191 |          203 |          271 |
| gpt-5.2_few_shot                                       | GPT-5.2              | OBRIGACAO     |      0.3774 |   0.7886 | 0.5105 |        97 |          123 |          257 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RECOMENDACAO  |      0.6774 |   0.9545 | 0.7925 |        21 |           22 |           31 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RESSARCIMENTO |      0.5698 |   0.7778 | 0.6577 |        49 |           63 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | MULTA         |      0.8726 |   0.9113 | 0.8916 |       185 |          203 |          212 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | OBRIGACAO     |      0.7398 |   0.7398 | 0.7398 |        91 |          123 |          123 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RECOMENDACAO  |      0.6667 |   0.9091 | 0.7692 |        20 |           22 |           30 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RESSARCIMENTO |      0.8276 |   0.7619 | 0.7934 |        48 |           63 |           58 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | MULTA         |      0.7792 |   0.2956 | 0.4286 |        60 |          203 |           77 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | OBRIGACAO     |      0.5200 |   0.3171 | 0.3939 |        39 |          123 |           75 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RECOMENDACAO  |      0.4000 |   0.0909 | 0.1481 |         2 |           22 |            5 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RESSARCIMENTO |      0.5000 |   0.0159 | 0.0308 |         1 |           63 |            2 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | MULTA         |      0.7817 |   0.8818 | 0.8287 |       179 |          203 |          229 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | OBRIGACAO     |      0.4675 |   0.6423 | 0.5411 |        79 |          123 |          169 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RECOMENDACAO  |      0.2195 |   0.8182 | 0.3462 |        18 |           22 |           82 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RESSARCIMENTO |      0.6575 |   0.7619 | 0.7059 |        48 |           63 |           73 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | MULTA         |      0.7677 |   0.7488 | 0.7581 |       152 |          203 |          198 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | OBRIGACAO     |      0.9733 |   0.5935 | 0.7374 |        73 |          123 |           75 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           22 |            0 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RESSARCIMENTO |      0.7143 |   0.5556 | 0.6250 |        35 |           63 |           49 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | MULTA         |      0.8511 |   0.7882 | 0.8184 |       160 |          203 |          188 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | OBRIGACAO     |      0.9474 |   0.5854 | 0.7236 |        72 |          123 |           76 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           22 |            0 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RESSARCIMENTO |      0.6905 |   0.4603 | 0.5524 |        29 |           63 |           42 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | MULTA         |      0.7816 |   0.7931 | 0.7873 |       161 |          203 |          206 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | OBRIGACAO     |      0.8864 |   0.6341 | 0.7393 |        78 |          123 |           88 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RECOMENDACAO  |      0.7500 |   0.1364 | 0.2308 |         3 |           22 |            4 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RESSARCIMENTO |      0.6562 |   0.6667 | 0.6614 |        42 |           63 |           64 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | MULTA         |      0.8852 |   0.7980 | 0.8394 |       162 |          203 |          183 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | OBRIGACAO     |      0.8041 |   0.6341 | 0.7091 |        78 |          123 |           97 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RECOMENDACAO  |      0.1667 |   0.0455 | 0.0714 |         1 |           22 |            6 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RESSARCIMENTO |      0.7255 |   0.5873 | 0.6491 |        37 |           63 |           51 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | MULTA         |      0.8148 |   0.7586 | 0.7857 |       154 |          203 |          189 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | OBRIGACAO     |      0.8095 |   0.5528 | 0.6570 |        68 |          123 |           84 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           22 |            0 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RESSARCIMENTO |      0.7193 |   0.6508 | 0.6833 |        41 |           63 |           57 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | MULTA         |      0.8525 |   0.7685 | 0.8083 |       156 |          203 |          183 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | OBRIGACAO     |      0.8941 |   0.6179 | 0.7308 |        76 |          123 |           85 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           22 |            0 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RESSARCIMENTO |      0.6739 |   0.4921 | 0.5688 |        31 |           63 |           46 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | MULTA         |      0.8324 |   0.7586 | 0.7938 |       154 |          203 |          185 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | OBRIGACAO     |      0.8511 |   0.6504 | 0.7373 |        80 |          123 |           94 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RECOMENDACAO  |      0.6667 |   0.0909 | 0.1600 |         2 |           22 |            3 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RESSARCIMENTO |      0.7619 |   0.7619 | 0.7619 |        48 |           63 |           63 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | MULTA         |      0.7744 |   0.7438 | 0.7588 |       151 |          203 |          195 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | OBRIGACAO     |      0.8810 |   0.6016 | 0.7150 |        74 |          123 |           84 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RECOMENDACAO  |      1.0000 |   0.0455 | 0.0870 |         1 |           22 |            1 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RESSARCIMENTO |      0.6667 |   0.4127 | 0.5098 |        26 |           63 |           39 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | MULTA         |      0.8090 |   0.7931 | 0.8010 |       161 |          203 |          199 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | OBRIGACAO     |      0.9048 |   0.6179 | 0.7343 |        76 |          123 |           84 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RECOMENDACAO  |      1.0000 |   0.0455 | 0.0870 |         1 |           22 |            1 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RESSARCIMENTO |      0.6600 |   0.5238 | 0.5841 |        33 |           63 |           50 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | MULTA         |      0.7716 |   0.7488 | 0.7600 |       152 |          203 |          197 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | OBRIGACAO     |      0.9091 |   0.5691 | 0.7000 |        70 |          123 |           77 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           22 |            0 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RESSARCIMENTO |      0.7241 |   0.6667 | 0.6942 |        42 |           63 |           58 |

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
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            16.2045 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            16.4626 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            48.2627 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            10.2304 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            13.8877 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            16.4122 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            16.1697 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            17.3709 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            14.3255 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | supervised |      861 |             nan      |             nan      |                 nan      |               nan      |             nan      |              nan      |              nan      |                nan      |               nan      |              nan      |             nan      | nan          |                            16.1726 |

## F. Function calling vs JSON schema

**Métricas overall:**

| model             | method           |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:-----------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | function_calling |     0.8741 |    0.8307 |          0.8031 |           0.8199 |        0.8418 |
| deepseek-v4-flash | json_schema      |     0.8645 |    0.8196 |          0.7911 |           0.8052 |        0.8345 |
| gpt-4.1           | function_calling |     0.8403 |    0.7846 |          0.7629 |           0.7154 |        0.8686 |
| gpt-4.1           | json_schema      |     0.8528 |    0.7818 |          0.7616 |           0.7175 |        0.8589 |

**Δ por modelo (FC − JS):**

| model             |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:------------------|-----------------:|----------------:|-----------------------:|--------------------:|
| deepseek-v4-flash |           0.0095 |          0.0111 |                 0.0147 |              0.0073 |
| gpt-4.1           |          -0.0125 |          0.0028 |                -0.0020 |              0.0097 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9029 |      0.7368 |         0.7692 |          0.8033 |
| deepseek-v4-flash | json_schema      |  0.8937 |      0.7309 |         0.7692 |          0.7705 |
| gpt-4.1           | function_calling |  0.8655 |      0.6764 |         0.7636 |          0.7463 |
| gpt-4.1           | json_schema      |  0.8591 |      0.6716 |         0.7636 |          0.7519 |

**Span Precision (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8900 |      0.7339 |         0.6667 |          0.8305 |
| deepseek-v4-flash | json_schema      |  0.8768 |      0.7222 |         0.6667 |          0.7966 |
| gpt-4.1           | function_calling |  0.7942 |      0.6118 |         0.6364 |          0.7042 |
| gpt-4.1           | json_schema      |  0.7869 |      0.6207 |         0.6364 |          0.7143 |

**Span Recall (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.9163 |      0.7398 |         0.9091 |          0.7778 |
| deepseek-v4-flash | json_schema      |  0.9113 |      0.7398 |         0.9091 |          0.7460 |
| gpt-4.1           | function_calling |  0.9507 |      0.7561 |         0.9545 |          0.7937 |
| gpt-4.1           | json_schema      |  0.9458 |      0.7317 |         0.9545 |          0.7937 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model             | technique   |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | cot         |     0.8591 |    0.7773 |          0.7013 |           0.7050 |        0.8662 |
| deepseek-v4-flash | few_shot    |     0.8690 |    0.8249 |          0.7985 |           0.8132 |        0.8370 |
| deepseek-v4-flash | two_stage   |     0.8718 |    0.8268 |          0.7953 |           0.8122 |        0.8418 |
| gpt-4.1           | cot         |     0.8365 |    0.7748 |          0.7586 |           0.7008 |        0.8662 |
| gpt-4.1           | few_shot    |     0.8411 |    0.7716 |          0.7495 |           0.7004 |        0.8589 |
| gpt-4.1           | two_stage   |     0.8434 |    0.7833 |          0.7611 |           0.7149 |        0.8662 |
| gpt-5.2           | cot         |     0.8219 |    0.7237 |          0.7504 |           0.6073 |        0.8954 |
| gpt-5.2           | few_shot    |     0.7905 |    0.6780 |          0.6917 |           0.5550 |        0.8710 |
| gpt-5.2           | two_stage   |     0.8236 |    0.7375 |          0.7422 |           0.6356 |        0.8783 |
| llama-3.3-70b     | cot         |     0.3133 |    0.2685 |          0.1606 |           0.6699 |        0.1679 |
| llama-3.3-70b     | few_shot    |     0.4160 |    0.3579 |          0.2504 |           0.6415 |        0.2482 |
| llama-3.3-70b     | two_stage   |     0.1724 |    0.1370 |          0.1400 |           0.5714 |        0.0779 |
| qwen2.5-72b       | cot         |     0.7855 |    0.6953 |          0.6222 |           0.5996 |        0.8273 |
| qwen2.5-72b       | few_shot    |     0.7491 |    0.6722 |          0.6055 |           0.5859 |        0.7883 |
| qwen2.5-72b       | two_stage   |     0.7721 |    0.6928 |          0.6244 |           0.6135 |        0.7956 |

**Span F1 pivotado (modelo × técnica):**

| model             |    cot |   few_shot |   two_stage |
|:------------------|-------:|-----------:|------------:|
| deepseek-v4-flash | 0.7773 |     0.8249 |      0.8268 |
| gpt-4.1           | 0.7748 |     0.7716 |      0.7833 |
| gpt-5.2           | 0.7237 |     0.6780 |      0.7375 |
| llama-3.3-70b     | 0.2685 |     0.3579 |      0.1370 |
| qwen2.5-72b       | 0.6953 |     0.6722 |      0.6928 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique   | token_f1           | token_f1.1          | token_f1.2          | token_f1.3         | span_f1            | span_f1.1           | span_f1.2           | span_f1.3          |
|:------------|:-------------------|:--------------------|:--------------------|:-------------------|:-------------------|:--------------------|:--------------------|:-------------------|
| nan         | mean               | std                 | min                 | max                | mean               | std                 | min                 | max                |
| cot         | 0.7232633980765509 | 0.23074995242380403 | 0.31326453905555934 | 0.8590534979423868 | 0.6479047814692936 | 0.21493252277213445 | 0.26848249027237353 | 0.777292576419214  |
| few_shot    | 0.7331195118555237 | 0.18320491499784647 | 0.4159537068724139  | 0.8690055260316317 | 0.6609297914824144 | 0.1812412367671276  | 0.3578947368421052  | 0.8249400479616307 |
| two_stage   | 0.6966595317361374 | 0.2953270998844574  | 0.17238893736484692 | 0.8718405806328389 | 0.6354738767737399 | 0.2830907070188033  | 0.13704496788008566 | 0.8267622461170848 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9095 |      0.7132 |         0.4118 |          0.7705 |
| deepseek-v4-flash | few_shot    |  0.8916 |      0.7398 |         0.7692 |          0.7934 |
| deepseek-v4-flash | two_stage   |  0.8916 |      0.7667 |         0.7692 |          0.7538 |
| gpt-4.1           | cot         |  0.8604 |      0.6528 |         0.7636 |          0.7576 |
| gpt-4.1           | few_shot    |  0.8546 |      0.6547 |         0.7368 |          0.7519 |
| gpt-4.1           | two_stage   |  0.8629 |      0.6739 |         0.7500 |          0.7576 |
| gpt-5.2           | cot         |  0.8578 |      0.5233 |         0.7925 |          0.8281 |
| gpt-5.2           | few_shot    |  0.8059 |      0.5105 |         0.7925 |          0.6577 |
| gpt-5.2           | two_stage   |  0.8470 |      0.5757 |         0.7925 |          0.7536 |
| llama-3.3-70b     | cot         |  0.3454 |      0.2971 |         0.0000 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.4286 |      0.3939 |         0.1481 |          0.0308 |
| llama-3.3-70b     | two_stage   |  0.1478 |      0.1507 |         0.2308 |          0.0308 |
| qwen2.5-72b       | cot         |  0.8519 |      0.5753 |         0.3564 |          0.7050 |
| qwen2.5-72b       | few_shot    |  0.8287 |      0.5411 |         0.3462 |          0.7059 |
| qwen2.5-72b       | two_stage   |  0.8392 |      0.5744 |         0.4270 |          0.6569 |

**Span Precision por entidade (mesmo eixo):**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.8802 |      0.6510 |         0.2625 |          0.7966 |
| deepseek-v4-flash | few_shot    |  0.8726 |      0.7398 |         0.6667 |          0.8276 |
| deepseek-v4-flash | two_stage   |  0.8726 |      0.7863 |         0.6667 |          0.7313 |
| gpt-4.1           | cot         |  0.7925 |      0.5697 |         0.6364 |          0.7246 |
| gpt-4.1           | few_shot    |  0.7828 |      0.5871 |         0.6000 |          0.7143 |
| gpt-4.1           | two_stage   |  0.7934 |      0.6078 |         0.6176 |          0.7246 |
| gpt-5.2           | cot         |  0.7814 |      0.3840 |         0.6774 |          0.8154 |
| gpt-5.2           | few_shot    |  0.7048 |      0.3774 |         0.6774 |          0.5698 |
| gpt-5.2           | two_stage   |  0.7702 |      0.4533 |         0.6774 |          0.6933 |
| llama-3.3-70b     | cot         |  0.9348 |      0.5000 |         0.0000 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.7792 |      0.5200 |         0.4000 |          0.5000 |
| llama-3.3-70b     | two_stage   |  0.6296 |      0.4783 |         0.7500 |          0.5000 |
| qwen2.5-72b       | cot         |  0.7924 |      0.4886 |         0.2278 |          0.6447 |
| qwen2.5-72b       | few_shot    |  0.7817 |      0.4675 |         0.2195 |          0.6575 |
| qwen2.5-72b       | two_stage   |  0.7965 |      0.5000 |         0.2836 |          0.6081 |

**Span Recall por entidade:**

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.9409 |      0.7886 |         0.9545 |          0.7460 |
| deepseek-v4-flash | few_shot    |  0.9113 |      0.7398 |         0.9091 |          0.7619 |
| deepseek-v4-flash | two_stage   |  0.9113 |      0.7480 |         0.9091 |          0.7778 |
| gpt-4.1           | cot         |  0.9409 |      0.7642 |         0.9545 |          0.7937 |
| gpt-4.1           | few_shot    |  0.9409 |      0.7398 |         0.9545 |          0.7937 |
| gpt-4.1           | two_stage   |  0.9458 |      0.7561 |         0.9545 |          0.7937 |
| gpt-5.2           | cot         |  0.9507 |      0.8211 |         0.9545 |          0.8413 |
| gpt-5.2           | few_shot    |  0.9409 |      0.7886 |         0.9545 |          0.7778 |
| gpt-5.2           | two_stage   |  0.9409 |      0.7886 |         0.9545 |          0.8254 |
| llama-3.3-70b     | cot         |  0.2118 |      0.2114 |         0.0000 |          0.0000 |
| llama-3.3-70b     | few_shot    |  0.2956 |      0.3171 |         0.0909 |          0.0159 |
| llama-3.3-70b     | two_stage   |  0.0837 |      0.0894 |         0.1364 |          0.0159 |
| qwen2.5-72b       | cot         |  0.9212 |      0.6992 |         0.8182 |          0.7778 |
| qwen2.5-72b       | few_shot    |  0.8818 |      0.6423 |         0.8182 |          0.7619 |
| qwen2.5-72b       | two_stage   |  0.8867 |      0.6748 |         0.8636 |          0.7143 |

## I. Análise de erros do melhor modelo

**Melhor modelo identificado por span F1: DeepSeek-V4-Flash.**

**Contagens por tipo de erro:**

| kind       |   count |
|:-----------|--------:|
| match      |     344 |
| boundary   |      38 |
| FN_no_pred |      37 |
| FP         |      37 |
| FN_overlap |      30 |
| type_error |       4 |

**Matriz rótulo × tipo de erro:**

| label         |   FN_no_pred |   FN_overlap |   FP |   boundary |   match |   type_error |
|:--------------|-------------:|-------------:|-----:|-----------:|--------:|-------------:|
| MULTA         |            6 |           12 |    6 |         11 |     185 |            0 |
| OBRIGACAO     |           22 |           10 |   20 |         12 |      91 |            0 |
| RECOMENDACAO  |            2 |            0 |    9 |          0 |      20 |            0 |
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
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |          0.7985 |          0.8249 |         0.7958 |        0.0266 |     0.7416 |     0.8453 |     0.1037 |
| gpt-4.1_few_shot                                       | GPT-4.1              |          0.7495 |          0.7716 |         0.7472 |        0.0274 |     0.6904 |     0.7992 |     0.1088 |
| gpt-5.1_few_shot                                       | GPT-5.1              |          0.7481 |          0.7524 |         0.7457 |        0.0267 |     0.6896 |     0.7958 |     0.1061 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |          0.7185 |          0.7403 |         0.7161 |        0.0280 |     0.6580 |     0.7678 |     0.1098 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.6917 |          0.6780 |         0.6896 |        0.0273 |     0.6330 |     0.7399 |     0.1069 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.6133 |          0.7513 |         0.6102 |        0.0381 |     0.5457 |     0.6893 |     0.1436 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.6055 |          0.6722 |         0.6039 |        0.0261 |     0.5522 |     0.6545 |     0.1023 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.6047 |          0.7348 |         0.6014 |        0.0393 |     0.5294 |     0.6808 |     0.1515 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.5832 |          0.4499 |         0.5810 |        0.0259 |     0.5282 |     0.6299 |     0.1018 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.5673 |          0.7433 |         0.5660 |        0.0244 |     0.5200 |     0.6160 |     0.0960 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.5516 |          0.7275 |         0.5499 |        0.0272 |     0.4990 |     0.6059 |     0.1069 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.5386 |          0.7106 |         0.5384 |        0.0203 |     0.4979 |     0.5770 |     0.0790 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.5315 |          0.7099 |         0.5314 |        0.0202 |     0.4912 |     0.5707 |     0.0795 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.5301 |          0.7094 |         0.5294 |        0.0221 |     0.4853 |     0.5709 |     0.0857 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.5270 |          0.7255 |         0.5264 |        0.0220 |     0.4809 |     0.5682 |     0.0873 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.5236 |          0.7280 |         0.5227 |        0.0214 |     0.4794 |     0.5632 |     0.0838 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.5176 |          0.6904 |         0.5171 |        0.0336 |     0.4573 |     0.5884 |     0.1311 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.4354 |          0.4805 |         0.4356 |        0.0248 |     0.3868 |     0.4846 |     0.0978 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2504 |          0.3579 |         0.2496 |        0.0323 |     0.1919 |     0.3174 |     0.1255 |

**Itens 43–46 — Pares destacados:**

| model_a                                            | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm_all |   p_bonferroni_all |   p_bh_all | sig_holm_all_5pct   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:---------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|-------------:|-------------------:|-----------:|:--------------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                         | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7985 | 0.5236 |    0.2731 |     0.2139 |     0.3285 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash | BERTimbau-large   | 0.7985 | 0.6047 |    0.1945 |     0.1042 |     0.2754 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| deepseek-v4-flash_few_shot                         | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7985 | 0.6133 |    0.1857 |     0.0971 |     0.2608 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |   0.0000 |         0.0000 | True            | True                  |            12 |
| gpt-4.1_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1           | LegalBert-pt      | 0.7495 | 0.6133 |    0.1370 |     0.0461 |     0.2133 |    0.0052 | True             |       0.3848 |             0.8892 |     0.0091 | False               |   0.0312 |         0.0624 | True            | False                 |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.5236 | 0.6133 |   -0.0874 |    -0.1669 |    -0.0223 |    0.0016 | True             |       0.1328 |             0.2736 |     0.0031 | False               |   0.0128 |         0.0192 | True            | True                  |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base    | BERTimbau-large   | 0.5236 | 0.6047 |   -0.0786 |    -0.1589 |    -0.0041 |    0.0342 | True             |       1.0000 |             1.0000 |     0.0527 | False               |   0.1710 |         0.4104 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7495 | 0.6917 |    0.0576 |     0.0229 |     0.0940 |    0.0010 | True             |       0.0860 |             0.1710 |     0.0019 | False               |   0.0090 |         0.0120 | True            | True                  |            12 |
| gpt-4.1_few_shot                                   | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7495 | 0.7985 |   -0.0487 |    -0.0828 |    -0.0157 |    0.0024 | True             |       0.1920 |             0.4104 |     0.0045 | False               |   0.0168 |         0.0288 | True            | True                  |            12 |
| bilstm-crf__supervised                             | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF        | LegalBert-pt      | 0.5673 | 0.6133 |   -0.0442 |    -0.0989 |     0.0085 |    0.1014 | False            |       1.0000 |             1.0000 |     0.1365 | False               |   0.3042 |         1.0000 | False           | False                 |            12 |
| gpt-4.1_few_shot                                   | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7495 | 0.7185 |    0.0310 |    -0.0011 |     0.0660 |    0.0596 | False            |       1.0000 |             1.0000 |     0.0849 | False               |   0.2384 |         0.7152 | False           | False                 |            12 |
| neuralmind_bert-large-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large   | LegalBert-pt      | 0.6047 | 0.6133 |   -0.0088 |    -0.0556 |     0.0471 |    0.6882 | False            |       1.0000 |             1.0000 |     0.7355 | False               |   1.0000 |         1.0000 | False           | False                 |            12 |
| neuralmind_bert-base-portuguese-cased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.5236 | 0.5270 |   -0.0036 |    -0.0405 |     0.0331 |    0.8500 | False            |       1.0000 |             1.0000 |     0.8756 | False               |   1.0000 |         1.0000 | False           | False                 |            12 |

**Itens 47–48 — Resumo:**

| metric                         | value                        |
|:-------------------------------|:-----------------------------|
| resampling_unit                | document                     |
| n_docs_resampled               | 861                          |
| n_total_pairs                  | 171                          |
| n_significant_5pct_uncorrected | 115                          |
| n_sig_holm_all                 | 84                           |
| n_sig_bonferroni_all           | 82                           |
| n_sig_bh_all                   | 110                          |
| highlighted_family_size        | 12                           |
| highlighted_n_sig_uncorrected  | 8                            |
| highlighted_n_sig_holm         | 7                            |
| highlighted_n_sig_bonferroni   | 6                            |
| highlighted_n_sig_holm_all     | 3                            |
| smallest_significant_abs_diff  | 0.04868737132876085          |
| smallest_significant_pair      | GPT-4.1 vs DeepSeek-V4-Flash |
| leader_model                   | DeepSeek-V4-Flash            |
| leader_group_size_holm         | 3                            |

**p48a — Correção para múltiplas comparações.** A família inferencial é o conjunto completo dos pares (`p_holm_all`, `p_bonferroni_all`, `p_bh_all`), pré-especificado por construção; os pares destacados acima são uma seleção para leitura e herdam esses valores. As colunas `p_holm`/`p_bonferroni` (correção restrita aos destacados) são mantidas apenas como referência.

**Grupo do líder (DS-p.55a).** Comparações líder × demais modelos, com o `p_holm` da família completa de pares; `in_leader_group=True` marca os modelos estatisticamente indistinguíveis do líder a 5% — a fonte do marcador (†) na tabela geral de resultados:

| model                                                  | display              |   span_f1 |   diff_vs_leader |    p_raw |   p_holm | in_leader_group   |
|:-------------------------------------------------------|:---------------------|----------:|-----------------:|---------:|---------:|:------------------|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |    0.7985 |           0.0000 | nan      | nan      | True              |
| gpt-4.1_few_shot                                       | GPT-4.1              |    0.7495 |           0.0487 |   0.0024 |   0.1920 | True              |
| gpt-5.1_few_shot                                       | GPT-5.1              |    0.7481 |           0.0501 |   0.0070 |   0.5040 | True              |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |    0.7185 |           0.0797 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.6917 |           0.1063 |   0.0000 |   0.0000 | False             |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.6133 |           0.1857 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.6055 |           0.1919 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.6047 |           0.1945 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.5832 |           0.2148 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.5673 |           0.2299 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.5516 |           0.2460 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.5386 |           0.2574 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.5315 |           0.2644 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.5301 |           0.2664 |   0.0000 |   0.0000 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.5270 |           0.2695 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.5236 |           0.2731 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.5176 |           0.2787 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.4354 |           0.3602 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2504 |           0.5462 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm_all |   p_bonferroni_all |   p_bh_all | sig_holm_all_5pct   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|-------------:|-------------------:|-----------:|:--------------------|
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7985 | 0.2504 |    0.5462 |     0.4588 |     0.6212 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7495 | 0.2504 |    0.4975 |     0.4095 |     0.5723 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.7481 | 0.2504 |    0.4961 |     0.4074 |     0.5725 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.7185 | 0.2504 |    0.4665 |     0.3689 |     0.5497 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.6917 | 0.2504 |    0.4399 |     0.3526 |     0.5172 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2504 | 0.6133 |   -0.3605 |    -0.4585 |    -0.2678 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.4354 | 0.7985 |   -0.3602 |    -0.4234 |    -0.2968 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2504 | 0.6055 |   -0.3543 |    -0.4342 |    -0.2635 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2504 | 0.6047 |   -0.3517 |    -0.4518 |    -0.2513 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.5832 | 0.2504 |    0.3314 |     0.2408 |     0.4102 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2504 | 0.5673 |   -0.3163 |    -0.3917 |    -0.2360 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7495 | 0.4354 |    0.3115 |     0.2521 |     0.3703 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.4354 | 0.7481 |   -0.3101 |    -0.3700 |    -0.2501 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2504 | 0.5516 |   -0.3002 |    -0.3817 |    -0.2146 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2504 | 0.5386 |   -0.2888 |    -0.3554 |    -0.2146 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2504 | 0.5315 |   -0.2818 |    -0.3465 |    -0.2090 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.7185 | 0.4354 |    0.2805 |     0.2226 |     0.3389 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2504 | 0.5301 |   -0.2798 |    -0.3498 |    -0.2015 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7985 | 0.5176 |    0.2787 |     0.1955 |     0.3541 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2504 | 0.5270 |   -0.2768 |    -0.3452 |    -0.2020 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7985 | 0.5236 |    0.2731 |     0.2139 |     0.3285 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2504 | 0.5236 |   -0.2731 |    -0.3431 |    -0.1943 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7985 | 0.5270 |    0.2695 |     0.2084 |     0.3248 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2504 | 0.5176 |   -0.2675 |    -0.3571 |    -0.1800 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7985 | 0.5301 |    0.2664 |     0.2007 |     0.3280 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7985 | 0.5315 |    0.2644 |     0.2027 |     0.3196 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7985 | 0.5386 |    0.2574 |     0.1960 |     0.3140 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.4354 | 0.6917 |   -0.2539 |    -0.3057 |    -0.2012 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7985 | 0.5516 |    0.2460 |     0.1785 |     0.3082 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7495 | 0.5176 |    0.2301 |     0.1439 |     0.3051 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7985 | 0.5673 |    0.2299 |     0.1633 |     0.2906 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.7481 | 0.5176 |    0.2286 |     0.1417 |     0.3029 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7495 | 0.5236 |    0.2244 |     0.1639 |     0.2810 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.7481 | 0.5236 |    0.2230 |     0.1631 |     0.2792 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7495 | 0.5270 |    0.2208 |     0.1602 |     0.2763 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.7481 | 0.5270 |    0.2193 |     0.1582 |     0.2741 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7495 | 0.5301 |    0.2177 |     0.1546 |     0.2778 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.7481 | 0.5301 |    0.2163 |     0.1541 |     0.2741 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7495 | 0.5315 |    0.2157 |     0.1536 |     0.2730 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.5832 | 0.7985 |   -0.2148 |    -0.2603 |    -0.1709 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.7481 | 0.5315 |    0.2143 |     0.1514 |     0.2716 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7495 | 0.5386 |    0.2087 |     0.1455 |     0.2670 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.7481 | 0.5386 |    0.2073 |     0.1446 |     0.2645 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.7185 | 0.5176 |    0.1990 |     0.1124 |     0.2718 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7495 | 0.5516 |    0.1973 |     0.1261 |     0.2633 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.7481 | 0.5516 |    0.1958 |     0.1246 |     0.2601 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7985 | 0.6047 |    0.1945 |     0.1042 |     0.2754 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.7185 | 0.5236 |    0.1934 |     0.1328 |     0.2484 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7985 | 0.6055 |    0.1919 |     0.1448 |     0.2403 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.7185 | 0.5270 |    0.1898 |     0.1259 |     0.2483 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.7185 | 0.5301 |    0.1867 |     0.1253 |     0.2460 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.4354 | 0.2504 |    0.1860 |     0.0989 |     0.2624 |    0.0002 | True             |       0.0186 |             0.0342 |     0.0004 | True                |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7985 | 0.6133 |    0.1857 |     0.0971 |     0.2608 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.7185 | 0.5315 |    0.1847 |     0.1219 |     0.2430 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7495 | 0.5673 |    0.1812 |     0.1135 |     0.2437 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.7481 | 0.5673 |    0.1797 |     0.1145 |     0.2405 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.7185 | 0.5386 |    0.1777 |     0.1143 |     0.2358 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.4354 | 0.6133 |   -0.1746 |    -0.2612 |    -0.1021 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.6917 | 0.5176 |    0.1725 |     0.0864 |     0.2493 |    0.0002 | True             |       0.0186 |             0.0342 |     0.0004 | True                |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.4354 | 0.6055 |   -0.1683 |    -0.2244 |    -0.1127 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.6917 | 0.5236 |    0.1668 |     0.1085 |     0.2224 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.7185 | 0.5516 |    0.1663 |     0.0940 |     0.2323 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7495 | 0.5832 |    0.1661 |     0.1266 |     0.2075 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.4354 | 0.6047 |   -0.1657 |    -0.2542 |    -0.0859 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.5832 | 0.7481 |   -0.1647 |    -0.2061 |    -0.1254 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.6917 | 0.5270 |    0.1632 |     0.1032 |     0.2171 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.6917 | 0.5301 |    0.1601 |     0.1001 |     0.2164 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.6917 | 0.5315 |    0.1581 |     0.0971 |     0.2149 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.6917 | 0.5386 |    0.1511 |     0.0882 |     0.2093 |    0.0002 | True             |       0.0186 |             0.0342 |     0.0004 | True                |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.7185 | 0.5673 |    0.1502 |     0.0811 |     0.2129 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7495 | 0.6047 |    0.1458 |     0.0543 |     0.2264 |    0.0018 | True             |       0.1476 |             0.3078 |     0.0034 | False               |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.4354 | 0.5832 |   -0.1454 |    -0.2043 |    -0.0862 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.7481 | 0.6047 |    0.1443 |     0.0553 |     0.2225 |    0.0022 | True             |       0.1782 |             0.3762 |     0.0041 | False               |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7495 | 0.6055 |    0.1432 |     0.0983 |     0.1893 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.7481 | 0.6055 |    0.1418 |     0.0962 |     0.1882 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.6917 | 0.5516 |    0.1397 |     0.0699 |     0.2024 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7495 | 0.6133 |    0.1370 |     0.0461 |     0.2133 |    0.0052 | True             |       0.3848 |             0.8892 |     0.0091 | False               |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.7481 | 0.6133 |    0.1355 |     0.0467 |     0.2089 |    0.0032 | True             |       0.2528 |             0.5472 |     0.0058 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.7185 | 0.5832 |    0.1351 |     0.0948 |     0.1755 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.4354 | 0.5673 |   -0.1304 |    -0.1944 |    -0.0687 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.6917 | 0.5673 |    0.1236 |     0.0588 |     0.1844 |    0.0002 | True             |       0.0186 |             0.0342 |     0.0004 | True                |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.7185 | 0.6047 |    0.1148 |     0.0237 |     0.1948 |    0.0140 | True             |       0.9380 |             1.0000 |     0.0228 | False               |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.4354 | 0.5516 |   -0.1143 |    -0.1779 |    -0.0553 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.7185 | 0.6055 |    0.1122 |     0.0676 |     0.1560 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.5832 | 0.6917 |   -0.1085 |    -0.1479 |    -0.0703 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.6917 | 0.7985 |   -0.1063 |    -0.1485 |    -0.0647 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.7185 | 0.6133 |    0.1060 |     0.0147 |     0.1833 |    0.0258 | True             |       1.0000 |             1.0000 |     0.0408 | False               |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.4354 | 0.5386 |   -0.1028 |    -0.1577 |    -0.0462 |    0.0010 | True             |       0.0860 |             0.1710 |     0.0019 | False               |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.4354 | 0.5315 |   -0.0958 |    -0.1524 |    -0.0373 |    0.0010 | True             |       0.0860 |             0.1710 |     0.0019 | False               |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.4354 | 0.5301 |   -0.0938 |    -0.1483 |    -0.0354 |    0.0032 | True             |       0.2528 |             0.5472 |     0.0058 | False               |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.6133 | 0.5176 |    0.0931 |     0.0043 |     0.1864 |    0.0430 | True             |       1.0000 |             1.0000 |     0.0651 | False               |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.4354 | 0.5270 |   -0.0908 |    -0.1469 |    -0.0333 |    0.0034 | True             |       0.2584 |             0.5814 |     0.0061 | False               |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.6917 | 0.6047 |    0.0882 |     0.0002 |     0.1669 |    0.0490 | True             |       1.0000 |             1.0000 |     0.0729 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.5236 | 0.6133 |   -0.0874 |    -0.1669 |    -0.0223 |    0.0016 | True             |       0.1328 |             0.2736 |     0.0031 | False               |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.4354 | 0.5236 |   -0.0871 |    -0.1423 |    -0.0303 |    0.0040 | True             |       0.3000 |             0.6840 |     0.0071 | False               |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.6055 | 0.5176 |    0.0868 |     0.0020 |     0.1625 |    0.0452 | True             |       1.0000 |             1.0000 |     0.0678 | False               |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.6917 | 0.6055 |    0.0856 |     0.0395 |     0.1325 |    0.0004 | True             |       0.0356 |             0.0684 |     0.0008 | True                |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.6047 | 0.5176 |    0.0842 |    -0.0082 |     0.1753 |    0.0724 | False            |       1.0000 |             1.0000 |     0.1007 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.5270 | 0.6133 |   -0.0838 |    -0.1618 |    -0.0218 |    0.0006 | True             |       0.0522 |             0.1026 |     0.0012 | False               |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.4354 | 0.5176 |   -0.0815 |    -0.1638 |    -0.0071 |    0.0314 | True             |       1.0000 |             1.0000 |     0.0488 | False               |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.6055 | 0.5236 |    0.0812 |     0.0220 |     0.1406 |    0.0082 | True             |       0.5740 |             1.0000 |     0.0137 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.5301 | 0.6133 |   -0.0807 |    -0.1635 |    -0.0147 |    0.0068 | True             |       0.4964 |             1.0000 |     0.0117 | False               |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.7185 | 0.7985 |   -0.0797 |    -0.1217 |    -0.0396 |    0.0000 | True             |       0.0000 |             0.0000 |     0.0000 | True                |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.6917 | 0.6133 |    0.0794 |    -0.0098 |     0.1556 |    0.0782 | False            |       1.0000 |             1.0000 |     0.1078 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.5315 | 0.6133 |   -0.0788 |    -0.1566 |    -0.0177 |    0.0032 | True             |       0.2528 |             0.5472 |     0.0058 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.5236 | 0.6047 |   -0.0786 |    -0.1589 |    -0.0041 |    0.0342 | True             |       1.0000 |             1.0000 |     0.0527 | False               |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.6055 | 0.5270 |    0.0775 |     0.0173 |     0.1363 |    0.0126 | True             |       0.8694 |             1.0000 |     0.0209 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.6047 | 0.5270 |    0.0750 |     0.0022 |     0.1534 |    0.0402 | True             |       1.0000 |             1.0000 |     0.0614 | False               |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.6055 | 0.5301 |    0.0745 |     0.0138 |     0.1342 |    0.0164 | True             |       1.0000 |             1.0000 |     0.0262 | False               |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.6055 | 0.5315 |    0.0725 |     0.0137 |     0.1306 |    0.0156 | True             |       1.0000 |             1.0000 |     0.0252 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.5301 | 0.6047 |   -0.0719 |    -0.1530 |     0.0009 |    0.0538 | False            |       1.0000 |             1.0000 |     0.0786 | False               |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.6133 | 0.5386 |    0.0717 |     0.0091 |     0.1515 |    0.0128 | True             |       0.8704 |             1.0000 |     0.0210 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.6047 | 0.5315 |    0.0699 |    -0.0017 |     0.1471 |    0.0588 | False            |       1.0000 |             1.0000 |     0.0845 | False               |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.6055 | 0.5386 |    0.0655 |     0.0068 |     0.1232 |    0.0268 | True             |       1.0000 |             1.0000 |     0.0420 | False               |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.5832 | 0.5176 |    0.0639 |    -0.0263 |     0.1411 |    0.1412 | False            |       1.0000 |             1.0000 |     0.1829 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.6047 | 0.5386 |    0.0629 |    -0.0081 |     0.1410 |    0.0994 | False            |       1.0000 |             1.0000 |     0.1349 | False               |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.6133 | 0.5516 |    0.0603 |     0.0147 |     0.1080 |    0.0076 | True             |       0.5396 |             1.0000 |     0.0129 | False               |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.5832 | 0.5236 |    0.0583 |    -0.0037 |     0.1177 |    0.0642 | False            |       1.0000 |             1.0000 |     0.0907 | False               |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7495 | 0.6917 |    0.0576 |     0.0229 |     0.0940 |    0.0010 | True             |       0.0860 |             0.1710 |     0.0019 | False               |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.7481 | 0.6917 |    0.0561 |     0.0220 |     0.0927 |    0.0004 | True             |       0.0356 |             0.0684 |     0.0008 | True                |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.5832 | 0.5270 |    0.0546 |    -0.0098 |     0.1147 |    0.0930 | False            |       1.0000 |             1.0000 |     0.1272 | False               |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.6055 | 0.5516 |    0.0541 |    -0.0143 |     0.1187 |    0.1166 | False            |       1.0000 |             1.0000 |     0.1546 | False               |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.5832 | 0.5301 |    0.0516 |    -0.0121 |     0.1120 |    0.1106 | False            |       1.0000 |             1.0000 |     0.1478 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.6047 | 0.5516 |    0.0515 |    -0.0009 |     0.1062 |    0.0550 | False            |       1.0000 |             1.0000 |     0.0797 | False               |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.7481 | 0.7985 |   -0.0501 |    -0.0866 |    -0.0133 |    0.0070 | True             |       0.5040 |             1.0000 |     0.0120 | False               |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.5832 | 0.5315 |    0.0496 |    -0.0130 |     0.1079 |    0.1230 | False            |       1.0000 |             1.0000 |     0.1618 | False               |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.5673 | 0.5176 |    0.0489 |    -0.0280 |     0.1225 |    0.2056 | False            |       1.0000 |             1.0000 |     0.2566 | False               |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7495 | 0.7985 |   -0.0487 |    -0.0828 |    -0.0157 |    0.0024 | True             |       0.1920 |             0.4104 |     0.0045 | False               |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.5673 | 0.6133 |   -0.0442 |    -0.0989 |     0.0085 |    0.1014 | False            |       1.0000 |             1.0000 |     0.1365 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.5236 | 0.5673 |   -0.0432 |    -0.0935 |     0.0005 |    0.0532 | False            |       1.0000 |             1.0000 |     0.0784 | False               |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.5832 | 0.5386 |    0.0426 |    -0.0204 |     0.1012 |    0.1820 | False            |       1.0000 |             1.0000 |     0.2305 | False               |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.5673 | 0.5270 |    0.0396 |    -0.0124 |     0.0972 |    0.1412 | False            |       1.0000 |             1.0000 |     0.1829 | False               |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.6055 | 0.5673 |    0.0380 |    -0.0286 |     0.1033 |    0.2662 | False            |       1.0000 |             1.0000 |     0.3275 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.5301 | 0.5673 |   -0.0365 |    -0.0929 |     0.0132 |    0.1624 | False            |       1.0000 |             1.0000 |     0.2072 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.6047 | 0.5673 |    0.0354 |    -0.0234 |     0.0952 |    0.2520 | False            |       1.0000 |             1.0000 |     0.3123 | False               |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.5673 | 0.5315 |    0.0346 |    -0.0122 |     0.0864 |    0.1578 | False            |       1.0000 |             1.0000 |     0.2029 | False               |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.5176 | 0.5516 |   -0.0328 |    -0.1053 |     0.0443 |    0.3892 | False            |       1.0000 |             1.0000 |     0.4590 | False               |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.5832 | 0.5516 |    0.0311 |    -0.0376 |     0.0933 |    0.3470 | False            |       1.0000 |             1.0000 |     0.4149 | False               |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7495 | 0.7185 |    0.0310 |    -0.0011 |     0.0660 |    0.0596 | False            |       1.0000 |             1.0000 |     0.0849 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.7185 | 0.7481 |   -0.0296 |    -0.0643 |     0.0019 |    0.0678 | False            |       1.0000 |             1.0000 |     0.0950 | False               |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.5832 | 0.6133 |   -0.0292 |    -0.1163 |     0.0449 |    0.5040 | False            |       1.0000 |             1.0000 |     0.5708 | False               |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.5673 | 0.5386 |    0.0275 |    -0.0233 |     0.0825 |    0.2996 | False            |       1.0000 |             1.0000 |     0.3633 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.5236 | 0.5516 |   -0.0271 |    -0.0850 |     0.0236 |    0.3262 | False            |       1.0000 |             1.0000 |     0.3928 | False               |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.7185 | 0.6917 |    0.0266 |    -0.0131 |     0.0666 |    0.1910 | False            |       1.0000 |             1.0000 |     0.2402 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.5270 | 0.5516 |   -0.0235 |    -0.0782 |     0.0253 |    0.3818 | False            |       1.0000 |             1.0000 |     0.4534 | False               |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.5832 | 0.6055 |   -0.0229 |    -0.0639 |     0.0195 |    0.2686 | False            |       1.0000 |             1.0000 |     0.3281 | False               |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.5176 | 0.5386 |   -0.0213 |    -0.0705 |     0.0392 |    0.4266 | False            |       1.0000 |             1.0000 |     0.4962 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.5301 | 0.5516 |   -0.0204 |    -0.0770 |     0.0283 |    0.4772 | False            |       1.0000 |             1.0000 |     0.5440 | False               |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.5832 | 0.6047 |   -0.0203 |    -0.1102 |     0.0573 |    0.6582 | False            |       1.0000 |             1.0000 |     0.7124 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.5315 | 0.5516 |   -0.0185 |    -0.0695 |     0.0270 |    0.4750 | False            |       1.0000 |             1.0000 |     0.5440 | False               |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.5673 | 0.5516 |    0.0161 |    -0.0228 |     0.0558 |    0.4090 | False            |       1.0000 |             1.0000 |     0.4790 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.5236 | 0.5386 |   -0.0157 |    -0.0551 |     0.0234 |    0.4384 | False            |       1.0000 |             1.0000 |     0.5065 | False               |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.5832 | 0.5673 |    0.0150 |    -0.0511 |     0.0768 |    0.6254 | False            |       1.0000 |             1.0000 |     0.6915 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.5315 | 0.5176 |    0.0143 |    -0.0510 |     0.0704 |    0.6186 | False            |       1.0000 |             1.0000 |     0.6914 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.5301 | 0.5176 |    0.0123 |    -0.0536 |     0.0696 |    0.6624 | False            |       1.0000 |             1.0000 |     0.7124 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.5270 | 0.5386 |   -0.0120 |    -0.0490 |     0.0241 |    0.5210 | False            |       1.0000 |             1.0000 |     0.5861 | False               |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.5516 | 0.5386 |    0.0114 |    -0.0365 |     0.0655 |    0.6990 | False            |       1.0000 |             1.0000 |     0.7378 | False               |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.5270 | 0.5176 |    0.0093 |    -0.0514 |     0.0614 |    0.7208 | False            |       1.0000 |             1.0000 |     0.7562 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.5301 | 0.5386 |   -0.0090 |    -0.0463 |     0.0266 |    0.6304 | False            |       1.0000 |             1.0000 |     0.6915 | False               |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.6047 | 0.6133 |   -0.0088 |    -0.0556 |     0.0471 |    0.6882 | False            |       1.0000 |             1.0000 |     0.7355 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.5236 | 0.5315 |   -0.0087 |    -0.0448 |     0.0271 |    0.6308 | False            |       1.0000 |             1.0000 |     0.6915 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.5315 | 0.5386 |   -0.0070 |    -0.0388 |     0.0258 |    0.6422 | False            |       1.0000 |             1.0000 |     0.6995 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.5301 | 0.5236 |    0.0067 |    -0.0258 |     0.0405 |    0.6980 | False            |       1.0000 |             1.0000 |     0.7378 | False               |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.6055 | 0.6133 |   -0.0062 |    -0.0923 |     0.0675 |    0.9258 | False            |       1.0000 |             1.0000 |     0.9338 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.5236 | 0.5176 |    0.0056 |    -0.0624 |     0.0668 |    0.8358 | False            |       1.0000 |             1.0000 |     0.8662 | False               |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.5315 | 0.5270 |    0.0050 |    -0.0302 |     0.0428 |    0.8032 | False            |       1.0000 |             1.0000 |     0.8375 | False               |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.5236 | 0.5270 |   -0.0036 |    -0.0405 |     0.0331 |    0.8500 | False            |       1.0000 |             1.0000 |     0.8756 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.5301 | 0.5270 |    0.0030 |    -0.0335 |     0.0402 |    0.8712 | False            |       1.0000 |             1.0000 |     0.8921 | False               |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.6055 | 0.6047 |    0.0026 |    -0.0865 |     0.0801 |    0.9290 | False            |       1.0000 |             1.0000 |     0.9338 | False               |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.5301 | 0.5315 |   -0.0020 |    -0.0406 |     0.0354 |    0.9338 | False            |       1.0000 |             1.0000 |     0.9338 | False               |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7495 | 0.7481 |    0.0015 |    -0.0248 |     0.0282 |    0.9210 | False            |       1.0000 |             1.0000 |     0.9338 | False               |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 **macro** por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0); o micro está em `K_iou_sensitivity_wide_micro.csv`:

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.5464 | 0.5236 | 0.5049 |  0.4490 |
| BERTimbau-large      | 0.6384 | 0.6047 | 0.5811 |  0.5169 |
| BERTimbauLaw         | 0.5545 | 0.5270 | 0.5111 |  0.4596 |
| BiLSTM-CRF           | 0.5974 | 0.5673 | 0.4816 |  0.3984 |
| DeepSeek-V4-Flash    | 0.8394 | 0.7985 | 0.7597 |  0.3733 |
| GPT-4.1              | 0.7962 | 0.7495 | 0.6934 |  0.2796 |
| GPT-4.1-mini         | 0.7573 | 0.7185 | 0.6648 |  0.2659 |
| GPT-4.1-nano         | 0.4895 | 0.4354 | 0.3780 |  0.1178 |
| GPT-5-mini           | 0.6062 | 0.5832 | 0.5534 |  0.1670 |
| GPT-5.1              | 0.7790 | 0.7481 | 0.6941 |  0.3177 |
| GPT-5.2              | 0.7270 | 0.6917 | 0.6385 |  0.2569 |
| GovBERT-BR           | 0.5626 | 0.5386 | 0.5041 |  0.4406 |
| JurisBERT            | 0.5478 | 0.5315 | 0.4833 |  0.3972 |
| Legal-BERT-STF       | 0.5766 | 0.5516 | 0.5238 |  0.4749 |
| Legal-BERTimbau-base | 0.5497 | 0.5301 | 0.5080 |  0.4456 |
| LegalBERTPT-br       | 0.5301 | 0.5176 | 0.4820 |  0.4389 |
| LegalBert-pt         | 0.6353 | 0.6133 | 0.5715 |  0.5224 |
| Llama-3.3-70B        | 0.2697 | 0.2504 | 0.2255 |  0.0582 |
| Qwen2.5-72B          | 0.6435 | 0.6055 | 0.5669 |  0.2684 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5, no macro e no micro):

| iou_threshold   |   spearman_macro_vs_0.5 |   spearman_micro_vs_0.5 |
|:----------------|------------------------:|------------------------:|
| 0.3             |                  0.9877 |                  0.9895 |
| 0.5             |                  1.0000 |                  1.0000 |
| 0.7             |                  0.9158 |                  0.9070 |
| exact           |                 -0.0561 |                  0.3807 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 659 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 202 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_macro_full |   span_f1_macro_informative |   delta_span_f1_macro |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------------:|----------------------------:|----------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  202 |               0.7985 |                      0.8312 |                0.0327 |         0.8249 |                0.8494 |          0.0244 |                0.8132 |                       0.8622 |                 0.0489 |             0.8370 |                    0.8370 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  202 |               0.7495 |                      0.8163 |                0.0668 |         0.7716 |                0.8200 |          0.0484 |                0.7004 |                       0.7844 |                 0.0840 |             0.8589 |                    0.8589 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  202 |               0.7481 |                      0.8124 |                0.0644 |         0.7524 |                0.8116 |          0.0591 |                0.6724 |                       0.7731 |                 0.1007 |             0.8540 |                    0.8540 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  202 |               0.7185 |                      0.7920 |                0.0735 |         0.7403 |                0.8089 |          0.0687 |                0.6384 |                       0.7479 |                 0.1095 |             0.8808 |                    0.8808 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  202 |               0.6917 |                      0.7611 |                0.0694 |         0.6780 |                0.7561 |          0.0780 |                0.5550 |                       0.6679 |                 0.1129 |             0.8710 |                    0.8710 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  202 |               0.5832 |                      0.7234 |                0.1402 |         0.4499 |                0.6919 |          0.2420 |                0.2986 |                       0.5572 |                 0.2586 |             0.9124 |                    0.9124 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  202 |               0.6055 |                      0.6936 |                0.0882 |         0.6722 |                0.7431 |          0.0709 |                0.5859 |                       0.7028 |                 0.1169 |             0.7883 |                    0.7883 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  202 |               0.6133 |                      0.6204 |                0.0071 |         0.7513 |                0.7583 |          0.0070 |                0.8232 |                       0.8402 |                 0.0170 |             0.6910 |                    0.6910 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  202 |               0.6047 |                      0.6121 |                0.0074 |         0.7348 |                0.7425 |          0.0077 |                0.7845 |                       0.8023 |                 0.0177 |             0.6910 |                    0.6910 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  202 |               0.5673 |                      0.5760 |                0.0087 |         0.7433 |                0.7544 |          0.0111 |                0.8249 |                       0.8528 |                 0.0278 |             0.6764 |                    0.6764 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  202 |               0.5516 |                      0.5557 |                0.0041 |         0.7275 |                0.7324 |          0.0049 |                0.8114 |                       0.8237 |                 0.0123 |             0.6594 |                    0.6594 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  202 |               0.5386 |                      0.5449 |                0.0063 |         0.7106 |                0.7174 |          0.0068 |                0.7952 |                       0.8123 |                 0.0171 |             0.6423 |                    0.6423 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  202 |               0.5315 |                      0.5359 |                0.0044 |         0.7099 |                0.7147 |          0.0048 |                0.7970 |                       0.8092 |                 0.0123 |             0.6399 |                    0.6399 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  202 |               0.5301 |                      0.5354 |                0.0052 |         0.7094 |                0.7163 |          0.0068 |                0.8075 |                       0.8254 |                 0.0179 |             0.6326 |                    0.6326 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  202 |               0.5270 |                      0.5317 |                0.0048 |         0.7255 |                0.7316 |          0.0061 |                0.8376 |                       0.8539 |                 0.0163 |             0.6399 |                    0.6399 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  202 |               0.5236 |                      0.5270 |                0.0034 |         0.7280 |                0.7331 |          0.0051 |                0.8529 |                       0.8671 |                 0.0142 |             0.6350 |                    0.6350 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  202 |               0.5176 |                      0.5256 |                0.0080 |         0.6904 |                0.6990 |          0.0086 |                0.7900 |                       0.8129 |                 0.0229 |             0.6131 |                    0.6131 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |           861 |                  202 |               0.4354 |                      0.4790 |                0.0436 |         0.4805 |                0.5499 |          0.0694 |                0.3883 |                       0.4878 |                 0.0995 |             0.6302 |                    0.6302 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |           861 |                  202 |               0.2504 |                      0.2553 |                0.0050 |         0.3579 |                0.3623 |          0.0044 |                0.6415 |                       0.6711 |                 0.0295 |             0.2482 |                    0.2482 |

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
