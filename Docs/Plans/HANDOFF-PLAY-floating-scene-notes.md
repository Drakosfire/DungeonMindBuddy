# PLAY: viewport-anchored current-scene notes

Status: ACTIVE. PRIME adopts Architecture's 2026-10-18 examination and the operator's explicit shared-writing-system goal. First independently useful slice: prominent Live notes, preserving their proven writer.

Base: origin/main 383fd4620befa3730fee83e468d17bde12bda4b6. Existing buddy-context-loop checkout, branch codex/play-floating-scene-notes. Serial one PR. Architecture's fetched current-main/open-PR census found no active shared-workspace implementation. Historical Play cockpit reservations are superseded for these exact paths by PRIME's current operator-authorized slice; preserve old branches, unrelated work and existing runtime. No new checkout/environment.

Exclusive expected writes:
- This handoff.
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx and .test.tsx.
- apps/live-control-ui/src/playSurface/currentMoment/FloatingSceneNotes.tsx, .css and .test.tsx.

Keep the current scene note immediately reachable through a stable viewport dock, collapsed by default with scene title and save/attention state. Opening/closing is view state only. Bind to the current Scene, not the inspected Scene. Preserve exact existing draft/cache/450ms debounce/Run progress CAS/ack/recovery paths and intentional empty notes; relocate controls without another store or writer. Keep the mounted form while collapsed. Escape closes and returns focus; no keyboard trap. Account for narrow viewport, safe areas, Agent launcher and compact scene/outcomes panels. No API/types/schema/global-style changes, provider calls or Agent integration.

Verification: existing actual cockpit note-writer tests remain green, plus presenter and mounted-cockpit checks for collapse/reopen, target identity while inspecting, current-scene changes and no writes on opening/closing. Typecheck/build/diff check and independent exact-head Architecture review. Rendered desktop/narrow disposable-Run note save/reopen/reload with retained scene/pin/progress and keyboard access; preserve real Edge notes. Deliver accepted assets to established 5202 with rollback retained, no API restart.

Architecture recommendation for later Live content edits: versioned Run-local edition retaining original Prep/Run pin; operator decision pending. This notes slice neither adopts nor implements that new server contract. Shared media projection is subsequent. Hosted auth, ingestion and structural Live scene edits are outside this lease. Earlier 1419 callout repair merged at 383fd462 and its implementation lease has ended.

Settlement: this lease ends after accepted merge/delivery. Goal remains open until the full shared-writing-system acceptance passes.
