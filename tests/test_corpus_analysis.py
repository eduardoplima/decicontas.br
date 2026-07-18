"""Unit tests for research.release.corpus_analysis on a tiny in-memory corpus."""

from __future__ import annotations


def _docs():
    # Doc 1: MULTA + OBRIGACAO (co-occurrence), spans near the end.
    text1 = "considerando os autos do processo julgo procedente e aplico multa de mil reais"
    # "aplico multa de mil reais" -> chars 53..78 ; "julgo procedente" -> 34..50
    # Doc 2: single RECOMENDACAO at the start.
    text2 = "recomendar ao gestor a adoção de providências cabíveis"
    # Doc 3: no entities.
    return [
        {
            "id": 1,
            "text": text1,
            "tokens": text1.split(),
            "entities": [
                {"start": 53, "end": 78, "label": "MULTA"},
                {"start": 34, "end": 50, "label": "OBRIGACAO"},
            ],
        },
        {
            "id": 2,
            "text": text2,
            "tokens": text2.split(),
            "entities": [{"start": 0, "end": 54, "label": "RECOMENDACAO"}],
        },
        {"id": 3, "text": "arquivamento puro e simples", "tokens": [], "entities": []},
    ]


def test_entities_per_document_histogram():
    from research.release.corpus_analysis import entities_per_document

    per_doc, hist = entities_per_document(_docs())
    assert len(per_doc) == 3
    assert per_doc.set_index("doc_id").loc[1, "n_entities"] == 2
    assert per_doc.set_index("doc_id").loc[3, "n_entities"] == 0
    h = hist.set_index("n_entities")["n_docs"]
    assert h["0"] == 1 and h["1"] == 1 and h["2"] == 1 and h["3+"] == 0
    # Histogram covers every document exactly once.
    assert int(hist["n_docs"].sum()) == 3


def test_class_cooccurrence_symmetric():
    from research.release.corpus_analysis import class_cooccurrence

    m = class_cooccurrence(_docs())
    assert m.loc["MULTA", "MULTA"] == 1  # one doc contains MULTA
    assert m.loc["MULTA", "OBRIGACAO"] == 1
    assert m.loc["OBRIGACAO", "MULTA"] == 1
    assert m.loc["RECOMENDACAO", "RECOMENDACAO"] == 1
    assert m.loc["MULTA", "RECOMENDACAO"] == 0


def test_span_positions_relative():
    from research.release.corpus_analysis import span_positions

    long_df, summary = span_positions(_docs())
    assert len(long_df) == 3
    rec = long_df[long_df["label"] == "RECOMENDACAO"].iloc[0]
    assert rec["start_rel"] == 0.0
    multa = long_df[long_df["label"] == "MULTA"].iloc[0]
    assert multa["center_rel"] > 0.5  # multa span sits in the second half
    assert set(summary["label"]) == {"MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO"}


def test_span_initial_ngrams():
    from research.release.corpus_analysis import span_initial_ngrams

    df = span_initial_ngrams(_docs(), n_max=2, top_k=5)
    uni = df[(df["label"] == "MULTA") & (df["n"] == 1)]
    assert uni.iloc[0]["ngram"] == "aplico"
    bi = df[(df["label"] == "RECOMENDACAO") & (df["n"] == 2)]
    assert bi.iloc[0]["ngram"] == "recomendar ao"


def test_performative_verbs():
    from research.release.corpus_analysis import performative_verbs

    df = performative_verbs(_docs()).set_index("stem")
    assert df.loc["aplic", "MULTA_spans"] == 1
    assert df.loc["recomend", "RECOMENDACAO_spans"] == 1
    assert df.loc["julg", "OBRIGACAO_spans"] == 1
    # doc_rate counts whole-document presence, not span presence.
    assert df.loc["julg", "docs_with_stem"] == 1
