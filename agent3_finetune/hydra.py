"""HydraLoRA with hard-coded complexity routing (Agent 3).

For every adapted linear layer: ONE shared A matrix and ONE B matrix per complexity bucket ("head").
A router picks the head of each example in the batch from its complexity label.

With n_heads = 1 this is exactly standard LoRA (same initialisation and scaling as PEFT), so the LoRA baseline,
HydraLoRA and a parameter-matched LoRA control can all use this one code path and differ only in
`n_heads` and `rank`.

Self-test (needs only torch, no GPU):  python -m agent3_finetune.hydra
"""
import json
import math
from pathlib import Path

import torch
from torch import nn

HEADS = ("simple", "single-join", "multi-join", "aggregation")  # must match agent1_retrieval.complexity.BUCKETS
TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


DEFAULT_HEAD = "single-join"  # fallback for unknown or missing labels (design choice, to be evaluated)


def head_index(label, default=DEFAULT_HEAD):
    """Head index for a complexity label. Unknown or missing labels fall back to `default` instead of failing."""
    return HEADS.index(label if label in HEADS else default)


class Router:
    """Shared holder. Every adapted layer reads the current batch's head indices (LongTensor [batch]) from here."""

    def __init__(self):
        self.index = None

    def set(self, index):
        self.index = index


class HydraLinear(nn.Module):
    """Frozen base nn.Linear + low-rank update: base(x) + (alpha/rank) * B[head] A x."""

    def __init__(self, base, router, rank, alpha, n_heads, dropout=0.05):
        super().__init__()
        dev = base.weight.device
        self.base, self.router = base, router
        self.n_heads, self.scale = n_heads, alpha / rank
        self.lora_A = nn.Linear(base.in_features, rank, bias=False, device=dev, dtype=torch.float32)
        self.lora_B = nn.Parameter(torch.zeros(n_heads, base.out_features, rank, device=dev, dtype=torch.float32))
        nn.init.kaiming_uniform_(self.lora_A.weight, a=math.sqrt(5))  # same as PEFT; B starts at zero
        self.dropout = nn.Dropout(dropout)

    @property
    def weight(self):  # some library code inspects .weight
        return self.base.weight

    def forward(self, x):
        out = self.base(x)
        h = self.lora_A(self.dropout(x.to(self.lora_A.weight.dtype)))  # [B, S, r], A is shared by all heads
        if self.n_heads == 1:
            delta = h @ self.lora_B[0].transpose(0, 1)
        else:
            idx = self.router.index
            if idx is None or idx.shape[0] != x.shape[0]:
                raise RuntimeError("router.index must be a LongTensor with one head index per example in the batch")
            delta = torch.bmm(h, self.lora_B[idx].transpose(1, 2))  # [B,S,r] x [B,r,out]
        return out + (delta * self.scale).to(out.dtype)


def add_adapters(model, router, rank, alpha, n_heads, dropout=0.05, targets=TARGETS):
    """Freeze the model and wrap every target nn.Linear with a HydraLinear. Returns the number of wrapped layers."""
    for p in model.parameters():
        p.requires_grad = False
    wrapped = 0
    for parent in list(model.modules()):
        for name, child in list(parent.named_children()):
            if name in targets and isinstance(child, nn.Linear):
                setattr(parent, name, HydraLinear(child, router, rank, alpha, n_heads, dropout))
                wrapped += 1
    return wrapped


def count_trainable(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def save_adapters(model, path, meta):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items() if "lora_" in k}, path / "adapters.pt")
    (path / "adapter_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_adapters(model, path):
    state = torch.load(Path(path) / "adapters.pt", map_location="cpu")
    res = model.load_state_dict(state, strict=False)
    missing = [k for k in res.missing_keys if "lora_" in k]
    if res.unexpected_keys or missing:
        raise RuntimeError(f"adapter mismatch: unexpected={res.unexpected_keys[:3]} missing={missing[:3]}")


# Qwen2.5-1.5B linear layers (in, out) per transformer block; 28 blocks. The LoRA rank-16 total below reproduces
# the 18,464,768 trainable parameters measured in the real LoRA run, which confirms these shapes.
QWEN15_LAYERS = [(1536, 1536), (1536, 256), (1536, 256), (1536, 1536), (1536, 8960), (1536, 8960), (8960, 1536)]
QWEN15_BLOCKS = 28


def expected_params(rank, n_heads, layers=QWEN15_LAYERS, blocks=QWEN15_BLOCKS):
    return blocks * sum(rank * i + n_heads * rank * o for i, o in layers)


# ------------------------------------------------------------------ self-test
def run_tests():
    torch.manual_seed(0)

    class Tiny(nn.Module):
        def __init__(self):
            super().__init__()
            self.q_proj = nn.Linear(8, 8)
            self.up_proj = nn.Linear(8, 16, bias=False)

    x = torch.randn(4, 5, 8)

    # 1. zero initialisation: before training the adapted layer equals the base layer
    t, r = Tiny(), Router()
    add_adapters(t, r, rank=4, alpha=8, n_heads=4, dropout=0.0)
    r.set(torch.tensor([0, 1, 2, 3]))
    assert torch.allclose(t.q_proj(x), t.q_proj.base(x)), "B must start at zero"
    print("PASS 1  zero init: adapted layer == base layer")

    # 2. routing: in a mixed batch, example i must receive head labels[i]
    with torch.no_grad():
        t.q_proj.lora_B.normal_()
    mixed = t.q_proj(x)
    uniform = {}
    for h in range(4):
        r.set(torch.full((4,), h))
        uniform[h] = t.q_proj(x)
        assert torch.allclose(mixed[h], uniform[h][h], atol=1e-6), f"example {h} did not receive head {h}"
    assert not torch.allclose(uniform[0], uniform[1]), "different heads must give different outputs"
    print("PASS 2  routing: each example reaches its own head, heads differ")

    # 3. gradient isolation: only the routed head gets gradient; shared A always does
    t.zero_grad()
    r.set(torch.full((4,), 2))
    t.q_proj(x).sum().backward()
    g = t.q_proj.lora_B.grad
    for h in range(4):
        assert (g[h].abs().sum().item() > 0) == (h == 2), f"gradient leaked to head {h}"
    assert t.q_proj.lora_A.weight.grad.abs().sum().item() > 0, "shared A got no gradient"
    print("PASS 3  gradients: only the routed head is updated, shared A is updated")

    # 4. one head == standard LoRA formula
    t1, r1 = Tiny(), Router()
    add_adapters(t1, r1, rank=4, alpha=8, n_heads=1, dropout=0.0)
    with torch.no_grad():
        t1.q_proj.lora_B.normal_()
    layer = t1.q_proj
    manual = layer.base(x) + (8 / 4) * (x @ layer.lora_A.weight.T) @ layer.lora_B[0].T
    assert torch.allclose(layer(x), manual, atol=1e-6), "n_heads=1 differs from standard LoRA"
    print("PASS 4  n_heads=1 equals standard LoRA")

    # 5. parameter count: A (rank*in) + one B (out*rank) per head, base frozen
    t4, r4 = Tiny(), Router()
    add_adapters(t4, r4, rank=4, alpha=8, n_heads=4)
    assert count_trainable(t4) == (4 * 8 + 4 * 4 * 8) + (4 * 8 + 4 * 4 * 16), "unexpected trainable parameter count"
    assert not any(p.requires_grad for n, p in t4.named_parameters() if ".base." in n), "base weights must be frozen"
    print("PASS 5  parameter count correct, base frozen")

    # 6. parameter counts for Qwen2.5-1.5B (the numbers to report)
    lora16 = expected_params(16, 1)
    assert lora16 == 18_464_768, "shape table does not reproduce the measured LoRA parameter count"
    hydra16 = expected_params(16, 4)
    matched = min(range(1, 128), key=lambda q: abs(expected_params(q, 1) - hydra16))
    print(f"PASS 6  Qwen2.5-1.5B trainable parameters: LoRA r=16: {lora16:,} | HydraLoRA r=16 x 4 heads: {hydra16:,} "
          f"({hydra16 / lora16:.2f}x) | parameter-matched LoRA: rank {matched} ({expected_params(matched, 1):,})")

    # 7. (GPU only) fp16 base layer with fp32 adapters keeps working
    if torch.cuda.is_available():
        base = nn.Linear(8, 8).half().cuda()
        rr = Router()
        layer = HydraLinear(base, rr, 4, 8, 4, 0.0)
        rr.set(torch.tensor([0, 1, 2, 3], device="cuda"))
        out = layer(torch.randn(4, 5, 8, device="cuda").half())
        assert out.dtype == torch.float16 and layer.lora_B.dtype == torch.float32
        print("PASS 7  fp16 base layer with fp32 adapters works on the GPU")
    else:
        print("SKIP 7  no GPU found (this test is optional)")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    run_tests()
