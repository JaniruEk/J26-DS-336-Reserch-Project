"""Run every question at every context width with one SQL model and save every result (the distraction curves).

  python -m scripts.width_sweep --pairs eval/chinook_pairs.json eval/spider_pairs.json --model qwen2.5:1.5b-instruct

One JSON line per question in results/width/<model>.jsonl:
  {"id", "db", "question", "bucket", "ok": {W1..W4}, "runs": {W1..W4}, "tokens": {W1..W4}, "sql": {W1..W4},
   "features": {...}}   (runs = the SQL ran without a database error; used by the retry-wider systems)
The script can be stopped and started again: finished questions are skipped, and model answers are cached.
Questions whose gold SQL returns no rows (schema-only databases) or fails are skipped: their accuracy has no meaning.
--local fp16|int8|int4 uses the team base model Qwen2.5-1.5B-Instruct through transformers (no Ollama; needs a GPU).
--agent3 <adapter folder> uses Agent 3's fine-tuned model in place of an Ollama model (needs torch, a GPU is recommended).
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from statistics import mean

from agent1_retrieval import RECOMMENDED
from agent1_retrieval.complexity import BUCKETS, classify_sql
from agent1_retrieval.db import DBError
from agent1_retrieval.execution import _rows, exec_match, ollama_generate
from agent1_retrieval.retrieval import Retriever
from agent1_retrieval.width import WIDTHS, elbow_context, features, width_context


def runs(db, sql):
    """The SQL runs without a database error (right or wrong answer): what the app's retry reacts to."""
    try:
        _rows(db, sql)
        return True
    except DBError:
        return False


def summary(rows):
    lines = [f"{'bucket':<13}{'n':>5}" + "".join(f"{w:>8}" for w in WIDTHS) + f"{'any':>8}"]
    for b in (*BUCKETS, "ALL"):
        v = [r for r in rows if b in (r["bucket"], "ALL")]
        if v:
            lines.append(f"{b:<13}{len(v):>5}" + "".join(f"{mean(bool(r['ok'][w]) for r in v):>8.2f}" for w in WIDTHS)
                         + f"{mean(any(r['ok'].values()) for r in v):>8.2f}")
    lines.append(f"{'mean tokens':<18}" + "".join(f"{mean(r['tokens'][w] for r in rows):>8.0f}" for w in WIDTHS))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--model", default="qwen2.5:1.5b-instruct", help="Ollama model name")
    ap.add_argument("--local", choices=("fp16", "int8", "int4"), help="Qwen2.5-1.5B-Instruct via transformers (replaces --model)")
    ap.add_argument("--agent3", metavar="ADAPTER", help="Agent 3's adapter folder (replaces --model)")
    ap.add_argument("--out", help="default results/width/<model>.jsonl")
    ap.add_argument("--limit", type=int, help="first N questions only (a quick check)")
    ap.add_argument("--value-hints", action="store_true", help="show code values in the schema (the live app setting)")
    ap.add_argument("--elbow", action="store_true", help="also run the adaptive-elbow baseline (stored as width 'E')")
    a = ap.parse_args()

    if a.agent3:
        from harness.generators import agent3
        gen3 = agent3(a.agent3)
        name = "agent3_" + Path(a.agent3).name
        generate = lambda q, ddl: gen3(q, ddl)
    elif a.local:
        from harness.generators import qwen_local
        genq = qwen_local(a.local)
        name = f"qwen2.5-1.5b-instruct_{a.local}_transformers"
        generate = lambda q, ddl: genq(q, ddl)
    else:
        name = a.model
        generate = lambda q, ddl: ollama_generate(q, ddl, a.model)
    out = Path(a.out or f"results/width/{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["id"]: json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else {}

    pairs = [p for f in a.pairs for p in json.loads(Path(f).read_text(encoding="utf-8"))][:a.limit]
    retrievers, skipped = {}, 0
    with out.open("a", encoding="utf-8") as f:
        for n, p in enumerate(pairs, 1):
            pid = hashlib.sha1(f"{p['db']}|{p['question']}".encode()).hexdigest()[:12]
            if pid in done:
                continue
            try:  # gold returns no rows (schema-only DB) or fails (a few Spider train golds name missing tables)
                scorable = bool(_rows(p["db"], p["sql"]))
            except DBError:
                scorable = False
            if not scorable:
                skipped += 1
                continue
            if p["db"] not in retrievers:
                retrievers[p["db"]] = Retriever(p["db"], **RECOMMENDED, value_hints=a.value_hints)
            r = retrievers[p["db"]]
            ctx = {w: width_context(r, p["question"], w) for w in WIDTHS}
            sql, ok, ran = {}, {}, {}
            if a.elbow:
                ctx["E"] = elbow_context(r, p["question"])
            for w in ctx:
                try:
                    sql[w] = generate(p["question"], ctx[w].text)
                    ok[w] = exec_match(p["db"], sql[w], p["sql"])
                    ran[w] = bool(ok[w]) or runs(p["db"], sql[w])
                except ValueError as e:  # schema too long for the model: counted as wrong, and recorded
                    sql[w], ok[w], ran[w] = f"-- {e}", False, False
            row ={"id": pid, "db": p["db"], "question": p["question"], "bucket": classify_sql(p["sql"]), "ok": ok,
                   "runs": ran, "tokens": {w: ctx[w].tokens for w in ctx}, "sql": sql, "features": features(r, p["question"], ctx)}
            f.write(json.dumps(row) + "\n")
            f.flush()
            done[pid] = row
            if n % 10 == 0:
                print(f"{n}/{len(pairs)}", flush=True)
    rows = list(done.values())
    print(f"\nmodel {name}: {len(rows)} questions scored, {skipped} skipped (gold SQL returns no rows or fails) -> {out}")
    if rows:
        print(summary(rows))


if __name__ == "__main__":
    main()
