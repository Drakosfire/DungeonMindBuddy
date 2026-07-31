HANDOFF — PR459 / SBW09a Durable Threat–Statblock Publication Operation

Created: 2026-07-30Status: ACTIVE — dispatch exactly one implementation capability.Canonical handoff path: Docs/Plans/HANDOFF-pr459-sbw09a-durable-threat-statblock-publication-operation.mdImplementation base: f450885493108ce5d0c46b5a0e9d4e42173e3c8c — merged PR #457 / SBW08Suggested branch: feat/sbw09a-durable-threat-publication-operationRepository: Drakosfire/DungeonMindBuddy

Dispatch note: this handoff was prepared against the exact main SHA above. Commit this file unchanged on the implementation branch before code. If implementation authority moves materially beyond this SHA, stop and re-anchor rather than silently adapting.

§0 Capability decomposition decision

Candidate outcome

Independently useful?

Public/durable contract changed?

User or operator surface changed?

Failure model changed?

Independently testable or revertible?

Decision

Claim and persist one publication operation from one mechanics-saved ThreatDraft

Yes

Yes

API only

Yes

Yes

Include

Snapshot exact authored Threat fields and accepted mechanics independently of later draft edits

No alone; required operation authority

Yes

No

Yes

Yes

Include

Detect that the expected World Graph parent has become stale

No alone; required recoverability

Yes

API only

Yes

Yes

Include

Reload, reconcile, and cancel a pre-publication operation

No alone; required state lifecycle

Yes

API only

Yes

Yes

Include

Decide create-new versus connect-existing Threat identity

Yes

Yes

Yes

Yes

Yes

Successor SBW09b

Build or seal a graph contribution/review package

Yes

Yes

Yes

Yes

Yes

Successor SBW09c

Confirm a graph write or record a terminal graph receipt

Yes

Yes

Yes

Yes

Yes

Successor SBW09c

Verify committed Threat/resource/binding effects

Yes

Yes

Yes

Yes

Yes

Successor SBW09c

Hydrate or render exact mechanics

Yes

No new graph write

Yes

Yes

Yes

Successor SBW10a/SBW10b

Add Workbench publication UI

Yes

No

Yes

Yes

Yes

Successor after SBW09b/09c contract is usable

Selected capability: a server caller can begin, reload, reconcile, and cancel one durable Threat/statblock publication operation that is bound to one exact mechanics-saved ThreatDraft snapshot and one expected World Graph parent revision.

Why the included rows share one invariant: they establish one durable operation authority. Claim, exact input snapshotting, reload, stale detection, and pre-side-effect cancellation are not separately useful product outcomes; together they make later identity resolution and governed confirmation restart-safe and idempotent.

Named successors:

SBW09b — create-new versus connect-existing Threat resolution
SBW09c — governed preview/confirm Threat + exact binding commit
SBW10a — Hermes query and exact mechanics hydration
SBW10b — exact compact/full Threat projection

§1 Mission

A caller can begin or resume one server-owned Threat/statblock publication operation from a mechanics-saved ThreatDraft so the exact authored source, exact accepted mechanics, and expected World Graph parent survive restart without recreating mechanics or falsely claiming graph publication.

Invariant

One publication operation ID is immutably bound to one request digest, one exact ThreatDraft publication snapshot, one six-field accepted-mechanics locator, one world/campaign, and one expected World Graph parent revision; identical replay returns that same durable authority, changed input conflicts, graph-head drift becomes explicit stale state, and no state may claim publication without a later exact graph receipt.

Mission falsification test

This is not one slice if implementation must choose or create a Threat node,
prepare or seal graph assertions, ask the GM to confirm, call a graph commit,
record a committed revision, hydrate DungeonMind mechanics, or add product UI.

§2 Context, authority, and boundaries

Field

Required content

Parent authority

Docs/Design/DECISION-statblock-contract-consumer-boundary.md; Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md; Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md; Campaign Supergraph architecture and continuity rules

Repository rules

AGENTS.md; .cursor/rules/external-agent-pr-loop.mdc; .cursor/skills/external-agent-pr-loop/SKILL.md

Base revision

f450885493108ce5d0c46b5a0e9d4e42173e3c8c

Predecessor contract

ThreatDraftV1; AcceptedMechanicsRefV1; MechanicsLocatorV1; SBW08 ExternalResourceV1 and ThreatStatblockBindingV1; current World Graph head/revision contract

Exact input consumed

Server-loaded exact ThreatDraft version with workflow_state=mechanics_saved, its exact accepted_mechanics_ref, and caller-supplied operation_id, expected_draft_version, and expected_parent_revision_id

Owning boundary

DungeonBuddy live-control backend publication-operation model/store/service/routes

Named successor

SBW09b identity resolution

What remains false

No Threat identity decision, graph proposal, review package, confirmation, graph write, receipt, verification, hydration, projection, placement, or combat integration

Explicit non-goals

UI, Hermes tools, DungeonMindServer calls, direct World Graph writes, ThreatDraft schema mutation, copied mechanics, automatic rebase, arbitrary latest fallback

Read authoritative inputs in this order before changing code:

Docs/Design/ARCHITECTURE-campaign-supergraph.md

Docs/Design/STATUS-world-graph-continuity-spine.md

Docs/Design/DECISION-statblock-contract-consumer-boundary.md

Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md

Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md

src/graph_memory/union_supergraph/statblock_binding.py

apps/live_control_server/models/statblock_mechanics_acceptance.py

apps/live_control_server/models/threat_draft.py

apps/live_control_server/services/statblock_acceptance_reconciliation.py

apps/live_control_server/services/threat_draft_store.py

apps/live_control_server/models/extract_promote.py

apps/live_control_server/services/extract_promote.py

Existing focused tests at those boundaries

Authority precedence

1. Current Campaign Supergraph and statblock ownership decisions
2. Active Threat + Statblock tracker and roadmap
3. This checked-in handoff
4. Executable code and tests at the immutable base
5. Older SBW09 omnibus handoff as strategic history only
6. Attached/project-source context and chat summaries

The pre-split Docs/Plans/HANDOFF-sbw09-governed-threat-binding-publication.md is not implementation authority. It combined SBW09a, SBW09b, and SBW09c and must not be copied wholesale into this slice.

Settled boundaries

DungeonMindServer owns:
  statblock contract semantics
  statblock/revision identity
  immutable mechanics persistence
  definition digest

ThreatDraft owns:
  mutable authored concept
  current accepted_mechanics_ref attachment

Publication operation store owns:
  exact pre-publication operation identity
  immutable publication source snapshot
  expected graph parent
  durable phase/checkpoint references
  stale/cancelled/failure state

World Graph owns:
  Threat durable identity
  external-resource node
  ThreatStatblockBinding
  immutable committed revision and head

Graph Review / governed confirmation owns:
  human review and confirmation
  sealed proposal authority
  terminal commit receipt

This slice may read the ThreatDraft and current World Graph head. It writes only its own publication-operation journal.

§3 Observable-path inventory

Observable path

Current behavior

Required behavior after this slice

Same invariant as §1?

Owning boundary

Begin from a mechanics-saved draft

No publication-operation authority exists

Atomically claim one operation with exact source snapshot and expected parent

Yes

service/store

Begin from draft without saved mechanics

No joined workflow

Reject before journal write

Yes

service

Existing operation exact replay

Not defined

Return/resume the same durable operation; do not rebuild from current draft

Yes

service/store

Existing operation ID with changed request

Not defined

Conflict; preserve stored authority unchanged

Yes

service/store

Draft edited after claim

Future publication could drift

Reload uses the frozen source snapshot; current draft edits do not silently alter the operation

Yes

model/store/service

Draft missing after claim

Future workflow could become unrecoverable

Existing operation remains readable from its durable snapshot

Yes

store/service

Expected parent is stale before claim

No publication operation

Reject; create no operation

Yes

service

Graph head advances after claim

No explicit state

Reconcile marks the operation stale; no automatic rebase

Yes

store/service

World Graph unavailable

No operation semantics

Fail closed; do not infer head or use draft graph context as authority

Yes

service

Concurrent begin calls

Not defined

One draft-scoped active slot; exact replay resumes, competing operation is busy

Yes

store

Process restart / hard reload

No operation

Exact JSON round trip and GET reload preserve all identity fields

Yes

store/route

Cancel before graph side effect

Not defined

CAS-bound terminal cancelled; exact mechanics remain saved

Yes

service/store

Duplicate cancel

Not defined

Idempotent when already cancelled

Yes

service/store

Cancel after a future graph side effect

Not implemented in this slice

Contract rule: prohibited once a commit-receipt artifact exists; receipt authority must be reconciled, never cancelled

Yes

model invariant; successor enforcement

Storage unavailable/corrupt

Not defined

Typed failure; no fallback to ThreatDraft, current head, or reconstructed operation

Yes

store/route

Operation history bound

Not defined

Enforce a finite per-draft record bound

Yes

store

UI / Workbench status

No publication UI

Remains unchanged

Yes—explicitly absent

out of scope

No row authorizes identity resolution, proposal preparation, graph confirmation, or publication verification.

§4 Files in scope — allowlist

Action

Path

Purpose: how this establishes or proves §1

Create

apps/live_control_server/models/threat_statblock_publication.py

Strict request/response, source snapshot, operation record, artifact-reference, state, and error contracts

Create

apps/live_control_server/services/threat_statblock_publication_store.py

Bounded durable JSON journal, path safety, draft-scoped locking, CAS transitions, exact reload

Create

apps/live_control_server/services/threat_statblock_publication.py

Begin/resume, exact snapshot, parent check, reconcile-stale, read, and cancel orchestration

Create

apps/live_control_server/routes/threat_statblock_publication.py

Browser-safe begin/read/reconcile/cancel API routes with stable typed failures

Modify

apps/live_control_server/main.py

Mount the new router only

Create

tests/test_threat_statblock_publication_store.py

Store round-trip, lock/CAS, bounds, corruption, path safety, transition invariants

Create

tests/test_threat_statblock_publication_service.py

Exact claim/replay/snapshot/stale/cancel/failure semantics

Create

tests/test_threat_statblock_publication_routes.py

HTTP contract and safe error mapping

Modify

Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md

Record SBW08 merged, SBW09a delivered, and SBW09b as successor

Modify

Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md

Add implementation checkpoint only; do not redesign the roadmap

Bounded discovery exception

Directory: apps/live_control_server/config.py and focused existing test fixtures/helpers
Maximum additional paths: 3
Allowed path kinds:
  - one configuration seam for an injectable publication-operation root;
  - one existing route-registration test;
  - one focused fixture/helper shared by the new tests.
Decision rule:
  Include only when the new operation cannot be tested or mounted through an existing seam.
Required report when a path is added:
  Name the exact missing seam, why the allowlisted files cannot own it, and why it does not add a second capability.

Any UI, src/graph_memory implementation, ThreatDraft model/store mutation, or existing graph prepare/confirm path is outside this exception.

§5 Files and capabilities explicitly out of scope

Path, ownership layer, or capability

Why this slice must not touch or claim it

src/graph_memory/union_supergraph/statblock_binding.py

SBW08 is merged predecessor authority; this slice consumes, not changes, it

graph_memory.kernel.merge_contribution_to_revision and callers

Graph commit belongs to SBW09c

apps/live_control_server/services/extract_promote.py

Existing governed prepare/confirm reference path; do not fork or modify it in SBW09a

apps/live_control_server/models/extract_promote.py

Proposal/receipt contracts are successor inputs, not this operation claim

apps/live_control_server/models/threat_draft.py

Publication state must not be stuffed into mutable draft state

apps/live_control_server/services/threat_draft_store.py

Read-only predecessor in this slice; no publication attachment

apps/live-control-ui/**

Product identity/review flow is not yet designed

DungeonMindServer transport/client

Accepted mechanics are already durable; no provider call is required

Create-new Threat ID generation

SBW09b

Existing Threat search/match/selection

SBW09b

GraphContribution construction

SBW09c

Graph Review preview/confirm

SBW09c

Commit receipt recording through a live graph call

SBW09c

Exact committed revision verification

SBW09c

Hermes hydration / Threat Sheet

SBW10a/SBW10b

Placement / combat

Later roadmap

Automatic parent rebase

Prohibited; new parent requires a new operation ID and fresh review lifecycle

Copied statblock definition or rendered Markdown in operation records

Violates external-mechanics ownership

§6 Implementation contract and conditional matrices

§6.0 Public contract

ThreatPublicationSourceSnapshotV1

The operation freezes only publication-relevant authored fields. It must not copy candidate bodies, accepted mechanics definitions, rendered Markdown, assets, or combat defaults.

schema: dmb_threat_publication_source_snapshot_v1
source_draft_id
source_draft_version
world_id
campaign_id
name
description
threat_kind
intended_roles[]
tags[]
graph_context_snapshot
accepted_mechanics_ref: AcceptedMechanicsRefV1

Rules:

The server builds this snapshot from the exact committed ThreatDraft version.

workflow_state must be mechanics_saved and accepted_mechanics_ref must be present.

The six-field mechanics locator is copied exactly:

provider
statblock_id
revision_id
contract
contract_version
definition_digest

Acceptance provenance fields remain present:

accepted_from_candidate_id
accepted_from_draft_version
accepted_at

source_snapshot_digest is canonical SHA-256 over alias-serialized JSON.

The draft's graph_context_snapshot.graph_revision_id is provenance, not the publication parent. It may be null or older than expected_parent_revision_id.

PublicationArtifactRefV1

This is a pointer-only checkpoint seam for successor-owned durable artifacts.

artifact_kind:
  identity_resolution
  prepared_graph_plan
  graph_commit_receipt
  publication_verification
artifact_id
artifact_schema
artifact_digest: sha256:<64 lowercase hex>
storage_owner

It does not contain the artifact body.

ThreatStatblockPublicationOperationV1

schema: dmb_threat_statblock_publication_operation_v1
operation_id
operation_version >= 1
claim_request_digest
source_snapshot
source_snapshot_digest
world_id
campaign_id
expected_parent_revision_id
last_observed_head_revision_id
authority_state
phase_artifacts[]
terminal_code?
terminal_message?
created_at
updated_at

authority_state reserves the complete publication lifecycle without implementing successor behavior:

awaiting_identity_resolution   # reachable in SBW09a
identity_resolved              # reserved for SBW09b
prepared                       # reserved for SBW09c
confirming                     # reserved for SBW09c
committed_unverified           # reserved for SBW09c
verified                       # reserved for SBW09c
stale                          # reachable in SBW09a
failed                         # reserved; storage/service errors do not fabricate a record
cancelled                      # reachable in SBW09a

Model invariants:

State

Required artifact refs

Forbidden condition

awaiting_identity_resolution

none

any phase artifact

identity_resolved

identity resolution

graph plan/receipt/verification without predecessor refs

prepared

identity resolution + prepared graph plan

commit receipt or verification

confirming

identity resolution + prepared graph plan

verification without receipt

committed_unverified

identity resolution + prepared graph plan + graph commit receipt

cancellation

verified

identity resolution + prepared graph plan + graph commit receipt + verification

missing exact receipt or verification ref

stale

preserve refs already earned; no new refs

automatic parent rewrite

failed

preserve refs already earned

deletion of exact mechanics or receipt evidence

cancelled

no graph commit receipt

any post-commit cancellation claim

SBW09a service code may create or transition only:

<missing> → awaiting_identity_resolution
awaiting_identity_resolution → stale
awaiting_identity_resolution → cancelled
cancelled → cancelled          # idempotent
stale → stale                  # idempotent

Do not add a generic “advance to arbitrary state” API. Successors must add phase-specific transition functions that validate their own artifact contracts.

Requests and responses

BeginThreatStatblockPublicationRequestV1:
  schema: dmb_begin_threat_statblock_publication_request_v1
  operation_id
  expected_draft_version
  expected_parent_revision_id

The client does not send world ID, campaign ID, authored Threat fields, or accepted mechanics. The server loads all of them from the exact draft.

ThreatStatblockPublicationOperationResponseV1:
  schema: dmb_threat_statblock_publication_operation_response_v1
  result_label:
    publication_claimed
    publication_resumed
    publication_stale
    publication_cancelled
  operation
  warnings[]

ReconcileThreatStatblockPublicationRequestV1:
  expected_operation_version

CancelThreatStatblockPublicationRequestV1:
  expected_operation_version

ThreatStatblockPublicationErrorV1:
  schema: dmb_threat_statblock_publication_error_v1
  code
  message
  status_code
  diagnostics[]

Route contract

POST /api/live/threat-drafts/{draft_id}/publication-operations
GET  /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}:reconcile
POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}:cancel

No query-parameter selectors. No client-supplied filesystem path, world root, graph head, locator, or artifact body.

§6.1 Durable storage contract

Default root:
  out/threat_statblock_publication_operations/

Record path:
  <root>/<draft_uuid>/<operation_id>.json

Lock:
  <root>/<draft_uuid>/.publication.lock

History bound:
  maximum 32 operation records per draft

Active slot:
  at most one operation in a nonterminal, pre-publication state for one draft

Safe operation IDs may be UUIDs or pubop_<bounded-safe-token>. Path traversal, separators, control whitespace, and unbounded IDs are rejected.

Lock order when both stores are read:

publication-operation draft lock
→ ThreatDraft store lock/read

Do not nest this lock under acceptance-operation or generation-operation locks. The operation claim must not call DungeonMindServer while holding a lock.

Use the existing atomic JSON writer. A partially written or invalid record is corruption, not a missing operation.

§6.2 Begin/resume behavior

Input:
  draft_id from route
  BeginThreatStatblockPublicationRequestV1

New claim:
  1. Validate draft and operation IDs.
  2. Under the publication draft lock, confirm no conflicting active operation.
  3. Read the exact committed ThreatDraft and require expected_draft_version.
  4. Require workflow_state=mechanics_saved and accepted_mechanics_ref.
  5. Build and digest the exact source snapshot.
  6. Open the draft's exact world and read the current World Graph head.
  7. Require current head == expected_parent_revision_id.
  8. Persist operation_version=1, state=awaiting_identity_resolution.

Exact replay:
  1. Resolve the existing operation before reading the current draft.
  2. Recompute the claim-request digest from route/body identity.
  3. If digest differs, return operation_input_conflict and mutate nothing.
  4. If identical, observe the current graph head.
  5. If head changed and state is awaiting_identity_resolution, CAS to stale.
  6. Otherwise return the existing operation.

The existing operation's source snapshot remains authority after the draft is edited or deleted. Do not reconstruct it from the current draft during replay.

§6.3 Reconcile behavior

Reconcile observes current World Graph authority without preparing or confirming a write.

awaiting_identity_resolution + current head == expected parent
  → unchanged publication_resumed

awaiting_identity_resolution + current head != expected parent
  → CAS transition to stale; record last_observed_head_revision_id

stale
  → unchanged publication_stale

cancelled
  → unchanged publication_cancelled

reserved successor state
  → do not mutate in SBW09a; return existing or a typed unsupported-state conflict

World Graph unreadable/uninitialized returns a typed dependency error and leaves the operation unchanged.

A stale operation is never rebased. The caller must start a new operation ID against a new exact parent revision.

§6.4 Cancellation behavior

Before any graph side effect:
  awaiting_identity_resolution + matching expected_operation_version
  → cancelled, operation_version + 1
  → accepted mechanics remain attached to ThreatDraft
  → no graph or draft mutation

Duplicate cancel:
  cancelled → unchanged, idempotent

Stale operation:
  remains stale; no rewrite to cancelled is required

After a future graph commit receipt exists:
  cancellation is prohibited
  committed authority must be verified/reconciled
  no successor may describe this as “cancelled”

CAS mismatch returns 409 and the current operation without mutation.

§6.5 Failure behavior

draft missing on new claim
  → 404 draft_not_found; no operation

draft version mismatch
  → 409 draft_version_mismatch; no operation

mechanics not saved / missing accepted ref
  → 409 mechanics_not_saved; no operation

expected parent is not current head
  → 409 stale_parent_revision; no operation

world graph missing/unreadable
  → 409 world_not_initialized or 500 world_graph_unreadable; no operation

active operation exists under another ID
  → 409 publication_busy; no second active operation

same operation ID with changed begin request
  → 409 operation_input_conflict; preserve existing record

history bound reached
  → 409 publication_history_full

record corrupt / digest mismatch / path mismatch
  → 500 corrupt_publication_operation; fail closed

storage unavailable
  → 500 publication_storage_unavailable; mechanics and graph unchanged

Never fall back to:

current draft fields instead of the stored source snapshot;

a different accepted mechanics ref;

a newer statblock revision;

the draft's graph-context revision as publication parent;

current graph head as an automatic replacement parent;

a display label or alias as Threat identity;

direct graph-store mutation;

Markdown or preview-union state.

§6.6 Commit model

Commit point in SBW09a:
  successful atomic write of the publication-operation record only

Before operation commit:
  accepted mechanics already exist independently
  no publication operation exists

After operation commit:
  exact pre-publication intent survives restart
  no Threat/resource/binding exists because of this operation

World Graph commit point:
  not present in this slice

Truthful result after operation-store failure:
  mechanics_saved remains true
  graph publication remains false
  caller may retry claim with the same operation ID only when no record exists

§6A State and fallback matrix

Observable path

Loading / initializing

Exact success

Ordinary miss

Dependency unavailable

Integrity / contract failure

Stale / superseded

Retry / replay

New begin

Read exact draft + head

Persist awaiting_identity_resolution

Draft missing → 404

Store/graph unavailable → fail closed

Invalid draft/ref/digest → reject

Parent mismatch → no record

Same ID/body safe

Existing begin

Read record first

Return exact stored operation

Record absent → new-begin path

Graph unavailable leaves record unchanged

Input digest mismatch → 409

Head drift → persist stale

Exact replay safe

Read

Exact record path

Exact round trip

404

Storage unavailable → 500

Corrupt record → 500

Return stored stale state

Safe repeat

Reconcile

Exact operation + current head

Unchanged or stale CAS

404

Graph unavailable → typed error

CAS/digest mismatch → fail closed

Never rebase

Safe repeat

Cancel

Exact operation + version

Terminal cancelled

404

Storage unavailable → 500

Version mismatch → 409

Stale remains stale

Duplicate cancel idempotent

No fallback source is permitted.

§6B Identity matrix

Situation

Required matching rule

Ambiguity behavior

Fallback permitted?

Persistence consequence

Publication operation

Exact operation_id plus claim-request digest

Changed body conflicts

No

Same ID cannot rebind

ThreatDraft

Exact UUID and exact version on first claim

Version mismatch blocks

No

Snapshot preserves source identity

Mechanics

Exact six-field locator from server-loaded AcceptedMechanicsRefV1

Any field mismatch is different mechanics

No latest

Exact ref frozen in snapshot

World

Exact draft.world_id

Missing/unreadable blocks

No default-world substitution

Stored exact world ID

Campaign

Exact draft.campaign_id

Missing/invalid blocks

No

Stored exact campaign ID

Graph parent

Exact caller-provided revision equals current head at claim

Drift is stale

No automatic rebase

Immutable expected parent

Threat node

Not selected in this slice

N/A

No label matching

Remains unresolved for SBW09b

Phase artifacts

Exact ID + schema + digest + owner

Conflicting ref fails

No

Pointer-only durable checkpoints

§6C Persistence and replay matrix

Operation

Durable representation

Round-trip guarantee

Duplicate/replay behavior

Compatibility / migration

Rollback / reversion

Claim

One versioned JSON operation record

Alias-serialized record and all six locator fields equal

Same ID/body resumes; changed body conflicts

New schema only; no legacy import

Delete only in test fixtures; product uses terminal state

Reconcile stale

Same record, incremented operation version

Source snapshot and expected parent unchanged

Exact repeat idempotent

Additive future states must preserve v1 records

No rebase; new operation required

Cancel

Same record, terminal state

Exact source snapshot retained

Duplicate cancel idempotent

Future commit states prohibit cancel

No graph/mechanics rollback

Read after restart

Same file

Exact model equality and digest validation

Safe repeat

Corrupt/unknown schema fails closed

No reconstruction fallback

Future phase checkpoint

Pointer-only artifact ref

ID/schema/digest/owner retained

Phase-specific successor rules

Successor may extend state literals additively

Receipt evidence never deleted to “roll back” truth

§6D Predecessor-to-consumer mapping

Grounding sources

ThreatDraftV1 and GraphContextSnapshotV1
AcceptedMechanicsRefV1 and MechanicsLocatorV1
SBW08 ExternalResourceV1 / ThreatStatblockBindingV1 six-field locator contract
World Graph head manifest / immutable revision identity

Predecessor field / outcome

Real shape and optionality

Operation field / behavior

Transformation

Proof fixture / test

ThreatDraftV1.draft_id

UUID string

source_snapshot.source_draft_id

Exact copy

source snapshot test

ThreatDraftV1.version

int >= 1

source_draft_version

Exact copy after CAS check

version mismatch test

world_id, campaign_id

required bounded IDs

operation world/campaign

Exact copy; never client supplied

scope test

name/description/kind/roles/tags

authored fields

source snapshot

Exact copy

full snapshot equality

graph_context_snapshot

freestanding or pinned pointer set

source snapshot provenance

Exact copy; not parent authority

freestanding/older-context tests

workflow_state

includes mechanics_saved

claim gate

Must equal mechanics_saved

blocked claim test

accepted_mechanics_ref

optional on draft; required when saved

source snapshot

Complete alias-serialized copy

six-field exactness test

accepted provider/statblock/revision/contract/version/digest

exact locator

future SBW08 resource/binding input

No defaulting, normalization, or latest resolution

compatibility test using same_mechanics_locator

current World Graph head revision

exact durable revision ID

last_observed_head_revision_id and claim check

Exact read

stale-parent/reconcile tests

expected parent request

required revision ID

expected_parent_revision_id

Exact copy; immutable

replay/conflict test

§7 Verification ownership map and commands

Guarantee

Owning boundary

Command or manual scenario

Expected evidence

Exact publication source snapshot

service/model

focused service test

Every authored field and full accepted ref equal

Six-field mechanics identity preserved

model/service

compatibility test

same_mechanics_locator true and serialized fields equal

Begin writes only operation journal

service integration

failure/side-effect test

Draft, acceptance record, and World Graph unchanged

Same-ID replay survives draft edits/deletion

service/store

replay test

Stored snapshot unchanged and readable

Changed input cannot rebind operation

service/store

digest conflict test

409 and byte/semantic record unchanged

One active operation per draft

store

concurrent/serial claim test

One claimed operation; competitor busy

Parent mismatch creates no operation

service

stale-at-begin test

409 and no record

Head drift becomes stale

service/store

reconcile test

version increments; expected parent unchanged

No automatic rebase

service/model

stale replay test

new current head recorded only as observation

Cancel is CAS-safe and idempotent

store/service

cancel tests

terminal cancelled; duplicate unchanged

After-receipt cancellation structurally prohibited

model

model invariant test

cancelled + commit receipt rejected

Exact reload after process boundary

store/route

write, reconstruct service/client, GET

full operation equality

Corruption/storage failure fail closed

store/route

malformed file / injected I/O failure

typed 500; no reconstruction

Routes expose no client-controlled roots/locators

route contract

request validation tests

extra fields rejected

SBW08 and acceptance predecessors remain green

predecessor tests

focused regression suite

no contract regression

Run and report every applicable command:

uv run pytest -q \
  tests/test_threat_statblock_publication_store.py \
  tests/test_threat_statblock_publication_service.py \
  tests/test_threat_statblock_publication_routes.py

uv run pytest -q \
  tests/test_statblock_mechanics_acceptance.py \
  tests/test_statblock_acceptance_reconciliation.py \
  tests/test_statblock_binding_graph_contract.py

uv run ruff check \
  apps/live_control_server/models/threat_statblock_publication.py \
  apps/live_control_server/services/threat_statblock_publication_store.py \
  apps/live_control_server/services/threat_statblock_publication.py \
  apps/live_control_server/routes/threat_statblock_publication.py \
  tests/test_threat_statblock_publication_store.py \
  tests/test_threat_statblock_publication_service.py \
  tests/test_threat_statblock_publication_routes.py

uv run python -m graph_memory.union_supergraph.validate --json
git diff --check
git diff --stat f450885493108ce5d0c46b5a0e9d4e42173e3c8c...HEAD -- \
  apps/live_control_server/models/threat_statblock_publication.py \
  apps/live_control_server/services/threat_statblock_publication_store.py \
  apps/live_control_server/services/threat_statblock_publication.py \
  apps/live_control_server/routes/threat_statblock_publication.py \
  apps/live_control_server/main.py \
  tests/test_threat_statblock_publication_store.py \
  tests/test_threat_statblock_publication_service.py \
  tests/test_threat_statblock_publication_routes.py \
  Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md \
  Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md

git diff --name-only f450885493108ce5d0c46b5a0e9d4e42173e3c8c...HEAD

Minimal live proof

Use the existing backend routes; do not build UI for proof.

Existing surface used:
  live-control server API

Smallest scenario:
  1. Use one existing mechanics-saved ThreatDraft.
  2. Read its exact draft version and current exact World Graph head.
  3. POST begin with a fresh operation ID.
  4. Restart the server process.
  5. GET the operation and compare the exact source snapshot/locator/parent.
  6. Reconcile while the parent is unchanged; observe resumed state.
  7. On a disposable test world root, advance head with an unrelated valid contribution.
  8. Reconcile; observe stale state and no draft/mechanics mutation.
  9. Claim a second operation on a fresh fixture draft and cancel it; reload and observe cancelled.

Evidence captured:
  redacted request/response JSON, operation file path relative to repo root,
  exact operation ID, exact parent revisions, and confirmation that the accepted
  mechanics ref remained unchanged.

Do not mutate the operator's live Eldyrwild graph merely to prove stale behavior. Use a disposable world root for that step.

Baseline failure protocol

For any required command failing on base:

run the same command on f450885493108ce5d0c46b5a0e9d4e42173e3c8c and head;

record whether head adds failures;

do not call the gate green;

name any operator waiver explicitly;

distinguish author-local, independently rerun, CI, and manual evidence.

§8 Required implementation handback

The implementation handback must include:

Base SHA f450885493108ce5d0c46b5a0e9d4e42173e3c8c and final head SHA.

Actual changed paths and focused diff stat.

The exact persisted schema with one redacted example record.

State-transition table actually implemented.

Every §7 command and exact result with provenance.

The minimal route-level restart/reload proof or an explicit reason it could not run.

Confirmation that no DungeonMindServer call occurred.

Confirmation that no ThreatDraft, accepted mechanics, graph revision, graph head, corpus file, preview union, or UI state was mutated by operation claim/reconcile/cancel.

Confirmation that only awaiting_identity_resolution, stale, and cancelled are service-reachable in this PR.

Confirmation that no generic arbitrary-state transition API exists.

Confirmation that SBW09b and SBW09c remain false.

Baseline failures and explicit waivers; write none where applicable.

Paths outside §4; write none or include a stop report.

Stop conditions encountered; write none where applicable.

Demolition declaration from §9.

Confirmation that this handoff was implemented without compressed or omitted constraints.

§9 Acceptance rubric

Accept only when every item is true.

Exactly one durable publication-operation capability is delivered.

A new claim freezes the full publication source snapshot and exact accepted mechanics.

The operation ID cannot be rebound through changed request input.

Exact replay reads the operation before consulting mutable draft state.

Draft edits or deletion after claim do not alter or erase the stored snapshot.

New claim requires exact current graph parent and creates no record when stale.

Later graph-head drift becomes explicit stale state without rewriting expected parent.

No automatic rebase exists.

One active publication slot is enforced per draft.

Operation history is bounded.

Cancel is version/CAS-safe, terminal, and idempotent before any graph side effect.

The model forbids cancellation once a graph-commit receipt artifact exists.

Full JSON round-trip survives restart.

Corrupt and unavailable storage fail closed.

No copied mechanics body, rendered Markdown, assets, or combat defaults enter the journal.

No DungeonMindServer call occurs.

No Threat identity is selected or created.

No graph proposal is prepared or sealed.

No graph write or receipt is produced.

No UI path is added.

No unexpected path changed.

Predecessor acceptance and SBW08 tests remain non-regressed.

Tracker/roadmap checkpoint names SBW09b as the next successor.

Demolition declaration

Replaced path:
  None. No durable Threat/statblock publication-operation path exists on base.

Deleted in this PR:
  no

If no, retained reason:
  The mechanics-acceptance journal remains authority for creating and attaching
  immutable mechanics. The extract-promote/worldbuilding prepare-confirm path
  remains the human graph-write reference protocol. SBW09a adds a new operation
  boundary between them; it does not replace either predecessor.

Named remaining consumer:
  Statblock Workbench acceptance uses the acceptance journal.
  Graph Review/worldbuilding confirmation uses extract-promote and the Kernel.

Required deletion owner:
  SBW09c may delete any temporary publication adapter it replaces, but this PR
  must not create one.

§10 Reviewer protocol

Restate the mission and invariant before examining files.

Confirm the diff does not contain identity resolution, graph proposal construction, graph commit, verification, or UI.

Inspect the persisted record before the service code.

Verify the source snapshot copies exact authored fields and the complete accepted mechanics ref.

Verify claim replay checks the stored operation before current draft state.

Verify expected parent is immutable and never rebased.

Inspect lock order, path safety, history bound, active-slot behavior, and atomic writer use.

Inject graph-head drift and prove only operation state changes.

Inject draft edit/deletion and prove the stored snapshot remains authority.

Inject storage corruption and prove no fallback reconstruction.

Verify cancellation cannot erase or contradict future receipt authority.

Re-run predecessor tests and exact diff inventory.

Confirm the successor remains SBW09b, not a hidden continuation inside this PR.

§11 Re-review protocol

Begin from the prior finding ledger.

Prior finding

Claimed fix

Owning files/tests

Verified?

New consequence?

<finding>

<fix>

<paths/tests>

Yes / No

<none or consequence>

For every fix, re-run the entire operation invariant, especially:

same-ID replay;

mutable draft divergence;

graph-head drift;

cancel CAS;

record corruption;

no unauthorized successor behavior.

Do not review only the changed line.

Stop conditions

Stop and report rather than expanding scope when implementation discovers:

SBW08's exact locator or binding contract differs materially from merged f4508854;

the current ThreatDraft no longer contains the exact accepted mechanics authority described here;

another durable publication-operation implementation already exists;

claiming an operation requires changing the ThreatDraft schema/store;

the current World Graph head cannot be read through the Kernel without direct file mutation or client-controlled paths;

identity resolution fields are required for a useful claim;

a graph plan, sealed proposal, confirmation token, contribution, or commit receipt must be created;

a generic arbitrary-state transition API appears necessary;

UI is required to prove the backend operation;

cancellation semantics require a live graph side effect in this slice;

a required path falls outside §4 and the bounded exception;

repository rules or current architecture conflict with this handoff;

a baseline failure requires operator waiver.

Use this report:

Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:

Final dispatch check

§0 records the split from SBW09b and SBW09c.

§1 names one durable operation capability.

Base SHA is immutable and contains merged SBW08.

Source snapshot, operation identity, parent revision, and state ownership are exact.

All observable paths are inventoried.

The allowlist expresses the entire expected diff.

Every state/fallback/identity/persistence/predecessor matrix is complete.

Cancellation is defined both before and after any future graph side effect.

Tests prove behavior at model, store, service, and route ownership boundaries.

Live proof uses only existing backend routes and a disposable world root.

SBW09b and SBW09c remain independently useful successors.

No essential constraint exists only in chat.

Concise handback to the operator

Current main:
  f450885493108ce5d0c46b5a0e9d4e42173e3c8c — SBW08 merged

Selected next slice:
  SBW09a — Durable Threat/Statblock Publication Operation

Why this slice:
  Accepted mechanics and the exact graph binding contract now exist, but no
  restart-safe operation binds them to one future governed publication attempt.

Owning boundary:
  DungeonBuddy live-control backend operation journal

Durable contract impact:
  New versioned publication-operation record and pointer-only future phase refs

User-visible effect:
  API callers can begin, reload, reconcile stale state, and cancel before publish;
  no Workbench UI changes

Failure model:
  exact replay; changed-input conflict; explicit stale; no rebase; mechanics survive

Acceptance proof:
  exact snapshot/reload, stale-head, cancel CAS, corruption, and predecessor tests

Paths retained:
  acceptance journal; extract-promote/Graph Review governed write path

Paths deleted:
  none

Explicitly deferred:
  identity resolution, graph prepare/confirm, receipt/verification, hydration,
  projection, placement, and combat
