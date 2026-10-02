# DEMO — saved managed-World Plan Agent conversation

**Status:** MERGED — Buddy #805, reviewed head `0dc016d93f81212f7ee32ea2c137b7cbb2577c5b`, merge `f23d43d714b7aba68d940bbcb4cceb027f3c63e1`

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), accepted [universal Agent turn contract](HANDOFF-DEMO-universal-agent-turn-context-v1.md) §3–§4, Buddy #804 merge `7a4159f447da715a2a5d586b862a7079b7316929`, and PRIME's explicit implementation dispatch after exact-head PRIME/ARCHITECTURE PASS.

**Pinned base:** `origin/main` at Buddy #804 merge `7a4159f447da715a2a5d586b862a7079b7316929`, fetched before implementation.

**Branch/checkout:** `codex/demo-plan-agent-conversation` in `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy`.

**Topology:** serial. Index #803 and design #804 are merged; no other DEMO Agent adoption lane is active. Re-anchored and inspected open PRs #798, #781, #760–#761, and #763–#765. Their exact changed paths do not overlap this lease. #764 touches Rules Lawyer / Plan projection catalog files and `planSurface/config/planSurfaceConfig.ts`; those remain outside this lease and read-only. No shared write-path or runtime-state collision was found.

## One capability and failure cases

On a saved Plan owned by the independently verified managed World, a user can
open the existing app Agent chrome and have a multi-turn conversation
associated with that Plan through `POST /api/live/agent/turn`. Each turn sends
the exact leased Plan surface instance, World owner, saved Plan document ID,
expected document revision, and `graph_request: {mode:"none"}` with no graph
selection. The request contains no local Markdown, title, path, fake document
ID, or browser thread scope. A saved dirty editor is reported as
`saved_dirty`; a clean one is `saved_clean`.

This is metadata-scoped conversation beside a saved Plan. The accepted
`graph:none` path gives the Agent the user's question, conversation continuity,
and resolved Plan metadata such as title and revision; it does not read or
provide the committed Plan Markdown/prose. It cannot answer from, quote,
retrieve, or revise the Plan's saved prose. The UI must say that the Agent
does not read the Plan text and must not imply document QA, grounding, citation,
retrieval, or editing. Sending browser-local editor content is not a workaround.
A future content-aware Plan Agent needs a separate owner-reviewed server-side
committed-content access contract with explicit privacy and revision behavior.

The transcript uses a browser-local namespace isolated by the independently
verified World and exact saved Plan document ID. It does not adopt a legacy
campaign Plan thread or provider pointer. The local namespace token is storage
metadata only; it is never serialized as owner or work authority.

The current `PlanAgentInteractionBar` remains the owner of existing campaign
Plan retrieval/citation and reviewed document-edit proposal behavior. This
slice does not route those flows through the new endpoint and does not alter
that component. The generic turn is available only for a saved managed-World
Plan. The accepted generic response has no typed citations or grounding
envelope and reports `graph_grounded: false`, so this conversation makes no
graph request and displays no retrieval or citation claim. Campaign-target
Plans remain unsupported by this new turn path pending campaign-to-World
authority. A World Plan local draft has no durable work ID or revision and
cannot submit a generic Plan turn; show that the user must save first. Never
put a `local-plan:*` token on the wire. A later content-aware or unified cited
conversation requires a separate Buddy contract proposal.

Pre-dispatch critique: the easiest false success is answering from a selected
World while omitting the exact Plan or using a stale document revision. The
highest identity risk is treating a local draft as a saved Plan or carrying a
late answer across a Plan/World/revision/thread/route change. Fail closed for
foreign, removed, unavailable, malformed, or mismatched saved work. The
accepted contract treats
`expected_revision` as a freshness expectation, not a historical content pin:
if the same Plan is still authorized at a newer committed revision, the
backend may answer from that actual revision and reports
`changed_since_expected`, expected revision, and used revision. The UI must
show that distinction with the actual revision and must never imply that the
answer used the older revision. Graph is not requested in this slice, so
graph-unavailable and graph-pin behavior are outside this implementation.

## Implementation path lease (released at merge)

These paths formed the exclusive write lease during implementation, activated
by PRIME's explicit dispatch on Buddy #804 merge
`7a4159f447da715a2a5d586b862a7079b7316929`. The lease was bounded to one
saved managed-World Plan conversation and ended when Buddy #805 merged at
`f23d43d714b7aba68d940bbcb4cceb027f3c63e1`.

- `Docs/Plans/HANDOFF-DEMO-plan-agent-conversation.md` — this bounded proposed
  proposal and its acceptance witness.
- `Docs/Plans/HANDOFF-DEMO-index-agent-conversation.md` — backward-looking
  #803 merge settlement only.
- `Docs/Roadmaps/ROADMAP-demo.md` — #803 settlement and this slice's bounded
  execution facts.
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — expose the
  current saved revision/dirty hint to the World Plan Agent plugin; mount it
  only on the managed-World Plan path.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
  — new Plan Ask plugin, exact request capture, response validation, transcript,
  thread persistence, visible metadata-only capability notice, and
  stale-response fencing.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
  — content placement inside the existing shared Ask portal.
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` — mounted
  World Plan / Agent chrome / endpoint witness.
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
  and `agentInteractionHistory.test.ts` — bounded safe Plan turn-result
  summary persistence and reload.
- `apps/live-control-ui/src/api/types.ts` — typed Plan request/response and
  source-free resolved summary.
- `apps/live-control-ui/src/api/liveApi.ts` and `liveApi.test.ts` — typed
  `/api/live/agent/turn` client and transport behavior.

The existing `PlanAgentInteractionBar.tsx` and its tests were outside the
implementation write set. So were
`AgentInteractionProvider.tsx`, `AgentInteractionChrome.tsx`, `AskPluginSlot.tsx`,
`surfaceInteraction/**`, App/root provider composition, all other surface
owners, `planSurface/config/planSurfaceConfig.ts`, backend routes/resolvers,
schemas, providers, dependencies, lockfiles, and root configuration. If the
capability needs any path outside this list, stop and return the exact blocker
to PRIME before editing it. No server, provider, port, database, corpus,
production data, or `.env` is leased.

## Owning-boundary acceptance witness

Mount the real `PlanSurfacePage` World-owned Plan path with the real selected-
World authority, Agent provider, Ask portal, and shared Agent chrome; mock the
endpoint and existing Plan snapshot/write APIs. Prove:

1. A loaded saved World Plan opens Ask and submits two turns through the
   accepted endpoint with one stable client thread ID, distinct turn IDs, exact
   `surface_id="plan"`, current leased instance, World ID, saved document ID,
   and expected revision. The graph request is explicitly `none` with no
   selection. A persistent, user-visible capability notice says the Agent
   receives Plan metadata but does not read the Plan text; no document QA,
   retrieval, grounding, citation, quotation, or editing capability is implied.
   The UI makes no retrieval or citation claim.
2. The actual answer and bounded per-turn resolved owner/work facts, including
   the revision actually used and whitelisted conversation `pointer_status`,
   are visible and survive thread reload. Do not persist provider identity,
   pointer ID, trace, source prose, local Markdown, storage token, or path in
   the new summary or wire request. Switching to another saved Plan and
   returning/reloading must not cross transcripts.
3. Clean/dirty saved state is reported accurately. A local unsaved draft has
   no enabled generic Ask and causes no endpoint call or fabricated document
   ID. While a save/commit is in flight, Ask is disabled and a request never
   uses a prepared-but-uncommitted revision; after commit, it uses the last
   confirmed committed revision. Campaign-target Plan requests are not sent
   through this new path.
4. Unavailable, foreign, removed, or mismatched work produces a visible error
   without rendering an answer. Runtime-validate the response against the
   declared response schema before display or persistence; TypeScript types
   alone are insufficient. Require the schema discriminator; matching
   top-level and nested client thread/turn IDs; exact Plan surface ID and
   instance echo with `surface.status="resolved"`; resolved owner kind/ID
   matching the requested World; Plan work kind and exact saved document ID;
   echoed expected revision; matching
   `client_work_state_reported`; and a valid used revision. Require
   `resolved` exactly when the used revision equals the expected revision and
   `changed_since_expected` when it differs. Require graph status
   `not_requested` with no scope or selection, and `answer.status="ok"`,
   nonblank text, and `graph_grounded=false` before accepting an answer.
   Missing, malformed, contradictory, or mismatched fields produce a visible
   protocol error and write neither the turn nor its summary. A valid
   `changed_since_expected` result may render only with a visible status naming
   both expected and actually used revisions.
5. Pending responses are suppressed after World, Plan document, expected
   revision, route, or thread replacement/unmount. Include the expected
   revision in the pending-request fence and recheck before appending or
   persisting. Switching Plans and returning/reloading restores only that
   World/document transcript. Negative mounted witnesses mutate Plan ID,
   revision, thread/turn IDs, surface instance/status—including `rejected`
   and `unavailable` paired with an otherwise valid answer—graph state,
   grounding flag, and answer shape and prove none is displayed or persisted;
   existing campaign Plan Ask/citation and reviewed document-edit proposal
   regressions still pass.

Run the focused World Plan and legacy Plan Agent tests, relevant API/history
tests, UI typecheck, and cumulative base-to-head diff review. Name inherited
failures. Mocked UI tests do not certify a live provider, campaign authority,
the other four surfaces, or full DEMO acceptance.

**Implementation authorization and settlement:** PRIME merged this design in
Buddy #804 at `7a4159f447da715a2a5d586b862a7079b7316929` after exact-head
PRIME and ARCHITECTURE PASS, then explicitly dispatched this bounded
implementation. Buddy #805 delivered the capability and merged at
`f23d43d714b7aba68d940bbcb4cceb027f3c63e1` from reviewed head
`0dc016d93f81212f7ee32ea2c137b7cbb2577c5b`. PRIME independently reviewed the
exact cumulative diff and owning-boundary evidence. The write lease is
released. This implementation does not claim full DEMO acceptance.

## Implementation verification record

Implementation is on `codex/demo-plan-agent-conversation`, based on fetched
`origin/main` at `7a4159f447da715a2a5d586b862a7079b7316929` (Buddy #804).
The current focused run passes all 147 tests: `PlanSurfacePage.test.tsx` 35,
`agentInteractionHistory.test.ts` 32, and `liveApi.test.ts` 80. The mounted
reviewed Plan edit regression passes (1/1); previously selected Plan shell
regressions passed (3/3). These are mocked UI/API checks, not a live provider or
runtime witness.

The UI typecheck remains blocked by the existing error
`src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): TS2503: Cannot
find namespace 'JSX'`; no typecheck error pointed to this slice. The
out-of-lease `PlanAgentInteractionBar.test.tsx` run is 3/8 passing and 5 failing
because each failure cannot find the existing `Capture Plan target` button;
this slice did not edit that component or test, and those paths are outside its
write lease. No edits were made to address that separate failure.

`git diff --check` passed. No live provider, server, port, database, corpus,
runtime state, or product generation was used or changed. The existing
`PlanAgentInteractionBar.test.tsx` fixture failures and inherited UI typecheck
error remain separate from #805. PRIME completed independent review and merge
control; broader DEMO acceptance remains open.

**Subsequent fixture settlement — Buddy #858:** RAKE reproduced the retired
`getWorkspaceDocument` fixture in five of nine mounted cases because current
`SelectedWorldContext` resolves through `getWorkspaceDocumentAny`. PRIME merged
the one-file test-only correction at main
`13dbf3a42b0b040a482c0ced1ec0fe5d7b314c37` from reviewed head
`6d1effa5665dd644c343e0d8627b295a18bd23f3`; the focused suite now passes 9/9.
This resolves the inherited fixture failures without changing Plan product
behavior or reopening #805's implementation lease. The typecheck failure and
broader DEMO acceptance remain as recorded above.
