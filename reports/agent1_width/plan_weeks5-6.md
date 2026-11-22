# Width Study Weeks 5-6 (Model Sizes, Hypotheses 1 and 4) Implementation Plan

> **Amended 23 Nov 2026:** no Colab GPU runtime was available. All runs are on the laptop: 0.5B and 3B FP16 (dev + train); no 7B (user decision); driver `scripts/local_size_runs.sh`. Rules: README, "Pre-registered rules for model sizes" (H1 = D(3B) - D(0.5B)). Tasks 5-6 below (Colab) are replaced by that script.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the width curves for Qwen2.5 0.5B, 1.5B, 3B and 7B (all FP16, same GPU, same prompt and decoding),
and test hypothesis 1 (best width narrower for smaller models) and hypothesis 4 (selector transfer across models).

**Architecture:** Same sweep (`scripts/width_sweep.py --local fp16`) for every size; only the Hugging Face model id
changes (`--hf-model`). The runs happen on a Google Colab GPU (evaluation hardware, not the deployment target) from
`notebooks/width_sweep_colab.ipynb`; results are written to the user's Google Drive and copied back to
`results/width/colab/`. Two analysis additions: a transfer row in `scripts/width_selector.py` and a size comparison
(`scripts/width_sizes.py`) on pure functions in `agent1_retrieval/width.py`. Decision rules are fixed in the README
BEFORE any new run (Task 1), because hypothesis 3 already failed and the remaining tests must not look tuned.

**Tech Stack:** Python, transformers (FP16), scikit-learn, pytest, Google Colab (A100 recommended).

**Spec:** `CLAUDE.md` ("Plan to PP2", "Hypotheses to test", "Implementation queue" steps 5-6) and
`reports/agent1_width/README.md` (1.5B results of 22 Nov 2026).

## Global Constraints

- Same prompt and decoding for all sizes: Agent 4's `src.prompt_builder.build_prompt` + `src.qwen_generate.generate_sql` (greedy, max 100 new tokens), FP16. Never mix Ollama rows into this comparison.
- Do not edit Agent 4's files under `src/`. Do not change `RECOMMENDED` / `LIVE` or old result files.
- Never delete `results/width/*.jsonl`. Colab outputs: `results/width/colab/{dev,train}_qwen{size}_fp16.jsonl`.
- No number in a report until its result file is committed; say which model, precision and hardware produced it.
- Project text never names a GPU model or a memory size for the target: say "mid-range hardware". The Colab GPU is named only as evaluation hardware.
- The user's Google account is never operated by Claude: the user uploads and runs the notebook.
- Qwen2.5-3B-Instruct has the Qwen Research licence (not Apache 2.0): fine for this study, never for the deployed system.
- Commit only what the plan says; never push unless the user asks.

## Review Focus

1. Colab disconnects mid-run: the start cell is re-run and every sweep resumes from its Drive file, losing at most one question. Pinned by: resumable sweep (existing) + notebook writes `--out` on Drive.
2. Two models written to one file: the default run name must contain the model id. Pinned by: Task 2 test.
3. Rows of different models joined on different questions: the size table uses only ids present in every file and prints that count. Pinned by: Task 4 test.
4. Bigger models write longer SQL and hit the 100-token cut more often: count answers >= 95 tokens per size; above 3% anywhere -> report and decide with the user (raising the limit means re-running all sizes). Pinned by: Task 7 step.
5. A different GPU changes greedy outputs a little: the 1.5B run is repeated on Colab; all four sizes in the size table come from Colab; the laptop/Colab agreement is reported. Pinned by: Task 4 `--same` line + Task 6 run.

---

### Task 1: Fix the decision rules before any new run

**Files:** Modify `reports/agent1_width/README.md` (new section "Pre-registered rules for model sizes", above "Not done yet")

- [ ] **Step 1: Write the section with exactly these rules**
  - Test set: the dev ids of the sweep files; every comparison uses the ids present in all files compared.
  - All size comparisons use the Colab runs (same GPU, FP16).
  - Distraction D(model) = accuracy(W4) - accuracy(W2) on the test set.
  - **H1 primary test:** D(7B) - D(0.5B) > 0, 95% paired bootstrap CI (10,000 resamples of questions, seed 0) excludes 0. Secondary (descriptive): best fixed width per size; D for all four sizes; simple-bucket accuracy(W1) - accuracy(W4) per size.
  - **H4 test:** on the 0.5B, 3B and 7B test rows, the selector trained on that model's own train rows against the selector trained on the 1.5B train rows (exact McNemar). Supported if own beats transfer at p < 0.0167 (0.05 / 3) for at least one model.
  - Hardware check (descriptive): agreement of the per-width correct flags between the laptop and Colab 1.5B runs.
  - Not done in these weeks: changing the label or the selector (post-hoc; separate decision by the user).
- [ ] **Step 2: Commit** `git commit -m "Width study: pre-registered rules for model sizes (H1, H4)"`

### Task 2: Any Qwen size in the local sweep

**Files:** Modify `harness/generators.py` (`qwen_local`), `scripts/width_sweep.py` (`--hf-model`, run name). Test: `tests/test_agent1.py`.

**Interfaces:**
- Produces: `qwen_local(precision="fp16", model=None)`; `model=None` keeps `Qwen/Qwen2.5-1.5B-Instruct`. Default 1.5B run name stays `qwen2.5-1.5b-instruct_fp16_transformers`; others `<model id after '/', lower case>_<precision>_transformers`.

- [ ] **Step 1: Write the failing test** `test_qwen_local_loads_the_requested_model`: fake `torch.cuda.is_available` and Agent 4's `load_qwen`; `qwen_local("int4", model="Qwen/Qwen2.5-0.5B-Instruct").load()` must call `load_qwen("int4")` while `src.qwen_model_loader.MODEL_NAME == "Qwen/Qwen2.5-0.5B-Instruct"`; labels start with `Qwen2.5-0.5B-Instruct INT4` and (default) `Qwen2.5-1.5B-Instruct FP16`.
- [ ] **Step 2: Run, expect FAIL** (`unexpected keyword argument 'model'`): `python -m pytest tests/test_agent1.py -k qwen_local -v`
- [ ] **Step 3: Implement**: set Agent 4's module global `MODEL_NAME` before `load_qwen` (her loader reads it; her code stays identical for every size), with a `ponytail:` comment; `--hf-model` (only with `--local`) in `width_sweep.py`.
- [ ] **Step 4: Run** `python -m pytest tests/test_agent1.py -k "qwen_local or width" -v`, expect PASS.
- [ ] **Step 5: Commit** `git commit -m "Width sweep: --hf-model for other Qwen sizes"`

### Task 3: Transfer selector (hypothesis 4)

**Files:** Modify `scripts/width_selector.py` (`--transfer <train rows of another model>`). Test: `tests/test_agent1.py`.

**Interfaces:** with `--transfer`, a system row `"transfer selector"` and a line `learned selector against the transfer selector: ...`.

- [ ] **Step 1: Failing test**: synthetic train file + a second train file whose `ok` flags favour a wider width; run `main()` with `--test` and `--transfer`; output contains `transfer selector` and `against the transfer selector`.
- [ ] **Step 2: Run, expect FAIL** (`unrecognized arguments: --transfer`).
- [ ] **Step 3: Implement** by reusing the train/test fit of `pick()` with the transfer file's labelled rows.
- [ ] **Step 4: Run** `python -m pytest tests/test_agent1.py -k width -v`, expect PASS.
- [ ] **Step 5: Commit** `git commit -m "Width selector: --transfer row for hypothesis 4"`

### Task 4: Size comparison (hypothesis 1)

**Files:** Modify `agent1_retrieval/width.py`; create `scripts/width_sizes.py`. Test: `tests/test_agent1.py`.

**Interfaces:**
- `distraction(rows, wide="W4", narrow="W2") -> float`; `size_effect(small, large, wide="W4", narrow="W2", n_boot=10000, seed=0) -> {"n", "d_small", "d_large", "diff", "ci"}` (rows joined on `id`, shared ids only; per-question paired difference; `stats.bootstrap_ci`).
- CLI: `python -m scripts.width_sizes <test files, smallest model first> --h1 <small> <large> [--same <a> <b>]`: accuracy by width x bucket and best fixed width per file, D per file, the H1 line, and for `--same` the share of equal per-width flags plus `size_effect(a, b)`.

- [ ] **Step 1: Failing test** `test_distraction_and_size_effect`: small model W4 wrong on half of 200 questions, large never; `distraction(small) == -0.5`, `distraction(large) == 0`; `size_effect(small, large + [extra id])` has `n == 200`, `diff == 0.5`, `ci[0] > 0`.
- [ ] **Step 2: Run, expect FAIL** (`ImportError`).
- [ ] **Step 3: Implement**; the per-file table reuses `width_sweep.summary` by import.
- [ ] **Step 4: Run** the tests, then the CLI on the laptop 1.5B file: D must be .53 - .57 = -.04 (README table).
- [ ] **Step 5: Commit** `git commit -m "Width study: size comparison for hypothesis 1"`

### Task 5: Colab notebook and upload bundles

**Files:** Create `notebooks/width_sweep_colab.ipynb`, `scripts/make_colab_bundle.py` (writes `data/colab/j26_code.zip` from `git archive HEAD` and `data/colab/j26_data.zip` with the Spider dev + train DBs, `chinook.db`, `northwind.db`).

Notebook cells: (1) GPU check (`nvidia-smi`), mount Drive; (2) unzip both bundles from `MyDrive/j26_width/` to `/content/j26`; (3) `pip install -r requirements.txt` + the GPU requirements, spaCy model; (4) `pytest -q tests/test_agent1.py -k width`; (5) smoke: 10 questions per model to a throw-away folder; (6) start the runs as background processes, `--out` and logs on Drive; (7) progress (row counts per file, last log lines, `nvidia-smi`); (8) final summary lines. Re-running cell 6 must not start a second process for a file that is already running (check with `pgrep -f <out file>`).

- [ ] Steps: build bundle, check zip sizes and contents; run the notebook's cells 2-4 locally where possible (unzip + tests on Windows) to catch path errors; commit notebook and bundle script (not the zips).

### Task 6: The runs (user starts them on Colab; resumable; all with `--elbow`)

Phase A (in parallel): 0.5B dev, 0.5B train, 1.5B dev, 3B dev, 3B train. Phase B (in parallel, after A): 7B dev, 7B train.
On a GPU with less memory than both 7B runs need, run 7B dev first, then 7B train.

### Task 7: Analysis and Stop point C

- [ ] **Step 1:** `python -m scripts.width_sizes results/width/colab/dev_qwen0.5b_fp16.jsonl results/width/colab/dev_qwen1.5b_fp16.jsonl results/width/colab/dev_qwen3b_fp16.jsonl results/width/colab/dev_qwen7b_fp16.jsonl --h1 results/width/colab/dev_qwen0.5b_fp16.jsonl results/width/colab/dev_qwen7b_fp16.jsonl --same results/width/dev_qwen1.5b_fp16.jsonl results/width/colab/dev_qwen1.5b_fp16.jsonl`
- [ ] **Step 2:** For 0.5B, 3B, 7B: `python -m scripts.width_selector results/width/colab/train_qwen<s>_fp16.jsonl --test results/width/colab/dev_qwen<s>_fp16.jsonl --transfer results/width/colab/train_qwen1.5b_fp16.jsonl` (the 1.5B train file on Colab is not re-run: use `results/width/train_qwen1.5b_fp16.jsonl`).
- [ ] **Step 3:** Count answers >= 95 Qwen tokens per size and width; above 3% anywhere -> report to the user.
- [ ] **Step 4:** Tables and "H1 / H4: supported / not supported" with numbers in `reports/agent1_width/README.md`; update Agent 1 status in `CLAUDE.md`; commit with the result files.
- [ ] **Step 5: Stop point C.** Show the user the size table, the H1, H4 and hardware lines. Wait.
