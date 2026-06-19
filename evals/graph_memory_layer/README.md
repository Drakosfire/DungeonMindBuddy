# Graph Memory Layer Evals

## Purpose

This directory is the evaluation scaffold for the Graph Memory Layer experiment. It gives the experiment a dedicated, non-production place for smoke checks, future baseline captures, and later shadow artifacts.

## Current Phase

PR 1 is baseline/fork tracking only. It establishes branch safety documentation, baseline artifact directories, and a no-LLM smoke runner.

The smoke runner must not require an OpenAI key, environment variables, network access, production retrieval imports, or graph-memory implementation modules.

## Non-Goals for PR 1

- No graph schemas.
- No graph retrieval.
- No RDF export.
- No LLM extraction.
- No production retrieval behavior changes.
- No benchmark output regeneration or reinterpretation.

## Expected Commands

Run the scaffold-only/default smoke check during bootstrap work:

```bash
uv run python -m evals.graph_memory_layer.run_smoke
```

Validate the frozen baseline case manifest with the no-LLM baseline validator:

```bash
uv run python -m evals.graph_memory_layer.validate_baseline_cases
```

This validation is standard-library only and safe for scaffold/baseline work.

Validate the controlled vocabulary registry with the no-LLM taxonomy validator:

```bash
uv run python -m evals.graph_memory_layer.validate_taxonomy_registry
```

This taxonomy validation is standard-library only. It validates the controlled vocabulary registry, semantic guardrail fields, and allowed graph-record-state values. It does not validate graph records, graph nodes, graph edges, ontology IR, materialization, extraction, or retrieval behavior yet.

Validate the synthetic Ontology IR example bundle with the no-LLM ontology validator:

```bash
uv run python -m evals.graph_memory_layer.validate_ontology_ir
```

This ontology IR validation uses the standard library plus the local `src.graph_memory.ontology_ir` package only. It validates a synthetic example bundle only and does not materialize campaign data, scan corpus files, call an LLM, extract entities, infer relationships, or change retrieval behavior.

Validate synthetic Ontology IR bundles against taxonomy and source-grounding guardrails with the no-LLM rule validator:

```bash
uv run python -m evals.graph_memory_layer.validate_ontology_ir_rules
```

This rule validation uses only synthetic bundles. It validates taxonomy references, evidence/admissibility policy, authority boundaries, visibility boundaries, lifecycle/promotion constraints, and source-grounding expectations. It does not call an LLM, materialize graph data, scan real data, or change retrieval behavior.

Validate the deterministic, fixture-only materializer with the no-LLM materializer validator:

```bash
uv run python -m evals.graph_memory_layer.validate_materializer
```

This materializer validation converts only the explicit synthetic fixture into an Ontology IR `GraphBundle`. It is deterministic, uses no LLM, performs no corpus scanning, and makes no retrieval changes.

Render the synthetic-only materializer report with the no-LLM report CLI:

```bash
uv run python -m evals.graph_memory_layer.report_materializer
```

Validate the report path with the no-LLM report validator:

```bash
uv run python -m evals.graph_memory_layer.validate_materializer_report
```

The materializer report is report-first and synthetic-only. It summarizes the deterministic fixture output, taxonomy usage, lifecycle and visibility states, evidence roles, provenance refs, source refs, validation issues, and per-record rows. It does not broaden materialization, scan real data, call an LLM, or change retrieval behavior. Informational diagnostic-only validation issues are expected and visible; the report path fails only on `error` or `fatal` validation issues.

Once fork enforcement is active for later stacked PRs, run strict branch-policy validation:

```bash
uv run python -m evals.graph_memory_layer.run_smoke --check-git-context
```

Strict git-context mode accepts the experiment root branch (`experiment/graph-memory-layer`) and any stacked branch that starts with `graph-exp/`. For a handoff that must be validated against one exact branch, add `--expected-branch`:

```bash
uv run python -m evals.graph_memory_layer.run_smoke --check-git-context --expected-branch graph-exp/01-freeze-baseline-reports
```

## Future PRs

Later phases may add graph materialization, graph reports, graph-shadow retrieval, entity candidates, relationship candidates, taxonomy governance, and live retrieval shadow mode.

Any LLM-backed experiment must be added behind explicit CLI flags in a later PR.
