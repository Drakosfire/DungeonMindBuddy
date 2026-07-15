---
pr_body_template: |
  ## Outcome

  A Python caller can run one real Hermes `AIAgent` turn in-process using only the five PR010A World Graph tools, without binding Agent Interaction threads or persisting conversation state.

  ## Scope and verification

  * Predecessor base: `ccbf8054ec5df47fa883ce7122043f16e2fff408` (merge of PR #351)
  * Implementation base: the docs-only handoff commit on `main` that lands this file
  * Hermes pin: `NousResearch/hermes-agent@861d69c7bba8d2ea6a1cd170e989c901c74d32d1` (package 0.18.2)
  * Changed paths: report the actual §4 paths
  * Verification: report every §7 command, exact result, and provenance
  * Baseline failures and waivers: report the known PR010A schema-fixture drift through the required predecessor/head comparison
  * Deferred successors: Agent Interaction thread/session binding, product wiring, persistence, obsolete-path demolition, live dogfood acceptance
---

# HANDOFF — PR010B Rung 3: Embedded Hermes graph-agent turn

**Created:** 2026-07-13
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr352-hermes-embedded-graph-agent-turn.md`
**Predecessor base:** `ccbf8054ec5df47fa883ce7122043f16e2fff408` — merge of GitHub PR #351
**Implementation base:** the docs-only commit that lands this handoff on `main` (record the immutable SHA after check-in; do not treat chat as authority)
**Suggested branch:** `agent/pr010b3-hermes-embedded-graph-agent-turn`
**Suggested PR title:** `feat(agent): add embedded Hermes graph-agent turn`

> **Dispatch gate**
> Commit this handoff before dispatch. Use that docs-only commit as the implementation base while retaining `ccbf8054ec5df47fa883ce7122043f16e2fff408` as the predecessor anchor.
> This checked-in handoff is the complete authority. The worker must implement this complete document without compressing, replacing, or silently reinterpreting its constraints.
> Opening the pull request must be the final repository action. Do not open a draft early.

---

## §0 Capability decomposition decision

PR010B is an architectural area containing several independently useful capabilities. This slice deliberately implements only one embedded Hermes graph-agent turn over the merged Rung 1 dispatcher and Rung 2 catalog/adapter.

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Pin Hermes and resolve OpenAI/Python intersection so `AIAgent` imports from the locked environment | Yes | Yes — dependency contract | No | Yes | Yes | Include |
| Packaged graph-only Hermes plugin registering exactly five World Graph tools | Yes | Yes — entry-point + toolset contract | No | Yes | Yes | Include |
| Embedded runtime that constructs a lockdown `AIAgent` and runs one turn | Yes | Yes — internal caller contract | No | Yes | Yes | Include |
| Accept optional prior Hermes message history for one turn without durable persistence | Yes — same turn contract | Yes — same internal contract | No | Yes | Yes | Include |
| Ordered safe tool-event summaries for one turn | Yes — same turn contract | Yes — same internal contract | No | Yes | Yes | Include |
| Bind one Hermes session to one Agent Interaction thread | Yes | Yes | Yes | Yes | Yes | Successor (Rung 4) |
| Persist thread/session pointers or full conversation payloads | Yes | Yes | Yes | Yes | Yes | Successor (Rung 4) |
| Replace transitional `live_agent_loop.py` / plugin / CLI product path | Yes | Yes | Yes | Yes | Yes | Successor (replacement rung) |
| Remove obsolete Hermes tools and Live/Hermes toggle | Yes | Yes | Yes | Yes | Yes | Successor (acceptance/demolition) |
| Reconcile tracker and roadmap to Rung 3 active | No — authority sync | No runtime contract | No | No | No | Include as required documentation sync |

**Selected capability**

A reusable embedded Hermes graph-agent turn: dependency-locked `AIAgent` construction, graph-only plugin registration for the five PR010A tools, one `run_conversation` invocation with optional caller-supplied history, and a typed internal result with ordered safe tool events.

**Why the included rows share one invariant**

Dependency resolution, plugin registration, and the turn runtime are one model-reachable factual boundary. If Hermes can see any non-graph toolset, or if the turn can fall back to Live/legacy retrieval, the invariant is already broken regardless of how clean the Python wrapper looks.

**Named successors**

1. **PR010B Rung 4 — Agent Interaction thread/session binding and reload continuity.**
2. **PR010B replacement rung — Plan product wiring and removal of obsolete Hermes retrieval paths.**
3. **PR010B acceptance/demolition rung — dogfood proof, backend-toggle removal, and remaining product-path deletion.**

---

## §1 Mission

```text
A Python caller can run one real Hermes AIAgent turn in-process using only the five PR010A World Graph tools so that later product wiring has a real agent boundary with no legacy retrieval dependency.
```

**Invariant**

```text
The model may see and execute only search_campaign_graph, get_campaign_object, get_object_neighborhood, get_object_evidence, and read_source_anchor; no terminal, web, filesystem, manifest, corpus, Markdown, lexical, continuity, legacy DungeonBuddy, ambient-memory, Live-synthesis, or subprocess path may be visible or reachable. Campaign facts must come from fresh graph-tool results; conversation history may resolve intent and pronouns but is not factual authority.
```

**Mission falsification test**

```text
This is not one slice if implementation must also bind a Hermes session to an Agent Interaction thread, persist conversation state across process restarts, modify a product route or UI, replace or delete the transitional plugin/CLI path, enable write tools, or introduce Live/legacy/subprocess fallback when Hermes fails.
```

---

## §2 Context, authority, and boundaries

| Field | Required content |
| --- | --- |
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/ANCHOR-agent-interaction-hermes.md`; `.hermes.md` |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; checked-in handoff template |
| Predecessor base | `ccbf8054ec5df47fa883ce7122043f16e2fff408` — merge of GitHub PR #351 |
| Implementation base | Docs-only commit that lands this handoff on `main` (record immutable SHA after check-in) |
| Predecessor contract | PR #351 Rung 2 catalog/adapter; PR #350 Rung 1 dispatcher; PR010A models/services |
| Exact input consumed | Question + graph scope (`worldId`, `campaignId`, optional `focus` / `admissibility` / `revisionPin`) + optional Hermes `conversation_history` + optional caller-owned `session_id` |
| Named successor | PR010B Rung 4 — Agent Interaction thread/session binding and reload continuity |
| What remains false | No Agent Interaction thread binding; no durable conversation persistence; no product route/UI change; no transitional plugin deletion; no Live/Hermes toggle removal; no write tools; no live dogfood acceptance claimed |
| Explicit non-goals | Thread binding, reload continuity, product response shaping, citation-pane wiring, cancellation transport, product replacement/demolition, live dogfood acceptance, all write tools, CLI one-shot replacement, Live synthesis fallback |

### Dependency gate

Use the reviewed Hermes upstream commit:

```text
NousResearch/hermes-agent
861d69c7bba8d2ea6a1cd170e989c901c74d32d1
package version 0.18.2
```

Published constraints conflict with the current repository:

```text
Hermes:
  Python >=3.11,<3.14
  openai==2.24.0

DungeonBuddy:
  Python >=3.13
  openai>=2.30.0
```

Required preflight:

1. Pin Hermes to the reviewed commit.
2. Narrow DungeonBuddy Python support to the valid intersection if required: `>=3.13,<3.14`.
3. Resolve the OpenAI dependency without weakening Hermes’s exact pin.
4. Run the complete DungeonBuddy suite against the resolved environment.

Stop immediately if existing DungeonBuddy OpenAI behavior cannot operate on the resolved version.

Prohibited workarounds:

* unpinned Hermes dependency;
* relaxing Hermes’s dependency metadata locally;
* runtime package installation;
* `sys.path` injection from an external checkout;
* a second Python interpreter;
* invoking Hermes through a subprocess.

### Current repository state

The predecessor base contains:

* merged PR010A retrieval service and strict camelCase request/result contracts;
* the five exact read operations;
* merged Rung 1 dispatcher at `apps/live_control_server/services/hermes_graph_read_tools.py`;
* merged Rung 2 catalog/adapter at `apps/live_control_server/services/hermes_graph_read_tool_adapter.py`;
* no Hermes Python package in `pyproject.toml` / `uv.lock`;
* transitional Hermes plugin at `integrations/hermes/plugins/dungeonbuddy/**` still advertising legacy retrieval tools;
* transitional `live_agent_loop.py` that may shell to `hermes --oneshot` or call legacy in-process plugin logic.

Those transitional paths are evidence of remaining replacement work. They are not implementation seams for this slice.

### Required authority synchronization

Update tracker and roadmap so the active sequence becomes:

```text
DONE    PR010B Rung 1 — graph-read dispatcher (#350)
DONE    PR010B Rung 2 — model catalog and JSON adapter (#351)
DOING   PR010B Rung 3 — embedded Hermes graph-agent turn
NEXT    PR010B Rung 4 — Agent Interaction thread/session binding
LATER   product replacement, dogfood acceptance, and demolition
```

Do not change PR011 or PR012 numbering.

### Read authoritative inputs in order

Before changing code, read:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
3. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
4. `Docs/Design/ANCHOR-agent-interaction-hermes.md`
5. `.hermes.md`
6. `apps/live_control_server/services/hermes_graph_read_tools.py`
7. `apps/live_control_server/services/hermes_graph_read_tool_adapter.py`
8. `src/graph_memory/retrieval/models.py`
9. `apps/live_control_server/services/world_graph_retrieval.py`
10. `tests/test_hermes_graph_read_tools.py`
11. `tests/test_hermes_graph_read_tool_adapter.py`
12. `pyproject.toml`
13. `AGENTS.md`
14. `.cursor/rules/external-agent-pr-loop.mdc`
15. `.cursor/skills/external-agent-pr-loop/SKILL.md`

Inspection-only (do not edit or import as a dependency of the new runtime):

* `apps/live_control_server/services/live_agent_loop.py`
* `integrations/hermes/plugins/dungeonbuddy/**`

### Authority precedence

```text
1. Current repository architecture and accepted decisions
2. Current Campaign Supergraph roadmap and tracker
3. This checked-in handoff
4. Merged PR010A / PR010B Rung 1 / PR010B Rung 2 contracts
5. Current repository tests
6. Reviewed Hermes upstream commit used only for the pinned library API
7. Project Sources, historical handoffs, proposals, and chat summaries
```

If `main` moves beyond the recorded implementation base, or another branch changes any §4 runtime path, stop and report whether this handoff must be re-anchored.

---

## §3 Observable-path inventory

This slice has no user-facing UI, but it creates an externally consumed internal runtime boundary.

| Observable path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
| --- | --- | --- | ---: | --- |
| Import `AIAgent` from locked environment | Hermes not installed | `from run_agent import AIAgent` succeeds under `uv run` after frozen sync | Yes | Dependency resolution |
| Discover packaged graph plugin | No `dungeonbuddy_graph` entry point | Plugin discovery registers exactly five tools under toolset `dungeonbuddy_graph` | Yes | New plugin module + entry point |
| Construct agent for one caller-owned session | No lockdown constructor | Fresh `AIAgent` with `quiet_mode=True`, `skip_memory=True`, `skip_context_files=True`, `enabled_toolsets=["dungeonbuddy_graph"]` only | Yes | New runtime module |
| Run one turn with graph scope | No embedded turn API | `AIAgent.run_conversation(...)` with compact graph-only system policy and supplied scope | Yes | New runtime module |
| Pass prior conversation history | N/A | Optional history is forwarded to `run_conversation`; not treated as campaign truth | Yes | New runtime module |
| Model selects a graph tool | N/A | Handler routes to `execute_hermes_graph_read_tool_json`; always returns JSON string; never raises through Hermes | Yes | Plugin + Rung 2 adapter |
| Ordinary graph miss / partial / denied / unavailable | Owned by PR010A/Rung 2 | Preserved in tool JSON; no alternate retrieval | Yes | Plugin handlers + runtime |
| Provider / plugin / dependency failure | N/A | Typed internal error result; no Live/legacy/subprocess fallback | Yes | New runtime module |
| Tool-event summaries | N/A | Ordered safe summaries without prompts, secrets, paths, stack traces, or full source bodies | Yes | New runtime module |
| Repeated turn with same inputs | N/A | Fresh agent construction per independent caller-owned session; no durable adapter/runtime cache inventing continuity | Yes | New runtime module |

No Agent Interaction save/reload, product UI path, or operator toggle belongs to this capability.

---

## §4 Files in scope — allowlist

Every changed path must appear below.

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `pyproject.toml` | Pin Hermes to the reviewed commit; narrow Python intersection if required; declare the `hermes_agent.plugins` entry point; resolve OpenAI without weakening Hermes’s exact pin |
| Modify | `uv.lock` | Lock the resolved environment so imports and tests are reproducible |
| Create | `src/graph_memory/hermes_graph_plugin.py` | Packaged Hermes plugin registering exactly five graph tools derived from Rung 2 definitions and routed to the Rung 2 JSON adapter |
| Create | `apps/live_control_server/services/hermes_graph_agent.py` | Embedded lockdown `AIAgent` turn runtime returning a typed internal result with ordered safe tool events |
| Create | `tests/test_hermes_graph_agent.py` | Owning proofs for dependency import, plugin discovery, lockdown config, history passthrough, tool routing, event redaction, and absence of legacy/fallback paths |
| Modify | `.hermes.md` | Narrow policy language only as needed so Rung 3’s embedded graph-only turn is accurately described without claiming product replacement |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Record Rung 2 done (#351), mark Rung 3 active, name Rung 4 next |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Same rung sequence without changing higher-level architecture |

### Bounded discovery exception

```text
Not applicable — every expected changed path is listed above, including dependency lock files required by the dependency gate.
```

If implementation requires any additional file, including a fixture, snapshot, plugin under `integrations/hermes/`, route, UI file, or test helper outside this table, stop and report it.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability | Why this slice must not touch or claim it |
| --- | --- |
| `apps/live_control_server/services/live_agent_loop.py` | Product orchestration and future replacement wiring |
| `integrations/hermes/plugins/dungeonbuddy/**` | Transitional plugin; do not modify or import |
| `apps/live_control_server/routes/**` | No HTTP or product route |
| `apps/live-control-ui/**` | No UI or Agent Interaction behavior |
| `apps/live_control_server/session_store.py` and related session files | Thread/session persistence is Rung 4 |
| Agent Interaction thread records | Rung 4 |
| CLI one-shot code | Product backend replacement, later |
| Backend toggles / Live/Hermes toggle | Acceptance/demolition later |
| Legacy-tool deletion | Demolition when replacement product path is usable |
| `src/graph_memory/retrieval/models.py` | Predecessor contract; consume unchanged |
| `apps/live_control_server/services/world_graph_retrieval.py` | Consume unchanged |
| `apps/live_control_server/services/hermes_graph_read_tools.py` | Consume unchanged |
| `apps/live_control_server/services/hermes_graph_read_tool_adapter.py` | Consume unchanged |
| Write tools | Deferred until governed write path exists |
| Citation-pane wiring / product response shaping | Later product rungs |
| Cancellation transport | Later |
| Live dogfood acceptance | Acceptance rung |
| Unpinned / `sys.path` / subprocess Hermes | Explicitly prohibited |

Nearby work is not authorization.

---

## §6 Implementation contract and conditional matrices

### Core contract

```text
Input:
  question: non-empty string
  worldId: non-empty string
  campaignId: non-empty string
  focus: optional structured focus matching PR010A vocabulary
  admissibility: optional string matching PR010A vocabulary
  revisionPin: optional string or null
  conversation_history: optional Hermes message history owned by the caller
  session_id: optional caller-owned session identifier (not Agent Interaction binding)

Output:
  typed internal result containing:
    status: ok | error
    final_response: string | null
    messages: Hermes conversation history from the turn
    hermes_session_id: string
    tool_events: ordered safe summaries
    error_code: string | null
    error_message: generic string | null

Invariant:
  The model may see and execute only the five PR010A World Graph tools;
  campaign facts come from fresh graph-tool results; history is not factual authority.

Failure behavior:
  missing Hermes dependency / import failure
    → typed error; no fallback
  plugin discovery failure / wrong toolset contents
    → typed error; no fallback
  provider failure / malformed Hermes response / unexpected runtime exception
    → typed error; no Live/legacy/subprocess fallback
  graph empty/partial/denied/unavailable/error tool JSON
    → preserved in tool results and available to the model; no alternate retrieval

Replay / idempotency:
  same input against same graph revision
    → fresh agent construction for an independent caller-owned session;
      semantically equivalent factual retrieval through the same tools
  retry after failure
    → no runtime state inventing continuity; caller may retry with same inputs
  duplicate delivery
    → another read turn; no writes or deduplication store

Trust boundary:
  Verifies:
    Hermes imports from locked environment
    exactly five tools registered under dungeonbuddy_graph
    schemas derive from hermes_graph_read_tool_definitions()[i]["function"]
    handlers call execute_hermes_graph_read_tool_json
    AIAgent lockdown flags and enabled_toolsets
    tool events omit unsafe content
  Records or trusts without proving:
    factual correctness of the published graph revision
    provider model quality
    future Agent Interaction UX
  Rejects:
    any other toolset
    legacy DungeonBuddy tools
    terminal/web/filesystem/memory tool visibility
    Live synthesis fallback
    subprocess Hermes
    direct OpenAI model/tool loop bypassing AIAgent
```

### Graph-only Hermes plugin

Create a packaged Hermes plugin entry point:

```toml
[project.entry-points."hermes_agent.plugins"]
dungeonbuddy_graph = "graph_memory.hermes_graph_plugin"
```

The plugin must:

* register exactly five tools under toolset `dungeonbuddy_graph`;
* derive each bare Hermes schema from `hermes_graph_read_tool_definitions()[i]["function"]`;
* route every handler to `execute_hermes_graph_read_tool_json`;
* accept `args: dict` and `**kwargs`;
* always return a JSON string;
* never raise through Hermes;
* contain no second request schema or dispatcher.

Do not modify or import the transitional `integrations.hermes.plugins.dungeonbuddy` plugin.

### Embedded runtime

Create `apps/live_control_server/services/hermes_graph_agent.py` around the upstream Python-library API:

```python
from run_agent import AIAgent
```

The runtime must construct a fresh agent for each independent caller-owned session with:

```text
quiet_mode=True
skip_memory=True
skip_context_files=True
enabled_toolsets=["dungeonbuddy_graph"]
```

It must not enable any other toolset or fallback model.

The public turn input must include:

```text
question
worldId
campaignId
focus
admissibility
revisionPin
optional conversation_history
optional caller-owned session_id
```

The runtime supplies a compact system policy stating:

* graph tools are the sole factual retrieval plane;
* every tool call must use the supplied graph scope;
* source text is readable only through returned opaque anchors;
* graph gaps require uncertainty or abstention;
* prior messages are conversational context, not campaign truth.

Use `AIAgent.run_conversation(...)`. Do not call OpenAI directly or implement a parallel model/tool loop.

### Tool-event contract

Each tool event records only:

```text
tool name
start/completion/error state
duration
request scope and bounded identifiers
retrieval schema and outcome
matched node IDs
relationship IDs
source-anchor IDs
diagnostic codes
```

Do not retain raw prompts, secrets, filesystem paths, stack traces, or full source-anchor bodies in events.

### §6A State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dependency import | Resolve pinned Hermes + OpenAI | `AIAgent` importable | N/A | Typed error; stop | Typed error | Lockfile defines environment | Fresh sync |
| Plugin discovery | Entry point loads | Exactly five graph tools | N/A | Typed error | Typed error if extra tools appear | Code version defines plugin | Fresh process |
| Embedded turn | Construct lockdown agent | `status=ok` with final response/messages/events | Model may abstain; graph miss preserved in tool JSON | Typed error; no Live fallback | Typed error | Caller-owned history only; no durable store | Fresh agent |
| Graph tool call | Validate via Rung 2 | JSON PR010A success | Preserve empty/partial/denied | Preserve unavailable/service error JSON | Fail closed via adapter | Revision owned by PR010A | Fresh read |
| Legacy/other toolset | Must never load | N/A | N/A | N/A | Fail closed / discovery error | N/A | N/A |

**Fallback rule**

```text
No Live fallback, legacy plugin fallback, alternate retrieval, or subprocess fallback is permitted anywhere in this slice.
```

### §6B Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
| --- | --- | --- | --- | --- |
| Exact tool name | Exact case-sensitive five-name set | Reject / unknown via Rung 1/2 | No | None |
| Old Hermes tool name | Prohibited / not registered | Not model-visible | No | None |
| Toolset name | Exact `dungeonbuddy_graph` | Reject other toolsets | No | None |
| Caller session_id | Opaque caller-owned string | No Agent Interaction binding | No | Not persisted by this slice |
| Graph node / anchor IDs | Passed through PR010A unchanged | Predecessor decides | No | None |
| Conversation history | Caller-owned messages | Not campaign truth | No factual fallback from history | Not persisted by this slice |

### §6C Persistence and replay matrix

```text
Not applicable as a durable store — this slice creates no Agent Interaction binding,
thread pointer, session store write, conversation archive, or migration.

Caller-owned conversation_history may be supplied in-memory for one turn and returned
in the result messages field. The runtime does not persist it.
```

### §6D Predecessor-to-consumer mapping

**Grounding source**

```text
apps/live_control_server/services/hermes_graph_read_tool_adapter.py
apps/live_control_server/services/hermes_graph_read_tools.py
src/graph_memory/retrieval/models.py
reviewed Hermes AIAgent API at commit 861d69c7bba8d2ea6a1cd170e989c901c74d32d1
```

| Predecessor field or outcome | Real shape and optionality | Consumer field or behavior | Transformation | Proof fixture or test |
| --- | --- | --- | --- | --- |
| `hermes_graph_read_tool_definitions()[i]["function"]` | OpenAI-style name/description/parameters | Bare Hermes tool schema | Extract inner `function` object only | Schema equality test |
| `execute_hermes_graph_read_tool_json` | Always returns JSON string | Plugin handler return value | Pass-through; catch and map unexpected raises to error JSON if needed before Hermes sees them | Handler spy/integration test |
| `HERMES_GRAPH_READ_TOOL_NAMES` | Exact five names | Registered tool names | Preserve exactly | Plugin discovery test |
| PR010A graph scope fields | camelCase request vocabulary | Turn input + tool arguments | Preserve; inject into system policy / tool calls as required by scope | Turn construction tests |
| `AIAgent.run_conversation` | Upstream library API | Turn execution | No parallel loop | Mocked agent test proving call shape |
| Hermes messages / final response | Upstream conversation objects | Result `messages` / `final_response` | Capture without product shaping | Capture test |
| Tool call metadata | Hermes registry events | `tool_events` | Redact unsafe content; preserve order | Redaction test |

Invented substitute request fields or “close enough” fixtures are not acceptable proof.

---

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or scenario | Expected evidence |
| --- | --- | --- | --- |
| Hermes imports from locked environment | Dependency + focused tests | Import smoke + focused suite | `AIAgent` importable under `uv run` |
| Plugin discovery registers exactly five tools in `dungeonbuddy_graph` | Plugin | Focused suite | Exact name equality |
| Tool schemas equal Rung 2 catalog inner function schemas | Plugin | Focused suite | Schema equality |
| Handlers execute Rung 2 JSON adapter | Plugin | Focused suite with spy | Adapter called; JSON returned |
| `AIAgent` receives exact lockdown configuration | Runtime | Focused suite | Constructor kwargs asserted |
| Model-selected graph call executes through Hermes registry | Runtime + plugin | Focused suite | No parallel OpenAI loop |
| Prior conversation history passed to `run_conversation` | Runtime | Focused suite | History argument asserted |
| Messages and final response captured | Runtime | Focused suite | Result fields populated |
| Tool events preserve order and redact unsafe content | Runtime | Focused suite | Ordered summaries; no prompts/secrets/paths/bodies |
| Empty/partial/denied/unavailable/error produce no alternate retrieval | Runtime + plugin | Focused suite | No legacy imports/calls |
| No legacy tool name or built-in toolset model-visible | Plugin + runtime | Focused suite | Only five graph tools |
| No subprocess or direct OpenAI model loop | Source boundary | AST/literal assertions | Absent |
| Rung 1 and Rung 2 remain green | Predecessor suites | Required pytest commands | Green |
| Dependency resolution does not regress broader repository | Full suite (with known deselect) | Required pytest commands | No new failures vs predecessor |
| Tracker/roadmap agree on Rung sequence | Docs | Diff review | Rung 2 done, Rung 3 doing, Rung 4 next |

### Required commands

Run from repository root after the dependency gate:

```bash
uv lock
uv sync --frozen

uv run python -c "from run_agent import AIAgent; print(AIAgent.__name__)"

uv run pytest -q tests/test_hermes_graph_agent.py

uv run pytest -q \
  tests/test_hermes_graph_read_tool_adapter.py \
  tests/test_hermes_graph_read_tools.py

uv run pytest -q \
  --deselect tests/test_world_graph_retrieval_routes.py::test_api_contract_fixture_matches_real_generated_operations

uv run pytest -q \
  tests/test_world_graph_retrieval_routes.py::test_api_contract_fixture_matches_real_generated_operations

uv run ruff check \
  src/graph_memory/hermes_graph_plugin.py \
  apps/live_control_server/services/hermes_graph_agent.py \
  tests/test_hermes_graph_agent.py

git diff --check

git diff --stat <IMPLEMENTATION_BASE>...HEAD -- \
  pyproject.toml \
  uv.lock \
  src/graph_memory/hermes_graph_plugin.py \
  apps/live_control_server/services/hermes_graph_agent.py \
  tests/test_hermes_graph_agent.py \
  .hermes.md \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md

git diff --name-only <IMPLEMENTATION_BASE>...HEAD
```

Replace `<IMPLEMENTATION_BASE>` with the immutable docs-only handoff commit SHA.

Also compare the known PR010A schema-fixture failure on predecessor `ccbf8054ec5df47fa883ce7122043f16e2fff408` and head. Any new failure blocks merge. Do not update `tests/fixtures/world_graph_retrieval/api-contract-v1.json`; it is outside the allowlist.

### Minimal live proof

```text
Not applicable as a product live proof — this slice deliberately does not wire Agent Interaction UI or routes.
Focused tests may mock AIAgent / provider boundaries while still proving real plugin registration and adapter routing.
A live provider dogfood turn is deferred to the acceptance rung.
```

### Baseline failure protocol

Required evidence table:

| Command | Predecessor (`ccbf8054`) result | Head result | New failure introduced? | Acceptance effect | Waiver |
| --- | --- | --- | ---: | --- | --- |
| `uv run pytest -q tests/test_world_graph_retrieval_routes.py::test_api_contract_fixture_matches_real_generated_operations` | Record exact result | Record exact result | Yes / No | Block if behavior differs; otherwise explicit baseline waiver required | Name operator waiver or `none` |

Do not call the full predecessor gate green while this test fails. State that the deselected suite is green and the baseline test remains failing identically only if the evidence proves that statement.

---

## §8 Required implementation handback

The pull-request body or implementation handback must include:

1. Predecessor base SHA: `ccbf8054ec5df47fa883ce7122043f16e2fff408`.
2. Implementation base SHA (docs-only handoff commit).
3. Head SHA.
4. Hermes commit and resolved dependency versions (Hermes package, Python constraint, OpenAI pin/resolution).
5. Actual changed paths and focused diff stat limited to §4.
6. Every §7 command and exact result.
7. Provenance for every result: author-local, independently rerun local, CI, or manual inspection.
8. Registered tool names and proof that no other toolset was visible.
9. Confirmation that tool schemas derive from Rung 2 definitions and handlers call the Rung 2 JSON adapter.
10. Confirmation that `AIAgent` lockdown flags match the contract.
11. Confirmation that no model/tool loop bypasses Hermes, no subprocess Hermes, and no Live/legacy fallback exists.
12. Confirmation that no Agent Interaction binding, durable persistence, route/UI, or product replacement was added.
13. Baseline failure predecessor/head comparison.
14. Explicit operator waivers; write `none` when none exist.
15. Paths outside §4; write `none` or include a stop report.
16. Stop conditions encountered and resolution; write `none` when none exist.
17. Deviations from §6 matrices; write `none` when none exist.
18. Named successor capabilities deferred and still false.
19. Confirmation that no successor is claimed as delivered.
20. Confirmation that the complete authoritative handoff was implemented without omitted constraints.
21. Confirmation that opening the pull request was the final repository action for the branch.

### Required retain / rewrite / delete statement

```text
Retained unchanged:
- Transitional Hermes plugin and legacy tool registrations
- live_agent_loop.py product paths
- one-shot CLI backend
- Live/Hermes product toggle

Reason:
- This rung creates only the embedded graph-only Hermes turn boundary.
- No replacement product path exists yet.

Remaining consumers:
- Existing transitional Plan/Hermes spike tests and product paths.

Required successor:
- PR010B Rung 4 binds Agent Interaction threads to Hermes sessions and reload continuity.
- Later PR010B replacement work wires the product path and deletes obsolete retrieval tools and backends at replacement time.
```

---

## §9 Acceptance rubric

The reviewer accepts only when every item is true.

* [ ] Exactly one independently useful capability was delivered: embedded Hermes graph-agent turn — proved by `tests/test_hermes_graph_agent.py` and diff inspection.
* [ ] Hermes imports from the locked environment — proved by import smoke and focused suite.
* [ ] Plugin discovery registers exactly five tools under `dungeonbuddy_graph` — proved by focused suite.
* [ ] Tool schemas equal Rung 2 catalog inner function schemas — proved by schema equality tests.
* [ ] Handlers route to `execute_hermes_graph_read_tool_json` and always return JSON without raising through Hermes — proved by focused suite.
* [ ] `AIAgent` receives exact lockdown configuration and only `dungeonbuddy_graph` — proved by constructor assertions.
* [ ] Optional conversation history is passed to `run_conversation` and is not treated as campaign truth — proved by focused suite plus system-policy assertions.
* [ ] Result captures status, final response, messages, hermes_session_id, tool_events, and typed errors — proved by focused suite.
* [ ] Tool events preserve order and redact unsafe content — proved by redaction tests.
* [ ] Empty/partial/denied/unavailable/error graph results produce no alternate retrieval — proved by focused suite and import/literal assertions.
* [ ] No legacy tool name or built-in toolset is model-visible — proved by discovery/lockdown tests.
* [ ] No subprocess Hermes or direct OpenAI model/tool loop exists — proved by source-boundary assertions.
* [ ] Dependency resolution does not regress the broader repository beyond the known baseline fixture drift — proved by full suite + predecessor/head baseline comparison.
* [ ] Rung 1 and Rung 2 suites remain green — proved by required pytest commands.
* [ ] Tracker and roadmap agree: Rung 2 done (#351), Rung 3 doing, Rung 4 next — proved by documentation diff review.
* [ ] No unexpected path changed — proved by `git diff --name-only <IMPLEMENTATION_BASE>...HEAD`.
* [ ] Baseline failures and waivers are reported truthfully.
* [ ] Rung 4 thread binding, product replacement, and demolition remain unimplemented and unclaimed.
* [ ] The complete authoritative handoff survived dispatch without omitted constraints.
* [ ] Opening the pull request was the final repository action.

---

## §10 Reviewer protocol

1. Confirm the diff is based on the recorded implementation base (docs-only handoff commit) with predecessor anchor `ccbf8054…`.
2. Restate the mission: one embedded graph-only Hermes turn, not product wiring.
3. Compare the actual diff against §4 and reject any unlisted path.
4. Inspect dependency resolution first: Hermes pin, Python intersection, OpenAI resolution without weakening Hermes’s pin.
5. Inspect the plugin: exact five tools, schemas from Rung 2, handlers to JSON adapter, no legacy plugin import.
6. Inspect the runtime: lockdown flags, `run_conversation` only, typed errors, no fallbacks.
7. Verify tool-event redaction.
8. Search the diff for: `manifest`, `corpus`, `markdown`, `breadcrumb`, `dungeon_search`, `dungeon_context_lookup`, `subprocess`, `--oneshot`, `live_agent_loop`, `sys.path`, Live fallback language.
9. Rerun every §7 command independently.
10. Compare the known baseline fixture test on predecessor and head.
11. Confirm tracker/roadmap sequencing.
12. Confirm Rung 4 and replacement work remain false.

---

## §11 Re-review protocol

Begin any re-review from the prior finding ledger.

| Prior finding | Claimed fix | Owning files or tests | Verified? | New consequence? |
| --- | --- | --- | ---: | --- |
| `<finding>` | `<claimed resolution>` | `<paths/tests>` | Yes / No | `<none or consequence>` |

For every prior finding:

1. Verify the literal fix.
2. Rerun the focused Hermes graph-agent suite.
3. Recheck dependency import and plugin discovery.
4. Recheck lockdown configuration and absence of other toolsets.
5. Recheck the §4 allowlist.
6. Recheck that no Live/legacy/subprocess fallback was introduced while fixing the issue.
7. Recheck tracker/roadmap agreement if documentation changed.
8. Add any new consequence to the ledger.

Do not approve a re-review solely because the reported failing test now passes.

---

## Stop conditions

Stop and report rather than expanding scope if implementation discovers:

* dependency resolution fails;
* existing OpenAI consumers regress;
* Hermes cannot load the packaged plugin without mutating a user-global profile;
* Hermes exposes any tool beyond the five graph reads;
* the implementation requires `live_agent_loop.py`, routes, persistence, legacy plugin changes, or subprocess execution;
* the normal Hermes registry/provider path cannot accept the generated schemas;
* a successful turn cannot expose ordered tool-call evidence;
* a required file falls outside §4;
* `main` or another open PR materially changes an allowlisted path;
* the baseline fixture failure differs between predecessor and head;
* an operator waiver is required for a newly introduced failure;
* repository rules conflict with this handoff.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update required:
Operator decision required:
```

The worker must not resolve a stop condition by silently adding a provider shim, request translator, plugin migration, product route, Live fallback, subprocess, or unpinned dependency.

---

## §12 Execution sequence and final PR action

Perform work in this order:

1. Confirm predecessor `ccbf8054ec5df47fa883ce7122043f16e2fff408` is present on `main`.
2. Branch from the recorded implementation base (this handoff’s docs-only commit).
3. Record the immutable implementation base SHA in the PR body.
4. Read the complete handoff.
5. Resolve the dependency gate before writing runtime code.
6. Implement only the allowlisted capability.
7. Run every §7 command.
8. Resolve failures without expanding scope.
9. Update tracker and roadmap narrowly.
10. Run `git diff --check` and verify changed paths exactly match §4 (plus this handoff only if comparing against predecessor rather than implementation base).
11. Prepare the complete PR body.
12. Commit all changes.
13. Push the branch.
14. Confirm `git status --short` is empty.
15. Confirm the remote branch contains the tested head.
16. **As the final repository action, open a non-draft pull request against `main`.**

Use:

```text
Title: feat(agent): add embedded Hermes graph-agent turn
Base: main
Head: agent/pr010b3-hermes-embedded-graph-agent-turn
```

Do not:

* open the PR before verification;
* open a placeholder or draft PR;
* push another implementation commit after opening the PR;
* modify PR metadata after opening it unless the operator explicitly requests a correction;
* create a second PR;
* merge the PR.

After opening it, return the PR URL and the final handback summary to the operator.

---

## Final dispatch check

Before dispatching, confirm:

* [ ] This handoff is checked into `Docs/Plans/HANDOFF-pr352-hermes-embedded-graph-agent-turn.md`.
* [ ] Predecessor base is still `ccbf8054ec5df47fa883ce7122043f16e2fff408`.
* [ ] Implementation base is the docs-only commit that lands this file.
* [ ] No open PR now overlaps an allowlisted runtime or authority path.
* [ ] §0 records the split between embedded turn and thread binding / product replacement.
* [ ] §1 contains one invariant reused throughout the document.
* [ ] §2 contains the Hermes dependency gate and prohibited workarounds.
* [ ] §3 inventories turn, plugin, dependency, miss, and failure paths.
* [ ] §4 expresses the complete expected diff including lockfiles.
* [ ] §5 names every tempting product-path expansion.
* [ ] Every §6 matrix is completed or explicitly marked not applicable.
* [ ] Every §9 behavioral guarantee maps to an owning-boundary §7 proof.
* [ ] The known baseline failure protocol is executable.
* [ ] No essential requirement exists only in chat or the PR summary.
* [ ] The worker is instructed that opening the PR is the final repository action.
