# E5G — Buddy retrieval synthesis through GenerationEngine

**Status:** MERGED — Buddy PR #746 at `9510a6dbdfde52917e249710724a35c089410f68`
**Flow:** E5G
**Architecture owner:** `Drakosfire/DungeonOverMind`
**Execution repository:** `Drakosfire/DungeonMindBuddy`
**Canonical design:** DungeonOverMind `Docs/Plans/HANDOFF-E5G-buddy-retrieval-synthesis-generationengine.md` at `705bb09e65858df1b046cce9db59eb7820478139`
**Design authority base:** `a9495fa0f14a31461de8aa60ed7fc0ad85697a40`
**Activation base:** `a9495fa0f14a31461de8aa60ed7fc0ad85697a40`
**Implementation branch base:** `26856027e36a9a66248259a01519d6378b56b795`
**Predecessor:** E5F, Buddy PR #743 merged at `a9495fa0f14a31461de8aa60ed7fc0ad85697a40`
**PR topology:** `serial`
**Assigned branch:** `codex/e5g-retrieval-synthesis-generationengine`
**Branch / checkout:** `codex/e5g-retrieval-synthesis-generationengine` / isolated worktree from `origin/main`
**Assigned PR title:** `E5G: migrate retrieval synthesis through GenerationEngine`
**Final reviewed head:** `30408200bf839855ae1aa223b466b44420acb1e2`
**Review cycles:** 2
**Accepted evidence:** focused E5G 40 passed; adjacent E5C–E5F 193 passed / 36 deselected; lock/sync/import/Ruff/diff-check green

## 1. Mission

Migrate exactly `src/agent/synthesis.py::synthesize_answer_async` from direct
OpenAI Chat Completions execution through `DungeonMindApiClient` to ordinary
`GenerationEngine.generate_text()` execution.

Buddy retains ownership of one-step versus two-step orchestration, retrieval
context, every prompt and prompt mode, model resolution, extracted-claim
sequencing, `synthesis_meta_out`, credential behavior, empty-output validation,
and interpretation of returned text. GenerationEngine executes the explicit
ordinary-text requests Buddy constructs.

No other inference consumer moves in this slice.

## 2. Activation and topology

Re-anchor on 2026-09-23 established:

- Buddy `origin/main` is exactly the E5F merge `a9495fa0...`;
- E5F ancestry is therefore direct;
- DungeonOverMind `origin/main` is the synchronized roadmap commit `f5740a2...`;
- the only open Buddy PR is #745, whose documentation/authoring paths do not
  overlap this lease;
- the accepted GE pin remains `80288d7b467ac3c3586f4e3c964385cefe69f931`.

Topology is `serial`. Open only the assigned E5G PR. A successor, cleanup,
repair, or E5H PR is not authorized by this handoff.

| Field | Required content |
|---|---|
| Implementation branch base | `26856027e36a9a66248259a01519d6378b56b795` |
| Branch / checkout | `codex/e5g-retrieval-synthesis-generationengine` / isolated worktree from `origin/main` |
| PR topology | `serial` |
| Authorized PR action | open and update only the assigned E5G implementation PR |
| Concurrent lanes checked | PR #745 is documentation/authoring authority with no lease overlap |
| Runtime/state ownership | injected/local test doubles only; no live provider call, shared service, durable external state, or port ownership |
| State-authority sync set after merge | Buddy E5G completion record; DungeonOverMind E5G completion record; DungeonOverMind ecosystem roadmap and direct-provider re-census |

## §3 Observable paths and adversarial sequences

The observable paths and failure sequences are defined by §§4–8 below and by
the immutable canonical design. Each must be proven at `synthesize_answer_async`
or the existing synchronous wrapper rather than only at a request helper.

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/agent/synthesis.py` | migrate exactly synthesis provider execution and response parsing to GE |
| Modify | `tests/test_synthesis.py` | own request, prompt, model, lifecycle, metadata, and failure witnesses |
| Modify | `tests/test_e5a_boundary_fitness.py` | move exactly synthesis from direct-provider debt to GE inventory |

## §5 Explicitly out of scope / collision boundary

| Action | Path | Reason |
|---|---|---|
| Do not modify | `src/cli.py` | CLI product behavior remains unchanged |
| Do not modify | `src/llm/api_client.py` | still-direct consumers own this compatibility wrapper |
| Do not modify | `src/llm/generation_sync.py` | native-async synthesis needs no sync bridge |
| Do not modify | `src/live_play/live_query_context.py` | live grounded answering requires a separate GE contract decision |
| Do not modify | `src/agent/document_planner.py` | JSON-object/fallback planning semantics require separate design |
| Do not modify | `src/agent/planner.py` | separate direct-provider consumer and `_load_api_key` dependent |
| Do not modify | `MODEL_POLICY.json` | model choice remains existing Buddy policy |
| Do not modify | `pyproject.toml` | accepted dependency authority is already present |
| Do not modify | `uv.lock` | GE pin must remain exact |

Verify but normally do not edit:

```text
tests/test_model_policy_authority.py
src/cli.py
src/agent/planner.py
src/live_play/live_query_context.py
src/live_play/classify_live_turn.py
src/npc_statblock_pipeline/canonical_intent.py
```

Do not edit dependency files, model policy, GE source/configuration, the shared
sync bridge, provider wrapper, live grounded answering, document planning,
planner/tool loops, extraction, Batch/repair, graph inference, or WorldKeeper
work. A required production change outside the three leased paths is a STOP.

## 4. Required runtime contract

Every synthesis inference request is an ordinary text request with:

```python
TextRequest(
    system_prompt=buddy_owned_system_prompt,
    user_prompt=buddy_owned_user_prompt,
    provider="openai",
    model=buddy_resolved_model,
    profile=None,
    temperature=None,
)
```

`temperature=None` is merge-blocking. Omitting it would make the accepted GE
compatibility default `0.7` explicit and change current provider-default
sampling behavior.

One-step mode performs one `generate_text` call. Two-step mode performs, in
order:

```text
GE extraction request
→ Buddy validates non-empty extracted text
→ Buddy writes existing extraction metadata
→ GE answer request
→ Buddy validates non-empty final text
```

Both two-step requests use the same exact Buddy-selected model and one
invocation-local `GenerationClient`. Product orchestration is not a GE retry,
profile, workflow, repair, or conformance feature.

## 5. Lifecycle and injection

`synthesize_answer_async` is natively async. Do not use `run_awaitable_sync` or
add another bridge.

When no client is injected, preserve the exact credential preflight:

```text
missing OPENAI_API_KEY
→ RuntimeError("OPENAI_API_KEY is required for synthesis.")
→ no GenerationClient construction
```

Then construct `GenerationClient.from_env()` inside the running coroutine,
once per synthesis operation. Reuse it only for the two sequential calls of
that same invocation. Do not cache it across invocations, threads, or loops.

Replace the test-only OpenAI-shaped `openai_client=` seam with a GE-shaped
`generation_client=` seam exposing async `generate_text(TextRequest)`. An
injected client bypasses real credential and provider construction.

Keep `_load_api_key()` present and behaviorally unchanged because still-direct
consumers import it. Keep the sync `synthesize_answer` wrapper as
`asyncio.run(synthesize_answer_async(...))`.

## 6. Behavior frozen by the migration

Preserve without prompt tuning or cleanup:

- explicit model passthrough and Buddy model-policy resolution;
- current default model witness `gpt-5.3-chat-latest` as Buddy policy, not GE policy;
- `provider="openai"`, `profile=None`, and no schema on every request;
- `_resolve_synthesis_profile`, `_resolve_verbosity`, `_env_truthy`,
  `_resolved_system_prompt`, `SYSTEM_PROMPT`, `SYSTEM_PROMPT_WIKI`,
  `EXTRACTION_PROMPT`, citation/profile appendices, and all current user prompts;
- one-step/two-step selection and call order;
- exact empty-extraction and empty-answer exceptions;
- GE/provider failure propagation with no Buddy retry or fallback;
- no GE observation data in `synthesis_meta_out`, CLI metadata, returned prose,
  or durable storage.

Metadata mutation timing is part of the contract:

- one-step writes `two_step=False` before answer inference;
- extraction failure or empty extraction writes no successful extraction metadata;
- successful extraction writes `two_step=True` and exact `extracted_claims`
  before answer inference;
- if that answer inference fails, those already-written values remain.

Remove synthesis-local OpenAI/AsyncOpenAI construction,
`DungeonMindApiClient` execution, chat-completion sync/async branching,
`choices[0].message.content` parsing, list-content normalization, and
`_extract_response_text` if nothing synthesis-local still needs them.

## 7. Boundary census movement

In `tests/test_e5a_boundary_fitness.py`, remove exactly:

```python
("src/agent/synthesis.py", "openai")
```

and add exactly:

```python
("src/agent/synthesis.py", "generationengine")
```

All other direct-provider and GE-consumer tuples remain unchanged.

## §9 Merge-blocking acceptance rubric

Tests at the owning boundary must prove:

- Exact one-step `TextRequest`, including `temperature is None` and no schema.
- Explicit alternate model and current Buddy default model parity.
- Default, wiki, citation, verbosity, and synthesis-profile prompt parity.
- Exact two-step extraction then answer request sequence and prompts.
- Same provider/model/profile/temperature contract for both calls.
- Successful metadata values and all failure-time mutation semantics.
- Empty extraction stops before the answer request.
- Empty answer raises the existing synthesis error.
- Original GE failures propagate with no Buddy retry/fallback.
- Injected GE client bypasses credentials and production construction.
- Production construction occurs inside the running coroutine.
- One client per invocation, reused for same-loop two-step calls, with no cross-invocation cache.
- `_load_api_key` compatibility and unchanged sync wrapper behavior.
- Source no longer owns OpenAI/wrapper/chat-response mechanics.
- Boundary census moves by exactly one tuple in each direction.

## §7 Evidence required to merge

Run on the final PR head:

```bash
uv lock --check
uv sync
uv run python -c "import generationengine; print(generationengine.__version__)"
uv run ruff check src/agent/synthesis.py tests/test_synthesis.py tests/test_e5a_boundary_fitness.py tests/test_model_policy_authority.py
uv run pytest -q tests/test_synthesis.py tests/test_e5a_boundary_fitness.py tests/test_model_policy_authority.py
git diff --check
git diff --name-only 26856027e36a9a66248259a01519d6378b56b795...HEAD
```

Also run and record exact existing CLI synthesis nodes for ordinary ask,
two-step synthesis, synthesis metadata, and existing wiki/citation/profile
flags where present.

Run and record the exact adjacent E5C–E5F regression union covering live-turn
classification, generation sync, NPC intent/skill pipeline, frontmatter
inference, wiki compiler, E5A fitness, and model-policy authority. No paid live
provider call is required.

## 10. Stop conditions

Stop rather than widening scope if current code has materially changed the
synthesis prompts/modes/metadata/model contract; a concurrent lane overlaps a
leased path; accepted GE cannot preserve `temperature=None`; a provider option
is now inexpressible; a real production/eval caller injects the old OpenAI seam;
CLI/product changes outside the lease are required; `_load_api_key` cannot
remain compatible; or model/provider policy must change.

## 11. Backward-looking state-authority sync after merge

After E5G merges and its facts are knowable, synchronize as one guarded steward
transaction before dispatching a successor:

- this Buddy handoff: mark E5G merged and record PR number, exact merge SHA,
  final reviewed head, review-cycle count, and accepted evidence;
- DungeonOverMind canonical E5G handoff: mark merged with the same facts;
- DungeonOverMind ecosystem roadmap: record E5G merged/closed and the result of
  the required post-E5G direct-provider re-census;
- any active E5 sequencing/status authority that still claims E5G is READY or
  in flight.

Do not preselect or pre-authorize E5H. The re-census must decide whether the next
slice is an already-expressible Buddy consumer or a prerequisite GE contract
extension such as output-token limits.

## §8 Required review handback

Return the PR URL, branch, exact base/head, E5F ancestry, GE pin, lease check,
changed paths, captured one-step/two-step requests, lifecycle/credential/error/
metadata witnesses, exact census movement, focused and adjacent regression
commands/results, CLI node results, lock/sync/import/lint/diff evidence, and
stop conditions encountered (`none` if none).
