# Graph Memory Ontology IR Validation Rules v0

## Purpose

These rules validate synthetic Graph Memory Ontology IR bundles before any future deterministic materialization step.

## Status

Rung 4 policy validation is no-LLM, deterministic, and limited to synthetic fixtures.

## What This Validates

- Taxonomy vocabulary and term references.
- Source-reference kind, layer, and line-range shape.
- Evidence/admissibility guardrails.
- Authority-state guardrails for promoted records.
- Visibility-state boundary conflicts.
- Lifecycle/promotion provenance requirements.
- Edge endpoint integrity within a bundle.

## What This Does Not Validate

- No real campaign graph data.
- No graph materialization.
- No corpus scanning.
- No session-memory scanning.
- No entity extraction, alias resolution, or relationship inference.
- No graph retrieval or production retrieval changes.
- No LLM calls.

## Rule Families

Rule families are implemented as structured `ValidationIssue` records with stable severities and codes.

## Taxonomy Reference Rules

Every `TaxonomyRef` must use a known vocabulary and a known term from `evals/graph_memory_layer/taxonomy_registry.json`. Node kinds must use `entity_kind`; edge predicate families must use `relationship_predicate_family`; lifecycle and visibility fields must use their matching vocabularies.

## Source Grounding Rules

`SourceRef.source_kind` must use `source_kind`, optional `source_layer` must use `source_layer`, and explicit line ranges must be positive and ordered. Source-evidence provenance must include at least one source ref.

## Evidence Role Rules

Diagnostic, routing, derived-summary, navigation-only, and not-admissible evidence roles are reported as informational `non_admissible_evidence_role` issues because they are not answer-supporting evidence.

## Authority Rules

Promoted records cannot depend on unsafe authority states such as GM prep, rumor, unreliable claims, candidates, LLM-inferred content, contradicted claims, or unknown authority.

## Visibility Rules

Player-visible records cannot depend on private GM, spoiler-sensitive, or internal diagnostic provenance.

## Lifecycle / Promotion Rules

Promoted nodes and edges require provenance and at least one source-grounded provenance ref. `ValidationStatus.state` is preserved as a schema field but is expected to reference `lifecycle_state` in this v0 policy.

## Synthetic Fixtures

- Valid fixture: `evals/graph_memory_layer/examples/ontology_ir_minimal_bundle.json`
- Invalid fixture: `evals/graph_memory_layer/examples/ontology_ir_invalid_bundle.json`

## Validation Commands

```bash
uv run python -m evals.graph_memory_layer.validate_ontology_ir_rules
```

The command loads only the taxonomy registry and synthetic Ontology IR fixtures.

## Future Rungs

These validation rules are prerequisites for deterministic materialization. Future rungs should not materialize graph records from real inputs until malformed or unsafe IR can be rejected first.
