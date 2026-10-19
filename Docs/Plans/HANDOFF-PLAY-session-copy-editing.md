# PLAY — edit Markdown and media in the session copy

Status: SETTLED — #1428 merged d7d5eedd70b4305669610f41f493581ecdc2beff, reviewed head6937b5ff93250d9ece554253c79c5374d367948f; Architecture Cycle2 PASS. PRIME completed normal5202 editing acceptance. All source/reviewer leases and consumers are released; the historical assignment below grants no continuing write lease.
Base origin/main1097d439d143006c89f32b11e433be05c91b358a; branch codex/play-session-editing.
PRIME authors/adopts this contract. DOGFOOD's source lease is withdrawn; its implementation is preserved as the checkpoint below. The fresh play_editing_finish execution agent owns the exclusive expected source paths in this same checkout after this transfer is pinned. Architecture independently reviews exact cumulative diff; PRIME merges and owns normal5202 delivery. No new checkout, environment, source export or /tmp task directory. Existing dependencies/private evidence location reused.

## Outcome

In Play, edit supported Markdown and existing media within the current session's existing scenes, with automatic durable session-copy saves. Original Plan and original Run pin remain unchanged. Plan and Play are the product names. This is the editing capability, not another read-only projection.

Expose a compact Edit session control, Markdown and visual editing using existing MarkdownEditorCore/parser/serializer/media node, with timestamped save status on the surface controls. Make current scene reachable in the editor. Full session source may be edited, but existing structure remains fixed and server structural validation is authoritative. Do not mount a Plan/Build writer or forge WorkRevision identity. Preserve leading YAML exactly; reuse existing split/preserveLeadingYamlFrontmatter, semantic serialization diagnostics and media resolution. No scene add/remove/reorder in this slice.

Existing images must be manipulable in the visual editor, including resize, move and collapse with persisted occurrence attributes; source editing supports existing media descriptors. Keep independent occurrences independent, tables/callouts and media metadata intact. Image generation/library insertion is not a prerequisite and must not silently create a second capability or fake Build capture authority. Return a concrete seam question if shared editor behavior prevents existing-media editing within these paths.

## Save and recovery invariants

- One controller above the scene cockpit owns accepted edition, draft and pending command. Stable World+Run+full original pin identity; preserve scene/current-inspected position and keep floating scene notes usable independently.
- Use existing authenticatedApiFetch/CSRF transport for content PUT and command/history reads. Validate exact server envelopes and receipt identities/hash. Inspect actual server schema; do not infer DTOs from prose.
- Before PUT, durably journal exact submitted payload, command UUID, accepted base revision/hash and draft generation. One content write at a time, debounce quiet edits. No-op/open/view toggle must not create an edition.
- A receipt for an older draft advances accepted base but cannot mark newer text saved or replace it. Follow-up save uses the new accepted base. Saved timestamp comes from the accepted server receipt.
- Ambiguous transport failure freezes new automatic commands; reconcile the same command/body via command receipt or exact retry. An instantaneous404 is not proof an in-flight request cannot commit. Preserve submitted payload without reconstruction.
- 409 preserves draft and requires explicit review of latest state; no silent overwrite/rebase. Definitive 422 preserves draft and explains validation without retry loop. Storage failure is visible and cannot claim durable recovery.
- Route/World/Run A→B→A: stale acknowledgments cannot paint another session. Retain pending journals and recover when returning. Reopen/reload must recover unsaved/pending content honestly. Never overwrite the Plan or progress/notes store.
- Unsaved session drafts must also disable misleading Agent sends before first edition; retain existing edited-edition transport guard. No edition-aware Agent implementation here. Use Play wording in any touched product label.

## Expected write paths

- This handoff; Docs/Plans/HANDOFF-PLAY-live-effective-content.md (settlement only); Docs/Roadmaps/ROADMAP-demo.md (current state/next boundary only).
- apps/live-control-ui/src/api/playRunContentApi.ts and .test.ts
- apps/live-control-ui/src/playSurface/playRunContentTypes.ts
- NEW apps/live-control-ui/src/playSurface/content/ controller, draft storage, editor components, styles and owning tests (choose clear Play names).
- apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx and .test.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx (product accessibility label only) and WorldAgentConversation.planPlay.integration.test.tsx (assert that exact label only).
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx and .test.tsx (editor integration/notes continuity only).
- apps/live-control-ui/src/playSurface/playRunEffectiveContent.ts and .test.ts if receipt validation/adoption requires it.

Shared MarkdownEditorCore, media node, parser/serializer, media resolver, note writer, Agent transport/controller, server/schema, global registry/router/chrome, dependencies and lockfiles are read-only. The WorldAgentConversation addition is only the accessibility label for the unavailable Play conversation; do not alter transport behavior. Return exact required path/invariant before widening. The existing effective-content reader is merged1425+1426; PRIME is completing its rendered gate separately without editing this source lease.

## Verification and completion

Meaningful owning API/controller/editor/mounted Page tests: actual request/receipt shapes, exact command recovery and duplicate behavior, overlapping newer edit, unknown success, conflict/validation/storage failure, identity races, unmodified open no write, recovered draft, notes continuity, unsaved Agent guard, frontmatter/table/callout fidelity and independent media attributes. Run typecheck/build and cumulative base→head diff/whitespace review. Distinguish inherited test failures with base reproduction; no blanket green claims.

Finish implement→verify→inspect cumulative diff→commit→push→open one PR. No worker merge. Return PR URL/exact head, tests, limitations and consumer/lease status. PRIME then proves normal5202 disposable prose and existing media edits→autosave→reopen/history, unchanged Plan/original Run/notes, desktop/narrow images and actual resize/move/collapse. No real user document edits, provider calls, Graph publication, database or serving process changes by worker. Report concrete blockers promptly and continue independent work.

## Serial execution-context transfer

PRIME withdrew DOGFOOD's lease after two completed turns drifted to an old Session10 discussion after compaction. No vitest/tsc/build consumers remain; all existing implementation is preserved in this checkpoint, not accepted as complete. Fresh bounded assignment uses GPT-6.1 Sol low for the unresolved asynchronous recovery/edition projection lifecycle, returning at one verified PR; this is within the normal upper allocation. PRIME allocation is unchanged. Original base remains1097d439d; review the full cumulative diff.

Observed focused run: six suites50pass (API10, protocol1, journal3, controller5, editor2, Page29); this is not all required evidence. Finish concrete missing controller proofs: StrictMode stored/pending journal recovery;409 draft editing stays gated until explicit review; unknown command GET404 followed by identical PUT definitive422/413/409; late unmounted controller A→B→A. Critical unresolved hazard: initialRawRef holds the initial journal while the recovery effect depends on changing initialContent and resets its started guard on cleanup. When a recovered acknowledgment updates the parent content prop, it can consume the old journal again. Prove a mounted parent feeds accepted content back without repeated recovery/replay or false conflict; consume the initial journal exactly once per identity while supporting StrictMode.

Editor explicit replacement, Page async route/progress fencing,413 rejection and sticky controls were partially repaired already; inspect rather than redo. Finish typecheck/build, intended diff inspection, docs settlement, commit/push/PR. Architecture reviews; PRIME delivers and proves actual media mutation/reopen plus unchanged Plan. Do not inspect or answer old Session10 conversation history. This contract and the current operator request are the task.

## Delivered acceptance — 2026-10-18

Normal5202 disposable session: Markdown prose autosaved as edition4; pointer resize changed one media occurrence40→66 while the other stayed80 (edition6); collapse persisted7; pointer drag reordered images8 and reload retained prose/order/collapse; expansion9 retained the new width. Authenticated current/history reads verified editions4/6/7/8/9, exact original origin/structure, and unchanged complete Plan snapshot, original Run/progress/notes and real Edge Run. Scene notes opened independently. Desktop and narrow416px client=scroll width showed loaded artwork and saved server timestamp. Verification tab closed, viewport reset and original Edge active selection restored. No provider call or real-user document edit.

PR1429 contrast repair merged0858ac568049b9d1df17a42e474737cd6454f067 after independent review of49f4a779bde6cbc276ae27e5b7c16361cd31d564; build and normal5202 computed-style/rendered readback passed (light text on dark controls). Private established evidence: play-editing-rollout.json. Accepted131 initial focused tests and final Architecture133 across8 suites plus2 Agent races; final affected repair49 tests, typecheck/build/diff passed. Existing chunk warning remains. Requested completion allocation Sol6.1low after Luna context drift; model-attributable cost is unknown.

This settles existing-scene Markdown/existing-media editing. Edition-aware Agent context/notes, image generation/library insertion, structural scene editing and the full shared Plan/Play workspace remain separate successors. No overall goal completion is claimed.
