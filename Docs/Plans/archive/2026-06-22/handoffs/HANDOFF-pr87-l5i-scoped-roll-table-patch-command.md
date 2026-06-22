---
document_id: dmb-handoff-pr87-l5i-scoped-roll-table-patch-command
title: PR 87 Handoff — L5I Scoped Roll-table Patch Command
status: completed
version: 0.1
created_at: "2026-05-29T17:00:00Z"
completed_at: "2026-05-29T17:55:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr86-l5h-pane-action-ui-append-observation.md
    role: prior_ui_action_slice
  - path: src/live_play/projections/commands.py
    role: command_contract
  - path: src/live_play/projections/write_results.py
    role: write_result_contract
  - path: src/live_play/projections/artifacts.py
    role: artifact_read_contract
---

# PR 87 Handoff — L5I Scoped Roll-table Patch Command

## Mission

Implement constrained backend `patch_artifact` semantics for roll-table markdown files in the existing command bus path (`POST /api/live/commands`) with stale-token protection, replace-text validation, parser validation, dry-run preview, audit event append, and scoped invalidations.

## Scope Delivered

- Added dedicated patch execution module:
  - `src/live_play/projections/artifact_patching.py`
- Implemented strict patch command constraints:
  - only `command_type=patch_artifact`
  - only `target.target_type=roll_table`
  - only `lane=prep_note`
  - payload allowlist + forbidden path-field rejection
  - required `expected_file_state_token`, `old_text`, `new_text`
  - optional `rationale`, `dry_run`
- Implemented roll-table source path resolution from `live_packet.known_roll_tables` only, with repo-root escape checks.
- Reused file-state token contract and parser contract:
  - `src/live_play/projections/artifacts.py` (`file_state_token_for_text`)
  - `src/live_play/roll_table_registry.py` (`parse_roll_table_text`)
- Implemented replace-text patch semantics:
  - exactly-once `old_text` match
  - no regex/unified-diff application
  - parse validation on patched markdown before write
  - temp-file + replace write strategy
- Implemented stale-token conflict behavior:
  - returns `status="conflict"` / `conflict_type="stale_artifact"`
  - no write, no event append
- Implemented dry-run preview behavior:
  - returns `status="noop"`
  - no write, no event append
  - includes patch metadata preview (`tokens`, `replacement_count`, truncated unified diff)
- Implemented accepted write behavior:
  - writes exactly one allowlisted roll-table markdown source file
  - appends one patch audit `state_note` event
  - returns invalidations for `live.artifact`, `live.capabilities`, `live.plan_view`, `live.events`
- Implemented idempotency handling for `patch_artifact`:
  - duplicate `idempotency_key` returns `status="noop"`
  - does not re-write file or append second event
- Added additive write-result metadata field:
  - `src/live_play/projections/write_results.py` (`metadata: dict[str, Any]`)
- Updated command bus dispatch:
  - `src/live_play/projections/command_bus.py`
  - `apps/live_control_server/routes/live.py` passes `repo_root()`
- Updated capabilities:
  - `src/live_play/projections/capability_registry.py` enables `patch_artifact` for roll_table only (with required fields + metadata)

## Tests Added/Updated

- Added:
  - `tests/test_live_artifact_patching.py`
- Updated:
  - `tests/test_live_command_bus.py`
  - `tests/test_live_artifact_reads.py`
  - `tests/test_live_control_server.py`

Coverage includes accepted patch, dry-run noop, stale-token conflict, payload validation rejects, old_text miss/duplicate rejects, parse-validation reject, malicious source-path reject, idempotency noop, mutation boundary assertions, and capability behavior.

## Out of Scope Preserved

- No React patch UI
- No markdown editor/diff viewer UI
- No generic capability runner
- No new patch endpoint outside existing `POST /api/live/commands`
- No non-roll-table patch support
- No `queue_canon_patch` enablement
- No retrieval refresh execution
- No job queue writes
- No current-state refresh inside command execution
- No browser-side file access

## Verification

```bash
uv run pytest tests/test_live_artifact_patching.py -q
uv run pytest tests/test_live_command_bus.py -q
uv run pytest tests/test_live_artifact_reads.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_projection_contracts.py -q
```
