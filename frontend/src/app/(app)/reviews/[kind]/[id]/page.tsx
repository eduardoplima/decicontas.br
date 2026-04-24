"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ClaimBanner } from "@/components/review/claim-banner";
import {
  ObrigacaoForm,
  useObrigacaoForm,
} from "@/components/review/obrigacao-form";
import {
  RecomendacaoForm,
  useRecomendacaoForm,
} from "@/components/review/recomendacao-form";
import { RejectDialog } from "@/components/review/reject-dialog";
import { SpanEditor } from "@/components/review/span-editor";
import { Button } from "@/components/ui/button";
import { useCurrentUser } from "@/hooks/use-current-user";
import {
  useApprove,
  useClaim,
  useReject,
  useRelease,
  useReview,
} from "@/hooks/use-reviews";
import { messageForError } from "@/lib/error-messages";
import {
  ObrigacaoReview,
  RecomendacaoReview,
  ReviewDetail,
  ReviewKind,
  reviewKindSchema,
} from "@/schemas/review";

const NOT_FOUND_HINT =
  "Trecho não encontrado no acórdão. Selecione manualmente o texto correspondente.";

export default function ReviewDetailPage() {
  const params = useParams<{ kind: string; id: string }>();
  const router = useRouter();
  const kindParse = reviewKindSchema.safeParse(params.kind);
  const id = Number(params.id);
  const kind: ReviewKind | null = kindParse.success ? kindParse.data : null;
  const idValid = Number.isFinite(id) && id > 0;

  useEffect(() => {
    if (!kind || !idValid) router.replace("/reviews");
  }, [kind, idValid, router]);

  if (!kind || !idValid) return null;

  return <Detail kind={kind} id={id} />;
}

function Detail({ kind, id }: { kind: ReviewKind; id: number }) {
  const router = useRouter();
  const { data: me } = useCurrentUser();
  const query = useReview({ kind, id });
  const claim = useClaim({ kind, id });
  const release = useRelease({ kind, id });
  const approve = useApprove({ kind, id });
  const reject = useReject({ kind, id });

  const [rejectOpen, setRejectOpen] = useState(false);

  const detail = query.data;

  // Claim on mount, release on unmount + tab close.
  useEffect(() => {
    claim.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      // Best-effort release. sendBeacon can't set the JWT header, so we
      // just fire the mutation; the backend's 15-min TTL covers missed
      // releases.
      release.mutate();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (query.isLoading || !detail) {
    return (
      <div className="flex flex-1 items-center justify-center p-10 text-sm text-muted-foreground">
        Carregando item...
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-10">
        <p className="text-sm">
          {messageForError(query.error, "Não foi possível carregar o item.")}
        </p>
        <Button variant="outline" onClick={() => router.push("/reviews")}>
          Voltar para a lista
        </Button>
      </div>
    );
  }

  return (
    <ReviewBody
      detail={detail}
      kind={kind}
      id={id}
      currentUsername={me?.username ?? null}
      onApprove={(payload) =>
        approve.mutate(payload, {
          onSuccess: () => {
            toast.success("Item aprovado.");
            router.replace("/reviews");
          },
          onError: (err) =>
            toast.error(messageForError(err, "Erro ao aprovar o item.")),
        })
      }
      onOpenReject={() => setRejectOpen(true)}
      approveSubmitting={approve.isPending}
      onReclaim={() =>
        claim.mutate(undefined, {
          onError: (err) =>
            toast.error(messageForError(err, "Não foi possível reservar.")),
        })
      }
      reclaimSubmitting={claim.isPending}
      onBackToList={() => router.push("/reviews")}
      rejectOpen={rejectOpen}
      onRejectOpenChange={setRejectOpen}
      onRejectConfirm={(notes) =>
        reject.mutate(notes, {
          onSuccess: () => {
            setRejectOpen(false);
            toast.success("Item rejeitado.");
            router.replace("/reviews");
          },
          onError: (err) =>
            toast.error(messageForError(err, "Erro ao rejeitar o item.")),
        })
      }
      rejectSubmitting={reject.isPending}
    />
  );
}

type ReviewBodyProps = {
  detail: ReviewDetail;
  kind: ReviewKind;
  id: number;
  currentUsername: string | null;
  onApprove: (payload: ObrigacaoReview | RecomendacaoReview) => void;
  onOpenReject: () => void;
  approveSubmitting: boolean;
  onReclaim: () => void;
  reclaimSubmitting: boolean;
  onBackToList: () => void;
  rejectOpen: boolean;
  onRejectOpenChange: (open: boolean) => void;
  onRejectConfirm: (notes: string) => void;
  rejectSubmitting: boolean;
};

function ReviewBody({
  detail,
  kind,
  currentUsername,
  onApprove,
  onOpenReject,
  approveSubmitting,
  onReclaim,
  reclaimSubmitting,
  onBackToList,
  rejectOpen,
  onRejectOpenChange,
  onRejectConfirm,
  rejectSubmitting,
}: ReviewBodyProps) {
  const holdsClaim =
    !!detail.claimed_by &&
    !!currentUsername &&
    detail.claimed_by === currentUsername;
  const formDisabled = !holdsClaim;

  const obrigacaoForm = useObrigacaoForm(detail.staged);
  const recomendacaoForm = useRecomendacaoForm(detail.staged);

  function handleSpanChange(span: string) {
    if (kind === "obrigacao") {
      obrigacaoForm.setValue("descricao_obrigacao", span, {
        shouldDirty: true,
        shouldValidate: true,
      });
    } else {
      recomendacaoForm.setValue("descricao_recomendacao", span, {
        shouldDirty: true,
        shouldValidate: true,
      });
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            {kind === "obrigacao" ? "Obrigação" : "Recomendação"} · Processo{" "}
            {detail.id_processo}
          </h1>
          <p className="text-xs text-muted-foreground">
            Item #{detail.id} · Pauta {detail.id_composicao_pauta}/
            {detail.id_voto_pauta}
          </p>
        </div>
        <Button variant="outline" onClick={onBackToList}>
          Voltar
        </Button>
      </div>

      <ClaimBanner
        currentUsername={currentUsername}
        claimedBy={detail.claimed_by ?? null}
        claimedAt={detail.claimed_at ?? null}
        onReclaim={onReclaim}
        onBack={onBackToList}
        isReclaiming={reclaimSubmitting}
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-medium">Texto do acórdão</h2>
          <SpanEditor
            text={detail.texto_acordao ?? ""}
            matchedSpan={detail.matched_span ?? null}
            disabled={formDisabled}
            onChange={handleSpanChange}
            emptyState={
              detail.span_match_status === "not_found" ? NOT_FOUND_HINT : null
            }
          />
        </div>
        <div>
          <h2 className="mb-2 text-sm font-medium">Campos</h2>
          {kind === "obrigacao" ? (
            <ObrigacaoForm
              form={obrigacaoForm}
              disabled={formDisabled}
              isSubmitting={approveSubmitting}
              onApprove={onApprove}
              onReject={onOpenReject}
            />
          ) : (
            <RecomendacaoForm
              form={recomendacaoForm}
              disabled={formDisabled}
              isSubmitting={approveSubmitting}
              onApprove={onApprove}
              onReject={onOpenReject}
            />
          )}
        </div>
      </div>

      <RejectDialog
        open={rejectOpen}
        onOpenChange={onRejectOpenChange}
        onConfirm={onRejectConfirm}
        isSubmitting={rejectSubmitting}
      />
    </main>
  );
}
