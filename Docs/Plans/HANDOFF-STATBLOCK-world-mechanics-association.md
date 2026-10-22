# STATBLOCK — explicit World mechanics association

SETTLED. #1582 merged b5fc320c9cad2e8958499b8419404e3323c39c81 and runs8000/5202.
Bugbot approved b74583cd7270748619211513d447d458587495ee after fixing cross-tab
recovery ownership (Web Locks and exact stored-body comparisons). Independently12
UI/API and19 backend tests passed. Ordinary Build associated real saved mechanics
with the selected existing World NPC; native head/exact DMS identity unchanged.
Restart preserved1488 APP rows and59 product files; normal history/Load creatures
reopened version1. Combat consumption remains separate.

Historical scope: PRIME owned design, implementation, exact-head merge and guarded
adoption under the preparation/play goal. Basee8e1514566fc401375f2d160fedfabd2160788ba;
reuse buddy-context-loop, codex/world-mechanics-association. Serial one PR; checked
open work has no competing association/schema lease. Architecture chat01a086f2
reviewed the boundary and invariants on2026-10-22.

Prerequisite: real Build generation→manual edit→AI revise→review→validate→accept,
exact DMS integrity and ordinary Tools/history reopen passed. API restart retained
1487 APP rows and59 product files.1581 corrected saved-state wording and runs5202.
Old original revise remains unresolved and unchanged; it grants no authority here.

One capability: explicit GM association of a proven accepted World-only draft's
immutable six-field DMS mechanics locator with a selected existing World creature.
Buddy APP PostgreSQL owns it; no native Graph binding/mutation or fake campaign.
One current mechanics association per(managedWorld,nodeID); replacement explicitly
appends slot versionN+1 referencing prior association. No multiple form/role slots.
Current means latest APP slot version, not cross-service currentness or atomicity.

Request captures UUID idempotency key, current draft version, exact selected node,
managed→native mapping/version, observed Graph revision and expected slot version
(0 absent). Same canonical request/key returns exact historical receipt before
external reads, marked replay; changed body409. Transaction advisory lock and DB
uniqueness arbitrate slot/key races; external calls stay outside that transaction.
New writes require mechanics_saved draft, reconciled+attached acceptance operation,
exact locator/candidate/source-version provenance (accepted_from_draft_version is
not current draft CAS version), exact DMS revision contract/digest integrity, typed
current managed projection matching selection, and final draft/mapping checks.
Final draft CAS holds its existing filesystem store lock through the short APP append
(file→APP lock order; no external IO inside). APP records preserve actor/time and immutable proof, request digest and lineage.
Unavailable/corrupt proof is an error, never absence. Historical Graph witness is
honest; Combat later rechecks current mapping/head/node and never follows latest
mechanics. No cross-filesystem/Graph/DMS/APP atomic commit claim.

Reusable Workbench panel: explicitly Load creatures, select exact typed node, then
associate/replace. Retain exact UUID/body through lost acknowledgement and reload;
Resume uses same request. Browser Web Locks serialize reservation and cleanup;
full stored-request equality prevents overwriting or deleting a different view's
recovery request. Check view lifetime after lock acquisition; unavailable locking
fails closed. Stale conflicts require explicit refresh/reconfirmation.
No name inference, automatic retry with new IDs, implicit publish or old-journal
repair. Combat snapshots/consumption are next serial slice, not this PR.

Exclusive writes: new src/application_state/world_mechanics/{__init__,types,service}.py;
additive migration0043; new services/world_mechanics_associations.py and
routes/world_mechanics_associations.py; threat_draft_store.py read-only locked snapshot; main.py router registration; new UI
statblocks/WorldMechanicsAssociationPanel{,.test}.tsx, api/worldMechanicsTypes.ts,
liveApi.ts functions/auth prefix, api/worldMechanicsApi.test.ts, Workbench panel registration; owning PostgreSQL,
HTTP and UI tests; this handoff, saved-state-copy predecessor and ROADMAP-demo.
No provider/model/dependency/accepted-digest changes, arbitrary caps, legacy paths,
new checkout, product data rewrites, native Graph writes or Combat actor changes.

Verify real disposable PostgreSQL append/replay/conflict/concurrency/scope/history,
HTTP proof admission/tamper/missing/corrupt/stale mapping/head/draft tests, UI exact
selection and retained retry across reload/ABA, typecheck/build and Bugbot cumulative
review. Guard additive migration with protected-row/file fingerprints and rollback
before live writes. Actual normal UI associate→reload→API restart same association,
unchanged native head/DMS accepted identity and all prior state. No J1–J6 award.
