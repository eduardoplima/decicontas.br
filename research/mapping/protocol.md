# Protocolo do mapeamento sistemático

Mapeamento sistemático da literatura sobre Processamento de Linguagem Natural
(PLN) e Reconhecimento de Entidades Nomeadas (REN) no domínio jurídico,
conduzido segundo Petersen et al. (2008): (i) definição das questões de
pesquisa; (ii) busca em bases acadêmicas; (iii) triagem por critérios de
inclusão e exclusão; (iv) *keywording* e extração de dados; (v) construção do
mapa. O protocolo corresponde ao Capítulo 3 da dissertação.

## Questões de pesquisa

- **QP1:** Quais técnicas de Processamento de Linguagem Natural (PLN) são
  utilizadas para estruturar e extrair informações de documentos jurídicos?
- **QP2:** Quais técnicas de Reconhecimento de Entidades Nomeadas oferecem
  melhor desempenho na extração de entidades em textos jurídicos complexos?
- **QP3:** Quais são os limites e potenciais dos Modelos de Linguagem de Grande
  Porte (LLMs) na realização de REN jurídico em comparação com modelos
  especializados treinados com supervisão?
- **QP4:** Quais tipos de entidades jurídicas são considerados na literatura e
  como os diferentes trabalhos estruturam seus esquemas de anotação?

## Bases e expressão de busca

Bases: ACM Digital Library, IEEE Xplore e Scopus. Campos: título, resumo e
palavras-chave. Expressão:

```
("legal" OR "law") AND ("NER" OR "named entity recognition" OR "information extraction") AND ("dataset" OR "corpus")
```

## Datas

| Etapa | Data |
|---|---|
| Busca | outubro de 2025 |
| Exportação dos registros usados na triagem (`search/`) | 2 de fevereiro de 2026 |
| Triagem por título e resumo | 3 a 11 de março de 2026 |
| Extração de dados | 2 de maio de 2026 |

Os 473 registros triados são os da exportação de 2 de fevereiro de 2026. Ela
contém 15 registros com ano de publicação 2026, todos rejeitados na triagem.

## Critérios

Inclusão (CI):

1. Estudos sobre Reconhecimento de Entidades Nomeadas em aplicações jurídicas;
2. Estudos sobre conjuntos de dados construídos a partir de *corpora* jurídicos;
3. Estudos sobre extração de informações estruturadas a partir de textos jurídicos;
4. Estudos sobre aplicações de NLP ou LLMs em textos jurídicos.

Exclusão (CE):

1. Artigos duplicados;
2. Artigos com menos de 4 páginas;
3. Literatura cinza (material sem revisão por pares: *preprints*, relatórios
   técnicos, *white papers*, teses e dissertações);
4. Publicações em ano inferior a 2015;
5. Revisões ou mapeamentos (estudos secundários);
6. Artigos fora do escopo determinado;
7. Artigo em idioma diferente do inglês ou português.

Na planilha de triagem (`screening/records.csv`, coluna `selection_criteria`)
os rótulos são os da ferramenta de triagem; o de páginas aparece ali como
"Artigos com menos de 3 páginas".

## Seleção dos estudos

| Etapa | ACM | IEEE | Scopus | Total |
|---|---:|---:|---:|---:|
| Identificados | 175 | 78 | 220 | 473 |
| Duplicados | 2 | 21 | 17 | 40 |
| Rejeitados por título e resumo | 164 | 47 | 132 | 343 |
| Aceitos na triagem | 9 | 10 | 71 | 90 |
| Excluídos na elegibilidade | 0 | 1 | 10 | 11 |
| **Incluídos** | **9** | **9** | **61** | **79** |

Exclusões na elegibilidade (`screening/eligibility_exclusions.csv`):

- 9 por texto completo não obtido: 3 sem PDF localizado, 1 com arquivo
  inválido, 4 em que o PDF obtido era de outro artigo e 1 em que só a primeira
  página foi obtida;
- 1 por texto não extraível do PDF;
- 1 por idioma (russo).

A exportação do Scopus tem 229 registros; 9 não foram importados pela
ferramenta de triagem (`search/scopus_not_imported.csv`).

## Extração de dados

Cada estudo incluído teve o texto extraído do PDF, truncado em 60 mil
caracteres quando mais longo (30 mil do início e 30 mil do fim), e submetido
ao modelo `gpt-5-mini` (OpenAI) com saída estruturada. O esquema tem 21 campos
(`extraction/schema.py`) e o *prompt* está em `extraction/prompt.py`. O
resultado por estudo está em `extraction/extracted.csv` e `extraction/cache/`.

## Referência

Petersen, K.; Feldt, R.; Mujtaba, S.; Mattsson, M. Systematic mapping studies
in software engineering. EASE 2008.
