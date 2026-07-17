# Plan — Hermes × World Graph interaction rebuild

**Status:** PROPOSED; STOP FOR OPERATOR REVIEW BEFORE IMPLEMENTATION  
**PR356 disposition:** supersede with replacement PR; do not merge as foundation.

## Sequencing principle

Each slice must create one independently useful contract or product outcome. Do not rebuild all layers in one PR. Dogfood after every user-visible slice.

## Slice 0 — forensic observability and Tripod graph migration

**Outcome:** the current journey becomes causally inspectable, and graph-native source anchors are honestly readable where authority exists.

**Deliver:**

- non-secret raw-result/event/classifier forensic capture behind dogfood flag;
- active Eldyrwild revision audit command/report;
- rebuild/republish migration for legacy contribution source-payload digests;
- direct deterministic Tripod retrieval/source-read fixture and command;
- no change to product authority semantics yet.

**Dogfood gate:** capture the exact first runtime failure branch for the current architecture.

**Why first:** this closes the forensic uncertainty and prevents the rebuild from hiding an unrelated runtime integration defect.

## Slice 1 — claim authority and ledger contracts

**Outcome:** accepted graph claims, source anchors, source reads, and inferences have distinct typed states.

**Deliver:**

- `GraphClaim`, `ClaimAuthorityClass`, `ClaimSupportState`;
- `GraphReference`, `SourceCitation`, `InferenceReference`;
- coverage/gap vocabulary;
- deterministic authority classifier;
- migration/display rule for legacy citations;
- ADR and canonical architecture reanchor.

**Retain:** Kernel retrieval models and security boundaries.  
**Delete/replace:** current generic grounding vocabulary in new path.

**Dogfood gate:** deterministic Tripod claim packet is graph-groundable even when source unreadable.

## Slice 2 — shared retrieval session and deterministic candidate handoff

**Outcome:** panel and Hermes consume one revision-pinned retrieval state.

**Deliver:**

- `GraphRetrievalSession` and operation event store;
- selected/referent/candidate contracts;
- deterministic initial candidate resolution;
- initial exact-object claim packet;
- UI can render session state read-only;
- Hermes host receives the same session ID/packet.

**Delete/replace:** query-dependent independent panel envelope as a separate semantic result. The existing projector may remain an internal adapter temporarily.

**Dogfood gate:** Tripod candidate/claims shown in panel are exactly those available to Hermes.

## Slice 3 — bounded retrieval-plan executor

**Outcome:** Hermes can flexibly expand one shared claim ledger through a small validated tool contract.

**Deliver:**

- `expand_graph_retrieval` model-visible tool;
- operations: object, neighborhood, compare, path, timeline, support, coverage;
- server-side operation validator/bounds;
- existing Kernel functions adapted internally;
- operation trace events;
- real Hermes policy evals.

**Delete/replace:** model-facing `search_campaign_graph`, `get_campaign_object`, `get_object_neighborhood`, and `get_object_evidence`. Retain Kernel primitives as internal implementation.

**Dogfood gate:** exact lookup, connections, comparison, path, and timeline scenarios.

## Slice 4 — source-read ledger and honest citations

**Outcome:** source availability, readability, opening, integrity, and citation are distinct.

**Deliver:**

- `read_graph_source` tool;
- source-read ledger entries;
- source citations only after successful read;
- unreadable/unavailable/integrity UI states;
- graph/source conflict representation.

**Delete/replace:** opaque anchor presence as citation/grounding.

**Dogfood gate:** Tripod unreadable/readable variants and exact quotation request.

## Slice 5 — structured answer validator and partial-answer policy

**Outcome:** accepted answer sections map claim-by-claim to graph claims, source reads, or disclosed inferences.

**Deliver:**

- structured answer draft schema;
- validator/repair/abstention logic;
- turn outcome states;
- partial coverage responses;
- inference records;
- no unsupported sentence acceptance.

**Delete/replace:** `classify_hermes_graph_result` anchor-ID predicate and whole-answer canned substitution as the primary policy.

**Dogfood gate:** all 23 core scenarios pass at contract/integration layer; Tripod gives a useful partial answer with unreadable source.

## Slice 6 — panel and trace convergence

**Outcome:** the GM sees current referent, candidates, used claims, opened sources, available connections, gaps, and acceptance reason in one calm UI.

**Deliver:**

- retrieval-session panel;
- answer-to-claim focus links;
- node/edge/assertion/source click behavior;
- candidate-versus-used display;
- user-facing graph-turn summary;
- developer trace secondary detail.

**Delete/replace:** current `WorldGraphQueryContextPanel`; generic `Steps 0 / Toolset n/a` presentation for graph turns.

**Dogfood gate:** operator can explain why each answer is graph-grounded, source-verified, partial, conflicted, or withheld without developer interpretation.

## Slice 7 — selected referents and bounded prose continuity

**Outcome:** clicked/pinned graph objects and same-thread conversation support natural follow-ups without carrying factual authority.

**Deliver:**

- selected/pinned/recent resolved referent persistence;
- priority/revalidation semantics;
- stale/deleted pointer behavior;
- one canonical bounded prose contract reused across boundaries;
- reapply salvageable PR356 tests/logic;
- cross-thread/campaign/focus isolation.

**PR356:** close as superseded after this slice lands or when operator approves closure.

**Dogfood gate:** Tripod pronouns, clicked-node follow-up, parallel thread isolation, revision change.

## Slice 8 — cumulative dogfood and demolition

**Outcome:** the new read path is the sole Hermes product path.

**Deliver:**

- real-agent scenario suite;
- latency/token/support metrics;
- legacy adapter removal;
- old schemas/tests/fixtures deletion;
- backend selector/default decision based on dogfood;
- docs/roadmap/tracker reanchor.

**Dogfood gate:** actual prep use across Plan and representative future Play/Build contexts.

## Slice 9 — durable Hermes session continuity, only if still valuable

**Outcome:** reload/process/model continuity improves conversational ergonomics without changing factual authority.

**Prerequisites:** Slices 1–8 accepted; retrieval sessions/referents stable; stale revision behavior tested.

**Deliver:**

- thread-to-Hermes session pointer;
- process/reload lifecycle;
- transcript/tool-state filtering;
- explicit current retrieval-session injection each turn;
- session corruption/recovery behavior.

**Decision gate:** dogfood may show that durable Hermes sessions add little beyond persisted referents and visible prose. Do not implement by inertia.

## PR011 unblock

PR011 may begin only after Slice 8 acceptance and a separate write-design review. The read path must expose exact claims, sources, inferences, and revision impact so proposals can be typed and previewed.

## Demolition map

| Existing code/contract | Action |
|---|---|
| `agent_world_graph_query_context.py` query envelope | replace with retrieval-session creation/projection; retain reusable projection internals only |
| `render_world_graph_prompt_block` | delete from Hermes path; review legacy live consumers separately |
| five model-visible graph tools | replace with expansion + source-read tools |
| `HermesGraphToolEvent` current summary | replace with retrieval operation/claim/source ledger events |
| `classify_hermes_graph_result` current classifier | replace with structured answer validator |
| `dmb_world_graph_anchor_citation_v1` | legacy display only; new source citation requires opened source |
| `WorldGraphQueryContextPanel` | replace |
| generic graph trace shell | replace for graph turns |
| duplicated history constants/validators | consolidate in Slice 7 |
| fake-anchor “grounded” tests | rewrite around claim/source contracts |

## Data migration and republishing

1. audit each active world head for `contribution_source_payload_sha256` coverage;
2. verify initialization receipt binding for graph-data reads;
3. rebuild legacy heads using lifecycle-neutral source payload digests;
4. republish/activate through existing governed bootstrap/rebuild path;
5. verify every graph-native accepted assertion has inspectable provenance even when no separate Markdown exists;
6. preserve historical revisions; do not mutate old stores in place without an explicit migration contract.

## Documentation reanchor timing

After ADR/architecture acceptance but before Slice 1 dispatch:

- replace relevant authority sections in Campaign Supergraph architecture;
- replace current Hermes anchor with shared retrieval-session target;
- replace UX stories;
- halt current Rung 6/7 ladder;
- mark PR356 superseded;
- insert rebuild slices into roadmap/tracker;
- keep PR011 blocked.

## Stop conditions

Stop and return to operator review if:

- graph summaries must become factual authority to make the design work;
- selected-object identity cannot be safely revalidated across revisions;
- one turn cannot remain revision coherent;
- source-read integrity requires arbitrary path access;
- answer validation requires hidden chain-of-thought;
- a slice introduces durable writes;
- legacy persistence cannot be safely displayed without interpreting old anchors as opened citations;
- the real Hermes model cannot reliably emit the structured answer contract after bounded repair.

## Immediate recommendation

Begin only Slice 0 after operator accepts the design. Do not merge PR356, begin durable sessions, or unblock PR011.
