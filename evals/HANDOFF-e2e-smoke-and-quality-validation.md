# HANDOFF — End-to-End Smoke Tests & Quality Validation

**Status:** Ready
**Prerequisites:** Phases 1–8 complete; `OPENAI_API_KEY` set in environment
**Estimated effort:** 1–2 hours active work + async batch wait times

---

## Goal

Validate all 8 phases together with real API calls against a sample of the corpus. Measure:

1. **API call count** — confirm batching reduces calls ~5x vs. baseline
2. **Token usage & cost** — confirm `batch_report.json` populates correctly; validate `cached_tokens > 0` (prompt caching working)
3. **Wall-clock time** — interactive vs. OpenAI Batch API latency
4. **Quality parity** — entity/fact counts and class distribution comparable to the pre-Phase baseline stores
5. **Incremental skip** — re-run confirms 0 LLM calls for unchanged files
6. **Recap lane** — session recap files produce `event_records` and `claims`

---

## Existing Baselines

| Store | Model | Files | Entities | Facts | Evidence Units |
|---|---|---|---|---|---|
| `cheapest_full` | pre-Phase (cheapest) | 130 | 1,759 | 22,548 | 3,867 |
| `escalation_full_mini_to_54` | mini + escalated | 130 | 2,779 | 21,964 | 5,299 |
| `nano_full` | nano | 130 | 4,845 | 15,359 | 2,526 |

These stores have **no** `usage` data, **no** `batch_report.json`, and used the old monolithic prompt format. They serve as quality-parity targets.

Baseline store location: `out/stores/dungeonbuddy_store_cheapest_full/`

---

## Test Plan

### Run 1: Interactive smoke (3 files, batch-size 5)

Purpose: Confirm the full pipeline works end-to-end with the new prompt structure, batching, and usage capture. Quick turnaround.

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy

uv run python tools/batch_ingest_corpus.py \
  --store out/stores/smoke_interactive_3 \
  --limit 3 \
  --batch-size 5
```

**Check:**
- [ ] Completes without error
- [ ] `out/stores/smoke_interactive_3/logs/batch_report.json` exists
- [ ] `batch_report.json` has non-zero `tokens.input_tokens`, `tokens.output_tokens`
- [ ] `batch_report.json` has `api_calls.total` — should be much less than `2 × evidence_units` (batching working)
- [ ] `model_name` is populated (e.g. `gpt-5.4-nano` or whatever `cheapest` resolves to)
- [ ] `model_calls.jsonl` entries have `usage` dicts with `api_calls`, `cache_hits`, `cache_misses`
- [ ] Human-readable report table printed to stdout
- [ ] `entities.json`, `facts.json`, `evidence_units.json` are non-empty

**Record:** `api_calls.total`, `tokens`, `estimated_cost_usd`, `files.succeeded`, wall-clock time (from `run_window`).

### Run 2: Interactive smoke re-run (incremental skip)

Purpose: Confirm unchanged files are skipped with 0 LLM calls.

```bash
uv run python tools/batch_ingest_corpus.py \
  --store out/stores/smoke_interactive_3 \
  --limit 3 \
  --batch-size 5
```

**Check:**
- [ ] All 3 files show `skipped (unchanged)`
- [ ] `batch_report.json` has `files.skipped: 3`, `api_calls.total: 0`
- [ ] Wall-clock time is <10 seconds (no LLM calls)
- [ ] Entity/fact/evidence counts unchanged from Run 1

### Run 3: OpenAI Batch API smoke (3 files)

Purpose: Confirm the Batch API path works end-to-end and the 50% discount is reflected.

```bash
uv run python tools/batch_ingest_corpus.py \
  --store out/stores/smoke_batch_api_3 \
  --limit 3 \
  --batch-size 5 \
  --use-batch-api
```

**Check:**
- [ ] Batch job submitted and polled to completion (stdout shows status updates)
- [ ] `out/stores/smoke_batch_api_3/logs/openai_batch/` directory exists with request/output JSONL
- [ ] `batch_report.json` has `cost_estimate.openai_batch_discount_applied: true`
- [ ] `cost_estimate.openai_batch_pricing_multiplier: 0.5`
- [ ] Entities and facts are non-empty
- [ ] Entity/fact counts roughly comparable to Run 1 (same 3 files, same model)

**Record:** Batch API wall-clock time (poll duration), compare to Run 1 interactive time.

### Run 4: Prompt caching validation (10 files)

Purpose: With 10 files the system prompt prefix should cache after the first call. Verify `cached_tokens > 0`.

```bash
uv run python tools/batch_ingest_corpus.py \
  --store out/stores/smoke_cache_10 \
  --limit 10 \
  --batch-size 5
```

**Check:**
- [ ] `batch_report.json` → `tokens.cached_tokens > 0`
- [ ] `tokens.cache_rate > 0` (ideally > 0.5 for 10 files)
- [ ] `model_calls.jsonl` — at least some entries have `usage.cached_tokens > 0`
- [ ] Cost estimate reflects cache savings (`cost_estimate.savings_pct > 0`)

### Run 5: Quality comparison (10-file subset)

Purpose: Compare entity/fact extraction quality against the baseline.

```bash
# Use the same first 10 files as the baseline stores
uv run python tools/batch_ingest_corpus.py \
  --store out/stores/smoke_quality_10 \
  --limit 10 \
  --batch-size 5
```

**Compare against baseline (cheapest_full, first 10 files):**

```python
import json

new = json.load(open("out/stores/smoke_quality_10/entities.json"))
old_summary = json.load(open("out/stores/dungeonbuddy_store_cheapest_full/logs/batch_ingest_summary.json"))

# Get first 10 run_ids from baseline
first_10_runs = [r for r in old_summary["results"][:10] if "run_id" in r]

# Compare entity counts, class distributions
new_classes = {}
for e in new:
    cls = e.get("entity_class", "missing")
    new_classes[cls] = new_classes.get(cls, 0) + 1
print("New entity class distribution:", json.dumps(new_classes, indent=2))
print(f"New entity count: {len(new)}")
print(f"New fact count: {len(json.load(open('out/stores/smoke_quality_10/facts.json')))}")
```

**Check:**
- [ ] Entity count within 30% of baseline's first-10-file subset (prompts changed, some drift expected)
- [ ] No `other` or `unknown` entity_class values (or < 5%)
- [ ] Class distribution follows expected pattern: `actor` > `place` > `group` > `object` > `event` > `concept`
- [ ] Fact count is plausible (not 0, not wildly different from baseline proportionally)

### Run 6: Session recap file (recap lane)

Purpose: Verify Phase 2 recap wiring produces event_records and claims.

Find a session recap file:
```bash
ls corpus/eldyrwild-markdown/Longmont\ Campaign/Campaign\ 1/Session\ Recaps/ | head -3
```

Ingest one:
```bash
uv run python -m src.cli
# then: ingest "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 17 - Recap.md"
```

**Check:**
- [ ] `event_records_count > 0` in the model_calls log entry
- [ ] `claims_count > 0` in the model_calls log entry
- [ ] Store's `event_records.json` has entries
- [ ] Store's `claims.json` has entries
- [ ] Completion print line includes non-zero event_records/claims counts

### Run 7: Full corpus (optional, longer)

Purpose: Full validation at scale. Only run after Runs 1–6 pass.

```bash
uv run python tools/batch_ingest_corpus.py \
  --store out/stores/post_phase8_full \
  --batch-size 5 \
  --enforce-cheap-pass \
  --auto-escalate
```

**Compare against `cheapest_full` baseline:**

| Metric | Baseline (cheapest_full) | Post-Phase8 | Delta |
|---|---|---|---|
| Entities | 1,759 | ? | ? |
| Facts | 22,548 | ? | ? |
| Evidence units | 3,867 | ? | ? |
| API calls | ~8,245 (estimated) | ? (from batch_report) | ? |
| Cost | unknown | ? (from batch_report) | ? |
| Duration | ~135 min | ? | ? |

---

## What to Record

For each run, capture from `batch_report.json`:

```
Run | Files | API Calls | Input Tokens | Cached Tokens | Cache Rate | Est. Cost | Duration
```

Also save:
- `batch_report.json` (copy to `evals/smoke_results/run_N_batch_report.json` for archival)
- Entity/fact counts
- Any errors or warnings from the batch log

---

## NPC voice planner benchmarks (Torbin / Dustwalker)

Planner Step 1-shaped live gates without Lysandra Step 2: [`evals/npc_voice_vertical_slice/README.md`](npc_voice_vertical_slice/README.md).

```bash
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --list-scenarios
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --scenario torbin_factual_ac
uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --all
```

Pytest (single scenario): `NPC_VOICE_PLANNER_LIVE=1 pytest tests/test_npc_voice_vertical_slice_planner.py::test_npc_voice_planner_live_single_scenario -m integration`. Full manifest: `NPC_VOICE_PLANNER_LIVE_ALL=1` on `test_npc_voice_planner_live_all_manifest`.

---

## Known Risks

1. **Prompt ID bump** — Phase 3 bumped `_PROMPT_ID`. All file caches are stale. First run against any corpus will be 100% cache misses. This is expected.
2. **Model name in pricing** — `MODEL_POLICY.json` uses `gpt-5.4-nano` for cheapest. If this model prefix isn't in `_PRICING_PER_1M` in `batch_ingest_corpus.py`, cost fields will be 0. Check and add if needed.
3. **Batch API result format** — Phase 8 noted that `extract_response_body_from_batch_line` may need adjustment if OpenAI changes the batch result line format. A `--limit 1 --use-batch-api` is the right first probe.
4. **Quality drift** — New prompt structure (system/user split, extended field descriptions) may shift entity/fact counts vs. baseline. Some drift is expected and acceptable; large swings (>50%) warrant investigation.

---

## Cleanup

Smoke test stores can be deleted after validation:

```bash
rm -rf out/stores/smoke_interactive_3
rm -rf out/stores/smoke_batch_api_3
rm -rf out/stores/smoke_cache_10
rm -rf out/stores/smoke_quality_10
```

Keep `post_phase8_full` if it becomes the new baseline.
