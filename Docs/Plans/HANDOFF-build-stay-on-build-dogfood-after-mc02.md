# HANDOFF — Build stay-on-Build dogfood after MC-02a

> **RE-ANCHOR (2026-08-01):** MC-02a / PR #431 (`graphReference`) is **MERGED**
> (`130104442b0ac7ad9a56c7e744014f1b8d56ad62`). This handoff is a **named successor**
> for stay-on-Build behavior — dispatch after SI-04 Build World Reference Loop per
> [`PLAN-surface-interaction-hoist-build-first.md`](PLAN-surface-interaction-hoist-build-first.md).

**Created:** 2026-07-31
**Status:** NAMED SUCCESSOR — dispatch after SI-04 (Build World Reference Loop); #431 gate cleared.
**Source PR:** #432 head `5cdcd107e50cc89f16e44c4072705549e28d696e`
**Salvage ledger:** [`REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md) §#432
**Predecessor gate:** #431 merged — [`HANDOFF-pr431-surface-neutral-graph-reference-loop.md`](HANDOFF-pr431-surface-neutral-graph-reference-loop.md). Next gate: SI-04 in hoist plan.

---

## §1 Mission (salvageable behaviors)

After SI-04 composes Build over the shared interaction hosts, Build can dogfood
stay-on-Build workflows: graph-reference search/insert using the shared
`graphReference` package, exact-run extraction summary/inspector, and Find-existing
handoff — **without** importing Plan surface state or obsolete
BuildGraphReferenceShell architecture.

**Invariant (when dispatched)**

```text
Build uses surface-neutral graphReference contracts from #431; extraction inspector shows exact-run truth;
operator remains on Build surface through inspect/summary; no auto-starter content as product.
```

---

## §2 Behaviors to reimplement (after #431)

| Behavior | Reference on #432 head | Successor slice |
|---|---|---|
| Build graph-ref search/insert | `buildGraphReference.test.tsx`, toolbar wiring | SI-04 Build config over #431 contracts |
| Stay-on-Build inspector | `BuildExtractionRunInspector.tsx` (+ tests) | Stay-on-Build milestone |
| Exact-run summary panel | `BuildExactRunSummary.tsx` | Same milestone |
| Find existing handoff | `buildFindExisting.ts` | MC-02b / candidate-assisted Find existing |
| Build surface shell integration | `BuildSurfaceShell.tsx`, `BuildSurfacePage.tsx` | Truthful Build lens only |

**ALREADY_PRESENT on main:**

- Plan `PlanGraphRefSearch` (Plan-side reference search)
- Basic Build extract + Graph Review handoff path

---

## §3 Explicitly rejected from #432 (do not implement)

| Capability | Why rejected |
|---|---|
| `BuildGraphReferenceShell` | Obsolete; replaced by #431 `graphReference` package |
| Plan-import architecture | Superseded by surface-neutral extraction |
| Auto Mireward starter as product | `buildWorldbuildingStarter.ts` — not a product requirement |
| Rebasing #432 stacked head (~1.7k lines) | Fresh slices from this handoff only |

---

## §4 Related named successors (still false)

| Successor | Relationship |
|---|---|
| MC-02a (#431) | **Landed prerequisite** — surface-neutral graph reference loop |
| SI-04 | Build World Reference Loop over shared hosts |
| Stay-on-Build | This handoff's primary milestone |
| BLD inspection-truth | Build inspector contract alignment |

---

## §5 Dispatch gate (future)

Do not dispatch until:

1. SI-01–SI-03 characterize and compose the shared hosts without Plan-owned bars.
2. Capability decomposition splits inspector vs Find-existing vs graph-ref enablement (do not monolith #432).
3. Dogfood plan written — no auto-starter seed content.

---

## §6 Predecessor evidence

Salvage disposition: **PRESERVED** in [`REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md). Source PR #432 was closed after salvage PR #464 opened; its branch remains historical evidence.
