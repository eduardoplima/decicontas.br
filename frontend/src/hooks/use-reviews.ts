"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveObrigacao,
  approveRecomendacao,
  claimReview,
  getReview,
  getReviewTexto,
  listReviews,
  rejectReview,
  releaseReview,
} from "@/lib/reviews-api";
import { useCurrentUser } from "@/hooks/use-current-user";
import {
  ClaimResponse,
  ObrigacaoReview,
  RecomendacaoReview,
  ReviewDetail,
  ReviewKind,
  ReviewStatus,
} from "@/schemas/review";

export const reviewKeys = {
  all: ["reviews"] as const,
  list: (args: {
    kind: ReviewKind;
    status: ReviewStatus;
    page: number;
    pageSize: number;
  }) => ["reviews", "list", args] as const,
  detail: (kind: ReviewKind, id: number) =>
    ["reviews", "detail", kind, id] as const,
  texto: (kind: ReviewKind, id: number) =>
    ["reviews", "texto", kind, id] as const,
};

type ListArgs = {
  kind: ReviewKind;
  status?: ReviewStatus;
  page?: number;
  pageSize?: number;
};

export function useReviews({
  kind,
  status = "pending",
  page = 1,
  pageSize = 20,
}: ListArgs) {
  return useQuery({
    queryKey: reviewKeys.list({ kind, status, page, pageSize }),
    queryFn: () => listReviews({ kind, status, page, pageSize }),
  });
}

type IdArgs = { kind: ReviewKind; id: number };

export function useReview({ kind, id }: IdArgs) {
  return useQuery({
    queryKey: reviewKeys.detail(kind, id),
    queryFn: () => getReview({ kind, id }),
  });
}

export function useReviewTexto({ kind, id }: IdArgs) {
  return useQuery({
    queryKey: reviewKeys.texto(kind, id),
    queryFn: () => getReviewTexto({ kind, id }),
    // Texto can be slow (MSSQL); don't refetch automatically.
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
    retry: 1,
  });
}

export function useClaim({ kind, id }: IdArgs) {
  const queryClient = useQueryClient();
  const { data: me } = useCurrentUser();

  return useMutation({
    mutationFn: () => claimReview({ kind, id }),
    onMutate: async () => {
      // Optimistic: paint ourselves as the claimant immediately so the
      // banner doesn't flash.
      await queryClient.cancelQueries({
        queryKey: reviewKeys.detail(kind, id),
      });
      const prev = queryClient.getQueryData<ReviewDetail>(
        reviewKeys.detail(kind, id),
      );
      if (prev && me) {
        const now = new Date().toISOString();
        queryClient.setQueryData<ReviewDetail>(reviewKeys.detail(kind, id), {
          ...prev,
          claimed_by: me.username,
          claimed_at: now,
        });
      }
      return { prev };
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) {
        queryClient.setQueryData(reviewKeys.detail(kind, id), context.prev);
      }
    },
    onSuccess: (claim: ClaimResponse) => {
      const prev = queryClient.getQueryData<ReviewDetail>(
        reviewKeys.detail(kind, id),
      );
      if (prev) {
        queryClient.setQueryData<ReviewDetail>(reviewKeys.detail(kind, id), {
          ...prev,
          claimed_by: claim.claimed_by,
          claimed_at: claim.claimed_at,
        });
      }
    },
  });
}

export function useRelease({ kind, id }: IdArgs) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => releaseReview({ kind, id }),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.all });
    },
  });
}

export function useApprove({ kind, id }: IdArgs) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ObrigacaoReview | RecomendacaoReview) =>
      kind === "obrigacao"
        ? approveObrigacao(id, payload as ObrigacaoReview)
        : approveRecomendacao(id, payload as RecomendacaoReview),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.all });
    },
  });
}

export function useReject({ kind, id }: IdArgs) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reviewNotes: string) =>
      rejectReview({ kind, id }, reviewNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reviewKeys.all });
    },
  });
}
