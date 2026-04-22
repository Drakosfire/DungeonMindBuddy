# evals/_archive/handoffs — Archived eval-scaffolding handoff docs

Historical handoff documents from completed eval-scaffolding phases. Preserved
for context; superseded by the per-slice READMEs and `Docs/Plans/STATUS-*.md`
files for current state.

These docs were retrospective handoffs written as each phase landed. They
remain useful as a record of what the contracts looked like and how the cost /
caching / batching levers were stacked, but they are no longer the authoritative
reference for runtime behavior — read the relevant slice README and the
`STATUS-Session-Recap-*.md` ledgers under `Docs/Plans/` first.

All eight phase docs were added in commit `cb69ecc docs: ingestion design refresh
and eval pipeline handoffs` (2026-04-04) and self-attest `Status: COMPLETED`
with a `2026-04-03` completion date.

## Index

In phase order:

- [HANDOFF-phase1-token-usage-capture.md](./HANDOFF-phase1-token-usage-capture.md) — Phase 1: `UsageStats` dataclass + `_usage` plumbing through entity / fact extractors and CLI; per-stage `usage` / `cache_hits` / `cache_misses` recorded on `model_calls` events. Doc landed in `cb69ecc`.
- [HANDOFF-phase2-recap-lane-wiring.md](./HANDOFF-phase2-recap-lane-wiring.md) — Phase 2: `cli.py` `_cmd_ingest()` wires `recap_artifacts` through `run_entity_extraction`, persists `event_records` / `claims` via `store.add_event_records` / `store.add_claims`. Doc landed in `cb69ecc`.
- [HANDOFF-phase3-prompt-restructure-caching.md](./HANDOFF-phase3-prompt-restructure-caching.md) — Phase 3: split entity / recap / fact prompts into static `system` + per-unit `user` to clear OpenAI prompt-caching's 1,024-token prefix bar; `_PROMPT_ID`s bumped. Doc landed in `cb69ecc`.
- [HANDOFF-phase4-multi-unit-batching.md](./HANDOFF-phase4-multi-unit-batching.md) — Phase 4: multi-unit batched prompts on entity + fact paths; `--batch-size` (default 5) on `ingest` and `tools/batch_ingest_corpus.py`; recap units stay one-per-call. Doc landed in `cb69ecc`.
- [HANDOFF-phase5-enriched-model-calls-logging.md](./HANDOFF-phase5-enriched-model-calls-logging.md) — Phase 5: `model_calls.jsonl` schema enriched with `model_name`, `event_records_count`, `claims_count`, nested `usage`. Doc landed in `cb69ecc`.
- [HANDOFF-phase6-batch-report-overhaul.md](./HANDOFF-phase6-batch-report-overhaul.md) — Phase 6: `_aggregate_batch_report()` writes `logs/batch_report.json` (entity + fact tokens, files / cost / cache_rate / class distribution); `_compute_escalation_metrics()` updated for explicit `other` / `unknown` / `missing` semantics. Doc landed in `cb69ecc`.
- [HANDOFF-phase7-incremental-resumable-ingest.md](./HANDOFF-phase7-incremental-resumable-ingest.md) — Phase 7: `compute_ingest_key_for_path()` plus `--force` / `--resume` / unchanged-skip behavior on `tools/batch_ingest_corpus.py` (with `batch_progress.json` checkpointing). Doc landed in `cb69ecc`.
- [HANDOFF-phase8-openai-batch-api.md](./HANDOFF-phase8-openai-batch-api.md) — Phase 8: `src/ingestion/openai_batch_pipeline.py` plus `--use-openai-batch-api` / `--use-batch-api` wiring; per-file Batch jobs feed the existing per-unit cache; `batch_report.json` applies the 0.5× multiplier. Doc landed in `cb69ecc`.

Sibling top-level handoffs left under `evals/` are not in this archive because
they were not part of the same Phase 1–8 cost-reduction stack and their
retire-or-keep status is independently tracked in `Backlog.md`.
