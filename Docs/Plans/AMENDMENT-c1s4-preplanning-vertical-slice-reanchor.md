---
document_id: dmb-amendment-c1s4-preplanning-vertical-slice-reanchor
title: C1S4 Preplanning Vertical Slice Reanchor
document_class: plan_amendment
plan_kind: execution_reanchor
status: active
created_at: "2026-05-14T00:00:00Z"
last_updated_at: "2026-05-14T00:00:00Z"
related_documents:
  - path: Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md
    role: amends_super_plan
  - path: Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md
    role: amends_operational_tracker
  - path: Docs/Plans/HANDOFF-pr25-c1s4-preplanning-vertical-slice.md
    role: implementation_handoff
  - path: Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md
    role: authority_model_anchor
---

# C1S4 Preplanning Vertical Slice Reanchor

This amendment records the current planning decision for the split-corpus retrieval to autonomous-demo track. It should be read as an operational update to the super-plan and dynamic lexical retrieval checklist until those very large archival documents are compacted or edited by a dedicated doc-sync pass.

## Decision

Move the next product-facing work away from more global retrieval tuning and toward a bounded C1S4 preplanning vertical slice.

The slice should demonstrate the loop:

```text
C1S1-C1S3 campaign memory
  -> single bounded knowledge base
  -> retrieval/context bundle
  -> synthetic C1S4 preplanning ask
  -> later live planner output
  -> grade against actual C1S4 recap as held-out oracle
```

The first implementation PR should **not** run the live planner and should **not** grade prep quality. It should prove the deterministic boundary first.

## Current repo state this builds on

- C1S1-C1S3 are already blessed pilot sessions in the session-memory lane.
- C1S4 exists in the corpus and can serve as a held-out oracle: `Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md`.
- Route-equivalence artifacts and conservative query-text-gated aliases are usable as the promoted retrieval baseline for cohort runs.
- Existing vertical slices supply useful patterns:
  - `evals/lysandra_vertical_slice/` for natural ask -> tool trace -> output grading.
  - `evals/session_recap_ingest_vertical_slice/` for isolated pre-state corpora, allowlisted reads, sidecar artifacts, and cohort summaries.

## Scope of the next PR

Create `evals/c1s4_preplanning_vertical_slice/` with deterministic scaffold only:

1. `gold/kb_policy.json` declaring:
   - included sessions: `[1, 2, 3]`,
   - held-out sessions: `[4]`,
   - included C1S1-C1S3 session-memory JSONL paths,
   - forbidden C1S4 oracle/source/derivative paths.
2. `step0_kb_materialize.py` to load a single C1S1-C1S3 KB manifest and prove no C1S4 source enters the KB.
3. `step1_retrieval_context.py` to run deterministic preplanning-oriented retrieval smokes over that KB.
4. `preplanning_context_bundle.py` to convert retrieved anchors/routes into a bounded planner-visible context bundle.
5. `tests/test_c1s4_preplanning_vertical_slice.py` to enforce KB boundary, C1S4 exclusion, retrieval smoke, and bundle schema.
6. README/GATES docs matching the existing vertical-slice style.

Implementation details and acceptance criteria live in `Docs/Plans/HANDOFF-pr25-c1s4-preplanning-vertical-slice.md`.

## Explicit non-goals

Do not tune retrieval in this slice.

Do not edit corpus files.

Do not regenerate existing retrieval baselines or question-delta artifacts.

Do not edit C1S4 recap content.

Do not add a canvas yet.

Do not run the live planner yet.

Do not grade prep quality yet.

Do not allow C1S4 content into planner-visible context.

## Why this reanchor matters

The current C1S13 falsification work is useful, but it can become an endless retrieval-local loop. The product demo needs a bounded integration proof that the system can:

- ingest multiple prior sessions into one KB,
- preserve a held-out future session as oracle only,
- retrieve and package prior continuity safely,
- support a future planner turn without oracle leakage,
- and eventually compare synthetic prep against actual play.

That is a better vertical slice for DungeonMindBuddy than continuing to optimize C1S13 retrieval rows before the planner loop exists.

## Future sequence after scaffold

After the deterministic scaffold lands:

1. **Oracle target authoring:** derive `c1s4_oracle_targets.json` from the actual C1S4 recap, with forecastability labels:
   - `should_surface_from_prior_context`,
   - `plausible_pressure`,
   - `oracle_only_event`,
   - `must_not_predict`.
2. **Live planner trace:** add `step2_preplanning_planner_trace.py`, using the same trace/output discipline as the Lysandra vertical slice.
3. **Oracle grader:** add `step3_grade_against_c1s4_oracle.py`, grading prep coverage, grounding, uncertainty hygiene, and oracle leakage.
4. **Cohort/cost wrapper:** optional N-run cohort summary once the single live run is stable.

## Super-plan/checklist synchronization note

The super-plan and checklist are currently large archival documents with long PR histories. This amendment is intentionally small and focused so the planning decision is reviewable. A later doc-sync pass may fold this content directly into the YAML `execution_state`, reanchor block, and phase checklist, but implementation agents should treat this amendment plus the PR #25 handoff as the current planning direction.
