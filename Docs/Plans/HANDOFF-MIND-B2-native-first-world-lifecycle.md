# MIND B2 — native first-World lifecycle

**Status:** DESIGNED / BLOCKED; no implementation write lease until B1 merges
and the consuming owner completes the activation checks below.
**Design anchor:** Buddy `main@98d3157a09790e5a53a851b9ea24a5de51bd2aa5`;
Core #231 merge `cf197b9939f7b9106c75a8afb9fcf918c8b4aa1c`, adopted by Buddy
#4093 merge `5289f99c27263c1176682588433921592ea818a2`.
**Prerequisite:** Buddy #4097 B1 compiler must merge; its final unmerged head
`3dbefaec9b9ea56fa03071c83d9c4202b8d1a904` is a reference, not an accepted
revision. Pin the actual merge and current main after it lands.
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
  versioned router/model where needed; do not edit shared import blocks, common
  auth helpers, middleware, recap, generic Worldbuilding, source observation or
  location-binding routes. Preserve `_reject_selector_query`, the existing
  first-World authorizer, error safety and hosted/local principal semantics.
  A necessary edit outside this exact section requires an explicit new split or
  transfer before editing, not a blanket claim on this shared file.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewFirstWorldPublishSheet.tsx`,
  `firstWorldPublicationRecovery.ts` and their owning tests, plus new dedicated
  first-World API/type modules and tests under the same workbench or `src/api/`.
  Wire the actual ordinary first-World UI to the native protocol and preserve
  retained exact-request recovery. Do not modify shared `src/api/types.ts` or
  `src/api/extractPromoteApi.ts`.
- Owning tests: `tests/test_database_first_world_publication.py`,
  `tests/test_world_graph_binding.py`, relevant first-World HTTP/auth tests,
  and new narrowly named native lifecycle/SQL tests; this handoff's consuming
  activation record only on a separately pinned, explicitly allocated path.
  B1 compiler files/tests may be read, not broadened without an explicit
  transfer. No dependency pin, Core/WK runtime, migration, generic schema,
  model policy, provider, or unrelated UI/route changes.

This is a proposed exclusive expected-path allowlist, not an instruction to
edit every listed file. Before activation, compare exact current open PR heads,
active leases and actual shared sections; record branch/base, checkout, owned
ports/databases/output paths, tests and any path-specific split. The user
explicitly requested this first-World section split; it does not transfer or
modify the other lanes. At the design anchor #1855 head `08b4c817` edits a
reviewed-location binding class in `models/extract_promote.py`; #3824 head
`76c31187` edits hosted-auth/shared router and
`integrations/dungeonmind/native_world_source_admission.py`; #2090 head
`19355258` edits ingest-selection handling in the same router. #4057, #2087
and #1235 touch shared frontend API/types, and #1235 has an explicit partial
lease withdrawal recorded in its own PR. B2 avoids those shared model, client
and admission-integration files, and the router split is only the first-World
handlers described above. Recheck #4050, #3531, #1163, #1148 and any new work.
If exact section isolation or safe composition is not possible, stop that edit
and obtain an explicit transfer/split or owning-boundary prerequisite; do not
infer that historical ACTIVE leases expired or rely on Git conflicts as consent.

## Sealed prepare, confirm and recovery contract

1. **Prepare is read-only**, including when no source has been admitted: no
   genesis, source admission, profile transition, Graph publication, APP
   reservation activation or provider call. Resolve and authorize the exact
   persisted run/document, original source bytes and current binding; compile
   the complete reviewed B1 intent and preserve accept/reject/defer decisions.
2. Seal a versioned, integrity-protected plan containing the exact principal-
   authorized managed/native World and reservation identity/version, persisted
   raw-to-native source association and full-body digest, frozen span/evidence
   commitments, intent/decision/policy digests, domain/profile pins, stable
   operation identities and timestamps, and expected parent/admission state.
   Record source-not-yet-admitted as such; do not fabricate a parent or span
   proof. Freeze the intended admission and any required profile transition
   preconditions so confirm cannot silently choose different authority or policy.
3. Confirm first authenticates and authorizes the current requester and verifies
   plan integrity/scope. **Before re-reading mutable candidate/source state**,
   query the exact durable native publication receipt by its sealed identity.
   If it exists, verify its request/payload, source association, World,
   reservation, profile, parent and ancestry against the sealed plan, then
   recover the same result and perform only the separately verified idempotent
   APP activation. Do not leak receipt existence across authorization scopes.
4. For a genuinely not-yet-applied plan, revalidate the exact source revision,
   live authorization, reservation, pins and expected state. Admit the source
   through the existing owner only at confirmation, obtain and verify the actual
   source-only parent and evidence, execute an explicitly sealed profile
   transition only when required, then bind the B1 intent and invoke Core's
   public prospective-alias publication. Verify the returned real receipt,
   native readback and ancestry before activating APP. Source admission, native
   Graph publication and APP reservation are distinct durable outcomes: expose
   recoverable partial/unknown states truthfully and replay only the exact sealed
   operation. No automatic reprepare, head refresh, source substitution, ID
   prediction or changed timestamps on retry.
5. Reject obsolete/unsubmitted plans explicitly while preserving recovery for
   potentially submitted operations. The UI must preserve the exact versioned
   request across interruption and distinguish not-invoked, unknown, committed,
   recovered and activation-pending outcomes. Do not make a stale plan current
   by silently rebuilding it; protect existing historical recovery records.

## Required verification and completion limits

Use isolated exact-SHA source and uniquely owned disposable APP/native
PostgreSQL targets; never operator/live databases or provider calls. Prove at
least: no-write prepare with existing and absent admission; exact reviewed
choices and all fields/evidence/aliases retained; raw/native full-body mismatch,
wrong source, scope, principal, reservation, profile, parent and stale plan
fail closed; needed and unnecessary profile transitions; source/Graph/APP
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
