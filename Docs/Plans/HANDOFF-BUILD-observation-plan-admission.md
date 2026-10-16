# BUILD: Shared observation profile admission

ACTIVE PRIME solo, ARCHITECTURE independent review. Base
98b28b08470ae9320e638dda8d8810b492b86ca0; branch
codex/worldbuilding-observation-plan-admission. Serial successor to #1248,
whose write lease ended. Disjoint DOGFOOD UI/source-packaging leases.

Isolated actual prepare rejects1.13 because inert write-plan builder retains a
literal1.11 gate. Centralize exact observation-profile identities in the closed
profile catalog and consume it at review, evidence preview and plan building.
Preserve closed unknown-profile rejection, v0.2 requirement and all validations.

Exclusive paths:
- This handoff
- src/graph_memory/extraction/worldbuilding_profile_catalog.py
- src/graph_memory/worldbuilding_write_plan.py
- apps/live_control_server/services/extract_promote.py
- tests/test_worldbuilding_source_observations.py
- evals/graph_memory_layer/examples/mirathorn_worldbuilding_query_gold_v1/gold.json (catalog fingerprint only)

OnePR; actual inert plan production regression for1.11/1.12/1.13, reject older
observation-incompatible profile and wrong candidate version. No retained write,
provider, serving, schema or fact changes. Fresh clone prepare follows accepted
code; independently review its exact effect before any confirmation.
