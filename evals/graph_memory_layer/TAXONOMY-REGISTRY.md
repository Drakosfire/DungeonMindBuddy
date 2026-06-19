# Graph Memory Taxonomy Registry v0

## Purpose

The taxonomy registry defines controlled vocabulary for the Graph Memory / Ontology / Taxonomy ladder before any ontology IR, graph materialization, extraction, or retrieval behavior exists.

This PR defines controlled vocabulary only.

## Status

- Version: `0.1`
- Status: `taxonomy_registry_v0`
- Workstream: `ontology_taxonomy_ladder`
- Machine-readable registry: `evals/graph_memory_layer/taxonomy_registry.json`
- Validator: `uv run python -m evals.graph_memory_layer.validate_taxonomy_registry`

## What This Defines

This registry defines vocabulary IDs, labels, descriptions, terms, usage guidance, examples, and allowed graph record states for future graph-memory work.

Vocabulary areas include source kinds, source layers, entity kinds, route kinds, evidence roles, authority states, visibility states, truth states, lifecycle states, relationship predicate families, planning lanes, retrieval lanes, graph candidate states, promotion states, and validation severities.

## What This Does Not Define

This PR does not define graph nodes, graph edges, graph bundles, ontology IR, graph schemas, materialization, extraction, alias resolution, LLM behavior, production retrieval behavior, RDF, JSON-LD, OWL, SHACL, or SPARQL export.

## Vocabulary Table

| Vocabulary | Purpose |
| --- | --- |
| `source_kind` | Classifies broad kinds of source artifacts. |
| `source_layer` | Classifies the source-processing layer for an artifact or derived record. |
| `entity_kind` | Classifies entity-like concepts without defining graph node classes. |
| `route_kind` | Classifies route and hub structures used by current and future retrieval surfaces. |
| `evidence_role` | Classifies how a record may be used as evidence or routing context. |
| `authority_state` | Distinguishes kinds of truth, authority, and source support. |
| `visibility_state` | Classifies whether content is player-visible, GM-only, spoiler-sensitive, or internal. |
| `truth_state` | Classifies claim truth semantics without adjudicating ontology records. |
| `lifecycle_state` | Classifies lifecycle for graph candidates and facts before any ontology schema exists. |
| `relationship_predicate_family` | Defines broad relationship families before exact ontology predicates or graph edges. |
| `planning_lane` | Classifies planner-facing context lanes for future graph-memory reporting. |
| `retrieval_lane` | Classifies retrieval and admission lanes for future shadow graph experiments. |
| `graph_candidate_state` | Classifies proposed graph records before validation or promotion. |
| `promotion_state` | Classifies readiness for promotion from experiment output toward durable use. |
| `validation_severity` | Classifies validation outcomes emitted by no-LLM validators or future graph checks. |

## Vocabulary Details

The JSON registry is authoritative for term IDs and usage guidance. Term fields are consistent across vocabularies: `id`, `label`, `description`, `allowed_usage`, `disallowed_usage`, `examples`, `allowed_graph_record_states`, and `admissibility_notes`.

`allowed_graph_record_states` means the controlled term may appear on records in those lifecycle states; it does **not** mean a claim is admissible as source evidence, player-visible, or safe to promote without source, authority, visibility, and validation checks.

Important safety distinctions are represented as first-class terms:

- `source_evidence` may support answer claims when source-grounded.
- `diagnostic_only`, `derived_summary`, and `routing_hint` are not admissible as source evidence.
- `played_truth`, `canonical_recap`, `gm_prep`, `rumor`, `candidate`, `llm_inferred`, `human_confirmed`, and `contradicted` preserve authority boundaries.
- `player_visible`, `private_gm`, `spoiler_sensitive`, and `internal_diagnostic` preserve visibility boundaries.
- `candidate`, `unknown`, `conflicted`, `needs_review`, and `missing_source` keep uncertainty explicit.

## Relationship to Baseline Cases

The baseline cases freeze graph-native failure families such as roster identity, clean control, location hierarchy, alias bridges, final beats, breadcrumb queries, unresolved hooks, hub over-attraction, authority boundaries, and citation grounding.

The taxonomy registry gives those future cases stable names for source layers, evidence roles, authority states, visibility states, relationship families, retrieval lanes, and lifecycle states. It does not evaluate or materialize those cases yet.

## Relationship to Future Ontology IR

Future ontology IR may reference these vocabulary values when it defines graph records, node-like objects, edge-like objects, provenance, validation status, and promotion state.

This registry intentionally comes first so the ladder has vocabulary before object and relationship definitions. Exact graph node schemas, graph edge schemas, and predicate names are deferred to later PRs.

## Next Step

The next ladder step is `graph-memory: add ontology IR schema v0` after this taxonomy registry is reviewed and merged.
