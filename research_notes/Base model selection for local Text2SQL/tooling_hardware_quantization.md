# Tooling, Hardware and Quantization Constraints for 0.5B–3.8B SLMs on an 8GB-VRAM Budget (as of Oct 2026)

## 1. VRAM for LoRA / QLoRA fine-tuning (0.5B, 1.5B, 3.8B; 1–2k tokens; gradient checkpointing). Does Phi-3 Mini 3.8B 16-bit LoRA fit in 8GB?

### Takeaway
Unsloth's official table (the only primary-source figures found) puts a **3B model at 3.5 GB minimum for QLoRA and 8 GB for 16-bit LoRA**. So 16-bit LoRA on Phi-3 Mini (3.8B) does **not** fit realistically on an 8GB RTX 3070 Ti. 3.8B is only workable as QLoRA. 0.5B–1.5B fit comfortably in 16-bit LoRA. No primary measured figures were found for 0.5B/1.5B at 1–2k tokens specifically.

### Cited Findings
- Unsloth official minimum VRAM table: 3B gives QLoRA (4-bit) 3.5 GB and LoRA (16-bit) 8 GB; 7B gives 5 GB / 19 GB; 8B gives 6 GB / 22 GB. Unsloth says "these numbers are the absolute minimum" and "sometimes more VRAM is required depending on the model". — [Unsloth Requirements](https://www.unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
- Unsloth's guidance on OOM is to set batch size to 1, 2 or 3. — [Unsloth Requirements](https://www.unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
- Unsloth requires NVIDIA CUDA capability ≥ 7.0 (V100, T4, RTX 20/30/40/50, A100…). — [Unsloth Requirements](https://www.unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
- Spheron's GPU-recommender tool estimates the following for Phi-3-mini: LoRA FP16 needs 12 GB, LoRA on an INT8 base 6.2 GB, LoRA on an INT4 base 3.1 GB. These are **calculator estimates, not measurements**. — [Spheron Phi-3-mini GPU guide](https://www.spheron.network/tools/gpu-recommender/microsoft/Phi-3-mini-4k-instruct/)
- The same calculator estimates about 5.0 GB peak for Qwen2.5-1.5B FP16 LoRA at batch 1 and 4,096 context. This is also an estimate, not a measurement. — [Spheron Qwen2.5-1.5B guide](https://www.spheron.network/tools/gpu-recommender/Qwen/Qwen2.5-1.5B-Instruct/)
- A Sept-2025 profiling study measured LoRA on Qwen2.5-1.5B-Instruct on a single RTX 4060 (8GB-class), reporting VRAM and throughput. The exact numbers were not visible in what was accessible. — [chatpaper summary](https://chatpaper.com/chatpaper/paper/188927)
- Kaitchup has a Phi-3 fine-tuning and quantization notebook on an "affordable GPU". The measured numbers are behind a paywall. — [Kaitchup](https://kaitchup.substack.com/p/phi-3-fine-tuning-and-quantization)

### Inferences
- Phi-3 Mini's bf16 weights alone are about 3.8B × 2 bytes ≈ 7.6 GB, before activations, LoRA optimizer states or CUDA context. A 16-bit LoRA cannot fit in 8 GB, which matches Unsloth's 3B → 8 GB minimum. **On the local GPU, 3.8B means QLoRA only.** That makes Agent 3's LoRA-vs-HydraLoRA comparison a QLoRA comparison, and it mixes up Agent 4's QAT-vs-PTQ story, because the base would already be 4-bit NF4 during training.
- 0.5B (≈1 GB bf16) and 1.5B (≈3 GB bf16) leave several GB for activations at 1–2k tokens with gradient checkpointing and batch 1–4. Plain 16-bit LoRA is feasible locally. This is extrapolated from the Unsloth table, not measured.
- The 8 GB budget is a *deployment* constraint. Training on Kaggle/Colab T4 (16 GB) would allow 16-bit LoRA on 3.8B. The proposal should therefore separate the "train on ≤16 GB cloud" budget from the "serve on 8 GB" budget.

### Gaps
- No primary-source **measured** peak VRAM for 0.5B/1.5B/3.8B at 1k and 2k tokens with gradient checkpointing. Recommend the team measures it themselves with `torch.cuda.max_memory_allocated()` (a one-hour experiment that also produces reportable evidence).
- The Unsloth Phi-3 blog (unsloth.ai/blog/phi3) returned HTTP 403, so its numbers were not checked.

## 2. Free and cheap GPU limits (Kaggle, Colab, rentals) in 2026

### Takeaway
Kaggle gives about 30 GPU-hours/week (T4×2 or P100 16 GB) with 12 h sessions. Colab free gives an unguaranteed T4 for at most 12 h. Colab paid tiers use compute units (T4 ≈ 1.76 CU/h, A100 ≈ 15 CU/h; $9.99 per 100 CU). Avoid Kaggle's P100: it is below Unsloth's and AWQ's minimum compute capability.

### Cited Findings
- Kaggle: one P100 (16 GB) or two T4s (2×16 GB). Roughly 30 GPU-h/week, which floats and is shown in account settings. GPU session cap 12 h, TPU 9 h. TPU v5e-8 replaced v3-8 in 2025. — [gpuperhour (2026)](https://gpuperhour.com/blog/free-cloud-gpus-and-credits) (secondary)
- Kaggle's quota resets Saturday midnight UTC. Commit ("Save Version") mode runs notebooks in the background, and you can edit without an accelerator to save quota. — [NVIDIA blog on Kaggle GPUs](https://developer.nvidia.com/blog/how-kaggle-makes-gpus-accessible-to-5-million-data-scientists/) (older but consistent)
- Colab official FAQ: free notebooks "can run for at most 12 hours, depending on availability and your usage patterns". Usage limits are "dynamic", with no guaranteed resources. Idle runtimes time out. GPU types "vary over time". — [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Colab free tier forbids SSH/remote desktop, "bypassing the notebook UI to interact primarily via a web UI", and distributed computing workers. Paid plans with a positive CU balance lift these restrictions. — [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Colab compute units: T4 ≈ 1.76 CU/h, A100 ≈ 15 CU/h. Pay-as-you-go is $9.99 per 100 CU (≈57 T4-h or ≈7 A100-h). Pro is $9.99/mo and Pro+ $49.99/mo. Paid tiers give access to L4 and occasionally A100. Running out of CU drops you back to free-tier limits. — [gpuperhour Colab alternatives](https://gpuperhour.com/blog/google-colab-alternatives); [Hivenet guide](https://www.hivenet.com/post/google-colaboratory-gpu-complete-guide-to-free-cloud-gpu-access-and-limitations) (secondary)
- AWQ kernels need NVIDIA compute capability ≥ 7.5 (Turing+). The faster Marlin kernel needs ≥ 8.0. — [AutoAWQ README](https://github.com/casper-hansen/AutoAWQ); [AutoAWQ PyPI](https://pypi.org/project/autoawq)

### Inferences
- A P100 is compute capability 6.0 (Pascal), which is below Unsloth's 7.0 minimum and AWQ's 7.5. It also lacks bf16. **Choose "GPU T4 x2" on Kaggle, not P100.** The T4 (7.5) also has no bf16, so you need fp16 training, and it cannot use Marlin AWQ kernels.
- The RTX 3070 Ti is Ampere (compute 8.6), so it supports bf16, Unsloth, AWQ and Marlin. The local GPU is actually the *best* inference target the team has.
- For reproducibility, pin one platform for all reported training runs. Colab GPU types vary over time, which hurts run-to-run comparability.

### Gaps
- No official Kaggle documentation page was fetched. The 30 h/12 h figures come from secondary 2026 sources and Kaggle's long-standing policy. Verify in the Kaggle account settings.
- Current cheap rental prices (RunPod, Vast.ai, Lambda) were not collected. No student-specific restrictions were found beyond the Colab FAQ items above.

## 3. HydraLoRA implementation; PEFT support for multi-B-head / mixture-of-LoRA; easiest hard-routed approach

### Takeaway
An official HydraLoRA repository exists (Clin0212/HydraLoRA). It is a **modified PEFT fork** with a *learned MoE router* and K-means-chosen head count, last updated Dec 2024. PEFT itself has **no shared-A / multi-B LoRA variant**. PEFT's X-LoRA and Arrow are learned or gradient-free routers over *separate full LoRA adapters*. The simplest defensible build is a small custom `nn.Module` wrapping the target Linear layers (one shared A, k B heads, head index set from the complexity label). That is about 50 lines, which is less work and less version-locking than adopting the 2024 fork.

### Cited Findings
- HydraLoRA uses an asymmetric structure: a shared A matrix and multiple B matrices. A trainable MoE router assigns samples to B experts, and the B matrices are merged dynamically at inference by the router. NeurIPS 2024 oral. — [arXiv 2404.19245](https://arxiv.org/html/2404.19245v2); [NeurIPS 2024](https://neurips.cc/virtual/2024/oral/97953)
- Official code: github.com/Clin0212/HydraLoRA. It is a fork of PEFT with `HydraLoRA/fine-tuning.py` and a modified peft, uses K-means to pick the number of B heads ("N can be manually specified"), and offers single-GPU and DeepSpeed scripts. Evaluation is via OpenCompass. About 242 stars, last update 1 Dec 2024, license not clearly stated. — [GitHub Clin0212/HydraLoRA](https://github.com/Clin0212/HydraLoRA)
- PEFT X-LoRA (`XLoraConfig`, docs at v0.21.0) is a mixture of *pre-trained, frozen* LoRA adapters with a **learned classifier** producing token/layer scalings. It is dense by default, with `top_k_lora` for sparse. It needs **two forward passes per step**. — [PEFT X-LoRA docs](https://huggingface.co/docs/peft/package_reference/xlora)
- PEFT Arrow (`ArrowConfig`, `create_arrow_model`) is a "gradient-free, token-wise mixture-of-experts routing mechanism" over multiple task-specific LoRA adapters. — [PEFT LoRA developer guide](https://huggingface.co/docs/peft/developer_guides/lora)
- PEFT supports **mixed-adapter batches**: `model.generate(..., adapter_names=[...])` applies a different named LoRA adapter per sample in one batch. That is hard routing, but each adapter has its own A and B. — [PEFT LoRA developer guide](https://huggingface.co/docs/peft/developer_guides/lora)
- No PEFT LoRA variant that shares the A matrix across adapters is documented. — [PEFT LoRA developer guide](https://huggingface.co/docs/peft/developer_guides/lora)
- A 2026 paper on hard-routed mixtures of LoRAs found that hard routing (exactly one expert, unit scaling) matches the original LoRA formulation and performs comparably to or better than soft routing. This is useful related work for defending hard-coded routing. — [arXiv 2606.31413](https://arxiv.org/pdf/2606.31413)

### Inferences
- The project's design (hard-coded routing from Agent 1's complexity label, fixed k=4 heads) **diverges from the HydraLoRA paper**, which uses a learned router and K-means k. Call it "HydraLoRA-style asymmetric LoRA with oracle/rule routing" and cite HydraLoRA for the architecture only. This is honest, and it is the novelty angle in CLAUDE.md.
- Easiest implementation: use PEFT LoRA as the standard-LoRA baseline. For Hydra, write a custom module over each targeted `nn.Linear`: `y = W x + (alpha/r) * B[h](A(x))`, where `h` is a per-batch attribute set before forward. Train with batches grouped by complexity bucket, so one `h` per batch, no per-sample gather and no Trainer changes beyond a custom collator. Save `A` and `B_0..B_3` with safetensors. The trainable parameter count is r·(d_in + 4·d_out) per layer, and that should be reported against LoRA rank-matched baselines.
- Approximation that needs no custom code: train 4 PEFT adapters and use `adapter_names` at inference. But that is *not* HydraLoRA (A is not shared), so use it only as an extra ablation ("separate LoRAs per bucket").
- Deployment caveat: llama.cpp LoRA-GGUF and vLLM multi-LoRA assume standard A·B adapters. Serving Hydra means either (a) merging A·B_h into 4 separate full-weight variants (4× disk) or (b) exporting each head as a standard LoRA (A, B_h) and hot-swapping. Option (b) is compatible with `convert_lora_to_gguf.py` and per-request adapter selection.

### Gaps
- The HydraLoRA repository's license could not be confirmed. Check before copying code; writing an own module avoids the issue.
- No benchmark found for HydraLoRA on Text-to-SQL or on models ≤4B.

## 4. QAT tooling in 2026 and whether "QAT in GGUF and AWQ at the same bit-rates" is feasible

### Takeaway
Practical LLM QAT in 2026 means **PyTorch torchao QAT**, either directly, via torchtune, or via **Unsloth's `qat_scheme`**, which is built on torchao and works with LoRA. These export **torchao / compressed formats for vLLM/ExecuTorch, not GGUF or AWQ**. True "QAT-native GGUF/AWQ" does not exist off the shelf. The defensible approximation: run QAT with a fake-quantizer configured to *match the target format's grid* (int4 symmetric/asymmetric, matching group size), then export the QAT-trained bf16 weights through the *normal* GGUF / AWQ converters. Compare against PTQ of the non-QAT model through the same converters.

### Cited Findings
- torchao provides an end-to-end LLM QAT flow (`Int8DynActInt4WeightQATQuantizer`: int8 dynamic per-token activations + int4 per-group weights). On Llama3-8B it recovered up to **96% of the hellaswag degradation and 68% of the wikitext perplexity degradation** versus PTQ. Wikitext PPL was 11.878 for PTQ and 9.859 for QAT, and hellaswag acc_norm 76.51% (−0.21%). — [PyTorch blog: QAT](https://pytorch.org/blog/quantization-aware-training/)
- torchtune has a QAT fine-tuning tutorial. — [torchtune QAT tutorial](https://docs.pytorch.org/torchtune/0.6/tutorials/qat_finetune.html)
- Unsloth QAT (with PyTorch) offers `qat_scheme` options `int4`, `fp8-int4`, `fp8-fp8`, `int8-int4`, and **can be combined with LoRA**. Export is via `model.save_pretrained_torchao` for vLLM / ExecuTorch / HF Hub. Reported gains: "recovers as much as 70% of the lost accuracy", 1–3% benchmark improvement. Gemma3-4B GPQA recovered 66.9% (+1.0% raw) and Gemma3-12B BBH 45.5% (+2.1%). The example notebook uses Qwen3-4B. — [Unsloth QAT docs](https://unsloth.ai/docs/blog/quantization-aware-training-qat)
- Unsloth also states that QAT adds "no extra overhead during inference" and uses the same disk and memory as naive quantization. — [Unsloth QAT docs](https://unsloth.ai/docs/blog/quantization-aware-training-qat)
- Precedent for QAT then GGUF: Google's Gemma 3 QAT checkpoints are distributed as GGUF Q4_0 (e.g. `gemma-3-4B-it-qat-GGUF`), and Unsloth ships Gemma-4 QAT GGUFs. — [lmstudio-community gemma-3-4B-it-qat-GGUF](https://huggingface.co/lmstudio-community/gemma-3-4B-it-qat-GGUF); [unsloth gemma-4 QAT GGUF discussion](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-qat-GGUF/discussions/1)
- GGUF quantization can be done with no calibration, with AWQ scales applied first, or with an importance matrix (imatrix) from calibration data. Qwen's docs recommend imatrix for Q4 and below. — [Qwen docs: GGUF](https://qwen.readthedocs.io/en/latest/quantization/gguf.html)

### Inferences
- **Feasible design for Agent 4:**
  1. PTQ arm: the fine-tuned bf16 model goes to (a) llama.cpp Q8_0 and Q4_0/Q4_K_M, and to (b) llm-compressor AWQ W4A16 g128. W8A16 AWQ is unusual: AWQ is essentially a 4-bit-weight method, so "8-bit AWQ" is weakly supported. Use INT8 W8A8/W8A16 via llm-compressor as the 8-bit HF-side counterpart, and say so.
  2. QAT arm: fine-tune with torchao/Unsloth fake-quant int4 weight-only, group size matched to the target (32 for GGUF Q4_0 blocks, 128 for AWQ). Then the *same* converters produce the deployed files.
  - This is the Gemma-QAT recipe in miniature, and it is honest to call it "format-targeted QAT + standard export".
- **Not defensible:** claiming QAT natively in "AWQ format". AWQ is itself a PTQ algorithm (activation-aware scaling from calibration data). The comparison should be framed as **QAT-then-quantize vs PTQ (RTN / AWQ / imatrix)** at matched bit-width.
- `int8-int4` (int8 activations) does not map onto llama.cpp or AWQ weight-only kernels. Use the weight-only `int4` scheme for the GGUF/AWQ comparison.
- 8-bit: PTQ at Q8_0 is usually near-lossless, so QAT at 8-bit may show no difference. That is a legitimate result, but plan for it.

### Gaps
- No primary source found for LLM-QAT, EfficientQAT or BitDistiller support status in 2026 (maintenance, small-model support, export paths). They are research repos; assume no GGUF/AWQ export unless verified.
- No published QAT result on ≤4B models for Text-to-SQL was found.
- Not verified whether Unsloth's QAT can save straight to GGUF in one step. Its docs mention the torchao export only.

## 5. llama.cpp GGUF and AutoAWQ / llm-compressor support for Qwen2.5/Qwen3, Llama-3.2, Phi-3, SmolLM2, Gemma; AWQ GPU needs on 8GB

### Takeaway
llama.cpp supports all five families and converts LoRA adapters to GGUF. **AutoAWQ is deprecated and archived (May 2025)**. Its last tested stack is Torch 2.6 / Transformers 4.51.3. AWQ now lives in **vLLM's llm-compressor**, which outputs *compressed-tensors* for vLLM. AWQ inference is GPU-oriented (CUDA ≥ 7.5). CPU paths existed via Intel IPEX in AutoAWQ only. On Windows, vLLM needs WSL2/Docker or community builds.

### Cited Findings
- The llama.cpp README lists Qwen (Qwen2/2.5/3), Llama 3.x, Phi-3, SmolLM and Gemma among supported models. It supports 1.5- to 8-bit integer quantization and includes `convert_lora_to_gguf.py`. CUDA, Vulkan, Metal and CPU backends. — [llama.cpp GitHub](https://github.com/ggml-org/llama.cpp)
- AutoAWQ: "officially deprecated and will no longer be maintained. The last tested configuration used Torch 2.6.0 and Transformers 4.51.3." Archived 11 May 2025. Functionality was adopted by vLLM llm-compressor (and MLX-LM for Mac). Requires NVIDIA compute capability ≥ 7.5, CUDA ≥ 11.8, and Intel CPU/XPU via IPEX ≥ 2.4. — [AutoAWQ GitHub](https://github.com/casper-hansen/AutoAWQ)
- vLLM docs (latest) mark AutoAWQ as deprecated and point to llm-compressor's AWQ examples. — [vLLM docs: AutoAWQ](https://docs.vllm.ai/en/latest/features/quantization/auto_awq/)
- llm-compressor supports GPTQ, AWQ, SmoothQuant and AutoRound. Output is compressed-tensors, natively loadable by vLLM. Supports disk offloading for large models under limited VRAM. — [llm-compressor GitHub](https://github.com/vllm-project/llm-compressor)
- AWQ CPU support (x86) was added to AutoAWQ in June 2024. Marlin kernel needs compute capability ≥ 8.0. — [AutoAWQ PyPI](https://pypi.org/project/autoawq)
- vLLM on Windows: Docker Model Runner supports vLLM on Docker Desktop for Windows (WSL2 + NVIDIA). Community native-Windows builds exist. — [Docker blog](https://www.docker.com/blog/docker-model-runner-vllm-windows); [vllm-windows (community)](https://github.com/davidnet/vllm-windows)

### Inferences
- **Standardise on GGUF + llama.cpp (or Ollama, which uses llama.cpp) for the deployed appliance.** It runs on CPU or GPU, on Windows natively, and is the format the harness already uses (Ollama phi3).
- Keep AWQ as the *comparison* format: use llm-compressor to produce W4A16, and serve with vLLM (Linux/WSL2) or Transformers. On 8 GB, a ≤4B AWQ model fits easily: about 2 GB of weights for 3.8B at 4-bit, which is arithmetic, not measured. **Do not build on AutoAWQ** because of version lock with the 2026 Transformers stack.
- Check that the chosen base model's architecture is in llm-compressor's tested list. Gemma and Phi-3 occasionally need model-specific AWQ mappings (unverified).

### Gaps
- No explicit per-architecture llm-compressor AWQ support matrix was retrieved for Phi-3, SmolLM2 or Gemma. Test a smoke quantization early.
- Whether current Transformers can still *load* AWQ checkpoints on CPU without AutoAWQ was not verified.

## 6. Checkpoint hand-off format, versioning and licensing for re-upload

### Takeaway
Hand off **HF-format folders** (`config.json`, `generation_config.json`, `*.safetensors`, tokenizer files) for full models (Agent 2 → 3). Hand off **PEFT adapter folders** (`adapter_config.json` + `adapter_model.safetensors`) for LoRA. Hydra heads need a custom safetensors plus a small JSON config. Version them on **private HF Hub repos** with tags/revisions. Licenses differ: Qwen2.5 (most sizes) and Phi-3 are permissive. Llama 3.2 adds attribution and naming rules for any distributed derivative.

### Cited Findings
- PEFT LoRA adapters are named, loadable artefacts (`load_adapter`, `adapter_names`), and X-LoRA consumes adapters "as per PeftModel.load_adapter", which shows that the adapter folder is PEFT's standard unit of exchange. — [PEFT X-LoRA docs](https://huggingface.co/docs/peft/package_reference/xlora); [PEFT LoRA guide](https://huggingface.co/docs/peft/developer_guides/lora)
- Llama 3.2 Community License: distributing derivatives requires displaying "Built with Llama", **prefixing the model name with "Llama"**, keeping a NOTICE file ("Llama 3.2 is licensed under the Llama 3.2 Community License, Copyright © Meta Platforms, Inc."), and shipping a copy of the agreement. — [Llama 3.2 LICENSE](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct/blob/main/LICENSE.txt); [Meta license page](https://developer.meta.com/ai/llama3_2/license/)
- llama.cpp can convert LoRA adapters to GGUF (`convert_lora_to_gguf.py`), so a PEFT adapter folder is also the input for GGUF adapter deployment. — [llama.cpp GitHub](https://github.com/ggml-org/llama.cpp)

### Inferences
- Freeze a hand-off contract in the Execution Plan:
  - (a) Base checkpoints from Agent 2 go in a private HF repo, one branch/tag per checkpoint (`distilled-v1`, `native-v1`). They should be bf16 safetensors with the tokenizer and chat template included.
  - (b) Agent 3 produces a PEFT adapter for LoRA, and for Hydra a `hydra_config.json` (rank, alpha, target_modules, head→bucket map) plus `hydra_adapter.safetensors`. Also provide a merged-per-head HF folder so Agent 4 can quantize with standard tools.
  - (c) Agent 4 produces GGUF files and an AWQ compressed-tensors folder, with the quantization recipe saved alongside.
  - Record the base model commit hash in every artefact.
- Prefer a permissively licensed base (Qwen2.5 0.5B/1.5B are Apache-2.0 per their model cards; Phi-3 is MIT). This avoids the Llama naming rule on the uploaded derivatives. The licenses themselves were not fetched in this session, so verify on the model cards before citing.
- Private Hub repos avoid "distribution" questions during development. Licensing matters if the models are made public at submission.

### Gaps
- Qwen2.5 (note: the 3B and 72B sizes reportedly use a different Qwen license), Phi-3, SmolLM2 and Gemma license terms were not fetched in this session. Verify on each model card.
- HF Hub free-tier private storage limits for 2026 were not checked.
