# DEMO — Plan document-switch safety

**Status:** MERGED — Buddy #800, reviewed head `d64a9745fdc751360468266323489a18d2579ee1`, merge `393ec5664916ee4eeabe0d0801bc6c8de9820c79`
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md) on fetched `origin/main@b82c25fe4cce7c1e560850c2db020cff648d4913`
**Topology:** serial; this slice lands before exact World Plan identity and EditHost controls
**Branch/base:** `codex/demo-plan-switch-safety` / `b82c25fe4cce7c1e560850c2db020cff648d4913`
**Checkout:** `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy`

## Invariant and failure case

When a GM selects a different saved World Plan, the outgoing editor and title
must stop accepting edits before the incoming snapshot resolves. No outgoing
update callback may persist content during that pending switch. The outgoing
local draft stays intact until the new snapshot is accepted; the incoming Plan
loads its own title, body and revision. This prevents a late edit from being
recorded against the wrong document. A failed load leaves the old editor inert
until the GM chooses a valid Plan or a new blank Plan.

The current page sets a loading status but leaves TipTap editable and accepts
its updates while the snapshot is pending. A delayed-snapshot mounted witness
exercises that failure at the owning Plan UI boundary. The repair closes the
editor synchronously on selection and guards title/editor persistence while
loading. It does not change save/recovery semantics or document identity.

## Exclusive expected write lease

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-plan-document-switch-safety.md`
- `Docs/Plans/STEWARDS-HANDOFF-demo.md` — only the backward-looking owner transfer
- `Docs/Roadmaps/ROADMAP-demo.md` — only this slice's current state and evidence

Shared context publisher, AppChrome/EditHost contracts, package lockfiles and
other repositories are read-only. Buddy open PRs #798 and #781 were inspected at
activation and do not edit these paths. Closed #793 is reference-only; its
branch, checkout and licensed corpus remain untouched.

## Runtime and verification

No server, port, database, schema, corpus or external state is leased. Tests use
mocked Plan APIs and browser-local storage. Verify a delayed second snapshot
while the first Plan is mounted: the first editor/title become inert, its local
draft remains intact, and the second Plan opens with its own title, body and
revision. Run the focused Plan page suite, UI typecheck and cumulative
base-to-head diff. Record inherited failures separately. No live database is a
gate for this bounded UI invariant; the connected DEMO rehearsal remains a
later milestone under its designated runtime owner.

PRIME's first exact-head review held the handoff allowlist; the corrected head
passed independent focused review and 9/9 mounted Plan page tests. UI typecheck
retained the inherited `ThreatPublicationPanel.tsx:553` JSX namespace error,
outside the cumulative diff. The exclusive Plan page lease was released by
merge. The connected DEMO journey and operator appearance acceptance remain open.
