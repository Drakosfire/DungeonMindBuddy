# PR55 Lane-Aware Gold Report

## Changes
- Added synthetic known-gap candidates (`known_gap:<gap>`) for lane-aware required-group matching.
- Added known-gap lane compatibility and rendered-section compatibility handling.
- Relaxed path hygiene for explicitly allowed `support_knowledge_card` evidence while still hard-blocking eval/docs/gold/artifacts/plans leakage paths.
- Added `text_contains_all` matcher semantics and tightened selected gold groups to conjunctive phrases.

## Disallowed evidence roles
- `navigation_only` cannot satisfy lane-aware required groups.
- Eval/docs/gold/artifact/plan paths are denied for required-group evidence.

## Benchmark snapshot
- Source report: `/tmp/c1s4_pr55_lane_aware_multimode_report.json`.
- Prior-only required-group hits: 1 / 8.
- Support-content-only required-group hits: 1 / 9.
- Lexical-hints required-group hits: 1 / 9.
- Lane-aware legacy-would-have-hit rejections observed: 0.

## Known limitations
- Admitted-context emptiness for some rows still dominates total recall outcomes in this snapshot.

## Recommendation for PR56
- Continue with upstream packet-admission diagnostics to improve non-empty admitted context coverage, then measure lane-aware rejection deltas on richer packets.
