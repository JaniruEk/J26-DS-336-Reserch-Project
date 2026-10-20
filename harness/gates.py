"""Question gate (stage 1, Agent 2's slot), chosen by env J26_GATE:

  word_match     Agent 1's check alone: a content word of the question names a table or column (default)
  kd_multitask   Wathsala's distilled Qwen2.5-1.5B-Instruct student (MultiTask_Research/student_1_5b_kd_multitask/
                 final_adapter, Task 1: DATABASE vs GENERAL). Needs an NVIDIA GPU + torch, transformers, peft.
                 If they or her files are missing, the app falls back to word_match.

A gate is called as gate(question) -> {"database": bool, "p_database": float}. The harness lets a question through only
if the gate says "database" AND Agent 1's word check finds it in this database (both decline 0 of the 224 eval
questions; the word check also stops general trivia that her model calls DATABASE, e.g. "Who won the world cup?").

Scoring follows her significance test (student_1_5b_kd_candidate_predictions.csv): the probability of each label,
normalised over the two, so there is never an invalid answer. Her training prompt is not in the repository; the prompt
below is reconstructed and reproduces her Task 1 test accuracy (.997 vs her .994, same label on 1,195 of 1,200).
Task 2 (prompt-injection detection) is NOT used: with this prompt it scores .81 against her .948, so it waits for her
exact prompt (handoff/Request_Wathsala.md)."""
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "MultiTask_Research"
KD_ADAPTER = ROOT / "student_1_5b_kd_multitask" / "final_adapter"
BASE = "Qwen/Qwen2.5-1.5B-Instruct"
INSTRUCTION = "Classify the user query as DATABASE or GENERAL."  # reconstructed (see module docstring)
THRESHOLD = 0.5  # P(database) below this = general question, declined

_lock = threading.Lock()  # one model on one GPU: load once, score one question at a time
_model = None


def _load(adapter=KD_ADAPTER):
    global _model
    with _lock:
        if _model is None:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            tok = AutoTokenizer.from_pretrained(adapter)
            base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float16).to("cuda")
            _model = (PeftModel.from_pretrained(base, str(adapter)).eval(), tok)
    return _model


def kd_multitask(adapter=KD_ADAPTER):
    import torch  # fail here (ImportError) rather than on the first question
    if not torch.cuda.is_available():
        raise RuntimeError("no CUDA GPU")
    if not (Path(adapter) / "adapter_model.safetensors").exists():
        raise RuntimeError(f"adapter not found: {adapter}")
    import peft  # noqa: F401  (missing peft -> ImportError -> fallback)

    def gate(question):
        model, tok = _load(adapter)
        prompt = tok.apply_chat_template([{"role": "user", "content": f"{INSTRUCTION}\n\nText: {question}"}],
                                         tokenize=False, add_generation_prompt=True)
        p_ids = tok(prompt, add_special_tokens=False).input_ids
        scores = []
        with _lock, torch.no_grad():
            for label in ("database", "general"):  # the student answers in lower case
                l_ids = tok(label, add_special_tokens=False).input_ids
                ids = torch.tensor([p_ids + l_ids], device="cuda")
                logp = torch.log_softmax(model(ids).logits[0, len(p_ids) - 1:-1].float(), -1)
                scores.append(sum(logp[i, t].item() for i, t in enumerate(l_ids)))
        p_db = torch.softmax(torch.tensor(scores), 0)[0].item()
        return {"database": p_db >= THRESHOLD, "p_database": round(p_db, 4)}

    gate.label = "Agent 2 distilled Qwen2.5-1.5B student (multitask, Task 1)"
    gate.stand_in = False
    threading.Thread(target=_load, args=(adapter,), daemon=True).start()  # warm up in the background
    return gate


def results(folder=ROOT):
    """Her native-vs-distilled comparison (native_vs_kd_statistical_results.csv), or None if it isn't here."""
    import csv
    f = folder / "native_vs_kd_statistical_results.csv"
    if not f.exists():
        return None
    return [{"task": r["task"], "n": int(r["test_examples"]), "native": float(r["native_accuracy"]), "kd": float(r["kd_accuracy"]),
             "wins": int(r["kd_wins"]), "losses": int(r["kd_losses"]), "p": float(r["mcnemar_exact_p_value"])}
            for r in csv.DictReader(open(f, encoding="utf-8"))]


def from_env():
    """The gate named by J26_GATE, or None for Agent 1's word check alone (also when her model can't run here)."""
    name = os.environ.get("J26_GATE", "word_match")
    if name == "word_match":
        return None
    if name == "kd_multitask":
        try:
            return kd_multitask()
        except (ImportError, RuntimeError) as e:
            print(f"J26_GATE=kd_multitask unavailable ({e}); using Agent 1's word check")
            return None
    raise ValueError(f"unknown J26_GATE '{name}' (use word_match or kd_multitask)")
