# Graph Memory Ontology IR Validation Rules v0

## Purpose

These rules validate synthetic Graph Memory Ontology IR bundles before any future materialization or extraction rung can build graph records from source artifacts.

## Status

Rung 4: Validation Before Extraction. The rules are deterministic, standard-library-only, and no-LLM.

## What This Validates

- Taxonomy vocabulary and term references.
- Source-reference taxonomy shape and line-range policy.
- Evidence-role admissibility guardrails.
- Authority-state promotion guardrails.
- Visibility boundary conflicts.
- Lifecycle and promoted-record source-grounding constraints.
- Bundle edge endpoint integrity.

## What This Does Not Validate

- Real campaign graph data.
- Corpus files, Markdown, Tiptap output, or session-memory JSONL.
- Entity extraction, alias resolution, or relationship inference.
- RDF, JSON-LD, OWL, or SPARQL export.
- Production retrieval behavior.

## Rule Families

The implementation lives in `src/graph_memory/validation_rules.py` and returns structured issues with stable severities and issue codes. `error` and `fatal` issues make a bundle invalid; `info` and `warning` issues can be reported without failing the bundle.

## Taxonomy Reference Rules

Every `TaxonomyRef` must reference a known vocabulary and term from `evals/graph_memory_layer/taxonomy_registry.json`. Node kinds must use `entity_kind`, edge predicate families must use `relationship_predicate_family`, lifecycle refs must use `lifecycle_state`, visibility refs must use `visibility_state`, and validation severity refs must use `validation_severity`.

## Source Grounding Rules

Source refs must use `source_kind`; optional source layers must use `source_layer`. When both source line bounds are present, both must be positive integers and `line_end` must be greater than or equal to `line_start`.

## Evidence Role Rules

`source_evidence` provenance must include at least one source ref. Diagnostic-only, routing-only, derived-summary, navigation-only, and not-admissible roles are reported as `info` because they are not answer-supporting evidence.

## Authority Rules

Promoted records cannot rely on unsafe authority states such as `gm_prep`, `rumor`, `unreliable_claim`, `candidate`, `llm_inferred`, `contradicted`, or `unknown`.

## Visibility Rules

A player-visible record cannot include private-GM, spoiler-sensitive, or internal-diagnostic provenance visibility.

## Lifecycle / Promotion Rules

Promoted nodes and edges require provenance, and at least one provenance ref must include source refs. The current IR validation status `state` field is preserved as a lifecycle-state reference for v0.

## Synthetic Fixtures

- Valid fixture: `evals/graph_memory_layer/examples/ontology_ir_minimal_bundle.json`
- Invalid fixture: `evals/graph_memory_layer/examples/ontology_ir_invalid_bundle.json`

The invalid fixture is synthetic and intentionally includes policy violations. It is not campaign data.

## Validation Commands

```bash
uv run python -m evals.graph_memory_layer.validate_ontology_ir_rules
```

This command loads the taxonomy registry, validates the synthetic valid bundle, validates the synthetic invalid bundle, and exits successfully only when the valid bundle passes and the invalid bundle is rejected.

## Future Rungs

These rules are prerequisites for deterministic materialization. Future rungs may materialize graph records only after validation policy can reject malformed or unsafe IR bundles first.
