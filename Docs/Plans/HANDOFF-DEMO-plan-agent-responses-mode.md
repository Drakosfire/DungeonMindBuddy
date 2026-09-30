# HANDOFF — DEMO: route the saved Plan Agent through Hermes Responses mode

**Status:** ACTIVE — PRIME authorized one bounded implementation PR on 2026-09-30

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), merged
saved managed-World Plan Agent contract in
[HANDOFF-DEMO-plan-agent-conversation.md](HANDOFF-DEMO-plan-agent-conversation.md),
ARCHITECTURE’s same-model transport ruling, RAKE DUTY’s read-only retry and
telemetry triage, and PRIME’s explicit activation.

**Base:** Buddy `main@a8b0d5c29feaf451b4a7b562302272bc02fdad2a`, verified from
the GitHub `main` ref on 2026-09-30. The local fetch metadata is read-only in
the calling checkout; this isolated worktree starts at the verified commit.

**Branch / checkout:** `codex/demo-plan-agent-responses-mode` in the isolated
worktree `/home/drakosfire/.codex/worktrees/demo-plan-agent-responses-mode/DungeonMindBuddy`.

**Topology:** `parallel-independent`, explicitly authorized by PRIME. Concurrent
#810 is at `a20e14518ebdb24a5e1790c2486dfad8758c7920`; its active paths cover
World Play Runbook/context routes and tests and exclude this adapter and test.
Concurrent #811 is at `ae1e3aaff746aee8ad630ffa58f7e22d79d3997e`; it is limited
to Alembic logging and its test. This PR uses no database, service, port, corpus,
or provider during implementation and tests. Do not edit either concurrent
lease. Obtain a fresh runtime target from PRIME after merge before the live Plan
witness.

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

- Preserve model `gpt-5.3-codex`, provider `openai-api`, base URL
  `https://api.openai.com/v1`, existing key resolution, prompts, turn history,
  graph-none policy, Plan identity, response mapping, and UI/session semantics.
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

## Post-merge live witness — separately leased runtime

PRIME authorized one new synthetic managed-World Plan witness only after this
repair is reviewed and merged. Before starting services, obtain a fresh
disposable DB/API/UI target from PRIME; the earlier containers and ports were
retired and must not be reused. Create a new synthetic World and saved Plan
through the ordinary UI; do not assume the retired witness’s Plan revision or
database still exists.

Use the same `gpt-5.3-codex` model and at most two ordinary UI turns on the same
saved Plan with `graph_request={"mode":"none"}`. The authorized additional cap
is at most 6 OpenAI HTTP attempts and $0.50 estimated/observed spend. Stop on
the first provider error or either cap. Record client-thread, turn and provider
request IDs, actual mode/model/base, returned usage/cost, saved editor state,
and no-graph evidence; report unavailable values as unknown. A successful
response on one turn alone does not prove multi-turn continuity.

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
failure. The post-merge two-turn live witness remains pending a fresh PRIME
runtime lease. The current roadmap also records inherited, unmodified Plan/UI
failures outside this lease: the `ThreatPublicationPanel.tsx` JSX namespace
typecheck error and the legacy `PlanAgentInteractionBar.test.tsx` fixture’s
3/8 result against its retired `getWorkspaceDocument` mock. They were not rerun
as part of this backend adapter slice.

## Review handback

PRIME owns exact-head review and merge. The final handback will include branch,
base, head, changed paths, focused and owning-boundary tests, relevant live
evidence after merge, inherited failures, unknown cost/usage where applicable,
remaining gates, and the next roadmap action. This repair does not accept the
Plan conversation until its live two-turn witness passes, and does not close
the appearance gate or J1–J6 journey.
