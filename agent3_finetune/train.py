"""Agent 3: ONE training script for every adapter variant, so that methods differ only in the adapter.

  --method lora    one B head  (standard LoRA, the control)           uses hydra.py with n_heads = 1
  --method hydra   four B heads, shared A, routed by complexity label  uses hydra.py with n_heads = 4
  --rank 43        parameter-matched LoRA control (same trainable parameters as hydra at rank 16)

All shared settings live in agent3_finetune/configs/shared_config.json (version-controlled); command-line
flags override them and the merged result is saved next to the run as config_used.json.

Plain PyTorch loop (fp16 autocast, AdamW, linear warm-up + cosine decay, gradient clipping, gradient accumulation).
Every run records total training time and peak GPU memory across resumes. If Colab disconnects, run the same
command again: training resumes from out/checkpoint.pt at the same position in the same data order.

Example (Colab):
  python -m agent3_finetune.train --method hydra --train /content/drive/MyDrive/agent3/train.jsonl \
      --val /content/drive/MyDrive/agent3/val.jsonl --out /content/drive/MyDrive/agent3/runs/hydra_r16_seed42
"""
import argparse
import json
import math
import os
import random
import time
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from agent3_finetune import hydra
from agent3_finetune.train_lora import PROMPT, read_jsonl  # same prompt format as the baseline and evaluation

DEFAULT_CONFIG = Path(__file__).parent / "configs" / "shared_config.json"
OVERRIDABLE = ("model", "rank", "alpha_over_rank", "dropout", "lr", "epochs", "warmup_steps", "weight_decay",
               "max_grad_norm", "batch", "accum", "max_len", "multijoin_repeat", "seed", "vram_cap_gb",
               "save_every", "log_every")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--method", required=True, choices=["lora", "hydra"])
    p.add_argument("--train", required=True)
    p.add_argument("--val", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--max_steps", type=int, default=0, help="stop after this many optimizer steps (smoke test)")
    p.add_argument("--limit", type=int, default=0, help="use only the first N rows (smoke test)")
    for k in OVERRIDABLE:
        p.add_argument(f"--{k}", type=type(json.loads(DEFAULT_CONFIG.read_text())[k]), default=None)
    return p.parse_args()


def load_config(args):
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    for k in OVERRIDABLE:
        if getattr(args, k) is not None:
            cfg[k] = getattr(args, k)
    cfg["alpha"] = cfg["alpha_over_rank"] * cfg["rank"]  # keeps the LoRA scaling (alpha/rank) the same at any rank
    return cfg


def encode(rows, tok, max_len):
    """Tokenise; loss only on the SQL; each item carries the head index of its complexity label."""
    items, dropped, fallbacks = [], Counter(), 0
    for r in rows:
        prompt = tok(PROMPT.format(ddl=r["ddl"], question=r["question"]), add_special_tokens=False)["input_ids"]
        target = tok(r["sql"], add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        if len(prompt) + len(target) > max_len:
            dropped[r["complexity"]] += 1
            continue
        fallbacks += r["complexity"] not in hydra.HEADS
        items.append({"input_ids": prompt + target, "labels": [-100] * len(prompt) + target,
                      "head": hydra.head_index(r["complexity"])})
    return items, dropped, fallbacks


def make_batch(items, pad_id, device):
    m = max(len(b["input_ids"]) for b in items)
    pad = lambda seq, v: seq + [v] * (m - len(seq))  # noqa: E731
    ids = torch.tensor([pad(b["input_ids"], pad_id) for b in items], device=device)
    att = torch.tensor([[1] * len(b["input_ids"]) + [0] * (m - len(b["input_ids"])) for b in items], device=device)
    lab = torch.tensor([pad(b["labels"], -100) for b in items], device=device)
    head = torch.tensor([b["head"] for b in items], device=device)
    return ids, att, lab, head


def epoch_groups(n, batch, accum, seed, epoch):
    """Deterministic data order: groups of `accum` micro-batches, one group per optimizer step."""
    g = torch.Generator().manual_seed(seed * 1000 + epoch)
    order = torch.randperm(n, generator=g).tolist()
    micro = [order[i:i + batch] for i in range(0, n, batch)]
    return [micro[i:i + accum] for i in range(0, len(micro), accum)]


def lr_factor(step, warmup, total):
    if step < warmup:
        return (step + 1) / warmup
    return 0.5 * (1 + math.cos(math.pi * (step - warmup) / max(1, total - warmup)))


def main():
    args = parse_args()
    for f in (args.train, args.val):
        if not Path(f).exists():  # check first, so a missing Drive mount cannot leave stray folders behind
            raise SystemExit(f"Data file not found: {f}\nIs Google Drive mounted? Run drive.mount('/content/drive') first.")
    cfg = load_config(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config_used.json").write_text(json.dumps({"method": args.method, **cfg}, indent=2), encoding="utf-8")

    random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])
    torch.cuda.manual_seed_all(cfg["seed"])
    device = "cuda"
    total_mem = torch.cuda.get_device_properties(0).total_memory
    torch.cuda.set_per_process_memory_fraction(min(1.0, cfg["vram_cap_gb"] * 1024 ** 3 / total_mem))
    gpu = torch.cuda.get_device_name(0)
    n_heads = 1 if args.method == "lora" else len(hydra.HEADS)
    print(f"GPU: {gpu} | memory cap {cfg['vram_cap_gb']} GB | method {args.method} ({n_heads} head(s)), rank {cfg['rank']}")

    tok = AutoTokenizer.from_pretrained(cfg["model"])
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    train_rows, val_rows = read_jsonl(args.train, args.limit), read_jsonl(args.val, args.limit)
    train_rows += [r for r in train_rows if r["complexity"] == "multi-join"] * (cfg["multijoin_repeat"] - 1)
    train_items, dropped_tr, fb_tr = encode(train_rows, tok, cfg["max_len"])
    val_items, dropped_va, _ = encode(val_rows, tok, cfg["max_len"])
    per_head = Counter(hydra.HEADS[it["head"]] for it in train_items)
    print(f"train {len(train_items)} (dropped too long: {dict(dropped_tr)}; per head: {dict(per_head)}; label fallbacks: {fb_tr})")
    print(f"val   {len(val_items)} (dropped too long: {dict(dropped_va)})")

    model = AutoModelForCausalLM.from_pretrained(cfg["model"], torch_dtype=torch.float16).to(device)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    router = hydra.Router()
    torch.manual_seed(cfg["seed"])  # same adapter initialisation for the same seed
    hydra.add_adapters(model, router, cfg["rank"], cfg["alpha"], n_heads, cfg["dropout"])
    params = [p for p in model.parameters() if p.requires_grad]
    trainable = hydra.count_trainable(model)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"trainable parameters: {trainable:,} of {total_params:,} ({100 * trainable / total_params:.2f}%)")

    opt = torch.optim.AdamW(params, lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    scaler = torch.amp.GradScaler("cuda")
    steps_per_epoch = len(epoch_groups(len(train_items), cfg["batch"], cfg["accum"], cfg["seed"], 0))
    total_steps = steps_per_epoch * int(cfg["epochs"])
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    print(f"{steps_per_epoch} steps per epoch, {total_steps} steps in total")

    ckpt_path = out / "checkpoint.pt"
    start, elapsed_before, peak_before = 0, 0.0, 0.0
    if ckpt_path.exists():
        st = torch.load(ckpt_path, map_location="cpu")
        model.load_state_dict(st["adapters"], strict=False)
        opt.load_state_dict(st["opt"])
        scaler.load_state_dict(st["scaler"])
        start, elapsed_before, peak_before = st["step"], st["elapsed"], st["peak_gb"]
        print(f"resuming from step {start}")

    def save_checkpoint(step):
        state = {"step": step, "adapters": {k: v.detach().cpu() for k, v in model.state_dict().items() if "lora_" in k},
                 "opt": opt.state_dict(), "scaler": scaler.state_dict(),
                 "elapsed": elapsed_before + time.time() - t0, "peak_gb": max(peak_before, torch.cuda.max_memory_allocated() / 1024 ** 3)}
        tmp = out / "checkpoint.tmp"
        torch.save(state, tmp)
        os.replace(tmp, ckpt_path)

    t0 = time.time()
    step, window = 0, []
    model.train()
    for epoch in range(int(cfg["epochs"])):
        for group in epoch_groups(len(train_items), cfg["batch"], cfg["accum"], cfg["seed"], epoch):
            if step >= total_steps:
                break
            if step < start:  # already done before the disconnect: same order, so just skip
                step += 1
                continue
            loss_sum = 0.0
            for mb in group:
                ids, att, lab, head = make_batch([train_items[i] for i in mb], tok.pad_token_id, device)
                router.set(head)
                with torch.autocast("cuda", dtype=torch.float16):
                    loss = model(input_ids=ids, attention_mask=att, labels=lab).loss / len(group)
                scaler.scale(loss).backward()
                loss_sum += loss.item()
            lr = cfg["lr"] * lr_factor(step, cfg["warmup_steps"], total_steps)
            for g in opt.param_groups:
                g["lr"] = lr
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, cfg["max_grad_norm"])
            scaler.step(opt)
            scaler.update()
            opt.zero_grad(set_to_none=True)
            step += 1
            window.append(loss_sum)
            if step % cfg["log_every"] == 0:
                avg = sum(window) / len(window)
                window = []
                print(f"step {step}/{total_steps}  loss {avg:.4f}  lr {lr:.2e}  "
                      f"{(elapsed_before + time.time() - t0) / 60:.1f} min", flush=True)
                with open(out / "train_log.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"step": step, "loss": round(avg, 5), "lr": lr}) + "\n")
            if step % cfg["save_every"] == 0:
                save_checkpoint(step)

    # validation loss (token-weighted mean over the SQL tokens)
    model.eval()
    tot, ntok = 0.0, 0
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for i in range(0, len(val_items), cfg["batch"]):
            ids, att, lab, head = make_batch(val_items[i:i + cfg["batch"]], tok.pad_token_id, device)
            router.set(head)
            n = (lab[:, 1:] != -100).sum().item()
            tot += model(input_ids=ids, attention_mask=att, labels=lab).loss.item() * n
            ntok += n
    val_loss = tot / max(1, ntok)

    info = {"method": args.method, "n_heads": n_heads, "model": cfg["model"], "gpu": gpu, "seed": cfg["seed"],
            "rank": cfg["rank"], "alpha": cfg["alpha"], "lr": cfg["lr"], "epochs": cfg["epochs"],
            "max_len": cfg["max_len"], "multijoin_repeat": cfg["multijoin_repeat"], "steps": step,
            "train_examples": len(train_items), "val_examples": len(val_items),
            "train_examples_per_head": dict(per_head), "dropped_train": dict(dropped_tr), "dropped_val": dict(dropped_va),
            "trainable_params": trainable, "total_params": total_params, "val_loss": round(val_loss, 5),
            "train_seconds_total": round(elapsed_before + time.time() - t0),
            "peak_vram_gb": round(max(peak_before, torch.cuda.max_memory_allocated() / 1024 ** 3), 2)}
    hydra.save_adapters(model, out / "adapter",
                        {"method": args.method, "n_heads": n_heads, "heads": list(hydra.HEADS), "rank": cfg["rank"],
                         "alpha": cfg["alpha"], "dropout": cfg["dropout"], "targets": list(hydra.TARGETS),
                         "base_model": cfg["model"], "default_head": hydra.DEFAULT_HEAD})
    (out / "run_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
