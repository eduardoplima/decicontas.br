"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ReviewList } from "@/components/review/review-list";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useReviews } from "@/hooks/use-reviews";
import { messageForError } from "@/lib/error-messages";
import { ReviewKind } from "@/schemas/review";

const PAGE_SIZE = 20;

export default function ReviewsPage() {
  const [kind, setKind] = useState<ReviewKind>("obrigacao");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, error } = useReviews({
    kind,
    status: "pending",
    page,
    pageSize: PAGE_SIZE,
  });

  useEffect(() => {
    if (isError) {
      toast.error(messageForError(error, "Erro ao carregar itens pendentes."));
    }
  }, [isError, error]);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-4 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Itens pendentes</h1>
        <p className="text-sm text-muted-foreground">
          Aprove, edite ou rejeite obrigações e recomendações extraídas.
        </p>
      </div>

      <Tabs
        value={kind}
        onValueChange={(v) => {
          setKind(v as ReviewKind);
          setPage(1);
        }}
      >
        <TabsList>
          <TabsTrigger value="obrigacao">Obrigações</TabsTrigger>
          <TabsTrigger value="recomendacao">Recomendações</TabsTrigger>
        </TabsList>
      </Tabs>

      <ReviewList
        kind={kind}
        items={data?.items ?? []}
        page={page}
        pageSize={PAGE_SIZE}
        total={data?.total ?? 0}
        onPageChange={setPage}
        isLoading={isLoading}
      />
    </main>
  );
}
