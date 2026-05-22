# PR63 Retrieval Universe Audit

## Scope
Q1/Q3/Q5 lane-aware expected evidence groups, including known gaps and support-enabled modes.

## Executive Summary
- Corpus markdown hubs/dossiers/recaps are materialized into the Step2C retrieval record universe (0 corpus rows still `source_not_materialized_as_retrieval_record`).
- Step2C retrieval universe combines Step0 session-memory records, PR58 campaign-corpus section records, and support-card augmentation.
- Support cards are materialized and retrieval-probe reachable (2 rows); Step2C candidate hits: 2; retrieved misses after probe hit: 2.
- Gold `known_context_gaps` are evaluator-only; planner packets must not carry `known_context_gaps`.
- Known-gap manifest rows classify as `known_gap_eval_only_not_in_planner_packet` unless oracle leak is detected.

## What this proves
1. Existence/hygiene for corpus paths is mostly not the bottleneck.
2. Record-universe materialization is the primary early surface for corpus hub/dossier/recap evidence.
3. Support-card Step2C visibility depends on bundle assembly (not admission).

## Caveats
`retrieval_probe_hit` uses the same candidate query API as Step2C (`query_session_memory_candidate`) over mode-specific Step2C record universes; lexical checks are kept separate under `lexical_file_probe_hit`.
