# Additive CI transition and qualification design

Status: PR1 #2284 merged; PR2 #2288 ACTIVE, full qualification HOLD.
Owner: CI transition coordinator. User's serial five-stage plan is authoritative.
No current PR gate is removed, filtered, renamed or treated as optional.

## Stage boundaries

1. Inventory/contract extraction: completed in #2284. Classify all discovered files, fail
   unclassified tests, publish file/case counts with distinct provenance, measured
   durations and source SHA. Classification does not yet drive PR selection.
2. Qualification first: add a separate manual, scheduled and release-candidate
   workflow. It must run the full declared regression contract, build a clean
   production image, and run that exact image against disposable databases.
   No stage-3 replacement or domain selection is enabled by this addition.
3. Add a discovered frontend/type/build/auth fast candidate beside all old checks,
   with real isolated DB wrong-principal/CAS/rollback/history cases and graph
   draft-loss regressions. Measure; never remove coverage to meet five minutes.
4. Shadow-only versioned changed-file/domain/dependent/suite mapping. Shared auth,
   schemas, migrations, factories, dependencies, CI, unknown paths or unreliable
   diffs select full coverage. Prove rename/deletion/mixed/error/monotonic behavior;
   replay regressions and inject tenant/CAS/publication/draft faults. Any missed
   required suite blocks rollout. No shadow result can suppress current checks.
5. Only after proof, coordinator may authorize narrowly enabled docs-only then
   isolated presentation selection, retaining full override, stable aggregate and
   one-switch rollback. Shared/uncertain changes stay full. Main/release qualification
   has an explicit failure owner who suspends rollout. Nightly cannot replace
   premerge high-risk verification. No branch protection changes are authorized.

## PR 2 concrete qualification design

Use a new `.github/workflows/qualification.yml`, with distinct concurrency from
PR gates and a pinned source SHA in every report. Proposed triggers:
workflow_dispatch (explicit candidate ref), daily schedule on main, and release
candidate tags `rc/**`. Resolve the source once; do not build one ref and test another.
Treat these triggers as qualification only, never deployment. Keep permissions
contents:read, do not expose production/provider secrets, and use hosted ephemeral
runners with task-owned artifacts and teardown in always-run cleanup.

Run the full declared default offline suite plus a clean `Dockerfile.production`
build (no push). Record image ID, source SHA and source/image binding. Start that
exact image on an isolated network with fresh PostgreSQL instances/databases,
synthetic fixtures and disposable mounted roots. Use existing migrations and test
DB isolation; do not substitute live DBs or invent a second fixture cache. Record
startup logs, exit code, health/live and ready responses, authenticated/denied API
responses and actual static asset responses from this container. Assert an index
and referenced asset contents, not merely a200 from SPA fallback.

Production defaults are hosted_dms and production; readiness validates hosted
configuration, route policy and runtime preflight. Supply a supported synthetic
configuration and protocol-faithful disposable DMS if necessary. Do not change to
local mode, monkeypatch readiness, or relabel liveness as production readiness to
obtain green. Unsupported readiness is an explicit qualification blocker to resolve
at its owner. Invalid configuration must still fail closed. No production source
repair is included automatically in a CI lease.

Use real Playwright Chromium against this image's static route in a fresh profile:
create a local World, edit graph, navigate away/back with an unsaved draft, verify
preservation, save and reopen after reload. Inspect saved state/visible values,
not screenshots alone. Retain browser trace, console/network failures, image logs,
source/image IDs and test output. Use no existing operator browser profile/state.

Dependency: #2276 graph-route behavior is still unmerged at PR-1 base. Current main
cannot honestly satisfy its graph-edit/draft route acceptance. PR 2 cannot report
qualified by skipping these tests, testing a different development server, or
calling an isolated composition main-ready. The coordinator now explicitly permits
a separately labeled candidate composition for harness proof while CI remains the
priority. Keep main readiness red/blocked while the graph contract is absent; do
not merge graph work to unblock CI.
Do not edit the other lane's Surface/canvas files.

Prove failure propagation with disposable fault controls owned by the qualification
harness: a container startup failure must make the workflow fail; denied/removed
browser storage persistence must make save/reopen acceptance fail. Inject only in
fresh CI containers/browser contexts, never production code/live data. Assert both
negative probes are detected by the same health/browser boundary used by the good
run, then prove cleanup. A negative probe expected to fail must not make an unrelated
real qualification failure green. Name coordinator-owned triage and suspend rollout
when qualification fails. The PR-2 handoff must pin the exact dependency state,
expected writes, commands, fault controls and evidence before activation.

## PR 1 exposed baseline collection failures

At base534ff9c70499d6dc847c949465e95a32e1012467, the broad Python collection
exposes seven unchanged import failures: graph_authoring_overlay_projection,
graph_authoring_overlay_projection_merge, graph_authoring_visibility,
graph_ingest_verified_snapshot_uri_shed, graph_object_authoring_merge_guard,
graph_review_authored_overlay and source_packet_density test modules. Missing
historical recap_projection/graph_ingest_verified_snapshot/merge reconciliation
helper imports and removed _empty_party_context are the observed errors. All seven
reproduce in an isolated exact-base worktree. The full candidate collection reports
16,600 selected/16,636 discovered cases before these errors (36 existing deselections);
these are partial counts from a failed collection, not full-suite success, and
subsequent new guard cases will increase them. Retain error logs and triage with
test/product owners before claiming a green full qualification lane. Do not delete,
exclude or stub these tests in the CI transition to obtain a successful run.

## Stage 2 implemented probes and observed blockers

PR1 merged atbe0ebf6c99f3d4b03b5810aa7e0a1ccc33ee35b0. The isolated successor
repairs the seven collection imports/call sites using live production contracts:
all89 affected cases pass, and broad collection completes16,726 cases with the
existing36 deselections (before adding new qualification guards). No original
test definition or parametrization is removed; collection-repairs.json freezes
those definitions/parameter expressions. URI and durable-overlay tests explicitly
move from the excised Union engine to current adapter/read-model boundaries, not
a stub restoration. Preserve the limits of that owning-boundary migration.

The manual/scheduled/rc-tag workflow resolves one source SHA and runs independent
full-regression and exact-image/browser jobs with a fail-closed aggregate. The
image harness uses canonical pinned Core migrations, real Buddy migrations, fresh
logical DBs with distinct owners, isolated persistent roots, and a synthetic HTTPS
DMS protocol fixture trusted only inside its disposable image process. No live
DMS/provider/account, operator state or authentication bypass is used. It verifies
production readiness, API auth/denial, served assets against actual image bytes,
and real-image startup rejection. Browser tests use fresh contexts, actual UI
navigation and save/reopen; only a persistence-boundary failure with an exercised
IndexedDB denial can satisfy the negative probe. Missing graph behavior remains
a hard failure with dependency#2276, never skip/xfail or a dev-server replacement.

The first real image diagnostic caught a packaging defect: .dockerignore's
**/corpus/ rule excludes executable src/corpus, so uvicorn import exits with
ModuleNotFoundError: No module named src.corpus. The startup negative-control
probe correctly refused to call this unrelated crash a successful fault injection.
Named resources were removed, but independent review later identified an implicit
PostgreSQL anonymous data-volume leak. The harness now mounts and removes an
explicitly named data volume and removes anonymous volumes only with each exact
owned container. A real never-started-container mount/teardown proof verifies the
Docker boundary. One exact-head leaked volume was traced from retained inspect
records and removed; an earlier untraced anonymous-volume candidate remains a
cleanup follow-up rather than grounds for deleting unowned data. Local builds
filled root-disk cache; exact unused/unshared task-cache records were reclaimed
(approximately2.93GB), restoring about3GB normal-user headroom. A new8GiB Docker
headroom check stops before build/resource allocation. Further local image builds
remain stopped; no global prune, mount or daemon configuration changed. Production
image verification moved to hosted runners. The coordinator-approved source-only
packaging inclusion and later runtime proof are recorded below; the original
failures remain evidence, not current unresolved packaging work.

## Approved packaging extension and premerge self-validation

The coordinator approved the .dockerignore transfer after re-anchoring current
main18b992193b103b1e0a05490855bd8af620bed835 and inspecting supported lease records.
#1802 and #1814 are MERGED; the latter's stale ACTIVE header is settled. Supported
steward_preflight parsing discovers21 candidate allowed paths and zero active
record conflicts before .dockerignore edits. Open1512/1514 are policy-only and
2289 is reference-doc-only; no current competing packaging writer was found.
The source exception includes exactly src/corpus/__init__.py and
src/corpus/session_recap_paths.py; all other corpus content remains excluded.
No production source, state, auth mode, graph code or protection change is granted.

Because workflow_dispatch cannot find a new workflow absent from default main,
qualification now validates its own workflow/harness/package-contract PR changes.
This is additional self-validation only: existing Hosted and ownership PR gates
remain unfiltered and authoritative. Outdated qualification PR runs may cancel
on material head changes; manual/scheduled/RC runs retain non-canceling behavior.
Resolve one checkout SHA once and pass it to full-regression and image jobs.
This is not domain selection or selective rollout. Actual graph/persistence runtime
proof is required for main readiness; explicit isolated candidate proof is now
authorized and separately labeled. No graph merge, skip or dev image substitution.


## Historical migration contract repair and remaining production failure

The first broad regression execution exposed old migration witnesses that attempted
to downgrade today's schema through intentional later reader fences. Exact-base
be0ebf6 reproduces16 failures among47 original conversation/provenance cases.
An audited test-only repair pins one migrated template per actual historical
revision, clones per witness, seeds real rows under unchanged constraints and
checks exact projected rows/fingerprints. Populated omissions require explicit
column/value policy: later default answer_composition_kind=base and the intentionally
absent0013 v1 intent marker for the0011 legacy-unverifiable witness. Real forward
migrations and original replay rejection assertions remain. Owning refusal tests
run the exact guard inside a real rollback transaction and verify all rows and
revision unchanged; a separate CLI test preserves the real0141 production fence.
No migration, fake version marker, exclusion or weakened assertion is introduced.

The remaining two route cases now supply real HTTP requests and valid uncapped
synthetic provider envelopes instead of obsolete run-only doubles. They expose a
production incompatibility: _policy_request_budget returns uncapped context=None
and output reserve0, while RulesOnlyRuntime.authorize compares integer input size
against None. A valid no-output-cap envelope reproduces TypeError before provider
or DB IO. Do not disguise this with a finite test budget or bypassed authorization.
Runtime-owner correction and fresh full-suite evidence are outstanding. This CI
lease does not automatically grant production/auth-policy source edits.

Isolated candidate5d718dd3cdcc8da65b28e5d9e54d9bce2b3b339a passed actual-image
startup/readiness/API/static, startup fault, real graph draft/save/reopen and
persistence fault in107.501s, all owned cleanup true. This proves the image witness
at its recorded candidate only; it is not full regression or main qualification.


## Material repair dependencies now merged

Root reviewed and explicitly authorized expected-head merges of runtime#2291
(d3182d5e7b890722518c1ef2e14a5d56982bbfe3) and APP#2294
(0d0f5af3418ae3327a4760376ba1f25385626b5d); both reviewed heads and merges were
verified on main after all8 owning/current checks passed. The uncapped Rules guard
and verified legacy producer defects above are historical findings now corrected
on main. CI2 consumes that main without rebasing for unrelated changes, preserves
all test IDs/assertion intent, settles the delivered owner handoffs, and refreshes
exact-head/full qualification. Earlier candidate image proofs remain bound to their
recorded SHAs; none becomes a main readiness claim. Main graph behavior remains
absent and separate. No deployment, live-data, protection change or graph merge.

## Full-lane runtime and stable execution partitions

An older full run reached the configured120-minute boundary around88% without
a completed summary. The additive lane now uses four stable Python file buckets,
not raw parametrized node IDs (some contain generated UUID labels). Every worker
first collects the entire default suite on clean pinned source. The plan proves
its raw actual node Counter is the exact union of disjoint buckets; all cases in
one canonical file belong to one bucket. Report/default selection drift, unknown
paths, duplicate or empty cases/partitions and partial pytest flags fail closed.
The same36live_llm default deselections remain.

Cross-worker coverage requires all four same-source reports, recomputes each plan
and validates the exact selected file union and parameter shapes. Only UUID
parameter-label churn can differ across same-source collections; it never affects
selection or the per-worker raw-ID union proof. Missing jobs/reports fail coverage.
All backend jobs retain independent APP session-template/test clones and a fresh
canonical native Core DB, locked tools/dependencies, fail-fast:false and120-minute
limits. Existing PR gates and unpartitioned full-regression command are unchanged.

Full Vitest, type/build and visual commands run in a separate source-pinned job.
After successful setup each runs even when an earlier frontend command fails;
ordinary failed-step status remains authoritative. This preserves the exact four
commands of the unpartitioned contract while preventing Python failures from
suppressing frontend execution. Qualification aggregate requires every backend,
frontend, coverage verifier and the existing exact-image/browser witness.

No latency claim is made from hash balance or case counts. Record actual hosted
partition durations and full residual totals before calling the runtime barrier
removed. This partition is an execution mechanism, not domain or change selection.
