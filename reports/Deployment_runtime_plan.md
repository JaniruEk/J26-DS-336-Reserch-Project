# Deployment runtime plan: replacing Ollama

*Status: planned, not started. Decided 18 Oct 2026: keep Ollama until after PP1. Implement once Agent 3 and Agent 4 deliver real artefacts (target: before PP2).*

## Decision

| Phase | Runtime | Why |
|---|---|---|
| Development and PP1 | **Ollama** (stand-ins phi3 / Qwen2.5-Coder-1.5B; team base model is Qwen2.5-1.5B-Instruct, agreed 19 Oct 2026) | Tested end to end; no final model artefacts exist yet, so switching gains nothing |
| Research evaluation (Agents 2, 3, 4) | **Hugging Face transformers + PEFT** | Native adapter switching; what the training code already uses |
| Deployment | **llama.cpp inside the application** (`llama-cpp-python`) | One process, no separate model server; loads Agent 4's GGUF and Agent 3's adapters directly; fast on mid-range hardware |

Fallback if in-process loading proves awkward: llama.cpp's own `llama-server` (OpenAI-compatible HTTP, supports several LoRA adapters chosen per request). Not planned: vLLM (built for many concurrent users, Linux only, heavier than one organisation needs).

## Why this is a small change

The harness takes the generator as a function: `create_app(generate=...)` with the signature `generate(question, ddl, hint=None, **kw) -> sql`. Swapping Ollama for llama.cpp means writing a new `generate`. Agent 1, execution, retry, logging, the chatbot and the BI endpoints do not change.

## Prerequisites (team decisions, settle before implementing)

1. **How HydraLoRA heads are served.** HydraLoRA picks a head per question (simple / single-join / multi-join / aggregation), so the runtime must switch per request.
   - **A (preferred): quantize the base only, keep each head as a separate LoRA adapter (GGUF).** One base in memory, adapters switched per question. Less memory, one quantized model to evaluate.
   - **B: merge each head into the base and quantize each merged model.** Four full models, so 4x disk, and switching means loading another model.
   - Owners: Thathsarani (export format) and Karunanayake (what gets quantized).
2. **Agent 4's mixed-precision study must quantize the configuration that will be deployed** (under A: the base, with layer sensitivity measured and evaluated with adapters attached). Otherwise the chosen INT4/INT8 allocation is not what ships.
3. **Artefacts available:** Agent 4's final mixed-precision base (one GGUF with per-layer INT8/INT4 types) and Agent 3's winner adapters (GGUF LoRA, via llama.cpp's `convert_lora_to_gguf.py`).
4. **Agent 3's live head routing** uses the complexity label from Agent 1's handoff (`complexity`), so the generator receives it per request.

## Implementation steps

1. Install `llama-cpp-python` with GPU support on the target machine. On Windows this may need the CUDA toolkit and a C++ build; allow a day, or use a prebuilt CUDA wheel if one matches.
2. Add `harness/runtime.py` with a `llama_cpp_generate` function: load the base once, load the adapters, pick the adapter from the complexity label, and use the same prompt as `ollama_generate` (so results stay comparable).
3. Select the runtime with an environment variable (e.g. `J26_RUNTIME=ollama|llama_cpp`, default `ollama`), so the switch is reversible and demos keep working.
4. Same-input check: run the Chinook + Spider evaluation through both runtimes on the same model. Execution accuracy should match within noise (greedy decoding on both).
5. Measure latency and memory per question (end to end, first query and warm), and record them in the NFR table.
6. Update the README run instructions and the PP1/PP2 docs.

## Done when

- The harness answers the demo questions through llama.cpp with Ollama stopped.
- Evaluation accuracy matches the Ollama run on the same model (no significant difference).
- Latency and memory are measured and recorded.
- The adapter chosen for each question is visible in the chatbot trace (Agent 3 section).
- Switching back to Ollama is one environment variable.

## Risks

| Risk | Mitigation |
|---|---|
| GPU build of `llama-cpp-python` fails on Windows | Use `llama-server` (prebuilt binaries) behind the same `generate` interface |
| Prompt formatting differs between runtimes (chat template) | Use the model's chat template explicitly in both; compare on the same-input check |
| Per-question adapter switching is slow | Measure; if slow, keep adapters loaded and set scales per request (`llama-server`), or fall back to option B |
| Quantized base + fp16 adapters behave differently from what Agent 4 evaluated | Prerequisite 2: evaluate exactly the deployed configuration |

## PP1 talking point

> "In development we serve the model through Ollama. In deployment it runs inside the application through llama.cpp, the engine Ollama itself is built on, loading Agent 4's quantized model and Agent 3's adapters directly. Our pipeline accepts any generator, so the swap doesn't change the other components. We switch once the final model artefacts exist."
