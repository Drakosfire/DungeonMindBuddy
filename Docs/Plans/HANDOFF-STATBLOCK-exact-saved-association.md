# STATBLOCK: associate the explicitly selected saved revision

Status: ACTIVE. PRIME owns design, implementation and delivery. Base
4b873f8d7216dadf3dc433d460c8b77e4921c7b2; branch
codex/exact-saved-mechanics-association; existing buddy-context-loop checkout.
Topology: serial, one coherent API/UI current-write contract. No unmerged parent.
The merged retrieval slices2251/2252 are delivered. Play2172/2104 holds remain.

Outcome: the shared saved editor associates its actual selected immutable
revision with an explicitly chosen native creature, including portrait successors.
No auto-publication or mechanics adoption into existing encounters.

Owners: statblock_saved_revision.resolve_saved_source proves original/successor
and exact DMS integrity; world_creature_selection owns native choice equality;
world_mechanics service owns append-only association CAS/idempotency. Remove
association orchestration's duplicate acceptance/DMS proof. No new store, Graph
publisher, candidate/provenance authority or current legacy writer.

New association requests must bind a complete explicit locator in their digest.
Retained historical requests/proofs remain closed read shapes with unchanged
request digests; two retained historical rehearsal rows make that necessary.
A no-op reader fence0135 follows0134; no rows are rewritten. Only current requests
may append. Read-only request lookup recovers obsolete pending acknowledgements;
never silently add a locator, reuse their keys for new requests or erase raw
recovery state. Browser CAS/locks protect reservations across tabs.

Move association controls from the original-acceptance Workbench-only location
into the shared saved revision editor. Use its exact opened locator, load current
draft CAS explicitly, preserve native catalog selection and current slot version.
Dirty/busy/pending image/Save work cannot be mistaken for a saved revision.
Preserve original/successor history, lost acknowledgements, stale conflicts and
explicit recovery. Native node previews and inline conversation hosting are
separate successors, not completion claims for this slice.

Expected writes: this handoff; src/application_state/world_mechanics/{types,service}.py;
src/application_state/migrations/versions/20261108_0135_exact_mechanics_association.py;
apps/live_control_server/{services,routes}/world_mechanics_associations.py;
apps/live-control-ui/src/api/{worldMechanicsTypes,liveApi}.ts;
apps/live-control-ui/src/statblocks/WorldMechanicsAssociationPanel{.tsx,.test.tsx};
apps/live-control-ui/src/statblocks/revision/SavedMechanicsRevisionEditor{.tsx,.test.tsx};
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule{.tsx,.test.tsx};
tests/test_world_mechanics_associations.py; tests/test_statblock_saved_revisions.py;
tests/application_state/test_world_mechanics_associations_postgres.py;
tests/test_combat_exact_world_mechanics.py; apps/live-control-ui/src/api/worldMechanicsApi.test.ts;
and directly owning reader-fence migration expectations if head advancement requires them.
No overlap with open local-World/ingestion/held Play work.

Verification: current/old model distinction and exact historical digest; actual
APP append/replay/slot CAS; selected successor through real saved-revision owner;
wrong World/locator/tamper/stale draft refusal; protected GM lookup; pending old
request read-only recovery and cross-tab conservation; shared-editor selected
revision and dirty/busy transitions. Owning tests, cumulative diff, independent
Bugbot and CI precede merge. Controlled delivery must preserve data and prove the
real ooze association by exact locator through ordinary controls. No paid model
or ingestion experiment, corpus edits, token caps or benchmark duplication.
Runtime8000/5202 remains untouched until a separately reviewed protected delivery.
Use existing APP test54329 and existing dependencies, no new environment.

Owning evidence before review:83 HTTP/APP/revision/encounter checks pass in26.26s;
151 existing Workbench tests pass and63 current picker/editor/API tests pass
(including exact successor, busy editor switch guard and read-only historical
acknowledgement). TypeScript+Vite build and targeted Python lint pass. Initial
failure logs retain a UUID boundary mismatch (corrected to typed UUID), missing
auth-test configuration, an obsolete Workbench placement expectation and a mock
HTTP Response missing text(). Evidence root: established runtime evidence,
exact-saved-association-{owning-tests-v2,ui-tests-v2,ui-tests-v4,build-v1}.log.
No primary/runtime writes or provider calls. Independent review/CI/delivery remain
pending; this evidence does not establish the full statblock goal as complete.

Shared schema allocation resolved with the owning retrieval steward: this
association slice owns shipping135 on134. Draft2253 remains experiment-only and
non-deliverable until its author rebases/renumbers its fence136 on the exact
merged association parent and requalifies that delivery head. No paid experiment
rerun is required solely for renumbering. There is no unmerged behavioral parent
for this association slice; ordinary review/CI gates still apply. No two fence
heads may ship. PRIME will return the exact association PR/head/merge revision.
