# Mirathorn Vertical Slice Phase Ledger

## Purpose

Provide a single source of truth for where the original Mirathorn event-sourced vertical slice effort stands now, what is complete, what is blocked, and what must happen next.

---

## Latest Milestone Update

- **Mirathorn three-gate benchmark status:** GREEN
  - `gate_ingestion`: PASS
  - `gate_projection`: PASS
  - `gate_qa`: PASS
- **Validation quality bar met:** gates were validated independently, mismatch taxonomy was used to drive C2/C3 fixes, and Gate 3 reliability was rechecked to avoid state-induced false negatives.
- **Scope note:** This milestone closes the vertical-slice gate validation objective; full-corpus operational hardening/calibration work remains tracked in Phases 5-6 below.

---

## Phase 0 - Foundation Lock

- **Status:** Done
- **Goal:** Lock canonical Mirathorn and campaign inputs and baseline assumptions.
- **Evidence:** Source lock/fingerprinting reflected in `evals/llm_ingestion_slice` artifacts and follow-on handoff updates.
- **Exit criteria:** Deterministic input set and reproducible manifest.
- **Residual risk:** Low.

## Phase 1 - Event-Sourced Slice Core (Milestone-1)

- **Status:** Done
- **Goal:** End-to-end event-first ingestion plus projections (`instantiation -> zero_tick -> live`) with strict gates.
- **Evidence:** Completion status and verification evidence documented in `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-next-agent-mirathorn-event-slice.md`.
- **Exit criteria:** Hard gates pass with auditable deltas and deterministic outputs.
- **Residual risk:** Medium (coverage breadth, not core mechanics).

## Phase 2 - Skeptical Gap Investigation (Council Room)

- **Status:** Done
- **Goal:** Explain stale/incomplete outcomes by root-cause category using evidence.
- **Evidence:** Gap audit outputs under `evals/mirathorn_vertical_slice/output/` and explicit mismatch matrix in handoff.
- **Exit criteria:** Gap -> evidence -> impact -> confidence mapping and ranked remediation list.
- **Residual risk:** Medium (not all remediation items implemented yet).

## Phase 3 - Extraction Quality Drift Classification

- **Status:** Done
- **Goal:** Determine whether entity/fact count shift is regression vs intended noise reduction.
- **Evidence:** `Docs/Plans/archive/2026-05-09/handoffs/HANDOFF-investigate-entity-fact-quality-drift.md` concludes Outcome A and baseline reset.
- **Exit criteria:** Quantified bucket analysis and accepted baseline rationale.
- **Residual risk:** Low.

## Phase 4 - Extraction Lab v1 Infrastructure

- **Status:** Done
- **Goal:** Contract-aware, anchor-based benchmark harness with reproducible artifacts, regression checks, and promotion flow.
- **Evidence:** `extraction_lab/` package, anchor files in `evals/mirathorn_vertical_slice/gold/`, passing tests and smoke runs.
- **Exit criteria:** Structured run artifacts + regression assert + baseline promotion operational.
- **Residual risk:** Low-Medium (full-corpus anchor calibration still pending).

## Phase 5 - Batch Pipeline Transition Stability

- **Status:** In Progress
- **Goal:** Make `entity_complete -> fact_submitted` reliable on constrained machines.
- **Current state:** Entity transition is now chunked/observable; likely hotspot remains fact-prep memory behavior.
- **Exit criteria (strict):**
  - From `entity_complete`, `--poll` consistently reaches `fact_submitted`.
  - No UI/system lock under laptop-safe operating profile.
  - Phase-level telemetry demonstrates bounded memory behavior.
- **Primary blocker:** Fact-prep still heavy at full-corpus scale.

## Phase 6 - Full-Corpus Validation and Calibration

- **Status:** Blocked (depends on Phase 5)
- **Goal:** Run Extraction Lab on finalized `batch_api_full_corpus` store and validate anchor/threshold behavior at production scale.
- **Exit criteria:**
  - Finalized store is available.
  - Full-corpus run artifacts are produced.
  - Anchor fail buckets are triaged with evidence.
  - Baseline promotion decision completed using explicit checklist.
- **Primary blocker:** Corpus batch flow not yet reliably advancing past fact-prep in this environment.

## Phase 7 - Readiness and Generalization Challenge

- **Status:** Pending
- **Goal:** Prove robustness beyond Milestone-1 happy path via blind replay and expanded scenario matrix.
- **Exit criteria:**
  - Scenario-level deterministic replay passes.
  - Strict gate behavior holds without threshold relaxation.
  - Assumptions are challenged with falsification-oriented evidence.
- **Primary blocker:** Production-scale operational stability must be completed first.

---

## Recommended Immediate Sequence

1. Finish Phase 5 (memory-safe fact-prep path, telemetry, checkpoint/resume behavior).
2. Unblock Phase 6 (`batch_api_full_corpus` completion, Extraction Lab run, anchor/threshold calibration).
3. Execute Phase 7 readiness challenge from the original vertical slice intent.

