# Manual scene editing in Plan Cards

Status: ACTIVE, 2026-10-19. PRIME designs/implements the operator's requested
manual Plan Cards editing and media support, removing the metadata footer.
Serial successor to merged callout PR1462 (95effa264). Callouts passed independent
Architecture review cycle1 at e51cb51a5 and desktop/narrow reader/editor/Play
acceptance; 5202 index6ddcd0f3eb6ba13f9a79dfec6454d2452d907af43dd6c37099d87c90d7a667cf.
No predecessor source lease remains active.

Branch codex/plan-card-manual-editing from fetched origin/main95effa264, existing
buddy-context-loop checkout. One implementation PR; no backend/state schema change.
The canonical whole-document Plan editor, save adapter, draft/undo owner stay
mounted at a stable location. Cards hides unrelated roots using a scene identity
resolved in current editor state, and gates every resulting document against exact
prefix (through scene heading), suffix and playable anchor inventory. Scene title
and topology stay protected; existing scene body, choices, media, tables and
callouts are editable. Missing/duplicate scene fails closed. Document removes
scope. Navigation/presentation transactions never change JSON or save content.

Architecture design critique accepted: close history groups at scope transitions;
reject out-of-scope undo/redo with visible Document escape; preserve stacks on
rejection. Media capture version includes monotonic scene/view scope generation,
including ABA navigation. No broad programmatic bypass. Keep fidelity/recovery/save
warnings and Agent capability. No new card store or fragment writer.

Exclusive write paths: this handoff; PlanSurfacePage.tsx and its integration tests;
new planSurface/planCardEditing.ts and tests; components/PlanCardDeck.css;
components/WorldPlanCardProjection.tsx and tests as needed. Shared media bridge
changes only if owning-host tests identify a necessary invariant defect. No other
active lease overlaps (open PR scan before activation).

Verify mounted Plan integration: typing/autosave/reopen; media mutate/insert and
stale captures; navigation no writes; same editor through Document/Cards; exact
other-scene bytes; boundary selection/delete/paste/multi-step attacks; history
across A/B/view scope. Production build, exact-head Architecture review, rendered
5202 disposable material desktop/narrow; protected real Plan/Run/notes/reflections
retained. UI-only guarded atomic adoption using prior index above. No API restart.
