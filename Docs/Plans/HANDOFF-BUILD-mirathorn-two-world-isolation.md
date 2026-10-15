# BUILD: prove Worldbuilding publication stays isolated across managed Worlds

**Status:** COMPLETED — merged as `f5487a8d57cac7335c3dc4f2b3cb502c92f30ad3`; this implementation lease is closed.

- **Base:** DungeonMindBuddy `main@3a890b9ec8b4e4c9924779249fe8570b7ecf9d1c`
- **Branch:** `codex/mirathorn-two-world-isolation`
- **Topology:** parallel-independent from open PR #1193 at `eb70124039890e4887b32e8c96b4cef797f4fea2`; this slice changes no shared profile, catalog, execution, UI, or gold paths.
- **Runtime/state:** none. Tests use temporary workspace and native-authority fixtures. No server, operator database, retained World, provider, corpus, or port changes.

## Capability

Prove that two registered managed Worlds with distinct active native Graph bindings publish each exact registered Worldbuilding source only to its own native World. Exercise the ordinary Build source registration, extraction-run, prepare, and confirm services with two World records present in the same registry. A result for one World must not advance or populate the other World or fall back to the default World.

## Exact write set

- This handoff.
- `tests/test_cutover_worldbuilding_authority_port.py`.
- `tests/_cutover_d3a_blocker_safe_fixtures.py` — assign each synthetic source its own component directory, preserving frozen evidence when multiple runs share a workspace.

If the owning-boundary test exposes a production defect, stop and return to PRIME to split or amend the scope before changing production code.

## Required witness

Use distinct managed IDs and native IDs (for example `managed-a` → `native-alpha`, `managed-b` → `native-beta`) in one temporary registered-World workspace. Seed independent parent revisions and use the actual Build registration and worldbuilding publication services with the native Graph authority boundary isolated in a deterministic fixture.

The test must prove:

1. Preparing each registered source seals its own managed ID and resolves its own native ID.
2. Confirming A advances only `native-alpha`; B remains exactly at its original head and has no A publication.
3. Confirming B advances only `native-beta`; A remains at its already-confirmed head and neither write reaches the default World.
4. Each child contains the accepted source-backed candidates for its own command, while no cross-world plan or source binding is accepted.
5. Swapping source/run bindings or forging the default target is rejected before publication; both native heads remain unchanged.
6. The original source artifacts and content remain distinct and immutable throughout the two publications.

Existing one-World tests remain in place. Do not weaken their stale-parent, source-binding, recovery, or confirm-time proof checks.

## Verification

- Run the focused Worldbuilding authority-port test and the existing registered source-catalog publication test where its disposable PostgreSQL fixture is available.
- Preserve test skips/failures and distinguish local unit evidence from database-backed publication evidence.
- Run Ruff and `git diff --check`; inspect the complete base-to-head diff.
- Request ARCHITECTURE independent review of the exact completed head. This proves target isolation at the service/native-authority boundary; it does not claim Mirathorn gold completeness, live Agent retrieval, server dogfood, or operator acceptance.
