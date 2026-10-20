# Análise descritiva e linguística do corpus

Gerado por `research.release.corpus_analysis` a partir de `dataset/release/decicontas/decicontas.json` (release corrigida, 861 docs). Os CSVs ao lado são as fontes canônicas.

## (a) Entidades por documento (DS-p.42)

| n_entities   |   n_docs |   pct_all_docs |   pct_informative_docs |
|:-------------|---------:|---------------:|-----------------------:|
| 0            |      638 |         0.7410 |               nan      |
| 1            |      106 |         0.1231 |                 0.4753 |
| 2            |       80 |         0.0929 |                 0.3587 |
| 3+           |       37 |         0.0430 |                 0.1659 |

## (b) Coocorrência de classes no mesmo documento

| label         |   MULTA |   OBRIGACAO |   RESSARCIMENTO |   RECOMENDACAO |
|:--------------|--------:|------------:|----------------:|---------------:|
| MULTA         |     144 |          59 |              38 |              6 |
| OBRIGACAO     |      59 |         100 |               2 |              4 |
| RESSARCIMENTO |      38 |           2 |              59 |              3 |
| RECOMENDACAO  |       6 |           4 |               3 |             27 |

## (c) Posição relativa dos spans no documento

Aproximação declarada para dispositivo × fundamentação: sem segmentação estrutural, usa-se a posição relativa do centro do span (`center_rel` ∈ [0, 1]); `frac_in_final_third` é a fração de spans no terço final do texto.

| label         |   count |   mean |   median |    q25 |    q75 |   frac_in_final_third |
|:--------------|--------:|-------:|---------:|-------:|-------:|----------------------:|
| MULTA         |     209 | 0.5338 |   0.4981 | 0.3776 | 0.6930 |                0.2679 |
| OBRIGACAO     |     122 | 0.6750 |   0.7185 | 0.6183 | 0.7475 |                0.7295 |
| RESSARCIMENTO |      66 | 0.6154 |   0.5777 | 0.4571 | 0.7906 |                0.4242 |
| RECOMENDACAO  |      32 | 0.6367 |   0.6657 | 0.4736 | 0.7810 |                0.4688 |

## (d) N-gramas iniciais dos spans por classe

| label         |   n | ngram                   |   count |   pct_of_spans |
|:--------------|----:|:------------------------|--------:|---------------:|
| MULTA         |   1 | multa                   |     162 |         0.7751 |
| MULTA         |   1 | multas:                 |       2 |         0.0096 |
| MULTA         |   1 | ao                      |       2 |         0.0096 |
| MULTA         |   1 | 1.multa                 |       2 |         0.0096 |
| MULTA         |   1 | valor                   |       2 |         0.0096 |
| MULTA         |   1 | 06                      |       1 |         0.0048 |
| MULTA         |   1 | carlo                   |       1 |         0.0048 |
| MULTA         |   1 | joel                    |       1 |         0.0048 |
| MULTA         |   1 | condenando              |       1 |         0.0048 |
| MULTA         |   1 | osvaldo                 |       1 |         0.0048 |
| MULTA         |   1 | obdulia                 |       1 |         0.0048 |
| MULTA         |   1 | heloisa                 |       1 |         0.0048 |
| MULTA         |   1 | clécio                  |       1 |         0.0048 |
| MULTA         |   1 | alonso                  |       1 |         0.0048 |
| MULTA         |   1 | reynaldo                |       1 |         0.0048 |
| MULTA         |   2 | multa no                |     117 |         0.5598 |
| MULTA         |   2 | multa de                |      15 |         0.0718 |
| MULTA         |   2 | multa ao                |      10 |         0.0478 |
| MULTA         |   2 | multa equivalente       |       7 |         0.0335 |
| MULTA         |   2 | multa na                |       4 |         0.0191 |
| MULTA         |   2 | multa à                 |       2 |         0.0096 |
| MULTA         |   2 | ao sr.                  |       2 |         0.0096 |
| MULTA         |   2 | multa em                |       2 |         0.0096 |
| MULTA         |   2 | 1.multa no              |       2 |         0.0096 |
| MULTA         |   2 | valor de                |       2 |         0.0096 |
| MULTA         |   2 | 06 multas               |       1 |         0.0048 |
| MULTA         |   2 | carlo ruiz              |       1 |         0.0048 |
| MULTA         |   2 | joel benigno            |       1 |         0.0048 |
| MULTA         |   2 | condenando a            |       1 |         0.0048 |
| MULTA         |   2 | osvaldo reynaldo        |       1 |         0.0048 |
| OBRIGACAO     |   1 | determinação            |      68 |         0.5574 |
| OBRIGACAO     |   1 | determinar              |      10 |         0.0820 |
| OBRIGACAO     |   1 | notificação             |       7 |         0.0574 |
| OBRIGACAO     |   1 | prazo                   |       6 |         0.0492 |
| OBRIGACAO     |   1 | determinando            |       4 |         0.0328 |
| OBRIGACAO     |   1 | com                     |       4 |         0.0328 |
| OBRIGACAO     |   1 | fixação                 |       3 |         0.0246 |
| OBRIGACAO     |   1 | deve,                   |       2 |         0.0164 |
| OBRIGACAO     |   1 | galo                    |       2 |         0.0164 |
| OBRIGACAO     |   1 | medida                  |       2 |         0.0164 |
| OBRIGACAO     |   1 | determinada             |       1 |         0.0082 |
| OBRIGACAO     |   1 | o                       |       1 |         0.0082 |
| OBRIGACAO     |   1 | adote                   |       1 |         0.0082 |
| OBRIGACAO     |   1 | 30                      |       1 |         0.0082 |
| OBRIGACAO     |   1 | determinado             |       1 |         0.0082 |
| OBRIGACAO     |   2 | determinação constante  |      48 |         0.3934 |
| OBRIGACAO     |   2 | determinação ao         |      13 |         0.1066 |
| OBRIGACAO     |   2 | determinar a            |       6 |         0.0492 |
| OBRIGACAO     |   2 | prazo de                |       6 |         0.0492 |
| OBRIGACAO     |   2 | notificação ao          |       5 |         0.0410 |
| OBRIGACAO     |   2 | com assinatura          |       4 |         0.0328 |
| OBRIGACAO     |   2 | fixação de              |       3 |         0.0246 |
| OBRIGACAO     |   2 | determinação à          |       3 |         0.0246 |
| OBRIGACAO     |   2 | deve, ainda,            |       2 |         0.0164 |
| OBRIGACAO     |   2 | galo chelo              |       2 |         0.0164 |
| OBRIGACAO     |   2 | medida de               |       2 |         0.0164 |
| OBRIGACAO     |   2 | determinação para,      |       2 |         0.0164 |
| OBRIGACAO     |   2 | notificação do          |       2 |         0.0164 |
| OBRIGACAO     |   2 | determinar aos          |       2 |         0.0164 |
| OBRIGACAO     |   2 | determinando que,       |       2 |         0.0164 |
| RESSARCIMENTO |   1 | ressarcimento           |      50 |         0.7576 |
| RESSARCIMENTO |   1 | ressarcir               |      11 |         0.1667 |
| RESSARCIMENTO |   1 | imputação               |       1 |         0.0152 |
| RESSARCIMENTO |   1 | chelo                   |       1 |         0.0152 |
| RESSARCIMENTO |   1 | devolução               |       1 |         0.0152 |
| RESSARCIMENTO |   1 | restituição             |       1 |         0.0152 |
| RESSARCIMENTO |   1 | ressarcimentos          |       1 |         0.0152 |
| RESSARCIMENTO |   2 | ressarcimento ao        |      32 |         0.4848 |
| RESSARCIMENTO |   2 | ressarcir ao            |       8 |         0.1212 |
| RESSARCIMENTO |   2 | ressarcimento da        |       4 |         0.0606 |
| RESSARCIMENTO |   2 | ressarcimento aos       |       3 |         0.0455 |
| RESSARCIMENTO |   2 | ressarcimento do        |       2 |         0.0303 |
| RESSARCIMENTO |   2 | ressarcimento no        |       2 |         0.0303 |
| RESSARCIMENTO |   2 | ressarcimento dos       |       2 |         0.0303 |
| RESSARCIMENTO |   2 | imputação de            |       1 |         0.0152 |
| RESSARCIMENTO |   2 | chelo fuster            |       1 |         0.0152 |
| RESSARCIMENTO |   2 | ressarcir aos           |       1 |         0.0152 |
| RESSARCIMENTO |   2 | ressarcir integralmente |       1 |         0.0152 |
| RESSARCIMENTO |   2 | ressarcimento em        |       1 |         0.0152 |
| RESSARCIMENTO |   2 | ressarcir a             |       1 |         0.0152 |
| RESSARCIMENTO |   2 | devolução ao            |       1 |         0.0152 |
| RESSARCIMENTO |   2 | restituição aos         |       1 |         0.0152 |
| RECOMENDACAO  |   1 | recomendação            |      19 |         0.5938 |
| RECOMENDACAO  |   1 | recomendar              |       7 |         0.2188 |
| RECOMENDACAO  |   1 | decide                  |       2 |         0.0625 |
| RECOMENDACAO  |   1 | decide-se               |       1 |         0.0312 |
| RECOMENDACAO  |   1 | como                    |       1 |         0.0312 |
| RECOMENDACAO  |   1 | intimação               |       1 |         0.0312 |
| RECOMENDACAO  |   1 | corpo                   |       1 |         0.0312 |
| RECOMENDACAO  |   2 | recomendação à          |       7 |         0.2188 |
| RECOMENDACAO  |   2 | recomendação ao         |       6 |         0.1875 |
| RECOMENDACAO  |   2 | recomendar ao           |       5 |         0.1562 |
| RECOMENDACAO  |   2 | recomendação de         |       2 |         0.0625 |
| RECOMENDACAO  |   2 | recomendação para       |       2 |         0.0625 |
| RECOMENDACAO  |   2 | recomendar à            |       2 |         0.0625 |
| RECOMENDACAO  |   2 | decide-se ainda         |       1 |         0.0312 |
| RECOMENDACAO  |   2 | recomendação aos        |       1 |         0.0312 |
| RECOMENDACAO  |   2 | como também             |       1 |         0.0312 |
| RECOMENDACAO  |   2 | decide recomendar       |       1 |         0.0312 |
| RECOMENDACAO  |   2 | decide também           |       1 |         0.0312 |
| RECOMENDACAO  |   2 | intimação da            |       1 |         0.0312 |
| RECOMENDACAO  |   2 | recomendação que,       |       1 |         0.0312 |
| RECOMENDACAO  |   2 | corpo de                |       1 |         0.0312 |

## (d') Verbos/marcadores performativos

Radicais buscados nos 5 primeiros tokens do span (colunas `*_rate` = fração dos spans da classe) e no documento inteiro (`doc_rate`).

| stem     |   docs_with_stem |   doc_rate |   MULTA_spans |   MULTA_rate |   OBRIGACAO_spans |   OBRIGACAO_rate |   RESSARCIMENTO_spans |   RESSARCIMENTO_rate |   RECOMENDACAO_spans |   RECOMENDACAO_rate |
|:---------|-----------------:|-----------:|--------------:|-------------:|------------------:|-----------------:|----------------------:|---------------------:|---------------------:|--------------------:|
| determin |              146 |     0.1696 |             0 |       0.0000 |                84 |           0.6885 |                     0 |               0.0000 |                    0 |              0.0000 |
| julg     |              860 |     0.9988 |             0 |       0.0000 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| aplic    |              229 |     0.2660 |             1 |       0.0048 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| recomend |               87 |     0.1010 |             0 |       0.0000 |                 0 |           0.0000 |                     0 |               0.0000 |                   28 |              0.8750 |
| conden   |               51 |     0.0592 |             1 |       0.0048 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| imput    |               49 |     0.0569 |             0 |       0.0000 |                 0 |           0.0000 |                     1 |               0.0152 |                    0 |              0.0000 |
| mult     |              204 |     0.2369 |           171 |       0.8182 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| ressarc  |              135 |     0.1568 |             0 |       0.0000 |                 0 |           0.0000 |                    62 |               0.9394 |                    0 |              0.0000 |
| restitu  |                2 |     0.0023 |             0 |       0.0000 |                 0 |           0.0000 |                     1 |               0.0152 |                    0 |              0.0000 |
| obrig    |               22 |     0.0256 |             0 |       0.0000 |                 1 |           0.0082 |                     0 |               0.0000 |                    0 |              0.0000 |
| fix      |               69 |     0.0801 |             0 |       0.0000 |                 4 |           0.0328 |                     0 |               0.0000 |                    0 |              0.0000 |

## (e) Comparação lexical com o LeNER-Br

| metric                          |      value |
|:--------------------------------|-----------:|
| decicontas_types                |  4034.0000 |
| lener_types                     | 14404.0000 |
| jaccard_top5000                 |     0.2737 |
| decicontas_top5000_oov_in_lener |     0.3632 |
| lener_top5000_oov_in_decicontas |     0.6118 |
| lener_docs                      | 10395.0000 |
| decicontas_docs                 |   861.0000 |

**Termos mais distintivos (log-odds com prior de Dirichlet, z):**

| word                  |   log_odds_z | corpus     |
|:----------------------|-------------:|:-----------|
| pelo                  |      36.0968 | decicontas |
| nos                   |      35.2774 | decicontas |
| do                    |      34.5467 | decicontas |
| contas                |      32.7889 | decicontas |
| termos                |      32.6454 | decicontas |
| voto                  |      30.9576 | decicontas |
| julgar                |      28.6445 | decicontas |
| autos                 |      28.4143 | decicontas |
| relator               |      24.9708 | decicontas |
| complementar          |      24.4802 | decicontas |
| ministerio            |      24.0606 | decicontas |
| estes                 |      22.6120 | decicontas |
| vistos                |      22.2619 | decicontas |
| desta                 |      22.0717 | decicontas |
| publico               |      22.0392 | decicontas |
| acordam               |      22.0353 | decicontas |
| com                   |      21.9462 | decicontas |
| estadual              |      21.8237 | decicontas |
| discutidos            |      21.7638 | decicontas |
| relatados             |      21.7116 | decicontas |
| corte                 |      21.6200 | decicontas |
| proferido             |      21.4747 | decicontas |
| inciso                |      20.9974 | decicontas |
| no                    |      20.6001 | decicontas |
| corpo                 |      19.6617 | decicontas |
| que                   |     -26.0055 | lener_br   |
| nao                   |     -22.0143 | lener_br   |
| ou                    |     -15.1345 | lener_br   |
| se                    |     -13.6988 | lener_br   |
| como                  |     -12.2508 | lener_br   |
| de                    |     -11.2398 | lener_br   |
| as                    |     -11.2338 | lener_br   |
| ser                   |     -10.9726 | lener_br   |
| foi                   |     -10.8931 | lener_br   |
| justica               |     -10.5403 | lener_br   |
| federal               |      -9.7649 | lener_br   |
| agravo                |      -9.7222 | lener_br   |
| acao                  |      -9.6139 | lener_br   |
| na                    |      -8.6994 | lener_br   |
| qual                  |      -8.5867 | lener_br   |
| militar               |      -8.5322 | lener_br   |
| fls                   |      -8.4396 | lener_br   |
| inconstitucionalidade |      -8.2602 | lener_br   |
| superior              |      -8.1829 | lener_br   |
| defesa                |      -8.0645 | lener_br   |
| quando                |      -7.9400 | lener_br   |
| codigo                |      -7.8633 | lener_br   |
| penal                 |      -7.8529 | lener_br   |
| sobre                 |      -7.4922 | lener_br   |
| recorrente            |      -7.4438 | lener_br   |
