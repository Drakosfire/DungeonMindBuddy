# PR48 Lane Corpus Audit Report

This PR is audit-only. It does **not** change retrieval, admission, renderer behavior, or active gold.

## Findings
- Q1 has strong prior campaign memory recall; current packets are admitted as `prior_campaign_memory`.
- Q3 currently pressures known-gap admission more than lane-balanced worldbuilding placement.
- Q5 successfully pressures support-card retrieval in support modes and forbids support cards in prior-only mode.
- Corpus now contains first-class NPC hubs for Pippa, Bubbles, and Grishna, and a Hempholm location hub.
- Corpus still lacks first-class Stone Bridge and River's Edge Pub location hubs.

## Benchmark pressure gap
Current gold does not require rendered section placement for location/npc lanes; it primarily requires group keyword hits and known-gap phrases.

## Sequencing recommendation
1. PR49: add Stone Bridge/River's Edge location hubs and any missing continuity artifacts.
2. PR50: classify first-class location/NPC artifacts into `location_worldbuilding` and `character_party_behavior`.
3. PR51: update gold to require lane-balanced section placement.
4. PR52: only then evaluate shadow query expansion.
