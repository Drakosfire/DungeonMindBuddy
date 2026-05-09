# REPORT — PR #1 merge-readiness

## Changed files summary
- `src/lexicon_phase_b/route_equivalence_manifest.py`
  - Fixed slug derivation to support both file-style (`.../<slug>/README.md`) and directory-style (`.../<slug>/`) hub paths.
  - Added deterministic `_extract_entity_slug` helper to avoid bucket-folder (`NPCs`, `Locations`) slug leakage.
- `tests/test_token_resolution_resolver.py`
  - Added tests for file-style and directory-style path slug derivation.
- `tests/test_token_resolution_contracts.py`
  - Added assertions for route-equivalence contract defaults.
- `tests/test_benchmark_lexicon_seeds.py`
  - Added seed-style test for non-NPC kind inference (`location`).

## Command outputs
- `uv run pytest tests/test_token_resolution_resolver.py` → PASS (2 passed)
- `uv run pytest tests/test_token_resolution_contracts.py` → PASS (1 passed)
- `uv run pytest tests/test_benchmark_lexicon_seeds.py` → PASS (1 passed)
- `uv run pytest tests/lexicon_phase_b` → PASS (3 passed)
- `uv run python scripts/audit_world_campaign_alignment.py` → FAIL (file missing in branch/environment)

## Before/after sample for route-id derivation
- Before (directory-style path risk):
  - Input: `.../NPCs/Captain Lysandra Ironveil/`
  - Could derive slug from wrong segment in some shapes (bucket-folder drift risk).
- After (fixed):
  - Input: `.../NPCs/Captain Lysandra Ironveil/`
  - Output route id: `route:longmont-c1:npc:captain-lysandra-ironveil`
  - Input: `.../NPCs/Captain Lysandra Ironveil/README.md`
  - Output route id: `route:longmont-c1:npc:captain-lysandra-ironveil`

## Remaining risks
- `scripts/audit_world_campaign_alignment.py` is not present on this branch, so that required audit gate could not be executed in this environment.
- Source contract is still `npc_registry` scoped even though kind inference is generalized from path segments.

## Merge verdict
- **NOT READY** until `audit_world_campaign_alignment.py` is added/restored and run green, or an explicitly approved replacement audit command is provided.
