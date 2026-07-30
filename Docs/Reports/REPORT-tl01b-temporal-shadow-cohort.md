# REPORT — TL01B temporal shadow cohort

**Status:** Live provider run completed (evaluator integrity corrections applied)
**Live execution commit (manifest `repository_sha`):** _pending clean live rerun_
**Implementation base (TL01 merge):** `d6ea4959c9bcc2f113ef50d912629864c1a1c04b`
**Evaluation verdict:** `ITERATE_PROMPT` (model quality) with documented coverage stop conditions below

## Cohort matrix

| # | Scenario | Gold |
| --- | --- | --- |
| 1 | Stafl revives Caelynn (Session 7 L14) | `resolved` occurrence `session-7` |
| 2 | Lysandra assigned to lead (Session 13 L18) | `resolved` valid from `session-13` |
| 3 | Hybrid destroyed (Session 24 L14) | `resolved` occurrence `session-24` |
| 4 | Party scene (Session 12 L14) | `not_applicable` |
| 5 | Road edge + legacy `session-22` scope | `not_applicable` |
| 6 | Maelthor password mention (Session 6 L18) | `ambiguous` |

## Coverage stop conditions

### Source differs from occurrence

Stop condition: `BLOCKED_BY_EVIDENCE`

Search scope:

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/*.md` (canonical recaps; archived/breadcrumbed/normalized variants excluded from seal decisions)
- Queries: cross-session prose (`Session N` references inside later recaps), flashback / previously / years-before patterns, explicit “during Session …” retellings

Queries and files inspected:

- Grep across C2 Session Recaps for `during Session`, `in Session N`, `years ago`, `long ago`, `previously`, role/transition language
- Existing sealed cohort assertions (6 candidates) and their evidence sessions

Why no sealed canonical case was available:

- C2 recaps almost always narrate events as contemporaneous with the recap session
- No sealable candidate assertion pairs a derived source session N with human-gold occurrence at a different normalized fictional time M
- Relative historical language exists (e.g. Session 11 “left about 30 years ago”) but is a different cohort category and lacks a matching sealed candidate assertion in this fixture set

Synthetic regression coverage:

- A1–A7 in `tests/test_temporal_shadow_extraction.py` (source copied over null gold, different non-null gold, unrelated session, legitimate same-session, valid-time copy, relative gold, fail-closed unsafe derivation)

Consequence for interpreting live source-leakage metrics:

- Live `source_to_occurrence_false_positives == 0` does **not** prove the model avoids source copying on a source≠occurrence adversarial case
- That safety path is proven only by synthetic regressions until a sealable corpus case exists

### Valid-time end or transition

Stop condition: `BLOCKED_BY_EVIDENCE`

Search scope:

- Same C2 Session Recaps tree
- Queries: `ceased`, `no longer`, `was replaced`, `left the`, `removed as`, `destroyed`, `ended`, ownership/role transition phrasing

Queries and files inspected:

- Session 23 / 24 battle recaps (charm “no longer compelled”, destruction language)
- Session 13 leadership assignment (start-only; no sealed end)
- Cohort assertions for persistent roles/states with explicit ends

Why no sealed canonical case was available:

- Available prose either describes momentary combat state (“no longer feel compelled”) or event occurrence (hybrid destroyed) rather than a persistent valid-time end/transition on a sealable candidate assertion
- No sealed assertion carries gold `valid_time.end` or an explicit transition interval

Synthetic regression coverage:

- A5 valid-time source-copying metric path
- Existing valid-time start gold row (Lysandra) remains the only live valid-time lane

Consequence for interpreting live valid-time quality:

- Live metrics do not exercise valid-time end/transition recovery
- Do not treat zero live valid-time leakage as coverage of that category

### Relative-historical

Current state: still missing from the sealed live cohort (Session 11 relative prose noted above; not sealed here).

## Live run

_Filled after clean-commit provider rerun._

| Field | Value |
| --- | --- |
| Case ID | `tl01b-temporal-shadow-cohort-v1` |
| Base contribution ID | `contribution:8408dabc602b750f` |
| Model | _pending_ |
| Prompt version (executed) | `tl01b-v1` |
| Provider response ID | _pending_ |
| Selected assertions | 6 |
| Overlay ID | _pending_ |
| Run ID | _pending_ |
| Preview verdict | _pending_ |
| Comparison verdict | _pending_ |
| Evaluation verdict | _pending_ |
| Input tokens | _pending_ |
| Output tokens | _pending_ |
| Elapsed ms | _pending_ |
| Cost | not reported by client |

Artifacts (local, gitignored): `evals/graph_memory_layer/artifacts/temporal_shadow_cohort/live-run/`

## Metrics (live vs gold)

_Filled after clean-commit provider rerun with corrected evaluator._

### Classification

| Metric | Count |
| --- | ---: |
| Exact semantic match | _pending_ |
| Resolved exact match | _pending_ |
| Wrong temporal value | _pending_ |
| Wrong temporal lane | _pending_ |
| Unsafe over-resolution / unsupported resolved | _pending_ |
| Status mismatch | _pending_ |
| Safe under-resolution | _pending_ |
| Missing / extra | _pending_ |
| Evidence-selection mismatch | _pending_ |

### Safety

| Metric | Count |
| --- | ---: |
| Source→occurrence false positives | _pending_ |
| Source→valid-time false positives | _pending_ |
| Unsupported resolved annotations | _pending_ |
| Foreign evidence attempts | 0 (success precondition) |
| Ungrounded source phrases | 0 (success precondition) |
| Invalid temporal payloads | 0 (success precondition) |

Zero live source-leakage counts must be read with the coverage stop conditions above.

### Quality

| Metric | Value |
| --- | --- |
| Status accuracy | _pending_ |
| Exact semantic match count | _pending_ |
| Resolved exact match count | _pending_ |
| Ambiguous or unresolved (gold) | _pending_ |
| Not-applicable accuracy | _pending_ |

## Strengths

- Source-leakage metrics now compare against TL01-derived assertion source time
- Foreign evidence is fail-closed at grounding; gold evidence differences are `evidence_selection_mismatch_count`
- Atomic overwrite and sealed run-manifest provenance retained from prior corrective commits
- Synthetic A/B regressions cover unavailable live adversarial categories

## Failure modes

_Filled after live rerun._

## Next decision

**`ITERATE_PROMPT`** for model quality, with explicit **`BLOCKED_BY_EVIDENCE`** coverage stop conditions for source≠occurrence and valid-time end/transition. Do not advance to TL02 on the strength of unrepresented live categories. Enum identity remains unchanged (`ITERATE_PROMPT`); coverage gaps are documented outside the verdict enum.
