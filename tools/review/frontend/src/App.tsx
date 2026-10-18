import { useCallback, useEffect, useMemo, useState } from "react";
import { AdjudicationView } from "./Adjudication";
import { api, type Doc, type Mention, type Person } from "./api";

type View = "docs" | "persons";

/** The same build serves two local tools; the backend says which one is running. */
export default function App() {
  const [mode, setMode] = useState<"persons" | "adjudication" | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .mode()
      .then((m) => {
        setMode(m.mode);
        document.title = m.mode === "adjudication" ? "decicontas.br — adjudicação" : "decicontas.br — revisão de pessoas";
      })
      .catch((e) => setError(String(e)));
  }, []);
  if (error) return <div className="error">{error}</div>;
  if (!mode) return null;
  return mode === "adjudication" ? <AdjudicationView /> : <PersonsApp />;
}

function PersonsApp() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [view, setView] = useState<View>("docs");
  const [current, setCurrent] = useState(0);
  const [pendingOnly, setPendingOnly] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const data = await api.documents();
    setDocs(data.documents);
    setFinished(data.finished);
  }, []);

  useEffect(() => {
    reload().catch((e) => setError(String(e)));
  }, [reload]);

  const visible = useMemo(
    () => (pendingOnly ? docs.filter((d) => d.mentions.some((m) => m.decision === null)) : docs),
    [docs, pendingOnly],
  );
  const doc = visible[Math.min(current, Math.max(0, visible.length - 1))];
  const totals = useMemo(() => {
    const all = docs.flatMap((d) => d.mentions);
    return {
      mentions: all.length,
      yes: all.filter((m) => m.decision === "yes").length,
      no: all.filter((m) => m.decision === "no").length,
      pending: all.filter((m) => m.decision === null).length,
    };
  }, [docs]);

  const decide = useCallback(
    async (mention: Mention, value: "yes" | "no") => {
      const { updated } = await api.decide(mention.id, value);
      const ids = new Set(updated);
      setDocs((prev) =>
        prev.map((d) =>
          d.doc_id !== mention.doc_id
            ? d
            : { ...d, mentions: d.mentions.map((m) => (ids.has(m.id) ? { ...m, decision: value } : m)) },
        ),
      );
    },
    [],
  );

  const decideAll = useCallback(
    async (value: "yes" | "no") => {
      if (!doc) return;
      for (const m of doc.mentions) if (m.decision === null) await decide(m, value);
    },
    [doc, decide],
  );

  useEffect(() => {
    if (view !== "docs") return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      if (!doc) return;
      const pending = doc.mentions.find((m) => m.decision === null);
      if (e.key === "s" && pending) decide(pending, "yes");
      else if (e.key === "n" && pending) decide(pending, "no");
      else if (e.key === "j" || e.key === "ArrowRight") setCurrent((c) => Math.min(c + 1, visible.length - 1));
      else if (e.key === "k" || e.key === "ArrowLeft") setCurrent((c) => Math.max(c - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view, doc, decide, visible.length]);

  return (
    <div className="app">
      <header>
        <h1>decicontas.br — revisão de pessoas</h1>
        <nav>
          <button className={view === "docs" ? "active" : ""} onClick={() => setView("docs")}>
            Documentos
          </button>
          <button className={view === "persons" ? "active" : ""} onClick={() => setView("persons")}>
            Pessoas
          </button>
        </nav>
        <div className="totals">
          {totals.yes} sim · {totals.no} não · <strong>{totals.pending} pendentes</strong> de {totals.mentions}
          {finished && <span className="done"> · concluído</span>}
        </div>
      </header>
      {error && <div className="error">{error}</div>}
      {view === "docs" ? (
        <DocsView
          docs={visible}
          doc={doc}
          current={current}
          setCurrent={setCurrent}
          pendingOnly={pendingOnly}
          setPendingOnly={(v) => {
            setPendingOnly(v);
            setCurrent(0);
          }}
          decide={decide}
          decideAll={decideAll}
          onAdded={reload}
        />
      ) : (
        <PersonsView onFinished={() => setFinished(true)} />
      )}
    </div>
  );
}

function DocsView(props: {
  docs: Doc[];
  doc: Doc | undefined;
  current: number;
  setCurrent: (i: number) => void;
  pendingOnly: boolean;
  setPendingOnly: (v: boolean) => void;
  decide: (m: Mention, v: "yes" | "no") => Promise<void>;
  decideAll: (v: "yes" | "no") => Promise<void>;
  onAdded: () => Promise<void>;
}) {
  const { docs, doc, current, setCurrent, pendingOnly, setPendingOnly, decide, decideAll, onAdded } = props;
  const [manual, setManual] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const add = async () => {
    if (!doc || !manual.trim()) return;
    try {
      await api.addMention(doc.doc_id, manual.trim());
      setManual("");
      setMsg(null);
      await onAdded();
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div className="docs">
      <aside>
        <label>
          <input type="checkbox" checked={pendingOnly} onChange={(e) => setPendingOnly(e.target.checked)} /> só pendentes
        </label>
        <ul>
          {docs.map((d, i) => {
            const pending = d.mentions.filter((m) => m.decision === null).length;
            return (
              <li key={d.doc_id} className={i === current ? "active" : ""} onClick={() => setCurrent(i)}>
                <span>doc {d.doc_id}</span>
                <span className="badge">
                  {d.mentions.length}
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
              <span className="hint">s = sim · n = não · j/k = próximo/anterior</span>
              <button onClick={() => decideAll("yes")}>todas pendentes: sim</button>
              <button onClick={() => decideAll("no")}>todas pendentes: não</button>
            </div>
            <Highlighted doc={doc} />
            <table className="mentions">
              <tbody>
                {doc.mentions.map((m) => (
                  <tr key={m.id} className={m.decision ?? "pending"}>
                    <td className="name">{m.text}</td>
                    <td className="sources">{m.sources.join(", ")}</td>
                    <td>
                      <button className={m.decision === "yes" ? "yes on" : "yes"} onClick={() => decide(m, "yes")}>
                        Sim
                      </button>
                      <button className={m.decision === "no" ? "no on" : "no"} onClick={() => decide(m, "no")}>
                        Não
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="manual">
              <input
                placeholder="nome que faltou (texto exato do documento)"
                value={manual}
                onChange={(e) => setManual(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && add()}
              />
              <button onClick={add}>adicionar</button>
              {msg && <span className="error">{msg}</span>}
            </div>
          </>
        ) : (
          <p>Nenhum documento.</p>
        )}
      </main>
    </div>
  );
}

function Highlighted({ doc }: { doc: Doc }) {
  const parts: React.ReactNode[] = [];
  let pos = 0;
  for (const m of [...doc.mentions].sort((a, b) => a.start - b.start)) {
    if (m.start < pos) continue;
    parts.push(doc.text.slice(pos, m.start));
    parts.push(
      <mark key={m.id} className={m.decision ?? "pending"} title={m.sources.join(", ")}>
        {doc.text.slice(m.start, m.end)}
      </mark>,
    );
    pos = m.end;
  }
  parts.push(doc.text.slice(pos));
  return <div className="text">{parts}</div>;
}

function PersonsView({ onFinished }: { onFinished: () => void }) {
  const [persons, setPersons] = useState<Person[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [groups, setGroups] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => setPersons((await api.persons()).persons), []);
  useEffect(() => {
    load().catch((e) => setMsg(String(e)));
  }, [load]);

  const toggle = (set: Set<string>, id: string) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  };

  const split = async () => {
    if (!selected.size) return;
    setPersons((await api.split([...selected])).persons);
    setSelected(new Set());
  };
  const merge = async () => {
    if (groups.size < 2) return;
    const ids = persons.filter((p) => groups.has(p.id)).map((p) => p.mentions[0].id);
    setPersons((await api.merge(ids)).persons);
    setGroups(new Set());
  };
  const finish = async () => {
    const r = await api.finish();
    setMsg(`Concluído: ${r.persons} pessoas.`);
    onFinished();
  };

  return (
    <div className="persons">
      <div className="toolbar">
        <strong>{persons.length} pessoas</strong>
        <button disabled={!selected.size} onClick={split}>
          separar menções selecionadas ({selected.size})
        </button>
        <button disabled={groups.size < 2} onClick={merge}>
          juntar grupos marcados ({groups.size})
        </button>
        <button className="finish" onClick={finish}>
          Concluir
        </button>
        {msg && <span className="hint">{msg}</span>}
      </div>
      {persons.map((p) => (
        <div key={p.id} className="person">
          <div className="head">
            <input type="checkbox" checked={groups.has(p.id)} onChange={() => setGroups(toggle(groups, p.id))} />
            <strong>{p.canonical}</strong>
            <select
              value={p.gender ?? ""}
              onChange={async (e) => {
                const g = (e.target.value || null) as "M" | "F" | null;
                setPersons((await api.gender(p.id, g)).persons);
              }}
            >
              <option value="">gênero?</option>
              <option value="M">M</option>
              <option value="F">F</option>
            </select>
            <span className="badge">{p.mentions.length} menções</span>
          </div>
          <div className="chips">
            {p.mentions.map((m) => (
              <label key={m.id} className={selected.has(m.id) ? "chip sel" : "chip"}>
                <input type="checkbox" checked={selected.has(m.id)} onChange={() => setSelected(toggle(selected, m.id))} />
                {m.text} <small>doc {m.doc_id}</small>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
