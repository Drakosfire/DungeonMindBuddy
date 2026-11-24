# CI: one owned App database per serial workstream

ACTIVE under Alan's explicit instruction: apply the one-App-clone rule to CI
and adapt its isolation contract. DOGFOOD owns implementation and independent
review; the existing overall writer/context goal remains incomplete.

Branch codex/ci-one-app-workstream, isolated checkout
Projects/.codex/dogfood-ci-one-app/DungeonMindBuddy, pinned base
f5538e832756ccb58d2a14b1e96c824682b1da48. Initial diagnostics used the
older c3a2ae6032b0f16fc19d21be14759a0a8607782b base; the rebase preserves
main’s lifecycle guard changes and is not qualified by those diagnostics.
Current open PRs/leases inspected:
RETRIEVAL4583 owns benchmark cohort work, not these CI fixture/runner paths;
2302 is report-only. Do not edit their benchmark lifecycle/allocator paths.

Delivery is serial: this CI contract PR to main, then its bounded CI-only
serving adoption against the then-current serving source, then rebase and
qualify writer PR4573 on that predecessor. The serving adoption may need the
already merged disposable helper as an explicit dependency because that serving
line predates it. Do not silently adopt unrelated main runtime changes. The
writer PR remains draft; its source/benchmark evidence is preserved and no
unqualified merge or deployment is implied. The existing DOGFOOD App clone is
reused for serial diagnostics; no second local App clone is allocated.

Outcome: one workstream owner allocates the App clone once from an explicit
local template, or adopts an explicitly assigned existing owner receipt. All
selected CI suites run serially on it; tests reset fixture state rather than
clone databases. A private pristine migrated snapshot is prepared once per
pytest session and restored only inside that exact owned database. Snapshot
preparation is fixture setup, not an extra database or repeated contents scan.
No operator/live database fallback, provider calls, full inventory scans, Core
clone, shared-template mutation, force termination, or production changes.

Ownership is pinned by loopback endpoint, exact database name/OID/cluster and
workstream receipt before any reset. Missing/stale/foreign ownership, changed
admin/source/schema, concurrent cases and open foreign connections fail closed.
Workers and connections close before final exact-clone teardown. Externally
owned clones remain retained across retries/follow-ups until their owner accepts
or abandons the result; fixtures never drop them. GitHub's completed aggregate
job explicitly accepts success or abandons failure and cleans its sole clone.

Replace physical-clone fixture assertions with owning-boundary proof of same
identity, independent row/schema state between serial cases, failure reset,
nested/concurrent refusal, mismatch refusal, and migration Engine closure.
Explicit predecessor/empty-schema migration tests use serial empty states on
the same database. Recovery tests save expected output/fingerprints and backup
files before emptying that owned target, then exercise restore and readback from
the offline backup. Keep same-source/World rejection tests and all domain
assertions. Do not claim simultaneous live-source/target physical isolation from
this serial test contract. Product restore guards are unchanged.

Exclusive expected writes: tests/application_state/conftest.py and database_fixture.py; tests/conftest.py and tests/test_source_statement_proposals.py for single fixture registration; new testing-only
workstream/isolation support; tests/test_application_state_database_fixture.py;
explicit migration/recovery tests currently using _create_database/_drop_database
(surface_native_turns, rules_authority_backup, plan_work_object_postgres,
reviewed_work_plan, manual_combat_postgres, application_state_authority,
native_storage_owner_migration, local_play_bootstrap, plan_action_consultation and its four fixture consumers); the existing App-only
media/authority integration fixtures, tests/test_runtime_preflight.py and Play historical timing helpers/callers,
which also allocate extra App databases, must use the same serial state owner.
Separately opted-in writable Core integration fixtures are not App clones and
are not launched or changed by this App workstream; shared Core stays read-only.
scripts/ci_contract.py and its owning tests, including tests/test_ownership_ci_partition.py; ci/contracts.json only two new
aliases for the unchanged existing short Rules/import commands; the four existing PostgreSQL CI
workflow job/setup bodies; test classification only for directly added guards;
AGENTS.md's backend isolation wording, development verification guide, this
handoff and truthful migrated-template predecessor settlement. Do not change
product runtime/migrations, provider/model settings, dependency locks, branch
protection, workflow permissions or paused PR triggers.

Review map: (1) target ownership and one-clone lifecycle; (2) serial fixture reset
and migration/recovery cases; (3) aggregate runner/workflow consumption; (4)
policy/docs and retained evidence. These parts form one indivisible isolation
contract. No test is retired merely for speed. Report selector/case changes when
physical-clone assertions are replaced; domain protections stay required.

Validation: offline refusal/command/lifecycle guards; real same-clone serial
row/schema/failure tests; exact-SHA named backend contracts in the locked Python
environment; exact-source hosted verifier as required by repository policy;
independent cumulative review. Retain exact commands, source/tool versions,
worker/connection/teardown results and all failures. Preserve known inherited
failures visibly red and do not substitute fixture-only success for full domain
qualification. No passing CI, merge or delivery is recorded in advance.


Working-tree diagnostics (not exact-commit qualification): the original 21
fixture guards passed on the retained App; runner guards subsequently passed
22 cases and managed lifecycle guards seven cases without database allocation.
The combined case-7 run exposed duplicate session fixture registration; fixture
definitions now register once from database_fixture.py. Case-8 retained 92 passes,
three failures and 61 errors. Case-9 retained 157 passes, two historical downgrade
failures and one restore teardown error. Its natural backend-closure wait was
two seconds; the current implementation allows five seconds and retains only
backend identity/state metadata on timeout, never query text or credentials.
The two downgrade failures are not yet qualified as inherited: exact-parent
comparison remains required. No tests/selectors are excluded to conceal them.
All 2,072 App tests collect. Old physical-clone fixture assertions are replaced:
seven parent functions (nine cases) become 17 functions (28 cases), preserving
migration Engine closure and adding retained-owner/failure/concurrency checks.
Bootstrap's physical creation test becomes dispatch-only coverage plus real
empty-owned-App migration/readback; simultaneous physical source/target recovery
is replaced by offline backup/fingerprint restoration on that same App.

Raw logs and receipts: retained DOGFOOD evidence root
buddy-check.retained-80c.MPEaXT/evidence-lore-request-022f/workstream-qualification,
cases 6–9. This clone is benchmark_run_e27fc178267a4d7cbc90bf173dd3ecfe,
OID 210452, cluster 7711451860937605159, evaluator
buddy-retrieval-projects-4560 / 33351. It remains owned by the existing DOGFOOD
broker for serial retries and writer qualification. Release only after accepted
or abandoned results, worker/connection closure and verified exact removal.


At exact head 188c124cbb619ac1fb4409bab678b9bcbce82b47, 50 fixture/runner guards
passed and the edition restore passed three serial repetitions. Hosted-contract
frontend verification and official evidence validation passed at that SHA.
Independent SOURCE PASS covered the cumulative change. The parent 55bf product
and byte-identical parent dialogue test functions reproduced both 0194 refusals
under the explicitly documented new one-clone adapter; this is bounded inherited
failure evidence, not original physical-clone fixture or full-parent CI proof.

The seven-contract case-12 attempt was abandoned after independently reproducing
one coupled workflow guard still requiring four separate commands. That guard
now retains selector completeness and partition assertions while checking one
aggregate command. The attempt also retained a low-score image test failure;
its classification remains unresolved. No incomplete run is a passing contract.
The external outer wrapper used subprocess.run and killed its CI parent on
KeyboardInterrupt before the escaped pytest group closed. The App stayed retained
and no new run started. The exact pytest group was pinned by PID/start time,
checkout, selectors and the retained log handle, interrupted gracefully, then
verified absent with zero connections on the pinned App. External descendant
closure evidence corrects the broker's insufficient group-only closure status.
The wrapper must wait through interrupts before further aggregate execution.

The abandoned attempt also exposed a real reset integration defect: a product
World-store test keeps Path.open patched through fixture teardown. Ownership
receipts and pristine snapshot hashing now use a captured io.open binding, and a
real fixture regression keeps that product guard active through teardown. The
product test still forbids its own file reads; no domain assertion is relaxed.

The replacement aggregate transport now invokes the repository CI CLI main()
in the broker-owned process, using its reviewed worker interruption barrier.
There is no outer subprocess.run parent-kill path. A real zero-database process
probe passed with two interrupts and a group leader already gone while its
member finished cleanup; all observed workers closed. Evidence:
buddy-check.retained-80c.MPEaXT/ci-inline-probe-1795485869169477297/receipt.json.
The proposed extra external waiter was retired after source review identified
missing leader-gone and exceptional closure paths; it was never used on a DB.
Current additional fixture regression raises the fixture cases from 28 to 29;
qualification of these amendments remains pending.

A subsequent remote re-anchor at f5538e832756ccb58d2a14b1e96c824682b1da48
preserves the newly merged cohort lifecycle, helper post-drop absence check,
Build save guard and Plan driver work. The implementation rebases without
leased-path overlap. Earlier 188c evidence remains exact to that predecessor;
it does not qualify the rebased source. Current database instructions were
reread before further benchmark work; the already owned App stays retained.
