# REFERENCE: retire the unmounted Plan canvas and old object picker

Status: ACTIVE. PRIME owns one serial PR from `be0ebf6c99f3d4b03b5810aa7e0a1ccc33ee35b0` (re-anchored after CI2284 merged), branch `codex/reference-retire-legacy-plan-picker`, existing buddy-context-loop checkout. No unmerged parent. Independent review and CI precede delivery.

## Outcome and caller proof

After native activation adoption, the mounted World-owned Plan route imports only PlanSurfaceCanvasFrame from the old canvas module. The only other external frame consumer is GraphReferenceContrast.stories.tsx. PlanSurfaceCanvas itself has only two test consumers. Its PlanWorldGraphObjectsPanel is the only remaining production-source caller of GraphReferenceSearch; the search utility/type serve that widget only. Preserve the exact frame function and its CSS dependencies in a focused module. Remove the unmounted canvas, its private insert gate, old object panel/search closure, and tests that exercise only those retired paths. Do not keep aliases or re-exports.

These files form one removal closure: leaving the private picker/search/gates after deleting their only caller would preserve competing reference paths without a runtime purpose. This slice does not remove unrelated legacy graph resolvers or dogfood panels whose caller audits remain separate.

## Review map and exclusive write lease

1. apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx → PlanSurfaceCanvasFrame.tsx: retain the frame body byte-for-byte; delete the unused canvas/authoring/insert code.
2. PlanSurfacePage.tsx and ui/GraphReferenceContrast.stories.tsx: change only the frame import path.
3. planSurface/components/PlanWorldGraphObjectsPanel.tsx; graphReference/GraphReferenceSearch.tsx and searchGraphReferences.ts; graphReference/types.ts, index.ts and graphReference.css: delete the private picker/search closure, unused exports/type and picker-only styles. Source audit finds only arbitrary test tool IDs bearing the old name; no remaining rendered class uses these selectors.
4. Delete PlanWorldGraphObjectsPanel.test.tsx, PlanSurfaceRunbookAuthoring.test.tsx, PlanAgentReviewedEdit.integration.test.tsx, GraphReferenceSearch.test.tsx and searchGraphReferences.test.ts. Their subject is the removed non-World canvas/picker, not the current route.
5. ci/test-classification.json: remove exactly the five deleted test files from their assignments; preserve every other assignment, classification basis, runner, validator and selection contract.
6. This handoff and truthful backward-looking settlement of HANDOFF-REFERENCE-plan-native-links.md.

All paths above are under apps/live-control-ui/src unless stated otherwise. No API, schema, database, dependency, workflow or user content writes. CI2284 merged during review and now rejects stale test-file assignments. The removal necessarily updates its inventory for exactly these five retired tests; it does not activate the CI successor, alter lanes/selectors, or touch commands, workflows, validators or CI design. This is a coupled retirement correction, independently reviewed with the removal. Held2104 owns the uncalled server proposal producer, its liveApi wrapper and server tests; none are touched or resumed. Play2172 remains held. Coordination with ADVERSARY remains off.

## Preserved invariants and verification

Current World Plan authoring uses its own writer/identity and is covered by PlanSurfacePage.test.tsx: Save/reload, pending recovery, exact committed basis, document switches, reviewed changes, stale targets, blank drafts, cards and conversation preservation. Native activation/editor affinity is covered by WorldPlanGraphReferenceActivation.test.tsx; Build guards remain in BuildReferenceCapability.test.tsx. Native object/source/statblock ownership remains exercised in their shared suites. Do not port old producer behavior into these owners merely to retain test counts.

Search all source/scripts/workflows for removed symbols, run the unchanged CI inventory validator and its contract tests, compile TypeScript/build, run current route/native/Build/reference owner suites and inspect cumulative diff. Independent review must check the caller closure, retained frame equality, test-to-owner mapping and held boundaries. No new test duplicating a pure frame move is required. Existing release technical evidence for native activation remains valid only for its own pinned runtime; this cleanup does not claim a newly delivered revision before activation.

## Predecessor

#2283 source `25969a83f45377e4aa291a9d2d08c731a2045c8d`, merge `9193d54ca874240ec181a47e8964905028794e05`, UI `2baeb50af8c7ace8b74b8ece4077232407292cd2` delivered. All180frozen owner tests and CI passed. An isolated actual Plan node/provider performed real authenticated native and exact retained statblock reads without write endpoints. Live retained legacy references accurately report unavailable and return focus; none of those IDs occur in the current native catalogue, so no by-label replacement was attempted. Retained APP/Core rows and sessions unchanged; lease released. These qualified results do not establish full References/held Play completion.
