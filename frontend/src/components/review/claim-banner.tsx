"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ClaimBannerProps = {
  currentUsername: string | null;
  claimedBy: string | null;
  claimedAt: string | null;
  // Hard-coded TTL for display; backend is authoritative on expiry (15 min).
  ttlMinutes?: number;
  onReclaim: () => void;
  onBack: () => void;
  isReclaiming?: boolean;
};

function formatCountdown(ms: number): string {
  if (ms <= 0) return "00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const mm = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const ss = String(totalSeconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function ClaimBanner({
  currentUsername,
  claimedBy,
  claimedAt,
  ttlMinutes = 15,
  onReclaim,
  onBack,
  isReclaiming,
}: ClaimBannerProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const handle = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(handle);
  }, []);

  const claimedAtMs = claimedAt ? Date.parse(claimedAt) : null;
  const expiresAtMs = claimedAtMs ? claimedAtMs + ttlMinutes * 60_000 : null;
  const remainingMs = expiresAtMs !== null ? expiresAtMs - now : 0;

  const isOwn = !!claimedBy && claimedBy === currentUsername;
  const isExpired = expiresAtMs !== null && remainingMs <= 0;
  const lost = !isOwn || isExpired;

  if (!claimedBy) {
    return (
      <div className="flex items-center justify-between rounded-md border bg-muted px-4 py-2 text-sm">
        <span>
          Item sem reserva. Clique em &ldquo;Reservar&rdquo; para iniciar.
        </span>
        <Button
          size="sm"
          onClick={onReclaim}
          disabled={isReclaiming}
          data-testid="claim-banner-reclaim"
        >
          {isReclaiming ? "Reservando..." : "Reservar"}
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-md border px-4 py-2 text-sm",
        lost
          ? "border-amber-500 bg-amber-50"
          : "border-emerald-500 bg-emerald-50",
      )}
      data-testid="claim-banner"
    >
      <div className="flex flex-col">
        <span>
          {isOwn ? "Reservado por você" : `Reservado por ${claimedBy}`}
        </span>
        <span
          className="text-xs text-muted-foreground"
          data-testid="claim-banner-countdown"
        >
          {isExpired
            ? "Reserva expirada."
            : `Expira em ${formatCountdown(remainingMs)}`}
        </span>
      </div>
      {lost ? (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onBack}>
            Voltar para lista
          </Button>
          <Button
            size="sm"
            onClick={onReclaim}
            disabled={isReclaiming}
            data-testid="claim-banner-reclaim"
          >
            {isReclaiming ? "Reservando..." : "Reclamar"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
