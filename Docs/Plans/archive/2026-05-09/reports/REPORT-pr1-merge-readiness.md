# REPORT — PR #1 merge readiness

## Rebase strategy
- Could not execute upstream rebase steps from the handoff because this local branch has no configured remote (`origin`) in this environment.
- Applied merge-playbook follow-up changes directly on current branch tip.
- Final HEAD OID at report time: 7a1bbe2

## Changed files summary
- `src/lexicon_phase_b/route_equivalence_manifest.py`
  - Added unknown-kind filtering policy (`entity_kind == "unknown"` => skip edge).
- `src/lexicon_phase_b/schemas.py`
  - Documented `source_type="npc_registry"` semantics as registry-contract lineage, not NPC-only entity restriction.
- `tests/lexicon_phase_b/test_route_equivalence_entity_kind_inference.py`
  - Added unknown-kind filtering test and campaign registry seed assertions.
- `tests/lexicon_phase_b/test_route_equivalence_record_defaults.py`
  - Asserts route-equivalence contract defaults.
- Renamed PR-specific root tests into `tests/lexicon_phase_b/` naming to avoid collision intent from merge playbook:
  - `test_route_id_path_shapes.py`
  - `test_route_equivalence_record_defaults.py`
  - `test_route_equivalence_entity_kind_inference.py`

## Diff scope excerpt
- `git diff --stat`:
  - `src/lexicon_phase_b/route_equivalence_manifest.py | 2 ++`
  - `src/lexicon_phase_b/schemas.py | 7 +++++-`
  - `tests/lexicon_phase_b/test_route_equivalence_entity_kind_inference.py | 25 ++++++++++++++++++++++`
  - `tests/lexicon_phase_b/test_route_equivalence_record_defaults.py | 2 ++`

## Verification commands and exit codes
- `uv run pytest tests/lexicon_phase_b -q` → exit 0 (8 passed)
- `uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q` → not runnable in this branch (paths absent locally)
- `uv run python scripts/audit_world_campaign_alignment.py` → not runnable in this branch (script absent at expected path)

## Before/after route-id example
- Input (directory shape):
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/Wolf Manor/`
- Input (file shape):
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/Wolf Manor/README.md`
- After behavior:
  - both shapes resolve to the same entity slug and route prefix pattern (`...:location:wolf-manor`) via terminal entity-folder extraction.

## Merge verdict
- **Not ready** in this local environment, because full handoff success gates requiring upstream rebase proof (`origin/main` diff) and required script/tests at listed paths cannot be executed without the remote/main tree and missing script/test files.
