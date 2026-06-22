---
document_id: dmb-handoff-pr90-l5l-fresh-recap-ingestion-session-bootstrap
title: PR 90 Handoff — L5L Fresh Recap Ingestion / Session Bootstrap
status: ready_for_implementation_after_pr89_merge
version: 0.1
created_at: "2026-05-29T20:00:00Z"
related_documents:
  - path: Docs/Plans/DESIGN-c2-live-control-l5-pane-state-boundaries.md
    role: primary_design_anchor
  - path: Docs/Plans/PLAN-c2-live-control-surface-query-pane.md
    role: parent_plan
  - path: Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md
    role: execution_tracker
  - path: Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr89-l5k-patch-ux-hardening-read-after-write-evidence.md
    role: prior_patch_hardening_slice
---

# PR 90 Handoff — L5L Fresh Recap Ingestion / Session Bootstrap

## Mission

Deterministic fresh recap ingestion and session bootstrap: recap file → session workspace → seeded live files → plan-view from `planning_beats`.

## Implementation map

| Area | Path |
|------|------|
| Paths / safety | `src/live_play/session_paths.py` |
| Recap heuristics | `src/live_play/recap_ingestion.py` |
| Bootstrap + CLI | `src/live_play/session_bootstrap.py` |
| Plan-view beats | `src/live_play/projections/plan_view.py` |
| Packet schema | `evals/c2_live_prep/live/schemas/live_packet.schema.json` (`planning_beats` optional) |
| Packet validation | `apps/live_control_server/schema_validation.py` (`validate_live_packet`) |
| Tests | `tests/test_live_session_bootstrap.py`, `tests/test_live_recap_ingestion.py` |
| Fixture | `tests/fixtures/live_bootstrap/session_22_fresh_recap.md` |
| Runbook | `Docs/Plans/RUNBOOK-c2-first-dogfood-planning-round.md` |

## Verification

```bash
uv run pytest tests/test_live_session_bootstrap.py -q
uv run pytest tests/test_live_recap_ingestion.py -q
uv run pytest tests/test_live_plan_view_projection.py -q
uv run pytest tests/test_live_control_server.py -q
uv run pytest tests/test_live_play_schemas.py -q
uv run pytest tests/test_live_command_bus.py tests/test_live_artifact_reads.py tests/test_live_artifact_patching.py -q
```

## Out of scope

UI upload, LLM-only parsing, embeddings/retrieval rebuild, corpus mutation, new write capabilities, multi-session UI switcher.

## Next slice

PR91 — first dogfood planning round harness (real recap + friction capture).
