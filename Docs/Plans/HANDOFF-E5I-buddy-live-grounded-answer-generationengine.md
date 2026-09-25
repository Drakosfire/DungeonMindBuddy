# E5I — Buddy live grounded answer through GenerationEngine

**Status:** MERGED — Buddy PR #748 at `3f1aa1baf9a72c16adf747ad5bf81e9e8b249a6a`
**Flow:** E5I
**Architecture owner:** `Drakosfire/DungeonOverMind`
**Execution repository:** `Drakosfire/DungeonMindBuddy`
**Canonical design:** DungeonOverMind `Docs/Plans/HANDOFF-E5I-buddy-live-grounded-answer-generationengine.md` at `639536912e78a07c6246528aae70e1f953785d0b`
**Activation base:** `99b8d431d6558f4d6028c736d41ebaa97af84ca5`
**Implementation branch base:** `1de19d3b7dc83c5ef536ae36588706e47dafb6d5`
**Accepted GE authority:** E5H PR #8 merge `f502c9883013d3ec9b866ca9276dfd7def141599`
**Predecessor:** E5G Buddy PR #746 merge `9510a6dbdfde52917e249710724a35c089410f68`
**PR topology:** `serial`
**Assigned branch:** `codex/e5i-live-grounded-answer-generationengine`
**Assigned PR title:** `E5I: migrate live grounded answering through GenerationEngine`
**Final reviewed head:** `e803d09c4323acc7ec72bf6a6f2de32d24bb537b`
**Review cycles:** 2
**Accepted evidence:** focused E5I 39 passed; E5C–E5G regression 218 passed / 36 deselected; exact E5H pin; lock/sync/Ruff/diff-check green

## §1 Mission and invariant

Migrate exactly `src/live_play/live_query_context.py::_run_llm_grounded_answer`
from direct OpenAI Responses execution to ordinary
`GenerationEngine.generate_text()` and deliberately advance Buddy's GE pin from
`80288d7b...` to accepted E5H merge `f502c988...`.

Buddy retains credential preflight, deterministic fallback, exact prompt/model,
the exact 400-token ceiling, warning categories, citation validation, and
read-only live-query semantics. GE executes the explicit request. No other
consumer moves.

## §2 Re-anchor, lane, and topology

Re-anchor on 2026-09-24 established:

- Buddy `origin/main` is `99b8d431...`, a descendant of E5G merge `9510a6db...`;
- PR #747 merged at `99b8d431...`; its dependency edits are now the base and it
  changed only the DungeonMind pin, not the GE pin or E5I code/tests;
- open PR #745 is documentation/authoring authority and disjoint;
- Buddy still pins GE `80288d7b...`;
- E5H merge `f502c988...` is the accepted new GE pin.

Topology is `serial`. Open only the assigned E5I PR. No successor, cleanup,
telemetry-eval migration, or second consumer PR is authorized.

| Field | Required content |
|---|---|
| Implementation branch base | `1de19d3b7dc83c5ef536ae36588706e47dafb6d5` |
| Branch / checkout | `codex/e5i-live-grounded-answer-generationengine` / isolated worktree |
| Runtime/state ownership | injected/local GE fakes and temporary stores only; no paid provider, shared service, or external durable state |
| Concurrent lanes checked | PR #745 disjoint; PR #747 merged before activation |
| State-authority sync after merge | Buddy E5I completion record; DungeonOverMind E5I completion record; ecosystem roadmap/direct-provider census |

## §3 Observable paths and adversarial sequences

- Missing API key returns `(None, [])`, constructs no GE client, and falls back silently.
- `CONFIGURATION_UNAVAILABLE` maps exactly to `llm_client_unavailable` and fallback.
- Other normalized GE/provider failures map to `llm_grounding_call_failed[:safe detail]` and fallback.
- Empty/whitespace GE text maps to `llm_empty_answer_fallback_used` and fallback.
- Successful stripped text flows through unchanged citation validation and read-only response construction.
- Active-event-loop invocation remains safe through `run_awaitable_sync`.
- Production `GenerationClient.from_env()` is constructed inside the awaited bridge coroutine and is not cached.

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/live_play/live_query_context.py` | migrate exactly grounded-answer execution to GE |
| Modify | `tests/test_live_query_manifest_context.py` | request, lifecycle, warning, fallback, citation, and loop witnesses |
| Modify | `tests/test_e5a_boundary_fitness.py` | move exactly live query from direct-provider debt to GE inventory |
| Modify | `pyproject.toml` | pin accepted E5H merge |
| Modify | `uv.lock` | resolve exact accepted E5H merge |

## §5 Explicitly out of scope / collision boundary

| Action | Path | Reason |
|---|---|---|
| Do not modify | `src/llm/generation_sync.py` | reuse the accepted mechanics-only bridge |
| Do not modify | `src/agent/synthesis.py` | E5G consumer is regression-only here |
| Do not modify | `MODEL_POLICY.json` | Buddy model policy remains authoritative |
| Do not modify | `src/agent/document_planner.py` | separate consumer/design decision |
| Do not modify | `src/agent/planner.py` | separate consumer |
| Do not modify | `src/llm/api_client.py` | other direct consumers remain |
| Do not modify | `evals/c2_live_prep/run_live_query_telemetry_trace.py` | bounded eval remains direct-provider and imports `_extract_answer_text` |

GenerationEngine source and all other consumer repositories are out of scope.

## §6 Implementation contract

Build the exact request:

```python
TextRequest(
    user_prompt=prompt,
    system_prompt=None,
    provider="openai",
    model=model,
    profile=None,
    temperature=None,
    max_output_tokens=400,
)
```

Use ordinary `generate_text`. Construct `GenerationClient.from_env()` inside
the coroutine passed to `run_awaitable_sync`. Do not cache clients, add a new
bridge, add a schema/deadline/system prompt, or move prompt/model/fallback policy
into GE.

Keep the initial `_load_api_key()` preflight. Missing credentials remain silent
and must prevent GE construction. Map only `GenerationEngineError` with
`FailureCode.CONFIGURATION_UNAVAILABLE` to `llm_client_unavailable`; other GE
errors use their normalized safe public message in the existing call-failed
warning category. Unexpected errors retain existing warning shaping.

Keep `_extract_answer_text()` because the telemetry eval imports it. Do not add
GE observations to response/provenance/warnings/citations/storage.

Pin `generationengine[openai]` in both `pyproject.toml` and `uv.lock` exactly to
`f502c9883013d3ec9b866ca9276dfd7def141599`. Keep direct `openai==2.24.0` and
all unrelated dependency changes from merged PR #747.

E5A removes exactly `("src/live_play/live_query_context.py", "openai")` and
adds exactly `("src/live_play/live_query_context.py", "generationengine")`.

## §7 Evidence required to merge

```bash
uv lock --check
uv sync
uv run python -c "import generationengine; print(generationengine.__version__); print(generationengine.__file__)"
uv run ruff check src/live_play/live_query_context.py tests/test_live_query_manifest_context.py tests/test_e5a_boundary_fitness.py tests/test_model_policy_authority.py
uv run pytest -q tests/test_live_query_manifest_context.py tests/test_e5a_boundary_fitness.py tests/test_model_policy_authority.py tests/test_generation_sync.py
git diff --check
git diff --name-only 1de19d3b7dc83c5ef536ae36588706e47dafb6d5...HEAD
```

Also run and record the exact final-head E5C–E5G regression union under the new
pin, including live-turn classification, generation sync, NPC intent/skill,
frontmatter inference, wiki compiler, synthesis, E5A/model-policy authority,
and relevant CLI coverage. No paid-provider call is required.

## §8 Required review handback

Return PR/base/head, ancestry and lease checks, exact old/new pins and lock
proof, changed paths, captured request, current/alternate model and exact prompt
witnesses, every fallback/warning/lifecycle/citation/read-only witness, helper
and eval compatibility, exact census movement, focused and E5C–E5G regression
counts, lock/sync/import/lint/diff results, and stop conditions (`none` if none).

## §9 Merge-blocking acceptance rubric

- Exact five-path lease and no concurrent overlap.
- Pin changes only from `80288d7b...` to `f502c988...` with no incidental lock churn.
- Exact prompt/provider/model/profile/temperature/400-token/no-schema request.
- Missing key causes zero GE construction/calls and no warning.
- Configuration, provider failure, and empty-output warnings/fallbacks remain exact and safe.
- Sync and active-loop paths use the existing bridge with construction inside the awaited context and no cache.
- Citation, provenance, read-only, mutation, and deterministic fallback behavior remain unchanged.
- `_extract_answer_text` and telemetry eval remain intact.
- No GE observation or second consumer enters product output/scope.
- E5A movement is exact and E5C–E5G regressions pass under the new pin.
