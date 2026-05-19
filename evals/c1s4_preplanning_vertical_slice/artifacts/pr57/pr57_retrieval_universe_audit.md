# PR57 Retrieval Universe Audit

## Scope
Q1/Q3/Q5 lane-aware expected evidence groups, including known gaps and support-enabled modes.

## Executive Summary
- Corpus markdown hubs/dossiers generally exist and pass hygiene but are often not materialized into the Step2C retrieval record universe (9 rows).
- Step2C retrieval universe is currently dominated by Step0 session-memory materialization plus support-card augmentation, not arbitrary corpus markdown hub ingestion.
- Support cards are materialized and retrieval-probe reachable (2 rows), yet some still miss Step2C retrieved/candidate surfaces (2 rows).
- Known-gap targets are audited against packet `known_context_gaps` and not treated as filesystem/index artifacts.

## What this proves
1. Existence/hygiene for corpus paths is mostly not the bottleneck.
2. Record-universe materialization is a primary early failing surface for corpus hub/dossier evidence.
3. There is a separate Step2C query/assembly mismatch for support evidence that is retrievable in direct probes.

## Caveats
`retrieval_probe_hit` uses the same candidate query API as Step2C (`query_session_memory_candidate`) over mode-specific Step2C record universes; lexical checks are kept separate under `lexical_file_probe_hit`.
