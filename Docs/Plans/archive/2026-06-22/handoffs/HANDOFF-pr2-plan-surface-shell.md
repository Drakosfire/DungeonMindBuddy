# HANDOFF pr2 — Plan Surface R1 shell + route

**Rung:** R1 surface-shell-plan-route  
**Depends on:** R0

## §1 Mission

Ship `SurfaceConfig`, `PlanSurfaceShell`, `/plan` route, and `PlanNavBar` with plan context from `getPlanView()`.

## §4 Allowlist

| Path | Action |
|------|--------|
| `apps/live-control-ui/src/planSurface/**` | create |
| `apps/live-control-ui/src/App.tsx` | modify |
| `apps/live-control-ui/src/chrome/appChromeConfig.ts` | modify |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | create |

## §7 Verification

```bash
cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
```

## §9 Rubric

- **Testing:** shell renders four regions; context header from plan view.
- **Security:** no corpus writes; plan context from API not env-only.
- **Simplicity:** SurfaceConfig only fields `/plan` needs today.
- **Composability:** shell surface-agnostic; config injected.
