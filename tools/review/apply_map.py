"""Apply the person map to every artefact that carries document text.

Reads ``docs/privacy/person_map.json`` (built by ``tools.review.build_map``) and
rewrites, in place and token for token:

- the Label Studio exports (``dataset/labeled_data/*.json``);
- the three independent annotations (``dataset/annotators/*.jsonl``);
- the LLM result JSONs (``dataset/results/models_outputs/{output,experiments}*``);
- the Cleanlab error list (``dataset/errors/erros_anotacao_decicontas.csv``);
- the raw extracts (``dataset/raw/``), restricted to the annotated decisions;
- the few-shot exemplars (``research/fewshot.py``).

Character offsets are remapped; the number of whitespace tokens of every document
is asserted unchanged, so token-level spans and metrics are untouched.

    uv run python -m tools.review.apply_map [--map docs/privacy/person_map.json] [--dry-run]
"""

from __future__ import annotations

import argparse
import ast
import csv
import glob
import json
import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from research.dataset_io import load_dataset, token_offsets
from research.ner_metrics import locate_span
from research.release import paths
from tools.review.pseudonymise import (
    _EDGE,
    normalise_token,
    pseudonymise_string,
    pseudonymise_text,
    render_like,
)

logger = logging.getLogger("tools.review.apply_map")

MAP_PATH = paths.REPO_ROOT / "docs" / "privacy" / "person_map.json"
RAW_DIR = paths.DATASET / "raw"
LLM_DIRS = (
    paths.RESULTS_ROOT / "output",
    paths.RESULTS_ROOT / "output_corrected",
    paths.RESULTS_ROOT / "experiments",
    paths.RESULTS_ROOT / "experiments_corrected",
)
RAW_CSV_TEXT_COLUMNS = {"texto_acordao", "text"}


class PersonMap:
    """The token map plus the mentions of every person, indexed by document."""

    def __init__(self, data: dict, corpus: dict[int, str]):
        self.tokens: dict[str, str] = data["tokens"]
        self.persons: list[dict] = data["persons"]
        self.by_doc: dict[int, list[dict]] = {}
        self.mentions: dict[int, list[str]] = {}
        for person in self.persons:
            for m in person["mentions"]:
                if m.get("doc_id") is None:
                    continue
                doc_id = int(m["doc_id"])
                if person not in self.by_doc.setdefault(doc_id, []):
                    self.by_doc[doc_id].append(person)
                if m["text"] not in self.mentions.setdefault(doc_id, []):
                    self.mentions[doc_id].append(m["text"])
        self.corpus = corpus
        self._by_text = {t: i for i, t in corpus.items()}
        self._by_text.update({t.strip(): i for i, t in corpus.items()})

    def doc_for_text(self, text: str) -> int | None:
        return self._by_text.get(text, self._by_text.get(text.strip()))

    @staticmethod
    def _find_all(text: str, needles: list[str], doc_id: int | None) -> list[dict]:
        found: list[dict] = []
        for needle in sorted(needles, key=len, reverse=True):
            start = 0
            while (i := text.find(needle, start)) >= 0:
                end = i + len(needle)
                if not any(i < f["end"] and end > f["start"] for f in found):
                    found.append({"doc_id": doc_id, "text": needle, "start": i, "end": end})
                start = i + 1
        return sorted(found, key=lambda m: m["start"])

    def locate(self, text: str, doc_id: int) -> list[dict]:
        """Every occurrence in ``text`` of the mentions marked for ``doc_id``."""
        return self._find_all(text, self.mentions.get(doc_id, []), doc_id)

    def _mentions(self, text: str, doc_id: int) -> list[dict]:
        located = self.locate(text, doc_id)
        seen = {m["text"] for m in located}
        # mentions not found verbatim still select the person (upper-case repeats, split lines)
        placeholders = [
            {"doc_id": doc_id, "text": t, "start": -1, "end": -1}
            for t in self.mentions.get(doc_id, [])
            if t not in seen
        ]
        return located + placeholders

    def text(self, doc_id: int, text: str) -> tuple[str, Callable[[int, int], tuple[int, int]], int]:
        persons = self.by_doc.get(doc_id, [])
        if not persons:
            return text, (lambda s, e: (s, e)), 0
        return pseudonymise_text(text, persons, self.tokens, self._mentions(text, doc_id))

    def string(self, doc_id: int, s: str) -> str:
        persons = self.by_doc.get(doc_id, [])
        if not persons or not isinstance(s, str) or not s:
            return s
        return pseudonymise_string(s, persons, self.tokens, self._mentions(s, doc_id))

    def free_text(self, text: str, strict: bool = False) -> tuple[str, int]:
        """Replace the mentions of any mapped person, each one token by token.

        For text not tied to a document (module source, where a name may be glued to
        code such as ``="Name``); only the located mentions change. ``strict`` skips
        names that also belong to someone who was kept (homonyms).
        """
        needles = sorted(
            {m["text"] for p in self.persons for m in p["mentions"] if not (strict and m.get("ambiguous"))}
        )
        pieces, pos, n = [], 0, 0
        for m in self._find_all(text, needles, None):
            pieces.append(text[pos : m["start"]])
            words = []
            for word in m["text"].split(" "):
                key = normalise_token(word)
                if key in self.tokens:
                    lead, core, trail = _EDGE.match(word).groups()
                    word = lead + render_like(self.tokens[key], core) + trail
                    n += 1
                words.append(word)
            pieces.append(" ".join(words))
            pos = m["end"]
        pieces.append(text[pos:])
        return "".join(pieces), n


def load_map(path: Path = MAP_PATH) -> PersonMap:
    data = json.loads(path.read_text(encoding="utf-8"))
    tasks = json.loads(paths.LABELED_CORPUS.read_text(encoding="utf-8"))
    return PersonMap(data, {int(t["id"]): t["data"]["text"] for t in tasks})


# ----- per-artefact transforms ------------------------------------------------


def _walk_strings(obj, fn: Callable[[str], str]):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_walk_strings(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk_strings(v, fn) for k, v in obj.items()}
    return obj


def pseudonymise_task(task: dict, pm: PersonMap, doc_id: int) -> int:
    """A Label Studio task: text plus the offsets/text of every result value."""
    text = task["data"]["text"]
    new, remap, n = pm.text(doc_id, text)
    task["data"]["text"] = new
    for key in ("annotations", "predictions", "drafts"):
        for ann in task.get(key) or []:
            for r in ann.get("result") or []:
                v = r.get("value")
                if not v or "start" not in v:
                    continue
                old = (v["start"], v["end"])
                v["start"], v["end"] = remap(*old)
                if "text" in v:
                    v["text"] = new[v["start"] : v["end"]] if v["text"] == text[old[0] : old[1]] else pm.string(doc_id, v["text"])
    return n


def pseudonymise_record(rec: dict, pm: PersonMap, doc_id: int) -> int:
    """An LLM result record: text, gold offsets and every string inside the prediction.

    A predicted string mirrors what happened to the text where the scorer aligns it
    (:func:`research.ner_metrics.locate_span`, same parameters): a literal copy
    becomes the new slice; anything else gets, token by token, the replacements made
    in the document. Names copied from the few-shot exemplars into another
    document's prediction are replaced as well.
    """
    text = rec["text"]
    new, remap, n = pm.text(doc_id, text)
    rec["text"] = new
    for g in rec.get("golden") or []:
        old = (g["start"], g["end"])
        g["start"], g["end"] = remap(*old)
        if "text" in g:  # some runs keep the gold snippet next to its offsets
            g["text"] = new[g["start"] : g["end"]] if g["text"] == text[old[0] : old[1]] else pm.string(doc_id, g["text"])
    replaced = _replacements(text, new, pm.tokens)

    def mirror(s: str) -> str:
        if s and replaced:
            located = locate_span(text, s)
            if located is not None and text[located[0] : located[1]] == s:
                s = new[slice(*remap(*located))]
            else:
                s = _apply_replacements(s, replaced)
        return pm.free_text(s, strict=True)[0] if s else s

    if "pred" in rec:
        rec["pred"] = _walk_strings(rec["pred"], mirror)
    return n


def _replacements(old: str, new: str, tokens: dict[str, str]) -> dict[str, str]:
    """``{normalised old core: synthetic token}`` for the tokens that changed between two texts."""
    out: dict[str, str] = {}
    for (s, e), (ns, ne) in zip(token_offsets(old), token_offsets(new)):
        a, b = old[s:e], new[ns:ne]
        if a != b:
            key = normalise_token(a)
            core = _EDGE.match(b).group(2)
            out[key] = tokens.get(key) or core[:1].upper() + core[1:].lower()
    return out


def _apply_replacements(s: str, replaced: dict[str, str]) -> str:
    pieces, pos = [], 0
    for start, end in token_offsets(s):
        tok = s[start:end]
        key = normalise_token(tok)
        if key in replaced:
            lead, core, trail = _EDGE.match(tok).groups()
            tok = lead + render_like(replaced[key], core) + trail
        pieces += [s[pos:start], tok]
        pos = end
    pieces.append(s[pos:])
    return "".join(pieces)


def pseudonymise_annotation(row: dict, pm: PersonMap) -> int:
    doc_id = int(row["id"])
    new, remap, n = pm.text(doc_id, row["text"])
    row["text"] = new
    for s in row.get("spans") or []:
        s["start"], s["end"] = remap(s["start"], s["end"])
    return n


def pseudonymise_errors(df: pd.DataFrame, pm: PersonMap, idx_to_doc: dict[int, int]) -> pd.DataFrame:
    """Cleanlab error list: the token column follows its position inside the context window."""
    out = df.copy()
    for i, row in df.iterrows():
        doc_id = idx_to_doc[int(row["sentenca_idx"])]
        ctx = str(row["contexto"])
        new_ctx = pm.string(doc_id, ctx)
        if new_ctx != ctx:
            old_toks, new_toks = ctx.split(), new_ctx.split()
            tok = str(row["token"])
            pos = 3 if len(old_toks) > 3 and old_toks[3] == tok else (old_toks.index(tok) if tok in old_toks else None)
            if pos is not None:
                out.at[i, "token"] = new_toks[pos]
            out.at[i, "contexto"] = new_ctx
    return out


def pseudonymise_frame(df: pd.DataFrame, col: str, pm: PersonMap) -> tuple[pd.DataFrame, int]:
    """Raw extract: keep only the annotated decisions and rewrite their text."""
    keep = df[col].map(lambda t: isinstance(t, str) and pm.doc_for_text(t) is not None)
    out = df[keep].copy()
    total = 0
    for i, row in out.iterrows():
        doc_id = pm.doc_for_text(row[col])
        new, _, n = pm.text(doc_id, row[col])
        out.at[i, col] = new
        total += n
        if "ner_decisao" in out.columns and isinstance(row.get("ner_decisao"), str):
            out.at[i, "ner_decisao"] = pm.string(doc_id, row["ner_decisao"])
    return out, total


# ----- the run -----------------------------------------------------------------


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _assert_tokens(before: str, after: str, where: str) -> None:
    if len(token_offsets(before)) != len(token_offsets(after)):
        raise AssertionError(f"token count changed in {where}")


def run(pm: PersonMap, dry_run: bool = False) -> dict[str, int]:
    stats: dict[str, int] = {}

    def done(name: str, n: int, path: Path | None = None) -> None:
        stats[name] = n
        logger.info("%-55s %6d tokens replaced", path.name if path else name, n)

    # Label Studio exports
    for path in sorted((paths.DATASET / "labeled_data").glob("*.json")):
        tasks = json.loads(path.read_text(encoding="utf-8"))
        n = 0
        for task in tasks:
            doc_id = pm.doc_for_text(task["data"]["text"])
            if doc_id is None:
                raise ValueError(f"{path.name}: task {task.get('id')} is not in the corpus")
            before = task["data"]["text"]
            n += pseudonymise_task(task, pm, doc_id)
            _assert_tokens(before, task["data"]["text"], f"{path.name}:{task.get('id')}")
        if not dry_run:
            _write_json(path, tasks)
        done(str(path.relative_to(paths.REPO_ROOT)), n, path)

    # independent annotations
    for path in sorted(paths.ANNOTATORS_DIR.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        n = 0
        for row in rows:
            before = row["text"]
            n += pseudonymise_annotation(row, pm)
            _assert_tokens(before, row["text"], f"{path.name}:{row['id']}")
        if not dry_run:
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        done(str(path.relative_to(paths.REPO_ROOT)), n, path)

    # LLM result JSONs (lists of records with text/golden/pred)
    for root in LLM_DIRS:
        for file in sorted(glob.glob(str(root / "**" / "*.json"), recursive=True)):
            path = Path(file)
            data = json.loads(path.read_text(encoding="utf-8"))
            if not (isinstance(data, list) and data and isinstance(data[0], dict) and "text" in data[0]):
                continue
            n = 0
            for rec in data:
                doc_id = pm.doc_for_text(rec["text"])
                if doc_id is None:
                    doc_id = int(rec["index"]) + 1  # row N-1 of the 866-task export is dataset id N
                before = rec["text"]
                n += pseudonymise_record(rec, pm, doc_id)
                _assert_tokens(before, rec["text"], f"{path.name}:{rec.get('index')}")
            if not dry_run:
                _write_json(path, data)
            done(str(path.relative_to(paths.REPO_ROOT)), n, path)

    # Cleanlab error list (sentenca_idx is the position in the 861-document list)
    ds = load_dataset(paths.LABELED_CORPUS)
    idx_to_doc = {i: int(doc_id) for i, doc_id in enumerate(ds.sentencas_doc_ids)}
    df = pd.read_csv(paths.CLEANLAB_ERRORS_CSV)
    out = pseudonymise_errors(df, pm, idx_to_doc)
    if not dry_run:
        out.to_csv(paths.CLEANLAB_ERRORS_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    done(str(paths.CLEANLAB_ERRORS_CSV.relative_to(paths.REPO_ROOT)), int((out["contexto"] != df["contexto"]).sum()))

    # raw extracts, restricted to the annotated decisions
    for path in sorted(RAW_DIR.glob("*.csv")):
        df = pd.read_csv(path)
        col = next(c for c in df.columns if c in RAW_CSV_TEXT_COLUMNS)
        out, n = pseudonymise_frame(df, col, pm)
        if not dry_run:
            out.to_csv(path, index=False)
        done(str(path.relative_to(paths.REPO_ROOT)), n, path)
        stats[f"{path.name}:rows"] = len(out)
    for path in sorted(RAW_DIR.glob("*.json")):
        tasks = json.loads(path.read_text(encoding="utf-8"))
        kept, n = [], 0
        for task in tasks:
            doc_id = pm.doc_for_text(task["data"]["text"])
            if doc_id is None:
                continue
            n += pseudonymise_task(task, pm, doc_id)
            kept.append(task)
        if not dry_run:
            _write_json(path, kept)
        done(str(path.relative_to(paths.REPO_ROOT)), n, path)
        stats[f"{path.name}:rows"] = len(kept)

    # few-shot exemplars (module source; must still parse)
    path = paths.REPO_ROOT / "research" / "fewshot.py"
    src = path.read_text(encoding="utf-8")
    new, n = pm.free_text(src)
    _assert_tokens(src, new, path.name)
    ast.parse(new)
    if not dry_run:
        path.write_text(new, encoding="utf-8")
    done("research/fewshot.py", n, path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--map", type=Path, default=MAP_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = run(load_map(args.map), dry_run=args.dry_run)
    logger.info("total: %d tokens replaced", sum(v for k, v in stats.items() if not k.endswith(":rows")))


if __name__ == "__main__":
    main()
