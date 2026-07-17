---

pr_body_template: |

## Outcome

An in-process Hermes runtime can obtain the exact five graph-only tool definitions and execute a selected call through one JSON-string adapter so that the later agent/session loop has a model-facing boundary with no legacy retrieval dependency.

## Scope and verification

* Base: `55fd41171ab91e0dd8a707bf63ad763326b15c3b`
* Changed paths: report the actual §4 paths
* Verification: report every §7 command, exact result, and provenance
* Baseline failures and waivers: report the known PR010A schema-fixture drift through the required base/head comparison
* Deferred successors: real Hermes model loop, session/thread lifecycle, product wiring, persistence, and obsolete-path demolition

---

# HANDOFF — PR010B Rung 2: Hermes graph-read model tool adapter

**Created:** 2026-07-13
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr351-hermes-graph-read-model-adapter.md`
**Implementation base:** `55fd41171ab91e0dd8a707bf63ad763326b15c3b`
**Suggested branch:** `agent/pr010b2-hermes-graph-read-model-adapter`

> **Dispatch gate:** This handoff must be checked into the repository before dispatch. The worker must implement this complete document without compressing, replacing, or silently reinterpreting its constraints.

---

## §0 Capability decomposition decision

PR010B is an architectural area containing several independently useful capabilities. This slice deliberately implements only the model-facing tool boundary immediately above the merged Rung 1 dispatcher.

| Candidate outcome                                                                            |                      Independently useful? |     Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision                               |
| -------------------------------------------------------------------------------------------- | -----------------------------------------: | -----------------------------------: | --------------------------------: | ---------------------: | ------------------------------------: | -------------------------------------- |
| Produce model-visible definitions for the five PR010A graph-read tools                       |                                        Yes |      Yes — internal runtime contract |                                No |                    Yes |                                   Yes | Include                                |
| Convert one model-selected tool call into a JSON-string result through the Rung 1 dispatcher |                                        Yes | Yes — same internal runtime contract |                                No |                    Yes |                                   Yes | Include                                |
| Instantiate a model or allow Hermes to choose a tool                                         |                                        Yes |                                  Yes |                                No |                    Yes |                                   Yes | Successor                              |
| Create or resume Hermes sessions                                                             |                                        Yes |                                  Yes |                                No |                    Yes |                                   Yes | Successor                              |
| Bind one Hermes session to one Agent Interaction thread                                      |                                        Yes |                                  Yes |                               Yes |                    Yes |                                   Yes | Successor                              |
| Persist thread/session pointers or full conversation payloads                                |                                        Yes |                                  Yes |                               Yes |                    Yes |                                   Yes | Successor                              |
| Replace the current manifest-backed plugin or one-shot CLI product path                      |                                        Yes |                                  Yes |                               Yes |                    Yes |                                   Yes | Successor                              |
| Remove obsolete Hermes tools and the Live/Hermes product toggle                              |                                        Yes |                                  Yes |                               Yes |                    Yes |                                   Yes | Successor                              |
| Reconcile tracker and roadmap language with the actual rung split                            | No — subordinate authority synchronization |                  No runtime contract |                                No |                     No |                                    No | Include as required documentation sync |

**Selected capability**

A reusable, model-facing Hermes graph-read tool catalog and JSON-string execution adapter over the already-merged graph-only dispatcher.

**Why the included rows share one invariant**

Tool definitions and handler execution are the two halves of one model-tool boundary: the catalog declares exactly what the model may call, and the adapter proves that every declared call reaches the same strict PR010A dispatcher. Neither half is useful as the intended runtime contract if it can drift independently from the other.

**Named successors**

1. **PR010B Rung 3 — real in-process Hermes agent/session loop.**
2. **PR010B Rung 4 — Agent Interaction thread/session binding and reload continuity.**
3. **PR010B replacement rung — Plan product wiring and removal of obsolete Hermes retrieval paths.**
4. **PR010B acceptance/demolition rung — dogfood proof, backend-toggle removal, and any remaining product-path deletion owned by PR010B.**

---

## §1 Mission

```text
An in-process Hermes runtime can obtain the exact five graph-only tool definitions and execute a selected call through one JSON-string adapter so that the later agent/session loop has a model-facing boundary with no legacy retrieval dependency.
```

**Invariant**

```text
Every advertised tool and every executed call is derived from the same five PR010A request/result contracts and the merged Rung 1 dispatcher; no manifest, corpus, repository-Markdown, arbitrary-path, lexical, breadcrumb, compatibility, or ambient-memory retrieval path can be advertised or invoked.
```

**Mission falsification test**

```text
This is not one slice if implementation must also instantiate a model, run a model/tool loop, create or resume a Hermes session, bind a session to an Agent Interaction thread, persist conversation state, modify a product route or UI, register or replace the transitional plugin, or delete the existing product backend.
```

---

## §2 Context, authority, and boundaries

| Field                | Required content                                                                                                                                                                                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent authority     | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/ANCHOR-agent-interaction-hermes.md`; `.hermes.md`                                                                          |
| Repository rules     | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; checked-in handoff template                                                                                                                                                     |
| Base revision        | `55fd41171ab91e0dd8a707bf63ad763326b15c3b` — merge commit for GitHub PR #350                                                                                                                                                                                                               |
| Predecessor contract | GitHub PR #350; `apps/live_control_server/services/hermes_graph_read_tools.py`; PR010A request/result/error models in `src/graph_memory/retrieval/models.py`                                                                                                                               |
| Exact input consumed | A model-selected exact tool name plus a mapping of camelCase arguments conforming to the corresponding PR010A Pydantic request model                                                                                                                                                       |
| Named successor      | PR010B Rung 3 — real in-process Hermes agent/session loop using this catalog and adapter                                                                                                                                                                                                   |
| What remains false   | No model chooses a tool; no LLM runs; no Hermes session exists; no Agent Interaction thread is bound; no route or UI uses this adapter; no product backend is replaced; no obsolete retrieval code is deleted                                                                              |
| Explicit non-goals   | Model inference, prompt design, session lifecycle, thread persistence, route/UI wiring, plugin migration, CLI replacement, product toggles, dogfood answer synthesis, citations, traces, cancellation, writes, drafts, Play migration, provider configuration, and dependency installation |

### Current repository state

The implementation base contains:

* the merged PR010A retrieval service and strict camelCase request/result contracts;
* the five exact read operations:

  * `search_campaign_graph`
  * `get_campaign_object`
  * `get_object_neighborhood`
  * `get_object_evidence`
  * `read_source_anchor`
* the merged Rung 1 strict dispatcher at `apps/live_control_server/services/hermes_graph_read_tools.py`;
* no installed Hermes Python SDK dependency in `pyproject.toml`;
* no model-visible graph-tool catalog;
* no JSON-string graph-tool handler adapter;
* a transitional Hermes plugin that still advertises manifest, corpus, arbitrary-path, continuity, and optional lexical retrieval tools;
* a transitional `live_agent_loop.py` path that either calls manifest-backed plugin logic in process or shells to a one-shot CLI and merely attaches graph context for inspection.

The existing product paths are evidence of replacement work still required. They are not implementation seams for this slice.

### Required authority synchronization

The active tracker currently combines “in-process Hermes tool definitions” and “real agent/session loop” under one Rung 2 label. That grouping conflicts with the independently useful capability decomposition above.

This slice must update the tracker and roadmap so the active sequence becomes:

```text
DONE    PR010B Rung 1 — strict graph-only read-tool dispatcher (#350)
DOING   PR010B Rung 2 — model-visible tool catalog plus JSON-string adapter
NEXT    PR010B Rung 3 — real in-process Hermes agent/session loop
LATER   PR010B thread binding, product replacement, dogfood acceptance, and demolition
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
7. `src/graph_memory/retrieval/models.py`
8. `apps/live_control_server/services/world_graph_retrieval.py`
9. `tests/test_hermes_graph_read_tools.py`
10. `AGENTS.md`
11. `.cursor/rules/external-agent-pr-loop.mdc`
12. `.cursor/skills/external-agent-pr-loop/SKILL.md`

### Authority precedence

```text
1. Current repository architecture and accepted decisions
2. Current Campaign Supergraph roadmap and tracker
3. This checked-in handoff
4. Merged PR010A and PR010B Rung 1 implementation contracts
5. Current repository tests
6. External Hermes documentation used only to clarify the adapter shape
7. Project Sources, historical handoffs, proposals, and chat summaries
```

If `main` moves beyond `55fd41171ab91e0dd8a707bf63ad763326b15c3b`, or another branch changes any §4 runtime path, stop and report whether this handoff must be re-anchored. Do not silently rebase the contract onto materially changed predecessor behavior.

---

## §3 Observable-path inventory

This slice has no user-facing UI, but it creates an externally consumed internal runtime boundary. The following paths are therefore observable to the future Hermes loop and must all preserve the §1 invariant.

| Observable path                               | Current behavior                                                                      | Required behavior                                                                                                                           | Same invariant as §1? | Owning boundary               |
| --------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------: | ----------------------------- |
| Request the tool catalog                      | No graph-only model definitions exist                                                 | Return exactly five model-visible function definitions backed by the five PR010A request models                                             |                   Yes | New adapter module            |
| Mutate a returned catalog object              | A future caller could accidentally mutate a shared constant if implemented carelessly | A later catalog request remains unchanged; caller mutation does not alter process-global definitions                                        |                   Yes | New adapter module            |
| Execute a declared tool successfully          | Rung 1 returns a Pydantic result object to Python callers                             | Adapter invokes Rung 1 and returns a JSON string containing the existing PR010A success result shape with camelCase aliases                 |                   Yes | New adapter module            |
| Execute `read_source_anchor` successfully     | Rung 1 returns the distinct PR010A source-anchor read result                          | Adapter returns that existing result schema as JSON without wrapping it in a parallel retrieval contract                                    |                   Yes | New adapter module            |
| Unknown tool name                             | Rung 1 raises `HermesGraphReadToolContractError(code="unknown_tool")`                 | Adapter returns a serialized existing `WorldGraphRetrievalErrorResponse` with stable code and status; it does not raise to the model caller |                   Yes | New adapter module            |
| Invalid argument mapping                      | Rung 1 raises `HermesGraphReadToolContractError(code="invalid_arguments")`            | Adapter returns a serialized existing `WorldGraphRetrievalErrorResponse`; rejected arguments never reach the service                        |                   Yes | New adapter module            |
| PR010A service failure                        | Service raises `WorldGraphRetrievalServiceError`                                      | Adapter serializes `exc.response()` without altering its code, status, diagnostics, or meaning                                              |                   Yes | New adapter module            |
| Unexpected adapter failure                    | No model-facing adapter exists                                                        | Return a fail-closed existing retrieval-error envelope with a stable adapter-internal error code; never consult a fallback retrieval path   |                   Yes | New adapter module            |
| Repeated identical execution                  | Rung 1 is stateless                                                                   | Same tool name, arguments, graph root, and graph revision produce semantically equivalent serialized output; no adapter state accumulates   |                   Yes | New adapter module            |
| Forbidden legacy field supplied               | Rung 1 rejects extra fields through strict PR010A request models                      | Adapter returns `invalid_arguments`; it never translates manifest, path, corpus, breadcrumb, query-backend, or compatibility fields         |                   Yes | Rung 1 plus new adapter       |
| Catalog inspection for forbidden capabilities | No catalog exists                                                                     | No definition, property, description, alias, or tool name advertises legacy retrieval or arbitrary document access                          |                   Yes | New adapter module plus tests |

No save/reload, persistence, background refresh, user interaction, or operator path exists in this capability.

---

## §4 Files in scope — allowlist

Every changed path must appear below.

| Action | Path                                                                  | Purpose: how this establishes or proves §1                                                                                                                           |
| ------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Modify | `apps/live_control_server/services/hermes_graph_read_tools.py`        | Expose the minimum read-only request-model metadata needed for the model catalog to derive from the same registry as execution, without adding a second dispatcher   |
| Create | `apps/live_control_server/services/hermes_graph_read_tool_adapter.py` | Provide the exact model-visible catalog and JSON-string execution adapter over Rung 1                                                                                |
| Create | `tests/test_hermes_graph_read_tool_adapter.py`                        | Prove catalog shape, shared-contract derivation, JSON serialization, failure behavior, mutation isolation, and absence of legacy dependencies at the owning boundary |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`                        | Record Rung 1 as merged, split model adapter from the real agent/session loop, and mark this Rung 2 active                                                           |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`                        | Reconcile stale PR010A/PR010B status and document the same rung decomposition without changing higher-level architecture                                             |

### Bounded discovery exception

```text
Not applicable — the predecessor contracts and intended adapter boundary are already known, and every expected changed path is listed above.
```

If implementation requires any additional file, including a fixture, snapshot, lockfile, dependency manifest, plugin file, route, or test helper outside this table, stop and report it.

---

## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability                                                                                         | Why this slice must not touch or claim it                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `apps/live_control_server/services/live_agent_loop.py`                                                                       | Owns transitional product orchestration and future Rung 3/product replacement work                                 |
| `integrations/hermes/plugins/dungeonbuddy/**`                                                                                | Transitional plugin migration and obsolete-tool removal are separate product-replacement capabilities              |
| `.hermes.md`                                                                                                                 | Policy already states the intended graph-only boundary; no runtime policy change is needed to create this adapter  |
| `apps/live_control_server/routes/**`                                                                                         | No HTTP or product route is part of the mission                                                                    |
| `apps/live-control-ui/**`                                                                                                    | No UI or Agent Interaction behavior is part of the mission                                                         |
| `apps/live_control_server/session_store.py` and related session files                                                        | Session/thread persistence belongs to later rungs                                                                  |
| `pyproject.toml`, `uv.lock`, or any dependency file                                                                          | This slice must not install or vendor Hermes                                                                       |
| `src/graph_memory/retrieval/models.py`                                                                                       | PR010A is the predecessor contract; this slice adapts it rather than changing it                                   |
| `apps/live_control_server/services/world_graph_retrieval.py`                                                                 | Existing service semantics remain authoritative and unchanged                                                      |
| `graph_memory/kernel/**`                                                                                                     | Kernel retrieval is already merged and outside this adapter capability                                             |
| Model provider configuration or prompts                                                                                      | No LLM or model call occurs                                                                                        |
| Hermes session creation or resumption                                                                                        | Named Rung 3 successor                                                                                             |
| Agent Interaction thread/session mapping                                                                                     | Separate durable lifecycle contract                                                                                |
| Full conversation persistence                                                                                                | Separate persistence contract                                                                                      |
| Tool start/completion trace events                                                                                           | Require an actual loop and belong to Rung 3 or later                                                               |
| Cite-or-abstain answer policy                                                                                                | Requires model synthesis and belongs to the real loop/dogfood rung                                                 |
| Removal of `dungeon_search`, `dungeon_manifest_index`, `dungeon_context_lookup`, `dungeon_get_document`, or continuity tools | Product-path demolition must occur when the replacement product path becomes usable                                |
| Removal of `hermes --oneshot`                                                                                                | Product backend replacement, not catalog construction                                                              |
| Removal of the Live/Hermes toggle                                                                                            | Acceptance/demolition work after real Hermes dogfood                                                               |
| Compatibility aliases for old tool names                                                                                     | Explicitly prohibited; old names remain unknown                                                                    |
| Request translation that injects or removes schema fields                                                                    | Would invent a compatibility request shape instead of exposing the merged PR010A contract                          |
| Broad Hermes SDK reconnaissance committed as code or docs                                                                    | External implementation details may inform design, but this slice must remain repository-local and dependency-free |

Nearby work is not authorization. Do not touch an excluded path to make a manual demonstration easier.

---

## §6 Implementation contract and conditional matrices

### Core contract

```text
Input:
  Catalog:
    no arguments

  Execution:
    tool_name: exact string
    arguments: Mapping[str, Any] using the corresponding PR010A camelCase request schema
    root: optional pathlib.Path test/runtime override, matching Rung 1

Output:
  Catalog:
    a fresh ordered collection of exactly five OpenAI/Hermes-compatible
    function definitions

  Execution:
    a JSON string representing exactly one existing PR010A model:
      - WorldGraphRetrievalResult
      - WorldGraphSourceAnchorReadResult
      - WorldGraphRetrievalErrorResponse

Invariant:
  Every advertised tool and every executed call is derived from the same five
  PR010A request/result contracts and the merged Rung 1 dispatcher; no legacy
  retrieval path can be advertised or invoked.

Failure behavior:
  unknown tool
    → WorldGraphRetrievalErrorResponse
      code="unknown_tool"
      statusCode=404

  invalid arguments
    → WorldGraphRetrievalErrorResponse
      code="invalid_arguments"
      statusCode=400

  WorldGraphRetrievalServiceError
    → serialize exc.response() without semantic translation

  unexpected adapter exception
    → WorldGraphRetrievalErrorResponse
      code="hermes_graph_read_tool_adapter_error"
      statusCode=500
      generic non-secret message
      no fallback

Replay / idempotency:
  same input
    → semantically equivalent JSON output against the same graph revision

  changed input
    → independently validated and dispatched

  retry after failure
    → no adapter state is retained; retry performs a fresh validation and call

  duplicate delivery
    → treated as another read; no writes or deduplication state exist

Trust boundary:
  Verifies:
    exact tool name
    mapping-shaped arguments
    strict PR010A request validation
    output is one of the existing PR010A response/error models
    JSON serialization uses field aliases

  Records or trusts without proving:
    factual correctness of the already-published graph revision
    source artifact truth beyond PR010A admission
    caller intent
    future model behavior

  Rejects:
    unknown tool names
    snake_case wire keys
    extra fields
    manifest selectors
    corpus selectors
    arbitrary paths
    repository Markdown paths
    breadcrumb fields
    legacy query-backend fields
    compatibility names
```

### Model-visible definition shape

Each returned item must have this outer shape:

```json
{
  "type": "function",
  "function": {
    "name": "<exact PR010A tool name>",
    "description": "<specific graph-only usage description>",
    "parameters": {
      "type": "object",
      "...": "JSON Schema derived from the corresponding PR010A request model"
    }
  }
}
```

Requirements:

1. Exactly five definitions are returned.
2. Definition names equal `HERMES_GRAPH_READ_TOOL_NAMES`.
3. Definitions are deterministic in order.
4. `parameters` uses camelCase aliases.
5. `additionalProperties: false` is preserved wherever emitted by the strict Pydantic model.
6. Required schema constants and required request fields remain visible.
7. No adapter-owned alternate argument shape is introduced.
8. Descriptions explain:

   * graph and revision scope;
   * when to use the operation;
   * that `read_source_anchor` accepts only graph-emitted opaque `anchorId`;
   * that graph misses are not invitations to search Markdown elsewhere.
9. Descriptions must not mention or advertise manifests, corpus indexes, lexical fallback, repository search, arbitrary files, breadcrumbs, or old tool names except to state that such fallback is unavailable.
10. Returned objects must be fresh copies or otherwise protected so caller mutation cannot alter later catalog reads.
11. The catalog must derive request schemas from the same Rung 1 registry metadata used for execution. A second hand-maintained name-to-model table in the adapter is prohibited.

### Serialization rules

1. Success values serialize with camelCase aliases.
2. `None` handling must match the existing PR010A response model rather than inventing a second omission policy.
3. Unicode content from admitted source excerpts is preserved.
4. The returned value is always a JSON string.
5. The adapter does not add prose outside the JSON value.
6. The adapter does not wrap successful retrieval results in a new success envelope.
7. The adapter does not replace PR010A error vocabulary with a plugin-specific error object.
8. Contract errors are mapped into the existing `WorldGraphRetrievalErrorResponse`.
9. Service errors preserve their existing code, status, and diagnostics.
10. An unexpected internal failure returns a generic message without filesystem paths, stack traces, secrets, prompts, or raw source bodies.

---

### §6A State and fallback matrix

| Observable path          | Loading or initializing                         | Exact success                                | Ordinary miss                                        | Dependency unavailable                                              | Integrity or contract failure                      | Stale or superseded                                               | Retry or replay          |
| ------------------------ | ----------------------------------------------- | -------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------- | ------------------------ |
| Tool catalog             | Build from current in-process registry metadata | Exactly five definitions                     | Not applicable; catalog is fixed                     | Import failure is an internal adapter failure; no alternate catalog | Fail closed; no partial legacy catalog             | Code version defines catalog; no persisted stale state            | Fresh equivalent catalog |
| Declared graph tool call | Validate before service invocation              | Serialize existing PR010A result             | Preserve PR010A `empty` or `partial` outcome         | Preserve PR010A `unavailable` or service error response             | Return stable error JSON; never raise to caller    | Revision behavior remains owned by PR010A request/result contract | Fresh read               |
| Unknown tool             | No lookup outside Rung 1 registry               | Not applicable                               | Return `unknown_tool`                                | No fallback                                                         | Fail closed                                        | Not applicable                                                    | Same stable error        |
| Invalid arguments        | Strict PR010A model validation                  | Not applicable                               | Return `invalid_arguments`                           | No fallback                                                         | Fail closed before service call                    | Not applicable                                                    | Revalidate from scratch  |
| Source-anchor read       | Validate opaque `anchorId` and request context  | Serialize existing source-anchor read result | Preserve existing empty/denied/unavailable semantics | Preserve service response                                           | Reject arbitrary path fields; no document fallback | Revision pin semantics remain PR010A-owned                        | Fresh read               |

**Fallback rule**

```text
No fallback source is permitted anywhere in this slice.
```

---

### §6B Identity matrix

This slice does not introduce graph identity semantics, but tool identity is exact and must be explicit.

| Situation            | Required matching rule                              | Ambiguity behavior                                                | Fallback permitted?        | Persistence consequence |
| -------------------- | --------------------------------------------------- | ----------------------------------------------------------------- | -------------------------- | ----------------------- |
| Exact tool name      | Exact case-sensitive key in the Rung 1 registry     | No ambiguity                                                      | No                         | None                    |
| Old Hermes tool name | Prohibited                                          | Return `unknown_tool`                                             | No                         | None                    |
| Alias or label       | Prohibited                                          | Return `unknown_tool`                                             | No                         | None                    |
| Normalized name      | Prohibited                                          | Do not lowercase, trim into another name, or normalize separators | No                         | None                    |
| Tool rename          | Requires a future explicit contract change          | Old name remains unknown unless separately authorized             | No                         | None                    |
| Graph node IDs       | Passed to PR010A unchanged after request validation | Existing PR010A behavior                                          | No adapter fallback        | None                    |
| Source anchor IDs    | Exact opaque `anchorId` only                        | Existing PR010A behavior                                          | No arbitrary path fallback | None                    |

First-win matching and compatibility aliases are prohibited.

---

### §6C Persistence and replay matrix

```text
Not applicable — this slice is a stateless in-process read adapter and creates no persisted format, session record, thread pointer, cache, event, or migration.
```

The catalog may be deterministically recomputed or held as immutable process data, but no durable cache or generated artifact may be added.

---

### §6D Predecessor-to-consumer mapping

**Grounding source**

```text
apps/live_control_server/services/hermes_graph_read_tools.py
src/graph_memory/retrieval/models.py
apps/live_control_server/services/world_graph_retrieval.py
```

| Predecessor field or outcome                                 | Real shape and optionality                                                                               | Consumer field or behavior          | Transformation                                        | Proof fixture or test                             |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ----------------------------------- | ----------------------------------------------------- | ------------------------------------------------- |
| `HERMES_GRAPH_READ_TOOL_NAMES`                               | Exact five-name frozen set                                                                               | Catalog names and executable names  | Preserve exactly                                      | Adapter catalog equality test                     |
| Rung 1 registry request model                                | One strict Pydantic request model per exact name                                                         | Function `parameters` schema        | Generate with aliases from the same registry metadata | Name-to-schema derivation test                    |
| Request `schema`                                             | Required literal alias `"schema"`                                                                        | Required model argument             | Preserve; do not inject or remove                     | Definition schema test plus invalid-argument test |
| `worldId`                                                    | Required non-empty string                                                                                | Model argument                      | Preserve exact key                                    | Definition and execution tests                    |
| `campaignId`                                                 | Required non-empty string                                                                                | Model argument                      | Preserve exact key                                    | Definition and execution tests                    |
| `focus`                                                      | Optional structured object with defaults and validation                                                  | Model argument                      | Preserve camelCase nested schema                      | Schema comparison test                            |
| `admissibility`                                              | Optional string with default                                                                             | Model argument                      | Preserve                                              | Schema comparison test                            |
| `revisionPin`                                                | Optional string or null                                                                                  | Model argument                      | Preserve                                              | Schema comparison test                            |
| Search `queryText`                                           | Required non-empty string                                                                                | Model argument                      | Preserve                                              | Search execution test                             |
| `seedNodeIds`                                                | Operation-dependent list                                                                                 | Model argument                      | Preserve exact constraints                            | Schema and invalid-argument tests                 |
| `nodeId`                                                     | Required object lookup ID                                                                                | Model argument                      | Preserve                                              | Catalog schema test                               |
| `target`                                                     | Required evidence target object                                                                          | Model argument                      | Preserve nested shape                                 | Catalog schema test                               |
| `anchorId`                                                   | Required opaque source anchor ID                                                                         | Model argument                      | Preserve; never translate to path                     | Catalog and forbidden-field tests                 |
| `WorldGraphRetrievalResult`                                  | Existing success model with operation, outcome, snapshot, objects, coverage, trust boundary, diagnostics | JSON tool result                    | Serialize by alias                                    | Parsed JSON equality test                         |
| `WorldGraphSourceAnchorReadResult`                           | Existing anchor-read model                                                                               | JSON tool result                    | Serialize by alias                                    | Anchor-read serialization test                    |
| `HermesGraphReadToolContractError(code="unknown_tool")`      | Pre-service exception                                                                                    | Existing retrieval-error JSON model | Map to code `unknown_tool`, status 404                | Unknown-tool test                                 |
| `HermesGraphReadToolContractError(code="invalid_arguments")` | Pre-service exception                                                                                    | Existing retrieval-error JSON model | Map to code `invalid_arguments`, status 400           | Invalid-arguments test                            |
| `WorldGraphRetrievalServiceError`                            | Stable code, status, diagnostics, `.response()`                                                          | Existing retrieval-error JSON model | Serialize `.response()` unchanged                     | Injected service-error test                       |
| PR010A outcomes                                              | `enough`, `partial`, `empty`, `denied`, `truncated`, `unavailable`                                       | Model-visible result outcome        | Preserve exactly                                      | Parameterized serialization test                  |

Invented substitute request fields or “close enough” fixtures are not acceptable proof.

---

## §7 Verification ownership map and commands

Every behavioral claim must be tested at the adapter boundary, not only through request-model or dispatcher unit tests.

| Guarantee                                                              | Owning boundary                         | Command or scenario                                        | Expected evidence                                                                                                    |
| ---------------------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Catalog contains exactly the five graph tools                          | Adapter                                 | Focused adapter test suite                                 | Exact name equality and deterministic order                                                                          |
| Catalog schemas derive from Rung 1 request-model metadata              | Adapter plus predecessor registry       | Focused adapter test suite                                 | No duplicate adapter name-to-model table; field-level schema assertions                                              |
| Catalog mutation cannot persist                                        | Adapter                                 | Focused adapter test suite                                 | Second catalog read is pristine                                                                                      |
| Successful search call returns PR010A JSON                             | Adapter invoking real Rung 1 dispatcher | Focused adapter test suite                                 | Parsed JSON has existing result schema, operation, outcome, aliases                                                  |
| Anchor read uses the existing distinct result model                    | Adapter                                 | Focused adapter test suite                                 | Parsed JSON has source-anchor read schema                                                                            |
| Unknown tools return stable error JSON                                 | Adapter                                 | Focused adapter test suite                                 | No exception; code/status match contract                                                                             |
| Invalid arguments fail before service invocation                       | Adapter plus Rung 1                     | Focused adapter test suite with service spy                | `invalid_arguments`; service call count remains zero                                                                 |
| Service failures preserve existing error response                      | Adapter                                 | Focused adapter test suite with injected service error     | Code, status, diagnostics unchanged                                                                                  |
| Unexpected adapter errors fail closed                                  | Adapter                                 | Focused adapter failure-injection test                     | Generic 500 error JSON; no traceback/path leak                                                                       |
| Forbidden legacy fields are rejected                                   | Adapter plus strict request models      | Focused adapter test suite                                 | Manifest/path/corpus/breadcrumb fields produce `invalid_arguments`                                                   |
| No legacy retrieval dependency exists                                  | Source boundary                         | AST/import and literal assertions in focused adapter tests | No imports or calls into plugin, manifest, corpus, Markdown search, lexical, breadcrumb, CLI, model, or session code |
| Rung 1 behavior is not regressed                                       | Predecessor dispatcher                  | Existing Rung 1 test suite                                 | Existing 44-test suite remains green or exact current count reported                                                 |
| PR010A retrieval remains green apart from known baseline fixture drift | Kernel/service/route                    | Existing predecessor suite                                 | No new failures relative to base                                                                                     |
| Tracker and roadmap describe the same rung sequence                    | Documentation inspection                | Diff review                                                | Rung 1 done, Rung 2 active, Rung 3 next in both documents                                                            |
| No unexpected file changed                                             | Repository diff                         | Changed-path commands                                      | Only §4 paths                                                                                                        |

### Required commands

Run and report exact output for:

```bash
uv run pytest -q tests/test_hermes_graph_read_tool_adapter.py
```

```bash
uv run pytest -q tests/test_hermes_graph_read_tools.py
```

```bash
uv run pytest -q \
  tests/test_graph_kernel_world_retrieval.py \
  tests/test_world_graph_retrieval_routes.py \
  tests/test_graph_kernel_public_api.py \
  tests/test_graph_kernel_boundaries.py \
  --deselect tests/test_world_graph_retrieval_routes.py::test_api_contract_fixture_matches_real_generated_operations
```

Run the known baseline test on the implementation head:

```bash
uv run pytest -q \
  tests/test_world_graph_retrieval_routes.py::test_api_contract_fixture_matches_real_generated_operations
```

Run the same exact baseline test at base revision `55fd41171ab91e0dd8a707bf63ad763326b15c3b` and record the base/head comparison. Do not update `tests/fixtures/world_graph_retrieval/api-contract-v1.json`; it is outside the allowlist.

Run lint:

```bash
uv run ruff check \
  apps/live_control_server/services/hermes_graph_read_tools.py \
  apps/live_control_server/services/hermes_graph_read_tool_adapter.py \
  tests/test_hermes_graph_read_tool_adapter.py
```

Run repository diff checks:

```bash
git diff --check
```

```bash
git diff --stat 55fd41171ab91e0dd8a707bf63ad763326b15c3b...HEAD -- \
  apps/live_control_server/services/hermes_graph_read_tools.py \
  apps/live_control_server/services/hermes_graph_read_tool_adapter.py \
  tests/test_hermes_graph_read_tool_adapter.py \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md
```

```bash
git diff --name-only 55fd41171ab91e0dd8a707bf63ad763326b15c3b...HEAD
```

### Minimal live proof

```text
Not applicable — this slice deliberately contains no LLM, Hermes session, route, UI, plugin registration, or product execution path. A live proof would require implementing the named Rung 3 successor.
```

### Baseline failure protocol

The PR010A contract-fixture test was reported failing identically on the predecessor base and PR #350 head because the checked-in JSON Schema fixture uses older serialization details.

The worker must independently rerun the exact test on this slice’s base and head.

Required evidence table:

| Command                                                                                                                    | Base result         | Head result         | New failure introduced? | Acceptance effect                                                      | Waiver                         |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------- | ------------------- | ----------------------: | ---------------------------------------------------------------------- | ------------------------------ |
| `uv run pytest -q tests/test_world_graph_retrieval_routes.py::test_api_contract_fixture_matches_real_generated_operations` | Record exact result | Record exact result |                Yes / No | Block if behavior differs; otherwise explicit baseline waiver required | Name operator waiver or `none` |

Do not call the full predecessor gate green while this test fails. State that the deselected suite is green and the baseline test remains failing identically only if the evidence proves that statement.

---

## §8 Required implementation handback

The pull-request body or implementation handback must include:

1. Implementation base SHA: `55fd41171ab91e0dd8a707bf63ad763326b15c3b`.
2. Head SHA.
3. Actual changed paths.
4. Focused diff stat limited to §4.
5. Every §7 command and exact result.
6. Provenance for every result:

   * author-local;
   * independently rerun local;
   * CI;
   * manual inspection.
7. Exact catalog names and exported adapter entry points.
8. Confirmation that tool schemas derive from the same Rung 1 registry metadata used for execution.
9. Confirmation that successful outputs are existing PR010A result models serialized by alias.
10. Confirmation that errors use the existing `WorldGraphRetrievalErrorResponse`.
11. Confirmation that no model, session, route, UI, plugin registration, CLI invocation, persistence, or product backend was added.
12. Confirmation that no manifest, corpus, Markdown, arbitrary-path, lexical, breadcrumb, or compatibility retrieval dependency was added.
13. Baseline failure base/head comparison.
14. Explicit operator waivers; write `none` when none exist.
15. Paths outside §4; write `none` or include a stop report.
16. Stop conditions encountered and resolution; write `none` when none exist.
17. Deviations from §6 matrices; write `none` when none exist.
18. Named successor capabilities deferred and still false.
19. Confirmation that no successor is claimed as delivered.
20. Confirmation that the complete authoritative handoff was implemented without omitted constraints.
21. Confirmation that opening the pull request was the final repository action for the branch.

### Required retain / rewrite / delete statement

Include this shape in the handback:

```text
Retained unchanged:
- Transitional Hermes plugin and legacy tool registrations
- live_agent_loop.py product paths
- one-shot CLI backend
- Live/Hermes product toggle

Reason:
- This rung creates only the reusable model-facing catalog and adapter.
- No replacement product path exists yet.

Remaining consumers:
- Existing transitional Plan/Hermes spike tests and product paths.

Required successor:
- PR010B Rung 3 creates the real in-process Hermes agent/session loop.
- Later PR010B replacement work wires the product path and deletes obsolete
  retrieval tools and backends at replacement time.
```

---

## §9 Acceptance rubric

The reviewer accepts only when every item is true.

* [ ] Exactly one independently useful capability was delivered: the model-facing graph-read catalog and JSON-string adapter — proved by `tests/test_hermes_graph_read_tool_adapter.py` and diff inspection.
* [ ] Every changed runtime layer establishes or proves the invariant — proved by the focused adapter suite and source-boundary inspection.
* [ ] Exactly five tools are advertised, with names equal to `HERMES_GRAPH_READ_TOOL_NAMES` — proved by the focused adapter suite.
* [ ] Catalog schemas derive from the same Rung 1 registry metadata used for execution, not from a second adapter-owned name-to-model map — proved by source inspection and schema-derivation tests.
* [ ] Returned definitions use camelCase PR010A request vocabulary and preserve strict request constraints — proved by schema assertions in the focused adapter suite.
* [ ] Caller mutation cannot corrupt later catalog reads — proved by the catalog-isolation test.
* [ ] A successful graph call returns an existing PR010A result shape serialized as JSON with aliases — proved by a real adapter-to-dispatcher integration test.
* [ ] A successful source-anchor read returns the existing source-anchor result shape, not a new wrapper contract — proved by the focused adapter suite.
* [ ] Unknown tools return stable `WorldGraphRetrievalErrorResponse` JSON and do not raise — proved by the unknown-tool adapter test.
* [ ] Invalid arguments return stable error JSON before any service operation runs — proved by the invalid-arguments service-spy test.
* [ ] Existing service errors preserve their code, status, and diagnostics — proved by the injected service-error test.
* [ ] Unexpected adapter failures return generic fail-closed error JSON without leaking paths, tracebacks, source bodies, prompts, or secrets — proved by failure injection.
* [ ] Manifest, corpus, Markdown, arbitrary-path, lexical, breadcrumb, legacy-tool, and compatibility fields are rejected or absent — proved by forbidden-field and AST/import tests.
* [ ] No LLM, Hermes session, thread binding, route, UI, plugin registration, CLI invocation, persistence, or product replacement was added — proved by §4 diff inspection.
* [ ] No second public retrieval contract was introduced; outputs remain the existing PR010A success/error models — proved by contract inspection and tests.
* [ ] State and fallback behavior follows §6A, including the rule that no fallback exists — proved by focused failure tests.
* [ ] Tool identity follows §6B with exact case-sensitive names and no aliases or normalization — proved by parameterized unknown-name tests.
* [ ] Persistence is absent as declared in §6C — proved by diff inspection.
* [ ] Predecessor vocabulary and shapes follow §6D — proved by schema derivation and parsed-result tests.
* [ ] Rung 1 remains green — proved by `uv run pytest -q tests/test_hermes_graph_read_tools.py`.
* [ ] The predecessor retrieval suite introduces no new failures beyond the independently confirmed baseline fixture drift — proved by the deselected suite and base/head comparison.
* [ ] Tracker and roadmap agree that Rung 1 is done, this adapter is Rung 2, and the real agent/session loop is Rung 3 — proved by documentation diff review.
* [ ] No unexpected path changed — proved by `git diff --name-only 55fd41171ab91e0dd8a707bf63ad763326b15c3b...HEAD`.
* [ ] Baseline failures and waivers are reported truthfully.
* [ ] Local, CI, and manual evidence provenance is distinguished.
* [ ] The real Hermes agent/session loop remains unimplemented and unclaimed.
* [ ] Product wiring and obsolete-path demolition remain unimplemented and unclaimed.
* [ ] The complete authoritative handoff survived dispatch without omitted constraints.

---

## §10 Reviewer protocol

Review the invariant before reviewing individual code.

1. Confirm the diff is based on `55fd41171ab91e0dd8a707bf63ad763326b15c3b`.
2. Restate the mission: model-facing definitions plus JSON adapter, not an agent loop.
3. Compare the actual diff against §4 and reject any unlisted path.
4. Inspect `hermes_graph_read_tools.py` first:

   * metadata exposure must be minimal;
   * execution must still use one registry and one dispatcher;
   * no model, plugin, or compatibility behavior may enter Rung 1.
5. Inspect the adapter:

   * catalog derives from Rung 1 metadata;
   * exact names only;
   * strict aliases and schema constraints;
   * no second retrieval implementation;
   * no fallback imports;
   * always returns JSON strings.
6. Verify every error branch at the adapter boundary.
7. Verify service invocation cannot occur after request validation fails.
8. Verify returned catalog objects cannot mutate process-global state.
9. Verify the adapter does not translate an easier model request shape into PR010A.
10. Search the diff for:

    * `manifest`
    * `corpus`
    * `markdown`
    * `breadcrumb`
    * `dungeon_search`
    * `dungeon_context_lookup`
    * `dungeon_manifest_index`
    * `dungeon_get_document`
    * `subprocess`
    * `--oneshot`
    * session or model imports
11. Distinguish comments that prohibit legacy behavior from code that imports or enables it.
12. Rerun every §7 command independently.
13. Compare the known baseline fixture test on base and head.
14. Confirm tracker and roadmap now express the same decomposition.
15. Confirm the named Rung 3 successor is still necessary and false.

A large generated schema is not itself a scope violation if it is produced from the predecessor model at runtime. A new checked-in schema fixture is outside scope.

---

## §11 Re-review protocol

Begin any re-review from the prior finding ledger.

| Prior finding | Claimed fix            | Owning files or tests | Verified? | New consequence?        |
| ------------- | ---------------------- | --------------------- | --------: | ----------------------- |
| `<finding>`   | `<claimed resolution>` | `<paths/tests>`       |  Yes / No | `<none or consequence>` |

For every prior finding:

1. Verify the literal fix.
2. Rerun the full focused adapter suite.
3. Recheck all error branches, not only the branch changed.
4. Recheck the catalog/dispatcher shared-source invariant.
5. Recheck the §4 allowlist.
6. Recheck that no compatibility translation or legacy fallback was introduced while fixing the issue.
7. Recheck tracker/roadmap agreement if documentation changed.
8. Add any new consequence to the ledger.

Do not approve a re-review solely because the reported failing test now passes.

---

## Stop conditions

Stop and report rather than expanding scope if implementation discovers:

* Rung 1 does not expose enough metadata to derive schemas without redesigning its dispatcher contract;
* the real Hermes runtime requires a materially different tool-definition format than the documented OpenAI function shape;
* a provider-specific schema normalization requires a new dependency, generated fixture, or second independently useful compatibility layer;
* PR010A request schemas cannot be presented directly without inventing a translated model request contract;
* errors cannot be represented honestly through the existing `WorldGraphRetrievalErrorResponse`;
* a model or Hermes session must be instantiated to prove the adapter;
* a route, UI, plugin, or product path must change for the capability to be useful;
* a second public/durable contract emerges;
* a required file falls outside §4;
* `main` or another open PR materially changes an allowlisted path;
* the baseline fixture failure differs between base and head;
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
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently adding a provider shim, request translator, plugin migration, session loop, dependency, fixture regeneration, or product route.

---

## Final dispatch check

Before dispatching, confirm:

* [ ] This handoff is checked into `Docs/Plans/HANDOFF-pr351-hermes-graph-read-model-adapter.md`.
* [ ] The implementation base is still `55fd41171ab91e0dd8a707bf63ad763326b15c3b`.
* [ ] No open PR now overlaps an allowlisted runtime or authority path.
* [ ] §0 records the split between model adapter and real agent/session loop.
* [ ] §1 contains one invariant reused throughout the document.
* [ ] §3 inventories catalog, success, miss, service failure, contract failure, mutation, and retry behavior.
* [ ] §4 expresses the complete expected diff.
* [ ] §5 names every tempting product-path expansion.
* [ ] Every §6 matrix is completed or explicitly marked not applicable.
* [ ] §6D uses the actual PR010A and Rung 1 vocabulary.
* [ ] Every §9 behavioral guarantee maps to an owning-boundary §7 proof.
* [ ] The known baseline failure protocol is executable.
* [ ] No essential requirement exists only in chat or the PR summary.
* [ ] The worker is instructed that opening the PR is the final repository action.
