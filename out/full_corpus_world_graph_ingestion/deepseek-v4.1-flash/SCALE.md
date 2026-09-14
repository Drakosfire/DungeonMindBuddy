# Full-corpus recap ingest — scale / health (`deepseek-v4.1-flash`)

Generated from this arm's `INGEST.json` after the serial C1→C2 run.
The OpenAI arm remains at `../openai-gpt-5.4-mini/` and was not overwritten.

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
