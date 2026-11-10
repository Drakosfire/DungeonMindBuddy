# REFERENCE: retire the obsolete Plan reference renderer

ACTIVE PRIME serial slice from b8c049283d90c1c79e7ac0fe9bb488ee16a65ce9,
branch codex/reference-retire-plan-card in the existing context-loop checkout.
The active goal authorizes References adoption/demolition; no unmerged parent.
Index/LocalWorld work is owned elsewhere. Coordination remains off; #2104 held.

Caller audit: the Plan-only legacy card has one catalog registration but its
opener/binding has no production mount. Live Plan links use the native activation
provider and NativeGraphObjectPreview. The corpus fallback/model are exclusive
to that card. Remove this renderer and its catalog entry, exclusive model/tests
and private styles. Retain the base .plan-reference-object-card grid/gap rule:
ThreatSheetProjection and GraphNodeHoverToken consume it. Keep shared GraphObjectCard, native preview, statblocks,
buildPlanGraphObjectActions and generic provider/catalog/binding contracts.
Do not retire the unmounted resolver or synthetic descriptor in this slice:
the successor must first move the surviving revision-event and type consumers.

Expected exclusive writes: this handoff; settlement of
HANDOFF-REFERENCE-retire-plan-checklist.md and HANDOFF-REFERENCE-unused-selected-card.md;
REFERENCE-adoption-inventory.md renderer decision; UI PlanProjectionCatalogRegistration.tsx
and projectionCatalogRegistrations.test.tsx, LegacyProjectionHostAdapter.test.tsx; deletion of reference/PlanReferenceObjectCard.tsx,
its test, buildGraphObjectCardFromCorpusFallback.ts, selectedObject/selectedObjectCardModel.ts
and its test; planSurface.css private .plan-reference-object-card block;
ci/test-classification.json exactly the two retired test entries. No current hosted
selector names these files; original frozen CI fixture remains unchanged.

Invariant: removal must not replace the live native reference route or remove
shared host/tool capabilities. Failure cases: dead imports, catalog still promises
a removed renderer, deleting shared statblock actions or provider lease checks.
Validate owning catalog/host/native activation/statblock tests, current CI inventory,
exact-source hosted/build and default-discovered comparison. Enumerate only the
retired exclusive tests and four obsolete renderer cases as expected removals;
other differences require diagnosis. Preserve inherited red diagnostic failures.
Independent exact cumulative review before merge and UI-only protected delivery.
No API/DB/provider changes; retain data/drafts. Browser bridge is unavailable,
so static/DOM proof does not establish rendered cross-surface journeys.

Working-tree diagnostics: first focused invocation ran from repository root and
missed the UI Vitest config (DOM/React errors); it is not qualifying evidence.
Correctly configured run passes native activation/preview/statblock tests. Two
legacy adapter tests depended on the retired card and retire with it; three
catalog Tools-toggle failures are present in retained parent full diagnostics.
No filtering or changes to those inherited failures.
