# HANDOFF pr1 — Plan Surface R0 scaffold

**Status:** ready for agent dispatch  
**Trunk:** `experiment/plan-surface-ladder`  
**Rung:** R0 ladder-scaffold

## §1 Mission

Create ladder tracking doc and baseline branch naming; no product UI changes beyond what lands in the integrated implementation PR on main.

## §4 Allowlist

| Path | Action |
|------|--------|
| `Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md` | create/update |
| `Docs/Plans/HANDOFF-pr*-plan-surface-*.md` | create |

## §7 Verification

```bash
test -f Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md
```

## §9 Rubric

- **Testing:** tracking doc exists; smoke path documented.
- **Security:** docs only; no corpus writes.
- **Simplicity:** single tracking anchor; no duplicate plan docs.
- **Composability:** handoffs reference rung dependency graph from plan.
