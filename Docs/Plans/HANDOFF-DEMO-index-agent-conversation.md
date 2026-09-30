# DEMO — Index conversational Agent entry

**Status:** ACTIVE — PRIME reviewed and activated design head `09430129e652fee4f8b507383488f6822dcffaed`

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), accepted [universal Agent turn context design](HANDOFF-DEMO-universal-agent-turn-context-v1.md) §3 and merged backend #791. PRIME selected Index as the first serial six-surface adoption bite; the umbrella gap analysis `Docs/Plans/HANDOFF-DEMO-universal-agent-ui-adoption.md` at `5da0ae287a94d025f1fa528e2a5924305640fc95` remains read-only reference.

**Pinned predecessor/base:** Buddy #802 reviewed head `1cc18982bb4e1db4bfbc13ab383761c3a8f64bb8`, merged as `118e680244ab830c24c0f7cfa12f636ac303e034`; fetched `origin/main` at that exact merge.

**Proposed branch/checkout:** `codex/demo-index-agent-design` in `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy` for design. After activation, reuse this isolated branch for one implementation PR.

**Topology:** serial. No parallel DEMO Agent implementation lane is active. Open #781 owns semantic action projection files and does not touch the proposed write set; #798, #763–#765 and #760–#761 were also refreshed. Recheck exact PR paths before activation and PR creation.

## One capability and failure cases

From Index, a user can open the existing app Agent chrome and hold a normal
multi-turn conversation through `POST /api/live/agent/turn`. The turn uses the
lease-guarded Index surface identity at submission, a verified managed World
owner when selected, `primary_work: null` and `client_work_state: "none"` by
the accepted Index contract, and `graph_request: {mode: "none"}`. No campaign,
Plan, document, session, graph scope, selection or citation is inferred from
the World or route. An Index without selected World remains a valid no-owner
conversation. Show the actual answer and a compact per-turn resolved summary
of surface, owner, absent work, graph not requested and provider continuation;
errors stay visible and preserve the unsent question for retry.

Reuse the existing app `AgentInteractionChrome` / Ask portal rather than adding
a second launcher. Register the Index Ask owner only while the Index route is
mounted. Use the existing browser-local Agent thread store under an explicitly
local namespace derived from verified owner or no-owner state; its historical
`campaignId` storage key is **not** a campaign assertion and must never enter
the wire request. Do not adopt a legacy Plan thread or provider pointer. Two
turns in one unchanged Index owner/work context reuse the client thread ID;
World replacement, route replacement, new thread and unmount fence pending
answers before they can be shown or persisted under a different context. The
response's canonical owner and status, rather than request hints, are saved
as a bounded safe summary with the turn. Keep transcript storage browser-local
and strip trace/source payloads through the existing sanitizer.

Pre-dispatch critique: the easiest false success is rendering an Agent launcher
without submitting a real second turn to the accepted endpoint. The highest
identity risk is an in-flight World A answer appearing under World B, or a
local storage namespace token being serialized as campaign/World authority.
The mounted witness below must exercise both. A server rejection cannot be
converted into an ungrounded answer. A no-graph result must not display a
retrieval/citation claim. `AgentInteractionChrome` remains hidden on routes
without a registered Ask owner.

## Proposed exclusive expected write lease (§4 after activation)

- `apps/live-control-ui/src/App.tsx` — mount the Index Ask owner beside the
  existing Index publication; do not alter other route owners.
- `apps/live-control-ui/src/api/types.ts` — type only the accepted generic
  Agent turn request/response and bounded per-turn resolved summary.
- `apps/live-control-ui/src/api/liveApi.ts` — typed `/api/live/agent/turn` client.
- `apps/live-control-ui/src/api/liveApi.test.ts` — exact path/payload/error
  transport witness.
- `apps/live-control-ui/src/agentInteraction/IndexAgentConversation.tsx` —
  Index Ask portal, transcript, request capture and stale-response fencing.
- `apps/live-control-ui/src/agentInteraction/IndexAgentConversation.css` —
  Index Ask content placement inside the established chrome only.
- `apps/live-control-ui/src/agentInteraction/IndexAgentConversation.test.tsx` —
  mounted real app chrome/portal and two-turn endpoint witness with mocked API.
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
  and `agentInteractionHistory.test.ts` — bounded safe result-summary persistence
  and reload, without source prose.
- `apps/live-control-ui/src/App.test.tsx` — Index route adoption and absence on
  non-Index routes, if the mounted Index witness does not already prove both.
- `Docs/Plans/HANDOFF-DEMO-index-agent-conversation.md` — active authority and
  exact evidence after activation.
- `Docs/Plans/HANDOFF-DEMO-world-plan-edithost.md` and
  `Docs/Roadmaps/ROADMAP-demo.md` — backward-looking Buddy #802 settlement and
  current Index execution facts in the implementation PR.

No `AgentInteractionProvider`, `AgentInteractionChrome`, shared surface host,
server route/resolver, Plan Ask owner, other surface page, Combat tracker,
dependency, lockfile or root configuration edit is leased. If Index requires
one of those paths, stop and return to PRIME for a bounded lease amendment.
No server, port, database, corpus, output directory or external state is
leased. The production endpoint is consumed via mocked API at the UI boundary;
no paid provider call is a merge gate.

## Owning-boundary verification and activation

Mount Index with the real `SelectedWorldProvider`, `AgentInteractionProvider`,
`AskPluginSlotProvider`, `AgentInteractionChrome` and neutral Index publication.
Prove opening the existing launcher, two sequential submitted turns to the
typed endpoint, one stable client thread ID with distinct turn IDs, transcript
and per-turn resolved summaries visible and persisted/reloaded, no owner and
verified managed-World request variants, no fabricated work/graph/campaign,
an exact request captured when the user submits, and stale responses dropped
after World/route/thread replacement and unmount. Assert API failures show
actionable error without fabricating an answer. Retain existing App/Agent chrome
and history regressions, run UI typecheck, and review the exact cumulative
base-to-head diff. Any inherited failures must be named. This mocked boundary
does not certify a live provider or the complete six-surface DEMO journey.

**Activation gate:** PRIME critiqued the pinned design head, confirmed the
exclusive write set and authorized ACTIVE implementation. Deliver one bounded
PR titled `DEMO: add Index Agent conversation` and return
its exact head, verification and remaining gates to PRIME for merge control.

## Author verification

The mounted real-provider and chrome witness passed 7/7 Index tests. It covers
two submitted turns with one client thread ID, verified World and no-owner
requests, unverified World lookup suppression, bounded transcript reload,
World and route replacement, new thread,
unmount, API error retry and mismatched-response rejection. API transport and
history sanitizer suites passed 79/79 and 30/30; Agent chrome passed 3/3 and
the real App root-route Index mount passed. The full App suite has 21 failures
in unrelated Plan, Build and Play fixtures that reach unmocked workspace/Run
URLs and show `World selection unavailable`; 11 tests pass. UI typecheck
reports the inherited `ThreatPublicationPanel.tsx:553` JSX namespace error.
No provider, server, port, database or corpus was used. The remaining five
surface adoptions, connected provider witness and operator acceptance stay
open.
