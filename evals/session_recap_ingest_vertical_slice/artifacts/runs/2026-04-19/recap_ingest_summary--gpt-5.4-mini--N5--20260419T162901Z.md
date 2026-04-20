<!-- benchmark_artifact: recap_ingest_multi_run_summary_v1 | iso_utc: 2026-04-19T16:29:01Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | runs: 5 | gates_pass: 5/5 -->

# Scope-B recap-ingest cohort summary (N=5)

- **scenario**: `session_recap_ingest_session_20`
- **model**: `gpt-5.4-mini`
- **iso_utc**: `2026-04-19T16:29:01Z`
- **gates pass rate**: 5/5
- **tool_trace pass rate**: 5/5
- **payload pass rate**: 5/5
- **cost_usd**: min=0.055416 mean=0.056761 max=0.057918 sum=0.283804
- **tool_trace rows**: min=8 mean=8 max=8
- **distinct recap_write payloads (sha256_16)**: 5 (15a8eb244da2a63e, b1d7650910ac3a65, cd21d94c8a5b5e5e, da85bd1dbdbf56ce, ea724b0e15f41ce7)
- **distinct tool_trace signatures**: 1
- **write_corpus_file**: preview_rate=5/5 commit_rate=5/5 no_write_rate=0/5 phase_shapes={'preview→commit': 5}

## Per-run table

| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |
|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|
| 0 | PASS | True | True | 0.057016 | 8 | b1d7650910ac3a65 | - |
| 1 | PASS | True | True | 0.05555 | 8 | da85bd1dbdbf56ce | - |
| 2 | PASS | True | True | 0.055416 | 8 | ea724b0e15f41ce7 | - |
| 3 | PASS | True | True | 0.057904 | 8 | 15a8eb244da2a63e | - |
| 4 | PASS | True | True | 0.057918 | 8 | cd21d94c8a5b5e5e | - |

## Aggregate JSON

```json
{
  "runs": 5,
  "gates_pass_rate": "5/5",
  "tool_trace_gates_pass_rate": "5/5",
  "payload_gates_pass_rate": "5/5",
  "cost_usd": {
    "min": 0.055416,
    "max": 0.057918,
    "mean": 0.056761,
    "sum": 0.283804
  },
  "tool_trace_rows": {
    "min": 8,
    "max": 8,
    "mean": 8
  },
  "distinct_recap_write_sha256_16": [
    "15a8eb244da2a63e",
    "b1d7650910ac3a65",
    "cd21d94c8a5b5e5e",
    "da85bd1dbdbf56ce",
    "ea724b0e15f41ce7"
  ],
  "violation_counts_total": {},
  "distinct_tool_trace_signatures": [
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,write_corpus_file,write_corpus_file"
  ],
  "write_corpus_file": {
    "preview_rate": "5/5",
    "commit_rate": "5/5",
    "no_write_rate": "0/5",
    "distinct_phase_shapes": {
      "preview→commit": 5
    },
    "soft_observations_total": 0
  }
}
```
