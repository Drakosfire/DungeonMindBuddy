# INGEST: use supported low reasoning for ordinary recap extraction

Status: ACTIVE. ADV owns bounded design/implementation under the user ingestion-quality assignment. Independent review subagent reviews exact head; PRIME coordinates merge/delivery only.

Serial successor to merged/delivered PR2067, base697312fedf8836639767c7110a2cdccda5345b81, branch codex/recap-low-reasoning, checkout /home/drakosfire/Projects/.codex/249d/DungeonMindBuddy. No unmerged dependency. Relevant open1853/1855/1868 paths inspected and do not overlap; old1146–1149 extraction stack remains frozen/unadopted. No active provider process or source freeze.

Outcome: ordinary recap requests select supported low reasoning through existing RecapExecutionLimits at their owning default route. Preserve configured DeepSeek1017 identity, source-onlyv2 prompts/schema, routing, accounting, evidence and review/publication gates. No alternate model/producer, review pass, representation, fallback or corpus-specific prompt.

Evidence: actual d8c73ac5 has88/89 structured factual recall and89/89 raw-beat recall but reversed possession/attack, modality/identity and source-authority failures. Several violated rules are already explicit in prompt/catalog. Adapter currently sends none when ordinary limits omit effort; public OpenRouter metadata for exact configured model reports supported efforts max/high/low/none, default high, reasoning enabled by default. Retained /tmp/pr2026-audit-8779/deepseek-1017-reasoning-metadata-v1.json from https://openrouter.ai/api/v1/models; reasoning semantics: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens. Requesting low is a quality hypothesis, not proven causation or an accepted quality result. Reasoning uses output budget and may increase cost/latency or truncation; retain actual tokens, attempts and failures in the post-review comparison. Do not silently change budgets or add call caps.

Exclusive expected write lease:
- apps/live_control_server/services/graph_preview_runner.py: ordinary recap default execution setting only.
- tests/test_recap_generationengine_default.py: actual request and retained telemetry assertions.
- src/graph_memory/extraction/bounded_recap_execution.py: shared total-output allowance upper bound only; default unchanged.
- tests/test_bounded_recap_execution.py: owning allowance boundary/default checks.
- Docs/Plans/HANDOFF-INGEST-recap-object-dispositions.md: truthful predecessor settlement.
- This handoff.

No provider, shared runtime/source restart, primary/evaluator writes, migration or publication allocated to this code slice. Test fixtures may use existing disposable PostgreSQL and mocked provider with HTTP forbidden. All six actual S7 runs and current Gold remain immutable.

Validation: owning ordinary route through real APP evidence owners verifies effort low on actual requests and retained call telemetry, exact model/route/attempt policy and file-independent evidence retention; direct Process route too. Existing adapter tests preserve explicit custom effort/default behavior and schemas. Inspect cumulative diff, Ruff, commit/push/open one PR, independent subagent review. Following review, independently assess one ordinary isolated source extraction against unchanged current89/17/20/14/7Gold, preserving all6priorruns; no model comparison or Gold exposure. Shared delivery acceptance remains separate. Full C1S1–10→worldbuilding→benchmark goal remains active.

Validation completed:84 ordinary-route/APP-retention and bounded-adapter tests pass in32.23s with provider HTTP forbidden and disposable PostgreSQL fixtures; Ruff and whitespace checks pass. All source-only prompts, schemas, model/route and pass budgets remain unchanged. Actual low-effort reasoning tokens, latency and semantic quality are unproven until the retained post-review execution.


Actual trial and required capacity amendment: isolated run c90d1636-080a-47bc-9112-c844b1dbf889 failed actor structured output after initial plus normal conformance attempt. Both used8192total tokens with6471/6503reasoning tokens, leaving1721/1689visible tokens and incomplete JSON. All six prior runs/native snapshot remained exact; no candidate/publication. Failure is retained in APP, not erased. No semantic quality result is claimed. Pair low effort with existing supported16384total capacity at this same ordinary recap owner; edge capacity remains16384, other passes rise8192→16384. Remove the now-redundant ordinary edge override. Existing valid explicit custom settings retain their requested values; the allowed common ceiling expands, while adapter and Worldbuilding defaults remain unchanged. This is necessary output headroom for this same capability, not a new producer, fallback, retry or call cap. New owning-boundary tests inspect all actual requests and retained call capacities. Subsequent actual assessment must preserve all SEVEN runs including this failure; do not rerun the stale six-run driver.


Capacity owner scope checkpoint: the ordinary-route tests caught a pre-existing common max_output_tokens ceiling8192, while only the edge override admitted16384. This same capability is indivisible without increasing the common allowed ceiling to16384 at RecapExecutionLimits. Its default remains8192, explicit edge overrides remain supported, and no Worldbuilding default changes. Add these two owning paths to the lease above; frozen old provider-diagnostic work is not adopted. This is a required contract extension for reasoning output headroom, not an independent extra capability. Preserve the six failed local checks as discovery evidence; no provider retry occurred.


Explicit ownership split: historical open PR1146 last updated2026-10-14 covers provider failure diagnostics in bounded_recap_execution.py and its worker, but has no adopted current-main implementation. ADV's current designing-steward assignment takes the common output-limit guard and its tests into this serial2068 lease; diagnostic/worker logic remains untouched and old evidence/PR preserved. PRIME notified to keep the old lane frozen and require re-anchor before any future writes/merge. No concurrent file writer is allocated.

Amended validation completed:89 ordinary-route/APP-retention and bounded-adapter checks pass in32.10s; Ruff and whitespace checks pass. The initial six local failures were the owning8192ceiling and are resolved by the explicit contract extension. No second real provider run has been dispatched; actual16384headroom and semantic quality remain unproven.


## Resumed allocation amendment — user authorized November 4

User explicitly assigns ADV the reasoning/output allocation fix, independent subagent review, and isolated C1S1–10 ingestion through publication. Same serial PR2068/base697312f and write set; no new producer, representation, provider transport or migration. No merge authority.

Run94faa665-d17e-43c1-b9f2-92562cca0d2b remains prepared revision2 after interruption. Durable APP captures retain all seven calls: first six original outputs parse JSON (not schema/Gold approval), edge output16384/reasoning16384/textnull. No sealed candidate/outcome, no publication. Independent evidence review HOLD; distinguish missing terminalization from output exhaustion. Preserve all EIGHT existing S7 runs. Old temporary audit exports were lost; hash-verified DB captures are now exported to /home/drakosfire/.codex/visualizations/2026/10/26/01a17647-5784-7bd3-acf7-924cd6f01968/ingestion-resume/. Do not redispatch old drivers or stitch a success candidate from partial responses.

Exact-model public metadata lists supported efforts max/high/low/none and no supports_max_tokens; OpenRouter official reasoning documentation says a hard reasoning budget requires that capability. Therefore no unsupported hard-budget control or GenerationEngine contract extension. Existing ordinary edge override becomes32768, other passes remain16384/low. Explicit ordinary call240000ms/run900000ms accompany output headroom; shared allowed ceilings expand only as required while generic defaults remain120000/480000/8192. These are bounded experimental capacities, not guaranteed visible-token reservations or proof of semantic improvement. Existing attempt accounting and profile call policy are unchanged.

Independent preimplementation design review agrees this is the smallest supported Buddy-owned capacity hypothesis and requires actual request/retained telemetry/deadline evidence plus real completion. No provider dispatch allocated until exact amended code review and separately pinned evaluator assessment; no publication until reviewed candidate selections and source authority are established. Primary stays unchanged. Recover/reconcile latest source-reviewed Gold before scoring; do not silently use an older Gold version.
