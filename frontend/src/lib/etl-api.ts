import { apiClient } from "@/lib/api-client";
import {
  ExtracaoListPage,
  extracaoListPageSchema,
  ExtracaoOut,
  extracaoOutSchema,
  ExtractionJobAccepted,
  extractionJobAcceptedSchema,
  ExtractionTriggerRequest,
} from "@/schemas/etl";

export async function triggerExtraction(
  body: ExtractionTriggerRequest,
): Promise<ExtractionJobAccepted> {
  const response = await apiClient.post("/api/v1/etl/run", body);
  return extractionJobAcceptedSchema.parse(response.data);
}

type ListArgs = { page?: number; pageSize?: number };

export async function listExtracoes({
  page = 1,
  pageSize = 20,
}: ListArgs = {}): Promise<ExtracaoListPage> {
  const response = await apiClient.get("/api/v1/etl/extracoes", {
    params: { page, page_size: pageSize },
  });
  return extracaoListPageSchema.parse(response.data);
}

export async function getExtracao(id: number): Promise<ExtracaoOut> {
  const response = await apiClient.get(`/api/v1/etl/extracoes/${id}`);
  return extracaoOutSchema.parse(response.data);
}
