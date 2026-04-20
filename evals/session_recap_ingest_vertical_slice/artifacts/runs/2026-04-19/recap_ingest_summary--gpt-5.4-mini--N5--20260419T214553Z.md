<!-- benchmark_artifact: recap_ingest_multi_run_summary_v1 | iso_utc: 2026-04-19T21:45:53Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | runs: 5 | gates_pass: 5/5 -->

# Scope-B recap-ingest cohort summary (N=5)

- **scenario**: `session_recap_ingest_session_20`
- **model**: `gpt-5.4-mini`
- **iso_utc**: `2026-04-19T21:45:53Z`
- **gates pass rate**: 5/5
- **tool_trace pass rate**: 5/5
- **payload pass rate**: 5/5
- **cost_usd**: min=0.062643 mean=0.064469 max=0.069755 sum=0.322345
- **tool_trace rows**: min=8 mean=8 max=8
- **distinct recap_write payloads (sha256_16)**: 5 (31e26de2eb295166, 40a22ad209b98c7b, 582ddcf8f3a694fc, 6afed3cab7dfccdc, d4cb1b3804aa37ed)
- **distinct tool_trace signatures**: 1
- **write_corpus_file**: preview_rate=5/5 commit_rate=5/5 no_write_rate=0/5 phase_shapes={'preview→commit': 5}

## Per-run table

| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |
|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|
| 0 | PASS | True | True | 0.063086 | 8 | 582ddcf8f3a694fc | - |
| 1 | PASS | True | True | 0.062643 | 8 | 6afed3cab7dfccdc | - |
| 2 | PASS | True | True | 0.069755 | 8 | d4cb1b3804aa37ed | - |
| 3 | PASS | True | True | 0.063371 | 8 | 31e26de2eb295166 | - |
| 4 | PASS | True | True | 0.06349 | 8 | 40a22ad209b98c7b | - |

## Aggregate JSON

```json
{
  "runs": 5,
  "gates_pass_rate": "5/5",
  "tool_trace_gates_pass_rate": "5/5",
  "payload_gates_pass_rate": "5/5",
  "cost_usd": {
    "min": 0.062643,
    "max": 0.069755,
    "mean": 0.064469,
    "sum": 0.322345
  },
  "tool_trace_rows": {
    "min": 8,
    "max": 8,
    "mean": 8
  },
  "distinct_recap_write_sha256_16": [
    "31e26de2eb295166",
    "40a22ad209b98c7b",
    "582ddcf8f3a694fc",
    "6afed3cab7dfccdc",
    "d4cb1b3804aa37ed"
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
