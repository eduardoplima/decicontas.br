# Annotation guidelines: decicontas.br

**Version 1.0**

A Portuguese version of this document is kept at
[`ANNOTATION_GUIDELINES.pt-BR.md`](ANNOTATION_GUIDELINES.pt-BR.md).

## 1. Goal and unit of annotation

The goal is to mark, in the text of a decision, the passages that carry commands issued by the
Tribunal to an audited party and that feed the General Registry for Decision Monitoring (CGAD,
art. 431, IV, of the TCE/RN Internal Rules).

- The unit is the **span**: a contiguous passage of the text with a single label.
- The scheme is **flat**: spans neither nest nor overlap.
- A document may have zero, one or several entities. Decisions with no registrable command stay
  in the corpus without annotation (638 of the 861).
- During annotation the labels were finer (`MULTA_FIXA`, `MULTA_PERCENTUAL`, `OBRIGACAO_MULTA`);
  the release collapses them into the four classes below.

## 2. General rules

| # | Rule |
|---|---|
| G1 | **Literal copy.** The span is exactly the text of the decision, with no spelling correction, no inference and no completion of missing information. |
| G2 | **One command, one span.** Commands listed under separate items (a, b, c…) get separate spans, even when they are of the same class. The item marker and the connective between items ("e b)") stay outside. |
| G3 | **Start at the head of the command.** The span starts at the word that names the command ("multa", "determinação", "ressarcimento", "recomendação", or the corresponding verb), not at the connective that introduces it ("pela aplicação de", "pela renovação da", "sem prejuízo da aplicação de"). |
| G4 | **End where the command's clause ends, punctuation included.** The span runs up to and including the full stop or semicolon that closes the command. |
| G5 | **Reasoning stays outside.** The report, the recitals and the grounds that precede the command are not part of the span. A legal basis cited *inside* the command ("com fundamento no art. 107…") is part of it. |
| G6 | **Word boundaries.** A span never starts or ends in the middle of a word. |
| G7 | **When in doubt whether to annotate, the registry decides:** annotate what would create a record to be monitored in the CGAD. |

## 3. Classes

### 3.1 MULTA (fine)

A pecuniary sanction for an administrative or fiscal infraction (State Complementary Law
464/2012, art. 107; Resolution 013/2015-TCE). Covers fixed-amount and percentage fines.

- **Inside the span:** the amount or percentage (with the amount in words in parentheses, when
  present), the responsible party when named in the same clause, and the legal basis when cited
  in the same clause.
- **Not a MULTA:** a daily or coercive fine set for non-compliance with a determination. It is
  part of the span of the corresponding OBRIGACAO (see 3.2).

Example (decision 798):

> a) Pela irregularidade da matéria, com a consequente aplicação de **multa no valor total de R$ 2.000 (dois mil reais), sendo R$ 1.000,00 (mil reais) relativo à ausência de pesquisa mercadológica; e R$ 1.000 (mil reais) relacionado à contratação sem amparo em legislação específica;**

### 3.2 OBRIGACAO (obligation)

A binding determination to do or not to do something (art. 431, IV, "c", of the Internal Rules).

- **Inside the span:** the addressee, the required conduct, the deadline and, when present, the
  daily or coercive fine for non-compliance.
- **Outside:** legal reasoning and motivating recitals.

Example (decision 232):

> … para conceder o **prazo de 18 (dezoito) meses, a contar da intimação do Acórdão n.º 138/2022, ao Município de Bom Jesus e ao gestor responsável, […], para saneamento dessa infração continuada, sob pena de multa diária, a ambos, no importe de R$ 1.000,00 por cada contrato irregular mantido (LOTCE/RN, art. 110);**

### 3.3 RESSARCIMENTO (reimbursement)

An order to return amounts to the treasury for established damage (art. 431, IV, "b", of the
Internal Rules).

- **Inside the span:** the amount of the damage, the responsible party when named in the same
  clause, and, when present, joint liability and the form of monetary adjustment.

Example (decision 798):

> b) Pelo dever de **ressarcir ao erário no valor de R$ 57.000,00 e (cinquenta e sete mil reais);**

### 3.4 RECOMENDACAO (recommendation)

Non-binding guidance addressed to the audited party, with no sanction for non-compliance.

- **Inside the span:** the addressee, when present, and the recommended measure.

Example (decision 798):

> c) Pela **recomendação ao atual gestor do Município de Pendências/RN para que, nas próximas licitações, não faça constar nos editais a cobrança de taxa ou emolumentos além do valor do custo efetivo de reprodução gráfica da documentação fornecida.**

## 4. Scope: what is not annotated

**E1. Deliberations addressed to the Tribunal's own units.** Recommendations and notices
addressed to the External Control Secretariat (SECEX) or to the Legal Counsel (CONJU) are acts
of internal management, with no audited party to monitor, and are not annotated in any class.
The rule is applied deterministically to the release by `research/annotation_scope.py`: the
clause runs from the word "recomend…" or "cientific…" to the next full stop or semicolon.

**Also left unannotated in the gold standard**, as a consequence of G5 and G7 (these are
descriptions of the gold standard):

- procedural commands with nothing to monitor, such as filing, summons, notification, referral
  of the case file and enforcement of the decision;
- judgments on the merits that carry no command (regularity, irregularity, approval of
  accounts), and mentions of a fine or debt from an earlier decision without a new imposition;
- the report, the opinion and the reasoning.

## 5. Boundary cases

- **MULTA and RESSARCIMENTO in the same item.** These are the two pecuniary classes and often
  appear together. Each segment belongs to one command: the part that imposes the sanction is
  MULTA, the part that orders the return of amounts is RESSARCIMENTO. Of the 13 class confusions
  among annotators, ten are between this pair.
- **Daily fine.** Part of the OBRIGACAO whose non-compliance it sanctions; not a separate MULTA.
- **Renewal of a determination.** "Renovação da determinação constante na decisão retro,
  estipulando o prazo de…" is an OBRIGACAO: there is a new deadline to monitor.
- **RECOMENDACAO has the lowest agreement** among the three annotators and changed the most
  under adjudication (from 22 to 32 entities). When in doubt between RECOMENDACAO and text with
  no command, apply G7.

