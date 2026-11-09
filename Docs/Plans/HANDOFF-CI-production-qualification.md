# CI: production qualification lane

**Status:** ACTIVE under Alan's five-stage execute instruction and coordinator's explicit
successor preparation assignment. This is PR 2 only. PR 1 #2284 merged at
be0ebf6c99f3d4b03b5810aa7e0a1ccc33ee35b0 after independent reviews and all seven
checks. Base is that real main merge; branch codex/ci-production-qualification in
its own task-owned worktree. Topology: serial CI successor, no other CI PR open.
No changes to PR1's reviewed branch. Graph route #2276 remains separately owned.

**Base revision:** `be0ebf6c99f3d4b03b5810aa7e0a1ccc33ee35b0`

| Lane field | Value |
| --- | --- |
| Branch / isolated checkout | `codex/ci-production-qualification` in the task-owned qualification worktree |
| Runtime/state ownership | Ephemeral hosted runners, uniquely named disposable Docker services/volumes and fresh browser contexts only. No operator state, shared DB or profile. |

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

## §4 Expected path allowlist

| Path | Bounded purpose |
| --- | --- |
| `.dockerignore` | Coordinator-approved inclusion of tracked src/corpus Python only; no corpus data/secrets. |
| `.github/workflows/qualification.yml` | Own-path premerge validation, manual/scheduled/RC qualification. |
| `.github/workflows/world-ownership-core.yml` | Add qualification guards only; preserve all existing PR suites/gates. |
| `scripts/qualification/` | Qualification and disposable lifecycle harness. |
| `apps/live-control-ui/tests/qualification/` | Fresh-browser image witness; no product/graph edits. |
| `tests/test_ci_qualification.py` | Owning harness guards. |
| `tests/test_ci_contract.py` | Additive contract guards only if required. |
| `ci/contracts.json` | Additive qualification contract only if required. |
| `ci/test-classification.json` | Explicit classification/discovery contract for new tests. |
| `ci/collection-repairs.json` | Preserve original definitions/parametrizations. |
| `tests/test_graph_authoring_overlay_projection.py` | Existing declared collection repair. |
| `tests/test_graph_authoring_overlay_projection_merge.py` | Existing declared collection repair. |
| `tests/test_graph_authoring_visibility.py` | Existing declared collection repair. |
| `tests/test_graph_ingest_verified_snapshot_uri_shed.py` | Existing declared current-adapter contract migration. |
| `tests/test_graph_object_authoring_merge_guard.py` | Existing declared real-model fixture migration. |
| `tests/test_graph_review_authored_overlay.py` | Existing declared collection repair. |
| `tests/test_source_packet_density.py` | Existing declared current-signature repair. |
| `Docs/Plans/HANDOFF-CI-production-qualification.md` | Owning authority and honest evidence. |
| `Docs/Plans/HANDOFF-CI-test-contract-inventory.md` | Truthful completed-predecessor settlement. |
| `Docs/Plans/HANDOFF-HOSTED-buddy-validation-ci.md` | Settle merged #1814's stale ACTIVE lease before transfer. |
| `Docs/Plans/DESIGN-CI-additive-qualification.md` | Qualification design/evidence/dependencies. |

### Coordinator-approved packaging transfer (recorded before edits)

Current main18b992193b103b1e0a05490855bd8af620bed835 and open PRs were inspected.
Supported repository ownership records are the pinned handoffs; no separate lease
connector or tracked .agents registry exists here. The supported read-only
steward_preflight handoff parser is used to verify this candidate allowlist.
HANDOFF-HOSTED-buddy-auth-packaging is already SETTLED (#1802). The validation
successor #1814 is confirmed MERGED atc7f83c086d39e01f129fa7e31ef03262dbf65f91;
its stale ACTIVE header is settled in this same consuming change. Open1512/1514
are policy/document-only and do not write packaging; current2289 is reference
document-only. No current competing packaging writer was found. The coordinator
explicitly approves transfer/extension of .dockerignore solely for needed Python
source inclusion, and safe qualification-own-path PR validation while old full PR
gates remain authoritative. No source/graph/auth-policy/deployment lease is added.
The prior proposals are now adopted authority; runtime success still requires proof.

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
executable src/corpus package. The coordinator has now extended the lease above for the narrow source-only inclusion.
The original failure and proposed patch remain retained; applying the correction
does not by itself establish successful runtime qualification. No startup/health/browser success is claimed,
and no missing-code mount, local-mode substitution or test exclusion is permitted.
Graph witness also requires real-main integration of#2276. The qualification lane
remains red/blocked until actual positive and negative boundaries pass.

## Review correction and infrastructure limit

Review cycle1 requested changes at31a89de7eacbcf636a0448adfc54852dc5b0f061:
PostgreSQL's image declared a data VOLUME and initial cleanup left it anonymous.
The correction explicitly creates/mounts/tracks/removes its named data volume and
uses --volumes only when removing exact task-owned containers. Real Docker create/
inspect/remove proof verifies the mount and absence of remaining owned resources.
Root disk filled during local build-cache allocation; verified task-only cache IDs
and one exactly traced leaked volume were cleaned, without global prune or changes
to shared data. Added8GiB headroom refusal before any build/resources. Local full
image verification is stopped until infrastructure/packaging scope is resolved.
No false qualification success; all runtime acceptance gates remain outstanding.
