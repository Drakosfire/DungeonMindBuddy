---
document_class: planning_rationale
plan_kind: companion_rationale
status: active
related_documents:
  - path: Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md
    role: canonical_super_plan
  - path: Docs/Plans/CHECKLIST-c1s4-preplanning-vertical-slice.md
    role: operational_tracker
  - path: Docs/Plans/HANDOFF-next-c1s4-preplanning-vertical-slice-scaffold.md
    role: implementation_handoff
---

# C1S4 Preplanning Vertical Slice — Companion Rationale

This rationale explains the C1S4 preplanning vertical-slice reanchor now represented in PLAN v32 under `pilot_memory_ingest` and `synthetic_session4_prep_benchmark`. It does not supersede the super-plan; it explains the implementation strategy and why the next PR should scaffold the deterministic boundary before running a live planner.

PLAN v32 is canonical. This document explains the rationale and implementation sequence for the C1S4 preplanning vertical slice.

PLAN v32 already contains the canonical super-plan anchor. This document is a readable companion rationale for implementation agents and reviewers.

## Why this slice now

- It creates a deterministic, auditable C1S1–C1S3 planner-visible boundary before any live planner run.
- It formalizes C1S4 as held-out oracle-only material for grading and benchmark integrity.
- It separates retrieval-local tuning work from product-facing autonomy scaffolding.

## Intended sequencing

1. Build deterministic KB and retrieval context bundles for C1S1–C1S3 only.
2. Prove policy enforcement that excludes all C1S4 source and derivative surfaces from planner-visible context.
3. Add live planner and oracle-grading passes only after deterministic scaffold checks pass.

## Scope boundaries

In-scope for next implementation PR:
- deterministic KB materialization
- deterministic retrieval context bundle generation
- policy checks for C1S4 holdout and oracle path handling

Explicit non-goals for scaffold PR:
- retrieval tuning experiments
- corpus mutation
- baseline regeneration
- live planner execution
