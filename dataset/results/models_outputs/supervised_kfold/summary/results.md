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
| BiLSTM-CRF | 0.5910 ± 0.0518 | 0.7191 ± 0.0956 | `hidden_dim=256, dropout=0.3, lr=0.003` | 0.569, 0.602, 0.562, 0.676, 0.545 |
| BERTimbau-base | 0.6753 ± 0.0475 | 0.7642 ± 0.0475 | `lr=5e-05, warmup_ratio=0.1` | 0.698, 0.704, 0.646, 0.607, 0.722 |
| BERTimbau-large | 0.5712 ± 0.1687 | 0.6514 ± 0.1939 | `lr=2e-05, warmup_ratio=0.1` | 0.286, 0.719, 0.565, 0.639, 0.647 |
| Legal-BERTimbau-base | 0.5885 ± 0.1394 | 0.6679 ± 0.1561 | `lr=5e-05, warmup_ratio=0.1` | 0.356, 0.674, 0.563, 0.698, 0.650 |

### F1 por entidade (média entre folds)
| Modelo | MULTA | OBRIGACAO | RECOMENDACAO | RESSARCIMENTO |
|---|---|---|---|---|
| BiLSTM-CRF | 0.6680 | 0.6914 | 0.1667 | 0.4235 |
| BERTimbau-base | 0.7891 | 0.6779 | 0.2732 | 0.4705 |
| BERTimbau-large | 0.6721 | 0.6332 | 0.2040 | 0.2815 |
| Legal-BERTimbau-base | 0.7507 | 0.5716 | 0.0444 | 0.1679 |

## Grid search dos supervisionados — F1 de span no dev

### BiLSTM-CRF
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `hidden_dim=256, dropout=0.3, lr=0.003` | 0.7134 | 0.8116 | 0.6364 | 0.7668 | **(escolhida)**
| `hidden_dim=128, dropout=0.5, lr=0.003` | 0.7006 | 0.7971 | 0.6250 | 0.7505 |
| `hidden_dim=256, dropout=0.5, lr=0.001` | 0.7000 | 0.7778 | 0.6364 | 0.7418 |
| `hidden_dim=128, dropout=0.5, lr=0.001` | 0.6933 | 0.8387 | 0.5909 | 0.7479 |
| `hidden_dim=256, dropout=0.5, lr=0.003` | 0.6914 | 0.7568 | 0.6364 | 0.8392 |
| `hidden_dim=256, dropout=0.3, lr=0.001` | 0.6232 | 0.8600 | 0.4886 | 0.7215 |
| `hidden_dim=128, dropout=0.3, lr=0.001` | 0.6197 | 0.8148 | 0.5000 | 0.7234 |
| `hidden_dim=128, dropout=0.3, lr=0.003` | 0.5652 | 0.7800 | 0.4432 | 0.7301 |

### BERTimbau-base
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `lr=5e-05, warmup_ratio=0.1` | 0.7808 | 0.9344 | 0.6706 | 0.7745 | **(escolhida)**
| `lr=3e-05, warmup_ratio=0.1` | 0.7286 | 0.9273 | 0.6000 | 0.7269 |
| `lr=5e-05, warmup_ratio=0` | 0.7273 | 0.8966 | 0.6118 | 0.7443 |
| `lr=3e-05, warmup_ratio=0` | 0.7050 | 0.9074 | 0.5765 | 0.7207 |
| `lr=2e-05, warmup_ratio=0` | 0.2828 | 1.0000 | 0.1647 | 0.3441 |
| `lr=2e-05, warmup_ratio=0.1` | 0.2292 | 1.0000 | 0.1294 | 0.3028 |

### BERTimbau-large
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `lr=2e-05, warmup_ratio=0.1` | 0.7838 | 0.9206 | 0.6824 | 0.7934 | **(escolhida)**
| `lr=2e-05, warmup_ratio=0` | 0.7600 | 0.8769 | 0.6706 | 0.7846 |
| `lr=3e-05, warmup_ratio=0.1` | 0.7485 | 0.7821 | 0.7176 | 0.8125 |
| `lr=3e-05, warmup_ratio=0` | 0.7296 | 0.7838 | 0.6824 | 0.7943 |
| `lr=5e-05, warmup_ratio=0.1` | 0.6977 | 0.6897 | 0.7059 | 0.8048 |
| `lr=5e-05, warmup_ratio=0` | 0.6946 | 0.7073 | 0.6824 | 0.7947 |

### Legal-BERTimbau-base
| Configuração | Span F1 dev | Prec | Rec | Token F1 |
|---|---|---|---|---|
| `lr=5e-05, warmup_ratio=0.1` | 0.6522 | 0.8491 | 0.5294 | 0.6839 | **(escolhida)**
| `lr=5e-05, warmup_ratio=0` | 0.3889 | 0.9130 | 0.2471 | 0.4529 |
| `lr=3e-05, warmup_ratio=0.1` | 0.3810 | 1.0000 | 0.2353 | 0.4329 |
| `lr=3e-05, warmup_ratio=0` | 0.0460 | 1.0000 | 0.0235 | 0.0628 |
| `lr=2e-05, warmup_ratio=0` | 0.0233 | 1.0000 | 0.0118 | 0.0319 |
| `lr=2e-05, warmup_ratio=0.1` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Leaderboard unificado — bootstrap CIs (95%)
Todos os modelos (LLMs e supervisionados) avaliados sob o mesmo bootstrap de documento (B=10.000, IoU ≥ 0.5). Para os supervisionados, as predições são as out-of-fold do 5-fold CV — coerentes com a média±dp reportada na seção anterior, mas com IC calculado por reamostragem de documentos.

| Modelo | Span F1 (pontual) | IC 95% | Largura IC |
|---|---|---|---|
| GPT-4 Turbo | 0.7619 | [0.718; 0.802] | 0.0841 |
| GPT-5.4-mini | 0.7614 | [0.716; 0.804] | 0.0887 |
| GPT-5.4-nano | 0.7550 | [0.711; 0.797] | 0.0869 |
| GPT-4o | 0.7515 | [0.706; 0.795] | 0.0888 |
| GPT-4.1-mini | 0.7345 | [0.689; 0.778] | 0.0883 |
| GPT-3.5 | 0.7323 | [0.685; 0.777] | 0.0923 |
| GPT-4.1 | 0.7264 | [0.684; 0.767] | 0.0829 |
| Gemini-2.5-flash | 0.7100 | [0.668; 0.750] | 0.0818 |
| BERTimbau-base | 0.6896 | [0.639; 0.738] | 0.0985 |
| DeepSeek-V3 | 0.6704 | [0.624; 0.714] | 0.0898 |
| Legal-BERTimbau-base | 0.6051 | [0.545; 0.661] | 0.1165 |
| BERTimbau-large | 0.6049 | [0.542; 0.663] | 0.1208 |
| BiLSTM-CRF | 0.5926 | [0.528; 0.656] | 0.1284 |
| GPT-4.1-nano | 0.4409 | [0.395; 0.486] | 0.0910 |

## Comparações pareadas — bootstrap (top 15 por |Δ|)
Diferenças significativas a 5% via bootstrap pareado de documento. Inclui pares LLM-LLM, LLM-supervisionado e supervisionado-supervisionado.

| A | B | Δ F1 | IC 95% (diff) | p-valor | Sig. (5%) |
|---|---|---|---|---|---|
| GPT-4 Turbo | GPT-4.1-nano | +0.3214 | [+0.277; +0.366] | 0.0000 | ✓ |
| GPT-5.4-mini | GPT-4.1-nano | +0.3211 | [+0.275; +0.367] | 0.0000 | ✓ |
| GPT-5.4-nano | GPT-4.1-nano | +0.3146 | [+0.271; +0.358] | 0.0000 | ✓ |
| GPT-4o | GPT-4.1-nano | +0.3111 | [+0.271; +0.353] | 0.0000 | ✓ |
| GPT-4.1-mini | GPT-4.1-nano | +0.2938 | [+0.249; +0.340] | 0.0000 | ✓ |
| GPT-3.5 | GPT-4.1-nano | +0.2917 | [+0.247; +0.337] | 0.0000 | ✓ |
| GPT-4.1 | GPT-4.1-nano | +0.2857 | [+0.243; +0.330] | 0.0000 | ✓ |
| Gemini-2.5-flash | GPT-4.1-nano | +0.2693 | [+0.225; +0.314] | 0.0000 | ✓ |
| BERTimbau-base | GPT-4.1-nano | +0.2487 | [+0.200; +0.297] | 0.0000 | ✓ |
| DeepSeek-V3 | GPT-4.1-nano | +0.2297 | [+0.186; +0.275] | 0.0000 | ✓ |
| GPT-4 Turbo | BiLSTM-CRF | +0.1695 | [+0.103; +0.235] | 0.0000 | ✓ |
| GPT-5.4-mini | BiLSTM-CRF | +0.1692 | [+0.098; +0.240] | 0.0000 | ✓ |
| Legal-BERTimbau-base | GPT-4.1-nano | +0.1640 | [+0.107; +0.220] | 0.0000 | ✓ |
| BERTimbau-large | GPT-4.1-nano | +0.1636 | [+0.103; +0.222] | 0.0000 | ✓ |
| GPT-5.4-nano | BiLSTM-CRF | +0.1626 | [+0.094; +0.231] | 0.0000 | ✓ |

## Notas para a redação
- Os modelos supervisionados (BiLSTM/BERT) foram fine-tunados nos 861 documentos via 5-fold CV; LLMs foram avaliadas em regime few-shot. A comparação mede paradigmas, não modelos sob "mesmas condições".
- O F1 de span usa correspondência IoU ≥ 0.5 com tokenização spaCy comum a todos os modelos — diferenças de ranking entre modelos vêm da qualidade de extração, não de variação de protocolo de avaliação.
- Para os supervisionados, a média ± dp entre folds quantifica variância entre splits; para LLMs, o IC bootstrap quantifica variância entre documentos.
