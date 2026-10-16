"""Agent 3: evaluate a model on the shared eval pairs (eval/spider_pairs.json, chinook_pairs.json, tpch_pairs.json).

Three steps. Heavy libraries are imported only inside the step that needs them.
  prepare   (laptop)  eval/*.json + databases -> agent3_finetune/data/eval_inputs.json
                      (question, gold SQL, complexity bucket, schema text in the SAME format as training)
  generate  (Colab)   eval_inputs.json + base model [+ LoRA adapter] -> predictions.json (greedy decoding)
  score     (laptop)  predictions.json -> exact match and execution accuracy per complexity bucket, 95% CIs

Run all commands from the project root, as modules, e.g.  python -m agent3_finetune.evaluate prepare

Metrics
  exact      normalised string match (lower-case, spacing and trailing ';' ignored). This is STRICTER than Spider's
             official exact-set-match (which parses the SQL), so report it as "normalised exact match".
  execution  the shared agent1_retrieval.execution.exec_match (row multiset vs gold). Pairs whose gold query
             returns no rows (e.g. the schema-only TPC-H database) are excluded from execution accuracy.
"""
import argparse
import json
import math
import re
import sqlite3
import time
from pathlib import Path

DATASETS = ("spider", "chinook", "tpch")
POOLED = ("spider", "chinook")  # same pooling the team used for execution results (Chinook + Spider)


# ---------------------------------------------------------------- shared helpers
def read_ddl(db, cache):
    """Schema text exactly as build_dataset.py produced it (CREATE TABLE statements from sqlite_master)."""
    if db not in cache:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode("utf-8", errors="replace")
        rows = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        con.close()
        cache[db] = ";\n".join(r[0] for r in rows) + ";"
    return cache[db]


def normalise(sql):
    s = sql.strip().rstrip(";").lower().replace('"', "'")
    s = re.sub(r"\s+", " ", s)
    return re.sub(r"\s*([(),=<>!])\s*", r"\1", s).strip()


def clean_sql(text):
    """Strip markdown code fences (```sql ... ```) and anything after the first ';'. Applied to every model alike."""
    m = re.search(r"```(?:sql)?\s*(.*?)(?:```|$)", text, re.S | re.I)
    if m:
        text = m.group(1)
    return text.split(";")[0].strip()


def wilson(k, n, z=1.96):
    """95% Wilson confidence interval for a proportion."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


# ---------------------------------------------------------------- step 1: prepare (laptop)
def cmd_prepare(a):
    from agent1_retrieval.complexity import classify_query, classify_sql

    def live_label(question):  # Agent 1's live classifier (what HydraLoRA would see in deployment)
        try:
            return classify_query(question)
        except Exception:
            return None

    items, cache = [], {}
    for name in DATASETS:
        pairs = json.loads(Path(f"eval/{name}_pairs.json").read_text(encoding="utf-8"))
        kept = 0
        for p in pairs:
            if not Path(p["db"]).exists():
                continue
            items.append({"dataset": name, "db": p["db"], "question": p["question"], "sql": p["sql"],
                          "complexity": classify_sql(p["sql"]), "nl_complexity": live_label(p["question"]),
                          "ddl": read_ddl(p["db"], cache)})
            kept += 1
        note = "" if kept == len(pairs) else "   <-- database file missing, run its scripts/ downloader first"
        print(f"{name}: {kept}/{len(pairs)} pairs{note}")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, indent=1), encoding="utf-8")
    print("wrote", out, f"({len(items)} items)")


# ---------------------------------------------------------------- step 2: generate (Colab GPU)
def cmd_generate(a):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from agent3_finetune.train_lora import PROMPT  # the exact prompt used in training

    items = json.loads(Path(a.inputs).read_text(encoding="utf-8"))
    if a.limit:
        items = items[:a.limit]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        total = torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(min(1.0, a.vram_cap_gb * 1024 ** 3 / total))
        gpu = torch.cuda.get_device_name(0)
    else:
        gpu = "cpu"
    print("device:", gpu, "| adapter:", a.adapter or "NONE (base model only)")

    tok = AutoTokenizer.from_pretrained(a.model)
    tok.padding_side = "left"  # needed for batched generation
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float16).to(device)
    router, n_heads = None, 0
    if a.adapter and (Path(a.adapter) / "adapters.pt").exists():  # made by agent3_finetune.train (LoRA or HydraLoRA)
        from agent3_finetune import hydra
        am = json.loads((Path(a.adapter) / "adapter_meta.json").read_text(encoding="utf-8"))
        router, n_heads = hydra.Router(), am["n_heads"]
        hydra.add_adapters(model, router, am["rank"], am["alpha"], n_heads, 0.0, tuple(am["targets"]))
        hydra.load_adapters(model, a.adapter)
    elif a.adapter:  # adapter from the first, PEFT-based LoRA run
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
    model.eval()
    label_key = "complexity" if a.routing == "oracle" else "nl_complexity"  # which label picks the head

    prompts = [PROMPT.format(ddl=i["ddl"], question=i["question"]) for i in items]
    lens = [len(tok(p, add_special_tokens=False)["input_ids"]) for p in prompts]
    preds = {i: "" for i in range(len(items)) if lens[i] > a.max_prompt_tokens}  # too long: counted as wrong
    todo = sorted((i for i in range(len(items)) if lens[i] <= a.max_prompt_tokens), key=lambda i: lens[i])
    print(f"{len(todo)} to generate, {len(preds)} skipped (prompt > {a.max_prompt_tokens} tokens)")

    t0 = time.time()
    for s in range(0, len(todo), a.batch):
        ids = todo[s:s + a.batch]
        enc = tok([prompts[i] for i in ids], return_tensors="pt", padding=True, add_special_tokens=False).to(device)
        if router is not None:
            router.set(torch.tensor([hydra.head_index(items[i].get(label_key)) for i in ids], device=device))
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=a.max_new_tokens, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        for i, seq in zip(ids, out):
            text = tok.decode(seq[enc["input_ids"].shape[1]:], skip_special_tokens=True)
            preds[i] = text.split(";")[0].strip()
        print(f"{min(s + a.batch, len(todo))}/{len(todo)}", flush=True)

    meta = {"model": a.model, "adapter": a.adapter or None, "gpu": gpu, "decoding": "greedy",
            "max_new_tokens": a.max_new_tokens, "max_prompt_tokens": a.max_prompt_tokens,
            "n_items": len(items), "n_prompt_too_long": sum(1 for i in range(len(items)) if lens[i] > a.max_prompt_tokens),
            "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2) if device == "cuda" else None,
            "n_heads": n_heads or None, "routing": a.routing if n_heads > 1 else None,
            "router_fallbacks": sum(1 for it in items if it.get(label_key) not in hydra.HEADS) if n_heads > 1 else None,
            "generate_seconds": round(time.time() - t0)}
    rows = [{**{k: v for k, v in it.items() if k != "ddl"}, "pred": preds[i], "prompt_tokens": lens[i]}
            for i, it in enumerate(items)]
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"meta": meta, "predictions": rows}, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=2))


# ---------------------------------------------------------------- step 3: score (laptop)
def fmt(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k / n:.2f} [{lo:.2f}-{hi:.2f}] ({k}/{n})"


def summarise(rows, title, buckets):
    print(f"\n=== {title} ===")
    print(f"{'bucket':<13}{'exact match':<30}{'execution accuracy':<30}")
    for b in list(buckets) + ["ALL"]:
        sub = rows if b == "ALL" else [r for r in rows if r["complexity"] == b]
        if not sub:
            continue
        scored = [r for r in sub if r["exec"] is not None]
        print(f"{b:<13}{fmt(sum(r['exact'] for r in sub), len(sub)):<30}"
              f"{fmt(sum(bool(r['exec']) for r in scored), len(scored)):<30}")


def cmd_score(a):
    from agent1_retrieval.complexity import BUCKETS
    from agent1_retrieval.execution import exec_match

    data = json.loads(Path(a.predictions).read_text(encoding="utf-8"))
    rows = []
    for p in data["predictions"]:
        pred = clean_sql(p["pred"])
        try:
            ex = exec_match(p["db"], pred, p["sql"])
        except Exception:
            ex = None  # gold query itself could not be run: not scorable
        rows.append({**p, "pred_clean": pred, "exact": normalise(pred) == normalise(p["sql"]), "exec": ex})

    print("meta:", json.dumps(data["meta"]))
    for name in DATASETS:
        sub = [r for r in rows if r["dataset"] == name]
        if sub:
            summarise(sub, f"{name} (n={len(sub)})", BUCKETS)
    pooled = [r for r in rows if r["dataset"] in POOLED]
    if pooled:
        summarise(pooled, f"pooled {' + '.join(POOLED)} (n={len(pooled)})", BUCKETS)
    pairs = [(r["complexity"], r["nl_complexity"]) for r in rows if r.get("nl_complexity")]
    if pairs:
        agree = sum(g == n for g, n in pairs)
        print(f"\nlive classifier agrees with the true label on {agree}/{len(pairs)} questions ({agree / len(pairs):.2f})")
    empty = sum(1 for r in rows if not r["pred_clean"].strip())
    print(f"\nempty predictions: {empty} (includes {data['meta'].get('n_prompt_too_long', 0)} prompts that were too long)")

    out = Path(a.out) if a.out else Path(a.predictions).with_name(Path(a.predictions).stem + "_scored.json")
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")  # per-item results, needed for paired tests later
    print("wrote", out)


# ---------------------------------------------------------------- command line
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--out", default="agent3_finetune/data/eval_inputs.json")
    p.set_defaults(fn=cmd_prepare)

    g = sub.add_parser("generate")
    g.add_argument("--inputs", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    g.add_argument("--adapter", default="", help="path to the LoRA adapter folder; empty = base model only")
    g.add_argument("--routing", choices=["oracle", "nl"], default="oracle",
                   help="HydraLoRA only: head chosen from the true label (oracle) or from Agent 1's live classifier (nl)")
    g.add_argument("--batch", type=int, default=4)
    g.add_argument("--max_new_tokens", type=int, default=256)
    g.add_argument("--max_prompt_tokens", type=int, default=2048)
    g.add_argument("--limit", type=int, default=0)
    g.add_argument("--vram_cap_gb", type=float, default=8.0)
    g.set_defaults(fn=cmd_generate)

    s = sub.add_parser("score")
    s.add_argument("--predictions", required=True)
    s.add_argument("--out", default="")
    s.set_defaults(fn=cmd_score)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
