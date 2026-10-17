# Concordância entre anotadores

Gerado por `research.release.annotator_agreement` a partir de `dataset/annotators/` (861 documentos comuns aos três anotadores). O anotador 1 é a anotação original pós-auditoria Cleanlab (idêntica à release corrigida); os anotadores 2 e 3 anotaram de forma independente e cega. Os CSVs ao lado são as fontes canônicas.

## (a) Concordância par-a-par

κ de Cohen no nível de token (O + 4 classes, tokenização canônica), F1 de span (IoU ≥ 0,5, matching guloso bipartido — a métrica do protocolo de avaliação) e κ de presença de entidade no documento.

| pair                  |   kappa_token |   obs_agreement_token |   span_precision |   span_recall |   span_f1_micro |   span_f1_macro |   kappa_doc_presence |
|:----------------------|--------------:|----------------------:|-----------------:|--------------:|----------------:|----------------:|---------------------:|
| anotador1 x anotador2 |         0.864 |                 0.954 |            0.854 |         0.796 |           0.824 |           0.795 |                0.872 |
| anotador1 x anotador3 |         0.875 |                 0.957 |            0.849 |         0.808 |           0.828 |           0.792 |                0.898 |
| anotador2 x anotador3 |         0.899 |                 0.966 |            0.830 |         0.847 |           0.838 |           0.812 |                0.918 |

## (b) Concordância global (3 anotadores)

| metric                      |   value |
|:----------------------------|--------:|
| fleiss_kappa_token          |   0.879 |
| mean_pairwise_kappa_token   |   0.879 |
| mean_pairwise_span_f1_micro |   0.830 |
| n_documents                 | 861.000 |

## (c) Concordância por classe

| pair                  | label         |   span_f1 |   kappa_doc_presence |   n_spans_a |   n_spans_b |
|:----------------------|:--------------|----------:|---------------------:|------------:|------------:|
| anotador1 x anotador2 | MULTA         |     0.866 |                0.945 |         203 |         231 |
| anotador1 x anotador2 | OBRIGACAO     |     0.797 |                0.858 |         123 |         118 |
| anotador1 x anotador2 | RESSARCIMENTO |     0.754 |                0.879 |          63 |          59 |
| anotador1 x anotador2 | RECOMENDACAO  |     0.764 |                0.704 |          22 |          33 |
| anotador1 x anotador3 | MULTA         |     0.920 |                0.940 |         203 |         208 |
| anotador1 x anotador3 | OBRIGACAO     |     0.726 |                0.886 |         123 |         125 |
| anotador1 x anotador3 | RESSARCIMENTO |     0.761 |                0.933 |          63 |          71 |
| anotador1 x anotador3 | RECOMENDACAO  |     0.760 |                0.693 |          22 |          28 |
| anotador2 x anotador3 | MULTA         |     0.884 |                0.953 |         231 |         208 |
| anotador2 x anotador3 | OBRIGACAO     |     0.823 |                0.912 |         118 |         125 |
| anotador2 x anotador3 | RESSARCIMENTO |     0.723 |                0.907 |          59 |          71 |
| anotador2 x anotador3 | RECOMENDACAO  |     0.820 |                0.778 |          33 |          28 |

## (d) Tipologia das divergências de span

`agreement`: spans casados (IoU ≥ 0,5) com mesmo rótulo; `class_confusion`: casados com rótulos distintos; `boundary`: mesmo rótulo com sobreposição parcial (0 < IoU < 0,5); `presence_only_*`: span sem contraparte no outro anotador.

| pair                  |   agreement |   class_confusion |   boundary |   presence_only_a |   presence_only_b |
|:----------------------|------------:|------------------:|-----------:|------------------:|------------------:|
| anotador1 x anotador2 |         351 |                 4 |         16 |                40 |                70 |
| anotador1 x anotador3 |         349 |                 4 |         18 |                40 |                61 |
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
| gold-pre-correcao x anotador1 |         0.983 |                 0.994 |            0.995 |         0.978 |           0.987 |           0.984 |                0.967 |
| gold-pre-correcao x anotador2 |         0.853 |                 0.950 |            0.851 |         0.780 |           0.814 |           0.784 |                0.851 |
| gold-pre-correcao x anotador3 |         0.866 |                 0.954 |            0.849 |         0.794 |           0.821 |           0.790 |                0.877 |
