"""Check the 100-token cut of Agent 4's generate_sql: re-generate long answers with a higher limit.

  python -m scripts.width_token_check results/width/dev_qwen0.5b_fp16.jsonl --hf-model Qwen/Qwen2.5-0.5B-Instruct

Decoding is greedy, so an answer that ended before 100 new tokens is the same with any higher limit. Only answers
that reached the limit can change. The script re-generates (limit --max-new, default 300):
  - every answer whose SQL has >= --threshold Qwen tokens (the possible cuts), and
  - a random sample (--sample, seed 0) of shorter answers: a check that they were not cut and come out identical.
Writes <rows>_tok<max-new>.jsonl (the original file is not changed): the same rows with the re-generated answers,
plus "cut100": {width: true} for answers whose model output reached 100 new tokens.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

from agent1_retrieval import RECOMMENDED
from agent1_retrieval.execution import exec_match
from agent1_retrieval.retrieval import Retriever
from agent1_retrieval.width import elbow_context, width_context
from scripts.width_sweep import runs

SETS = ["eval/spider_dev_full.json", "eval/chinook_pairs.json", "eval/northwind_pairs.json", "eval/spider_train_width.json"]


class Limit:
    """Agent 4's model with another max_new_tokens; her generate_sql stays unchanged. Records the output length."""

    def __init__(self, model, n):
        self.model, self.n, self.last = model, n, None

    def __getattr__(self, k):
        return getattr(self.model, k)

    def generate(self, **kw):
        out = self.model.generate(**{**kw, "max_new_tokens": self.n})
        self.last = out.shape[-1] - kw["input_ids"].shape[-1]
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--hf-model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--max-new", type=int, default=300)
    ap.add_argument("--threshold", type=int, default=70)
    ap.add_argument("--sample", type=int, default=100)
    a = ap.parse_args()

    from harness.generators import qwen_local
    gen = qwen_local("fp16", a.hf_model)
    state = gen.load()
    model = state["model"] = Limit(state["model"], a.max_new)
    ntok = lambda s: len(state["tok"](s or "")["input_ids"])

    gold = {hashlib.sha1(f"{p['db']}|{p['question']}".encode()).hexdigest()[:12]: p["sql"]
            for f in SETS if Path(f).exists() for p in json.loads(Path(f).read_text(encoding="utf-8"))}
    rows = [json.loads(l) for l in Path(a.rows).read_text(encoding="utf-8").splitlines()]
    long = [(r, w) for r in rows for w in r["sql"] if ntok(r["sql"][w]) >= a.threshold]
    short = [(r, w) for r in rows for w in r["sql"] if ntok(r["sql"][w]) < a.threshold]
    sample = random.Random(0).sample(short, min(a.sample, len(short)))
    print(f"{len(long)} answers >= {a.threshold} tokens, {len(sample)} sampled shorter answers", flush=True)

    retrievers, stats = {}, {"long": [0, 0, 0], "sample": [0, 0, 0]}  # [cut at 100, changed, context differs]
    for i, (r, w) in enumerate(long + sample, 1):
        kind = "long" if i <= len(long) else "sample"
        if r["db"] not in retrievers:
            retrievers[r["db"]] = Retriever(r["db"], **RECOMMENDED)
        ret = retrievers[r["db"]]
        ctx = elbow_context(ret, r["question"]) if w == "E" else width_context(ret, r["question"], w)
        stats[kind][2] += ctx.tokens != r["tokens"][w]
        sql = gen(r["question"], ctx.text)
        cut = model.last >= 100
        stats[kind][0] += cut
        if sql != r["sql"][w]:
            stats[kind][1] += 1
            r["sql"][w] = sql
            r["ok"][w] = exec_match(r["db"], sql, gold[r["id"]])
            r["runs"][w] = bool(r["ok"][w]) or runs(r["db"], sql)
        if cut:
            r.setdefault("cut100", {})[w] = True
        if i % 50 == 0:
            print(f"{i}/{len(long) + len(sample)}", flush=True)

    out = Path(a.rows).with_name(Path(a.rows).stem + f"_tok{a.max_new}.jsonl")
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    for kind, (cut, changed, ctxdiff) in stats.items():
        print(f"{kind}: {cut} reached 100 new tokens, {changed} answers changed, {ctxdiff} contexts differ from the sweep")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
