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
| Pares significativos a 5% (de 91)  | 61.0000 | 130.0000 | 69.0000 |
| Menor Δ detectável (significativo) |  0.0337 |   0.0309 | -0.0028 |

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

| model                                                  | display              |   span_f1_point |   span_f1_mean |   span_f1_std |   ci_lower |   ci_upper |   ci_width |
|:-------------------------------------------------------|:---------------------|----------------:|---------------:|--------------:|-----------:|-----------:|-----------:|
| deepseek-v4-flash_few_shot                             | DeepSeek-V4-Flash    |          0.7527 |         0.7528 |        0.0229 |     0.7079 |     0.7970 |     0.0891 |
| gpt-4.1_few_shot                                       | GPT-4.1              |          0.7216 |         0.7219 |        0.0225 |     0.6778 |     0.7661 |     0.0883 |
| raquelsilveira_legalbertpt_fp__supervised              | LegalBert-pt         |          0.7003 |         0.7001 |        0.0258 |     0.6492 |     0.7496 |     0.1004 |
| gpt-4.1-mini_few_shot                                  | GPT-4.1-mini         |          0.6851 |         0.6853 |        0.0212 |     0.6433 |     0.7265 |     0.0832 |
| gpt-5.1_few_shot                                       | GPT-5.1              |          0.6847 |         0.6847 |        0.0222 |     0.6405 |     0.7276 |     0.0871 |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbauLaw         |          0.6844 |         0.6842 |        0.0259 |     0.6317 |     0.7334 |     0.1017 |
| neuralmind_bert-base-portuguese-cased__supervised      | BERTimbau-base       |          0.6786 |         0.6783 |        0.0273 |     0.6243 |     0.7300 |     0.1057 |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERT-STF       |          0.6546 |         0.6547 |        0.0284 |     0.5984 |     0.7094 |     0.1109 |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | JurisBERT            |          0.6390 |         0.6389 |        0.0292 |     0.5795 |     0.6951 |     0.1156 |
| qwen2.5-72b_few_shot                                   | Qwen2.5-72B          |          0.6135 |         0.6137 |        0.0217 |     0.5703 |     0.6561 |     0.0858 |
| gpt-5.2_few_shot                                       | GPT-5.2              |          0.6067 |         0.6068 |        0.0215 |     0.5635 |     0.6478 |     0.0843 |
| rufimelo_Legal-BERTimbau-base__supervised              | Legal-BERTimbau-base |          0.6021 |         0.6016 |        0.0303 |     0.5410 |     0.6593 |     0.1183 |
| neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-large      |          0.6018 |         0.6012 |        0.0314 |     0.5383 |     0.6616 |     0.1232 |
| bilstm-crf__supervised                                 | BiLSTM-CRF           |          0.5926 |         0.5925 |        0.0329 |     0.5269 |     0.6569 |     0.1300 |
| dccmpmgfinalisticas_GovBERT-BR__supervised             | GovBERT-BR           |          0.5434 |         0.5429 |        0.0327 |     0.4784 |     0.6056 |     0.1272 |
| ulysses-camara_legal-bert-pt-br__supervised            | LegalBERTPT-br       |          0.4945 |         0.4940 |        0.0320 |     0.4293 |     0.5554 |     0.1261 |
| gpt-4.1-nano_few_shot                                  | GPT-4.1-nano         |          0.4325 |         0.4325 |        0.0239 |     0.3853 |     0.4792 |     0.0939 |
| gpt-5-mini_few_shot                                    | GPT-5-mini           |          0.4097 |         0.4094 |        0.0176 |     0.3746 |     0.4431 |     0.0685 |
| llama-3.3-70b_few_shot                                 | Llama-3.3-70B        |          0.3396 |         0.3397 |        0.0325 |     0.2764 |     0.4045 |     0.1281 |

**Itens 43–46 — Pares destacados:**

| model_a                                           | model_b                                                | display_a         | display_b         |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |   p_holm |   p_bonferroni | sig_holm_5pct   | sig_bonferroni_5pct   |   family_size |
|:--------------------------------------------------|:-------------------------------------------------------|:------------------|:------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|---------:|---------------:|:----------------|:----------------------|--------------:|
| deepseek-v4-flash_few_shot                        | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash | Llama-3.3-70B     | 0.7527 | 0.3396 |    0.4131 |     0.3506 |     0.4754 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| llama-3.3-70b_few_shot                            | qwen2.5-72b_few_shot                                   | Llama-3.3-70B     | Qwen2.5-72B       | 0.3396 | 0.6135 |   -0.2740 |    -0.3410 |    -0.2053 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-5.2           | Llama-3.3-70B     | 0.6067 | 0.3396 |    0.2671 |     0.1969 |     0.3361 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1-mini_few_shot                             | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini      | GPT-4.1-nano      | 0.6851 | 0.4325 |    0.2528 |     0.2050 |     0.2992 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-5.2           | DeepSeek-V4-Flash | 0.6067 | 0.7527 |   -0.1461 |    -0.1884 |    -0.1020 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-4.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1           | GPT-5.2           | 0.7216 | 0.6067 |    0.1151 |     0.0810 |     0.1500 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2           | LegalBert-pt      | 0.6067 | 0.7003 |   -0.0933 |    -0.1417 |    -0.0451 |    0.0008 | True             |   0.0080 |         0.0136 | True            | True                  |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | bilstm-crf__supervised                                 | BERTimbau-base    | BiLSTM-CRF        | 0.6786 | 0.5926 |    0.0857 |     0.0304 |     0.1438 |    0.0020 | True             |   0.0180 |         0.0340 | True            | True                  |            17 |
| gpt-5.1_few_shot                                  | gpt-5.2_few_shot                                       | GPT-5.1           | GPT-5.2           | 0.6847 | 0.6067 |    0.0779 |     0.0460 |     0.1104 |    0.0000 | True             |   0.0000 |         0.0000 | True            | True                  |            17 |
| deepseek-v4-flash_few_shot                        | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash | BERTimbau-base    | 0.7527 | 0.6786 |    0.0746 |     0.0268 |     0.1222 |    0.0024 | True             |   0.0180 |         0.0408 | True            | True                  |            17 |
| gpt-5.2_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2           | BERTimbau-base    | 0.6067 | 0.6786 |   -0.0715 |    -0.1174 |    -0.0240 |    0.0036 | True             |   0.0216 |         0.0612 | True            | False                 |            17 |
| deepseek-v4-flash_few_shot                        | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash | LegalBert-pt      | 0.7527 | 0.7003 |    0.0527 |     0.0051 |     0.0998 |    0.0294 | True             |   0.1470 |         0.4998 | False           | False                 |            17 |
| gpt-4.1_few_shot                                  | gpt-4.1-mini_few_shot                                  | GPT-4.1           | GPT-4.1-mini      | 0.7216 | 0.6851 |    0.0366 |     0.0130 |     0.0619 |    0.0020 | True             |   0.0180 |         0.0340 | True            | True                  |            17 |
| gpt-4.1_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1           | DeepSeek-V4-Flash | 0.7216 | 0.7527 |   -0.0309 |    -0.0616 |    -0.0027 |    0.0298 | True             |   0.1470 |         0.5066 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base    | LegalBert-pt      | 0.6786 | 0.7003 |   -0.0218 |    -0.0567 |     0.0126 |    0.2150 | False            |   0.6450 |         1.0000 | False           | False                 |            17 |
| gpt-5.2_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-5.2           | Qwen2.5-72B       | 0.6067 | 0.6135 |   -0.0069 |    -0.0478 |     0.0341 |    0.7308 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |
| neuralmind_bert-base-portuguese-cased__supervised | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base    | BERTimbauLaw      | 0.6786 | 0.6844 |   -0.0059 |    -0.0392 |     0.0271 |    0.7300 | False            |   1.0000 |         1.0000 | False           | False                 |            17 |

**Itens 47–48 — Resumo:**

| metric                         | value                        |
|:-------------------------------|:-----------------------------|
| resampling_unit                | document                     |
| n_docs_resampled               | 861                          |
| n_total_pairs                  | 171                          |
| n_significant_5pct_uncorrected | 130                          |
| highlighted_family_size        | 17                           |
| highlighted_n_sig_uncorrected  | 14                           |
| highlighted_n_sig_holm         | 12                           |
| highlighted_n_sig_bonferroni   | 11                           |
| smallest_significant_abs_diff  | 0.030910809459704303         |
| smallest_significant_pair      | GPT-4.1 vs DeepSeek-V4-Flash |

**p48a — Correção para múltiplas comparações.** A família reportada são os pares destacados acima; `p_holm`/`p_bonferroni` controlam o erro familiar (FWER) e `sig_holm_5pct` substitui a coluna 'Sig.' não corrigida da Tabela 13. Diferenças marginais tendem a não sobreviver, reforçando a leitura de saturação.

**Tabela completa dos 91 pares (ordenada por |Δ|):**

| model_a                                                | model_b                                                | display_a            | display_b            |   f1_a |   f1_b |   diff_f1 |   ci_lower |   ci_upper |   p_value | significant_95   |
|:-------------------------------------------------------|:-------------------------------------------------------|:---------------------|:---------------------|-------:|-------:|----------:|-----------:|-----------:|----------:|:-----------------|
| deepseek-v4-flash_few_shot                             | llama-3.3-70b_few_shot                                 | DeepSeek-V4-Flash    | Llama-3.3-70B        | 0.7527 | 0.3396 |    0.4131 |     0.3506 |     0.4754 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-4.1              | Llama-3.3-70B        | 0.7216 | 0.3396 |    0.3822 |     0.3162 |     0.4465 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | raquelsilveira_legalbertpt_fp__supervised              | Llama-3.3-70B        | LegalBert-pt         | 0.3396 | 0.7003 |   -0.3604 |    -0.4265 |    -0.2939 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-mini         | Llama-3.3-70B        | 0.6851 | 0.3396 |    0.3456 |     0.2790 |     0.4108 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.1              | Llama-3.3-70B        | 0.6847 | 0.3396 |    0.3450 |     0.2772 |     0.4101 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Llama-3.3-70B        | BERTimbauLaw         | 0.3396 | 0.6844 |   -0.3445 |    -0.4122 |    -0.2772 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | deepseek-v4-flash_few_shot                             | GPT-5-mini           | DeepSeek-V4-Flash    | 0.4097 | 0.7527 |   -0.3434 |    -0.3890 |    -0.3004 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-base-portuguese-cased__supervised      | Llama-3.3-70B        | BERTimbau-base       | 0.3396 | 0.6786 |   -0.3385 |    -0.4049 |    -0.2706 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-nano         | DeepSeek-V4-Flash    | 0.4325 | 0.7527 |   -0.3203 |    -0.3705 |    -0.2674 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | Llama-3.3-70B        | Legal-BERT-STF       | 0.3396 | 0.6546 |   -0.3150 |    -0.3823 |    -0.2461 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-5-mini_few_shot                                    | GPT-4.1              | GPT-5-mini           | 0.7216 | 0.4097 |    0.3125 |     0.2695 |     0.3568 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Llama-3.3-70B        | JurisBERT            | 0.3396 | 0.6390 |   -0.2992 |    -0.3672 |    -0.2284 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | raquelsilveira_legalbertpt_fp__supervised              | GPT-5-mini           | LegalBert-pt         | 0.4097 | 0.7003 |   -0.2907 |    -0.3457 |    -0.2375 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | gpt-4.1-nano_few_shot                                  | GPT-4.1              | GPT-4.1-nano         | 0.7216 | 0.4325 |    0.2894 |     0.2408 |     0.3349 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-mini         | GPT-5-mini           | 0.6851 | 0.4097 |    0.2759 |     0.2370 |     0.3156 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.1_few_shot                                       | GPT-5-mini           | GPT-5.1              | 0.4097 | 0.6847 |   -0.2753 |    -0.3180 |    -0.2337 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5-mini           | BERTimbauLaw         | 0.4097 | 0.6844 |   -0.2748 |    -0.3276 |    -0.2221 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | qwen2.5-72b_few_shot                                   | Llama-3.3-70B        | Qwen2.5-72B          | 0.3396 | 0.6135 |   -0.2740 |    -0.3410 |    -0.2053 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5-mini           | BERTimbau-base       | 0.4097 | 0.6786 |   -0.2688 |    -0.3261 |    -0.2122 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-nano         | LegalBert-pt         | 0.4325 | 0.7003 |   -0.2676 |    -0.3200 |    -0.2160 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | llama-3.3-70b_few_shot                                 | GPT-5.2              | Llama-3.3-70B        | 0.6067 | 0.3396 |    0.2671 |     0.1969 |     0.3361 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | rufimelo_Legal-BERTimbau-base__supervised              | Llama-3.3-70B        | Legal-BERTimbau-base | 0.3396 | 0.6021 |   -0.2619 |    -0.3289 |    -0.1944 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | neuralmind_bert-large-portuguese-cased__supervised     | Llama-3.3-70B        | BERTimbau-large      | 0.3396 | 0.6018 |   -0.2615 |    -0.3298 |    -0.1916 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | ulysses-camara_legal-bert-pt-br__supervised            | DeepSeek-V4-Flash    | LegalBERTPT-br       | 0.7527 | 0.4945 |    0.2589 |     0.1974 |     0.3212 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | bilstm-crf__supervised                                 | Llama-3.3-70B        | BiLSTM-CRF           | 0.3396 | 0.5926 |   -0.2528 |    -0.3200 |    -0.1843 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-4.1-nano_few_shot                                  | GPT-4.1-mini         | GPT-4.1-nano         | 0.6851 | 0.4325 |    0.2528 |     0.2050 |     0.2992 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-nano         | GPT-5.1              | 0.4325 | 0.6847 |   -0.2522 |    -0.3005 |    -0.2024 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-nano         | BERTimbauLaw         | 0.4325 | 0.6844 |   -0.2516 |    -0.3045 |    -0.1980 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-nano         | BERTimbau-base       | 0.4325 | 0.6786 |   -0.2457 |    -0.3004 |    -0.1903 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5-mini           | Legal-BERT-STF       | 0.4097 | 0.6546 |   -0.2453 |    -0.3034 |    -0.1876 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5-mini           | JurisBERT            | 0.4097 | 0.6390 |   -0.2295 |    -0.2885 |    -0.1705 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1              | LegalBERTPT-br       | 0.7216 | 0.4945 |    0.2279 |     0.1675 |     0.2899 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-nano         | Legal-BERT-STF       | 0.4325 | 0.6546 |   -0.2221 |    -0.2776 |    -0.1671 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dccmpmgfinalisticas_GovBERT-BR__supervised             | DeepSeek-V4-Flash    | GovBERT-BR           | 0.7527 | 0.5434 |    0.2100 |     0.1463 |     0.2743 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-nano         | JurisBERT            | 0.4325 | 0.6390 |   -0.2064 |    -0.2641 |    -0.1469 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | LegalBert-pt         | LegalBERTPT-br       | 0.7003 | 0.4945 |    0.2061 |     0.1529 |     0.2615 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | qwen2.5-72b_few_shot                                   | GPT-5-mini           | Qwen2.5-72B          | 0.4097 | 0.6135 |   -0.2043 |    -0.2483 |    -0.1596 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | Llama-3.3-70B        | GovBERT-BR           | 0.3396 | 0.5434 |   -0.2032 |    -0.2743 |    -0.1307 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | gpt-5.2_few_shot                                       | GPT-5-mini           | GPT-5.2              | 0.4097 | 0.6067 |   -0.1974 |    -0.2365 |    -0.1587 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5-mini           | Legal-BERTimbau-base | 0.4097 | 0.6021 |   -0.1922 |    -0.2519 |    -0.1315 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5-mini           | BERTimbau-large      | 0.4097 | 0.6018 |   -0.1918 |    -0.2553 |    -0.1275 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-mini         | LegalBERTPT-br       | 0.6851 | 0.4945 |    0.1913 |     0.1327 |     0.2520 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.1              | LegalBERTPT-br       | 0.6847 | 0.4945 |    0.1907 |     0.1297 |     0.2527 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbauLaw         | LegalBERTPT-br       | 0.6844 | 0.4945 |    0.1902 |     0.1390 |     0.2447 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-base       | LegalBERTPT-br       | 0.6786 | 0.4945 |    0.1843 |     0.1344 |     0.2356 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | bilstm-crf__supervised                                 | GPT-5-mini           | BiLSTM-CRF           | 0.4097 | 0.5926 |   -0.1831 |    -0.2533 |    -0.1140 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-nano         | Qwen2.5-72B          | 0.4325 | 0.6135 |   -0.1812 |    -0.2263 |    -0.1346 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1              | GovBERT-BR           | 0.7216 | 0.5434 |    0.1790 |     0.1179 |     0.2408 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-nano         | GPT-5.2              | 0.4325 | 0.6067 |   -0.1742 |    -0.2177 |    -0.1302 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-nano         | Legal-BERTimbau-base | 0.4325 | 0.6021 |   -0.1691 |    -0.2259 |    -0.1111 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-nano         | BERTimbau-large      | 0.4325 | 0.6018 |   -0.1687 |    -0.2292 |    -0.1084 |    0.0000 | True             |
| ulysses-camara_legal-bert-pt-br__supervised            | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBERTPT-br       | Legal-BERT-STF       | 0.4945 | 0.6546 |   -0.1607 |    -0.2164 |    -0.1076 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | bilstm-crf__supervised                                 | DeepSeek-V4-Flash    | BiLSTM-CRF           | 0.7527 | 0.5926 |    0.1603 |     0.0954 |     0.2249 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-nano         | BiLSTM-CRF           | 0.4325 | 0.5926 |   -0.1600 |    -0.2291 |    -0.0921 |    0.0000 | True             |
| raquelsilveira_legalbertpt_fp__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBert-pt         | GovBERT-BR           | 0.7003 | 0.5434 |    0.1572 |     0.1026 |     0.2141 |    0.0000 | True             |
| llama-3.3-70b_few_shot                                 | ulysses-camara_legal-bert-pt-br__supervised            | Llama-3.3-70B        | LegalBERTPT-br       | 0.3396 | 0.4945 |   -0.1543 |    -0.2294 |    -0.0770 |    0.0002 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-large-portuguese-cased__supervised     | DeepSeek-V4-Flash    | BERTimbau-large      | 0.7527 | 0.6018 |    0.1516 |     0.0952 |     0.2098 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | rufimelo_Legal-BERTimbau-base__supervised              | DeepSeek-V4-Flash    | Legal-BERTimbau-base | 0.7527 | 0.6021 |    0.1512 |     0.0973 |     0.2069 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.2              | DeepSeek-V4-Flash    | 0.6067 | 0.7527 |   -0.1461 |    -0.1884 |    -0.1020 |    0.0000 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | ulysses-camara_legal-bert-pt-br__supervised            | JurisBERT            | LegalBERTPT-br       | 0.6390 | 0.4945 |    0.1450 |     0.0897 |     0.2010 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-mini         | GovBERT-BR           | 0.6851 | 0.5434 |    0.1424 |     0.0826 |     0.2029 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.1              | GovBERT-BR           | 0.6847 | 0.5434 |    0.1418 |     0.0796 |     0.2050 |    0.0000 | True             |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbauLaw         | GovBERT-BR           | 0.6844 | 0.5434 |    0.1413 |     0.0903 |     0.1951 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | qwen2.5-72b_few_shot                                   | DeepSeek-V4-Flash    | Qwen2.5-72B          | 0.7527 | 0.6135 |    0.1391 |     0.0971 |     0.1820 |    0.0000 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-base       | GovBERT-BR           | 0.6786 | 0.5434 |    0.1354 |     0.0855 |     0.1879 |    0.0000 | True             |
| gpt-5-mini_few_shot                                    | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5-mini           | GovBERT-BR           | 0.4097 | 0.5434 |   -0.1335 |    -0.2036 |    -0.0639 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-4.1              | BiLSTM-CRF           | 0.7216 | 0.5926 |    0.1294 |     0.0669 |     0.1915 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1              | BERTimbau-large      | 0.7216 | 0.6018 |    0.1207 |     0.0657 |     0.1785 |    0.0000 | True             |
| gpt-4.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1              | Legal-BERTimbau-base | 0.7216 | 0.6021 |    0.1203 |     0.0652 |     0.1778 |    0.0002 | True             |
| qwen2.5-72b_few_shot                                   | ulysses-camara_legal-bert-pt-br__supervised            | Qwen2.5-72B          | LegalBERTPT-br       | 0.6135 | 0.4945 |    0.1197 |     0.0582 |     0.1826 |    0.0004 | True             |
| gpt-4.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-4.1              | GPT-5.2              | 0.7216 | 0.6067 |    0.1151 |     0.0810 |     0.1500 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | alfaneo_jurisbert-base-portuguese-uncased__supervised  | DeepSeek-V4-Flash    | JurisBERT            | 0.7527 | 0.6390 |    0.1139 |     0.0603 |     0.1686 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5.2              | LegalBERTPT-br       | 0.6067 | 0.4945 |    0.1128 |     0.0519 |     0.1743 |    0.0006 | True             |
| dominguesm_legal-bert-base-cased-ptbr__supervised      | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERT-STF       | GovBERT-BR           | 0.6546 | 0.5434 |    0.1118 |     0.0594 |     0.1668 |    0.0000 | True             |
| gpt-4.1-nano_few_shot                                  | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-4.1-nano         | GovBERT-BR           | 0.4325 | 0.5434 |   -0.1103 |    -0.1710 |    -0.0490 |    0.0010 | True             |
| gpt-4.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-4.1              | Qwen2.5-72B          | 0.7216 | 0.6135 |    0.1082 |     0.0649 |     0.1515 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | ulysses-camara_legal-bert-pt-br__supervised            | Legal-BERTimbau-base | LegalBERTPT-br       | 0.6021 | 0.4945 |    0.1076 |     0.0540 |     0.1629 |    0.0000 | True             |
| bilstm-crf__supervised                                 | raquelsilveira_legalbertpt_fp__supervised              | BiLSTM-CRF           | LegalBert-pt         | 0.5926 | 0.7003 |   -0.1076 |    -0.1655 |    -0.0504 |    0.0000 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | ulysses-camara_legal-bert-pt-br__supervised            | BERTimbau-large      | LegalBERTPT-br       | 0.6018 | 0.4945 |    0.1072 |     0.0507 |     0.1644 |    0.0008 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-large      | LegalBert-pt         | 0.6018 | 0.7003 |   -0.0989 |    -0.1474 |    -0.0532 |    0.0000 | True             |
| bilstm-crf__supervised                                 | ulysses-camara_legal-bert-pt-br__supervised            | BiLSTM-CRF           | LegalBERTPT-br       | 0.5926 | 0.4945 |    0.0986 |     0.0305 |     0.1689 |    0.0032 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | raquelsilveira_legalbertpt_fp__supervised              | Legal-BERTimbau-base | LegalBert-pt         | 0.6021 | 0.7003 |   -0.0985 |    -0.1445 |    -0.0555 |    0.0000 | True             |
| deepseek-v4-flash_few_shot                             | dominguesm_legal-bert-base-cased-ptbr__supervised      | DeepSeek-V4-Flash    | Legal-BERT-STF       | 0.7527 | 0.6546 |    0.0982 |     0.0455 |     0.1504 |    0.0004 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dccmpmgfinalisticas_GovBERT-BR__supervised             | JurisBERT            | GovBERT-BR           | 0.6390 | 0.5434 |    0.0961 |     0.0425 |     0.1522 |    0.0002 | True             |
| gpt-5.2_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.2              | LegalBert-pt         | 0.6067 | 0.7003 |   -0.0933 |    -0.1417 |    -0.0451 |    0.0008 | True             |
| gpt-4.1-nano_few_shot                                  | llama-3.3-70b_few_shot                                 | GPT-4.1-nano         | Llama-3.3-70B        | 0.4325 | 0.3396 |    0.0928 |     0.0231 |     0.1616 |    0.0082 | True             |
| gpt-4.1-mini_few_shot                                  | bilstm-crf__supervised                                 | GPT-4.1-mini         | BiLSTM-CRF           | 0.6851 | 0.5926 |    0.0928 |     0.0301 |     0.1535 |    0.0032 | True             |
| gpt-5.1_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.1              | BiLSTM-CRF           | 0.6847 | 0.5926 |    0.0922 |     0.0285 |     0.1562 |    0.0040 | True             |
| bilstm-crf__supervised                                 | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BiLSTM-CRF           | BERTimbauLaw         | 0.5926 | 0.6844 |   -0.0917 |    -0.1480 |    -0.0366 |    0.0004 | True             |
| qwen2.5-72b_few_shot                                   | raquelsilveira_legalbertpt_fp__supervised              | Qwen2.5-72B          | LegalBert-pt         | 0.6135 | 0.7003 |   -0.0864 |    -0.1390 |    -0.0341 |    0.0010 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | bilstm-crf__supervised                                 | BERTimbau-base       | BiLSTM-CRF           | 0.6786 | 0.5926 |    0.0857 |     0.0304 |     0.1438 |    0.0020 | True             |
| gpt-5-mini_few_shot                                    | ulysses-camara_legal-bert-pt-br__supervised            | GPT-5-mini           | LegalBERTPT-br       | 0.4097 | 0.4945 |   -0.0846 |    -0.1495 |    -0.0202 |    0.0106 | True             |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-large-portuguese-cased__supervised     | GPT-4.1-mini         | BERTimbau-large      | 0.6851 | 0.6018 |    0.0841 |     0.0312 |     0.1389 |    0.0014 | True             |
| gpt-4.1-mini_few_shot                                  | rufimelo_Legal-BERTimbau-base__supervised              | GPT-4.1-mini         | Legal-BERTimbau-base | 0.6851 | 0.6021 |    0.0837 |     0.0315 |     0.1375 |    0.0022 | True             |
| gpt-5.1_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.1              | BERTimbau-large      | 0.6847 | 0.6018 |    0.0835 |     0.0283 |     0.1407 |    0.0022 | True             |
| gpt-5.1_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.1              | Legal-BERTimbau-base | 0.6847 | 0.6021 |    0.0831 |     0.0258 |     0.1416 |    0.0064 | True             |
| gpt-4.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1              | JurisBERT            | 0.7216 | 0.6390 |    0.0830 |     0.0302 |     0.1360 |    0.0026 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-large      | BERTimbauLaw         | 0.6018 | 0.6844 |   -0.0830 |    -0.1273 |    -0.0419 |    0.0000 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Legal-BERTimbau-base | BERTimbauLaw         | 0.6021 | 0.6844 |   -0.0826 |    -0.1242 |    -0.0420 |    0.0000 | True             |
| gpt-4.1-mini_few_shot                                  | gpt-5.2_few_shot                                       | GPT-4.1-mini         | GPT-5.2              | 0.6851 | 0.6067 |    0.0785 |     0.0485 |     0.1099 |    0.0000 | True             |
| gpt-5.1_few_shot                                       | gpt-5.2_few_shot                                       | GPT-5.1              | GPT-5.2              | 0.6847 | 0.6067 |    0.0779 |     0.0460 |     0.1104 |    0.0000 | True             |
| gpt-5.2_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.2              | BERTimbauLaw         | 0.6067 | 0.6844 |   -0.0774 |    -0.1245 |    -0.0289 |    0.0016 | True             |
| neuralmind_bert-base-portuguese-cased__supervised      | neuralmind_bert-large-portuguese-cased__supervised     | BERTimbau-base       | BERTimbau-large      | 0.6786 | 0.6018 |    0.0770 |     0.0352 |     0.1214 |    0.0002 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-base-portuguese-cased__supervised      | Legal-BERTimbau-base | BERTimbau-base       | 0.6021 | 0.6786 |   -0.0766 |    -0.1175 |    -0.0375 |    0.0002 | True             |
| deepseek-v4-flash_few_shot                             | neuralmind_bert-base-portuguese-cased__supervised      | DeepSeek-V4-Flash    | BERTimbau-base       | 0.7527 | 0.6786 |    0.0746 |     0.0268 |     0.1222 |    0.0024 | True             |
| gpt-4.1-mini_few_shot                                  | qwen2.5-72b_few_shot                                   | GPT-4.1-mini         | Qwen2.5-72B          | 0.6851 | 0.6135 |    0.0716 |     0.0323 |     0.1108 |    0.0004 | True             |
| gpt-5.2_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.2              | BERTimbau-base       | 0.6067 | 0.6786 |   -0.0715 |    -0.1174 |    -0.0240 |    0.0036 | True             |
| gpt-5.1_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.1              | Qwen2.5-72B          | 0.6847 | 0.6135 |    0.0710 |     0.0268 |     0.1144 |    0.0026 | True             |
| qwen2.5-72b_few_shot                                   | dccmpmgfinalisticas_GovBERT-BR__supervised             | Qwen2.5-72B          | GovBERT-BR           | 0.6135 | 0.5434 |    0.0708 |     0.0060 |     0.1377 |    0.0312 | True             |
| qwen2.5-72b_few_shot                                   | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | Qwen2.5-72B          | BERTimbauLaw         | 0.6135 | 0.6844 |   -0.0705 |    -0.1231 |    -0.0170 |    0.0080 | True             |
| gpt-5-mini_few_shot                                    | llama-3.3-70b_few_shot                                 | GPT-5-mini           | Llama-3.3-70B        | 0.4097 | 0.3396 |    0.0697 |    -0.0043 |     0.1424 |    0.0646 | False            |
| deepseek-v4-flash_few_shot                             | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | DeepSeek-V4-Flash    | BERTimbauLaw         | 0.7527 | 0.6844 |    0.0687 |     0.0205 |     0.1176 |    0.0046 | True             |
| gpt-5.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-5.1              | DeepSeek-V4-Flash    | 0.6847 | 0.7527 |   -0.0681 |    -0.1053 |    -0.0313 |    0.0008 | True             |
| gpt-4.1-mini_few_shot                                  | deepseek-v4-flash_few_shot                             | GPT-4.1-mini         | DeepSeek-V4-Flash    | 0.6851 | 0.7527 |   -0.0675 |    -0.1012 |    -0.0347 |    0.0004 | True             |
| gpt-4.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1              | Legal-BERT-STF       | 0.7216 | 0.6546 |    0.0672 |     0.0128 |     0.1210 |    0.0174 | True             |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-base-portuguese-cased__supervised      | Qwen2.5-72B          | BERTimbau-base       | 0.6135 | 0.6786 |   -0.0645 |    -0.1163 |    -0.0128 |    0.0150 | True             |
| gpt-5.2_few_shot                                       | dccmpmgfinalisticas_GovBERT-BR__supervised             | GPT-5.2              | GovBERT-BR           | 0.6067 | 0.5434 |    0.0639 |     0.0021 |     0.1257 |    0.0430 | True             |
| bilstm-crf__supervised                                 | dominguesm_legal-bert-base-cased-ptbr__supervised      | BiLSTM-CRF           | Legal-BERT-STF       | 0.5926 | 0.6546 |   -0.0621 |    -0.1147 |    -0.0090 |    0.0228 | True             |
| gpt-4.1-nano_few_shot                                  | ulysses-camara_legal-bert-pt-br__supervised            | GPT-4.1-nano         | LegalBERTPT-br       | 0.4325 | 0.4945 |   -0.0614 |    -0.1213 |    -0.0001 |    0.0500 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | raquelsilveira_legalbertpt_fp__supervised              | JurisBERT            | LegalBert-pt         | 0.6390 | 0.7003 |   -0.0611 |    -0.1067 |    -0.0170 |    0.0068 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | dccmpmgfinalisticas_GovBERT-BR__supervised             | Legal-BERTimbau-base | GovBERT-BR           | 0.6021 | 0.5434 |    0.0587 |     0.0059 |     0.1150 |    0.0290 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dccmpmgfinalisticas_GovBERT-BR__supervised             | BERTimbau-large      | GovBERT-BR           | 0.6018 | 0.5434 |    0.0583 |     0.0136 |     0.1061 |    0.0070 | True             |
| neuralmind_bert-large-portuguese-cased__supervised     | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-large      | Legal-BERT-STF       | 0.6018 | 0.6546 |   -0.0535 |    -0.1034 |    -0.0053 |    0.0286 | True             |
| rufimelo_Legal-BERTimbau-base__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | Legal-BERTimbau-base | Legal-BERT-STF       | 0.6021 | 0.6546 |   -0.0531 |    -0.0918 |    -0.0154 |    0.0054 | True             |
| deepseek-v4-flash_few_shot                             | raquelsilveira_legalbertpt_fp__supervised              | DeepSeek-V4-Flash    | LegalBert-pt         | 0.7527 | 0.7003 |    0.0527 |     0.0051 |     0.0998 |    0.0294 | True             |
| bilstm-crf__supervised                                 | dccmpmgfinalisticas_GovBERT-BR__supervised             | BiLSTM-CRF           | GovBERT-BR           | 0.5926 | 0.5434 |    0.0497 |    -0.0145 |     0.1158 |    0.1390 | False            |
| ulysses-camara_legal-bert-pt-br__supervised            | dccmpmgfinalisticas_GovBERT-BR__supervised             | LegalBERTPT-br       | GovBERT-BR           | 0.4945 | 0.5434 |   -0.0489 |    -0.0943 |    -0.0024 |    0.0398 | True             |
| gpt-5.2_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.2              | Legal-BERT-STF       | 0.6067 | 0.6546 |   -0.0479 |    -0.0998 |     0.0042 |    0.0682 | False            |
| bilstm-crf__supervised                                 | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BiLSTM-CRF           | JurisBERT            | 0.5926 | 0.6390 |   -0.0464 |    -0.0995 |     0.0041 |    0.0710 | False            |
| gpt-4.1-mini_few_shot                                  | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-4.1-mini         | JurisBERT            | 0.6851 | 0.6390 |    0.0464 |    -0.0047 |     0.0976 |    0.0712 | False            |
| gpt-5.1_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.1              | JurisBERT            | 0.6847 | 0.6390 |    0.0457 |    -0.0060 |     0.0980 |    0.0826 | False            |
| raquelsilveira_legalbertpt_fp__supervised              | dominguesm_legal-bert-base-cased-ptbr__supervised      | LegalBert-pt         | Legal-BERT-STF       | 0.7003 | 0.6546 |    0.0454 |     0.0031 |     0.0884 |    0.0332 | True             |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | JurisBERT            | BERTimbauLaw         | 0.6390 | 0.6844 |   -0.0452 |    -0.0793 |    -0.0114 |    0.0090 | True             |
| gpt-4.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1              | BERTimbau-base       | 0.7216 | 0.6786 |    0.0437 |    -0.0008 |     0.0896 |    0.0544 | False            |
| qwen2.5-72b_few_shot                                   | dominguesm_legal-bert-base-cased-ptbr__supervised      | Qwen2.5-72B          | Legal-BERT-STF       | 0.6135 | 0.6546 |   -0.0410 |    -0.0970 |     0.0146 |    0.1546 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-base       | JurisBERT            | 0.6786 | 0.6390 |    0.0393 |    -0.0023 |     0.0815 |    0.0626 | False            |
| gpt-4.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1              | BERTimbauLaw         | 0.7216 | 0.6844 |    0.0377 |    -0.0082 |     0.0856 |    0.1126 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | alfaneo_jurisbert-base-portuguese-uncased__supervised  | BERTimbau-large      | JurisBERT            | 0.6018 | 0.6390 |   -0.0377 |    -0.0832 |     0.0060 |    0.0928 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Legal-BERTimbau-base | JurisBERT            | 0.6021 | 0.6390 |   -0.0373 |    -0.0803 |     0.0060 |    0.0892 | False            |
| gpt-4.1_few_shot                                       | gpt-5.1_few_shot                                       | GPT-4.1              | GPT-5.1              | 0.7216 | 0.6847 |    0.0372 |     0.0083 |     0.0667 |    0.0082 | True             |
| gpt-4.1_few_shot                                       | gpt-4.1-mini_few_shot                                  | GPT-4.1              | GPT-4.1-mini         | 0.7216 | 0.6851 |    0.0366 |     0.0130 |     0.0619 |    0.0020 | True             |
| gpt-5.2_few_shot                                       | alfaneo_jurisbert-base-portuguese-uncased__supervised  | GPT-5.2              | JurisBERT            | 0.6067 | 0.6390 |   -0.0322 |    -0.0849 |     0.0224 |    0.2386 | False            |
| gpt-4.1_few_shot                                       | deepseek-v4-flash_few_shot                             | GPT-4.1              | DeepSeek-V4-Flash    | 0.7216 | 0.7527 |   -0.0309 |    -0.0616 |    -0.0027 |    0.0298 | True             |
| gpt-4.1-mini_few_shot                                  | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-4.1-mini         | Legal-BERT-STF       | 0.6851 | 0.6546 |    0.0306 |    -0.0228 |     0.0831 |    0.2520 | False            |
| gpt-5.1_few_shot                                       | dominguesm_legal-bert-base-cased-ptbr__supervised      | GPT-5.1              | Legal-BERT-STF       | 0.6847 | 0.6546 |    0.0300 |    -0.0249 |     0.0833 |    0.2716 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbauLaw         | Legal-BERT-STF       | 0.6844 | 0.6546 |    0.0295 |    -0.0083 |     0.0685 |    0.1282 | False            |
| qwen2.5-72b_few_shot                                   | alfaneo_jurisbert-base-portuguese-uncased__supervised  | Qwen2.5-72B          | JurisBERT            | 0.6135 | 0.6390 |   -0.0252 |    -0.0824 |     0.0332 |    0.3940 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | dominguesm_legal-bert-base-cased-ptbr__supervised      | BERTimbau-base       | Legal-BERT-STF       | 0.6786 | 0.6546 |    0.0236 |    -0.0163 |     0.0628 |    0.2406 | False            |
| gpt-4.1-nano_few_shot                                  | gpt-5-mini_few_shot                                    | GPT-4.1-nano         | GPT-5-mini           | 0.4325 | 0.4097 |    0.0231 |    -0.0269 |     0.0735 |    0.3602 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | raquelsilveira_legalbertpt_fp__supervised              | BERTimbau-base       | LegalBert-pt         | 0.6786 | 0.7003 |   -0.0218 |    -0.0567 |     0.0126 |    0.2150 | False            |
| gpt-4.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1              | LegalBert-pt         | 0.7216 | 0.7003 |    0.0218 |    -0.0235 |     0.0670 |    0.3482 | False            |
| qwen2.5-72b_few_shot                                   | bilstm-crf__supervised                                 | Qwen2.5-72B          | BiLSTM-CRF           | 0.6135 | 0.5926 |    0.0212 |    -0.0479 |     0.0909 |    0.5464 | False            |
| alfaneo_bertimbaulaw-base-portuguese-cased__supervised | raquelsilveira_legalbertpt_fp__supervised              | BERTimbauLaw         | LegalBert-pt         | 0.6844 | 0.7003 |   -0.0159 |    -0.0523 |     0.0202 |    0.3966 | False            |
| alfaneo_jurisbert-base-portuguese-uncased__supervised  | dominguesm_legal-bert-base-cased-ptbr__supervised      | JurisBERT            | Legal-BERT-STF       | 0.6390 | 0.6546 |   -0.0157 |    -0.0571 |     0.0249 |    0.4530 | False            |
| gpt-5.1_few_shot                                       | raquelsilveira_legalbertpt_fp__supervised              | GPT-5.1              | LegalBert-pt         | 0.6847 | 0.7003 |   -0.0154 |    -0.0621 |     0.0313 |    0.5150 | False            |
| gpt-4.1-mini_few_shot                                  | raquelsilveira_legalbertpt_fp__supervised              | GPT-4.1-mini         | LegalBert-pt         | 0.6851 | 0.7003 |   -0.0148 |    -0.0593 |     0.0303 |    0.5180 | False            |
| gpt-5.2_few_shot                                       | bilstm-crf__supervised                                 | GPT-5.2              | BiLSTM-CRF           | 0.6067 | 0.5926 |    0.0142 |    -0.0507 |     0.0786 |    0.6680 | False            |
| qwen2.5-72b_few_shot                                   | neuralmind_bert-large-portuguese-cased__supervised     | Qwen2.5-72B          | BERTimbau-large      | 0.6135 | 0.6018 |    0.0125 |    -0.0512 |     0.0779 |    0.7014 | False            |
| qwen2.5-72b_few_shot                                   | rufimelo_Legal-BERTimbau-base__supervised              | Qwen2.5-72B          | Legal-BERTimbau-base | 0.6135 | 0.6021 |    0.0121 |    -0.0465 |     0.0711 |    0.6876 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | bilstm-crf__supervised                                 | Legal-BERTimbau-base | BiLSTM-CRF           | 0.6021 | 0.5926 |    0.0091 |    -0.0485 |     0.0673 |    0.7680 | False            |
| neuralmind_bert-large-portuguese-cased__supervised     | bilstm-crf__supervised                                 | BERTimbau-large      | BiLSTM-CRF           | 0.6018 | 0.5926 |    0.0087 |    -0.0493 |     0.0671 |    0.7856 | False            |
| gpt-4.1-mini_few_shot                                  | neuralmind_bert-base-portuguese-cased__supervised      | GPT-4.1-mini         | BERTimbau-base       | 0.6851 | 0.6786 |    0.0071 |    -0.0368 |     0.0512 |    0.7662 | False            |
| gpt-5.2_few_shot                                       | qwen2.5-72b_few_shot                                   | GPT-5.2              | Qwen2.5-72B          | 0.6067 | 0.6135 |   -0.0069 |    -0.0478 |     0.0341 |    0.7308 | False            |
| gpt-5.1_few_shot                                       | neuralmind_bert-base-portuguese-cased__supervised      | GPT-5.1              | BERTimbau-base       | 0.6847 | 0.6786 |    0.0064 |    -0.0409 |     0.0538 |    0.7944 | False            |
| neuralmind_bert-base-portuguese-cased__supervised      | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | BERTimbau-base       | BERTimbauLaw         | 0.6786 | 0.6844 |   -0.0059 |    -0.0392 |     0.0271 |    0.7300 | False            |
| gpt-5.2_few_shot                                       | neuralmind_bert-large-portuguese-cased__supervised     | GPT-5.2              | BERTimbau-large      | 0.6067 | 0.6018 |    0.0056 |    -0.0502 |     0.0632 |    0.8608 | False            |
| gpt-5.2_few_shot                                       | rufimelo_Legal-BERTimbau-base__supervised              | GPT-5.2              | Legal-BERTimbau-base | 0.6067 | 0.6021 |    0.0052 |    -0.0498 |     0.0609 |    0.8628 | False            |
| gpt-4.1-mini_few_shot                                  | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-4.1-mini         | BERTimbauLaw         | 0.6851 | 0.6844 |    0.0011 |    -0.0430 |     0.0471 |    0.9714 | False            |
| gpt-4.1-mini_few_shot                                  | gpt-5.1_few_shot                                       | GPT-4.1-mini         | GPT-5.1              | 0.6851 | 0.6847 |    0.0006 |    -0.0246 |     0.0263 |    0.9568 | False            |
| gpt-5.1_few_shot                                       | alfaneo_bertimbaulaw-base-portuguese-cased__supervised | GPT-5.1              | BERTimbauLaw         | 0.6847 | 0.6844 |    0.0005 |    -0.0473 |     0.0489 |    0.9826 | False            |
| rufimelo_Legal-BERTimbau-base__supervised              | neuralmind_bert-large-portuguese-cased__supervised     | Legal-BERTimbau-base | BERTimbau-large      | 0.6021 | 0.6018 |    0.0004 |    -0.0401 |     0.0430 |    0.9960 | False            |

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
