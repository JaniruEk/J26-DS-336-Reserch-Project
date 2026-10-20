# Request for Thathsarani: LoRA and HydraLoRA adapters for the team app

From: Janiru (Agent 1, team app) · To: Thathsarani (Agent 3) · 20 Oct 2026

The team app (chat, pipeline trace, dashboard) runs Agent 1 for real, and Karunanayake's quantized model as the SQL writer on a laptop GPU. The SQL-generation stage still shows **stand-in**. With the files below I can connect your real LoRA and HydraLoRA models, so the PP1 demo shows your work inside the team pipeline, and I can re-run Agent 1's results on your fine-tuned model.

**How to send:** zip each folder **without changing its internal structure**, put it in a Google Drive folder and share the link with me (not in git: the files are too large). Fill in the checklist below as a short reply, or as a `README.txt` inside the zip.

---

## Files

| # | What | Where it is (from your scripts) | Contents expected |
|---|---|---|---|
| 1 | LoRA adapter, the **winner** (72/128) | Drive `agent3/runs/lora_r16_seed42/adapter/` | `adapters.pt`, `adapter_meta.json` |
| 2 | HydraLoRA adapter, the **runner-up** (66/128) | Drive `agent3/runs/hydra_r16_seed42/adapter/` | `adapters.pt`, `adapter_meta.json` |

Your manifests on `thathsarani-demo` (`agent3_finetune/artifacts/*_manifest.json`) describe these. If they contain checksums, the zips must match them.

## Please confirm

- [ ] Base model: `Qwen/Qwen2.5-1.5B-Instruct` (same revision you trained on).
- [ ] Prompt: exactly `agent3_finetune/train_lora.PROMPT` (`### Schema:` / `### Question:` / `### SQL:`), with the full-schema DDL from `build_dataset.py`. I'll pass Agent 1's **pruned** schema in the same format; tell me if anything in the format must differ.
- [ ] Decoding: greedy, `max_new_tokens` 256, cut at the first `;` (as in your demo).
- [ ] HydraLoRA head order (`simple, single-join, multi-join, aggregation`) and the default head when no label is given (`single-join`?).
- [ ] Can I use `agent3_finetune/demo/engine.py` from your `thathsarani-demo` branch as is? Better: open a PR to `main` for `agent3_finetune/demo/` and `agent3_finetune/hydra.py` changes, so the app doesn't depend on an unmerged branch.

## How it will be used (so you can check it)

`generate(question, ddl, hint)` in the app → your engine in LoRA or HydraLoRA mode → SQL. For HydraLoRA, the head is chosen by the complexity label in Agent 1's handoff. That is the new schema-aware classifier: .676 routing accuracy on your 148 questions, against .588 for the one in your demo. The chat trace will show which head answered.

## Optional, but it finishes two of your experiments

- [ ] The **four fixed-head runs** (each head on all 148 questions, `evaluate.py` with the fixed-head option, about 12 min on Colab). They give your routing-error curve, and the exact HydraLoRA accuracy with Agent 1's new classifier (estimated .45–.54 today).
- [ ] Sign-off on the Agent 1 → Agent 3 handoff fields: `query, complexity, mode, anchor, matched, tables, ddl, tokens, latency_ms, trace`.

---

## What happens next

1. I add an `agent3:lora` / `agent3:hydra` option to the app's model switch, using your engine and your training prompt. It falls back to the current stand-in until your files arrive, so nothing breaks meanwhile.
2. When the files arrive, I check a few known answers from your own results before the demo uses them.
3. Your stage in the chat switches from **stand-in** to **real**, with the head that answered shown in the trace, and I re-run the evaluations so we can quote numbers measured on the integrated pipeline.

Questions: message me. Setup and run instructions for the app are in `RUNNING_THE_APP.md`.
