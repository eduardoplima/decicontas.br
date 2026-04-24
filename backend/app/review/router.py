"""Review router. All endpoints under ``/api/v1/reviews``, JWT-authenticated.

Thin wrappers over ``app.review.service``. RFC 7807-compatible errors come
from ``HTTPException`` — FastAPI serializes them as ``{"detail": "..."}``.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db_session
from app.review import schemas, service
from tools.etl.staging import ReviewStatus
from tools.models import UserORM


router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.get("", response_model=schemas.ReviewListPage)
def list_reviews(
    kind: Literal["obrigacao", "recomendacao"],
    status_filter: Literal["pending", "approved", "rejected"] = Query(
        "pending", alias="status"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> schemas.ReviewListPage:
    return service.list_reviews(
        session,
        kind=kind,
        status_filter=ReviewStatus(status_filter),
        page=page,
        page_size=page_size,
        current_user=current_user,
    )


@router.get("/{kind}/{id}", response_model=schemas.ReviewDetail)
def get_review(
    kind: Literal["obrigacao", "recomendacao"],
    id: int,
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> schemas.ReviewDetail:
    return service.get_review(session, kind=kind, id=id, current_user=current_user)


@router.post("/{kind}/{id}/claim", response_model=schemas.ClaimResponse)
def claim_review(
    kind: Literal["obrigacao", "recomendacao"],
    id: int,
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> schemas.ClaimResponse:
    return service.claim(session, kind=kind, id=id, current_user=current_user)


@router.post("/{kind}/{id}/release", status_code=status.HTTP_204_NO_CONTENT)
def release_review(
    kind: Literal["obrigacao", "recomendacao"],
    id: int,
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> None:
    service.release(session, kind=kind, id=id, current_user=current_user)


@router.post("/obrigacao/{id}/approve", response_model=schemas.ReviewDetail)
def approve_obrigacao(
    id: int,
    payload: schemas.ObrigacaoReview,
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> schemas.ReviewDetail:
    return service.approve_obrigacao(
        session, id=id, payload=payload, current_user=current_user
    )


@router.post("/recomendacao/{id}/approve", response_model=schemas.ReviewDetail)
def approve_recomendacao(
    id: int,
    payload: schemas.RecomendacaoReview,
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> schemas.ReviewDetail:
    return service.approve_recomendacao(
        session, id=id, payload=payload, current_user=current_user
    )


@router.post("/{kind}/{id}/reject", response_model=schemas.ReviewDetail)
def reject_review(
    kind: Literal["obrigacao", "recomendacao"],
    id: int,
    body: schemas.RejectRequest,
    session: Session = Depends(get_db_session),
    current_user: UserORM = Depends(get_current_user),
) -> schemas.ReviewDetail:
    return service.reject(
        session,
        kind=kind,
        id=id,
        notes=body.review_notes,
        current_user=current_user,
    )
