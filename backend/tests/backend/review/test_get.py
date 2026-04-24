"""``GET /api/v1/reviews/{kind}/{id}`` — detail + span-match status."""

from __future__ import annotations


def test_get_detail_reports_not_found_when_texto_acordao_unavailable(
    authenticated_client, make_staging_obrigacao
) -> None:
    """Without MSSQL available, ``_load_texto_acordao`` returns None.
    The endpoint must still respond with ``span_match_status='not_found'``
    and null ``texto_acordao`` rather than 500-ing.
    """
    client, _, _ = authenticated_client(username="alice")
    staged = make_staging_obrigacao()

    resp = client.get(f"/api/v1/reviews/obrigacao/{staged['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == staged["id"]
    assert body["kind"] == "obrigacao"
    assert body["status"] == "pending"
    assert body["texto_acordao"] is None
    assert body["matched_span"] is None
    assert body["span_match_status"] == "not_found"


def test_get_detail_reports_exact_span_when_texto_acordao_mocked(
    authenticated_client, make_staging_obrigacao, mocker
) -> None:
    """With a known ``texto_acordao`` containing the descricao verbatim,
    ``span_match_status`` must be ``exact``."""
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

    resp = client.get(f"/api/v1/reviews/obrigacao/{staged['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["span_match_status"] == "exact"
    assert "adotar providências" in body["matched_span"]


def test_get_returns_404_for_unknown_id(authenticated_client) -> None:
    client, _, _ = authenticated_client(username="alice")
    resp = client.get("/api/v1/reviews/obrigacao/999999")
    assert resp.status_code == 404
