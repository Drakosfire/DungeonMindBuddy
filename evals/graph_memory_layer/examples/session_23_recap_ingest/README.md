# Session 23 recap ingest fixture

This fixture bridges the saved raw Session 23 recap into the existing recap-ingest spine for Graph Memory. It mechanically assembles the expected normalized recap, records paragraph/source-line provenance, and validates source span seed refs.

It does not call an LLM, run the live planner, write corpus files, extract entities, infer relationships, produce a candidate graph, or produce a gold graph.

```bash
uv run python -m evals.graph_memory_layer.validate_session_23_recap_ingest_fixture
uv run python -m evals.graph_memory_layer.report_session_23_recap_ingest_fixture
```
