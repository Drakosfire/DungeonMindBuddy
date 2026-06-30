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

- [ ] Run post-extraction vocabulary diagnostics baseline.
- [ ] Run edge-pass vocabulary packet ablation.
- [ ] Run node-pass vocabulary packet ablation.
- [ ] Compare endpoint binding, edge miss reasons, cross-class collisions, unsafe collision count, and combat encounter pickup.

## Milestone 5 — Stable Global Node alignment

- [ ] Design vocabulary-to-Stable-Global-Node alignment candidates.
- [ ] Add merge-blocked and needs-review diagnostics.
- [ ] Connect vocabulary diagnostics to union-supergraph reconciliation.
- [ ] Defer review UI until artifact evidence proves the workflow.
