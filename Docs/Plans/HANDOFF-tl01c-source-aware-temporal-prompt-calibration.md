# HANDOFF — TL01C: Source-Aware Temporal Prompt Calibration

**Created:** 2026-07-29
**Project:** DungeonBuddy / DungeonMindBuddy
**Repository:** `Drakosfire/DungeonMindBuddy`
**Status:** ACTIVE — Timeline evaluation slice
**Required dependency:** PR `#452`, merged as `6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6`
**Required implementation base:** `origin/main` containing that merge
**Branch:** `feat/tl01c-temporal-prompt-calibration`
**Expected PR count:** one
**Operating mode:** Eval-only prompt and input-context calibration
**Authoritative graph writes:** forbidden
**TL00/TL01 contract changes:** forbidden
**Timeline API, UI, and participant roles:** forbidden

---

## §0 Mission

Calibrate the temporal shadow extractor so it can distinguish source provenance from fictional occurrence time, persistent valid time, and non-temporal or ambiguous assertions — without modifying the TL01B evaluator, the temporal kernel, or graph authority.

```text
frozen TL01B baseline prompt
+ versioned source-aware candidate prompt
+ explicitly labeled derived source-time context
+ sealed development cohort
+ sealed holdout cohort
+ repeated paired provider runs
→ trustworthy prompt-quality decision
```

## Frozen dependencies

Do not change: TemporalEnvelopeV1 / TemporalAnnotationOverlayV1 / TemporalShadowPreviewV1 /
`compare_temporal_overlays` classifications / grounding / evidence ownership / TL01B output publication.

Baseline `tl01b-v1` must remain immutable (instructions + V1 packet renderer).

## Implementation map

| Piece | Location |
| --- | --- |
| Prompt registry + packet V2 | `src/graph_memory/temporal_shadow_extraction.py` |
| Calibration schema | `src/graph_memory/temporal_shadow_extraction_schema.py` |
| Development case (frozen) | `evals/graph_memory_layer/examples/temporal_shadow_cohort/` |
| Candidate case | `.../temporal_shadow_cohort/temporal-case-tl01c.json` |
| Holdout | `evals/graph_memory_layer/examples/temporal_shadow_holdout/` |
| Adversarial synthetic | `evals/graph_memory_layer/examples/temporal_shadow_adversarial/` |
| Calibration runner | `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` |
| Contract | `Docs/Design/CONTRACT-temporal-prompt-calibration-v1.md` |
| Report | `Docs/Reports/REPORT-tl01c-temporal-prompt-calibration.md` |

## Candidate prompt rules (summary)

1. Annotate the assertion proposition, not every event in evidence.
2. Choose lane: occurrence / valid_time / not_applicable / ambiguous / unresolved.
3. `source_context.source_time` is provenance_only; reuse only when narrated same-episode event/state boundary.
4. Explicit alternate fiction time overrides source episode.
5. Prefer ambiguity/unresolved/not_applicable over unsupported precision.

## Calibration decisions

`PROMPT_READY_FOR_BROADER_SHADOW` | `ITERATE_PROMPT` | `BLOCKED_BY_INPUT_REPRESENTATION` |
`BLOCKED_BY_EVIDENCE` | `BLOCKED_BY_CONTRACT` | `PROVIDER_FAILURE`

Do not modify the TL01B `EvaluationVerdict` enum.

## Live proof order

Seal (prompt + holdout) → development paired 3× → freeze confirmation → holdout paired 3× →
adversarial 3× → aggregate → report.

## Explicit non-goals

No TL00/TL01 schema changes; no authoritative extraction; no participant roles; no Timeline API/UI;
no graph writes.

## Acceptance (abbrev)

PR 452 in ancestry; baseline byte-stable; registry with fail-closed unknown versions; packet V2
provenance-only source_context; holdout sealed before candidate holdout run; 3 repetitions per
required pair; aggregate reproducible; focused tests + `git diff --check` clean.
