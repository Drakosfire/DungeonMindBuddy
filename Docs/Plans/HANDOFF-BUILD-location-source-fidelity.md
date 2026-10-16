# BUILD: Location source fidelity experiment

ACTIVE. PRIME solo; ARCHITECTURE independent review. Base
0bb78d4499d7ea2fd66fd3a936405caa4291d1d4; branch
codex/worldbuilding-location-source-fidelity; /tmp/prime-recap-mention-boundaries.
Serial successor to accepted #1246/#1247. Their implementation leases ended.
Disjoint DOGFOOD #1235/#1237 presentation and #1244 evidence packaging.

Introduce exact Gazetteer1.13, inheriting1.12 and changing only location-pass
instructions: distinguish literal quotations from supported paraphrases and
explicitly named places from generic illustrative classes. Do not infer local
scope from a setting document alone, and do not turn an institution's actor-role
mention into a second physical-site identity without site evidence. Preserve
named sites and supported location/trade details; do not drop difficult facts.
No name-specific deterministic filter or manual candidate polishing.

Exclusive write set:
- This handoff
- src/graph_memory/extraction/worldbuilding_location_source_fidelity.py (new)
- src/graph_memory/extraction/worldbuilding_profile_catalog.py
- apps/live_control_server/services/worldbuilding_ge_execution.py
- apps/live_control_server/services/extract_promote.py (exact1.13 observation admission)
- tests/test_worldbuilding_location_source_fidelity.py (new)
- tests/test_worldbuilding_ge_execution.py
- tests/test_worldbuilding_source_observations.py
- tests/test_worldbuilding_gazetteer_profile.py
- evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json (catalog implementation fingerprint only)

One PR. Verify exact profile production dispatch, GE service and review/publication
preview admission with synthetic provider/disposable APP. Keep previous profiles,
retainers, schema/defaults, evidence/identity authority and semantic gold unchanged.
Independent review before merge. Fresh candidate-only comparison follows merge
under existing GE→OpenRouter DeepSeekV4.1Flash approval; no runtime or World writes
in implementation. Record losses and false claims against frozen expectations.
