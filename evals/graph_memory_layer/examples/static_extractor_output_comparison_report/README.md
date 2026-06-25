# Static Extractor Output Comparison Report Fixture

This directory contains the deterministic Session 23 static extractor output comparison report fixture.

It consumes the eval-only extractor harness candidate-vs-gold comparison and writes reviewer-facing JSON and Markdown artifacts. It does not call an LLM, execute a live extractor, write graph memory, approve writes, execute graph queries, scan or mutate corpus files, connect `/plan`, connect Agent Interaction, promote facts, promote canon, or change runtime behavior.

Validate with:

```bash
uv run python -m evals.graph_memory_layer.validate_static_extractor_output_comparison_report
```

Print the Markdown report with:

```bash
uv run python -m evals.graph_memory_layer.report_static_extractor_output_comparison_report
```
