# Lab and evaluation

This directory holds experiments, regression fixtures, and evaluation evidence.
Start with the suite that owns the question you are testing.

| Question | Entry point |
| --- | --- |
| Did an extraction or graph change preserve the expected evidence? | [Graph memory fixtures and baselines](graph_memory_layer/README.md) |
| Did session-event extraction preserve chronology? | [Session-event extraction suite](session_events_extraction_vertical_slice/README.md) |
| How does the canon layering baseline score? | [Canon layering runner](canon_layering/run_benchmarks.py) |

Use the locked environment from the [root quickstart](../README.md).
The canon baseline runs with `uv run python evals/canon_layering/run_benchmarks.py`.
Read the suite's inputs before running it. Some runners use paid providers or
private campaign sources. Record the source revision, inputs, runner options,
and result location. Keep generated runs in the task's output location and
promote only evidence or fixtures with a named consumer.

### Offline retrieval oracle

Pass `--oracle gold-oracle.json --citation-readback reopened.jsonl` to the
ordinary benchmark workflow's `report` mode with the retained capture
manifest. The report embeds `retrieval_analytics` keyed by case and item.
Capture mode rejects both options.

The `buddy_retrieval_oracle_v1` file maps case IDs under `cases` to
`question` and `items`. Each item has an `id` and a nonempty `witnesses`
list with `session`, `line`, `text`, and `source_sha256` per witness.
All witnesses for an item must appear with matching source readback.
Readback JSONL uses `question` (case ID), `handle`, and `matches` with
`ref`, `event`, `body_sha256`, `excerpt_sha256`, `start`, and `end`. The report matches them against Buddy’s authorized selected reads.

The report counts packet and excerpt tokens, verified unique Gold lines, and
exact repeated source spans. Gold line counts include surrounding prose.
Graph restatements and paraphrases are outside the exact overlap measure.
Erroneous context is unknown without semantic assessment.
