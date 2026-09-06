# Concordância entre anotadores

Gerado por `research.release.annotator_agreement` a partir de `dataset/annotators/` (861 documentos comuns aos três anotadores). O anotador 1 é a anotação original pós-auditoria Cleanlab (idêntica à release corrigida); os anotadores 2 e 3 anotaram de forma independente e cega. Os CSVs ao lado são as fontes canônicas.

## (a) Concordância par-a-par

κ de Cohen no nível de token (O + 4 classes, tokenização canônica), F1 de span (IoU ≥ 0,5, matching guloso bipartido — a métrica do protocolo de avaliação) e κ de presença de entidade no documento.

| pair                  |   kappa_token |   obs_agreement_token |   span_precision |   span_recall |   span_f1_micro |   span_f1_macro |   kappa_doc_presence |
|:----------------------|--------------:|----------------------:|-----------------:|--------------:|----------------:|----------------:|---------------------:|
| anotador1 x anotador2 |         0.843 |                 0.945 |            0.796 |         0.796 |           0.796 |           0.728 |                0.789 |
| anotador1 x anotador3 |         0.855 |                 0.949 |            0.794 |         0.810 |           0.802 |           0.727 |                0.820 |
| anotador2 x anotador3 |         0.899 |                 0.966 |            0.830 |         0.847 |           0.838 |           0.812 |                0.918 |

## (b) Concordância global (3 anotadores)

| metric                      |   value |
|:----------------------------|--------:|
| fleiss_kappa_token          |   0.865 |
| mean_pairwise_kappa_token   |   0.866 |
| mean_pairwise_span_f1_micro |   0.812 |
| n_documents                 | 861.000 |

## (c) Concordância por classe

| pair                  | label         |   span_f1 |   kappa_doc_presence |   n_spans_a |   n_spans_b |
|:----------------------|:--------------|----------:|---------------------:|------------:|------------:|
| anotador1 x anotador2 | MULTA         |     0.866 |                0.945 |         203 |         231 |
| anotador1 x anotador2 | OBRIGACAO     |     0.797 |                0.858 |         123 |         118 |
| anotador1 x anotador2 | RESSARCIMENTO |     0.754 |                0.879 |          63 |          59 |
| anotador1 x anotador2 | RECOMENDACAO  |     0.494 |                0.402 |          52 |          33 |
| anotador1 x anotador3 | MULTA         |     0.920 |                0.940 |         203 |         208 |
| anotador1 x anotador3 | OBRIGACAO     |     0.726 |                0.886 |         123 |         125 |
| anotador1 x anotador3 | RESSARCIMENTO |     0.761 |                0.933 |          63 |          71 |
| anotador1 x anotador3 | RECOMENDACAO  |     0.500 |                0.407 |          52 |          28 |
| anotador2 x anotador3 | MULTA         |     0.884 |                0.953 |         231 |         208 |
| anotador2 x anotador3 | OBRIGACAO     |     0.823 |                0.912 |         118 |         125 |
| anotador2 x anotador3 | RESSARCIMENTO |     0.723 |                0.907 |          59 |          71 |
| anotador2 x anotador3 | RECOMENDACAO  |     0.820 |                0.778 |          33 |          28 |

## (d) Tipologia das divergências de span

`agreement`: spans casados (IoU ≥ 0,5) com mesmo rótulo; `class_confusion`: casados com rótulos distintos; `boundary`: mesmo rótulo com sobreposição parcial (0 < IoU < 0,5); `presence_only_*`: span sem contraparte no outro anotador.

| pair                  |   agreement |   class_confusion |   boundary |   presence_only_a |   presence_only_b |
|:----------------------|------------:|------------------:|-----------:|------------------:|------------------:|
| anotador1 x anotador2 |         351 |                 4 |         16 |                70 |                70 |
| anotador1 x anotador3 |         350 |                 4 |         18 |                69 |                60 |
| anotador2 x anotador3 |         366 |                 5 |         15 |                55 |                46 |

### Confusões de classe

| label_a       | label_b       |   n |
|:--------------|:--------------|----:|
| MULTA         | RESSARCIMENTO |   6 |
| RESSARCIMENTO | MULTA         |   4 |
| OBRIGACAO     | MULTA         |   2 |
| MULTA         | OBRIGACAO     |   1 |

## (e) Robustez: anotadores vs. gold pré-correção

Mesmas medidas tomando como referência a anotação original *antes* da auditoria Cleanlab (`decicontas-before-correction`).

| pair                          |   kappa_token |   obs_agreement_token |   span_precision |   span_recall |   span_f1_micro |   span_f1_macro |   kappa_doc_presence |
|:------------------------------|--------------:|----------------------:|-----------------:|--------------:|----------------:|----------------:|---------------------:|
| gold-pre-correcao x anotador1 |         0.980 |                 0.993 |            0.984 |         0.980 |           0.982 |           0.976 |                0.958 |
| gold-pre-correcao x anotador2 |         0.828 |                 0.941 |            0.784 |         0.780 |           0.782 |           0.711 |                0.758 |
| gold-pre-correcao x anotador3 |         0.844 |                 0.946 |            0.784 |         0.796 |           0.790 |           0.715 |                0.789 |
