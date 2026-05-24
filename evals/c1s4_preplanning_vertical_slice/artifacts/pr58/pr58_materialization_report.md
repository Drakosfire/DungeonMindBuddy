# PR58 Retrieval Universe Audit

## Scope
Q1/Q3/Q5 lane-aware expected evidence groups, including known gaps and support-enabled modes.

## Executive Summary
- Corpus markdown hubs/dossiers/recaps are materialized into the Step2C retrieval record universe (0 corpus rows still `source_not_materialized_as_retrieval_record`).
- Step2C retrieval universe combines Step0 session-memory records, PR58 campaign-corpus section records, and support-card augmentation.
- Support cards are materialized and retrieval-probe reachable (2 rows); Step2C candidate hits: 0; retrieved misses after probe hit: 2.
- Known-gap targets are audited against packet `known_context_gaps` and not treated as filesystem/index artifacts.

## What this proves
1. Existence/hygiene for corpus paths is mostly not the bottleneck.
2. Record-universe materialization is the primary early surface for corpus hub/dossier/recap evidence.
3. Support-card Step2C visibility depends on bundle assembly (not admission).

## Caveats

**Probe semantics:** `retrieval_probe_hit` uses the same candidate query API as Step2C (`query_session_memory_candidate`) over mode-specific record universes. Lexical file presence is separate (`lexical_file_probe_hit`).

**Materialization ≠ lane-correct rendering:** PR58 makes hub/dossier/recap evidence retrievable with correct `source_kind` / `evidence_role`. Lane-aware gold also requires the right **rendered section** (`character_party_behavior`, `location_worldbuilding`, …).

That second bar is still limited by **lane-budget admission** (`build_lane_budgeted_admission` → `_infer_lane` in `context_admission.py`):

1. Classifier lanes `location_context`, `party_timeline`, `pc_timeline`, and `worldbuilding` are folded into the budget key `prior_campaign_memory`.
2. Each admitted item’s `presentation_lane` is overwritten with that budget key.
3. `render_context_packet()` routes `prior_campaign_memory` to **Prior campaign memory**, not Character or Location.

So corpus rows can appear in `candidate_context` (and even satisfy legacy text match) while lane-aware grading still fails (`incompatible_required_lane`, `wrong_rendered_section`). Canvas **required recall %** can stay low for that reason alone.

**Audit-aligned misses after PR58** (not fixed in this PR):

| Target | Why it still fails |
|--------|-------------------|
| Grishna (Q1) | Thin hub + question retrieval miss |
| Stone Bridge (Q3) | Materialized; question retrieval / lane placement miss |
| Q5 support | Bundle assembly fixed; support card outranked on the real question (PR59) |

Follow-up: query/ranking (PR59); preserve planner lanes through admission + renderer (PR60).
