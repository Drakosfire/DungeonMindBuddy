# Design — Build document ingestion as one workflow

**Status:** Worldbuilding inline-review slice ACTIVE under [its handoff](../Plans/HANDOFF-BUILD-inline-extraction-review.md); Recap mode and full recovery acceptance remain planned.
**Repository anchor:** DungeonMindBuddy `main@63f96f948538bcb897d21a341795c756d0d2e80a`
**Product authority:** [`ROADMAP-demo.md`](../Roadmaps/ROADMAP-demo.md), Authoring/view continuity
**Scope owner:** Buddy owns the Build experience and source-document interaction; the admitted knowledge and publication owners retain their current validation and write boundaries.

## Decision

Treat ingestion as a way to write knowledge from the Build document already open, not as a separate destination. Build keeps one editable Markdown document and one editor. The user chooses what kind of graph-writing run to make from that exact saved document. `Recap` is a frozen run mode with its own source/session configuration; it is not a different document editor or a reinterpretation switch on an existing run.

The intended customer experience is:

```text
paste or import Markdown in Build
→ continue editing the saved Build document
→ choose Worldbuilding or Recap for this run
→ review source-grounded candidates in the same Build work context
→ explicitly accept selected changes
→ keep the source document and open the accepted World references from Build
```

The existing Build document remains ordinary editable writing. Extracted candidates remain proposals. Publication remains an explicit, separately validated operation. Editing already accepted World facts is a separate follow-on capability described below.

## One document workflow

1. **Start with the existing Build document.** Pasted/imported Markdown is committed as the current Build workspace document and opens in the existing editor. Do not add a Markdown preview, a second editor, a duplicate source workspace, or a pre-ingestion transformation stage. The same Markdown is the user-authored source.
2. **Choose the graph-writing mode before launching.** The initial choices are `Worldbuilding` and `Recap`. Keep the choice beside the existing Build run action. Recap asks for its required source campaign and session and may attach the existing bounded session-evidence references. The selected destination World remains a separate explicit value.
3. **Launch from a frozen source snapshot.** The server validates the committed document identity, revision, and content digest, then registers an immutable source artifact and run. It freezes the mode, profile/version, recap source campaign/session, optional evidence references, destination World, and all other interpretation-affecting settings into that run. The browser cannot change the meaning of a run by changing a toggle later.
4. **Review without leaving the document context.** Keep the same Build document selected and editable while the exact run’s evidence, candidate selection, resolution, and decisions are available in the existing Build workspace. Reuse the current exact-run review and publication components through their owners. Evidence actions refer to the run’s immutable source artifact and spans. If the current editor is newer than the run’s revision, show which revision the run used; never silently align evidence to the newer text.
5. **Accept explicitly and retain the receipt.** Candidate acceptance publishes only through the current governed path for that source domain. Show the exact receipt and World revision, with durable object references available from Build. Editing the Markdown afterward does not amend the accepted graph, and accepting graph changes does not rewrite the source document.
6. **Recover the same work.** Reopening Build, changing navigation, or returning from another surface restores the exact selected document and run. Historical `/ingest` links continue to resolve their named run until the compatibility gate in Phase 3 is met.

The review panel can show evidence excerpts and candidate state, but it does not create a second Markdown reading surface or render unverified extraction as accepted content. A candidate may point to and highlight a span only when the frozen run and exact source bytes are still the authority for that span.

## Frozen identity and provenance

Every run launched from Build must carry and validate this identity set:

| Identity | Meaning |
|---|---|
| Build document ID | The existing workspace document the user is authoring. |
| Committed document revision and content digest | The exact immutable Markdown bytes used for this run. A dirty editor buffer is not a source revision. |
| Registered source-artifact ID and source digest | The immutable source admitted to the extraction run. It must resolve to the same Build document revision and bytes. |
| Extraction-run ID | The exact proposal and processing outcome to inspect, recover, correct, or publish. |
| Frozen mode and configuration digest | The mode identifier/version, applicable profile/version, recap source campaign/session, optional session-evidence pins, and any other settings that affect interpretation. |
| Destination World ID | The World in which a reviewed publication is intended. For Recap, this is distinct from the recap’s source campaign/session identity. |
| Publication receipt | The accepted object/relation IDs and exact resulting World revision, returned by the owning publication boundary. |

The server, not the UI, binds these values. A run’s source domain is fixed at creation. If the current extraction-run schema cannot represent both the Build document provenance and the recap source/session context without collapsing them into one campaign field, that is a model gap: add an explicit owner-approved binding instead of guessing or overloading an existing identity.

The durable provenance chain is:

```text
Build document ID + committed revision + content digest
→ registered immutable source artifact
→ ExtractionRun ID + frozen mode/configuration
→ candidate IDs + exact evidence spans + review decisions
→ publication receipt + World revision + accepted object/relation IDs
```

A correction records the parent run/candidate, corrected child run/candidate, exact source span, changed value, actor decision and resulting receipt. It never edits the original document, source artifact or parent run in place. A later edit to an accepted World fact must identify the exact prior object revision, new authored source/evidence, and resulting immutable revision through its separate governed write path.

For a multi-document import, the unit of extraction and acceptance is still one exact document revision plus one frozen mode/configuration. If a batch already exists at import time, show one run/status/receipt per document and allow independent recovery. This design adds no batch transaction and promises no all-or-nothing batch outcome; canceling or retrying one item cannot rewrite another item’s source or receipt.

### Mode configuration is immutable per run

- A mode selection is launch configuration. After launch, changing the selector affects only a later launch.
- Relaunching the same source revision in another mode creates a distinct run and configuration digest. It never updates or reinterprets the first run.
- A retry of an already-created run resumes or reloads that run’s recorded status and components. An explicit fresh extraction creates a new run identity and says so in the UI.
- Reusing a launch idempotency key with a different document revision, digest, mode/configuration, or destination is rejected. Repeating the same launch after a lost response recovers the same registered run rather than making a duplicate proposal.

## Reuse and domain boundaries

| Ingest capability | Build destination / existing owner | Reuse decision |
|---|---|---|
| Pasted/imported Markdown and saved document identity | `BuildDocumentCreateControl`, `useBuildWorkspaceDocumentController`, `BuildSurfaceContext`, and the existing Build editor | Keep as the sole source-writing workflow. Extend its existing run controller instead of adding an editor or draft store. |
| Exact document revision and source artifact | Build’s exact extraction launch and the server workspace-document/source-artifact registries | Keep the committed revision + digest check. Every run must preserve this binding. |
| Exact run reload and source evidence | `GraphReviewExactRunProjection`, source/evidence projection services, and the ExtractionRun registry | Reuse exact-run projection, source-span anchoring, and strict run identity checks inside the Build work context. |
| Candidate selection, object resolution, and reviewed publication | `GraphReviewWorldbuildingPublication` and the current source-domain publication owner | Reuse the explicit create/bind/accept/reject/defer decisions where valid. Candidate selection is not acceptance, and similar names do not authorize identity merging. |
| Recap extraction and session context | The recap ingestion pipeline, recap-specific context/evidence resolvers, and recap publication validation | Add an exact-Build-document server adapter. Preserve recap-specific source campaign/session and validation. Do not feed Build document text through the Worldbuilding validator or silently substitute a corpus recap with the same session number. |
| Correction and recovery | Exact-run correction child-run service, exact run reload, current review receipts | Reuse immutable child-run correction and recovery. Preserve the parent, original source bytes, original candidate and prior decisions. Do not create generic model-training feedback. |
| Accepted result visibility | Current committed-projection/receipt components and admitted World object reads | Return durable IDs and revision in Build context so accepted results can be inspected/opened. Do not imply that a document edit changes published facts. |

`DESIGN-source-to-world-authoring-interaction-contract.md` remains the accepted interaction boundary for governed World authoring; its consumer migration status must be rechecked before implementation. Existing historical Gold-workbench and extract/promote design notes are implementation ancestry, not authority to revive their old product framing.

## Recap adapter: the real model gap

The current Build extraction endpoint accepts an exact committed `worldbuilding_source` document revision and allowlisted Worldbuilding profiles. The separate recap route accepts recap operations plus campaign/session and recap-specific options; it does not take a Build document ID, committed revision, or content digest. The current Ingest page also distinguishes a recap’s source campaign from the selected managed World destination.

Therefore, adding a Recap dropdown alone is unsafe. The server adapter must:

1. resolve the exact Build document and reject dirty, stale, inactive, cross-World, or mismatched revision/digest input;
2. use those exact committed bytes as the recap source artifact, preserving the original bytes and their Build document provenance;
3. freeze explicit recap source campaign/session and any exact supplemental evidence references into the run;
4. preserve the destination World as an independent, validated publication target;
5. invoke recap-specific extraction, evidence, candidate validation, correction, and publication rules; and
6. register an exact ExtractionRun whose source, mode, configuration and publication receipt can all be recovered without reading a mutable “latest recap” path.

If recap normalization is needed, it is an internal derived input tied to that source artifact; it must not replace or rewrite the original Build Markdown. A historical filesystem recap that happens to share the selected session is never a fallback.

The shared product contract is the run lifecycle and review interaction. Source admission, interpretation policy, candidate validators, evidence rules, and publication authority remain domain-specific. Do not flatten them into a generic validator or one universal commit endpoint.

## Cancellation, retry, and stale context

The current Build exact extraction and recap operations are request/response routes, not durable cancellable jobs. The first unified slice must be honest about that:

- Before submit, canceling means no run was launched.
- After submit, do not show a `Cancel run` control unless the server has a cancellation operation that can prove it stopped before publication. Aborting a browser wait is not server cancellation.
- If the launch response is lost, resolve it through the frozen idempotency key and exact run registry. A later status refresh must not launch again.
- If the run fails, keep the exact run and diagnostic. An explicit retry either resumes the same registered job or creates a linked, clearly identified attempt; it must not create duplicate accepted objects.
- If the document is edited after launch, leave the run pinned to its original revision. Starting from the new revision creates a new run. Never quietly update the original source binding.
- If World selection or navigation changes during review, keep the run’s original target visible and reject stale commands. Do not retarget or publish into the newly selected World without a new explicit run/decision.
- If publication succeeds but the response is lost, recover the original receipt by its operation identity before offering another commit. Idempotency belongs at the server publication boundary.

An optional future job adapter may expose honest named stages (for example, queued, extracting, reviewable, failed, canceled). Until server events/jobs exist, show only states the current response or exact-run registry proves. No fabricated percent, provisional accepted-looking graph, streaming animation, or client-only cancellation semantics.

## Proposed sequence and scope

The linked Worldbuilding review handoff is the active bounded lease. The remaining sequence is planned; this design alone grants no additional write ownership.

1. **Build owns the whole existing Worldbuilding loop.** Keep the current saved Build document and exact extraction launch. Bring the exact-run candidate review, decisions, correction/recovery and publication receipt into the same Build work context. Do not open `/ingest` as the destination for newly launched runs. Keep the old route available for existing run links.
2. **Add Recap as a frozen run mode.** Implement the exact-document adapter and provenance/configuration model above before making the Recap option available. Test source campaign/session and destination World independently, including supplemental evidence.
3. **Move new-ingest navigation to Build.** Only after both modes can launch, review, recover and return receipts from Build should the primary Ingest navigation entry be removed or redirected. Keep backend extraction/review/publication capabilities and old deep links until old-run compatibility and recovery are accepted.
4. **Separately design editing existing World facts.** Reuse the accepted source-to-World authoring contract and its owning mutation boundary. Do not include direct edits to previously accepted objects in the initial workflow slice.

The activation gate is a fresh roadmap/lease re-anchor after the active shared navigation-width ownership is settled. This addition does not reorder the roadmap’s currently named focused-card/Play-adapter direction, PRIME’s active Rules lookup work, or the Rules→Combat follow-on. Reconcile those owners and any open PRs before dispatch; this design grants no parallel implementation lane.

## Acceptance checks for a future implementation

- Pasting/importing Markdown lands in the existing Build document and editor; the user does not enter a second editor or preview surface.
- A run is created only from the exact committed document ID, revision, source artifact and digest; dirty/stale/mismatched input fails closed.
- The run stores mode/configuration immutably. Switching modes after launch does not change the existing run; launching a different mode creates a distinct run.
- Recap requires explicit source campaign/session and keeps the destination World separate. Optional session-evidence references are exact run/revision/digest pins.
- Every candidate can be inspected against exact source evidence. Editing the current document after extraction cannot change the older run’s evidence or candidacy.
- Candidate choice/resolution is explicit. Similarity is advice; create-new and bind-existing remain separate. No candidate becomes accepted truth before the owning confirmation.
- Successful acceptance returns a stable receipt with exact object/relation IDs and resulting World revision. Reopen shows the same receipt and run without repeated writes.
- A correction is an immutable child of the exact run, keeps the parent/source/candidate unchanged, and is reviewed before acceptance.
- Retry, uncertain launch, uncertain publication, cancellation claims, changed document revision, changed selected World and stale navigation follow the rules above.
- Existing `/ingest?extractionRunId=…` links still load the named run and its original source mode; they never infer a mode from the current Build toggle or silently load “latest.”
- The source document remains editable after acceptance. Editing it does not revise published facts. Existing accepted World facts remain outside this slice.
- No live event/percent/provisional content is shown without server evidence; no cancellation is claimed without server acknowledgement.

## Current source anchors

These paths describe accepted `main@63f96f9`; inspect them again at implementation dispatch because ownership and routes can move.

- Build import, document lifecycle and editor: [`BuildDocumentCreateControl.tsx`](../../apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.tsx), [`useBuildWorkspaceDocumentController.ts`](../../apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts), [`BuildSurfaceContext.tsx`](../../apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx).
- Build extraction launch, query handoff and exact-run checks: [`useBuildExtraction.ts`](../../apps/live-control-ui/src/buildSurface/useBuildExtraction.ts), [`BuildIngestToolbar.tsx`](../../apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx), [`liveApi.ts`](../../apps/live-control-ui/src/api/liveApi.ts), [`graph_preview.py`](../../apps/live_control_server/routes/graph_preview.py).
- Recap route and current request contract: [`recapIngestApi.ts`](../../apps/live-control-ui/src/api/recapIngestApi.ts), [`recap_ingest.py`](../../apps/live_control_server/routes/recap_ingest.py), [`MemoryIngestPage.tsx`](../../apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx).
- Exact review and publication components: [`GraphReviewWorkbenchModule.tsx`](../../apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx), [`GraphReviewExactRunProjection.tsx`](../../apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExactRunProjection.tsx), [`GraphReviewWorldbuildingPublication.tsx`](../../apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorldbuildingPublication.tsx), [`GraphReviewExtractPromoteSheet.tsx`](../../apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx), [`GraphReviewCommittedProjectionPanel.tsx`](../../apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.tsx).
- Server-side run/source integrity, corrections and governed publication: [`graph_run_registry.py`](../../apps/live_control_server/services/graph_run_registry.py), [`exact_run_evidence_correction.py`](../../apps/live_control_server/services/exact_run_evidence_correction.py), [`extract_promote.py`](../../apps/live_control_server/services/extract_promote.py).
- Accepted authoring contract: [`DESIGN-source-to-world-authoring-interaction-contract.md`](DESIGN-source-to-world-authoring-interaction-contract.md).
