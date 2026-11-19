# MIND B2 — native first-World lifecycle

**Status:** DESIGNED / READY FOR MIND RE-ANCHOR; no implementation write lease
until the consuming owner completes the activation checks below.
**Design anchor:** Buddy `main@98d3157a09790e5a53a851b9ea24a5de51bd2aa5`;
**Auth-boundary re-anchor:** Buddy `main@3624806dd` (2026-11-19);
Core #231 merge `cf197b9939f7b9106c75a8afb9fcf918c8b4aa1c`, adopted by Buddy
#4093 merge `5289f99c27263c1176682588433921592ea818a2`.
**Prerequisite settled:** Buddy #4097 B1 compiler merged at
`cf8ab495965026334249eba557be3843a1c5d45d`, reviewed final head
`3dbefaec9b9ea56fa03071c83d9c4202b8d1a904`. Re-fetch current main and active
leases again before adoption; the B1 merge does not itself activate B2.
**Topology:** serial: #4097 → B2 one independently reviewed implementation PR
→ later managed-default retirement. No PRIME or standing-steward gate.
**Owner:** the user-authorized MIND first-World completion lane. Implementation,
review, merge and launch authority follow that user's assignment; this design
itself does not perform a serving switch, authorize primary-data writes, or
claim full V10/V11 completion.

## Outcome and boundary

The actual first-World review/confirm path publishes the reviewed B1 inventory
into the same native KnowledgeSpace as source admission, then activates only the
exact reserved APP binding after verifying real native publication and ancestry.
It does not write a new classic first-World revision, dual-write, relabel a
classic D0 receipt, predict allocated IDs or fabricate a WorldKeeper context.
Historical classic receipts and previously retained recovery records remain
truthful and explicitly readable; they must not be reinterpreted as native.
The existing `activate_reviewed_native_graph` requires a classic
`reviewed_world_initialization` and null-parent D0; introduce an explicitly
typed native proof/activation path rather than weakening that check.

B1 is a pure compiler/binder, not current source authorization. In particular,
`SourceRevisionV2` full-body digest and native span proof bind supplied bytes
and actual parent evidence; they do not establish the persisted raw-to-native
association, present principal access, reservation ownership or current source
admission. B2 must establish and seal those facts at their owning boundaries.

## Proposed exclusive write set after activation

- New `apps/live_control_server/models/native_first_world_publication.py` for
  explicit versioned native prepare, sealed plan, confirm and receipt types.
- New `apps/live_control_server/services/native_first_world_publication.py` for
  lifecycle orchestration; existing `services/first_world_graph_publication.py`
  only for first-World dispatch/retained-classic compatibility, and
  `services/world_graph_binding.py` only for a distinct native proof and exact
  reservation activation. Preserve existing classic and native-source checks.
- `apps/live_control_server/routes/extract_promote.py`: **section split only**
  for the two `/worldbuilding/first-world/{prepare,confirm}` handlers and
  their response/dispatch wiring. Use local imports or a separately defined
  versioned router/model where needed. **Exact import-wiring exception:** remove
  only `FirstWorldGraphConfirmReceipt`, `FirstWorldGraphConfirmRequest`,
  `FirstWorldGraphPlan`, `FirstWorldGraphPrepareRequest`, `confirm_first_world`
  and `prepare_first_world` from their existing shared blocks when their only
  uses in these two handlers are replaced; add dedicated native protocol and
  historical-response imports immediately adjacent to the first-World handlers.
  These are the six exclusive legacy imports present at Buddy main
  `f27992d11`; do not remove any additional name without separately establishing
  its scope. Otherwise do not edit shared import blocks, common auth helpers,
  middleware, recap, generic Worldbuilding, source observation or location-
  binding routes. Preserve `_reject_selector_query`, the existing
  first-World authorizer, error safety and hosted/local principal semantics.
  A necessary edit outside this exact section requires an explicit new split or
  transfer before editing, not a blanket claim on this shared file.
- `apps/live_control_server/services/hosted_native_graph_access.py`: **function
  split only** for `resolve_hosted_first_world` to parse the versioned native
  first-World request and establish current subject/World ownership. Put narrow
  first-World auth witnesses in the existing owning test file below. Do not edit other
  helpers, middleware, generic auth, recap or location paths; no blanket lease
  on this file or transfer of #3824's other sections is implied.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewFirstWorldPublishSheet.tsx`,
  `firstWorldPublicationRecovery.ts` and their existing owning tests, plus new
  dedicated first-World API/type implementation modules under the same workbench
  or `src/api/`. Extend existing first-World UI test files; avoid new test files
  that would require the shared classification inventory.
  Wire the actual ordinary first-World UI to the native protocol and preserve
  retained exact-request recovery. Do not modify shared `src/api/types.ts` or
  `src/api/extractPromoteApi.ts`.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`:
  **section split only** for mounting a dedicated saved-first-World recovery
  affordance independently of mutable exact-review readiness, with a local import
  if needed. Clamp it to the currently selected managed World and run, preserve
  `sourceReviewOnly` restrictions, and do not change general navigation, agent,
  correction or other publication behavior. The current publication component
  is gated on ready `exactReview`, so a missing/error review package must not
  prevent recovery of an already-submitted exact native plan.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorldbuildingPublication.tsx`:
  **section split only** for first-World saved-entry selection/wiring; source
  revision changes must not hide a submitted recovery. Leave normal subsequent
  Worldbuilding, native and recap publication behavior untouched. The recovery-
  only panel may be exported from the already allocated first-World sheet or a
  dedicated first-World component; it must not require today's candidate review.
  Use existing `firstWorldPublicationContinuity.test.tsx` and existing sheet/
  recovery tests for mounted reachability; do not allocate the shared
  `GraphReviewWorkbenchModule.test.tsx`.
- **Narrow B1 transfer into this B2 capability:**
  `apps/live_control_server/services/native_first_world_compilation.py` only for
  the `_span_requirements` `source_ref_id` correlation-versus-document-reference
  equality correction and the native binder's evidence-role check described
  below; and `tests/test_first_world_typed_evidence.py` only for focused coverage
  of those two corrections. Keep nonblank correlation validation,
  full raw audit/request commitment, and all artifact, revision, full-body
  digest, frozen index/span, locator and native-proof checks unchanged. This is
  a required producer-mapping correction, not a bridge, ID prediction, relaxed
  source authorization, new public contract, or generic metadata expansion.
  Do not edit B1's models or unrelated compiler behavior.
- Owning tests: `tests/test_database_first_world_publication.py` for first-World
  HTTP, hosted authorization, lifecycle and SQL witnesses, and
  `tests/test_reviewed_native_graph_activation.py` for native APP activation.
  Preserve their classic historical tests. Do not allocate the shared
  `tests/test_hosted_native_graph_access.py` or `ci/test-classification.json`;
  run affected shared regressions read-only. This handoff's consuming activation
  record belongs on a separately pinned, explicitly allocated path. B1 compiler
  files/tests outside the narrowly transferred correction above may be read,
  not broadened without explicit transfer. No dependency pin, Core/WK runtime,
  migration, generic schema, model policy, provider, or
  unrelated UI/route changes.

This is a proposed exclusive expected-path allowlist, not an instruction to
edit every listed file. Before activation, compare exact current open PR heads,
active leases and actual shared sections; record branch/base, checkout, owned
ports/databases/output paths, tests and any path-specific split. The user granted MIND lane and handoff authority; this architecture disposition
designs the exact first-World section splits. It does not transfer or modify
the other lanes. At the design anchor #1855 head `08b4c817` edits a
reviewed-location binding class in `models/extract_promote.py`; #3824 head
`76c31187` edits hosted-auth/shared router, other hosted access sections and
`integrations/dungeonmind/native_world_source_admission.py`; its inspected
hosted-access diff has no first-World resolver hunk. #3824 and #3808 share
`tests/test_hosted_native_graph_access.py`, which B2 does not allocate. #3824
also edits both UI parent components, #1235 edits the Workbench component and
#2405 edits its shared test; the explicit split above is only the first-World
recovery affordance/selection sections and existing first-World tests. It does
not transfer those lanes' other sections or the shared Workbench test. #2090 head
`19355258` edits ingest-selection handling in the same router. #4057, #2087
and #1235 touch shared frontend API/types, and #1235 has an explicit partial
lease withdrawal recorded in its own PR. B2 avoids those shared model, client
and admission-integration files. The router, hosted resolver and UI parent
splits cover only the first-World sections described above. Recheck #4050, #3531, #1163, #1148 and any new work.
If exact section isolation or safe composition is not possible, stop that edit
and obtain an explicit transfer/split or owning-boundary prerequisite; do not
infer that historical ACTIVE leases expired or rely on Git conflicts as consent.

## B1 producer-mapping correction — re-anchored 2026-11-19

Actual producer `_materialize_evidence_ref` preserves a supplied nonblank
`source_ref_id` plus artifact pair. `candidate_graph_to_contribution` derives
the authoritative evidence ID from the verified artifact and frozen span and
retains `source_ref_id` as optional correlation; the frozen index separately
has its document source reference. B1 currently requires those two source-ref
values to be equal in `_span_requirements`, even though a valid candidate can
carry its own correlation alias. The B2 isolated PostgreSQL diagnostic at
`prepare-diagnostic-2.log` failed both absent/admitted-source cases with
`reviewed_span_identity_mismatch` before lifecycle publication writes; its
disposable databases were dropped. This is diagnostic evidence, not a publication or live-data witness.

Transfer only the two paths and sections named above into the same serial B2
PR. Prove a valid per-candidate nonblank correlation alias is accepted and
retained/committed, and changing it changes the sealed intent/request identity.
Negative controls must still refuse a wrong actual artifact, revision, body,
index, span, locator or native proof. Re-run the existing B1 regressions and
both actual SQL prepare cases; do not weaken any other validation or turn a
correlation alias into source authority.

## Existing exact source proofs and native evidence role

Core's source-extension publication rejects an interval already registered for
the same source. A one-paragraph source without a terminal newline can have a
required frozen span identical to the whole-document interval already admitted
as `context`. The existing native recap admission also uses `context`; Core's
public evidence contracts permit `context` and `support`. B1 currently requires
native parent evidence role `support` unconditionally.

For these source-derived/inferred reviewed facts, B2 must reuse an **actual**
existing native proof at the sealed parent when the artifact, revision,
full-body digest, exact byte interval and slice digest match; retain its actual
`context` or `support` role and identity. Never relabel `context` as `support`,
accept `contradiction`, create a duplicate-interval extension, or use a
correlation alias as source authority. Resolve multiple possible exact proofs
deterministically and seal the chosen identity, or refuse ambiguity; do not
silently choose a different proof on confirm. Extend only missing intervals.
Prepare may seal existing proofs when an authorized admitted parent exists; if
source admission is absent, prepare seals that fact without invented proofs and
confirm obtains the actual whole-document proof from the durable admission
receipt before binding. Retain all current owner authorization, source access,
origin and integrity checks.

Extend only the B1 binder's native evidence-role check to allow actual
`support` **or** `context` for this bounded purpose, while continuing to refuse
`contradiction`. Do not loosen the reviewed raw evidence's separate support
semantics or any artifact/revision/body/index/span/locator/proof validation.
The focused B1 test path must prove exact existing context proof reuse through
the public Core publisher with role retained, support preservation, and
contradiction refusal. Add owning B2 SQL coverage for a one-paragraph source
without a final newline: both already-admitted and absent-admission paths must
reuse the real exact proof rather than attempt duplicate extension. Also prove
mismatched artifact, revision, full-body digest, interval or slice digest fails
closed and a genuinely missing interval is extended once. These tests do not
claim current source access after withdrawal or grant new Core authority.

## Sealed prepare, confirm and recovery contract

1. **Prepare is read-only**, including when no source has been admitted: no
   genesis, source admission, profile transition, Graph publication, APP
   reservation activation or provider call. Resolve and authorize the exact
   persisted run/document, original source bytes and current binding; compile
   the complete reviewed B1 intent and preserve supported `create_new`, `accept`
   and `reject` decisions. The current UI/request does not offer defer and B1
   explicitly refuses deferred identity; reject unsupported defer clearly. Do
   not silently broaden B1 or drop an unsupported decision.
2. Seal a versioned, integrity-protected plan containing the exact principal-
   authorized managed/native World and reservation identity/version, persisted
   raw-to-native source association and full-body digest, frozen span/evidence
   commitments, intent/decision/policy digests, domain/profile pins, stable
   operation identities and timestamps, and expected parent/admission state.
   Record source-not-yet-admitted as such; do not fabricate a parent or span
   proof. Freeze the intended admission and any required profile transition
   preconditions so confirm cannot silently choose different authority or policy.
3. The hosted middleware invokes `resolve_hosted_first_world` before the route.
   Native prepare must resolve the exact server-owned current run and authorize
   its World as today. For native confirm, the resolver must verify the actual
   server-signed versioned plan, then enforce `_owned_world(subject, sealedWorld)`
   before receipt lookup/disclosure, without reloading the mutable run on the
   recovery path. Reject malformed/unsigned/tampered plans, query selectors,
   foreign subjects/Worlds and revoked access. A claimed World alone is never
   authorization. Retain current local GM enforcement and do not weaken hosted
   principal, body or selector checks. Legacy submitted recovery must not treat
   an unsigned World claim as sufficient publication or receipt authority: its
   service must require the exact current reservation and verified historical
   receipt. No generic authorization bypass is introduced.
4. Confirm first authenticates and authorizes the current requester and verifies
   plan integrity/scope. **Before re-reading mutable candidate/source state**,
   query the exact durable native publication receipt by its sealed identity.
   If it exists, verify its request/payload, source association, World,
   reservation, profile, parent and ancestry against the sealed plan, then
   recover the same result and perform only the separately verified idempotent
   APP activation. For recovery read retained source-admission and evidence-
   extension receipts plus immutable source metadata, origin associations and
   proofs; do not replay the extension or call the source owner's
   `_verify_receipt_and_source`, because those paths check current availability.
   Keep ordinary source-access authorization and withdrawal denial intact. Do
   not leak receipt existence across authorization scopes.
5. For a genuinely not-yet-applied plan, revalidate the exact source revision,
   live authorization, reservation, pins and expected state. Admit the source
   through the existing owner only at confirmation, obtain and verify the actual
   source-only parent and evidence, reuse any actual exact matching proofs and
   extend only missing intervals, execute an explicitly sealed profile
   transition only when required, then bind the B1 intent and invoke Core's
   public prospective-alias publication. Verify the returned real receipt,
   native readback and ancestry before activating APP. Source admission, native
   Graph publication and APP reservation are distinct durable outcomes: expose
   recoverable partial/unknown states truthfully and replay only the exact sealed
   operation. Core's prospective-alias publication has parent CAS but no atomic
   source-epoch precondition: a withdrawal racing after extension can leave the
   Graph committed while source evidence is unavailable. Report and recover the
   actual durable outcome truthfully, and preserve normal source-access denial;
   do not promise zero commit, fabricate availability, or require a new Core
   prerequisite for this slice. No automatic reprepare, head refresh, source
   substitution, ID prediction or changed timestamps on retry.
6. Reject obsolete/unsubmitted plans explicitly while preserving recovery for
   potentially submitted operations. The UI must preserve the exact versioned
   request across interruption and distinguish not-invoked, unknown, committed,
   recovered and activation-pending outcomes. Recovery discovery must not be
   keyed solely by today's source revision or validated against today's mutable
   candidate list: provide a bounded saved-entry lookup scoped to the selected
   managed World and run, followed by signed-plan/server authorization. It must
   remain reachable when the current review package is missing, errors or has a
   different source revision, without exposing other Worlds or bypassing
   `sourceReviewOnly`. Do not make a stale plan current
   by silently rebuilding it; protect existing historical recovery records.

## Required verification and completion limits

Use isolated exact-SHA source and uniquely owned disposable APP/native
PostgreSQL targets; never operator/live databases or provider calls. Prove at
least: no-write prepare with existing and absent admission; exact reviewed
choices and all fields/evidence/aliases retained; raw/native full-body mismatch,
wrong source, scope, principal, reservation, profile, parent and stale plan
fail closed; hosted middleware accepts only a valid signed native plan and current
World owner before receipt disclosure, rejects forged/unsigned World claims and
query selectors, and recovers after the mutable run disappears or changes;
legacy recovery requires its verified historical receipt and exact reservation;
mounted recovery remains reachable with missing/error/changed current review,
rejects a wrong World/run and honors `sourceReviewOnly`; a withdrawal between
extension and publication reports the actual durable commit or unknown outcome
and keeps ordinary evidence reads denied; receipt recovery uses retained
immutable proofs without extension replay/current-availability checks;
needed and unnecessary profile transitions; source/Graph/APP
partial failures, lost responses, exact receipt-first recovery after mutable
candidate/source changes, idempotent retries, ancestry and reservation
races; no classic initialization/dual write; unchanged classic historical
recovery. Exercise actual HTTP and UI request/recovery boundaries, including
hosted and local authorization and cross-World denial, not only a compiler or
mock. Run the existing first-World, binding, typed-evidence, source admission,
auth and UI regressions plus the repository-required exact-head verification;
retain commands, commit SHAs, versions, database ownership/cleanup and all
failures. Independently review the complete base→head diff and proof.

A B2 failure is repaired in its owning Buddy or Core repository and re-reviewed;
do not fold runtime changes into a control-plane artifact. A successful B2
proves only its scoped lifecycle. Optimized deployment and ordinary real
acceptance, V10 retirement, and V11 completion remain required later outcomes;
serving :5202 remains untouched by this design.
