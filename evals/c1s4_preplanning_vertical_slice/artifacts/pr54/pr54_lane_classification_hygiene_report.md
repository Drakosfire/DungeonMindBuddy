# PR54 Lane Classification and Retrieval-Corpus Hygiene Report

## Current Drivers
- Lane classification is assigned in admission (`classify_presentation_lane`) and section placement is performed in renderer (`render_context_packet`) using `presentation_lane` + `source_kind`.
- PR54 adds shared deterministic helpers in `context_classification.py` and reuses them in metrics/hygiene paths.

## Helpers Added
- `is_allowed_retrieval_corpus_path(path)`
- `infer_context_subject_class(item)`
- `infer_planner_lane(item)`
- `is_navigation_only_context(item)`
- `is_context_compatible_with_required_lane(item, required_lane)`

## Denied Retrieval Path Patterns
- path parts: `evals/`, `docs/`, `tests/`, `gold/`, `canvas_templates/`, `artifacts/`, `docs/plans/`, `analysis/`
- basename patterns: `pr*_report.md`, `pr*_analysis.md`, `pr*_summary.json`, `*_gold.json`, `*.canvas.tsx`
- explicit allow: `corpus/eldyrwild-markdown/**`

## Navigation-only Headings
- Retrieval keywords
- Suggested reads
- Cross-references
- NPCs anchored here
- Campaign-canon NPCs anchored here
- NPC and social anchors
- Sub-locations and scene anchors

## Mapping Examples
- `.../Locations/stone_bridge/README.md` -> `location_worldbuilding`
- `.../Locations/rivers_edge_pub/README.md` -> `location_worldbuilding`
- `.../Locations/hempholm/README.md` -> `location_worldbuilding`
- `.../NPCs/pippa/README.md` -> `character_party_behavior`
- `.../NPCs/bubbles_the_float_goat/README.md` -> `character_party_behavior`
- `.../NPCs/grishna/README.md` -> `character_party_behavior`

## Hygiene Enforcement Point
- Retrieval-corpus denial is now enforced in preplanning context bundle item construction (`preplanning_context_bundle.py`) and surfaced in metrics via shared helper usage.

## Unresolved Limitations
- Navigation-only detection is deterministic text/heading based, not full structural markdown parsing.
- Compatibility helper is scaffolding for PR55 lane-aware gold and does not rewrite benchmark gold in PR54.

## Recommendation for PR55
- Use `is_context_compatible_with_required_lane` + `is_navigation_only_context` in benchmark matching rules for stricter lane-aware evidence validation.
