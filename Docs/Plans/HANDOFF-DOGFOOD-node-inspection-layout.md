# DOGFOOD — node inspection layout

Status: ACTIVE, direct operator defect report: Karsemine card overlaps Author Node.
Base: merged PR881 at4dd785a0baecc713fddcfaa6d7b31e96832ae7e9. Branch codex/dogfood-node-inspection-layout; serial successor, one PR.
Write lease: this handoff; planSurface/graphPreview/WorldGraphRecapProjection.tsx; planSurface/planSurface.css, only scoped published recap inspection rule; WorldGraphRecapProjection.test.tsx owning regression (PRIME extended lease). Active PR869 checked, no stylesheet/component overlap; PRIME notified before edit.
Invariant: while a node card owns secondary context, published Author Node fixed toggle/drawer do not overlap it. Keep authoring mounted and preserve draft/open state; closing inspection restores prior authoring chrome. Exact-run authoring unaffected.
Runtime: owned DOGFOOD UI5202/API7866; UI hot reload only, no restart/provider/Graph writes.
Verification: owning mounted regression passes using actual scoped CSS: keyboard/accessibility suppression, relationship expansion, same drawer identity/open state and staged draft count restored after close. Live Karsemine pill open, selected object and relationships visible, author toggle suspended; close restores toggle, screenshot evidence and cumulative whitespace/diff review.
