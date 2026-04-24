import { AxiosError } from "axios";

/**
 * Map a backend error to a Portuguese user-facing message.
 *
 * The backend currently returns free-form English `detail` strings rather
 * than structured error codes (see backend/app/review/service.py). We match
 * by (status, detail substring). When a machine-readable code replaces the
 * string, collapse this file to a code → message table.
 */
export function messageForError(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const data = error.response?.data as
      | { detail?: string | unknown }
      | undefined;
    const detail = typeof data?.detail === "string" ? data.detail : "";

    if (error.code === "ERR_NETWORK") {
      return "Não foi possível conectar ao servidor.";
    }

    if (status === 401) return "Sessão expirada. Entre novamente.";
    if (status === 403) {
      if (detail.includes("no active claim")) {
        return "A reserva deste item expirou ou foi perdida.";
      }
      return "Você não tem permissão para esta ação.";
    }
    if (status === 404) return "Item não encontrado.";
    if (status === 409) {
      if (detail.toLowerCase().startsWith("claimed by")) {
        return "Item já está reservado por outro revisor.";
      }
      if (detail.startsWith("review is ")) {
        return "Este item já foi revisado.";
      }
      return "Conflito ao executar a ação.";
    }
    if (status === 422) return "Dados inválidos. Verifique os campos.";
    if (status && status >= 500) {
      return "O servidor está indisponível. Tente novamente em instantes.";
    }
  }

  return fallback;
}
