# HANDOFF — DEMO Plan Agent trace receipts

- **Status:** ACTIVE — PRIME-authorized implementation slice
- **Base:** Buddy `main@3494b8f4561b2ec465af42bf4fb55bac3f42ee3c`
- **Branch:** `codex/demo-plan-trace-receipts`
- **Topology:** parallel-independent from C1 PR #810, Alembic PR #811, and RAKE's Hermes worker-home repair; one PR to Buddy `main`
- **Owner:** DEMO

## User-visible gap

The saved World Plan conversation validates the generic Agent response but drops
`answer.trace` while constructing its local interaction turn. The backend may
already return provider request IDs, usage, and cost, but those receipts are not
available after the user reloads the saved conversation.

## Bounded change

Carry the validated trace into the saved turn only through the existing
`safeTraceForPersistence` projection. Keep the currently accepted answer text,
metadata-only Plan behavior, request contract, stale-response fencing, provider
routing, and graph mode unchanged. Persist only bounded allow-listed trace
fields; never persist prompt, message, request body, or other raw content.

## Exclusive write lease

```text
Docs/Plans/HANDOFF-DEMO-plan-agent-trace-receipts.md
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts
```

The last two paths are available if the existing safe projection needs a scoped
correction; do not broaden the sanitizer beyond receipt fields needed by this
slice. Stop if another path or contract is required.

## Collision check

- Buddy #810 is CLEAN at `a20e14518ebdb24a5e1790c2486dfad8758c7920`; its current
  file list does not contain any leased UI paths.
- Buddy #811 is CLEAN at `ae1e3aaff746aee8ad630ffa58f7e22d79d3997e`; it owns the
  Alembic environment and migration logger regression, with no leased UI paths.
- The Hermes worker-home lifetime repair and its fake-model test use backend
  service paths, separate from this UI lease.

No shared route, schema, migration, dependency, provider, database, or runtime
state is in scope.

## Acceptance witness

1. A mounted fake-response Plan test proves available request ID, usage, and
   cost survive a saved-thread reload while a prompt-secret sentinel is absent.
2. Existing Plan response validation and stale-response fencing remain intact;
   the answer continues to state that Plan prose is not read.
3. Run focused Plan and interaction-history tests, UI typecheck, and
   `git diff --check`. Make no live provider or database calls.
4. Review the exact cumulative base-to-head diff, commit the leased change, push
   the assigned branch, and open one PR to Buddy `main`. PRIME owns review and
   merge.

## Verification record

- Focused Plan and interaction-history suites: **68 passed** (36 Plan, 32
  history) on a serial rerun.
- One initial run concurrent with typecheck failed the existing blank-Plan
  surface-context test; that test passed alone on the unchanged checkout, and
  the serial focused rerun passed all 68 tests. The timing cause was not proven.
- UI typecheck remains blocked by the existing error
  `src/statblocks/publication/ThreatPublicationPanel.tsx:553:77: Cannot find
  namespace 'JSX'`. The same error reproduced on the unchanged Buddy checkout;
  this slice introduces no reported type errors.
- `git diff --check` passed. No provider or database calls were made.
