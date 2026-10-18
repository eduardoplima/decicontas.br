export type Decision = "yes" | "no" | null;

export interface Mention {
  id: string;
  doc_id: number;
  text: string;
  start: number;
  end: number;
  sources: string[];
  decision: Decision;
}

export interface Doc {
  doc_id: number;
  text: string;
  mentions: Mention[];
}

export interface Person {
  id: string;
  canonical: string;
  tokens: string[];
  gender: "M" | "F" | null;
  mentions: { id: string; doc_id: number; text: string }[];
}

export async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  mode: () => call<{ mode: "persons" | "adjudication" }>("/api/mode"),
  documents: () => call<{ documents: Doc[]; finished: boolean }>("/api/documents"),
  decide: (id: string, value: "yes" | "no") =>
    call<{ id: string; decision: Decision; updated: string[] }>(`/api/decisions/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  addMention: (doc_id: number, text: string) =>
    call<Mention>("/api/mentions", { method: "POST", body: JSON.stringify({ doc_id, text }) }),
  persons: () => call<{ persons: Person[] }>("/api/persons"),
  merge: (mention_ids: string[]) =>
    call<{ persons: Person[] }>("/api/persons/merge", { method: "POST", body: JSON.stringify({ mention_ids }) }),
  split: (mention_ids: string[]) =>
    call<{ persons: Person[] }>("/api/persons/split", { method: "POST", body: JSON.stringify({ mention_ids }) }),
  gender: (group_id: string, gender: "M" | "F" | null) =>
    call<{ persons: Person[] }>(`/api/persons/${encodeURIComponent(group_id)}/gender`, {
      method: "POST",
      body: JSON.stringify({ gender }),
    }),
  finish: () => call<{ finished: boolean; persons: number }>("/api/finish", { method: "POST" }),
};

// ----- adjudication (annotator 1 vs annotators 2/3) -------------------------

export type Source = "A1" | "A2" | "A3";
export type Kind = "add" | "gold_only" | "label";
export type Action = "include" | "reject" | "keep" | "remove" | "relabel" | "replaced";

export interface LayerSpan {
  start: number;
  end: number;
  char_start: number;
  char_end: number;
  label: string;
}

export interface GoldRef {
  start: number;
  end: number;
  label: string;
  iou: number;
}

export interface Candidate extends LayerSpan {
  source: Source;
  replaces: GoldRef[];
  also_adds: LayerSpan[];
}

export interface AdjDecision {
  action: Action;
  source?: Source;
  start?: number;
  end?: number;
  label?: string;
  replaced_by?: string;
  decided_at?: string;
}

export interface Item {
  id: string;
  doc_id: number;
  kind: Kind;
  label: string | null;
  sources: Source[];
  candidates: Candidate[];
  labels: Record<Source, string | null> | null;
  overlaps: (GoldRef & { source: Source })[];
  in_scope_clause: boolean;
  default: AdjDecision | null;
  decision: AdjDecision | null;
  explicit: boolean;
  replaced_by: string | null;
}

export interface AdjDoc {
  doc_id: number;
  text: string;
  layers: Record<Source, LayerSpan[]>;
  items: Item[];
}

export interface Summary {
  items_total: number;
  items_decided: number;
  items_pending: number;
  include: number;
  reject: number;
  keep: number;
  remove: number;
  relabel: number;
  replaced: number;
  token_changes: number;
  in_scope_included: number;
  entities_before: Record<string, number>;
  entities_after: Record<string, number>;
  added_per_label: Record<string, number>;
  removed_per_label: Record<string, number>;
  relabelled: { from: string; to: string; n: number }[];
}

export const adjudication = {
  documents: () => call<{ documents: AdjDoc[]; finished: boolean }>("/api/adjudication/documents"),
  decide: (id: string, body: { action: string; source?: Source; label?: string }) =>
    call<{ document: AdjDoc }>(`/api/adjudication/decisions/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  finish: () =>
    call<{ finished: boolean; path: string; summary: Summary }>("/api/adjudication/finish", { method: "POST" }),
};
