# Request for Wathsala: the distilled Qwen2.5-1.5B model

> **Update, 21 Oct 2026:** your `MultiTask_Research/` folder arrived. Your distilled multitask student now runs as **stage 1 of the team app** (the question gate), shown as "real" in the chat and the Explorer. Thank you. One thing is still needed:
>
> **Your exact training prompt**, word for word: the notebook cell that turns a `text` (and its `task`) into the model input, and how you scored the candidate labels. It isn't in the folder. I reconstructed one that reproduces your query-classification result (.997 vs your .994, same label on 1,195 of 1,200), but for prompt-injection detection it only reaches .81 against your .948. The app now uses it anyway as a partial guard (it catches 39 of 60 attacks and flags none of our real questions), and with your prompt it should match your .948.
>
> Also useful: which checkpoint `final_adapter` is (step number), and the notebook itself, committed under `Agent2/`.
>
> The rest of this document is the original request, for the SQL base model.


From: Janiru (Agent 1, team app) · To: Wathsala (Agent 2) · 20 Oct 2026

The team app (chat, pipeline trace, dashboard) runs Agent 1 for real, and Karunanayake's quantized model as the SQL writer on a laptop GPU. With your distilled Qwen2.5-1.5B model I can run it inside the team pipeline, test it on the same evaluation sets as everyone else, and hand it to Thathsarani as the base for her adapters.

**How to send:** zip each folder **without changing its internal structure**, put it in a Google Drive folder and share the link with me (not in git: the files are too large). Fill in the checklist below as a short reply, or as a `README.txt` inside the zip.

---

## Files: the distilled Qwen2.5-1.5B model you are training

| # | What | Contents expected |
|---|---|---|
| 1 | **Distilled student**: Qwen2.5-1.5B-Instruct distilled from the Qwen2.5-7B-Instruct teacher | A Hugging Face model folder: `config.json`, `model.safetensors` (or shards + index), `generation_config.json`, tokenizer files (`tokenizer.json`, `tokenizer_config.json`). If you trained with LoRA, send **either** the merged model **or** the adapter folder (`adapter_config.json`, `adapter_model.safetensors`) and say which |
| 2 | **Native baseline**, if ready: plain Qwen2.5-1.5B-Instruct given the same treatment except distillation (or your C0 control: same prompts, gold-SQL answers) | Same format as #1 |

Same size and tokenizer as the team base (Qwen2.5-1.5B-Instruct), so Thathsarani can train her adapters on it and Agent 4 can quantize it.

## Please confirm

- [ ] Teacher: `Qwen/Qwen2.5-7B-Instruct`; student starting point: `Qwen/Qwen2.5-1.5B-Instruct` (exact revision if pinned).
- [ ] What the student was distilled on: which prompts (Spider **train** schemas only, never Spider dev or the `eval/*.json` questions), how many, and whether teacher answers were kept only when their SQL executed.
- [ ] Training method: soft-target KL on logits, or training on teacher-written answers (sequence-level)? Temperature, epochs, LoRA rank if any.
- [ ] **The exact prompt format** used in training, word for word (chat template or plain text). The app must send the same format, or accuracy drops.
- [ ] Decoding settings you evaluated with (greedy? `max_new_tokens`?).
- [ ] Any numbers you have so far (e.g. distilled vs native on a held-out set), and on which questions.

## How it will be used (so you can check it)

1. **Directly as the SQL writer in the app**, for a first look: Agent 1's pruned schema + the question → your model → SQL, shown live in the chat trace. The same evaluation sets the rest of the team uses (`eval/*.json`, including the hard multi-join set) give comparable numbers.
2. **As the base for Agent 3:** Thathsarani's current adapters were trained on plain Qwen2.5-1.5B-Instruct and **cannot** be moved onto your model. She re-trains LoRA / HydraLoRA on your distilled and native models (the planned comparison), and Agent 4 then quantizes the winner.

## Optional

- [ ] Your Task 1 question classifier (`Task1_Research/finetuned_teacher_kd_student/`, test .999) plus its exact input format and one `predict(question) -> (label, confidence)` cell, if you want it shown as the question gate (stage 1 of the pipeline).

---

## What happens next

1. I add your model as an option in the app's model switch (the current model stays the default until your files arrive).
2. When the files arrive, I check a few known answers from your own results before the demo uses it.
3. I run it on the team's evaluation sets (including the hard multi-join set) and send you the per-question results, so you can quote numbers measured on the integrated pipeline; Thathsarani then re-trains her adapters on it.

Questions: message me. Setup and run instructions for the app are in `RUNNING_THE_APP.md`.
