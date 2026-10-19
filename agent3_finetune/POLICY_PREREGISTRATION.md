# Pre-registration: inference-time routing policies for HydraLoRA

Written before any policy was run. Commit this file first; the commit time is the evidence that the policies, thresholds and decision rules were fixed in advance.

**Honest disclosure:** the policies were chosen after the head-specialisation table and the routing analysis had been seen (both use the same 128 evaluation questions). So this protects against choosing a policy by its score, not against all influence of earlier results.

## Question
Can an inference-time routing policy recover the accuracy HydraLoRA loses when its heads are chosen by Agent 1's live classifier (59% routing accuracy; 0.391 execution accuracy), and can any policy beat plain LoRA at equal cost?

## Data and outcome
- The same 128 scored questions (pooled Spider dev + Chinook, execution accuracy).
- **Primary outcome:** overall execution accuracy. Per-bucket accuracies are descriptive only.
- Every policy picks among the answers of the four HydraLoRA heads that were already generated (greedy decoding, saved in the four fixed-head runs). The offline method was verified: rebuilding the live-classifier run from the fixed-head files reproduced it exactly (50/128, 0 differences).
- Policies may use only what a deployed system can see: the classifier's probabilities, and whether each generated SQL **runs without error** and **returns at least one row** ("ok"). They must never use the gold answer.

## Policies (fixed now; no other policies, thresholds or variants will be reported as findings)
| ID | Rule | Cost (heads run per question) |
|---|---|---|
| P1 fallback | If the classifier's top probability is below **0.5**, use the **aggregation** head (the head with the most training data, 2,336 rows); otherwise use the top head | 1 |
| P2 retry | Run the top-ranked head. If its SQL is not "ok", run the **second** most probable head and use it if it is "ok"; otherwise keep the first answer | 1 to 2 |
| P3 vote | Run all four heads; among the "ok" answers, choose the **result set returned by most heads**; ties go to the group containing the head with the highest classifier probability; if no head is "ok", use the top head | 4 |

## References
Plain LoRA (single pass); HydraLoRA with the live classifier (the deployable baseline); HydraLoRA with the true label (not deployable); the best fixed head; the **ceiling** "any of the four heads is correct" (no selection policy can exceed it).

## Decision rules
1. Each policy is compared with (a) HydraLoRA with the live classifier and (b) plain LoRA, with the paired bootstrap CI and exact McNemar test of the shared `stats.py`. With three policies, p below **0.017** (0.05 / 3) counts as evidence; everything is reported with its CI, significant or not.
2. A policy may be called better than plain LoRA **only if** its paired CI against LoRA excludes zero **and** it also beats LoRA at equal cost. P2 costs up to 2x and P3 costs 4x. The equal-cost LoRA baselines (greedy answer plus sampled answers with execution-based retry / vote; temperature 0.7, seed 42) are run on the GPU only if a policy first beats single-pass LoRA; if it does not, no "win" is claimed and no extra run is needed.
3. If no policy beats LoRA, that is reported as the result: "routing policies recover X points of the Y points lost, but do not beat a single adapter".

## Limits to state
One seed, 128 questions (about 31 per bucket), a placeholder base model, execution accuracy on questions whose gold query returns rows.
