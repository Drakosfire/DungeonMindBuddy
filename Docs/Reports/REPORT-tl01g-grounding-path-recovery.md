# REPORT — TL01 Shared Source-Phrase Grounding-Path Recovery

**Status:** Durable diagnostic evidence  
**Implementation base:** `58c186dd666bceaee1296d5e44c7710261aaad35`  
**Handoff:** `Docs/Plans/HANDOFF-pr488-tl01-grounding-path-recovery.md`  
**Fixture:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/`  
**Expected phrase:** `the brass moth struck the north bell exactly twice`

## Scope

This slice adds a diagnostic-only paired smoke (not promotion authority) exercising the
production `run_temporal_shadow_extraction` path through frozen `tl01f-v1` and `tl01g-v1`
prompt identities on one shared assertion/evidence fixture.

No production repair was required or applied. Frozen prompt hashes, packet version
(`tl01c-packet-v1`), and renderer identity (`render_temporal_shadow_user_content_v2`) are
unchanged.

## Frozen identity guards

| Item | Value | Changed? |
|---|---|---|
| Control prompt `tl01f-v1` SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` | No |
| Candidate prompt `tl01g-v1` SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` | No |
| Packet version | `tl01c-packet-v1` | No |
| Renderer | `render_temporal_shadow_user_content_v2` | No |
| Live model | `gpt-5.4-mini` | N/A (diagnostic only) |

Retired holdout v8–v13 and adversarial v6–v11 cohort bytes were not modified. No V14 or Adv V12
directory was created.

## Deterministic lane results (`--mode deterministic --phase initial`)

| Lane | Prompt | Lane result | Metrics present |
|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | true (`exact_match_count=1`) |
| candidate | `tl01g-v1` | `EVALUABLE` | true (`exact_match_count=1`) |

Provider calls: **0** (deterministic fake replay; no live delegate counted).

Pre-provider observations on both lanes:

- packet phrase present: true
- decoded renderer phrase present: true
- resolved span digest: `4d98be8e9ac48a0f17fe9bae3a4810092612bba83a15be1982224be18444f345`

Deterministic-only overall classifier output: `UNRESOLVED_DIAGNOSTIC_GAP` (live evidence still
required by §6.8 until paired live smoke completes).

## Live lane results (`DMB_RUN_LIVE_TL01_GROUNDING_SMOKE=1 --mode live --phase initial`)

| Lane | Prompt | Lane result | Provider response ID | Metrics present |
|---|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | `resp_0207dffb227fbed2006a6ed36f4bbc81949cfa5214373f1ac0` | true |
| candidate | `tl01g-v1` | `EVALUABLE` | `resp_07fc478c5452975c006a6ed371c7188196af0bfb23a17d04ae` | true |

Provider calls: **2** (one control + one candidate; no automatic retries).

Both live lanes returned an owned-evidence-grounded phrase containing the expected contiguous
substring (`the brass moth struck the north bell exactly twice`) and reached ordinary comparison
metrics on the same fixture/model/renderer.

## Overall conclusion

**`GROUNDING_PATH_READY`**

Both deterministic lanes and both initial live lanes are `EVALUABLE` on the shared smoke fixture
with real comparison metrics observed. No local shared-path repair was required.

## Conditional production repair

**None.** No base-failing reproducer identified a defect in `temporal_shadow_extraction.py` or
`temporal_shadow_prompt_calibration.py`.

## Successor gate

`GROUNDING_PATH_READY` unlocks consideration of fresh V14 holdout + Adv V12 cohort authoring in a
**separate** successor slice. This report does **not** authorize `tl01h-v1`, prompt mutation,
promotion, Kernel/graph writes, projection, or UI work.

## Verification commands (author-local)

```text
uv run pytest -q tests/test_temporal_shadow_grounding_path.py          → 18 passed
uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py       → passed (suite)
uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py     → passed (suite)
uv run ruff check evals/graph_memory_layer/temporal_shadow_grounding_path.py \
                 tests/test_temporal_shadow_grounding_path.py           → All checks passed!
deterministic CLI → control/candidate EVALUABLE, provider calls 0
live CLI (opt-in) → control/candidate EVALUABLE, provider calls 2, overall GROUNDING_PATH_READY
```

Evidence provenance: author-local deterministic replay + author-local provider-observed live smoke
(initial phase only; budget 2/4 calls spent).
