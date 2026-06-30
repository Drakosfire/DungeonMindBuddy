# Design — Contextual Vocabulary Layer

Date: 2026-06-29
Status: proposed architecture direction
Workstream: Graph Memory / Contextual Vocabulary / Stable Global Identity
Branch: `experiment/ontology-taxonomy-ladder`

## Purpose

This document defines the architecture target for an evolving contextual vocabulary layer in DungeonMindBuddy graph memory.

The project direction is a campaign/worldbuilding union supergraph. Session recap projections are scoped lenses over stable global identity, not separate session-local graphs. The vocabulary layer exists so recap ingestion can reuse, question, and extend campaign/world vocabulary instead of asking each extraction run to rediscover identity from scratch.

This is a design document only. It does not authorize implementation by itself.

## 2026-06-30 — Objective lock, falsification plan, and test-bed expansion

This section is an addendum written after the first end-to-end dogfood of the
Milestone 4 ablation harness (C2S23 Mireward recap, `gpt-5.4-mini`, four
variants). It supersedes any implicit objective that the dogfood runner encoded.
The body of this document below remains the architecture reference; this section
locks *what counts as success* and *what would falsify the idea*.

### Objective lock

The contextual vocabulary layer exists to improve **cross-session identity
stability and relational structure** in the union supergraph. Its value must be
proven by **structural**, **generalization**, and **safety** signals, in that
priority order:

1. **Structural** (primary): fewer duplicate cross-class proper-noun nodes,
   fewer ambiguous/missing-endpoint edge drops, fewer wrong-type/object
   bindings, more reliable containment (`located_in`) and `governs`→place edges.
   These are *behaviors the model cannot fake by echoing a supplied string*.
2. **Generalization**: node/edge recall and precision against **full
   hand-authored gold**, including entities the packet did **not** list.
3. **Safety**: zero hallucinated foreign entities (a name with no textual hook
   in the source must not appear just because the packet carried it), and zero
   unsafe merges across do-not-merge pairs.

Single-source recall over **packet-supplied names** is demoted to a secondary
diagnostic. It is structurally circular (the model is rewarded for repeating
what the prompt handed it) and is therefore not a success criterion on its own.

### Hard rule: packets are source-derived, never gold-derived

The C2S23 dogfood built its vocabulary packet from **gold label forms**. That is
the root cause of the circular recall signal and it quietly teaches the metric
the answer key (the exact anti-pattern called out in `Backlog.md` and the
parent handoff §3.3). For every experiment under this objective:

- The packet MUST be compiled only from corpus sources, NPC/PC registries, and
  prior graph observations — never from the gold graph being scored against.
- The gold graph is the **scoring key only**. It is never an input to packet
  construction, extraction, or the comparator alias table.

### Lessons recorded from the C2S23 dogfood (so we do not repeat them)

- **Recall over supplied names is circular.** All four variants recognized an
  identical set (`Edge, Mireward Reach, North gate, Orik Tane`) and missed an
  identical set (`Lysandra, Lysandro, First meat wave`); recognition moved by
  zero. Exact-label scoring is blind to near-variant labels
  (`Father Lysandro`, `the first wave`) — which is precisely the divergence the
  layer is meant to fix, so the instrument was blind to its own target.
- **The recap is a weak test bed.** On 13 recap paragraphs, baseline
  `cross_class_collision_count`, `conflicting_kind_collision_count`, and
  `unsafe_cross_class_blocked_count` were all ~0. The pathologies the layer
  targets barely manifest, so variants cannot be discriminated. The design
  doc's own collision evidence came from full S22/S23 **stored category runs**,
  not a recap.
- **The absent-set was mis-constructed.** It mixed truly-foreign proper nouns
  (zero textual hook: `Maelthor`, `The Shepherd`, `Under-Hymn Brood`) with a
  contextually-inferable governance term (`Mireward Council`). The model did
  **not** echo any of the three foreign names despite them being in the packet
  — the dangerous failure mode did not occur — and the one leak was the
  plausible-from-context term. Contamination probes must use **zero-textual-hook
  foreign nouns only**; plausible inferences belong in a separate lane.

### Falsification plan (go / no-go)

The layer earns continued investment only if, on the **expanded test bed**
(≥2 sessions across both campaigns + 1 worldbuilding doc), a packet variant
clears **all** of these against its own baseline:

- **GO-1 (structural):** `cross_class_collision_count` and
  `unsafe_collision_count` strictly decrease on at least one test bed where the
  baseline exhibits the pathology, with no increase on the others.
- **GO-2 (binding):** `dropped_edges_missing_endpoints_count` +
  `ambiguous_endpoint_drop_count` strictly decrease.
- **GO-3 (no regression):** `node_recall` and `edge_recall` are ≥ baseline
  (within run-to-run noise; require ≥3 trials for the LLM passes).
- **GO-4 (safety):** absent-set (zero-textual-hook) contamination = 0 and
  do-not-merge violations = 0.
- **GO-5 (generalization):** at least one structural or recall gain appears on
  an entity the packet did **not** list. A gain visible only as packet-name
  echo does not count.

Kill / redesign criteria:

- If structural metrics are **flat across variants** on a bed where the baseline
  shows the pathology, the packet **placement or contents** are wrong — redesign
  the packet, not the metric.
- If recall **regresses** with the packet, the packet is over-constraining
  (forcing unsupported entities/types) — tighten authority gating.
- If the only movement is packet-name recall, the experiment is measuring
  circularity — discard the result.

### Test-bed expansion (decided 2026-06-30)

Two new hand-authored `candidate_graph_gold` fixtures, authored from source
evidence with anchor spans, following the existing S22/S23 fixture contract
(`session_NN_recap_ingest` + `session_NN_candidate_graph_gold` + loader +
`_GOLD_SESSIONS` registration + tests):

1. **Campaign 1, Session 1 recap** — `Session 01 - Stonebridge and Glowkindle
   Rats`. Chosen over C1S13 (the roadmap's earlier candidate) because it is the
   earliest, smallest, cleanest recap, sits in a **different campaign**
   (`longmont-c1`) the packet has not memorized, and carries built-in
   cross-class and containment probes: `Wizard's Tower Brewing Co` (place vs
   organization), `Stone Bridge` the town vs the literal stone bridge landmark,
   `The River's Edge Pub` contained in Stone Bridge, the brewing **gnomes** as a
   collective, and an opening combat encounter (giant rats). This is a clean
   generalization probe with a fresh proper-noun set.
2. **A worldbuilding doc** — a Stonebridge setting hub (e.g. the Stonebridge
   town/`Grishna` world hub). This adds the **world-authority axis** the recap
   beds cannot test: evergreen setting facts with `authority = world_reference`
   and `temporal_scope = evergreen`, **no session-occurrence claims**. Gold
   nodes carry `world_reference` authority (not `canon_play`), `corpus_ref`
   resolves to the hub itself, and edges are evergreen relations
   (`located_in`, `runs`/`operates`, `part_of`) rather than played-canon events.
   This exercises the design's world-vs-campaign vocabulary split directly.

These two beds let us run the same four-variant ablation where the failure modes
actually appear and where packet contents (compiled from C1 registries + the
Stonebridge hub, never from gold) can be judged against the GO/kill criteria
above.

## Architecture commitments

The vocabulary layer must be provenance-grounded, evolving during ingestion, storage-agnostic, inspectable, safe against silent canon promotion, usable by prompts and deterministic code, scoped across separate world and campaign vocabulary stores, and oriented toward Stable Global Node alignment.

It must not become a hardcoded benchmark alias table, a comparator cheat sheet, an opaque canon source, a static config file, an eval-only helper, or a replacement for the union supergraph.

The durable package home should be `src/graph_memory/vocabulary/`, as a sibling to `src/graph_memory/union_supergraph/`.

## Current graph ingest workflow

Current runtime path:

```text
raw recap or existing recap
→ apps/live_control_server/routes/recap_ingest.py
→ stage/apply/normalize through recap ingest pipeline as needed
→ apps/live_control_server/services/recap_graph_preview_ingest.py
→ evals/graph_memory_layer/graph_preview_runner.py
→ source span bundle + provenance index
→ category-decomposed extraction when LLM extraction is enabled
→ candidate graph JSON
→ candidate validation report
→ preview union supergraph materialization
→ projection payload for /plan
```

Current category extraction path:

```text
source_span_index
→ source packet rows
→ party context anchors
→ actor pass
→ location pass
→ collective pass
→ object pass
→ thread pass
→ deterministic consolidation
→ beat pass
→ deterministic consolidation
→ edge pass with consolidated node summaries injected
→ deterministic consolidation
→ evidence repair/sanitize
→ candidate graph envelope
```

Current consolidation already performs node normalization, party-anchor insertion, exact-label cross-class reconciliation, dropped-edge diagnostics, party-collective insertion, edge deduplication, predicate validation capture, and no-evidence sanitization.

The vocabulary layer should plug into this ingestion flow, not live only as an external prompt appendix.

## Failure modes addressed

The category extractor improves coverage by splitting extraction into passes, but the same proper noun can appear in multiple node classes. This creates duplicate identities such as a place also appearing as an organization. Exact-label cross-class reconciliation is a useful emergency pressure valve, but it is too broad to be the long-term identity strategy.

The system also needs to preserve distinctions between places, authority bodies, organizations, factions, people, and encounter aggregators. A leadership body may be associated with a settlement without replacing that settlement as the endpoint for location and governance edges.

Candidate aliases are currently disconnected strings. A displaced group might be labeled with several related phrases across recaps and extraction runs. Hardcoding those phrases into Python helps one benchmark but is the wrong architecture. The system needs evidence-bearing alias candidates with confidence, risk flags, and review status.

Shared labels can also create unsafe false merges. An eponymous person and faction may be related without being the same entity. The desired behavior is to recognize the relationship, preserve the distinction, and make the do-not-auto-merge reason inspectable.

Combat encounter aggregators need first-class ontology support. This design canonizes `combat_encounter` as a node kind. It should not be flattened into generic `event`, generic `encounter`, creature, or faction. Future kinds such as `social_encounter` can be modeled separately.

## Target lifecycle

```text
source artifacts
→ source artifact records
→ source spans / provenance refs
→ lexical observation extraction
→ world vocabulary lookup
→ campaign vocabulary lookup
→ contextual vocabulary packet rendering
→ candidate graph extraction
→ vocabulary-aware consolidation diagnostics
→ alias / do-not-merge / missing-context candidate updates
→ candidate graph fragment
→ identity resolution toward Stable Global Nodes
→ union supergraph materialization
→ projection lens / graph preview
```

The design should support ablations around placement. Candidate placements include pre-node extraction, pre-edge extraction, post-extraction consolidation, two-pass feedback, and full ingestion-first lexical observation. The preferred eventual shape is ingestion-first, but the first experiments should keep placement explicit and measurable.

## Separate world and campaign vocabulary

World vocabulary and campaign vocabulary should be stored separately.

World vocabulary covers setting-wide concepts: places, regions, settlements, institutions, factions, recurring world threats, statblock-derived creature concepts, and evergreen worldbuilding references.

Campaign vocabulary covers campaign-local memory: PCs, NPCs as used in this campaign, session-established facts, recap-derived aliases, local groups, combat encounters, unresolved candidate identities, prior extracted observations, and campaign-specific Stable Global Node candidates.

Prompt-time packets may append both world and campaign sections, but storage and authority must remain separate. Campaign recap ingestion should not mutate the world vocabulary store unless a future explicit world-vocabulary update path exists.

## Stable Global Node relationship

A vocabulary entry is not always a global node.

```text
VocabularyEntry = language/identity concept with labels, aliases, evidence, status, and hints.
StableGlobalNode = graph identity that projections, edges, and global node views should attach to.
```

A vocabulary entry may have no global node yet, may point to one resolved global node, or may list candidate global node IDs. The vocabulary layer should help candidate graph fragments resolve toward stable global nodes, but it should not replace the union-supergraph identity layer.

## Conceptual domain model

The model is storage-agnostic. Near-term artifacts may be JSON, but the concepts should also fit a future persistent graph-memory store.

### SourceArtifact

Represents a source document or generated artifact that can provide evidence.

Key fields: `source_artifact_id`, `source_domain`, `scope`, `campaign_id`, `world_id`, `session_id`, `uri`, `content_hash`, `document_class`, `subject_class`, `authority`, `indexed_at`.

Initial domains: `recap`, `worldbuilding`, `npc_note`, `location_note`, `faction_note`, `item_note`, `statblock`, `session_memory`, `manual_seed`, `future_artifact`, `prior_graph_observation`.

### LexicalObservation

A raw mention from a source. It is not a stable entity.

Key fields: `observation_id`, `source_artifact_id`, `source_span_ref_id`, `surface_text`, `normalized_text`, `observed_kind_hint`, `context_window_hash`, `evidence_refs`, `extraction_method`, `confidence`.

### VocabularyEntry

A stable-ish language concept that may or may not resolve to a Stable Global Node.

Key fields: `vocab_id`, `canonical_label`, `entity_kind`, `entity_kind_confidence`, `scope`, `campaign_id`, `world_id`, `global_node_id`, `candidate_global_node_ids`, `aliases`, `candidate_aliases`, `negative_aliases`, `do_not_merge_with`, `related_entries`, `source_refs`, `evidence_refs`, `first_seen_session`, `last_seen_session`, `status`, `authority`, `notes`.

Initial entity kinds: `actor`, `place`, `collective`, `object`, `thread`, `phenomenon`, `combat_encounter`, `social_encounter`, `session_beat`, `unknown`.

### AliasCandidate

A possible same-entity relationship between two labels or entries.

Key fields: `alias_candidate_id`, `left_surface`, `right_surface`, `left_vocab_id`, `right_vocab_id`, `candidate_cluster_id`, `evidence_refs`, `supporting_sources`, `contradicting_sources`, `confidence`, `status`, `reason`, `risk_flags`.

Risk flags should include: `cross_type`, `eponymous_group`, `place_vs_polity`, `person_vs_faction`, `single_shared_token`, `source_span_only`, `gold_only_support`, `conflicting_kind_hint`, `ambiguous_place_or_leadership_body`, `combat_encounter_vs_creature_group`.

### DoNotMergeDecision

A generated warning or reviewed decision that two labels or entries should not auto-merge.

Key fields: `decision_id`, `left_vocab_id`, `right_vocab_id`, `status`, `source`, `reason`, `evidence_refs`, `created_by`, `reviewed_by`.

Generated warnings are not reviewed decisions. The model must preserve this distinction.

### ContainmentHint

A scoped hint that a location or sublocation belongs within a larger place.

Key fields: `hint_id`, `child_label`, `parent_label`, `child_vocab_id`, `parent_vocab_id`, `relationship_type`, `confidence`, `status`, `evidence_refs`, `authority`.

### ContextVocabularyPacket

A lossy prompt-time slice, not the full store.

Key fields: `packet_id`, `scope`, `world_entry_refs`, `campaign_entry_refs`, `known_names`, `alias_hints`, `candidate_alias_hints`, `do_not_merge_hints`, `containment_hints`, `type_hints`, `predicate_hints`, `combat_encounter_hints`, `budget_policy`, `generated_at`.

Prompt packets must be compact. The packet guides extraction but does not prove session facts. Candidate graph nodes and edges still require source-span evidence.

## Status and authority

Initial statuses: `observed`, `candidate`, `accepted`, `rejected`, `needs_review`, `do_not_merge`, `deprecated`, `superseded`.

Initial authority labels: `world_reference`, `canon_play`, `campaign_dossier`, `statblock_reference`, `derived_memory`, `prior_graph_observation`, `inferred_from_recap`, `llm_candidate`, `gm_reviewed`, `manual_seed`.

Authority rules:

- `world_reference` grounds setting vocabulary but not session occurrence.
- `canon_play` grounds what happened in-session when sourced to recaps.
- `derived_memory` and `prior_graph_observation` are useful but not source-of-truth by themselves.
- `llm_candidate` must never promote canon or accepted aliases by itself.
- `gm_reviewed` is the strongest local approval signal and must still retain evidence/source refs.

## Ingestion placement ablations

Baseline:

```text
source spans
→ category node passes
→ consolidation
→ edge pass
→ consolidation/sanitize
```

Variant A — pre-node packet:

```text
source spans
→ load world vocabulary
→ load campaign vocabulary
→ render scoped packet
→ category node passes with packet
→ consolidation
→ edge pass with packet + nodes
```

Variant B — pre-edge packet:

```text
source spans
→ category node passes without packet
→ consolidation
→ render packet using source + existing vocab + observed nodes
→ edge pass with packet
```

Variant C — post-extraction vocabulary consolidation:

```text
source spans
→ category extraction baseline
→ candidate graph
→ lexical observation + alias/do-not-merge diagnostics
→ campaign vocabulary candidate update artifact
```

Variant D — two-pass feedback:

```text
baseline extraction
→ vocabulary diagnostics
→ packet render
→ selective re-run of affected node/edge passes
```

Recommended first experimental path: start with C and B together. Produce diagnostics from a baseline run, render a packet, inject only into the edge pass and deterministic binding diagnostics, then measure endpoint-binding quality. Test pre-node injection only after packet quality is stable.

## Deterministic use

The vocabulary layer should be consumed by deterministic code as well as prompts.

Endpoint binding should classify results such as `bound_exact_label`, `bound_accepted_alias`, `bound_candidate_alias`, `ambiguous_candidate_alias`, `blocked_by_do_not_merge`, `place_vs_leadership_conflict`, `combat_encounter_missing`, and `unbound_missing_vocabulary`.

Node consolidation should use vocabulary to reduce false duplicate nodes while avoiding unsafe merges. The current broad exact-label cross-class reconciliation should be narrowed in a separate safety PR before vocabulary work depends on it. The safe first target is place-to-collective/polity exact-label collisions when no do-not-merge or person-vs-faction risk applies.

Comparator diagnostics should not silently use hand-coded aliases as answer keys. It may consume vocabulary to explain misses and suspicious matches, but reports must distinguish actual extraction improvement from alias-aware scoring.

Union-supergraph reconciliation should use vocabulary inputs to resolve candidate fragments toward Stable Global Nodes and to explain merge-blocked or needs-review outcomes.

## Success metrics

Success is better graph memory quality, not a single Session 23 score bump. Metrics must explain what they measure and why they matter.

Vocabulary compilation metrics:

- `source_artifact_count_by_domain`: proves source scope.
- `lexical_observation_count`: proves ingestion is collecting mention signals.
- `vocab_entry_count_by_scope`: confirms world/campaign separation.
- `candidate_alias_count`: measures alias discovery without claiming acceptance.
- `do_not_merge_warning_count`: measures visible ambiguity.
- `entries_with_evidence_ratio`: guards against opaque lookup drift.
- `authority_distribution`: shows reliance on high/low authority sources.

Prompt packet metrics:

- `packet_entry_count`: controls prompt budget.
- `packet_relevance_hit_rate`: detects noisy packets.
- `packet_candidate_alias_count`: measures alias assistance pressure.
- `packet_do_not_merge_count`: confirms ambiguity exposure.
- `packet_world_campaign_balance`: prevents world lore from overwhelming recap ingest.

Extraction quality metrics:

- `cross_class_collision_count`: targets duplicate identity failure.
- `unsafe_collision_count`: targets false-merge risk.
- `node_kind_accuracy_proxy`: measures typing alignment with known vocabulary.
- `combat_encounter_pickup_count`: measures encounter aggregator modeling.
- `dropped_edges_missing_endpoints_count`: measures endpoint-binding health.
- `ambiguous_endpoint_drop_count`: measures duplicate/alias ambiguity.
- `candidate_edge_count_by_predicate_family`: measures relation coverage.
- `located_in_edge_pickup`: targets containment failures.

Benchmark metrics:

- `node_recall` and `node_precision_proxy`.
- `edge_recall` and `edge_precision_proxy`.
- `edge_miss_reason_distribution`.
- `suspicious_match_count`.
- `alias_helped_match_count`.
- `do_not_merge_prevented_false_match_count`.

GM-facing metrics:

- `clickable_mentions_resolved_ratio`.
- `stable_global_node_resolution_ratio`.
- `needs_review_surface_count`.
- `explainable_failure_count`.

## Benchmark discovery and fixture authority

Known graph-memory fixtures from current anchors:

- `evals/graph_memory_layer/examples/session_23_candidate_graph_gold/` — Session 23 candidate graph gold.
- `evals/graph_memory_layer/examples/session_24_manual_projection_dogfood/` — Session 24 projection dogfood, not candidate extraction gold.
- `evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/` — Session 22 category pipeline validation.
- `evals/graph_memory_layer/examples/session_22_recap_ingest/` — Session 22 mechanical recap ingest fixture.
- `evals/graph_memory_layer/examples/session_23_recap_ingest/` — Session 23 mechanical recap ingest fixture.

Additional benchmark discovery should search for earlier gold surfaces, especially likely Campaign 1 Sessions 1, 2, 3, and 13. Do not assume they are candidate-graph gold until fixture shape and authority are inspected.

Fixture authority classes should include `candidate_graph_gold`, `projection_gold`, `routing_gold`, `retrieval_gold`, `session_event_gold`, `classifier_gold`, `mechanical_ingest_fixture`, and `static_review_fixture`.

Only `candidate_graph_gold` should be used as direct graph extraction gold. Other fixtures can still be useful for vocabulary coverage, routing context, or user-story validation.

## Roadmap

### Phase 0 — safety cleanup before vocabulary dependency

Separate PR, not bundled with vocabulary implementation:

- Narrow `reconcile_cross_class_label_collisions` to the proven place-to-collective/polity case.
- Add tests that actor/person-to-collective/faction eponymous pairs do not auto-merge.
- Preserve diagnostics for blocked exact-label collisions.

### Phase 1 — current ingestion and fixture inventory

- Map runtime graph ingest workflow with exact files.
- Inventory graph benchmark fixtures and authority classes.
- Identify where graph run artifacts should record vocabulary artifacts.
- Identify current candidate graph node kinds and type-class gaps, including `combat_encounter`.

### Phase 2 — vocabulary contract design

- Define DTOs for source artifacts, lexical observations, vocabulary entries, alias candidates, do-not-merge decisions, containment hints, and context packets.
- Separate world and campaign vocabulary stores.
- Define artifact schemas for near-term JSON experiments.
- Define prompt packet rendering contract.

### Phase 3 — ingestion-stage lexical observation spike

```text
source_span_index
→ lexical observations
→ candidate vocabulary diagnostics
→ contextual packet artifact
```

Do not mutate corpus, promote canon, or merge global nodes.

### Phase 4 — edge-pass vocabulary ablation

Compare baseline category extraction against category extraction with a vocabulary packet only on the edge pass. Measure endpoint binding, edge miss reasons, and alias diagnostics.

### Phase 5 — node-pass vocabulary ablation

Run category extraction with vocabulary packet on node passes. Measure cross-class collisions, node kind proxy accuracy, unsafe merge risk, and downstream edge effects.

### Phase 6 — Stable Global Node alignment design

Define how vocabulary entries are assigned to global nodes, how new global-node candidates are proposed, how merge-blocked diagnostics work, and what the future review UI/store needs.

## Future PR handoff standards

When a PR handoff is requested, it should include exact file edit plans because coding agents receive no outside context.

Each handoff should include: mission, non-goals, required reading, exact files to edit, exact files not to edit, implementation steps, DTO/schema details, artifact paths, test plan, acceptance criteria, known risks, and one bounded repo hygiene task.

The hygiene task must be small and related, such as archiving stale generated eval output, updating fixture status labels, renaming ambiguous fixture directories, documenting generated artifacts, or cleaning duplicated design pointers.

## Non-goals

This design does not authorize implementation code, corpus mutation, canon promotion, hardcoded benchmark aliases, treating Session 24 projection gold as candidate graph gold, merging world and campaign vocabulary stores, replacing Stable Global Nodes with vocabulary entries, changing production retrieval, approved memory writes, review UI work, or silent comparator semantics changes.

## Best current hypothesis

The next high-leverage architecture step is an ingestion-stage contextual vocabulary layer that records lexical observations, candidate aliases, do-not-merge warnings, containment hints, type hints, and Stable Global Node alignment candidates from evidence-bearing sources.

The layer should first prove value through diagnostics and ablations, not permanent prompt rewrites. The strongest near-term proof is improved edge quality and endpoint binding across multiple sessions without hardcoded corpus-specific alias tables.
