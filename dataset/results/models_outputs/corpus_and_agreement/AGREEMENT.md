# Concordância entre anotadores

Gerado por `research.release.annotator_agreement` a partir de `dataset/annotators/` (861 documentos comuns aos três anotadores). O anotador 1 é a anotação original pós-auditoria Cleanlab (idêntica à release corrigida); os anotadores 2 e 3 anotaram de forma independente e cega. Os CSVs ao lado são as fontes canônicas.

## (a) Concordância par-a-par

κ de Cohen no nível de token (O + 4 classes, tokenização canônica), F1 de span (IoU ≥ 0,5, matching guloso bipartido — a métrica do protocolo de avaliação) e κ de presença de entidade no documento.

| pair                  |   kappa_token |   obs_agreement_token |   span_precision |   span_recall |   span_f1_micro |   span_f1_macro |   kappa_doc_presence |
|:----------------------|--------------:|----------------------:|-----------------:|--------------:|----------------:|----------------:|---------------------:|
| anotador1 x anotador2 |         0.842 |                 0.945 |            0.760 |         0.791 |           0.776 |           0.714 |                0.787 |
| anotador1 x anotador3 |         0.855 |                 0.949 |            0.765 |         0.812 |           0.788 |           0.716 |                0.817 |
| anotador2 x anotador3 |         0.899 |                 0.966 |            0.830 |         0.847 |           0.838 |           0.812 |                0.918 |

## (b) Concordância global (3 anotadores)

| metric                      |   value |
|:----------------------------|--------:|
| fleiss_kappa_token          |   0.865 |
| mean_pairwise_kappa_token   |   0.865 |
| mean_pairwise_span_f1_micro |   0.801 |
| n_documents                 | 861.000 |

## (c) Concordância por classe

| pair                  | label         |   span_f1 |   kappa_doc_presence |   n_spans_a |   n_spans_b |
|:----------------------|:--------------|----------:|---------------------:|------------:|------------:|
| anotador1 x anotador2 | MULTA         |     0.835 |                0.941 |         212 |         231 |
| anotador1 x anotador2 | OBRIGACAO     |     0.779 |                0.858 |         131 |         118 |
| anotador1 x anotador2 | RESSARCIMENTO |     0.754 |                0.879 |          63 |          59 |
| anotador1 x anotador2 | RECOMENDACAO  |     0.488 |                0.396 |          53 |          33 |
| anotador1 x anotador3 | MULTA         |     0.900 |                0.936 |         212 |         208 |
| anotador1 x anotador3 | OBRIGACAO     |     0.711 |                0.886 |         131 |         125 |
| anotador1 x anotador3 | RESSARCIMENTO |     0.761 |                0.933 |          63 |          71 |
| anotador1 x anotador3 | RECOMENDACAO  |     0.494 |                0.401 |          53 |          28 |
| anotador2 x anotador3 | MULTA         |     0.884 |                0.953 |         231 |         208 |
| anotador2 x anotador3 | OBRIGACAO     |     0.823 |                0.912 |         118 |         125 |
| anotador2 x anotador3 | RESSARCIMENTO |     0.723 |                0.907 |          59 |          71 |
| anotador2 x anotador3 | RECOMENDACAO  |     0.820 |                0.778 |          33 |          28 |

## (d) Tipologia das divergências de span

`agreement`: spans casados (IoU ≥ 0,5) com mesmo rótulo; `class_confusion`: casados com rótulos distintos; `boundary`: mesmo rótulo com sobreposição parcial (0 < IoU < 0,5); `presence_only_*`: span sem contraparte no outro anotador.

| pair                  |   agreement |   class_confusion |   boundary |   presence_only_a |   presence_only_b |
|:----------------------|------------:|------------------:|-----------:|------------------:|------------------:|
| anotador1 x anotador2 |         349 |                 3 |         20 |                87 |                69 |
| anotador1 x anotador3 |         351 |                 4 |         16 |                88 |                61 |
| anotador2 x anotador3 |         366 |                 5 |         15 |                55 |                46 |

### Confusões de classe

| label_a       | label_b       |   n |
|:--------------|:--------------|----:|
| RESSARCIMENTO | MULTA         |   5 |
| MULTA         | RESSARCIMENTO |   5 |
| MULTA         | OBRIGACAO     |   1 |
| OBRIGACAO     | MULTA         |   1 |

## (e) Robustez: anotadores vs. gold pré-correção

Mesmas medidas tomando como referência a anotação original *antes* da auditoria Cleanlab (`decicontas-before-correction`).

| pair                          |   kappa_token |   obs_agreement_token |   span_precision |   span_recall |   span_f1_micro |   span_f1_macro |   kappa_doc_presence |
|:------------------------------|--------------:|----------------------:|-----------------:|--------------:|----------------:|----------------:|---------------------:|
| gold-pre-correcao x anotador1 |         0.979 |                 0.992 |            0.982 |         0.939 |           0.960 |           0.959 |                0.961 |
| gold-pre-correcao x anotador2 |         0.828 |                 0.941 |            0.779 |         0.776 |           0.777 |           0.709 |                0.758 |
| gold-pre-correcao x anotador3 |         0.844 |                 0.946 |            0.786 |         0.799 |           0.792 |           0.716 |                0.789 |
