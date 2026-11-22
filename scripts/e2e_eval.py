"""End-to-end evaluation of the whole pipeline, as the application runs it:
question -> Agent 1 (retrieval) -> Agent 2 (gate) -> Agent 3 (SQL) -> Agent 4 (read-only run, retries).

  python -m scripts.e2e_eval --pairs eval/chinook_pairs.json eval/spider_pairs.json --name agent3_lora
  python -m scripts.e2e_eval --compare results/e2e/agent3_lora.jsonl results/e2e/phi3.jsonl

The components come from the same settings as the app (J26_GENERATOR, J26_AGENT3_ADAPTER, J26_GATE,
J26_WIDTH_SELECTOR), so one run = one system configuration. Set them, then give the run a --name.
A question is correct when the final SQL returns the same rows as the gold SQL. A question that the gate declines,
or that still fails after the retries, is wrong. Questions whose gold SQL returns no rows are skipped.
One JSON line per question in results/e2e/<name>.jsonl; the run can be stopped and started again.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean, median

from agent1_retrieval.complexity import BUCKETS, classify_sql
from agent1_retrieval.execution import exec_match
from agent1_retrieval.stats import bootstrap_ci, mcnemar_exact


def read(path):
    return {r["id"]: r for r in (json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip())}


def table(rows, name):
    lines = [f"{name}: {len(rows)} questions",
             f"{'bucket':<13}{'n':>5}{'correct':>9}{'declined':>10}{'1st try':>9}{'attempts':>10}{'median s':>10}"]
    for b in (*BUCKETS, "ALL"):
        v = [r for r in rows if b in (r["bucket"], "ALL")]
        if v:
            ran = [r for r in v if r["attempts"]]
            lines.append(f"{b:<13}{len(v):>5}{mean(r['correct'] for r in v):>9.2f}{mean(r['declined'] for r in v):>10.2f}"
                         f"{mean(r['correct'] and r['attempts'] == 1 for r in v):>9.2f}"
                         f"{(mean(r['attempts'] for r in ran) if ran else 0):>10.2f}{median(r['seconds'] for r in v):>10.1f}")
    return "\n".join(lines)


def compare(a_path, b_path):
    a, b = read(a_path), read(b_path)
    ids = sorted(set(a) & set(b))
    print(f"{len(ids)} questions in both runs (A = {a_path}, B = {b_path})")
    print(f"{'bucket':<13}{'n':>5}{'A':>7}{'B':>7}{'A-B':>8}{'95% CI':>18}{'A only/B only':>15}{'p':>7}")
    for bucket in (*BUCKETS, "ALL"):
        v = [i for i in ids if bucket in (a[i]["bucket"], "ALL")]
        if not v:
            continue
        x, y = [a[i]["correct"] for i in v], [b[i]["correct"] for i in v]
        win, loss = sum(p and not q for p, q in zip(x, y)), sum(q and not p for p, q in zip(x, y))
        d, lo, hi = bootstrap_ci([p - q for p, q in zip(x, y)])
        ci, wl = f"[{lo:+.2f}, {hi:+.2f}]", f"{win}/{loss}"
        print(f"{bucket:<13}{len(v):>5}{mean(x):>7.2f}{mean(y):>7.2f}{d:>+8.2f}{ci:>18}{wl:>15}{mcnemar_exact(win, loss):>7.3f}")
    print("Five rows are tested: a single p just under 0.05 is weak evidence. Report the difference with its interval.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+")
    ap.add_argument("--name", help="name of this system configuration, e.g. agent3_lora_selector")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    a = ap.parse_args()
    if a.compare:
        return compare(*a.compare)
    if not (a.pairs and a.name):
        ap.error("give --pairs and --name, or --compare A B")

    from fastapi.testclient import TestClient
    from harness.app import create_app

    pairs = [p for f in a.pairs for p in json.loads(Path(f).read_text(encoding="utf-8"))][:a.limit]
    dbs = {hashlib.sha1(p["db"].encode()).hexdigest()[:10]: p["db"] for p in pairs}
    names = {v: k for k, v in dbs.items()}
    out = Path(f"results/e2e/{a.name}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    app = create_app(dbs, log_path=f"results/e2e/{a.name}.handoff.log.jsonl", answers_path=f"results/e2e/{a.name}.answers.db")
    client = TestClient(app)
    health = client.get("/health").json()
    done = read(out) if out.exists() else {}
    skipped = 0
    with out.open("a", encoding="utf-8") as f:
        for n, p in enumerate(pairs, 1):
            pid = hashlib.sha1(f"{p['db']}|{p['question']}".encode()).hexdigest()[:12]
            if pid in done:
                continue
            resp = client.post("/query", json={"query": p["question"], "db": names[p["db"]]})
            r = resp.json() if resp.status_code == 200 else {"ok": False, "sql": None, "attempts": 0, "error": resp.text[:200]}
            ok = exec_match(p["db"], r["sql"], p["sql"]) if r.get("ok") and r.get("sql") else (
                None if exec_match(p["db"], p["sql"], p["sql"]) is None else False)
            if ok is None:  # the gold query returns no rows
                skipped += 1
                continue
            row = {"id": pid, "db": p["db"], "question": p["question"], "bucket": classify_sql(p["sql"]), "correct": bool(ok),
                   "declined": r.get("attempts", 0) == 0, "attempts": r.get("attempts", 0), "sql": r.get("sql"),
                   "width": (r.get("context") or {}).get("width"), "tokens": (r.get("context") or {}).get("tokens"),
                   "seconds": round(r.get("total_ms", 0) / 1000, 2), "error": None if r.get("ok") else str(r.get("error"))[:200]}
            f.write(json.dumps(row) + "\n")
            f.flush()
            done[pid] = row
            if n % 10 == 0:
                print(f"{n}/{len(pairs)}", flush=True)
    meta = {"name": a.name, "generator": health.get("generator"), "stand_ins": health.get("stand_ins"), "pairs": a.pairs,
            "scored": len(done), "skipped_no_gold_rows": skipped}
    Path(f"results/e2e/{a.name}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1))
    if done:
        print(table(list(done.values()), a.name))


if __name__ == "__main__":
    main()
