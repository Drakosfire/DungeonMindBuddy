# HANDOFF — INGEST: GE-backed bounded DeepSeek recap client

**Status:** IMPLEMENTED — awaiting independent PRIME review; no provider execution or publication
**Authority:** `/tmp/HANDOFF-INGEST-ge-deepseek-bounded-client-activation.json` (SHA256 `bacb69bc58c3216e782651b4eef55df91d9a40fa145830b28a2da27cd734c448`)
**Buddy base:** `62417c6664a3625505bd7775c3c14de224b612dd`
**GenerationEngine prerequisite:** merged `38d77f33d0e45b3be02459f43add560c2ca2ff8a`
**Branch:** `codex/ge-deepseek-bounded-client`
**Topology:** independent PR; PRIME reviews the exact cumulative head before merge.

## One capability

The existing bounded recap pass client can select the accepted DeepSeek V4.1 Flash transport through GenerationEngine's OpenRouter provider. It preserves the current recap extraction profile, prompt construction, source/identity handling, and GraphIngestRun packaging. It does not invoke the provider in this slice.

The DeepSeek selection is exact: `provider=openrouter`, `model=deepseek/deepseek-v4.1-flash`, `ProviderRoute(order=("DeepSeek",), allow_fallbacks=False)`, reasoning disabled, JSON-object transport, existing pass schema in instructions with local validation, zero retries or repair calls. Existing explicit Luna/OpenAI selection remains supported. Both selections retain at most eight calls, 60 seconds per call, 480 seconds per run, and 8192 output tokens per call.

Requested route is recorded as policy; the GenerationEngine observation does not prove which upstream OpenRouter endpoint served the request. Unknown provider cost stays `null`, never zero or a fabricated charge. No credential, prompt, or source text enters the inference ledger.

## Exclusive changed-path lease

1. `pyproject.toml`
2. `uv.lock`
3. `src/graph_memory/extraction/bounded_recap_execution.py`
4. `tests/test_bounded_recap_execution.py`
5. This handoff

The existing `apps/live_control_server/services/graph_preview_runner.py` bounded-client injection is read-only. Any essential sixth path requires PRIME rebrief before editing. Preserve the current DungeonMind/Core pin. Buddy PR #763's dependency lease is suspended; PRIME suspended the stale draft #826 dependency lease for this GE adoption. Both must re-anchor before resuming their own dependency edits.

## Proof and stop lines

Fake GenerationEngine tests must prove exact request shape, one-attempt limits, local JSON/schema failure stopping before a second pass, credential non-disclosure, truthful observation/unknown-cost ledger, and unchanged explicit OpenAI behavior. Run focused tests, inspect the cumulative diff, commit, push, and open the PR. No paid inference, retained database/World change, route or UI change, direct SDK fallback, identity re-adjudication, or model-winner claim is authorized.

The deferred one-recap input and comparator are recorded in `/tmp/c1s16-ge-deepseek-bounded-consumer-proposal.json` (SHA256 `f3fdd7e7ce25517aed4cf8ebb52f418ac7024946d11788461f4fe147d0ff85bd`); they are not an execution lease.

## Implementation evidence

The exact GenerationEngine merge pin is locked while the DungeonMind/Core pin remains unchanged. Focused fake-provider tests cover the DeepSeek route/request, local schema acceptance and rejection, fail-closed observation mismatches, no credential, no second call after failure, and the pre-existing OpenAI path. `pytest -q tests/test_bounded_recap_execution.py` passed (18 tests); Ruff passed on the two touched Python paths. No paid provider call was made. A real upstream route, bill, and recap quality result remain unproved and are reserved for a separately authorized one-recap consumer slice.
