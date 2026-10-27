# PLAN — preserve protected capture across editor round trips

Status: ACTIVE. Owner: PRIME. Topology: serial, one implementation PR.
Authority: operator-authorized goal work and the explicit 2026-10-27 direction
that an ADVERSARY blocker does not block authoring/preparation/play acceptance.
Base: origin/main 5e4bd3eb027465e9202de511816eac76cd6a44ff.
Lane: codex/plan-playable-capture in the existing buddy-context-loop checkout.
This committed handoff is the pinned bounded write lease; no new checkout.

## Observed failure and invariant

Ordinary Conks Plan navigation selects the descent Scene. An explicit request
to discuss a guardian without editing is refused before provider dispatch:
“This Plan draft changes structure during Markdown reload and is unavailable
for card edit proposals.” The clean saved Plan has one Beat, five Scenes and
an ordinary social-leads table. The composer retains the unsent request.

Capture must compare semantic content across parser/editor representations,
including schema-default attributes and adjacent equivalent inline runs, while
preserving text, meaningful marks/attributes, playable identities, protected
references, target ranges and untouched siblings. Keep round-trip warnings and
real structure changes fail-closed. Do not bypass capture for this question,
remove the full-document guard, or repair retained Plan content manually.

Independent invariant critique: existing Bugbot response-contract reviewer
confirmed the invariant and identified divergent semantic projections as a
candidate false refusal. A red rendered-editor regression must establish the
actual discrepancy before selecting the smallest owning-boundary fix.

## Expected write set

- apps/live-control-ui/src/planSurface/agentEdit/planPlayableBodyTarget.ts
- apps/live-control-ui/src/planSurface/agentEdit/planPlayableBodyTarget.test.ts
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts
- One internal shared semantic-comparison module in that agentEdit directory,
  only if needed to eliminate divergent implementations.
- Docs/Plans/HANDOFF-PLAN-playable-capture-roundtrip.md
- Docs/Roadmaps/ROADMAP-demo.md for truthful delivery/sequence settlement.

If the red regression proves a distinct parser/codec defect outside this set,
PRIME must amend and pin the contract before implementation. No model, provider,
authority schema, database migration, generated mechanics or encounter changes
belong in this PR. No added compatibility execution or arbitrary limits.

## Runtime and verification

Reuse installed UI dependencies. Ports 8000/5202 stay on their reviewed runtime
until exact-head verification, independent Bugbot review and PRIME merge permit
protected UI delivery. Preserve APP/native databases, sources, corpus, drafts,
versions, scenes and the existing empty descent encounter. No database repair.
ADVERSARY owns independent fixtures/audits; its provider holds are action-local.

Prove a real rendered synthetic marked Plan containing ordinary tables can be
captured; include a selected body and an unaffected sibling table. Exercise
proposal preparation/application and Save/reload serialization. Negative tests
must reject changed marks, playable identities, references, sibling text and
unsupported/lossy structures. Run affected capture/codec tests and UI typecheck;
inspect the exact cumulative diff and obtain independent review of its head.
Commit/push/open the assigned PR, merge under PRIME gates, then protect/deploy
5202 and resume the retained ordinary Conks question. A successful discussion
alone does not prove editable proposal preservation or broader J1–J6 acceptance.
