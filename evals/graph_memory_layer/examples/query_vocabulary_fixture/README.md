# Query Vocabulary Fixture

Static graph memory query vocabulary fixture for Session 23. It defines safe, unsafe, and deferred query intents, answer shapes, evidence requirements, and Agent Interaction readiness boundaries.

This fixture does not execute graph retrieval, execute graph queries, call an LLM, write graph memory, approve writes, connect `/plan`, connect Agent Interaction, promote facts, promote canon, or change runtime behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_query_vocabulary_fixture
uv run python -m evals.graph_memory_layer.report_query_vocabulary_fixture
```
