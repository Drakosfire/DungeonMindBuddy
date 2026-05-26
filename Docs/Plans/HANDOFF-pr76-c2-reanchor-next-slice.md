# HANDOFF — PR 76: C2 Live Control Surface Re-anchor / Next Slice

**Created:** 2026-05-25 (UTC).  
**Status:** PLACEHOLDER — use this branch for the next re-anchor before dispatching implementation work.  
**Base:** `main` after PR #75 merge (`af27c47`) — L3-min FastAPI query loop landed, but full Phase L3 is not complete.

---

## Purpose

This branch exists as a fresh PR/code branch for the next C2 Live Control Surface step. It intentionally does not pre-decide the implementation slice.

Before writing implementation code, re-anchor against:

1. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md`
2. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md`
3. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr75-c2-l3-fastapi-query-loop-min.md`
4. `apps/live_control_server/**`
5. `tests/test_live_control_server.py`
6. `Docs/Plans/README-c2-live-control-ui.md`

## Current Known State

- L1 live substrate is merged.
- L2 roll resolver/classifier/live-turn handler is merged.
- L3-min FastAPI query loop is merged.
- Full Phase L3 is still open unless the plan/checklist is intentionally split.
- L4 React UI is not started.

## Likely Next Choices

Choose one after re-anchor:

1. **L3-rest:** surface endpoints, layout persistence, job completion, resolve-roll wrapper, rebuild-packet stub, OpenAPI path tests.
2. **Doc-sync split:** update PLAN/CHECKLIST to explicitly split L3-min from L3-rest.
3. **L4 prep handoff:** only if the team intentionally accepts L3-min as enough server spine for the first UI pass.

## Guardrails

- Do not mark full L3 complete merely because PR #75 merged.
- Do not start React UI unless the plan explicitly says L3-min is enough for L4 start.
- Do not write corpus files from live-play endpoints.
- Do not mutate committed Session 22 seed JSONL files in tests.
- Preserve the L2 contract: `handle_live_turn` returns events/jobs; server appends them.
