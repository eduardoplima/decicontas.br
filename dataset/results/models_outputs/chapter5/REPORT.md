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
| Pares significativos a 5% (de 91)  | 61.0000 | 133.0000 | 72.0000 |
| Menor Δ detectável (significativo) |  0.0337 |   0.0318 | -0.0019 |

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

## C. Resultados gerais (14 modelos × 6 métricas)

| model                                                  | display              |   token_f1 |   token_f1_macro |   token_precision |   token_recall |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:-------------------------------------------------------|:---------------------|-----------:|-----------------:|------------------:|---------------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |     0.8086 |           0.7695 |            0.8447 |         0.7754 |    0.7527 |          0.7306 |           0.7370 |        0.7691 |
| gpt-4.1_few_shot                                       | GPT-4.1              |     0.8002 |           0.7648 |            0.7928 |         0.8077 |    0.7216 |          0.7062 |           0.6560 |        0.8017 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |     0.7964 |           0.6904 |            0.9339 |         0.6942 |    0.7003 |          0.6370 |           0.7634 |        0.6468 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |     0.7812 |           0.7439 |            0.7538 |         0.8106 |    0.6851 |          0.6743 |           0.5946 |        0.8083 |
| gpt-5.1_few_shot                                       | GPT-5.1              |     0.7700 |           0.7365 |            0.7492 |         0.7919 |    0.6847 |          0.6745 |           0.6142 |        0.7734 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |     0.7675 |           0.6701 |            0.9455 |         0.6459 |    0.6844 |          0.6224 |           0.7701 |        0.6158 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |     0.7683 |           0.6318 |            0.9506 |         0.6447 |    0.6786 |          0.5801 |           0.7994 |        0.5895 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |     0.7502 |           0.5758 |            0.9265 |         0.6302 |    0.6546 |          0.5351 |           0.7507 |        0.5803 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |     0.7200 |           0.5929 |            0.9457 |         0.5812 |    0.6390 |          0.5678 |           0.7469 |        0.5584 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |     0.7023 |           0.6582 |            0.7121 |         0.6928 |    0.6135 |          0.5778 |           0.5491 |        0.6950 |
| gpt-5.2_few_shot                                       | GPT-5.2              |     0.7415 |           0.7024 |            0.6952 |         0.7945 |    0.6067 |          0.5852 |           0.5029 |        0.7647 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |     0.6855 |           0.4242 |            0.9474 |         0.5371 |    0.6021 |          0.4058 |           0.8223 |        0.4749 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |     0.6820 |           0.5103 |            0.9607 |         0.5287 |    0.6018 |          0.4778 |           0.8285 |        0.4726 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |     0.7307 |           0.5638 |            0.8455 |         0.6434 |    0.5926 |          0.5004 |           0.7742 |        0.4800 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |     0.5919 |           0.4365 |            0.9701 |         0.4259 |    0.5434 |          0.4245 |           0.8646 |        0.3962 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |     0.5728 |           0.3582 |            0.9710 |         0.4063 |    0.4945 |          0.3412 |           0.7182 |        0.3771 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |     0.5795 |           0.4965 |            0.5876 |         0.5717 |    0.4325 |          0.3943 |           0.3587 |        0.5447 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |     0.5721 |           0.6215 |            0.4423 |         0.8097 |    0.4097 |          0.5242 |           0.2765 |        0.7908 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |     0.4023 |           0.2789 |            0.7545 |         0.2743 |    0.3396 |          0.2734 |           0.5956 |        0.2375 |

**Variabilidade entre folds dos supervisionados (itens 17–19):**

| model                                                  | display              |   span_f1_mean |   span_f1_std |   span_f1_min |   span_f1_max | span_f1_per_fold                       |   token_f1_mean |   token_f1_std |   token_f1_min |   token_f1_max | token_f1_per_fold                      | config                                                                                         |
|:-------------------------------------------------------|:---------------------|---------------:|--------------:|--------------:|--------------:|:---------------------------------------|----------------:|---------------:|---------------:|---------------:|:---------------------------------------|:-----------------------------------------------------------------------------------------------|
| bilstm-crf__supervised                                 | BiLSTM-CRF           |         0.5910 |        0.0518 |        0.5455 |        0.6761 | 0.5690; 0.6023; 0.5622; 0.6761; 0.5455 |          0.7191 |         0.0956 |         0.5531 |         0.7932 | 0.7400; 0.7716; 0.7376; 0.7932; 0.5531 | {"hidden_dim": 256, "dropout": 0.3, "lr": 0.003}                                               |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |         0.6753 |        0.0475 |        0.6071 |        0.7218 | 0.6984; 0.7035; 0.6456; 0.6071; 0.7218 |          0.7642 |         0.0475 |         0.7148 |         0.8261 | 0.7756; 0.8261; 0.7148; 0.7182; 0.7863 | {"model_name": "neuralmind/bert-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1}      |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |         0.5712 |        0.1687 |        0.2857 |        0.7191 | 0.2857; 0.7191; 0.5652; 0.6387; 0.6475 |          0.6514 |         0.1939 |         0.3323 |         0.8035 | 0.3323; 0.8035; 0.6045; 0.7442; 0.7724 | {"model_name": "neuralmind/bert-large-portuguese-cased", "lr": 2e-05, "warmup_ratio": 0.1}     |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |         0.5885 |        0.1394 |        0.3564 |        0.6984 | 0.3564; 0.6744; 0.5634; 0.6984; 0.6500 |          0.6679 |         0.1561 |         0.4115 |         0.8146 | 0.4115; 0.7469; 0.6413; 0.8146; 0.7252 | {"model_name": "rufimelo/Legal-BERTimbau-base", "lr": 5e-05, "warmup_ratio": 0.1}              |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |         0.6401 |        0.0487 |        0.5854 |        0.6917 | 0.5854; 0.6462; 0.5952; 0.6917; 0.6822 |          0.7157 |         0.0635 |         0.6469 |         0.7771 | 0.6492; 0.7771; 0.6469; 0.7677; 0.7375 | {"model_name": "alfaneo/jurisbert-base-portuguese-uncased", "lr": 3e-05, "warmup_ratio": 0.1}  |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |         0.6801 |        0.0599 |        0.5763 |        0.7286 | 0.5763; 0.6907; 0.6957; 0.7286; 0.7092 |          0.7622 |         0.0726 |         0.6486 |         0.8264 | 0.6486; 0.7961; 0.7325; 0.8264; 0.8071 | {"model_name": "alfaneo/bertimbaulaw-base-portuguese-cased", "lr": 5e-05, "warmup_ratio": 0.1} |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |         0.6992 |        0.0233 |        0.6777 |        0.7381 | 0.7015; 0.6900; 0.7381; 0.6777; 0.6887 |          0.7944 |         0.0141 |         0.7810 |         0.8175 | 0.7875; 0.8175; 0.7972; 0.7810; 0.7890 | {"model_name": "raquelsilveira/legalbertpt_fp", "lr": 5e-05, "warmup_ratio": 0.0}              |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |         0.4358 |        0.2533 |        0.0000 |        0.6465 | 0.4510; 0.6465; 0.5315; 0.0000; 0.5500 |          0.5074 |         0.2985 |         0.0000 |         0.7722 | 0.5108; 0.7722; 0.6137; 0.0000; 0.6401 | {"model_name": "ulysses-camara/legal-bert-pt-br", "lr": 5e-05, "warmup_ratio": 0.0}            |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |         0.6594 |        0.0455 |        0.5922 |        0.7049 | 0.6528; 0.6484; 0.5922; 0.6986; 0.7049 |          0.7507 |         0.0361 |         0.7005 |         0.7855 | 0.7759; 0.7657; 0.7005; 0.7855; 0.7258 | {"model_name": "dominguesm/legal-bert-base-cased-ptbr", "lr": 5e-05, "warmup_ratio": 0.1}      |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |         0.5044 |        0.1937 |        0.2529 |        0.6951 | 0.3596; 0.6951; 0.5429; 0.2529; 0.6718 |          0.5529 |         0.2052 |         0.2787 |         0.7443 | 0.4040; 0.7303; 0.6073; 0.2787; 0.7443 | {"model_name": "dccmpmgfinalisticas/GovBERT-BR", "lr": 5e-05, "warmup_ratio": 0.0}             |

**Resumo por paradigma (média entre modelos):**

| ('paradigm', '')   |   ('token_f1', 'mean') |   ('token_f1', 'std') |   ('token_f1', 'min') |   ('token_f1', 'max') |   ('span_f1', 'mean') |   ('span_f1', 'std') |   ('span_f1', 'min') |   ('span_f1', 'max') |
|:-------------------|-----------------------:|----------------------:|----------------------:|----------------------:|----------------------:|---------------------:|---------------------:|---------------------:|
| few-shot           |                 0.6842 |                0.1380 |                0.4023 |                0.8086 |                0.5829 |               0.1509 |               0.3396 |               0.7527 |
| supervised         |                 0.7065 |                0.0748 |                0.5728 |                0.7964 |                0.6191 |               0.0655 |               0.4945 |               0.7003 |

## D. F1 de Span por entidade × modelo

**Heatmap (span F1 por modelo × entidade):**

| display              |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:---------------------|--------:|------------:|---------------:|----------------:|
| BERTimbau-base       |  0.7836 |      0.6737 |         0.3226 |          0.5405 |
| BERTimbau-large      |  0.7178 |      0.6452 |         0.2034 |          0.3448 |
| BERTimbauLaw         |  0.7562 |      0.6907 |         0.4103 |          0.6325 |
| BiLSTM-CRF           |  0.6534 |      0.6887 |         0.2466 |          0.4130 |
| DeepSeek-V4-Flash    |  0.8160 |      0.7008 |         0.6619 |          0.7438 |
| GPT-4.1              |  0.7895 |      0.6364 |         0.6621 |          0.7368 |
| GPT-4.1-mini         |  0.7735 |      0.5748 |         0.6301 |          0.7188 |
| GPT-4.1-nano         |  0.6529 |      0.3153 |         0.1017 |          0.5072 |
| GPT-5-mini           |  0.6820 |      0.2231 |         0.5860 |          0.6056 |
| GPT-5.1              |  0.7600 |      0.5833 |         0.6383 |          0.7164 |
| GPT-5.2              |  0.7371 |      0.4742 |         0.5255 |          0.6040 |
| GovBERT-BR           |  0.6054 |      0.6257 |         0.0000 |          0.4667 |
| JurisBERT            |  0.6845 |      0.6595 |         0.2388 |          0.6885 |
| Legal-BERT-STF       |  0.7590 |      0.6866 |         0.1905 |          0.5042 |
| Legal-BERTimbau-base |  0.7548 |      0.6243 |         0.0727 |          0.1714 |
| LegalBERTPT-br       |  0.6028 |      0.5432 |         0.0800 |          0.1389 |
| LegalBert-pt         |  0.7784 |      0.6952 |         0.4474 |          0.6271 |
| Llama-3.3-70B        |  0.4014 |      0.3689 |         0.2927 |          0.0308 |
| Qwen2.5-72B          |  0.7528 |      0.5116 |         0.3704 |          0.6765 |

**Detalhe completo (precision, recall, F1, matched/gold/pred):**

| model                                                  | display              | label         |   precision |   recall |     f1 |   matched |   total_gold |   total_pred |
|:-------------------------------------------------------|:---------------------|:--------------|------------:|---------:|-------:|----------:|-------------:|-------------:|
| gpt-4.1_few_shot                                       | GPT-4.1              | MULTA         |      0.7377 |   0.8491 | 0.7895 |       180 |          212 |          244 |
| gpt-4.1_few_shot                                       | GPT-4.1              | OBRIGACAO     |      0.5871 |   0.6947 | 0.6364 |        91 |          131 |          155 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RECOMENDACAO  |      0.5217 |   0.9057 | 0.6621 |        48 |           53 |           92 |
| gpt-4.1_few_shot                                       | GPT-4.1              | RESSARCIMENTO |      0.7000 |   0.7778 | 0.7368 |        49 |           63 |           70 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | MULTA         |      0.7070 |   0.8538 | 0.7735 |       181 |          212 |          256 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | OBRIGACAO     |      0.4667 |   0.7481 | 0.5748 |        98 |          131 |          210 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RECOMENDACAO  |      0.4946 |   0.8679 | 0.6301 |        46 |           53 |           93 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         | RESSARCIMENTO |      0.7077 |   0.7302 | 0.7188 |        46 |           63 |           65 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | MULTA         |      0.6368 |   0.6698 | 0.6529 |       142 |          212 |          223 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | OBRIGACAO     |      0.2327 |   0.4885 | 0.3153 |        64 |          131 |          275 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RECOMENDACAO  |      0.0726 |   0.1698 | 0.1017 |         9 |           53 |          124 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         | RESSARCIMENTO |      0.4667 |   0.5556 | 0.5072 |        35 |           63 |           75 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | MULTA         |      0.6128 |   0.7689 | 0.6820 |       163 |          212 |          266 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | OBRIGACAO     |      0.1285 |   0.8473 | 0.2231 |       111 |          131 |          864 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RECOMENDACAO  |      0.4423 |   0.8679 | 0.5860 |        46 |           53 |          104 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           | RESSARCIMENTO |      0.5443 |   0.6825 | 0.6056 |        43 |           63 |           79 |
| gpt-5.1_few_shot                                       | GPT-5.1              | MULTA         |      0.7185 |   0.8066 | 0.7600 |       171 |          212 |          238 |
| gpt-5.1_few_shot                                       | GPT-5.1              | OBRIGACAO     |      0.5028 |   0.6947 | 0.5833 |        91 |          131 |          181 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RECOMENDACAO  |      0.5114 |   0.8491 | 0.6383 |        45 |           53 |           88 |
| gpt-5.1_few_shot                                       | GPT-5.1              | RESSARCIMENTO |      0.6761 |   0.7619 | 0.7164 |        48 |           63 |           71 |
| gpt-5.2_few_shot                                       | GPT-5.2              | MULTA         |      0.6568 |   0.8396 | 0.7371 |       178 |          212 |          271 |
| gpt-5.2_few_shot                                       | GPT-5.2              | OBRIGACAO     |      0.3580 |   0.7023 | 0.4742 |        92 |          131 |          257 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RECOMENDACAO  |      0.4286 |   0.6792 | 0.5255 |        36 |           53 |           84 |
| gpt-5.2_few_shot                                       | GPT-5.2              | RESSARCIMENTO |      0.5233 |   0.7143 | 0.6040 |        45 |           63 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | MULTA         |      0.8160 |   0.8160 | 0.8160 |       173 |          212 |          212 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | OBRIGACAO     |      0.7236 |   0.6794 | 0.7008 |        89 |          131 |          123 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RECOMENDACAO  |      0.5349 |   0.8679 | 0.6619 |        46 |           53 |           86 |
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    | RESSARCIMENTO |      0.7759 |   0.7143 | 0.7438 |        45 |           63 |           58 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | MULTA         |      0.7532 |   0.2736 | 0.4014 |        58 |          212 |           77 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | OBRIGACAO     |      0.5067 |   0.2901 | 0.3689 |        38 |          131 |           75 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RECOMENDACAO  |      0.4138 |   0.2264 | 0.2927 |        12 |           53 |           29 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        | RESSARCIMENTO |      0.5000 |   0.0159 | 0.0308 |         1 |           63 |            2 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | MULTA         |      0.7249 |   0.7830 | 0.7528 |       166 |          212 |          229 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | OBRIGACAO     |      0.4529 |   0.5878 | 0.5116 |        77 |          131 |          170 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RECOMENDACAO  |      0.2752 |   0.5660 | 0.3704 |        30 |           53 |          109 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          | RESSARCIMENTO |      0.6301 |   0.7302 | 0.6765 |        46 |           63 |           73 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | MULTA         |      0.7965 |   0.7173 | 0.7548 |       137 |          191 |          172 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | OBRIGACAO     |      0.9818 |   0.4576 | 0.6243 |        54 |          118 |           55 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RECOMENDACAO  |      0.2857 |   0.0417 | 0.0727 |         2 |           48 |            7 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base | RESSARCIMENTO |      0.7500 |   0.0968 | 0.1714 |         6 |           62 |            8 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | MULTA         |      0.8218 |   0.7487 | 0.7836 |       143 |          191 |          174 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | OBRIGACAO     |      0.8889 |   0.5424 | 0.6737 |        64 |          118 |           72 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RECOMENDACAO  |      0.7143 |   0.2083 | 0.3226 |        10 |           48 |           14 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       | RESSARCIMENTO |      0.6122 |   0.4839 | 0.5405 |        30 |           62 |           49 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | MULTA         |      0.8667 |   0.6126 | 0.7178 |       117 |          191 |          135 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | OBRIGACAO     |      0.8824 |   0.5085 | 0.6452 |        60 |          118 |           68 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RECOMENDACAO  |      0.5455 |   0.1250 | 0.2034 |         6 |           48 |           11 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      | RESSARCIMENTO |      0.6000 |   0.2419 | 0.3448 |        15 |           62 |           25 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | MULTA         |      0.7986 |   0.5529 | 0.6534 |       115 |          208 |          144 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | OBRIGACAO     |      0.8488 |   0.5794 | 0.6887 |        73 |          126 |           86 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RECOMENDACAO  |      0.4500 |   0.1698 | 0.2466 |         9 |           53 |           20 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           | RESSARCIMENTO |      0.6552 |   0.3016 | 0.4130 |        19 |           63 |           29 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | MULTA         |      0.7232 |   0.6497 | 0.6845 |       128 |          197 |          177 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | OBRIGACAO     |      0.9242 |   0.5126 | 0.6595 |        61 |          119 |           66 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RECOMENDACAO  |      0.4444 |   0.1633 | 0.2388 |         8 |           49 |           18 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            | RESSARCIMENTO |      0.7119 |   0.6667 | 0.6885 |        42 |           63 |           59 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | MULTA         |      0.7931 |   0.7225 | 0.7562 |       138 |          191 |          174 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | OBRIGACAO     |      0.8816 |   0.5678 | 0.6907 |        67 |          118 |           76 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RECOMENDACAO  |      0.5333 |   0.3333 | 0.4103 |        16 |           48 |           30 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         | RESSARCIMENTO |      0.6727 |   0.5968 | 0.6325 |        37 |           62 |           55 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | MULTA         |      0.8045 |   0.7539 | 0.7784 |       144 |          191 |          179 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | OBRIGACAO     |      0.7935 |   0.6186 | 0.6952 |        73 |          118 |           92 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RECOMENDACAO  |      0.6071 |   0.3542 | 0.4474 |        17 |           48 |           28 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         | RESSARCIMENTO |      0.6607 |   0.5968 | 0.6271 |        37 |           62 |           56 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | MULTA         |      0.6524 |   0.5602 | 0.6028 |       107 |          191 |          164 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | OBRIGACAO     |      1.0000 |   0.3729 | 0.5432 |        44 |          118 |           44 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RECOMENDACAO  |      1.0000 |   0.0417 | 0.0800 |         2 |           48 |            2 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       | RESSARCIMENTO |      0.5000 |   0.0806 | 0.1389 |         5 |           62 |           10 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | MULTA         |      0.7789 |   0.7400 | 0.7590 |       148 |          200 |          190 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | OBRIGACAO     |      0.8734 |   0.5656 | 0.6866 |        69 |          122 |           79 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RECOMENDACAO  |      0.5000 |   0.1176 | 0.1905 |         6 |           51 |           12 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       | RESSARCIMENTO |      0.5357 |   0.4762 | 0.5042 |        30 |           63 |           56 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | MULTA         |      0.8641 |   0.4660 | 0.6054 |        89 |          191 |          103 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | OBRIGACAO     |      0.9180 |   0.4746 | 0.6257 |        56 |          118 |           61 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RECOMENDACAO  |      0.0000 |   0.0000 | 0.0000 |         0 |           48 |            0 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           | RESSARCIMENTO |      0.7500 |   0.3387 | 0.4667 |        21 |           62 |           28 |

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
| deepseek-v4-flash | function_calling |     0.8170 |    0.7620 |          0.7362 |           0.7469 |        0.7778 |
| deepseek-v4-flash | json_schema      |     0.8142 |    0.7503 |          0.7174 |           0.7384 |        0.7625 |
| gpt-4.1           | function_calling |     0.7978 |    0.7271 |          0.7110 |           0.6637 |        0.8039 |
| gpt-4.1           | json_schema      |     0.8022 |    0.7163 |          0.6946 |           0.6576 |        0.7865 |

**Δ por modelo (FC − JS):**

| model             |   delta_token_f1 |   delta_span_f1 |   delta_span_precision |   delta_span_recall |
|:------------------|-----------------:|----------------:|-----------------------:|--------------------:|
| deepseek-v4-flash |           0.0028 |          0.0117 |                 0.0085 |              0.0153 |
| gpt-4.1           |          -0.0044 |          0.0108 |                 0.0061 |              0.0174 |

## G. FC vs JSON Schema por entidade

**Span F1 (modelo+método × entidade) — pivotado:**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8314 |      0.7137 |         0.6619 |          0.7377 |
| deepseek-v4-flash | json_schema      |  0.8227 |      0.7160 |         0.6260 |          0.7049 |
| gpt-4.1           | function_calling |  0.7912 |      0.6502 |         0.6713 |          0.7313 |
| gpt-4.1           | json_schema      |  0.7807 |      0.6594 |         0.6014 |          0.7368 |

**Span Precision (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8373 |      0.7339 |         0.5349 |          0.7627 |
| deepseek-v4-flash | json_schema      |  0.8246 |      0.7302 |         0.5256 |          0.7288 |
| gpt-4.1           | function_calling |  0.7407 |      0.6053 |         0.5333 |          0.6901 |
| gpt-4.1           | json_schema      |  0.7295 |      0.6276 |         0.4778 |          0.7000 |

**Span Recall (modelo+método × entidade):**

| model             | method           |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:-----------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | function_calling |  0.8255 |      0.6947 |         0.8679 |          0.7143 |
| deepseek-v4-flash | json_schema      |  0.8208 |      0.7023 |         0.7736 |          0.6825 |
| gpt-4.1           | function_calling |  0.8491 |      0.7023 |         0.9057 |          0.7778 |
| gpt-4.1           | json_schema      |  0.8396 |      0.6947 |         0.8113 |          0.7778 |

## H. Técnicas de prompting

**Métricas overall (modelo × técnica):**

| model             | technique   |   token_f1 |   span_f1 |   span_f1_macro |   span_precision |   span_recall |
|:------------------|:------------|-----------:|----------:|----------------:|-----------------:|--------------:|
| deepseek-v4-flash | cot         |     0.8038 |    0.7051 |          0.6724 |           0.6306 |        0.7996 |
| deepseek-v4-flash | few_shot    |     0.8086 |    0.7527 |          0.7306 |           0.7370 |        0.7691 |
| deepseek-v4-flash | two_stage   |     0.8060 |    0.7481 |          0.7181 |           0.7303 |        0.7669 |
| gpt-4.1           | cot         |     0.7925 |    0.7195 |          0.7064 |           0.6525 |        0.8017 |
| gpt-4.1           | few_shot    |     0.8002 |    0.7216 |          0.7062 |           0.6560 |        0.8017 |
| gpt-4.1           | two_stage   |     0.8062 |    0.7298 |          0.7142 |           0.6667 |        0.8061 |
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
| deepseek-v4-flash | 0.7051 |     0.7527 |      0.7481 |
| gpt-4.1           | 0.7195 |     0.7216 |      0.7298 |
| gpt-5.2           | 0.6762 |     0.6067 |      0.6574 |
| llama-3.3-70b     | 0.2526 |     0.3396 |      0.1231 |
| qwen2.5-72b       | 0.6346 |     0.6135 |      0.6261 |

**Resumo agregado por técnica (média ± std, min, max):**

| technique   | token_f1           | token_f1.1          | token_f1.2          | token_f1.3         | span_f1            | span_f1.1           | span_f1.2           | span_f1.3          |
|:------------|:-------------------|:--------------------|:--------------------|:-------------------|:-------------------|:--------------------|:--------------------|:-------------------|
| nan         | mean               | std                 | min                 | max                | mean               | std                 | min                 | max                |
| cot         | 0.6843994246782771 | 0.2136586900320103  | 0.30499119510079636 | 0.8037704646932363 | 0.59757637828506   | 0.1955581757878387  | 0.25259515570934254 | 0.7194525904203323 |
| few_shot    | 0.690979463683193  | 0.16716501695998784 | 0.402299676607977   | 0.8085765863959944 | 0.6068001694154269 | 0.16271757746952556 | 0.3395638629283489  | 0.7526652452025585 |
| two_stage   | 0.6524620919623081 | 0.2804546715739215  | 0.15450922509225093 | 0.8061960237859909 | 0.57690746334632   | 0.2586302618313607  | 0.12307692307692308 | 0.7481402763018066 |

**Por entidade — span F1 (modelo+técnica × entidade):** essencial para a narrativa de queda do DeepSeek-V3 com CoT, ganho do gpt-5.4-nano e do Gemini.

| model             | technique   |   MULTA |   OBRIGACAO |   RECOMENDACAO |   RESSARCIMENTO |
|:------------------|:------------|--------:|------------:|---------------:|----------------:|
| deepseek-v4-flash | cot         |  0.8345 |      0.6929 |         0.4571 |          0.7049 |
| deepseek-v4-flash | few_shot    |  0.8160 |      0.7008 |         0.6619 |          0.7438 |
| deepseek-v4-flash | two_stage   |  0.8160 |      0.7177 |         0.6619 |          0.6769 |
| gpt-4.1           | cot         |  0.7859 |      0.6351 |         0.6620 |          0.7424 |
| gpt-4.1           | few_shot    |  0.7895 |      0.6364 |         0.6621 |          0.7368 |
| gpt-4.1           | two_stage   |  0.7930 |      0.6549 |         0.6667 |          0.7424 |
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
| deepseek-v4-flash | cot         |  0.8249 |      0.6510 |         0.3057 |          0.7288 |
| deepseek-v4-flash | few_shot    |  0.8160 |      0.7236 |         0.5349 |          0.7759 |
| deepseek-v4-flash | two_stage   |  0.8160 |      0.7607 |         0.5349 |          0.6567 |
| gpt-4.1           | cot         |  0.7386 |      0.5697 |         0.5281 |          0.7101 |
| gpt-4.1           | few_shot    |  0.7377 |      0.5871 |         0.5217 |          0.7000 |
| gpt-4.1           | two_stage   |  0.7438 |      0.6078 |         0.5275 |          0.7101 |
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
| deepseek-v4-flash | cot         |  0.8443 |      0.7405 |         0.9057 |          0.6825 |
| deepseek-v4-flash | few_shot    |  0.8160 |      0.6794 |         0.8679 |          0.7143 |
| deepseek-v4-flash | two_stage   |  0.8160 |      0.6794 |         0.8679 |          0.6984 |
| gpt-4.1           | cot         |  0.8396 |      0.7176 |         0.8868 |          0.7778 |
| gpt-4.1           | few_shot    |  0.8491 |      0.6947 |         0.9057 |          0.7778 |
| gpt-4.1           | two_stage   |  0.8491 |      0.7099 |         0.9057 |          0.7778 |
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
| exact      |     364 |
| FN         |      78 |
| FP         |      64 |
| boundary   |      49 |
| type_error |       2 |

**Matriz rótulo × tipo de erro:**

| label         |   FN |   FP |   boundary |   exact |   type_error |
|:--------------|-----:|-----:|-----------:|--------:|-------------:|
| MULTA         |   33 |    6 |         12 |     181 |            0 |
| OBRIGACAO     |   32 |   20 |         14 |      89 |            0 |
| RECOMENDACAO  |    6 |   36 |          1 |      48 |            0 |
| RESSARCIMENTO |    7 |    2 |         22 |      46 |            2 |

**Pares de tipo errado (gold → pred):**

| label         | pred_label   |   count |
|:--------------|:-------------|--------:|
| RESSARCIMENTO | MULTA        |       2 |

**Histograma de IoU para erros de fronteira:**

|   bin_low |   bin_high |   count |
|----------:|-----------:|--------:|
|    0.0000 |     0.2000 |  5.0000 |
|    0.2000 |     0.4000 | 28.0000 |
|    0.4000 |     0.5000 | 16.0000 |
|    0.5000 |     0.7000 |  0.0000 |
|    0.7000 |     0.9000 |  0.0000 |
|    0.9000 |     1.0000 |  0.0000 |

## J. Significância estatística (bootstrap pareado)

**Item 41 — N de reamostragens**: 10.000.

**Item 42 — IC 95% por modelo:**

| model                                                  | display              |   span_f1_point |   span_f1_micro |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:-------------------------------------------------------|:---------------------|----------------:|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |          0.7306 |          0.7527 |         0.7303 |        0.0238 |     0.6832 |     0.7765 |     0.0933 |
| gpt-4.1_few_shot                                       | GPT-4.1              |          0.7062 |          0.7216 |         0.7059 |        0.0228 |     0.6614 |     0.7504 |     0.0889 |
| gpt-5.1_few_shot                                       | GPT-5.1              |          0.6745 |          0.6847 |         0.6741 |        0.0227 |     0.6284 |     0.7184 |     0.0900 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |          0.6743 |          0.6851 |         0.6740 |        0.0226 |     0.6286 |     0.7179 |     0.0893 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.6370 |          0.7003 |         0.6361 |        0.0292 |     0.5782 |     0.6916 |     0.1134 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.6224 |          0.6844 |         0.6217 |        0.0295 |     0.5641 |     0.6789 |     0.1148 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.5852 |          0.6067 |         0.5853 |        0.0259 |     0.5339 |     0.6348 |     0.1009 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.5801 |          0.6786 |         0.5788 |        0.0309 |     0.5184 |     0.6385 |     0.1201 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.5778 |          0.6135 |         0.5775 |        0.0231 |     0.5323 |     0.6223 |     0.0900 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.5678 |          0.6390 |         0.5673 |        0.0301 |     0.5078 |     0.6262 |     0.1184 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.5351 |          0.6546 |         0.5349 |        0.0293 |     0.4779 |     0.5933 |     0.1154 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.5242 |          0.4097 |         0.5241 |        0.0229 |     0.4776 |     0.5677 |     0.0901 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.5004 |          0.5926 |         0.4998 |        0.0322 |     0.4378 |     0.5640 |     0.1262 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.4778 |          0.6018 |         0.4768 |        0.0312 |     0.4159 |     0.5378 |     0.1219 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.4245 |          0.5434 |         0.4238 |        0.0269 |     0.3701 |     0.4757 |     0.1056 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.4058 |          0.6021 |         0.4049 |        0.0278 |     0.3524 |     0.4608 |     0.1084 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.3943 |          0.4325 |         0.3948 |        0.0253 |     0.3448 |     0.4449 |     0.1001 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.3412 |          0.4945 |         0.3397 |        0.0296 |     0.2830 |     0.4001 |     0.1171 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.2734 |          0.3396 |         0.2733 |        0.0273 |     0.2205 |     0.3276 |     0.1071 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                        | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash | Llama-3.3-70B     | 0.7306 | 0.2734 |    0.4570 |     0.3961 |     0.5168 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-5.2           | Llama-3.3-70B     | 0.5852 | 0.2734 |    0.3120 |     0.2411 |     0.3821 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| llama-3.3-70b_few_shot                            | qwen2.5-72b_few_shot                                   | Llama-3.3-70B     | Qwen2.5-72B       | 0.2734 | 0.5778 |   -0.3042 |    -0.3726 |    -0.2365 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1-mini_few_shot                             | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini      | GPT-4.1-nano      | 0.6743 | 0.3943 |    0.2792 |     0.2233 |     0.3343 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7306 | 0.5801 |    0.1515 |     0.0883 |     0.2159 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-5.2           | DeepSeek-V4-Flash | 0.5852 | 0.7306 |   -0.1450 |    -0.1933 |    -0.0967 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7062 | 0.5852 |    0.1206 |     0.0792 |     0.1634 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7306 | 0.6370 |    0.0942 |     0.0357 |     0.1534 |    0.0014 | True             |   0.0126 |         0.0238 | True            | True                  |            17 |
| gpt-5.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-5.1           | GPT-5.2           | 0.6745 | 0.5852 |    0.0888 |     0.0458 |     0.1329 |    0.0002 | True             |   0.0020 |         0.0034 | True            | True                  |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                                 | BERTimbau-base    | BiLSTM-CRF        | 0.5801 | 0.5004 |    0.0790 |    -0.0011 |     0.1566 |    0.0538 | False            |   0.3228 |         0.9146 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.5801 | 0.6370 |   -0.0573 |    -0.1083 |    -0.0047 |    0.0328 | True             |   0.2296 |         0.5576 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2           | LegalBert-pt      | 0.5852 | 0.6370 |   -0.0508 |    -0.1194 |     0.0176 |    0.1506 | False            |   0.4518 |         1.0000 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.5801 | 0.6224 |   -0.0429 |    -0.0919 |     0.0046 |    0.0744 | False            |   0.3228 |         1.0000 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7062 | 0.6743 |    0.0319 |     0.0073 |     0.0592 |    0.0102 | True             |   0.0816 |         0.1734 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7062 | 0.7306 |   -0.0244 |    -0.0507 |     0.0014 |    0.0626 | False            |   0.3228 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-5.2           | Qwen2.5-72B       | 0.5852 | 0.5778 |    0.0078 |    -0.0390 |     0.0554 |    0.7488 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2           | BERTimbau-base    | 0.5852 | 0.5801 |    0.0065 |    -0.0666 |     0.0797 |    0.8590 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |

**Itens 47–48 — Resumo:**

| metric                         | value               |
|:-------------------------------|:--------------------|
| resampling_unit                | document            |
| n_docs_resampled               | 861                 |
| n_total_pairs                  | 171                 |
| n_significant_5pct_uncorrected | 133                 |
| highlighted_family_size        | 17                  |
| highlighted_n_sig_uncorrected  | 11                  |
| highlighted_n_sig_holm         | 9                   |
| highlighted_n_sig_bonferroni   | 9                   |
| smallest_significant_abs_diff  | 0.03184401910604364 |
| smallest_significant_pair      | GPT-4.1 vs GPT-5.1  |
| leader_model                   | DeepSeek-V4-Flash   |
| leader_group_size_holm         | 2                   |

**p48a — Correção para múltiplas comparações.** A família reportada são os pares destacados acima; `p_holm`/`p_bonferroni` controlam o erro familiar (FWER) e `sig_holm_5pct` substitui a coluna 'Sig.' não corrigida da Tabela 13. Diferenças marginais tendem a não sobreviver, reforçando a leitura de saturação.

**Grupo do líder (DS-p.55a).** Família: as comparações líder × demais modelos, com correção de Holm; `in_leader_group=True` marca os modelos estatisticamente indistinguíveis do líder a 5% — a fonte do marcador (†) na tabela geral de resultados:

| model                                                  | display              |   span_f1 |   diff_vs_leader |    p_raw |   p_holm | in_leader_group   |
|:-------------------------------------------------------|:---------------------|----------:|-----------------:|---------:|---------:|:------------------|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |    0.7306 |           0.0000 | nan      | nan      | True              |
| gpt-4.1_few_shot                                       | GPT-4.1              |    0.7062 |           0.0244 |   0.0626 |   0.0626 | True              |
| gpt-5.1_few_shot                                       | GPT-5.1              |    0.6745 |           0.0562 |   0.0008 |   0.0024 | False             |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |    0.6743 |           0.0563 |   0.0000 |   0.0000 | False             |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |    0.6370 |           0.0942 |   0.0014 |   0.0028 | False             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |    0.6224 |           0.1086 |   0.0000 |   0.0000 | False             |
| gpt-5.2_few_shot                                       | GPT-5.2              |    0.5852 |           0.1450 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |    0.5801 |           0.1515 |   0.0000 |   0.0000 | False             |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |    0.5778 |           0.1528 |   0.0000 |   0.0000 | False             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |    0.5678 |           0.1630 |   0.0000 |   0.0000 | False             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |    0.5351 |           0.1954 |   0.0000 |   0.0000 | False             |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |    0.5242 |           0.2062 |   0.0000 |   0.0000 | False             |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |    0.5004 |           0.2305 |   0.0000 |   0.0000 | False             |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |    0.4778 |           0.2535 |   0.0000 |   0.0000 | False             |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |    0.4245 |           0.3065 |   0.0000 |   0.0000 | False             |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |    0.4058 |           0.3254 |   0.0000 |   0.0000 | False             |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |    0.3943 |           0.3355 |   0.0000 |   0.0000 | False             |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |    0.3412 |           0.3906 |   0.0000 |   0.0000 | False             |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |    0.2734 |           0.4570 |   0.0000 |   0.0000 | False             |

**Tabela completa dos pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7306 | 0.2734 |    0.4570 |     0.3961 |     0.5168 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7062 | 0.2734 |    0.4326 |     0.3710 |     0.4930 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.6745 | 0.2734 |    0.4008 |     0.3353 |     0.4626 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.6743 | 0.2734 |    0.4007 |     0.3362 |     0.4622 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7306 | 0.3412 |    0.3906 |     0.3161 |     0.4582 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7062 | 0.3412 |    0.3662 |     0.2941 |     0.4322 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.2734 | 0.6370 |   -0.3628 |    -0.4324 |    -0.2895 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.2734 | 0.6224 |   -0.3484 |    -0.4157 |    -0.2786 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.3943 | 0.7306 |   -0.3355 |    -0.3947 |    -0.2737 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.6745 | 0.3412 |    0.3344 |     0.2619 |     0.3996 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.6743 | 0.3412 |    0.3344 |     0.2595 |     0.4011 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7306 | 0.4058 |    0.3254 |     0.2636 |     0.3848 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.5852 | 0.2734 |    0.3120 |     0.2411 |     0.3821 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7062 | 0.3943 |    0.3111 |     0.2526 |     0.3666 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7306 | 0.4245 |    0.3065 |     0.2447 |     0.3674 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.2734 | 0.5801 |   -0.3055 |    -0.3772 |    -0.2307 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.2734 | 0.5778 |   -0.3042 |    -0.3726 |    -0.2365 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7062 | 0.4058 |    0.3010 |     0.2408 |     0.3600 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.6370 | 0.3412 |    0.2964 |     0.2304 |     0.3608 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.2734 | 0.5678 |   -0.2940 |    -0.3626 |    -0.2229 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7062 | 0.4245 |    0.2821 |     0.2244 |     0.3392 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.6224 | 0.3412 |    0.2821 |     0.2153 |     0.3476 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.3943 | 0.6745 |   -0.2793 |    -0.3346 |    -0.2227 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.6743 | 0.3943 |    0.2792 |     0.2233 |     0.3343 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.6745 | 0.4058 |    0.2692 |     0.2054 |     0.3290 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.6743 | 0.4058 |    0.2691 |     0.2096 |     0.3255 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.2734 | 0.5351 |   -0.2616 |    -0.3274 |    -0.1929 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7306 | 0.4778 |    0.2535 |     0.1871 |     0.3208 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.5242 | 0.2734 |    0.2508 |     0.1846 |     0.3157 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.6745 | 0.4245 |    0.2502 |     0.1890 |     0.3103 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.6743 | 0.4245 |    0.2502 |     0.1914 |     0.3086 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.5852 | 0.3412 |    0.2456 |     0.1711 |     0.3159 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.3943 | 0.6370 |   -0.2413 |    -0.3098 |    -0.1725 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.5801 | 0.3412 |    0.2392 |     0.1741 |     0.3037 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.5778 | 0.3412 |    0.2378 |     0.1654 |     0.3069 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.4058 | 0.6370 |   -0.2312 |    -0.2925 |    -0.1687 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7306 | 0.5004 |    0.2305 |     0.1584 |     0.3012 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7062 | 0.4778 |    0.2291 |     0.1642 |     0.2927 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.5678 | 0.3412 |    0.2276 |     0.1559 |     0.2951 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.3943 | 0.6224 |   -0.2269 |    -0.2951 |    -0.1580 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.2734 | 0.5004 |   -0.2265 |    -0.2975 |    -0.1566 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.4058 | 0.6224 |   -0.2168 |    -0.2732 |    -0.1606 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.6370 | 0.4245 |    0.2123 |     0.1480 |     0.2767 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.5242 | 0.7306 |   -0.2062 |    -0.2486 |    -0.1643 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7062 | 0.5004 |    0.2061 |     0.1365 |     0.2729 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.2734 | 0.4778 |   -0.2035 |    -0.2740 |    -0.1318 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.6224 | 0.4245 |    0.1979 |     0.1392 |     0.2580 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.6745 | 0.4778 |    0.1973 |     0.1324 |     0.2607 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.6743 | 0.4778 |    0.1972 |     0.1308 |     0.2617 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7306 | 0.5351 |    0.1954 |     0.1337 |     0.2542 |    0.0000 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.3412 | 0.5351 |   -0.1953 |    -0.2625 |    -0.1243 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.3943 | 0.5852 |   -0.1905 |    -0.2373 |    -0.1425 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.5242 | 0.3412 |    0.1844 |     0.1122 |     0.2534 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.3943 | 0.5801 |   -0.1840 |    -0.2568 |    -0.1095 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.3943 | 0.5778 |   -0.1827 |    -0.2363 |    -0.1286 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7062 | 0.5242 |    0.1818 |     0.1418 |     0.2222 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.5852 | 0.4058 |    0.1804 |     0.1132 |     0.2449 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.6745 | 0.5004 |    0.1742 |     0.1029 |     0.2420 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.6743 | 0.5004 |    0.1742 |     0.1033 |     0.2427 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.4058 | 0.5801 |   -0.1739 |    -0.2391 |    -0.1064 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.5778 | 0.4058 |    0.1726 |     0.1077 |     0.2361 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.3943 | 0.5678 |   -0.1725 |    -0.2428 |    -0.1008 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7062 | 0.5351 |    0.1710 |     0.1085 |     0.2316 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7306 | 0.5678 |    0.1630 |     0.1011 |     0.2255 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.4058 | 0.5678 |   -0.1624 |    -0.2154 |    -0.1073 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.5852 | 0.4245 |    0.1615 |     0.1011 |     0.2229 |    0.0000 | True             |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.5004 | 0.3412 |    0.1601 |     0.0851 |     0.2351 |    0.0002 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.4778 | 0.6370 |   -0.1593 |    -0.2255 |    -0.0909 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.5801 | 0.4245 |    0.1550 |     0.0945 |     0.2160 |    0.0000 | True             |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.5778 | 0.4245 |    0.1537 |     0.0917 |     0.2159 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7306 | 0.5778 |    0.1528 |     0.1093 |     0.1989 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7306 | 0.5801 |    0.1515 |     0.0883 |     0.2159 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.2734 | 0.4245 |   -0.1505 |    -0.2154 |    -0.0842 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.5242 | 0.6745 |   -0.1500 |    -0.1924 |    -0.1083 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.6743 | 0.5242 |    0.1499 |     0.1113 |     0.1902 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.5852 | 0.7306 |   -0.1450 |    -0.1933 |    -0.0967 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.4778 | 0.6224 |   -0.1449 |    -0.2030 |    -0.0894 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.5678 | 0.4245 |    0.1435 |     0.0829 |     0.2055 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.3943 | 0.5351 |   -0.1401 |    -0.2084 |    -0.0702 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.6745 | 0.5351 |    0.1391 |     0.0745 |     0.2005 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.6743 | 0.5351 |    0.1391 |     0.0762 |     0.2000 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7062 | 0.5678 |    0.1386 |     0.0777 |     0.1983 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.4778 | 0.3412 |    0.1371 |     0.0644 |     0.2071 |    0.0002 | True             |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.5004 | 0.6370 |   -0.1363 |    -0.2135 |    -0.0562 |    0.0014 | True             |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.2734 | 0.4058 |   -0.1316 |    -0.2021 |    -0.0615 |    0.0002 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.4058 | 0.5351 |   -0.1300 |    -0.1882 |    -0.0710 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.3943 | 0.5242 |   -0.1293 |    -0.1816 |    -0.0752 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7062 | 0.5778 |    0.1284 |     0.0860 |     0.1720 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7062 | 0.5801 |    0.1271 |     0.0660 |     0.1895 |    0.0000 | True             |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.5004 | 0.6224 |   -0.1219 |    -0.1877 |    -0.0538 |    0.0004 | True             |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.3943 | 0.2734 |    0.1215 |     0.0522 |     0.1893 |    0.0012 | True             |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7062 | 0.5852 |    0.1206 |     0.0792 |     0.1634 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.5242 | 0.4058 |    0.1192 |     0.0549 |     0.1798 |    0.0008 | True             |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.5242 | 0.6370 |   -0.1120 |    -0.1794 |    -0.0439 |    0.0022 | True             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.5351 | 0.4245 |    0.1111 |     0.0509 |     0.1712 |    0.0002 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7306 | 0.6224 |    0.1086 |     0.0518 |     0.1658 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.5852 | 0.4778 |    0.1085 |     0.0378 |     0.1787 |    0.0034 | True             |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.6745 | 0.5678 |    0.1068 |     0.0442 |     0.1681 |    0.0012 | True             |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.6743 | 0.5678 |    0.1068 |     0.0450 |     0.1684 |    0.0004 | True             |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.3943 | 0.5004 |   -0.1050 |    -0.1816 |    -0.0278 |    0.0080 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.5801 | 0.4778 |    0.1020 |     0.0425 |     0.1647 |    0.0010 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.6370 | 0.5351 |    0.1012 |     0.0353 |     0.1656 |    0.0034 | True             |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.5778 | 0.4778 |    0.1007 |     0.0282 |     0.1736 |    0.0070 | True             |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.5242 | 0.4245 |    0.1003 |     0.0391 |     0.1623 |    0.0014 | True             |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.5242 | 0.6224 |   -0.0976 |    -0.1621 |    -0.0336 |    0.0034 | True             |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.6745 | 0.5778 |    0.0966 |     0.0526 |     0.1407 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.6743 | 0.5778 |    0.0965 |     0.0578 |     0.1361 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.6745 | 0.5801 |    0.0952 |     0.0331 |     0.1579 |    0.0030 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.6743 | 0.5801 |    0.0952 |     0.0343 |     0.1567 |    0.0020 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.4058 | 0.5004 |   -0.0949 |    -0.1634 |    -0.0238 |    0.0112 | True             |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7306 | 0.6370 |    0.0942 |     0.0357 |     0.1534 |    0.0014 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.4778 | 0.5678 |   -0.0905 |    -0.1515 |    -0.0299 |    0.0026 | True             |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.6745 | 0.5852 |    0.0888 |     0.0458 |     0.1329 |    0.0002 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.6743 | 0.5852 |    0.0887 |     0.0464 |     0.1323 |    0.0002 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.6224 | 0.5351 |    0.0868 |     0.0378 |     0.1368 |    0.0012 | True             |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.5852 | 0.5004 |    0.0855 |     0.0072 |     0.1616 |    0.0356 | True             |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7062 | 0.6224 |    0.0842 |     0.0282 |     0.1405 |    0.0028 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.3412 | 0.4245 |   -0.0842 |    -0.1352 |    -0.0285 |    0.0038 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.3943 | 0.4778 |   -0.0820 |    -0.1517 |    -0.0123 |    0.0226 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.5801 | 0.5004 |    0.0790 |    -0.0011 |     0.1566 |    0.0538 | False            |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.5778 | 0.5004 |    0.0777 |    -0.0012 |     0.1557 |    0.0528 | False            |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.5004 | 0.4245 |    0.0760 |     0.0067 |     0.1489 |    0.0302 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.4058 | 0.4778 |   -0.0719 |    -0.1351 |    -0.0052 |    0.0358 | True             |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7062 | 0.6370 |    0.0698 |     0.0121 |     0.1290 |    0.0176 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.5678 | 0.6370 |   -0.0688 |    -0.1353 |    -0.0020 |    0.0444 | True             |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.5004 | 0.5678 |   -0.0675 |    -0.1236 |    -0.0100 |    0.0238 | True             |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.2734 | 0.3412 |   -0.0664 |    -0.1417 |     0.0077 |    0.0812 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.4058 | 0.3412 |    0.0652 |    -0.0079 |     0.1360 |    0.0750 | False            |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.5242 | 0.5852 |   -0.0612 |    -0.1023 |    -0.0195 |    0.0036 | True             |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.5778 | 0.6370 |   -0.0586 |    -0.1220 |     0.0063 |    0.0790 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.4778 | 0.5351 |   -0.0581 |    -0.1253 |     0.0083 |    0.0898 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.5801 | 0.6370 |   -0.0573 |    -0.1083 |    -0.0047 |    0.0328 | True             |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.6743 | 0.7306 |   -0.0563 |    -0.0886 |    -0.0245 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.6745 | 0.7306 |   -0.0562 |    -0.0894 |    -0.0237 |    0.0008 | True             |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.3943 | 0.3412 |    0.0551 |    -0.0139 |     0.1234 |    0.1218 | False            |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.5242 | 0.5801 |   -0.0547 |    -0.1247 |     0.0161 |    0.1264 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.5678 | 0.6224 |   -0.0545 |    -0.1012 |    -0.0098 |    0.0162 | True             |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.5242 | 0.5778 |   -0.0534 |    -0.0999 |    -0.0055 |    0.0302 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.4778 | 0.4245 |    0.0530 |     0.0006 |     0.1068 |    0.0460 | True             |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.6745 | 0.6224 |    0.0523 |    -0.0068 |     0.1110 |    0.0822 | False            |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.6743 | 0.6224 |    0.0523 |    -0.0037 |     0.1077 |    0.0684 | False            |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.5852 | 0.6370 |   -0.0508 |    -0.1194 |     0.0176 |    0.1506 | False            |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.5852 | 0.5351 |    0.0504 |    -0.0196 |     0.1192 |    0.1614 | False            |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.5242 | 0.4778 |    0.0473 |    -0.0210 |     0.1167 |    0.1796 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.5778 | 0.6224 |   -0.0442 |    -0.1094 |     0.0216 |    0.1842 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.5801 | 0.5351 |    0.0439 |    -0.0214 |     0.1090 |    0.1908 | False            |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.5242 | 0.5678 |   -0.0432 |    -0.1114 |     0.0237 |    0.2072 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.5801 | 0.6224 |   -0.0429 |    -0.0919 |     0.0046 |    0.0744 | False            |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.5778 | 0.5351 |    0.0426 |    -0.0273 |     0.1107 |    0.2370 | False            |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.6745 | 0.6370 |    0.0380 |    -0.0202 |     0.0969 |    0.2000 | False            |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.6743 | 0.6370 |    0.0379 |    -0.0212 |     0.0988 |    0.2102 | False            |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.5852 | 0.6224 |   -0.0364 |    -0.1052 |     0.0306 |    0.2960 | False            |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.5004 | 0.5351 |   -0.0351 |    -0.0947 |     0.0263 |    0.2450 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.5678 | 0.5351 |    0.0323 |    -0.0164 |     0.0811 |    0.1970 | False            |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7062 | 0.6743 |    0.0319 |     0.0073 |     0.0592 |    0.0102 | True             |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7062 | 0.6745 |    0.0318 |     0.0045 |     0.0594 |    0.0198 | True             |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.3943 | 0.4245 |   -0.0290 |    -0.0883 |     0.0328 |    0.3436 | False            |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7062 | 0.7306 |   -0.0244 |    -0.0507 |     0.0014 |    0.0626 | False            |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.5242 | 0.5004 |    0.0243 |    -0.0471 |     0.0942 |    0.4950 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.4778 | 0.5004 |   -0.0230 |    -0.0952 |     0.0468 |    0.5206 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.4058 | 0.4245 |   -0.0189 |    -0.0811 |     0.0479 |    0.5566 | False            |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.5852 | 0.5678 |    0.0180 |    -0.0531 |     0.0883 |    0.6132 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.6224 | 0.6370 |   -0.0144 |    -0.0675 |     0.0389 |    0.5930 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.5801 | 0.5678 |    0.0116 |    -0.0545 |     0.0774 |    0.7274 | False            |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.5242 | 0.5351 |   -0.0108 |    -0.0797 |     0.0547 |    0.7506 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.5778 | 0.5678 |    0.0102 |    -0.0574 |     0.0788 |    0.7738 | False            |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.3943 | 0.4058 |   -0.0101 |    -0.0753 |     0.0562 |    0.7678 | False            |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.5852 | 0.5778 |    0.0078 |    -0.0390 |     0.0554 |    0.7488 | False            |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.5852 | 0.5801 |    0.0065 |    -0.0666 |     0.0797 |    0.8590 | False            |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.5778 | 0.5801 |   -0.0013 |    -0.0680 |     0.0671 |    0.9668 | False            |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.6743 | 0.6745 |   -0.0000 |    -0.0308 |     0.0302 |    0.9994 | False            |

## K. Sensibilidade ao limiar de IoU (p43a)

Como as entidades são longas, IoU ≥ 0,5 é permissivo. Span F1 por modelo para IoU ∈ {0,3, 0,5, 0,7} e correspondência exata (1,0):

| display              |    0.3 |    0.5 |    0.7 |   exact |
|:---------------------|-------:|-------:|-------:|--------:|
| BERTimbau-base       | 0.7143 | 0.6786 | 0.6511 |  0.5962 |
| BERTimbau-large      | 0.6170 | 0.6018 | 0.5866 |  0.5410 |
| BERTimbauLaw         | 0.7162 | 0.6844 | 0.6499 |  0.5756 |
| BiLSTM-CRF           | 0.6365 | 0.5926 | 0.5405 |  0.4280 |
| DeepSeek-V4-Flash    | 0.7910 | 0.7527 | 0.7036 |  0.0810 |
| GPT-4.1              | 0.7647 | 0.7216 | 0.6588 |  0.1255 |
| GPT-4.1-mini         | 0.7202 | 0.6851 | 0.6223 |  0.0849 |
| GPT-4.1-nano         | 0.4758 | 0.4325 | 0.3599 |  0.0536 |
| GPT-5-mini           | 0.4289 | 0.4097 | 0.3837 |  0.0711 |
| GPT-5.1              | 0.7213 | 0.6847 | 0.6384 |  0.1813 |
| GPT-5.2              | 0.6517 | 0.6067 | 0.5532 |  0.1504 |
| GovBERT-BR           | 0.5466 | 0.5434 | 0.5205 |  0.4714 |
| JurisBERT            | 0.6658 | 0.6390 | 0.5989 |  0.5107 |
| Legal-BERT-STF       | 0.6675 | 0.6546 | 0.6132 |  0.5485 |
| Legal-BERTimbau-base | 0.6112 | 0.6021 | 0.5779 |  0.5083 |
| LegalBERTPT-br       | 0.5164 | 0.4945 | 0.4664 |  0.4131 |
| LegalBert-pt         | 0.7261 | 0.7003 | 0.6848 |  0.5969 |
| Llama-3.3-70B        | 0.3801 | 0.3396 | 0.2991 |  0.0062 |
| Qwen2.5-72B          | 0.6423 | 0.6135 | 0.5596 |  0.1365 |

**Estabilidade do ranking** (Spearman do ranking de cada limiar vs. IoU = 0,5):

| iou_threshold   |   spearman_vs_0.5 |
|:----------------|------------------:|
| 0.3             |            0.9895 |
| 0.5             |            1.0000 |
| 0.7             |            0.9632 |
| exact           |            0.2982 |

## L. Métrica restrita aos documentos informativos (p41b)

Dos 861 documentos, 629 não têm entidade gold e só contribuem com falsos positivos. Restringindo aos 232 documentos com ≥ 1 entidade, vê-se quanto da precisão vinha do volume de negativos (queda de precisão = inflada pelos vazios):

| model                                                  | display              |   n_docs_full |   n_docs_informative |   span_f1_full |   span_f1_informative |   delta_span_f1 |   span_precision_full |   span_precision_informative |   delta_span_precision |   span_recall_full |   span_recall_informative |
|:-------------------------------------------------------|:---------------------|--------------:|---------------------:|---------------:|----------------------:|----------------:|----------------------:|-----------------------------:|-----------------------:|-------------------:|--------------------------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |           861 |                  232 |         0.7527 |                0.7959 |          0.0433 |                0.7370 |                       0.8248 |                 0.0878 |             0.7691 |                    0.7691 |
| gpt-4.1_few_shot                                       | GPT-4.1              |           861 |                  232 |         0.7216 |                0.7813 |          0.0597 |                0.6560 |                       0.7619 |                 0.1059 |             0.8017 |                    0.8017 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |           861 |                  232 |         0.6851 |                0.7579 |          0.0728 |                0.5946 |                       0.7135 |                 0.1189 |             0.8083 |                    0.8083 |
| gpt-5.1_few_shot                                       | GPT-5.1              |           861 |                  232 |         0.6847 |                0.7497 |          0.0651 |                0.6142 |                       0.7275 |                 0.1133 |             0.7734 |                    0.7734 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |           861 |                  232 |         0.7003 |                0.7179 |          0.0176 |                0.7634 |                       0.8065 |                 0.0432 |             0.6468 |                    0.6468 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |           861 |                  232 |         0.6844 |                0.7011 |          0.0167 |                0.7701 |                       0.8139 |                 0.0437 |             0.6158 |                    0.6158 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |           861 |                  232 |         0.6786 |                0.6890 |          0.0104 |                0.7994 |                       0.8289 |                 0.0295 |             0.5895 |                    0.5895 |
| gpt-5.2_few_shot                                       | GPT-5.2              |           861 |                  232 |         0.6067 |                0.6829 |          0.0761 |                0.5029 |                       0.6169 |                 0.1140 |             0.7647 |                    0.7647 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |           861 |                  232 |         0.6135 |                0.6709 |          0.0574 |                0.5491 |                       0.6484 |                 0.0993 |             0.6950 |                    0.6950 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |           861 |                  232 |         0.6546 |                0.6658 |          0.0112 |                0.7507 |                       0.7809 |                 0.0301 |             0.5803 |                    0.5803 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |           861 |                  232 |         0.6390 |                0.6521 |          0.0131 |                0.7469 |                       0.7836 |                 0.0367 |             0.5584 |                    0.5584 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |           861 |                  232 |         0.6021 |                0.6123 |          0.0102 |                0.8223 |                       0.8615 |                 0.0392 |             0.4749 |                    0.4749 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |           861 |                  232 |         0.6018 |                0.6111 |          0.0093 |                0.8285 |                       0.8646 |                 0.0362 |             0.4726 |                    0.4726 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |           861 |                  232 |         0.5926 |                0.6076 |          0.0150 |                0.7742 |                       0.8276 |                 0.0534 |             0.4800 |                    0.4800 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |           861 |                  232 |         0.4097 |                0.5941 |          0.1844 |                0.2765 |                       0.4758 |                 0.1993 |             0.7908 |                    0.7908 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |           861 |                  232 |         0.5434 |                0.5443 |          0.0009 |                0.8646 |                       0.8691 |                 0.0045 |             0.3962 |                    0.3962 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |           861 |                  232 |         0.4945 |                0.4953 |          0.0008 |                0.7182 |                       0.7215 |                 0.0033 |             0.3771 |                    0.3771 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |           861 |                  232 |         0.4325 |                0.4840 |          0.0515 |                0.3587 |                       0.4355 |                 0.0769 |             0.5447 |                    0.5447 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |           861 |                  232 |         0.3396 |                0.3499 |          0.0104 |                0.5956 |                       0.6646 |                 0.0690 |             0.2375 |                    0.2375 |

## M. Taxa de falha de alinhamento string→offset (p34)

As predições dos LLMs são strings (não offsets); são localizadas no texto-fonte por correspondência difusa (rapidfuzz `partial_ratio`, janela 500 / passo 100 / `min_score` 80). Strings que nenhuma janela casa nesse piso são descartadas silenciosamente na pontuação — a taxa de falha abaixo quantifica quantas predições nunca chegam à métrica:

| model                      | display           |   n_pred_strings |   n_aligned |   n_failed |   failure_rate |
|:---------------------------|:------------------|-----------------:|------------:|-----------:|---------------:|
| gpt-4.1-nano_few_shot      | GPT-4.1-nano      |              707 |         697 |         10 |         0.0141 |
| qwen2.5-72b_few_shot       | Qwen2.5-72B       |              584 |         581 |          3 |         0.0051 |
| gpt-5-mini_few_shot        | GPT-5-mini        |             1315 |        1313 |          2 |         0.0015 |
| gpt-4.1_few_shot           | GPT-4.1           |              561 |         561 |          0 |         0.0000 |
| gpt-4.1-mini_few_shot      | GPT-4.1-mini      |              624 |         624 |          0 |         0.0000 |
| gpt-5.1_few_shot           | GPT-5.1           |              578 |         578 |          0 |         0.0000 |
| gpt-5.2_few_shot           | GPT-5.2           |              698 |         698 |          0 |         0.0000 |
| deepseek-v4-flash_few_shot | DeepSeek-V4-Flash |              479 |         479 |          0 |         0.0000 |
| llama-3.3-70b_few_shot     | Llama-3.3-70B     |              183 |         183 |          0 |         0.0000 |

## Nota — Token F1 do GPT-4-turbo (canônico)
