import { z } from "zod";

// Mirrors DTOs in backend/app/etl/schemas.py.

const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, { message: "Use o formato AAAA-MM-DD." });

// Mirrors ExtractionFiltersBody.
export const extractionFiltersSchema = z.object({
  start_date: isoDateSchema,
  end_date: isoDateSchema,
  process_numbers: z.array(z.string()).nullable().optional(),
  overwrite: z.boolean().optional().default(false),
});
export type ExtractionFilters = z.infer<typeof extractionFiltersSchema>;

// Mirrors ExtractionTriggerRequest. Single-shot orchestration — no kind.
export const extractionTriggerRequestSchema = z.object({
  filters: extractionFiltersSchema,
});
export type ExtractionTriggerRequest = z.infer<
  typeof extractionTriggerRequestSchema
>;

// Mirrors ExtractionJobAccepted.
export const extractionJobAcceptedSchema = z.object({
  extracao_id: z.number().int(),
  job_id: z.string(),
  status_url: z.string(),
  enqueued_at: z.string(),
});
export type ExtractionJobAccepted = z.infer<
  typeof extractionJobAcceptedSchema
>;

export const runStatusSchema = z.enum(["queued", "running", "done", "error"]);
export type RunStatus = z.infer<typeof runStatusSchema>;

export const etapaSchema = z.enum([
  "queued",
  "decisoes",
  "obrigacoes",
  "recomendacoes",
  "done",
]);
export type Etapa = z.infer<typeof etapaSchema>;

// Mirrors ExtracaoOut.
export const extracaoOutSchema = z.object({
  id: z.number().int(),
  data_inicio: isoDateSchema,
  data_fim: isoDateSchema,
  data_execucao: z.string(),
  status: runStatusSchema,
  etapa_atual: etapaSchema,
  decisoes_processadas: z.number().int(),
  obrigacoes_geradas: z.number().int(),
  recomendacoes_geradas: z.number().int(),
  erros: z.number().int(),
  mensagem_erro: z.string().nullable().optional(),
  job_id: z.string().nullable().optional(),
});
export type ExtracaoOut = z.infer<typeof extracaoOutSchema>;

// Mirrors ExtracaoListPage.
export const extracaoListPageSchema = z.object({
  items: z.array(extracaoOutSchema),
  page: z.number().int(),
  page_size: z.number().int(),
  total: z.number().int(),
});
export type ExtracaoListPage = z.infer<typeof extracaoListPageSchema>;

// Form: dates only, end >= start.
export const triggerFormSchema = z
  .object({
    start_date: isoDateSchema,
    end_date: isoDateSchema,
  })
  .refine((v) => v.end_date >= v.start_date, {
    message: "A data final deve ser igual ou posterior à inicial.",
    path: ["end_date"],
  });
export type TriggerForm = z.infer<typeof triggerFormSchema>;
