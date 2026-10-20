
import argparse
import gc
import json
import time
from pathlib import Path

import bitsandbytes as bnb
import pandas as pd
import torch
import torch.nn as nn

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer
)

from src.qwen_generate import generate_sql
from src.prompt_builder import build_prompt
from src.sql_util import clean_sql



# ============================================================
# STEP 1 - CONFIGURATION
# ============================================================

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

TOTAL_LAYERS = 28
DEVICE = torch.device("cuda:0")

INT4_TYPE = "nf4"
INT8_THRESHOLD = 6.0

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "results/qwen/qwen_precision_allocation.csv"
)

OUTPUT_DIR = ROOT / "results/qwen"

MODULE_NAMES = [
    ("self_attn", "q_proj"),
    ("self_attn", "k_proj"),
    ("self_attn", "v_proj"),
    ("self_attn", "o_proj"),
    ("mlp", "gate_proj"),
    ("mlp", "up_proj"),
    ("mlp", "down_proj"),
]


# ============================================================
# STEP 2 - LOAD PRECISION ALLOCATION
# ============================================================

def read_allocation():

    if not INPUT.is_file():
        raise FileNotFoundError(
            f"Allocation file not found: {INPUT}"
        )

    df = pd.read_csv(INPUT)

    required = {"layer", "precision"}

    if not required.issubset(df.columns):
        raise ValueError(
            "CSV must contain layer and precision columns"
        )

    if df[["layer", "precision"]].isnull().any().any():
        raise ValueError(
            "Allocation contains missing values"
        )

    layer_numbers = pd.to_numeric(
        df["layer"],
        errors="raise"
    )

    if (layer_numbers % 1 != 0).any():
        raise ValueError("Layer IDs must be integers")

    df["layer"] = layer_numbers.astype(int)

    df["precision"] = (
        df["precision"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if len(df) != TOTAL_LAYERS:
        raise ValueError(
            f"Expected {TOTAL_LAYERS} allocation rows"
        )

    if df["layer"].duplicated().any():
        raise ValueError("Duplicate layer IDs found")

    if set(df["layer"]) != set(range(TOTAL_LAYERS)):
        raise ValueError("Layer IDs must be 0 to 27")

    if not df["precision"].isin(["INT4", "INT8"]).all():
        raise ValueError(
            "Precision must be INT4 or INT8"
        )

    return dict(zip(df["layer"], df["precision"]))


# ============================================================
# STEP 3 - VERIFY QUANTIZED MODULE
# ============================================================

def verify_quantized_module(module, bits):

    if bits == 4:

        if not isinstance(module, bnb.nn.Linear4bit):
            raise RuntimeError("Expected Linear4bit")

        if getattr(module.weight, "quant_state", None) is None:
            raise RuntimeError(
                "INT4 quantization state missing"
            )

    elif bits == 8:

        if not isinstance(module, bnb.nn.Linear8bitLt):
            raise RuntimeError("Expected Linear8bitLt")

        if module.weight.dtype != torch.int8:
            raise RuntimeError(
                "INT8 weights are not quantized"
            )

        if getattr(module.weight, "SCB", None) is None:
            raise RuntimeError(
                "INT8 scaling information missing"
            )

    else:
        raise ValueError("Unsupported precision")

    if module.weight.device.type != "cuda":
        raise RuntimeError(
            "Quantized module is not on CUDA"
        )


# ============================================================
# STEP 4 - CONVERT FP16 LINEAR MODULE
# ============================================================

def convert_linear_module(original, bits):

    if not isinstance(original, nn.Linear):
        raise TypeError(
            f"Expected nn.Linear, got {type(original)}"
        )

    if original.weight.device.type != "cpu":
        raise RuntimeError(
            "Original linear module must be on CPU"
        )

    in_features = original.in_features
    out_features = original.out_features
    has_bias = original.bias is not None

    if bits == 4:

        quantized = bnb.nn.Linear4bit(
            in_features,
            out_features,
            bias=has_bias,
            compute_dtype=torch.float16,
            quant_type=INT4_TYPE,
            compress_statistics=True
        )

    elif bits == 8:

        quantized = bnb.nn.Linear8bitLt(
            in_features,
            out_features,
            bias=has_bias,
            has_fp16_weights=False,
            threshold=INT8_THRESHOLD
        )

    else:
        raise ValueError(
            f"Unsupported precision: {bits}"
        )

    # Load pretrained FP16 weights
    quantized = quantized.half()

    quantized.load_state_dict(
        original.state_dict(),
        strict=True
    )

    quantized.requires_grad_(False)

    # Quantization occurs during transfer to CUDA
    quantized = quantized.to(DEVICE)

    verify_quantized_module(quantized, bits)

    return quantized


# ============================================================
# STEP 5 - BUILD ADAPTIVE MODEL
# ============================================================

def load_adaptive_model(probe_one=False):

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU is not available"
        )

    print("=" * 60)
    print("DAY 8 - QWEN ADAPTIVE MIXED-PRECISION MODEL")
    print("=" * 60)

    print("GPU:", torch.cuda.get_device_name(0))

    free_memory, total_memory = torch.cuda.mem_get_info()

    print(
        f"Free GPU memory: {free_memory / 1024**2:.2f} MB"
    )

    print(
        f"Total GPU memory: {total_memory / 1024**2:.2f} MB"
    )

    # --------------------------------------------------------
    # Load Day 7 allocation
    # --------------------------------------------------------

    precision_map = read_allocation()

    print("\nPrecision allocation:")

    for layer_id, precision in sorted(
        precision_map.items()
    ):
        print(f"Layer {layer_id:02d} -> {precision}")

    int4_layers = sum(
        p == "INT4" for p in precision_map.values()
    )

    int8_layers = sum(
        p == "INT8" for p in precision_map.values()
    )

    print("\nTotal INT4 layers:", int4_layers)
    print("Total INT8 layers:", int8_layers)

    # --------------------------------------------------------
    # Load original FP16 Qwen on CPU
    # --------------------------------------------------------

    print("\nLoading original FP16 Qwen on CPU...")

    start_time = time.perf_counter()

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID
    )

    model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    dtype=torch.float16,
    device_map={"": "cpu"},
    low_cpu_mem_usage=True,
    weights_only=True
    )

    model.eval()

    print(
        "Model loading time:",
        round(time.perf_counter() - start_time, 2),
        "seconds"
    )

    total_layers = len(model.model.layers)

    print("Total transformer layers:", total_layers)

    if total_layers != TOTAL_LAYERS:
        raise RuntimeError(
            f"Expected 28 layers, found {total_layers}"
        )

    for name, parameter in model.named_parameters():

        if parameter.device.type != "cpu":
            raise RuntimeError(
                f"Original model is not fully on CPU: {name}"
            )

    # Verify Qwen module structure before conversion
    for layer_id, layer in enumerate(model.model.layers):

        for parent_name, module_name in MODULE_NAMES:

            parent = getattr(layer, parent_name)
            original = getattr(parent, module_name)

            if not isinstance(original, nn.Linear):
                raise TypeError(
                    f"Layer {layer_id}: "
                    f"{parent_name}.{module_name} "
                    f"is not nn.Linear"
                )

    print("Qwen module structure verified.")

    # --------------------------------------------------------
    # Convert layer-by-layer
    # --------------------------------------------------------

    torch.cuda.reset_peak_memory_stats(DEVICE)

    conversion_start = time.perf_counter()

    conversion_report = []

    layers_to_convert = (
        1 if probe_one else TOTAL_LAYERS
    )

    for layer_id in range(layers_to_convert):

        precision = precision_map[layer_id]

        bits = 8 if precision == "INT8" else 4

        layer = model.model.layers[layer_id]

        print(
            f"\nConverting Layer {layer_id:02d} "
            f"-> {precision}",
            flush=True
        )

        for parent_name, module_name in MODULE_NAMES:

            parent = getattr(
                layer,
                parent_name
            )

            original = getattr(
                parent,
                module_name
            )

            quantized = convert_linear_module(
                original,
                bits
            )

            # Replace original module
            setattr(
                parent,
                module_name,
                quantized
            )

            conversion_report.append({
                "layer": layer_id,
                "module": f"{parent_name}.{module_name}",
                "precision": precision,
                "weight_dtype": str(quantized.weight.dtype),
                "module_type": type(quantized).__name__
            })

            del original, quantized

        if probe_one:
            print(
                "\nLayer 0 conversion successful!"
            )
            print(
                "This is a conversion test, "
                "not a complete inference model."
            )

            return None, tokenizer, {
                "conversion_report": conversion_report,
                "precision_map": precision_map
            }

        # Move normalization modules to GPU
        layer.input_layernorm.to(DEVICE)
        layer.post_attention_layernorm.to(DEVICE)

        gc.collect()

        allocated_mb = (
            torch.cuda.memory_allocated(DEVICE)
            / 1024**2
        )

        print(
            f"Layer {layer_id:02d} converted. "
            f"GPU memory: {allocated_mb:.2f} MB",
            flush=True
        )

    conversion_time = (
        time.perf_counter() - conversion_start
    )

    print("\nAll 28 layers converted!")

    # --------------------------------------------------------
    # Move remaining model modules to GPU
    # --------------------------------------------------------

    print("\nMoving remaining modules to GPU...")

    model.model.embed_tokens.to(DEVICE)
    model.model.norm.to(DEVICE)
    model.lm_head.to(DEVICE)

    if getattr(model.model, "rotary_emb", None) is not None:
        model.model.rotary_emb.to(DEVICE)

    # Verify every parameter is on CUDA
    cpu_parameters = [
        name
        for name, parameter in model.named_parameters()
        if parameter.device.type != "cuda"
    ]

    if cpu_parameters:
        raise RuntimeError(
            "Some parameters remain on CPU: "
            + str(cpu_parameters[:10])
        )

    print("All model parameters are on CUDA.")

    # --------------------------------------------------------
    # Verify actual quantization
    # --------------------------------------------------------

    print("\nVerifying quantized modules...")

    count_4bit = 0
    count_8bit = 0

    for layer_id, layer in enumerate(model.model.layers):

        bits = (
            4 if precision_map[layer_id] == "INT4"
            else 8
        )

        for parent_name, module_name in MODULE_NAMES:

            parent = getattr(layer, parent_name)

            module = getattr(parent, module_name)

            verify_quantized_module(
                module,
                bits
            )

            if bits == 4:
                count_4bit += 1
            else:
                count_8bit += 1

    expected_4bit = int4_layers * len(MODULE_NAMES)
    expected_8bit = int8_layers * len(MODULE_NAMES)

    if count_4bit != expected_4bit:
        raise RuntimeError(
            "INT4 module count mismatch"
        )

    if count_8bit != expected_8bit:
        raise RuntimeError(
            "INT8 module count mismatch"
        )

    if count_4bit + count_8bit != 196:
        raise RuntimeError(
            "Expected exactly 196 quantized modules"
        )

    print("\nQuantization verification successful!")

    print("INT4 modules:", count_4bit)
    print("INT8 modules:", count_8bit)

    model.eval()

    model_memory_mb = (
        torch.cuda.memory_allocated(DEVICE)
        / 1024**2
    )

    conversion_peak_mb = (
        torch.cuda.max_memory_allocated(DEVICE)
        / 1024**2
    )

    metrics = {
        "model": MODEL_ID,
        "total_layers": TOTAL_LAYERS,
        "int4_layers": int4_layers,
        "int8_layers": int8_layers,
        "int4_modules": count_4bit,
        "int8_modules": count_8bit,
        "conversion_time_seconds": round(
            conversion_time, 3
        ),
        "model_gpu_allocated_mb": round(
            model_memory_mb, 2
        ),
        "conversion_peak_vram_mb": round(
            conversion_peak_mb, 2
        ),
        "precision_allocation": {
            str(layer): precision
            for layer, precision in precision_map.items()
        },
        "conversion_report": conversion_report
    }

    print("\nAdaptive model built successfully!")

    return model, tokenizer, metrics


# ============================================================
# STEP 6 - MAIN FUNCTION
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--check",
        action="store_true"
    )

    parser.add_argument(
        "--probe-one",
        action="store_true"
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Allocation verification only
    # --------------------------------------------------------

    if args.check:

        allocation = read_allocation()

        print("Qwen precision allocation verified!")

        print("Total layers:", len(allocation))

        for layer_id, precision in sorted(
            allocation.items()
        ):
            print(
                f"Layer {layer_id:02d} -> {precision}"
            )

        return

    # --------------------------------------------------------
    # Build model
    # --------------------------------------------------------

    model, tokenizer, metrics = load_adaptive_model(
        probe_one=args.probe_one
    )

    if args.probe_one:
        return

    # --------------------------------------------------------
    # SQL generation smoke test
    # --------------------------------------------------------

    print("\nTesting adaptive SQL generation...")

    question = "How many singers are there?"

    schema = """
CREATE TABLE singer (
    Singer_ID INTEGER,
    Name TEXT,
    Age INTEGER
);
"""

    
    prompt = build_prompt(schema, question)

    torch.cuda.synchronize(DEVICE)

    torch.cuda.reset_peak_memory_stats(DEVICE)

    start_time = time.perf_counter()

    generated_sql = generate_sql(
        model,
        tokenizer,
        prompt
    )

    generated_sql = clean_sql(generated_sql)

    torch.cuda.synchronize(DEVICE)

    latency = time.perf_counter() - start_time

    inference_peak_mb = (
        torch.cuda.max_memory_allocated(DEVICE)
        / 1024**2
    )

    print("\n" + "=" * 60)
    print("SQL GENERATION RESULT")
    print("=" * 60)

    print("Question:", question)
    print("Generated SQL:", generated_sql)

    print(
        f"Latency: {latency:.2f} seconds"
    )

    print(
        f"Peak inference VRAM: "
        f"{inference_peak_mb:.2f} MB"
    )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report = pd.DataFrame(
        metrics.pop("conversion_report")
    )

    report.to_csv(
        OUTPUT_DIR / "module_quantization_report.csv",
        index=False
    )

    with open(
        OUTPUT_DIR / "mixed_precision_config.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metrics,
            f,
            indent=4
        )

    smoke_results = {
        "question": question,
        "generated_sql": generated_sql,
        "latency_seconds": round(latency, 4),
        "inference_peak_vram_mb": round(
            inference_peak_mb, 2
        )
    }

    with open(
        OUTPUT_DIR / "smoke_test_results.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            smoke_results,
            f,
            indent=4
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("DAY 8 - FINAL SUMMARY")
    print("=" * 60)

    print("Model:", MODEL_ID)
    print("Total layers:", TOTAL_LAYERS)

    print(
        "INT4 layers:",
        metrics["int4_layers"]
    )

    print(
        "INT8 layers:",
        metrics["int8_layers"]
    )

    print(
        "INT4 modules:",
        metrics["int4_modules"]
    )

    print(
        "INT8 modules:",
        metrics["int8_modules"]
    )

    print(
        f"SQL latency: {latency:.2f} seconds"
    )

    print("Generated SQL:", generated_sql)

    print("\nResults saved to:", OUTPUT_DIR)

    print("\nSUCCESSFULLY COMPLETED !")


if __name__ == "__main__":
    main()
