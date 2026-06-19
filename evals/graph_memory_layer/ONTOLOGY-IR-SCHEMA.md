# Graph Memory Ontology IR Schema v0

## Purpose

Ontology IR Schema v0 defines the first schema-only internal representation for graph-memory records in the Ontology / Taxonomy ladder.

It exists to prove that graph bundles, graph nodes, graph edges, source references, provenance references, taxonomy references, and validation status can be represented safely before any graph materialization begins.

## Status

This is an experimental Rung 3 schema. It is not wired into production retrieval, live play, planner routing, or session-memory capture.

## What This Defines

- `TaxonomyRef` records that point at a taxonomy vocabulary and term.
- `SourceRef` records that preserve room for source anchoring.
- `ProvenanceRef` records that attach authority, evidence role, visibility, and source refs.
- `ValidationStatus` records for schema and future validation outcomes.
- `GraphNode` records for node-like graph memory entities.
- `GraphEdge` records for edge-like graph memory relationships.
- `GraphBundle` records as portable containers for nodes, edges, and validation status.

## What This Does Not Define

This schema does not materialize real graph data, extract entities, resolve aliases, infer relationships, define final ontology predicates, add graph retrieval, or change production behavior.

It is RDF-compatible in spirit because it uses stable IDs, source-grounded records, and controlled taxonomy references, but it does not export RDF, JSON-LD, OWL, or SPARQL.

## Relationship to Taxonomy Registry

The IR uses `TaxonomyRef` for controlled terms rather than duplicating the taxonomy registry as enum classes. This keeps the schema taxonomy-backed while leaving full cross-validation against `taxonomy_registry.json` for a later validation-rules rung.

## IR Records

- `TaxonomyRef`: a `{vocabulary, term}` pair.
- `SourceRef`: source identity, source kind, optional source layer, line range, reference, path, and anchor.
- `ProvenanceRef`: provenance identity, source refs, authority state, evidence role, optional visibility state, and notes.
- `ValidationStatus`: lifecycle/validation state, optional severity, and optional message.
- `GraphNode`: node ID, kind, label, aliases, scalar properties, provenance, lifecycle state, and visibility state.
- `GraphEdge`: edge ID, subject node ID, object node ID, predicate family, label, scalar properties, provenance, lifecycle state, and visibility state.
- `GraphBundle`: bundle metadata plus node, edge, and validation lists.

## Source Grounding

The schema includes provenance and source reference slots so future records can be grounded in source evidence. This PR does not enforce final source-grounding policy. Empty provenance remains allowed for the tiny diagnostic-only synthetic example.

## Synthetic Example Bundle

The example bundle is stored at:

`evals/graph_memory_layer/examples/ontology_ir_minimal_bundle.json`

It uses synthetic IDs and labels only. It is intended for schema validation and must not contain real campaign facts.

## Validation

Run the no-LLM validator with:

```bash
uv run python -m evals.graph_memory_layer.validate_ontology_ir
```

The validator loads the synthetic example bundle, checks schema version `0.1`, uniqueness of node and edge IDs, edge endpoint integrity, nonblank taxonomy refs, and scalar-only properties.

## Future Rungs

Future rungs may add validation rules that cross-check IR records against the taxonomy registry and source-grounding policies. Deterministic materialization, graph reports, graph retrieval, and RDF / JSON-LD / OWL / SPARQL export remain deferred.
