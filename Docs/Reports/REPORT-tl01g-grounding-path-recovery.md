# REPORT — TL01 Shared Source-Phrase Grounding-Path Recovery

**Status:** Classification/accounting defects fixed; prior `GROUNDING_PATH_READY` **revoked** (not authoritative)  
**Handoff:** `Docs/Plans/HANDOFF-pr488-tl01-grounding-path-recovery.md`  
**Fixture:** `evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1/`  
**Expected phrase:** `the brass moth struck the north bell exactly twice`

## Authority / provenance gate

PR #486 remains an open draft. Implementation was continued on this branch under an
operator override to keep a single PR, which **deviates** from the handoff’s
“immutable `origin/main` containing merged jumpstart + handoff” dispatch gate.

Consequently:

- The prior report claim of `GROUNDING_PATH_READY` at commit `83917009…` is **not
  authoritative** and **must not unlock V14 / Adv V12**.
- Live response IDs recorded under that head are retained below as historical
  observation only; they are **not** bound to a post-fix clean execution SHA.
- A durable `GROUNDING_PATH_READY` requires: (1) both deterministic lanes
  `EVALUABLE`, (2) both live lanes `EVALUABLE`, (3) exact clean repository SHA of
  the committed diagnostic that produced the live response IDs, and (4) merge of
  that evidence onto `main` before successor cohort authoring.

**Live-execution SHA (post-fix):** _pending — re-run live only after this repair
commit is clean and record the exact `git rev-parse HEAD` here with response IDs._

## Scope

This slice adds a diagnostic-only paired smoke (not promotion authority) exercising the
production `run_temporal_shadow_extraction` path through frozen `tl01f-v1` and `tl01g-v1`
prompt identities on one shared assertion/evidence fixture.

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

## Deterministic lane results (`--mode deterministic --phase initial`)

| Lane | Prompt | Lane result | Metrics present |
|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` | true (`exact_match_count=1`) |
| candidate | `tl01g-v1` | `EVALUABLE` | true (`exact_match_count=1`) |

Provider calls: **0** (deterministic fake replay; no live delegate counted).

Single-mode overall classifier output: `UNRESOLVED_DIAGNOSTIC_GAP` (live evidence +
combined conclusion required by §6.8).

## Historical live observation (pre-repair; not provenance-bound)

Observed under dirty/pre-repair workflow on draft PR #486 (response IDs only; **do not**
treat as readiness authority):

| Lane | Prompt | Lane result | Provider response ID |
|---|---|---|---|
| control | `tl01f-v1` | `EVALUABLE` (historical) | `resp_0207dffb227fbed2006a6ed36f4bbc81949cfa5214373f1ac0` |
| candidate | `tl01g-v1` | `EVALUABLE` (historical) | `resp_07fc478c5452975c006a6ed371c7188196af0bfb23a17d04ae` |

Exact clean repository SHA that produced those response IDs was **not** recorded.

## Overall conclusion

**`UNRESOLVED_DIAGNOSTIC_GAP`** (authoritative disposition until post-fix live re-proof)

Reasons:

1. Prior READY claim lacked an exact clean live-execution SHA.
2. Classifier/accounting defects above invalidate readiness until re-proven.
3. Combined conclusion API now refuses READY without both deterministic and live
   `EVALUABLE` evidence supplied together.

## Conditional production repair

**None.** No base-failing reproducer identified a defect in `temporal_shadow_extraction.py` or
`temporal_shadow_prompt_calibration.py`.

## Successor gate

**Blocked.** V14 / Adv V12 / `tl01h-v1` remain forbidden until a later report revision binds
post-fix live evidence to an exact clean execution SHA and that evidence merges to
`main`. Happy-path phrase grounding in historical live smoke is encouraging but not
sufficient.

## Verification commands (author-local)

```text
uv run pytest -q tests/test_temporal_shadow_grounding_path.py
uv run ruff check evals/graph_memory_layer/temporal_shadow_grounding_path.py \
                 tests/test_temporal_shadow_grounding_path.py
deterministic CLI → control/candidate EVALUABLE, provider calls 0,
                    overall UNRESOLVED_DIAGNOSTIC_GAP
```
