# PLAY — effective session-copy content projection

Status: ACTIVE under the operator's refreshed Plan/Live goal,2026-10-18.
Base origin/main7b73ffb07d21899c9007035a4b93ee9dcd455d18; branch codex/live-effective-content.
Topology serial successor of merged server PR1422. PRIME assigns DOGFOOD exclusive implementation ownership of the existing buddy-context-loop checkout/paths below; PRIME and Architecture read/review only. PRIME separately owns private runtime/schema adoption on8000 behind5202. That operational work does not change this checkout. No new checkout/env/source export or /tmp task directory. Existing dependencies/private evidence directory reused. Architecture independently reviews; PRIME merges/delivers.

## Outcome and invariant

Load and honestly project the effective content of a World-owned grammar-v2 session: its immutable original pin before editing, or its versioned session copy after editing. This is the read-adoption predecessor to Live editing/autosave, not completion of that user goal. Plan fully replaces legacy Prep; visible mode terminology Plan/Live. Preserve original Run pin/manifest/progress/notes. Existing v1/campaign behavior unchanged.

GET the authenticated1422 content endpoint using existing authenticatedApiFetch/LiveApiError patterns. Validate schema, World/Run, exact origin tuple, nonnegative edition N and nullable/positive edition UUID relation, exact UTF8 SHA256, structure witness and timestamps. Effective text is neither a forged WorkRevision DTO nor a replacement for original provenance. Fail closed on missing/corrupt edition; no quiet fallback. A newer Plan/Runbook is informational; an edition-bearing Run must not enter the old latest-Runbook rebase-required path.

Owning seam is PlaySurfacePage.loadExactRun: retain origin fetch/manifest admission, then admit effective content through the existing native parser/derivation. Feed one effective projection pipeline through progress/notes updates; do not revert to origin text when overlayRuntimeOnV2Ready runs. Keep original Run identity and note-cache key stable across edition changes; effective-content identity is separate. Preserve current/inspected scene and clamp only if absent.

SceneCardIdentity needs explicit run-edition state/descriptor: label Session copy · revision N, separately retain From Plan version M provenance. Do not substitute edition UUID into WorkRevision ID. Unsaved drafts/writers are a later bounded slice.

Agent context currently reads original pin server-side. For an effective edition, clear Play conversation registration/current-moment contribution and show explicit temporary unavailability for session-edited material. Prove composer cannot send postWorldPlayAgentTurn under that state, including late history/in-flight responses; do not leak edited titles as if Agent sees them. Pinned unmodified sessions retain current Agent behavior. Final goal requires edition-aware Agent including notes; this temporary guard does not meet that final acceptance.

## Exclusive expected paths

- This handoff; settle Docs/Plans/HANDOFF-PLAY-run-local-content-editions.md with exact merged and later supplied runtime evidence (no invented delivery).
- NEW apps/live-control-ui/src/api/playRunContentApi.ts and .test.ts
- NEW apps/live-control-ui/src/playSurface/playRunContentTypes.ts
- NEW apps/live-control-ui/src/playSurface/playRunEffectiveContent.ts and .test.ts
- apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx and .test.tsx
- apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts and existing owning .test.ts
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx and .test.tsx (effective identity metadata only; notes writer unchanged)
- apps/live-control-ui/src/shared/SceneCard.tsx and SceneCard.adapters.test.tsx
- apps/live-control-ui/src/playSurface/playSurfaceAgentContext.ts and .test.ts only if needed for contribution guard
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx and WorldAgentConversation.planPlay.integration.test.tsx only if Page-level null registration cannot prove disabled transport; inspect actual existing test filename before using, return if different.

No broad liveApi.ts/types.ts registry, router/chrome/Plan editor, shared media/editor, server/schema/dependency or lockfile changes. Return exact path questions before widening.

## Verification and completion

Actual API-shaped fixtures plus mounted Play page prove edition text/media/table/callout while origin unchanged; progress/notes refresh retains edition; newer source cannot force forbidden rebase; explicit provenance; wrong World/origin/hash fails; v1 unchanged; edition Agent no-network assertion. Test late World/Run A→B→A and errors. Typecheck/build/cumulative diff; one PR through commit/push/open; no merge by worker. Independent exact-head Architecture review. Existing API runtime adoption is PRIME-owned; actual disposable session edition read/reopen on normal5202 and desktop/narrow rendered evidence follow accepted UI delivery. No provider call, real user document edit, Graph publication or serving service restart by this worker.

Next bounded successor remains existing-scene Markdown/media Live editing with session-copy autosave/CAS, durable pending-command journal and recovery. Preserve this scope and report precise next seam, not another wide redesign.
