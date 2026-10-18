import { useCallback, useEffect, useMemo, useState } from "react";
import { adjudication, type Action, type AdjDoc, type Change, type Item, type Kind, type LayerSpan, type Source, type Summary } from "./api";
import { LayeredText } from "./LayeredText";

const LABELS = ["MULTA", "OBRIGACAO", "RESSARCIMENTO", "RECOMENDACAO"];
const KIND_NAME: Record<Kind, string> = { add: "adição", gold_only: "só A1", label: "rótulo" };
const CHANGE_NAME: Record<Change["change"], string> = { added: "+ adicionada", removed: "− removida", relabelled: "± rerrotulada" };
const ACTION_NAME: Record<Action, string> = {
  include: "incluído",
  reject: "rejeitado",
  keep: "mantido",
  remove: "removido",
  relabel: "rerrotulado",
  replaced: "substituído",
};

type Choice = { source?: Source; label?: string };

const decided = (item: Item) => item.decision !== null;
const bounds = (s: { start: number; end: number }) => `[${s.start},${s.end})`;

/** Labels proposed by the annotators on a `label` item. */
function proposals(item: Item): string[] {
  if (!item.labels) return [];
  const out = new Set<string>();
  for (const [source, label] of Object.entries(item.labels)) if (source !== "A1" && label && label !== item.label) out.add(label);
  return [...out];
}

function longest(item: Item): Source {
  return item.candidates.reduce((a, b) => (b.end - b.start > a.end - a.start ? b : a)).source;
}

export function AdjudicationView() {
  const [docs, setDocs] = useState<AdjDoc[]>([]);
  const [view, setView] = useState<"docs" | "changes">("docs");
  const [finished, setFinished] = useState(false);
  const [current, setCurrent] = useState(0);
  const [label, setLabel] = useState<string | null>(null);
  const [kind, setKind] = useState<Kind | null>(null);
  const [pendingOnly, setPendingOnly] = useState(false);
  const [hover, setHover] = useState<Item | null>(null);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adjudication
      .documents()
      .then((d) => {
        setDocs(d.documents);
        setFinished(d.finished);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const passes = useCallback(
    (item: Item) =>
      (!label || item.label === label || Object.values(item.labels ?? {}).includes(label) || item.candidates.some((c) => c.label === label)) &&
      (!kind || item.kind === kind) &&
      (!pendingOnly || !decided(item)),
    [label, kind, pendingOnly],
  );
  const visible = useMemo(
    () => docs.map((d) => ({ ...d, items: d.items.filter(passes) })).filter((d) => d.items.length),
    [docs, passes],
  );
  const doc = visible[Math.min(current, Math.max(0, visible.length - 1))];
  const totals = useMemo(() => {
    const all = docs.flatMap((d) => d.items);
    return {
      items: all.length,
      decided: all.filter(decided).length,
      auto: all.filter((i) => i.decision && !i.explicit && i.decision.action !== "replaced").length,
      pending: all.filter((i) => !decided(i)).length,
    };
  }, [docs]);

  const apply = useCallback(async (item: Item, body: { action: string; source?: Source; label?: string }) => {
    try {
      const { document } = await adjudication.decide(item.id, body);
      setDocs((prev) => prev.map((d) => (d.doc_id === document.doc_id ? document : d)));
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const adopt = useCallback(
    (item: Item) => {
      const choice = choices[item.id] ?? {};
      if (item.kind === "add") {
        const lbl = choice.label ?? item.label ?? undefined;
        if (!lbl) return;
        return apply(item, { action: "include", source: choice.source ?? longest(item), label: lbl });
      }
      if (item.kind === "gold_only") return apply(item, { action: "remove" });
      const options = proposals(item);
      if (options.length === 1) return apply(item, { action: "relabel", label: options[0] });
    },
    [apply, choices],
  );
  const keepGold = useCallback((item: Item) => apply(item, { action: item.kind === "add" ? "reject" : "keep" }), [apply]);

  const openDoc = (doc_id: number) => {
    setLabel(null);
    setKind(null);
    setPendingOnly(false);
    setCurrent(Math.max(0, docs.findIndex((d) => d.doc_id === doc_id)));
    setView("docs");
  };

  useEffect(() => {
    if (view !== "docs") return;
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || !doc) return;
      const pending = doc.items.find((i) => !decided(i) && !i.replaced_by);
      if (e.key === "s" && pending) adopt(pending);
      else if (e.key === "n" && pending) keepGold(pending);
      else if (e.key === "j" || e.key === "ArrowRight") setCurrent((c) => Math.min(c + 1, visible.length - 1));
      else if (e.key === "k" || e.key === "ArrowLeft") setCurrent((c) => Math.max(c - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view, doc, adopt, keepGold, visible.length]);

  const finish = async () => {
    try {
      const r = await adjudication.finish();
      setSummary(r.summary);
      setFinished(true);
      setError(null);
    } catch (e) {
      const msg = String(e);
      const body = msg.startsWith("Error: 409") ? msg.slice(msg.indexOf("{")) : null;
      if (body) {
        const pairs: string[][] = JSON.parse(body).detail.conflicts;
        setError(`Spans incluídos se sobrepõem: ${pairs.map((p) => p.join(" × ")).join("; ")}. Rejeite um deles (ou escolha outro candidato) antes de concluir.`);
      } else setError(msg);
    }
  };

  const focus: LayerSpan[] = hover ? [...hover.candidates, ...hover.candidates.flatMap((c) => c.also_adds)] : [];

  return (
    <div className="app">
      <header>
        <h1>decicontas.br — adjudicação A1 × A2/A3</h1>
        <nav>
          <button className={view === "docs" ? "active" : ""} onClick={() => setView("docs")}>
            Documentos
          </button>
          <button className={view === "changes" ? "active" : ""} onClick={() => setView("changes")}>
            Alterações
          </button>
        </nav>
        <div className="totals">
          {totals.decided} decididos ({totals.auto} auto) · <strong>{totals.pending} pendentes</strong> de {totals.items}
          {finished && <span className="done"> · concluído</span>}
        </div>
        <button className="finish" onClick={finish}>
          Concluir
        </button>
      </header>
      {error && <div className="error">{error}</div>}
      {summary && <SummaryPanel summary={summary} onClose={() => setSummary(null)} />}
      {view === "changes" ? (
        <ChangesView onOpen={openDoc} />
      ) : (
      <div className="docs">
        <aside>
          <div className="filters">
            {LABELS.map((l) => (
              <span key={l} className={label === l ? "chip sel" : "chip"} onClick={() => (setLabel(label === l ? null : l), setCurrent(0))}>
                {l}
              </span>
            ))}
          </div>
          <div className="filters">
            {(Object.keys(KIND_NAME) as Kind[]).map((k) => (
              <span key={k} className={kind === k ? "chip sel" : "chip"} onClick={() => (setKind(kind === k ? null : k), setCurrent(0))}>
                {KIND_NAME[k]}
              </span>
            ))}
          </div>
          <label>
            <input type="checkbox" checked={pendingOnly} onChange={(e) => (setPendingOnly(e.target.checked), setCurrent(0))} /> só pendentes
          </label>
          <ul>
            {visible.map((d, i) => {
              const pending = d.items.filter((it) => !decided(it)).length;
              return (
                <li key={d.doc_id} className={i === current ? "active" : ""} onClick={() => setCurrent(i)}>
                  <span>
                    doc {d.doc_id}
                    {d.items.some((it) => it.in_scope_clause) && <span className="scope"> !</span>}
                  </span>
                  <span className="badge">
                    {d.items.length}
                    {pending ? ` · ${pending} pend.` : ""}
                  </span>
                </li>
              );
            })}
          </ul>
        </aside>
        <main>
          {doc ? (
            <>
              <div className="toolbar">
                <strong>Documento {doc.doc_id}</strong>
                <span className="legend">
                  <span className="seg a1">A1</span> <span className="seg a2">A2</span> <span className="seg a3">A3</span>
                </span>
                <span className="hint">s = adotar anotadoras · n = manter A1 · j/k = próximo/anterior</span>
              </div>
              <LayeredText text={doc.text} layers={doc.layers} focus={focus} />
              <table className="items">
                <tbody>
                  {doc.items.map((item) => (
                    <ItemRow
                      key={item.id}
                      item={item}
                      text={doc.text}
                      choice={choices[item.id] ?? {}}
                      setChoice={(c) => setChoices((prev) => ({ ...prev, [item.id]: { ...prev[item.id], ...c } }))}
                      apply={apply}
                      adopt={adopt}
                      onHover={setHover}
                    />
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p>Nenhum documento com esses filtros.</p>
          )}
        </main>
      </div>
      )}
    </div>
  );
}

/** Everything the current decisions add to, remove from or relabel in the gold. */
function ChangesView({ onOpen }: { onOpen: (doc_id: number) => void }) {
  const [changes, setChanges] = useState<Change[]>([]);
  const [conflicts, setConflicts] = useState<string[][]>([]);
  const [totals, setTotals] = useState<Record<string, number>>({});
  const [type, setType] = useState<Change["change"] | null>(null);
  const [label, setLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adjudication
      .changes()
      .then((r) => {
        setChanges(r.changes);
        setConflicts(r.conflicts);
        setTotals(r.totals);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const rows = changes.filter((c) => (!type || c.change === type) && (!label || c.label === label || c.old_label === label));

  return (
    <div className="changes">
      <div className="toolbar">
        <strong>
          +{totals.added ?? 0} adicionadas · −{totals.removed ?? 0} removidas · ±{totals.relabelled ?? 0} rerrotuladas
        </strong>
        <span className="hint">o que o arquivo de decisões fará com o gold (inclui os itens pré-marcados)</span>
      </div>
      {error && <div className="error">{error}</div>}
      {conflicts.length > 0 && (
        <div className="error">Conflitos pendentes: {conflicts.map((p) => p.join(" × ")).join("; ")} — esses documentos ficaram de fora.</div>
      )}
      <div className="filters">
        {(Object.keys(CHANGE_NAME) as Change["change"][]).map((t) => (
          <span key={t} className={type === t ? "chip sel" : "chip"} onClick={() => setType(type === t ? null : t)}>
            {CHANGE_NAME[t]}
          </span>
        ))}
        {LABELS.map((l) => (
          <span key={l} className={label === l ? "chip sel" : "chip"} onClick={() => setLabel(label === l ? null : l)}>
            {l}
          </span>
        ))}
      </div>
      <table className="changes-table">
        <thead>
          <tr>
            <th>alteração</th>
            <th>doc</th>
            <th>classe</th>
            <th>trecho</th>
            <th>item</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={`${c.doc_id}:${c.change}:${c.start}-${c.end}`} className={c.change}>
              <td>{CHANGE_NAME[c.change]}</td>
              <td>{c.doc_id}</td>
              <td>{c.old_label ? `${c.old_label} → ${c.label}` : c.label}</td>
              <td className="excerpt">{c.excerpt.length > 220 ? c.excerpt.slice(0, 220) + "…" : c.excerpt}</td>
              <td className="sources">
                {c.item}
                {c.item && !c.explicit && <span className="auto">(auto)</span>}
              </td>
              <td>
                <button onClick={() => onOpen(c.doc_id)}>abrir</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p>Nenhuma alteração com esses filtros.</p>}
    </div>
  );
}

function ItemRow({
  item,
  text,
  choice,
  setChoice,
  apply,
  adopt,
  onHover,
}: {
  item: Item;
  text: string;
  choice: Choice;
  setChoice: (c: Choice) => void;
  apply: (item: Item, body: { action: string; source?: Source; label?: string }) => Promise<void>;
  adopt: (item: Item) => Promise<void> | undefined;
  onHover: (item: Item | null) => void;
}) {
  const action = item.decision?.action;
  const first = item.candidates[0];
  const excerpt = text.slice(first.char_start, first.char_end);
  const replaced = Boolean(item.replaced_by);
  const twoBounds = item.candidates.length === 2 && bounds(item.candidates[0]) !== bounds(item.candidates[1]);
  const source = choice.source ?? item.decision?.source ?? longest(item);
  const chosenLabel = choice.label ?? item.decision?.label ?? item.label ?? "";
  const on = (a: Action) => (action === a ? "on" : "");

  const notes: string[] = [];
  if (item.kind === "add")
    for (const c of item.candidates) {
      for (const r of c.replaces) notes.push(`${c.source} sobrepõe A1 ${r.label} ${bounds(r)} (IoU ${r.iou.toFixed(2)}) — incluir substitui`);
      for (const a of c.also_adds) notes.push(`incluir ${c.source} readiciona ${c.source} ${a.label} ${bounds(a)}`);
    }
  if (item.kind === "gold_only") for (const o of item.overlaps) notes.push(`${o.source} marcou ${o.label} ${bounds(o)} (IoU ${o.iou.toFixed(2)})`);
  if (item.kind === "label" && item.labels) notes.push(["A2", "A3"].map((s) => `${s}: ${item.labels![s as Source] ?? "—"}`).join(" · "));
  if (item.in_scope_clause) notes.push("fora do escopo (SECEX/CONJU)");
  if (replaced) notes.push(`substituído por ${item.replaced_by}`);

  return (
    <tr className={[action ?? "pending", item.decision && !item.explicit ? "auto" : ""].join(" ")} onMouseEnter={() => onHover(item)} onMouseLeave={() => onHover(null)}>
      <td>
        <span className={`kind ${item.kind}`}>{KIND_NAME[item.kind]}</span>
      </td>
      <td className="label">{item.label ?? item.candidates.map((c) => `${c.source}: ${c.label}`).join(" / ")}</td>
      <td className="sources">{item.kind === "gold_only" ? "A1" : item.sources.join("+")}</td>
      <td className="excerpt" title={excerpt}>
        {excerpt.length > 160 ? excerpt.slice(0, 160) + "…" : excerpt}
        {notes.length > 0 && <div className="notes">{notes.join(" · ")}</div>}
      </td>
      <td className="controls">
        {item.kind === "add" && (
          <>
            {twoBounds &&
              item.candidates.map((c) => (
                <label key={c.source} className="radio">
                  <input type="radio" name={item.id} checked={source === c.source} onChange={() => setChoice({ source: c.source })} /> {c.source} {bounds(c)}
                </label>
              ))}
            {item.label === null && (
              <select value={chosenLabel} onChange={(e) => setChoice({ label: e.target.value })}>
                <option value="">rótulo?</option>
                {[...new Set(item.candidates.map((c) => c.label))].map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            )}
            <button className={`yes ${on("include")}`} disabled={!chosenLabel} onClick={() => apply(item, { action: "include", source, label: chosenLabel })}>
              Incluir
            </button>
            <button className={`no ${on("reject")}`} onClick={() => apply(item, { action: "reject" })}>
              Rejeitar
            </button>
          </>
        )}
        {item.kind === "gold_only" && (
          <>
            <button className={`no ${on("keep")}`} disabled={replaced} onClick={() => apply(item, { action: "keep" })}>
              Manter
            </button>
            <button className={`yes ${on("remove")}`} disabled={replaced} onClick={() => apply(item, { action: "remove" })}>
              Remover
            </button>
          </>
        )}
        {item.kind === "label" && (
          <>
            <button className={`no ${on("keep")}`} disabled={replaced} onClick={() => apply(item, { action: "keep" })}>
              Manter {item.label}
            </button>
            {proposals(item).map((l) => (
              <button key={l} className={`yes ${action === "relabel" && item.decision?.label === l ? "on" : ""}`} disabled={replaced} onClick={() => apply(item, { action: "relabel", label: l })}>
                → {l}
              </button>
            ))}
          </>
        )}
        {action && <span className="auto">{ACTION_NAME[action]}{item.explicit ? "" : " (auto)"}</span>}
        {item.explicit && (
          <a href="#" className="hint" onClick={(e) => (e.preventDefault(), apply(item, { action: "pending" }))}>
            pendente
          </a>
        )}
        {!action && item.kind === "add" && item.label === null && <span className="hint">escolha o rótulo</span>}
        {!action && !item.replaced_by && (
          <span className="hint" onClick={() => adopt(item)}>
            {" "}
          </span>
        )}
      </td>
    </tr>
  );
}

function SummaryPanel({ summary: s, onClose }: { summary: Summary; onClose: () => void }) {
  const rel = (label: string, dir: "from" | "to") => s.relabelled.filter((r) => r[dir] === label).reduce((n, r) => n + r.n, 0);
  const total = (m: Record<string, number>) => Object.values(m).reduce((a, b) => a + b, 0);
  return (
    <div className="summary">
      <div className="toolbar">
        <strong>Arquivo de decisões gravado</strong>
        <span className="hint">
          {s.items_decided}/{s.items_total} itens decididos · {s.items_pending} pendentes ficam como A1 · {s.token_changes} tokens alterados
          {s.in_scope_included ? ` · ${s.in_scope_included} incluídos fora do escopo (o export os descarta)` : ""}
        </span>
        <button onClick={onClose}>fechar</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>classe</th>
            <th>antes</th>
            <th>+adic.</th>
            <th>−rem.</th>
            <th>rerrot. −/+</th>
            <th>depois</th>
          </tr>
        </thead>
        <tbody>
          {LABELS.map((l) => (
            <tr key={l}>
              <td>{l}</td>
              <td>{s.entities_before[l] ?? 0}</td>
              <td>{s.added_per_label[l] ?? 0}</td>
              <td>{s.removed_per_label[l] ?? 0}</td>
              <td>
                {rel(l, "from")}/{rel(l, "to")}
              </td>
              <td>{s.entities_after[l] ?? 0}</td>
            </tr>
          ))}
          <tr>
            <td>
              <strong>total</strong>
            </td>
            <td>{total(s.entities_before)}</td>
            <td>{total(s.added_per_label)}</td>
            <td>{total(s.removed_per_label)}</td>
            <td></td>
            <td>
              <strong>{total(s.entities_after)}</strong>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
