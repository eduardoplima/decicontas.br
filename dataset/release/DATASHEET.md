# Datasheet: decicontas.br

This document follows the *Datasheets for Datasets* template (GEBRU, T. et al. Datasheets for datasets. *Communications of the ACM*, v. 64, n. 12, 2021. arXiv:1803.09010v8), answering, question by question, the seven proposed sections: motivation, composition, collection process, preprocessing/cleaning/labelling, uses, distribution and maintenance. Questions that do not apply are answered "N/A" with a brief justification, as the authors recommend.

Documented dataset version: **decicontas** (861 documents, cleanlab corrections applied), distributed alongside **decicontas-before-correction**.

A Portuguese translation of this document is kept at [`DATASHEET.pt-BR.md`](DATASHEET.pt-BR.md).

---

## 1. Motivation

**For what purpose was the dataset created? Was there a specific task in mind? Was there a specific gap that needed to be filled?**

`decicontas.br` was created for Named Entity Recognition (NER) over accountability rulings of the Court of Accounts of the State of Rio Grande do Norte (TCE/RN, *Tribunal de Contas do Estado do Rio Grande do Norte*). The applied goal is to automate the feeding of the subregistries of the General Registry for Decision Monitoring (CGAD, art. 431, IV of the Court's internal rules) — the registries of fines (CGM), refunds (CGD) and recommendations (CGR) — which are today filled in by reading each decision by hand. The gap it fills is the absence of an annotated NER corpus for Brazilian Court of Accounts decisions: the existing Portuguese legal NER corpora (LeNER-Br, UlyssesNER-Br) cover judicial litigation and the legislative domain, but none addresses the external control exercised by Courts of Accounts. The dataset also serves as an evaluation benchmark for comparing few-shot LLMs against domain-adapted supervised models.

**Who created the dataset (team, research group) and on behalf of which entity (company, institution, organisation)?**

The dataset was created by Eduardo Pereira Lima as an artefact of the master's dissertation *"Reconhecimento de Entidades Nomeadas em Decisões do TCE/RN"* (Named Entity Recognition in TCE/RN Decisions), at the Federal University of Rio Grande do Norte (UFRN). The reference annotation (gold standard) was produced by the author, who has working knowledge of the external-control domain (Annotator 1); two additional annotators — staff of the TCE/RN unit responsible for decision monitoring (Annotators 2 and 3) — independently re-annotated the corpus for the agreement study that accompanies the dataset.

**Who funded the creation of the dataset?**

No specific funding (grant or project with an award number) was dedicated to building the dataset.

**Any other comments?**

The dataset is distributed in two paired versions — before and after the cleanlab annotation-error audit — precisely to enable studies on the effect of label noise (see Sections 3 and 4).

---

## 2. Composition

**What do the instances that comprise the dataset represent (documents, photos, people, countries)?**

Each instance is the full text of a collegiate decision (*acórdão* or *decisão*) issued by the TCE/RN in accountability proceedings. The decision is the unit of analysis throughout the work, including as the resampling unit of the evaluation bootstrap. There is a single instance type.

**How many instances are there in total (of each type, if appropriate)?**

861 documents, totalling 116,844 tokens and 754,555 characters. Of these, 232 documents (27.0%) contain at least one annotated entity and 629 (73.0%) are empty — true negatives, read in full and judged to carry no registrable command (filings, clean-account judgments). The corrected version holds 459 entities: 212 MULTA, 131 OBRIGACAO, 63 RESSARCIMENTO and 53 RECOMENDACAO (before corrections: 439 entities — 202/119/62/56).

**Does the dataset contain all possible instances or is it a sample (not necessarily random) of a larger set?**

It is a sample. The larger set is the TCE/RN base of collegiate decisions (more than 40,000 decisions between 2012 and 2025 in the raw extract shipped with the repository, under `dataset/raw/`). The annotated subset was imported into Label Studio in batches drawn from Court sessions, including a complementary batch targeted at decisions containing reimbursements, to reinforce the rarest class. The sample is **not** probabilistic and does not claim to represent the full historical base; it reflects the recent flow of deliberations, which preserves the realistic proportion of decisions with no registrable command (73.0% empty documents). Of the 866 originally annotated documents, 5 were removed from evaluation because they had been reused as few-shot exemplars in the LLM prompts (contamination prevention), yielding the 861 published.

**What data does each instance consist of? "Raw" data or features?**

Raw (unprocessed) decision text, accompanied by derived artefacts: token list, per-token BIO labels (`ner_tags`), per-token character offsets (`token_offsets`) and entities reconstructed as character spans (`entities` in the JSON bundle, `spans` in the JSONL bundle).

**Is there a label or target associated with each instance?**

Yes. Each token receives one of nine BIO labels: `O`, `B-/I-MULTA`, `B-/I-OBRIGACAO`, `B-/I-RESSARCIMENTO`, `B-/I-RECOMENDACAO`. The four categories map onto the CGAD subregistries: MULTA (pecuniary sanction), OBRIGACAO (binding order to do or refrain from doing), RESSARCIMENTO (reimbursement to the treasury) and RECOMENDACAO (non-binding guidance). The scheme is flat — no nesting and no overlapping spans (across the 459 entities there is not a single overlapping pair).

**Is any information missing from individual instances?**

Yes, by design: (i) the corpus carries no explicit structural segmentation (report / opinion / operative part) — decisions are published as running text; (ii) procedural metadata (case number, session date, rapporteur, audited body) does not ship with the release, though it exists in the raw extracts; (iii) Brazilian taxpayer numbers (CPF) present in the original texts were masked (see "sensitive data" below).

**Are relationships between individual instances made explicit (e.g., user ratings, social-network links)?**

No. Decisions are treated as independent documents. Distinct decisions may refer to the same case or the same public official, but those links are not annotated.

**Are there recommended data splits (training, validation, test)?**

There is no fixed split. The dissertation protocol uses 5-fold cross-validation at the document level (seed 1007) for the supervised models, and evaluation over all 861 documents for the few-shot LLMs, with confidence intervals from a paired document-level bootstrap (B = 10,000, seed 42). We recommend reporting macro span F1 (IoU ≥ 0.5) as the primary metric, given the class imbalance, alongside the informative subset (232 documents) reported separately.

**Are there any errors, sources of noise, or redundancies in the dataset?**

Yes, and they are documented. The gold standard reflects the judgement of a single annotator; two independent mechanisms quantify and mitigate the resulting noise.

First, an inter-annotator agreement study: two additional annotators independently re-annotated all 861 documents, yielding pairwise token-level Cohen's κ of 0.842–0.899 (Fleiss' κ 0.865, the "almost perfect" band of Landis & Koch) and pairwise span F1 (IoU ≥ 0.5) of 0.776–0.838. The three annotations and the divergence tables are distributed under `dataset/annotators/` and `dataset/results/models_outputs/chapter4/`.

Second, an annotation-error audit with the cleanlab library (*confident learning*), which confronts each label with out-of-sample predictions from a model ensemble. Of the 794 flagged groups, the 567 with ensemble confidence ≥ 0.95 were reviewed one by one in a purpose-built interface (6 accepted, 544 rejected, 17 custom corrections). The review is best read as a confirmation of the original annotation: only 23 of the 567 reviewed groups (4.1%) were actually changed. The 227 groups below the threshold were **not** reviewed and keep their original label — residual annotation noise may persist in those cases. Both versions (before/after corrections) are distributed so that this effect can be quantified. There are no duplicate documents in the release.

**Is the dataset self-contained, or does it link to or otherwise rely on external resources (websites, tweets, other datasets)?**

Self-contained. All texts and annotations live in the release files themselves; `MANIFEST.json` records the SHA-256 of every artefact. The original texts are also public through the TCE/RN official channels (mandatory publication of decisions), but the dataset does not depend on them.

**Does the dataset contain data that might be considered confidential (protected by legal privilege, private communications)?**

No. The decisions are public documents, subject to mandatory official publication, issued by an external-control body in the exercise of its constitutional competence.

**Does the dataset contain data that, if viewed directly, might be offensive, insulting, threatening, or might otherwise cause anxiety?**

No. The content is technical and legal (adjudication of public accounts). We note only that the decisions attribute irregularities and sanctions to named individuals, in the ordinary exercise of the Court's sanctioning function.

**Does the dataset identify any subpopulations (by age, gender)?**

No. No subpopulation is annotated or identified by demographic attributes.

**Is it possible to identify individuals (i.e., one or more natural persons), either directly or indirectly, from the dataset?**

Yes. The decisions name public officials, agents and other responsible parties in the accountability proceedings — information that is part of the original public document and is essential to the dataset's purpose (MULTA and RESSARCIMENTO spans must contain the identification of the responsible party). This is data already public by force of the transparency and publicity duties attached to acts of external control.

**Does the dataset contain data that might be considered sensitive (racial or ethnic origin, political opinions, religious beliefs, health data, biometrics, government identifiers such as document numbers, criminal history)?**

The original texts contained CPF numbers (a Brazilian government identifier) of individuals mentioned. Those numbers were masked with the pattern `***.***.***-**` in the distributed raw extracts, and the release texts were checked for the absence of formatted CPFs. Names of individuals and the facts established in the proceedings (administrative irregularities and the corresponding sanctions) remain, and are public information. There are no health, biometric, religious or ethnic-origin data.

**Any other comments?**

The entity distribution is strongly skewed (MULTA accounts for ~46% of entities) and spans are long (median ~300 characters for MULTA), characteristics that drive the choice of metrics and labelling schemes (see Section 5).

---

## 3. Collection process

**How was the data associated with each instance acquired? Was it directly observable, reported by subjects, or inferred from other data?**

Directly observable: raw text of the collegiate decisions as recorded in the TCE/RN institutional systems (the ruling text field linked to the session agenda and to the vote of the judging session). No data was reported by subjects nor inferred by models; the only derived data are the manual entity annotations.

**What mechanisms or procedures were used to collect the data (hardware apparatus, manual human curation, software programs, APIs)? How were these mechanisms validated?**

Programmatic extraction from the TCE/RN decisions base (queries against the corporate database that records session deliberations), exported to CSV and imported into Label Studio as annotation tasks. Validation consisted of manual inspection during annotation — each of the 866 imported documents was read in full by the annotator, which doubles as a quality check on the extraction (truncated or corrupted texts would surface in that reading).

**If the dataset is a sample from a larger set, what was the sampling strategy (deterministic, probabilistic with specific probabilities)?**

Non-probabilistic convenience sampling by recency: batches of decisions extracted from the institutional base, complemented by a batch targeted at decisions containing reimbursements (a search driven by the rarest class). The strategy prioritised the recent decision flow — the same flow that will feed the production pipeline — over historical representativeness.

**Who was involved in the data collection process (students, crowdworkers, contractors) and how were they compensated?**

The dissertation author (extraction and reference annotation) and two annotators from the TCE/RN decision-monitoring unit (independent re-annotation for the agreement study), with no specific compensation for the task.

**Over what timeframe was the data collected? Does this timeframe match the creation timeframe of the data associated with the instances?**

The annotated texts come from decisions issued in sessions held between July 2015 and May 2025, with 86.9% concentrated in 2024 and a sparse tail over the earlier years. Import into Label Studio and the reference annotation took place in June 2025; the cleanlab audit and the review of corrections were completed in May 2026; the independent re-annotation by Annotators 2 and 3 took place in August 2026. The collection timeframe is therefore close to the creation timeframe of the documents.

**Were any ethical review processes conducted (e.g., by an institutional review board)?**

No. Because the work deals with official public documents and involves no data collection directly from persons, it does not fall under the cases requiring submission to a research ethics committee for human-subjects research.

**Was the data collected directly from the individuals in question, or obtained via third parties or other sources (websites)?**

From another source: the TCE/RN institutional decisions base. The individuals named in the decisions are not the source of the data; they are mentioned in public documents produced by the Court.

**Were the individuals in question notified about the data collection?**

Not individually. The decisions are public acts, officially published by the Court, and the parties to the proceedings are summoned in the form prescribed by procedural law. Building the dataset involved no new collection from individuals.

**Did the individuals in question consent to the collection and use of their data?**

N/A — individual consent does not apply: the processing bears on official public documents, for academic purposes and in the public interest (improving external control), which are compatible with the Brazilian General Data Protection Law (LGPD, Law 13,709/2018) for data made manifestly public and for processing for study purposes by a research body. As an additional safeguard, CPF numbers were masked.

**If consent was obtained, was a mechanism provided to revoke it in the future or for certain uses?**

N/A (see the previous answer). Requests concerning personal data can be addressed to the maintainer (Section 7).

**Has an analysis of the potential impact of the dataset and its use on data subjects been conducted (e.g., a data protection impact assessment)?**

No formal impact assessment was conducted. The minimisation measures adopted — masking of CPF numbers, absence of additional personal metadata, restriction of scope to the operative commands — reflect an informal risk assessment: the dataset adds no information beyond what the original public documents already contain.

**Any other comments?**

None.

---

## 4. Preprocessing / cleaning / labelling

**Was any preprocessing, cleaning, or labelling of the data done (discretisation, tokenisation, removal of instances, handling of missing values)?**

Yes:

1. **Manual labelling** — the 866 imported documents were annotated at the span level in Label Studio, recording the start and end boundaries of each entity, following delimitation guidelines anchored on the operative part of the decision (the command, not its reasoning). Fine-grained labels used during annotation were collapsed into the four evaluation categories: `MULTA_FIXA`/`MULTA_PERCENTUAL` → `MULTA`; `OBRIGACAO_MULTA` → `OBRIGACAO`.
2. **Tokenisation** — whitespace-based (`re.finditer(r'\S+', text)`), identical across the whole pipeline (annotation → audit → training → evaluation), implemented in `research/dataset_io.py`, the single source of truth for token indices.
3. **BIO projection** — character spans are projected onto per-token BIO labels (9 classes).
4. **Removal of instances** — the 5 documents reused as few-shot exemplars in the prompts (IDs 6, 782, 790, 817 and 852 of the original export) were removed, yielding 861 documents.
5. **Audit and label correction** — annotation-error detection with cleanlab (*confident learning*) over out-of-sample ensemble probabilities; human review of the 567 groups with confidence ≥ 0.95; 4,199 token-level decisions recorded, of which 961 changed a label (183 `accept` and 778 `custom`) while 3,238 confirmed the original annotation (file `dataset/errors/dataset-corrections.json`, schema v2).
6. **CPF masking** — CPF numbers replaced by `***.***.***-**` in the distributed raw extracts.

**Was the "raw" data saved in addition to the preprocessed/cleaned/labelled data (to support unanticipated future uses)?**

Yes. The repository preserves the raw extracts (`dataset/raw/`), the original Label Studio export (`dataset/labeled_data/decicontas.json`, 866 tasks) and the corrections-decision file (`dataset/errors/dataset-corrections.json`), allowing every step to be reconstructed. The `decicontas-before-correction` version freezes the state prior to the audit, and `dataset/annotators/` preserves the three independent annotations used in the agreement study (anonymised as annotator 1/2/3).

**Is the software used to preprocess/clean/label the data available?**

Yes. Labelling used Label Studio (open source). Everything else in the pipeline — tokenisation, BIO projection, application of corrections, release exporters — is in the `research/` package of the public repository (`https://github.com/eduardoplima/decicontas.br/`); the command `uv run python -m research.release.export_dataset` deterministically regenerates the distributed bundles.

**Any other comments?**

Whitespace tokenisation is deliberately simple, to guarantee exact index alignment across all producers and consumers of the dataset. The legacy file `dataset/labeled_data/decicontas.conll` was generated by a different tokeniser and must **not** be used — its indices are not compatible.

---

## 5. Uses

**Has the dataset been used for any tasks already?**

Yes. In the originating dissertation it was used to: (i) compare nine LLMs from four providers (OpenAI, DeepSeek, Meta and Alibaba, including three open-weights models) under few-shot prompting with structured output against ten supervised models (BiLSTM-CRF, BERTimbau *base* and *large*, and seven encoders with legal or governmental pre-training) under 5-fold cross-validation; (ii) evaluate the impact of the structured-output mechanism (function calling vs. JSON schema) and of three prompting techniques (static few-shot, chain-of-thought, two-stage); (iii) study annotation-error detection with cleanlab; (iv) assess statistical significance via paired document-level bootstrap; and (v) conduct an inter-annotator agreement study with three independent annotations of the corpus.

**Is there a repository that links to any or all papers or systems that use the dataset?**

The repository `https://github.com/eduardoplima/decicontas.br/` gathers the dataset, the code and the results; future uses will be listed in the README.

**What (other) tasks could the dataset be used for?**

Beyond NER: structured extraction of decision attributes (amounts, deadlines, responsible parties — the repository includes Pydantic schemas for this); decision classification (informative vs. no registrable command); research on domain adaptation for legal-administrative Portuguese; few-shot learning studies in a low-annotation regime; methodological research on annotation-error detection (using the before/after correction pair); and pre-training or evaluation of models for the Court-of-Accounts decision genre.

**Is there anything about the composition of the dataset or the way it was collected and preprocessed/cleaned/labelled that might impact future uses?**

Yes, four points: (i) **imbalance** — MULTA concentrates ~46% of entities and 73.0% of documents are empty; micro F1 is dominated by the majority class and by the ability to abstain, so macro span F1 and the informative-subset analysis are recommended; (ii) **single-annotator gold standard** — the agreement study with two independent annotators (pairwise span F1 0.776–0.838) provides a human reference ceiling, but divergences were not adjudicated (particularly for RECOMENDACAO, the class with the lowest agreement against the gold), and the 227 groups below the audit review threshold keep their original label; (iii) **institutional and temporal scope** — a single court (TCE/RN), with 86.9% of the decisions from 2024; transfer to other Courts of Accounts, with different decision templates, must be validated empirically; (iv) **CPF masking** — models trained on the corpus will never see real CPF numbers, which affects uses that depend on that numeric pattern. The corpus vocabulary is also distant from judicial corpora (Jaccard of 0.29 with LeNER-Br over the 5,000 most frequent types), which limits direct comparisons.

**Are there tasks for which the dataset should not be used?**

Yes. The dataset must **not** be used to: identify, profile or score individuals named in the decisions (including attempts to re-identify the masked CPF numbers); build rankings or judgements about public officials from the sanctions mentioned — the decisions reflect one procedural moment and may have been reversed on appeal or review, and the dataset records neither finality nor the current state of each case; or serve as an authoritative source of the decisions in force — for official purposes, consult the original TCE/RN publication.

**Any other comments?**

None.

---

## 6. Distribution

**Will the dataset be distributed to third parties outside of the entity on behalf of which it was created?**

Yes. The dataset is public, as an academic artefact accompanying the dissertation.

**How will the dataset be distributed (tarball on a website, API, GitHub)? Does it have a digital object identifier (DOI)?**

Through the GitHub repository (`https://github.com/eduardoplima/decicontas.br/`), under `dataset/release/`, in four formats per version: JSON (array with text, tokens, BIO, offsets and entities), JSONL (compatible with the HuggingFace `datasets` library, with a `dataset_info.json` declaring the `ClassLabel` features), CoNLL-2003 BIO and BRAT standoff. `MANIFEST.json` lists the SHA-256 of every file. The BRAT trees are not versioned in git; they are regenerated by `research.release.export_dataset` and shipped as release assets. A DOI is being minted by depositing the release in Zenodo.

**When will the dataset be distributed?**

The repository is already public; the formal release (with citation and DOI) accompanies the publication of the dissertation, expected in 2026.

**Will the dataset be distributed under a copyright or other intellectual property (IP) licence, and/or under applicable terms of use?**

The decision texts are official acts, not protected by copyright (art. 8, IV of Brazilian Law 9,610/1998). The annotations and derived artefacts are distributed under CC BY 4.0; the repository code is under the MIT licence (see `LICENSE`).

**Have any third parties imposed IP-based or other restrictions on the data associated with the instances?**

No. There is no third-party data subject to contractual or IP restriction.

**Do any export controls or other regulatory restrictions apply to the dataset or to individual instances?**

There are no export controls. Processing of personal data contained in the public documents observes the LGPD (see Section 3).

**Any other comments?**

None.

---

## 7. Maintenance

**Who will be supporting/hosting/maintaining the dataset?**

The author, through the GitHub repository.

**How can the owner/curator/manager of the dataset be contacted (e.g., email address)?**

Eduardo Pereira Lima — `eduardo.lima.059@ufrn.edu.br`, or through issues in the GitHub repository.

**Is there an erratum?**

Yes, in practice: the file `dataset/errors/dataset-corrections.json` documents, decision by decision, every label correction applied after the cleanlab audit, and the version pair `decicontas-before-correction`/`decicontas` materialises the before/after. Future corrections will follow the same mechanism, recorded in the release README.

**Will the dataset be updated (to correct labelling errors, add or remove instances)?**

Yes, if needed. Label corrections identified by users or by new audit rounds will be incorporated through the versioned corrections file and a new release regenerated deterministically (`research.release.export_dataset`), with `MANIFEST.json` updated. Updates will be communicated through the GitHub repository history (commits and releases).

**If the dataset relates to people, are there applicable limits on the retention of the data (were individuals told their data would be retained for a fixed period)?**

There is no retention period: the source documents are public by nature and permanently retained by the Court. Requests grounded in the LGPD concerning personal data can be addressed to the maintainer and will be assessed case by case.

**Will older versions of the dataset continue to be supported/hosted/maintained?**

Yes. The pre-correction version (`decicontas-before-correction`) is a permanent part of the release, and the Git history preserves every previous state of the artefacts. Should a version be discontinued, this will be announced in the README.

**If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so?**

Yes: issues and pull requests in the GitHub repository. Annotation contributions will be validated by the maintainer against the delimitation guidelines of the scheme (Chapter 4 of the dissertation) and, where applicable, submitted to the same automated audit procedure before being incorporated into a new release.

**Any other comments?**

None.
