import { z } from "zod";

// All schemas in this file mirror DTOs in backend/app/review/schemas.py.
// Field names and types must stay one-to-one with the Pydantic source —
// mismatches cause silent data loss on approve.

export const reviewKindSchema = z.enum(["obrigacao", "recomendacao"]);
export type ReviewKind = z.infer<typeof reviewKindSchema>;

export const reviewStatusSchema = z.enum(["pending", "approved", "rejected"]);
export type ReviewStatus = z.infer<typeof reviewStatusSchema>;

export const spanMatchStatusSchema = z.enum(["exact", "fuzzy", "not_found"]);
export type SpanMatchStatus = z.infer<typeof spanMatchStatusSchema>;

// Pydantic `date` — ISO yyyy-mm-dd on the wire.
const isoDateSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, { message: "Data inválida." });

// Mirrors ObrigacaoReview in backend/app/review/schemas.py.
// Reviewer-editable fields one-to-one with ObrigacaoORM (minus the
// auto-assigned IdObrigacao PK). When ObrigacaoORM gains a new
// reviewer-editable column, the backend schema-parity test fails — update
// this schema in lockstep.
export const obrigacaoReviewSchema = z.object({
  id_processo: z.number().int().nullable().optional(),
  id_composicao_pauta: z.number().int().nullable().optional(),
  id_voto_pauta: z.number().int().nullable().optional(),

  descricao_obrigacao: z
    .string()
    .trim()
    .min(1, { message: "Descreva a obrigação." }),

  // Pydantic defaults (True/False) kick in server-side when a field is
  // absent; on the wire the type is still nullable. Defaults for the form
  // live in the toDefaults() helper in obrigacao-form.tsx.
  de_fazer: z.boolean().nullable().optional(),
  prazo: z.string().nullable().optional(),
  data_cumprimento: isoDateSchema.nullable().optional(),
  orgao_responsavel: z.string().nullable().optional(),
  id_orgao_responsavel: z.number().int().nullable().optional(),

  tem_multa_cominatoria: z.boolean().nullable().optional(),
  nome_responsavel_multa_cominatoria: z.string().nullable().optional(),
  documento_responsavel_multa_cominatoria: z.string().nullable().optional(),
  id_pessoa_multa_cominatoria: z.number().int().nullable().optional(),
  valor_multa_cominatoria: z.number().nullable().optional(),
  periodo_multa_cominatoria: z.string().nullable().optional(),
  e_multa_cominatoria_solidaria: z.boolean().nullable().optional(),
  solidarios_multa_cominatoria: z.array(z.string()).nullable().optional(),
});
export type ObrigacaoReview = z.infer<typeof obrigacaoReviewSchema>;

// Mirrors RecomendacaoReview in backend/app/review/schemas.py.
// Reviewer-editable fields one-to-one with RecomendacaoORM (minus the
// auto-assigned IdRecomendacao PK).
export const recomendacaoReviewSchema = z.object({
  id_processo: z.number().int().nullable().optional(),
  id_composicao_pauta: z.number().int().nullable().optional(),
  id_voto_pauta: z.number().int().nullable().optional(),

  descricao_recomendacao: z.string().nullable().optional(),
  prazo_cumprimento_recomendacao: z.string().nullable().optional(),
  data_cumprimento_recomendacao: isoDateSchema.nullable().optional(),
  nome_responsavel: z.string().nullable().optional(),
  id_pessoa_responsavel: z.number().int().nullable().optional(),
  orgao_responsavel: z.string().nullable().optional(),
  id_orgao_responsavel: z.number().int().nullable().optional(),
  cancelado: z.boolean().nullable().optional(),
});
export type RecomendacaoReview = z.infer<typeof recomendacaoReviewSchema>;

// Mirrors ReviewListItem in backend/app/review/schemas.py.
export const reviewListItemSchema = z.object({
  id: z.number().int(),
  kind: reviewKindSchema,
  status: reviewStatusSchema,
  descricao: z.string(),
  id_processo: z.number().int(),
  id_composicao_pauta: z.number().int(),
  id_voto_pauta: z.number().int(),
  claimed_by: z.string().nullable().optional(),
  claimed_at: z.string().datetime({ offset: true }).nullable().optional(),
  reviewer: z.string().nullable().optional(),
  reviewed_at: z.string().datetime({ offset: true }).nullable().optional(),
});
export type ReviewListItem = z.infer<typeof reviewListItemSchema>;

// Mirrors ReviewListPage in backend/app/review/schemas.py.
export const reviewListPageSchema = z.object({
  items: z.array(reviewListItemSchema),
  page: z.number().int(),
  page_size: z.number().int(),
  total: z.number().int(),
});
export type ReviewListPage = z.infer<typeof reviewListPageSchema>;

// Mirrors ReviewDetail in backend/app/review/schemas.py.
// `texto_acordao` and span-match metadata are fetched separately via
// reviewTextoSchema below — splitting these makes the form render fast
// while the (slow) MSSQL text query runs in parallel.
export const reviewDetailSchema = z.object({
  id: z.number().int(),
  kind: reviewKindSchema,
  status: reviewStatusSchema,

  id_processo: z.number().int(),
  id_composicao_pauta: z.number().int(),
  id_voto_pauta: z.number().int(),

  staged: z.record(z.string(), z.unknown()),
  original_payload: z.record(z.string(), z.unknown()).nullable().optional(),

  claimed_by: z.string().nullable().optional(),
  claimed_at: z.string().datetime({ offset: true }).nullable().optional(),
  reviewer: z.string().nullable().optional(),
  reviewed_at: z.string().datetime({ offset: true }).nullable().optional(),
  review_notes: z.string().nullable().optional(),
});
export type ReviewDetail = z.infer<typeof reviewDetailSchema>;

// Mirrors ReviewTexto in backend/app/review/schemas.py.
export const reviewTextoSchema = z.object({
  texto_acordao: z.string().nullable().optional(),
  matched_span: z.string().nullable().optional(),
  span_match_status: spanMatchStatusSchema,
});
export type ReviewTexto = z.infer<typeof reviewTextoSchema>;

// Mirrors ClaimResponse in backend/app/review/schemas.py.
export const claimResponseSchema = z.object({
  claimed_by: z.string(),
  claimed_at: z.string().datetime({ offset: true }),
  expires_at: z.string().datetime({ offset: true }),
});
export type ClaimResponse = z.infer<typeof claimResponseSchema>;

// Mirrors RejectRequest in backend/app/review/schemas.py.
export const rejectRequestSchema = z.object({
  review_notes: z
    .string()
    .trim()
    .min(10, { message: "Justifique com ao menos 10 caracteres." }),
});
export type RejectRequest = z.infer<typeof rejectRequestSchema>;
