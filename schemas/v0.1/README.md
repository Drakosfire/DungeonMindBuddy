# DungeonBuddy JSON Schemas v0.1

This bundle turns the Phase 1 narrative architecture into enforceable JSON contracts.

Included schemas:
- `common.schema.json` — shared enums, temporal fields, and reusable definitions.
- `evidence_unit.schema.json`
- `mention.schema.json`
- `entity.schema.json`
- `corpus_entity_profile.schema.json` — citation-backed narrative audit row (complements lean `Entity` identity).
- `fact.schema.json`
- `event.schema.json`
- `conflict.schema.json`
- `canon_decision.schema.json`

Included examples:
- one minimal example instance for each schema, using Lysandra-flavored placeholder data.
- `examples/corpus_entity_profile.bonogo_exemplar.json` — full-depth narrative audit (see `Docs/Plans/HANDOFF-entity-definition-audit-top-N.md`).

## Design notes

These schemas intentionally split identity from state:
- `Entity` holds identity and merge status.
- `CorpusEntityProfile` (see `corpus_entity_profile.schema.json`) holds **human- or agent-curated** prose about an entity with **corpus file citations**, narrative-layer splits (dossier vs observed play vs GM prep), optional relationships/terminal beats, and **store reliability** caveats. It is not extracted mechanically from chunks; it is an audit artifact for interpretability and QA. Query/filter on `citations[].layer_tags`, `store_reliability.caveat_kind`, `evidence_sufficiency`, and `cohort`.
- `Fact` holds attribute claims, truth state, authority, and validity windows.
- `Event` holds scene-level incidents and candidate state changes.
- `Conflict` preserves unresolved contradiction rather than flattening it.
- `CanonDecision` records manual intervention so canon stays rebuildable.

## Important constraints in v0.1

- IDs are opaque strings. They are stable references, not semantic keys.
- Session time is modeled as integer session numbers for facts, with optional string `session_id` on events.
- Facts are Phase 1 NPC-centric and use a controlled attribute set.
- `Entity` is intentionally lean. Typed character state belongs in `Fact`, not on the entity object.
- `CANON` is allowed as a stored truth state, but the safer default is still to derive canon through the reducer and recorded decisions.
- Lifecycle metadata uses `record_status` to avoid colliding with domain-specific status fields such as `conflict_status`.

## Known limitations

- Query request/response contracts are not included yet.
- Planning validation request/response contracts are not included yet.
- Attribute enums are Phase 1 scoped and intentionally NPC-heavy, with initial event-state support (`event_outcome`, `event_progression`).
- Location / faction / item typed profiles are deferred.
- Some workflow invariants still live outside schema and must be enforced in code, especially:
  - reducer ordering
  - no silent overwrite
  - provisional entity quarantine rules
  - event immutability semantics

## Suggested next document

`DungeonBuddy Reducer + Validation Contracts v0.1`

That doc should define:
- deterministic canon reducer input/output
- planning validation input/output
- conflict report output
- entity profile query output
