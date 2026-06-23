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


Validate the real-structure materialization gate with the no-LLM gate validator:

```bash
uv run python -m evals.graph_memory_layer.validate_real_structure_gate
```

This validates the gate manifest for the first future real-structure materializer. It does not materialize real data, read session-memory JSONL, scan corpus files, parse Markdown/Tiptap output, call an LLM, or change retrieval behavior. The gate admits exactly one future source family and keeps real materialization deferred to a later PR under validation and reporting constraints.

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

## Session-Memory Sentence-Unit Materializer

The session-memory sentence-unit materializer validates the first gated real-structure source family:

```bash
uv run python -m evals.graph_memory_layer.validate_session_memory_materializer
uv run python -m evals.graph_memory_layer.report_session_memory_materializer
```

By default these commands read only the tiny synthetic fixture at
`evals/graph_memory_layer/examples/session_memory_sentence_units_minimal.jsonl`.
The validator checks real-structure gate compliance, emits a diagnostic
candidate graph bundle, validates it, and reports the output. The report CLI
also includes session-memory route/source-unit coverage counts.

This rung does not scan corpus files, read manifests, parse Markdown or Tiptap
output, infer entities or aliases, promote graph facts, call LLMs, or change
production retrieval behavior. Optional input must be supplied as an explicit
JSONL path.


## Projection-Readiness Reporting

Projection-readiness reporting measures whether materialized session-memory source-unit records have enough source grounding, provenance, lifecycle, canon, evidence, authority, and visibility metadata to become projection-safe surface payloads in a future adapter. It does not implement adapters, touch `/plan`, or change runtime behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_projection_readiness_report
uv run python -m evals.graph_memory_layer.report_projection_readiness
```

The report is diagnostic only: missing fields are reported instead of invented, display summaries are not evidence, and full source text/raw ingestion internals are not printed.

## Recap-Ingestion Source-Family Gate

Validate the recap-ingestion source-family gate with the no-runtime gate validator:

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_family_gate
```

Validates the recap-ingestion source-family gate. This gate decides which current recap-ingestion outputs may later be materialized as source artifacts, anchors, and units. It does not materialize those artifacts, implement adapters, touch `/plan`, scan corpus files, or change runtime behavior.

## Recap-Ingestion Source Artifact Fixture

Validate the synthetic recap-ingestion source artifact fixture with the no-runtime fixture validator:

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_fixture
```

Validates the synthetic recap-ingestion source artifact fixture. This fixture proves the gate-admitted recap-ingestion artifact families can be represented as `SourceArtifact -> SourceAnchor -> SourceUnit` without reading real recap outputs, implementing a materializer, touching `/plan`, or changing runtime behavior.

## Recap-Ingestion Source Artifact Materializer Gate

Validate the recap-ingestion source artifact materializer gate with the no-runtime gate validator:

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_gate
```

Validates the recap-ingestion source artifact materializer gate. This gate decides whether a future PR may implement a real explicit-input materializer for gate-admitted recap-ingestion artifacts. It does not implement the materializer, add adapters, touch `/plan`, scan corpus files, or change runtime behavior.

## Recap-Ingestion Source Artifact Materializer

Validate and report the explicit-input recap-ingestion source artifact materializer:

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer
uv run python -m evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer
```

Validates and reports the explicit-input recap-ingestion source artifact materializer. This materializer reads only explicitly supplied synthetic/eval recap-ingestion artifact inputs and emits diagnostic `SourceArtifact -> SourceAnchor -> SourceUnit` structures. It does not discover files, scan corpus files, implement adapters, touch `/plan`, or change runtime behavior.

## Surface Vocabulary Boundary

Validate the surface vocabulary boundary manifest with the no-runtime boundary validator:

```bash
uv run python -m evals.graph_memory_layer.validate_surface_vocabulary_boundary
```

This validates which terms belong to the shared semantic envelope, which terms are ontology-owned, which terms are surface-owned, which terms are contested, and which collapses are forbidden before graph memory is consumed by DungeonMindBuddy surfaces. It does not implement adapters, does not touch `/plan`, and preserves shared source/provenance/evidence/lifecycle semantics while allowing surface-owned vocabulary such as chips, projections, drawers, and tool workflows.

## Projection-Safe Source Unit Fixture

Validate the eval-only projection-safe source unit fixture with the no-runtime fixture validator:

```bash
uv run python -m evals.graph_memory_layer.validate_projection_safe_source_unit
```

Validates the eval-only projection-safe source unit fixture. This proves a graph/source-unit-shaped record can be represented as a surface-safe payload carrying the shared semantic envelope. It does not implement adapters, touch `/plan`, or change runtime behavior.

## Recap-Ingestion Source Artifact Materializer Diagnostics Report v0

Validates and renders a richer diagnostic report over explicit-input recap-ingestion source artifact materializer output. This report summarizes artifact coverage, semantic states, structural coverage, and known gaps. It does not implement projection-readiness, adapters, `/plan`, Agent Interaction, or runtime behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_report
uv run python -m evals.graph_memory_layer.report_recap_ingestion_source_artifact_materializer_diagnostics
```


## Recap-Ingestion Projection-Readiness

Validates and renders projection-readiness diagnostics over explicit-input recap-ingestion materializer output. This report may intentionally return a blocked readiness status when required source-ref/provenance structure is missing. It does not implement projection adapters, `/plan`, Agent Interaction, retrieval, corpus scanning, or runtime behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_projection_readiness
uv run python -m evals.graph_memory_layer.report_recap_ingestion_projection_readiness
```

## Recap-Ingestion Source Ref / Provenance Linkage Hardening

The recap-ingestion source artifact materializer now emits stable `source_ref_id` values in each source_ref and links each provenance record back to the same source_ref_id. This hardening moves the source-ref/provenance projection-readiness checks from blocked to ready while remaining diagnostic-only.

Validation:

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_source_artifact_materializer_report
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_projection_readiness
```

## Recap-Ingestion Projection Payload Fixture

Validates and reports a diagnostic projection payload fixture over hardened recap-ingestion source artifact materializer output. This fixture proves a bounded surface-safe shape for future adapter design. It is not a production adapter, `/plan` payload, Agent Interaction payload, retrieval result, or runtime UI payload.

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_projection_payload_fixture
uv run python -m evals.graph_memory_layer.report_recap_ingestion_projection_payload_fixture
```

## Recap-Ingestion Explicit Real-Artifact Dogfood Fixture

Validates and reports the first explicit real-artifact dogfood fixture for recap-ingestion Graph Memory. The dogfood bundle is loaded from a manifest of explicit relative file paths only. It exercises the materializer, materializer report, projection-readiness, and projection-payload chain outside runtime. It does not scan directories, scan corpus files, mutate corpus files, connect `/plan`, connect Agent Interaction, perform retrieval, or change production behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_recap_ingestion_explicit_real_artifact_dogfood
uv run python -m evals.graph_memory_layer.report_recap_ingestion_explicit_real_artifact_dogfood
```
## Source Span Evidence Resolver Fixture

The source span evidence resolver fixture validates that source refs can resolve to bounded snippets or structured fields suitable for future graph preview evidence drawers. It does not perform extraction, graph retrieval, `/plan` integration, Agent Interaction integration, corpus scanning, corpus mutation, or production behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_source_span_resolver_fixture
uv run python -m evals.graph_memory_layer.report_source_span_resolver_fixture
```

## Candidate Graph Preview IR v0

The candidate graph preview IR fixture validates a preview-only object model for recap-derived graph candidates. Candidate nodes, edges, session beats, proposed writes, ignored items, and deferred items carry evidence refs compatible with the source span evidence resolver. This is an IR and fixture contract only; it does not perform extraction, approval, graph writes, query execution, `/plan` integration, Agent Interaction integration, corpus scanning, corpus mutation, or production behavior.

```bash
uv run python -m evals.graph_memory_layer.validate_candidate_graph_preview_ir
uv run python -m evals.graph_memory_layer.report_candidate_graph_preview_ir
```
