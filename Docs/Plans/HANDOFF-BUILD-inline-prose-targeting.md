# Inline prose targeting without an incidental caret

Status: ACTIVE, isolated opt-in native replacement proof. The baseline/catalog
sections below record predecessors; the latest scoped amendments govern execution. Root explicitly assigned design
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

## Isolated vertical proof activation, November 17
Root relayed Alan's explicit “Continue building it” and authorized a runnable
isolated opt-in native review/apply/Save/reopen proof. Main is still eecaf799.
Current open PR inventories show no overlap for the owners below; shared harness,
controller, #3824 test and APP migrations remain excluded. The image lane's exact
capture/apply/result code and heads stay reserved/unchanged.

Added exclusive paths: `src/application_state/build_proposal/{types,review,service}.py`;
`apps/live-control-ui/src/api/{buildDocumentProposalApi,buildProposalReviewApi}.ts`;
`buildSurface/BuildPageProposal.tsx` and the already-transferred bridge/tests;
`documentEditing/markdownInsertion.ts` for schema-faithful simulation only. Tests,
fixture scripts and disposable adapters remain in evals/inline_prose_targeting/**.
No edits to shared harness/controller, public routing or any migration slot.

Only the first replacement operation is activated in a disposable test owner:
one host-catalog-nominated root prose paragraph, with actual author selection empty
and caret elsewhere. The production service constructors retain default denial;
explicit in-process proof opt-in is required for v2 record and v4 review reads and
writes. No environment flag or route exposes that opt-in. Default readers keep
refusing unsupported prose records. New-format bytes exist only in uniquely owned
disposable fixture databases, never operator Worlds or browser profiles.

A scripted choice nominates the alias, not an ordinary provider. Prove selected
paragraph occurrence despite duplicate text in another section, snapshot/admission,
exact unrelated-node preservation, native Undo, explicit Save and fresh reopen.
Keep persisted owner tests, mounted adapter tests, cross-boundary roundtrip and
model-routing evidence separate. No model/provider evidence is implied.

Proof database may use the already-installed pgvector Postgres image on a newly
checked loopback port with uniquely owned Projects-backed data. Do not start,
stop or reuse54329/5202/8001 or any existing runtime. Retain commands and cleanup.
Any missing lease or unsupported owning contract is reported rather than bypassed.

### Explicit disposable schema adaptation approval
Actual migrated fixture checks reject proposal v2 and review v4. Root explicitly
authorized extending only record-format CHECKs on our uniquely owned empty test
clone on55467, after verifying server/database identity. Retain every complete
legacy predicate as the first OR arm and add narrow prose-format arms; exercise
legacy and new rows and retain exact original/installed definitions externally.
Never alter the session template, production migrations/version, original database,
default activation or any running product service. This is a labeled test-only
schema difference, not proof of production migration/rollout compatibility.
Default/no-opt-in and old-reader refusal evidence remains separately required.

### Additive offline nomination scoring (2026-11-17)

After isolated native proof at `50609174ff6199344dc31ac1f63fd54c592e85a6`,
the coordinating owner authorized an eval-only continuation within this same
lease/PR. Add only files under `evals/inline_prose_targeting` and this handoff.
Export actual Build/Plan host catalogs and natural requests separately from
private expected answers; score supplied replay decisions offline. Preserve
held-out inputs/answers, missing-coverage accounting, clarification recall and
overuse, intentional non-edit, and wrong-target nomination as the hardest failure.
Deterministic snapshot admission is separate from language understanding. No
provider, runtime writes, shared harness/controller, migration or activation.
Scripted replay verifies scorer correctness, not ordinary routing quality.

### Serial isolated paragraph-boundary insertion (2026-11-17)

The coordinating owner authorized this continuation from published
`7c08bc2bcdd14c61396ab85bc68119cc26ba1482`. It reuses the existing immutable
before/after paragraph catalog, not an additional catalog or ordinary router.
Write scope: the existing Build proposal/review API codecs, Build compose bridge,
BuildPageProposal, native build_proposal types/service/review, this handoff and
`evals/inline_prose_targeting` only. No shared conversation/controller/harness,
image operation, Plan runtime or migration paths. Fresh main/open-PR file checks
found no external overlap in this bounded write set; #3864 and #3824 remain
separate owners.

Explicit insertion provenance uses `dmb_build_prose_boundary_target_v1`, operation
`insert_before` or `insert_after`, equal nonnegative `from`/`to` at a host-admitted
root boundary, catalog digest/alias and the anchor paragraph's text digest. The
snapshot identity is still the actual editor/document basis. New proof-only
proposal v3/review v5 codecs distinguish it from replacement v2/v4; default legacy
codecs remain closed. The actual authored caret and selection are never rewritten;
Move stays unavailable for host-targeted proof. One new plain paragraph may be
added, with every existing node/ID/mark/row unchanged byte-for-byte. Native Undo,
explicit existing Save and fresh editor reopen remain required witnesses.

Test-only DDL is authorized only on fresh uniquely owned synthetic clones on the
same isolated PostgreSQL55467, preserving all original legacy CHECK clauses. No
production schema, reader drain, runtime activation, provider or private data.
Use duplicate passages across headings and unrelated caret; prove exact before/
after placement, semantic order, stale/readonly/foreign/ambiguous refusal and
missing-ID normalization refusal. Scripted target choice is not model quality.

Boundary witness coverage is deliberately limited to pre-existing composed Pages.
`projectPresentation` returns null for plain Pages; preserving their exact IDs
through native Save/reopen needs the Page presentation owner contract, outside
this lease. Boundary admission refuses plain pages and any project/hydrate JSON
normalization before mutation. It never adds a wrapper to force persistence.
New IDs respect the existing80-character bound. This is an isolated coverage gap,
not completion of ordinary contextual placement.

### Frozen Build placement benchmark correction (2026-11-17)

ACTIVE serial continuation from `758690683e1f86804f65b0fc890d0a4be7899474`,
explicitly assigned by coordinating root. Fetched main remains eecaf799; all157
open PR file lists plus expanded #3824 have no overlap with this eval-only scope.
Write lease: this handoff and evals/inline_prose_targeting/** only. Replace the
shared Build routing page with separately authored frozen dev/holdout pages and
add semantic insertion requests using actual before/after paragraph aliases.
Private acceptable sets must resolve to the same physical boundary; plausible
opening and wrong-section nominations must fail. No model runs, runtime, Save,
plain-page coverage repair, shared harness, migration, merge or deployment.
Validate artifacts and scorer together, independent review, exact hosted verifier;
retain prior full-discovered diagnostic as the meaningful integrated checkpoint,
not as a green result for this new head. Publish only to the existing draft #3867.

### Plan mounted contextual-boundary witness (2026-11-18)

ACTIVE serial eval-only continuation from63d972db, authorized by coordinating root
on the user's request to resume cross-surface agent layout. Fresh main eecaf799,
173 open PRs plus expanded #3824 inspected. PlanSurfacePage runtime is #3824-owned;
Plan producer/review backend overlaps #3919; Plan bridge and mounted fixture source
also overlap #1014/#1188. No lease is transferred. Write only this handoff and
new evals/inline_prose_targeting adapter/tests/docs. Reuse the existing mounted
Plan fixture in an explicit generated test with guarded source anchors, rather
than copying or editing its owning source. Record source SHA/checksum and generated
fixture bytes. Run contextual existing section boundary with top caret, duplicate
passage, untouched neighbors, Undo, explicit native frontend Save owner and cold
remount; include malformed boundary refusal. Transport/model and server persistence
stay scripted. This is no production route change, ordinary model accuracy claim,
native PostgreSQL proof, or authority to enable new writers. No provider/live data,
merge/deploy or leased source writes. Exact-head review/hosted check remain gates.

### Typed-reference Plan persistence witness (2026-11-18)

ACTIVE eval-only continuation from5ce661c26, explicitly assigned by root after
confirming ordinary requested-work reservation/clarification already has real
owner coverage. No authorized ordinary provider transport is available; private
Sheep fixtures are out of scope. One distinct increment: same-label/different-ID
graphNodeReference atoms through our contextual mounted Plan Save/remount fixture.
Write only this handoff and owned eval adapter/tests/docs.154 open PR file lists
plus expanded #3824 have no external overlap in these paths. Runtime/owner leases
remain untouched. Allow selecting a separately pinned current-main source checkout
for the adapter; record both harness and owner-source commits. Assert exact typed
node identities, not labels/URLs/evidence citations; a wrong but valid ID is an
oracle failure, not runtime rejection. No Graph lookup/opener claim, Graph writes,
provider use, real World, merge or deploy. Scripted server transport remains explicit.

Observed current-owner limit: ordinary boundary proposal validation rejects new
graph identities. Keep that raw failed-positive evidence. This increment therefore
proves retention of pre-existing same-label/distinct-ID atoms across contextual
plain-prose Save/remount and explicit new-identity refusal, not new reference
authoring. Do not weaken the runtime guard or confuse a bare label with a typed ID.
