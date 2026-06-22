# Graph Memory Surface Vocabulary Boundary v0

## Purpose

This report defines the vocabulary boundary between Graph Memory and DungeonMindBuddy surfaces before any adapter, graph-backed `/plan` path, shadow retrieval, or production integration is built.

The boundary answers which concepts must be shared globally, which terms remain ontology-owned, which terms remain surface-owned, which terms are contested, and which semantic collapses are forbidden because they erase provenance, lifecycle, evidence, authority, or visibility distinctions.

## Decision

DungeonMindBuddy should not force a single shared vocabulary across graph memory and UI surfaces. It should force a shared semantic envelope while preserving surface-owned interaction vocabulary.

In short: **Share semantics, not surface labels.**

Graph Memory owns truth/provenance/lifecycle semantics. Surfaces own interaction vocabulary. Projection boundaries are allowed only where explicit, validated, and source-safe.

## Why Not Force One Shared Vocabulary?

Arguments for forcing one shared vocabulary:

- It prevents lifecycle drift by making every consumer use the same names for generated, candidate, promoted, diagnostic-only, and played states.
- It prevents evidence-role drift by keeping source evidence, display summaries, diagnostics, and generated text distinct everywhere.
- It prevents source-backed claims from being confused with display summaries.
- It makes privacy and visibility rules consistent across planning, live control, ingestion, recap, and tool surfaces.
- It improves validation and reporting across surfaces because reports can search one vocabulary.
- It reduces translation ambiguity when graph-backed retrieval is eventually promoted beyond diagnostic/shadow use.

Arguments against forcing one shared vocabulary:

- UI vocabulary is product-facing and task-shaped; `npc_chip`, `drawer_section`, and `tool_workflow` are real interaction concepts.
- Surface terms like `statblock`, `roll-table`, and `location` are not pure ontology classes.
- one UI term may map to multiple ontology concepts depending on provenance and lifecycle.
- One ontology concept may project differently across `/plan`, live-control drawers, ingestion results, recap tools, and combat workflows.
- Forcing ontology names into UI can make surfaces brittle and awkward.
- Premature sharing can hide unresolved lifecycle and writeback distinctions, especially when an action such as "accepted" might be combat-local rather than corpus-promoted.

Conclusion: **Share semantics, not surface labels.**

## Shared Semantic Envelope

Every graph-derived surface payload must carry or be able to derive this envelope:

- `source_artifact`
- `source_anchor`
- `source_unit`
- `source_ref`
- `provenance`
- `evidence_role`
- `authority_state`
- `visibility_state`
- `lifecycle_state`
- `validation_issue`
- `source_backed_claim`
- `display_summary`
- `diagnostic_record`

Rules:

- `display_summary` may be shared as a field name, but it is never evidence.
- `source_backed_claim` requires source refs and evidence role.
- `diagnostic_record` cannot be shown as canon.
- Future surface-facing graph payloads must preserve source/provenance/evidence/lifecycle/authority/visibility semantics even if the UI renders them as chips, cards, drawers, or workflow results.

## Ontology-Owned Vocabulary

Graph Memory owns these terms, though surfaces may display them as labels, badges, colors, filters, or affordances:

- `source_kind`
- `source_layer`
- `entity_kind`
- `relationship_predicate_family`
- `route_kind`
- `evidence_role`
- `authority_state`
- `visibility_state`
- `lifecycle_state`
- `validation_severity`
- `graph_candidate_state`
- `promotion_state`

Surfaces may not redefine these terms. Taxonomy changes should happen in the ontology ladder, not in UI code.

## Surface-Owned Vocabulary

Surfaces own these product and interaction concepts:

- `npc_chip`
- `location_chip`
- `statblock_projection`
- `roll_table_projection`
- `planning_canvas`
- `drawer_section`
- `tool_workflow`
- `edit_unlock`
- `combat_local_accept`
- `recap_ingestion_result`
- `statblock_generation_result`
- `reference_chip`
- `projection_card`

These terms should not be forced to become ontology classes. They must carry the shared semantic envelope when backed by graph-derived content.

## Contested Terms

### `statblock`

Why ambiguous: `statblock` can mean source content, generated output, combat-local acceptance, promoted corpus content, indexed content, or a visible UI card.

Graph-memory concern: source artifact, generated candidate, combat-local state, promoted corpus record, indexed content.

Surface concern: visible monster/NPC/combat card/tool output.

Boundary rule: `statblock` remains a surface projection kind. Graph memory must carry lifecycle and provenance fields that distinguish generated draft, accepted-to-combat, promoted-to-corpus, indexed, and source-backed statblock records.

Detection: reports flag statblock-like payloads that lack lifecycle state, source refs, evidence role, or authority state.

### `summary`

Why ambiguous: `summary` can mean a display convenience, generated digest, navigation teaser, or text incorrectly treated as evidence.

Graph-memory meaning: a derived display/navigation aid that is not evidence.

Surface meaning: short prose shown in a drawer, chip preview, or planning card.

Boundary rule: summaries may be displayed but must not be treated as source evidence.

Detection: reports flag summary text used with `evidence_role=source_evidence` without source refs.

### `route`

Why ambiguous: `route` can refer to graph relationship paths, taxonomy/navigation groupings, corpus/source locations, UI routing, or reference resolution.

Graph-memory meaning: a taxonomy/relationship/navigation concept that may connect entities, source units, or corpus locations.

Surface meaning: a UI navigation/ref resolution concept.

Boundary rule: do not collapse graph route semantics and UI navigation routes; an adapter may map between them explicitly later.

Detection: reports flag route payloads that lack source-family, relation type, or provenance.

### `source`

Boundary rule: surface source labels must be backed by `source_ref`, `source_anchor`, and provenance when graph-derived.

Detection: flag source labels with no source anchor or source ref.

### `anchor`

Boundary rule: UI anchors may point at source anchors, but UI scroll targets must not redefine source-anchor stability.

Detection: flag graph-derived payloads with UI-only anchors and no `source_anchor`.

### `canon`

Boundary rule: canon labels require authority and lifecycle states that permit canon display.

Detection: flag canon display without `authority_state`, `lifecycle_state`, and provenance.

### `draft`

Boundary rule: draft UI state must not imply graph candidate promotion or demotion.

Detection: flag draft records with promoted/canonical authority unless provenance explains the transition.

### `accepted`

Boundary rule: accepted must state scope: combat-local, session-local, corpus-promoted, or diagnostic.

Detection: flag accepted payloads missing lifecycle state and promotion state or scope.

### `generated`

Boundary rule: generated content remains authority-limited until source, provenance, and lifecycle permit promotion.

Detection: flag generated claims shown as source-backed evidence without source refs.

### `promotion`

Boundary rule: promotion remains ontology-owned and auditable; UI actions may request promotion but must not redefine it.

Detection: flag promotion-like actions without `promotion_state` and provenance.

### `index`

Boundary rule: indexes are navigation/retrieval aids, not evidence; indexed content still needs source refs and evidence roles.

Detection: flag indexed summaries treated as source evidence.

## Forbidden Collapses

- `summary_as_source_evidence`: display summaries must not be treated as source evidence.
- `lifecycle_as_known_fact`: generated candidates, rumors, prep, diagnostic-only records, and played truth must not collapse into a generic known-fact state.
- `ui_ref_type_as_taxonomy_owner`: surface ref types such as npc, location, statblock, and roll-table must not become ontology ownership.
- `surface_projection_as_corpus_truth`: projection payloads must not be treated as promoted corpus truth unless lifecycle and provenance say so.

## Surface-Facing Payload Requirements

Every future graph-derived surface-facing payload should include at least:

- `adapter_key`
- `ref_id`
- `label`
- `source_anchor`
- `evidence_role`
- `authority_state`
- `visibility_state`
- `lifecycle_state`
- `provenance`

These fields are an envelope, not a UI vocabulary replacement. A `projection_card` or `npc_chip` may still use surface-owned names while carrying the envelope.

## Examples

A graph-derived NPC reference may render as an `npc_chip`, a `reference_chip`, or a `projection_card`. Those labels belong to the surface. The chip still needs source anchors, provenance, evidence role, authority state, visibility state, and lifecycle state if it is backed by graph-derived content.

A graph-derived statblock preview may display a `display_summary`, but that summary cannot become source evidence. A source-backed statblock claim must carry source refs and evidence role.

A combat workflow may mark a statblock as `combat_local_accept`; that is not the same as corpus promotion. The payload must keep lifecycle and authority scope explicit.

## Detection and Validation

The diagnostic manifest is:

`evals/graph_memory_layer/surface_vocabulary_boundary.json`

The no-runtime validator is:

`uv run python -m evals.graph_memory_layer.validate_surface_vocabulary_boundary`

The validator checks the boundary decision, shared semantic envelope, ontology-owned vocabulary, surface-owned vocabulary, contested terms, forbidden collapses, and future payload required fields.

## Deferred Work

This report does not implement adapters, projection adapters, graph-backed `/plan`, graph traversal, shadow retrieval, materializers, entity extraction, alias resolution, relationship inference, corpus mutation, prompt changes, or LLM calls.

Future work should add an eval-only projection-safe source-unit fixture that proves an existing graph materialized source unit can become a surface-safe payload carrying the shared semantic envelope without touching runtime surfaces.
