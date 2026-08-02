# REPORT — TL01 Shared Source-Phrase Grounding-Path Recovery

**Status:** Evidence-bound diagnostic READY under frozen contract; global live budget **4/4 exhausted**  
**Handoff:** `Docs/Plans/HANDOFF-pr488-tl01-grounding-path-recovery.md`  
**Fixture:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/`  
**Expected phrase:** `the brass moth struck the north bell exactly twice`  
**Canonical budget ledger:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/provider-budget-ledger.json`

## Authority / provenance gate

| Item | Value |
|---|---|
| Shared clean implementation SHA (det + live) | `46158038c8f29c1b6fbaba70039a71bb5cf6f063` |
| Global provider budget | **4/4 spent — no further live calls authorized** |
| Budget enforcement | Canonical fixture ledger only; missing/alternate paths rejected; `total_calls` reconciled to entries |
| PR #486 | Open draft (operator override to keep one PR) |

**Successor unlock (V14 / Adv V12 / `tl01h-v1`) remains blocked until this report merges to `main`.**

## Scope

Diagnostic-only paired smoke (not promotion authority). No production repair. Frozen
prompt hashes, packet version (`tl01c-packet-v1`), and renderer identity unchanged.

`provider-budget-ledger.json` is a review-driven path outside the original exact
allowlist; it is required to enforce the handoff §6.10 global call budget across
invocations.

## Review repairs (cumulative)

| Finding | Fix |
|---|---|
| Empty refs → owned fallback | `EVIDENCE_OWNERSHIP_MISMATCH` |
| Live-only / bare-enum READY | String triage never READY |
| Failed attempts uncharged | Charge before delegate |
| `transport_accepted` contradictions | False for provider/transport failures |
| Malformed raw batch crash | Shape guards → `TRANSPORT_REJECTED` |
| Alternate/missing ledger resets budget | Canonical path only; missing fails closed; totals reconcile to entries |
| READY equality without frozen authority | Exact `tl01f-v1`/`tl01g-v1` + frozen SHA256s, packet/renderer constants, shared clean SHA, nested lane/run-mode, success fields |

## Provider-call budget (global, §6.10)

| Entry | SHA | Calls | Response IDs |
|---|---|---|---|
| Historical pre-repair (`initial`) | `83917009…` | 2 | `resp_0207dffb…`, `resp_07fc478c…` |
| Post-fix (`post_fix`) | `46158038…` | 2 | `resp_0b4be0ad…`, `resp_02052a11…` |
| **Total** | | **4 / 4** | |

Remaining: **0**. Live mode binds only to the canonical ledger path under the smoke
fixture; a fifth pair cannot invent a new filename or copy cases elsewhere to reset
the counter. Budget amendment requires a governed edit of that ledger (not an
alternate path).

## Frozen identity guards

| Item | Value | Changed? |
|---|---|---|
| Control prompt `tl01f-v1` SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` | No |
| Candidate prompt `tl01g-v1` SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` | No |
| Packet version | `tl01c-packet-v1` | No |
| Renderer | `render_temporal_shadow_user_content_v2` | No |
| Live model | `gpt-5.4-mini` | N/A |

## Deterministic + live evidence (SHA `46158038…`)

| Mode | Lane | Result | Metrics | Success fields |
|---|---|---|---|---|
| deterministic | control `tl01f-v1` | `EVALUABLE` | true | transport/owned_match/phrase/overlay OK |
| deterministic | candidate `tl01g-v1` | `EVALUABLE` | true | same |
| live | control `tl01f-v1` | `EVALUABLE` | true | `resp_0b4be0ad…` |
| live | candidate `tl01g-v1` | `EVALUABLE` | true | `resp_02052a11…` |

## Overall conclusion (evidence-bound frozen contract)

**`GROUNDING_PATH_READY`**

Computed by `combine_paired_summary_conclusions` on author-local paired summaries
from the same clean SHA `46158038…`, requiring frozen prompt identities/hashes,
authoritative packet/renderer constants, nested lane/run-mode identity, shared
implementation SHA, and EVALUABLE success fields (`transport_accepted`,
`owned_evidence_check=owned_match`, `phrase_match`, owned returned refs, no
production error, overlay ID, metrics).

`prompt_sha256="deadbeef"` (or any non-frozen hash) cannot unlock READY.

## Conditional production repair

**None.**

## Successor gate

**Blocked until merge to `main`.** No further live smokes without governed ledger
amendment (4/4).

## Verification commands (author-local)

```text
uv run pytest -q tests/test_temporal_shadow_grounding_path.py          → 44 passed
uv run ruff check evals/graph_memory_layer/temporal_shadow_grounding_path.py \
                 tests/test_temporal_shadow_grounding_path.py           → All checks passed!
canonical ledger total_calls reconciled → 4 (remaining 0)
alternate --budget-ledger path → rejected
combine(det@46158038, live@46158038) → GROUNDING_PATH_READY
```
