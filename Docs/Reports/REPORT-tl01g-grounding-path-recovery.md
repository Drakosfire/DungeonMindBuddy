# REPORT — TL01 Shared Source-Phrase Grounding-Path Recovery

**Status:** Post-repair diagnostic evidence bound to clean execution SHA  
**Handoff:** `Docs/Plans/HANDOFF-pr488-tl01-grounding-path-recovery.md`  
**Fixture:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/`  
**Expected phrase:** `the brass moth struck the north bell exactly twice`

## Authority / provenance gate

| Item | Value |
|---|---|
| Repair commit / live-execution SHA | `46158038c8f29c1b6fbaba70039a71bb5cf6f063` (clean; `git status --porcelain` empty at execution) |
| PR #486 | Still open draft (operator override to keep one PR; handoff’s “merged jumpstart on `origin/main` first” dispatch was not used) |
| Prior READY at `83917009…` | **Revoked** — lacked exact clean live-execution SHA and had classifier/accounting defects |

Combined lane evidence on the repair SHA satisfies §6.8 diagnostic readiness below. **Successor unlock (V14 / Adv V12 / `tl01h-v1`) remains blocked until this report merges to `main`.** Draft-PR evidence alone does not authorize cohort authoring.

## Scope

Diagnostic-only paired smoke (not promotion authority) exercising production
`run_temporal_shadow_extraction` through frozen `tl01f-v1` and `tl01g-v1` on one
shared assertion/evidence fixture.

No production repair was required or applied. Frozen prompt hashes, packet version
(`tl01c-packet-v1`), and renderer identity (`render_temporal_shadow_user_content_v2`) are
unchanged.

## Review repair (blocking findings on `83917009`)

| Finding | Fix |
|---|---|
| Empty returned `evidence_ref_ids` fell back to owned refs | No fallback; absent/empty refs → `EVIDENCE_OWNERSHIP_MISMATCH` |
| `compute_overall_conclusion` could READY from live-only; mis-mapped provider fail | Requires explicit deterministic **and** live `EVALUABLE`; provider execution → `UNRESOLVED_DIAGNOSTIC_GAP`; phrase-fidelity requires deterministic proof |
| Failed provider attempts not charged | Ledger increments **before** delegate; refusals/errors consume budget |
| `transport_accepted` contradicted lane result | `False` for `invalid_model_output` and provider execution failures |

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

## Deterministic lane results (SHA `46158038…`)

| Lane | Prompt | Lane result | Metrics present |
|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | true |
| candidate | `tl01g-v1` | `EVALUABLE` | true |

Provider calls: **0**. Single-mode overall: `UNRESOLVED_DIAGNOSTIC_GAP` (live evidence required).

## Live lane results (same clean SHA `46158038…`)

| Lane | Prompt | Lane result | Provider response ID | Metrics present |
|---|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | `resp_0b4be0ad599b8170006a6f5cd725dc81959c76796092286538` | true |
| candidate | `tl01g-v1` | `EVALUABLE` | `resp_02052a11ad001b49006a6f5cd964a88196a303d6fea79c5f35` | true |

Provider calls: **2** (one control + one candidate; no retries). Trace
`repository_sha` matches execution HEAD exactly (no `+dirty` suffix).

## Overall conclusion (combined deterministic + live)

**`GROUNDING_PATH_READY`** (diagnostic path on SHA `46158038c8f29c1b6fbaba70039a71bb5cf6f063`)

Computed via `compute_overall_conclusion(deterministic_*=EVALUABLE, live_*=EVALUABLE)`.
Single-mode live CLI correctly prints `UNRESOLVED_DIAGNOSTIC_GAP` until deterministic
evidence is combined at report time.

## Conditional production repair

**None.**

## Successor gate

**Blocked for cohort authoring until merge to `main`.** Diagnostic READY on this draft
branch does not unlock V14 / Adv V12 / `tl01h-v1`. After merge, a successor slice may
author fresh cohorts; it still must not mutate frozen prompts without isolated
prompt-defect evidence.

## Historical (revoked) live observation

Pre-repair response IDs under `83917009…` are not provenance-bound and must not be
cited as readiness authority:
`resp_0207dffb…` / `resp_07fc478c…`.

## Verification commands (author-local)

```text
uv run pytest -q tests/test_temporal_shadow_grounding_path.py          → 28 passed
uv run ruff check evals/graph_memory_layer/temporal_shadow_grounding_path.py \
                 tests/test_temporal_shadow_grounding_path.py           → All checks passed!
deterministic CLI @ 46158038 → EVALUABLE / EVALUABLE, calls 0, overall UNRESOLVED_DIAGNOSTIC_GAP
live CLI @ 46158038 (opt-in) → EVALUABLE / EVALUABLE, calls 2, overall UNRESOLVED_DIAGNOSTIC_GAP
combined conclusion           → GROUNDING_PATH_READY
```
