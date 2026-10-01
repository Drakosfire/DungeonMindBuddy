# HANDOFF — DEMO Hermes GPT-6 Luna starting model

**Status:** ACTIVE — operator selected GPT-6 Luna on 2026-09-30; PRIME owns this bounded lane.

**Base:** Buddy `origin/main@9aa82aacca3d27849b3fba83dcfc6577097b9b7d` after a fresh fetch.

**Branch / checkout:** `codex/hermes-gpt6-luna` / `/tmp/prime-demo-plan-continuity-witness-20261001`.

**Topology:** parallel-independent. DEMO's active C2 lane owns World Play route, handoff, and roadmap work. Open PRs #798, #781, #765, #764, #763, #761, and #760 do not lease this slice's files. This lane does not use their databases or ports.

## Decision and boundary

The operator chose `gpt-6-luna` as the starting model for the player-facing Hermes Agent. Consider GPT-6 Sol at light effort only if Luna proves insufficient. OpenRouter is a later option, not a prerequisite or fallback in this slice. Do not run a broad model comparison before starting Luna.

Add a dedicated `hermes_graph_agent` action and model role to Buddy's policy. Preserve the shared `default_text_generation` and `structured_generation` roles, other callers' models, provider and key routing, graph capability policy, continuity, prompts, and UI. Both graph and conversation-only Hermes modes use the same existing resolver. Keep the existing explicit environment override.

The pinned Hermes `AIAgent` selected `codex_responses` for `openai-api` / `gpt-6-luna` / `https://api.openai.com/v1` in an offline construction probe. Official OpenAI documentation says GPT-6 Luna supports tool calling through Responses; Chat Completions supports function calling only at reasoning effort `none`. Keep the existing runtime-selected Responses path. No Hermes dependency or endpoint change is needed for this slice.

## Exclusive write set

- `Docs/Plans/HANDOFF-DEMO-hermes-gpt6-luna.md`
- `MODEL_POLICY.json`
- `src/agent/planner_pricing.py` and `tools/batch_ingest_corpus.py` for matching published short-context token rates
- `tests/test_agent_graph_policy.py`, `tests/test_model_policy_authority.py`, `tests/test_hermes_graph_agent.py`, and `tests/test_planner_pricing.py` for resolver, transport, isolation, and pricing checks

Anything else requires PRIME to revise this scope before editing.

## Verification and handback

Check the policy resolver selects Luna while structured extraction still selects its previous model, the pinned Hermes runtime selects Responses, and Agent cost estimates match the documented Luna rates when usage exists. Run focused tests and review the exact cumulative diff. A live provider smoke should report model, transport, request/usage/cost evidence, and whether conversation-only and graph tool turns work; do not claim product quality from one smoke. If the account or provider rejects Luna, keep the error and return it to PRIME rather than silently substituting Sol or OpenRouter.

Commit, push, and open a focused PR. PRIME has operator authority for subsequent merges after review.

## Initial evidence — 2026-09-30

- The pinned Hermes `AIAgent` constructed offline with `openai-api` / `gpt-6-luna` and selected `codex_responses` without an API-mode override.
- Focused policy, authority, Hermes, and pricing tests: **72 passed** with an isolated writable `HERMES_HOME`. The first run had 70 passes and two failures from Hermes trying to log under a read-only ambient `~/.hermes`; both passed after isolating that home, and the full focused set was rerun.
- The process-host integration test for a real pinned `AIAgent` graph-tool turn over a local Responses stub passed (`1 passed`, zero network attempts). It proves the adapter/wire path with the Luna policy, while using simulated provider output.
- One live conversation-only call through Buddy's `run_hermes_graph_agent_turn` succeeded. It returned two concise gate-prep questions, observed `requested_model=response_model=gpt-6-luna`, `api_mode=codex_responses`, a runtime API request ID, 469 input tokens, 52 output tokens, and estimated cost `$0.0000729` from the published short-context rates. This verifies provider access and the conversation path, not graph-tool behavior or overall answer quality.
- The cost figure is an **estimate** from reported usage and the local rate table; it is not a provider invoice.

## Sources

- OpenAI model documentation: <https://developers.openai.com/api/docs/models/gpt-6-luna>
- OpenAI GPT-6 migration guidance: <https://developers.openai.com/api/docs/guides/latest-model>
