# Plan Cards opens a scene, without a redundant outline destination

Status: COMPLETED; exclusive source lease released. User agreed to remove the outline/overview destination, retain
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

## Settlement — 2026-10-19
Architecture Cycle1 approved136f83dee9f2db46515160eb96d665dae969c925;
PR1476 merged3ecc12c240ddc066dbe5b4416f9a96d3f0775572.
Both new owning integration tests and9 shared/deck tests passed, independently
rerun by Architecture. Build passed (existing chunk-size warning); integration
emits React act warnings. The18 legacy integration cases were not run/migrated;
this does not claim their suite is green.
5202 indexSHA256 cc68a9961a6c0803e43da5513f7b256b8f3cb19925e11ed7163392fb5f841527.
Real Plan direct Cards entry shows editable Journey north, no Scene outline button
or Plan cards overview. Selecting First sight and Document/Cards retains selection;
book collapse/keyboard expansion works. At666px selecting Journey north dismisses
Contents, returns focus to book, and Document/Cards retains it; no page overflow.
Browser HTML comparison differed due editor presentation state; no HTML-identity
claim is made. New owning integration separately proves editor identity, draft JSON,
media settings, caret through disclosure/views, and undo with no commits.
All13 protected responses unchanged after rollout and browser checks. No API restart
or provider call. QA closed, viewport reset, original scene restored in QA.
