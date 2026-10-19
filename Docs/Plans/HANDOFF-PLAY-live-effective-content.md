# PLAY — effective session-copy content projection

Status: MERGED #1425 at e12b59363b7abace631607f4223bfb2b55c3bf3d; Architecture Cycle2 source PASS. Rendered delivery HOLD pending the bounded notice repair below. Original DOGFOOD lease ended.
Base origin/main7b73ffb07d21899c9007035a4b93ee9dcd455d18; branch codex/live-effective-content.
Topology serial successor of merged server PR1422. PRIME assigns DOGFOOD exclusive implementation ownership of the existing buddy-context-loop checkout/paths below; PRIME and Architecture read/review only. PRIME separately owns private runtime/schema adoption on8000 behind5202. That operational work does not change this checkout. No new checkout/env/source export or /tmp task directory. Existing dependencies/private evidence directory reused. Architecture independently reviews; PRIME merges/delivers.

## Outcome and invariant

Load and honestly project the effective content of a World-owned grammar-v2 session: its immutable original pin before editing, or its versioned session copy after editing. This is the read-adoption predecessor to Live editing/autosave, not completion of that user goal. Plan fully replaces legacy Prep; visible mode terminology Plan/Live. Preserve original Run pin/manifest/progress/notes. Existing v1/campaign behavior unchanged.

GET the authenticated1422 content endpoint using existing authenticatedApiFetch/LiveApiError patterns. Validate schema, World/Run, exact origin tuple, nonnegative edition N and nullable/positive edition UUID relation, exact UTF8 SHA256, structure witness and timestamps. Effective text is neither a forged WorkRevision DTO nor a replacement for original provenance. Fail closed on missing/corrupt edition; no quiet fallback. A newer Plan/Runbook is informational; an edition-bearing Run must not enter the old latest-Runbook rebase-required path.

Owning seam is PlaySurfacePage.loadExactRun: retain origin fetch/manifest admission, then admit effective content through the existing native parser/derivation. Feed one effective projection pipeline through progress/notes updates; do not revert to origin text when overlayRuntimeOnV2Ready runs. Keep original Run identity and note-cache key stable across edition changes; effective-content identity is separate. Preserve current/inspected scene and clamp only if absent.

SceneCardIdentity needs explicit run-edition state/descriptor: label Session copy · revision N, separately retain From Plan version M provenance. Do not substitute edition UUID into WorkRevision ID. Unsaved drafts/writers are a later bounded slice.

Agent context currently reads original pin server-side. For an effective edition, clear Play conversation registration/current-moment contribution and show explicit temporary unavailability for session-edited material. Prove composer cannot send postWorldPlayAgentTurn under that state, including late history/in-flight responses; do not leak edited titles as if Agent sees them. Pinned unmodified sessions retain current Agent behavior. Final goal requires edition-aware Agent including notes; this temporary guard does not meet that final acceptance.

## Exclusive expected paths

- apps/live-control-ui/src/api/liveApi.ts and liveApi.test.ts (PRIME narrow amendment: only authenticated content/current/history/command path admission through existing credential machinery and owning auth-path tests; no DTO/registry/writer changes).
- Docs/Roadmaps/ROADMAP-demo.md (PRIME amendment: current server1422 row and next-action settlement only).
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


## Implementation evidence — 2026-10-18

DOGFOOD implemented the bounded read-adoption and provenance guard in the leased
UI paths. Effective content is strictly validated against the existing Run pin,
then projected through the native v2 parser/index while preserving the original
Run and structure. Scene metadata now distinguishes session-copy revision/hash
from Plan origin. Progress refreshes preserve the admitted edition. Edition-backed
Play explicitly disables Agent transport and clears its context; tests prove a
late history result and late reply cannot restore the composer or send. The narrow
credential-path amendment is covered by the owning auth tests. No server writer,
service, provider or user-owned document was changed.

Focused owning command covered eight suites: 330 passed; the shared
`WorldAgentConversation.planPlay.integration` suite reports seven failures. The
identical seven failures reproduced with the suite and host restored from
`origin/main` (38 passed, seven failed), so they are inherited Build/conversation
expectations; both new edition transport-race tests pass. The other seven focused
suites pass. `npm run typecheck`, production build (existing chunk-size warning),
and `git diff --check` passed. The full branch→base cumulative review and one
Architecture cycle are still required before delivery. Rendered desktop/narrow UI
acceptance is not claimed; it remains part of PRIME's post-review 5202 delivery.

## Verification and completion

Actual API-shaped fixtures plus mounted Play page prove edition text/media/table/callout while origin unchanged; progress/notes refresh retains edition; newer source cannot force forbidden rebase; explicit provenance; wrong World/origin/hash fails; v1 unchanged; edition Agent no-network assertion. Test late World/Run A→B→A and errors. Typecheck/build/cumulative diff; one PR through commit/push/open; no merge by worker. Independent exact-head Architecture review. Existing API runtime adoption is PRIME-owned; actual disposable session edition read/reopen on normal5202 and desktop/narrow rendered evidence follow accepted UI delivery. No provider call, real user document edit, Graph publication or serving service restart by this worker.

Next bounded successor remains existing-scene Markdown/media Live editing with session-copy autosave/CAS, durable pending-command journal and recovery. Preserve this scope and report precise next seam, not another wide redesign.

## Rendered follow-through: visible availability notice

PRIME owns serial branch codex/live-session-copy-notice from e12b59363. Exact
repair lease: this handoff, PlaySurfacePage.tsx and its owning test only. Actual
normal5202 rendering showed edition2/media/Plan-origin cues and Graph Ready, but
the conversation host's temporary-unavailable notice was below the800px viewport
(top800/bottom823), with the launcher absent. PRIME restored the previous UI index
while retaining0035/API/session editions. Add an inline status next to the source
cue before the cockpit, preserve the existing transport guard, and verify visible
normal5202 desktop/narrow notice, real images/reopen and unchanged Run/Plan/notes.
Owning tests prove the notice precedes session prose and is absent for unmodified
sessions; typecheck/build/diff, independent exact-head review, one corrective PR,
then reversible delivery. No new capability, server or data mutation.
