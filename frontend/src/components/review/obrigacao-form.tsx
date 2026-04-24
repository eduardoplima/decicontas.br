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
import { ObrigacaoReview, obrigacaoReviewSchema } from "@/schemas/review";

function toDefaults(staged: Record<string, unknown>): ObrigacaoReview {
  return {
    id_processo: (staged.id_processo as number | null | undefined) ?? null,
    id_composicao_pauta:
      (staged.id_composicao_pauta as number | null | undefined) ?? null,
    id_voto_pauta: (staged.id_voto_pauta as number | null | undefined) ?? null,
    descricao_obrigacao:
      (staged.descricao_obrigacao as string | undefined) ?? "",
    de_fazer: (staged.de_fazer as boolean | null | undefined) ?? true,
    prazo: (staged.prazo as string | null | undefined) ?? null,
    data_cumprimento:
      (staged.data_cumprimento as string | null | undefined) ?? null,
    orgao_responsavel:
      (staged.orgao_responsavel as string | null | undefined) ?? null,
    id_orgao_responsavel:
      (staged.id_orgao_responsavel as number | null | undefined) ?? null,
    tem_multa_cominatoria:
      (staged.tem_multa_cominatoria as boolean | null | undefined) ?? false,
    nome_responsavel_multa_cominatoria:
      (staged.nome_responsavel_multa_cominatoria as
        | string
        | null
        | undefined) ?? null,
    documento_responsavel_multa_cominatoria:
      (staged.documento_responsavel_multa_cominatoria as
        | string
        | null
        | undefined) ?? null,
    id_pessoa_multa_cominatoria:
      (staged.id_pessoa_multa_cominatoria as number | null | undefined) ?? null,
    valor_multa_cominatoria:
      (staged.valor_multa_cominatoria as number | null | undefined) ?? null,
    periodo_multa_cominatoria:
      (staged.periodo_multa_cominatoria as string | null | undefined) ?? null,
    e_multa_cominatoria_solidaria:
      (staged.e_multa_cominatoria_solidaria as boolean | null | undefined) ??
      false,
    solidarios_multa_cominatoria:
      (staged.solidarios_multa_cominatoria as string[] | null | undefined) ??
      null,
  };
}

export function useObrigacaoForm(staged: Record<string, unknown>) {
  return useForm<ObrigacaoReview>({
    resolver: zodResolver(obrigacaoReviewSchema),
    defaultValues: toDefaults(staged),
    mode: "onTouched",
  });
}

type ObrigacaoFormProps = {
  form: UseFormReturn<ObrigacaoReview>;
  disabled?: boolean;
  onApprove: (payload: ObrigacaoReview) => void;
  onReject: () => void;
  isSubmitting?: boolean;
};

export function ObrigacaoForm({
  form,
  disabled,
  onApprove,
  onReject,
  isSubmitting,
}: ObrigacaoFormProps) {
  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onApprove)}
        className="space-y-4"
        noValidate
      >
        <FormField
          control={form.control}
          name="descricao_obrigacao"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Descrição da obrigação</FormLabel>
              <FormControl>
                <Textarea rows={3} disabled={disabled} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="de_fazer"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={!!field.value}
                    onCheckedChange={field.onChange}
                    disabled={disabled}
                  />
                </FormControl>
                <FormLabel className="!m-0">Obrigação de fazer</FormLabel>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="tem_multa_cominatoria"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={!!field.value}
                    onCheckedChange={field.onChange}
                    disabled={disabled}
                  />
                </FormControl>
                <FormLabel className="!m-0">Multa cominatória</FormLabel>
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="prazo"
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
            name="data_cumprimento"
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

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="nome_responsavel_multa_cominatoria"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Responsável pela multa</FormLabel>
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
            name="documento_responsavel_multa_cominatoria"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Documento do responsável</FormLabel>
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

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="valor_multa_cominatoria"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Valor da multa</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    step="0.01"
                    disabled={disabled}
                    value={field.value ?? ""}
                    onChange={(e) =>
                      field.onChange(
                        e.target.value === "" ? null : Number(e.target.value),
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
            name="periodo_multa_cominatoria"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Período da multa</FormLabel>
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
          name="e_multa_cominatoria_solidaria"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center gap-2 space-y-0">
              <FormControl>
                <Checkbox
                  checked={!!field.value}
                  onCheckedChange={field.onChange}
                  disabled={disabled}
                />
              </FormControl>
              <FormLabel className="!m-0">Multa solidária</FormLabel>
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
