# Mirathorn city world doc fixture

This fixture snapshots the evergreen worldbuilding doc **The City of Mirathorn** and validates source span seed refs for Graph Memory world-authority testing.

It does not call an LLM, run the live planner, write corpus files, extract entities, infer relationships, produce a candidate graph, or produce a gold graph.

```bash
uv run python -m evals.graph_memory_layer.validate_mirathorn_city_world_doc_fixture
uv run python -m evals.graph_memory_layer.report_mirathorn_city_world_doc_fixture
```
