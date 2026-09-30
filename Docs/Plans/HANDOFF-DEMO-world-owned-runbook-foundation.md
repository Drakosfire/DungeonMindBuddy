# HANDOFF — DEMO: World-owned Runbook foundation

**Status:** ACTIVE — PRIME explicitly activated the Phase A lease
**Steward:** DEMO task 01a0efc8-f3a8-7be2-a556-33eb338338e8
**Repository:** Drakosfire/DungeonMindBuddy
**Pinned proposal base:** Buddy main at 36deec27e8a963cdb75bdb67609e15547786b446, the merge of #806
**Design predecessor:** #806, reviewed head 16974eee5f4904f907cdb4d57b170affa1107a15, merged at 36deec27e8a963cdb75bdb67609e15547786b446
**Architecture ruling:** ARCHITECTURE task 01a086f2-c457-7b10-b753-df6063cab1ce, 2026-09-30
**PRIME activation:** after #807 merged; explicit activation pins main at f59395a9c5677b1beb46402b7de6c148a5ef6e8d
**Implementation branch:** codex/demo-world-runbook-foundation in /home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy
**Topology:** Serial Phase A predecessor to Phase B in HANDOFF-DEMO-world-owned-play-runs.md; one open implementation PR for this workstream

PRIME explicitly activated this bounded Phase A lane after reviewing #807.
The implementation branch was created from the exact authorized main base
f59395a9c5677b1beb46402b7de6c148a5ef6e8d. The path allowlist below is now an
exclusive write lease. If a required path falls outside it, stop before editing
and return to PRIME for an explicit transfer or split.

## Capability and owner invariant

Persist a World-owned Runbook foundation that a later World PlayRun backend can
resolve from the Run's exact pinned artifact, committed revision, and content
SHA. Phase A establishes the owner chain only; it does not make a Play Run from
that Runbook.

1. A World-owned Runbook WorkObject has kind runbook, a nonblank world_id,
   campaign_id null, and target_session null. Existing campaign Runbooks keep
   their campaign_id and null world_id.
2. Every committed WorkRevision stores the same explicit world_id as its
   WorkObject. Campaign revisions keep world_id null. The revision owner is
   verified against its WorkObject when an exact revision is resolved.
3. The exact resolver takes the Runbook ID, revision number, and expected SHA.
   It returns the owner stored on that exact revision and fails closed on a
   missing or mismatched owner, artifact, revision, or digest. A requested
   World may be checked as an expectation; it is never the owner proof.
4. A migration may copy an already-explicit work_object.world_id onto that
   object's existing revisions. It must not infer ownership from campaign_id,
   including equality between campaign_id and a World ID. Campaign revisions
   remain unowned by a World.
5. Campaign PlayRun V1 rejects World-owned Runbooks before persistence. The V1
   record, storage, routes, and campaign behavior remain unchanged. No Run is
   created from a World-owned Runbook in Phase A.

The current application-state layer restricts World ownership to Plans, the
database scope constraint admits only World-owned Plans, and WorkRevision has
no owner field. Runbook creation and committed-revision ownership are therefore
campaign-only today. ARCHITECTURE ruled that the exact pinned Runbook revision
is the canonical Run owner source; campaign equality is not authority.

## ACTIVE exclusive write lease

The lane may edit only these paths:

~~~text
src/application_state/content/types.py
src/application_state/content/service.py
src/application_state/content/repository.py
src/application_state/content/import_plans.py
src/application_state/content/import_runbooks.py
src/application_state/content/playable_admission.py
src/application_state/migrations/versions/20260929_0008_world_owned_runbook_revision.py
apps/live_control_server/services/workspace_document_registry.py
tests/application_state/test_runbook_work_object_postgres.py
tests/application_state/test_plan_work_object_postgres.py
tests/application_state/test_runbook_existing_state_import.py
tests/application_state/test_plan_existing_state_import.py
tests/test_live_play_runs.py
Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md
Docs/Plans/HANDOFF-DEMO-world-owned-runbook-foundation.md
Docs/Roadmaps/ROADMAP-demo.md
~~~

The lease covers the Content model, SQL repository, migration, importer
compatibility, exact committed-revision resolver, and the guard at campaign V1
Play admission. It does not include a new public World Runbook API or UI
consumer. If implementation requires a path outside this list, stop before
editing and return to PRIME for an explicit transfer or split.

## Owning-boundary witness

The Phase A tests must exercise the PostgreSQL-backed Content boundary and the
existing campaign Play route:

- Create a World-owned Runbook, commit it, reload the exact revision, and prove
  both WorkObject and WorkRevision carry the same World ID.
- Resolve an older exact revision after a newer commit using its own revision
  number and SHA; prove its owner and bytes remain bound to that revision.
- Reject blank/mixed scope, a mismatched WorkObject/revision owner, a foreign
  expected World, a missing revision, and an incorrect SHA before mutation.
- Attempt to start a Run through campaign PlayRun V1 from the World-owned
  Runbook; prove it fails before a Run or manifest is persisted.
- Keep campaign Runbook create, commit, exact read, PlayRun create/list, and
  imported campaign records working with world_id null.
- Keep existing World Plan creation, commit, and revision ownership working.
- Do not change PlayRun V1 schemas or routes, add World Run storage, expose a
  tagged Campaign locator, or start any Run from the World-owned Runbook.

Focused verification command after dependencies are available:

~~~sh
uv run pytest \
  tests/application_state/test_runbook_work_object_postgres.py \
  tests/application_state/test_plan_work_object_postgres.py \
  tests/application_state/test_runbook_existing_state_import.py \
  tests/application_state/test_plan_existing_state_import.py \
  tests/test_live_play_runs.py
~~~

The application-state fixture creates a uniquely named disposable PostgreSQL
database and drops it during teardown. It uses
DMB_APPLICATION_STATE_TEST_DATABASE_URL when configured, otherwise its
127.0.0.1:54329 admin target. Do not point it at persistent demo databases or
start a server, provider, corpus, or shared runtime for this slice. The focused
suite must apply the migration through its fixture and run the complete
owner/campaign compatibility witness. Run Ruff on changed Python paths and
git diff --check before review.

Baseline suite execution was unavailable while preparing this proposal:
rtk pytest could not spawn pytest, and UV_CACHE_DIR=/tmp/dmb-uv-cache uv run
--offline pytest stopped before collection because ruff==0.15.7 was not in the
cache. No baseline test assertions ran; this is an environment limitation, not
a reported test failure. Recheck after PRIME activation in the authorized test
environment and record any inherited failure before implementation changes.

Post-activation environment recheck on 2026-09-30: the fixture's local test
admin at `127.0.0.1:54329` was not accepting connections (`pg_isready` reported
no response). After project dependencies were available, the focused new
World Runbook exact-revision test reached fixture setup but failed before
collection/assertions when the fixture could not connect to create its unique
`dungeonbuddy_app_state_test_<uuid>` database (`connection refused`). No test
database was created, no migration or test body ran, and no PostgreSQL service
was started. The full focused suite remains pending this disposable target.

Implementation checkpoint on 2026-09-30: the active lease now adds World-owned
Runbook Content creation, persists and checks `WorkRevision.world_id`, backfills
only explicit existing WorkObject owners, fences mismatched revision owners,
and rejects World Runbooks on campaign Play V1 before Run/manifest writes. Added
tests exercise exact historical Runbook resolution, bad scope/digest/owner,
imported campaign ownership, existing World Plan ownership, migration backfill
without campaign-ID inference, and V1 no-persistence behavior. Python compilation,
scoped Ruff 0.15.7, `git diff --check`, and Alembic offline upgrade/downgrade
rendering pass; Alembic reports single head `20260929_0008`. These checks do not
replace the required PostgreSQL execution, which remains pending the local test
admin target becoming available.

## Collision and predecessor audit

After #807 merged, the refreshed open PR inventory was #798, #781, #763, #764,
#765, #760, and #761. Their exact file lists cover backlog records, the
interaction map, Rules Lawyer routes/services/UI and dependencies, and UI
design handoffs. None overlaps this Phase A lease. This collision check is a
snapshot; recheck exact PR files and active leases before any transfer or
successor slice.

Phase A follows the merged #806 design and is serial. Do not dispatch Phase B
until the Phase A PR is merged and its exact owning-boundary witness passes.
Phase B still needs a separate ACTIVE handoff for the World PlayRun V2 backend,
its independently audited storage strategy, and campaign V1 compatibility.
Phase C remains a later separate lease for typed Play/context consumers and the
mounted World Run create/list/resume witness. Generic Agent Run resolution and
Play conversation remain a later successor.

## Activation and handback

PRIME's activation pins base
f59395a9c5677b1beb46402b7de6c148a5ef6e8d, branch
codex/demo-world-runbook-foundation, this exact path allowlist, the five-suite
pytest command above, and one serial implementation PR before Phase B. Main was
fetched and current open PR files were checked after #807 merged. The
application-state fixture creates a unique disposable database, but verify
the configured test-admin target is the intended local test PostgreSQL before
running the suite; never use a persistent demo database.

After implementation, inspect the cumulative base-to-head diff, run the owning
tests, record exact evidence and inherited failures here and in ROADMAP-demo,
commit and push the bounded branch, and open the assigned PR. Send PRIME the
exact head, tests, diff, and failure dispositions for review. PRIME owns merge.
Phase A does not close J1–J6, prove Play UI integration, or establish operator
acceptance.
