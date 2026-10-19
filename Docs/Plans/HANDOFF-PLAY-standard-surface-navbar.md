# PLAY — use the established surface navbar

Status: SUPERSEDED by [the compact-reader correction](HANDOFF-PLAY-compact-scene-reader.md). PR1431 merged6e9437546108579fdd0ffcab82b0a89df2f5ecdc and its UI is served on5202. Operator screenshots prove the shared projection but show excessive wrapping and repeated scene metadata; compact-layout acceptance is not complete. Original authority follows: Operator explicitly requests Play's surface-specific navbar using the existing standardized design, 2026-10-18. Base origin/main9c1f34b479a520d23186f32df5dd3d1dc15cf158; branch codex/play-surface-navbar; serial topology, one implementation PR.

PRIME adopts this contract. Fresh play_navbar agent owns the expected source paths in the existing buddy-context-loop checkout after this contract is pinned. Previous editing/contrast/settlement lanes are complete and their consumers released. Reuse this checkout and dependencies; no new checkout/environment/source export/tmp task directory. Architecture independently reviews; PRIME merges and owns normal5202 delivery and disposable browser acceptance. No worker runtime/data/provider/Graph writes.

## User outcome

Play uses the same SurfaceContextHost/contribution/module/action/select/status/popover primitives as Plan and Build. Do not invent a second toolbar/nav system, body-level fixed strip, global navbar rewrite or new event bus. Relevant existing reference: planSurface/components/PlanSurfaceContext.tsx and chrome/AppChrome.tsx. Shared primitives are read-only.

Primary controls on the standard surface row: Load, scene navigation, Notes. Existing Edit session and exact server saved timestamp should join that same surface row rather than remain in a separate body card header. Run record is rarely needed: move access into a secondary More popover and start its panel collapsed on desktop as well as narrow. Keep its retained data accessible. Remove duplicate primary body navigation controls; avoid raw UUID/revision metadata in the navbar. Use readable scene/session labels and existing styling, with only scoped layout CSS.

Load invokes the existing chooser/navigation path; it does not create a Run. Scene select and previous/next reuse existing inspection navigation; do not silently mark resolved, change the current scene/progress, or write on browsing. Make inspected versus current state clear and retain existing explicit return/current-setting actions. Expose Notes as access to the existing current-scene note dock/writer; label its target clearly when inspecting another scene. Do not retarget or rewrite note data. Scene outline may remain a secondary panel; default collapsed if navbar navigation makes its persistent body column redundant.

Control ownership stays at the owning controller: cockpit owns scene inspection/panels/current-note target and presentation open state; editor owns draft/save/edit state; Page owns loading/routing. Publish those existing actions through stable exact World/Run/original-pin surface contributions. No global DOM query/click bridge or stale callback registry. On route/World/Run changes, old controls/contributions must clean up; A→B→A late publications cannot resurrect old actions. Keep the editor and notes writer mounted while opening/closing navbar panels so drafts and pending commands survive. Preserve current server CAS/receipt/recovery and original Plan/Run pin.

Use controlled presentation props for FloatingSceneNotes only if needed; retain uncontrolled standalone compatibility. Shared SurfaceContextProvider/Host supplies placement and chrome measurement; no changes to its global semantics. Existing legacy/campaign behavior must remain usable; if a legacy deck cannot supply V2 scene controls, do not fabricate actions.

## Expected paths

- This handoff; Docs/Roadmaps/ROADMAP-demo.md (one current-state row/next-boundary update only).
- NEW apps/live-control-ui/src/playSurface/components/PlaySurfaceContext.tsx, scoped .css, owning .test.tsx (choose clear existing-context naming).
- apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx and .test.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx and .test.tsx
- apps/live-control-ui/src/playSurface/currentMoment/FloatingSceneNotes.tsx and existing owning .test.tsx
- apps/live-control-ui/src/playSurface/content/PlaySessionContentEditor.tsx and .test.tsx, playSessionContentEditor.css
- `apps/live-control-ui/src/playSurface/playSurface.css` — scoped duplicate-control/default-panel layout only; shared header/host layout remains read-only.

Shared chrome/context host/provider/primitives/registries, editor/media/parser internals, server/API/DTOs, note/content save controllers, dependencies/lockfiles and other surfaces are read-only. Return exact required path/invariant before widening. Tests should mount the real SurfaceContextProvider/Host to prove contributions land in the actual shared navbar; no fake local toolbar fallback just to satisfy old isolated fixtures. Adapt only leased test harnesses where needed.

## Verification and completion

Owning mounted tests: actual shared host contains Load/scene/Notes/Edit/saved timestamp; Load invokes existing chooser without create; scene select/prev-next inspect the intended scene and do not mutate progress; Notes opens the existing correctly targeted dock; Run record remains behind More/default collapsed; controls clean up on route/World/Run change; editor/note drafts and unknown save recovery remain intact while navbar/panels toggle. Keep the earlier 133+2 editing/Agent regressions meaningful; rerun affected suites, typecheck/build and exact cumulative diff/whitespace. No tests that merely mirror styles.

Finish implement→verify→cumulative review→commit→push→open one PR. Return exact head, evidence and limitations; no merge by worker. PRIME then verifies normal5202 desktop/narrow shared-nav placement, keyboard/touch access, no overflow, scrolled accessibility, notes/scene/load behavior and retained original Plan/Run/notes. Use disposable sessions; do not edit the real Edge session as a fixture. No broad Plan/Play workspace redesign or edition-aware Agent context in this slice.
