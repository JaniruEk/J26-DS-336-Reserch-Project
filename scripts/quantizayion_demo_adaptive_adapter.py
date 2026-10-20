
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.qwen_build_adaptive import (
    load_adaptive_model,
    MODEL_ID as ADAPTIVE_MODEL_ID,
)


def load_adaptive(model_id):
    if model_id != ADAPTIVE_MODEL_ID:
        raise ValueError(
            f"Model mismatch: {model_id} != {ADAPTIVE_MODEL_ID}"
        )

    model, tokenizer, metrics = load_adaptive_model(
        probe_one=False
    )

    if model is None:
        raise RuntimeError("Adaptive model was not loaded")

    return model, tokenizer
