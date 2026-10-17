# Agent 3 - LoRA vs HydraLoRA (K.G.Y.V. Thathsarani)

Goal: compare standard LoRA with HydraLoRA for text-to-SQL.
HydraLoRA uses one head per query type: simple, single-join, multi-join, aggregation.

Plan:
1. Build the training dataset from Spider train, labelled by complexity.
2. Train a standard LoRA baseline.
3. Build the HydraLoRA module with hard-coded routing.
4. Compare both on the same data and report per complexity bucket.

Status: environment set up on 2026-10-06 (Python 3.11.9, tests pass).