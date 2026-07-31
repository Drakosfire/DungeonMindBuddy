---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  The live-control server can durably claim and reload one publication operation for one exact mechanics-saved ThreatDraft and one exact expected World Graph parent, giving later identity-resolution and governed-commit work stable authority without reconstructing mutable draft or graph state.

  ## Merge-ready invariant
  For one `operation_id`, the server-owned source snapshot, exact accepted-mechanics locator, expected World Graph parent, request digest, lifecycle state, and retry lineage round-trip exactly across begin, read, refresh, cancel, restart, and retry. Exact replay is idempotent; changed inputs, source drift, parent drift, dependency failure, or corrupt storage never silently rebase or repair authority. This slice writes only its publication ledger and performs no DungeonMind or World Graph mutation.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Exact mechanics-saved source is snapshotted and digest-bound | publication models + service | predecessor mapping and digest-tamper matrix | {{TODO}} |
  | Begin, reload, and exact replay preserve one operation authority | publication ledger store | atomic round-trip and replay integration tests | {{TODO}} |
  | Draft or graph-parent drift becomes explicit stale state without rebasing | refresh service | ordered stale/race tests | {{TODO}} |
  | Cancel and retry preserve one coherent active lineage | ledger transaction | cancellation, supersession, injected-failure, and concurrency tests | {{TODO}} |
  | Routes expose the typed lifecycle without graph or DungeonMind writes | FastAPI route boundary | route contract and no-mutation proof | {{TODO}} |
  | Existing ThreatDraft, accepted-mechanics, and SBW08 contracts do not regress | predecessor boundaries | focused regression commands | {{TODO}} |

  ## Scope and explicit deferrals
  - Required base: `c371d43178a2b83da299319a047f93bae50d0959`
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Paths outside the handoff allowlist: {{TODO: none or stop report}}
  - Still false after merge: create-new/connect-existing Threat resolution, graph proposal construction, preview/confirm, World Graph mutation, publication verification, Workbench UI, Hermes hydration, Threat projection UI, placement, and combat.

  ## Evidence produced
  ### Automated
  {{TODO}}

  ### Adversarial
  {{TODO}}

  ### Regression
  {{TODO}}

  ### Manual / dogfood
  Not applicable. This slice exposes a server contract and durable no-write operation ledger; it does not yet expose a GM-facing publication action or mutate campaign state.

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence / waiver / split}}
---

# HANDOFF — SBW09a durable Threat publication operation ledger

**Created:** 2026-07-31.  
**Status:** ACTIVE DESIGN — dispatch exactly one durable publication-operation capability after the repository synchronization gate below.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw09a-publication-operation-ledger.md`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Design anchor:** `103b727cbfe7ce5f816e381c7dc8fab64fd76372`  
**Authority-sync main:** `c371d43178a2b83da299319a047f93bae50d0959` — current `main` merge containing the unnumbered handoff and tracker-pointer correction.
**Required implementation base:** `c371d43178a2b83da299319a047f93bae50d0959` — exact authority-sync commit, or a later deliberate authority-sync commit.
**Suggested branch:** `feat/sbw09a-publication-operation-ledger`

No future PR number is assigned by this handoff. The hosting system or operator may assign one when a pull request is actually opened.

> **Predecessor gate:** merged SBW08 established strict persisted and projected `ExternalResourceV1` and exact `ThreatStatblockBindingV1` contracts derived from the accepted six-field mechanics locator. Do not reopen that graph contract or re-prove mechanics acceptance.
>
> **Dispatch boundary:** this slice creates durable authority for a future publication attempt. It does not choose create-new versus connect-existing, construct graph assertions, prepare a reviewed proposal, confirm a write, update the World Graph, verify a committed publication, or add Workbench controls.

## §0 Repository synchronization gate

Current `main` contains a numbered draft handoff and tracker language that pre-assigns a future pull-request number. Before external implementation dispatch:

1. add this handoff at `Docs/Plans/HANDOFF-sbw09a-publication-operation-ledger.md`;
2. mark the numbered draft as superseded or remove it so only one handoff is ACTIVE;
3. update the Threat/statblock tracker and superseded bundled SBW09 document to point to this unnumbered path;
4. remove future-number language from the active SBW09a tracker row and immediate-dispatch text;
5. replace `{{EXACT_HANDOFF_COMMIT_SHA}}` in the PR-body template with the resulting immutable main SHA (current authority-sync base: `c371d43178a2b83da299319a047f93bae50d0959`);
6. dispatch the worker from `c371d43178a2b83da299319a047f93bae50d0959`, or from a later deliberate authority-sync commit that contains this complete handoff, tracker, and roadmap state.

Do not combine those documentation corrections with the implementation slice unless repository process explicitly requires the handoff file to travel in the implementation branch.

## §1 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User/operator surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Durable publication-operation authority | Yes | Yes | Server API only | Yes | Yes | Include |
| Create-new versus connect-existing Threat resolution | Yes | Yes | Later review surface | Yes | Yes | Successor: `SBW09b` |
| Graph assertion/proposal construction and review package | Yes | Yes | Review surface | Yes | Yes | Successor: `SBW09c` |
| Confirmed World Graph commit and exact post-commit verification | Yes | Yes | Publication result | Yes | Yes | Successor: `SBW09c` |
| Workbench publication controls | Yes | No new authority by itself | Yes | Yes | Yes | Successor after server publication path |
| Hermes query/hydration and Threat projection | Yes | Yes | Yes | Yes | Yes | Successor: `SBW10a`/`SBW10b` |

**Selected capability:** durable no-write Threat publication-operation authority.

**Why the included work shares one invariant:** begin, read, refresh, cancel, restart, and retry are all observable transitions over the same immutable source-and-parent authority record. The route, model, service, persistence, and tests exist only to establish or prove that record.

**Mission falsification test:** this is no longer one slice if implementation must decide Threat identity, create graph assertions, mint a confirmation token, mutate a graph revision, verify a committed binding, or expose a GM publication workflow.

## §2 Mission and invariant

The live-control server can durably claim and reload one publication operation for one exact mechanics-saved ThreatDraft and one exact expected World Graph parent, giving later identity-resolution and governed-commit work stable authority without reconstructing mutable draft or graph state.

**Merge-ready invariant**

```text
For one operation_id, the server-owned source snapshot, exact accepted-mechanics
locator, expected World Graph parent, request digest, lifecycle state, and retry
lineage round-trip exactly across begin, read, refresh, cancel, restart, and retry.

Exact replay is idempotent. Changed inputs, source drift, parent drift, dependency
failure, or corrupt storage never silently rebase or repair authority.

This slice writes only its publication ledger and performs no DungeonMind,
ThreatDraft, accepted-mechanics, or World Graph mutation.
```

## §3 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`; active Threat/statblock roadmap and tracker |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; canonical handoff template |
| Design anchor | `103b727cbfe7ce5f816e381c7dc8fab64fd76372` |
| Implementation base | `c371d43178a2b83da299319a047f93bae50d0959`, or a later deliberate authority-sync commit that contains this complete handoff, tracker, and roadmap state |
| Predecessor contracts | `ThreatDraftV1`; `AcceptedMechanicsRefV1`; `MechanicsLocatorV1`; SBW08 `ExternalResourceV1` and `ThreatStatblockBindingV1`; immutable World Graph head |
| Existing precedent | `AcceptanceOperationV1` and its reconciliation journal; reuse durability, replay, and fail-closed lessons without reusing its schema or authority states blindly |
| Exact input consumed | Route `draft_id`; caller-supplied `operation_id`, expected draft version, expected World Graph parent, actor, optional note; server-loaded current ThreatDraft and observed current graph head |
| Storage roots | Publication ledger root and ThreatDraft root are both `repo_root()`; World Graph root is independently `world_graph_root()` from `DUNGEONMIND_WORLD_GRAPH_ROOT` |
| Named successors | `SBW09b` explicit create/connect resolution; `SBW09c` reviewed proposal, governed commit, and exact verification |
| What remains false | No Threat identity decision, graph contribution, review preview, confirmation token, committed revision, or published Threat exists |
| Explicit non-goals | DungeonMind calls; mechanics bodies; graph writes; proposal/confirm contracts; UI; Hermes tools; placement; combat; universal authored-object framework |

Read authoritative inputs in order before changing code:

1. `AGENTS.md` and the external-agent PR loop rules.
2. `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`.
3. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` after the synchronization gate.
4. `Docs/Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md` and merged SBW08 code/tests.
5. `apps/live_control_server/models/threat_draft.py`.
6. `apps/live_control_server/models/statblock_mechanics_acceptance.py`.
7. `apps/live_control_server/services/threat_draft_store.py`.
8. `apps/live_control_server/services/statblock_acceptance_reconciliation.py` as persistence/replay precedent.
9. `apps/live_control_server/config.py` and `src/graph_memory/kernel/world_graph.py` / exported public read boundary.
10. Existing live-control route registration and focused tests.

Authority precedence:

```text
repository rules
→ grounded authored-object lifecycle decision
→ active publication-first roadmap/tracker
→ this unnumbered SBW09a handoff
→ merged ThreatDraft / accepted-mechanics / SBW08 contracts
→ current implementation precedents
→ superseded bundled SBW09 design
→ chat or local summaries
```

Stop and report if the implementation base changes any predecessor field, graph-head read behavior, store lock order, route namespace, or authority assumption used below.

## §4 Shared vocabulary

| Term | Definition |
|---|---|
| **Publication operation** | A durable server-owned intent to begin publishing one exact mechanics-saved ThreatDraft snapshot against one exact expected World Graph parent. |
| **Publication source snapshot** | An immutable projection of the committed ThreatDraft fields needed for later create/connect review, including the exact `AcceptedMechanicsRefV1`; it contains no statblock definition or rules body. |
| **Expected parent** | The exact immutable World Graph revision the caller intends later proposal work to use. It is never silently replaced with current/latest. |
| **Ready** | Trusted draft and graph reads matched the caller's pins during claim or refresh. This is an observed-as-of check, not a promise that the graph can never advance afterward. |
| **Stale** | A monotonic state proving the current trusted draft source or observed graph head no longer matches the immutable operation authority. A stale operation never becomes ready again. |
| **Cancelled** | A terminal operator decision that ends the operation without changing draft, mechanics, DungeonMind, or graph state. |
| **Superseded** | A terminal lineage state linking an old stale operation to one explicit retry operation. |
| **Retry** | An explicit new operation ID that reuses the same still-current immutable source snapshot and a newly supplied exact graph parent, atomically superseding the stale operation. |
| **No-write slice** | Only the publication ledger may change. ThreatDraft, accepted mechanics, DungeonMind, and World Graph are read-only dependencies. |

## §5 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Begin from mechanics-saved draft | No durable publication authority | Validate caller pins against trusted server reads, snapshot exact source, and atomically persist one ready operation | Yes | service + ledger |
| Begin from draft without saved mechanics | Publication intent could be reconstructed ad hoc | Reject before ledger mutation | Yes | service |
| Draft version mismatch | No publication contract | Reject; do not snapshot another version | Yes | service |
| Expected parent mismatch | No publication contract | Reject; never substitute observed current head | Yes | service |
| Exact begin replay | No contract | Same operation ID and exact request returns the durable existing record without re-snapshotting | Yes | ledger + service |
| Operation ID reused with changed input | No contract | Typed conflict; existing record unchanged | Yes | model + service |
| Competing active operation | No contract | At most one ready/stale operation per draft; unrelated begin returns busy | Yes | ledger |
| Read after restart | No contract | Exact operation and immutable snapshot reload from storage | Yes | ledger |
| Refresh with no drift | No contract | Ready record remains semantically unchanged | Yes | service |
| Refresh after draft/source drift | No contract | Transition monotonically to stale with typed reason; immutable snapshot remains unchanged | Yes | service + ledger |
| Refresh after graph-head drift | No contract | Transition monotonically to stale; expected parent remains unchanged | Yes | service + ledger |
| Trusted dependency unavailable/corrupt | No contract | Typed unavailable/integrity failure; ledger remains byte-identical | Yes | service |
| Cancel | No contract | Ready/stale → cancelled; exact replay idempotent; no external dependency read required | Yes | ledger |
| Retry stale operation | No contract | New ID plus exact still-current source and caller-supplied observed parent atomically supersedes old and installs one ready active operation | Yes | service + ledger |
| Retry after source drift | No contract | Reject and leave the stale operation active; caller must cancel that stale operation before beginning a new publication intent from the current draft | Yes | service + ledger |
| Corrupt or over-bound ledger | No contract | Fail closed; never opportunistically repair or overwrite | Yes | parser + store |
| Downstream successor use | Successors could reconstruct mutable state | Consume exact operation ID and immutable snapshot; no fallback | Yes | durable public contract |

## §6 Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Caller supplies parent `A`; observed head is already `B` | Reject parent mismatch; no record; never substitute `B` | begin mismatch integration test |
| Begin observes `A`; graph later advances to `B`; refresh | Same operation becomes stale with `graph_parent_changed`; stored parent stays `A` | refresh integration test |
| Begin snapshots draft version/ref; draft authored fields or accepted ref later change; refresh | Stale with exact source reason; original snapshot/ref stay unchanged | source-drift test |
| Begin; process restart; read | Complete snapshot, digest, locator, parent, state, and audit fields reload exactly | round-trip test |
| Exact same-ID replay after draft/head drift | Return existing operation; never rebuild it from current state | replay test |
| Same ID with changed draft version, parent, actor, note, or path draft ID | Conflict; no mutation | request-digest test |
| Two unrelated begins race for one draft | Exactly one ready active operation; loser receives busy | concurrency test |
| Exact retry replay after old stale operation was superseded | Return the existing child operation before checking the stale-active slot | retry replay-order test |
| Source-drift retry followed by new begin | Retry rejects unchanged stale operation; cancel frees the slot; new begin succeeds from current source | cancel-before-begin lineage test |
| Stale operation retries while cancel races | Serialized draft-scoped ledger produces one coherent winner and no broken lineage | concurrency test |
| Retry persistence fails before atomic replace | Old ledger remains byte-identical and no new operation is visible | injected-write-failure test |
| Refresh cannot trust draft or graph read | Typed failure; operation does not become stale based on absence or corrupt data | failure-injection test |
| Any operation path | ThreatDraft bytes, accepted mechanics, graph head/revision files, and DungeonMind call count remain unchanged | no-mutation proof |

## §7 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_publication.py` | Strict source snapshot, operation, ledger, request/response, state, stale-reason, digest, and cross-record contracts |
| Create | `apps/live_control_server/services/threat_publication_operations.py` | Snapshot construction, begin/read/refresh/cancel/retry orchestration, lock order, and atomic ledger persistence |
| Create | `apps/live_control_server/routes/threat_publication.py` | Browser-safe typed API without graph or DungeonMind mutation |
| Modify | `apps/live_control_server/main.py` | Mount only the focused router |
| Create | `tests/test_threat_publication_operations.py` | Model/store/service round-trip, replay, stale, concurrency, corruption, bounds, and no-mutation proof |
| Create | `tests/test_threat_publication_routes.py` | Exact route schemas, status/error mapping, restart/replay, and route no-write proof |

**Bounded discovery exception:**

```text
Directories: apps/live_control_server/, tests/
Maximum additional paths: 3
Allowed kinds:
- an existing shared test fixture/helper;
- a package export;
- a route-registration test;
- a minimal existing graph-head read adapter owned by the live-control server.

Decision rule:
The path must already own the exact draft load, trusted graph-head read,
atomic JSON write, or FastAPI registration used by this operation.
No behavior expansion is permitted.
```

If implementation needs to modify `ThreatDraftV1`, accepted-mechanics models/store, SBW08 graph contracts, graph Kernel write behavior, Graph Review, generated clients, or UI, stop and report the split.

## §8 Explicitly out of scope

| Path/capability | Why excluded |
|---|---|
| `apps/live-control-ui/**` | Product controls belong after identity resolution and governed commit exist |
| `src/graph_memory/**` writes or contract changes | SBW08 is complete; this slice reads the current head only |
| DungeonMind client, routes, generated definitions, or definitions | Accepted mechanics already exist; no provider call or hydration is needed |
| `ThreatDraftV1` workflow states or persisted draft schema | Publication owns separate authority and must not collapse into `mechanics_saved` |
| Create-new/connect-existing matching or choice | `SBW09b` |
| Graph assertions, effects, proposal digest, review package, or confirmation token | `SBW09c` |
| Graph commit, receipt, or post-commit verification | `SBW09c` |
| Graph overlay or direct JSON mutation | Prohibited bypass of governed immutable World Graph authority |
| Automatic current/latest parent substitution | Violates caller-reviewed exact-parent authority |
| Historical draft reconstruction/version store | Separate capability; this slice snapshots the committed source it consumes |
| Hermes autonomous publication | Prohibited by lifecycle authority |
| Query, hydration, Threat Sheet, placement, combat, media | Later roadmap phases |
| Generic `PublicationOperation` framework | Threat + statblock must prove the seam before extraction |

## §9 Public contracts

### 9.1 Route namespace

The public route contract is frozen as one table. `{operation_id}` on the retry
route identifies the existing stale predecessor; `new_operation_id` in the
request body identifies the child operation. A successful retry response carries
the child operation, not the predecessor.

| Operation | Method and path | Request body | Success response | Success status |
|---|---|---|---|---:|
| Begin | `POST /api/live/threat-drafts/{draft_id}/publication-operations` | `BeginThreatPublicationOperationRequestV1` | `ThreatPublicationOperationResponseV1` | `201` new / `200` exact replay |
| Read | `GET /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}` | none | `ThreatPublicationOperationResponseV1` | `200` |
| Refresh | `POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/refresh` | none | `ThreatPublicationOperationResponseV1` | `200` |
| Cancel | `POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/cancel` | `CancelThreatPublicationOperationRequestV1` | `ThreatPublicationOperationResponseV1` | `200` |
| Retry | `POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/retry` | `RetryThreatPublicationOperationRequestV1` | `ThreatPublicationOperationResponseV1` | `201` new / `200` exact replay |

Every response is the typed `ThreatPublicationOperationResponseV1` envelope,
including expected errors. The route must not expose FastAPI's untyped default
error body as its public contract.

Do not add aliases, hidden mutation endpoints, or a route that automatically chooses current/latest parent.

### 9.2 Begin request

```text
BeginThreatPublicationOperationRequestV1:
  schema: dmb_begin_threat_publication_operation_request_v1
  operation_id
  expected_draft_version
  expected_parent_revision_id
  actor
  operator_note?
```

The client must not send:

- a Threat source snapshot;
- an accepted mechanics locator;
- world/campaign overrides;
- a current-head fallback flag;
- create/connect identity;
- graph assertions or proposal data.

The route path `draft_id` is part of canonical request identity and must be included when computing `request_digest`.

### 9.3 Server eligibility checks

The server loads the committed typed draft and requires:

```text
draft.draft_id == route draft_id
draft.version == expected_draft_version
draft.workflow_state == mechanics_saved
draft.accepted_mechanics_ref != null
draft.accepted_mechanics_ref.to_mechanics_locator() validates exactly
observed_world_graph_head == expected_parent_revision_id
```

`draft.graph_context_snapshot.graph_revision_id` is grounding provenance. It is not a publication-parent fallback and must not replace the caller's expected parent.

### 9.4 Immutable source snapshot

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

- Build only from the server-loaded `ThreatDraftV1`.
- Preserve nested typed shapes and list ordering exactly as alias-serialized by the canonical predecessor models.
- Include all authored concept fields needed for later create/connect review so current-only draft storage cannot erase publication authority.
- Exclude candidate bodies, statblock definitions, rules elements, rendered Markdown, mutable timestamps, candidate workflow lists, and UI state.
- Compute `source_digest` from canonical alias-serialized snapshot JSON using sorted keys, compact separators, UTF-8, and SHA-256.
- Recompute and verify `source_digest` every time an operation is loaded.
- Prove the snapshot's `accepted_mechanics_ref.to_mechanics_locator()` equals the exact locator later consumed by SBW08 binding construction.

Nested wire strictness is part of this contract:

- `ThreatPublicationSourceSnapshotV1` uses `extra="forbid"` and every listed
  field is required on the wire; nullable fields use explicit `null`, and list
  fields use explicit lists rather than model defaults.
- `accepted_mechanics_ref` is loaded first through a publication-owned
  `ThreatPublicationAcceptedMechanicsRefV1` with `extra="forbid"` and mandatory
  wire keys: `schema`, `provider`, `statblock_id`, `revision_id`, `contract`,
  `contract_version`, `definition_digest`, `accepted_from_candidate_id`,
  `accepted_from_draft_version`, and `accepted_at`.
- The raw nested mapping must be checked for those keys before constructing the
  predecessor `AcceptedMechanicsRefV1`; in particular, a missing `provider`
  must reject rather than inherit `AcceptedMechanicsRefV1`'s
  `provider="dungeonmind"` default.
- The strict publication ref must round-trip to the predecessor ref and its
  six-field `MechanicsLocatorV1` without adding mechanics bodies or silently
  repairing omitted fields.

### 9.5 Operation model

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

Required invariants:

- strict schema; unknown fields reject;
- operation ID is UUID or bounded `pubop_...`; path traversal and aliases reject;
- `request_digest` is recomputed from canonical typed begin/retry request identity, including route draft ID;
- timestamps are audit metadata, never identity;
- `ready` has no stale reasons or terminal linkage;
- `stale` has one or more typed reasons and cannot return to `ready`;
- `cancelled` is terminal and requires cancellation actor; it is not active;
- `superseded` is terminal and requires a valid forward link;
- immutable source, source digest, request digest, and expected parent never change after creation.

Suggested stale-reason vocabulary:

```text
draft_version_changed
source_digest_changed
accepted_mechanics_changed
world_or_campaign_changed
graph_parent_changed
```

A missing or unreadable dependency is not a semantic stale reason.

### 9.6 Ledger model and storage

```text
ThreatPublicationLedgerV1:
  schema: dmb_threat_publication_ledger_v1
  draft_id
  active_operation_id?
  operations[]
```

Storage:

```text
publication ledger root: repo_root()
out/threat_publication_operations/<draft_id>/ledger.json
out/threat_publication_operations/<draft_id>/.publication.lock
```

The ThreatDraft store also receives `repo_root()`. The World Graph is a
separate authority: always call
`open_current_world_graph(world_graph_root(), draft.world_id)`. Service
functions accept these roots independently, and tests must provide distinct
temporary repository and World Graph roots so one root cannot accidentally make
the contract pass.

Ledger invariants:

- one draft-scoped ledger is the commit authority;
- maximum 32 operations per draft unless a smaller existing repository bound is deliberately reused and documented;
- operation IDs are unique;
- `active_operation_id` is null or identifies exactly one `ready` or `stale` operation;
- at most one `ready`/`stale` operation exists;
- `cancelled` and `superseded` operations cannot be active;
- supersession links are bidirectional, acyclic, and reference records in the same ledger;
- the new retry operation's source snapshot and source digest exactly equal the stale predecessor's;
- embedded `draft_id` matches directory and route identity;
- duplicate IDs, bad digests, broken links, invalid active pointers, unknown schemas, malformed JSON, or over-bound history fail closed;
- corrupt storage is never auto-repaired or overwritten by begin/retry/cancel.

### 9.7 Lifecycle requests

```text
CancelThreatPublicationOperationRequestV1:
  schema: dmb_cancel_threat_publication_operation_request_v1
  actor
  note?

RetryThreatPublicationOperationRequestV1:
  schema: dmb_retry_threat_publication_operation_request_v1
  new_operation_id
  expected_parent_revision_id
  actor
  operator_note?
```

Refresh has no client-supplied source, locator, or parent override. Read has no freshness side effect.

### 9.8 Response envelope

```text
ThreatPublicationOperationResponseV1:
  schema: dmb_threat_publication_operation_response_v1
  draft_id
  result_label
  operation?
  message?
```

Result labels are a closed typed vocabulary exactly as follows; adding a label
requires a public-contract revision:

```text
publication_ready
publication_stale
publication_cancelled
publication_superseded
publication_busy
publication_input_conflict
publication_parent_mismatch
publication_source_mismatch
publication_history_full
publication_not_found
publication_draft_unavailable
publication_graph_unavailable
publication_storage_unavailable
publication_integrity_failure
publication_invalid_state
```

Routes must not collapse expected conflicts, dependency failures, and integrity failures into one opaque response.

### 9.9 HTTP behavior

| Outcome | Status |
|---|---|
| New begin or new retry operation created | 201 |
| Exact replay, read, refresh, or cancel success | 200 |
| Draft or operation not found | 404 |
| Busy, input conflict, parent mismatch, source mismatch, or invalid terminal transition | 409 |
| Invalid identifier or request contract | 422 |
| Trusted draft/graph dependency temporarily unavailable | 503 |
| Corrupt publication ledger or impossible persisted invariant | 500 |

The typed response body remains authoritative; status code alone is insufficient proof.

## §10 Lifecycle behavior

**Begin**

1. Validate route ID and typed request.
2. Under the draft-scoped publication lock, load and strictly validate the ledger.
3. If `operation_id` exists:
   - identical canonical request digest → return existing exact record;
   - changed request → input conflict, no mutation.
4. If another ready/stale operation is active → busy, no mutation.
5. Load the committed ThreatDraft through its owning store.
6. Validate exact draft identity/version/state and accepted mechanics.
7. Read the trusted current World Graph head.
8. Require exact equality with caller expected parent.
9. Build the typed source snapshot and digests.
10. Append one ready operation and atomically replace the ledger.

An exact replay must return the existing operation before consulting current draft or graph state. It must never re-snapshot.

**Read**

- load and strictly validate ledger;
- return exact operation by ID;
- perform no draft or graph read;
- perform no freshness transition.

**Refresh**

- `ready`: load trusted current draft and graph head;
- exact source and parent match: return ready without semantic write;
- trusted source or parent drift: atomically transition to stale with typed reasons;
- `stale`: return exact stale operation without attempting resurrection;
- `cancelled`/`superseded`: return exact terminal record;
- dependency unavailable or corrupt: typed failure and byte-identical ledger.

**Cancel**

- ready/stale → cancelled; clear active pointer; record actor/note;
- cancelled replay with same request → exact cancelled record;
- cancelled replay with changed request → input conflict;
- superseded → invalid-state conflict;
- no draft, graph, or DungeonMind read.

**Retry**

1. Load and strictly validate the ledger. If `new_operation_id` already exists,
   an identical canonical retry request returns that child record immediately;
   a changed request is an input conflict. This replay check precedes the
   stale-active-slot check because a successful retry has superseded its old
   predecessor.
2. Only the current stale active operation may create a new retry.
3. A new operation ID is required.
4. Load trusted current draft and graph head.
5. Current source snapshot/digest and accepted locator must equal the stale operation's immutable source.
6. Caller-supplied expected parent must equal observed current head.
7. In one atomic ledger replacement:
   - old stale → superseded;
   - `old.superseded_by_operation_id` → new ID;
   - new ready operation supersedes old;
   - `active_operation_id` → new ID.
8. Any source drift rejects and leaves old operation unchanged. The caller must
   cancel that stale operation before beginning a new publication intent from
   the current draft; begin must not implicitly supersede an active stale record.

## §11 Lock, commit, replay, and failure contract

**Lock order**

The implementation must document and test one lock order. Preferred order:

```text
publication ledger lock
→ ThreatDraft store read lock
→ trusted World Graph read
```

No existing path may acquire the publication lock while already holding the ThreatDraft lock. If inspection discovers a reverse acquisition or graph lock cycle, stop rather than improvising.

**Commit point**

Atomic replacement of one draft-scoped `ThreatPublicationLedgerV1`.

Before commit, no publication operation or lineage change exists. After commit, operation authority survives restart while ThreatDraft, accepted mechanics, DungeonMind, and World Graph remain unchanged.

A response failure after a successful ledger write is recovered through exact replay using the same operation ID and request.

**Failure behavior**

```text
draft missing or not mechanics_saved -> no record
version mismatch -> no record
expected parent mismatch -> no record
operation input conflict -> existing record unchanged
active slot busy -> no record
history full -> no record
refresh dependency unavailable -> operation unchanged
ledger/digest corruption -> fail closed; never auto-repair
retry source mismatch -> old operation unchanged; cancel it before a new begin
cancel/retry terminal conflict -> unchanged
atomic write failure -> prior ledger remains authoritative
```

## §12 Identity, fallback, persistence, and predecessor matrices

### Identity matrix

| Identity | Rule | Ambiguity behavior | Fallback? |
|---|---|---|---|
| Operation | Exact validated `operation_id` | Reuse with changed canonical request conflicts | No |
| Draft | Exact route UUID and exact version | Current version drift stales or rejects | No |
| Mechanics | Exact six-field locator inside accepted ref | Changed accepted ref stales/conflicts | No |
| Source | Complete canonical snapshot plus SHA-256 digest | Digest mismatch is integrity failure | No |
| World Graph | Exact expected immutable parent | Changed head stales or rejects | No |
| Actor/note | Audit inputs bound into replay identity | Same-ID change conflicts | No |
| Labels/aliases | Snapshot content only for later review | Never resolve durable identity here | No |
| Retry lineage | Exact old/new IDs and backlinks | Broken or multiple active lineage is corruption | No |

### Fallback matrix

No fallback is permitted to:

- current draft fields;
- another accepted mechanics ref;
- latest statblock revision;
- current/latest graph parent;
- `graph_context_snapshot.graph_revision_id` as publication parent;
- label, alias, slug, or display name;
- a different operation for the same draft;
- direct graph state or overlay.

### Persistence matrix

| Operation | Durable representation | Round-trip guarantee | Replay behavior | Migration rule |
|---|---|---|---|---|
| Begin | Draft-scoped ledger JSON | Exact snapshot/digests/parent/state | Same ID/body returns same record | Strict v1; unknown fields reject |
| Refresh | Atomic ledger replace only on stale transition | Immutable authority preserved | Ready/no drift and stale replay are no-op | Reason vocabulary change requires schema review |
| Cancel | Same ledger | Terminal audit fields exact | Same request idempotent | No uncancel |
| Retry | Same ledger with linked old/new records | Backlinks and active pointer exact | Same new ID/body returns same new record | No silent cross-version upgrade |
| Reload | Strict parser and cross-record validation | Every digest/invariant rechecked | Read-only | Operator repair is separate tooling |

### Predecessor-to-consumer mapping

| Predecessor | Real shape | Snapshot/operation use | Transformation | Required proof |
|---|---|---|---|---|
| `ThreatDraftV1.draft_id`/`version` | UUID string / integer ≥1 | Source identity | Exact copy | Real typed fixture |
| `world_id`/`campaign_id` | Bounded identity strings | Source and graph scope | Exact copy | Mapping test |
| Authored concept fields | Typed nested models/lists/nullability | Immutable source snapshot | Alias-serialized exact copy | Full snapshot equality |
| `workflow_state` | `mechanics_saved` required | Begin eligibility | Validate; do not create new draft state | Negative matrix |
| `accepted_mechanics_ref` | Exact locator + acceptance provenance | Snapshot exact ref | Require non-null; exact copy | Locator equality test |
| `to_mechanics_locator()` | Six exact identity fields | Future SBW08 binding input | Equality proof only; no graph assertion | Compatibility test |
| Current World Graph head | Immutable revision ID | Expected-parent check | Exact equality with request | Parent mismatch/race test |
| Caller request | Route draft ID + op/version/parent/actor/note | Request digest | Canonical typed digest | Tamper/replay test |
| Acceptance operation precedent | Durable claim/resume/conflict patterns | Design precedent | Reuse semantics, not schema/state names | Regression/design inspection |

Invented fixtures that bypass canonical `ThreatDraftV1`, `AcceptedMechanicsRefV1`, `MechanicsLocatorV1`, or World Graph head models do not prove the mapping.

## §13 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected result | Stop condition |
|---|---|---|---|---|
| Snapshot is complete, strict, and digest-bound | models | Full typed round-trip and tamper matrix | Missing/extra/tampered fields reject | Any default/repair of authority |
| Begin writes one exact ready operation | service + ledger | Integration using real typed draft and temp graph | Exact snapshot/ref/parent persists; dependencies unchanged | Partial/reconstructed authority |
| Replay and same-ID conflict are deterministic | service + ledger | Same ID same/different request | Exact record or typed conflict | Second record or silent mutation |
| Parent/source drift is explicit | refresh service | Ordered claim/edit/advance/refresh tests | Stale reasons exact; source/parent unchanged | Silent rebasing |
| Dependency failure cannot invent staleness | service | Failure injection | Typed failure and byte-identical ledger | State change from untrusted read |
| Cancel is terminal and idempotent | ledger | Transition/replay/conflict tests | Active pointer cleared once | Uncancel or external side effect |
| Retry is atomic and lineage-safe | ledger transaction | Concurrency and injected-write tests | One active operation; linked old/new or no change | Orphan or dual-active lineage |
| External authorities stay untouched | service + route | Hash/spy no-mutation proof | Draft/graph bytes identical; zero DungeonMind calls | Any external mutation |
| Route contract is strict and reloadable | FastAPI | Route integration plus app restart | Typed responses and exact reload | Opaque failures or mutation |
| Bounds/corruption fail closed | parser/store | Malformed schema/digest/link/history tests | No overwrite or auto-repair | Corrupt state accepted |
| Predecessor suites remain green | existing contracts | Focused regression commands | No unexplained new failure | Unwaived regression |

Required test names or exact equivalents:

```text
test_begin_rejects_parent_mismatch_without_record
test_begin_rejects_non_mechanics_saved_draft_without_record
test_begin_exact_replay_does_not_resnapshot_current_state
test_begin_same_id_changed_request_conflicts_without_mutation
test_competing_begin_allows_one_active_operation
test_restart_reload_preserves_exact_snapshot_locator_parent_and_digests
test_refresh_marks_graph_parent_changed_without_rebasing
test_refresh_marks_source_drift_without_replacing_snapshot
test_refresh_dependency_failure_leaves_ledger_byte_identical
test_cancel_is_terminal_and_idempotent
test_retry_atomically_supersedes_and_installs_one_active_operation
test_retry_exact_replay_after_supersession_returns_child_before_stale_slot_check
test_retry_source_drift_rejects_without_mutation
test_source_drift_retry_requires_cancel_before_new_begin
test_concurrent_cancel_and_retry_have_one_coherent_winner
test_atomic_write_failure_preserves_previous_ledger
test_all_operations_leave_draft_graph_and_dungeonmind_unchanged
test_storage_roots_are_independently_injected
test_nested_accepted_ref_missing_provider_rejects
test_corrupt_ledger_fails_closed_without_rewrite
```

Required commands:

```bash
uv run pytest -q \
  tests/test_threat_publication_operations.py \
  tests/test_threat_publication_routes.py

uv run pytest -q \
  tests/test_threat_draft_store.py \
  tests/test_statblock_mechanics_acceptance.py \
  tests/test_statblock_binding_graph_contract.py

uv run ruff check \
  apps/live_control_server/models/threat_publication.py \
  apps/live_control_server/services/threat_publication_operations.py \
  apps/live_control_server/routes/threat_publication.py \
  apps/live_control_server/main.py \
  tests/test_threat_publication_operations.py \
  tests/test_threat_publication_routes.py

uv run python -m compileall -q \
  apps/live_control_server/models/threat_publication.py \
  apps/live_control_server/services/threat_publication_operations.py \
  apps/live_control_server/routes/threat_publication.py

git diff --check
git diff --name-only c371d43178a2b83da299319a047f93bae50d0959...HEAD
```

For every required command failure that also occurs on base:

- run the identical command on base and head;
- record exact base/head output and provenance;
- do not call the gate green;
- obtain and name an explicit operator waiver if the failure remains part of acceptance.

## §14 PR description and handback requirements

The implementation PR body must include:

1. §2 mission copied exactly.
2. §2 invariant copied exactly.
3. Each §13 guarantee, owning boundary, produced result, and provenance.
4. Exact implementation base and head SHA.
5. Actual changed paths and focused diff stat.
6. Every required command and exact result.
7. Base/head comparison for any failure.
8. Explicit waivers, or none.
9. Paths outside §7, or none.
10. Stop conditions encountered and their resolution.
11. Confirmation that ThreatDraft, accepted mechanics, DungeonMind, and World Graph remained unchanged.
12. Confirmation that `SBW09b` and `SBW09c` remain false.
13. Confirmation that exact replay does not consult or reconstruct current draft/graph state.
14. Confirmation that the complete handoff matrices were followed without compression.

Required demolition declaration:

```text
Replaced path: ad hoc reconstruction of publication intent from current ThreatDraft/current graph head
Deleted in this PR: no
If no, retained reason: no existing product publication operation exists to delete; adjacent current-state reads remain valid for their current consumers
Named remaining consumer: existing Workbench accepted-mechanics and generic graph-authoring flows
Required deletion owner: SBW09c must remove any temporary statblock-specific publication bypass discovered during implementation
```

## §15 Acceptance rubric

- [ ] Exactly one independently useful capability was delivered: durable no-write publication-operation authority.
- [ ] The invariant holds across begin, read, refresh, cancel, retry, restart, concurrency, and failure sequences.
- [ ] Source snapshot uses real canonical predecessor types and recomputes its digest on load.
- [ ] Expected graph parent is exact and immutable; no current/latest substitution exists.
- [ ] Exact same-ID replay is idempotent and does not re-read mutable draft/graph state.
- [ ] Changed same-ID input conflicts without mutation.
- [ ] One draft has at most one ready/stale active operation.
- [ ] Stale is monotonic and records typed reasons without replacing immutable authority.
- [ ] Retry updates old/new lineage and active pointer in one atomic ledger replacement.
- [ ] Source-drift retry leaves the stale operation active until explicit cancel; a new begin cannot collide with it.
- [ ] Cancel is terminal and idempotent.
- [ ] Dependency failures and corrupt storage do not mutate or auto-repair the ledger.
- [ ] Publication ledger and ThreatDraft use `repo_root()` while World Graph reads use `world_graph_root()` independently in production and tests.
- [ ] The route table freezes every endpoint, body, typed response, stable result code, and HTTP mapping.
- [ ] Nested accepted-mechanics wire fields reject omission before predecessor-model defaults can repair them.
- [ ] ThreatDraft, accepted mechanics, DungeonMind, and World Graph remain unchanged.
- [ ] No create/connect, graph proposal, confirm, commit, verification, or UI contract was introduced.
- [ ] Every changed path is in §7 or a reported bounded exception.
- [ ] PR body records all evidence, provenance, gaps, and waivers truthfully.
- [ ] `SBW09b` and `SBW09c` remain named, unimplemented successors.

## §16 Stop conditions

Stop and report rather than expanding if implementation discovers:

- a need to choose or resolve Threat identity;
- a need to define graph assertions, proposal effects, review packages, confirmation tokens, or commit receipts;
- a need to mutate World Graph, an authored overlay, ThreatDraft, accepted mechanics, or DungeonMind;
- an inability to snapshot later-publication source without copying mechanics;
- an operation state that cannot be expressed honestly before `SBW09b`/`SBW09c`;
- a retry transaction that cannot prove atomic old/new lineage in one ledger authority;
- an unavoidable lock-order cycle with ThreatDraft or graph stores;
- a second active operation that cannot be rejected or serialized;
- a predecessor model mismatch from §12;
- a required path outside §7 and its bounded exception;
- a test that can pass only through current/latest fallback;
- a base failure requiring operator waiver;
- an implementation that needs a GM-facing UI to prove the server contract.

Stop report template:

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

## §17 Named successors

**SBW09b — explicit Threat identity resolution**

Consumes one ready SBW09a operation. Produces a separate immutable resolution record choosing exactly one of:

- create a new Threat identity;
- connect to one exact existing Threat;
- refuse because the match set is ambiguous or unsafe.

It must not mutate the SBW09a source snapshot or expected parent.

**SBW09c — governed preview, confirmation, commit, and verification**

Consumes one ready SBW09a operation plus one exact SBW09b resolution. Constructs the SBW08 external-resource node and binding edge through the existing governed World Graph contribution path, binds confirmation to reviewed effects and exact parent, commits once, and verifies the exact committed revision.

Committed-but-unverified must remain distinct from not committed.

**SBW10a/SBW10b — query, hydration, and projection**

After publication, Hermes and product surfaces can resolve the published Threat, select zero/one/many exact bindings explicitly, hydrate mechanics from DungeonMind by exact locator, and present useful game information without copying mechanics into graph state.
