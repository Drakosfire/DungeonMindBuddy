<!-- benchmark_artifact: recap_ingest_multi_run_summary_v1 | iso_utc: 2026-04-20T03:06:44Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | runs: 5 | gates_pass: 1/5 -->

# Scope-B recap-ingest cohort summary (N=5)

- **scenario**: `session_recap_ingest_session_20`
- **model**: `gpt-5.4-mini`
- **iso_utc**: `2026-04-20T03:06:44Z`
- **gates pass rate**: 1/5
- **tool_trace pass rate**: 1/5
- **payload pass rate**: 5/5
- **cost_usd**: min=0.029591 mean=0.050242 max=0.081818 sum=0.251209
- **tool_trace rows**: min=8 mean=8.2 max=9
- **distinct recap_write payloads (sha256_16)**: 5 (44ab26722a763174, 80c8ebf936608b4c, 8650b99941264600, 8a105ce686d1a851, fcff2774e89f884f)
- **distinct tool_trace signatures**: 2
- **write_corpus_file**: preview_rate=1/5 commit_rate=5/5 no_write_rate=0/5 phase_shapes={'commit': 4, 'preview→commit': 1}
- **mechanical_fields**: build_recap_write_payload_called_rate=5/5 match_rate_overall=5/5 match_rate_when_called=5/5 match_rate_when_not_called=0/0 applicable=5/5 (n/a=0)

## Per-run table

| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |
|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|
| 0 | FAIL | False | True | 0.04061 | 8 | 8650b99941264600 | scope_b:1, scope_b_tool:1 |
| 1 | FAIL | False | True | 0.04564 | 8 | 8a105ce686d1a851 | scope_b:1, scope_b_tool:1 |
| 2 | FAIL | False | True | 0.029591 | 8 | 80c8ebf936608b4c | scope_b:1, scope_b_tool:1 |
| 3 | PASS | True | True | 0.081818 | 9 | 44ab26722a763174 | - |
| 4 | FAIL | False | True | 0.05355 | 8 | fcff2774e89f884f | scope_b:1, scope_b_tool:1 |

## Aggregate JSON

```json
{
  "runs": 5,
  "gates_pass_rate": "1/5",
  "tool_trace_gates_pass_rate": "1/5",
  "payload_gates_pass_rate": "5/5",
  "cost_usd": {
    "min": 0.029591,
    "max": 0.081818,
    "mean": 0.050242,
    "sum": 0.251209
  },
  "tool_trace_rows": {
    "min": 8,
    "max": 9,
    "mean": 8.2
  },
  "distinct_recap_write_sha256_16": [
    "44ab26722a763174",
    "80c8ebf936608b4c",
    "8650b99941264600",
    "8a105ce686d1a851",
    "fcff2774e89f884f"
  ],
  "violation_counts_total": {
    "scope_b_tool": 4,
    "scope_b": 4
  },
  "distinct_tool_trace_signatures": [
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,build_recap_write_payload,write_corpus_file",
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,build_recap_write_payload,write_corpus_file,write_corpus_file"
  ],
  "write_corpus_file": {
    "preview_rate": "1/5",
    "commit_rate": "5/5",
    "no_write_rate": "0/5",
    "distinct_phase_shapes": {
      "commit": 4,
      "preview→commit": 1
    },
    "soft_observations_total": 0
  },
  "mechanical_fields": {
    "build_recap_write_payload_called_rate": "5/5",
    "match_rate_overall": "5/5",
    "match_rate_when_called": "5/5",
    "match_rate_when_not_called": "0/0",
    "applicable_runs": 5,
    "not_applicable_runs": 0
  }
}
```
