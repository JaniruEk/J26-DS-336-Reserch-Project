"""Agent 3, Phase 2: standard LoRA baseline (the control condition).

Fine-tunes a small causal LM on the Spider-train set built by build_dataset.py.
Designed for a free Colab T4:
  - fp16 base model + LoRA adapters kept in fp32
  - hard memory cap (default 8 GB, the project's hardware budget)
  - checkpoints saved regularly and resumed automatically after a disconnect
  - writes run_info.json (GPU, peak VRAM, trainable params, loss) next to the adapter

Example (Colab):
  python -m agent3_finetune.train_lora --train /content/drive/MyDrive/agent3/train.jsonl \
      --val /content/drive/MyDrive/agent3/val.jsonl --out /content/drive/MyDrive/agent3/runs/lora_seed42
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from transformers.trainer_utils import get_last_checkpoint

PROMPT = "### Schema:\n{ddl}\n\n### Question:\n{question}\n\n### SQL:\n"
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")  # placeholder base; one-line switch
    p.add_argument("--train", required=True)
    p.add_argument("--val", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--alpha", type=int, default=32)
    p.add_argument("--epochs", type=float, default=3)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--max_len", type=int, default=1024)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--accum", type=int, default=4)
    p.add_argument("--max_steps", type=int, default=-1, help="use e.g. 50 for a smoke test")
    p.add_argument("--limit", type=int, default=0, help="use only the first N rows (smoke test)")
    p.add_argument("--multijoin_repeat", type=int, default=2, help="over-sample multi-join rows")
    p.add_argument("--vram_cap_gb", type=float, default=8.0)
    return p.parse_args()


def read_jsonl(path, limit=0):
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows[:limit] if limit else rows


class ListDataset(torch.utils.data.Dataset):
    def __init__(self, items):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def encode(rows, tok, max_len):
    """Tokenise; loss is computed on the SQL only (prompt tokens masked with -100)."""
    items, dropped = [], Counter()
    for r in rows:
        prompt = tok(PROMPT.format(ddl=r["ddl"], question=r["question"]), add_special_tokens=False)["input_ids"]
        target = tok(r["sql"], add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        if len(prompt) + len(target) > max_len:
            dropped[r["complexity"]] += 1  # too long to fit; counted so we can report it honestly
            continue
        items.append({"input_ids": prompt + target, "labels": [-100] * len(prompt) + target})
    return items, dropped


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if torch.cuda.is_available():
        total = torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(min(1.0, args.vram_cap_gb * 1024 ** 3 / total))
        gpu = torch.cuda.get_device_name(0)
    else:
        gpu = "cpu (no GPU found - training will be extremely slow)"
    print("GPU:", gpu, "| memory cap:", args.vram_cap_gb, "GB")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    train_rows = read_jsonl(args.train, args.limit)
    val_rows = read_jsonl(args.val, args.limit)
    extra = [r for r in train_rows if r["complexity"] == "multi-join"] * (args.multijoin_repeat - 1)
    train_rows = train_rows + extra
    train_items, dropped_tr = encode(train_rows, tok, args.max_len)
    val_items, dropped_va = encode(val_rows, tok, args.max_len)
    print(f"train examples: {len(train_items)} (dropped as too long: {dict(dropped_tr)})")
    print(f"val examples:   {len(val_items)} (dropped as too long: {dict(dropped_va)})")

    def collate(batch):
        m = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id
        return {
            "input_ids": torch.tensor([b["input_ids"] + [pad] * (m - len(b["input_ids"])) for b in batch]),
            "attention_mask": torch.tensor([[1] * len(b["input_ids"]) + [0] * (m - len(b["input_ids"])) for b in batch]),
            "labels": torch.tensor([b["labels"] + [-100] * (m - len(b["labels"])) for b in batch]),
        }

    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float16)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    cfg = LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05,
                     target_modules=TARGET_MODULES, task_type="CAUSAL_LM")
    model = get_peft_model(model, cfg)
    for p in model.parameters():
        if p.requires_grad:
            p.data = p.data.float()  # fp16 training needs fp32 trainable weights
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"trainable parameters: {trainable:,} of {total_params:,} ({100 * trainable / total_params:.2f}%)")

    ckpt_dir = out / "checkpoints"
    targs = TrainingArguments(
        output_dir=str(ckpt_dir), per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch, gradient_accumulation_steps=args.accum,
        num_train_epochs=args.epochs, max_steps=args.max_steps, learning_rate=args.lr,
        lr_scheduler_type="cosine", warmup_ratio=0.03, fp16=True, logging_steps=20,
        save_steps=200, save_total_limit=2, seed=args.seed, report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=ListDataset(train_items),
                      eval_dataset=ListDataset(val_items), data_collator=collate)

    last = get_last_checkpoint(str(ckpt_dir)) if ckpt_dir.exists() else None
    print("resuming from:", last if last else "scratch")
    t0 = time.time()
    trainer.train(resume_from_checkpoint=last)
    seconds = time.time() - t0

    metrics = trainer.evaluate()
    model.save_pretrained(out / "adapter")
    tok.save_pretrained(out / "adapter")

    info = {
        "model": args.model, "gpu": gpu, "seed": args.seed, "rank": args.rank, "alpha": args.alpha,
        "epochs": args.epochs, "lr": args.lr, "max_len": args.max_len,
        "multijoin_repeat": args.multijoin_repeat, "train_examples": len(train_items),
        "val_examples": len(val_items), "dropped_train": dict(dropped_tr), "dropped_val": dict(dropped_va),
        "trainable_params": trainable, "total_params": total_params,
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2) if torch.cuda.is_available() else None,
        "train_seconds_this_session": round(seconds), "val_loss": metrics.get("eval_loss"),
    }
    (out / "run_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
