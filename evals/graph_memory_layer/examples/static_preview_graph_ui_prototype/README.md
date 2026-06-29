# Static Preview Graph UI Prototype v0

This directory contains a deterministic static HTML prototype for the Graph Memory Preview Graph UX using checked-in Session 23 fixture/report data only.

- Manifest: `static_preview_graph_ui_prototype_manifest.json`
- Model: `session_23_preview_graph_ui_prototype_model.json`
- HTML: `session_23_preview_graph_ui_prototype.html`

This is not production UI. It does not call an LLM, execute extraction, write graph memory, persist approval state, execute graph queries, connect `/plan`, connect Agent Interaction, scan or mutate corpus files, promote facts, promote canon, or change runtime behavior.

Validate with:

```bash
uv run python -m evals.graph_memory_layer.validate_static_preview_graph_ui_prototype
```
