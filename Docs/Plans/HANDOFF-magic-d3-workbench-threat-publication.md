Handoff pointer

Conversation: MAGIC-D3 Workbench Publication Bridge

Flow / agent: STATBLOCK

Direction: DESIGN → CODE

Handoff: Docs/Plans/HANDOFF-magic-d3-workbench-threat-publication.md

PR / branch: optional transport metadata only

Verification pointer

Base/reviewed head: b6d1df07fae7b28760994509dcf2ae9bd8fb74c7 / cf8e68cad24dd897337012f3081f9de1d50466c6 (cycle-6 recovery head; cycle-7 recovery repair is the current worktree slice; dogfood implementation head: d1123dd0)

Changed paths: cumulative branch paths from b6d1df07 through d1123dd0 plus corrective contract/provenance and cycle-5/6 commits through cf8e68ca; cycle-7 recovery ownership and verification are recorded in §4, §6E, §6F, §6G, §6H, and §7.

Verification: owning backend identity/operation/proposal/commit tests and the frontend publication/workbench suite; exact commands and results are recorded in §7.

HANDOFF — Workbench governed Threat publication bridge

Created: 2026-08-04. Status: IMPLEMENTED — corrective cycle-4 contract expansion through cycle-6 head cf8e68ca, with cycle-5, cycle-6, and cycle-7 recovery contracts recorded below (dogfood implementation head d1123dd0).

Canonical handoff path: Docs/Plans/HANDOFF-magic-d3-workbench-threat-publication.md
Conversation name: MAGIC-D3 Workbench Publication Bridge
Flow / agent: STATBLOCK
Handoff direction: DESIGN → CODE
Design agent: DungeonBuddy MAGIC-D3 stewardship design agent
Code agent: STATBLOCK code agent using the exact conversation name above
PR title: STATBLOCK: publish accepted Threat from Workbench

Historical dispatch gate: before implementation, origin/main had to contain commit b6d1df07fae7b28760994509dcf2ae9bd8fb74c7, the publication route/model contracts had to match §6D, and no open PR could own the same Workbench/API-client paths. That gate is satisfied; this handoff now records the implemented head and corrective expansion.

This checked-in handoff is complete authority for the implemented Workbench publication capability and its corrective contract expansion. The original frontend-only dispatch boundary was widened after the Latchling dogfood exposed server/kernel contracts required for a complete governed path. Do not silently add Threat presentation, Hermes cards, performance work, placement, Build insertion, or graph-contract repair beyond the contracts recorded here.

Shared vocabulary

Term

Definition

Publication chain

One exact draft_id → operation_id → resolution_id → proposal_id → commit_id lineage.

Durable authority

The server-owned operation, identity, proposal, commit, and immutable World Graph records.

Session pointer

A bounded browser sessionStorage record containing exact publication IDs only; never graph bodies, mechanics, candidate bodies, or authority claims.

Committed-unverified

A known immutable graph commit whose exact verification is incomplete, degraded, or failed. It is durable publication truth but not verified success and is never confirmation-retryable.

Normal product path

Workbench controls and typed API calls; no copied IDs, developer console, hidden storage edits, or direct HTTP scripting.

Owning boundary

The layer where the guarantee becomes true: typed API client, session-pointer codec, publication state machine/component, or Workbench integration.

Agent flow and nano-commit contract

Use STATBLOCK for every commit and review reference. Keep nano commits discrete. A suitable sequence is:

statblock: type Threat publication API envelopes

statblock: preserve typed publication outcomes

statblock: persist exact publication session pointers

statblock: add Workbench publication journey

test(statblock): prove publication replay and failure states

Do not mix tracker, roadmap, report, or backlog sync into the implementation commits.

Review and document-sync contract

The reviewer must identify the exact branch/head SHA and inspect the cumulative diffagainst this handoff. Review the invariant across the full journey before reviewingindividual files. Require all repair cycles needed to reach merge.

Roadmap, tracker, dogfood report, backlog, and handoff-status updates are a separatepost-merge DOCUMENTS operation.

§1 Mission and merge-ready invariant

Mission

A GM can publish one mechanics-saved ThreatDraft through the existing governed
begin → identity decision → proposal review → confirmation protocol from the
Statblock Workbench, so publication is reachable without architecture knowledge
or copied identifiers.

Merge-ready invariant

One Workbench draft and one exact publication chain remain bound across every
visible action, retry, and browser reload; the UI never auto-selects identity,
never changes parent or mechanics authority, never repeats confirmation after a
committed revision is known, and always distinguishes verified,
committed-unverified, uncommitted, ambiguous, stale, unavailable, and integrity
outcomes while leaving accepted mechanics unchanged.

Findings addressed

Finding

Severity

Accepted observation

Treatment in this PR

D3-F01

S1

Clean main had backend publication routes but no normal Workbench publication entry.

Resolve completely.

D3-F02

S2

A failed attempt left an active operation and the next begin returned publication_busy until cancellation.

Preserve the exact operation pointer and expose truthful cancel/retry actions.

D3-F03

S2

Publication progress and durable outcome were difficult to understand; hard refresh lost local journey context.

Rehydrate exact IDs from bounded session state and re-read server authority.

D3-F04

Integrity candidate

Dogfood reached committed_unverified with verification codes.

Display truthfully and prohibit re-confirmation. The corrective cycle also repairs proposal provenance packaging and aligns source-domain verification with the canonical embedded shape; broader projection/audit policy remains a successor.

Named successors not included

STATBLOCK: make Threat glance campaign-useful

STATBLOCK: emit Hermes Threat cards

STATBLOCK: measure and reduce Threat publication/hydration latency

complete MAGIC-D3 rerun and closeout documentation

exact Threat embed, placement, Build insertion, Play/combat activation, mechanics revision adoption

Pre-dispatch critique

Question

Answer

Can one invariant govern every claimed observable path?

Yes. Every path exists to establish or recover one exact publication chain and render its durable authority honestly.

What adversarial sequence is most likely to falsify it?

Begin publication → prepare candidates → choose identity → prepare proposal → confirm request reaches server → response is lost or returns committed_unverified → browser reload → UI creates a new commit ID or re-confirms.

Would §7 detect that failure?

Yes. Component tests freeze IDs, inject lost responses, restore from sessionStorage, re-read the exact commit, and assert zero additional confirm calls after a committed revision is known.

Which owning boundary is easiest to under-test?

Typed non-2xx response preservation in liveApi.ts; lifecycle 409/503 envelopes must not collapse into generic exceptions.

What fact forces stop or split?

Any required server endpoint/model change; inability to recover the chain without introducing a server “list active publication” contract; or discovery that the dogfood publication chrome already exists in an open PR touching the allowlist.

§2 Context, authority, and boundaries

Field

Required content

Parent authority

Docs/Plans/STEWARDSHIP-magic-d3-usability-polish-and-closeout.md supplied to the design agent; Docs/Reports/MAGIC-MOMENT-D3-2026-08-04.md; Docs/Plans/HANDOFF-magic-d3-threat-publication-query-projection-dogfood.md; Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md.

Repository architecture

Docs/Design/ARCHITECTURE-campaign-supergraph.md; exact immutable revisions and governed writes remain Kernel/server authority.

Repository rules

AGENTS.md; .cursor/rules/external-agent-pr-loop.mdc; checked-in handoff template; nano commits; PR description is transport only.

Base revision

b6d1df07fae7b28760994509dcf2ae9bd8fb74c7 — docs commit containing the MAGIC-D3 report and execution handoff. Re-anchor before implementation.

Merged predecessor contracts

SBW09a PR #462; SBW09b PR #467; SBW09c1 PR #478; SBW09c2b PR #491; SBW10a PR #502; SBW10b PR #504.

Shared-surface predecessor

PR #506, merge 5d9bb23ecb1acdc58d8dd405540bacf9549ed635; this slice must not alter its graph-reference or projection-host contracts.

Exact input consumed

Current ThreatDraftV1 with workflow_state="mechanics_saved" and an exact accepted_mechanics_ref; current World Graph head from the existing typed bootstrap-status read; typed publication route envelopes in §6D.

Durable output

Existing server-owned publication ledgers and immutable graph revision only. This PR adds no new server persistence.

Local persisted output

One versioned, pointer-only sessionStorage record per draft, specified in §6C.

Named successor

Campaign-useful Threat glance.

What remains false

Hermes card output, automatic Plan refresh, cross-device publication recovery, generic object publication, latency budgets, placement/combat, and broad automatic verification repair. The publication-specific provenance and source-domain contracts required to make the dogfood merge/audit behavior explicit are now implemented.

Explicit non-goals

No new publication route or persistence store; no graph write outside the existing confirm route; no Threat Sheet styling; no Hermes prompt/tool changes; no Build or Plan mutation; no generic object-publication framework; no cross-device recovery. Existing server and Kernel owners were changed only to make the Workbench path's identity, ledger, provenance, merge-diagnostic, and verification contracts durable.

Read authoritative inputs in this order before changing code:

Docs/Reports/MAGIC-MOMENT-D3-2026-08-04.md

this handoff

SBW09a/SBW09b/SBW09c1/SBW09c2b models, routes, services, and owning tests

apps/live-control-ui/src/api/liveApi.ts and api/types.ts

apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx

current Workbench and API-client tests

PR #506 changed paths and current open PR collision state

Re-anchor requirements

Before implementation:

git fetch origin
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD

Record:

actual origin/main SHA;

commits after b6d1df07…;

open PRs touching any §4 path;

whether publication routes or envelopes changed;

whether Workbench publication chrome landed elsewhere.

Stop when the base moved through owning paths until this handoff is reconciled.

§3 Observable-path and adversarial-sequence inventory

Observable paths

Path

Current behavior

Required behavior

Same invariant?

Owning boundary

Workbench eligibility

mechanics_saved draft has no publication entry.

A visible Publish Threat action appears only for a current mechanics-saved draft with exact accepted mechanics and a readable current graph head.

Yes

Workbench integration

Begin

No client method or UI.

Generate one operation UUID, call begin with exact draft version and observed graph head, persist the ID before/with the request, and render the typed outcome.

Yes

API client + state machine

Begin replay

Reload or response loss loses the local chain.

Same operation ID and same request replays; changed draft/head never silently reuses it.

Yes

session codec + state machine

Active-operation recovery

A failed attempt can strand the user at publication_busy.

A stored exact operation can be re-read, refreshed, cancelled, or retried using server-permitted actions. An unknown busy operation is reported honestly; do not guess its ID.

Yes

Workbench state machine

Identity candidate review

Backend only.

Show candidate label, role, summary, aliases, scope, bindings, and match reasons; keep IDs secondary. Require explicit create-new, connect-existing, or refuse.

Yes

publication panel

Create-new collision handling

Backend contract requires rejected exact collisions.

Every exact-name collision must be explicitly rejected before create-new is enabled.

Yes

publication panel

Connect-existing

Backend only.

Confirm exactly one candidate by node_id; never first-win or label resolution.

Yes

publication panel

Refuse

Backend only.

Refuse ends the journey without proposal or commit and explains that no graph write occurred.

Yes

publication panel

Proposal review

Backend only.

Show create/connect decision, target identity, source draft, exact accepted mechanics locator, expected graph parent, and effect counts before confirmation. IDs/digests are inspectable details, not the primary reading order.

Yes

publication panel

Confirm

Backend only.

Generate one commit UUID once, submit exact proposal digest and parent, disable duplicate confirmation while pending, and preserve the ID through uncertainty.

Yes

API client + state machine

Verified commit

No UI.

Report durable verified publication, exact Threat node, binding, revision, and clear next action.

Yes

publication panel

Committed-unverified

No UI.

Report “Published; verification needs attention,” show exact revision and bounded verification codes behind details, prohibit another commit, and permit only exact commit re-read.

Yes

publication panel

Uncommitted/ambiguous/recovery pending

No UI.

Preserve chain and render typed state. Retry only when the server envelope permits it; never convert ambiguity into success.

Yes

publication panel

Browser reload

In-memory work is lost.

Rehydrate the pointer, re-read operation/resolution/proposal/commit in order, validate every returned identity, and resume the exact safe stage.

Yes

session codec + state machine

Draft switch

One monolithic module risks stale completions.

Abort/ignore stale completions, load the new draft’s separate pointer, and never attach old publication state.

Yes

Workbench integration

Accepted mechanics mutation

Publication work could accidentally affect existing Workbench state.

Publication never changes draft, candidate, editor, accepted mechanics, or revision controls.

Yes

Workbench integration tests

Ordered adversarial sequences

Sequence

Required safe outcome

Owning proof

Begin request sent → response lost → reload

Re-read same operation ID; no second begin ID unless the first is terminal and the operator explicitly starts over.

E4, E8

Identity candidates loaded → draft changes or another draft opens → old response resolves

Old completion is ignored; no resolution is created for the new draft.

E5

Exact collisions exist → operator chooses create-new without rejecting all

Control remains disabled; no resolution POST.

E6

Candidate set changes between prepare and decision

Render typed changed-set conflict; require fresh candidate review; no auto-replay decision.

E6

Proposal ready → confirm sent → server commits → client receives network error

Preserve commit ID; on reload/read, accept verified or committed-unverified response; zero second confirm calls.

E7, E8

Confirm returns committed_unverified

Show durable commit, verification warning, exact revision; Confirm remains permanently unavailable.

E7

Commit returns ambiguous/recovery pending

Keep exact chain; do not display published success; only exact read/retry behavior allowed by response.

E7

Stored pointer IDs do not match server envelopes

Fail closed, clear no server state, show recovery error, and retain a copyable technical detail for diagnosis.

E4

Existing operation is active but no local pointer exists and begin returns busy without the active operation

State that another publication is active and cannot be safely recovered from this browser; do not add a server listing endpoint in this PR.

E3

Component unmount or draft switch during any request

Stale completion cannot mutate current UI or issue the next lifecycle request.

E5

§4 Files in scope

Action

Path

Purpose

Modify

apps/live-control-ui/src/api/types.ts

Add exact TypeScript mirrors for existing SBW09a/b/c1/c2b request and response envelopes consumed by the UI.

Modify

apps/live-control-ui/src/api/liveApi.ts

Add publication client methods and a private typed-outcome fetch path that preserves valid non-2xx lifecycle envelopes.

Modify

apps/live-control-ui/src/api/liveApi.test.ts

Prove paths, bodies, typed 2xx/409/503 handling, malformed-envelope failure, and ordinary transport failure.

Create

apps/live-control-ui/src/statblocks/publication/threatPublicationSession.ts

Versioned pointer-only session codec, identity validation, and keying by exact draft ID.

Create

apps/live-control-ui/src/statblocks/publication/threatPublicationSession.test.ts

Exact round-trip, corrupt/mismatched/versioned-state, and clear/restore proofs.

Create

apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.tsx

Own the publication journey state machine and GM-facing decision/recovery UI.

Create

apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.test.tsx

Component-level lifecycle, identity, retry, commit, reload, and stale-completion evidence.

Modify

apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx

Mount the publication capability only for the exact current mechanics-saved draft and isolate it from editor/acceptance state.

Modify

apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx

Prove entry eligibility, no accepted-mechanics mutation, draft switching, and integration with existing Workbench behavior.

Bounded discovery exception:

Directory: apps/live-control-ui/src/statblocks/publication/
Maximum additional paths: 1
Allowed path kinds: test fixture or a small pure view-model helper only
Decision rule: required to keep ThreatPublicationPanel free of duplicated pure
classification logic and directly exercised by its own test; no CSS, barrel, or
general-purpose framework file may be added under this exception.

Corrective contract owners promoted by the Latchling dogfood:

Modify

apps/live_control_server/services/threat_publication_identity.py

Make identity-surface evidence the candidate policy; preserve exact collision, mixed-match, ranking, and digest behavior.

Modify

apps/live_control_server/services/threat_publication_operations.py

Validate the active-operation pointer and return the ledger's exact active record in publication_busy.

Modify

apps/live_control_server/services/threat_publication_proposals.py

Canonicalize embedded evidence, source_artifacts, and source_domains in every packaged assertion for create-new and connect-existing.

Modify

apps/live_control_server/services/threat_publication_commits.py

Consume structured merge diagnostics and verify the canonical provenance domains without brittle diagnostic-string dependence.

Modify

src/graph_memory/kernel/contribution_models.py

Expose structured failure_code and failure_message on merge results.

Modify

src/graph_memory/kernel/contribution_merge.py

Populate structured merge failure fields at the owning merge boundary.

Modify

src/graph_memory/kernel/contributions.py

Normalize embedded evidence/source-artifact source domains into the shared provenance contract.

Modify

apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.tsx

Provide dock-driven candidate/proposal retry recovery, publication_busy recovery, structured uncommitted messaging, exact commit-ID preservation, and refusal-cancellation uncertainty handling.

Tests

tests/test_threat_publication_identity.py; tests/test_threat_publication_operations.py; tests/test_threat_publication_proposals.py; tests/test_threat_publication_commits.py; apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.test.tsx; apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx

Prove the promoted server/client contracts and the no-duplicate-confirm reload path.

Evidence artifacts

Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md; evals/c2_live_prep/live/session_22/current_state.json; evals/c2_live_prep/live/session_22/hermes_thread_pointers.json

Record exact dogfood provenance; these artifacts are evidence, not new runtime authority.

The original frontend-only allowlist was expanded after the Latchling dogfood. The paths above are the recorded corrective contract owners; no other backend, Kernel, Plan, Build, Hermes, projection, or styling path is included.

§5 Explicitly out of scope

Path, layer, or capability

Why excluded

Generic server routes, new persistence stores, and unrelated server services

The existing Threat publication routes remain the API surface. The listed service changes only harden their response/ledger/proposal/verification behavior.

Unrelated src/graph_memory/**

The listed contribution model/merge/provenance helpers are the owning Kernel contracts for the embedded proposal package; graph schema redesign, identity architecture, and unrelated projection work remain excluded.

apps/live-control-ui/src/statblocks/projection/**

Campaign-useful Threat glance/full projection is the next visual slice.

apps/live-control-ui/src/agentInteraction/**

Hermes structured cards and shared host behavior are separate.

apps/live-control-ui/src/planSurface/**

No Plan refresh, insertion, or projection change in this slice.

apps/live-control-ui/src/buildSurface/**

Build is not the test host and remains outside MAGIC-D3 publication.

LandingPage/**, theme CSS, TipTap styling

Visual grammar port belongs to the Threat-glance successor.

telemetry/performance infrastructure

Measurement and latency reduction require a distinct invariant.

Backlog, trackers, roadmaps, reports

Post-merge document sync only.

generic object publication

Threat publication is the proven domain; do not generalize.

cross-device persistence

Session pointer is browser-session-local only.

“list active publication” server endpoint

Independently useful recovery contract; stop and propose separately if required.

automatic verification repair

A committed-unverified receipt is rendered honestly; server repair requires a reproduced defect and its own handoff.

§6 Implementation contract and matrices

Core contract

Input:
  - one exact current ThreatDraftV1
  - workflow_state == "mechanics_saved"
  - exact accepted_mechanics_ref
  - current typed World Graph head observation
  - existing typed SBW09a/b/c1/c2b route envelopes

Output:
  - one GM-facing publication journey
  - existing server-owned durable operation/resolution/proposal/commit records
  - one pointer-only browser session record for exact rehydration

Invariant:
  One Workbench draft and one exact publication chain remain bound across every
  visible action, retry, and browser reload; identity, parent, mechanics, and
  commit authority never move silently.

Failure behavior:
  Typed lifecycle conflict/unavailable/integrity result → stable rendered state
  preserving exact known IDs; no next request unless explicitly permitted.
  Malformed response or ID mismatch → fail closed as client contract failure.
  Unknown publication_busy → honest blocked state; no guessed recovery.

Replay / idempotency:
  same generated ID + same request → exact server replay;
  same ID + changed request → typed conflict, never mutate local authority;
  lost response → re-read exact ID;
  committed revision known → GET exact commit only, never POST confirm again.

Trust boundary:
  Verifies:
    - response schema discriminator and required fields at the client boundary;
    - every route identity equals the active draft and stored chain;
    - candidate decisions use exact node IDs from the frozen candidate set;
    - proposal/commit parent and digest come from server envelopes;
    - committed states carry a committed revision.
  Records or trusts without proving:
    - server validation of graph contents;
    - Kernel merge correctness;
    - mechanics digest correctness;
    - verification code semantics.

Commit point

Commit point:
  The existing SBW09c2b confirm endpoint knows an immutable committed revision
  and returns a commit record in committed_verified or committed_unverified.

Before commit:
  The UI may cancel/retry only through typed predecessor actions and may not
  claim the Threat exists durably.

After commit:
  The UI freezes operation/resolution/proposal/commit IDs and prohibits another
  confirmation. It may re-read the exact commit and navigate elsewhere.

Truthful result after post-commit failure:
  "Published; verification needs attention" with exact revision and verification
  status/codes. Never "not published," never "try publishing again."

A. State and fallback matrix

Path

Loading

Exact success

Ordinary miss

Dependency unavailable

Integrity/contract failure

Stale/superseded

Retry/replay

Eligibility/head

Disable publish with visible status.

Show Publish action.

Draft not mechanics-saved → no action, explain prerequisite.

Disable; preserve draft.

Disable; technical detail.

Re-read current draft/head.

Manual retry only.

Begin/read operation

Keep generated ID and disable duplicate click.

publication_ready with exact operation.

publication_not_found on restore → recovery error; no new begin automatically.

Preserve pointer and offer same exact read.

Fail closed.

Show reasons; cancel or typed retry.

Same operation ID for replay; new ID only through explicit retry/start-over.

Candidate prepare

Keep operation visible.

Frozen candidate set and digest.

No candidates is valid; create-new/refuse remain available.

Preserve operation.

Fail closed.

Refresh candidates explicitly.

Re-run prepare; never reuse an old digest after changed-set response.

Identity decision

Disable all decision controls while pending.

Exact active resolution.

Target not found → return to candidate review.

Preserve review.

Fail closed.

Superseded → re-read active chain or stop.

Same resolution ID/request for replay.

Proposal prepare/read

Keep resolution visible.

Exact active proposal.

Not found → recovery error.

Preserve chain.

Fail closed.

Parent/predecessor mismatch → no silent repin; restart explicitly.

Same proposal ID/request for replay.

Confirm/read commit

Disable confirm immediately and retain commit ID.

Verified or committed-unverified.

Confirm POST with commit_admitted=false → return to proposal review without
label enumeration. Exact GET publication_commit_not_found → return to proposal
review as a distinct read outcome. Lost transport or an admitted failure →
retain the exact commit ID and use exact reread/retry policy.

Preserve exact chain.

Fail closed.

Proposal not active/parent mismatch → no graph claim.

POST same commit only when no committed revision is known and server contract permits; otherwise GET only.

Session restore

Validate pointer before requests.

Re-read exact stage chain.

Missing pointer → idle.

Preserve pointer.

Mark local recovery failure; do not mutate server.

Draft version mismatch → show old-chain warning; do not attach to new draft state.

User may clear local pointer only after warning; server remains authoritative.

Fallback sources: none. Do not fall back to labels, current head after begin, current mechanics, first candidate, latest proposal, or latest commit.

B. Identity matrix

Situation

Required rule

Ambiguity behavior

Fallback permitted?

Draft

Exact draft_id from current Workbench load.

Pointer/response mismatch fails closed.

No

Operation/resolution/proposal/commit

Exact generated UUID stored once and validated against every response.

Missing or conflicting response blocks progression.

No

Existing Threat

Exact candidate node_id from frozen candidate set.

Multiple candidates require operator selection.

No

Label/alias

Display and search context only.

Never resolves identity.

No

Create-new collision

Every exact_name_collision=true candidate must be explicitly rejected.

Incomplete rejection blocks request.

No

Rename after candidate snapshot

Snapshot remains decision authority for this resolution.

Changed candidate set requires fresh review.

No

Published Threat

Exact threat_node_id and binding_id from commit.

Missing fields are contract failure.

No

C. Persistence and replay matrix

Session pointer contract

Storage: window.sessionStorage
Key: dmb.statblock.threat-publication.v1:<draft_id>

ThreatPublicationWorkbenchSessionV1 {
  schema: "dmb_threat_publication_workbench_session_v1"
  draft_id: string
  draft_version: number
  operation_id: string
  resolution_id: string | null
  proposal_id: string | null
  commit_id: string | null
  stage:
    "operation" | "identity" | "proposal" | "commit"
  updated_at: string
}

The pointer contains no actor prose, candidate bodies, graph objects, sourcesnapshots, mechanics definitions, digests, accepted assertions, or result claims.Those are re-read from server authority.

Operation

Representation

Round-trip guarantee

Duplicate/replay behavior

Compatibility

Rollback/reversion

Save pointer

Versioned JSON above

Exact IDs and stage survive same-tab reload.

Overwrite only for same draft and forward chain.

Unknown schema/version ignored with visible recovery warning; no migration in v1.

Explicit local clear does not cancel or alter server state.

Restore pointer

Parse + strict field validation

Every response identity must match pointer and active draft.

GET exact records; no mutation.

Invalid record quarantined/cleared locally after warning.

User can clear local pointer.

Begin/decision/proposal/confirm

Server ledgers

Same ID + same request is replay-safe per predecessor contracts.

Reuse generated ID until terminal classification.

Existing server v1 schemas only.

Use existing cancel/retry/supersession semantics; never edit storage.

Terminal commit

Existing commit ledger + immutable graph revision

Reload returns exact committed revision and binding identity.

Committed state forbids another confirm.

No client migration.

Retraction/undo is out of scope.

A different persistence mechanism or a need for server-side active-chain discovery is a split trigger.

D. Predecessor-to-consumer mapping

Predecessor

Exact route/shape consumed

Consumer behavior

Transformation/proof

ThreatDraftV1

Current Workbench draft: draft_id, version, workflow_state, accepted_mechanics_ref, world_id, campaign_id.

Gate publication and display exact source/mechanics summary.

Existing draft load fixture + Workbench integration test.

World Graph bootstrap status

Existing typed getWorldGraphBootstrapStatus() result and its current head field already used by Workbench create scope.

Supply expected_parent_revision_id; disable when unreadable.

Use the current canonical type; stop if the field is not exact/current-head authority.

SBW09a begin

POST /api/live/threat-drafts/{draft_id}/publication-operations; BeginThreatPublicationOperationRequestV1; ThreatPublicationOperationResponseV1.

Begin/replay one exact operation and render all result labels.

Captured route/model types; API-client tests for 201/200/409/503.

SBW09a read/refresh/cancel/retry

Existing exact operation routes.

Restore and recover known operation only.

Route-path/body tests and component recovery tests.

SBW09b candidates

POST .../{operation_id}/identity-candidates/prepare; ThreatPublicationIdentityResponseV1.candidate_set.

Render frozen candidates and exact collision requirements.

Exact field mapping tests; no approximate fixtures.

SBW09b resolution

POST .../{operation_id}/identity-resolutions; request fields include exact candidate set digest, decision, target node, rejected candidate IDs, actor, reason.

Create explicit create/connect/refuse authority.

Component request assertion for all three decisions.

SBW09c1 proposal

POST .../{operation_id}/identity-resolutions/{resolution_id}/proposals; response carries proposal, effect summary, sealed digest, expected parent.

Present human review and prepare confirmation.

Proposal fixture based on canonical model, not invented names.

SBW09c2b confirm

POST .../{operation_id}/proposals/{proposal_id}/commits; exact proposal digest + parent + commit ID.

Confirm once and classify durable result.

Lost-response and committed-unverified tests.

SBW09c2b read

GET .../{operation_id}/commits/{commit_id}.

Exact reload/recovery; never current/latest.

Session restore integration test.

Typed non-2xx rule

Publication routes intentionally return valid lifecycle envelopes with HTTP 409 and503. The generic apiFetch throws away those envelopes. Add a private publicationfetch helper that:

parses JSON once for every status;

validates/returns the typed publication envelope for expected 2xx/409/503 statuses;

throws LiveApiError only for transport failure, HTML/non-JSON, malformed schema,or an unexpected status without a valid publication envelope;

does not weaken generic apiFetch behavior for unrelated callers.

Do not globally change all API error handling.

§6E. Corrective cycle-4 durable contracts

Identity candidate policy

Identity decision candidates require identity-surface evidence. A candidate is
eligible for operator identity choice only when its match reasons include a
surface match on the draft label, an alias, or the exact node_id. Attribute,
binding, source-domain, or other context-only matches remain diagnostic context
and are hidden from identity choice. Exact surface matches remain; mixed
surface-plus-context matches remain; exact-name collisions remain visible and
block create-new until explicitly rejected. Candidate ranking and the sealed
candidate_set_digest are deterministic for the same inputs, independent of
input ordering.

Busy recovery contract

publication_busy returns the exact non-terminal operation record named by the
ledger's active_operation_id for the same draft. Ledger load fails closed when
the pointer is missing, terminal, dangling, or coexists with multiple active
records; it never invents an operation. The client may expose Cancel stuck
publication only for the returned exact operation_id. A busy response without
an operation is an honest unrecoverable-from-this-browser state.

Canonical proposal provenance

Every accepted assertion in a sealed create-new or connect-existing package
uses the same embedded shape:

  value.evidence[]:
    evidence_ref_id, locator, source_artifact_id, source_domain
  value.source_artifacts[]:
    campaign_id, source_artifact_id, source_domain, uri
  value.source_domains: sorted source-domain names

The assertion keeps its evidence_ref_ids and source_artifact_id alongside that
embedded value. The shape applies to node, attribute, and edge assertions,
including resource and binding assertions. The sealed package is the replay
authority: its canonical JSON/digest must reconstruct the same contribution
and preserve the exact source-domain semantics. Reference-only
evidence:tpub IDs are not sufficient for merge.

Structured merge diagnostics

ContributionMergeResult.failure_code and failure_message are the owning merge
diagnostic contract. The commit service and UI use those fields for actionable
uncommitted messages. Parsing legacy merge_failed: strings is compatibility
fallback only for pre-contract injected/persisted results.

Dock recovery and exact chain IDs

Candidate prepare failures and changed candidate sets expose Refresh identity
candidates. Proposal rejection or transport uncertainty exposes Retry proposal
preparation/replay with the same proposal ID when one was admitted. Classified
failures block one-shot auto-advance until an explicit dock action succeeds.
Candidate transport failures use the same candidate-specific message lane as
typed failures, so the dock never falls back to a misleading loading state.
Refusal is a distinct "recorded, cancellation unresolved" state: Start over is
hidden, exact re-cancel and operation reread remain available, and the session
pointer is cleared only after publication_cancelled.
The commit response carries commit_admitted. Confirm POST responses with
commit_admitted=false are pre-admission and roll back to proposal review
regardless of result label. Every admitted response carries the durable commit
record. An exact GET publication_commit_not_found is handled as a distinct
read outcome and rolls back only after that exact read; it is not inferred from
a client-maintained rejection label list.

§6F. Corrective cycle-5 recovery contracts

Refusal cancellation

An accepted refusal records the resolution before attempting cancellation. If
the automatic cancellation throws or returns any non-publication_cancelled
envelope, the UI enters refusal-cancellation-unresolved, retains the exact
operation/resolution pointer, hides Start over, and exposes exact re-cancel plus
operation reread. Only publication_cancelled terminalizes the chain and clears
the pointer. Reload reconstructs the same refusal state from the exact
resolution.

Candidate transport recovery

A rejected candidate-prepare promise is a candidate-specific transport failure,
not a generic panel error. It sets candidateMessage, blocks automatic
repetition, and exposes Refresh identity candidates in both the panel and dock.
An explicit successful refresh replaces the candidate set and reopens review.

Commit admission and exact reads

The server response's commit_admitted field is the admission authority. False
means no commit ledger record exists and commit is null; true means the response
carries the exact durable record, including post-admission graph or integrity
failures; null means admission is unknown because the ledger could not be read.
The client clears the local commit pointer on a confirm POST only when
commit_admitted is false. An exact GET not-found is a separate, authoritative
absence result that returns the chain to proposal review so it can be retried;
unknown admission, ambiguous transport errors, and admitted records retain the
exact commit ID.

§6G. Corrective cycle-6 recovery contracts

Unknown commit admission

If the server cannot load the commit ledger while handling confirm or exact
commit read, commit_admitted is null. This is not evidence of pre-admission:
the ledger may already contain the requested commit record. The client retains
the exact commit ID and session pointer, disables a fresh confirmation, and
offers exact reread/recovery. Only commit_admitted=false on a confirm POST
proves that no durable commit record was admitted.

Cancellation reread

When an explicit operation reread returns publication_cancelled, the client
clears the bounded session pointer before resetting the panel to Publish. Lost
cancellation responses therefore cannot leave a cancelled operation pointer
behind for the next mount.

§6H. Corrective cycle-7 recovery contract

Admitted record survives proposal-ledger failure

When confirm replay first loads an existing commit ledger record, that load is
authoritative evidence that the exact commit was admitted. If the record is
still committing and the subsequent proposal-ledger read fails, the response
returns that already-loaded record with commit_admitted=true and the exact
commit_id. It must not route through a storage outcome that drops the record
and infers false admission. The client retains the chain and exposes only
governed commit recovery/reread; it never reopens a fresh confirmation for the
same proposal.

§7 Evidence required to merge

ID

Guarantee

Owning boundary

Evidence

Expected result

Stop condition

E1

Publication API types mirror current server v1 contracts.

api/types.ts

Compile-time fixtures covering all request/response discriminators and required fields.

No approximate or optionalized authority fields.

Current server shape cannot be represented without backend change.

E2

Typed 409/503 outcomes survive client boundary.

liveApi.ts

API tests for begin busy/stale, candidate review-required/unavailable, proposal mismatch, commit recovery pending/unverified.

Caller receives result_label and envelope body.

Generic error behavior changes for unrelated API calls.

E3

Eligible Workbench exposes one normal entry and unknown busy stays honest.

Workbench integration

Render mechanics-saved draft, click Publish, inject busy without operation.

Visible blocked state; no guessed ID or extra call.

UI uses direct IDs or developer controls.

E4

Session pointer round-trips exact IDs and fails closed on mismatch.

session codec

Unit tests for valid, corrupt, wrong draft/version/schema, forward stage, explicit clear.

No bodies or authority claims stored.

Need server list-active endpoint.

E5

Async completions cannot cross draft/unmount boundaries.

publication panel/Workbench

Delayed begin, candidates, proposal, and commit responses across draft switch/unmount.

No stale state or next request.

Shared provider changes required.

E6

Identity decision is explicit and collision-safe.

publication panel

Candidate-set tests for zero/one/many, exact collision rejection, connect exact ID, refuse, changed-set conflict.

No first-win; request matches frozen set.

Need new matching policy.

E7

Commit truth is exact and no duplicate write occurs.

publication panel

verified, committed-unverified, recovery-pending, uncommitted, ambiguous, integrity tests; inspect confirm call count.

Committed states permanently disable confirm; exact revision shown.

UI treats committed-unverified as verified or retryable.

E8

Lost response + reload resumes exact chain.

integrated panel + session codec + API mocks

Confirm resolves on server but client rejects; remount; GET exact commit returns committed state.

Same commit ID; zero second POST confirm.

Pointer cannot recover exact chain.

E9

Existing Workbench mechanics state is untouched.

Workbench integration

Snapshot draft, editor state, accepted ref, candidate/revise/accept controls before and after publication stages.

No mutation or disabled unrelated controls except while explicitly required.

Publication logic couples to editor persistence.

E10

Real product probe reaches durable publication.

manual dogfood

Current-main mechanics-saved real draft → Publish → identity → proposal → confirm → reload exact commit.

Verified or honestly committed-unverified result through UI; no copied IDs.

Backend scripting or hidden storage edit required.

E11

Identity candidates require identity-surface evidence and deterministic ranking/digest.

threat_publication_identity.py + identity tests

Attribute-only context matches are hidden; exact and mixed surface matches remain; collisions, input-order variation, and candidate digests are deterministic.

Matching policy is implicit, order-dependent, or label-only.

E12

publication_busy is an exact active-operation response contract.

threat_publication_operations.py + operation tests + dock client tests

Returned operation equals the ledger record for the same draft; dangling, terminal, missing, and multiple-active pointers fail closed; client cancellation uses that exact ID.

Client guesses an operation or invents recovery for null operation.

E13

Proposal provenance is self-contained and replayable.

threat_publication_proposals.py + contributions.py + proposal tests

Create-new and connect-existing node/attribute/edge assertions embed evidence, source_artifacts, and source_domains; sealed replay reconstructs the intended contribution and merge/verification uses the same domains.

Reference-only evidence, missing assertion kind coverage, or source-domain drift.

E14

Merge failures have structured UI diagnostics.

contribution_models.py + contribution_merge.py + threat_publication_commits.py + commit tests

failure_code/failure_message drive the actionable uncommitted message; legacy string parsing is compatibility-only.

UI requires parsing an ungoverned diagnostic string.

E15

Dock failure recovery never strands the operator or changes an admitted chain ID;
refusal cancellation and commit admission remain explicit.

ThreatPublicationPanel.tsx + panel tests

Candidate refresh after typed or transport failure, proposal retry, changed-set
recovery, lost-response re-read, refusal cancellation recovery, explicit
commit_admitted handling including unknown admission, exact GET not-found
rollback, cancellation reread cleanup, and pre/post-admission graph/integrity
outcomes are explicit and tested; an admitted commit ID survives ambiguity.

Auto-advance repeats after a classified or transport failure, Start over clears
a refusal before publication_cancelled, cancellation reread leaves a cancelled
pointer in storage, or unknown admission is treated as pre-admission and
destroys an exact commit chain.

Run and record exact results:

Recorded provenance for reviewed head cf8e68cad24dd897337012f3081f9de1d50466c6, dogfood implementation head d1123dd08ab925964de4c9d54634f58ec908be14, and the current cycle-7 worktree verification:

- `cd apps/live-control-ui && npm test -- --run src/api/liveApi.test.ts src/statblocks/publication/threatPublicationSession.test.ts src/statblocks/publication/ThreatPublicationPanel.test.tsx src/surface/modules/StatblockWorkbenchModule.test.tsx` — **228 passed** (4 files).
- `cd apps/live-control-ui && npx tsc -b --force` — **baseline waiver**: two pre-existing `BuildReferenceCapability.tsx` `graphScope` errors at lines 122 and 247; publication client errors are cleared.
- `cd apps/live-control-ui && npm run build` — same two baseline `BuildReferenceCapability.tsx` errors; Vite phase is not reached.
- `uv run pytest tests/test_threat_publication_identity.py tests/test_threat_publication_operations.py tests/test_threat_publication_proposals.py tests/test_threat_publication_commits.py -q` — **200 passed**.
- `uv run pytest tests/test_threat_publication_routes.py tests/test_threat_publication_identity_routes.py tests/test_threat_publication_proposal_api.py tests/test_threat_publication_commit_api.py -q` — **26 passed**, 10 existing Pydantic warnings.
- `/usr/bin/git --no-pager diff --check` — clean.

cd apps/live-control-ui

npm test -- --run \
  src/api/liveApi.test.ts \
  src/statblocks/publication/threatPublicationSession.test.ts \
  src/statblocks/publication/ThreatPublicationPanel.test.tsx \
  src/surface/modules/StatblockWorkbenchModule.test.tsx

npm run typecheck
npm run build

cd ../..
uv run pytest \
  tests/test_threat_publication_identity.py \
  tests/test_threat_publication_operations.py \
  tests/test_threat_publication_proposals.py \
  tests/test_threat_publication_commits.py -q

git diff --check
git diff --stat b6d1df07fae7b28760994509dcf2ae9bd8fb74c7...HEAD -- \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/api/liveApi.test.ts \
  apps/live-control-ui/src/statblocks/publication \
  apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx \
  apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx

git diff --name-only b6d1df07fae7b28760994509dcf2ae9bd8fb74c7...HEAD

Minimal live dogfood proof

Existing surface:
  Statblock Workbench

Scenario:
  Open one real mechanics-saved draft on current main.
  Publish.
  Review identity candidates.
  Make an explicit create-new or connect-existing decision.
  Review proposal.
  Confirm.
  Record the exact result.
  Reload the browser and re-open the same draft.

Expected:
  The same publication chain returns.
  No copied identifiers are required.
  A committed revision is never confirmed twice.
  committed_unverified is visibly durable but not called verified.
  The accepted statblock revision remains unchanged.

Evidence:
  Screenshot or concise interaction trace plus exact draft, operation,
  resolution, proposal, commit, Threat, binding, and graph revision IDs in the
  PR handback. Technical IDs belong in evidence, not default product copy.

Baseline failure protocol

If any required test fails on base:

run the exact command on base and head;

record the comparison;

do not call the gate passing;

require an explicit operator waiver if the command remains an acceptance gate.

§8 Required review handback

The code agent/reviewer handback must include:

exact PR URL or branch/head SHA;

mission and invariant copied exactly;

finding IDs resolved;

base and head SHA;

nano-commit list and discrete story;

actual changed paths and focused diff stat;

every §7 result and provenance;

typed non-2xx evidence;

session pointer schema and proof it stores IDs only;

lost-response/reload proof with confirm call counts;

verified and committed-unverified screenshots/traces;

baseline failures and waivers;

paths outside §4, or none;

stop conditions encountered, or none;

named successors still false;

confirmation that only the recorded backend/Kernel contract owners changed; no unrelated Plan, Build, Hermes, Threat Sheet, projection, performance, or style path changed.

Demolition declaration

Replaced path:
  No existing Workbench publication path on base.

Deleted in this PR:
  no

If no, retained reason:
  Backend publication routes and ledgers are predecessors, not replaced paths.

Named remaining consumer:
  Server tests and future agent/shared-capability consumers.

Required deletion owner:
  none

§9 Acceptance rubric

Exactly one capability was delivered: normal governed Threat publication from Workbench.

The exact publication chain remains coherent across all §3 paths.

No identity decision is automatic or label-based.

Exact-name collisions require explicit rejection before create-new.

Proposal review precedes confirmation and uses server authority.

Confirmation creates/reuses one commit ID and cannot duplicate after committed authority is known.

committed_verified and committed_unverified are visibly and semantically distinct.

Typed lifecycle 409/503 envelopes reach the component intact.

Browser reload rehydrates exact IDs without copying durable bodies into browser storage.

Unknown publication_busy is honest rather than guessed around.

Publication never mutates accepted mechanics, editor state, candidate state, or draft version.

Only the recorded Threat publication service/Kernel contract owners entered the corrective PR; no unrelated Plan, Build, Hermes, projection, style, performance, or generic documentation scope entered it.

Every acceptance claim has owning evidence and exact result provenance.

The minimal real dogfood probe completed without direct HTTP or hidden storage edits.

Threat glance, Hermes cards, latency, placement, combat, and verification repair remain unimplemented and unclaimed.

Stop conditions

Stop and report rather than expanding when:

an existing open PR already contains the dogfood publication chrome;

current origin/main changed any predecessor route/model contract;

a new server route/model/service or unrelated Kernel change is required;

recovery requires a new “list active publication chain” endpoint;

the session pointer must store proposal bodies, candidate sets, graph objects, or mechanics;

Workbench cannot isolate publication from editor/acceptance state;

committed-unverified semantics are contradictory in current server tests;

a second host or generic publication framework is proposed;

presentation styling, Hermes output, latency work, Plan refresh, Build insertion,placement, or combat becomes necessary to prove this mission;

any path outside §4 is required.

Use this report shape:

Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
</user_query>
