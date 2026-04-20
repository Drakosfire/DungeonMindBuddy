<!-- benchmark_artifact: recap_ingest_multi_run_summary_v1 | iso_utc: 2026-04-18T20:00:27Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | runs: 5 | gates_pass: 1/5 -->

# Scope-B recap-ingest cohort summary (N=5)

- **scenario**: `session_recap_ingest_session_20`
- **model**: `gpt-5.4-mini`
- **iso_utc**: `2026-04-18T20:00:27Z`
- **gates pass rate**: 1/5
- **tool_trace pass rate**: 1/5
- **payload pass rate**: 5/5
- **cost_usd**: min=0.027485 mean=0.040072 max=0.053853 sum=0.20036
- **tool_trace rows**: min=6 mean=7 max=8
- **distinct recap_write payloads (sha256_16)**: 5 (1cc938b14cef18e3, 4cc2ef57a9c1b916, 55e88e766d4f05e8, 8269eec836a16160, bfefd017d54c5a3a)
- **distinct tool_trace signatures**: 3

## Per-run table

| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |
|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|
| 0 | PASS | True | True | 0.053853 | 7 | 4cc2ef57a9c1b916 | - |
| 1 | FAIL | False | True | 0.027485 | 6 | 1cc938b14cef18e3 | scope_b:1, scope_b_tool:1 |
| 2 | FAIL | False | True | 0.042274 | 8 | 55e88e766d4f05e8 | scope_b:1, scope_b_tool:1 |
| 3 | FAIL | False | True | 0.042288 | 7 | 8269eec836a16160 | scope_b:1, scope_b_tool:1 |
| 4 | FAIL | False | True | 0.03446 | 7 | bfefd017d54c5a3a | scope_b:1, scope_b_tool:1 |

## Aggregate JSON

```json
{
  "runs": 5,
  "gates_pass_rate": "1/5",
  "tool_trace_gates_pass_rate": "1/5",
  "payload_gates_pass_rate": "5/5",
  "cost_usd": {
    "min": 0.027485,
    "max": 0.053853,
    "mean": 0.040072,
    "sum": 0.20036
  },
  "tool_trace_rows": {
    "min": 6,
    "max": 8,
    "mean": 7
  },
  "distinct_recap_write_sha256_16": [
    "1cc938b14cef18e3",
    "4cc2ef57a9c1b916",
    "55e88e766d4f05e8",
    "8269eec836a16160",
    "bfefd017d54c5a3a"
  ],
  "violation_counts_total": {
    "scope_b_tool": 4,
    "scope_b": 4
  },
  "distinct_tool_trace_signatures": [
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft",
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,write_corpus_file",
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,write_corpus_file"
  ]
}
```
