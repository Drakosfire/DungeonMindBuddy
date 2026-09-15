# Frozen 42-session recap ingest — scale / health (`deepseek-v4.1-flash`)

Generated from this arm's `INGEST.json` after the serial C1→C2 run.
The OpenAI arm remains at `../openai-gpt-5.4-mini/` and was not overwritten.

**Corpus:** C1 S1–17 + C2 S1–25.  Do not regenerate C2 S26/S27.

**Experiment claim:** two autoregressive, chronologically generated candidate
arms, followed by zero-model governed replay into independently initialized
Worlds.  This arm's candidate generation accumulated `extra_known_entities`
from prior **candidate graphs**; it is not evidence that production Session N
extraction sees only the committed World through Session N−1.

These counts are candidate-generation measurements, not graph-quality results.

## Execution

| Item | Result |
|---|---|
| Documents | 42 / 42 ok (C1 S1–S17, then C2 S1–S25) |
| Model | `deepseek/deepseek-v4.1-flash` |
| Provider | OpenRouter, DeepSeek pin, fallback disabled, reasoning off |
| Transport | Chat Completions `json_object` + local schema retry |
| `node_pass_workers` | 6 (intra-document only) |
| Extra-known-entity count | 708 (monotonic) |
| Wall time (full run) | 1169 s (~19.5 min), S1 resumed from canary |
| Independent-pass overlap | ratio 3.05 |
| Total cost | $0.604547 |

## Candidate inventory vs OpenAI arm

| Metric | DeepSeek | openai-gpt-5.4-mini |
|---|---:|---:|
| Cost | $0.60 | $3.33 |
| Nodes (sum) | 1079 | 1265 |
| Edges (sum) | 636 | 463 |
| Zero-edge recaps | none | 5 |
| Extra-known end | 708 | 886 |

These are durable **candidates**, not a published World Graph.
