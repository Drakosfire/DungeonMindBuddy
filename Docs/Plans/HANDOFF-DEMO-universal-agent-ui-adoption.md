# DEMO — shared conversational Agent UI adoption

**Status:** BLOCKED — design gates below are unresolved; no implementation write lease or runtime allocation

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md) and accepted [universal Agent turn context design](HANDOFF-DEMO-universal-agent-turn-context-v1.md). The backend baseline merged in Buddy #791; this handoff does not reopen its implementation.

**Re-anchor:** fetched Buddy `origin/main@118e680244ab830c24c0f7cfa12f636ac303e034` after Buddy #802 merged (reviewed head `1cc18982bb4e1db4bfbc13ab383761c3a8f64bb8`). The three World Plan repair PRs #800–#802 are complete. Open #798, #781, #763–#765 and #760–#761 remain active; #781 owns Agent semantic action files. This design branch makes no product edits.

## Required outcome

One ordinary conversational Agent entry is reachable on Index, Plan, Play,
Build, Ingest and Combat. Each submitted turn carries the exact current
surface instance and verified owner, with saved work, selected object and graph
lens only when their owning authority can resolve them. The UI displays the
server's actual per-turn owner/work/graph result beside the answer and keeps
bounded browser-local history without presenting prior legacy Plan turns as
continuity for the new endpoint. A route or work change must not render a late
answer as the new context. This is conversation/retrieval only; editing,
generation, graph writes and tool execution remain separate later work.

## Present code and failure cases

- `AgentInteractionChrome` renders only while an Ask plugin is registered.
  `PlanAgentInteractionBar` is the sole production registration; other React
  surfaces do not get a working shared conversation entry. The Plan plugin
  still calls legacy `/api/live/query` and requires a packet/session path.
- `POST /api/live/agent/turn` has the accepted generic wire contract. Its
  `_work_resolver` currently resolves saved `plan` only. `build`, `run` and
  `combat` work locators fail with `work_kind_unresolved`; an Ingest source or
  extraction is not a primary-work kind. A null locator returns work `absent`,
  which cannot distinguish an active but unsupported work object from true
  absence. The accepted six-surface design requires explicit unavailable
  context rather than a fabricated work claim.
- `/combat` is served as the standalone `combat.html` tracker by Vite, not the
  React `App.tsx` tree. App navigation deliberately uses a native link there.
  A React-only shared Agent host cannot reach that page. Duplicating the chat
  and authority logic in standalone script would introduce a second UI owner.
- The new endpoint is not typed or called by the current UI API module. Plan's
  browser-local history has legacy response shape, so a new response summary
  and cutover/new-thread behavior need explicit tests before use.

The highest-risk failure is a user asking from a loaded Run, Build document or
Combat encounter while the request silently sends `primary_work: null`; the
answer would appear context-aware although the backend resolved no such work.
A selected World alone also must not synthesize a campaign, Plan, graph head or
session focus. The empty graph result must remain distinct from an outage.

## Activation decisions needed from PRIME and the owning architecture lane

1. Choose the Combat composition boundary: bring the current standalone
   tracker into the React shell in its own bounded predecessor, or approve a
   specific standalone adapter that shares the accepted Agent UI/request
   contract without duplicating authority.
2. Choose the work-status sequence: extend the Buddy generic resolver/result
   with typed unsupported/unavailable work states for Play, Build, Ingest and
   Combat before six-surface UI adoption, or explicitly approve a first UI
   stage that shows “current work not linked” and sends only the verified
   surface/World while keeping full work-aware acceptance open. Do not treat
   `primary_work: null` as evidence that a selected Run or encounter is absent.
3. Pin the first serial implementation slice and exclusive expected paths
   after those choices. `App.tsx`, `AgentInteractionChrome`, the Plan Ask owner,
   API types/client, local Agent history, and surface publishers are collision
   hotspots. Reinspect #781 and other open PRs before activation. No service,
   port, database, corpus, output directory or external state is leased here.

## Candidate owning-boundary witness after activation

Use injected endpoint responses and mounted navigation/host tests to prove two
submitted turns from each supported surface, exact request fields at submit time,
fresh owner/work selection after navigation, clean new client thread when owner
or primary work changes, truthful empty/unsupported/outage display, browser
history summaries without source prose, and no stale answer on route replacement.
Exercise the actual `/combat` entry after its composition decision. A mocked
client test does not complete the connected provider/restart rehearsal or the
operator's visual acceptance.
