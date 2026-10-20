"""SQL generators the harness can use for the generation stage (Agent 3's slot), chosen by env J26_GENERATOR:

  ollama:<model>   any Ollama model (default ollama:phi3), e.g. ollama:qwen2.5-coder:1.5b-instruct
  adaptive_qwen    Agent 4's adaptive mixed-precision Qwen2.5-1.5B-Instruct (Karunanayake: sensitive layers INT8,
                   the rest INT4, built by scripts/qwen_build_adaptive.py from results/qwen/). Needs an NVIDIA GPU and
                   torch + transformers + accelerate + bitsandbytes. If they are missing, the app falls back to phi3.

Every generator has the harness signature generate(question, ddl, hint=None, dialect=...) -> SQL, plus two attributes:
`label` (shown on the chat page) and `stand_in` (True until it is Agent 3's fine-tuned model)."""
import os
import re
import threading
from functools import partial

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
    raise ValueError(f"unknown J26_GENERATOR '{name}' (use ollama:<model> or adaptive_qwen)")
