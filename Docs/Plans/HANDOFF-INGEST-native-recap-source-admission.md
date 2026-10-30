# INGEST — native recap source admission

## Authority and lane

ACTIVE, serial, PRIME-owned source-admission capability. Base:
`e0fc8907aaa32c9b413a00ca6d282a2ee626360b`; branch:
`codex/native-recap-source-admission`; reuse the existing Buddy context-loop
checkout and pinned dependencies. Open1853/1855/1868 own historical identity/V7
reads;1828 owns hosting;1764 remains held. No overlapping lease is transferred.
No new checkout, container, environment or source export. Models, prompts,
extraction, identity repair and fact publication are outside this slice.

PRIME owns runtime and delivery; ADVERSARY owns independent fixtures, gold,
assessment and original failures. Starting portable contracts under the private
recap-admission-contract-preflight-v1 root remain retained:

- v1:742f99cbec8cdddbcffe8997b35308b1230590547b0a2cde86e63afd367d0f34
- v2:71e0f48b3a5e3a4256a2d0a5422008931610b79edad683ab6efeacd1a933647c
- v3:4c555e38680fb096125070b796313b77a8e823f41558775c55e5294d37196d41
- v4:4e1ca8951409372aadef1ce33c4544d99209111f146ea73e733dfdb4f5a60c88

Independent architecture review approved the source-only seam and the explicit
corrections below. This current contract supersedes earlier assumptions about
outside-root provenance and the legacy publication broker. The independent0750
ordinary503 and all prior failures remain evidence; they are not rewritten.

## Initial admission

Use ordinary POST `/api/live/recap-ingest`, operation
`build_graph_preview_bundle`, with exact source-only flags: extract_graph=false,
candidate_graph_path=null, force_graph_run=false, materialize_after_extract=false,
include_graph_extraction=false, session_evidence=[], raw_text=null,
graph_model_id=null, force_stage=false, force_recap=false.

Authorize before source/APP/native access. Declared local deployment retains the
existing nonblank GM check. Hosted deployment uses the real middleware principal,
origin/World checks and authoritative World owner/MANAGE permission. Record the
subject and local_gm/world_manage basis. No hosted denial falls back to local
credentials. One narrow code-owned route resolver mapping is shared by hosted
middleware and startup/readiness validation; other recap operations stay denied
through that hosted mapping. No global native-auth change.

Resolve managed/native identity and binding version with
`resolve_managed_source_identity`; use a small typed source scope. Campaign and
session are source-grouping metadata, verified against actual committed
normalized frontmatter. They are not verified membership, Graph context,
permission or fact-publication authority. Later fact publication must obtain its
own lawful campaign authority. Existing classic Graph/extraction operations
retain `_request_recap_context` and their broker enforcement unchanged. Native
source admission has no legacy publication endpoint/token/head dependency.

Use the current committed normalized-source inspection. Require a current stage
with matching valid expected/output digests; pin that digest through the actual
read before persistence. Resolved paths must lie inside the authoritative managed
World source_root, including symlink-escape refusal. The old normalized-path
helper returns its own path/digest and is not original-source provenance; no
outside-root fallback is allowed. Artifact/output storage may be separate. Resolve the managed root from the original caller root before applying an artifact-root override; retain that exact managed root through admission, status, binding checks and recovery.

Check selected-input size against Core's existing MAX_NATIVE_TEXT_BYTES before
opening and use a limit+1 bounded read to defend growth. Preserve input bytes,
raw SHA and separate canonical UTF8/universal-newline/terminal-LF SHA; canonical
body must satisfy the same Core budget. Never infer or rewrite NULL-World rows.

Bypass classic preview/extraction/span-bundle generation on this exact branch.
Reuse World-scoped recap artifact registration and immutable APP source storage.
Create a deterministic source-only DRAFT ingest.run using
fresh_recap_native_source_v1: no fabricated components, classic head, REVIEWABLE
status or source_span_bundle_ready claim. Persist intent before native effects;
freeze exact Core parent/descriptors/request hash before dispatch. Core must
already own a native head; do not create a new genesis authority.

Admit only dungeonbuddy.source:session_recap, primary, GM-private, with one full
canonical-body context span. A receipt proves source admission, not model
exposure, extraction, played facts or full ingestion. Core owns head/effect/
idempotency; existing APP ingest.run and CAS own intent/recovery. No new ledger
or table. Preserve actual receipt/child before opening or APP settlement can fail.

## Recovery and visibility

Production-mounted status uses the same POST route, operation inspect_status,
exact native_recap_run_id and selected World/campaign/session. Authorize first,
then load exact scope before corpus scanning. No CAS, lock creation, provider,
publication or file write. Return strict dmb_native_recap_source_status_v1 and a
server-generated exact status_request; do not mount the developer/eval router.
Generic raw run/result.run/build-context/catalog serializers omit only the private
lineage.native_recap_source block on copies; storage stays complete. Errors and
other projections must not leak private commands or validation inputs.

Explicit source-only resume is {run_id,expected_run_revision,command_sha256}; hash
is null only before a command exists. Load the frozen APP run/source directly,
revalidate selected scope and current caller, and re-read under the origin mutex.
Changed/deleted live files cannot block or retarget recovery. Ordinary duplicate
imports are status-only. New admissions still require current committed source
verification.

Borrow PublicationProgressStore.exclusive as a mutex only, keyed by immutable
admission origin under the canonical shared artifact root's
out/native_recap_source_locks. Hold across reconciliation, CAS, Core I/O and APP
settlement; never unlink/replace lock files or read/write progress JSON. Busy
means no dispatch. Execution requires single-host/shared-root topology; inspection
never probes that mutating mutex. No elapsed-time/PID inference.

Entered/unknown recovery may reconcile or redeliver only the same frozen request
under explicit resume, mutex, winning CAS and Core idempotency. Receipt absence
never permits reparenting. Only Core's typed definitive prewrite-stale outcome
permits an explicit new-parent command, preserving the prior command/outcome.
One attempt per POST; no implicit retry loop or arbitrary attempt cap. Retain all
initial failures and delivery history. A local mutex does not prove absence of a
remote effect.

## Reader fence and delivery

New APP0096 follows0095 without rewriting rows. Exact-head checks fence older
generic writers that could replace the new private intent; new same-lifecycle
CAS/update/supersession guards remain. Downgrade refuses: recover forward.
Protected delivery drains owned writers, verifies backup/fingerprints, explicitly
advances APP and starts compatible code, then proves retained state and health.
Preserve the pre-existing local standing-router omission under the independently
approved exact two-line composition; this slice does not deliver standing.

## Exclusive expected writes

- This handoff and anchored-coachmark predecessor settlement.
- src/graph_memory/ingestion/native_recap_source.py.
- src/application_state/ingest/service.py and migration
  versions/20261030_0096_native_recap_source_intent.py.
- apps/live_control_server/integrations/dungeonmind/native_recap_source_admission.py.
- apps/live_control_server/services/native_recap_source_admission.py.
- routes/recap_ingest.py; main.py only the narrow hosted resolver wiring.
- routes/graph_preview.py and services/ingest_run_catalog.py: public omission only.
- services/graph_run_registry.py and source_artifact_registry.py only if the owning
  persistence seam requires it; neither currently needs an edit.
- Owning source-admission tests and affected recap/catalog/APP tests.

Paths without a root above are under apps/live_control_server. No Core edits,
broad router activation, generic locking framework or production extraction
runner changes. Re-anchor and amend before expanding this lease.

## Gates

Real disposable APP/Core authority through authenticated ordinary HTTP: exact
version/opening, real normalization without a broker, scope/frontmatter/root/
symlink refusal, raw/canonical hashing, same-source idempotency, changed-source
origins and NULL refusal. Verify all generic projections omit private lineage
without altering storage, production status routing and error non-disclosure.

Cover separate-process contention/hard-kill and committed in-flight Core effects,
unknown replay, live-file removal, partial APP/native commits, explicit stale-parent
recovery and CAS losers. Prove read-only status has zero writes. Verify old rows
survive0096; older installed heads refuse get/update/supersede before mutation;
retained new work survives and downgrade refuses. Use existing fixture services
and pinned Coreb73c115/GEe9366ef/WKef9c50f; no primary-state test mutations.

Inspect cumulative diff; obtain independent exact-head review and CI; commit,
push and update the one owning PR. Evaluator effects require a separate exact
resource lease after review. Preserve frozen originals and full-ingestion0/15
until the complete independent chain is proved. Protected delivery follows gates.
Tour memory-anchor follow-up, remaining journeys and operator acceptance stay open.
