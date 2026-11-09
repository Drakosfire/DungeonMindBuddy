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
| `tests/local_operator_client.py` | Supported local boundary test helper, no auth override. |
| `tests/application_state/test_plan_work_object_postgres.py` | Scoped authenticated endpoint and explicit World-owned Page prerequisites. |
| `tests/application_state/test_play_active_run_postgres.py` | Scoped authenticated endpoint fixture only. |
| `tests/test_graph_existing_object_resolver.py` | Scoped authenticated endpoint fixture only. |
| `tests/test_live_artifact_reads.py` | Scoped authenticated endpoint fixture only. |
| `apps/live_control_server/services/native_authored_references.py` | Coordinator-authorized native source-loss hard422/zero-writer policy only, after real unavailable read admission. No Core/APP schema or reader changes. |
| `tests/test_build_authored_references.py` | Coordinator-assigned two real-Core owner-contract witnesses only: actual current producer receipt/selection and current source-storage loss; preserve legacy rejection and all original cases/assertions. |
| `tests/test_cutover_dungeonmind_first_world_initialization.py` | Native client and five named residual witnesses: Page lineage, committed snapshot, activation outage and two frozen-component variants. |
| `tests/test_cutover_graph_review_authoring_continuity.py` | Native operator fixture and current native-ID/durable-output prerequisites in existing continuity witnesses. |
| `tests/test_cutover_native_genesis_continuity.py` | Native operator fixture and current native-ID/durable-output prerequisites in existing continuity witnesses. |
| `tests/_cutover_d3a_blocker_safe_fixtures.py` | Current extraction component resolver signature in owned synthetic-run mutation helpers only. |
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

## Authenticated fixture batch ownership adoption

Coordinator authorizes authenticated fixture corrections. Narrow CI test-only
lease extension: tests/local_operator_client.py and four modules
tests/application_state/test_plan_work_object_postgres.py,
tests/application_state/test_play_active_run_postgres.py,
tests/test_graph_existing_object_resolver.py, tests/test_live_artifact_reads.py.
The APP foundation/play-continuity handoffs are DONE (#641/#649) and World active
Run charter is MERGED/HISTORICAL (#952). Current active APP accepted-prefix work
owns validators/storage, not these four endpoint fixtures. Graph route#2276
ownership is independent and untouched. No auth production/policy/test denial
lease is transferred. Configure only these non-auth owner tests to the actual
supported local_operator mode over an explicit unproxied loopback peer, retaining
all production middleware and original test bodies/IDs/assertions. Dedicated
hosted and graph auth tests retain their own environments and must stay unchanged.
This is explicit test authentication setup, not a global permissive test mode.

Authenticated fixture author evidence: exact prior candidate5e08 allfour modules
39passed/21failed in10.91s. Corrected same60IDs58passed/2failed, with69additional
dedicated hosted/graph auth and CI guards allpassing (combined127passed/2failed
in12.57s).19original failures resolved; remaining two directly create a Page
without its required World owner. Test function ASTs and all60 ordered nodeIDs
are identical, duplicates0. No product authorization or denial tests changed.
Two explicit helper guards prove supported loopback succeeds and remote peer
still receives real403 hosted_auth_local_boundary. Exact owned test DB removed.

## Explicit source fixture correction batch

Coordinator authorizes source fixture corrections. Extend this test-only lease
to tests/test_cutover_dungeonmind_first_world_initialization.py solely for its
native_first_world_client fixture: pin deterministic UUID at the actual APP
world_catalog.service allocator (registry now delegates), and configure the real
supported local middleware boundary alongside its existing token-based Graph
auth. No fixture/test assertions or product source change. Legacy CUTOVER
charters describe#651-era work; current origin/main includes the later1959,1960
and2058 changes on this fixture. No active CUTOVER writer/task/worktree was found;
current Graph route lane writes UI only. Adopt this narrow fixture seam into CI2;
retain all broader CUTOVER acceptance obligations.

The two existing Plan module residuals are in its already granted source fixture
lease: create a real catalog World and supply its explicit world_id for the lore
Page prerequisite. Preserve fail-closed unavailable-DB and latency assertions.

The source correction batch additionally owns the two obsolete label keyword
arguments in tests/_cutover_d3a_blocker_safe_fixtures.py. Their production helper
now accepts only(repo,uri); synthetic fixture paths/payloads/digest resealing and
all validation assertions remain. This helper belongs to the same historical
CUTOVER fixture lane, with no current matching writer found.

The Page outage witness reaches a genuine retired test contract: #1990 moved
Worldbuilding Pages from file-backed storage into typed PostgreSQL. Keeping its
old200-under-DB-outage expectation would require a prohibited production fallback.
Retain the original positive200/exact-record assertions with the healthy owner
before cutting its DSN, then assert503 for source-filtered outage as well as the
original unfiltered/runbook outage assertions. This strengthens current fail-closed
coverage without dropping a case or original assertion; it explicitly migrates
the old file-availability assumption and requires independent contract review.

Source batch final author results: all60original scoped endpoint IDs pass, plus
69dedicated hosted/Graph auth and CI guards=129passed12.66s. Same54native baseline
IDs now44passed/10failed28.97s, no errors:54missing-DSN baseline→7pass with native
provisioning→44pass with current UUID/auth/resolver prerequisites. Residual10
remain visible:2native Graph reference admission409s,1retired filesystem registry
mutation,2removed internal patch seams,2file-only source/span tamper fixtures,
and3continuity fixtures lacking auth. No assertion or product policy relaxed.
Every original assert AST/decorator/name in the touched test modules is retained;
the outage test adds the source-filtered503check. Both owning disposable DBs clean.
Broader full totals remain pending and cannot be inferred by signature counts.

## Native residual batch: current storage fault boundaries

Coordinator authorizes the remaining native residuals without ADVERSARY overlap.
This batch extends only the existing D3A test module lease: replace the deleted
workspace registry mutation with an actual owned Page commit; use the current
committed Page snapshot owner; inject activation outage at the current APP catalog
save seam; and replace inert file source/span edits with current durable component
mutation/resealing in the owned test DB. Preserve exact API rejection codes, zero
preflight/publication assertions, recovery/idempotency and binding identity checks.
No production writer/auth/admission change or external data mutation is allowed.
The INGEST benchmark and APP accepted-prefix files remain read-only.

The same coordinator-assigned ten-residual batch adopts two additional historical
CUTOVER client fixtures: graph-review authoring continuity and native-genesis
continuity. Last shared change is merged2058; no active writer/task was found
on these fixtures. Add supported local operator configuration, explicit loopback
peer and test-only bearer credential through the scoped helper. All real hosted
and native Graph middleware/dependencies remain installed; preserve the test
bodies, including fresh-client restart assertions. Dedicated denial tests remain
unchanged and run alongside the batch. No ADVERSARY lease is touched.

Native residual author subset: same54originalIDs now49passed/5failed with no
setup errors;71dedicated auth/CI/fixture checks allpass (combined120passed/5failed
in30.77s). Current principal setup advances three continuity witnesses past
auth and exposes their next stale native-ID/durable-output assumptions. Two
authored-reference cases still409; read-only exception observation identifies
"Authored selection snapshot is unavailable": their first-world receipt pins
legacy world_graph D0, while the current query checks a native vNext selection
snapshot. This is an unresolved producer/reader contract, not permission to relax
admission or silently replace the fixture with an easier path.

The source variant now changes the sealed run's exact source reference digest
through the existing owned test CAS helper and proves the immutable source body
is unchanged. Source bytes are not ingest outputs and cannot be persisted via
that API; no synthetic mutable source owner is introduced. Span variant persists
real changed output under its new digest. Original request422/409, zero preflight
and zero native revision checks remain. Activation failure now occurs at actual
APP catalog.save_world with ApplicationStateUnavailableError, then real retry.

Independent review ofc04 identified a coverage gap before approval: changing a
run's source digest tests binding drift, not the original source-byte corruption
path. Preserve[source] as a real source-service read fault: read the exact stored
record, change only returned Markdown with original metadata, and require the
actual registry digest check to reject it. Assert the fault was exercised and
the real stored body/metadata and run binding remain unchanged. Retain the
binding fault as one additional[source_binding] case; all three original
parameter IDs and their rejection/zero-publication assertions remain. No
production corruption, fallback, exclusion or compatibility relaxation.

Corrected author boundary verification: full three native owning modules, the
nine additional original selected cases and71auth/CI checks collect138cases;
133pass/5fail31.72s, no errors. All original54subset IDs remain49pass/5fail;
one new source_binding case passes separately. The real source-body fault
[source] passes with fault-exercised, immutable-store and unchanged-run checks.
Both named APP/Core clusters cleaned. The five remaining IDs are unchanged:
two unavailable authored-selection snapshots, two managed/native-ID count
assumptions, and one missing durable synthetic extraction output. Independent
review must cover the corrected cumulative head before any disposition.

## Native continuity identity/output batch

Coordinator's remaining-native assignment adopts only the existing two continuity
modules' fixture prerequisites and native Core call operands. Current first-world
creation reserves a native UUID distinct from the managed World ID. Read that
actual binding after confirm; use it for Core counts, direct snapshot/read/write
calls and native response assertions. Keep managed IDs in product HTTP requests
and the legacy-file tripwire. Use explicit World scope/campaign=None for the
uncampaigned native first-world genesis instead of an invented managed campaign.
Preserve all original receipt/revision/idempotency/source/privacy assertions and
counts; add separation assertions. The post-genesis synthetic run must persist
its actual candidate/span bytes through the existing ingest component API before
freezing status; no production path reads these files as fallback. No producer/
reader admission relaxation or ADVERSARY path is authorized.

Continuity request fixtures now select the actual unique frozen span ID for their
existing selected text, as the current manual authoring API requires. The hint
is derived from the real retained source/index and still verified by production;
no source-span check is patched or weakened. Direct v1 wire DTOs require a string
campaign field, so World-scope requests send the supported empty string, which
the adapter maps to Core campaign=None; no campaign is invented.

Two later prerequisites surfaced after correcting native IDs: registered source
locators are now object:// identities, not repo-file grants, so the source-read
witness asserts the opaque locator and reads actual registered DB bytes, retaining
all exact excerpt/digest/revision assertions. The child publication fixture must
actually admit its synthetic recap source through the existing real Core admission
helper, as its sibling D3A witness already does; a sealed hash alone is no source
authority. Preserve admission and idempotency fences rather than bypassing them.
The one retired URI-parsing assertion is explicitly migrated to the current
anti-filesystem contract; no positive source-body/excerpt check is removed.

The continuity child fixture uses the actual sealed identity gate's node_id_map
for its published canonical child ID, rather than assuming a provisional preview
ID survives promotion. Assert the mapped child was absent at D0, exists at D1
with its exact intended label, and retains the original parent/source/retry/
recovery checks. No guessed mapping or production identity override is introduced.

Continuity batch author result: complete138-case native/auth boundary now
136passed/2failed in33.21s, no errors. All three continuity journeys pass actual
read/write/source/restart/recovery checks. Original54subset now52pass/2fail;
eight of the ten initial native residuals resolved. The only two failures remain
the independently diagnosed legacy-D0/native-vNext authored selection contract.
Test names/decorators unchanged; every original assertion retained after explicit
managed→native and provisional→canonical operand mapping, except the one
documented retired file-URI assumption replaced by opaque-URI plus real-DB-body
checks. All source bytes, span hashes, revisions, receipt counts and replay/
idempotency assertions remain. Both owned database clusters cleaned.

## Stable full qualification partition batch

Coordinator explicitly authorizes coverage-preserving full-lane partitioning.
Use four versioned SHA-256 buckets of canonical collected Python file paths.
Keep every case in a file together; never hash generated UUID node labels. Each
worker collects the full default suite first, proves the exact raw-node Counter
union/disjointness, records the same36default deselections, and then selects its
file bucket. Invalid arguments/paths, duplicates, empty collection/partition or
deselection drift fail closed. Four source-pinned reports are mandatory; aggregate
checks exact per-worker plans, file coverage and parameter shapes (only generated
UUID labels may vary between same-source processes). No normalization affects
selection or exact per-collection parity.

Keep original unpartitioned full-regression CLI and all old PR commands unchanged.
Every backend shard retains the old locked tool/dependency setup and independent
APP template/clones plus separately migrated native Core cluster. Matrix fail-fast
is false. Run all frontend tests/type/build/visual separately in parallel; a test
failure does not suppress the other two commands, and every failed step still
fails its job. Qualification aggregate requires all backends, frontend, collection
coverage and the unchanged image/browser witness. This is execution partitioning,
not domain/change selection or rollout. Existing120-minute backend limit remains;
only real hosted measurements can establish the new latency.

Independent review R5 atd7 reproduced inherited--ignore dropping10cases before
collection while reduced reports agreed. Correct before approval: reject inherited
PYTEST_ADDOPTS/PYTEST_PLUGINS before owned DB allocation and again in runner/hook;
reject ignore/glob/config/root/plugin/discovery overrides and runtime early-stop
options. Only cache/log timeout ini overrides remain permissible. Explicit
collect-only diagnostic reports are marked and cannot satisfy execution coverage;
parity verification must opt into a clearly labelled collection-only proof.
Original worker/aggregate execution commands never pass that diagnostic option.

### Current authored-reference test-contract repair

Coordinator explicitly assigns the two remaining real-Core cases. Remote main
was fetched and open PR/leases inspected before edits; no active open writer
owns this test file. Historical AGENT authored-context design is BLOCKED and
BUILD same-page quote lease is DELIVERED; REFERENCE authored input is delivered.
No ADVERSARY path is touched or outreach sent. Local successor preparation at
de0e4504462ab3335b03d06814cc1da305bbb1d9 preserves the running PR head.

The first-world confirmation receipt identifies its legacy world_graph D0, not
a current vNext entity-selection receipt. The test must not silently treat it as
a valid current revision. Keep real first-world initialization and immutable
source admission, then publish the selected entity using the current governed
Core producer with evidence from that exact admitted source. Select the actual
returned entity ID and child revision; verify both real repository snapshots and
explicitly reject the legacy receipt before source reads. No automatic migration
or production fallback is implied. Source-loss injection belongs at the current
Core source-body read and must be exercised, preserve stored source bytes, forbid
the writer and retain exact unavailable receipts. Original two parameter IDs and
positive/negative APP outcome assertions remain mandatory.

Graph witness sequencing remains an explicit coordinator/user decision, not a
technical waiver: (A) retain stage2 HOLD until graph work resumes and its reviewed
behavior is on main, then rerun the same mandatory witness; this postpones stage2
completion despite candidate proof. (B) explicitly revise the staged contract so
CI infrastructure/other proven portions can advance while main graph/persistence
acceptance remains a separately named unresolved required gate; candidate proof
must remain labelled candidate-only and cannot set main readiness true. Option B
changes the original stage2 acceptance sequencing and therefore needs coordinator
resolution with Alan before implementation. Neither option merges graph early,
removes the witness, claims qualification on main, or changes existing PR gates.
Current code implements A/HOLD. Candidate915b142b6a8109b494578c57bcc1b4a2ff9bbe4d
passes all6 image/browser/fault checks102.846s with all11 cleanup checks. Current
main-based composition54fdb76b5bf1ccbae3bc45bd69ccf2e0b156d7e5 passes5 image
checks125.161s but refuses graph_route_dependency_missing; all11 cleanup checks
pass. These measurements are not a controlled performance comparison.

Coordinator disposition now preserves hard422/zero-writer source loss. The shared
native acquisition owner is adopted for this narrow product correction: its only
tracked exclusive implementation lease (REFERENCE plan-authored-input) is
MERGED_AND_DELIVERED, and no open writer owns this file. RETRIEVAL verified-support-
once owns native_graph_reads.py, which remains untouched; ADVERSARY's provider
execution/types/context-test lease remains untouched. No outside outreach. This
is an explicit bounded exception to the earlier test-only qualification scope,
not permission for broader runtime changes. Record actual native unavailable
read evidence, then refuse before writer authority; never fabricate classic
receipts or discard partial inventory. New current-native producer witness does
not claim first-world D0 object migration. Source-loss replay must not silently
redispatch and stored source must remain unchanged.
