# PLAN — current integration contracts

SHIPPED #1646, merge5a534527b. Bugbot approved exact head
7f3b87e20e9702741997024244cd8c07f708f3e8 in one cycle. Independently125 owning
checks passed; author246 combined checks and UI typecheck/build passed. Mutation
control removing all23 malformed response mutations made every corresponding
negative test fail. No production files changed; existing5202/API health passed.

Historical authority: serial PRIME slice onbaf0a6644c33c6ab1fcdedc0687511e5545c3687,
branch codex/plan-current-integration-contracts, existing buddy-context-loop checkout.
One Bugbot-reviewed PR, PRIME merge. Tests/documentation only; existing API/UI on
8000/5202 stay unchanged unless a separately bounded runtime defect is identified.
No overlapping open lane in the fetched census.

The exact-base save→Start verification exposed52 inherited failures:50 in
PlanSurfacePage.test.tsx and2 in WorldPlanCardProjection.integration.test.tsx.
The current main/live product supports direct scene cards, shared Contents and
World conversation; these tests still assume removed outline destinations, v1
playable authoring, old conversation regions and diagnostics presentation.

Outcome: make the owning mounted Plan/Card suite verify current behavior. Update
fixtures and UI interactions at current boundaries; retain meaningful checks for
immutable Plan/scene identity, draft/undo continuity, exact request/response joins,
server-owned history and lazy Debug. Replace obsolete authoring paths with current
v2 markers and source/scene navigation; historical read contracts remain owned by
their existing historical tests. Do not restore old runtime routes, introduce test
compatibility shims, weaken strict refusal assertions, delete failures merely to
get green, or replace rendered checks with helper-only tests. Wait for real ready
state and use shared current app hosting where required. No private story data.

Critique: bulk label substitution can hide a missing provider or loading race;
inspect each failure family and assert the current interaction's result. Removal
requires identifying its retired contract and preserving the invariant elsewhere.
Any runtime behavior defect returns to PRIME for an explicit scope amendment.

Writes: this handoff; HANDOFF-PLAN-saved-authoring-handoff.md settlement;
Docs/Roadmaps/ROADMAP-demo.md factual settlement;
apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx and
WorldPlanCardProjection.integration.test.tsx. No production edits authorized here.

Verify full two-file mounted suites plus shared session preparation/current
conversation integration where relevant, typecheck/build and exact cumulative
Bugbot review. Settle #1645's delivered facts truthfully. Ordinary connected Sheep
flow passed once including restart, saved notes and closing reflections; full
J1–J6 twice, real recorded rolls/images, memory publication and performance remain
open. A green suite does not complete those journeys.

Retired test mapping: v1 card-authoring/outline/Select-for-Ask UI cases become
current v2 focused-scene request/basis and pending-verification freeze witnesses.
Historical carrier/read tests remain in their owning suites; no runtime v1
authoring path is restored. Shared scene position is sessionStorage, so fresh
fixture teardown clears it while within-test reload/continuity witnesses retain it.

Current recovery mapping: malformed-delivery fixtures must not simultaneously
invent a valid durable history acknowledgement. Refuse the wire answer, preserve
the exact original request in pending recovery and avoid automatic retransmission.
The cross-document witness uses the real shared World conversation provider/host;
completed historical output retains its original Plan provenance. Isolated Plan
component tests keep the documented standalone registration harness. A saving
Plan may retain an editable composer draft while Send stays disabled. Current
semantic Markdown rejects hard breaks in headings; ordinary paragraph hard breaks
are supported and are not a valid refusal fixture. Graph peeks retain the same
editor/node identities through Document/Cards and do not write document content.
