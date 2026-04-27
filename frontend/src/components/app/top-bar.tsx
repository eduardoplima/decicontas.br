"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { currentUserQueryKey } from "@/hooks/use-current-user";
import { clearTokens, getRefreshToken } from "@/lib/auth";
import { logout as logoutRequest } from "@/lib/auth-api";
import { UserOut } from "@/schemas/auth";

export function TopBar({ user }: { user: UserOut | null }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await logoutRequest(refreshToken);
      } catch {
        // Best-effort: even if the backend call fails we still clear locally.
      }
    }
    clearTokens();
    queryClient.setQueryData(currentUserQueryKey, null);
    queryClient.clear();
    router.replace("/login");
  }

  return (
    <header className="flex items-center justify-between border-b bg-background px-6 py-3">
      <div className="flex items-center gap-6">
        <h1 className="text-lg font-semibold">DeciContas</h1>
        <nav className="flex items-center gap-4 text-sm">
          <Link
            href="/reviews"
            className="text-muted-foreground hover:text-foreground"
          >
            Revisões
          </Link>
          {user?.role === "admin" ? (
            <Link
              href="/etl"
              className="text-muted-foreground hover:text-foreground"
            >
              Extrações
            </Link>
          ) : null}
        </nav>
      </div>
      <div className="flex items-center gap-4">
        {user ? (
          <span className="text-sm text-muted-foreground">{user.username}</span>
        ) : null}
        <Button variant="outline" size="sm" onClick={handleLogout}>
          Sair
        </Button>
      </div>
    </header>
  );
}
