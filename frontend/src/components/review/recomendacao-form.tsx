"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { UseFormReturn, useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { RecomendacaoReview, recomendacaoReviewSchema } from "@/schemas/review";

function toDefaults(staged: Record<string, unknown>): RecomendacaoReview {
  return {
    id_processo: (staged.id_processo as number | null | undefined) ?? null,
    id_composicao_pauta:
      (staged.id_composicao_pauta as number | null | undefined) ?? null,
    id_voto_pauta: (staged.id_voto_pauta as number | null | undefined) ?? null,
    descricao_recomendacao:
      (staged.descricao_recomendacao as string | null | undefined) ?? null,
    prazo_cumprimento_recomendacao:
      (staged.prazo_cumprimento_recomendacao as string | null | undefined) ??
      null,
    data_cumprimento_recomendacao:
      (staged.data_cumprimento_recomendacao as string | null | undefined) ??
      null,
    nome_responsavel:
      (staged.nome_responsavel as string | null | undefined) ?? null,
    id_pessoa_responsavel:
      (staged.id_pessoa_responsavel as number | null | undefined) ?? null,
    orgao_responsavel:
      (staged.orgao_responsavel as string | null | undefined) ?? null,
    id_orgao_responsavel:
      (staged.id_orgao_responsavel as number | null | undefined) ?? null,
    cancelado: (staged.cancelado as boolean | null | undefined) ?? null,
  };
}

export function useRecomendacaoForm(staged: Record<string, unknown>) {
  return useForm<RecomendacaoReview>({
    resolver: zodResolver(recomendacaoReviewSchema),
    defaultValues: toDefaults(staged),
    mode: "onTouched",
  });
}

type RecomendacaoFormProps = {
  form: UseFormReturn<RecomendacaoReview>;
  disabled?: boolean;
  onApprove: (payload: RecomendacaoReview) => void;
  onReject: () => void;
  isSubmitting?: boolean;
};

export function RecomendacaoForm({
  form,
  disabled,
  onApprove,
  onReject,
  isSubmitting,
}: RecomendacaoFormProps) {
  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onApprove)}
        className="space-y-4"
        noValidate
      >
        <FormField
          control={form.control}
          name="descricao_recomendacao"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Descrição da recomendação</FormLabel>
              <FormControl>
                <Textarea
                  rows={3}
                  disabled={disabled}
                  {...field}
                  value={field.value ?? ""}
                  onChange={(e) =>
                    field.onChange(
                      e.target.value === "" ? null : e.target.value,
                    )
                  }
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="prazo_cumprimento_recomendacao"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Prazo</FormLabel>
                <FormControl>
                  <Input
                    disabled={disabled}
                    {...field}
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value === "" ? null : e.target.value,
                      )
                    }
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="data_cumprimento_recomendacao"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Data de cumprimento</FormLabel>
                <FormControl>
                  <Input
                    type="date"
                    disabled={disabled}
                    {...field}
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value === "" ? null : e.target.value,
                      )
                    }
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="nome_responsavel"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Responsável</FormLabel>
                <FormControl>
                  <Input
                    disabled={disabled}
                    {...field}
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value === "" ? null : e.target.value,
                      )
                    }
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="orgao_responsavel"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Órgão responsável</FormLabel>
                <FormControl>
                  <Input
                    disabled={disabled}
                    {...field}
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value === "" ? null : e.target.value,
                      )
                    }
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="cancelado"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center gap-2 space-y-0">
              <FormControl>
                <Checkbox
                  checked={!!field.value}
                  onCheckedChange={field.onChange}
                  disabled={disabled}
                />
              </FormControl>
              <FormLabel className="!m-0">Cancelado</FormLabel>
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2 border-t pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onReject}
            disabled={disabled || isSubmitting}
            data-testid="reject-button"
          >
            Rejeitar
          </Button>
          <Button
            type="submit"
            disabled={disabled || isSubmitting}
            data-testid="approve-button"
          >
            {isSubmitting ? "Aprovando..." : "Aprovar"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
