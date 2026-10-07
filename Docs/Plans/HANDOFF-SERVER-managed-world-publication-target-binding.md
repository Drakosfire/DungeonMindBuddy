# HANDOFF — SERVER: bind extract-promote publication to an explicit managed World

**Status:** ACTIVE — PRIME explicitly activated the bounded source implementation on 2026-10-06 after reviewing the proposed scope. No runtime or S27 publication is authorized.
**Owner:** DungeonMindBuddy SERVER. PRIME owns activation, collision arbitration, and independent review.
**Topology:** serial implementation on branch `codex/server-managed-world-publication-target-handoff`, based on `a869c27a7b4b3d6e77048bbb80a55984d709e705`, updating draft PR #980. Separate from annotation and any real S27 publication operation.
**Inspected base:** Buddy `origin/main@a869c27a7b4b3d6e77048bbb80a55984d709e705` on 2026-10-06, containing merged #977 and #978. Re-fetch before activation.
**Design authority:** DungeonOverMind architecture/ownership/contract map and the architecture ruling that requires explicit managed-World selection, a verified native binding, prepare-time sealing, and confirm-time revalidation. Buddy's current code and tests determine implementation details.
**Open-work check:** current open Buddy PRs have no edits to extract-promote models, route, service, or owning tests. #826 edits `world_container_registry.py`; this proposal does not lease that path and must re-check its status before activation. #922 is a distinct handoff-only Plan Graph context contract.

## Primary question

Can the existing recap extract-promote prepare/confirm path publish to the native World selected through an explicit, verified Buddy managed World binding, while rejecting a changed binding before any governed write?

The current `ExtractPromotePrepareRequest` accepts only `runId` and optional `nodeIds`. `prepare()` passes `DEFAULT_WORLD_ID` to candidate admission and production mutation context; the receipt also has a default fallback. That makes the publication target implicit. `managed_world_graph_projection.py` already verifies the managed record and source root, requires an active native binding, and checks its native ID/version after a read. Reuse its binding rules rather than trusting a client-supplied native ID or deriving a target from a campaign, source artifact, or `DEFAULT_WORLD_ID`.

## Intended behavior

1. Prepare receives an explicit managed World ID. Preserve a legacy run-only transport shape only if parsing compatibility requires it; reject it with a clear target-required error before preparing a mutation unless the exact run already contains an explicit immutable managed-World binding that can be independently revalidated. Do not create that binding in source storage for this slice.
2. Resolve the selected managed World through the existing verified-record/active-binding primitive. The mutation target is the resolved native World ID. Seal managed World ID, native World ID, and binding version into the reviewed candidate's canonical basis/fingerprint alongside the expected graph state. Revalidate the verified source root privately at both gates; it is deterministic from the managed ID and need not appear in the client-facing package. The response should make the reviewed target understandable without allowing the client to supply native identity.
3. Keep run campaign/session checks and any declared source-World check independent. A declared source World that conflicts with the selected target must fail closed. Do not infer campaign-to-World membership or treat a source World as a target selector.
4. Confirm re-resolves the exact selected managed World before governed publication. Missing, disabled, foreign, ambiguous, stale, or remapped bindings, including any change in sealed identity/version or verified source-root status, reject with a new-prepare/review requirement. No partial write may occur. Use the sealed native World ID for governed mutation and native readback/receipt; never fall back to `DEFAULT_WORLD_ID`.
5. Preserve the existing governed DungeonMind publication authority and current admission, evidence, semantic-disposition, idempotency, and assertion-selection checks. This slice changes target binding, not those contracts.

## Proposed implementation write set, pending activation

- `Docs/Plans/HANDOFF-SERVER-managed-world-publication-target-binding.md` — activation facts and final evidence.
- `apps/live_control_server/models/extract_promote.py` — explicit target input and sealed target projection/validation.
- `apps/live_control_server/services/extract_promote.py` — prepare/confirm binding resolution, sealing, drift rejection, target/readback selection.
- `apps/live_control_server/routes/extract_promote.py` — only if transport validation or error mapping needs a bounded change.
- `apps/live_control_server/services/managed_world_graph_projection.py` — expose one shared verified active-binding resolver. Its existing project method calls the same resolver. Concrete API gap: current verification helpers are private and projection triggers a native Graph read, so prepare/confirm cannot reuse the public method safely.
- `tests/test_managed_world_graph_projection.py` — regression for the shared resolver.
- `tests/test_extract_promote_managed_world_target.py` — new focused HTTP/prepare/confirm target-boundary witnesses. The proposed `tests/test_live_extract_promote_api.py` does not exist on the inspected base.
- `tests/test_recap_semantic_disposition.py` — existing recap prepare/confirm interaction.
- `tests/test_recap_semantic_candidate_correction.py` — preserve the held/rejected semantic gate under explicit target input.
- `tests/test_candidate_graph_source_provenance_admission.py` — declared source-World and candidate admission boundary.

A needed change to `world_graph_writes.py`, Graph Memory proposal encoding, public schema versions, or another path is a stop/re-scope signal unless it is genuinely necessary for this one invariant and explicitly added to the lease before editing.

No SourceArtifact/ExtractionRun storage change, campaign-to-World relation, schema migration, annotation work, first-World initializer, UI change, actual S27 publication, or production runtime mutation belongs to this PR.

## Activation gates and acceptance witness

PRIME approved the source scope, but APP-STATE/PRIME independent review remains required before merge. No open PR edits the leased extract-promote paths; #826 edits `world_container_registry.py`, which remains outside this lease. Re-fetch and re-check collisions before review.

At the owning boundary, prove: explicit valid managed-to-native targeting with different IDs; legacy run-only rejection or a genuinely revalidated run-sealed binding; missing/inactive/foreign/unverified bindings; declared source-World mismatch; prepare/confirm remap or version/source-root change; no governed write on each rejection; and successful receipt/native readback against the sealed native ID. Exercise HTTP request/error behavior as well as service behavior. Run focused tests, relevant full repository test/lint/type gates, inspect the exact cumulative base-to-head diff, and record the implementation head and evidence here before review.

**Proposed acceptance token:** `SERVER_MANAGED_WORLD_PUBLICATION_TARGET_BINDING_ACCEPTED` — available only after PRIME's independent exact-head review, never from this design PR alone.
