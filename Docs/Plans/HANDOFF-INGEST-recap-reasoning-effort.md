# INGEST: use supported low reasoning for ordinary recap extraction

Status: ACTIVE. ADV owns bounded design/implementation under the user ingestion-quality assignment. Independent review subagent reviews exact head; PRIME coordinates merge/delivery only.

Serial successor to merged/delivered PR2067, base697312fedf8836639767c7110a2cdccda5345b81, branch codex/recap-low-reasoning, checkout /home/drakosfire/Projects/.codex/249d/DungeonMindBuddy. No unmerged dependency. Relevant open1853/1855/1868 paths inspected and do not overlap; old1146–1149 extraction stack remains frozen/unadopted. No active provider process or source freeze.

Outcome: ordinary recap requests select supported low reasoning through existing RecapExecutionLimits at their owning default route. Preserve configured DeepSeek1017 identity, source-onlyv2 prompts/schema, routing, accounting, output budgets, evidence and review/publication gates. No alternate model/producer, review pass, representation, fallback or corpus-specific prompt.

Evidence: actual d8c73ac5 has88/89 structured factual recall and89/89 raw-beat recall but reversed possession/attack, modality/identity and source-authority failures. Several violated rules are already explicit in prompt/catalog. Adapter currently sends none when ordinary limits omit effort; public OpenRouter metadata for exact configured model reports supported efforts max/high/low/none, default high, reasoning enabled by default. Retained /tmp/pr2026-audit-8779/deepseek-1017-reasoning-metadata-v1.json from https://openrouter.ai/api/v1/models; reasoning semantics: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens. Requesting low is a quality hypothesis, not proven causation or an accepted quality result. Reasoning uses output budget and may increase cost/latency or truncation; retain actual tokens, attempts and failures in the post-review comparison. Do not silently change budgets or add call caps.

Exclusive expected write lease:
- apps/live_control_server/services/graph_preview_runner.py: ordinary recap default execution setting only.
- tests/test_recap_generationengine_default.py: actual request and retained telemetry assertions.
- Docs/Plans/HANDOFF-INGEST-recap-object-dispositions.md: truthful predecessor settlement.
- This handoff.

No provider, shared runtime/source restart, primary/evaluator writes, migration or publication allocated to this code slice. Test fixtures may use existing disposable PostgreSQL and mocked provider with HTTP forbidden. All six actual S7 runs and current Gold remain immutable.

Validation: owning ordinary route through real APP evidence owners verifies effort low on actual requests and retained call telemetry, exact model/route/attempt policy and file-independent evidence retention; direct Process route too. Existing adapter tests preserve explicit custom effort/default behavior and schemas. Inspect cumulative diff, Ruff, commit/push/open one PR, independent subagent review. Following review, independently assess one ordinary isolated source extraction against unchanged current89/17/20/14/7Gold, preserving all6priorruns; no model comparison or Gold exposure. Shared delivery acceptance remains separate. Full C1S1–10→worldbuilding→benchmark goal remains active.

Validation completed:84 ordinary-route/APP-retention and bounded-adapter tests pass in32.23s with provider HTTP forbidden and disposable PostgreSQL fixtures; Ruff and whitespace checks pass. All source-only prompts, schemas, model/route, pass budgets and output limits remain unchanged. Actual low-effort reasoning tokens, latency and semantic quality are unproven until the retained post-review execution.
