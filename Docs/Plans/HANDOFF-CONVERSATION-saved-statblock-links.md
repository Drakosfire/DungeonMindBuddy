# CONVERSATION: keep saved statblock links outside history authority

Status: ACTIVE. Base: `5d116c9d7304b8a91605ebfccf0969bdd77b5f63`.
Branch: `codex/statblock-history-display-metadata`.
Topology: one serial, UI-only PR from current `origin/main`; independent of open
PR #2462, whose lease is limited to native Graph reads and admission.

## Outcome

Keep validated saved statblock links visible on their originating lightweight
conversation message without copying them into the strict execution-history
envelope. The active-message reader already validates World, draft and revision
identity. `messagePresentation` currently spreads this display-only field into
the history turn, whose exact-key validator correctly rejects it.

## Invariant

Presentation metadata must not become execution, retry, evidence or action
authority. Keep the original active-message row intact for display; exclude its
`saved_statblocks` field only while constructing the verified history projection.
Keep exact history keys and all World/scope/revision checks unchanged. Do not
change server/API behavior, persisted data, statblock links, citations or actions.

## Exclusive write lease

- This handoff.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/api/conversationLibraryApi.test.ts`

No API implementation, server, schema, database, Graph, model, provider, corpus,
runtime, or other UI files. No new fallback or compatibility path.

## Verification

- Active-message contract test accepts exact saved statblock links and rejects
  foreign World, malformed draft/revision identity, and extra fields.
- Lightweight conversation test renders the saved link while the strict history
  projection remains valid and no full-history read is needed.
- Run both focused UI test files, the UI typecheck/build, inspect the cumulative
  diff, then obtain independent review of the exact PR head and required CI.
- Do not claim end-to-end statblock retrieval until an ordinary Build dogfood
  turn opens the Meat Mind revision successfully.

The predecessor lightweight-history contract is merged in #2266/#2274 and its
write lease is released. This slice preserves its separation of presentation
metadata from execution and source evidence.
