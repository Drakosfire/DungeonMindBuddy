# BUILD: show retained Play context in answer evidence

Status: ACTIVE — PRIME owns this user-requested Evidence Trail repair.
Base: origin/main@1b6258e304e96cd87b485785422310e0b4801120.
Topology: serial, one PR. Reuse buddy-context-loop checkout and dependencies.
DOGFOOD owns read-only Session26 review in996b; it has no overlapping code lease.
Open historical PRs remain held; no active implementation reservation on these paths.

## Capability and critique

The displayed Play answer has no knowledge_context or Graph citations but retains
Run, exact Runbook WorkRevision, current Beat and Scene references in provenance.
Evidence Trail must show these original references and offer a deliberate read
of the exact pinned Runbook through the existing World-scoped committed-revision
API. Do not infer titles from the answer, fetch current/latest material, claim
Graph citation coverage, or reconstruct missing context traces. Clearly separate
authored preparation from recorded events and distinguish reference provenance
from claim-level source citations.

Pin reads to World, Runbook, revision number, SHA and WorkRevision ID. Verify
returned markdown SHA and identity before display. Fence stale requests on turn,
World, basis changes and unmount. Malformed, duplicate, missing and cross-World
references must not trigger reads; show unavailable status. Existing Graph and
Build passage evidence remains intact. No new endpoints, models, provider calls,
retained writes, Run changes or synthetic Graph citations.

## Exclusive write set

- This handoff
- apps/live-control-ui/src/planSurface/components/PlayAnswerEvidence.tsx
- apps/live-control-ui/src/planSurface/components/PlayAnswerEvidence.test.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx

## Verification and delivery

Exercise mounted historical Play evidence and unchanged Plan/Build history.
Owning component tests cover exact source read and hash, World/WorkRevision/pin
mismatch, duplicate references, empty/missing provenance, stale completion and
unmount. Typecheck, production build, cumulative diff inspection, commit/push/PR.
Independent review before PRIME merge and5202 static rollout preserving assets,
operator tab and drafts. Live read of the exact displayed turn proves retained
Runbook access; no new inference or current source substitution. Missing trace
capture is separate and must remain honestly unavailable.
