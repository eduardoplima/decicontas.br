"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { TopBar } from "@/components/app/top-bar";
import { useCurrentUser } from "@/hooks/use-current-user";
import { hasSession } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, isError } = useCurrentUser();

  useEffect(() => {
    // If there is no token at all, don't bother hitting /auth/me.
    if (!hasSession()) {
      router.replace("/login");
    }
  }, [router]);

  useEffect(() => {
    // The api-client will redirect on a 401 it can't recover from, but we
    // still guard against other failures (e.g. 403 on /me) explicitly.
    if (isError) {
      router.replace("/login");
    }
  }, [isError, router]);

  if (!hasSession() || isLoading || isError || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Carregando...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar user={user} />
      <div className="flex-1">{children}</div>
    </div>
  );
}
