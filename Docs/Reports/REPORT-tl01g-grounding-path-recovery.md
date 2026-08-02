# REPORT — TL01 Shared Source-Phrase Grounding-Path Recovery

**Status:** Evidence-bound diagnostic READY; global live budget **4/4 exhausted**  
**Handoff:** `Docs/Plans/HANDOFF-pr488-tl01-grounding-path-recovery.md`  
**Fixture:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/`  
**Expected phrase:** `the brass moth struck the north bell exactly twice`  
**Budget ledger:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/provider-budget-ledger.json`

## Authority / provenance gate

| Item | Value |
|---|---|
| Authoritative live-execution SHA | `46158038c8f29c1b6fbaba70039a71bb5cf6f063` (clean) |
| Global provider budget | **4/4 spent — no further live calls authorized** |
| PR #486 | Still open draft (operator override to keep one PR) |
| Prior enum-only READY | **Revoked** — READY now requires `combine_paired_*` identity binding |

**Successor unlock (V14 / Adv V12 / `tl01h-v1`) remains blocked until this report merges to `main`.**

## Scope

Diagnostic-only paired smoke (not promotion authority) exercising production
`run_temporal_shadow_extraction` through frozen `tl01f-v1` and `tl01g-v1` on one
shared assertion/evidence fixture. No production repair applied. Frozen prompt
hashes, packet version (`tl01c-packet-v1`), and renderer identity unchanged.

## Review repairs

### On `83917009` (first blocking review)

| Finding | Fix |
|---|---|
| Empty refs fell back to owned refs | Absent/empty → `EVIDENCE_OWNERSHIP_MISMATCH` |
| Live-only READY / provider→phrase mis-map | String triage never READY; provider → unresolved |
| Failed attempts uncharged | Charge before delegate |
| `transport_accepted` contradictions | False for provider/transport failures |

### On `fca35289` (second blocking review)

| Finding | Fix |
|---|---|
| READY from four bare `EVALUABLE` strings | `compute_overall_conclusion` never returns READY; `combine_paired_diagnostic_conclusions` / `combine_paired_summary_conclusions` require shared assertion/evidence/phrase/span/packet/renderer, cross-mode case digests + prompts, live clean SHA, metrics, response IDs, and ≥2 live calls |
| 4/4 budget unreported / unenforceable across invocations | Persistent `provider-budget-ledger.json`; live mode requires ledger and fail-closes when remaining &lt; phase need; report states **4/4** |
| Malformed raw batch crashed observer | Shape guards on annotations / entries / `evidence_ref_ids`; malformed → `TRANSPORT_REJECTED` without TypeError |

## Provider-call budget (global, §6.10)

| Entry | SHA | Calls | Response IDs |
|---|---|---|---|
| Historical pre-repair (`initial`) | `83917009…` | 2 | `resp_0207dffb…`, `resp_07fc478c…` |
| Post-fix (`post_fix`) | `46158038…` | 2 | `resp_0b4be0ad…`, `resp_02052a11…` |
| **Total** | | **4 / 4** | |

Remaining: **0**. Further live invocations are unauthorized without an explicit operator
budget amendment. Enforcement is the on-disk ledger (not a per-process counter).

## Frozen identity guards

| Item | Value | Changed? |
|---|---|---|
| Control prompt `tl01f-v1` SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` | No |
| Candidate prompt `tl01g-v1` SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` | No |
| Packet version | `tl01c-packet-v1` | No |
| Renderer | `render_temporal_shadow_user_content_v2` | No |
| Live model | `gpt-5.4-mini` | N/A |

No V14 / Adv V12 directories created. Retired cohorts untouched.

## Deterministic lane results

| Lane | Prompt | Lane result | Metrics present |
|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | true |
| candidate | `tl01g-v1` | `EVALUABLE` | true |

Provider calls: **0**. Single-mode overall: `UNRESOLVED_DIAGNOSTIC_GAP`.

## Live lane results (clean SHA `46158038…`)

| Lane | Prompt | Lane result | Provider response ID | Metrics present |
|---|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | `resp_0b4be0ad599b8170006a6f5cd725dc81959c76796092286538` | true |
| candidate | `tl01g-v1` | `EVALUABLE` | `resp_02052a11ad001b49006a6f5cd964a88196a303d6fea79c5f35` | true |

This pair spent the final 2 calls of the global 4-call budget.

## Overall conclusion (evidence-bound)

**`GROUNDING_PATH_READY`**

Computed by `combine_paired_summary_conclusions(deterministic_summary, live_summary)`
against saved paired-summary traces sharing:

- assertion `assertion:b8a9e88438e5c6a5`
- evidence `evidence:tl01-grounding-smoke-v1:bell-strike`
- phrase / resolved-span digest / packet / renderer
- cross-mode case digests and prompt identities
- live clean repository SHA `46158038…`, model `gpt-5.4-mini`, metrics present, response IDs

Bare `compute_overall_conclusion(EVALUABLE×4)` returns `UNRESOLVED_DIAGNOSTIC_GAP`
and cannot unlock READY.

## Conditional production repair

**None.**

## Successor gate

**Blocked until merge to `main`.** Diagnostic READY does not authorize V14 / Adv V12 /
`tl01h-v1`. **No further live grounding smokes** on this fixture without a new budget
authorization (ledger already at 4/4).

## Verification commands (author-local)

```text
uv run pytest -q tests/test_temporal_shadow_grounding_path.py          → 36 passed
uv run ruff check evals/graph_memory_layer/temporal_shadow_grounding_path.py \
                 tests/test_temporal_shadow_grounding_path.py           → All checks passed!
deterministic CLI → EVALUABLE / EVALUABLE, calls 0, overall UNRESOLVED_DIAGNOSTIC_GAP
combine_paired_summary_conclusions(det, live@46158038) → GROUNDING_PATH_READY
provider-budget-ledger.json total_calls → 4 (remaining 0)
```
