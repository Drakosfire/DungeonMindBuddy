# HANDOFF — SBW07 Persist accepted mechanics as an immutable revision

**Created:** 2026-07-22  
**Updated:** 2026-07-24 — re-anchored after `SBW05c`; review fixes for reconcile crash protocol, history bound, and commit-point wording  
**Status:** IN REVIEW — `SBW07-contract` (docs-only approve/reject of §12). After approval: `SBW07a` → `SBW07b` → `SBW07c`. **Before SBW06**.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw07-persist-accepted-mechanics.md`  
**Workstream:** `SBW07`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**PR base / repository tip (not an SBW claim):** `bf28e46c` on `main` at PR open (includes unrelated BLD work)  
**Logical SBW predecessor:** `#404` / `427a357b` — SBW05c workbench host + preview validate (no accept/save)  
**This PR:** `SBW07-contract` — docs-only; normative surface is §12  
**Next code bite after this PR merges:** `SBW07a` (create/read Server client + fixtures)

> Dispatch one capability across a contract PR plus three code PRs: persist validated mechanics as one logical statblock with one exact immutable first revision and record that locator on the ThreatDraft. Do not publish a Threat, update a graph binding, append a later revision, embed Markdown, or add combat/media behavior.

## Bite schedule

| Bite | Status | PR mission | Allowlist focus | Still false |
|---|---|---|---|---|
| `SBW07-contract` | **this PR** | Doc-only acceptance authority + partial-state transition table + ThreatDraft schema delta (§12 approve/reject) | Docs only; no implementation | All code |
| `SBW07a` | next after contract | Create/read Server client + fixtures | Integration client + tests | Draft mutation, UI, demolition |
| `SBW07b` | after `SBW07a` | Acceptance orchestration + atomic ref / pending reconcile | Service/store/routes/tests | UI, corpus demolition, graph |
| `SBW07c` | after `SBW07b` | Accept UI + corpus-promotion demolition | Workbench + demolition ledger | Graph, append revision |

**Deferred outside this workstream (`Backlog.md`):** Server HP/AC/Phases consumer sync into Buddy; context-aware workbench ThreatDraft create-and-generate; browser-local editor draft persistence (restore as unvalidated). These may run before `SBW07a` if needed for dogfood, but they are not part of `SBW07-contract`.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Create logical statblock + immutable first revision | Yes | Yes | Yes | Include |
| Store exact accepted mechanics ref on ThreatDraft | No; required to make the save recoverable | Yes | Yes | Include under same invariant |
| Publish Threat + binding to graph | Yes | Yes | Yes | Successor `SBW09` |
| Append later revision | Yes | Yes | Yes | Successor `SBW13` |
| Compare/upgrade uses | Yes | Yes | Yes | Successor `SBW13–14` |
| Corpus promotion | No longer desired architecture | Yes | Yes | Demolish from normal acceptance path |

**Selected capability:** the GM can turn one validation-eligible complete definition into exact durable mechanics and later reload the same immutable revision.

## §1 Mission

A GM can save one validated complete definition as a DungeonMind statblock and immutable first revision so accepted mechanics survive reload with exact identity and digest before any campaign graph publication.

**Invariant**

```text
“Mechanics saved” always means one exact persisted (statblock_id, revision_id, definition_digest) returned by DungeonMindServer and atomically recorded on the source ThreatDraft; it never implies graph publication.
```

**Mission falsification test**

```text
This is not one slice if implementation must also create/update a Threat node, choose a campaign-preferred revision, append a child revision, embed a document, mutate combat, or bind media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §7.1–7.3; tracker `SBW07`; DungeonMindServer create-statblock persistence/idempotency contract |
| Repository rules | `AGENTS.md`; external-agent PR loop rules/template |
| PR base | `bf28e46c` (`main` tip at PR open; may include unrelated work — not an SBW capability claim) |
| Logical SBW predecessor | `#404` / `427a357b` (`SBW05c` complete); **must not** require or include `SBW06` |
| Predecessor contract | Complete typed working definition + preview validation receipt bound to exact digest (SBW05a–c); no accept/save path yet |
| Exact input consumed | Draft/candidate locator, complete definition, current validation receipt/digest, stable idempotency key, acceptance metadata |
| Named successor | `SBW09` governed Threat publication; `SBW13` append child revision. **`SBW06` is a later Milestone B sibling (after this slice), not a base.** |
| What remains false | No World Graph object or binding exists; no “published/canonical threat” claim |
| Explicit non-goals | Graph, append revision, preferred revision, Markdown, combat, image selection, Server schema redesign |

Read in order:

1. integration design §7 and object ownership table
2. tracker `SBW07`
3. merged `SBW05` digest/validation state contract
4. current Server create-statblock route/OpenAPI/client fixtures and idempotency rules
5. merged `SBW02` ThreatDraft atomic update semantics
6. current workbench corpus-promotion path solely for demolition inventory

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Open acceptance confirmation | Corpus promotion/transitional controls | Show exact definition digest, validation state, and “mechanics only” consequence | Yes | workbench UI |
| Save valid definition | No v1 persistence workflow | Call Server create with stable idempotency key | Yes | service/route |
| Validation errors present | No authoritative gate | Block before downstream create | Yes | UI/service |
| Warnings only | Undefined | Permit only when Server validation semantics allow; disclose warnings | Yes | UI/service |
| Duplicate submit | Risk of duplicate resources | Idempotent replay returns same exact resource/revision | Yes | service/Server/store |
| Downstream success + Buddy response loss | Undefined | Recover exact result by idempotency/read; no second resource | Yes | orchestration |
| Downstream success + draft-ref write failure | Undefined | Authority `server_committed` + materialization `draft_ref=failed`; product never claims `mechanics_saved` until reconcile | Yes | orchestration/store |
| Reload saved mechanics | Corpus path lookup | Exact revision read and digest proof | Yes | service/route/UI |
| Graph publication absent | Potentially conflated | UI explicitly says saved, not published | Yes | workflow state |
| Corpus promotion acceptance | Active predecessor | Removed from normal acceptance path | Yes | workbench/backend demolition |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/models/statblock_candidate_workflow.py` | `AcceptedMechanicsRefV1`, save request/result, partial state |
| Create | `apps/live_control_server/services/statblock_mechanics_acceptance.py` | Validation gate, idempotent create orchestration, reconciliation |
| Modify | merged `SBW01` DungeonMind client implementation | Add typed create-statblock and exact-read operations |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Atomic accepted-ref/workflow-state write |
| Modify | `apps/live_control_server/routes/statblock_candidates.py` | Accept/save and reconciliation/read endpoints |
| Create | `tests/test_statblock_mechanics_acceptance.py` | gate/idempotency/partial/reload proof |
| Modify | `tests/test_statblock_candidate_routes.py` | route contract proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | acceptance/ref/result types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | accept/read/reconcile calls |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | mapping proof |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | confirmation, state, retry/reload UX |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | user workflow proof |
| Delete/Modify | exact corpus-promotion acceptance UI/backend paths named by inventory | remove replaced normal acceptance path |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package; current statblock corpus-promotion route/service area
Maximum additional paths: 5
Allowed path kinds: client method, real create/read fixtures, direct predecessor route/service/test deletion
Decision rule: required to consume real Server persistence or delete the exact normal acceptance predecessor
Required report: name every retained predecessor consumer and deletion owner
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| World Graph Threat/resource/binding | `SBW08–09` |
| graph preview/confirm UI | `SBW09` |
| append child revision | `SBW13` |
| revision comparison/upgrade | `SBW13–14` |
| Markdown/Tiptap embed | `SBW11–12` after decomposition |
| combat | `SBW15` |
| images/media | `SBW16–17` |
| deleting valid Server revision after graph failure | prohibited; mechanics resource remains valid |
| local persistence of canonical definition | Server owns mechanics authority |

## §6 Implementation contract

```text
Input:
  draft_id + expected draft version/workflow token
  exact candidate/source locator
  complete StatblockDefinitionV1_Input
  current validation receipt bound to exact definition digest
  stable idempotency key persisted before/with attempt
  acceptance metadata safe for Server contract

Output:
  AcceptedMechanicsRefV1:
    provider=dungeonmind
    statblock_id
    revision_id
    contract/version
    definition_digest
    accepted_from_candidate_id?
    accepted_from_draft_version
    accepted_at
  plus workflow state mechanics_saved only after Phase 1 ThreatDraft attach of this
    operation's locator (journal may still be server_committed pending Phase 2 repair;
    server_committed + draft_ref pending / unattached is never product mechanics_saved)

Invariant:
  exact persisted locator/digest is the only success truth; graph publication remains separate

Failure behavior:
  validation errors/stale receipt -> block before downstream
  integration/auth/timeout -> typed uncertainty or failure category; authority stays
    dispatched_unknown until same-key same-body replay or authoritative non-commit proof
  same key + changed body (local or Server 409) -> reject attempt only; original operation
    authority unchanged; recover via original stored body; no alternate create
  active acceptance slot occupied -> acceptance_busy; no new claim
  server_committed + different existing accepted_mechanics_ref -> accepted_ref_conflict;
    never overwrite or delete either Server revision
  malformed create response/exact-read mismatch -> integrity failure; no accepted ref
  downstream success + local ref write failure -> authority server_committed; expose
    server_committed_reference_pending recovery; do not delete Server resource
  exact-read unavailable after create -> locator from create response may establish
    server_committed; mark verification pending honestly; never claim mechanics_saved

Replay / idempotency:
  same idempotency key + same full create-request digest -> same logical resource/revision
  same key + changed definition/metadata -> attempt conflict; original op unchanged
  UI double-submit -> one operation
  retry after partial failure -> reconcile by same-key same-body / exact locator before create

Trust boundary:
  Verifies: validation receipt/digest association, complete definition, Server response, exact IDs/digest, draft version
  Records without proving: campaign-world identity, graph canon, game balance beyond validation
  Rejects: stale validation, name/path identity, corpus write as acceptance, local-generated revision IDs
```

### Commit model

```text
External commit: DungeonMindServer successfully persists logical statblock and first
  immutable revision (may be invisible to Buddy if the response is lost).
Buddy observation: create/replay/exact-read supplies the exact locator → authority
  may become server_committed.
Before Buddy observation: no durable Buddy mechanics claim; authority stays
  dispatched_unknown (response loss is the defining case).
After Buddy observation: valid immutable Server mechanics exist even if DungeonBuddy
  cannot attach the draft ref or publish graph truth.
Truthful result after post-observation draft-attach failure: Server mechanics exist
  (authority server_committed); product must not claim mechanics_saved until Phase 1
  ThreatDraft attach succeeds. Journal reaches reconciled only via Phase 2 repair.
Recovery: same-key same-body replay / exact read → durable locator → Phase 1 draft
  attach (version CAS) → Phase 2 journal reconcile. Two store writes are ordered and
  restart-recoverable; they are not crash-atomic together.
```

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Downstream unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Acceptance gate | compute current digest/receipt | eligible confirmation | no receipt = blocked | N/A | digest mismatch blocked | stale receipt blocked | revalidate |
| Create | dispatched_unknown | server_committed (Buddy-observed locator) | N/A | stay dispatched_unknown + replay | fail closed | draft/version for attach only | same-key reconcile |
| Draft ref write (Phase 1) | current draft load | draft `mechanics_saved` + matching ref; journal still `server_committed` until Phase 2 | draft missing = server_committed retained | N/A | fail closed | stale draft CAS = retry Phase 1 | exact ref retry |
| Journal reconcile (Phase 2) | draft attach observed | `reconciled` + `draft_ref=attached` | draft attach missing = stay server_committed | N/A | fail closed | N/A | restart repair |
| Reload exact revision | read locator | exact digest match | 404 integrity issue | unavailable but locator retained | mismatch fail closed | N/A | retry read |

No fallback to corpus file, display name, latest revision, or a second create.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Idempotency operation | stable persisted key scoped to draft/source/digest | changed payload conflict | No | dedupe across retries |
| Statblock | exact Server `statblock_id` | none | No | logical mechanics identity |
| Revision | exact Server `revision_id` | none | No latest | immutable mechanics identity |
| Definition | exact deterministic digest confirmed by Server | mismatch integrity failure | No | accepted ref |
| Draft | exact `draft_id` + expected version/token | stale conflict/partial state | No name match | atomic ref write |
| Candidate | exact source ID if present | expired still valid as provenance if definition/validation exact | No | provenance only |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Recovery |
|---|---|---|---|---|---|
| Create statblock | Server-owned resource + immutable revision | exact IDs/digest readable | idempotent same request | Server contract authority | exact read/idempotency lookup |
| Store accepted ref | strict `AcceptedMechanicsRefV1` on ThreatDraft | exact locator/digest | same ref idempotent; different ref conflict/explicit replacement not allowed here | schema versioned | retry atomic write |
| Store attempt/recovery | mandatory `AcceptanceOperationV1` journal | idempotency/source/body/locator retained | same operation reconciles | separate from mechanics authority | resume after restart |
| Reload | exact Server read | digest equality | safe repeat | no latest migration | unavailable state retains ref |

### §6D Predecessor-to-consumer mapping

**Grounding source:** real Server create-statblock request/response, exact revision read, error/idempotency fixtures.

Required mapping:

| Server field/outcome | Buddy field/behavior | Rule | Proof |
|---|---|---|---|
| idempotency key/header | acceptance operation | persisted before call; never browser secret | replay test |
| logical statblock ID | accepted ref | exact copy | fixture/read test |
| first revision ID | accepted ref | exact copy | fixture/read test |
| definition digest | accepted ref/gate | exact equality | mismatch test |
| created/revision metadata | disclosure/audit | bounded copy | fixture |
| validation/conflict envelope | blocked/failure state | stable category | error tests |
| exact-read response | reload proof | IDs/digest must match | integration test |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Stale/error validation cannot create | acceptance service | focused tests with fake call counter | zero downstream calls |
| Double submit creates once | service + fake Server/idempotency | concurrency/replay tests | one resource/revision |
| Post-commit local failure truthful/recoverable | service/store failure injection | focused test | partial state then same ref saved |
| Exact reload/digest proof | service/route | create + exact read test | IDs/digest equal |
| UI wording/state separation | workbench component | tests | “mechanics saved; not published” |
| Corpus acceptance predecessor removed | diff/tests | search and workflow test | no normal promotion path |
| No graph mutation | service/diff | spies/path inspection | zero graph calls |

Required commands:

```bash
uv run pytest tests/test_statblock_mechanics_acceptance.py tests/test_statblock_candidate_routes.py -q
cd apps/live-control-ui && npm test -- --run src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use the existing workbench with a validation-clean candidate. Confirm save, capture exact IDs/digest, reload exact revision, double-submit safely, then inject a local draft-write failure and show mechanics remain saved with a reconciliation action. Do not publish a graph object.

## §8 Required handback

Include real Server mapping/idempotency semantics, operation/partial-state schema, base/head, paths, tests/results/provenance, live IDs/digest proof, demolition ledger, baseline failures/waivers, and confirmation that graph/latest/embed/combat/media remain false.

## §9 Acceptance rubric

- [ ] Validation-clean exact digest is required.
- [ ] One idempotent operation creates one logical statblock and first immutable revision.
- [ ] Exact IDs/digest are atomically recorded or recoverably pending.
- [ ] Exact reload proves the same revision.
- [ ] UI never labels saved mechanics as a published/canonical Threat.
- [ ] Post-commit failure never deletes or hides valid Server mechanics.
- [ ] Corpus promotion is not the normal acceptance path.
- [ ] No graph, append revision, preferred/latest, embed, combat, or media behavior ships.

## §10 Reviewer protocol

Start at the commit point and failure injection. Audit idempotency persistence, exact digest comparison, stale validation, double-submit races, wording, and demolition. Search for graph writers, corpus writers, `latest`, local revision IDs, and rollback deletion.

## §11 Re-review protocol

Re-run validation gates, replay/concurrency, post-commit failure, reconciliation, exact-read mismatch, and UI state tests after every fix.

## Stop conditions

Stop if:

- Server create semantics do not provide stable idempotency;
- accepted ref cannot be written atomically or recovered after restart;
- exact revision read disagrees with create response;
- validation receipt cannot be tied to the submitted digest;
- removing corpus promotion breaks an unnamed active consumer;
- graph publication is required to call mechanics saved;
- a path outside the allowlist is required.

## Final dispatch check

- [x] Re-anchor after predecessor merge (`SBW05c` `#404` / `427a357b`).
- [ ] Capture real create/read/idempotency fixtures (`SBW07a`).
- [ ] Name demolition consumers/deletion owner (`SBW07c`).
- [x] Confirm all graph/projection/runtime successors remain false for this contract PR.
- [ ] `SBW07-contract` transition table approved (this PR) before `SBW07a+` code.

## §12 Acceptance operation-authority model (normative — `SBW07-contract`)

This section is the **approve-or-reject contract** for `SBW07-contract`. Implementation (`SBW07a–c`) may not invent alternate journals, optional pending fields, or demote unknown transport outcomes to failed.

**Success claim:** For every acceptance that may have reached DungeonMindServer create, Buddy retains a durable acceptance-operation record with a recovery path. Product may claim `mechanics_saved` when the ThreatDraft durable write has attached this operation’s locator and set `workflow_state=mechanics_saved`. Journal authority reaches `reconciled` by an ordered, restart-recoverable repair after that draft write. Retry never deletes a valid Server revision. Graph publication remains false.

### Three separated concerns (non-negotiable)

| Concern | Where it lives | Closed values | May fail independently? |
|---|---|---|---|
| **Operation authority** | Acceptance operation journal (sibling durable store; not ThreatDraft fields) | `dispatched_unknown` \| `server_committed` \| `reconciled` \| `terminal_failure` | No — this is the recovery spine |
| **ThreatDraft materialization** | `accepted_mechanics_ref` + materialization flags on the operation | `draft_ref`: `missing` \| `attached` \| `failed` \| `conflicted` | Yes — after Server commit |
| **Product workflow state** | `ThreatDraftV1.workflow_state` | `drafting` \| `candidate_ready` \| `mechanics_saved` | Yes — only advances to `mechanics_saved` on durable draft attach |

`mechanics_saved` is reserved for ThreatDraft state after a successful attach of this operation’s locator. Partial Server-commit outcomes without that draft write must never use that name. Journal `reconciled` acknowledges the attach; it is not a second independent product claim.

### External commit vs Buddy observation (closed)

```text
External commit: DungeonMindServer has persisted the logical statblock + immutable
  first revision. This may already be true even when Buddy has no response.
Buddy observation: a create response, same-key same-body replay, or authoritative
  exact-read recovery has supplied the exact
  (statblock_id, revision_id, definition_digest) locator to Buddy.
  Only then may authority advance to server_committed.

Before Buddy observation: authority remains dispatched_unknown.
  Response loss after a possible external commit is the defining case for
  dispatched_unknown + same-key same-body recovery — not failure.

After Buddy observation (server_committed): Server mechanics exist even if the
  ThreatDraft attach later fails. Product workflow_state must NOT be
  mechanics_saved until the ordered draft-attach protocol succeeds.
```

Not chosen: defining “commit” as “Server persisted **and** returned a locator to Buddy.” Return/observation is separate from external persistence.

### Journal shape decision (closed)

```text
Choice: SEPARATE acceptance-operation journal under the draft state root
  (sibling to the SBW03 generation journal; distinct schema namespace).
Not chosen: optional flag/field on ThreatDraftV1 for pending locator.
Not chosen: embedding the full create request body on ThreatDraftV1.
```

Rationale: the current ThreatDraft model only has placeholder `accepted_mechanics_ref: None` and `drafting | candidate_ready`. Restart-safe idempotency, request digest, and unknown-transport recovery cannot live there without overloading product workflow state. Mirror SBW03: journal owns authority; draft owns the reconciled ref.

### Mandatory durable schema — `AcceptanceOperationV1`

Schema literal: `dmb_statblock_acceptance_operation_v1`

Every acceptance attempt that may call Server create **must** persist this record **before** the outbound create (claim-before-dispatch). Fields are mandatory unless marked nullable-after-commit.

| Field | Required | Meaning |
|---|---|---|
| `schema` | yes | `dmb_statblock_acceptance_operation_v1` |
| `operation_id` | yes | Stable Buddy operation id (UUID / `accop_…`) |
| `idempotency_key` | yes | Exact key sent to Server create; unique per accept attempt intent |
| `create_request_digest` | yes | **Buddy-local** canonical digest over the stored `request_body` (full create payload: definition **and** metadata fields Buddy sends). Binds this operation to its replay body. **Does not** claim equality with DungeonMindServer’s private internal digest or projection; adapter mapping to Server belongs in `SBW07a`. |
| `request_body` | yes | Exact replayable create-request JSON (same bytes/canonicalization as digest input) |
| `source_draft_id` | yes | ThreatDraft id at claim time |
| `source_draft_version` | yes | ThreatDraft `version` at claim time |
| `source_candidate_id` | nullable | Provenance only; when present must match request body |
| `validation_receipt_digest` | yes | Definition digest the gate accepted |
| `authority_state` | yes | Closed enum below |
| `locator` | null until known | `{ provider, statblock_id, revision_id, definition_digest, contract, contract_version }` once Server create (or same-key replay) returns it |
| `materialization.draft_ref` | yes | `missing` \| `attached` \| `failed` \| `conflicted` (`conflicted` = draft already holds a different locator) |
| `terminal_code` / `failure_category` / `http_status` | only on `terminal_failure` | Present only when SBW07a-captured evidence proves persistence did not begin |
| `created_at` / `updated_at` | yes | ISO timestamps |

### Cardinality and history bound (closed)

```text
Choice: At most ONE acceptance operation per draft may be in
  {dispatched_unknown, server_committed, reconciled} at a time.
Not chosen: multiple concurrent committed proposals + later selection
  (incompatible with singular accepted_mechanics_ref; replacement is out of slice).

History bound: MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT = 32
  (counts every retained AcceptanceOperationV1 for that draft, including
   terminal_failure history and any active/unresolved/reconciled record).

33rd otherwise-valid claim (closed):
  Explicit pre-claim backpressure. Refuse the claim with acceptance_history_full.
  No Server create call. No journal insert. No compaction in SBW07.
Not chosen: proof-based compaction / durable tombstones in this slice
  (may be revisited later; unresolved/active records remain non-compactable forever
   under this contract).
```

**Atomic singular-slot claim (docs contract):**

```text
Under one draft-scoped lock or atomic transaction, and before any Server call:
  1. If retained AcceptanceOperationV1 count for this draft is already ≥ 32,
     refuse with acceptance_history_full (no insert).
  2. Else if any operation occupies
     {dispatched_unknown, server_committed, reconciled}, refuse with acceptance_busy.
  3. Else insert a new AcceptanceOperationV1 initialized exactly as:
       authority_state = dispatched_unknown
       locator = null
       materialization.draft_ref = missing
       terminal_code / failure_category / http_status = null/absent
       plus mandatory identity fields (operation_id, idempotency_key,
       create_request_digest, request_body, source_draft_id/version,
       validation_receipt_digest, timestamps; source_candidate_id as applicable).
  4. Release the lock before calling DungeonMindServer.
```

Concurrency proof and filesystem/store implementation belong in `SBW07b`, not this contract PR.

Consequences:

- New distinct accept claim (new `operation_id` / new `idempotency_key`) is **refused** while any operation is `dispatched_unknown`, `server_committed`, or `reconciled`.
- After `terminal_failure` only, a **new** key/operation may claim (prior create did not begin / did not commit per SBW07a-captured proof), **unless** the history bound blocks with `acceptance_history_full`.
- `reconciled` closes first-save for this draft in SBW07; replacing `accepted_mechanics_ref` is a later slice.
- Historical `terminal_failure` records may be retained for audit; they do not consume the singular active slot, but they **do** consume history capacity toward the 32 bound.
- Unresolved `dispatched_unknown` / unattached `server_committed` are **never** compacted away to admit new work.

### Authority states

| State | Meaning | Product may claim `mechanics_saved`? |
|---|---|---|
| `dispatched_unknown` | Claim written; Server create outcome **unknown** (in flight, timeout, response loss, auth failure before durable create proof, restart mid-flight) | **No** |
| `server_committed` | Exact locator/digest known from Server create or same-key **same-body** replay; draft-ref may be missing/failed/conflicted | **No** — use recovery UX (`server_committed_reference_pending` as **display label only**) |
| `reconciled` | Ordered journal repair completed after ThreatDraft attach of **this** operation's locator (`materialization.draft_ref=attached`) | **Yes** — and the draft already holds `workflow_state=mechanics_saved` |
| `terminal_failure` | Server error **explicitly captured in `SBW07a` fixtures** as proving persistence did not begin; all other post-dispatch failures stay `dispatched_unknown` | No |

**Not an authority state:** changed-body / wrong-key input conflicts. Those are **attempt responses** only; they must not rewrite the original operation's `authority_state`.

**Display label (not an authority state):** `server_committed_reference_pending` means authority=`server_committed` ∧ `draft_ref ≠ attached`. It must never be stored as `workflow_state` or as `mechanics_saved_*`.

### Product / gate states (pre-journal)

| State | Meaning |
|---|---|
| `acceptance_blocked` | Missing/stale validation receipt, validation errors, or digest mismatch — **no journal claim yet** |
| `acceptance_busy` | Another operation already occupies the singular active slot — **no new claim** |
| `acceptance_history_full` | Retained operation count already ≥ 32 — **no new claim**; no Server call; no compaction in SBW07 |

### Ordered reconcile protocol across two stores (closed)

The operation journal and the ThreatDraft are **separate durable records**. A draft-scoped lock prevents concurrent writers; it does **not** make two filesystem replacements crash-atomic. SBW07 therefore freezes an **ordered, restart-recoverable protocol**, not a multi-record transaction.

```text
Not chosen: requiring a real multi-document / multi-file ACID transaction for reconcile.
Chosen: Phase 1 then Phase 2 with explicit crash recovery and product-trust rules.
```

**Phase 1 — ThreatDraft attach (single draft-document replace / version CAS):**

```text
Allowed only when:
  - authority is server_committed with a durable locator, AND
  - draft.accepted_mechanics_ref is null, OR equals this operation's locator.
On success, one draft write sets:
  - accepted_mechanics_ref = exact locator fields
  - workflow_state = mechanics_saved
Do not advance journal authority in this phase.
```

**Phase 2 — Journal reconcile (single journal-record replace):**

```text
Allowed only after Phase 1 durable success is observed for this locator.
On success, one journal write sets:
  - authority_state = reconciled
  - materialization.draft_ref = attached
```

**Crash / restart between Phase 1 and Phase 2:**

```text
Observed combined state:
  - draft.accepted_mechanics_ref equals this operation.locator
  - draft.workflow_state = mechanics_saved
  - journal still server_committed
  - materialization.draft_ref ≠ attached (missing/failed/stale)

Product trust (closed):
  Trust the ThreatDraft. The product MAY claim mechanics_saved from
  draft.workflow_state + matching accepted_mechanics_ref even though the
  journal has not yet reached reconciled.

Recovery obligation (idempotent; no Server create; no locator overwrite):
  Perform Phase 2 journal repair to reconciled + draft_ref=attached.
```

**Crash before Phase 1:**

```text
Observed: journal server_committed (locator known); draft ref still null /
  not this locator; workflow_state ≠ mechanics_saved.
Product trust: must NOT claim mechanics_saved.
Recovery: retry Phase 1 under CAS rules, then Phase 2.
```

**Crash after Phase 2:** fully reconciled; reload proves both stores.

### Authoritative transition table

| Current | Event | Next | Required evidence | Server create? | Response truth | Compact/delete Server? |
|---|---|---|---|---|---|---|
| (none) / eligible; no active op; count < 32 | begin accept (atomic claim) | `dispatched_unknown` | under draft-scoped lock: history bound + singular-slot empty **and** `AcceptanceOperationV1` inserted with `authority_state=dispatched_unknown`, `locator=null`, `draft_ref=missing`, terminal fields null/absent, plus mandatory identity/body/digest fields; **lock released before Server call** | pending | submitting / unknown | no |
| retained count ≥ 32 | begin accept | unchanged (no claim) | history-bound check under same draft-scoped lock | no | `acceptance_history_full` | no |
| active op exists (`dispatched_unknown` \| `server_committed` \| `reconciled`) | begin accept with **new** key | unchanged (no new claim) | singular-slot check under same draft-scoped lock | no | `acceptance_busy` | no |
| any editable without claim | validate errors / stale receipt | `acceptance_blocked` | receipt digest ≠ current OR errors present | no | blocked | no |
| `dispatched_unknown` | process restart / response loss / transport timeout / connection unavailable | `dispatched_unknown` | stored `request_body` + Buddy-local `create_request_digest` | **same-key same-body replay required** | typed uncertainty; external commit may already exist; no failed claim | no |
| `dispatched_unknown` | auth 401/403 without durable create proof | `dispatched_unknown` | claim retained | retry **after** auth repair, same key + same body | auth failure category; still unknown | **never** |
| `dispatched_unknown` | same-key **same-body** replay → Buddy observes original resource/revision | `server_committed` | exact IDs/digest written to durable `locator` **before** Phase 1 draft attach | replay only | Buddy observation achieved; draft ref pending | no |
| `dispatched_unknown` | create success (first Buddy-observed response) | `server_committed` | exact IDs/digest; durable `locator` before Phase 1 | done | Buddy observation achieved | no |
| `dispatched_unknown` (original) | attempt presents **same key + changed** Buddy-local digest / body (local detect before call) | **`dispatched_unknown` unchanged** | original `request_body` / Buddy-local digest retained | **never** with changed body | attempt response: input conflict; recover via original body replay | no |
| `dispatched_unknown` (original) | Server idempotency **409** on a **changed-body** attempt | **`dispatched_unknown` unchanged** | treat as attempt conflict; original may have externally committed — **must** next replay original stored body (do not interpret 409 as original failure) | **never** alternate create | attempt response: input conflict; original still unknown pending original-body recovery | no |
| `dispatched_unknown` | Server error on **original** same-body path that `SBW07a` fixtures capture as proving persistence did **not** begin | `terminal_failure` | fixture-captured terminal evidence + category + HTTP | no further create for this op | typed failure | no |
| `server_committed` | Phase 1 draft attach success (version CAS; ref was null or equals this locator) | `server_committed` (draft now `mechanics_saved`; journal not yet reconciled) | durable draft write of `AcceptedMechanicsRefV1` + `workflow_state=mechanics_saved`; journal unchanged | no | product may claim **mechanics_saved**; journal repair still required | no |
| `server_committed` ∧ draft already attached this locator | Phase 2 journal repair | `reconciled` | journal write: `authority_state=reconciled`, `draft_ref=attached` | no | **mechanics_saved**; not published | no |
| `server_committed` | Phase 1 draft-ref write failure (I/O) while ref still null | `server_committed` (`draft_ref=failed`) | locator retained | no | `server_committed_reference_pending`; product must **not** claim `mechanics_saved` | **never** |
| `server_committed` | draft version CAS miss while ref still null | `server_committed` | reload draft; retry Phase 1 **only if** ref still null or equals this locator | no | pending ref; no second create | no |
| `server_committed` | draft already has `accepted_mechanics_ref` with a **different** locator | `server_committed` (`draft_ref=conflicted`) | both locators retained (draft ref + operation locator); never overwrite | no | explicit `accepted_ref_conflict`; no silent attach; no delete of either Server revision | **never** |
| `server_committed` | restart observes draft already attached this locator (`mechanics_saved`) while journal not reconciled | `server_committed` → then Phase 2 → `reconciled` | draft locator equality proof; then journal repair | no | product already **mechanics_saved**; repair journal | no |
| `server_committed` | draft missing / deleted | `server_committed` | locator retained; expose recovery/error | no | Server mechanics exist; draft ref impossible until draft restored | **never** |
| `server_committed` | exact-read confirms locator/digest | `server_committed` (then Phase 1/2 if attach still needed) | read equality | read only | verification ok | no |
| `reconciled` | reload | `reconciled` | draft ref + journal reconciled + exact revision read digest equality | read | same IDs/digest; workflow `mechanics_saved` | no |
| any durable | same-key **same-body** replay | unchanged | digest match | no (unless still `dispatched_unknown`) | identical external result | — |

### Version / workflow CAS semantics (closed)

```text
1. Claim records source_draft_id + source_draft_version (audit / lineage).
2. Phase 1 ThreatDraft attach is allowed only when:
     - draft.accepted_mechanics_ref is null, OR
     - draft.accepted_mechanics_ref equals this operation's locator.
   On durable Phase 1 success (single draft-document write / version CAS):
     - accepted_mechanics_ref = exact locator fields
     - workflow_state = mechanics_saved
   Journal authority remains server_committed until Phase 2.
3. Phase 2 journal reconcile is allowed only after Phase 1 success (or restart
   observation of the same draft attach). On durable Phase 2 success:
     - operation.authority_state = reconciled
     - materialization.draft_ref = attached
4. CAS miss with ref still null/same: do not change authority; reload + retry Phase 1.
5. If reload shows a different accepted_mechanics_ref: do NOT retry overwrite.
   Stay server_committed; surface accepted_ref_conflict; retain both locators;
   never delete either Server revision. Selection/replacement is out of SBW07.
6. workflow_state becomes mechanics_saved ONLY in Phase 1 (ThreatDraft write).
   Journal reconciled is acknowledgment/repair, not a second product commit.
7. Authoring edits that advance draft.version while authority=server_committed
   do not invalidate the locator; they only change the CAS token for Phase 1
   when the attach is still legal under rule 2.
```

### ThreatDraft schema delta (declared here; implemented in `SBW07b`)

```text
# On ThreatDraftV1 (product materialization only):
accepted_mechanics_ref: AcceptedMechanicsRefV1 | null   # singular; no replacement in SBW07
workflow_state: drafting | candidate_ready | mechanics_saved

# Sibling journal (mandatory; not optional):
AcceptanceOperationV1 records under draft state root
  schema = dmb_statblock_acceptance_operation_v1
  active unresolved/committed count ≤ 1
```

`AcceptedMechanicsRefV1` fields (exact):

```text
provider = dungeonmind
statblock_id
revision_id
contract / contract_version
definition_digest
accepted_from_candidate_id?   # nullable provenance
accepted_from_draft_version
accepted_at
```

### Idempotency (Buddy-local binding; Server adapter in `SBW07a`)

- Persist `AcceptanceOperationV1` (including `idempotency_key`, Buddy-local `create_request_digest`, `request_body`) **before** outbound create.
- Buddy guarantees only:
  - same Buddy operation + same stored canonical body → replay allowed
  - same Buddy operation + changed body → reject locally (original authority unchanged)
- Precise adapter mapping onto Server create/idempotency semantics belongs in `SBW07a` (fixtures + client); this contract does **not** assert Buddy’s digest equals Server’s private internal digest.
- Server idempotency 409 on a changed-body attempt: attempt conflict; recover original via stored body; never interpret as original `terminal_failure`.
- UI double-submit → one operation_id / one idempotency key.
- Never invent local `statblock_id` / `revision_id`.

### Transport / terminality proof boundary

**Conservative terminal rule (frozen here):**

```text
An operation may become terminal_failure only from a Server error explicitly
captured in SBW07a fixtures as proving that persistence did not begin.
All other post-dispatch failures remain dispatched_unknown.
```

**Must remain `dispatched_unknown` (not failed):** Buddy/client transport timeout, connection unavailable, response loss after possible commit, authentication 401/403, persistence/write uncertainty, process restart, pre-route validation without SBW07a-captured non-begin proof, changed-body conflict responses, and any Server error not yet fixture-proven as “persistence did not begin.”

This contract PR does **not** enumerate a full Server exception taxonomy. Exact transport mapping and fixture capture belong in `SBW07a`. Idempotency 409 is never a terminal-failure proof for the original operation.

### Explicitly still false after SBW07

Graph Threat/binding, append child revision, preferred/latest, Markdown embed, combat, media, corpus promotion as acceptance, treating Buddy-unobserved Server persistence as `server_committed`, treating `server_committed` without ThreatDraft attach as `mechanics_saved`, replacing an existing `accepted_mechanics_ref`, multi-proposal selection, mutating original authority on changed-body conflict, pretending two store writes are crash-atomic without the ordered Phase 1→2 protocol, compacting history to admit a 33rd claim, and shipping `SBW06` before this slice.
