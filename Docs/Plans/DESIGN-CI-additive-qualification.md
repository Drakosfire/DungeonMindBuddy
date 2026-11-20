# Additive CI transition and qualification design

Status: design delivered with PR 1; PR 2 implementation is not yet activated.
Owner: CI transition coordinator. User's serial five-stage plan is authoritative.
No current PR gate is removed, filtered, renamed or treated as optional.

## Stage boundaries

1. Inventory/contract extraction: this PR. Classify all discovered files, fail
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
merging the route into a hidden synthetic head. Wait for reviewed real-main route
integration, or report the qualification lane red/blocked with the exact dependency.
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
