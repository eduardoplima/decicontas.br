import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ClaimBanner } from "@/components/review/claim-banner";

describe("ClaimBanner", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows 'no claim' empty state with a Reservar button", () => {
    const onReclaim = vi.fn();
    render(
      <ClaimBanner
        currentUsername="alice"
        claimedBy={null}
        claimedAt={null}
        onReclaim={onReclaim}
        onBack={() => {}}
      />,
    );
    expect(screen.getByText(/Item sem reserva/i)).toBeInTheDocument();
    screen.getByTestId("claim-banner-reclaim").click();
    expect(onReclaim).toHaveBeenCalledOnce();
  });

  it("counts down from a fresh claim and shows 'Reservado por você'", () => {
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    render(
      <ClaimBanner
        currentUsername="alice"
        claimedBy="alice"
        claimedAt="2026-01-01T12:00:00Z"
        ttlMinutes={15}
        onReclaim={() => {}}
        onBack={() => {}}
      />,
    );

    expect(screen.getByText(/Reservado por você/i)).toBeInTheDocument();
    expect(screen.getByTestId("claim-banner-countdown")).toHaveTextContent(
      "Expira em 15:00",
    );

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(screen.getByTestId("claim-banner-countdown")).toHaveTextContent(
      "Expira em 14:00",
    );
  });

  it("shows 'expirada' once the TTL elapses", () => {
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    render(
      <ClaimBanner
        currentUsername="alice"
        claimedBy="alice"
        claimedAt="2026-01-01T11:40:00Z"
        ttlMinutes={15}
        onReclaim={() => {}}
        onBack={() => {}}
      />,
    );

    expect(screen.getByTestId("claim-banner-countdown")).toHaveTextContent(
      "Reserva expirada.",
    );
  });

  it("marks the claim as lost when another reviewer holds it", () => {
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));
    const onReclaim = vi.fn();

    render(
      <ClaimBanner
        currentUsername="alice"
        claimedBy="bob"
        claimedAt="2026-01-01T11:58:00Z"
        ttlMinutes={15}
        onReclaim={onReclaim}
        onBack={() => {}}
      />,
    );

    expect(screen.getByText(/Reservado por bob/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Voltar para lista/i }),
    ).toBeInTheDocument();
    screen.getByTestId("claim-banner-reclaim").click();
    expect(onReclaim).toHaveBeenCalledOnce();
  });
});
