"""SQL generators the harness can use for the generation stage (Agent 3's slot), chosen by env J26_GENERATOR:

  ollama:<model>   any Ollama model (default ollama:phi3), e.g. ollama:qwen2.5-coder:1.5b-instruct
  adaptive_qwen    Agent 4's adaptive mixed-precision Qwen2.5-1.5B-Instruct (Karunanayake: sensitive layers INT8,
                   the rest INT4, built by scripts/qwen_build_adaptive.py from results/qwen/). Needs an NVIDIA GPU and
                   torch + transformers + accelerate + bitsandbytes. If they are missing, the app falls back to phi3.
  qwen_fp16        the team base model Qwen2.5-1.5B-Instruct, loaded with transformers from the Hugging Face cache
  qwen_int8        (no Ollama), at full precision or with uniform bitsandbytes INT8 / INT4. Same loader, prompt and
  qwen_int4        generation code as Agent 4's experiments (src/). Needs an NVIDIA GPU + requirements-gpu.txt.
  agent3           Agent 3's fine-tuned model (Thathsarani): Qwen2.5-1.5B-Instruct + her LoRA or HydraLoRA adapter.
                   J26_AGENT3_ADAPTER = the folder with adapters.pt and adapter_meta.json (made by agent3_finetune.train
                   or package_artifacts). J26_AGENT3_BASE = another base model (optional). Needs torch + transformers;
                   a GPU is recommended (the CPU works but is slow). If it cannot load, the app falls back to phi3.

Every generator has the harness signature generate(question, ddl, hint=None, dialect=...) -> SQL, plus two attributes:
`label` (shown on the chat page) and `stand_in` (True until it is Agent 3's fine-tuned model). A generator with
`wants_complexity = True` also gets complexity=<Agent 1's label> (HydraLoRA uses it to select the head)."""
import json
import os
import re
import threading
from functools import partial
from pathlib import Path

from agent1_retrieval.execution import ollama_generate


def ollama(model="phi3"):
    gen = partial(ollama_generate, model=model, cache=False)  # live calls never touch the evaluation cache
    gen.label, gen.stand_in = f"{model} via Ollama", True
    return gen


_lock = threading.Lock()  # one model on one GPU: load once, generate one question at a time
_model = None


def _load():
    global _model
    with _lock:
        if _model is None:
            from scripts.qwen_build_adaptive import load_adaptive_model
            model, tokenizer, _ = load_adaptive_model()
            _model = (model, tokenizer)
    return _model


def adaptive_qwen():
    """Agent 4's model, called with her own prompt and generation code so the app behaves like her experiments."""
    import torch  # fail here (ImportError) rather than on the first question
    if not torch.cuda.is_available():
        raise RuntimeError("no CUDA GPU")
    from src.prompt_builder import build_prompt
    from src.qwen_generate import generate_sql
    from src.sql_util import clean_sql

    def generate(question, ddl, hint=None, dialect="SQLite"):
        model, tokenizer = _load()
        ask = question + (f"\nUse {dialect} SQL." if dialect != "SQLite" else "") + (f"\n{hint}" if hint else "")
        with _lock:
            sql = clean_sql(generate_sql(model, tokenizer, build_prompt(ddl, ask)))
        return re.split(r";\s*", sql, maxsplit=1)[0]  # first statement only: the executor refuses more than one

    generate.label = "Agent 4 adaptive INT4/INT8 Qwen2.5-1.5B (not fine-tuned for SQL)"
    generate.stand_in = True
    threading.Thread(target=_load, daemon=True).start()  # warm up in the background: loading takes a while
    return generate


def qwen_local(precision="fp16"):
    """The plain base model without Ollama: src.qwen_model_loader.load_qwen(precision), called like adaptive_qwen.
    Not fine-tuned for SQL, so it stays a stand-in. Her generate_sql stops at 100 new tokens (long SQL is cut)."""
    import torch  # fail here (ImportError) rather than on the first question
    if not torch.cuda.is_available():
        raise RuntimeError("no CUDA GPU")
    from src.prompt_builder import build_prompt
    from src.qwen_generate import generate_sql
    from src.qwen_model_loader import MODEL_NAME, load_qwen
    from src.sql_util import clean_sql
    state = {}

    def load():
        with _lock:
            if not state:
                state["model"], state["tok"] = load_qwen(precision)
        return state

    def generate(question, ddl, hint=None, dialect="SQLite"):
        s = load()
        ask = question + (f"\nUse {dialect} SQL." if dialect != "SQLite" else "") + (f"\n{hint}" if hint else "")
        with _lock:
            sql = clean_sql(generate_sql(s["model"], s["tok"], build_prompt(ddl, ask)))
        return re.split(r";\s*", sql, maxsplit=1)[0]

    generate.label = f"{MODEL_NAME.split('/')[-1]} {precision.upper()} via transformers (not fine-tuned for SQL)"
    generate.stand_in = True
    generate.load = load
    return generate

AGENT3_BASE = "Qwen/Qwen2.5-1.5B-Instruct"
# Copy of agent3_finetune.train_lora.PROMPT (that module needs peft at import time). A test keeps the two equal.
AGENT3_PROMPT = "### Schema:\n{ddl}\n\n### Question:\n{question}\n\n### SQL:\n"


def _load_hf(base, device):
    """The base model and tokenizer from Hugging Face (first use downloads about 3 GB)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(base)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    dtype = torch.float16 if device == "cuda" else torch.float32
    return AutoModelForCausalLM.from_pretrained(base, torch_dtype=dtype).to(device), tok


def agent3(adapter, base=None, load_base=_load_hf, max_new_tokens=200, max_prompt_tokens=3000):
    """Agent 3's model, called with her training prompt and her greedy decoding (agent3_finetune.evaluate), so the
    app behaves like her experiments. One adapter (LoRA) ignores the complexity label; HydraLoRA uses it to select
    the head, with her fallback head for an unknown label. load_base is injectable for tests."""
    import torch  # fail here (ImportError) rather than on the first question
    from agent3_finetune import hydra
    from agent3_finetune.evaluate import clean_sql

    adapter = Path(adapter)
    if not (adapter / "adapters.pt").exists() or not (adapter / "adapter_meta.json").exists():
        raise RuntimeError(f"no adapters.pt + adapter_meta.json in '{adapter}' (set J26_AGENT3_ADAPTER)")
    meta = json.loads((adapter / "adapter_meta.json").read_text(encoding="utf-8"))
    base = base or meta.get("model") or meta.get("base_model") or AGENT3_BASE
    device = "cuda" if torch.cuda.is_available() else "cpu"
    n_heads = meta["n_heads"]
    state = {}

    def load():
        with _lock:
            if not state:
                model, tok = load_base(base, device)
                router = hydra.Router()
                hydra.add_adapters(model, router, meta["rank"], meta["alpha"], n_heads, 0.0, tuple(meta["targets"]))
                hydra.load_adapters(model, adapter)
                model.eval()
                state.update(model=model, tok=tok, router=router)
        return state

    def generate(question, ddl, hint=None, dialect="SQLite", complexity=None):
        s = load()
        ask = question + (f"\nUse {dialect} SQL." if dialect != "SQLite" else "") + (f"\n{hint}" if hint else "")
        enc = s["tok"](AGENT3_PROMPT.format(ddl=ddl, question=ask), return_tensors="pt", add_special_tokens=False).to(device)
        if enc["input_ids"].shape[1] > max_prompt_tokens:
            raise ValueError(f"schema too long for the model ({enc['input_ids'].shape[1]} tokens)")
        with _lock, torch.no_grad():
            if n_heads > 1:
                s["router"].set(torch.tensor([hydra.head_index(complexity)], device=device))
            out = s["model"].generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                      pad_token_id=s["tok"].pad_token_id)
        return clean_sql(s["tok"].decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True))

    kind = "LoRA" if n_heads == 1 else f"HydraLoRA ({n_heads} heads)"
    generate.label = f"Agent 3 {kind} on {base.split('/')[-1]}" + ("" if device == "cuda" else " (CPU: slow)")
    generate.stand_in = False
    generate.wants_complexity = True
    generate.load = load
    return generate


def from_env():
    """The generator named by J26_GENERATOR; phi3 via Ollama if unset, or if the named one can't run here."""
    name = os.environ.get("J26_GENERATOR", "ollama:phi3")
    if name.startswith("ollama:"):
        return ollama(name.split(":", 1)[1])
    if name == "adaptive_qwen":
        try:
            return adaptive_qwen()
        except (ImportError, RuntimeError) as e:
            print(f"J26_GENERATOR=adaptive_qwen unavailable ({e}); using phi3 via Ollama")
            gen = ollama("phi3")
            gen.label = f"phi3 via Ollama (adaptive_qwen unavailable: {e})"
            return gen
    if name in ("qwen_fp16", "qwen_int8", "qwen_int4"):
        try:
            gen = qwen_local(name.split("_")[1])
            threading.Thread(target=gen.load, daemon=True).start()  # warm up in the background
            return gen
        except (ImportError, RuntimeError) as e:
            print(f"J26_GENERATOR={name} unavailable ({e}); using phi3 via Ollama")
            gen = ollama("phi3")
            gen.label = f"phi3 via Ollama ({name} unavailable: {e})"
            return gen
    if name == "agent3":
        try:
            gen = agent3(os.environ.get("J26_AGENT3_ADAPTER", "agent3_finetune/artifacts/lora_r16_seed42"),
                         os.environ.get("J26_AGENT3_BASE"))
            threading.Thread(target=gen.load, daemon=True).start()  # warm up in the background
            return gen
        except (ImportError, RuntimeError) as e:
            print(f"J26_GENERATOR=agent3 unavailable ({e}); using phi3 via Ollama")
            gen = ollama("phi3")
            gen.label = f"phi3 via Ollama (agent3 unavailable: {e})"
            return gen
    raise ValueError(f"unknown J26_GENERATOR '{name}' (use ollama:<model>, qwen_fp16, qwen_int8, qwen_int4, adaptive_qwen or agent3)")
