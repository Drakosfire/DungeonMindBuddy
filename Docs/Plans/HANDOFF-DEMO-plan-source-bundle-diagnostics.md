# HANDOFF — DEMO: clarify Plan source-bundle diagnostics

**Status:** COMPLETE — Buddy PR #839 merged at
`47f9955fd054017a1739dfa8129df65dd61d6bcd` from reviewed head
`fccb75c5ce5392681bdbaf14beb15b79be220ecc`.

**Steward:** DEMO

**Base:** Buddy `origin/main@012ff01acc4e490601f4993644903689af2708c4`.

**PR title:** `DEMO: clarify Plan source-bundle diagnostics`

## User-visible outcome

The collapsed Plan Ask diagnostics drawer must say what its status checks and
which session it scans. The current `PlanAgentInteractionBar` loads the legacy
campaign source bundle and computes its layer checklist from
`sessionDescriptor.liveSession`. The selected Plan target is the separate
`planningDocument.targetSession`; World Graph retrieval focus is the separate
`memorySession`. At the reproduced dogfood checkpoint the Plan targets Session
23 while the source-bundle scan reports live Session 22, yet the drawer is
called “Memory coverage diagnostics” and its result can be mistaken for Graph
coverage or Session 28 admission.

Rename the drawer and layer section to identify the source bundle. Show the
exact live session being scanned, the Plan target, and the World Graph focus as
separate values. State that source-bundle layers do not report native Graph
evidence or recap admission. Do not claim anything about Session 28's current
Graph state.

## Scope and write lease

This is presentation-only. Preserve the existing source-bundle request/session,
Plan target and Graph focus behavior. Do not change Ask results, Graph
retrieval, ingestion/admission, Plan persistence, citations, provider payloads,
or external contracts.

Only this lane may edit these paths:

- `Docs/Plans/HANDOFF-DEMO-plan-source-bundle-diagnostics.md`
- `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`

No API server, provider, port, database, or Graph runtime is used. Run the
mounted UI regression and inspect the exact cumulative base-to-head diff.

## Topology and collisions

**Topology:** parallel-independent with Buddy PR #836 at head
`18c5de19cb481742206f7c8c3cdfdc97a9097f77`. The work has no unmerged
behavioral dependency on the managed-World binding. #836 owns its server,
registry, handoff, and roadmap paths; this lease owns only the three paths
above. The paused draft PR #826 overlaps #836's server registry paths, not this
UI lease. Refreshed open-PR path comparison found no other overlap with this
lease. Recheck exact heads and paths before push or dispatch.

`Docs/Roadmaps/ROADMAP-demo.md` is currently in #836's exclusive write lease;
do not edit it here. After #836 settles, DEMO must re-anchor and record this
slice's actual merged status and witness in the roadmap before dispatching a
dependent Plan Agent slice. Do not pre-mark completion or invent a merge SHA.

## Acceptance

- The collapsed drawer is named **Source-bundle diagnostics**.
- With Plan target Session 23 and live session 22, the mounted view explicitly
  reports a source-bundle layer check for live Session 22, Plan target Session
  23, and the current Graph focus independently.
- Those scope labels remain visible if the source-bundle request is loading or
  fails.
- The explanatory copy says that the source-bundle layer check does not report
  native Graph evidence or recap admission.
- Existing source-bundle request pins and ordinary Ask behavior remain
  unchanged; the test exercises the same loaded bundle used by the current
  panel.
- Mounted Plan shell regressions passed **2/2** under bundled Node v24.19.0:
  the session-22/target-23 source-bundle view and the source-bundle error state
  both retain the distinct session labels.
- UI `tsc -b` reports only the inherited out-of-lease
  `ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`;
  that file is unchanged from the pinned base. No formatting script is
  configured in the UI package; `git diff --check` passes.

At completion, commit the intended diff, push this branch, open one PR, and
send PRIME its exact head and verification evidence. PRIME owns review and
merge; DEMO does not merge.


## Settlement — 2026-10-02

Buddy PR #839 merged at `47f9955fd054017a1739dfa8129df65dd61d6bcd` from
reviewed code head `fccb75c5ce5392681bdbaf14beb15b79be220ecc`. The mounted
Plan shell regressions passed 2/2 under bundled Node v24.19.0, and the
cumulative diff check passed. UI `tsc -b` retains the inherited out-of-lease
diagnostic `ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace
'JSX'`. No server, provider, database, or Graph runtime was used. PRIME reports
an exact-head review; GitHub currently exposes no submitted review record and
no commit status or check run. The implementation lease ended at merge.

The ROADMAP-demo.md sync remains sequenced after PR #836 releases its exclusive
roadmap path lease. Re-anchor before making that backward-looking update.
