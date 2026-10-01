# HANDOFF — DEMO: route the saved Plan Agent through Hermes Responses mode

**Status:** IMPLEMENTATION MERGED — Buddy #812 complete;
separately leased two-turn live witness pending

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), merged
saved managed-World Plan Agent contract in
[HANDOFF-DEMO-plan-agent-conversation.md](HANDOFF-DEMO-plan-agent-conversation.md),
ARCHITECTURE’s same-model transport ruling, RAKE DUTY’s read-only retry and
telemetry triage, and PRIME’s explicit activation.

**Implementation base (historical):** Buddy
`main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a`, verified from
the GitHub `main` ref on 2026-09-30. The local fetch metadata is read-only in
the calling checkout; the isolated worktree started at the verified commit.

**Implementation branch / checkout (historical):**
`codex/demo-plan-agent-responses-mode` in the isolated
worktree `/home/drakosfire/.codex/worktrees/demo-plan-agent-responses-mode/DungeonMindBuddy`.

**Topology:** The implementation was authorized as one parallel-independent
PR; Buddy #812 is now merged. Concurrent PRs #810 and #811 also completed and
their paths did not overlap the Hermes adapter. The implementation/tests used no
database, service, port, corpus, or provider. The post-merge Plan witness has a
separate PRIME runtime lease recorded below.

## One capability and observed failure

Route Buddy’s existing OpenAI-backed Hermes Agent invocation through the mode
the pinned Hermes runtime selects for the existing provider, model, and base
URL. This should unblock the accepted saved managed-World Plan conversation;
it does not add a surface, alter Agent behavior, or create a provider contract.

The exact synthetic Plan witness used the accepted Plan flow with
`surface_id="plan"`, a saved clean document at revision 3, and
`graph_request={"mode":"none"}`. Existing policy selected
`("openai-api", "gpt-5.3-codex", "https://api.openai.com/v1")`. Buddy’s Hermes
adapter nevertheless forced `api_mode="chat_completions"`. The ordinary UI
turn received HTTP 404 directing use of `/v1/responses`; three HTTP attempts
were logged. Request IDs, usage, and billable cost are unavailable, not zero.
No second turn was sent, and no graph request was made.

GPT-5.3-Codex documentation lists more than one API endpoint generally. This
change is scoped to the observed Buddy invocation and uses the pinned Hermes
selection contract; it does not claim that every account or project rejects
Chat Completions.

## Invariants and failure cases

- PR #812 changes no model policy, provider, URL, key resolution, prompts, turn
  history, graph-none policy, Plan identity, response mapping, or UI/session
  semantics. Its offline adapter/selector proof used the then-configured
  `openai-api`, `gpt-5.3-codex`, and `https://api.openai.com/v1` inputs; the
  post-merge witness uses current policy-selected model settings.
- Omit Buddy’s forced `api_mode` argument so the exact pinned Hermes runtime
  can resolve `codex_responses` from the existing provider/model/base inputs.
- If exact-pin offline verification does not resolve to `codex_responses`, stop
  and return the evidence to PRIME. Do not add an explicit alternate transport,
  Chat fallback, model substitution, retry-policy change, second client, or
  GenerationEngine migration.
- If the post-merge Responses witness fails, stop on the first provider error
  and return the exact evidence to PRIME/ARCHITECTURE. Do not switch models or
  retry speculatively.
- Plan conversation remains metadata-only: no saved Plan prose is sent or
  retrieved, no graph selection is made, and no document QA/citation/editing
  claim is introduced.

## Exclusive write lease

Only these paths may change in this slice:

1. `Docs/Plans/HANDOFF-DEMO-plan-agent-responses-mode.md` — this bounded
   authority, evidence, and review handback.
2. `apps/live_control_server/services/hermes_graph_agent.py` — remove the
   forced transport mode at Buddy’s Hermes invocation.
3. `tests/test_hermes_graph_agent.py` — prove the adapter omits the override
   and the exact installed Hermes pin selects Responses for the existing
   configured model/provider/base.

No other path is leased. In particular, `agent_graph_policy.py`,
`MODEL_POLICY.json`, generic Agent routes, UI, schemas, migrations, retry
settings, dependency pins, lockfiles, and the Hermes package are read-only. If
the behavior or test requires another path, stop and return the exact blocker
to PRIME before editing it.

## Exact runtime contract

Buddy main pins Hermes 0.18.2 at
`861d69c7bba8d2ea6a1cd170e989c901c74d32d1` and `openai==2.24.0`. At these pins,
Hermes upgrades its default Chat Completions mode to `codex_responses` when no
mode was explicitly supplied and the existing direct OpenAI URL/model rules
match. An explicit mode suppresses that selection, which is why Buddy’s
current override is ineffective. No dependency bump is authorized.

ARCHITECTURE owns the cross-owner transport ruling; Buddy owns this adapter
integration. RAKE DUTY found that Hermes’ configured API request maximum is
three attempts and the OpenAI SDK retries are disabled. The failed-call trace
can expose the mode, status, retry information, model, and error type; failed
calls do not provide usage or estimated cost. The observed 404’s three logged
attempts therefore remain part of the recorded failure, and spend remains
unknown.

## Owning-boundary verification

Use the exact pinned environment and prove all of the following offline:

1. Buddy’s adapter passes the unchanged `openai-api` provider, configured
   `gpt-5.3-codex` model, and exact OpenAI base URL but does not pass an explicit
   `api_mode` override.
2. Construct the pinned Hermes agent without a conversation or network request
   under the same provider/model/base inputs and assert its resolved mode is
   exactly `codex_responses`.
3. Keep the graph-none turn/history/output and model-call usage mapping
   regressions passing. Prove there is no hidden Chat call, fallback, or new
   retry behavior. Do not weaken existing capability, identity, privacy, or
   turn-trace assertions.

Run the focused Hermes graph-agent tests, relevant Agent turn/trace tests, and
`git diff --check`. Review the exact cumulative `a8b0d5c2..HEAD` diff and all
leased paths. Report inherited failures without broadening this slice.

## Post-merge live witness — assigned isolated runtime

**Status at 2026-10-01:** assigned and pending; the API/UI services have not
started and the empty databases have not been migrated or bootstrapped.

PRIME assigned this fresh disposable, localhost-only pair exclusively to DEMO
for this witness:

- Buddy application-state PostgreSQL: container
  `prime-demo-agent-buddy-pg-20261001`, `127.0.0.1:55457`, database
  `dungeonbuddy_application_state`.
- DungeonMind World graph PostgreSQL: container
  `prime-demo-agent-mind-pg-20261001`, `127.0.0.1:55458`, database
  `dungeonmind`.
- Buddy API: `127.0.0.1:7866`; UI: `127.0.0.1:5178`.

Both databases are empty and require explicit owner migrations/bootstrap. Before
using them, verify the API resolves both configured database URLs to these
assigned endpoints. Keep this witness isolated from persistent ports
`54330/54331` and existing Plan services `7865/5177`. Start/stop only the
API/UI processes on the assigned ports. Database access was delivered through
an operator-approved mode-0600 local credential file; do not print, log, commit,
or copy its values into this handoff, and remove the temporary file after the
witness.

Use current Buddy policy from the merged #819 model-policy change:
`hermes_graph_agent` selects `gpt-6-luna`. Do not force the historical
`gpt-5.3-codex` model. Record the model and actual transport resolved by the
live request; the #812 offline selector test used its historical
`gpt-5.3-codex` input and does not establish the live Luna transport. Because
this handoff proves the Responses-mode repair, a PASS requires actual transport
`codex_responses`. If policy-selected Luna resolves otherwise or the transport
cannot be identified, stop and report exact evidence to PRIME. Do not override
the model or transport to make the witness pass.

Create one synthetic managed World and saved Plan through the ordinary UI. Run
two consecutive ordinary Plan UI turns on that same World/Plan with
`graph_request={"mode":"none"}`. Record the World/Plan, client-thread and turn
IDs, provider request IDs where available, actual model/transport/base,
conversation continuity, usage/cost when returned, saved editor state after
reload, and evidence that no graph request occurred. Stop on the first provider
error, six total OpenAI HTTP attempts, or the previously authorized additional
spend cap of $0.50. Unknown usage/cost stays unknown, not zero. A successful
single turn does not prove continuity. If an assigned prerequisite fails,
return its exact failure to PRIME without switching targets.

This is bounded post-merge transport/conversation evidence. It does not establish
J1/J2, the complete connected DEMO, or operator acceptance.

## Implementation verification record

On `codex/demo-plan-agent-responses-mode` at base
`a8b0d5c29feaf451b4a7b562302272bc02fdad2a`, the exact isolated environment
reports Hermes Agent `0.18.2` from commit
`861d69c7bba8d2ea6a1cd170e989c901c74d32d1` and OpenAI SDK `2.24.0`. The
offline pinned-Hermes selection probe and Buddy adapter omission test pass
`2/2`. The complete `tests/test_hermes_graph_agent.py`,
`tests/test_agent_turn_service.py`, and `tests/test_agent_turn_trace.py` run
passes `74/74`. Those tests cover the existing turn history, response, usage,
tool-capability, and observer behavior. No server, database, port, corpus, or
provider request was used. The test-only OpenAI client constructor was mocked
while inspecting Hermes’ selected mode; no conversation was run.

The RTK wrapper could not spawn `pytest` because it is absent from its command
path; the same targeted test was then run successfully with the exact project
virtualenv’s pytest executable. This was a test-runner lookup issue, not a test
failure. PR #812 is merged; the assigned post-merge two-turn witness remains
pending and has not started as of this handoff update. The current roadmap also
records inherited, unmodified Plan/UI
failures outside this lease: the `ThreatPublicationPanel.tsx` JSX namespace
typecheck error and the legacy `PlanAgentInteractionBar.test.tsx` fixture’s
3/8 result against its retired `getWorkspaceDocument` mock. They were not rerun
as part of this backend adapter slice.

## Review handback

PRIME reviewed the exact cumulative PR #812 head
`3e006ca17aa2d3bc5ac2db45e84d33a4e972cb6e` and merged it at
`3494b8f4561b2ec465af42bf4fb55bac3f42ee3c`. The remaining
handback is the assigned live witness result: report its exact evidence,
inherited failures, unknown cost/usage where applicable, remaining gates, and
next roadmap action. Until that witness passes, this does not accept the Plan
conversation, close the appearance gate, or accept J1–J6.
