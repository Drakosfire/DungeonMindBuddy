---
document_id: dmb-plan-addendum-c1s4-preplanning-vertical-slice
title: C1S4 Preplanning Vertical Slice Addendum
document_class: plan
plan_kind: super_plan_addendum
status: active
created_at: "2026-05-14"
last_updated_at: "2026-05-14"
related_documents:
  - path: Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md
    role: canonical_super_plan
  - path: Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md
    role: existing_operational_tracker
  - path: Docs/Plans/CHECKLIST-c1s4-preplanning-vertical-slice.md
    role: vertical_slice_tracker
  - path: Docs/Design/DESIGN-c1s4-preplanning-vertical-slice.md
    role: technical_design
  - path: Docs/Plans/HANDOFF-c1s4-preplanning-vertical-slice.md
    role: implementation_handoff
---

# Addendum — C1S4 preplanning vertical slice

This addendum re-anchors the active split-corpus / autonomous-demo plan around a bounded product loop:

> Ingest Longmont Campaign 1 Sessions 1–3 into a single queryable campaign-memory knowledge base, use that KB to enrich a synthetic preplanning turn for Session 4, and grade the resulting prep against the existing C1S4 recap as a held-out oracle.

This is not a replacement for `PLAN-split-corpus-retrieval-to-autonomous-demo.md`. It is the next scoped execution layer under that plan. The canonical super-plan remains the narrative owner; this addendum records the concrete C1S4 demo shape so future coding agents do not continue optimizing retrieval in the abstract.

---

## Current interpretation of the repo state

The repo already has the key pieces for this slice:

- C1S1–C1S3 are part of the blessed session-memory pilot surface.
- Session-memory materialization produces deterministic JSONL and meta artifacts from breadcrumbed recaps.
- The retrieval harness can run over C1S1–C1S3 as a cohort and now has route-equivalence diagnostics / default-equivalence baseline behavior.
- Existing vertical slices prove two reusable patterns:
  - agent trace + natural ask gating (`lysandra_vertical_slice`), and
  - isolated pre-state corpus + strict tool/read/write contracts (`session_recap_ingest_vertical_slice`).
- C1S4 exists in the corpus and can be used as a held-out oracle, but it must not be readable by the planner during the synthetic prep turn.

The missing artifact is a single integration slice that composes those pieces into the actual product loop.

---

## Canonical scope

### Included knowledge base input

The first demo KB includes only:

- Longmont Campaign 1 Session 1 session-memory records.
- Longmont Campaign 1 Session 2 session-memory records.
- Longmont Campaign 1 Session 3 session-memory records.
- Route-equivalence / lexical artifacts that are already allowed by the current retrieval harness, so long as they do not introduce held-out C1S4 content.

### Held-out oracle

The C1S4 recap is the oracle and must be grader-only:

- `Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md`

Any normalized, breadcrumbed, or session-memory derivative of C1S4 is also forbidden to the planner/tool context until the oracle-grade phase.

### Product behavior under test

The target loop is:

1. Build a deterministic C1S1–C1S3 KB manifest.
2. Run retrieval against that single KB.
3. Convert retrieved anchors/routes into a bounded preplanning context bundle.
4. Let the planner produce synthetic C1S4 prep from only the allowed KB context.
5. Grade the prep against C1S4 oracle targets.
6. Emit trace, retrieval, context, oracle-grade, cost, and leak-check sidecars.

---

## Strategic decision

Do not wait for every C1S13 retrieval failure to clear before building the C1S4 slice.

C1S13 remains useful as a falsification and holdout cohort for retrieval tuning. It should not block the narrower product-loop proof. The C1S4 slice should use the current stable default-equivalence retrieval lane as its baseline, then optionally add scene-beat packet or other retrieval variants as comparative lanes after the boundary/oracle harness is in place.

---

## Critical invariants

### No oracle leakage

The planner must not read C1S4 source files, normalized files, breadcrumb files, session-memory JSONL, or any C1S4-derived oracle target file. This must be proven from the tool trace and from the KB manifest.

### Candidate retrieval remains candidate retrieval

The existing `query_session_memory` candidate mode should not be weakened to return arbitrary recap prose. For planning, add an explicit context-bundle step that resolves retrieved unit IDs/routes into bounded snippets from allowed sessions.

### Linked context is not answer evidence unless authorized

Route equivalence and lexical artifacts may help locate relevant C1S1–C1S3 records. They must not promote C1S4 oracle content or world-fallback facts into campaign-state evidence.

### The oracle must distinguish forecastable continuity from unpredictable play

C1S4 contains events that may not be inferable from C1S1–C1S3. Oracle targets must label whether they are:

- continuity anchors that should have been surfaced from prior sessions,
- plausible planning affordances,
- oracle-only events that must not be required as predictions,
- forbidden leakage indicators.

---

## Proposed milestone decomposition

### M4.0 — KB boundary proof

Build a deterministic C1S1–C1S3 KB manifest and tests proving that C1S4 is excluded.

Deliverables:

- `evals/c1s4_preplanning_vertical_slice/gold/kb_policy.json`
- `evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py`
- tests asserting included/excluded sessions and forbidden paths

### M4.1 — Retrieval/context-bundle proof

Run deterministic retrieval over the combined KB and emit a bounded preplanning context bundle.

Deliverables:

- `preplanning_context_bundle.py`
- deterministic retrieval smoke queries
- bundle schema with unit IDs, routes, snippets, and source references
- no C1S4 leakage gate

### M4.2 — C1S4 oracle target seed

Extract a human-reviewed oracle target file from C1S4. The oracle file is grader-only.

Deliverables:

- `gold/c1s4_oracle_targets.json`
- target categories: continuity anchor, planning affordance, oracle-only event, forbidden leakage token
- grader-only source-path rules

### M4.3 — Live planner synthetic prep turn

Run a natural preplanning ask through the planner using the C1S1–C1S3 KB and context-bundle tool.

Deliverables:

- `step2_preplanning_planner_trace.py`
- planner gold fixture / scenario config
- tool trace report
- output artifact with structured prep sections

### M4.4 — Oracle grading and cohort report

Compare the synthetic prep against C1S4 oracle targets without rewarding impossible prediction.

Deliverables:

- `step3_grade_against_c1s4_oracle.py`
- `grader.py`
- sidecar JSON and markdown report
- optional N-run cohort summary once the one-shot path is green

---

## First PR recommendation

The first implementation PR should be deliberately boring:

1. Add the slice directory and README/GATES shell.
2. Add `kb_policy.json` with C1S1–C1S3 included and C1S4 excluded.
3. Add `step0_kb_materialize.py` that loads only the approved session-memory JSONL files.
4. Add tests proving C1S4 is excluded from manifest, records, paths, and traceable context.
5. Add a deterministic retrieval smoke that does not call an LLM.

Do not implement the live planner turn in the first PR.

The first slice should prove the boundary before it proves intelligence.

---

## Intended super-plan/checklist alignment

When the large canonical files are next touched safely, update them as follows:

- Add this addendum under `related_documents` in `PLAN-split-corpus-retrieval-to-autonomous-demo.md`.
- Change the active next fork from broad promotion criteria vs wider falsification vs gold audit into: **build C1S4 preplanning vertical-slice M4.0 boundary proof first**.
- Keep C1S13 retrieval failures as a parallel falsification lane, not the blocker for the product-loop demo.
- Add `CHECKLIST-c1s4-preplanning-vertical-slice.md` as the operational tracker for M4.0–M4.4.
- Preserve the existing dynamic lexical rollout checklist as the tracker for retrieval/lexicon promotion, not the owner of the preplanning demo loop.

---

## Success statement

The slice succeeds when DungeonMindBuddy can say:

> Given only C1S1–C1S3 campaign memory, I can assemble a grounded, bounded planning context for C1S4; generate synthetic prep from that context; and compare that prep against the actual C1S4 recap without leaking the oracle or pretending unpredictable play outcomes were knowable.
