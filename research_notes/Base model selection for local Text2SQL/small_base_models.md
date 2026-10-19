# Small open-weight base models for a local Text-to-SQL pipeline (as of Oct 2026)

Provenance key: **[F]** = fetched and read this session; **[MC]** = standard model-card fact from prior knowledge of the official card, URL given but NOT re-fetched this session (re-check before citing in the dissertation); **[S]** = search-snippet / aggregator only (lower confidence).

## Q1. Candidate comparison table (facts)

### Takeaway
The realistic 0.5–1.5B shortlist is Qwen2.5-Coder-0.5B/1.5B-Instruct, Qwen3-0.6B/1.7B, and (newest) Qwen3.5-0.8B/2B. Only Qwen and Llama families give an Apache/permissive small model **plus** a same-tokenizer ~7–9B teacher. Phi-3 Mini has no same-tokenizer ~7B sibling and sits outside the 0.5–1.5B student range.

### Cited Findings

| Model | Params | Licence (academic / commercial) | Context | Tokenizer / vocab | Released | Same-tokenizer ~7B teacher? | Status Oct 2026 |
|---|---|---|---|---|---|---|---|
| Qwen2.5-0.5B / 1.5B-Instruct | 0.49B / 1.54B | Apache 2.0 (yes/yes) [MC] | 32K [MC] | Qwen BPE, ~151.6K [MC] | Sep 2024 [MC] | Qwen2.5-7B-Instruct | superseded by Qwen3/3.5 but still the most studied |
| Qwen2.5-Coder-0.5B / 1.5B-Instruct | 0.49B / 1.54B | Apache 2.0 [MC] ("permissive licensing" per tech report [F]) | 32K (YaRN to 128K) [F] | Qwen BPE, same as Qwen2.5 [MC] | Sep–Nov 2024 [MC] | **Qwen2.5-Coder-7B-Instruct** (and OmniSQL-7B is a Qwen2.5-Coder-7B fine-tune [F]) | older, but best SQL evidence at ≤1.5B |
| Qwen3-0.6B / 1.7B | 0.6B / 1.7B | Apache 2.0 [MC] | 32K [MC] | Qwen BPE ~151.7K [MC] | Apr 2025 [MC] | Qwen3-8B | current; thinking/non-thinking switch |
| **Qwen3.5-0.8B / 2B** (newest small Qwen) | 0.8B / 2B (also 4B, 9B) | Apache 2.0, commercial OK — [Gigazine](https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small) [S], [HF card](https://huggingface.co/Qwen/Qwen3.5-0.8B) [F] | 262,144 native [F] | **248,320** vocab (new, differs from Qwen2.5/3) [F] | Feb–Mar 2026 [F][S] | Qwen3.5-9B (9B, not 7B) [S] | newest; hybrid Gated-DeltaNet + gated attention, vision encoder, needs bleeding-edge transformers/vLLM [F] |
| Llama-3.2-1B-Instruct | 1.23B | Llama 3.2 Community Licence (commercial OK below 700M MAU; acceptable-use policy) [MC] | 128K [MC] | Llama 3 tiktoken-style, 128K vocab [MC] | Sep 2024 [MC] | Llama-3.1-8B-Instruct | superseded; no Llama 4 small model [gap] |
| SmolLM2-360M / 1.7B | 0.36B / 1.7B | Apache 2.0 [MC] | 8K [MC] | 49K vocab [MC] | Nov 2024 [MC] | **none** (family stops at 1.7B) | superseded by SmolLM3 |
| SmolLM3-3B | 3B | Apache 2.0 [F] | 64K trained, 128K via YaRN [F] | not stated on card [F] | Jul 2025 [MC] | none (single size) | outside 0.5–1.5B; reasoning on by default [F] |
| DeepSeek-Coder-1.3B-Instruct | 1.3B | DeepSeek Model Licence (commercial OK with use restrictions) [MC] | 16K [MC] | 32K vocab [MC] | Nov 2023 [MC] | DeepSeek-Coder-6.7B | **old/superseded**, but strong after SQL fine-tuning (below) |
| Gemma 3 1B-it | 1B | Gemma Terms of Use (commercial OK, use policy) [MC] | 32K [MC] | 262K vocab (embedding-heavy at 1B) [MC] | Mar 2025 [MC] | no 7B; 4B/12B siblings | text-only at 1B |
| Gemma 2 2B-it | 2.6B | Gemma Terms [MC] | 8K [MC] | 256K vocab [MC] | Jul 2024 [MC] | Gemma 2 9B | superseded by Gemma 3 |
| Phi-3-mini (4K/128K) | 3.8B | MIT [F] | 4K / 128K [F] | Llama-2 style 32,064 vocab [MC] | Apr 2024 [MC] | **No**: Phi-3-small (7B) uses a different ~100,352 vocab [F](https://huggingface.co/microsoft/Phi-3-small-8k-instruct); Phi-3-medium is 14B | superseded by Phi-3.5-mini (Aug 2024) and Phi-4-mini (Feb 2025, 200K vocab) [MC] |
| Prem-1B-SQL | 1.3B | see card (built on DeepSeek-Coder-1.3B) [S] | — | DeepSeek-Coder | 2024 | DeepSeek-Coder-6.7B | SQL specialist |
| CodeS-1B / 3B | 1B / 3B (also 7B, 15B) | — | — | StarCoder | 2024 (SIGMOD) [F](https://arxiv.org/abs/2402.16347) | CodeS-7B | **old**, StarCoder-based |
| XiYanSQL-QwenCoder-3B (2502/2504) | 3.1B | see card | — | Qwen2.5-Coder | 2025 [S] | XiYanSQL-QwenCoder-7B | SQL specialist, above 1.5B |
| SLM-SQL-0.5B…1.5B | 0.5–1.5B | see card | — | Qwen2.5-Coder / Qwen3 / Llama / DeepSeek | Jul 2025 [F](https://arxiv.org/abs/2507.22478) | — | SQL specialists (SFT+RL) |
| OmniSQL-7B/14B/32B | 7B+ | arXiv text under CC BY-NC-ND 4.0 [F]; weight licence not checked | — | Qwen2.5-Coder | Mar 2025 [F](https://arxiv.org/html/2503.02240) | is itself a 7B Qwen2.5-Coder teacher candidate | no small sizes |

- Qwen3.5 small series = 0.8B, 2B, 4B, 9B, Apache 2.0, supports LoRA/full fine-tuning on consumer GPUs — [Gigazine](https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small) [S]; [aibase](https://news.aibase.com/news/25854) [S].
- Qwen3.5-0.8B: 24 layers, "6 x (3 x Gated DeltaNet->FFN) -> 1 x (Gated Attention->FFN)", hidden 1024, vision encoder (Image-Text-to-Text), non-thinking by default, requires transformers from main / vLLM nightly — [HF card](https://huggingface.co/Qwen/Qwen3.5-0.8B) [F]. (The fetch summary also said "sparse MoE"; that seems inconsistent with a 0.8B dense card. Treat it as unverified.)
- Qwen4 was only *previewed* (Max/Flash/Plus/27B), with no weights as of Sep 2026 — [llmreference changelog](https://www.llmreference.com/changelog/2026-09) [S, aggregator]. No newer small Qwen than Qwen3.5 found.

### Inferences
- If the team wants a same-family 7B teacher with an **identical tokenizer** (needed for logit-level KD), the clean pairs are: Qwen2.5-Coder-7B to Qwen2.5-Coder-1.5B/0.5B; Qwen3-8B to Qwen3-1.7B/0.6B; Llama-3.1-8B to Llama-3.2-1B; DeepSeek-Coder-6.7B to 1.3B. Qwen3.5's teacher is 9B (4-bit needed on 8GB) and Phi-3-mini has none.
- Qwen3.5's new hybrid linear-attention architecture is a tooling risk for this project specifically: AWQ/GGUF kernels, PEFT target modules for HydraLoRA, and QAT recipes are much more mature for standard transformer blocks (Qwen2.5/Qwen3/Llama). This is an inference, not a verified incompatibility.

### Gaps
- Exact Qwen3.5-2B/9B context, vocab and layer specs were not fetched. Qwen3.5 weight-licence text was confirmed only via the HF card summary.
- Licences of Prem-1B-SQL, CodeS, XiYanSQL-3B and OmniSQL *weights* were not verified.
- No Llama 4 or Gemma 4 sub-2B models were checked.

## Q2. Published Text-to-SQL results (Spider / BIRD), base vs fine-tuned

### Takeaway
At 0.5–1.5B, the only head-to-head, same-protocol study found is SLM-SQL (arXiv 2507.22478). After SFT+RL+self-consistency, Qwen2.5-Coder-1.5B is best (BIRD dev 67.08%) and the 0.5–0.6B models reach about 55–60%. Zero-shot small models are far weaker (roughly 28–46% BIRD in that paper's baselines). Strong numbers at this size come from heavy fine-tuning, not from the base model.

### Cited Findings
- SLM-SQL abstract: SFT + RL on SynSQL-derived data (SynSQL-Think-916K, SynSQL-Merge-Think-310K) + corrective self-consistency; "five evaluated models achieved an average improvement of 31.4 points" on BIRD dev; "0.5B model reached 56.87% EX, while the 1.5B model achieved 67.08% EX" — [arXiv 2507.22478](https://arxiv.org/abs/2507.22478) [F].
- SLM-SQL Table 2 (BIRD dev, fine-tuned): Qwen2.5-Coder-0.5B 56.87; Qwen3-0.6B 59.52; Llama-3.2-1B 54.78; DeepSeek-Coder-1.3B 62.19; Qwen2.5-Coder-1.5B 67.08 — [arXiv html](https://arxiv.org/html/2507.22478) [F]. Listed baselines: DeepSeek-Coder-1.3B 46.0, Qwen2.5-Coder-0.5B 28.40. The tool output gave 28.40 for the 1.5B baseline too, which looks like an extraction error, so **re-check Table 2 before citing baselines**.
- SLM-SQL-1.5B on Spider (trained on BIRD data, i.e. cross-dataset): 76.72% dev / 79.06% test EX — [search summary of arXiv 2507.22478](https://arxiv.org/pdf/2507.22478) [S]. A second table read gave Spider numbers by model, with baseline to SFT+RL+CSC: Qwen2.5-Coder-0.5B 42.13 to 72.08 (dev); Qwen3-0.6B 63.19 to 72.99; Llama-3.2-1B 30.79 to 69.12; DeepSeek-Coder-1.3B 48.23 to 76.11; Qwen2.5-Coder-1.5B 63.54 to 76.72 (dev), 67.61 to 79.06 (test) — [arXiv html](https://arxiv.org/html/2507.22478) [F; the fetch labelled this table "BIRD" but the 76.72 / 79.06 values match the Spider numbers in the abstract and search snippet, so I read it as **Spider**. Verify.]
- Prem-1B-SQL (DeepSeek-Coder-1.3B full fine-tune): 51.54% EX on BIRD private test and about 85% on Spider — [Prem blog](https://blog.premai.io/prem-1b-sql-fully-local-performant-slm-for-text-to-sql) [S, vendor-reported].
- XiYanSQL-QwenCoder-3B-2504: BIRD dev 54.11% (M-Schema) / 53.19% (DDL); Spider test 82.69% — [featherless model page](https://featherless.ai/models/XGenerationLab/XiYanSQL-QwenCoder-3B-2504) [S, mirrors the vendor card].
- OmniSQL (Qwen2.5-Coder base, SynSQL-2.5M + Spider + BIRD, greedy): OmniSQL-7B Spider dev 81.2 / test 87.9 / BIRD dev 63.9. Untuned Qwen2.5-Coder-7B-Instruct: 73.4 / 82.2 / 50.9. The paper has **no** sub-7B results — [arXiv 2503.02240](https://arxiv.org/html/2503.02240) [F].
- The Qwen2.5-Coder tech report gives Text-to-SQL results only in a figure (Fig. 12), so no sub-7B table numbers could be extracted — [arXiv 2409.12186](https://arxiv.org/html/2409.12186) [F].
- CodeS (StarCoder-based; 1B/3B/7B/15B; incremental SQL-centric pre-training) reports competitive Spider/BIRD at 1B/3B. Exact numbers were not extracted — [arXiv 2402.16347](https://arxiv.org/abs/2402.16347) [F].
- "How Small Can You Go?" (arXiv 2607.25583) uses T5-small (60M) on **WikiSQL** (single-table). LoRA r=16 gives 59.6% EM vs 71.2% full FT; QLoRA INT8/NF4 gives about 53% EM at 0.60 GB — [arXiv 2607.25583](https://arxiv.org/abs/2607.25583) [F]. Not comparable to Spider/BIRD, and its model is far smaller than the proposed students.

### Inferences
- Fine-tuning gain at 0.5–1.5B is large: about +15 to +40 points on BIRD dev in SLM-SQL (the abstract's average is +31.4). Part of that comes from RL and self-consistency, not SFT alone, so a plain-LoRA SFT gain on Chinook/Spider will likely be smaller.
- Qwen2.5-Coder-1.5B has the best ceiling in the only like-for-like study. Qwen3-0.6B has the strongest *untuned* sub-1B baseline (63.19 vs 42.13 for Coder-0.5B, Spider dev per the table read above). That makes Qwen3-0.6B a good "native small" comparator.

### Gaps
- No verified Spider/BIRD numbers were found for Qwen3.5-0.8B/2B, Gemma 3 1B, SmolLM2/3 or Phi-3/3.5/4-mini under a comparable protocol.
- Qwen3-1.7B was not in SLM-SQL; no comparable number was found.
- The MATS abstract page (arXiv 2512.18622) did not show base models or scores. The project's figures (87.1% Spider / 64.73% BIRD, 9B total) come from CLAUDE.md and were not re-verified here.

## Q3. Which fine-tune well for SQL at small scale; Phi-3 Mini as shared base; recommendation

### Takeaway
**Recommended shared placeholder and student family: Qwen2.5-Coder-1.5B-Instruct**, with Qwen2.5-Coder-7B-Instruct as the same-tokenizer teacher (Apache 2.0, best published fine-tuned result at ≤1.5B, mature PEFT/AWQ/GGUF tooling). For the "native small vs distilled" comparison, use the same checkpoint before and after distillation. A modern alternative family is Qwen3-1.7B/0.6B with a Qwen3-8B teacher. Phi-3 Mini is not a good *shared* base for a 0.5–1.5B plan: keep it only as an external reference point.

### Cited Findings
- Small models that fine-tune well for SQL with published evidence: Qwen2.5-Coder-0.5B/1.5B, Qwen3-0.6B, DeepSeek-Coder-1.3B, Llama-3.2-1B (all improved with SFT+RL in SLM-SQL) — [arXiv 2507.22478](https://arxiv.org/abs/2507.22478) [F]; DeepSeek-Coder-1.3B also via Prem-1B-SQL — [Prem blog](https://blog.premai.io/prem-1b-sql-fully-local-performant-slm-for-text-to-sql) [S].
- Phi-3-mini is 3.8B under MIT; its only ~7B sibling (Phi-3-small) uses a different vocabulary (about 100,352 tokens) — [Phi-3-small card](https://huggingface.co/microsoft/Phi-3-small-8k-instruct) [F].

### Inferences
- **Cost of mixing sizes (Phi-3 3.8B placeholder vs 0.5–1.5B real base):**
  1. Agent 3's LoRA-vs-HydraLoRA results and Agent 4's QAT-vs-PTQ results on Phi-3 would not transfer. Quantization sensitivity and adapter-capacity effects scale with model size, so placeholder findings become throwaway work rather than a preview.
  2. The tokenizer differs (Phi-3 32K vocab vs Qwen 151K), so token counts (Agent 1's metric), prompt templates and chat formats all change at swap time.
  3. On 8GB VRAM, LoRA on 3.8B needs 4-bit QLoRA, while 1.5B fits in bf16 LoRA. Training regimes would differ, which confounds the QAT vs PTQ study.
  4. There is no same-tokenizer Phi teacher at about 7B for logit distillation.
- **Practical setup:** Agent 2: teacher Qwen2.5-Coder-7B-Instruct (or OmniSQL-7B if its weight licence allows), student Qwen2.5-Coder-1.5B (or 0.5B). "Native" baseline = the untouched student checkpoint. Agents 3/4: start now on Qwen2.5-Coder-1.5B-Instruct as the placeholder. The swap to the distilled checkpoint is then same-architecture and same-tokenizer, with zero code changes.
- **Why not Qwen3.5 as the primary choice:** it is the newest Apache option, but the hybrid DeltaNet+vision architecture, 248K vocab (embedding-heavy at 0.8B), 9B teacher and immature quantization/PEFT tooling add risk without a published SQL result. It would be a good "future work / re-run" check.
- **Why not the others:** SmolLM2 has no 7B sibling. Gemma 3 1B has no 7B sibling and a 262K vocab. DeepSeek-Coder-1.3B is old (2023) with 16K context. Llama-3.2-1B has a weaker baseline and a more restrictive licence. SQL-specialist checkpoints (Prem-1B-SQL, SLM-SQL, XiYanSQL-3B) are already SQL-tuned, so they would blur the project's own distillation/fine-tuning contribution. Use them as published reference points only.
- **Phi-3 Mini's role:** report it as an "off-the-shelf 3.8B general model" baseline, consistent with Agent 1's phi3 stand-in results. Keep it out of the shared training base.

### Gaps
- No direct measurement found of LoRA vs full-FT gap at 0.5–1.5B on Spider (SLM-SQL uses full SFT+RL).
- No published QAT vs PTQ results for Qwen2.5-Coder-1.5B on SQL were found.
- Verify the OmniSQL weight licence before using it as the teacher.
