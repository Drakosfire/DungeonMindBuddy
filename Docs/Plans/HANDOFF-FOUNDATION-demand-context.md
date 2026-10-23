# FOUNDATION — demand-mounted conversation context

ACTIVE serial PRIME slice, base 5fed2e70378b12897dae7974ba34e798c6c64f66,
branch codex/demand-mount-conversation-context, reused buddy-context-loop checkout.
One independently Bugbot-reviewed PR, PRIME merge and protected UI delivery on5202.
Current fetched open-PR census contains no overlapping shared dock implementation.
Existing older dock handoffs describe merged historical work, not concurrent lanes.

The ordinary collapsed Plan mounts1141 DOM elements,636 in its hidden conversation,
452 in unopened context. This is a DOM footprint proxy, not browser heap or8GB
hardware acceptance. The context includes the graph explorer and its hidden list.

Defer the shared context slot until first explicit opening. Keep it mounted after
that so graph selection, query, context settings and portal host identity survive
hide/show and conversation collapse. Reader, messages, composer and their controller
stay mounted throughout; no draft, request, focus, history or Graph authority changes.
This applies to every ConversationDock consumer, including Plan/Build portal hosts
and Play direct slots. No provider calls or new API/persistent contract.

Critique: conditional unmount on every close loses local context state; a deferred
portal host must appear when opened and remain stable afterward. Existing hidden
content must become visible normally on demand. Newly supplied context remains
current even after hiding. Removing context may remove its host as today.

Exclusive writes: this handoff; apps/live-control-ui/src/ui/ConversationDock.tsx
and ConversationDock.test.tsx; planSurface/components/PlanConversationDockAdapter.test.tsx
under the same src root; predecessor settlement in
Docs/Plans/HANDOFF-AGENT-candidate-acquisition-guidance.md and
Docs/Roadmaps/ROADMAP-demo.md. No dependencies, prompts, database, source or service
changes. Private logs/build outputs stay ignored under .pytest_cache.

Verify delayed child effects, retained input/portal identity and current context
updates, shared direct and portal-host tests, UI build and ordinary rendered
Plan/Play opening/closing/draft retention. Measure DOM before/after first context
open. Baseline19pass/4fail: adapter assertions still name old240/360 heights,
What Buddy sees and Saved World Plan conversation. Update those four expectations
to current280/420, Show context and World conversation without removing assertions.
Review exact cumulative diff before merge; preserve APP/native/mechanics/frozen
records at rollout. Original private Jev/fal checks remain consent-held.
