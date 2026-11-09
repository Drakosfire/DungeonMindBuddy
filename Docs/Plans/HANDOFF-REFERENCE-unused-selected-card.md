# REFERENCE: retire the unmounted selected-object card

Status: ACTIVE preparatory source retirement. PRIME owns one serial slice from
verified main b4ccdd1ea74d569b7284ef9410338b488bcd167f on
codex/reference-retire-selected-card in the existing buddy-context-loop checkout.
No unmerged parent or runtime lease. Recovery, coordination-off and2104 holds stay.

## Outcome and reviewed boundary

Independent scope review confirms SelectedObjectCard has no production mount.
Its private actions, source-preview renderer and roll formatter are consumed only
by that component. Remove this unused presentation leaf, not the registered
Graph-reference capability. No renderer, descriptor, provider callback, binding
or authorization contract is removed in this slice.

Keep selectedObjectCardModel.ts and its nine model tests: the registered
PlanReferenceObjectCard's corpus fallback still consumes that model. Keep the
shared host, tool/epoch/revocation behavior, PlanReferenceProjectionBinding,
resolver, diagnostic panel/report, native references and saved-statblock owners.
The larger capability closure must stay coherent and requires the owning frozen
CI contract decision before retirement. This leaf is not full goal completion.

## Exclusive expected writes

Under apps/live-control-ui/src/planSurface/selectedObject delete:
- SelectedObjectCard.tsx and SelectedObjectCard.test.tsx
- selectedObjectActions.ts
- SelectedObjectSourcePreview.tsx
- formatResolvedRoll.ts

In selectedObjectCardModel.test.ts remove only the actions import and final
buildSelectedObjectActions describe block (six passing cases); preserve the first
buildSelectedObjectCardModel describe block byte-for-byte except the unused import.
In planSurface/planSurface.css remove only flat rules whose selectors all start
with .plan-selected-object. Preserve adjacent plan-reference-object-card styles
used by retained projections and every unrelated rule.

Remove only SelectedObjectCard.test.tsx from ci/test-classification.json under
the exact-retired-entry partition in HANDOFF-PLAY-shared-native-retrieval.md.
CI2288 head657def68f68bfffca839c92549146c8ded1044e0 retains additive infrastructure
ownership. Frozen contracts/fixture/guard remain unchanged; neither exclusive
subject is in the original commands. This handoff and the existing adoption
inventory record the newly proved leaf boundary; no new registry or shim.

## Verification and serial continuation

Parent frontend tree equals the retained93f8f2ac3 diagnostic:17 component cases
and six action cases pass; the nine retained model cases pass. Verify raw hashes
and actual imported-symbol/private-CSS closure before removal. Afterward inspect
all deleted subjects, retained model/body, classification delta and cumulative
diff. Run nine CI command/inventory guards, exact-head local hosted frontend/build
and immutable evidence validation, then the discovered diagnostic. Account for
exactly23 passing removed cases and no other losses. Preserve all unrelated red
failures and investigate any new failure rather than suppressing it.

Obtain independent exact-head Bugbot review, push/open the owning PR and merge
under standing PRIME authority when source gates pass. Source-only removal needs
no migration, provider, browser storage, service, database or user-data action.
Next reassess the atomic registered capability closure only with its CI owner
contract settled; do not delete a renderer while leaving usable advertisement or
invent a compatibility wrapper to get around that dependency. Protected runtime
activation and controlled verification remain separate, held goal requirements.
