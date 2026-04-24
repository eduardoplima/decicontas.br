"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { RejectRequest, rejectRequestSchema } from "@/schemas/review";

type RejectDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (notes: string) => void;
  isSubmitting?: boolean;
};

export function RejectDialog({
  open,
  onOpenChange,
  onConfirm,
  isSubmitting,
}: RejectDialogProps) {
  const form = useForm<RejectRequest>({
    resolver: zodResolver(rejectRequestSchema),
    defaultValues: { review_notes: "" },
    mode: "onTouched",
  });

  useEffect(() => {
    if (!open) form.reset({ review_notes: "" });
  }, [open, form]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rejeitar item</DialogTitle>
          <DialogDescription>
            Justifique a rejeição. O texto ficará registrado no histórico do
            item.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((values) =>
              onConfirm(values.review_notes.trim()),
            )}
            className="space-y-4"
            noValidate
          >
            <FormField
              control={form.control}
              name="review_notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Motivo</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={5}
                      placeholder="Ex.: trecho destacado não corresponde a uma obrigação..."
                      {...field}
                      value={field.value ?? ""}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancelar
              </Button>
              <Button
                type="submit"
                variant="destructive"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Enviando..." : "Rejeitar"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
