---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI Presentation Substrate Sidequest
  - Flow: UI
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-UI-toolhost-presentation-split.md
  - Branch / PR: docs/ui-toolhost-presentation-split / #758
  - PR topology: stacked provisional review on #771

  ## Verification pointer
  - Review parent: #771 exact implementation head f505921aa822fb4e1dd951519b12c8e1bfd6fefa
  - Changed paths: exact §4 allowlist only
  - Verification: existing ToolHost behavior suite + new view tests + typecheck/build + diff checks

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — UI ToolHost presentation split

**Created:** 2026-09-25  
**Status:** PROVISIONAL IMPLEMENTATION REVIEW IN PR #758 — not ACTIVE on `main`; do not merge before predecessor review and re-anchor
**Canonical handoff path:** `Docs/Plans/HANDOFF-UI-toolhost-presentation-split.md`  
**Conversation/workstream:** `UI Presentation Substrate Sidequest`  
**Flow / owner:** `UI`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `bbd3112053a6ac61356a9d3157d3e2be09cab42c` — UI-F2 design head  
**Provisional review parent:** #771 exact head `f505921aa822fb4e1dd951519b12c8e1bfd6fefa`; #758 is the existing handoff PR, now carrying its implementation
**Merge gate:** UI-F2 accepted/merged, then re-anchor this PR on current `main` and review the new exact head
**PR topology:** stacked provisional review experiment; merge order remains UI-F0 → F1 → F2 → F3
**PR authorization:** user explicitly directed implementation on this existing PR; do not open or merge another PR
**PR title:** `UI: separate ToolHost presentation`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

**User-directed review experiment, 2026-09-26:** The implementation lives in the
same unmerged PR as this handoff so the designing agent can review the actual
slice before any merge. This is PR-local scope, not an ACTIVE `main` write lease.
The original serial activation wording below records the normal merge route;
for this experiment, predecessor review/merge is a *merge gate*, not a reason
to invent another implementation PR. No current-slice completion is claimed.

## §1 Mission and merge-ready invariant

**Mission:** The shared ToolHost can replace its visual composition without rewriting lease, activation, focus, or stale-state behavior so that later UI experiments are presentation changes rather than interaction-kernel changes.

**Merge-ready invariant:** Existing ToolHost runtime behavior remains byte-for-byte equivalent at the observable level while state/authorization/activation remains in the controller boundary and the rendered toggle/drawer/peek structure plus ToolHost-specific CSS moves behind one presentation component with no new authority or behavior.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every current ToolHost success/failure/identity path must remain equivalent; the sole new capability is replaceable presentation ownership. |
| Most likely adversarial sequence | Split JSX → view captures tool objects/callbacks → same-identity publication replaces invoke or removes tool → stale view activates captured behavior. |
| Will §7 actually detect that failure? | Yes. Existing same-ID replacement, authorization loss, async activation, identity-switch, and Peek tests remain mandatory at the integrated ToolHost boundary. |
| Easiest owning boundary to under-test | Focus restoration and async activation after the rendered button disappears/re-authorizes. |
| What PR topology is authorized, and why is it safe? | Serial. ToolHost and global styles are shared shell hotspots. |
| Fact that forces stop/split | Separation requires moving lease/activation logic into the view, changing ToolHost behavior, or touching EditHost/ProjectionHost/AppChrome beyond style import ownership. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | Surface Interaction architecture; UI Presentation Substrate plan |
| Design authority base | `bbd3112053a6ac61356a9d3157d3e2be09cab42c` |
| Provisional review gate | UI-F2 implemented at #771 head `f505921a`; merge remains gated on predecessor acceptance |
| Review base | exact #771 implementation head; later re-anchor on fresh `main` before merge |
| Predecessor contract | singular app-level `ToolHost`; `SurfaceInteractionPublication.tools`; `activateToolContribution`; `groupToolContributions`; Peek placement behavior |
| Exact input consumed | current effective SurfaceInteraction publication + ToolHost local open/focus state |
| Named successor | UI-F4 — canonical visual fixture/screenshot contract |
| What remains false | EditHost still combined; Agent dock still combined; ToolHost visual redesign not attempted; no new tool behavior |
| Explicit non-goals | new Tool types; command palette; Base UI adoption; ToolHost redesign; AppChrome redesign; EditHost split; projection semantics |
| PR topology | stacked provisional review on existing #758; serial merge order preserved |
| Authorized PR action | update #758 only; no new PR or merge |
| Open implementation PRs in workstream at dispatch | #770 F1 and #771 F2, both unmerged |
| Stack parent + merge/rebase order | #771 exact head `f505921a`; F0 → F1 → F2 → F3 |
| Branch / isolated checkout | existing #758 branch in isolated worktree |
| Parallel lanes / collision hotspots | `ToolHost.tsx`, `ToolHost.test.tsx`, `styles.css`, `surfaceInteraction/**` are shared-shell hotspots |
| Runtime/state ownership | existing AgentInteractionProvider/SurfaceInteraction lease remains sole runtime owner |
| State-authority sync set after merge | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` records UI-F2 completed predecessor / UI-F3 current |

Read before implementation:

1. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
2. `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.tsx`
3. `ToolHost.test.tsx`
4. `activateToolContribution.ts`
5. `groupTools.ts`
6. ToolHost-specific rules in `apps/live-control-ui/src/styles.css`
7. UI-F1 primitive/token result (available but not required for behavior-preserving extraction)

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Empty tool inventory | Host absent | identical | Yes | ToolHost integration |
| Open/close legacy drawer | toggle/backdrop/drawer + focus return | identical | Yes | ToolHost + view |
| Ingest Peek tools | Tool content claims Peek; no backdrop | identical | Yes | ToolHost + Peek |
| Group ordering | deterministic placement order | identical | Yes | existing group helper + view |
| Disabled tool | disabled reason; cannot activate | identical | Yes | activation/controller |
| Command tool | current invoke resolved at click time | identical | Yes | controller/lease |
| Projection tool | current tool id opens authorized projection; launcher closes on success | identical | Yes | controller/Provider |
| Identity switch | open state closes/revalidates | identical | Yes | controller |
| Same-ID callback replacement | newest callback runs | identical | Yes | controller/lease |
| Async auth loss | stale completion cannot resurrect/mutate wrong state | identical | Yes | controller |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Open Tools → replace same-ID command callback → click | newest guarded invoke only | existing ToolHost test |
| Start async projection activation → authorization removed before completion | no unauthorized projection/URL mutation; focus remains valid | existing async regression tests |
| Open on Plan → bind empty Build identity | ToolHost disappears; no stale drawer | existing identity-switch test |
| Open Ingest Peek → dismiss via Peek navigation | Peek closes and underlying ToolHost state is consistent | existing Peek test |
| Open drawer → Escape | closes and returns focus to toggle | existing focus test |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.tsx` | Retain controller/state/lease logic; delegate rendering |
| Create | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHostView.tsx` | Replaceable presentation-only DOM boundary |
| Create | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHostView.css` | ToolHost-specific presentation styles moved out of global stylesheet |
| Create | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHostView.test.tsx` | Pure presentation contract tests |
| Modify | `apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.test.tsx` | Preserve integrated behavioral regression proof after split |
| Modify | `apps/live-control-ui/src/styles.css` | Remove only ToolHost-specific styles that move to view CSS; no unrelated paint |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Backward-looking predecessor sync |
| Modify | `Docs/Plans/HANDOFF-UI-toolhost-presentation-split.md` | Record the user-directed same-PR review topology truthfully |

**Bounded discovery exception:**
```text
Directory: apps/live-control-ui/src/surfaceInteraction/toolHost/
Maximum additional paths: 1
Allowed path kinds: one presentation-only type/helper module
Decision rule: required solely to keep ToolHostView props/readability bounded; no lease/activation behavior
```

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/surfaceInteraction/editHost/**` | EditHost split is separate evidence if later needed |
| `apps/live-control-ui/src/surfaceInteraction/projection/**` | Projection semantics unchanged |
| `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | Lease/runtime owner unchanged |
| `apps/live-control-ui/src/chrome/AppChrome.tsx` | No shell redesign |
| `apps/live-control-ui/src/ui/ObjectSheet*` | F2 presentation pattern is predecessor evidence, not ToolHost scope |
| Base UI | No new interaction mechanic needed for a behavior-preserving split |

## §6 Implementation contract

```text
Input:
  current effective SurfaceInteractionPublication
  controller-owned open/identity/focus state
  deterministic grouped tools

Output:
  same user-visible ToolHost behavior rendered by ToolHostView

Invariant:
  same as §1

Failure behavior:
  missing/disabled/stale tool → controller refuses activation exactly as before
  missing inventory → host absent
  view callback → delegates only to controller-provided current handlers

Replay / idempotency:
  same publication/state → same presentation
  same identity + changed callback/inventory → controller re-resolves current behavior
  identity replacement → old view cannot activate

Trust boundary:
  Verifies: controller is current lease/activation authority
  Records/trusts without proving: visual quality of later ToolHost redesigns
```

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| ToolHost | no special loading | render authorized inventory | empty → no host | projection activator false → keep/restore truthful launcher state | invalid publication already fails upstream | identity/inventory change closes/revalidates | current publication re-evaluated |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Surface identity | exact `surfaceId + instanceKey` via existing helper | none | No |
| Tool id | click resolves exact current id from publication | missing → ignored | No label fallback |
| Label | display only | n/a | Never identity |
| Identity replace | close old open state before/with new inventory | n/a | No stale resurrection |

### C. Persistence / replay matrix

Not applicable — ToolHost open state is transient and not newly persisted.

### D. Predecessor → consumer mapping

**Grounding source:** existing `ToolHost.tsx`, `SurfaceInteractionToolContribution`, and `ToolHostGroup`.

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| tool label/eyebrow | strings, eyebrow optional | render button copy | none | view test |
| placement groups | deterministic helper output | render ordered groups | no re-sort in view | group test |
| availability | enabled/disabled with reason | button state/title | none | integrated test |
| activation | controller only | view emits tool-id intent; controller activates | no captured invoke in view | same-ID replacement test |
| Peek placement | surfaceId ingest currently selects Peek | view presentation placed by controller/PeekClaim | no route authority in view | Peek test |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Current lease owns activation | ToolHost integration | adversarial/regression | full `ToolHost.test.tsx` | all existing stale/replacement tests PASS | any behavior drift |
| View is presentation-only | ToolHostView | contract | focused view tests + source review | props/callbacks only; no AgentInteraction/provider/activation imports | view imports authority layer |
| ToolHost CSS is localizable | CSS boundary | regression | source/diff inspection | moved ToolHost selectors live in view CSS; unrelated global CSS unchanged | broad styling churn |
| Production frontend remains green | frontend | regression | typecheck/build/full relevant Vitest | no new failures | new failure |
| Exact lease | Git | contract | diff checks | only §4/bounded path | unexpected path |
| User-visible equivalence | existing product harness | manual/dogfood | Plan drawer + Ingest Peek basic smoke | same open/close/Peek/focus behavior; deliberate no visual redesign | interaction/placement change |

Exact commands:

```bash
npm --prefix apps/live-control-ui run test -- src/surfaceInteraction/toolHost/ToolHostView.test.tsx src/surfaceInteraction/toolHost/ToolHost.test.tsx
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal live / dogfood proof

```text
Existing surfaces: Plan Tool drawer + Ingest Tools Peek
Smallest realistic scenario: open/close Tools, launch one command/projection, switch surface, repeat on Ingest Peek
Expected observation: behavior and placement are interaction-equivalent to base
Evidence captured: reviewer records any visual/interaction delta; intentional redesign is not allowed in F3
```

### Baseline failure handling

Same-command base/head comparison required for any existing failure.

## §8 Required review handback

Record exact head/base, ToolHost controller/view responsibility split, actual moved CSS selectors, full pre-existing ToolHost regression results, view source-boundary result, manual equivalence notes, and any behavior delta. Any behavior delta requires explicit steward review rather than being called refactor noise.

## §9 Acceptance rubric

- [x] UI-F2 exact unmerged review head and F1/F2 presentation APIs recorded; merger remains gated on predecessor review.
- [ ] ToolHost remains the runtime/controller owner.
- [ ] ToolHostView owns presentation only.
- [ ] View cannot activate a captured stale contribution directly.
- [ ] Existing identity/async/focus/Peek tests pass.
- [ ] ToolHost-specific CSS is no longer mixed into unrelated global styling except unavoidable shared shell rules.
- [ ] No EditHost/Projection/AppChrome behavior changed.
- [ ] No visual redesign was smuggled into the split.
- [ ] UI-F4 remains false.

## Stop conditions

Stop if:

- ToolHost semantics changed materially since design;
- controller/view split requires provider changes;
- focus/async stale behavior cannot remain covered at ToolHost integration boundary;
- CSS selectors are shared with unrelated components such that extraction becomes a broad design rewrite;
- EditHost or AppChrome must be modified to complete the split;
- a new headless library is proposed simply to perform the extraction.
