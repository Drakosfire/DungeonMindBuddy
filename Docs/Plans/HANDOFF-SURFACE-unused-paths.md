# Surface unused-path cleanup

Status: ACTIVE. Operator authorizes the same cleanup/review/merge/5202 pattern
across all surfaces, with no backwards compatibility. PRIME/Buddy UI owns this
serial, finite no-behavior slice. Base cd54c10eb110207824291d22409c75ab5885fc81;
branch codex/remove-unused-surface-paths; reused buddy-context-loop checkout.
Architecture read-only invariant/candidate critique accepted before activation.

## Removal map and current replacements

| Candidate | Callers/replacement | State / writes |
|---|---|---|
| Zero-consumer chrome alias, old ingest status panels, Plan Edit bar, MarkdownEditor wrapper, unused URL hook | No runtime/test/story/HTML/script consumers; current chrome, IngestionModule, EditHost, MarkdownEditorCore and workspace authoring remain | No reachable state owner removed |
| GraphPreviewProjection + SourceExcerptPanel; RecapGraphProjection + recapMarkdown/parser tests | Disconnected clusters; current GraphProjectionReader, WorldGraphRecapProjection and exact-run review remain | Removed tests exclusively describe removed parser; no source/data API removal |
| Plan-local graphLens reexports and World Graph adapter wrapper | Every runtime/type/test consumer switches to identical canonical graphLens/worldGraph functions | No wrapper semantics, save owner, URL behavior or publication changed |
| recapGraphNodeRuntime and GraphNodePresentation forwarding aliases | GraphProjectionReader type switches to GraphNodeChipDeltaPresentation; GraphReviewProjectionLane uses shared GraphNodeHoverToken/presentationForNodeId | Dead empty getter/setter facade removed; current provider/reader retained |
| Build controller creatableCampaignIds return property | No production consumers; tests assert equivalent canonical destinationOptions | Internal admissibility calculation and suggested destination stay unchanged |

## Census, ownership and exclusions
TS AST import census:926 source/test/story files,473 production-reachable from main.
Checked sole Vite HTML entry/static plugin, literal/dynamic imports, barrels, type
imports, public/static scripts and shell/test consumers. Exact private census and
import map: established jev-evidence-loop-20261016 surface-cleanup-*.json. File
names shared with backend Python classes are not consumers of the removed TSX.
Open1188/1190 are historical welcome proposals, not active dispatch authority per
current roadmap; none of their changed source paths is leased here. Combat1367 is
a doc-only acceptance gate; current /combat static tracker remains live.
Live LegacyProjectionHostAdapter, route publications, shell/module registry, current
Ingest/exact-run readers, campaign APIs, grammar parsers, data/storage keys, developer
spike route and planned UI prototypes remain outside this removal slice. Disconnected
GraphReview rendering clusters require a separate equivalence map and are not leased.

## Exact exclusive write lease
- This handoff
- apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.test.ts
- apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts
- apps/live-control-ui/src/chrome/AppChromeGraphLens.tsx
- apps/live-control-ui/src/modules/AuthorityTransitionPanel.tsx
- apps/live-control-ui/src/modules/IngestionModule.tsx
- apps/live-control-ui/src/modules/SpellingAuditPanel.tsx
- apps/live-control-ui/src/planSurface/PlanAgentReviewedEdit.integration.test.tsx
- apps/live-control-ui/src/planSurface/PlanGraphLensContext.tsx
- apps/live-control-ui/src/planSurface/PlanSurfaceRunbookAuthoring.test.tsx
- apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
- apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx
- apps/live-control-ui/src/planSurface/ReviewCampaignPicker.tsx
- apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.test.tsx
- apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
- apps/live-control-ui/src/planSurface/components/PlanEditBar.tsx
- apps/live-control-ui/src/planSurface/components/PlanGraphLoadPanel.tsx
- apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx
- apps/live-control-ui/src/planSurface/components/PlanWorldGraphObjectsPanel.tsx
- apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts
- apps/live-control-ui/src/planSurface/config/planSurfaceConfig.ts
- apps/live-control-ui/src/planSurface/dogfood/GraphObjectDogfoodPanel.tsx
- apps/live-control-ui/src/planSurface/graphGoldReview/GraphGoldReviewModule.tsx
- apps/live-control-ui/src/planSurface/graphGoldReview/GraphGoldReviewSessionPicker.tsx
- apps/live-control-ui/src/planSurface/graphPreview/GraphNodePresentation.tsx
- apps/live-control-ui/src/planSurface/graphPreview/GraphPreviewModule.tsx
- apps/live-control-ui/src/planSurface/graphPreview/GraphPreviewProjection.tsx
- apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx
- apps/live-control-ui/src/planSurface/graphPreview/RecapGraphProjection.tsx
- apps/live-control-ui/src/planSurface/graphPreview/SourceExcerptPanel.tsx
- apps/live-control-ui/src/planSurface/graphPreview/recapGraphNodeRuntime.ts
- apps/live-control-ui/src/planSurface/graphPreview/recapMarkdown.test.ts
- apps/live-control-ui/src/planSurface/graphPreview/recapMarkdown.ts
- apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewProjectionLane.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAuthority.ts
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts
- apps/live-control-ui/src/planSurface/planGraphFocusOptions.ts
- apps/live-control-ui/src/planSurface/projection/projectionBindings.test.tsx
- apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts
- apps/live-control-ui/src/planSurface/reference/resolvePlanRelationshipTarget.ts
- apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts
- apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.test.ts
- apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.ts
- apps/live-control-ui/src/planSurface/sessionCampaignContext.ts
- apps/live-control-ui/src/tiptap/MarkdownEditor.tsx
- apps/live-control-ui/src/tiptap/descriptors/tiptapRunbookDescriptors.ts
- apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentUrlSelection.ts
- apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.planCard.test.ts
- apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.test.ts

## Gates
Inspect cumulative base-to-head diff; negative retired import-path fitness scan;
production build/typecheck with honest baseline failures; canonical graphLens,
worldGraph/reference/XSS and current Plan/Play/Build/Ingest owner tests, actualApp
route/context smoke. Preserve semantic adapter assertions at canonical owner; retire
only migration-structure assertions about removed wrappers. Browser all-current-
surface scoped smoke and16 protected-state responses unchanged; no provider or
extraction/commit call, API restart, data deletion or conversion. Independently review
exact head, merge, guarded5202 artifact adoption and truthful settlement/lease release.

## Owning-test repair amendment before edits
Baseline typecheck passes;35-file cohort390pass/2fail. Extend lease to
apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.test.tsx and
apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.test.tsx
for obsolete host/callout assertions only: Build lacks current Peek host, and reader
expects aside instead of current collapsible details. Preserve actual scope and prose.

## Exact forwarding map
- planSurface/sessionCampaignContext.ts → graphLens/sessionCampaignContext.ts
- planSurface/planGraphFocusOptions.ts → graphLens/planGraphFocusOptions.ts
- planSurface/PlanGraphLensContext.tsx → graphLens/WorldGraphLensContext.tsx
- planSurface/components/PlanGraphLoadPanel.tsx → graphLens/GraphLoadPanel.tsx
- planSurface/reference/worldGraphProjectionAdapter.ts → worldGraph/worldGraphNodeViewAdapter.ts
- planSurface/graphPreview/recapGraphNodeRuntime.ts → graphReference/index.ts

Author verification: production TypeScript/build passed;36-file owner cohort396/396
passed, no skips. Reference/lease/source/draft/media supplemental cohort196pass/2fail:
2 old graphAwareReferenceResolver tests expect incomplete fixture nodes to resolve;
their test, adapter and canonical resolver files are byte-identical to the base.
No full-repository-green claim. All other reference/relationship, Build leases and
workspace Markdown/media authoring tests in that18-file cohort passed. Retired import
fitness scan:17 removed modules,0 remaining source/test/story path consumers.
