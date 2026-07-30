# Temporal Shadow Extraction V1 (TL01B)

**Status:** Implemented (evaluation seam)  
**Authority modules:** `src/graph_memory/temporal_shadow_extraction.py`, `src/graph_memory/temporal_shadow_extraction_schema.py`  
**CLI:** `python -m graph_memory.temporal_shadow_extraction_cli`  
**Depends on:** `CONTRACT-temporal-shadow-overlay-v1.md` (TL01), `CONTRACT-temporal-envelope-v1.md` (TL00)

## Purpose

Run **evidence-bound model shadow temporal extraction** on a **sealed case**:

```text
sealed case JSON
→ candidate-only GraphContribution + evidence registry digests
→ assertion evidence packets (snippets only)
→ OpenAI Responses API strict JSON batch
→ deterministic grounding + TL01 overlay assembly
→ shadow preview
→ gold overlay comparison
```

No graph writes, no merge, no world projection, no kernel changes.

## Non-authoritative status

| Artifact | Authoritative? |
| --- | --- |
| Model annotation batch | No — transport only |
| Assembled `TemporalAnnotationOverlayV1` (`producer.kind=model_shadow`) | No — TL01 sidecar |
| `TemporalShadowPreviewV1` | No — derived report |
| Sealed case / gold overlay | Evaluation fixtures only |
| Base `GraphContribution` in case | Read-only input |

## Sealed case contract (`dmb_temporal_shadow_extraction_case_v1`)

Required fields:

- `case_id`, `prompt_version` (`tl01b-v1`)
- `base_contribution_path` — repo-relative, candidate-only contribution JSON
- `base_contribution_sha256` — digest of that file bytes
- `gold_overlay_path` — repo-relative TL01 gold overlay
- `selected_assertion_ids` — non-empty, unique, subset of base candidates, canonical IDs
- `evidence_registry` — entries for all owned evidence on selected assertions
- `snippet_max_chars` — cohort uses `2000`

Path rules (fail closed):

- Repo-relative only; reject absolute paths and `..`
- Re-verify contribution and source artifact `content_sha256` at load time

## Evidence packets

Built per selected assertion from `explicit_assertion_evidence_ref_ids` and the case registry:

- Load source markdown into `SourceArtifactText`
- Resolve spans via `resolve_source_span_ref` / `analyze_evidence_resolution`
- Fail on resolution blockers (`evidence_unresolved`)
- Packet includes semantic assertion fields + owned evidence snippets (no full documents)

## Model batch (`dmb_temporal_model_annotation_batch_v1`)

Produced via OpenAI **Responses API** with `temporal_model_annotation_batch_text_format()`:

- `format.type == json_schema`, `strict: true`
- One transport annotation per selected `base_assertion_id`
- Transport temporal points require all keys; unused fields are JSON `null`

System rules (summary):

- **Never** promote recap/source session to `occurrence_time` or `valid_time` by default
- `resolved` requires grounded `occurrence_time` and/or `valid_time`
- `not_applicable` / `ambiguous` / `unresolved` follow TL01 overlay constraints

## Grounding (fail closed)

After transport validation:

1. Target set must equal `selected_assertion_ids` exactly (no duplicates)
2. Every `evidence_ref_id` must be owned by the target assertion and present in the packet
3. `resolved` requires a nonblank `source_phrase` that appears verbatim in a cited snippet (whitespace-normalized)
4. When `source_phrase` is non-null for any status (including `not_applicable`), it must be grounded the same way
5. `not_applicable` requires a nonblank diagnostic explanation
6. Convert transport → `TemporalAssertionAnnotationV1` via TL00 temporal models
7. Any violation → `TemporalShadowExtractionError` (no silent repair)

Stable `annotation_id` via `compute_temporal_annotation_id` → `temporal-annotation:{16hex}`
(includes `case_id`, `model_id`, and executed `prompt_version`).

Sealed cases also require:

- unique `evidence_ref_id` values (no last-wins remapping)
- agreeing metadata for repeated `source_artifact_id` values
- `gold_overlay_sha256` plus gold binding (`human_gold`, matching base contribution ID/digest, exact selected target set)
- supported `prompt_version` only (`tl01b-v1`); run manifest records the executed version

## Overlay assembly

Producer:

- `kind=model_shadow`
- `name=temporal-shadow-extractor`
- `version=<executed prompt version>`

Then `compute_temporal_overlay_id`, `load_temporal_annotation_overlay`, `build_temporal_shadow_preview` (TL01).

## Comparison (`dmb_temporal_shadow_comparison_v1`)

Semantic comparison only. Equality uses:

- interpretation status
- occurrence-time payload
- valid-time payload
- normalized (sorted) evidence selection

Ignored for equality: annotation ID, producer identity, diagnostic wording, source-phrase wording, extraction confidence.

Per-assertion classifications:

- `exact_match`, `safe_under_resolution`, `unsafe_over_resolution`, `wrong_temporal_lane`, `wrong_temporal_value`, `status_mismatch`, `semantic_mismatch`, `missing_prediction`, `extra_prediction`

Safety metrics (minimum):

- `source_to_occurrence_false_positives` — predicted occurrence contains the assertion’s **derived source-time point** and gold does not contain that exact point (null gold, different session, relative/textual/campaign-date, or different interval boundary). Unrelated invented sessions are ordinary wrong values, not source leakage. Legitimate same-session occurrence matching gold is not leakage.
- `source_to_valid_time_false_positives` — predicted valid interval uses the derived source-time point as start or end and gold does not use that exact point
- `unsupported_resolved_annotations` — resolved when gold is ambiguous/unresolved/not_applicable
- `foreign_evidence_attempts` — fail-closed pre-overlay count of cited evidence IDs that are not both owned by the assertion (`explicit_assertion_evidence_ref_ids`) **and** present in that assertion’s prompt packet. Always `0` on successful comparisons; non-zero values appear only on `grounding_failure` manifests
- `evidence_selection_mismatch_count` — predicted vs gold chose different assertion-owned evidence after normalization (not foreign evidence)
- `ungrounded_source_phrases` / `invalid_temporal_payloads` — zero on successful comparisons (fail-closed before overlay)

Quality metrics (minimum):

- `status_accuracy`
- `exact_semantic_match_count` / `resolved_exact_match_count`
- `safe_under_resolution_count`
- `ambiguous_or_unresolved_count`
- `not_applicable_accuracy`

Comparator API: `compare_temporal_overlays(predicted, gold, *, base_contribution=...)` or an immutable `assertion_source_times` map. Source time is derived only through TL01 `derive_assertion_source_time`; skipped/unsafe derivation fails closed (`comparison_source_time_failure`).

Verdict enum:

- `pass` — all gold targets exact match
- `partial` — mismatches without missing/extra/unsafe over-resolution
- `fail` — missing/extra predictions or unsafe over-resolution

Evaluation verdict separately encodes promotion readiness (`SAFE_FOR_NEXT_EXPERIMENT` / `ITERATE_PROMPT` / …).

## Run artifacts

Written under `--output-dir` (no full prompts or source documents):

- `run-manifest.json`
- `model-output.json`
- `overlay.json`
- `preview.json`
- `comparison.json`
- `provider-metadata.json`

## CLI

```bash
uv run python -m graph_memory.temporal_shadow_extraction_cli \
  --case evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json \
  --output-dir evals/graph_memory_layer/artifacts/temporal_shadow_cohort/latest \
  [--model-id MODEL] [--overwrite]
```

## Typed errors

`TemporalShadowExtractionError` codes include:

`invalid_case`, `path_escape`, `digest_mismatch`, `selected_assertion_invalid`, `evidence_unresolved`, `target_set_mismatch`, `grounding_failure`, `provider_refusal`, `provider_incomplete`, `provider_error`, `invalid_model_output`, `overlay_assembly_failed`

## Prohibited

- Mutating `src/graph_memory/kernel/**`, TL01 `temporal_shadow.py`, graph stores, or promotion paths
- Writing model output into durable graph contributions
