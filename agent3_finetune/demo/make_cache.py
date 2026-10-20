"""Demo (Agent 3): record the saved answers for the cached fallback. Run on Colab (GPU), from the project root:

  !python -m agent3_finetune.demo.make_cache \
      --lora /content/drive/MyDrive/agent3/runs/lora_r16_seed42/adapter \
      --hydra /content/drive/MyDrive/agent3/runs/hydra_r16_seed42/adapter \
      --db-dir /content/drive/MyDrive/agent3/demo_dbs

It writes agent3_finetune/demo/cache/examples.json (small: commit it to the repo, or download it and put it there).
Read the printed summary: if a question looks bad for the story, edit EXAMPLES in cache.py and record again.
"""
import argparse
import time

from agent3_finetune.demo.cache import EXAMPLES, build_cache, save_cache
from agent3_finetune.demo.pipeline import list_databases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lora", required=True)
    ap.add_argument("--hydra", required=True)
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--out", default="agent3_finetune/demo/cache/examples.json")
    a = ap.parse_args()

    from agent3_finetune.demo.classifier import LiveClassifier
    from agent3_finetune.demo.engine import Engine

    dbs = list_databases(a.db_dir)
    missing = sorted({e["db"] for e in EXAMPLES} - set(dbs))
    if missing:
        raise SystemExit(f"these databases are not in {a.db_dir}: {missing}")
    classifier = LiveClassifier()
    engine = Engine(a.lora, a.hydra)
    meta = {"recorded_at": time.strftime("%Y-%m-%d %H:%M"), "gpu": engine.gpu, "model": engine.model_name,
            "note": "Saved answers recorded from the live system; not a live run."}
    cache = build_cache(engine, classifier, dbs, EXAMPLES, meta)
    save_cache(cache, a.out)
    print("\n=== RECORDED ===")
    for e in cache["examples"]:
        r = e["result"]
        print("\n" + e["title"])
        if "error" in r:
            print("  ERROR:", r["error"])
            continue
        print("  label:", r["label"], "| routed head:", r["routed_head"])
        for m, v in r["modes"].items():
            print(f"  {m:6s}: {v['status']}")
            print(f"          {v['sql'][:150]}")
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
