"""``GET /api/v1/reviews/{kind}/{id}`` (detail) +
``GET /api/v1/reviews/{kind}/{id}/texto-acordao`` (full text + span match).

The two are split so the fast-path detail (form + identifiers) doesn't block
on the slow MSSQL ``texto_acordao`` query.
"""

from __future__ import annotations


def test_get_detail_loads_without_texto_acordao(
    authenticated_client, make_staging_obrigacao
) -> None:
    """Detail endpoint must respond fast (no MSSQL hit) and not carry
    texto_acordao at all — that's a separate request.
    """
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()

    resp = client.get(f"/api/v1/reviews/obrigacao/{staged['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == staged["id"]
    assert body["kind"] == "obrigacao"
    assert body["status"] == "pending"
    # Schema dropped these from ReviewDetail.
    assert "texto_acordao" not in body
    assert "matched_span" not in body
    assert "span_match_status" not in body


def test_get_texto_reports_not_found_when_texto_unavailable(
    authenticated_client, make_staging_obrigacao
) -> None:
    """Without MSSQL available, ``_load_texto_acordao`` returns None and the
    texto endpoint must respond with ``span_match_status='not_found'`` rather
    than 500-ing."""
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()

    resp = client.get(f"/api/v1/reviews/obrigacao/{staged['id']}/texto-acordao")
    assert resp.status_code == 200
    body = resp.json()
    assert body["texto_acordao"] is None
    assert body["matched_span"] is None
    assert body["span_match_status"] == "not_found"


def test_get_texto_reports_exact_span_when_texto_mocked(
    authenticated_client, make_staging_obrigacao, mocker
) -> None:
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao(
        descricao="adotar providências corretivas no prazo de 90 dias"
    )
    mocker.patch(
        "app.review.service._load_texto_acordao",
        return_value=(
            "Acórdão fictício. Determina adotar providências corretivas "
            "no prazo de 90 dias, sob pena de multa."
        ),
    )

    resp = client.get(f"/api/v1/reviews/obrigacao/{staged['id']}/texto-acordao")
    assert resp.status_code == 200
    body = resp.json()
    assert body["span_match_status"] == "exact"
    assert "adotar providências" in body["matched_span"]


def test_get_returns_404_for_unknown_id(authenticated_client) -> None:
    client, _, _ = authenticated_client(username="alice")
    resp = client.get("/api/v1/reviews/obrigacao/999999")
    assert resp.status_code == 404


def test_get_texto_returns_404_for_unknown_id(authenticated_client) -> None:
    client, _, _ = authenticated_client(username="alice")
    resp = client.get("/api/v1/reviews/obrigacao/999999/texto-acordao")
    assert resp.status_code == 404
