# Plan Surface Ladder Tracking

Version: 0.1  
Status: active implementation on main  
Workstream: Plan Surface / SurfaceConfig / Projection  
Trunk branch: `experiment/plan-surface-ladder`  
Sibling workstream: `experiment/ontology-taxonomy-ladder` (derived semantics; consume via adapter only)

## Purpose

Track the Plan Surface Toolbox ladder: an intentional `/plan` route composed from `SurfaceConfig` + `PlanSurfaceShell` (NavBar, ToolBar, EditBar, SurfaceCanvas) with one projection registry for tools and reference-chip navigation.

## Branch Contract

Root experiment branch:

`experiment/plan-surface-ladder`

Stacked PR branches:

`surface-exp/<number>-<short-name>`

## Rung Map

| Rung | Slug | Depends on |
|------|------|------------|
| R0 | ladder-scaffold | — |
| R1 | surface-shell-plan-route | R0 |
| L1 | shared-reference-resolver | R0 |
| L2 | derived-views-adapter | R0 |
| L3 | edit-capability | R0 |
| R2 | projection-registry | R1 |
| R8 | surface-theme | R1 |
| R6 | ingestion-tool-mount | R2 |
| R7 | statblock-tool-mount | R2 |
| R5 | reference-projection | R2, L1, L2, L3 |
| R9 | integration-verification | R5, R6, R7, R8 |

## Defensible Rubric (every PR)

- **Testing:** unit + seam test at owning boundary; §7 command named in handoff.
- **Security:** two-phase writer + allowlist for corpus writes; validate `refId` before path use; no secrets/PII in artifacts.
- **Simplicity:** one registry, one edit capability, one resolver, one theme; resolve kinds, don't declare enums.
- **Composability:** leaf modules usable without shell; typed contracts; allowlist-scoped diffs.

## Handoffs

See `Docs/Plans/HANDOFF-pr*-plan-surface-*.md` for agent dispatch packages.

## Verification (integration)

```bash
cd apps/live-control-ui && npm run build && npm test -- --run src/planSurface
uv run pytest tests/test_live_recap_ingest_api.py -q
```
