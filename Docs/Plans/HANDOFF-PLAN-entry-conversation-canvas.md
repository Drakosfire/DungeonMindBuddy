# PLAN: usable blank Plan workspace

ACTIVE under explicit operator request; PRIME owns this serial small slice.
Base e0200edb23edbbba173ee5789b1090f01b5718af; branch codex/plan-entry-conversation-canvas.
Reuse buddy-context-loop and its dependencies. No new worktree, environment or provider calls.
Statblock exact-association branch is clean and deferred while this dogfood blocker ships.

Outcome: document workspaces expose their conversation launcher independently of whether
saved-object execution is ready, and the Plan canvas fills the workspace whenever
Contents navigation is absent. Conversation eligibility, save requirements, scope checks,
transport and mutation authorization stay with their existing owners. Chrome owns the
launcher, not a second fallback or duplicated conversation. Grid tracks follow rendered
Contents rather than assuming that every Plan has a saved navigation deck.

Writes: this handoff; agentInteraction/AgentInteractionChrome.tsx and .test.tsx;
planSurface/components/PlanCardDeck.css. No Plan persistence, statblocks, native Graph,
API, schema, routing or retrieval changes. Source paths are beneath apps/live-control-ui/src.
Verify launcher open/close with absent and changing plugin readiness, no launcher in
unowned chrome without a plugin; existing component checks; production build; real
browser blank/saved Plan, navigation layout at desktop/narrow sizes, unsaved draft and
scroll preservation while opening/closing the dock, and fresh reload. No model calls or
saved-document writes. Independent exact source/integration/transport review and CI,
merge then protected UI-only delivery conserving API, sources and drafts.
