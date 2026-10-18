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
API. Runs may pin a Plan as their Runbook; after a Runbook-kind 404,
read only the identical document ID and revision through the existing Plan
reader, then verify World, kind, WorkRevision and SHA before display. No fallback
on authorization, conflict or server errors. Do not infer titles from the answer, fetch current/latest material, claim
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

## Implementation evidence

24 focused source-reader tests pass, including Plan-as-Runbook, foreign source,
exact WorkRevision/digest mismatch, navigation and unmount. The new mounted
Build/shared-history regression passes. Across the two complete suites, the
initial patch passed56 tests with7 failures; the same7 failures reproduce on
exact origin/main (37passed/7failed), with no new failures. The additional six
Plan fallback cases pass. TypeScript and production Vite build pass; the latter
retains inherited chunk-size warnings.

The actual displayed turn is e6ca3694-f8a7-4c6b-924e-322815152061. Its history
retains Run9bbd98e1-ebaa-4a3f-92e9-f51db8268c73 and Plan-as-Runbook
3aa3df48-533c-44be-9ef8-2162e8d21196 revision2, WorkRevision
73535c5a-0333-48b9-8171-ff0fc1c0dd3a, SHA
e94284a104cc123bdb98ddad6dd541d65bcb35e682a035257b1df7a5a22c2a03.
A read-only live exact-revision GET returned200, correct World and hash, and
the Arrival at Mirathorn / The lakeside approach source text (846characters).
The dedicated Runbook endpoint returns404 for this Plan; the explicitly bounded
Plan reader handles that kind distinction. No current source substitution.
The turn context-trace endpoint returns attempts=[]; no trace reconstruction is
claimed. Review, merge and live rendered delivery remain outstanding.
