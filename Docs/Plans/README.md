# Plans (`Docs/Plans/`)

Execution plans, experiments, audits, and design notes for DungeonMindBuddy. **Operational truth** for the lexical-retrieval track is the checklist + super-plan pair below.

## Canonical (root)

| Doc | Role |
| --- | ---- |
| [`PLAN-split-corpus-retrieval-to-autonomous-demo.md`](PLAN-split-corpus-retrieval-to-autonomous-demo.md) | Versioned super-plan (YAML + narrative): split-corpus retrieval through autonomous C1S1–C1S3 demo. |
| [`CHECKLIST-dynamic-lexical-retrieval-rollout.md`](CHECKLIST-dynamic-lexical-retrieval-rollout.md) | Operational tracker (phases A–E, session log). |
| [`HANDOFF-execute-evidence-retrieval-synthesis-experiments.md`](HANDOFF-execute-evidence-retrieval-synthesis-experiments.md) | **Hub handoff** for Mirathorn council-room evidence→retrieval→synthesis waves (per-wave reports live under `archive/2026-05-09/evidence-gap-waves/`). |
| [`../Design/DECISION-world-campaign-knowledge-hierarchy.md`](../Design/DECISION-world-campaign-knowledge-hierarchy.md) | Decision anchor (world vs campaign authority). |

## Active narrative & design (root)

- **Sentence routing:** [`PLAN-Sentence-Routing-Stages-B-through-D.md`](PLAN-Sentence-Routing-Stages-B-through-D.md), [`DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md`](DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md), related `EXPERIMENT-*` / `STATUS-*` / `GUARDRAILS-*` in this directory.
- **Session recap benchmarks:** `EXPERIMENT-Session-Recap-*`, `STATUS-Session-Recap-*`, [`BACKLOG-session-recap-benchmarking.md`](BACKLOG-session-recap-benchmarking.md).
- **Stage D / registry:** [`AUDIT-Stage-D-Entity-Resolution-Discovery.md`](AUDIT-Stage-D-Entity-Resolution-Discovery.md) — cross-campaign synthesis report is archived (see [`archive/2026-05-09/reports/`](archive/2026-05-09/reports/)).

## Historical handoffs, reports, and notes

**Sorted under** [`archive/2026-05-09/`](archive/2026-05-09/) (see that folder’s `README.md`):

| Subfolder | Contents |
| --------- | -------- |
| [`handoffs/`](archive/2026-05-09/handoffs/) | `HANDOFF-*.md` moved from this directory (one-shot execution briefs). |
| [`reports/`](archive/2026-05-09/reports/) | `REPORT-*.md` moved from this directory (dated run / synthesis write-ups). |
| [`reviews/`](archive/2026-05-09/reviews/) | `REVIEW-*.md` (failure-mode / gold audits). |
| [`operational-notes/`](archive/2026-05-09/operational-notes/) | `PROCESSING-*.md` and similar operational logs. |
| [`evidence-gap-waves/`](archive/2026-05-09/evidence-gap-waves/) | Mirathorn wave 1–5 reports + comprehensive rollup. |

Older batch: [`archive/2026-04-07/`](archive/2026-04-07/) (Phase 6 corpus-question handoffs).

## Other roots here

- `entity_profiles/`, `entity_audit_manifest.tsv`, `entity_definitions_batch_sanity.md` — corpus / entity audit artifacts tied to planning work.

## Policy

- Prefer **`git mv`** when archiving (preserves history).
- After a move, update **in-repo** links in the same change (grep `Docs/Plans/HANDOFF-`, `Docs/Plans/REPORT-`, etc.).
- Leave a **stub** at the old path only when external bookmarks require a stable filename (example: [`mirathorn_event-sourced_slice_8eab1beb.plan.md`](mirathorn_event-sourced_slice_8eab1beb.plan.md)).
