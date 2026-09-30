# DEMO — World Plan editing controls in AppChrome EditHost

**Status:** MERGED — Buddy #802, reviewed head `1cc18982bb4e1db4bfbc13ab383761c3a8f64bb8`, merge `118e680244ab830c24c0f7cfa12f636ac303e034`

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), operator-approved third serial World Plan slice

**Pinned predecessor/base:** Buddy #801 reviewed head `550aa4c0251ffa08477bda2293829725f2d6a8d8`, merged as `442ee470a33ce4dfa0ba3239c9022ab69220cde9`; fetched `origin/main` at that merge

**Proposed branch/checkout:** `codex/demo-world-plan-edithost` in `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy`

**Topology:** serial. #800 switch safety and #801 exact World Plan identity are merged. No parallel DEMO Plan page lane is active. Closed #793 is reference-only; its visual styling remains parked.

## One capability and failure cases

The World-owned Plan already publishes one exact saved-document or World-scoped
local-draft canvas work object. Consume that same work object in one
`AppChromeToolsGeneration` inventory. Put Plan title editing and Save in the
existing EditHost, alongside the current formatting and callout insertion
commands. Keep saved-Plan selection in the existing World Plan context area and
the editor body on the central canvas. Remove duplicate inline title, Save and
toolbar controls from the content area. Keep actionable recovery/conflict
decisions and errors visible beside the relevant Plan until their owning host is
ready; do not hide them in collapsed metadata.

Every EditHost command or title callback must validate the currently mounted
World, work object, document/local draft, and editor generation at click/change
time. A held callback from an old document, old blank draft, save promotion,
World replacement or unmount is inert. The active Save command uses the current
title/body/revision and existing create/prepare/commit/conflict/recovery path;
moving it must not change those durable semantics. During an unresolved saved
document load, no old command remains actionable. AppChrome receives exactly
one target-matching edit inventory for the current canvas publication. Shared
publisher, lease and EditHost implementation contracts remain read-only.

Do not use visual acceptance of the rejected #789 canvas as a prerequisite for
this functional placement repair. This slice keeps the current canvas theme;
any separate appearance decision remains with the operator/PRIME.

## Proposed exclusive expected write lease

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanEditHost.integration.test.tsx` — mounted real AppChrome/EditHost witness, if a distinct test is needed
- `apps/live-control-ui/src/styles.css` — only World Plan title/control placement styles needed by the EditHost composition
- `Docs/Plans/HANDOFF-DEMO-world-plan-edithost.md`
- `Docs/Plans/HANDOFF-DEMO-world-plan-identity.md` — only backward-looking #801 result/status settlement
- `Docs/Roadmaps/ROADMAP-demo.md` — #801 settlement and this slice's execution evidence

`AppChrome.tsx`, `EditHost.tsx`, neutral Surface publication/lease/host files,
shared toolbar conversion, package dependencies, lockfiles and all other
repository paths are read-only. Current open Buddy PRs #798, #781, #763–765
and #760–761 were inspected after #801; none owns the proposed paths. Return
to PRIME before editing if the required write set exceeds this lease.

## Runtime and acceptance witness

No server, port, database, schema, corpus or external state is leased. Use
mocked Plan APIs at the mounted World Plan → AppChrome → EditHost boundary,
including the required `PeekRegionProvider` in the real host harness. Existing
`AppChrome.surfaceInteraction.test.tsx` failures without that provider are an
inherited harness setup issue, not proof of this capability. Prove one matching
inventory, title/Save/format/insertion through EditHost, no duplicate inline
controls, exact current-at-click writes, inert held callbacks after each
replacement/promotion/unmount, and a 390×844 close/reopen click path with
controls still reachable. Retain the #800 and #801 focused regressions. Review
the cumulative base-to-head diff, focused tests and UI typecheck; label any
inherited failures. A mocked host witness does not self-award operator visual
acceptance or the connected DEMO journey.

**Activation gate:** PRIME critiqued the exact pushed design head and authorized
ACTIVE implementation. Complete one bounded PR and return its
exact reviewed head, evidence and remaining gates to PRIME for merge control.

## Author verification

The mounted World Plan page and context regressions plus the real
World Plan → AppChrome → EditHost integration witness passed 19/19 focused
tests. The real host test exercises title, Save, formatting, insertion,
target-matched inventory, no inline duplicates and Edit close/reopen at
390×844. Held title/Save/format callbacks were checked after saved-document
replacement, blank-draft rotation, World replacement, local-to-saved
promotion and unmount. UI typecheck reports only the inherited
`ThreatPublicationPanel.tsx:553` JSX namespace error outside this lease.
No runtime, service, database, corpus or provider was used; operator visual
acceptance and the connected DEMO journey remain outstanding.

**Settlement:** PRIME independently reviewed the exact cumulative seven-path
diff and reran the 19 focused tests at the accepted head. The remaining
typecheck error was inherited. The EditHost functional lease ended at merge;
the rejected Plan appearance and six-surface Agent UI remain open.
