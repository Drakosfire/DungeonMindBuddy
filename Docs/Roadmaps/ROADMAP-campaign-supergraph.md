# Roadmap — Campaign Supergraph

**Status:** Canonical implementation roadmap  
**Updated:** 2026-08-26 — #645 D.2C2 `DONE`; #647 D.2C3 design `DONE`; D.2C2 provenance compatibility DESIGN `DOING` (Review Cycle 1 `5036355801` REQUEST-CHANGES-equivalent; Review Cycle 2 `5036457798` REQUEST-CHANGES-equivalent on `ce902411…`; Review Cycle 3 in-flight); DungeonMind provenance CODE `BLOCKED`; Buddy producer CODE `BLOCKED`; D.2C3 implementation `DOING` / PARKED ON PREDECESSOR / Buddy #651 (Review Cycle 3 `5035980646`; frozen acceptance still requires admitted `D_0` projection); D.2C4/D.3A/D.3B `BLOCKED`; D.3 not `DONE`  
**Repository anchor / current Buddy `main`:** `555a9c7965aca47a24536277b9b36ae569a7285a` (PLAY-SURFACE cockpit re-anchor). Historical #650 APP-STATE merge: `cc016661f80416e0816f56349217cf33c53a195f`. D.2C3 dispatch base remains #647 merge `d96a21363fd0decbcb8c4390f951a6316b53060c`. Historical D.2C2 implementation #645 merge: `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`. Historical D.2C2 design #644 merge: `f1eae2a3d27e430ee19e254d5b52fa556b2632ff`. Historical native-read switch #633 merge: `65d13dcca8162b5eccd0c81dd4235dec93c8cd0c`. **#633 accepted head:** `ebb57adebe063b9c81fd4caa9a1274cfd6d6fb01`. **#632 merge:** `54779636750ebf7a639aef8a6184cc61ead9c860`. **Historical #631 merge:** `ffc39ab394ea55b00dc8b2a0fd41be0448635600`. Reviewed R.3 implementation head: `65405b48`.
**#536 design predecessor:** `413e808112dc85499651cf232ff71614dc4b18b6`  
**DungeonMind pin:** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b` (PR #46 merge / reviewed first-world initialization)
**Architecture authority:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Sequencing authority:** [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md)  
**Current-state guide:** [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md)  
**UI shell (cross-boundary):** [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)

This roadmap describes the infrastructure and product-authority milestones for one durable World Supergraph serving every DungeonBuddy surface. It intentionally omits completed PR-by-PR narrative; the tracker owns exact sequence and Git history preserves prior detail.

## Objective

DungeonBuddy uses one authoritative World Supergraph per world, with campaign-scoped assertions, evidence, chronology, visibility, correction history, and projections for every product surface. Plan, Play, Build, Graph Review, Ingest, and Agent Interaction consume revision-aware projections rather than owning independent graphs or campaign truth.

```text
source prose and authored records
→ candidate extraction or governed authoring
→ GraphContribution / identity resolution / correction authority
→ proposed immutable World Graph revision
→ validation and atomic head advancement
→ campaign/focus/admissibility projection
→ product surfaces and Hermes
```

Source artifacts remain prose and evidence authority. The graph is durable materialized campaign knowledge. Conversation history is continuity, never campaign truth.

## Locked decisions

- Tenancy is one World Supergraph with campaign scopes.
- Published revisions are immutable; graph-head advancement is atomic.
- Identity, contribution, evidence, epistemic, temporal, visibility, canon-state, and approved correction decisions are durable and replayable.
- Agents are not privileged writers. Durable changes require typed capabilities and explicit authority boundaries.
- Factual discovery is graph-first. Source excerpts are opened through graph-admitted anchors, except for explicitly typed server-owned memory-lag workflows.
- A graph miss remains visible. The product must not hide coverage gaps with arbitrary Markdown, manifest, corpus-index, or lexical fallback.
- Runtime graph selection never uses latest-ingest, preview-source, manifest path, run directory, or mutable store path.
- Replacement paths are deleted when their replacement becomes production-ready unless a named consumer is documented.
- Conformance analyzers, adjudication fixtures, and explicit adapters are interpretation/proof layers. They do not silently mutate the World Graph.
- A source-derived assertion may remain historically true-to-source while being semantically wrong as current graph meaning. Human correction must preserve that historical source authority while explicitly changing current durable assertion authority.

## Phase status

| Phase | State | Outcome |
|---|---|---|
| 0 — Architecture reset | DONE | Canonical architecture, authority model, roadmap, and tracker |
| 1 — Persistent storage | DONE | Durable per-world store, immutable revisions, atomic head |
| 2 — Graph Kernel foundations | DONE | Identity outcomes, contribution lifecycle, replay, retraction, source-revision supersession, CAS publication |
| 2.5 — Source and agent contracts | DONE | Source authority, typed capability classes, no-privileged-writer rule |
| 3 — Initial publication | DONE | Eldyrwild Campaign 2 World Graph initialized and active |
| 4 — Projection Engine | DONE | Revision-pinned campaign/focus/admissibility projections |
| 5 — Surface integration | PARTIAL | Plan, Recap, Build context, and Agent reads are graph-backed; Play remains |
| 6 — Multi-source expansion | ONGOING | Additional recaps, worldbuilding, prep, and authored records enter through governed contributions |
| 7 — Graph-native retrieval | DONE | Hermes is graph-first in Plan with bounded evidence admission and continuity |
| 8 — Governed context, correction, and tools | ACTIVE | Human confirm reference path exists; exact assertion-correction authority and candidate-path cleanup remain |
| 9 — Living memory and cleanup | NOT STARTED | Continuous Plan/Play use with obsolete dual paths removed and corrected memory surviving normal operation |

Phase 2's foundational lifecycle is complete. PR #534 later published the governed assertion-level correction operation that can replace one defective assertion while preserving unrelated assertions from the same source contribution. That primitive is historical `DONE`, not current CUTOVER work.

## Completed product authority spine

```text
DONE  PR380A / #412  Revision-pinned World Graph recap projection
DONE  PR380B / #437  Recap + Build exact-ID World Graph consumption and shared object navigation
DONE  PR380C / #443  Graph Review post-confirm transition to the exact committed revision
```

PR380C means a terminal confirm receipt replaces candidate authority for its exact review binding. Graph Review either renders the receipt-pinned committed projection or preserves the receipt in a durable-read-unavailable state. It does not re-confirm, fall back to candidate content, or silently read current head.

## Completed DungeonMind semantic-adoption spine

The August adoption work changed the question from “can selected Buddy objects be bridged?” to “can the entire existing World Graph be understood and eventually adopted without losing meaning or authority?”

```text
DONE  #521  Generalized exact Buddy world-object bridge
DONE  #522  Whole-world conformance inventory; adoption fails closed on real gaps
DONE  #523  Re-pin after DungeonMind graph-v5/world-object-v2; emit exact residual ledger
DONE  #525  Re-pin after DungeonMind PR #28; reduce semantic gaps to 59 relationships
DONE  #526  Source-ground and adjudicate every residual relationship
DONE  #528  Re-pin after DungeonMind PR #29; 287/59 → 291/55; DungeonMind relationship debt → 0
DONE  #530  Govern three remaining explicit adapters; 291/55 → 294/52
DONE  #531  Carry adjudication across proven descendants; compose effective conformance
DONE  #534  Targeted structural edge-assertion correction (synthetic/replay-safe; no Eldyrwild mutation)
DONE  #536  Current-support-aware relationship conformance (durable history ≠ current residual)
```

At the immutable Eldyrwild adjudication domain:

- `346` durable relationship semantics;
- `294` effectively represented against the pinned DungeonMind contracts;
- `52` effective residual relationships;
- `2` retained `uses_statblock` mechanics attachments;
- `0` remaining DungeonMind-owned relationship debt in the exact adjudication domain.

The remaining relationship debt is Buddy-owned. The adjudication ledger distinguishes source corrections, compound assertions that are not one relationship, identity-not-relationship cases, and insufficient-evidence cases. Those are different authority problems and should not be collapsed into one migration PR.

## Current critical path — exact adopted-membership checkpoint before product cutover

```text
DONE    Captain/Thrin alias package (#587)
DONE    dual-sense relationship package (#588)
DONE    DungeonMind adoption v2 runtime (#31/#32/#33)
DONE    exact Eldyrwild adoption-v2 bundle (#602)
STOPPED first real PostgreSQL attempt (evidence identity collision)
DONE    Buddy contribution evidence identity (#609)
DONE    dungeonmind-eldyrwild-postgres-existing-world-adoption-proof
        DungeonMind PR #34; head 935d3d9117442a92ef2dd8f11967fed20f863ea1;
        merge d2204dd0901237d8b446b4f2363f896306e32e6f; 2 review cycles;
        Cycle 2 4948479110. Unchanged #33 runtime f2e27380… accepted exact
        blob 274cdd9e… / sha256 90574dfc… / published rev:34b1f8e2… /
        payload 047214f1… / shape 469/323/3/5. Three test/fixture paths
        only. Does not prove correspondence, snapshot drift, writer
        ownership, or product-authority switch.

DONE    cutover-observational-correspondence-drift DESIGN (#614)
        Buddy PR #614; head b270b1ea13d198ba0008e38cf6b5dedb64036bdf;
        merge e1d2b4941f629f9cd6bcaf02a9bac5d7dca8e83a; 4 review cycles;
        accepting Cycle 4 4953256382. Accepted the read-only
        correspondence contract: CORRESPONDING / STALE / MISMATCH /
        NOT_ADOPTED plus typed integrity/unavailable errors; no dual
        writes, no authority transfer.

DONE    dungeonmind-observational-correspondence-implementation (#35)
        DungeonMind PR #35; head 36e9c0d21aaccbd9dfe850a5f6fe27e1e9789529;
        merge 9ff0d1f9e278e44fb1444bdf1fda8beb6348bc11; 3 review cycles
        (4955043192 / 4955268953 / 4955637320, all CHANGES REQUIRED;
        merged by steward split decision). Proved exact bundle identity,
        fail-closed pre-classification adopted-history integrity, closed
        MISMATCH algebra, zero durable writes. Cycle 3 residual
        intentionally open: V2 cardinality-only pins cannot detect
        same-cardinality adopted-membership substitution behind STALE.

DONE    cutover-exact-membership-receipt-v3 (DungeonMind #36)
        DungeonMind PR #36; head 6a249b483687c5f25c46298016c53dbb9afe4521;
        merge 9a19584d31baea77f590d7726e508b144c7dd39d; Review Cycle 3
        PASS / no code changes requested; formal review 4956825887;
        integration green. Exact adopted-membership receipt V3 with one
        membership_sha256 over sorted (record_id, record_fingerprint)
        pairs; steward-supervised Eldyrwild V2→V3 promotion; pre-STALE
        checkpoint verification; unpromoted V2 fails closed.

DONE    cutover-v6-governed-review-publication (DungeonMind #37)
        DungeonMind PR #37; merge 2edc07ff27a21b1c83aed847edf95b77d297910e;
        3 review cycles; final PASS review 4963853068. Delivered the
        DungeonMind public v2 contribution-review finalize + v6
        materialization + head CAS publication seam.

DONE    cutover/whole-world-authority-transfer (Buddy #619 + #620 + live)
        Buddy PR #619 merged at 6c2fe9d37dcecf34e025db8373fce072de30b62e
        (2 review cycles) as the authority adapter predecessor.
        Buddy PR #620 merged at 18bcb18475ac30679ebec84bec17c4e81390f674
        (4 review cycles; final PASS review 4966969478) completing the
        adapter repairs. Live cutover then adopted exact A at V3,
        switched product reads to DungeonMind, and published the first
        DungeonMind-owned child:
          D_A = rev:34b1f8e2625d5ba693fc726a2a1a4720
          D_B = rev:680c246047d67f9fe0293ee90526f670
        Buddy local World Graph writer remains fail-closed.
        Parent handoff status: CUTOVER_COMPLETE.

DONE    DungeonMind R.2b / PR #43
        Merge 519b2c96fc42d22f3113cc9ca0d48bc70b6780e5; 4 formal review
        cycles. Governed V3→V4 adopted-source classification repair
        (ExistingWorldAdoptionReceiptV4, membership manifest, effective M1).
        Live Eldyrwild repair applied 2026-08-23: receipt V4, historical M0
        preserved, M1 16d3161d…, manifest 83/83/93/13, D_A and current head
        unchanged.

DONE    cutover/v4-hydrated-authority-compatibility / Buddy #630
        Merge 3b25dbd89664b5a148ad76e0f5780b5ddc742f9a. Landed typed V3/V4
        receipt binding and V4 manifest/M1 membership verification on the
        existing hydrated DungeonMind-authority path. Direct reads stay off.

DEFERRED pinned exact-snapshot catch-up
        Still conditional only — no STALE observed during the live
        pre-switch correspondence check (result was CORRESPONDING). The
        parked design handoff on branch cutover/design-pinned-snapshot-catchup
        stays unmerged.

DONE    cutover/r3-read-contract-ratification
        Design accepted. Replaced zero-difference Buddy-kernel parity with
        the supported DungeonMind ↔ Buddy graph-read contract. Handoff:
        Docs/Plans/HANDOFF-CUTOVER-r3-read-contract-ratification.md.

DONE    cutover/direct-dungeonmind-production-reads (R.3) / Buddy #631
        Reviewed/accepted implementation head 65405b48; merge
        ffc39ab3 (historical Buddy main at #631; later superseded by
        #632 merge 54779636 then current main 87597f40). Sealed V4
        witness: 0 blocking, 0 errored, 199 approved. Direct-read gate
        stayed default-off at that merge.

DONE    DungeonMind R.3a / PR #45
        Merge c5d3688587b0f5d506e0f7d64f33eb0628bac896. Native
        read-context optimization (~20.7s → ~115 ms warm on Eldyrwild).

DONE    cutover/r3a-dungeonmind-pin / Buddy #632
        Pin Buddy to DungeonMind #45 merge c5d36885…. Merge
        54779636750ebf7a639aef8a6184cc61ead9c860. Sealed R.3
        witness rerun: 0 blocking, 0 errored, 199 approved.
        Adapter projection ~0.55–0.85s; retrievals 120–226 ms.
        SWITCH_READY. Operator dogfood accepted.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-r3a-dungeonmind-pin.md.

DONE    native-read switch / Buddy #633
        Remove DUNGEONMIND_WORLD_GRAPH_DIRECT_READ. Native DungeonMind
        reads are the only dungeonmind-authority production path,
        including Hermes latest-recap comparison facts.
        Merge 65d13dcca8162b5eccd0c81dd4235dec93c8cd0c; accepted head
        ebb57adebe063b9c81fd4caa9a1274cfd6d6fb01; Cycle 2 approval
        5011598382; DEMOLITION_READY.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-native-read-switch.md.

DONE    D.1 native governed write context / hydration retirement / Buddy #634
        Exact-run prepare → confirm seals public DungeonMind parents
        and publishes DungeonMind children without Buddy hydration.
        Merge 31f2885cc18f96b98a1028304ae98914d1139fa3; accepted head
        aa4980a8cfd1dfedbb8b05d683f01cf27cfd0c3b.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-native-governed-write-context.md.

DONE    D.2A Threat authority-port migration / Buddy #637
        Mounted Threat publication lifecycle consumes World Graph
        authority only through a storage-neutral port backed by
        DungeonMind. Buddy-owned operation/identity/proposal/commit
        state stays Buddy state.
        Merge 28daea7e90b396c1b9e9b5fcc12a0b9427674d8c; accepted head
        3c74dc40dbcaf46b316e379e5a703e66570d2dea; 3 review cycles;
        Cycle 3 PASS-equivalent.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-threat-authority-port.md.

DONE    D.2B worldbuilding writer migration / Buddy #640
        Mounted existing-world worldbuilding prepare → confirm obtains
        graph and identity authority only through WorldGraphAuthority
        and publishes or recovers one DungeonMind child.
        Merge 6ef7aefa741a82f512f5918b460cbee1a427cae4; accepted head
        caa9d84e4431db1b90ea58dab2e74d270fbcffee; 3 review cycles;
        Cycle 3 PASS-equivalent 5020798053.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-worldbuilding-authority-port.md.

DONE    D.2C1 reviewed first-world initialization DESIGN / Buddy #642
        Frozen D.2C1 provider contract.
        Merge d80c8688774602972e07593b83e3d8d09d4b0a7b; accepted design
        head 0f9e07686dfd157bb35acbd10765bfe3de68166f; Cycle 2
        PASS-equivalent 5023757627.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-reviewed-first-world-initialization.md.

DONE    D.2C1 reviewed first-world initialization provider / DungeonMind #46
        DungeonMind reviewed zero-parent initialization authority.
        Merge bf40e933bdedf3cf08bb23a07a135958bdb7cc6b; accepted head
        bc2800b1d09aa70cf33d92ea6b8fc4a786f4b999; Cycle 3 PASS-equivalent
        5024825675.

DONE    D.2C2 mounted first-world authority migration DESIGN / Buddy #644
        Frozen D.2C2 consumer design.
        Merge f1eae2a3d27e430ee19e254d5b52fa556b2632ff; accepted design
        head ded066cec49c3840c3b19c3e817ffa569a116f39; Cycle 2
        PASS-equivalent 5025378684.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration.md.

DONE    D.2C2 mounted first-world authority migration / Buddy #645
        Move mounted first-world review/prepare/confirm onto
        WorldGraphInitializationAuthority and one DungeonMind D_0.
        Merge 3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c; accepted head
        f772db17e00cbe2c0198ae53f169a10a6332a3ed; Cycle 2 PASS-equivalent
        5026532158.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration-code.md.

DOING   D.2C2 first-world provenance compatibility DESIGN
        Freeze DungeonMind-owned #645 first-world producer-family
        genesis OTHER interpretation and Buddy future producer stamp.
        Review Cycle 1 5036355801 REQUEST-CHANGES-equivalent; Review
        Cycle 2 5036457798 REQUEST-CHANGES-equivalent on ce902411…;
        Review Cycle 3 in-flight.
        Frozen: WorldGraphProjectionService builds GenesisEvidenceCompatibility
        above graph_scope; producer family is dmb_first_world_graph_plan_v1 /
        dmb:first-world:<sha256> / live_control:graph_review_confirm /
        zero-parent D_0 / worldbuilding; replay is one shared dual-hash
        identity at all four seams; descendant eligibility is canonical
        record equality; ADR-0023 if free.
        Do not invent its merge SHA.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-compatibility.md.

BLOCKED D.2C2 first-world provenance compatibility CODE / DungeonMind
        WorldGraphProjectionService builds verified genesis compatibility
        context for the named #645 producer family; graph_scope consumes
        it; correction replay is the shared dual-hash identity at
        application preflight, recovery, PostgreSQL under-lock, and
        in-memory under-lock. ADR-0023 if free.

BLOCKED D.2C2 first-world provenance producer CODE / Buddy
        Stamp new first-world evidence from SourceArtifact domain and
        pin DungeonMind. Blocked on DungeonMind CODE.

DONE    D.2C3 native genesis read/write continuity DESIGN / Buddy #647
        Frozen two-genesis binder and D.2C3/D.2C4/D.3A/D.3B sequence.
        Merge d96a21363fd0decbcb8c4390f951a6316b53060c; accepted design
        head 1f5676c204ee917d18efd553106c07306541e820; Cycle 7
        PASS-equivalent 5034239255.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md §4.

DOING   D.2C3 native genesis read/write continuity / Buddy #651
        PARKED ON PREDECESSOR at cf453078a5c1950ec5f23a5d5b99001ee9e456db
        after Review Cycle 3 5035980646. Shared DirectAuthorityBinding
        recognizes existing-world adoption and reviewed first-world
        initialization; D_0 is a legal native parent. Frozen acceptance
        still requires admitted D_0 projection/search/exact-object
        retrieval. Do not merge or weaken that rubric. Resume as Review
        Cycle 4 after the provenance predecessor lands.
        Handoff: Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md.

BLOCKED D.2C4 manual Graph Review authoring continuity
        Migrate Graph Review manual authoring onto WorldGraphAuthority.
        Not dispatched until D.2C3 implementation merges.

BLOCKED D.3A mounted graph-engine excision
        Excise Buddy graph engine from production imports/routes.
        Not dispatched until D.2C4 merges.

BLOCKED D.3B physical legacy-package deletion
        Delete kernel/world_supergraph/union_supergraph source and prove
        physical absence. D.3 is not DONE until D.3B merges.
```

Historical correction/heal slices (integrity heal, Lysandra, Session-24, closure, #566) remain `DONE` and are not current dispatch. The tracker, not this roadmap, decides which `READY` slice is dispatched next.

### Why targeted assertion correction was a prerequisite

Contribution supersession is intentionally source-revision-shaped: replacing contribution A with contribution B removes A's support from every assertion A carried, then re-applies B. That is correct when a source revision is replaced. It is too broad when a human adjudicates exactly one extracted assertion as semantically wrong while the rest of that source contribution remains valid.

PR #534 published the correction primitive that preserves four distinct facts at once:

1. the historical source contribution really did assert the old meaning;
2. the human correction is a separate governed authored authority;
3. unrelated assertions from the historical contribution remain actively supported;
4. replay of contributions plus correction records reconstructs the corrected head exactly.

The first synthetic proof used a multi-assertion source contribution so the implementation could not accidentally pass by superseding an entire one-assertion contribution. The later Lysandra live correction applied that seam and is historical `DONE`, not current dispatch.

## Parallel product path retained

The July product work remains valid and may proceed in parallel when it does not touch semantic correction/adoption authority:

```text
READY   exact-run-candidate-review-projection
        Replace Graph Review's remaining preview-union / fixture-oriented candidate lane
        with a direct exact-ExtractionRun review projection.

BLOCKED retire-preview-union-review-materialization
        Delete preview-union lifecycle requirements, dormant Graph Preview paths, and
        legacy endpoints after the last product consumer moves.

READY   PR380D projection coordinator
        Normalize request construction, coalesce in-flight reads, add short-lived cache,
        revision invalidation, and projection telemetry. Cache is never authority.

BLOCKED PR380E Ingest primary-path simplification
        Simplify the source → extract → review → confirm workflow after candidate authority
        no longer depends on preview-union materialization.

READY   PR380F extraction and identity hardening
        Repair concrete dogfood failures without reopening graph tenancy or authority.

READY   fresh end-to-end durable-memory acceptance
        Prove ingest → review → confirm → exact committed reload → Plan/Hermes retrieval →
        process/browser reload against one bounded fixture.

BLOCKED PR011B Hermes preview_write / confirm_commit
        Reuse the human reference protocol; do not create an agent-specific write path.

READY   PR009 Play projection migration
        Consume the same projection and admissibility contracts for encounter/play lenses.
```

The tracker, not this roadmap, decides which `READY` slice is dispatched next. Current Buddy `main` is `87597f40…`. Native-read switch is the live CUTOVER lane; `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` is retired. After this PR merges, demolish the hydrated Buddy graph runtime.

## Phase 8 exit criteria

- Ingest creates proposed memory and never auto-publishes.
- Graph Review presents candidates from an exact run-bound review model.
- Explicit GM confirmation publishes through the existing sealed proposal and Kernel path.
- A terminal receipt switches the surface to the exact committed revision.
- Fresh reload proves the object, evidence, and relationships remain durable and retrievable.
- A human-authored factual correction can replace one exact durable assertion without retiring unrelated source-derived assertions.
- Historical source evidence remains inspectable after correction; current projection reflects only the governed active meaning.
- Correction replay is deterministic and stale-parent failure leaves the prior head untouched.
- Hermes uses the same preview/confirm capability model and cannot bypass Graph Review authority.
- Player-facing tools fail closed on GM-only assertions.
- Preview-union and obsolete product fallback paths are removed when their last consumer moves.

## Phase 9 objective

Create continuous, correctable campaign memory across Plan and Play. One durable object identity should survive recap ingestion, agent-assisted elaboration, planning references, exact mechanics binding, human correction, and Play runtime use without copying graph bodies or canonical mechanics between surfaces.

The coordinating integration roadmap is [`ROADMAP-cross-surface-statblock-demo.md`](ROADMAP-cross-surface-statblock-demo.md).

## Explicitly abandoned product and migration paths

- Session-local or campaign-copied graphs as durable identity ownership.
- Latest-ingest or preview-union as runtime campaign authority.
- Agent-side manifest routing, arbitrary document paths, or repo-wide Markdown search.
- Chat/session memory as campaign fact authority.
- Silent graph mutation by Ingest, surfaces, agents, conformance analyzers, or adapters.
- Whole-contribution supersession used as a shortcut for a narrower human assertion correction unless the whole source revision is actually being replaced.
- Rewriting historical source prose or adjudication fixtures to make a residual disappear.
- Global predicate reversal/rename rules introduced to repair one adjudicated edge.
- A second Hermes-specific write protocol.
- Hiding graph coverage defects with a compatibility fallback.

## Historical detail

The longer pre-consolidation roadmap remains in Git history at `09aed8db`. Completed handoffs and dogfood reports remain evidence, but they do not override this roadmap, the architecture, or the active tracker. The August semantic-adoption transition is preserved by merged PRs #521–#531 and their exact fixtures/source seals.
