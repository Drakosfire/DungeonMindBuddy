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
| `tests/application_state/conftest.py` | Exact historical templates/clones; preserve strict default head isolation. |
| `tests/application_state/historical_migrations.py` | Audited test row projection and transactional owning refusal guards. |
| `tests/application_state/test_historical_migration_contract.py` | Real PostgreSQL schema/isolation/fence guards. |
| `tests/application_state/test_agent_conversation_postgres.py` | Audited historical witnesses and current HTTP/provider test prerequisites. |
| `tests/application_state/test_agent_conversation_provenance_migration.py` | Audited provenance transition/refusal witnesses. |
| `tests/application_state/test_agent_conversation_service.py` | Claim-recovery migration witness only; retain all original cases/assertions. |
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
| `Docs/Plans/HANDOFF-RULES-uncapped-authorization.md` | Settle actual merged #2291 dependency only. |
| `Docs/Plans/HANDOFF-APP-legacy-import-intent.md` | Settle actual merged #2294 dependency only. |

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
alternate dev server may claim qualification. Main readiness stays blocked while
the graph contract is absent. The coordinator separately authorizes an explicit
isolated candidate composition as harness proof, never as main readiness or a
reason to merge/expand graph work under the CI-first priority.
Full suite errors beyond the repaired collection imports remain visible and require
owner triage, not opportunistic deletion/expectation weakening.

Retain stdout/stderr, container/browser traces, DB/image/source identities, cleanup
results and failure owner. Qualification failure suspends any future selective
rollout. Run applicable guards, actual owning-boundary probes and independent
exact-head review plus unchanged PR CI before coordinator disposition. Merge is
separate coordinator authority; no rollout stages3–5 are activated here.

## Observed image boundary and candidate proof

The source-only packaging exception fixed the src/corpus import defect. Actual
hosted image startup, readiness, auth/denial, static bytes and startup-fault checks
passed at recorded PR test compositions. Main's graph witness correctly remains
red because the route is absent; no skip or substitute server is allowed.

Explicit candidate5d718dd3cdcc8da65b28e5d9e54d9bce2b3b339a combines CI68ffb2c36,
main946813e3 and graph72107e9ad865ced7d515f49570ce7c1bf60c84c9. Run42581327676
image job passed all six boundaries, including actual graph draft/navigation,
save/reopen and exercised persistence denial, in107.501s. Image ID:
sha256:7792c8a6c87669301fe03a21b5b1b8559712312eeac7e1ccbb294ef849bd72af.
All exact-owned cleanup checks true. Image report qualified=true applies only to
this isolated image probe; full-regression/aggregate and main readiness are NOT
qualified. No graph/main merge occurred. Traces and IDs are retained in task evidence.

## Review correction and infrastructure limit

Review cycle1 requested changes at31a89de7eacbcf636a0448adfc54852dc5b0f061:
PostgreSQL's image declared a data VOLUME and initial cleanup left it anonymous.
The correction explicitly creates/mounts/tracks/removes its named data volume and
uses --volumes only when removing exact task-owned containers. Real Docker create/
inspect/remove proof verifies the mount and absence of remaining owned resources.
Root disk filled during local build-cache allocation; verified task-only cache IDs
and one exactly traced leaked volume were cleaned, without global prune or changes
to shared data. Added8GiB headroom refusal before any build/resources. Local full
image builds remain stopped because local free space is below the8GiB guard.
Hosted image probes provide the evidence above; full qualification remains HOLD.

## Authorized historical migration test-contract extension

The coordinator explicitly authorizes audited test-only historical schema setup,
exact-base failure proof, forward schema behavior and production fence enforcement.
Current main and open ownership were checked before edits: #2290 owns
`test_native_storage_owner_migration.py` and its new production migration; neither
will be edited. The migrated-template predecessor is SETTLED by #2203. No active
competing conftest/test-contract writer was found.

Additional bounded writes: `tests/application_state/conftest.py` (generalize existing
migrate-once/clone-per-test to explicitly pinned historical revisions; default head
behavior remains); `tests/application_state/historical_migrations.py` (owned test
row projection into real historical schemas); `tests/application_state/test_historical_migration_contract.py`
(real schema/isolation/fence guards); `tests/application_state/test_agent_conversation_postgres.py`
and `tests/application_state/test_agent_conversation_provenance_migration.py`
(audited stale-head and historical-transition witnesses only). Classification and
owning CI guards may include these added tests. Other failing contracts will be
reported/audited before extending this list. Production migrations, schema fences,
operator databases and graph source remain outside scope.

Historical witness design: create/migrate one empty owned template per exact
historical revision; clone independently for each witness; seed only actual rows
from another owned test database using the historical schema's columns and all
its real constraints; fail on populated source tables absent from that schema.
Do not stamp versions, disable constraints, run a historical writer against today's
schema, or downgrade through unrelated later fences. All old assertions/cases stay
represented; current-head downgrade denial is verified separately.

The same audited conversation module also exposed four existing route fixtures
that supply only SimpleNamespace(app=app), while the current route negotiates via
HTTP headers. Correct only those fixture arguments to real Starlette Request
objects with empty Accept headers (the existing JSON path). Preserve every route,
authentication, provider-once, history and concurrency assertion; no product route,
shared auth fixture or streaming behavior changes. This is a prerequisite test
fixture correction inside the already owned module, not runtime feature work.

Refusal witnesses that contain modern receipt generations invoke the exact owning
historical migration's refusal in a real rollback transaction rather than project
unsupported future payloads into an old schema. The helper asserts the exact
refusal message plus every row and revision unchanged; a missing refusal forces
rollback and test failure. Separate actual CLI downgrade verifies the production
head fence. Successful historical transitions still use real revision-pinned
schema templates/clones. No version stamping or skipped full migration is used.
The two Plan route fixtures then exposed their obsolete run-only provider doubles.
Use the existing guarded-provider callback protocol in a local synthetic transport
with the current uncapped envelope, retaining custom recording/nested-run behavior.
The shared route FakeRuntime still fabricates a zero output cap and is not changed.
The real authorization, SDK-entered/response-received and captured native-reply
callbacks must succeed; do not bypass Rules-only authorization or edit that shared
fixture. This corrects test prerequisites rather than relaxing production guards.
Actual valid uncapped envelopes expose a production RulesOnlyRuntime TypeError
(integer estimate compared with None); these two cases remain legitimate failures,
not candidates for finite-budget test overrides. No runtime write lease is assumed.


Hosted merge-composition testing exposed a new guard's accidental assumption that
0141 remained the latest head. Main #2290 merged0142 at7abfaccaccf63737a31a52e33c79a0df75e1b873;
0142 correctly refuses before0141. Correct the new witness to clone a real pinned
0141 template and invoke the actual CLI downgrade to0140 there. This preserves the
specific production fence without another obsolete latest-head constant. Current
head fixture guards remain dynamic/strict, and0142's own source/tests stay owned
by its merged implementation. No rebase or production modification is needed.

## Authorized claim-recovery witness repair

The coordinator assigns the three reproduced conversation-service failures:
APP's verified legacy producer bug is isolated in its own narrow product lane;
CI2 owns only `tests/application_state/test_agent_conversation_service.py`'s stale
historical claim-recovery witness and its original-definition/parameter manifest.
No other open PR edits that test file. APP successor settles the historical
#822/#867 implementation headers; CI2 does not concurrently edit those documents.
CI2 pauses classification writes while the APP lane adds its one new owner-module
entry. This explicitly splits that append from CI2's other manifest authority.

Use a real0013 template/clone, seed the completed owned test row, downgrade only
the owning0013→0012 edge, then upgrade the real chain to head. Preserve every
fingerprint, provenance, attempt, result and legacy-unverifiable replay assertion.
Only the later answer_composition_kind=base default is explicitly projected away
and must be recreated by forward migration. No production downgrade through0142,
version stamping, finite budget override or skipped case is permitted.


## Verified dependency consumption

Root independently PASSed runtime#2291 at a6923b5421ff7971508055b84c043e1470be63c7
and APP#2294 at a8b5d8382fc2fca0ded3b4eef796a5d6ffbd6a16, then explicitly
assigned expected-head ready/merge. Both had8/8 live green checks and clean
mergeability; no classic branch protection or effective main rules required a
rebase or bypass. #2291 merged d3182d5e7b890722518c1ef2e14a5d56982bbfe3 at
09:31:53UTC; #2294 merged0d0f5af3418ae3327a4760376ba1f25385626b5d at09:34:04UTC
on2026-11-09. Fresh fetch and ancestry checks verify both exact reviewed heads
on main. No deployment, graph merge, live-data or protection change occurred.

This consuming CI branch merges that actual main for the two material repairs;
it does not rebase solely for unrelated UI commits. The review base for the
resulting CI-only delta is actual main0d0f5af3418ae3327a4760376ba1f25385626b5d;
be0ebf6 remains the original implementation authority/history. The two owning
handoffs above are narrowly transferred for factual already-merged settlement.
Both original production failures are fixed on main, and the corrected historical
witness remains CI-owned. All257 affected cases passed in the prior labeled
candidate, including all95 service cases; exact consumed-head verification and
full qualification are refreshed before disposition. Main's graph witness stays
honestly blocked; no graph merge is inferred or requested by this consumption.

## Completed baseline and startup race follow-through

The original full candidate5d718dd3cdcc8da65b28e5d9e54d9bce2b3b339a run
42581327676 completed (not timed out):1125 failed,15101 passed,154 skipped,
36 deselected and358 setup errors in6916.48s. The preserved failure inventory
spans203 failing and22 setup-error modules. This predates the reviewed runtime,
legacy import and historical fixture repairs; it is not a current-head failure
count. Backend failure prevented subsequent frontend/build/visual commands.
No omissions or successful full-regression claim follow from this baseline.

Candidate17b6a9d10415a1cd602839edcb77335c030a09a3 image run42595308008 exposed
a disposable PostgreSQL entrypoint race before health checks: pg_isready accepted
the socket-only initialization server, then psql encountered its shutdown. Wait
for TCP127.0.0.1/postgres instead, which the official entrypoint enables only for
the final server. Keep bounded60 polls and the same fail-closed lifecycle; do not
retry application startup/fault assertions. Two added regression guards cover
transient initialization and permanent unavailability. All24 CI guards pass; an
owned postgres16-alpine fresh-cluster probe reached TCP then SELECT1 in1.117s,
and its exact RAM-only container was removed. This is harness correctness, not
production readiness or controlled performance proof. Current main re-anchored
atf6e174e407ab83b4632160771412b77c09833ed0; unrelated reference settlement does
not require rebasing the reviewed CI composition. PR2 remains HOLD.

## Native test database provisioning batch

Coordinator authorizes the separately migrated native Core test DB batch. Keep
Buddy's existing Postgres16 service/template-clone fixture unchanged. The full
qualification command additionally owns one uniquely named RAM-only pgvector
cluster, bound to a random127.0.0.1 port, with no externally accepted DSN/volume.
Create vector and run the exact installed Core pin's canonical migrations from
a fresh checkout, then pass only that DSN as DMB_CUTOVER_TEST_DATABASE_URL to
the unchanged declared full regression command. Retain migration/PG/cleanup logs;
setup, test and cleanup errors fail qualification. Native tests retain their
existing serial truncate/reset behavior inside this separate ephemeral cluster.
No product DSN, shared operator data or APP fixture policy changes.

Benchmark transfer remains pending: the active ADVERSARY task is working on
accepted-prefix APP validation, while merged Q01 handoffs retain stale ACTIVE
headers. No benchmark source/lease files have been edited pending narrow owner
coordination. Native provisioning is independent within this CI write lease.

Native provisioning author validation uses all54 original baseline IDs with the
missing-native-DSN signature. Canonical Core430c1a6 migrated to
0018_native_source_extensions, separate APP clone server unchanged; both owned
clusters cleaned. Result7passed/3failed/44errors in8.52s: the absent-native-DSN
error is gone;44now expose stale world_container_registry.uuid4 patching, and
three reach later contracts. This is7observed passes, not54promised fixes;
residual fixture work remains visible.26CI guards and Ruff pass.
