<!-- benchmark_artifact: recap_ingest_multi_run_summary_v1 | iso_utc: 2026-04-18T21:47:08Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | runs: 5 | gates_pass: 0/5 -->

# Scope-B recap-ingest cohort summary (N=5)

- **scenario**: `session_recap_ingest_session_20`
- **model**: `gpt-5.4-mini`
- **iso_utc**: `2026-04-18T21:47:08Z`
- **gates pass rate**: 0/5
- **tool_trace pass rate**: 0/5
- **payload pass rate**: 5/5
- **cost_usd**: min=0.032931 mean=0.033962 max=0.035159 sum=0.169808
- **tool_trace rows**: min=7 mean=7 max=7
- **distinct recap_write payloads (sha256_16)**: 5 (05f774ff4d073d71, 29085a8fd4e3e0ba, a4bae0aa34e5e3ba, a844bf8d66915ef8, d164dbfe52772770)
- **distinct tool_trace signatures**: 1

## Per-run table

| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |
|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|
| 0 | FAIL | False | True | 0.034452 | 7 | a844bf8d66915ef8 | scope_b:1, scope_b_tool:1 |
| 1 | FAIL | False | True | 0.035159 | 7 | 29085a8fd4e3e0ba | scope_b:1, scope_b_tool:1 |
| 2 | FAIL | False | True | 0.033255 | 7 | a4bae0aa34e5e3ba | scope_b:1, scope_b_tool:1 |
| 3 | FAIL | False | True | 0.032931 | 7 | d164dbfe52772770 | scope_b:1, scope_b_tool:1 |
| 4 | FAIL | False | True | 0.034011 | 7 | 05f774ff4d073d71 | scope_b:1, scope_b_tool:1 |

## Aggregate JSON

```json
{
  "runs": 5,
  "gates_pass_rate": "0/5",
  "tool_trace_gates_pass_rate": "0/5",
  "payload_gates_pass_rate": "5/5",
  "cost_usd": {
    "min": 0.032931,
    "max": 0.035159,
    "mean": 0.033962,
    "sum": 0.169808
  },
  "tool_trace_rows": {
    "min": 7,
    "max": 7,
    "mean": 7
  },
  "distinct_recap_write_sha256_16": [
    "05f774ff4d073d71",
    "29085a8fd4e3e0ba",
    "a4bae0aa34e5e3ba",
    "a844bf8d66915ef8",
    "d164dbfe52772770"
  ],
  "violation_counts_total": {
    "scope_b_tool": 5,
    "scope_b": 5
  },
  "distinct_tool_trace_signatures": [
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,write_corpus_file"
  ]
}
```
