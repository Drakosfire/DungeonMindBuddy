# APP: explicit uncapped execution authorization

Status: ACTIVE — PRIME implementation under operator's standing instruction to remove fixed call/Graph-operation caps; ARCHITECTURE owns independent review.

## Invariant and activation

Required nullable count/aggregate-token policy fields distinguish explicit uncapped authorization from missing or malformed authorization. A distinct policy version admits null; historical finite receipts retain identical serialization, fingerprints and enforcement. Preserve accounting, event ordering, evidence inclusion, storage capacity, cancellation/fencing and uncertainty safeguards.

Base: `38f79e1c64c93968ea15802a5cd58ff81d55d9f9`, fetched 2026-10-16 UTC. Branch `codex/app-nullable-execution-counts`, checkout `/tmp/prime-recap-mention-boundaries`. This document is pinned before implementation. Serial producer prerequisite for a separately pinned ordinary Agent consumer. Open PRs inspected; no concurrent APP execution-policy or migration owner. Gold audit is read-only and independent.

## Exact exclusive write set

- `Docs/Plans/HANDOFF-APP-nullable-execution-counts.md`
- `Docs/Plans/HANDOFF-BUILD-host-derived-citations.md` — truthful predecessor settlement
- `src/application_state/agent_conversation/types.py`
- `src/application_state/migrations/versions/20261016_0025_nullable_execution_counts.py`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`

## Contract

Four required fields admit null only under `world_graph_execution_uncapped_v1` or `world_graph_execution_selected_scope_uncapped_v1`: provider attempts, Graph operations, aggregate input tokens, aggregate output tokens. These versions require all four null, avoiding implicit aggregate-token caps. Old versions require integers. Selected-scope subtype checks admit the new selected version. Source-call V2 limits remain finite in this producer; ordinary V3 has no such policy fields. The consumer must separately remove remaining worker/parent source/context call caps. Per-request context/output limits and source character/result/storage capacities remain separate constraints.

Migration admits these explicit policies without rewriting rows and refuses downgrade while retained uncapped records exist, including consultation records. No retained database migration, serving change, provider call, extraction or World publication in this slice.

## Proof and completion

Exercise V1/V2/V3 validation and digests, >4 provider authorizations and >8 Graph operations at APP boundary, unchanged finite refusal and integer serialization, required/null/bool/mixed/version rejection, source/evidence/order/storage checks, actual disposable PostgreSQL persistence/fresh-service readback and migration downgrade protection. Review cumulative base→head diff, Ruff and focused tests. Commit/push/open one PR and request ARCHITECTURE exact-head review; PRIME alone merges. Consumer/runtime proof remains required before claiming the ordinary conversation is fixed.

## Author evidence

APP V1/V2/V3 each accept and persist 9 Graph operations plus 5 provider authorizations/outcomes with explicit null policy; fresh-service readback retains all 24 events and token estimates. Each finite historical limit is independently enforced. Boolean/string/mixed/omitted fields and old-version nulls reject at model and database boundaries. Disposable migration downgrade/upgrade preserves finite records byte-for-byte and refuses downgrade after uncapped retention. V3 selected-scope commitment and V2 projection tests pass.

Affected regression command: `PYTHONPATH=.:src <runtime-python> /tmp/run-build-governed-tests.py tests/application_state/test_agent_conversation_service.py tests/application_state/test_agent_conversation_postgres.py tests/application_state/test_build_graph_turns.py tests/test_agent_build_governed_graph.py` — 161 passed, 1 inherited submitted-intent fingerprint expectation failure reproduced unchanged on exact base `38f79e1c`. Final added independent finite-limit checks: 3 parametrized tests pass. Ruff/diff check pass. Logs `/tmp/nullable-execution-regression-final.log`, `/tmp/nullable-execution-base-failure.log`, `/tmp/nullable-policy-final.log` are local review evidence, not runtime dependencies. No provider or retained-state changes.
