# Plans (`Docs/Plans/`)

Execution plans, experiments, audits, and design notes for DungeonMindBuddy.

**Operational truth (lexical retrieval → autonomous demo):** [`PLAN-split-corpus-retrieval-to-autonomous-demo.md`](PLAN-split-corpus-retrieval-to-autonomous-demo.md) + [`CHECKLIST-dynamic-lexical-retrieval-rollout.md`](CHECKLIST-dynamic-lexical-retrieval-rollout.md). Everything else here is supporting context, another track, or historical reference.

---

## Lexical retrieval → autonomous demo

| Doc | Role |
| --- | ---- |
| [`PLAN-split-corpus-retrieval-to-autonomous-demo.md`](PLAN-split-corpus-retrieval-to-autonomous-demo.md) | Versioned super-plan (YAML + narrative): split-corpus retrieval through autonomous C1S1–C1S3 demo. |
| [`CHECKLIST-dynamic-lexical-retrieval-rollout.md`](CHECKLIST-dynamic-lexical-retrieval-rollout.md) | Operational tracker (phases A–E, session log). |
| [`../Design/DECISION-world-campaign-knowledge-hierarchy.md`](../Design/DECISION-world-campaign-knowledge-hierarchy.md) | Decision anchor (world vs campaign authority). |

---

## Mirathorn evidence-gap / council-room series

| Doc | Role |
| --- | ---- |
| [`HANDOFF-execute-evidence-retrieval-synthesis-experiments.md`](HANDOFF-execute-evidence-retrieval-synthesis-experiments.md) | Hub handoff: evidence → retriever → synthesis experiments; links to wave artifacts. |
| [`HYPOTHESES-evidence-retrieval-synthesis-improvements.md`](HYPOTHESES-evidence-retrieval-synthesis-improvements.md) | Hypothesis list paired with the handoff / ledger work. |
| [`archive/2026-05-09/evidence-gap-waves/`](archive/2026-05-09/evidence-gap-waves/) | Per-wave reports (1–5) + [`REPORT-all-waves-comprehensive.md`](archive/2026-05-09/evidence-gap-waves/REPORT-all-waves-comprehensive.md). |
| [`archive/2026-05-09/reports/REPORT-evidence-gap-phases-0-6-findings.md`](archive/2026-05-09/reports/REPORT-evidence-gap-phases-0-6-findings.md) | Phases 0–6 findings (referenced from the hub handoff). |

---

## Sentence routing & grounded ingestion

| Doc | Role |
| --- | ---- |
| [`PLAN-Sentence-Routing-Stages-B-through-D.md`](PLAN-Sentence-Routing-Stages-B-through-D.md) | Staged plan B–D for sentence-routing work. |
| [`DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md`](DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md) | Stage B hub-routing design. |
| [`EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md`](EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md) | Retrieval falsification experiment doc. |
| [`GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md`](GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md) | Vision / guardrails for sentence-grounded ingestion. |

---

## Session recap benchmarks

| Doc | Role |
| --- | ---- |
| [`EXPERIMENT-Session-Recap-Ingest-Benchmark.md`](EXPERIMENT-Session-Recap-Ingest-Benchmark.md) | Ingest benchmark experiment. |
| [`STATUS-Session-Recap-Ingest-Benchmark.md`](STATUS-Session-Recap-Ingest-Benchmark.md) | Ingest benchmark status. |
| [`EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md`](EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md) | Timeline-pass benchmark experiment. |
| [`STATUS-Session-Recap-Timeline-Pass-Benchmark.md`](STATUS-Session-Recap-Timeline-Pass-Benchmark.md) | Timeline-pass benchmark status. |
| [`EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md`](EXPERIMENT-Session-Recap-Timeline-Append-Benchmark.md) | Timeline-append benchmark experiment. |
| [`STATUS-Session-Recap-Timeline-Append-Benchmark.md`](STATUS-Session-Recap-Timeline-Append-Benchmark.md) | Timeline-append benchmark status. |
| [`EXPERIMENT-Inline-Recap-Breadcrumbing.md`](EXPERIMENT-Inline-Recap-Breadcrumbing.md) | Inline recap breadcrumbing experiment. |
| [`BACKLOG-session-recap-benchmarking.md`](BACKLOG-session-recap-benchmarking.md) | Session recap benchmarking backlog. |
| [`SCOPE-B-GOLD-Session-20-Ingest.md`](SCOPE-B-GOLD-Session-20-Ingest.md) | Scope B gold / Session 20 ingest companion to evals. |
| [`INDEX-Recap-Normalization.md`](INDEX-Recap-Normalization.md) | Recap normalization index. |

---

## Registry & Stage D entity resolution

| Doc | Role |
| --- | ---- |
| [`AUDIT-Stage-D-Entity-Resolution-Discovery.md`](AUDIT-Stage-D-Entity-Resolution-Discovery.md) | Stage D discovery audit (contracts, NC3, open questions). |
| [`archive/2026-05-09/reports/REPORT-Stage-C-Cross-Campaign-Generalisation.md`](archive/2026-05-09/reports/REPORT-Stage-C-Cross-Campaign-Generalisation.md) | Cross-campaign Stage C synthesis (cited from audit / backlog). |

---

## Guides, naming, and pipelines

| Doc | Role |
| --- | ---- |
| [`GUIDE-multi-session-document-splitting.md`](GUIDE-multi-session-document-splitting.md) | Multi-session document splitting guide. |
| [`NAMING-benchmark-vs-runtime.md`](NAMING-benchmark-vs-runtime.md) | Naming conventions: benchmark vs runtime. |
| [`FLOW-npc-power-skill-pipeline.md`](FLOW-npc-power-skill-pipeline.md) | NPC power-increase skill pipeline flow. |

---

## Vertical slice design (benchmark)

| Doc | Role |
| --- | ---- |
| [`DESIGN-lysandra-statblock-vertical-slice-benchmark.md`](DESIGN-lysandra-statblock-vertical-slice-benchmark.md) | Lysandra statblock vertical slice benchmark design. |

---

## Entity audit artifacts (data + notes)

| Path | Role |
| ---- | ---- |
| [`entity_profiles/`](entity_profiles/) | JSON entity profile examples. |
| [`entity_audit_manifest.tsv`](entity_audit_manifest.tsv) | Entity audit manifest (TSV). |
| [`entity_definitions_batch_sanity.md`](entity_definitions_batch_sanity.md) | Batch sanity notes for entity definitions. |

---

## Stubs (stable old paths)

| Doc | Role |
| --- | ---- |
| [`mirathorn_event-sourced_slice_8eab1beb.plan.md`](mirathorn_event-sourced_slice_8eab1beb.plan.md) | Stub: superseded Cursor plan → [`archive/2026-05-09/mirathorn_event-sourced_slice_8eab1beb.plan.md`](archive/2026-05-09/mirathorn_event-sourced_slice_8eab1beb.plan.md) + [`../Design/DESIGN-layered-canon-vertical-slice.md`](../Design/DESIGN-layered-canon-vertical-slice.md). |

---

## Archive (historical handoffs, reports, notes)

Material moved out of this directory root lives under [`archive/`](archive/). Batch layout:

| Subfolder (under `archive/2026-05-09/`) | Contents |
| --------------------------------------- | -------- |
| [`handoffs/`](archive/2026-05-09/handoffs/) | One-shot `HANDOFF-*.md`. |
| [`reports/`](archive/2026-05-09/reports/) | Dated `REPORT-*.md`. |
| [`reviews/`](archive/2026-05-09/reviews/) | `REVIEW-*.md` audits. |
| [`operational-notes/`](archive/2026-05-09/operational-notes/) | e.g. `PROCESSING-*.md`. |
| [`evidence-gap-waves/`](archive/2026-05-09/evidence-gap-waves/) | Mirathorn wave 1–5 + rollup. |

Older batch: [`archive/2026-04-07/`](archive/2026-04-07/) (Phase 6 corpus-question handoffs). Narrative for `2026-05-09`: [`archive/2026-05-09/README.md`](archive/2026-05-09/README.md).

---

## Policy (when adding or moving docs)

1. Prefer **`git mv`** when archiving (preserves history).
2. After a move, update **in-repo** links in the same change (grep `Docs/Plans/HANDOFF-`, `Docs/Plans/REPORT-`, `Docs/Plans/REVIEW-`, `Docs/Plans/PROCESSING-`, and relative `../../../Docs/Plans/...` from eval trees).
3. Leave a **stub** at the old path only when external bookmarks require a stable filename (see stub row above).
4. After adding a new root plan doc, **add one row** under the right section in this README so the index stays complete.
