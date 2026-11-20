# INGEST: database-owned private execution evidence

Status: MERGED_DELIVERED as PR2049 at
1e5ae2d0d432f141ce5a411d0a368909233ebd9f; implementation lease closed. Exact
reviewed head 9e0dddde passed independent review and all seven CI checks; the
actual merge tree/patch matched. Conserved delivery proof:
database-execution-evidence-api-delivery-proof.json. All 91 primary tables,
nine session files, saved Plan HTTP and UI stayed unchanged. ADVERSARY's later
isolated S6 run retained seven responses with no retries and reopened exact DB
components; that is lifecycle evidence, not semantic-quality acceptance. Gold
and ingestion quality remain independently owned by ADVERSARY.
Owner: PRIME. Base: origin/main@ba208e8002413f3aec228d3ac7ec7fe715fe40dc.
Design/initial implementation started from delivered2046@783980f28; rebased after
independently reviewed/all-green2047 and2048 merged, with disjoint patches.
Branch: codex/database-execution-evidence.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: serial after merged/delivered PR2046. PR2047(profile common guidance)
and PR2048 (unused party-fill/schema retirement) are merged predecessors with no
shared write paths. Their separate conserved API delivery completed at ba208e8.
Proof recap-common-and-party-retirement-api-delivery-proof.json verifies all 91
primary tables, nine session files, saved Plan HTTP, UI and 439 native objects
unchanged; lease RELEASED. Reuse the existing checkout/dependencies and disposable
PostgreSQL on 54329 only.
No new provider, primary database, runtime, Graph/Gold or publication effect lease.

## Outcome and design adoption

Both live GE adapters retain attempt responses and usage through existing APP
immutable component storage. Remove mandatory output directories, file globs,
file-ledger writers and post-REVIEWABLE revocation. Preserve exact private bytes,
source/profile hashes, actual attempts and honest unknown outcomes. Do not add a
provider, table, public reader, generic callback framework or compatibility sink.

Adopt the independently critiqued design93197c844b121aa87304a488a0895b38a6b76233daf2645479868aa179f6c7c2
and its atomic replay/PREPARED revision/sealing conditions. Installed GE already
awaits on_attempt_completed and emits nonretryable ATTEMPT_EVIDENCE_PERSISTENCE_FAILED;
reuse that contract rather than duplicating its provider-error policy.

Bind only after the real PREPARED CAS, with actual run/revision/source/profile/model.
Private APP event persistence validates exact binding and contradictory replay
under the existing run lock. Public get_component_bytes stays exact-bound only;
source-only runs cannot own generic outputs. Staging grants no publication power.
Commit pass intent before dispatch and each callback before acknowledgement.
Recover committed records after child loss without globbing. Retain normalized
actor evidence. Callback-acknowledged bytes survive later kill/cleanup; death
during retention can leave unknown outcome and must not invent complete counts.

Seal raw/advisory evidence together and PASS_TELEMETRY before advancing/finalizing
success or failure. Persistence/sealing failure records explicit non-reviewable
INCOMPLETE reconciliation when possible; never freeze inaccessible partial bytes,
suppress retention errors or redispatch. Existing PR2046 returns exact saved
pending/failed state. Keep real worker isolation/deadline kill/reap and temporary
receipt IPC as transport, a separate concern from persistent evidence authority.

## Exclusive expected write set

- src/application_state/ingest/components.py: private exact execution-event
  binding, atomic replay and recovery on the existing component table/run lock.
- src/graph_memory/extraction/bounded_recap_execution.py: DB capture/binding,
  honest accounting and final private evidence composition; retire file sink.
- src/graph_memory/extraction/_recap_inference_worker.py: commit callbacks through
  the bound owner and retain existing GE failure distinctions/temporary IPC.
- src/graph_memory/extraction/graph_preview_runner.py: concrete client binding and
  pre-terminal sealing, with explicit retention reconciliation on all exits.
- apps/live_control_server/services/graph_preview_runner.py and
  apps/live_control_server/services/worldbuilding_ge_execution.py: retire both
  file-ledger gates and output-directory requirements, preserve source/model pins.
- apps/live_control_server/services/build_recap_launch.py: retire obsolete output
  argument; preserve exact Build reservation/recovery.
- src/graph_memory/extraction/worldbuilding_edge_review.py: private diagnostics
  component references replace file locators; preserve advisory bundle content.
- tests/application_state/test_ingest_components_postgres.py,
  tests/test_bounded_recap_execution.py, tests/test_recap_inference_worker.py,
  tests/test_recap_generationengine_default.py, tests/test_worldbuilding_ge_execution.py,
  tests/test_worldbuilding_edge_review.py: update owning evidence assertions and
  add synthetic/real-process/disposable-APP failure regressions.
- Docs/Plans/HANDOFF-INGEST-recap-explicit-retry.md: truthful delivered predecessor
  settlement at783980f28, original-head CI +33merged-tree checks, retained-state
  proof recap-explicit-retry-api-delivery-proof.json; close its implementation lease.
- tests/test_build_recap_source.py, tests/test_recap_managed_standing_context.py,
  tests/test_artifact_data_root.py, tests/application_state/test_session_evidence_consumers.py
  and tests/test_registered_recap_input.py: narrow retired-argument closure as
  described below; no unrelated fixture/style repair.
- This handoff. Any other required caller or public contract is a scope checkpoint.

## Independent proof and delivery

Exercise both live adapters with persistent output unavailable; failed and
conformance attempts; callback acknowledgement followed by real child kill and
cleanup failure; ambiguous persistence; malformed receipt; source/run/revision
substitution; identical/contradictory replay; failed final sealing; existing public
bound-read and source-only refusal. Preserve original failures and frozen files.
Use synthetic process-safe GE/provider doubles and existing disposable54329,
never primary data or fresh real ingestion. Independent Bugbot review, cumulative
diff inspection, applicable CI and conserved delivery remain required. Prompt/
semantic quality, Gold and fresh model captures remain ADVERSARY's work.

ADVERSARY confirmed no active capture driver needs the live file interface. Its
next S6 Process driver will read exact run-bound RAW_MODEL_RESPONSE/PASS_TELEMETRY
and export linked immutable evidence after this contract is reviewed/delivered.
Historical drivers and fixed-run file consumers remain untouched. No file-writer
compatibility path or manual Graph curation is authorized.

The shared storage/client/controller/adapters are one indivisible owner change:
a staging-only API has no exercised consumer, and removing the shared sink without
both active adapters would break existing required audit capture. Review APP
atomic/revision guards, child capture, parent recovery, generic lifecycle seal,
then both adapters and the actual failure proofs. No unrelated discovery UI,
fixture debt, profiles, schemas, model policy, Gold or publication changes.

## Caller-closure checkpoint

Retiring the live output_dir argument also requires narrow call-site changes in
four existing tests: tests/test_build_recap_source.py,
tests/test_recap_managed_standing_context.py, tests/test_artifact_data_root.py and
tests/application_state/test_session_evidence_consumers.py. These join the exact
write set only to remove the retired argument/its exclusive path-confinement
assertion, preserving their current source/context/DB assertions. No compatibility
parameter is retained. The already-owned Worldbuilding GE test fixture must use
the existing save_page DB helper instead of its retired page-file write before
it can exercise this adapter. This directly required fixture adaptation is in
scope; broader inherited fixture debt remains excluded. No added capability,
public contract or data effect. Owner/storage tests9existing +11new now pass
separately; the initial new fixture omitted recap campaign/session and was fixed
without weakening the actual invariant, with original output retained.

The final caller search also found tests/test_registered_recap_input.py passing
output_dir to the same recap adapter. Its allowlist expansion is limited to
removing that argument while retaining source-scope rejection assertions. No
other output_dir uses belong to this adapter; unrelated export/transport APIs
remain outside scope.

## Coherent implementation checkpoint (not merge/delivery acceptance)

Both live adapters now use DB capture/sealing; their mandatory directory/glob/
ledger and late-revocation code is gone. Source/model/profile/Build reservation
contracts remain. Owner9existing+11new checks,73bounded checks,29Process/Build,
21actualworker cases and10actualdefaultGE/controller cases passed. Worldbuilding
native composition8cases and its config/scope controls pass after the fixture
uses save_page plus explicit disposableDB; advisory byte/accounting/reopen checks
pass after synthetic events meet the native event identity contract. Original
fixture/setup failures remain private evidence, never product-quality claims.

The old wrapper-only ledger test is retired; stronger real-controller success,
failure and pre-terminal retention tests replace it. Five narrow argument-only
caller files have35pre-existing Ruff diagnostics with no additional rule/message
occurrences at base/head (database-execution-caller-lint-baseline.json); do not
remove pytest fixture imports or reformat unrelated tests to conceal this debt.
Core modified runtime/capture tests pass targeted Ruff/diff checks. This checkpoint
grants no live effect lease or quality acceptance.

## Exact-head review and final caller evidence

Bugbot independently APPROVED code head b6703ca1fec838fd6c7886c21a99a792c65f8c8b
against ba208e8 after reviewing all 21 paths and passing 30 storage/default-GE
checks plus four actual worker failure checks; no actionable findings. ADVERSARY
independently passed 74 owning checks and one synthetic default-GE → database
responses → governed native prepare/commit/replay proof at that same head.
Exact proof, pins and hashes:
/tmp/pr2026-audit-8779/pr2049-b6703ca-independent-proof.json. Its synthetic
membership transport seam and disposable-only limits remain explicit. It does
not establish actual model quality, live 5202 behavior or operator acceptance.

Final author bounded/advisory/caller/ordinary Process/Build cohort: 219 passed and
four failed. All four failed node IDs and exact exception messages reproduce at
current base ba208e8: two artifact-root fixtures omit required typed source/World
owners; two historical session-evidence cases use obsolete recovery/input
expectations. Original head/base logs and
database-execution-caller-failure-comparison.json are retained. No assertion was
relaxed or adjacent fixture debt repaired. The five narrow caller files retain
35 inherited Ruff diagnostics with zero additional rule/message occurrences.
CI, final documentation delta qualification and protected delivery remain
separate required gates.
