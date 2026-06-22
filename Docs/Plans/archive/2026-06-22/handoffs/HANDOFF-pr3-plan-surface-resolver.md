# HANDOFF pr3 — Shared reference resolver (L1)

**Rung:** L1 shared-reference-resolver  
**Depends on:** R0

## §1 Mission

Extract `referenceResolver.ts` shared by React plan surface; resolve kind from live indexes; validate opaque locators.

## §4 Allowlist

| Path | Action |
|------|--------|
| `apps/live-control-ui/src/planSurface/reference/**` | create |

## §7 Verification

```bash
cd apps/live-control-ui && npm test -- --run src/planSurface/reference/referenceResolver.test.ts
```

## §9 Rubric

- **Testing:** resolver matches prep.js normalization and index matching behavior.
- **Security:** rejects invalid locators; no path traversal in refId.
- **Simplicity:** no surface-owned category enum.
- **Composability:** usable without PlanSurfaceShell.
