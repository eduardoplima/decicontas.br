# Systematic mapping: NLP and NER in the legal domain

Replication material for the systematic literature mapping reported in Chapter 3 of
the dissertation: 473 records retrieved from ACM Digital Library, IEEE Xplore and
Scopus, 79 studies included. The protocol is in [`protocol.md`](protocol.md)
(Portuguese, as in the dissertation).

## Contents

```
mapping/
├── protocol.md          # research questions, search expression, databases, dates, criteria, funnel
├── verify_counts.py     # recomputes the funnel from the files below
├── search/
│   ├── acm.bib          # 175 records as exported
│   ├── ieee.bib         # 78 records
│   ├── scopus.bib       # 229 records
│   └── scopus_not_imported.csv   # the 9 Scopus records the screening tool did not import
├── screening/
│   ├── records.csv      # the 473 screened records, with status and criterion
│   └── eligibility_exclusions.csv   # the 11 accepted records excluded at full-text stage
├── extraction/
│   ├── schema.py        # the 21-field extraction form (pydantic)
│   ├── prompt.py        # system and user prompts
│   ├── extracted.csv    # one row per included study (79)
│   ├── cache/           # the same extractions as JSON, one file per study
│   ├── citekeys.csv     # study → BibTeX key used in the dissertation
│   └── included_studies.bib      # the 79 included studies
└── analysis/
    ├── scripts/, tools/ # the pipeline as it was run
    ├── requirements.txt
    └── outputs/         # the charts and LaTeX tables generated from extracted.csv
```

`python verify_counts.py` checks every count quoted above against the files.

## Funnel

| Stage | ACM | IEEE | Scopus | Total |
|---|---:|---:|---:|---:|
| Identified | 175 | 78 | 220 | 473 |
| Duplicates | 2 | 21 | 17 | 40 |
| Rejected on title and abstract | 164 | 47 | 132 | 343 |
| Accepted on title and abstract | 9 | 10 | 71 | 90 |
| Excluded at eligibility | 0 | 1 | 10 | 11 |
| **Included** | **9** | **9** | **61** | **79** |

Of the 11 eligibility exclusions, 9 are studies whose full text was not obtained, 1 is
a PDF with no machine-readable text and 1 is written in Russian. The reason for each is
in `screening/eligibility_exclusions.csv`.

`screening/records.csv` has a `status` column (the title-and-abstract decision:
`Accepted`, `Rejected`, `Duplicated`) and a `final_decision` column (`included`,
`excluded_eligibility`, `rejected`, `duplicated`).

## What is not here

- **Full texts.** Publisher PDFs are not redistributed. Each record carries its DOI.
- **Abstracts.** They were removed from the `.bib` exports and from `records.csv`.

## Running the mapping again

1. Run the search expression in `protocol.md` on the three databases and export BibTeX.
2. Screen the records against the criteria in `protocol.md`.
3. Obtain the full texts of the accepted records and place the PDFs in
   `analysis/pdfs_artigos/`.
4. From `analysis/`, install `requirements.txt`, set `OPENAI_API_KEY`, and run
   `scripts/run_extracao.py`, `scripts/aplicar_filtros.py` and `scripts/gerar_bibtex.py`.

The scripts are published as they were run and expect the working layout below, relative
to `analysis/`:

| Script path | File in this package |
|---|---|
| `todos_artigos.xlsx` | `screening/records.csv` (the spreadsheet export of the screening tool) |
| `data/revisao/artigos_filtrados.csv` | `extraction/extracted.csv` |
| `data/revisao/cache/` | `extraction/cache/` |
| `data/revisao/citekeys.csv` | `extraction/citekeys.csv` |
| `outputs/estudos_aprovados.bib` | `extraction/included_studies.bib` |
| `outputs/figures/`, `outputs/latex/` | `analysis/outputs/charts/`, `analysis/outputs/latex/` |

## Limits

- The extraction uses `gpt-5-mini` through the OpenAI API, with no pinned model snapshot
  and default temperature. A new run will not return identical values; the values behind
  the dissertation are the ones in `extraction/`.
- `extracted.csv` is the model output, with the publication year filled in from the
  screening record where the model returned none.
- Texts longer than 60,000 characters were truncated to their first and last 30,000.

## License

Data and documentation in this folder: CC BY 4.0. Code: MIT. See the repository
[`LICENSE`](../../LICENSE).
