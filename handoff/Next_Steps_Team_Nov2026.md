# Next steps for each member (21 November 2026)

From: Janiru (Agent 1, team application). This document uses short sentences on purpose.
Source: the system recap and novelty check of 21 November 2026.

## For all members

- Use the same question sets. Run `python -m scripts.get_spider --width` one time. It makes
  `eval/spider_dev_full.json` (about 1,000 questions).
- Report execution accuracy for each complexity bucket, with a paired test (McNemar) and a 95% confidence interval.
- The full pipeline has one evaluation script: `python -m scripts.e2e_eval --pairs <files> --name <configuration>`.
  It uses the same settings as the application. `--compare A B` compares two runs.
- Put large model files on Google Drive, not in git. Put the result files in git.

## Thathsarani (Agent 3)

Your LoRA adapter can now write the SQL in the application: `J26_GENERATOR=agent3` (see `RUNNING_THE_APP.md`).

1. Send the two adapter folders (`lora_r16_seed42`, `hydra_r16_seed42`): `adapters.pt` and `adapter_meta.json`.
2. Merge the branch `thathsarani-hydra` into `main`. `main` does not have your policies and artefacts.
3. Train two more seeds for LoRA and for HydraLoRA. One seed is not sufficient evidence.
4. Evaluate on `eval/spider_dev_full.json`. 128 questions cannot show a difference smaller than about 20 points.
5. Route HydraLoRA again with the schema-aware classifier (accuracy 0.676, was 0.588).
6. Note: your adapters learned from the full schema. The application sends Agent 1's selected schema.
   A training run with Agent 1's schema format is a useful comparison.

## Wathsala (Agent 2)

1. Commit your 1.5B training notebook, your exact prompt and the checkpoint location. The application gets 0.81 on
   injection detection without them. Your result is 0.948.
2. Fix the free-text problem: the distilled student gives 60 invalid answers of 116. Label scoring hides this.
3. Start the SQL distillation now. Agent 3's final comparison cannot start without the two base models.
   - Teacher: Qwen2.5-7B-Instruct. Questions: Spider TRAIN only. Keep only teacher SQL that runs.
   - Output: a distilled 1.5B model, a native 1.5B model, and the control model (same prompts, gold SQL).
4. Agree a delivery date with the team. If the date is missed, Agent 3 uses the released Qwen model (the fallback in
   the execution plan).

## Karunanayake (Agent 4)

1. Use separate questions to select the layers and to test: `python -m scripts.make_quant_split` makes
   `eval/quant_calibration.json` and `eval/quant_test.json`. The two sets share no database.
2. Test the mixed model, INT4, INT8 and FP16 on the same test set (200 questions).
3. Add two controls: 8-bit layers selected at random (same count), and a standard GGUF `Q4_K_M` model.
4. A paper named TAQ (arXiv 2511.06516) selects 8-bit and 4-bit layers for one task, with Qwen2.5-3B.
   Cite it. Your new part is the SQL task and the result for each SQL complexity bucket.
5. Add the empty-result check: 0 rows after a filter -> read the real values of the column -> one retry.
6. Run the method again on Agent 3's LoRA model when it is in the application.

## Ekanayake (Agent 1)

1. Run the adaptive-width experiment: `reports/agent1_width/README.md`.
2. Run the end-to-end evaluation for each system configuration and make the one results table for PP2.
