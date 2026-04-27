"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCurrentUser } from "@/hooks/use-current-user";
import {
  useExtracao,
  useExtracoes,
  useTriggerExtraction,
} from "@/hooks/use-etl";
import { messageForError } from "@/lib/error-messages";
import {
  Etapa,
  ExtracaoOut,
  RunStatus,
  TriggerForm,
  triggerFormSchema,
} from "@/schemas/etl";

const PAGE_SIZE = 20;

const STAGES: { key: Etapa; label: string }[] = [
  { key: "decisoes", label: "Extração de decisões" },
  { key: "obrigacoes", label: "Extração de obrigações" },
  { key: "recomendacoes", label: "Extração de recomendações" },
];

const STAGE_INDEX: Record<Etapa, number> = {
  queued: -1,
  decisoes: 0,
  obrigacoes: 1,
  recomendacoes: 2,
  done: 3,
};

type StageState = "idle" | "running" | "done" | "error";

function stageStateFor(extracao: ExtracaoOut, stageIdx: number): StageState {
  const current = STAGE_INDEX[extracao.etapa_atual];
  if (extracao.status === "error" && current === stageIdx) return "error";
  if (current > stageIdx || extracao.status === "done") return "done";
  if (current === stageIdx && extracao.status === "running") return "running";
  return "idle";
}

function StatusBadge({ status }: { status: RunStatus }) {
  const map: Record<RunStatus, string> = {
    queued: "bg-muted text-muted-foreground",
    running: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
    done: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    error: "bg-red-500/15 text-red-700 dark:text-red-300",
  };
  const label: Record<RunStatus, string> = {
    queued: "na fila",
    running: "em andamento",
    done: "concluída",
    error: "erro",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${map[status]}`}>
      {label[status]}
    </span>
  );
}

function StageDot({ state }: { state: StageState }) {
  const map: Record<StageState, string> = {
    idle: "bg-muted",
    running: "bg-blue-500 animate-pulse",
    done: "bg-emerald-500",
    error: "bg-red-500",
  };
  return <span className={`h-2.5 w-2.5 rounded-full ${map[state]}`} />;
}

function ExtracaoStepper({ extracao }: { extracao: ExtracaoOut }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-sm">
          Extração #{extracao.id} ({formatDate(extracao.data_inicio)} a{" "}
          {formatDate(extracao.data_fim)})
        </span>
        <StatusBadge status={extracao.status} />
      </div>
      <ol className="space-y-2">
        {STAGES.map((stage, idx) => {
          const state = stageStateFor(extracao, idx);
          const counter =
            stage.key === "decisoes"
              ? extracao.decisoes_processadas
              : stage.key === "obrigacoes"
                ? extracao.obrigacoes_geradas
                : extracao.recomendacoes_geradas;
          return (
            <li key={stage.key} className="flex items-center gap-3">
              <StageDot state={state} />
              <span
                className={
                  state === "idle" ? "text-muted-foreground" : "text-foreground"
                }
              >
                {stage.label}
              </span>
              {state === "done" || state === "running" ? (
                <span className="text-xs text-muted-foreground">
                  {state === "done" ? "concluído" : "executando"} ·{" "}
                  {counter} {stage.key === "decisoes" ? "decisões" : "itens"}
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
      {extracao.status === "error" && extracao.mensagem_erro ? (
        <p className="text-sm text-red-600">{extracao.mensagem_erro}</p>
      ) : null}
    </div>
  );
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function EtlPage() {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [activeId, setActiveId] = useState<number | null>(null);

  useEffect(() => {
    if (!meLoading && me && me.role !== "admin") {
      router.replace("/reviews");
    }
  }, [me, meLoading, router]);

  const form = useForm<TriggerForm>({
    resolver: zodResolver(triggerFormSchema),
    defaultValues: { start_date: "", end_date: "" },
    mode: "onTouched",
  });

  const trigger = useTriggerExtraction();
  const active = useExtracao(activeId);
  const { data, isLoading: listLoading } = useExtracoes({
    page,
    pageSize: PAGE_SIZE,
  });

  function onSubmit(values: TriggerForm) {
    trigger.mutate(
      {
        filters: {
          start_date: values.start_date,
          end_date: values.end_date,
          overwrite: false,
        },
      },
      {
        onSuccess: (res) => {
          toast.success("Extração iniciada.");
          setActiveId(res.extracao_id);
          form.reset({ start_date: "", end_date: "" });
        },
        onError: (err) => {
          toast.error(messageForError(err, "Erro ao disparar a extração."));
        },
      },
    );
  }

  if (!me || me.role !== "admin") return null;

  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Extrações</h1>
        <p className="text-sm text-muted-foreground">
          A extração executa três passos: decisões, obrigações e recomendações.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Nova extração</CardTitle>
          <CardDescription>
            Selecione o intervalo de datas das sessões.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="grid gap-4 md:grid-cols-2"
              noValidate
            >
              <FormField
                control={form.control}
                name="start_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data inicial</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="end_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data final</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="md:col-span-2">
                <Button type="submit" disabled={trigger.isPending}>
                  {trigger.isPending ? "Disparando..." : "Disparar extração"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {activeId !== null ? (
        <Card>
          <CardHeader>
            <CardTitle>Em andamento</CardTitle>
            <CardDescription>
              Acompanhamento dos passos da extração disparada agora.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {active.data ? (
              <ExtracaoStepper extracao={active.data} />
            ) : (
              <p className="text-sm text-muted-foreground">Carregando...</p>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Histórico</CardTitle>
          <CardDescription>
            Execuções anteriores, da mais recente para a mais antiga.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Período</TableHead>
                <TableHead>Executada em</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Decisões</TableHead>
                <TableHead className="text-right">Obrigações</TableHead>
                <TableHead className="text-right">Recomendações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {listLoading && items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center text-muted-foreground"
                  >
                    Carregando...
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center text-muted-foreground"
                  >
                    Nenhuma extração registrada.
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {formatDate(item.data_inicio)} a {formatDate(item.data_fim)}
                    </TableCell>
                    <TableCell>{formatDateTime(item.data_execucao)}</TableCell>
                    <TableCell>
                      <StatusBadge status={item.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      {item.decisoes_processadas}
                    </TableCell>
                    <TableCell className="text-right">
                      {item.obrigacoes_geradas}
                    </TableCell>
                    <TableCell className="text-right">
                      {item.recomendacoes_geradas}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {total > PAGE_SIZE ? (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Página {page} de {lastPage} — {total} execuções
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= lastPage}
                  onClick={() => setPage((p) => Math.min(lastPage, p + 1))}
                >
                  Próxima
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </main>
  );
}
