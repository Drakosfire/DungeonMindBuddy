# Manual scene editing in Plan Cards

Status: COMPLETED / SETTLED, 2026-10-19. No active write lease or successor
authorization remains. PRIME implemented the operator's requested
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

Historical implementation write paths (released): this handoff; PlanSurfacePage.tsx and its integration tests;
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

## Completion evidence

- Buddy PR #1463 merged at `09c841ac043e86bf2c63ea86376961ccaaada44b`.
  Accepted implementation head: `9a4154f05edb9964833cb959f3246000b7625029`.
- Two formal Architecture review cycles: Cycle 1 HOLD at `198b44046` for
  duplicated YAML frontmatter; Cycle 2 source APPROVE at the accepted head.
  The export helper now owns the single frontmatter envelope. Intermediate
  trailing-whitespace export rejection was also repaired before acceptance.
- Architecture independently reran 14 focused plugin/export and owning Plan
  tests on the clean accepted head; all passed. Bugbot found no remaining
  concrete defects. PRIME reported 15 focused tests and production build passing.
  The owning scoped test stops at prepare; durable acceptance is separate below.
- PRIME reported rendered 5202 acceptance using disposable YAML fixture
  `1770f158-c5ea-43c0-b54f-e72db26c17af`: actual typing, Saved status,
  scene/view navigation and reload retained text; existing media presentation
  changed and a saved-library map was inserted directly from Cards, saved and
  reopened. At revision 9, exactly one YAML envelope and two media objects were
  present, with exact untouched-scene and prefix bytes.
- PRIME reported desktop and 433px narrow acceptance: only the selected scene
  was visible, with no horizontal overflow. All 11 protected API records and
  the real Run review remained exact. No API restart occurred.
- Serving UI index: `a0580a69c2a86dbee4097fd6997e70a9e894020ee3abad0c94ab1bd34bf98877`.
  PRIME retains fixture cleanup and read-only state checks; this settlement
  neither performs those operations nor authorizes another capability.
