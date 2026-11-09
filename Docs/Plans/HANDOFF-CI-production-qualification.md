# CI: production qualification lane

Status: ACTIVE under Alan's five-stage execute instruction and coordinator's explicit
successor preparation assignment. This is PR 2 only. PR 1 #2284 merged at
be0ebf6c99f3d4b03b5810aa7e0a1ccc33ee35b0 after independent reviews and all seven
checks. Base is that real main merge; branch codex/ci-production-qualification in
its own task-owned worktree. Topology: serial CI successor, no other CI PR open.
No changes to PR1's reviewed branch. Graph route #2276 remains separately owned.

## Invariant and exclusive write lease

Add qualification without suppressing any existing PR gate. Preserve every declared
full test file/case and expose baseline failures honestly. Run source-bound clean
production image, disposable DBs and fresh browser profiles only. No deployment,
operator DB/profile, live provider, branch protection or graph/Surface/canvas edits.

Expected writes: .github/workflows/world-ownership-core.yml (add qualification guards only); this handoff; predecessor HANDOFF-CI-test-contract-inventory.md
settlement; DESIGN-CI-additive-qualification.md; .github/workflows/qualification.yml;
ci/collection-repairs.json, ci/contracts.json and ci/test-classification.json for additive qualification only;
scripts/qualification/* and tests/test_ci_qualification.py; new browser witness
under apps/live-control-ui/tests/qualification/*; the seven existing collection-error
modules listed in the design. Update tests/test_ci_contract.py only if the additive
qualification manifest needs contract guards; keep original command fixture intact.
No runtime source or shared database fixture lease is granted.

## Test-contract repair scope

Four authored-overlay tests import RecapGraphProjection from a deleted module;
repoint to the live recap_projection_contracts owner already used by the service.
The merge-guard tests import fixtures from a deleted test module; construct the same
real Pydantic assertions/overlay locally, preserving all assertions and test IDs.
The source-packet test supplies removed party-context plumbing; use the current
render signature, preserving canonical evidence/anchor assertions and parameter IDs.
The removed verified-snapshot URI helper belongs to an excised engine. Rehome its
two tests to current production source adapters: opaque worldbuilding locators do
not trigger file reads, while explicit local recap/file input still must exist and
retain contents/hash/span locators. Preserve both test IDs and explain the owning
boundary migration; do not restore dead helpers, stub production or exclude tests.

## Qualification acceptance and dependency

Implement independent image/startup/health/API/static/failure propagation portions
while graph route integration is pending. Build once; bind reports to source SHA and
image ID; boot that image with isolated PostgreSQL logical DBs/owners and disposable
persistent roots. Assert supported production readiness, real API denial and actual
static asset bytes. Prove bad startup is detected. Browser create/edit/navigation/
draft/save/reopen and denied-persistence probe must exercise the actual image route
with a fresh profile, and must fail when graph behavior is absent. No skip/xfail or
alternate dev server may claim qualification. #2276 exact real-main merge is a
recorded dependency; keep qualification red/blocked if its graph contract is absent.
Full suite errors beyond the repaired collection imports remain visible and require
owner triage, not opportunistic deletion/expectation weakening.

Retain stdout/stderr, container/browser traces, DB/image/source identities, cleanup
results and failure owner. Qualification failure suspends any future selective
rollout. Run applicable guards, actual owning-boundary probes and independent
exact-head review plus unchanged PR CI before coordinator disposition. Merge is
separate coordinator authority; no rollout stages3–5 are activated here.

## Observed image boundary blocker

The actual clean-built image fails import because .dockerignore excludes the
executable src/corpus package. This path is outside the current explicit lease.
The proposed minimal source-only inclusion is retained for coordinator scope
disposition; it has not been applied. No startup/health/browser success is claimed,
and no missing-code mount, local-mode substitution or test exclusion is permitted.
Graph witness also requires real-main integration of#2276. The qualification lane
remains red/blocked until actual positive and negative boundaries pass.
