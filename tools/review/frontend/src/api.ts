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

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
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
