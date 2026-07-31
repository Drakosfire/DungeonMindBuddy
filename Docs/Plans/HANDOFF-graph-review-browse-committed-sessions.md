# HANDOFF — Graph Review browse-first committed World Graph sessions

**Created:** 2026-07-31  
**Status:** NAMED SUCCESSOR — not dispatched; salvage preserved intent only.  
**Source PR:** #444 head `127168de48d2d94803f906ff69a26bbc9fefaf82`  
**Salvage ledger:** [`REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md) §#444  
**Depends on:** Current strict World Graph projection (`semantic_assertion_divergence` 409 on mismatch) — **no first-wins tolerance**.

---

## §1 Mission (salvageable intent)

Graph Review operators can browse a committed World Graph session catalog and load a chosen session into the workbench without navigating ingest-run internals first — a browse-first Load UX atop existing recap/projection APIs.

**Invariant (when dispatched)**

```text
Load path selects one committed session identity; projection uses strict divergence checks;
no silent first-wins merge of conflicting contribution assertions.
```

---

## §2 Salvageable paths (reference from #444 head — reimplement fresh)

| Area | Reference paths on #444 head | Notes |
|---|---|---|
| Session catalog service | `apps/live_control_server/services/world_graph_sessions.py` | Browse/list API backing |
| Load surface UI | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.tsx` | Browse-first layout |
| Load bar / lane summary | `GraphReviewLoadBar.tsx`, `GraphReviewLoadLaneSummary.tsx`, `GraphReviewLanePicker.tsx` | Session picker UX |
| Workbench module wiring | `GraphReviewWorkbenchModule.tsx` | Load → review handoff |
| Recap adapter | `adaptWorldGraphRecapProjection.ts` | Projection bridge |
| Kernel projection helpers | `src/graph_memory/kernel/world_projection.py` | **Strict path only** |
| Tests | `tests/test_world_graph_sessions.py`, `tests/test_graph_kernel_world_projection.py` | Adapt, do not cherry-pick first-wins cases |

**ALREADY_PRESENT on main (do not re-port as salvage):**

- `postWorldGraphRecapProjection` / `/recap-projection` API
- Ingest-run catalog path

---

## §3 Explicitly rejected from #444 (do not implement)

| Capability | Why rejected |
|---|---|
| `per_contribution_assertion_ids` first-wins tolerance | Main keeps strict `semantic_assertion_divergence` 409 |
| Divergent-shadow projection rewrite | Bounded rewrite size exceeds salvage exception; incompatible with strict projection |
| Rebasing #444 stacked head | Superseded; fresh slice from this handoff only |

---

## §4 Dispatch gate (future)

Do not dispatch until:

1. Operator confirms browse-first UX still matches Graph Review roadmap priority.
2. Strict projection invariants have regression tests covering divergence 409.
3. A fresh implementation base is chosen (not #444 head).
4. Rewrite scope is bounded in a new capability decomposition — #444's full stacked diff (~1.1k lines) exceeds salvage exception.

---

## §5 Named predecessor evidence

Salvage disposition: **PRESERVED** in [`REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md). Source PR #444 to be closed on salvage merge.
