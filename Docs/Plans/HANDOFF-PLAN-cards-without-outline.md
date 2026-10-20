# Plan Cards opens a scene, without a redundant outline destination

Status: ACTIVE. User agreed to remove the outline/overview destination, retain
Document as the complete Plan and Cards as one editable scene. PRIME owns this
bounded UI slice. Base: b09046145 (fetched origin/main); topology serial, one PR.
Reused buddy-context-loop checkout; branch codex/plan-cards-without-outline.
Open PRs inspected, no overlapping active lane. Shared Contents predecessor settled.

## Exclusive paths
- This handoff
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/components/PlanCardDeck.tsx
- apps/live-control-ui/src/planSurface/components/PlanCardDeck.test.tsx
- apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx

Remove Scene outline from the shared thumbnail deck's Plan adapter. Resolve the
Plan cursor to a valid selected scene or first available scene, including stale or
null cursor cases; do not require saved verification to read the current draft.
Keep empty/invalid-card diagnostics and Document escape. The legacy standalone
projection's read-only hierarchy is not a live Plan destination once cursor resolves;
retain its isolated legacy interface in this slice, avoid unrelated test migration.
No editor remount, content/schema/API/provider changes. Scene changes are presentation
only; never alter Run progress or saved Plan. Existing Agent actions remain scoped
with selected card; diagnostics remain available for invalid/empty projections.

## Verification and delivery
Focused adapter, new real Plan integration continuity/default-scene regressions,
production build; inspect cumulative diff and independent Architecture exact-head
review before merge. Adopt existing5202 UI artifact preserving old assets. Verify
real Plan Cards direct-entry/thumbnail/Document continuity, collapsed Contents;
all13 protected saved-state responses unchanged. No API restart/provider calls.
Postmerge settle handoff and release lease. Record inherited tests honestly.
