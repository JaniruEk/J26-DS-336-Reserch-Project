# Agent 1 – Phase 8 (PP1 fixes): retrieval results

Run on 17 Oct 2026. The embedding model is Chroma's MiniLM-L6-v2, and token counts use tiktoken cl100k_base, the same back-ends as Phases 1–7. Each raw `*.txt` file is the full output of
`python -m agent1_retrieval.evaluate --pairs eval/<set>_pairs.json [--recommended]`. The default files reproduce the Phase 3–6 numbers exactly.

`--recommended` (`RECOMMENDED` in `retrieval.py`) uses 3 semantic anchors joined by FK paths on every question. It leaves tables with 8 columns or fewer unpruned, which was the Phase 7 best execution setting. It also adds the new linking signals in `linking.py`:
- split and abbreviated column names (`c_acctbal`, `o_totalprice`);
- a small business-synonym list ("spent" → total, "sold" → quantity);
- value linking: a literal like "Canada" is found in `Customer.Country` by a read-only lookup;
- display columns (Name, Title, FirstName and LastName) kept for tables the question names.

Every kept column now carries its reason, shown in the handoff `trace`.

## Before and after for hybrid_pruned (column recall, tokens)

| Set | Phase 1–7 default | PP1 recommended | hybrid with the same anchors (reference) |
|---|---|---|---|
| Chinook (14, tuning set) | .73 @ 168 | **.95 @ 200** | .95 @ 262 |
| TPC-H (14) | .46 @ 137 | **.97 @ 241** | .97 @ 322 |
| Spider (120, never tuned) | .89 @ 87 | **.98 @ 138** | .99 @ 161 |

Paired, pruned minus hybrid with the same anchors (95% bootstrap CI): Spider tokens −23 [−29, −17], column recall −.01 [−.01, .00]. Chinook −62 tokens, recall ±0. TPC-H −81 tokens, recall ±0.

## Latency

The question embedding used to pad every text to 256 tokens. It now runs unpadded, and the vectors are identical (maximum difference 0.0). Embedding time per question fell from 82 ms to 5.5 ms. A full 148-question evaluation now takes 21 s instead of 2 min. Warm hybrid_pruned latency is about 80–120 ms mean against the 500 ms target. Tests cover a warm-latency check on Chinook and synthetic schemas of 20 and 60 tables.

## Not measured here

Execution accuracy needs Ollama (phi3), which this environment can't reach. Run it on your machine:

```
python -m agent1_retrieval.evaluate --pairs eval/chinook_pairs.json eval/spider_pairs.json --recommended --exec phi3
```

Until that run exists, describe the accuracy effect as unknown. Phase 7 showed that pruning only breaks even when column recall is about .96 or higher, and the recommended configuration reaches .98 on Spider.

## Caveats

- The synonym list and the label-column rule came from error analysis on Chinook and TPC-H. Spider is the clean test, and there the new signals add +.01 recall, which is neutral.
- Value linking needs rows in the database. The generated TPC-H file is schema-only.
- FK inference (`--infer-fks`, `infer_missing_fks=True`) is opt-in. Rules: a column with the same name as another table's primary key, `<table>_id`, and TPC-H prefixes.
