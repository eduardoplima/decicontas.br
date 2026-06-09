# Resultados consolidados — decicontas.br
Briefing pronto para consumo por uma LLM redatora do capítulo de Resultados. Cobre os modelos supervisionados (5-fold CV após grid search) e as LLMs (bootstrap pareado de documento), todos avaliados sobre os mesmos 861 documentos.

## Setup do experimento
- Dataset: 861 documentos (866 rotulados originais menos 5 IDs `[6, 782, 790, 817, 852]` excluídos por aparecerem como exemplos few-shot no prompt das LLMs).
- Métrica primária: F1 de **span** com IoU ≥ 0.5, calculada via tokenização spaCy `pt_core_news_sm` (mesmo pipeline `tools.ner_metrics.calculate_metrics` em todos os modelos).
- Random seed: **1007** (todos os splits, shuffles e inits).
- Supervisionados: protocolo em duas etapas — grid search em split fixo 80/20 (estratificado por presença de anotação) seguido de 5-fold CV com a config vencedora.
- LLMs: zero/few-shot (12 exemplos no prompt), avaliados via bootstrap de documento (B=10.000, IoU ≥ 0.5).

## Modelos supervisionados — 5-fold CV
| Modelo | Span F1 (média ± dp) | Token F1 (média ± dp) | Configuração escolhida | Folds |
|---|---|---|---|---|
| BiLSTM-CRF | 0.7190 ± 0.0720 | 0.8018 ± 0.0349 | `hidden_dim=256, dropout=0.5, lr=0.003` | 0.704, 0.802, 0.615, 0.769, 0.705 |
| BERTimbau-base | 0.6899 ± 0.1148 | 0.7369 ± 0.1175 | `lr=5e-05, warmup_ratio=0` | 0.500, 0.761, 0.699, 0.797, 0.692 |
| BERTimbau-large | 0.6509 ± 0.0841 | 0.6996 ± 0.0826 | `lr=5e-05, warmup_ratio=0.1` | 0.566, 0.583, 0.678, 0.776, 0.651 |
| Legal-BERTimbau-base | 0.6159 ± 0.0964 | 0.6757 ± 0.1073 | `lr=5e-05, warmup_ratio=0` | 0.552, 0.727, 0.700, 0.500, 0.600 |

### F1 por entidade (média entre folds)
| Modelo | MULTA | OBRIGACAO | RECOMENDACAO | RESSARCIMENTO |
|---|---|---|---|---|
| BiLSTM-CRF | 0.7949 | 0.7202 | 0.5377 | 0.6409 |
| BERTimbau-base | 0.8073 | 0.6894 | 0.4824 | 0.4954 |
| BERTimbau-large | 0.7748 | 0.6760 | 0.3061 | 0.4299 |
| Legal-BERTimbau-base | 0.7960 | 0.5804 | 0.2088 | 0.2483 |

## Grid search dos supervisionados — F1 de span no dev

### BiLSTM-CRF
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `hidden_dim=256, dropout=0.5, lr=0.003` | 0.7250 | 0.7838 | 0.6744 | 0.8166 | **(escolhida)**
| `hidden_dim=256, dropout=0.5, lr=0.001` | 0.7215 | 0.7917 | 0.6628 | 0.7429 |
| `hidden_dim=128, dropout=0.5, lr=0.003` | 0.7044 | 0.7671 | 0.6512 | 0.8344 |
| `hidden_dim=128, dropout=0.5, lr=0.001` | 0.6846 | 0.8095 | 0.5930 | 0.7359 |
| `hidden_dim=128, dropout=0.3, lr=0.001` | 0.6842 | 0.7879 | 0.6047 | 0.7747 |
| `hidden_dim=256, dropout=0.3, lr=0.003` | 0.6575 | 0.8000 | 0.5581 | 0.8229 |
| `hidden_dim=256, dropout=0.3, lr=0.001` | 0.6351 | 0.7581 | 0.5465 | 0.7482 |
| `hidden_dim=128, dropout=0.3, lr=0.003` | 0.6061 | 0.8696 | 0.4651 | 0.6853 |

### BERTimbau-base
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `lr=5e-05, warmup_ratio=0` | 0.7808 | 0.9344 | 0.6706 | 0.7660 | **(escolhida)**
| `lr=5e-05, warmup_ratio=0.1` | 0.6622 | 0.7778 | 0.5765 | 0.7337 |
| `lr=3e-05, warmup_ratio=0` | 0.5938 | 0.8837 | 0.4471 | 0.6659 |
| `lr=2e-05, warmup_ratio=0.1` | 0.5333 | 0.9143 | 0.3765 | 0.5984 |
| `lr=3e-05, warmup_ratio=0.1` | 0.3925 | 0.9545 | 0.2471 | 0.4611 |
| `lr=2e-05, warmup_ratio=0` | 0.3000 | 1.0000 | 0.1765 | 0.3889 |

### BERTimbau-large
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `lr=5e-05, warmup_ratio=0.1` | 0.7547 | 0.8108 | 0.7059 | 0.7869 | **(escolhida)**
| `lr=3e-05, warmup_ratio=0.1` | 0.7059 | 0.7059 | 0.7059 | 0.8045 |
| `lr=3e-05, warmup_ratio=0` | 0.6761 | 0.8421 | 0.5647 | 0.7334 |
| `lr=5e-05, warmup_ratio=0` | 0.6753 | 0.7536 | 0.6118 | 0.7484 |
| `lr=2e-05, warmup_ratio=0` | 0.6486 | 0.7619 | 0.5647 | 0.7273 |
| `lr=2e-05, warmup_ratio=0.1` | 0.5938 | 0.8837 | 0.4471 | 0.6329 |

### Legal-BERTimbau-base
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `lr=5e-05, warmup_ratio=0` | 0.6763 | 0.8704 | 0.5529 | 0.7118 | **(escolhida)**
| `lr=3e-05, warmup_ratio=0` | 0.3462 | 0.9474 | 0.2118 | 0.4251 |
| `lr=2e-05, warmup_ratio=0` | 0.2474 | 1.0000 | 0.1412 | 0.3359 |
| `lr=2e-05, warmup_ratio=0.1` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `lr=3e-05, warmup_ratio=0.1` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `lr=5e-05, warmup_ratio=0.1` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Leaderboard unificado — bootstrap CIs (95%)
Todos os modelos (LLMs e supervisionados) avaliados sob o mesmo bootstrap de documento (B=10.000, IoU ≥ 0.5). Para os supervisionados, as predições são as out-of-fold do 5-fold CV — coerentes com a média±dp reportada na seção anterior, mas com IC calculado por reamostragem de documentos.

| Modelo | Span F1 (pontual) | IC 95% | Largura IC |
|---|---|---|---|
| GPT-4 Turbo | 0.7737 | [0.733; 0.812] | 0.0790 |
| GPT-5.4-mini | 0.7689 | [0.725; 0.810] | 0.0858 |
| GPT-5.4-nano | 0.7623 | [0.719; 0.803] | 0.0834 |
| GPT-4o | 0.7611 | [0.717; 0.802] | 0.0843 |
| GPT-4.1-mini | 0.7437 | [0.700; 0.784] | 0.0845 |
| GPT-3.5 | 0.7376 | [0.691; 0.780] | 0.0886 |
| GPT-4.1 | 0.7333 | [0.691; 0.772] | 0.0807 |
| BiLSTM-CRF | 0.7257 | [0.678; 0.771] | 0.0927 |
| Gemini-2.5-flash | 0.7141 | [0.673; 0.752] | 0.0791 |
| BERTimbau-base | 0.7080 | [0.658; 0.754] | 0.0964 |
| DeepSeek-V3 | 0.6756 | [0.630; 0.719] | 0.0889 |
| BERTimbau-large | 0.6542 | [0.599; 0.707] | 0.1085 |
| Legal-BERTimbau-base | 0.6388 | [0.585; 0.689] | 0.1045 |
| GPT-4.1-nano | 0.4494 | [0.403; 0.494] | 0.0903 |

## Comparações pareadas — bootstrap (top 15 por |Δ|)
Diferenças significativas a 5% via bootstrap pareado de documento. Inclui pares LLM-LLM, LLM-supervisionado e supervisionado-supervisionado.

| A | B | Δ F1 | IC 95% (diff) | p-valor | Sig. (5%) |
|---|---|---|---|---|---|
| GPT-4 Turbo | GPT-4.1-nano | +0.3246 | [+0.281; +0.369] | 0.0000 | ✓ |
| GPT-5.4-mini | GPT-4.1-nano | +0.3199 | [+0.274; +0.366] | 0.0000 | ✓ |
| GPT-5.4-nano | GPT-4.1-nano | +0.3131 | [+0.270; +0.358] | 0.0000 | ✓ |
| GPT-4o | GPT-4.1-nano | +0.3120 | [+0.271; +0.354] | 0.0000 | ✓ |
| GPT-4.1-mini | GPT-4.1-nano | +0.2944 | [+0.249; +0.340] | 0.0000 | ✓ |
| GPT-3.5 | GPT-4.1-nano | +0.2883 | [+0.244; +0.333] | 0.0000 | ✓ |
| GPT-4.1 | GPT-4.1-nano | +0.2840 | [+0.241; +0.329] | 0.0000 | ✓ |
| BiLSTM-CRF | GPT-4.1-nano | +0.2764 | [+0.223; +0.331] | 0.0000 | ✓ |
| Gemini-2.5-flash | GPT-4.1-nano | +0.2648 | [+0.220; +0.310] | 0.0000 | ✓ |
| BERTimbau-base | GPT-4.1-nano | +0.2585 | [+0.210; +0.308] | 0.0000 | ✓ |
| DeepSeek-V3 | GPT-4.1-nano | +0.2263 | [+0.181; +0.272] | 0.0000 | ✓ |
| BERTimbau-large | GPT-4.1-nano | +0.2047 | [+0.148; +0.260] | 0.0000 | ✓ |
| Legal-BERTimbau-base | GPT-4.1-nano | +0.1893 | [+0.134; +0.245] | 0.0000 | ✓ |
| GPT-4 Turbo | Legal-BERTimbau-base | +0.1352 | [+0.083; +0.188] | 0.0000 | ✓ |
| GPT-5.4-mini | Legal-BERTimbau-base | +0.1306 | [+0.075; +0.186] | 0.0000 | ✓ |

## Notas para a redação
- Os modelos supervisionados (BiLSTM/BERT) foram fine-tunados nos 861 documentos via 5-fold CV; LLMs foram avaliadas em regime few-shot. A comparação mede paradigmas, não modelos sob "mesmas condições".
- O F1 de span usa correspondência IoU ≥ 0.5 com tokenização spaCy comum a todos os modelos — diferenças de ranking entre modelos vêm da qualidade de extração, não de variação de protocolo de avaliação.
- Para os supervisionados, a média ± dp entre folds quantifica variância entre splits; para LLMs, o IC bootstrap quantifica variância entre documentos.
