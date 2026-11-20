# INGEST: pin the OpenRouter effective model

**Status:** ACTIVE — PRIME delegated design and bounded implementation under the active ingestion goal.
**Base:** `origin/main@cae231366d22726f69fabf391bc43f282d8327e5` (fetched 2026-10-17).
**Branch:** `codex/ingest-openrouter-model-identity` in the existing clean `996b` checkout.
**Topology:** Serial; one Buddy implementation PR. PRIME retains independent exact-head review and merge authority. No new checkout or environment.

## Mission and invariant

The normal Session 29 Process request used `deepseek/deepseek-v4.1-flash`. The
one approved provider attempt returned `deepseek/deepseek-v4.1-flash-1017` as the
model actually used. Buddy's bounded recap client requires exact provider,
requested, resolved, and response model identity, so it correctly failed closed
before candidate graph parsing. Keep that equality guard. Make the ordinary
Ingest route request the exact catalogued dated model
`deepseek/deepseek-v4.1-flash-1017`, so future runs have explicit, stable model
selection and the guard can continue to compare all four identities exactly.

This intentionally changes the default from OpenRouter's unversioned
`deepseek/deepseek-v4.1-flash` identifier to the separately catalogued October
17 snapshot. If that pinned model is unavailable, extraction must fail closed
rather than accept another model. Do not add prefix/suffix/family matching,
loosen provider identity, rewrite historical run ledgers, or add a speculative
GenerationEngine identity-resolution contract.

## Evidence

- The fresh run `13b16df7-87ea-4723-b5d5-bf60ae72517c` recorded one OpenRouter
  attempt, requested/resolved model `deepseek/deepseek-v4.1-flash`, response
  model `deepseek/deepseek-v4.1-flash-1017`, and no retries. It produced no
  candidate graph. The original run `f43e48e6-c775-4960-824f-fb398fe50bb9` is
  preserved. No second provider call is authorized.
- Read-only OpenRouter model metadata for the unversioned requested ID reports
  `canonical_slug=deepseek/deepseek-v4.1-flash-20260910`; the returned dated ID
  reports `canonical_slug=deepseek/deepseek-v4.1-flash-20261017`. Metadata
  snapshots are preserved locally, mode 0700/0600, under the ignored path
  `.pytest_cache/ingest-openrouter-model-metadata/`. Requested JSON SHA-256:
  `ee76516c7fe13c7f0150e565f3340cf52f54836df0989c25b23e4d8d9a2db666`;
  returned JSON SHA-256:
  `781b1bbb48dc2165833b4d18a829d5a1ec0600eb9ad8603e7a5eb09ed3d02ac3`.
- OpenRouter's public catalog describes 1017 as the October 17 snapshot of
  DeepSeek V4.1 Flash and lists it as the current DeepSeek Flash version. The
  two IDs therefore have different dated canonical slugs; this evidence does
  not justify treating them as equal aliases.
- OpenRouter's Chat Completions reference describes response `model` as the
  model used for completion. References: [response model field](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request),
  [model metadata](https://openrouter.ai/docs/api/api-reference/models/get-model),
  [V4.1 Flash 1017 catalog entry](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017),
  [DeepSeek Flash versions](https://openrouter.ai/deepseek/deepseek-flash).
- Public metadata for `deepseek/deepseek-flash` is not a model entry (HTTP 404);
  the family webpage is descriptive and does not establish an exact
  request-bound alias mapping from the configured September 10 slug to 1017.

## Exclusive write set

- `Docs/Plans/HANDOFF-INGEST-openrouter-exact-model-pin.md` — this authority and
  truthful completion evidence.
- `src/graph_memory/extraction/bounded_recap_execution.py` — pin the one
  supported OpenRouter model ID without weakening validation.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — send the same pinned
  exact ID in the ordinary Process request.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — prove the
  mounted Process request carries the pinned ID.
- `tests/test_bounded_recap_execution.py` — exact pinned identity passes;
  previous unversioned and unrelated returned IDs fail after one call.
- `tests/test_live_recap_ingest_graph_preview_api.py` — update ordinary route
  fixtures and assert the pinned ID is carried into the extraction result.
- `tests/test_worldbuilding_ge_execution.py` — assert exact model passed to GE.
- `tests/test_live_recap_ingest_process_review_persistence.py` — update any
  current-model fixture affected by the exact pin.
- `tests/test_known_npc_endpoint_pipeline.py` — update any current-model
  fixture affected by the exact pin.
- `tests/test_registered_known_entity_context.py` — update any current-model
  fixture affected by the exact pin.

No other paths are in scope. In particular, no GenerationEngine/Core repository
changes, graph candidate schema, model identity prefix matching, retries,
provider execution, source/gold edits, saved run edits, database, service,
environment, publication, or user-state changes.

## Failure cases and acceptance

- Exact request, resolved, and response model IDs are preserved distinctly and
  all equal the pinned dated ID for an accepted bounded attempt.
- The old unversioned ID and an unrelated dated response ID reject before a
  second attempt; provider mismatch, retry caps, bounded limits, and existing
  schema validation remain intact.
- UI ordinary Process requests use the exact same dated model ID as the server
  allowlist. The Advanced graph extraction control names the pinned version so
  the configured behavior is visible where model details are relevant.
- No live provider call is used for verification. The saved Session 29 response
  identity can be represented in a synthetic fixture; do not replay it against
  OpenRouter.
- Existing generated run and source artifacts remain byte-for-byte unchanged;
  no candidate graph or publication is synthesized.
- Run focused owning tests, typecheck/build as applicable, lint, and
  `git diff --check`. Inspect the exact cumulative base-to-head diff; commit,
  push, and open the assigned PR. PRIME reviews the new exact head. Do not merge
  or modify 5202.

## PR and active-work check

#1377 (`INGEST: preserve modality in claimed party fill`) is merged at
`590686f5d5c7933480d7e57ce080bddf4f4fc473`; the branch was re-anchored on
fetched current main `cae231366d22726f69fabf391bc43f282d8327e5` after the
separate Build PR #1382. Open Ingest PR #1235 owns graph-review UI paths;
open MIND PR #1148 owns the edge-prompt catalog and recap-planning code. Neither
intersects this write set. No active open PR owns the listed model-selection
paths.

## Implementation verification (2026-10-17)

- `tests/test_bounded_recap_execution.py`,
  `tests/test_recap_generationengine_default.py`, the exact DeepSeek GE request
  test, and `tests/test_known_npc_endpoint_pipeline.py`: **83 passed**.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`: **78 passed**;
  this includes the ordinary Process payload carrying 1017 and the Advanced
  graph-tool label/request.
- Ruff on all changed Python source/tests: **passed**.
- `npm run build` (`tsc -b && vite build`): **passed**. Vite emitted its
  existing large-chunk advisory (>500 kB).
- A broader attempt across the owning API/persistence suites reported 76
  passed and 39 setup errors because the disposable PostgreSQL fixture at
  `127.0.0.1:54329` was unavailable (`psycopg.OperationalError` while creating
  test databases). Those database-backed cases remain unverified; no database
  service was started.
- No live provider call, Process replay, runtime adoption, saved-run edit, or
  publication was performed. `git diff --check` passed.
