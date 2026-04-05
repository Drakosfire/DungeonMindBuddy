# Auto-Escalation Report (Pilot + Full Corpus)

**Date:** 2026-04-03  
**Repo:** `DungeonMindBuddy`  
**Scope:** Evaluate two-pass ingestion policy (`base -> escalate`) after taxonomy v3 rollout.

## 1) Runs and Configuration

### Pilot run (10 files)
- Store: `dungeonbuddy_store_escalation_pilot`
- Base role: `fast_smart_mini`
- Escalation role: `highest_intelligence`
- Auto-escalate: enabled
- `--escalate-world`: **true**
- Thresholds:
  - `other_rate > 0.30`
  - `unknown_kind_rate > 0.08`
  - `other_missing_facets_rate > 0.40`
  - `entities_per_chunk < 0.80`
  - `facts_per_chunk < 2.00`

### Full corpus run (130 files)
- Store: `dungeonbuddy_store_escalation_full_mini_to_54`
- Base role: `fast_smart_mini`
- Escalation role: `highest_intelligence`
- Auto-escalate: enabled
- `--escalate-world`: **false** (disabled as requested)
- Same thresholds as above

## 2) Topline Outcomes

| Run | Corpus files | Completed ingests | Zero-output files | Escalation candidates | Escalated | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| Pilot | 10 | 10 | 0 | 9 | 9 | 839s (~14.0m) |
| Full | 130 | 121 | 9 | 40 | 40 | 5649.6s (~94.2m) |

Notes:
- Full run "completed ingests" aligns with `decisions_count=121`.
- 9 files had `facts_delta=entities_delta=evidence_delta=0` (cards/templates/token sheets and similar non-ingestible docs).

## 3) Escalated-Subset Aggregate Quality Deltas

The table below compares **base vs escalated outputs only on the escalated subset**.

### Pilot (9 escalated files)
- `other_rate`: **29.13% -> 31.38%** (+2.25pp, worse)
- `unknown_kind_rate`: **1.07% -> 0.00%** (-1.07pp, better)
- `other_missing_facets_rate`: **3.05% -> 13.64%** (+10.59pp, worse)
- `entities_per_chunk`: **1.297 -> 1.454** (+12.1%, higher)
- `facts_per_chunk`: **4.265 -> 4.509** (+5.7%, higher)

### Full (40 escalated files)
- `other_rate`: **36.91% -> 42.45%** (+5.54pp, worse)
- `unknown_kind_rate`: **0.07% -> 0.29%** (+0.22pp, worse)
- `other_missing_facets_rate`: **8.41% -> 23.59%** (+15.18pp, worse)
- `entities_per_chunk`: **1.066 -> 1.229** (+15.3%, higher)
- `facts_per_chunk`: **3.326 -> 3.782** (+13.7%, higher)

Interpretation:
- Escalation improves **throughput density** (more entities/facts per chunk).
- Escalation degrades **taxonomy quality** (more `other`, more facet-missing `other`).

## 4) Pairwise File-Level Win/Loss Counts

### Full run (40 escalated files)
- `other_rate` (lower is better): improved **9**, worsened **30**, unchanged **1**
- `unknown_kind_rate` (lower): improved **1**, worsened **4**, unchanged **35**
- `other_missing_facets_rate` (lower): improved **8**, worsened **29**, unchanged **3**
- `entities_per_chunk` (higher): improved **30**, worsened **7**, unchanged **3**
- `facts_per_chunk` (higher): improved **36**, worsened **4**, unchanged **0**

### Pilot run (9 escalated files)
- `other_rate`: improved **3**, worsened **5**, unchanged **1**
- `unknown_kind_rate`: improved **4**, worsened **0**, unchanged **5**
- `other_missing_facets_rate`: improved **1**, worsened **6**, unchanged **2**
- `entities_per_chunk`: improved **7**, worsened **1**, unchanged **1**
- `facts_per_chunk`: improved **6**, worsened **2**, unchanged **1**

## 5) Trigger Mix (Full Run)

Escalation trigger frequencies across 40 escalated files:
- `other_rate > 0.30`: **32**
- `entities_per_chunk < 0.80`: **9**
- `other_missing_facets_rate > 0.40`: **6**
- `facts_per_chunk < 2.00`: **2**

Counts exceed 40 because multiple triggers can fire on one file.

## 6) Representative Observations

### Strong regressions (quality)
- `Longmont Campaign/NPCs/Torbin Jove/Torbin Characteristics.md`
  - `other_rate` delta: **+0.3556**
- `Festival/Cultural Ceremonies at the Temple of the Aspitome.md`
  - `other_rate` delta: **+0.1761**
- `Bardic Storytelling Circle.md`
  - `other_missing_facets_rate` delta: **+0.55**
- `Item Name_ Silver Raven.md`
  - `other_missing_facets_rate` delta: **+0.55**

### Positive outliers
- `The Hearthbound Bake-Off.md`
  - `other_rate`: **0.3409 -> 0.3023**
  - `other_missing_facets_rate`: **0.0667 -> 0.0**
- `Session 4 - The Grotesque Tree of Hempholm.md`
  - `other_rate`: **0.0714 -> 0.0588**
  - `other_missing_facets_rate`: **0.5 -> 0.0**
- `Session 18 - Recap.md`
  - `other_rate`: **0.1818 -> 0.1220**
  - `other_missing_facets_rate`: **0.5 -> 0.4**

## 7) Core Learnings

1. Current policy optimizes for **volume**, not **quality**.  
   Escalation frequently increases extracted entities/facts while hurting taxonomy health.

2. Blanket world escalation was a false-positive amplifier.  
   Pilot (`--escalate-world=true`) escalated 9/10 files and produced quality regressions, which validated disabling this for full corpus.

3. Triggering is useful; acceptance is missing.  
   Triggering correctly identifies "interesting" files, but "escalate and always keep" is the wrong merge policy.

4. Acceptance gate is now mandatory for cost-effectiveness.  
   Hypothetical gate: keep escalated output only when both:
   - `other_rate` non-worse, and
   - `other_missing_facets_rate` non-worse  
   would accept only **3/40** full-run escalations (pilot: **2/9**), preventing most quality regressions and unnecessary spend.

5. `other_missing_facets_rate` is a high-signal guardrail.  
   It captured many taxonomy degradations not visible from raw fact/entity count growth.

## 8) Recommended Policy Update (Next Implementation Step)

Add an acceptance phase after escalated pass:
- Compute `delta_other_rate` and `delta_other_missing_facets_rate`.
- Accept escalated output only if both are `<= tolerance` (default tolerance `0.0`).
- Otherwise reject escalated output and retain base result for the file.
- Write per-file decisions to `escalation_acceptance.json`:
  - `accepted`/`rejected`
  - reason(s)
  - base and escalated metrics
  - deltas

Optional extension:
- Include `unknown_kind_rate` as a third quality criterion.
- Add `quality_priority_mode` to prefer lower-taxonomy-risk outputs over higher fact volume.

## 9) Artifact Index

- Full summary: `dungeonbuddy_store_escalation_full_mini_to_54/logs/batch_ingest_summary.json`
- Full decisions: `dungeonbuddy_store_escalation_full_mini_to_54/logs/escalation_decisions.json`
- Full runs (base vs escalated metrics): `dungeonbuddy_store_escalation_full_mini_to_54/logs/escalation_runs.json`
- Pilot summary: `dungeonbuddy_store_escalation_pilot/logs/batch_ingest_summary.json`
- Pilot decisions: `dungeonbuddy_store_escalation_pilot/logs/escalation_decisions.json`
- Pilot runs: `dungeonbuddy_store_escalation_pilot/logs/escalation_runs.json`
