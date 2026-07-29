# Temporal Shadow Overlay V1

**Status:** Implemented (TL01 evaluation seam)  
**Authority module:** `src/graph_memory/temporal_shadow.py`  
**CLI:** `src/graph_memory/temporal_shadow_cli.py`  
**Depends on:** `CONTRACT-temporal-envelope-v1.md` (TL00 substrate)

## Purpose

Provide a strict, evidence-bound **temporal annotation overlay** and a
deterministic **shadow preview** that shows how candidate-only
`GraphContributionAssertion` rows would look if their durable
`temporal_scope` were normalized to `TemporalEnvelopeV1` and optionally
annotated with source-grounded occurrence or valid time.

The preview answers:

```text
existing candidate assertion
+ deterministic source-time derivation
+ optional overlay annotation (resolved / ambiguous / unresolved / not_applicable)
→ shadow temporal_scope
→ shadow assertion_id
→ inspectable before/after report
```

This slice exists for evaluation, gold authoring, and later temporal
producer work. It does **not** change extraction, promotion, merge, or
publication.

## Non-authoritative status

| Artifact | Authoritative? |
| --- | --- |
| `TemporalAnnotationOverlayV1` | No — sidecar input only |
| `TemporalShadowPreviewV1` | No — derived report only |
| Base `GraphContribution` | Unchanged — never mutated by the builder |
| Candidate assertions in the ledger | Unchanged |
| Accepted / published graph state | Untouched |

Shadow output must not be consumable as a `GraphContribution`, must not
enter merge or world projection, and must not imply canon.

## Base contribution binding

Every overlay binds to exactly one **candidate-only** base contribution:

- `base_contribution_id` must equal `contribution.contribution_id`.
- `base_contribution_source_payload_sha256` must equal
  `compute_contribution_source_payload_sha256(contribution)`.

Binding failures raise `TemporalShadowBuildError` with stable codes:

| Code | Meaning |
| --- | --- |
| `base_contribution_id_mismatch` | Overlay points at a different contribution |
| `base_contribution_digest_mismatch` | Source payload changed since overlay authorship |
| `invalid_base_contribution` | Base is not active candidate-only material |

Candidate-only rules (fail closed):

- `status == "active"`.
- Non-empty `candidate_assertions`.
- Empty `accepted_assertions` and `rejected_assertions`.
- Every row has `acceptance_state == "candidate"`.
- Candidate `assertion_id` values are unique within the contribution.
- Each candidate `assertion_id` matches `compute_assertion_id(...)` for that
  row's semantic content (non-canonical IDs fail as
  `invalid_base_contribution`).

The builder never mutates the base contribution object.

## Assertion targeting

- Each annotation targets exactly one `base_assertion_id` present in the
  base contribution.
- At most one annotation per assertion (duplicate targets rejected at overlay
  validation).
- Base contributions with duplicate candidate `assertion_id` values are
  rejected (`invalid_base_contribution`). Assertion identity excludes
  evidence provenance, so two semantically identical rows with different
  evidence can share an ID — that shape is not shadow-safe.
- `annotation_id` values must be unique within the overlay.
- Missing targets raise `annotation_target_not_found`.

`load_temporal_annotation_overlay` always revalidates, including when the
caller already holds a `TemporalAnnotationOverlayV1` instance. Mutated
models and `model_copy(update=...)` results cannot bypass overlay-ID,
duplicate-target, evidence, or status validation.

Overlay identity (`overlay_id`) is deterministic from canonical overlay
content (base IDs, digest, producer, annotations sorted by
`base_assertion_id`). Annotation list order does not affect `overlay_id`.

## Evidence binding

Annotations must cite at least one non-blank, unique `evidence_ref_id`.

During preview build, every cited ID must be **owned** by the target
assertion via `explicit_assertion_evidence_ref_ids` (top-level and embedded
provenance). Subsets of owned evidence are allowed. Foreign IDs raise
`annotation_evidence_not_owned`.

Evidence binding is about **lineage**, not about inventing temporal semantics.

## Interpretation statuses

| Status | Semantic time in annotation | Requirements |
| --- | --- | --- |
| `resolved` | Required (`occurrence_time` and/or `valid_time`) | Normalized V1 extent/interval |
| `ambiguous` | Forbidden | `source_phrase` + non-empty non-blank `diagnostics` |
| `unresolved` | Forbidden | `source_phrase` and/or non-blank `diagnostics` |
| `not_applicable` | Forbidden | Explicit re-attestation that fiction time does not apply |

Diagnostic strings are trimmed; blank-only entries (e.g. `"   "`) are
rejected. Non-`resolved` statuses preserve extraction-facing metadata in row
diagnostics; they do not write `source_phrase` into `temporal_scope`.

## Source-time derivation

`derive_assertion_source_time` maps base assertion provenance and legacy
scope to a V1 `source_time` **without** creating occurrence or valid time.

| Derivation | When |
| --- | --- |
| `legacy_session_scope` | Legacy `{"session_id": ...}` observation scope |
| `existing_v1_source_time` | Schema-tagged envelope already has `source_time` |
| `evidence_session` | No scope / no envelope source; single evidence session |
| `none` | No derivable session |
| `skipped` | Unresolved legacy (`as_of`, unknown schema tag, etc.) |

Conflict rules:

- Multiple distinct evidence sessions → `multiple_source_sessions`.
- Existing V1 or legacy scope session disagrees with sole evidence session →
  `source_time_conflict`.

Campaign scope may backfill `campaign_id` on legacy session source points.

## No source-to-occurrence inference

**Never** set `occurrence_time` or `valid_time` merely because
`source_time` was derived from a session recap or legacy
`temporal_scope.session_id`.

Occurrence and valid time enter the shadow envelope only when:

- a `resolved` annotation supplies them, or
- an existing V1 envelope already carried them (and the annotation does not
  conflict).

## Occurrence-time semantics

`occurrence_time` on a `resolved` annotation is fiction-facing: when the
described event happened. It may equal the source session when explicitly
annotated; equality is not assumed by default.

Conflicts with an existing V1 envelope raise
`conflicting_existing_occurrence_time` or `conflicting_existing_valid_time`.

## Valid-time semantics

`valid_time` on a `resolved` annotation expresses persistent-state intervals
(open or closed). It changes both shadow assertion identity and core temporal
fingerprints when present.

## Semantic versus extraction metadata

These fields affect overlay validation and preview diagnostics only; they
**do not** change shadow assertion identity when the composed
`temporal_scope` is unchanged:

- `source_phrase`
- `extraction_confidence`
- `diagnostics` (annotation-level)
- overlay `producer.name` (changes `overlay_id`, not shadow rows)

Shadow assertion IDs hash the composed durable `temporal_scope` dict via
`compute_assertion_id`, same as production assertions.

## Existing temporal-scope composition

Composition order for each row:

1. Derive `source_time` (or skip row if derivation is `skipped`).
2. Start from existing V1 occurrence/valid if present.
3. Apply `resolved` annotation overrides when compatible.
4. Serialize with `serialize_temporal_envelope`.

Legacy observation session scopes normalize to V1 `source_time` only
(provenance lane). Core semantic projection (occurrence/valid) stays null
unless annotated — so identity may change while core temporal fingerprint
does not.

Unresolved legacy (`session_id` + `as_of`, unrecognized `schema` tags)
produces **skipped** rows and a **partial** preview verdict.

## Shadow identity calculation

For each non-skipped row:

```text
shadow_assertion_id = compute_assertion_id(..., temporal_scope=shadow_scope)
identity_changed = shadow_assertion_id != base_assertion_id
core_temporal_changed = temporal_core_semantic_payload(base) != temporal_core_semantic_payload(shadow)
```

Preview summary counts: derived source times, identity/core changes,
unchanged rows, skipped rows, annotation status histogram.

## Preview schema

`TemporalShadowPreviewV1` (`dmb_temporal_shadow_preview_v1`):

- Binds overlay + base IDs and digest (copied from overlay).
- `verdict`: `complete` if no skipped rows, else `partial`.
- `summary`: aggregate counters.
- `rows`: one entry per base candidate assertion in **base list order**
  (not annotation order).

Row `status`:

| Status | Meaning |
| --- | --- |
| `ok` | Shadow scope and ID computed |
| `skipped` | Source-time derivation skipped (unresolved legacy / unknown schema) |
| `error` | Reserved for future row-level failures (TL01 builder raises before preview on hard errors) |

## Determinism

Given the same candidate contribution and validated overlay:

- `build_temporal_shadow_preview` is pure (no wall clock, no randomness).
- Repeated calls yield identical `model_dump(mode="json", by_alias=True)`.
- Row order follows base assertion order.
- Overlay ID is order-invariant over annotations.

## Failure behavior

Hard failures raise `TemporalShadowBuildError` with a stable `code` and
diagnostics (overlay parse/bind, evidence ownership, source-time conflicts,
semantic conflicts). The CLI maps these to exit code `1` and does not write
output.

Successful builds with skipped rows still return exit code `0` but emit a
stderr warning when `verdict == "partial"`.

Output path protection: existing `--output` without `--overwrite` exits
non-zero (`output_exists`).

## Examples

### Input: legacy session scope + resolved occurrence annotation

**Base assertion** (candidate):

```json
{
  "assertion_kind": "node",
  "acceptance_state": "candidate",
  "temporal_scope": {"session_id": "session-20"},
  "value": {
    "evidence": [
      {
        "evidence_ref_id": "evidence:session-20:recap",
        "session_id": "session-20"
      }
    ]
  },
  "evidence_ref_ids": ["evidence:session-20:recap"]
}
```

**Overlay annotation** (`interpretation_status: resolved`):

```json
{
  "annotation_id": "ann-occurrence-12",
  "base_assertion_id": "<assertion_id>",
  "interpretation_status": "resolved",
  "evidence_ref_ids": ["evidence:session-20:recap"],
  "occurrence_time": {
    "kind": "point",
    "point": {
      "kind": "session",
      "session_id": "session-12",
      "certainty": "explicit"
    }
  }
}
```

**Shadow row** (conceptual):

- `source_time_derivation`: `legacy_session_scope`
- `shadow_temporal_scope.source_time.session_id`: `session-20`
- `shadow_temporal_scope.occurrence_time.point.session_id`: `session-12`
- `identity_changed`: true (raw legacy dict → V1 envelope)
- `core_temporal_changed`: true (occurrence added)

### Input: provenance-only normalization (no annotation)

Legacy `{"session_id":"session-12"}` with matching evidence → shadow V1
source-only envelope, `occurrence_time` null, `identity_changed` true,
`core_temporal_changed` false.

## Non-goals

TL01 does **not**:

- write or merge `GraphContribution` records
- promote candidates or touch accepted assertions
- run LLM extraction or auto-annotate
- infer occurrence from source sessions
- expose timeline UI or projected events
- change `compute_assertion_id` or TL00 envelope rules
- mutate `src/graph_memory/candidate_graph_*.py` producers

## Successor capabilities

| Slice | Intent |
| --- | --- |
| TL02+ | Participant bindings, projected occurrence IR, timeline surfaces |
| Temporal producer | Model-generated overlays constrained by this contract |
| Promotion bridge | Separate contract if shadow-approved semantics ever land durably |

## Demolition

```text
Replaced path:
Ad hoc before/after temporal inspection in notebooks or one-off scripts

Retained path:
GraphContributionAssertion.temporal_scope remains the durable carrier (TL00)

Required successor owner:
Temporal producer + promotion bridge (future slices)
```
