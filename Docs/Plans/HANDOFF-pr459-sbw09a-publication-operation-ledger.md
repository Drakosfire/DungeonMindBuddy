---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  The live-control server can durably claim and reload one graph-publication operation for an exact mechanics-saved ThreatDraft so later identity resolution and governed commit resume from stable authority instead of reconstructing mutable draft or graph state.

  ## Merge-ready invariant
  For one `operation_id`, the server-owned publication source snapshot, exact accepted-mechanics locator, expected World Graph parent, request digest, and lifecycle state must round-trip exactly across begin, read, refresh, cancel, and retry; exact replay is idempotent, changed inputs or source/head drift fail closed or become explicitly stale, and this slice performs no DungeonMind or World Graph mutation and never alters accepted mechanics.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Exact mechanics-saved source is snapshotted and digest-bound | publication models + service | predecessor mapping and digest-tamper matrix | {{TODO}} |
  | Begin/reload/replay preserve one operation authority | publication ledger store | atomic round-trip and exact-replay integration tests | {{TODO}} |
  | Draft or graph-parent drift never silently rebases | refresh/retry service | ordered stale/race adversarial tests | {{TODO}} |
  | Cancel and retry preserve one coherent active lineage | ledger transaction | cancellation, supersession, crash-boundary tests | {{TODO}} |
  | Routes expose the typed lifecycle without graph or DMS writes | FastAPI route boundary | route contract and no-mutation proof | {{TODO}} |
  | Existing accepted mechanics and SBW08 graph contracts do not regress | predecessor stores/contracts | focused regression commands | {{TODO}} |

  ## Scope and explicit deferrals
  - Required base: `f450885493108ce5d0c46b5a0e9d4e42173e3c8c`
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Paths outside §4: {{TODO: none or stop report}}
  - Deferred and still false: Threat create/connect resolution, graph proposal construction, preview/confirm, graph mutation, publication verification, Workbench UI, Hermes query/hydration, Threat projection UI, placement, and combat.

  ## Evidence produced
  ### Automated
  {{TODO}}

  ### Adversarial
  {{TODO}}

  ### Regression
  {{TODO}}

  ### Manual / dogfood
  Not applicable — this PR exposes a server contract and durable no-write operation ledger; it does not yet create a product publication action or mutate the World Graph.

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence / waiver / split}}
---

# HANDOFF — PR459 SBW09a durable Threat publication operation ledger

**Created:** 2026-07-30.  
**Status:** ACTIVE — dispatch exactly one durable operation-ledger capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr459-sbw09a-publication-operation-ledger.md`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Required implementation base:** `f450885493108ce5d0c46b5a0e9d4e42173e3c8c`  
**Suggested branch:** `feat/sbw09a-publication-operation-ledger`

> **Predecessor gate:** PR `#457` is merged. The World Graph can strictly persist and project an external statblock resource and exact `ThreatStatblockBinding`. Do not reopen the SBW08 contract or re-prove accepted-mechanics authoring.
>
> **Dispatch boundary:** This PR creates the durable authority record for a future publication. It does not choose create-new versus connect-existing, construct graph assertions, prepare a review proposal, confirm a write, update the World Graph, or add Workbench/UI controls.
>
> **Authority correction:** This handoff supersedes the operation-ledger portion of `HANDOFF-sbw09-governed-threat-binding-publication.md`. The bundled historical handoff is not dispatch authority; `SBW09b` and `SBW09c` remain separate successors.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Publication operation** | A durable server-owned intent to publish one exact mechanics-saved ThreatDraft against one exact expected World Graph parent. |
| **Publication source snapshot** | An immutable projection of the server-loaded ThreatDraft fields needed by later publication, including the exact `AcceptedMechanicsRefV1`; it contains no statblock definition or rules body. |
| **Expected parent** | The exact immutable World Graph revision against which later proposal/commit work must be prepared. It is never silently replaced by the current head. |
| **Ready** | The operation was claimed from an exact source snapshot while the observed graph head equaled the caller's expected parent. This is an as-of-claim statement, not a promise that the head can never advance. |
| **Stale** | A monotonic state proving that the current draft/source or graph head no longer matches the operation's immutable authority. The same operation never becomes ready again. |
| **Retry** | An explicit new operation ID that reuses the same still-current source snapshot and a newly supplied exact graph parent, atomically superseding the stale operation. |
| **Accepted mechanics** | The exact six-field locator plus acceptance provenance already attached to the ThreatDraft. It remains valid independently of graph publication. |
| **No-write slice** | The World Graph and DungeonMindServer are read-only dependencies in this PR; only the publication ledger is mutated. |

## §1 Mission and merge-ready invariant

The live-control server can durably claim and reload one graph-publication operation for an exact mechanics-saved ThreatDraft so later identity resolution and governed commit resume from stable authority instead of reconstructing mutable draft or graph state.

**Merge-ready invariant:** For one `operation_id`, the server-owned publication source snapshot, exact accepted-mechanics locator, expected World Graph parent, request digest, and lifecycle state must round-trip exactly across begin, read, refresh, cancel, and retry; exact replay is idempotent, changed inputs or source/head drift fail closed or become explicitly stale, and this slice performs no DungeonMind or World Graph mutation and never alters accepted mechanics.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Begin, reload, replay, freshness checks, cancellation, and retry all preserve or terminate the same immutable operation authority. |
| What adversarial sequence is most likely to falsify it? | Caller reads parent `A` → graph advances to `B` → begin or retry silently records `B` while claiming the caller reviewed `A` → later commit publishes against an unreviewed parent. |
| Would §7 detect that failure? | Yes. Tests require exact parent comparison at claim, no server substitution, post-claim advance → explicit stale, and retry with a new caller-supplied parent. |
| Which owning boundary is easiest to under-test? | The draft-scoped ledger transaction. Retry must supersede the old operation and install the new active operation in one atomic file write; helper-only tests would miss split lineage. |
| What fact would force this slice to stop or split? | Needing a Threat identity choice, graph assertion/proposal schema, confirmation token, commit receipt, graph write, post-commit verification, UI state, or mutation of `ThreatDraftV1`. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`; active Threat/statblock roadmap and tracker |
| Repository rules | `AGENTS.md`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; handoff template and allowlist discipline |
| Base revision | `f450885493108ce5d0c46b5a0e9d4e42173e3c8c` — merged PR `#457` |
| Predecessor contract | `ThreatDraftV1`; `AcceptedMechanicsRefV1`; `MechanicsLocatorV1`; SBW08 `ExternalResourceV1` / `ThreatStatblockBindingV1`; immutable World Graph head |
| Existing operation precedent | `AcceptanceOperationV1` plus the draft-scoped acceptance reconciliation journal; reuse lessons, not schema or state names blindly |
| Exact input consumed | Caller-supplied `operation_id`, expected draft version, expected World Graph parent, actor; server-loaded current ThreatDraft and current graph head |
| Named successor | `SBW09b` create-or-connect Threat resolution, then `SBW09c` governed proposal/confirm/verification |
| What remains false | No Threat identity decision, graph contribution, review preview, confirm token, committed revision, or published Threat exists |
| Explicit non-goals | DMS calls; statblock definition storage; graph writes; proposal/commit child contracts; UI; Hermes tools; placement; combat; generic authored-object framework |

Read authoritative inputs in order before changing code:

1. `AGENTS.md` and the external-agent PR loop.
2. `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`.
3. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.
4. `Docs/Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md` and merged SBW08 code/tests.
5. `apps/live_control_server/models/threat_draft.py`.
6. `apps/live_control_server/models/statblock_mechanics_acceptance.py`.
7. `apps/live_control_server/services/threat_draft_store.py`.
8. `apps/live_control_server/services/statblock_acceptance_reconciliation.py` as a persistence/replay precedent.
9. `apps/live_control_server/config.py` and `graph_memory.kernel.open_current_world_graph`.
10. Current route registration and focused tests named in §4.

Authority precedence:

```text
repository rules
→ grounded-object lifecycle decision
→ active publication-first roadmap/tracker
→ this PR459 handoff
→ merged ThreatDraft / accepted-mechanics / SBW08 contracts
→ current implementation precedents
→ old bundled SBW09 design
```

If the implementation base moved and changes any predecessor field, graph-head read behavior, store lock order, or route namespace, re-anchor this handoff before implementation.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Begin from mechanics-saved draft | No durable publication authority exists | Server loads exact draft/ref and graph head, validates caller pins, snapshots source, and atomically writes one ready operation | Yes | publication service + ledger |
| Begin from unsaved/mismatched draft | Publication intent could be reconstructed ad hoc | Reject before ledger mutation | Yes | service |
| Exact operation replay | No contract | Same operation ID + exact request returns the existing record without re-snapshotting or writing | Yes | ledger/service |
| Operation ID input conflict | No contract | Same ID + changed request fields returns conflict; existing record is unchanged | Yes | model/service |
| Competing operation | No contract | One ready/stale active operation per draft; unrelated second begin returns busy | Yes | ledger |
| Read after restart | No contract | Exact record and source snapshot reload from durable storage | Yes | ledger |
| Freshness refresh | No contract | Compare current draft/source and graph head; exact match stays ready, any drift transitions monotonically to stale | Yes | service + ledger |
| Dependency unreadable during refresh | No contract | Return typed unavailable/integrity result and leave durable state unchanged | Yes | service |
| Cancel | No contract | Ready/stale → cancelled; exact replay is idempotent; no draft/graph dependency required | Yes | ledger |
| Retry stale operation | No contract | New ID + exact still-current source + caller-supplied current parent atomically supersedes old and installs one new ready operation | Yes | ledger/service |
| Retry after source drift | No contract | Reject; caller must begin from the current draft as a new publication intent | Yes | service |
| History bound/corruption | No contract | Bounded records; malformed ledger fails closed and is never overwritten opportunistically | Yes | ledger parser/store |
| Downstream use | No stable root operation | Successors can reference `operation_id` and immutable snapshot without changing it | Yes | public durable contract |

Ordered adversarial sequences:

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Caller supplies parent `A` → head is already `B` at begin | Reject with parent mismatch; no record; never substitute `B` | begin mismatch test |
| Begin records parent `A` → graph advances to `B` → refresh | Same operation becomes stale with `graph_parent_changed`; stored parent remains `A` | stale refresh integration |
| Begin records source version/ref → draft authored fields or accepted ref changes → refresh | Operation becomes stale with exact source reason; snapshot/ref remain unchanged | draft drift test |
| Begin → process restart → read | Complete source snapshot, digest, locator, parent, and state reload exactly | round-trip test |
| Same ID exact replay after draft/head drift | Return existing record; do not silently rebuild it from current state | replay test |
| Same ID changed expected parent/version/actor | Conflict; no mutation | request-digest test |
| Stale operation → retry → crash boundary | One atomic ledger write yields old superseded + new active, or neither; never two active operations or orphan lineage | ledger transaction test |
| Cancel and retry race | Serialized draft-scoped lock yields one coherent terminal/active lineage | concurrency test |
| Refresh cannot read graph or draft due to dependency/integrity failure | Return typed failure; do not mark stale based on untrusted absence and do not rewrite ledger | failure-injection test |
| Any begin/refresh/cancel/retry | ThreatDraft bytes, accepted mechanics ref, graph head/revision payload, and DMS call count remain unchanged | no-mutation proof |

## §4 Files in scope — allowlist

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication.py` | Strict snapshot, request/response, operation, ledger, state, digest, and transition contracts |
| Create | `apps/live_control_server/services/threat_publication_operations.py` | Server-owned snapshot construction, claim/read/refresh/cancel/retry orchestration, lock order, and atomic ledger persistence |
| Create | `apps/live_control_server/routes/threat_publication.py` | Browser-safe begin/read/refresh/cancel/retry API without graph or DMS mutation |
| Modify | `apps/live_control_server/main.py` | Mount the focused router |
| Create | `tests/test_threat_publication_operations.py` | Model/store/service round-trip, stale, replay, concurrency, corruption, bounds, and no-mutation proof |
| Create | `tests/test_threat_publication_routes.py` | Exact route schemas, status/error mapping, restart/replay, and route no-write proof |

**Bounded discovery exception:**

```text
Directory: apps/live_control_server/, tests/
Maximum additional paths: 3
Allowed path kinds: an existing shared test fixture/helper, package export, or route-registration test directly required to prove §1
Decision rule for including one: the named path must already own the exact draft load, graph-head read, atomic JSON write, or FastAPI app registration used by this operation; no behavior expansion
```

If implementation needs to modify `ThreatDraftV1`, accepted-mechanics models/store, SBW08 graph contracts, graph Kernel code, Graph Review, UI, or generated clients, stop and report the split.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/**` | A product publication action belongs after identity resolution and governed commit exist |
| `src/graph_memory/**` | SBW08 is merged; PR459 reads the head only and must not create or merge contributions |
| DungeonMind clients/routes/generated definitions | Accepted mechanics already exist; no provider call or mechanics hydration is needed |
| `ThreatDraftV1` workflow states or draft JSON schema | Publication has separate authority and must not collapse into mechanics-saved state |
| create-new / connect-existing choice or matching | `SBW09b` |
| graph assertions, proposal digest, review package, confirmation token | `SBW09b`/`SBW09c` |
| graph commit, receipt, post-commit verification | `SBW09c` |
| graph overlay as a statblock-specific bypass | Publication must eventually use current governed immutable World Graph authority |
| automatic latest/current-parent substitution | Exact parent is caller-reviewed authority |
| historical draft reconstruction or general draft version store | Separate capability; PR459 snapshots only the source used by its operation |
| Hermes autonomous publication | Prohibited by the lifecycle decision |
| query/hydration/Threat Sheet | `SBW10a`/`SBW10b` |
| placement/combat/media | Later roadmap phases |
| universal `PublicationOperation` framework | Threat + statblock must prove the seam first |

Collision-risk pre-flight result:

```text
No current code/test artifact named threat_publication or dmb_threat_publication_operation_v1 exists.
The historical HANDOFF-sbw09-governed-threat-binding-publication.md is superseded research, not an implementation collision.
```

## §6 Implementation contract and conditional matrices

### 6.1 Public request and source authority

Begin request:

```text
BeginThreatPublicationOperationRequestV1:
  operation_id
  expected_draft_version
  expected_parent_revision_id
  actor
  operator_note?
```

The client must not send:

- a Threat source snapshot;
- an accepted mechanics locator;
- world or campaign overrides;
- a current-head fallback;
- create/connect identity;
- graph assertions or proposal data.

The server loads the committed `ThreatDraftV1` and requires:

```text
draft.version == expected_draft_version
draft.workflow_state == mechanics_saved
draft.accepted_mechanics_ref != null
current_world_graph.head_revision_id == expected_parent_revision_id
```

### 6.2 Immutable publication source snapshot

```text
ThreatPublicationSourceSnapshotV1:
  schema: dmb_threat_publication_source_v1
  draft_id
  draft_version
  world_id
  campaign_id
  focus
  name
  slug_hint
  description
  threat_kind
  intended_roles[]
  tags[]
  generation_intent
  encounter_context
  graph_context_snapshot
  accepted_mechanics_ref
```

Rules:

- Build the snapshot only from the server-loaded typed draft.
- Include all authored concept fields that can affect later create/connect review so a current-only draft store cannot erase publication authority.
- Exclude candidate bodies, statblock definitions, rules elements, rendered Markdown, mutable timestamps, and operation/UI state.
- Compute `source_digest` from canonical alias-serialized snapshot JSON.
- Validate `accepted_mechanics_ref.to_mechanics_locator()` against the existing six-field contract.
- The operation model recomputes and verifies `source_digest` on every load.

### 6.3 Durable operation and ledger

```text
ThreatPublicationOperationV1:
  schema: dmb_threat_publication_operation_v1
  operation_id
  request_digest
  source_snapshot
  source_digest
  expected_parent_revision_id
  state: ready | stale | cancelled | superseded
  stale_reasons[]
  supersedes_operation_id?
  superseded_by_operation_id?
  cancelled_by?
  cancellation_note?
  created_by
  created_at
  updated_at
```

```text
ThreatPublicationLedgerV1:
  schema: dmb_threat_publication_ledger_v1
  draft_id
  active_operation_id?
  operations[]
```

Storage:

```text
out/threat_publication_operations/<draft_id>/ledger.json
out/threat_publication_operations/<draft_id>/.publication.lock
```

Rules:

- One draft-scoped ledger is the commit authority so retry can update old and new lineage in one atomic JSON replace.
- Maximum 32 operations per draft unless a smaller existing repo bound is deliberately reused.
- `active_operation_id` must identify exactly one `ready` or `stale` record.
- `cancelled` and `superseded` are terminal.
- `stale` requires at least one typed reason and can never transition back to `ready`.
- `superseded` requires `superseded_by_operation_id`; the referenced record must exist and point back through `supersedes_operation_id`.
- Operation IDs use UUID or a bounded `pubop_...` form; path traversal and alias forms reject.
- Record timestamps are metadata, never identity.
- Corrupt schema, digest, lineage, active pointer, duplicate ID, or over-bound history fails closed.

### 6.4 Lifecycle operations

```text
begin:
  exact existing operation_id + identical request_digest -> return existing
  existing operation_id + different request -> input_conflict
  another ready/stale operation for draft -> publication_busy
  valid source + exact observed parent -> append ready and set active
  source/head mismatch -> reject before write

read:
  load exact operation; no freshness side effect

refresh:
  load exact operation and trusted current draft/head
  exact source + parent -> ready unchanged
  source or parent drift -> monotonically stale with typed reasons
  dependency/integrity unavailable -> typed failure, no ledger mutation

cancel:
  ready/stale -> cancelled, clear active
  cancelled replay -> unchanged
  superseded -> conflict
  does not read or mutate draft/graph

retry:
  only stale active operation
  new operation_id required
  current source digest and accepted locator must equal old snapshot
  caller supplies a new exact expected parent that equals observed head
  one atomic ledger write: old superseded, new ready, active -> new
  source drift -> reject; begin a new publication intent from current draft
```

Suggested stale reasons:

```text
draft_version_changed
source_digest_changed
accepted_mechanics_changed
world_or_campaign_changed
graph_parent_changed
```

Do not use a missing/corrupt dependency as evidence of semantic staleness. Return typed unavailable/integrity failure and leave the record unchanged.

### 6.5 Replay and trust contract

```text
Input:
  caller operation identity and exact version/parent expectations;
  server-loaded ThreatDraft and graph head

Output:
  durable typed operation/ledger or typed no-write refusal

Invariant:
  same as §1

Failure behavior:
  draft missing/not mechanics_saved -> no record
  version mismatch -> no record
  graph parent mismatch -> no record
  operation input conflict -> existing record unchanged
  active slot busy/history full -> no record
  refresh dependency unavailable -> record unchanged
  digest/ledger corruption -> fail closed; never auto-repair
  retry source mismatch -> old operation unchanged
  cancel terminal conflict -> unchanged

Replay / idempotency:
  same begin input + same operation_id -> exact existing record
  changed begin input + same operation_id -> conflict
  refresh on ready with no drift -> no semantic write
  refresh on stale -> exact stale record
  cancel replay -> exact cancelled record
  retry replay with same new operation_id/request -> exact new record and lineage
  changed retry body + reused new operation_id -> conflict

Trust boundary:
  Verifies: committed draft identity/version/state, exact accepted mechanics ref,
            canonical source digest, current graph head equality at claim/refresh,
            ledger lineage and operation request identity
  Records without proving: creative correctness of description, whether the selected
            future Threat identity is new or existing, DMS availability after acceptance
  Rejects: client-supplied snapshots/locators, display-name identity, latest-parent
           fallback, graph contribution data, copied mechanics
```

### 6.6 Commit model

The only irreversible boundary in PR459 is the publication-ledger write.

```text
Commit point:
  atomic replace of one draft-scoped ThreatPublicationLedgerV1

Before commit:
  no publication operation exists or changes

After commit:
  operation authority survives restart; ThreatDraft, accepted mechanics, DMS, and
  World Graph are unchanged

Truthful result after a post-write response failure:
  exact replay with the same operation_id/request returns the durable record

Retry transaction:
  old supersession + new operation + active pointer are one ledger replacement
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Begin | load ledger, draft, graph head | ready record | draft/op missing handled explicitly | no write | fail closed | parent/source mismatch rejects | exact ID/body resumes |
| Read | load ledger only | exact record | typed 404 | storage unavailable | corrupt ledger = 500 | terminal state returned | no mutation |
| Refresh | load ledger + trusted draft/head | ready unchanged | operation miss = 404 | unchanged + typed failure | unchanged + fail closed | drift → stale | stale replay exact |
| Cancel | load ledger only | cancelled | op miss = 404 | storage unavailable | fail closed | superseded rejects | cancelled replay exact |
| Retry | load ledger + trusted draft/head | atomic old→superseded/new→ready | old/new miss/conflict explicit | unchanged | fail closed | only stale active source | exact new ID/body resumes |
| Future SBW09b/c consumer | exact operation ID | consume immutable snapshot | missing blocks | blocks | digest mismatch blocks | stale/cancelled/superseded blocks | no fallback |

No fallback to current draft fields, another accepted ref, current graph head, label/alias, latest statblock revision, or direct graph state.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Operation | exact validated `operation_id` | reuse with changed request conflicts | No |
| Draft | exact UUID + exact version in snapshot | current version drift stales | No |
| Mechanics | exact six-field locator inside `AcceptedMechanicsRefV1` | changed ref stales/conflicts | No |
| Source | canonical complete snapshot + SHA-256 digest | digest mismatch is integrity failure | No |
| World Graph | exact `world_id` + expected parent revision | changed head stales or rejects | No |
| Actor/note | actor is audit metadata bound into request replay; note is not world identity | changed same-ID request conflicts | No |
| Labels/aliases | snapshot presentation/input for later review only | never resolve durable identity in PR459 | No |
| Retry lineage | exact old/new operation IDs | two active or broken backlink is corruption | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Begin | draft-scoped ledger JSON | exact snapshot/digests/parent/state | same ID/body returns same record | strict v1 schema; no permissive unknown fields | delete only through explicit future migration, not runtime |
| Refresh | atomic ledger replacement only when state changes | immutable source/parent preserved | ready no-drift and stale replay are no-op | additive reason vocabulary requires version review | stale is monotonic |
| Cancel | same ledger | terminal audit fields exact | idempotent | v1 terminal state | no uncancel |
| Retry | same ledger, two linked records | old/new/backlink/active pointer exact | exact replay returns same new record | no cross-version silent upgrade | old remains superseded |
| Reload | strict ledger parse | every digest and cross-record invariant revalidated | read-only | corrupt/unknown schema fails | operator repair is separate tooling |

### D. Predecessor-to-consumer mapping

**Grounding source:** canonical current models, not hand-written approximations.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| `ThreatDraftV1.draft_id/version` | UUID string / integer ≥1 | snapshot identity | exact copy | typed draft fixture |
| `world_id/campaign_id` | bounded IDs | snapshot + graph read scope | exact copy | mapping test |
| authored concept fields | typed nested models/lists/nullability | snapshot | alias-serialized exact copy | full snapshot equality |
| `workflow_state` | `mechanics_saved` required | begin eligibility | validate, not copied as mutable state | negative matrix |
| `accepted_mechanics_ref` | exact locator + acceptance provenance, nullable | snapshot exact ref | require non-null; exact copy | locator equality test |
| `AcceptedMechanicsRefV1.to_mechanics_locator()` | six exact fields | later SBW08 binding input | prove equality only; no graph assertion yet | compatibility test |
| current World Graph head | `WorldGraphHead.head_revision_id` | expected parent check | exact equality with caller request | parent mismatch/race test |
| caller request | operation ID/version/parent/actor/note | `request_digest` | canonical typed request digest | tamper/replay test |
| acceptance operation precedent | durable claim/resume/conflict patterns | publication ledger behavior | reuse semantics, not schema/state names | regression/design inspection |

Invented fixtures that bypass `ThreatDraftV1`, `AcceptedMechanicsRefV1`, or real World Graph head models do not prove this mapping.

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Snapshot is complete, strict, and digest-bound | models | contract/adversarial | focused model matrix | full typed source round-trips; missing/extra/tampered fields reject | any permissive repair/default of authority |
| Begin writes one exact ready operation | service + ledger | integration | begin from real typed draft/temp graph | exact source/ref/parent persisted; draft/head unchanged | reconstructed or partial authority |
| Replay and operation-ID conflict are deterministic | ledger/service | adversarial | same ID same/different body | same returns exact record; changed conflicts | second record or silent mutation |
| Parent/source drift is explicit, never rebased | refresh service | ordered adversarial | claim A, advance/edit, refresh | stored source/parent unchanged; stale reasons exact | parent/source silently replaced |
| Dependency failure cannot invent staleness | service | failure injection | draft/graph/storage unreadable | typed failure and byte-identical ledger | state mutation from untrusted read |
| Cancel is terminal and idempotent | ledger | transition | cancel/replay/conflict | active pointer cleared once | uncancel or dependency side effect |
| Retry is atomic and lineage-safe | ledger transaction | concurrency/adversarial | stale→retry plus injected write failure/concurrent cancel | one active operation; linked old/new or no change | orphan/new active plus old active |
| Accepted mechanics and graph remain untouched | service/route | no-mutation | hash draft and graph files; spy DMS client/import boundary | byte-identical draft/head/revision and zero DMS calls | any external mutation |
| Route contract is strict and reloadable | FastAPI | contract/integration | route test suite | typed status/errors, exact operation after app restart | generic 500/opaque body or mutation |
| Bounds/corruption fail closed | ledger store | adversarial | history limit, malformed schema/digest/linkage | no overwrite/auto-repair | corrupt record accepted |
| Predecessor suites remain green | existing stores/contracts | regression | commands below | no new failures vs base | unexplained regression |

Required commands:

```bash
uv run pytest -q tests/test_threat_publication_operations.py tests/test_threat_publication_routes.py
uv run pytest -q tests/test_threat_draft_store.py tests/test_statblock_mechanics_acceptance.py tests/test_statblock_binding_graph_contract.py
uv run ruff check apps/live_control_server/models/threat_publication.py apps/live_control_server/services/threat_publication_operations.py apps/live_control_server/routes/threat_publication.py apps/live_control_server/main.py tests/test_threat_publication_operations.py tests/test_threat_publication_routes.py
uv run python -m compileall -q apps/live_control_server/models/threat_publication.py apps/live_control_server/services/threat_publication_operations.py apps/live_control_server/routes/threat_publication.py
git diff --check
git diff --name-only f450885493108ce5d0c46b5a0e9d4e42173e3c8c...HEAD
git diff --stat f450885493108ce5d0c46b5a0e9d4e42173e3c8c...HEAD -- \
  apps/live_control_server/models/threat_publication.py \
  apps/live_control_server/services/threat_publication_operations.py \
  apps/live_control_server/routes/threat_publication.py \
  apps/live_control_server/main.py \
  tests/test_threat_publication_operations.py \
  tests/test_threat_publication_routes.py
```

Required adversarial test names or equivalent:

```text
test_begin_rejects_parent_mismatch_without_record
test_refresh_marks_graph_parent_changed_without_rebasing
test_refresh_marks_source_drift_without_replacing_snapshot
test_exact_replay_does_not_resnapshot_current_draft
test_dependency_failure_leaves_ledger_byte_identical
test_retry_atomically_supersedes_and_installs_one_active_operation
test_concurrent_cancel_retry_has_one_coherent_winner
test_all_operations_leave_draft_and_graph_bytes_unchanged
test_corrupt_ledger_fails_closed_without_rewrite
```

### Minimal live / dogfood proof

Not applicable — PR459 intentionally has no GM-facing publication surface and no World Graph mutation. Route-level temp-root integration is the owning proof. A new panel, manual graph write, or real campaign mutation would be scope expansion.

### Baseline failure protocol

For any required command failing on base:

- run the same command on `f450885493108ce5d0c46b5a0e9d4e42173e3c8c` and PR head;
- record exact base/head results;
- do not call the gate green;
- name an explicit operator waiver if the failure remains an acceptance gate.

## §8 Required PR description and handback

The PR description must remain current and include:

1. §1 Mission copied exactly.
2. §1 merge-ready invariant copied exactly.
3. Every §7 guarantee with required evidence, produced result, and provenance.
4. Base `f450885...` and exact head SHA.
5. Actual changed paths and focused diff stat.
6. Every required command and exact result.
7. Author-local, independently rerun, CI, or manual provenance for each result.
8. Base/head comparison for any failure.
9. Explicit waivers; `none` when none.
10. Paths outside §4; `none` or a stop report.
11. Stop conditions encountered and resolution.
12. Confirmation that graph and draft bytes remained unchanged in no-mutation tests.
13. Confirmation that `SBW09b`/`SBW09c` remain false.
14. Confirmation that the complete handoff was followed without compressing the matrices.

Required demolition declaration:

```text
Replaced path: ad hoc reconstruction of graph-publication intent from current ThreatDraft/current head
Deleted in this PR: no
If no, retained reason: no existing product publication operation exists to delete; adjacent current-state reads remain valid for their present consumers
Named remaining consumer: existing Workbench accepted-mechanics and generic graph authoring flows
Required deletion owner: SBW09c removes any temporary statblock-specific publication bypass if one is discovered
```

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability was delivered: a durable no-write publication operation root — proved by §7 begin/reload tests.
- [ ] The §1 invariant holds across begin, read, refresh, cancel, retry, restart, concurrency, and failure sequences — proved by the owning-boundary tests.
- [ ] The source snapshot uses real `ThreatDraftV1` / `AcceptedMechanicsRefV1` shapes and recomputes its digest on reload.
- [ ] Expected graph parent is exact and immutable; no current/latest substitution exists.
- [ ] Same operation ID exact replay is idempotent; changed request reuse conflicts.
- [ ] One draft has at most one ready/stale active operation.
- [ ] Stale is monotonic and records typed reasons without replacing source/parent authority.
- [ ] Retry updates supersession lineage and active pointer in one atomic ledger replacement.
- [ ] Cancel is terminal and idempotent.
- [ ] Dependency failures and corrupt storage do not mutate or auto-repair the ledger.
- [ ] ThreatDraft, accepted mechanics, DMS, and World Graph remain unchanged.
- [ ] No create/connect, graph proposal, confirm, commit, verification, or UI contract was introduced.
- [ ] Every changed path is in §4 or a reported bounded exception.
- [ ] PR body truthfully records all evidence, provenance, gaps, and waivers.
- [ ] `SBW09b` and `SBW09c` remain named, unimplemented successors.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- a need to choose or resolve Threat identity;
- a need to define graph assertions, proposal effects, confirmation tokens, or commit receipts;
- a need to mutate the World Graph, an authored overlay, ThreatDraft, accepted mechanics, or DMS;
- an inability to snapshot later-publication source without copying mechanics;
- an operation state that cannot be expressed honestly before SBW09b/c;
- a two-file retry transaction that cannot prove atomic old/new lineage;
- an unavoidable lock-order cycle with ThreatDraft or graph stores;
- a second active operation that cannot be rejected or serialized;
- a predecessor model mismatch from the shapes mapped in §6D;
- a required path outside §4/bounded discovery;
- a test that can only pass by using current/latest fallback;
- a base failure requiring operator waiver.

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
