# Inline prose targeting without an incidental caret

Status: ACTIVE, baseline-only disjoint sub-slice. Root explicitly assigned design
and implementation on November 17, then authorized this baseline-only split.
Base: eecaf7991bebd58c6ae625cad194cb962ebfa132.
Branch: codex/inline-prose-targeting-20261117.
Checkout: /home/drakosfire/Projects/inline-prose-targeting-20261117.
Topology: serial. No unmerged behavioral dependency. No merge/deploy authority.

## Invariant and critique
Named section plus referenced passage must choose an exact existing prose target
without selection; contextual additions choose a meaningful existing boundary.
An incidental top-of-page caret is not permission to insert there. Genuine
ambiguity clarifies without mutation; unnecessary clarification is a valid miss,
not an unsafe edit. Preserve explicit-selection fallback, citations, facts,
unrelated nodes and playable Plan structure. Retain current reviewed suggestion,
explicit Save and cold-reopen owners. No model offsets or new saving authority.

First measure existing behavior, including already-working Plan heading-boundary
placement. Keep deterministic host tests, routing quality and ordinary provider
results distinct. Synthetic inputs only; no provider call is authorized here.
Dev and held-out cases are separate. Table captions, nested structure, duplicate
passages, stale captures and read-only/discussion are adversarial cases.

## Exclusive expected writes
- This handoff.
- evals/inline_prose_targeting/**: synthetic fixtures, runnable baseline and scoring.
No runtime/controller/bridge/type/policy path is leased yet. After baseline,
a bounded unleased immutable catalog may be adopted explicitly; no implied lease.

## Ownership and external state
Fresh open PR inventory inspected November17. #3824 owns PlanSurfacePage,
WorldPlanAgentConversation and hosted shared owners; #3307 owns Plan driver,
harness and writer; #2401 is a separate proof-only heading probe. The active
image lane owns BuildComposeBridge and BuildComposeProposal, despite its ordinary
routing still being blocked. Do not edit those files or steer that task.
No5202/API8001 or other runtime, real World, database or browser state changes.
Outputs use uniquely owned external Projects storage and global verifier lock.

## Verification and stop
Baseline runs real editor/bridge/catalog APIs, reporting capability misses rather
than deliberately failing tests as product regressions. No baseline test is a
provider or end-to-end Save/reopen claim. Preserve raw output and source pin.
Runtime integration and ordinary synthetic provider exercise remain explicit gates.
Affected checks, exact-source repo verifier and independent review precede any
completion claim; push/draft PR is authorized, not merge/deploy.

## Baseline and bounded catalog adoption
Four real-editor baseline checks pass at179521171: Build lacks named prose offers;
Plan heading boundary+Undo already works; intra-paragraph sentence boundary is not
offered; stale/read-only guards refuse. Ordinary routing and Save remain unscored.
75 open PR file inventories checked: no overlap for this handoff, eval directory or
`apps/live-control-ui/src/documentEditing/proseTargetCatalog.ts`. This one new
runtime helper is now added to the exclusive lease, plus tests in the eval dir.
It offers immutable root prose-paragraph occurrences and adjacent legal root
boundaries with heading context, no incidental caret. It never selects, applies,
saves or routes model output. Replacement of partial sentences remains unsupported.
Resolution requires the exact live editable snapshot/scope and an issued catalog.
No arbitrary returned offsets or first-match substring resolution. Model selection
and integration with reviewed proposals remain blocked on bounded owner splits.

## Prose-only bridge split, November 17
Coordinating root explicitly transferred prose-only additions in
`buildSurface/buildComposeBridge.ts` and `.test.ts`, and
`planSurface/components/BuildComposeProposal.tsx` and `.test.ts`. Image capture,
apply and result portions remain exclusively image-owned; its task is paused and
its heads must remain untouched. No shared controller or other lane is transferred.
Fresh main remains eecaf799. External inventories show no overlap on these four
paths; #3864 owns build_jev_harness.py and #3824 owns the shared proposal-review
backend test. Neither is leased here.

Immediate sub-slice: bridge-issued read-only catalogs and explicit host nomination
provenance, retaining the actual author caret/selection basis unchanged. This does
not alter request/response schemas, durable reservations, review receipts, routing,
application or Save. Nonempty author selection stays with the existing path.
Hook writes are permitted only for this provenance scope; no need to change it
until a safe wire consumer exists. Existing author-selected selection metadata
must never impersonate an agent-nominated passage.

Current server reservation/output/review models are strict closed grammars.
Safe ordinary integration needs an explicitly reviewed additive catalog-target
contract with historical serialization and old-reader behavior, current snapshot
and replay checks, single-paragraph output admission, composer-compatible reviewed
application, and Save/cold-reopen proof. These remain gates, not assumed permissions.

## Minimal additive provenance contract and reader-first gate
Pinned design only; no new-format producer is authorized by this amendment.
Main remains eecaf799.87 current open PR file inventories have no overlap for
`src/application_state/build_proposal/service.py`; historical handoffs naming it
are settled. Add that one service file to the exclusive reader-refusal lease;
its new synthetic tests stay in the already-owned eval directory, not the
#3824-owned review test or test-classification registry. #3864's harness is not
needed to implement this refusal and remains untouched.

Proposed next wire/persistence contract, requiring owning review before emission:
- Legacy `dmb_build_document_proposal_v1`, its actual basis, optional field omission,
  fingerprints, selection meanings and review v2/v3 serialization remain exact.
- Proposed Markdown record v2 retains the current lifecycle/claim owner and adds
  `prose_target` to the frozen reservation. This is distinct from `basis.selection`.
  The basis still records the actual author caret/selection, managed World/document,
  registry revision/content hash, editor/draft hashes, and draft/selection generations.
- `prose_target` has a versioned schema tag, a frozen catalog digest, an opaque
  turn-local selected alias, operation (replace_paragraph/insert_before/insert_after),
  host-resolved from/to and exact before-text digest. The selected member must match
  an offered host catalog bound to that same basis. Model output nominates an alias
  or unavailable only; it never supplies offsets, hashes, identities or provenance.
- Request admission uses existing authenticated World access and current document
  authority; possession of a self-reported digest is not authentication. Match the
  conversation pointer and durable turn claim, and recheck live editor instance,
  scope, revision, draft generation and full document before staging or applying.
  Discussion/read-only/foreign/stale/ambiguous/unknown target grants no mutation.
- Persist the chosen target and catalog binding in the existing immutable proposal
  reservation/fingerprint. Proposed review successor retains that same binding in
  its apply receipt plus existing before/after hashes and apply id. Reopen validates
  receipt-to-reservation equality; historical records gain no nomination authority.
  A duplicate request is existing idempotency behavior, not a new target selection.
  Replayed apply cannot acquire another live capture. No provider replay on uncertainty.
- Keep editable suggestion, single-paragraph replacement admission, explicit native
  Save/CAS and existing journal/recovery owner. Nomination, generation, review read
  and receipt decoding do not apply or Save. Actual Save and cold reopen must be
  proven separately; unsupported citation/paragraph structures remain unavailable.

Reader-first implementation now: the real Markdown service explicitly refuses
unknown versions in the Markdown record family before get/list/retry/advance can
present them as absent or mutate them. Intentional image-record filtering stays
unchanged. No new-version schema is accepted or written, no database is opened by
the synthetic tests, and no APP migration slot is claimed.

Rollout/rollback: current old code silently omits future Markdown versions from
lists. This guard cannot fix already-running old processes. Do not emit v2 until
all service/browser/history/review readers have an approved forward-reader fence
and retired old writers are accounted for. Once v2 exists, rollback may use only
a qualified fenced reader or must stop writes and retain the records unchanged;
never downgrade to v1, strip the binding, treat unsupported history as empty, or
reissue the provider request. Existing rows require no rewrite. The proposed exact
new fields and review version still require owner review; this guard does not
activate them or claim that schema compatibility is complete.

### Proposed field placement (not accepted by this reader prerequisite)
The next contract review must accept or revise these concrete additive shapes:
1. Future write capability adds `prose_catalog` with
   `schema: dmb_build_prose_catalog_v1`, `catalog_sha256`, and `entries` containing
   `alias`, `operation`, `from`, `to`, `before_text_sha256`, `section`, `passage`.
   Its existing actual `basis.editor_sha256` binds the entire catalog snapshot.
   Digest uses the existing canonical owner convention, not a second identity store.
   Only alias/operation/section/passage project to model context.
2. Existing `propose_build_insertion` tool gains optional `target_alias` for this
   capability. The parent resolves that alias against the authenticated frozen
   catalog before reserving work; no new requested-work/action enum is proposed.
   Missing/unknown/ambiguous alias must not fall back to actual caret. Ordinary
   clarification/discussion remains non-mutating.
3. Only after that admission, proposed record v2 freezes `reservation.prose_target`:
   `schema: dmb_build_prose_target_v1`, `catalog_sha256`, `alias`, `operation`, `from`,
   `to`, `before_text_sha256`. Reservation fingerprint includes it. Generated
   proposal uses `target: prose_target`; it cannot change the admitted binding.
   Actual author `basis.selection` stays absent for this no-selection path.
4. Proposed review v4 carries `prose_target` at review and apply receipt levels,
   equal to its immutable reservation binding. Existing source/editor/draft and
   reviewed-output hashes, CAS revision, apply id and disposition checks remain.
   Current v1 proposal/v2-v3 review readers do not accept these additions.

These names are a pinned design proposal, not permission to allocate a migration,
write a new record, call providers or relax existing strict parsing. Authenticated
route validation, mixed-version rollout, hosted history and review consumers need
an explicit owner review before activation. The current tests verify rejection by
the actual legacy owner, not merely an invented compatibility model.
