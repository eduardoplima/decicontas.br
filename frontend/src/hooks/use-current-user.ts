"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCurrentUser } from "@/lib/auth-api";

export const currentUserQueryKey = ["auth", "me"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 5 * 60_000,
  });
}
