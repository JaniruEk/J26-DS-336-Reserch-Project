"""Agent 3: package a trained adapter as a versioned artefact for Agent 4 (requirement FR5: winner AND runner-up).

An artefact folder holds the adapter weights, a manifest (version, role, settings, parameter count, training cost,
evaluation summary, SHA-256 of the weights, git commit), the run settings, the evaluation log and a short loading guide.
No GPU and no PyTorch needed. Large files stay on Google Drive; commit only manifest.json to the repository.

  package : python -m agent3_finetune.package_artifacts package --name lora_r16_seed42 --role winner \
              --adapter <adapter folder> --run-info <run_info.json> --config <config_used.json> \
              --scored <..._predictions_scored.json> --out <artifacts folder> [--extra file ...] [--note "..."]
  verify  : python -m agent3_finetune.package_artifacts verify --dir <artifacts folder>/<name>_v1
"""
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

POOLED = ("spider", "chinook")
LOAD_ME = """# How to load this artefact

Base model: `{base}` (fp16). Adapter format: `adapters.pt` + `adapter_meta.json` written by `agent3_finetune/train.py`.

```python
import json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from agent3_finetune import hydra          # from the project repository

meta = json.load(open("adapter_meta.json"))
tok = AutoTokenizer.from_pretrained(meta["base_model"])
model = AutoModelForCausalLM.from_pretrained(meta["base_model"], torch_dtype=torch.float16).to("cuda")
router = hydra.Router()
hydra.add_adapters(model, router, meta["rank"], meta["alpha"], meta["n_heads"], 0.0, tuple(meta["targets"]))
hydra.load_adapters(model, ".")             # folder that contains adapters.pt
model.eval()
# HydraLoRA only (n_heads = 4): before each generation choose the head from the complexity label
# router.set(torch.tensor([hydra.head_index(label)], device="cuda"))
```

Prompt format (identical to training): `### Schema:\\n{{ddl}}\\n\\n### Question:\\n{{question}}\\n\\n### SQL:\\n`
(`agent3_finetune/train_lora.py: PROMPT`). Clean the output with `clean_sql` from `agent3_finetune/evaluate.py`.

{note}
"""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def eval_summary(scored_path):
    rows = json.loads(Path(scored_path).read_text(encoding="utf-8"))
    rows = [r for r in rows if r["dataset"] in POOLED and r["exec"] is not None]
    out = {"metric": "execution accuracy", "questions": "pooled Spider dev + Chinook", "n_scored": len(rows),
           "overall": f"{sum(bool(r['exec']) for r in rows)}/{len(rows)}", "by_bucket": {}}
    for b in ("simple", "single-join", "multi-join", "aggregation"):
        sub = [r for r in rows if r["complexity"] == b]
        out["by_bucket"][b] = f"{sum(bool(r['exec']) for r in sub)}/{len(sub)}"
    return out


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


def cmd_package(a):
    src = Path(a.adapter)
    for need in ("adapters.pt", "adapter_meta.json"):
        if not (src / need).exists():
            raise SystemExit(f"{need} not found in {src}")
    out = Path(a.out) / f"{a.name}_{a.version}"
    if out.exists() and not a.force:
        raise SystemExit(f"{out} already exists (use --force to overwrite)")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "adapters.pt", out / "adapters.pt")
    shutil.copy2(src / "adapter_meta.json", out / "adapter_meta.json")
    meta = json.loads((src / "adapter_meta.json").read_text(encoding="utf-8"))
    info = {}
    if a.run_info:
        shutil.copy2(a.run_info, out / "run_info.json")
        info = json.loads(Path(a.run_info).read_text(encoding="utf-8"))
    if a.config:
        shutil.copy2(a.config, out / "config_used.json")
    evaluation = None
    if a.scored:
        shutil.copy2(a.scored, out / "evaluation_scored.json")
        evaluation = eval_summary(a.scored)
    for extra in a.extra or []:
        shutil.copy2(extra, out / Path(extra).name)

    heads = meta["n_heads"]
    routing = ("none (single adapter)" if heads == 1 else
               "needs a complexity label per query: the true label is not available in deployment, so Agent 1's live classifier "
               "must supply it (a wrong head costs accuracy; see the project results)")
    manifest = {
        "name": a.name, "version": a.version, "role": a.role, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "method": meta["method"], "base_model": meta["base_model"], "rank": meta["rank"], "alpha": meta["alpha"],
        "n_heads": heads, "heads": meta.get("heads"), "targets": meta["targets"], "default_head": meta.get("default_head"),
        "routing_requirement": routing, "seed": info.get("seed"), "trainable_params": info.get("trainable_params"),
        "train_seconds_total": info.get("train_seconds_total"), "train_peak_vram_gb": info.get("peak_vram_gb"),
        "validation_loss": info.get("val_loss"), "evaluation": evaluation, "git_commit": git_commit(),
        "files": {p.name: {"bytes": p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()},
        "adapters_pt_sha256": sha256(out / "adapters.pt"), "note": a.note,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out / "LOAD_ME.md").write_text(LOAD_ME.format(base=meta["base_model"], note=a.note or ""), encoding="utf-8")
    print(f"packaged {out}  (role: {a.role}, sha256 {manifest['adapters_pt_sha256'][:12]}...)")
    print("Commit only manifest.json to the repository (copy it as <name>_<version>_manifest.json); the weights stay on Drive.")


def cmd_verify(a):
    d = Path(a.dir)
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    if sha256(d / "adapters.pt") != m["adapters_pt_sha256"]:
        problems.append("adapters.pt does not match the recorded SHA-256")
    for name in m["files"]:
        if name != "manifest.json" and not (d / name).exists():
            problems.append(f"missing file: {name}")
    for need in ("LOAD_ME.md", "adapter_meta.json"):
        if not (d / need).exists():
            problems.append(f"missing file: {need}")
    if problems:
        raise SystemExit("VERIFY FAILED: " + "; ".join(problems))
    print(f"VERIFY OK: {m['name']} {m['version']} ({m['role']}), {m['n_heads']} head(s), rank {m['rank']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("package")
    p.add_argument("--name", required=True)
    p.add_argument("--role", required=True, choices=["winner", "runner-up"])
    p.add_argument("--adapter", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--version", default="v1")
    p.add_argument("--run-info", dest="run_info", default="")
    p.add_argument("--config", default="")
    p.add_argument("--scored", default="")
    p.add_argument("--extra", nargs="*", default=[])
    p.add_argument("--note", default="")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_package)
    v = sub.add_parser("verify")
    v.add_argument("--dir", required=True)
    v.set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
