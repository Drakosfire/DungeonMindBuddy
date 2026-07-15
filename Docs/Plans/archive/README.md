# Plans archive

Historical plan, handoff, report, review, and operational-note material lives under **dated** folders. **Canonical active** execution plans stay in `Docs/Plans/` root (for example `PLAN-split-corpus-retrieval-to-autonomous-demo.md` and `CHECKLIST-dynamic-lexical-retrieval-rollout.md`).

## Batches

| Folder | Contents |
| ------ | -------- |
| `2026-04-07/` | Phase 6 corpus-question design / gold-promotion handoffs (early archive). |
| `2026-05-09/` | Aggressive sort: `handoffs/`, `reports/`, `reviews/`, `operational-notes/`, plus `evidence-gap-waves/` and superseded Mirathorn Cursor plan. See [`2026-05-09/README.md`](2026-05-09/README.md). |
| `2026-06-22/` | Tier-1 cleanup: completed L5 slices, Session 22 handoffs, plan-surface R0–L1, merged statblock PRs #107–#112. See [`2026-06-22/README.md`](2026-06-22/README.md). |
| `2026-07-15/` | Hermes foundation reset package + completed supergraph/statblock handoffs and superseded roadmaps. See [`2026-07-15/hermes-campaign-authoring-foundation-reset/`](2026-07-15/hermes-campaign-authoring-foundation-reset/), [`completed-supergraph-handoffs/`](2026-07-15/completed-supergraph-handoffs/), [`completed-statblock-handoffs/`](2026-07-15/completed-statblock-handoffs/), [`superseded-roadmaps/`](2026-07-15/superseded-roadmaps/). |

When moving a file here, prefer:

1. **`git mv`** (preserve history).
2. A **stub** at the old path only when external bookmarks or tooling still expect the original filename (see Mirathorn plan stub in `Docs/Plans/`).
3. Update **in-repo** links in the same change (grep `Docs/Plans/HANDOFF-`, `Docs/Plans/REPORT-`, `Docs/Plans/REVIEW-`, `Docs/Plans/PROCESSING-`, and relative `../../../Docs/Plans/...` from eval trees).
