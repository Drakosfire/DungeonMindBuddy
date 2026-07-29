# Temporal Envelope V1

**Status:** Implemented (TL00 substrate)  
**Authority module:** `src/graph_memory/kernel/temporal.py`  
**Durable carrier:** `GraphContributionAssertion.temporal_scope: dict[str, Any] | None`

## Purpose

Provide one canonical typed interpretation seam for Graph V1 assertion
`temporal_scope` so later timeline work can distinguish:

- **source time** — where/when the assertion was recorded or observed
- **occurrence time** — when the described event happened in the fiction
- **valid time** — during what interval a state or persistent relationship was true

without rewriting the contribution ledger, rekeying existing assertions, changing
extraction, or publishing event/timeline surfaces.

## Authority and ownership

| Authority | Owns |
| --- | --- |
| `GraphContributionAssertion.temporal_scope` | Durable serialized carrier (unchanged in TL00) |
| `compute_assertion_id` | Deterministic assertion identity over the **raw** temporal dict |
| `graph_memory.kernel.temporal` | Typed models, parsers, serializers, compatibility interpretation, semantic projection helpers |
| `world_projection` core fingerprints | Consume `temporal_core_semantic_payload` for correction-sensitive agreement |

The temporal module may **interpret**. It does not own extraction, event
resolution, graph publication, current-state reduction, timeline ordering, or UI.

## Source time

Answers: *Where or when was this assertion recorded or observed?*

Examples: “This assertion came from Session 12.” / “This assertion came from a
dated worldbuilding document.”

Source time is provenance-facing. It is **not** evidence that the described
event occurred then.

## Occurrence time

Answers: *When did this event or occurrence happen in the fiction?*

Examples: “Baergrom revived Caelynn during Session 12.” / “Maelthor was exiled
twenty years before the campaign.”

Occurrence time is semantic. Never infer `source_time == occurrence_time` merely
because the source is a session recap.

## Valid time

Answers: *During what interval was this state or persistent relationship true?*

Examples: “Lysandra commanded the guard beginning in Session 13.” / “The gate
was intact until the siege.”

Valid time is semantic.

## Transaction/revision-time boundary

Transaction / revision time is **outside** `TemporalEnvelopeV1`.

Graph revision identity and contribution metadata already own when DungeonBuddy
recorded or changed an interpretation. Do not add transaction time to this
envelope.

## Supported point kinds

| Kind | Required | Allowed optional | Forbidden (cross-kind) |
| --- | --- | --- | --- |
| `session` | `session_id` | `campaign_id`, `raw_expression`, `certainty` | `value`, `calendar_id`, `relation`, `anchor_ref` |
| `campaign_date` | `value` | `calendar_id`, `campaign_id`, `raw_expression`, `certainty` | `session_id`, `relation`, `anchor_ref` |
| `relative` | `relation`+`anchor_ref` **or** `raw_expression` | `campaign_id`, `certainty` (and the other relative form) | `session_id`, `value`, `calendar_id` |
| `textual` | `raw_expression` | `campaign_id`, `certainty` | `session_id`, `value`, `calendar_id`, `relation`, `anchor_ref` |
| `unknown` | — | `raw_expression`, `campaign_id`, `certainty` | `session_id`, `value`, `calendar_id`, `relation`, `anchor_ref` |

All optional strings must be null/absent or non-blank after trimming. Cross-kind
fields are rejected at validation so serialized envelopes leave a single
authoritative field set per kind.

Occurrence time uses a tagged extent: `{kind:"point", point}` or
`{kind:"interval", start?, end?, raw_expression?}`.

Valid time uses `TemporalIntervalV1` (`start` / `end` / `raw_expression`; at
least one required). TL00 does not order unlike time systems.

## Partial and unknown time

Incomplete fictional time is first-class. Prefer `kind="unknown"`,
`kind="textual"`, or `kind="relative"` over inventing precision. Blank
identifiers and blank raw expressions are rejected.

## Legacy temporal_scope compatibility

| Input | Format | Interpretation |
| --- | --- | --- |
| `null` | `none` | No envelope |
| `{"session_id":"session-12"}` | `legacy_session_observation` | Source-time session point only; occurrence/valid stay null |
| `{"session_id":"session-12","as_of":"T1"}` | `legacy_unresolved` | Session → source time; `as_of` preserved under `unresolved_legacy_fields` |
| Unknown legacy dict (no `schema`) | `legacy_unresolved` | Raw fields preserved; no claimed occurrence/valid time |
| Explicit unrecognized `schema` tag | `legacy_unresolved` | Full payload preserved unresolved; no V1 claim |
| `{"schema":"dmb_temporal_envelope_v1", ...}` | `temporal_envelope_v1` | Strict validate, or raise `TemporalScopeValidationError` |

Malformed schema-tagged V1 is **never** reinterpreted as legacy.

## Assertion identity behavior

`compute_assertion_id` is untouched. Identity continues to hash the **raw**
`temporal_scope` dict.

Consequences:

- Different source sessions may yield different assertion IDs.
- Different occurrence or valid times yield different assertion IDs.
- Absence of time remains legal.
- Projection may still treat source-time-distinct assertions as compatible
  support for one persistent edge when core semantics agree.

Assertion identity and durable edge compatibility are not the same concept.

## Projection semantic behavior

Both `_node_core_semantic_fingerprint` and `_edge_core_semantic_fingerprint`
use `_temporal_core_semantic_for_fingerprint` (wraps
`temporal_core_semantic_payload`):

- V1: only `occurrence_time` and `valid_time` (source_time excluded).
- Schema-less legacy: remove top-level `session_id`; preserve every other
  legacy field; return null when nothing remains.
- Explicit unrecognized `schema` tag: return the **full** payload unchanged
  (fail-closed — do not apply the observation-session strip; a future schema
  may use `session_id` semantically).
- Malformed schema-tagged V1: raise `WorldGraphProjectionError` with
  `code=projection_integrity_error` and `status_code=409` (not a generic 500).

Required agreement:

| Pair | Core fingerprint |
| --- | --- |
| Same semantics, different legacy source session | agree |
| Same semantics, different V1 `source_time` only | agree |
| Different V1 occurrence times | disagree |
| Different V1 valid-time intervals | disagree |
| Different legacy `as_of` (non-session) | disagree |
| Same shape, different unrecognized schema `session_id` | disagree |

**Known asymmetry (TL00):** write-time node refuse in `contribution_merge.py`
still fingerprints full raw `temporal_scope`. Projection is the relaxed reader.
Fail-closed at write time; resolve in a later slice if needed.

## Serialization examples

### Source session only (V1)

```json
{
  "schema": "dmb_temporal_envelope_v1",
  "source_time": {
    "kind": "session",
    "session_id": "session-12",
    "certainty": "explicit"
  },
  "occurrence_time": null,
  "valid_time": null
}
```

### Event occurrence in a session

```json
{
  "schema": "dmb_temporal_envelope_v1",
  "source_time": {
    "kind": "session",
    "session_id": "session-20",
    "certainty": "explicit"
  },
  "occurrence_time": {
    "kind": "point",
    "point": {
      "kind": "session",
      "session_id": "session-12",
      "certainty": "explicit"
    }
  },
  "valid_time": null
}
```

### Historical relative event

```json
{
  "schema": "dmb_temporal_envelope_v1",
  "source_time": null,
  "occurrence_time": {
    "kind": "point",
    "point": {
      "kind": "relative",
      "relation": "before",
      "anchor_ref": "event:festival-of-expansion",
      "raw_expression": "twenty years before the campaign",
      "certainty": "approximate"
    }
  },
  "valid_time": null
}
```

### Open-ended persistent relationship

```json
{
  "schema": "dmb_temporal_envelope_v1",
  "source_time": null,
  "occurrence_time": null,
  "valid_time": {
    "start": {
      "kind": "session",
      "session_id": "session-13",
      "certainty": "explicit"
    }
  }
}
```

### Ended relationship

```json
{
  "schema": "dmb_temporal_envelope_v1",
  "source_time": null,
  "occurrence_time": null,
  "valid_time": {
    "start": {
      "kind": "session",
      "session_id": "session-5",
      "certainty": "inferred"
    },
    "end": {
      "kind": "session",
      "session_id": "session-18",
      "certainty": "explicit"
    }
  }
}
```

### Unknown ancient event

```json
{
  "schema": "dmb_temporal_envelope_v1",
  "source_time": null,
  "occurrence_time": {
    "kind": "point",
    "point": {
      "kind": "unknown",
      "raw_expression": "in the Age of Ash",
      "certainty": "unknown"
    }
  },
  "valid_time": null
}
```

### Legacy unresolved `as_of` qualifier

Input:

```json
{"session_id": "session-12", "as_of": "T1"}
```

Interpretation: `format=legacy_unresolved`; envelope source_time =
session-12; `unresolved_legacy_fields={"as_of":"T1"}`; occurrence/valid null.

## Invalid examples

- All three lanes null under `schema: dmb_temporal_envelope_v1`
- `kind="session"` without `session_id`
- Blank `session_id` / blank `raw_expression`
- Extra fields (`extra="forbid"`)
- `kind="unknown"` with invented `session_id` or campaign-date `value`
- Transaction/revision time fields inside the envelope

## Non-goals

TL00 does **not** implement:

- timeline endpoints or UI
- event nodes / projected occurrences
- participant-role bindings
- fictional calendar arithmetic or temporal ordering
- temporal extraction / LLM interpretation
- Graph V2 frame storage
- changes to `compute_assertion_id` or durable contribution models
- updates to the legacy producer (`candidate_graph_to_contribution.py`)

## Successor capabilities

| Slice | Intent |
| --- | --- |
| TL01 | Temporal producer / shadow-extraction support |
| TL02 | Participant-role bindings |
| TL03 | Projected occurrence IR |
| TL04 | Node timeline projection |
| TL05 | Timeline dogfood UI |
| TL06 | Rejuvenation cohort |

## Demolition

```text
Replaced path:
Ad hoc temporal_scope.session_id removal inside projection fingerprints

Deleted in this PR:
yes — replace the duplicated temporal interpretation with the canonical helper

Retained path:
GraphContributionAssertion.temporal_scope remains the durable serialized carrier

Retained reason:
Changing the durable field or assertion identity would require a separate migration contract

Named remaining legacy producer:
candidate_graph_to_contribution.py writes {"session_id": ...}

Required successor owner:
TL01 temporal producer slice
```
