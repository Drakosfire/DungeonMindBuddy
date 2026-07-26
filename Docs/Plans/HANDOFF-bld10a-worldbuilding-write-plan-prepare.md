HANDOFF — BLD-10a worldbuilding write-plan contract and prepare service

Created: 2026-07-25Status: ACTIVE — dispatch exactly one implementation capability.Canonical handoff path: Docs/Plans/HANDOFF-bld10a-worldbuilding-write-plan-prepare.mdImplementation base: 86027b17325e0282506eff73aad3bca4f952fd2c — main after PR #394 (BLD-08) mergedRequired predecessors: PR #393 / BLD-07, PR #394 / BLD-08, PR #408 / recap-only Kernel cleanupSuggested branch: agent/bld10a-worldbuilding-write-plan-prepare

This handoff is the complete implementation authority for BLD-10a. Do not compress it into a narrower task brief before dispatch. PR-description completeness and atomic status-document synchronization are not merge gates; runtime behavior, contract correctness, tests, regression safety, and the implementation handback are.

§0 Capability decomposition decision

Candidate outcome

Independently useful?

Public/durable contract changed?

User or operator surface changed?

Failure model changed?

Independently testable or revertible?

Decision

Convert a complete set of reviewed worldbuilding candidate dispositions into one deterministic, head-pinned write plan

Yes

Yes

API only

Yes

Yes

Include

Define a strict request/response contract for node creation, exact existing-node binding, edge acceptance, rejection, and defer

No — required input/output contract for the selected capability

Yes

API only

Yes

Yes

Include

Map explicitly accepted worldbuilding_draft candidates into inert Kernel-shaped contribution assertions without weakening recap promotion rules

No — required transformation for the selected capability

Yes

No

Yes

Yes

Include

Persist a write-plan journal or plan registry

Yes

Yes

Operator/recovery surface

Yes

Yes

Successor, not BLD-10a

Confirm a worldbuilding plan, write a GraphContribution, or advance the World Graph head

Yes

Yes

Yes

Yes

Yes

BLD-10b

Add Graph Review create/bind/reject/defer controls and prepare UX

Yes

Yes

Yes

Yes

Yes

BLD-10c

Automatically resolve identity from labels, aliases, similarity, or first match

Yes

Yes

No

Yes

Yes

Reject

Record durable Kernel identity decisions, merge/split identities, or create redirects

Yes

Yes

Yes

Yes

Yes

Successor; reject from this slice

Seed or restore a missing World Graph head

Yes

Yes

Operator workflow

Yes

Yes

Separate operator capability

Add PDF/OCR, another extraction profile, bulk ingestion, or extraction-quality work

Yes

Yes

Possibly

Yes

Yes

Separate workstreams

Selected capability: an authorized caller can submit complete, explicit review dispositions for every node and edge in one exact reviewable worldbuilding ExtractionRun and receive one deterministic, evidence-preserving, parent-revision-pinned write plan.

Why the included rows share one invariant: the request contract, semantic mapping, exact-run service, deterministic sealing, and HTTP response all establish the same fact: a specific review decision set over a specific source run and graph revision resolves to one inert proposed graph effect and nothing else.

Named successors:

BLD-10b — worldbuilding plan confirm and graph commit

BLD-10c — Graph Review worldbuilding disposition and publication workflow

Optional later plan persistence/recovery if real dogfood shows response-carried plans are insufficient

Identity-decision management and merge/split UI remain separate Kernel/product work

§1 Mission

An authorized caller can convert a complete set of explicit dispositions for one exact reviewable worldbuilding ExtractionRun into a deterministic, source-evidenced, parent-revision-pinned proposed graph contribution so that later confirmation can commit exactly the reviewed effect without repeating identity inference.

Invariant

For one exact worldbuilding ExtractionRun, one exact parent World Graph revision,
and one complete canonical disposition set, the server returns one canonical
worldbuilding write-plan digest and one proposed contribution effect. Missing or
ambiguous decisions, label-based identity inference, invalid evidence, invalid
targets, unresolved accepted edge endpoints, stale parent identity, or altered
candidate/source lineage cannot produce a plan. No BLD-10a code path writes a
GraphContribution, records an identity decision, publishes a revision, or
advances the World Graph head.

Mission falsification test

This is not one slice if implementation must also deliver any of:
- Graph Review controls for creating the disposition request;
- confirmation, contribution-ledger persistence, or graph-head advancement;
- a durable write-plan store or recovery journal;
- automatic identity merging, identity-decision persistence, redirects, split,
  unmerge, or rename behavior;
- World Graph initialization;
- another source adapter, extraction profile, or extraction-quality claim.

§2 Context, authority, and boundaries

Field

Required content

Parent architecture

Docs/Design/ARCHITECTURE-campaign-supergraph.md

Kernel boundary

Docs/Design/CONTRACT-graph-kernel-boundary.md

Product publication reference

Docs/Design/DESIGN-extract-promote-graph-review-bridge.md

Build sequencing context

Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md

Exact-run predecessor

Docs/Plans/HANDOFF-bld07-graph-review-generic-run-handoff.md / PR #393

Worldbuilding extraction predecessor

Docs/Plans/HANDOFF-bld08-worldbuilding-profile-pilot.md / PR #394

Cleanup predecessor

PR #408: recap prepare remains recap-only; no speculative source_domain parameter

Repository rules

AGENTS.md, .cursor/rules/external-agent-pr-loop.mdc, environment rule, existing strict Pydantic/API conventions

Base revision

86027b17325e0282506eff73aad3bca4f952fd2c

Exact input consumed

exact reviewable BLD-08 ExtractionRun; its run-pinned candidate graph and SourceSpanIndex; exact SourceArtifact/revision; exact expected parent revision; complete dispositions

Public output

versioned dmb_worldbuilding_write_plan_v1 response containing a sealed deterministic effect, typed summary, and explicit confirmable=false

Named successor

BLD-10b confirm/commit; BLD-10c Graph Review UX

What remains false

no contribution-ledger write, no World Graph revision, no head advancement, no durable plan registry, no UI disposition controls, no projection/reload of new graph objects

Explicit non-goals

recap prepare/confirm redesign; generic promotion loosening; label/alias fallback; source mutation; corpus mutation; eval-gold changes; PDF/OCR; extraction-quality claims; Hermes tool registration

Authority precedence

1. Docs/Design/ARCHITECTURE-campaign-supergraph.md
2. Docs/Design/CONTRACT-graph-kernel-boundary.md
3. Docs/Design/DESIGN-extract-promote-graph-review-bridge.md
4. This checked-in BLD-10a handoff
5. Canonical current code and owning-boundary tests at the recorded base
6. BLD-07 and BLD-08 handoffs for predecessor behavior
7. Project Sources, local attachments, and chat summaries

This handoff intentionally supersedes the earlier sequence’s implicit assumption that BLD-09 follows BLD-08 before worldbuilding can publish. BLD-09 remains separate source-lineage work; it is not a predecessor for BLD-10a.

Locked ownership decisions

Use the existing extract-promote product boundary. Add the worldbuilding prepare route beneath the existing /api/live/extract-promote router and service. Do not create a second application-level promotion service or a second route family with separate error policy.

Use a distinct inert plan schema. The response must not be a dmb_extract_promote_proposal_v1 package and must not be accepted by the existing /confirm route. BLD-10a prepares a future commit authority; it does not manufacture a currently confirmable recap proposal.

Keep recap behavior unchanged. prepare_extract_promote() remains recap-only and its semantic eligibility remains played_canon plus current authority rules. Do not add source_domain back to that function and do not broaden map_candidate_semantics_to_kernel() to admit worldbuilding_draft.

Add an explicit reviewed-worldbuilding semantic policy. A candidate stamped by the bounded BLD-08 profile may be elevated into an inert accepted assertion only because the request contains a complete explicit operator disposition. This must be a separate code path/policy from recap promotion.

The plan is response-carried, not persisted. Repeating the same request must rebuild the same plan. A plan registry, operation journal, expiry policy, list/read endpoint, cleanup process, or disk artifact is a second capability and is out of scope.

Kernel mutation APIs are prohibited. The implementation may use pure read/classification and deterministic model/factory helpers. It must not call:

merge_contribution_to_revision

publish_world_graph_revision / publish_world_revision

record_identity_decision

merge_identity, split_identity, or unmerge_identity

contribution-ledger persistence

rollback or head mutation APIs

Server-owned authority. The request does not accept worldId, preparedBy, authoredBy, sourceUri, source paths, candidate paths, profile IDs, graph-root paths, or arbitrary principals. These are resolved or fixed by the server.

Read authoritative inputs in this order

Docs/Design/ARCHITECTURE-campaign-supergraph.md

Docs/Design/CONTRACT-graph-kernel-boundary.md

Docs/Design/DESIGN-extract-promote-graph-review-bridge.md

this handoff

Docs/Plans/HANDOFF-bld07-graph-review-generic-run-handoff.md

Docs/Plans/HANDOFF-bld08-worldbuilding-profile-pilot.md

apps/live_control_server/services/promotable_ingest_run.py

apps/live_control_server/services/extract_promote.py

apps/live_control_server/models/extract_promote.py

apps/live_control_server/routes/extract_promote.py

src/graph_memory/candidate_graph_to_contribution.py

src/graph_memory/candidate_semantic_promote_matrix.py

src/graph_memory/extract_promote_proposal.py

src/graph_memory/kernel/contributions.py

existing exact-run, BLD-08 pipeline, recap prepare/confirm, and Kernel-boundary tests

If the base moves, re-anchor only after confirming that these seams and model contracts have not materially changed. A material change is a stop condition, not permission to reinterpret the handoff.

§3 Observable-path inventory

Observable path

Current behavior

Required behavior after BLD-10a

Same invariant?

Owning boundary

Exact run resolution

Worldbuilding runs can be inspected but prepare returns not_promote_eligible

Resolve the exact reviewable run for worldbuilding write-plan preparation without enabling recap confirm

Yes

service resolver

Source and candidate loading

Exact review package loads pinned evidence; recap prepare resolves candidate/source internally

Load the run-pinned candidate graph, SourceArtifact, source revision, and SourceSpanIndex; no browser paths

Yes

service/registry

World Graph parent selection

Recap prepare reads current head; worldbuilding has no prepare

Request must include expectedParentRevisionId; service loads that exact revision and rejects if it is not the current head at admission

Yes

route/service/Kernel read

Disposition admission

No worldbuilding disposition contract

Strict, complete, duplicate-free disposition set covering every candidate node and edge exactly once

Yes

API model/service

Create-new node

Not available

Explicit node create_new maps candidate node ID to the proposed durable node ID; fail if that ID already exists in the pinned revision

Yes

plan builder

Bind-existing node

Not available

Explicit bind_existing requires one exact active canonical target node ID in the pinned revision; no labels, aliases, normalization, or “best match” fallback

Yes

plan builder

Reject node/edge

Worldbuilding remains inspect-only

Explicit reject creates no accepted effect and is retained in rejected plan diagnostics/assertions

Yes

plan builder

Defer node/edge

No contract

Explicit defer creates no accepted effect; deferred node remains an unresolved mention and deferred edge remains an explicit deferred candidate record

Yes

plan builder

Accept relationship

Not available

Explicit edge accept maps only when both endpoints have accepted node dispositions and exact durable IDs; retains edge-native evidence

Yes

plan builder

Semantic elevation

worldbuilding_draft is not recap-promote eligible

Separate reviewed-worldbuilding policy maps explicitly accepted candidates to inert canonical/accepted Kernel-shaped assertions

Yes

semantic mapper

Evidence preservation

BLD-08 validates exact evidence

Every accepted or rejected mapped assertion retains exact run-pinned SourceArtifact/span evidence; no endpoint evidence inheritance

Yes

mapper/plan validator

Plan sealing

No worldbuilding plan

Canonical effect body, canonical decision snapshot, deterministic digest, deterministic plan ID

Yes

plan contract

Repeated prepare

No path

Same run + same expected parent + same disposition set in any order returns the same plan ID, digest, effect, and summary

Yes

plan/service tests

Changed request

No path

Changed target, action, run, source revision, candidate bytes, or parent revision yields a different digest or fails

Yes

plan contract

Stale parent

No worldbuilding path

Stable 409; no plan and no mutation

Yes

service/route

Missing/uninitialized world

Review may diagnose 409 for recap merge

Stable world_not_initialized; no bootstrap and no plan

Yes

service/route

Existing recap prepare/confirm

Governed mutation path

Unchanged behavior and contracts

Yes

regression tests

Existing confirm receives worldbuilding plan

Not applicable today

Reject as invalid request/proposal; never mutate

Yes

confirm route/regression

Unexpected server exception

Existing safe correlation-ID behavior

Same safe 500 boundary for worldbuilding prepare

Yes

route

World store after prepare

No worldbuilding prepare

Head, revisions, contribution ledger, identity decisions, and files are byte-for-byte unchanged

Yes

integration/failure-injection tests

Every row is part of the same capability. Any implementation need for UI, plan persistence, confirm, commit, graph reload, or identity-decision mutation is a split trigger.

§4 Files in scope — allowlist

Action

Path

Purpose: how this establishes or proves §1

Create

Docs/Plans/HANDOFF-bld10a-worldbuilding-write-plan-prepare.md

Complete implementation authority

Create

src/graph_memory/worldbuilding_write_plan.py

Versioned plan contract, disposition validation, deterministic canonicalization/sealing/verification, exact parent-revision mapping, and no-mutation builder

Modify

src/graph_memory/candidate_semantic_promote_matrix.py

Add a separate exact reviewed-worldbuilding semantic mapping; leave recap matrix unchanged

Modify

src/graph_memory/candidate_graph_to_contribution.py

Reuse one evidence/source/assertion mapping authority through a bounded semantic-policy seam; do not duplicate provenance mapping

Modify

apps/live_control_server/models/extract_promote.py

Strict disposition request and write-plan response models

Modify

apps/live_control_server/services/extract_promote.py

Resolve exact run/source/candidate/head, invoke plan builder, map stable errors, and preserve recap path

Modify

apps/live_control_server/routes/extract_promote.py

Add POST /api/live/extract-promote/worldbuilding/prepare with existing safe error boundary

Create

tests/test_worldbuilding_write_plan.py

Pure contract, mapping, determinism, identity, evidence, and no-mutation tests

Modify

tests/test_live_extract_promote_api.py

Route-level exact-run, stale, malformed, confirm-rejection, regression, and world-store immutability proofs

Modify if required

tests/test_graph_kernel_boundaries.py

Prove legal imports and absence of application imports from internal world-store modules

Modify if required

tests/test_graph_kernel_public_api.py

Only if a pure read/model helper must be exported from graph_memory.kernel; no mutation API changes

Bounded discovery exception

Directory:
  tests/

Maximum additional paths:
  2

Allowed path kinds:
  Existing focused tests that own exact-run resolution or candidate semantic mapping.

Decision rule:
  Add only when an existing test file is the owning regression boundary and
  duplicating the proof in the new test would miss the real caller.

Required report when a path is added:
  Name the exact guarantee, why the existing file owns it, and why the change
  does not expand product capability.

No frontend path is allowed. No graph-store implementation path is allowed. No plan/roadmap/status synchronization path is required for merge approval.

If implementation requires any other production path, stop and report it before changing the file.

§5 Files and capabilities explicitly out of scope

Path, ownership layer, or capability

Why this slice must not touch or claim it

apps/live-control-ui/**

Graph Review disposition and prepare UX is BLD-10c

Existing /api/live/extract-promote/confirm contract

BLD-10a must not make worldbuilding confirmable

src/graph_memory/kernel/merge.py and publication/storage code

Graph mutation is BLD-10b

src/graph_memory/world_supergraph/**

Internal store is not an application contract and must not be written

Contribution ledger files or stores

No plan persistence or contribution persistence

Identity-decision stores and APIs

Explicit request dispositions are plan input, not durable identity decisions

src/graph_memory/kernel/identity_decisions.py or equivalent

No decision recording

Identity merge/split/redirect code

Separate identity-management capability

prepare_extract_promote() signature and recap source_domain="recap" behavior

PR #408 deliberately removed speculative coupling

Broad loosening of map_candidate_semantics_to_kernel()

Recap promotion must remain played-canon only

New generic “source domain” abstraction

BLD-10a uses an explicit worldbuilding path, not a speculative generic parameter

Workspace document editing/commit

BLD-05/06 predecessor

Extraction prompts, profiles, model calls, or BLD-08 bounds

Input is an existing reviewable run

PDF/OCR and BLD-09

Separate source lineage

Corpus or source mutation

The plan reads immutable source evidence only

Eval gold, quality reports, or model-quality claims

BLD-10a proves deterministic review-to-plan plumbing

World Graph bootstrap/restore

Missing head fails closed

Hermes tool code

Later consumer of the same governed path

Plan list/read/delete/expiry/recovery UI

Persistent plan management is a successor

Nearby work is not authorization. Do not add a small UI, CLI, temporary plan file, or debug endpoint “just for dogfood.”

§6 Implementation contract and conditional matrices

6.0 Public HTTP contract

Endpoint

POST /api/live/extract-promote/worldbuilding/prepare

No query parameters.

Request schema

{
  "schema": "dmb_worldbuilding_write_plan_prepare_request_v1",
  "runId": "exact-extraction-run-id",
  "expectedParentRevisionId": "exact-world-graph-revision-id",
  "dispositions": [
    {
      "assertionId": "candidate-node-or-edge-id",
      "decision": "create_new | bind_existing | accept | reject | defer",
      "targetNodeId": "required-only-for-bind_existing"
    }
  ]
}

Strict rules:

extra="forbid" at every model level.

runId and expectedParentRevisionId are required bounded nonblank strings.

dispositions must be non-empty.

assertionId must be nonblank and unique.

targetNodeId:

required for bind_existing;

prohibited for every other decision.

The server resolves candidate kind:

node permits create_new, bind_existing, reject, defer;

edge permits accept, reject, defer;

any other decision/kind pairing is 422.

The request must cover every candidate node and edge in the exact candidate graph exactly once.

Omission is never interpreted as reject, defer, or accept.

Unknown IDs, duplicate IDs, missing IDs, and IDs for beats or non-candidate objects fail.

Request order carries no meaning.

Response schema

{
  "schema": "dmb_worldbuilding_write_plan_v1",
  "version": 1,
  "planId": "worldbuilding-write-plan:<digest-prefix>",
  "planDigest": "sha256:<canonical-effect-digest>",
  "decisionDigest": "sha256:<canonical-disposition-digest>",
  "worldId": "eldyrwild",
  "parentRevisionId": "exact-revision-id",
  "runId": "exact-extraction-run-id",
  "sourceDomain": "worldbuilding",
  "sourceArtifactId": "exact-source-artifact-id",
  "sourceRevisionId": "sha256:<source-digest>",
  "extractionProfile": "worldbuilding_shepherds_flock_v0@0.1",
  "candidatePreviewId": "exact-preview-id",
  "candidateSchema": "dmb_candidate_graph_preview_v0",
  "candidateVersion": "exact-version",
  "effect": {
    "contributionMeta": {},
    "acceptedProposals": [],
    "rejectedAssertions": [],
    "unresolvedMentions": [],
    "deferredCandidateIds": [],
    "nodeIdMap": {},
    "identityOutcomeSnapshot": {},
    "decisionSnapshot": []
  },
  "summary": {
    "createNewNodeCount": 0,
    "bindExistingNodeCount": 0,
    "acceptedEdgeCount": 0,
    "rejectedCandidateCount": 0,
    "deferredCandidateCount": 0,
    "acceptedAssertionCount": 0
  },
  "diagnostics": [],
  "confirmable": false,
  "confirmableReason": "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
}

The exact field casing follows existing Pydantic camel-case behavior. The Python contract should use snake_case model fields.

effect is the future BLD-10b authority. Presentation summary and diagnostics are derived data. The browser must not be expected to parse effect to render controls in BLD-10a.

6.1 Canonical disposition semantics

Node: create_new

Candidate must be a node in the exact run.

Candidate node ID becomes the proposed durable node ID.

The pinned parent revision must not already contain that node ID as an active node, redirected source, provisional node, rejected identity, or merged-away identity.

No alternative ID is minted.

No label or alias search substitutes another node.

Pure Kernel identity classification may run for warnings only. It cannot override the explicit disposition.

nodeIdMap[candidateNodeId] = candidateNodeId.

Accepted node assertion uses:

exact source evidence;

source_domain="worldbuilding";

acceptance_state="accepted";

identity_resolution_outcome="created_new";

reviewed-worldbuilding semantic mapping.

Potential same-label or alias rivals may be included as deterministic warnings, but they do not silently bind or block an explicit create unless the exact proposed node ID conflicts.

Node: bind_existing

Candidate must be a node.

targetNodeId is required.

Target must exist in the exact pinned parent revision.

Target must be active and canonical:

no redirected source ID;

no provisional identity;

no rejected identity;

no merged-away identity.

Candidate type must map to the same Kernel object-kind family as the target. A mismatched type fails; no cross-kind override in BLD-10a.

Label, alias, similarity, normalization, and automatic identity classification are diagnostics only.

nodeIdMap[candidateNodeId] = targetNodeId.

Do not emit a competing full node assertion for the target.

Reuse the existing connect-existing support mapping:

source-backed summary/attribute support;

safe aliases only under existing alias ownership rules;

exact evidence;

identity_resolution_outcome="human_override".

The target node is not mutated in BLD-10a; the assertion is only part of the inert effect.

Node or edge: reject

Creates no accepted graph effect.

If the existing mapping can produce a rejected assertion without weakening semantic/evidence checks, include it in rejectedAssertions.

At minimum, the canonical decision snapshot and summary must retain the rejection.

Rejection is distinct from defer.

Node: defer

Creates no accepted graph effect.

Add one unresolved mention carrying:

candidate ID;

label;

mapped object kind;

aliases;

exact evidence reference IDs;

identity_resolution_outcome="deferred_by_operator";

deterministic diagnostic operator_disposition:defer.

Do not mint a provisional durable node.

Do not record an identity decision.

Edge: accept

Candidate must be an edge.

Edge must have its own valid evidence; endpoint evidence may not be inherited.

Both candidate endpoints must have node dispositions of create_new or bind_existing.

Exact durable endpoint IDs are derived from nodeIdMap.

If either endpoint is rejected, deferred, missing, or otherwise unmapped, fail the whole prepare request with edge_endpoint_unresolved.

Preserve exact predicate and direction from the candidate.

Reuse current candidate-edge-to-assertion mapping with reviewed-worldbuilding semantics and exact endpoint overrides.

No label-first endpoint binding.

No acceptance of an edge whose endpoint IDs are not in the exact candidate graph.

Edge: defer

Creates no accepted graph effect.

Include edge ID in deferredCandidateIds.

Preserve the explicit defer in decisionSnapshot.

Do not convert a deferred edge into an unresolved node mention.

6.2 Reviewed-worldbuilding semantic mapping

Do not loosen the existing recap policy.

Add a separate mapping whose input is exactly:

canon_state: worldbuilding_draft
authority_state: system_derived
evidence_role: source_evidence
lifecycle_state: candidate | validated
visibility_state: gm_private | player_visible | spoiler_sensitive
proposed_action: create | anchor
explicit disposition: accepted create_new | bind_existing | edge accept

It maps accepted write-plan assertions to:

canon_state: canonical
approval_state: accepted
epistemic_kind: source_derived_candidate
visibility: existing gm/player mapping
source_domain: worldbuilding

This is an inert intended effect, not proof that the graph already contains canonical truth.

Rejected mapping uses acceptance_state="rejected". Deferred objects do not use the accepted semantic mapper.

The implementation must reuse existing evidence payload, SourceArtifact payload, assertion ID, alias safety, predicate, and source revision code. Duplicating those mapping rules in worldbuilding_write_plan.py is a stop condition. Introduce the smallest explicit policy seam in candidate_graph_to_contribution.py.

6.3 Deterministic plan construction

Canonical decision snapshot:

[
  {
    assertion_id,
    candidate_kind: node | edge,
    decision,
    target_node_id: exact string or null
  },
  ...
]

Sort by (candidate_kind, assertion_id).

Normalize strings once.

Reject duplicate IDs before canonicalization.

decisionDigest is SHA-256 over canonical JSON of the complete decision snapshot.

Build the effect using deterministic assertion and contribution helpers.

The effect must not contain current time, random UUIDs, filesystem paths supplied by the caller, mutable diagnostics, or response-order artifacts.

planDigest is SHA-256 over canonical JSON of the complete sealed effect plus exact run/source/candidate/parent identity and decision snapshot.

planId = "worldbuilding-write-plan:" + first 24 hexadecimal characters of planDigest without the sha256: prefix.

Diagnostics and presentation summary do not affect plan identity.

The proposed contribution metadata must use:

source_kind="source_extraction";

exact SourceArtifact/revision;

exact extraction profile;

exact campaign scope or null from the run;

server-owned authored_by="live_control:worldbuilding_write_plan".

Do not include produced_at in the sealed effect. BLD-10b owns commit-time contribution materialization. If a typed GraphContribution is built transiently, use a fixed non-authoritative value or strip produced_at before sealing; it must not make repeated prepare nondeterministic.

6.4 Exact-run and evidence admission

The service must:

Resolve the exact run through the canonical BLD-03/07 registry seam.

Require:

status reviewable;

source_domain == "worldbuilding";

profile exactly worldbuilding_shepherds_flock_v0@0.1;

semantic authority compatible with BLD-08 worldbuilding_draft;

null session;

candidate graph and source-span-index components present and valid.

Load candidate bytes and SourceArtifact bytes from server-owned resolved paths only.

Re-run typed candidate validation and the profile post-extraction validator.

Verify:

exact SourceArtifact ID;

exact source revision/digest;

all accepted/rejected mapped assertions use only the run-pinned artifact;

every span exists in the run-pinned SourceSpanIndex;

anchor quotes still validate under the existing evidence policy;

no multi-artifact candidate graph.

Reject any request that would “repair” missing evidence or substitute endpoint evidence.

Never derive source paths, candidate paths, scope, profile, or artifact IDs from the request.

6.5 Parent revision and identity admission

The service must:

Open the server-owned world ID.

Require an initialized, readable World Graph.

Compare current head ID with expectedParentRevisionId.

If unequal, return stable 409 stale_parent_revision; do not build a plan against a different head.

Load the exact expected revision and resolve all bind_existing targets against that revision.

Do not infer the current revision when the request omits the pin; omission is request validation failure.

The plan remains valid only for the sealed parent revision. BLD-10b will re-check at confirm.

6.6 Full implementation contract

Input:
  exact runId
  exact expectedParentRevisionId
  complete explicit disposition for every exact candidate node and edge
  server-resolved SourceArtifact, source revision, candidate graph, span index,
  profile, world ID, and server principal

Output:
  one dmb_worldbuilding_write_plan_v1 response containing:
  - deterministic plan ID and digests;
  - exact run/source/profile/candidate/parent identity;
  - canonical decision snapshot;
  - Kernel-shaped proposed contribution effect;
  - explicit rejected/deferred outcomes;
  - derived summary/diagnostics;
  - confirmable=false.

Invariant:
  same invariant as §1.

Failure behavior:
  malformed request → 422 invalid_request
  unknown run → existing exact-run not-found behavior
  non-reviewable run → 422 run_not_reviewable
  non-worldbuilding run → 422 worldbuilding_run_required
  wrong profile/version → 422 unsupported_worldbuilding_profile
  source/candidate/span mismatch → 422 or 409 using existing safe lineage errors
  world missing → 409 world_not_initialized
  expected parent != current head → 409 stale_parent_revision
  incomplete/duplicate/unknown dispositions → 422 invalid_disposition_set
  invalid decision for candidate kind → 422 invalid_disposition
  bind target missing/noncanonical/type mismatch → stable 409/422 target error
  create-new exact ID conflict → 409 new_node_id_conflict
  accepted edge endpoint unresolved → 422 edge_endpoint_unresolved
  mapping/evidence failure → fail closed; no plan
  unexpected exception → safe 500 + correlation ID
  any failure → no world-store mutation

Replay / idempotency:
  same run + same source/candidate bytes + same expected parent + same complete
  disposition set, regardless of request order → byte-equivalent authority fields,
  same decisionDigest, planDigest, planId, effect, and summary
  changed disposition/target → new decision and plan digest
  changed run/source/candidate/profile/parent → new plan or fail
  retry after response loss → recompute same plan; no registry lookup and no write
  duplicate request → same response authority; no new artifact

Trust boundary:
  Verifies:
  - exact run and run components;
  - source/candidate/profile/scope/evidence integrity;
  - complete explicit review decisions;
  - exact target IDs against exact parent revision;
  - edge endpoint closure;
  - deterministic effect and digest;
  - no mutation.

  Records or trusts without proving:
  - the operator's semantic judgment that create/bind/accept/reject/defer is correct;
  - the authored lore's creative truth;
  - whether an intentional same-label create is desirable.

  Rejects:
  - browser paths, world IDs, profiles, principals, or source identity;
  - label/alias fallback;
  - incomplete decisions;
  - implicit defaults;
  - stale parents;
  - unsupported worldbuilding semantics;
  - mutation.

Commit point

Not applicable — BLD-10a has no irreversible or durable graph commit point.
The only observable output is a response-carried inert plan.

§6A State and fallback matrix

Observable path

Loading or initializing

Exact success

Ordinary miss

Dependency unavailable

Integrity or contract failure

Stale or superseded

Retry or replay

Exact run resolution

Resolve registry entry and components

Exact reviewable BLD-08 run

404 exact run missing

Stable service error

Fail closed; no path fallback

Non-reviewable/superseded rejects

Retry same exact ID

World head

Open server-owned world

Exact expected parent is current and readable

world_not_initialized 409

world_unreadable stable error

Fail closed

stale_parent_revision 409

Refresh status and resubmit explicit pin

Candidate/source

Load server-owned resolved files

Exact bytes/digests/spans

Component missing rejects

Stable unavailable error

Mismatch/false anchor/multi-artifact rejects

Changed run creates different input

Retry same exact run

Dispositions

Validate complete exact set

One decision per node/edge

Missing decision is not a default; reject

N/A

Unknown/duplicate/kind mismatch rejects

Candidate set drift rejects

Same canonical set is idempotent

Bind existing

Exact target lookup in pinned revision

Active canonical same-kind target

Target missing rejects

N/A

Redirect/provisional/rejected/merged/type mismatch rejects

Parent mismatch rejects earlier

Resubmit after explicit re-review

Create new

Exact candidate ID check

ID absent; deterministic proposed ID

N/A

N/A

Existing/redirected/provisional ID conflicts

Parent mismatch rejects earlier

Resubmit after explicit re-review

Accept edge

Resolve endpoints from accepted node dispositions

Exact IDs + exact predicate/evidence

No implicit edge acceptance

N/A

Missing/deferred/rejected endpoint rejects

Candidate/parent drift rejects

Correct dispositions and retry

Plan sealing

Canonicalize effect

Stable plan/digests

N/A

N/A

Serialization/verification failure rejects

Changed inputs produce new plan

Recompute same plan

Existing confirm

N/A

Recap proposals unchanged

Worldbuilding plan rejected

Existing behavior

Must never accept plan schema

Existing behavior

No BLD-10a confirm retry

No fallback may substitute “latest run,” current head without an explicit pin, label matching, alias matching, normalized keys, or another source artifact.

§6B Identity matrix

Situation

Required matching rule

Ambiguity behavior

Fallback permitted?

Persistence consequence

Candidate identity

Exact candidate node ID from exact run

Unknown/duplicate fails

No

Plan only

create_new durable ID

Exact candidate node ID

Any exact-ID occupancy/conflict fails

No alternate minting

Proposed map only; no node written

bind_existing target

Exact active canonical target node ID in exact parent revision

Missing, redirect, provisional, rejected, merged-away, or type mismatch fails

No label/alias/similarity fallback

Proposed map only; no decision written

Label or alias

Diagnostics only

May report rivals

No binding fallback

None

Normalized key

Prohibited as authority

N/A

No

None

Edge endpoint

Exact candidate endpoint → exact nodeIdMap value

Missing mapping fails whole prepare

No

Plan only

Rename

Exact durable target ID remains the request authority for the pinned revision

If later head changes, BLD-10b must reject stale plan

No rebinding

None in BLD-10a

Deletion

Target absent from pinned revision fails

N/A

No tombstone fallback

None

Rebinding

Requires a changed disposition and therefore a new digest

Silent rebind prohibited

No

New inert plan only

Identity decision record

Prohibited

N/A

No

No record

Same-label intentional create

Explicit create_new is retained; rivals may be warnings

No auto-bind

No fallback

Proposed node only

First-win matching is prohibited. Display labels never substitute for durable identity.

§6C Persistence and replay matrix

Operation

Durable representation

Round-trip guarantee

Duplicate or replay behavior

Compatibility or migration

Rollback or reversion

Prepare request

None beyond caller/request logs

Strict request parses to same canonical disposition snapshot

Same request recomputes same plan

New v1 API; no legacy compatibility body

No write

Write plan

Response-carried dmb_worldbuilding_write_plan_v1

Model dump/parse preserves effect and digests exactly

Same input returns same authority fields

BLD-10b must consume v1 explicitly; existing confirm rejects

Discard response

Proposed contribution effect

Inert JSON inside plan

Exact canonical effect survives round trip

Recompute, do not append

Reuses Kernel assertion/contribution field vocabulary

Discard response

World Graph

No representation written by BLD-10a

Head/revision/ledger bytes unchanged

Repeated prepare remains read-only

Recap graph remains compatible

Not applicable

Identity state

No decisions or redirects written

Unchanged

Repeated prepare unchanged

Existing identity store untouched

Not applicable

A persistent plan artifact discovered as necessary is a stop condition and successor, not an incidental file write.

§6D Predecessor-to-consumer mapping

Grounding sources

- Exact BLD-03/07 ExtractionRun and reviewable-run resolver
- dmb_candidate_graph_preview_v0 typed candidate graph
- BLD-08 worldbuilding_shepherds_flock_v0@0.1 semantic defaults and validator
- SourceArtifact + run-pinned SourceSpanIndex
- Graph Kernel GraphContributionAssertion vocabulary and deterministic ID helpers
- Existing extract-promote canonical JSON/digest conventions

Predecessor field or outcome

Real shape and optionality

Consumer field or behavior

Transformation

Proof fixture or test

ExtractionRun ID

exact nonblank ID

runId

Exact registry lookup; no latest

route/service test

Run status

enum; must be reviewable

admission

Non-reviewable rejects

route test

Source domain

worldbuilding

sourceDomain and evidence mapping

Exact equality

plan test

Profile

worldbuilding_shepherds_flock_v0@0.1

extractionProfile

Exact qualified ID

plan/service test

SourceArtifact ID

exact ID

plan/source/evidence

Preserve exactly

lineage test

Source revision

sha256 digest

sourceRevisionId

Verify bytes; preserve exact

mismatch test

Candidate preview ID/schema/version

exact fields

plan identity

Preserve exactly

round-trip test

Candidate node ID

exact stable candidate ID

disposition ID and proposed new ID/map key

No label conversion

create/bind tests

Candidate edge ID

exact stable candidate ID

disposition ID

No index selection

edge tests

Candidate semantic state

worldbuilding_draft, system_derived, source evidence, null session

reviewed-worldbuilding mapper

Explicit accepted disposition elevates inert assertion only

semantic-policy test

Node evidence refs

exact artifact/span refs

assertion provenance

Reuse current mapper

evidence test

Edge evidence refs

edge-native exact refs

relationship provenance

No endpoint inheritance

negative pipeline test

Existing World Graph target

exact node ID in pinned revision

targetNodeId / nodeIdMap

Exact lookup and kind check

bind tests

Kernel assertion IDs

deterministic semantic IDs

accepted/rejected effect

Reuse build_assertion/mapping helpers

determinism test

Existing recap promote proposal

dmb_extract_promote_proposal_v1

existing confirm only

No transformation from worldbuilding plan

confirm rejection test

Worldbuilding write plan

new dmb_worldbuilding_write_plan_v1

BLD-10b future input

Distinct schema; no current confirm

route/model test

Invented “close enough” fixtures are not sufficient. Tests must construct a canonical reviewable ExtractionRun using the same registry/component paths as production or reuse the existing BLD-08 exact-run fixture helpers.

§7 Verification ownership map and commands

Guarantee

Owning boundary

Command or scenario

Expected evidence

Request strictness and complete dispositions

Pydantic models + route

focused API tests

422 for extra, blank, duplicate, missing, unknown, invalid kind/action, invalid target field

Reviewed-worldbuilding semantic policy is separate

semantic mapper

unit tests

BLD-08 semantics accepted only by new mapper; recap mapper still rejects worldbuilding_draft

Evidence/source mapping is shared

candidate mapping

unit tests/diff inspection

exact artifact/span payload; no duplicated evidence builder

Create-new mapping

plan builder

unit tests

candidate ID mapped to itself; exact-ID conflicts reject

Bind-existing mapping

plan builder against exact revision

unit tests

exact canonical same-kind target accepted; alias-only/missing/redirect/type mismatch reject

Edge endpoint closure

plan builder

unit tests

accepted edge uses exact mapped endpoints; rejected/deferred endpoint blocks accepted edge

Edge-native evidence

plan builder

unit/integration test

empty/invalid edge evidence fails; endpoint citations never substituted

Complete deterministic effect

plan contract

repeat/permutation tests

same request in different order yields identical plan ID/digests/effect/summary

Changed decision changes identity

plan contract

mutation tests

changed action/target/parent/run changes digest or fails

Exact run/source/profile admission

service

route integration tests

only exact reviewable BLD-08 worldbuilding run prepares

Stale parent

service/route

route test

409, no plan, no mutation

Safe public errors

route

forced exception test

generic 500 + correlation ID; no raw exception

No graph mutation

world-store integration

before/after tree and content digest + monkeypatch mutation APIs

head/revisions/ledger/identity files unchanged; mutation functions never called

Existing confirm rejects plan

confirm route

route regression

422/invalid proposal; no head change

Existing recap path unchanged

service/Kernel regression

current recap prepare/confirm tests

existing behavior green

Legal Kernel boundary

import boundary tests

boundary suite

no app imports from internal world-store modules

Scope

diff inspection

name-only/stat commands

only §4 paths or reported bounded discovery

Required commands

Run from repository root unless noted:

uv run pytest \
  tests/test_worldbuilding_write_plan.py \
  tests/test_live_extract_promote_api.py \
  tests/test_promotable_ingest_run.py \
  tests/test_worldbuilding_profile_pipeline.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_graph_kernel_boundaries.py \
  tests/test_graph_kernel_public_api.py \
  -q --tb=line

uv run ruff check \
  src/graph_memory/worldbuilding_write_plan.py \
  src/graph_memory/candidate_semantic_promote_matrix.py \
  src/graph_memory/candidate_graph_to_contribution.py \
  apps/live_control_server/models/extract_promote.py \
  apps/live_control_server/services/extract_promote.py \
  apps/live_control_server/routes/extract_promote.py \
  tests/test_worldbuilding_write_plan.py \
  tests/test_live_extract_promote_api.py

git diff --check
git diff --stat 86027b17325e0282506eff73aad3bca4f952fd2c...HEAD -- \
  Docs/Plans/HANDOFF-bld10a-worldbuilding-write-plan-prepare.md \
  src/graph_memory/worldbuilding_write_plan.py \
  src/graph_memory/candidate_semantic_promote_matrix.py \
  src/graph_memory/candidate_graph_to_contribution.py \
  apps/live_control_server/models/extract_promote.py \
  apps/live_control_server/services/extract_promote.py \
  apps/live_control_server/routes/extract_promote.py \
  tests/test_worldbuilding_write_plan.py \
  tests/test_live_extract_promote_api.py \
  tests/test_graph_kernel_boundaries.py \
  tests/test_graph_kernel_public_api.py

git diff --name-only 86027b17325e0282506eff73aad3bca4f952fd2c...HEAD

The focused pytest command is a merge gate. Splitting it into many smaller green commands does not excuse a failing combined run.

Required adversarial tests

At minimum, tests must prove all of the following:

Same dispositions in reverse/random order produce identical authority fields.

Missing one node disposition fails.

Missing one edge disposition fails.

Duplicate disposition fails.

Unknown candidate ID fails.

Node with edge-only accept fails.

Edge with node-only create_new or bind_existing fails.

targetNodeId absent for bind fails.

targetNodeId supplied for any other action fails.

Create-new exact candidate ID already in head fails.

Bind target missing fails.

Alias/label-only plausible target does not bind.

Redirected target ID fails and reports the canonical ID only as diagnostic.

Provisional/rejected/merged-away target fails.

Kind mismatch fails.

Accepted edge with rejected endpoint fails.

Accepted edge with deferred endpoint fails.

Accepted edge with both endpoints accepted maps exact IDs and direction.

Empty/invalid edge evidence fails and is not inherited.

False anchor or wrong artifact fails.

Session-bearing worldbuilding candidate fails.

Unsupported profile fails.

Recap run fails worldbuilding_run_required.

Stale expected parent fails 409.

Missing world head fails 409 without bootstrap.

Same request after response loss recomputes same plan.

Changed bind target changes decision and plan digest.

Changed expected parent changes plan or fails stale.

World store and contribution ledger are byte-for-byte unchanged.

Mutation APIs are not called.

Existing /confirm rejects the worldbuilding plan.

Existing recap prepare and confirm tests remain green.

Minimal live proof

Not required as a merge gate — BLD-10a has no user-facing controls and no
durable mutation. The owning proof is the real HTTP route over a canonical
registered ExtractionRun plus byte-for-byte world-store immutability.

Optional operator smoke after automated gates:
- start existing live-control server against a disposable initialized world;
- use a canonical fixture-created reviewable BLD-08 run;
- POST a complete disposition set twice in different orders;
- observe identical planId/planDigest/effect;
- GET extract-promote status before and after and verify the same head revision;
- inspect world-root file hashes and confirm no change.

Do not build a CLI, page, or debug persistence feature for this smoke.

Baseline failure protocol

For any required command failing on base:

run the exact same command or the narrowest equivalent on base and head;

record full base/head result;

do not call the command green;

no waiver may cover a new failure in a §4 path or an owning-boundary test;

an existing unrelated baseline failure may be accepted only with explicit operator waiver and proof that head adds no failures.

Command

Base result

Head result

New failure introduced?

Acceptance effect

Waiver

<required command>

<exact>

<exact>

Yes / No

blocked / explicit waiver

none or operator-granted

No frontend build waiver is relevant because no frontend path is in scope.

§8 Required implementation handback

The implementation handback must include:

Base SHA and head SHA.

Actual changed paths.

Focused diff stat limited to §4.

Any bounded-discovery path with justification.

Exact public request and response examples from the implemented models.

Exact plan schema/version, plan ID rule, decision digest rule, and plan digest rule.

Exact disposition normalization and completeness rules.

Exact reviewed-worldbuilding semantic mapping.

Exact create-new and bind-existing identity behavior.

Exact edge endpoint and evidence behavior.

Exact stable error codes/statuses.

Every §7 command and exact result.

Evidence provenance:

author-local;

independently rerun local;

CI;

manual observation.

Before/after world-root identity and content hashes from the no-mutation proof.

Confirmation that mutation APIs were not called.

Confirmation that existing recap prepare/confirm behavior remains unchanged.

Confirmation that the existing confirm route rejects dmb_worldbuilding_write_plan_v1.

Baseline failures and explicit waivers; write none when none.

Paths outside §4; write none or include stop report.

Stop conditions encountered and resolution; write none when none.

Deviations from §6 matrices; write none when none.

Successors still false:

BLD-10b confirm/commit;

BLD-10c UI;

plan persistence;

graph reload/projection of new objects;

identity-decision persistence.

Confirmation that the complete handoff was implemented without omitted constraints.

This information may be supplied in a dedicated review handback, PR comment, or equivalent review artifact. PR-description polish is not an approval criterion.

Do not report “all tests passed” unless the combined required command actually passed and provenance is stated.

§9 Acceptance rubric — binary merge readiness

The PR is not merge-ready until every unchecked item is closed or an explicitly permitted baseline waiver is recorded.

Capability and scope

Exactly one independently useful capability was delivered: deterministic worldbuilding disposition → inert write plan.

No plan persistence, confirm, contribution write, graph revision, head advancement, UI, or identity-decision mutation shipped.

Every production path is in §4.

Any bounded-discovery test path is justified.

No second public contract was introduced outside the request, response, and plan v1 contracts.

Existing recap prepare/confirm contracts are byte- and behavior-compatible where the handoff requires.

Contract

Request is strict, path-free, server-authority-safe, and complete.

Every candidate node and edge requires exactly one explicit disposition.

Decision/kind matrix is enforced.

targetNodeId rules are enforced.

Request order does not affect output.

Response is typed dmb_worldbuilding_write_plan_v1.

Plan is distinct from and rejected by dmb_extract_promote_proposal_v1 confirm.

Plan ID/digest and decision digest are deterministic and documented.

No timestamp/random value enters plan identity.

confirmable=false is explicit and truthful.

Source, evidence, and semantics

Only exact reviewable BLD-08 worldbuilding runs are admitted.

Exact source/profile/candidate/span lineage is revalidated.

Null session is enforced.

Multi-artifact candidates fail closed.

Every mapped assertion retains exact evidence.

Edge evidence is relationship-native and never inherited.

Recap semantic mapping remains played-canon only.

Separate reviewed-worldbuilding mapping admits only exact BLD-08 semantics plus explicit accepted disposition.

Mapping reuses existing provenance/assertion helpers rather than duplicating them.

Identity and relationships

Create-new uses exact candidate ID and fails on exact-ID conflict.

Bind-existing uses exact active canonical same-kind target ID.

Label, alias, similarity, normalized key, and first match are never authority.

No automatic identity merge or identity-decision record occurs.

Accepted edges require accepted endpoint dispositions.

Exact endpoint mapping, predicate direction, and evidence are preserved.

Reject and defer remain distinct and visible in the plan.

Parent pin and failure behavior

Expected parent revision is required.

Missing/unreadable world fails closed.

Stale parent returns stable 409.

Invalid dispositions return stable 422.

Target conflicts and mapping failures return stable safe errors.

Unexpected errors use a safe correlation-ID 500 boundary.

Every failure leaves world store unchanged.

No-mutation proof

World head ID is unchanged before/after.

World revision set is unchanged before/after.

Contribution ledger is unchanged before/after.

Identity decisions/redirects are unchanged before/after.

World-root file list and content hashes are unchanged.

Mutation APIs are proven uncalled.

Verification and handback

Combined required pytest command passes.

Required Ruff command passes.

git diff --check passes.

Actual changed paths match §4.

Required adversarial tests exist and pass.

Evidence provenance is explicit.

Baseline failures are compared honestly.

No required gate is replaced by a PR-description claim.

BLD-10b and BLD-10c remain unimplemented and unclaimed.

Complete implementation handback is present.

Reviewer verdict rules

APPROVE:
  Every rubric item is true, or only an explicitly permitted unrelated baseline
  waiver remains with base/head proof.

REQUEST CHANGES:
  Any invariant, no-mutation, exact identity, evidence, deterministic digest,
  complete disposition, parent pin, recap regression, or owning-boundary test
  item is false or unproven.

COMMENT / nonblocking follow-up:
  PR-description wording, plan/roadmap status synchronization, optional manual
  smoke, or unrelated cleanup that does not affect the capability.

§10 Reviewer protocol

Review the invariant before individual files.

Restate the mission: complete reviewed dispositions become one inert deterministic plan.

Confirm the response is not accepted by existing confirm.

Search the diff for every Kernel/world-store mutation API.

Compare actual paths with §4 and §5.

Inspect the request model for omitted/default behavior.

Verify candidate coverage is exact and complete.

Verify canonical decision ordering and digest inputs.

Verify same-set permutation tests.

Verify changed target/action/head changes plan identity.

Inspect the semantic mapper:

recap rules unchanged;

worldbuilding path exact and explicit;

no generic “anything reviewed becomes canonical” shortcut.

Inspect evidence mapping:

shared helper;

exact artifact/span;

no edge inheritance;

no multi-artifact leak.

Inspect identity behavior:

exact create ID;

exact bind target;

no label/alias fallback;

no decision persistence.

Inspect edge endpoint closure.

Verify stale parent and missing world behavior.

Verify no-mutation tests at the world-root boundary, not merely mocks.

Verify mutation-api tripwire tests.

Run recap regression tests.

Run the combined §7 command.

Distinguish author-local, independent, CI, and manual evidence.

Treat doc/status cleanup as nonblocking unless it changes implementation authority.

A large diff is acceptable only when every changed layer establishes or proves the single invariant. A small diff is not acceptable if it weakens recap semantics, makes the plan confirmable, or hides incomplete decisions.
