"""Demo (Agent 3): one base model that can answer as BASE, LoRA or HydraLoRA.

Memory plan (one model in GPU memory, about 3.9 GB on the T4):
  * the base model is loaded once and wrapped with the 4-head hydra layers (hydra.add_adapters)
  * the three "modes" are just three small weight sets kept on the CPU and copied in when needed:
      hydra : the real 4-head adapter (adapters.pt of the HydraLoRA run)
      lora  : the real 1-head LoRA adapter, its single B copied into all 4 head slots, so every head is
              identical and the maths equals the 1-head LoRA that was trained (same A, same B, same scale)
      base  : the hydra weights with every B set to zero, so the adapter adds exactly 0 and the output
              equals the plain base model
This relies on LoRA and HydraLoRA having the same rank, alpha and target layers (checked at start-up).

Heavy libraries are imported inside __init__, so this file can be imported without torch.
UNTESTED on a GPU until you run check_engine.py on Colab.
"""
import json
import time
from pathlib import Path

MODES = ("base", "lora", "hydra")
MAX_PROMPT_TOKENS = 2048  # same limit as evaluate.py: longer prompts are refused politely, not run


def prompt_template():
    """The exact training prompt (agent3_finetune/train_lora.py: PROMPT); documented format as a fallback."""
    try:
        from agent3_finetune.train_lora import PROMPT
        return PROMPT
    except Exception:
        return "### Schema:\n{ddl}\n\n### Question:\n{question}\n\n### SQL:\n"


class Engine:
    def __init__(self, lora_dir, hydra_dir, model_name=None, max_new_tokens=None, vram_cap_gb=8.0):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from agent3_finetune import hydra

        self.torch, self.hydra = torch, hydra
        lora_dir, hydra_dir = Path(lora_dir), Path(hydra_dir)
        lm = json.loads((lora_dir / "adapter_meta.json").read_text(encoding="utf-8"))
        hm = json.loads((hydra_dir / "adapter_meta.json").read_text(encoding="utf-8"))
        for key in ("rank", "alpha", "targets"):
            if lm[key] != hm[key]:
                raise RuntimeError(f"LoRA and HydraLoRA differ in '{key}' ({lm[key]} vs {hm[key]}): "
                                   "the single-model weight swap would be wrong")
        if lm["n_heads"] != 1 or hm["n_heads"] != len(hydra.HEADS):
            raise RuntimeError(f"expected 1 LoRA head and {len(hydra.HEADS)} Hydra heads, "
                               f"got {lm['n_heads']} and {hm['n_heads']}")
        self.n_heads = hm["n_heads"]

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32  # fp16 is slow/unsupported on CPU
        if self.device == "cuda":
            total = torch.cuda.get_device_properties(0).total_memory
            torch.cuda.set_per_process_memory_fraction(min(1.0, vram_cap_gb * 1024 ** 3 / total))
            self.gpu = torch.cuda.get_device_name(0)
        else:
            self.gpu = "cpu"
        self.max_new_tokens = max_new_tokens or (256 if self.device == "cuda" else 128)

        name = model_name or hm.get("base_model") or "Qwen/Qwen2.5-1.5B-Instruct"
        self.model_name = name
        self.tok = AutoTokenizer.from_pretrained(name)
        if self.tok.pad_token_id is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype).to(self.device)
        self.router = hydra.Router()
        hydra.add_adapters(self.model, self.router, hm["rank"], hm["alpha"], self.n_heads, 0.0, tuple(hm["targets"]))
        self.model.eval()

        hydra_state = torch.load(hydra_dir / "adapters.pt", map_location="cpu")
        lora_state = torch.load(lora_dir / "adapters.pt", map_location="cpu")
        if set(hydra_state) != set(lora_state):
            raise RuntimeError("LoRA and HydraLoRA adapter files have different layer names")
        self.states = {
            "hydra": hydra_state,
            "lora": {k: (v.expand(self.n_heads, -1, -1).contiguous() if v.dim() == 3 and v.shape[0] == 1 else v)
                     for k, v in lora_state.items()},
            "base": {k: (torch.zeros_like(v) if k.endswith("lora_B") else v) for k, v in hydra_state.items()},
        }
        self.current = None
        self.template = prompt_template()
        self._ddl_cache = {}

    # ------------------------------------------------------------------ helpers
    def _use(self, mode):
        if self.current == mode:
            return
        res = self.model.load_state_dict(self.states[mode], strict=False)
        if res.unexpected_keys:
            raise RuntimeError(f"unexpected adapter keys: {res.unexpected_keys[:3]}")
        self.current = mode

    def head_for(self, label):
        """Name of the HydraLoRA head that a label is routed to (unknown or missing labels use the fallback head)."""
        return self.hydra.HEADS[self.hydra.head_index(label)]

    def prompt(self, db_path, question):
        from agent3_finetune.evaluate import read_ddl
        return self.template.format(ddl=read_ddl(str(db_path), self._ddl_cache), question=question)

    def generate(self, mode, prompt, label=None):
        """Greedy generation (as in evaluate.py). Returns (raw_text, seconds)."""
        torch = self.torch
        enc = self.tok(prompt, return_tensors="pt", add_special_tokens=False)
        n = enc["input_ids"].shape[1]
        if n > MAX_PROMPT_TOKENS:
            raise ValueError(f"the database schema is too long for this demo ({n} tokens, limit {MAX_PROMPT_TOKENS})")
        enc = enc.to(self.device)
        self._use(mode)
        head = self.hydra.head_index(label) if mode == "hydra" else 0  # lora/base: all heads identical or zero
        self.router.set(torch.tensor([head], device=self.device))
        t0 = time.time()
        with torch.no_grad():
            # stop at the first ';': clean_sql cuts there anyway, so the SQL is unchanged but the chatty
            # base model no longer runs on to the token limit
            out = self.model.generate(**enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                                      pad_token_id=self.tok.pad_token_id,
                                      stop_strings=[";"], tokenizer=self.tok)
        text = self.tok.decode(out[0][n:], skip_special_tokens=True)
        return text, round(time.time() - t0, 2)

    def answer(self, question, db_path, label, modes=MODES):
        """SQL from each mode for one question. Never raises: a failing mode returns {'error': ...}."""
        from agent3_finetune.evaluate import clean_sql
        results = {}
        try:
            prompt = self.prompt(db_path, question)
        except Exception as e:
            return {m: {"error": f"Could not read the database schema: {e}"} for m in modes}
        for m in modes:
            try:
                raw, secs = self.generate(m, prompt, label)
                results[m] = {"sql": clean_sql(raw), "raw": raw, "seconds": secs,
                              "head": self.head_for(label) if m == "hydra" else None}
            except Exception as e:
                results[m] = {"error": f"{type(e).__name__}: {e}"}
        return results

    def peak_vram_gb(self):
        if self.device != "cuda":
            return None
        return round(self.torch.cuda.max_memory_allocated() / 1024 ** 3, 2)
