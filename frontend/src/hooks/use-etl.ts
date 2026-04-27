"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getExtracao,
  listExtracoes,
  triggerExtraction,
} from "@/lib/etl-api";
import { ExtracaoOut, ExtractionTriggerRequest } from "@/schemas/etl";

export const etlKeys = {
  all: ["etl"] as const,
  extracoes: (args: { page: number; pageSize: number }) =>
    ["etl", "extracoes", args] as const,
  extracao: (id: number) => ["etl", "extracao", id] as const,
};

type ListArgs = { page?: number; pageSize?: number };

export function useExtracoes({ page = 1, pageSize = 20 }: ListArgs = {}) {
  return useQuery({
    queryKey: etlKeys.extracoes({ page, pageSize }),
    queryFn: () => listExtracoes({ page, pageSize }),
  });
}

export function useTriggerExtraction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["etl", "trigger"],
    mutationFn: (body: ExtractionTriggerRequest) => triggerExtraction(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: etlKeys.all });
    },
  });
}

/** Polls one ``Extracao`` row every 3s while the run is queued or running.
 * Stops once the row reaches ``done`` or ``error``.
 */
export function useExtracao(id: number | null) {
  return useQuery<ExtracaoOut>({
    queryKey: id !== null ? etlKeys.extracao(id) : ["etl", "extracao", "null"],
    queryFn: () => getExtracao(id as number),
    enabled: id !== null,
    refetchInterval: (query) => {
      const data = query.state.data as ExtracaoOut | undefined;
      if (!data) return 3000;
      return data.status === "queued" || data.status === "running"
        ? 3000
        : false;
    },
    refetchIntervalInBackground: false,
  });
}
