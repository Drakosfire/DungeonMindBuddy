# HANDOFF — Graph Review browse-first committed World Graph sessions

**Created:** 2026-07-31
**Revised:** 2026-08-01 (salvage re-anchor — capture omitted #444 corpus-catalog finding)
**Status:** NAMED SUCCESSOR — not dispatched; salvage preserved intent only.
**Source PR:** #444 head `127168de48d2d94803f906ff69a26bbc9fefaf82`
**Salvage ledger:** [`REPORT-superseded-open-pr-salvage-2026-07-31.md`](../Reports/REPORT-superseded-open-pr-salvage-2026-07-31.md) §#444
**Depends on:** Current strict World Graph projection (`semantic_assertion_divergence` 409 on mismatch) — **no first-wins tolerance**.

---

## §1 Mission (salvageable intent)

Two related but distinct product obligations were mined from #444. Future work may split them into separate slices; both must remain named until explicitly accepted or dropped.

### 1A — Browse committed World Graph sessions

Graph Review operators can browse a committed World Graph session catalog and load a chosen session into the workbench without navigating ingest-run internals first — a browse-first Load UX atop existing recap/projection APIs.

### 1B — Corpus-backed recap catalog (distinct from 1A)

Graph Review Load must index **corpus recaps**, not only filesystem ingest-run discovery or gold-fixture session lists. Operators need a first-class recap catalog with explicit populate/refresh and quarantine of eval dogfood from the product picker.

**Invariant (when dispatched)**

```text
Load path selects one committed session identity OR one corpus-backed catalog row;
projection uses strict divergence checks;
no silent first-wins merge of conflicting contribution assertions;
eval dogfood never appears as the only/default product Load choice.
```

---

## §2 Salvageable paths (reference from #444 head — reimplement fresh)

### 2A — Browse committed sessions (World Graph contributions)

| Area | Reference paths on #444 head | Notes |
|---|---|---|
| Session catalog service | `apps/live_control_server/services/world_graph_sessions.py` | Browse/list API backing |
| Load surface UI | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.tsx` | Browse-first layout |
| Load bar / lane summary | `GraphReviewLoadBar.tsx`, `GraphReviewLoadLaneSummary.tsx`, `GraphReviewLanePicker.tsx` | Session picker UX |
| Workbench module wiring | `GraphReviewWorkbenchModule.tsx` | Load → review handoff |
| Recap adapter | `adaptWorldGraphRecapProjection.ts` | Projection bridge |
| Kernel projection helpers | `src/graph_memory/kernel/world_projection.py` | **Strict path only** |
| Tests | `tests/test_world_graph_sessions.py`, `tests/test_graph_kernel_world_projection.py` | Adapt, do not cherry-pick first-wins cases |

### 2B — Corpus-backed recap catalog (product finding from #444 / Backlog)

Captured on #444 head in `Backlog.md` as `[IDEA] Recap catalog + populate surface for Graph Review Load` (2026-07-27). This is **not** satisfied by World-Graph-contribution browsing alone.

| Requirement | Detail |
|---|---|
| Corpus-backed session index | Built from normalized recaps (not gold manifests / eval roots) |
| Per-session status vocabulary | `not_ingested` / `preview_ready` / `stale_vs_source` / `broken(reason)` against current verified-snapshot contract |
| Explicit populate/refresh | Operator CTA to ingest/refresh/mark broken into product `out/` (or successor store) |
| Quarantine eval dogfood | Hide or quarantine gold-review / vocabulary-ablation / other eval fixtures from the product Load picker |

**Reference surfaces (current main / #444 discussion):**

- `apps/live-control-ui/.../graphReviewWorkbenchUtils.ts` (`buildGraphReviewCatalog`)
- `apps/live_control_server/services/graph_ingest_run_registry.py`
- `apps/live_control_server/services/graph_gold_review.py` (`include_eval_roots=True` is the dogfood leak)
- `apps/live_control_server/services/graph_ingest_verified_snapshot.py`

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

1. Operator confirms whether 1A, 1B, or both remain Graph Review roadmap priority (they may ship as separate slices).
2. Strict projection invariants have regression tests covering divergence 409.
3. A fresh implementation base is chosen (not #444 head).
4. Rewrite scope is bounded in a new capability decomposition — #444's full stacked diff (~1.1k lines) exceeds salvage exception.
5. For 1B: product status vocabulary and populate/refresh ownership are designed before fixture repairs paper over empty `out/graph_memory/runs`.

---

## §5 Named predecessor evidence

Salvage dispositions:

- **PRESERVED** browse-first committed-session UX → this handoff §1A / §2A
- **PRESERVED** corpus-backed recap catalog product finding → this handoff §1B / §2B
- **REJECTED** first-wins / divergent-shadow tolerance → REPORT §#444

Source PR #444 closed after salvage PR #464 opened; branch remains historical evidence.
