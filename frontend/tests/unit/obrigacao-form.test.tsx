import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  ObrigacaoForm,
  useObrigacaoForm,
} from "@/components/review/obrigacao-form";
import { ObrigacaoReview } from "@/schemas/review";

function Harness({
  staged,
  onApprove,
  onReject,
}: {
  staged: Record<string, unknown>;
  onApprove: (payload: ObrigacaoReview) => void;
  onReject: () => void;
}) {
  const form = useObrigacaoForm(staged);
  return (
    <ObrigacaoForm form={form} onApprove={onApprove} onReject={onReject} />
  );
}

describe("ObrigacaoForm", () => {
  it("submits a payload with every DTO field after user edits", async () => {
    const onApprove = vi.fn();
    const user = userEvent.setup();

    const staged = {
      id_processo: 101,
      id_composicao_pauta: 202,
      id_voto_pauta: 303,
      descricao_obrigacao: "Texto inicial",
      de_fazer: true,
      tem_multa_cominatoria: false,
    };

    render(
      <Harness staged={staged} onApprove={onApprove} onReject={() => {}} />,
    );

    const descricao = screen.getByLabelText(
      "Descrição da obrigação",
    ) as HTMLTextAreaElement;
    await user.clear(descricao);
    await user.type(descricao, "Nova descrição da obrigação.");

    await user.type(screen.getByLabelText("Prazo"), "30 dias");
    await user.type(screen.getByLabelText("Data de cumprimento"), "2026-12-31");
    await user.type(
      screen.getByLabelText("Órgão responsável"),
      "Secretaria de Saúde",
    );

    await user.click(screen.getByTestId("approve-button"));

    await waitFor(() => expect(onApprove).toHaveBeenCalledOnce());

    const payload = onApprove.mock.calls[0][0] as Record<string, unknown>;
    expect(payload).toEqual(
      expect.objectContaining({
        id_processo: 101,
        id_composicao_pauta: 202,
        id_voto_pauta: 303,
        descricao_obrigacao: "Nova descrição da obrigação.",
        de_fazer: true,
        tem_multa_cominatoria: false,
        prazo: "30 dias",
        data_cumprimento: "2026-12-31",
        orgao_responsavel: "Secretaria de Saúde",
      }),
    );
    // Fields untouched by the user come through as null / default.
    expect(payload).toHaveProperty("valor_multa_cominatoria", null);
    expect(payload).toHaveProperty("e_multa_cominatoria_solidaria", false);
  });

  it("blocks submission with an empty descricao_obrigacao", async () => {
    const onApprove = vi.fn();
    const user = userEvent.setup();

    render(<Harness staged={{}} onApprove={onApprove} onReject={() => {}} />);

    await user.click(screen.getByTestId("approve-button"));

    expect(
      await screen.findByText("Descreva a obrigação."),
    ).toBeInTheDocument();
    expect(onApprove).not.toHaveBeenCalled();
  });
});
