# PLAY — understandable session entry

Status: COMPLETE — PR#1423 merged at `8dd30d111a220bd469436b7c1a90f845d4a63a4f` and delivered on5202. Implementation/write lease ended. Reconciled2026-10-18.

Current disposition: Architecture independently passed49 tests and rendered evidence. Delivered5202 with normal Graph Ready; full real Edge Run before/after equality verified. Session-copy server PR1422 was not adopted by this delivery. Remaining work requires its own bounded successor; this document grants no continuing lease.

Base: origin/main 3dfa43f946837d4ffb1a1a1d3c84b33d497e0b31.
Topology: parallel-independent of server PR1422; same checkout reused serially after DOGFOOD released its clean checkout. PRIME owns implementation; Architecture reviews exact head. Branch codex/play-session-entry. No API/schema or serving-state writes during implementation.

## Outcome and invariant

Show a readable session entry with Plan/Runbook title, local last-played timestamp and note count. Offer a primary Resume session action for the verified active session within the selected Plan, or newest matching session. A selected Plan scopes the main list; other sessions remain available under a disclosure. Put starting a new session behind an explicit secondary disclosure when sessions exist. Technical UUIDs and pin details are disclosure-only. Opening the chooser performs reads only; resuming preserves the existing Run/notes/pin and uses existing validated admission/navigation. Never auto-create, repin or choose an unrelated session. Missing title metadata must not block resuming. Stale World results must not paint a new World.

## Exclusive paths

- This handoff
- apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
- apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx
- apps/live-control-ui/src/playSurface/StartRunPanel.tsx (display copy only)
- apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx (copy assertions only)
- apps/live-control-ui/src/playSurface/playSurface.css

No worker edits these paths. Existing server PR1422 remains read-only by pinned SHA; no adoption of its schema in this slice. No new checkout/env/source export. Existing dependencies and private evidence location reused.

## Verification and delivery

Owning page tests: readable labels, selected-Plan filtering, active/newest recommendation, date/notes, metadata failure, late World response, explicit resume opens exact Run without creating one. Preserve existing admission tests. StartRunPanel copy tests, typecheck/build, cumulative diff. Independent exact-head Architecture review; PRIME merge and static UI adoption on5202. Render real Edge entry on desktop/narrow, verify readable primary action and retained notes/pin; no generation or real session mutation beyond an explicitly selected existing session.

## Pre-review evidence

49 owning-page/start-panel tests pass. UI typecheck/build pass; existing bundle-size warning remains. Real Edge read-only preview shows the actual active Run9a2af4d9 with title and one saved-note entry, other Plan/test sessions collapsed. Desktop and actual433px narrow screenshots retained under the current Codex visualization directory; narrow document width equals433px, no horizontal overflow. Port5210 preview Graph auth is unavailable at that origin; this is chooser rendering/read-only metadata proof, not normal-origin Graph auth proof. Final5202 proof follows accepted-head delivery. Before-state entire real Edge Run retained privately for exact after comparison. No Run or note was created/edited.
