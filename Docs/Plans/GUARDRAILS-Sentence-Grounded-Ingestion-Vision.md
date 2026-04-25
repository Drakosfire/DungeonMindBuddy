# Guardrails — Sentence-Grounded Ingestion Vision

**Date:** 2026-04-24  
**Status:** Active operational checklist  
**Companion design:** `Docs/Design/DESIGN-citation-grounded-corpus-architecture.md`

---

## 1. Purpose

This document turns the sentence-grounded ingestion vision into day-to-day decision rules.
Use it to prevent drift when editing prompts, graders, schemas, and write paths.

---

## 2. Canonical Contract (Non-Negotiable)

### 2.1 Canonical truth layer

Canonical memory is:

- sentence/claim units,
- source anchors (`path`, line range, hash, commit context),
- hub routing links (multi-label allowed),
- explicit uncertainty/abstain signals.

### 2.2 Derived layer

Derived memory is:

- timeline rows,
- dossier prose,
- relationship summaries,
- plot-thread summaries,
- other compressed render artifacts.

Derived artifacts are views over canonical units. They are never the only source of truth.

---

## 3. Stage Boundaries

Keep these stages separable and independently testable:

1. **Capture (deterministic):** corpus text -> sentence/claim units + anchors.
2. **Routing (LLM):** units -> existing hubs (0..N hubs per unit).
3. **Proposal (LLM):** unresolved units -> new-hub candidates.
4. **Projection (LLM/deterministic):** canonical units -> timeline/dossier/etc.

Do not let one stage hide failures in another stage.

---

## 4. PR Gate Checklist

Any ingestion/retrieval/projection change must answer these before merge:

1. Does this preserve or improve source-anchor integrity?
2. Does this keep canonical vs derived layers separate?
3. Does this alter stage boundaries? If yes, is the benchmark split updated?
4. Does this change routing semantics (single vs multi-label, abstain behavior)?
5. Could this silently promote derived prose into canonical truth?
6. Are new failure modes measurable by an existing gate?
7. Is cost impact surfaced (`scenario_estimated_cost_usd` or cohort stats)?

If any answer is unknown, the change is not ready.

---

## 5. Anti-Patterns (Reject in Review)

1. **Compression-first extraction:** forcing one neat beat before grounding.
2. **Count-as-quality proxies:** event count gates used as primary quality signal.
3. **Gold deflation:** editing expected anchors to match model paraphrase.
4. **Cross-stage masking:** patching projection prompts to hide routing misses.
5. **Canonical-by-accident prose:** accepting timeline text with no linked canonical units.
6. **All-or-nothing verdicts:** reporting only headline pass rate without per-stage diagnostics.

---

## 6. Retrieval-Fit Guardrails

The goal is fast, relevant, grounded context for preplanning/planning/tool calls.

Required retrieval properties:

- relevance filtering by scope/document/session/entity context,
- bounded context pack size (token budget enforced),
- citation-preserving excerpts,
- deterministic fallback when uncertain (abstain + include rationale).

Preferred policy:

- unknown relevance => deprioritize, do not hard-exclude,
- out-of-scope confident => exclude from top context,
- question-mention protection => never hard-exclude explicitly named entities.

---

## 7. Projection/Bloat Policy

Projection artifacts can bloat over time. Manage by policy, not ad hoc edits.

Rules:

1. Projections are rebuildable from canonical units.
2. Pruning/de-dup runs target projections first, canonical units second.
3. Timeline is the compact continuity index, not the full narrative store.
4. Dossier stores synthesized continuity state; it must cite canonical unit IDs/fact IDs.
5. Relationship and plot-thread views are separate projections, not inline timeline overload.

---

## 8. Required Telemetry

Every cohort summary for this lane should include:

- stage pass counts (Capture/Routing/Proposal/Projection),
- unresolved-unit rate,
- new-hub proposal rate and acceptance rate,
- retrieval precision on scoped prompts (must-include / must-exclude),
- cost (`min/mean/max/sum`),
- context pack size (`tokens_in_context`, units included).

---

## 9. Decision Rule

When tradeoffs conflict:

1. Preserve grounding.
2. Preserve retrieval relevance.
3. Preserve debuggability.
4. Improve prose quality only after 1-3 are satisfied.

If a change improves prose but weakens grounding/relevance observability, reject it.

---

## 10. Review Cadence

- Re-evaluate this checklist after any benchmark redesign.
- Reconfirm canonical/derived boundaries when adding a new projection type.
- Reconfirm cost envelope after each new LLM stage.
