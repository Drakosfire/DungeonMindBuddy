# Temporal Prompt Calibration V1 (TL01C)

**Status:** Implemented (evaluation seam)  
**Authority modules:** `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`, `src/graph_memory/temporal_shadow_extraction_schema.py`  
**CLI:** `uv run python evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`  
**Depends on:** `CONTRACT-temporal-shadow-extraction-v1.md` (TL01B), TL01B handoff §16 verdict semantics

## Purpose

Compare **frozen TL01B baseline** prompt behavior against **candidate TL01C source-aware** prompt behavior across development, holdout, and adversarial cohorts. Produce a **calibration aggregate** with min/median/max metrics, per-assertion repetition stability, and a **promotion decision** for broader shadow rollout.

No graph writes, no kernel changes, no live provider calls required for unit tests (`--fake`).

## Frozen baseline

- Prompt version: `tl01b-v1`
- Instructions: `TL01B_BASELINE_INSTRUCTIONS` (immutable fingerprint via `baseline_prompt_fingerprint()`)
- Packet: `tl01b-packet-v1` (no `source_context`)
- Baseline lane runs: development sealed case + holdout TL01B mirror case

Baseline exists to detect prompt drift and provide an A/B control during calibration.

## Prompt registry

Registry lives in `graph_memory.temporal_shadow_extraction.TEMPORAL_PROMPT_SPECS`:

| Version | Packet | User content renderer |
| --- | --- | --- |
| `tl01b-v1` | `tl01b-packet-v1` | `render_temporal_shadow_user_content_v1` |
| `tl01c-v1` | `tl01c-packet-v1` | `render_temporal_shadow_user_content_v2` |

Unknown `prompt_version` in a sealed case fails closed before provider invocation (`unsupported_prompt_version`).

## Packet V2 source_context

TL01C packets add `source_context` per assertion:

```json
{
  "source_time": { "...": "TemporalPointV1 transport or null" },
  "derivation": "single_session | ...",
  "semantic_authority": "provenance_only"
}
```

Built only via TL01 `derive_assertion_source_time`. Unsafe or skipped derivation fails closed at packet build time.

V1 packets omit `source_context` entirely.

## Candidate decision sequence

TL01C instructions require this per-assertion order:

1. Identify proposition from assertion metadata (evidence must not override proposition type)
2. Choose temporal lane: occurrence, valid, not_applicable, ambiguous, unresolved
3. Treat `source_context.source_time` as **provenance_only** — never auto-copy into occurrence/valid
4. Normalize conservatively; preserve relative/textual incompleteness
5. Ground per TL01B rules (resolved requires snippet-grounded payloads)

## Development vs holdout

| Cohort | Role | Assertion IDs | Evidence IDs |
| --- | --- | --- | --- |
| Development | Sealed TL01B/TL01C mirror on shared base contribution | Overlap by design (same 6 assertions) | TL01B-prefixed registry |
| Holdout | Independent sealed contribution + gold | **Must not overlap** development assertion IDs | **Must not overlap** development evidence IDs |

Holdout seal SHA256 (`holdout_seal_sha256`) is recorded on the aggregate — default digest of `--candidate-holdout-case` bytes; override via `--holdout-seal-sha`.

## Synthetic adversarial separation

Adversarial cohort uses **synthetic markdown sources** under `examples/temporal_shadow_adversarial/sources/` (source≠occurrence, valid-time transitions, ambiguous-relative patterns). Few-shot examples in TL01C instructions use **invented campaigns only** — no Stafl, Caelynn, Lysandra, Maelthor, Hybrid, Copper and Quartz terms.

Adversarial runs are **candidate lane only** and contribute to unsafe-over-resolution totals.

## Calibration aggregate

Schema: `dmb_temporal_prompt_calibration_v1` (`TemporalPromptCalibrationAggregateV1`)

Recorded fields:

- `calibration_id`, `repository_sha`, `model_id`, `repetitions`
- `baseline_prompt_sha256`, `candidate_prompt_sha256`, `holdout_seal_sha256`
- Per-lane slices with cohort aggregates
- `decision`, `diagnostics`

Per cohort aggregate includes:

- `exact_match` / `resolved_exact_match` min/median/max across repetitions
- `min_status_accuracy`, `min_not_applicable_accuracy`
- Totals: unsafe over-resolution, source leakage FPs, evidence selection mismatches, provider failures, grounding failures, invalid payloads
- `assertion_stability`: classification and predicted-status distributions per assertion across repetitions

Run layout:

```text
calibration/
  baseline/development/run-01/ ...
  baseline/holdout/run-01/
  candidate/development/run-01/
  candidate/holdout/run-01/
  candidate/adversarial/run-01/
  aggregate.json
```

Failed repetitions remain on disk (`failure-manifest.json`); aggregate counts include them.

## Decision thresholds

Encoded as named constants in `temporal_shadow_prompt_calibration.py` (`compute_calibration_decision`). Priority order:

| Decision | Condition |
| --- | --- |
| `PROVIDER_FAILURE` | Any candidate repetition with provider failure code |
| `BLOCKED_BY_CONTRACT` | Any candidate invalid temporal payload total > 0 |
| `BLOCKED_BY_EVIDENCE` | Any candidate grounding failure |
| `BLOCKED_BY_INPUT_REPRESENTATION` | `total_wrong_temporal_value >= 2` with zero wrong lane and zero status mismatch (correct status/lane, wrong payload — input representation heuristic) |
| `PROMPT_READY_FOR_BROADER_SHADOW` | Zero candidate unsafe over-resolution **across all cohorts and repetitions**; zero source leakage FPs; zero candidate failures; min status accuracy ≥ 0.85; min not-applicable accuracy ≥ 1.0; holdout min exact/resolution ratios ≥ 1.0 |
| `ITERATE_PROMPT` | Default when quality insufficient or unsafe behavior present |

**Non-negotiable:** one successful repetition cannot hide unsafe repetitions. Any unsafe over-resolution in any candidate run blocks `PROMPT_READY_FOR_BROADER_SHADOW`.

Maps TL01B §16 semantics:

- `SAFE_FOR_NEXT_EXPERIMENT` → `PROMPT_READY_FOR_BROADER_SHADOW`
- Other TL01B blocked/failure verdicts map directly except `BLOCKED_BY_INPUT_REPRESENTATION` (TL01C-specific)

## Non-goals

- Publishing temporal data to the graph
- Changing TL00 temporal kernel types
- Replacing per-run TL01B comparison with calibration-only scoring
- Auto-promoting prompt versions without human review of aggregate + artifacts

## Successor decision

When `PROMPT_READY_FOR_BROADER_SHADOW`:

- Broader shadow extraction cohort (beyond sealed development/holdout/adversarial)
- Participant-role / TL02 experimentation per threat-statblock roadmap

When `ITERATE_PROMPT` or blocked:

- Revise TL01C instructions or packet representation
- Re-run calibration with same holdout seal for comparability
