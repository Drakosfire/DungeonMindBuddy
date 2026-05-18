# PR55 Lane-Aware Gold Report

## Changes
- Added lane-aware gold constraints for Q1/Q3/Q5 required groups.
- Required rendered section checks now enforced via provenance map.
- Added subject-class, source-kind, path eligibility, and navigation-only evidence rejection checks.

## Disallowed evidence roles
- `navigation_only` cannot satisfy lane-aware required groups.
- Non-corpus paths (eval/docs/gold/artifacts) are rejected for required-group evidence.

## Benchmark snapshot
- Source report: `/tmp/c1s4_pr55_lane_aware_multimode_report.json`.
- All three retrieval modes currently fail required groups under strict lane-aware gold (valuable signal, no retrieval tuning done in PR55).

## Known limitations
- Current packets in this environment contain empty admitted context for benchmark rows, so lane-aware acceptance rates are uniformly zero.

## Recommendation for PR56
- Diagnose upstream packet-generation/ingestion path to restore admitted evidence flow, then reassess lane-aware group recall before any tuning.
