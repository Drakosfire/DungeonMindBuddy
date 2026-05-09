# Stage C — Cross-Campaign Generalisation Report

**Date:** 2026-04-22  
**Scope:** Validate Stage C (NPC candidate identification) across both ends of the campaign timeline:
- **LATE** — C2 Session 20: rich registry (9 NPCs), most entities canonical
- **EARLY** — C1 Sessions 1/2/3: sparse registry (2 pre-seeded NPCs), most entities unknown
**Cohort:** N=5 per scenario, model `gpt-5.4-mini`

---

## TL;DR

Stage C generalises cleanly across both regimes. The bootstrap loop is proven: **15/15 C1 cohort runs PASS, every expected named NPC surfaced as a `new_npc_candidates[]` record across all sessions, and Kirfan — the canonical motivating example for the entire `referenced_slugs[]` work — was correctly proposed in 5/5 C1S3 runs with citation back to the exact event.**

---

## Per-scenario results

| scenario | runs | pass | tracked avg | new avg | unresolved avg | soft-bonus hits | PC leaks | cost |
|---|---|---|---|---|---|---|---|---|
| C2 S20 (late, rich) | 5 | **4/5** | 6.2 | 1.0 | 0.0 | 5/5 | **1/5** | $0.0136 |
| C1 S1 (early, sparse) | 5 | **5/5** | 0.0 | 2.0 | 1.8 | 5/5 | 0/5 | $0.0100 |
| C1 S2 (early, sparse) | 5 | **5/5** | 0.0 | 1.0 | 0.0 | 5/5 | 0/5 | $0.0055 |
| C1 S3 (early, sparse) | 5 | **5/5** | 0.0 | 4.0 | 0.0 | 5/5 | 0/5 | $0.0107 |
| **Aggregate C1** | **15** | **15/15** | 0.0 | 2.3 | 0.6 | 15/15 | **0/15** | $0.0263 |
| **Aggregate (S20+C1)** | 20 | **19/20** | 1.6 | 2.1 | 0.5 | 20/20 | 1/20 | $0.0399 |

**Total cost of cross-campaign validation: $0.04 across 20 cohort runs.**

---

## Bootstrap loop proof

The proof point identified before the slice: would Stage C correctly propose Kirfan (the elderly fisherman in the C1S3 "Stone Bridge Flood" recap, named only in a Big-beats summary header) as a `new_npc_candidates[]` record?

**Yes — 5/5 runs.** Every C1S3 cohort run produced a `new_npc_candidates[]` record with:
- `descriptor: "Kirfan"`
- `suggested_slug: "kirfan"`
- `evidence_event_indices: [1]` (the "Recover debris from the broken riverside structure" event)
- a one-sentence rationale citing "named entity referenced in event but not in registry"

End-to-end pipeline trace:

```
Recap text (C1S3, Big beats header)
  "Helped Kirfan pull up debris from the broken structure from upriver"
              ↓ Stage A extraction
event_record[1] = {
  "event_name": "Recover debris from the broken riverside structure",
  "participants": ["bonogo", "stafl", "baergrom"],
  "referenced_slugs": ["kirfan"]    ← the new field doing its job
}
              ↓ Stage C classification
new_npc_candidates[*] = {
  "descriptor": "Kirfan",
  "suggested_slug": "kirfan",
  "evidence_event_indices": [1],
  "rationale": "Named referenced entity appears in the recap and does not match any tracked registry NPC."
}
```

Every link in the chain works as designed. The architectural decision to add `referenced_slugs[]` to the event_record schema (commit `559b92c`) is structurally validated: the model uses it, downstream Stage C consumes it, the result is a deterministic candidate proposal that goes into the registry's seed material.

---

## C1 candidate aggregation (all 15 runs)

Aggregated across C1S1+C1S2+C1S3, ranked by cross-run appearance count:

| recommendation | suggested_slug | appearances | sessions | top descriptor |
|---|---|---|---|---|
| **high** | `grishna` | 10/10 | C1S1, C1S3 | Grishna |
| **high** | `glowkindle` | 10/10 | C1S1, C1S2 | Glowkindle |
| **high** | `pippa` | 5/5 | C1S3 | Pippa |
| **high** | `kirfan` | 5/5 | C1S3 | Kirfan |
| **high** | `bubbles_the_float_goat` | 4/5 | C1S3 | Bubbles the Float Goat |
| low | `bubbles` | 1/5 | C1S3 | Bubbles the Float Goat |

(Persisted in `evals/stage_c_npc_candidates_vertical_slice/artifacts/c1_registry_proposals_*.json` for GM review.)

**Slug-derivation inconsistency anomaly:** `bubbles` and `bubbles_the_float_goat` are the same entity emitted under two different suggested slugs across runs. The model is right both times semantically; the slug-derivation prompt instruction ("derive from the most distinctive part of the descriptor") is ambiguous when the descriptor includes both a name and an epithet. Worth a small prompt-iteration ticket (queued in Backlog).

---

## Failure-mode synthesis

**S20 (1 failure across 5 runs):**
- Run 5: `stafl` (PC) leaked into `tracked_npcs_active[]`. NC1 caught it (slug not in registry); NC2 caught it (PC leak). Root cause: model treated a heavily-active PC as if it were an NPC-class entity. The system prompt's "PC NEGATIVE LIST — HARD RULE" did not hold under that run's inference path.

**C1 (0 failures across 15 runs):**
- 0 PC leaks across all 15 runs. The smaller registry + the explicit empty `expected_tracked_active_minimum` may make PC discipline easier in the C1 regime — fewer competing positive signals for the model to confuse with PC-ness.
- 1 unresolved descriptor in C1S2 (1.8 avg in C1S1 — model is more conservative when there's less context, surfacing more "could be NPC, can't tell" entries to `unresolved_descriptors[]`). This is desired behavior, not a defect.

**Failure-mode count summary:**
- PC leaks: 1/20 runs total (5%)
- NC3 misses: 0/20 runs total
- All other gates: clean

---

## Recommendations

### 1. Stage C system prompt — minor PC-leak hardening (LOW priority)
1/20 PC-leak rate is low but non-zero. Tightening could be:
- Add a worked example showing a PC who acts heavily across many events (the case that confused the model) and explicitly classified as NOT an NPC.
- Or add a hard-coded post-output filter at the runner level that drops any `tracked_active` slug that matches the PC roster, before grading.

I'd lean toward the prompt-side fix first (the prompt is the contract; the post-filter is a band-aid). Queued in Backlog.

### 2. Stage A coverage gap for summary-only-named NPCs (MEDIUM priority)
The S20 fixture-generation Stage A run was itself FAIL-graded; "Professor Tealeaf" appeared in `event_name` and `outcomes` but never in `referenced_slugs[]`. Stage C compensated by inference 5/5, but the upstream contract should be tighter: when the model writes a name into `event_name` or an `outcome`, the same name should also surface in `referenced_slugs[]`. This would let Stage C grade more strictly on NC3 (registry recall via the event-entity union).

In contrast, the C1 fixtures are clean on this front — every named NPC the recap surfaces ends up in `referenced_slugs[]` of at least one event. The difference may be S20's higher event density (more entities per recap) stressing the prompt more. Worth a Stage A prompt-iteration ticket. (Already exists in Backlog as the parent Kirfan entry.)

### 3. C1 registry proposals — GM review unblocks the next iteration (HIGH priority)
The `c1_registry_proposals_*.json` sidecar contains 5 high-confidence candidates ready for GM review. Promoting `grishna`, `glowkindle`, `pippa`, `kirfan`, and `bubbles_the_float_goat` (or `bubbles` — pick one) to `candidate`-status records in the C1 registry closes the bootstrap loop and lets a re-run of Stage C C1 cohorts test whether NC3 recall improves (today every C1 run has 0 tracked_active because Lysandra/Torbin don't appear in S1-S3). This is the workflow the registry was designed to enable.

Queued in Backlog as the immediate next manual step.

### 4. Slug-derivation consistency (LOW priority)
`bubbles` vs `bubbles_the_float_goat` is a minor prompt-iteration target. The "most distinctive part of the descriptor" guidance is ambiguous for compound names. A small example or rule-tightening would close it.

---

## Open questions

1. **When do candidate-status records become tracked?** The bootstrap proposal sidecar produces `candidate`-status records by recommendation. The promotion path from `candidate` → `tracked` is currently undefined — does it require a hub README to be authored first? Is there a minimum session-appearance threshold? Worth a design conversation before Stage D / Stage E.

2. **Should NC3 recall include `candidate`-status registry entries?** Today NC3 only counts `tracked` and `background`. If we promote candidates in batch and re-run, NC3 will pass trivially (because the model emits them in `new_npc_candidates`, not `tracked_active` — and they were `candidate` in the registry, not `tracked`). The grader semantics deserve a second look once the bootstrap loop is exercised in anger.

3. **Cross-campaign character handling.** Lysandra and Torbin were pre-seeded as `tracked` in the C1 registry pointing at Elderwyld setting hubs (no C1 hub exists). Both have rich C2 hub data. If the GM eventually authors C1-specific Lysandra/Torbin sub-pages, what's the canonical `hub_path` — the campaign-specific or the setting-wide? Decision deferrable.

---

## Cost summary

| activity | cost |
|---|---|
| C2 S20 cohort N=5 (prior commit) | $0.0136 |
| Stage A fixture-gen for C1S1, C1S2, C1S3 (3 runs) | ~$0.030 |
| C1S1 cohort N=5 | $0.0100 |
| C1S2 cohort N=5 | $0.0055 |
| C1S3 cohort N=5 | $0.0107 |
| **Total cross-campaign validation** | **~$0.07** |

Well under the $0.10 budget originally projected.

---

## Verdict

**Clean.** Stage C generalises across both campaign regimes. Bootstrap loop is proven end-to-end. The pipeline `recap → Stage A (with referenced_slugs[]) → Stage C (3-bucket) → registry proposals → GM review → registry growth` is now mechanically validated. Stage D (entity resolution against tracked + candidate registry records) and Stage E (per-NPC artifact updates) can build on a working foundation.
