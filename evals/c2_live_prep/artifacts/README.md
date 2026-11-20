# C2 live-preparation artifacts

The `last_*` files are retained lab snapshots, not production readiness evidence.
Dated packets, gold inputs and Canvas test fixtures remain where their consumers
expect them. Run the lab only after checking its provider and campaign inputs;
see the [lab guide](../../README.md).

## Retired duplicate reports

Five dated reports and summaries duplicated the retained snapshots byte for byte.
Their exact historical contents remain available at the pinned links below.
The `last_*` copies are mutable: use the historical links for an exact replay.

| Removed dated copy | Retained copy | Exact historical content |
| --- | --- | --- |
| `runs/2026-05-30/c2s23_dogfood_planner_report.md` | [last_c2s23_dogfood_planner_report.md](last_c2s23_dogfood_planner_report.md) | [Pinned copy](https://github.com/Drakosfire/DungeonMindBuddy/blob/13ea571faffd9bdc3e909ade910be623f66e25db/evals/c2_live_prep/artifacts/runs/2026-05-30/c2s23_dogfood_planner_report.md) |
| `runs/2026-05-30/c2s23_dogfood_planner_summary.json` | [last_c2s23_dogfood_planner_summary.json](last_c2s23_dogfood_planner_summary.json) | [Pinned copy](https://github.com/Drakosfire/DungeonMindBuddy/blob/13ea571faffd9bdc3e909ade910be623f66e25db/evals/c2_live_prep/artifacts/runs/2026-05-30/c2s23_dogfood_planner_summary.json) |
| `runs/2026-05-30/c2s23_manifest_context_benchmark_summary.json` | [last_c2s23_manifest_context_benchmark_summary.json](last_c2s23_manifest_context_benchmark_summary.json) | [Pinned copy](https://github.com/Drakosfire/DungeonMindBuddy/blob/13ea571faffd9bdc3e909ade910be623f66e25db/evals/c2_live_prep/artifacts/runs/2026-05-30/c2s23_manifest_context_benchmark_summary.json) |
| `runs/2026-06-06/c2s23_manifest_query_context_summary.json` | [last_c2s23_manifest_query_context_summary.json](last_c2s23_manifest_query_context_summary.json) | [Pinned copy](https://github.com/Drakosfire/DungeonMindBuddy/blob/13ea571faffd9bdc3e909ade910be623f66e25db/evals/c2_live_prep/artifacts/runs/2026-06-06/c2s23_manifest_query_context_summary.json) |
| `runs/2026-05-30/c2s23_trace_context_packet_adapter_summary.json` | [last_c2s23_trace_context_packet_adapter_summary.json](last_c2s23_trace_context_packet_adapter_summary.json) | [Pinned copy](https://github.com/Drakosfire/DungeonMindBuddy/blob/13ea571faffd9bdc3e909ade910be623f66e25db/evals/c2_live_prep/artifacts/runs/2026-05-30/c2s23_trace_context_packet_adapter_summary.json) |

For a historical directory replay, recover the selected summary into owned scratch
before invoking the evaluator. From the repository root:

```bash
git show 13ea571faffd9bdc3e909ade910be623f66e25db:evals/c2_live_prep/artifacts/runs/2026-06-06/c2s23_manifest_query_context_summary.json > "$TMPDIR/c2-summary.json"
python -I -B evals/c2_live_prep/evaluate_c2s23_context_packets.py \
  --gold evals/c2_live_prep/benchmarks/c2s23_manifest_query_gold.json \
  --packet-dir evals/c2_live_prep/artifacts/runs/2026-06-06 \
  --packet-prefix c2s23_manifest_query_context_packet_ \
  --summary "$TMPDIR/c2-summary.json" \
  --output "$TMPDIR/c2-evaluation.json"
```

Use a task-owned `TMPDIR` allocated through the lab guide. The explicit summary
argument matters: the evaluator default points at today’s adapter run, not the
packet directory selected by `--packet-dir`. Other summaries can be recovered
with the same `git show <pinned-commit>:<removed-path>` form.

Runners still support generating dated reports and updating latest mirrors.
This retirement does not change their output policy or delete unique captures.
