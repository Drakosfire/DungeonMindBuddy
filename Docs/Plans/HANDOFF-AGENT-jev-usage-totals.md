# AGENT: truthful Jev/one-writer usage totals

ACTIVE under PRIME responsive source-faithful Graph goal. Base `0dbdd85a8db8038ef7fe21e083dbe3cc8905462d`; branch `codex/jev-usage-total-accounting`; reuse `/home/drakosfire/.codex/worktrees/buddy-tool-denial-delivery/DungeonMindBuddy` and existing dependencies. PRIME implements solo; ARCHITECTURE independently reviews. Serial successor to merged #1351; no open Agent implementation PR. Concurrent DOGFOOD #1353 owns IngestionModule and its cold-reader handoff/tests only; no overlap.

## Invariant and failure

Fresh ordinary HTTP Council run completed with reported input170069/output15700 tokens, but its trace aggregate showed total_tokens0 because GE observations omit total_tokens and the Harness bypasses the legacy observer normalizer. Keep GE input semantics (cache is a subset), original observations and provider totals intact. When both input/output are reported and total is absent, derive total as input+output before recording the call and durable context-capture usage. Never add cached or reasoning tokens again; never invent missing usage or price unknown provider costs.

## Exact write lease and topology

One serial bounded PR: this handoff; factual settlement `Docs/Plans/HANDOFF-AGENT-finite-writer-selectors.md`; `apps/live_control_server/services/build_jev_harness.py` (_record_observation only); `tests/test_build_jev_default_runtime.py` (actual HTTP/default/trace/capture assertions and observation edge cases); `tests/test_agent_build_jev_ordinary_harness.py` (existing failed-writer usage assertion only if needed). No generic trace aggregation/legacy Hermes changes, schema/migrations, prompts/retrieval/provider routes, dependencies, runtime/user data or provider calls.

## Verification and limits

Run actual SDK->APP default HTTP witness with mocked providers through final trace and protected persisted context capture; totals must equal reported input+output and count every observed call once. Explicit provider totals remain authoritative; cache/reasoning are not added; absent/incomplete usage stays unavailable; error observations with reported usage remain counted. Preserve one writer, no retries and durable completion/replay tests. Scoped lint/diff check and independent exact-head review before merge. No fresh model or serving acceptance claimed by this accounting fix.

## Implementation evidence

15 focused cases pass: actual default HTTP/prepared factory/SDK->APP completion/replay and protected persisted usage sum, five observation edge cases, and a failed structured writer retaining its reported total. Initial capture-count assertion also counted lifecycle response notices; corrected to distinguish reported input/output observations from lifecycle records without changing runtime capture. Scoped Ruff and cumulative diff checks pass. No inference, retained data, schema or serving change.
