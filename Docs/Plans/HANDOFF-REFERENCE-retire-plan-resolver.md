# REFERENCE: retire the unmounted Plan resolver

SETTLED: merged #2346 at60d28dda015c46ffd9e345f72bf48216684a30a3;
reviewed UI94f59ccba3ff6be5cf269d512769a5856f22490e delivered on5202.
Exact hosted/build passed. Full comparison removed exactly52 exclusive/obsolete
cases; shared statuses and collection error unchanged. Full diagnostic remains red.

Historical ACTIVE PRIME serial slice from d8f1bd8b92fc6b0d33217034d85a307466712403,
branch codex/reference-retire-plan-resolver in the existing context-loop checkout.
Predecessor #2344 is merged and UI-only delivered; no unmerged parent. Active
References goal authorizes this retirement. Index work belongs elsewhere;
coordination remains off and #2104 remains held.

The resolver provider and PlanReferenceProjectionBinding have no production
mount. Their graph/corpus fallback, relationship lookup and Plan request builders
are exclusive. Shared callers must survive: move the unchanged revision event to
worldGraph/worldGraphRevisionEvents.ts; GraphLoadPanel adopts existing shared
GraphReferenceProjectionState; derivedViewsAdapter adopts structurally identical
GraphReferenceCorpusFallback instead of retaining a dead resolver for its type.
Shared actions remain for threat sheets. Native preview and admission are untouched.

Expected exclusive writes: this handoff; settlement of predecessor
HANDOFF-REFERENCE-retire-plan-card.md and adoption inventory; UI planSurface/reference/
{PlanReferenceProjectionBinding.tsx,usePlanGraphReferenceResolver.ts and test,
graphAwareReferenceResolver.ts and test,resolvePlanRelationshipTarget.ts and test,
planGraphContextRequest.ts and test,referenceResolver.ts and test} deletion;
planSurface/projection/projectionBindings.test.tsx only exclusive retired renderer
cases/fixtures; graphLens/{GraphLoadPanel.tsx,useWorldGraphLensProjection.ts};
api/{liveApi.ts,liveApi.projectionAcquisition.test.ts};
planSurface/derivedViews/derivedViewsAdapter.ts and test; new existing-event owner
worldGraph/worldGraphRevisionEvents.ts; ci/test-classification.json five exact
retired entries. No current hosted selector references these files; frozen fixture
unchanged. No runtime, DB, provider, Index, workflow or generic provider changes.

The synthetic Plan compatibility descriptor and generic binding/provider tests
remain for a separate coherent authority-contract slice; do not claim complete
References closure. That successor must preserve generic native Build authority,
revocation and lease coverage while retiring implicit legacy Plan advertisement.

Invariant: preserve the event string and shared read invalidation, existing native
Plan activation, generic provider semantics and statblock owners. Failure cases:
dead imports, deleted shared event invalidating refresh, type drift or tests that
silently drop generic binding safety. Verify affected tests, CI guards/inventory,
exact-source hosted/build and full discovered comparison. Only the five exclusive
files and two retired Plan renderer cases may disappear; all other outcomes must
match or be diagnosed. Preserve prior failures and keep full diagnostics honestly
red. Independent exact-head review before merge and UI-only delivery. No API
restart/backend activation. Rendered journey proof remains open while browser
bridge reports no browsers/native pipe unavailable.

Expected full-diagnostic retirement:50 cases in the five exclusive resolver test
files plus2 obsolete Plan renderer cases. The first working-tree focused run
caught a removed useState import still needed by a surviving diagnostics test;
restored it and retained that original failure separately. No retired tests are
counted as passing coverage.
