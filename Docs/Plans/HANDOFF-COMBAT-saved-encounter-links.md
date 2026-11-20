# Combat saved encounter links

ACTIVE under the user's Combat implementation, review and passing-merge
assignment. Root owns the isolated fc67 checkout on
codex/combat-encounter-links, based on e645b9385ded5d568458add2aebef06868b4b005.
Serial successor to the compact workspace PR #4274, merged at that base after
review of 2fc4cb49a518836f11558044f26a016c2f31fd73.

Deliver a standalone link to an exact saved encounter under an explicitly
selected World. Reuse the scoped roster and existing authorized Combat GET.
An invalid, duplicate or mismatched selector must never load a fallback
encounter. Back and forward navigation must take effect without a stale
roster. Previously committed revision and participant IDs are the future Map
and VTT read boundary. Keep that boundary private to Combat access.

Write lease: this handoff, Docs/Guides/GUIDE-combat-encounter-links.md,
apps/live-control-ui/src/combat/{CombatSurfacePage.tsx,
CombatSurfacePage.test.tsx,combatEncounterLocation.ts}, and
apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx. No backend,
auth, routing registry, schema, provider, storage, live state or deployment
writes. Open #3824 and #3716 remain read-only. Historical source publication is
the next serial slice and can use the resulting direct link.

Verify World admission, exact requested UUID, invalid selector refusal,
location changes, normal landing behavior, direct resource reopening and the
existing save/recovery lifecycle. Qualify the reviewed commit through the
repo frontend verifier and a browser exercise. No migration or backend
contract change.
