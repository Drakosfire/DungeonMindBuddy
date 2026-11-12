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
