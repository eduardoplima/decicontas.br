# Capítulo 4 — Análise descritiva e linguística do corpus

Gerado por `research.release.corpus_analysis` a partir de `dataset/release/decicontas/decicontas.json` (release corrigida, 861 docs). Os CSVs ao lado são as fontes canônicas.

## (a) Entidades por documento (DS-p.42)

| n_entities   |   n_docs |   pct_all_docs |   pct_informative_docs |
|:-------------|---------:|---------------:|-----------------------:|
| 0            |      629 |         0.7305 |               nan      |
| 1            |      115 |         0.1336 |                 0.4957 |
| 2            |       75 |         0.0871 |                 0.3233 |
| 3+           |       42 |         0.0488 |                 0.1810 |

## (b) Coocorrência de classes no mesmo documento

| label         |   MULTA |   OBRIGACAO |   RESSARCIMENTO |   RECOMENDACAO |
|:--------------|--------:|------------:|----------------:|---------------:|
| MULTA         |     141 |          58 |              37 |              3 |
| OBRIGACAO     |      58 |          92 |               2 |              8 |
| RESSARCIMENTO |      37 |           2 |              57 |              2 |
| RECOMENDACAO  |       3 |           8 |               2 |             48 |

## (c) Posição relativa dos spans no documento

Aproximação declarada para dispositivo × fundamentação: sem segmentação estrutural, usa-se a posição relativa do centro do span (`center_rel` ∈ [0, 1]); `frac_in_final_third` é a fração de spans no terço final do texto.

| label         |   count |   mean |   median |    q25 |    q75 |   frac_in_final_third |
|:--------------|--------:|-------:|---------:|-------:|-------:|----------------------:|
| MULTA         |     212 | 0.5305 |   0.4909 | 0.3579 | 0.6928 |                0.2689 |
| OBRIGACAO     |     131 | 0.6518 |   0.7185 | 0.5815 | 0.7474 |                0.6794 |
| RESSARCIMENTO |      63 | 0.6144 |   0.5866 | 0.4595 | 0.7879 |                0.4286 |
| RECOMENDACAO  |      53 | 0.6226 |   0.6311 | 0.5525 | 0.6751 |                0.3019 |

## (d) N-gramas iniciais dos spans por classe

| label         |   n | ngram                   |   count |   pct_of_spans |
|:--------------|----:|:------------------------|--------:|---------------:|
| MULTA         |   1 | multa                   |     157 |         0.7406 |
| MULTA         |   1 | o                       |       2 |         0.0094 |
| MULTA         |   1 | multas:                 |       2 |         0.0094 |
| MULTA         |   1 | ao                      |       2 |         0.0094 |
| MULTA         |   1 | 1.multa                 |       2 |         0.0094 |
| MULTA         |   1 | valor                   |       2 |         0.0094 |
| MULTA         |   1 | 06                      |       1 |         0.0047 |
| MULTA         |   1 | saint                   |       1 |         0.0047 |
| MULTA         |   1 | ciro                    |       1 |         0.0047 |
| MULTA         |   1 | condenando              |       1 |         0.0047 |
| MULTA         |   1 | servidores              |       1 |         0.0047 |
| MULTA         |   1 | grande                  |       1 |         0.0047 |
| MULTA         |   1 | claudio                 |       1 |         0.0047 |
| MULTA         |   1 | tatiana                 |       1 |         0.0047 |
| MULTA         |   1 | cinthia                 |       1 |         0.0047 |
| MULTA         |   2 | multa no                |     115 |         0.5476 |
| MULTA         |   2 | multa de                |      15 |         0.0714 |
| MULTA         |   2 | multa ao                |      10 |         0.0476 |
| MULTA         |   2 | multa equivalente       |       6 |         0.0286 |
| MULTA         |   2 | multa na                |       4 |         0.0190 |
| MULTA         |   2 | multa à                 |       2 |         0.0095 |
| MULTA         |   2 | ao sr.                  |       2 |         0.0095 |
| MULTA         |   2 | 1.multa no              |       2 |         0.0095 |
| MULTA         |   2 | valor de                |       2 |         0.0095 |
| MULTA         |   2 | 06 multas               |       1 |         0.0048 |
| MULTA         |   2 | saint clay              |       1 |         0.0048 |
| MULTA         |   2 | ciro gustavo            |       1 |         0.0048 |
| MULTA         |   2 | condenando a            |       1 |         0.0048 |
| MULTA         |   2 | servidores do           |       1 |         0.0048 |
| MULTA         |   2 | grande do               |       1 |         0.0048 |
| OBRIGACAO     |   1 | determinação            |      68 |         0.5191 |
| OBRIGACAO     |   1 | determinar              |      10 |         0.0763 |
| OBRIGACAO     |   1 | decide                  |       7 |         0.0534 |
| OBRIGACAO     |   1 | prazo                   |       6 |         0.0458 |
| OBRIGACAO     |   1 | determinando            |       3 |         0.0229 |
| OBRIGACAO     |   1 | deve,                   |       2 |         0.0153 |
| OBRIGACAO     |   1 | notificação             |       2 |         0.0153 |
| OBRIGACAO     |   1 | joão                    |       2 |         0.0153 |
| OBRIGACAO     |   1 | medida                  |       2 |         0.0153 |
| OBRIGACAO     |   1 | representação           |       2 |         0.0153 |
| OBRIGACAO     |   1 | município               |       2 |         0.0153 |
| OBRIGACAO     |   1 | fixação                 |       2 |         0.0153 |
| OBRIGACAO     |   1 | decide,                 |       2 |         0.0153 |
| OBRIGACAO     |   1 | determinada             |       1 |         0.0076 |
| OBRIGACAO     |   1 | saúde                   |       1 |         0.0076 |
| OBRIGACAO     |   2 | determinação constante  |      48 |         0.3692 |
| OBRIGACAO     |   2 | determinação ao         |      13 |         0.1000 |
| OBRIGACAO     |   2 | determinar a            |       6 |         0.0462 |
| OBRIGACAO     |   2 | prazo de                |       6 |         0.0462 |
| OBRIGACAO     |   2 | decide pela             |       3 |         0.0231 |
| OBRIGACAO     |   2 | determinação à          |       3 |         0.0231 |
| OBRIGACAO     |   2 | deve, ainda,            |       2 |         0.0154 |
| OBRIGACAO     |   2 | notificação ao          |       2 |         0.0154 |
| OBRIGACAO     |   2 | joão maria              |       2 |         0.0154 |
| OBRIGACAO     |   2 | medida de               |       2 |         0.0154 |
| OBRIGACAO     |   2 | determinação para,      |       2 |         0.0154 |
| OBRIGACAO     |   2 | representação ao        |       2 |         0.0154 |
| OBRIGACAO     |   2 | determinar aos          |       2 |         0.0154 |
| OBRIGACAO     |   2 | município de            |       2 |         0.0154 |
| OBRIGACAO     |   2 | fixação de              |       2 |         0.0154 |
| RESSARCIMENTO |   1 | ressarcimento           |      49 |         0.7778 |
| RESSARCIMENTO |   1 | ressarcir               |      10 |         0.1587 |
| RESSARCIMENTO |   1 | maria                   |       1 |         0.0159 |
| RESSARCIMENTO |   1 | devolução               |       1 |         0.0159 |
| RESSARCIMENTO |   1 | restituição             |       1 |         0.0159 |
| RESSARCIMENTO |   1 | ressarcimentos          |       1 |         0.0159 |
| RESSARCIMENTO |   2 | ressarcimento ao        |      32 |         0.5079 |
| RESSARCIMENTO |   2 | ressarcir ao            |       7 |         0.1111 |
| RESSARCIMENTO |   2 | ressarcimento da        |       4 |         0.0635 |
| RESSARCIMENTO |   2 | ressarcimento do        |       2 |         0.0317 |
| RESSARCIMENTO |   2 | ressarcimento no        |       2 |         0.0317 |
| RESSARCIMENTO |   2 | ressarcimento dos       |       2 |         0.0317 |
| RESSARCIMENTO |   2 | ressarcimento aos       |       2 |         0.0317 |
| RESSARCIMENTO |   2 | maria izabel            |       1 |         0.0159 |
| RESSARCIMENTO |   2 | ressarcir aos           |       1 |         0.0159 |
| RESSARCIMENTO |   2 | ressarcir integralmente |       1 |         0.0159 |
| RESSARCIMENTO |   2 | ressarcimento em        |       1 |         0.0159 |
| RESSARCIMENTO |   2 | ressarcir a             |       1 |         0.0159 |
| RESSARCIMENTO |   2 | devolução ao            |       1 |         0.0159 |
| RESSARCIMENTO |   2 | restituição aos         |       1 |         0.0159 |
| RESSARCIMENTO |   2 | ressarcimento das       |       1 |         0.0159 |
| RECOMENDACAO  |   1 | recomende               |      26 |         0.4906 |
| RECOMENDACAO  |   1 | recomendação            |      14 |         0.2642 |
| RECOMENDACAO  |   1 | recomendar              |       7 |         0.1321 |
| RECOMENDACAO  |   1 | decide                  |       2 |         0.0377 |
| RECOMENDACAO  |   1 | ramalho                 |       1 |         0.0189 |
| RECOMENDACAO  |   1 | como                    |       1 |         0.0189 |
| RECOMENDACAO  |   1 | imediata                |       1 |         0.0189 |
| RECOMENDACAO  |   1 | corpo                   |       1 |         0.0189 |
| RECOMENDACAO  |   2 | recomende à             |      26 |         0.4906 |
| RECOMENDACAO  |   2 | recomendação ao         |       5 |         0.0943 |
| RECOMENDACAO  |   2 | recomendar ao           |       4 |         0.0755 |
| RECOMENDACAO  |   2 | recomendação à          |       4 |         0.0755 |
| RECOMENDACAO  |   2 | recomendação de         |       2 |         0.0377 |
| RECOMENDACAO  |   2 | recomendar à            |       2 |         0.0377 |
| RECOMENDACAO  |   2 | ramalho cortez,         |       1 |         0.0189 |
| RECOMENDACAO  |   2 | recomendar a            |       1 |         0.0189 |
| RECOMENDACAO  |   2 | recomendação aos        |       1 |         0.0189 |
| RECOMENDACAO  |   2 | como também             |       1 |         0.0189 |
| RECOMENDACAO  |   2 | decide recomendar       |       1 |         0.0189 |
| RECOMENDACAO  |   2 | decide também           |       1 |         0.0189 |
| RECOMENDACAO  |   2 | recomendação que,       |       1 |         0.0189 |
| RECOMENDACAO  |   2 | recomendação para       |       1 |         0.0189 |
| RECOMENDACAO  |   2 | imediata da             |       1 |         0.0189 |

## (d') Verbos/marcadores performativos

Radicais buscados nos 5 primeiros tokens do span (colunas `*_rate` = fração dos spans da classe) e no documento inteiro (`doc_rate`).

| stem     |   docs_with_stem |   doc_rate |   MULTA_spans |   MULTA_rate |   OBRIGACAO_spans |   OBRIGACAO_rate |   RESSARCIMENTO_spans |   RESSARCIMENTO_rate |   RECOMENDACAO_spans |   RECOMENDACAO_rate |
|:---------|-----------------:|-----------:|--------------:|-------------:|------------------:|-----------------:|----------------------:|---------------------:|---------------------:|--------------------:|
| determin |              146 |     0.1696 |             0 |       0.0000 |                82 |           0.6260 |                     0 |               0.0000 |                    0 |              0.0000 |
| julg     |              860 |     0.9988 |             0 |       0.0000 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| aplic    |              229 |     0.2660 |             1 |       0.0047 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| recomend |               87 |     0.1010 |             0 |       0.0000 |                 0 |           0.0000 |                     0 |               0.0000 |                   49 |              0.9245 |
| conden   |               51 |     0.0592 |             1 |       0.0047 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| imput    |               49 |     0.0569 |             0 |       0.0000 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| mult     |              204 |     0.2369 |           166 |       0.7830 |                 0 |           0.0000 |                     0 |               0.0000 |                    0 |              0.0000 |
| ressarc  |              135 |     0.1568 |             0 |       0.0000 |                 0 |           0.0000 |                    60 |               0.9524 |                    0 |              0.0000 |
| restitu  |                2 |     0.0023 |             0 |       0.0000 |                 0 |           0.0000 |                     1 |               0.0159 |                    0 |              0.0000 |
| obrig    |               22 |     0.0256 |             0 |       0.0000 |                 1 |           0.0076 |                     0 |               0.0000 |                    0 |              0.0000 |
| fix      |               69 |     0.0801 |             0 |       0.0000 |                 3 |           0.0229 |                     0 |               0.0000 |                    0 |              0.0000 |

## (e) Comparação lexical com o LeNER-Br

| metric                          |      value |
|:--------------------------------|-----------:|
| decicontas_types                |  3997.0000 |
| lener_types                     | 14404.0000 |
| jaccard_top5000                 |     0.2868 |
| decicontas_top5000_oov_in_lener |     0.3320 |
| lener_top5000_oov_in_decicontas |     0.5990 |
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
