import { apiClient } from "@/lib/api-client";
import {
  ClaimResponse,
  claimResponseSchema,
  ObrigacaoReview,
  RecomendacaoReview,
  ReviewDetail,
  reviewDetailSchema,
  ReviewKind,
  ReviewListPage,
  reviewListPageSchema,
  ReviewStatus,
} from "@/schemas/review";

type ListArgs = {
  kind: ReviewKind;
  status?: ReviewStatus;
  page?: number;
  pageSize?: number;
};

export async function listReviews({
  kind,
  status = "pending",
  page = 1,
  pageSize = 20,
}: ListArgs): Promise<ReviewListPage> {
  const response = await apiClient.get("/api/v1/reviews", {
    params: { kind, status, page, page_size: pageSize },
  });
  return reviewListPageSchema.parse(response.data);
}

type IdArgs = { kind: ReviewKind; id: number };

export async function getReview({ kind, id }: IdArgs): Promise<ReviewDetail> {
  const response = await apiClient.get(`/api/v1/reviews/${kind}/${id}`);
  return reviewDetailSchema.parse(response.data);
}

export async function claimReview({
  kind,
  id,
}: IdArgs): Promise<ClaimResponse> {
  const response = await apiClient.post(`/api/v1/reviews/${kind}/${id}/claim`);
  return claimResponseSchema.parse(response.data);
}

export async function releaseReview({ kind, id }: IdArgs): Promise<void> {
  await apiClient.post(`/api/v1/reviews/${kind}/${id}/release`);
}

export async function approveObrigacao(
  id: number,
  payload: ObrigacaoReview,
): Promise<ReviewDetail> {
  const response = await apiClient.post(
    `/api/v1/reviews/obrigacao/${id}/approve`,
    payload,
  );
  return reviewDetailSchema.parse(response.data);
}

export async function approveRecomendacao(
  id: number,
  payload: RecomendacaoReview,
): Promise<ReviewDetail> {
  const response = await apiClient.post(
    `/api/v1/reviews/recomendacao/${id}/approve`,
    payload,
  );
  return reviewDetailSchema.parse(response.data);
}

export async function rejectReview(
  { kind, id }: IdArgs,
  reviewNotes: string,
): Promise<ReviewDetail> {
  const response = await apiClient.post(
    `/api/v1/reviews/${kind}/${id}/reject`,
    { review_notes: reviewNotes },
  );
  return reviewDetailSchema.parse(response.data);
}
