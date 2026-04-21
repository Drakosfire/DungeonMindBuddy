<!-- benchmark_artifact: recap_ingest_multi_run_summary_v1 | iso_utc: 2026-04-21T01:48:27Z | scenario: session_recap_ingest_session_20 | model: gpt-5.4-mini | runs: 3 | gates_pass: 2/3 -->

# Scope-B recap-ingest cohort summary (N=3)

- **scenario**: `session_recap_ingest_session_20`
- **model**: `gpt-5.4-mini`
- **iso_utc**: `2026-04-21T01:48:27Z`
- **gates pass rate**: 2/3
- **tool_trace pass rate**: 2/3
- **payload pass rate**: 3/3
- **cost_usd**: min=0.046355 mean=0.05939 max=0.076249 sum=0.17817
- **tool_trace rows**: min=9 mean=9 max=9
- **distinct recap_write payloads (sha256_16)**: 2 (05dc457667a62cc1, d7bb5e0b1f219901)
- **distinct tool_trace signatures**: 1
- **write_corpus_file**: preview_rate=3/3 commit_rate=3/3 no_write_rate=0/3 phase_shapes={'preview→commit': 3}
- **commit_outcome** (BACKLOG §1.0): attempted=3/3 succeeded=2 refused=1 unknown=0 success_rate_when_attempted=2/3 refusal_kinds={'stale confirm_token (file or content changed since dry_run)': 1}
- **mechanical_fields**: build_recap_write_payload_called_rate=3/3 match_rate_overall=3/3 match_rate_when_called=3/3 match_rate_when_not_called=0/0 applicable=3/3 (n/a=0)

## Per-run table

| run | gates | tool_trace | payload | cost_usd | trace_rows | recap_write_sha16 | violations |
|-----|-------|------------|---------|---------:|-----------:|-------------------|------------|
| 0 | FAIL | False | True | 0.046355 | 9 | d7bb5e0b1f219901 | scope_b:1, scope_b_tool:1 |
| 1 | PASS | True | True | 0.055566 | 9 | 05dc457667a62cc1 | - |
| 2 | PASS | True | True | 0.076249 | 9 | 05dc457667a62cc1 | - |

## Aggregate JSON

```json
{
  "runs": 3,
  "gates_pass_rate": "2/3",
  "tool_trace_gates_pass_rate": "2/3",
  "payload_gates_pass_rate": "3/3",
  "cost_usd": {
    "min": 0.046355,
    "max": 0.076249,
    "mean": 0.05939,
    "sum": 0.17817
  },
  "tool_trace_rows": {
    "min": 9,
    "max": 9,
    "mean": 9
  },
  "distinct_recap_write_sha256_16": [
    "05dc457667a62cc1",
    "d7bb5e0b1f219901"
  ],
  "violation_counts_total": {
    "scope_b_tool": 1,
    "scope_b": 1
  },
  "distinct_tool_trace_signatures": [
    "get_recap_context,read_corpus_file,read_corpus_file,read_corpus_file,read_corpus_file,assemble_recap_draft,build_recap_write_payload,write_corpus_file,write_corpus_file"
  ],
  "write_corpus_file": {
    "preview_rate": "3/3",
    "commit_rate": "3/3",
    "no_write_rate": "0/3",
    "distinct_phase_shapes": {
      "preview→commit": 3
    },
    "soft_observations_total": 0
  },
  "commit_outcome": {
    "attempted_runs": 3,
    "succeeded_runs": 2,
    "refused_runs": 1,
    "unknown_runs": 0,
    "success_rate_when_attempted": "2/3",
    "refusal_rate_when_attempted": "1/3",
    "refusal_kinds": {
      "stale confirm_token (file or content changed since dry_run)": 1
    }
  },
  "mechanical_fields": {
    "build_recap_write_payload_called_rate": "3/3",
    "match_rate_overall": "3/3",
    "match_rate_when_called": "3/3",
    "match_rate_when_not_called": "0/0",
    "applicable_runs": 3,
    "not_applicable_runs": 0
  }
}
```
