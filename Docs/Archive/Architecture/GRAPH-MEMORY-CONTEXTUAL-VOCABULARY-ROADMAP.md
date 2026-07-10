# Graph Memory Contextual Vocabulary Roadmap

Status: active roadmap checklist  
Branch anchor: `experiment/ontology-taxonomy-ladder`

## Rule for future handoffs

Every PR handoff in this workstream must update this checklist.

Each update should mark completed items, add newly discovered follow-ups, and preserve deferred decisions. Do not silently remove unfinished work.

## Milestone 1 — Identity safety and observability

- [x] PR 0 — Narrow cross-class reconciliation safety policy.
- [x] Add blocked exact-label collision diagnostics.
- [x] Document comparator-vs-production dedup test naming.
- [x] Inventory benchmark fixture authority classes.

Completed notes:

- PR 1 added `evals/graph_memory_layer/FIXTURE-AUTHORITY-LEDGER.md` as the durable fixture authority map for vocabulary and graph-memory ablations.


Milestone 1 follow-ups:

- [ ] Convert selected routing/retrieval, session-event, or entity-resolution gold into candidate graph gold only through a dedicated reviewed conversion PR.
- [ ] Add candidate graph gold for C1 Session 13 if graph-memory ablations need that campaign/session surface.
- [ ] Add fixture authority rows automatically when future benchmark fixtures are introduced.

## Milestone 2 — Vocabulary substrate

- [x] Add `src/graph_memory/vocabulary/` contract skeleton.
- [x] Add storage-agnostic DTOs for vocabulary entries, observations, aliases, do-not-merge decisions, containment hints, and context packets.
- [x] Add deterministic vocabulary contract fixtures.
- [x] Add graph-ingest artifact seam for vocabulary artifacts.

Completed notes:

- PR 2 added the initial storage-agnostic vocabulary model contracts under `src/graph_memory/vocabulary/`.
- PR 2 added deterministic JSON round-trip unit tests for the vocabulary contracts; stable fixture files are deferred.
- PR 3 added deterministic hand-authored JSON fixtures under `evals/graph_memory_layer/examples/vocabulary_contract_fixtures/` and fixture-loading tests.
- PR 4 added `src/graph_memory/vocabulary/artifact.py`, a storage-neutral vocabulary artifact bundle loader and diagnostics seam backed by deterministic fixture tests.

Milestone 2 follow-ups:

- [ ] Add explicit JSON schema export for vocabulary contracts if downstream tooling needs schema files.
- [ ] Reconcile `SourceDomain` constants with `src/graph_memory/evidence/source_domain.py` if duplication becomes confusing.
- [ ] Use stable fixture JSON examples as references before packet renderer work.

Milestone 2 is now complete enough to begin ingestion vocabulary evidence work. Future PRs should keep lexical observation extraction behind explicit tests and should use the artifact seam rather than ad hoc JSON loading.

## Milestone 3 — Ingestion vocabulary evidence

- [x] Add lexical observation pass from source spans.
- [x] Emit vocabulary diagnostics without mutating corpus.
- [x] Compile separate world and campaign vocabulary seed artifacts.
- [x] Render scoped context vocabulary packets.

Completed notes:

- PR 5 added a deterministic in-memory lexical observation pass that emits `LexicalObservation` objects and JSON-serializable diagnostics without wiring into ingest or mutating corpus.
- PR 6 added a deterministic vocabulary seed compiler that groups lexical observations into separate world and campaign `VocabularyEntry` seed payloads without writing artifacts or mutating corpus.
- PR 7 added a deterministic scoped context vocabulary packet renderer that converts supplied world/campaign entries and review hints into `ContextVocabularyPacket` payloads without prompt injection or extraction changes.

Milestone 3 is now complete enough to begin extraction ablations. Future PRs should wire packet use only behind explicit ablation tests and diagnostics.

## Milestone 4 — Extraction ablations

- [x] Run post-extraction vocabulary diagnostics baseline.
- [x] Run edge-pass vocabulary packet ablation.
- [x] Run node-pass vocabulary packet ablation.
- [x] Compare endpoint binding, edge miss reasons, cross-class collisions, unsafe collision count, and combat encounter pickup.

Completed notes:

- PR 8 added `src/graph_memory/vocabulary/extraction_diagnostics.py`, a passive diagnostics layer for comparing existing extraction output to rendered vocabulary packets without changing extraction or injecting packets.
- PR 9 added `src/graph_memory/vocabulary/edge_context.py` and an explicit opt-in edge-pass vocabulary packet ablation seam with diagnostics while preserving default extraction behavior.
- PR 10 added an explicit opt-in node-pass vocabulary packet ablation path. It renders scoped packets into targeted node/category-pass context, exposes per-pass diagnostics, and preserves default extraction behavior.
- PR 11 added a deterministic vocabulary ablation comparison harness for precomputed baseline, edge-packet, node-packet, and combined extraction variants. It compares vocabulary pickup, type alignment, predicate pickup, edge-drop/miss reasons, cross-class collisions, unsafe collision counts, and combat encounter pickup without running LLMs or dogfood material.

Milestone 4 is now complete enough to begin dogfood runs. Future PRs should use the comparison harness on reviewed campaign material and must clearly separate synthetic harness tests from observed model behavior.

Milestone 4 follow-ups (captured 2026-06-30 after the first C2S23 recap dogfood):

- [x] First dogfood run (C2S23 Mireward recap, four variants). Surfaced that the
  recap bed cannot discriminate variants (structural pathologies ~0) and that a
  gold-derived packet makes recall circular. See
  `Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md`.
- [x] Lock objective + falsification plan in
  `Docs/Design/DESIGN-contextual-vocabulary-layer.md` (2026-06-30 addendum):
  structural > generalization > safety; packets source-derived not gold-derived;
  GO/kill thresholds.
- [ ] Author candidate graph gold for **C1 Session 1** recap
  (`Session 01 - Stonebridge and Glowkindle Rats`, `longmont-c1`) following the
  S22/S23 fixture contract. Cross-campaign generalization bed with built-in
  cross-class + containment probes.
- [ ] Author candidate graph gold for a **worldbuilding doc** (Stonebridge hub),
  with `world_reference` authority and evergreen relations — the world-authority
  axis the recap beds cannot test.
- [ ] Re-run the four-variant ablation on the expanded bed with a packet
  compiled only from corpus/registries (never gold), and score against the
  GO/kill criteria.

## Milestone 5 — Stable Global Node alignment

- [ ] Design vocabulary-to-Stable-Global-Node alignment candidates.
- [ ] Add merge-blocked and needs-review diagnostics.
- [ ] Connect vocabulary diagnostics to union-supergraph reconciliation.
- [ ] Defer review UI until artifact evidence proves the workflow.
