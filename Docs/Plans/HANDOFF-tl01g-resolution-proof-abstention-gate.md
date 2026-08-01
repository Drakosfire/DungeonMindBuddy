---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  Create and evaluate frozen tl01g-v1 that permits interpretation_status=resolved
  only after a complete resolution proof (temporal proposition + unique lane +
  grounded value + licensed source-time reuse + valid copy/grounding), otherwise
  selecting exactly one of not_applicable / unresolved / ambiguous — with known
  lane and abstention regressions, legacy safety regression, and genuinely fresh
  holdout V8 + adversarial V6 promotion evidence.

  ## Merge-ready invariant
  A resolved annotation is emitted only when the assertion proposition is
  temporally eligible, exactly one temporal lane is justified, a temporal value
  is grounded, any source_context.source_time reuse is licensed, and every
  copied phrase/evidence ref is valid; otherwise the model selects the correct
  abstention class without using source time as a fallback, while preserving
  TL01F lane gains and producing durable sealed evaluation evidence without
  kernel, packet, renderer, threshold, or runner changes.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | tl01g-v1 frozen; tl01f-v1 unchanged | prompt registry + hash tests | `uv run pytest tests/test_temporal_shadow_extraction_tl01g.py -q` | TODO |
  | Packet/renderer V2 unchanged | registry identity tests | same + registry assertions | TODO |
  | No kernel/schema/evaluator/threshold/runner change | diff allowlist | `git diff --stat` vs §4 | TODO |
  | Lane regression green | Matrix A aggregate | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-lane/calibration/aggregate.json` | TODO |
  | Abstention regression green on known TL01F blockers | Matrix B aggregate | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-abstention/calibration/aggregate.json` | TODO |
  | Legacy safety regression green | Matrix C aggregate | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-legacy/calibration/aggregate.json` | TODO |
  | Fresh V8/V6 independent + sealed before execution | fixtures + independence tests | separate semantic + source fingerprint gates + ID/vocab tests + seal SHA | TODO |
  | Promotion decision trustworthy from fresh cohorts only | Matrix D aggregate + report | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` + REPORT | TODO |

  ## Scope and explicit deferrals
  Base: origin/main containing PR #463 merge e04a2126.
  Branch: feat/tl01g-resolution-proof-abstention-gate.
  Explicitly deferred: broader-shadow acceptance, textual normalization productization,
  grounding retries/salvage, Temporal Kernel/packet/renderer changes, graph writes,
  Timeline API/UI, world-line scope / named branch refs / multi-parent revisions / merge
  semantics.

  ## Evidence produced
  ### Automated
  TODO
  ### Adversarial
  TODO
  ### Regression
  TODO
  ### Manual / dogfood
  not applicable — sealed provider calibration only

  ## Gaps, waivers, and stop conditions
  TODO — none, or exact missing evidence / waiver / stop
---

# HANDOFF — TL01G: Resolution-Proof Abstention Gate

**Created:** 2026-07-31  
**Project:** DungeonBuddy / DungeonMindBuddy  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Status:** ACTIVE DESIGN — docs-only authority for the next Timeline prompt-calibration slice  
**Canonical handoff path:** `Docs/Plans/HANDOFF-tl01g-resolution-proof-abstention-gate.md`  
**Also known as:** this unnumbered active handoff (no planned implementation PR number)  
**Planned PR number:** none — this documentation change is itself PR `#465`; do not map `HANDOFF-pr465-*` to the future implementation. Rename to `HANDOFF-pr<N>-…` only after the implementation PR number `<N>` is actually known, in a separately reviewed doc-sync.  
**Required dependency:** PR `#463`, merged as `e04a2126adc8fbb735a2a7052fb0ebeeda2791ef`  
**Design anchor:** the commit that lands this unnumbered handoff on `main` (fill after merge)  
**Required implementation base:** exact `main` SHA that contains this merged handoff — record before dispatch; the implementation worker must start from that SHA and must not redefine or rename this authority document  
**Suggested branch:** `feat/tl01g-resolution-proof-abstention-gate`  
**Suggested worktree:** `../DungeonMindBuddy-tl01g`  
**Expected PR count:** one implementation PR after this docs PR merges  
**Operating mode:** prompt-only semantic iteration with sealed evaluation  
**Graph writes:** forbidden  
**Temporal Kernel changes:** forbidden  
**Packet or renderer changes:** forbidden  
**Comparison, threshold, and calibration-runner changes:** forbidden  
**Timeline API, event nodes, participant roles, projection, and UI:** forbidden  

> **Dispatch gate:** Dispatch is prohibited until (1) this docs PR merges, (2) the exact implementation-base SHA containing the merged handoff is recorded, (3) the pre-dispatch critique below is accepted, and (4) every acceptance claim has an owning proof. This checked-in handoff is the complete authority; the implementation worker must not edit it. The implementation PR description must use the frontmatter `pr_body_template` and remain a truthful merge contract.

---

## Pre-dispatch critique

| Question | Answer |
| --- | --- |
| Can one invariant govern every claimed observable path? | **Yes.** Every control/candidate run is the same shadow extraction path; the invariant is “resolved only after full resolution proof, else correct abstention,” evaluated via four sealed matrices. Split only if packet/kernel/evaluator changes become necessary. |
| What adversarial sequence is most likely to falsify it? | Future commitment spoken in a timed source → model reuses `source_context.source_time` as `valid_time.start` / occurrence (Lysandra / Corveth patterns) while emitting `resolved`, counting as readiness. |
| Would the proposed §7 / Matrix B evidence detect that failure? | **Yes**, if Matrix B gates require 3/3 unresolved/NA on those known rows and the promotion aggregate refuses readiness when `unsafe_over_resolution > 0`. |
| Which owning boundary is easiest to under-test? | Fresh V8 **separate** semantic-proposition and source/evidence fingerprint gates (combined tuple or ID-only disjointness is insufficient — TL01F V7 lesson). Also: anti-oracle contamination of instructional prose; authoring fresh rows before prompt freeze. |
| What fact would force this slice to stop or split? | Need for Temporal Kernel / packet V3 / renderer V3 / threshold or runner changes; inability to assemble independent canonical V8; gold defect after first provider execution; overlapping active TL01G PR. |

**Collision-risk pre-flight (authoring time):** no existing `tl01g-v1`, `test_temporal_shadow_extraction_tl01g.py`, `temporal_shadow_holdout_v8`, or `temporal_shadow_adversarial_v6` on `origin/main`. No open TL01G PR. TL01F merge is ancestor of `origin/main`.

### Dispatch contract — §4 allowlist (Path)

| Action | Path | Purpose |
| --- | --- | --- |
| Modify | `src/graph_memory/temporal_shadow_extraction.py` | Add `TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS` + `tl01g-v1` registry entry only |
| Create | `tests/test_temporal_shadow_extraction_tl01g.py` | Prompt identity, content guards, freshness, gold coverage, whole-prompt anti-oracle scan |
| Modify | `tests/test_temporal_shadow_extraction_tl01f.py` | Only if required to preserve/assert `tl01f-v1` hash stability (prefer no edit) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v8/**` | Fresh canonical promotion holdout + audit + cases |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v6/**` | Fresh synthetic promotion adversarial + sources + audit + cases |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01g.json` | Regression mirror (Matrices A–D development) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01g.json` | Regression mirror (Matrix C holdout) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v5/temporal-case-tl01g.json` | Regression mirror (Matrix A holdout) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_holdout_v7/temporal-case-tl01g.json` | Regression mirror (Matrix B holdout) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/temporal-case-tl01g.json` | Regression mirror (Matrix C adversarial) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3/temporal-case-tl01g.json` | Regression mirror (Matrix A adversarial) |
| Create | `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5/temporal-case-tl01g.json` | Regression mirror (Matrix B adversarial) |
| Create | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-lane/calibration/aggregate.json` | Matrix A durable aggregate |
| Create | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-abstention/calibration/aggregate.json` | Matrix B durable aggregate |
| Create | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-legacy/calibration/aggregate.json` | Matrix C durable aggregate |
| Create | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` | Matrix D durable aggregate |
| Modify | `.gitignore` | Allowlist entries for the four TL01G aggregates only if required |
| Create | `Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md` | Roadmap recommendation + evidence |

**Out of implementation allowlist:** `Docs/Plans/HANDOFF-tl01g-resolution-proof-abstention-gate.md` and any acceptance-authority edits. Changing this handoff requires a separately reviewed re-brief, not an implementation-side edit.

**Bounded discovery exception:** none. No unrestricted globs. Exact seven regression mirrors and four aggregates only.

### Dispatch contract — §5 denylist (must not touch)

| Path / capability | Why |
| --- | --- |
| `src/graph_memory/kernel/**` | Temporal Kernel / contribution identity contract changes forbidden |
| `src/graph_memory/temporal_shadow.py` (schema/models) | Overlay contract immutable |
| `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py` | Runner / thresholds / decision logic immutable |
| Prior sealed fixtures’ base/gold/source/audit/aggregates/reports | Immutable; mirrors only |
| Packet/renderer functions’ behavior | V2 identity only; no V3 |
| `Docs/Plans/HANDOFF-tl01g-resolution-proof-abstention-gate.md` | Acceptance authority; re-brief only, not implementation edits |
| Graph writes, Timeline API/UI, Hermes tools | Explicit non-goals |

### Dispatch contract — §7 verification commands

```bash
uv run pytest \
  tests/test_temporal_shadow_extraction.py \
  tests/test_temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_extraction_tl01f.py \
  tests/test_temporal_shadow_extraction_tl01g.py \
  -q

# Then the broader temporal + Graph Kernel suite used by TL01F (same selection as PR #463).

git diff --check
```

Provider matrices (not pytest; required for merge evidence):

```text
Matrix A regression-lane → aggregate.json
Matrix B regression-abstention → aggregate.json
Matrix C regression-legacy → aggregate.json
Matrix D promotion (V8/V6) → aggregate.json
```

All four must run 3 repetitions from one clean execution SHA after Commits A–C.

---

## §0 Mission

Create and evaluate a new frozen temporal-shadow prompt:

```text
tl01g-v1
```

that permits `interpretation_status=resolved` only after the model proves all of the following from the assertion and its owned evidence:

```text
1. The assertion proposition is temporally eligible.
2. Exactly one temporal lane is justified.
3. A temporal value is grounded.
4. Any reuse of source_context.source_time is licensed.
5. Every copied phrase and evidence reference is valid.
```

When that proof cannot be completed, the model must select the correct abstention class:

```text
not_applicable
unresolved
ambiguous
```

The completed capability is:

```text
frozen tl01f-v1 control
+ new frozen tl01g-v1 candidate
+ unchanged packet V2 and renderer V2
+ known lane-regression evidence
+ known abstention-regression evidence
+ legacy safety-regression evidence
+ genuinely fresh canonical holdout V8
+ genuinely fresh synthetic adversarial V6
+ repeated paired provider runs
→ trustworthy promotion decision
```

This PR must answer:

```text
Can the temporal producer preserve TL01F’s proposition/lane gains
while refusing unsupported temporal resolution,
distinguishing not_applicable from unresolved from ambiguous,
and producing grounded output reliably?
```

This remains model-shadow evaluation. Success does not publish temporal annotations, change graph authority, or complete TL01 by itself.

The strongest successful result is:

```text
PROMPT_READY_FOR_BROADER_SHADOW
```

That result authorizes a later bounded broader-shadow acceptance slice.

---

## §1 Why this slice exists

TL01F introduced proposition-type-first lane selection and produced a real improvement:

```text
authority/reporting relationship:
valid_time.start=session-13 in 3/3 observed runs
occurrence-lane leakage: 0
```

It did not clear readiness.

The corrected TL01F evidence still contains:

```text
unsafe over-resolution
source→occurrence leakage
source→valid-time leakage
grounding failures
wrong temporal lanes
unstable unresolved behavior
unstable ambiguous behavior
```

The known corrective V7 failures include:

```text
Abandoned restaurant
  gold: valid_time.start textual
  prediction: occurrence textual

Migrating forest forecast
  gold: resolved textual occurrence
  prediction: unresolved or wrong textual value

Lysandra future pledge
  gold: unresolved
  prediction: valid_time.start at source session

Dustwalker in Academy cell
  gold: ambiguous
  prediction: not_applicable or resolved
```

The known adversarial V5 failure includes:

```text
Corveth holds the Amber Ledger
  assertion: stable state/restatement
  evidence: contains unrelated eventive wording
  gold: not_applicable
  observed candidate: unsafe source-session occurrence
```

These are not representation failures. The existing contracts already support:

```text
resolved occurrence
resolved valid-time start
resolved valid-time end
not_applicable
unresolved
ambiguous
textual temporal points
null extents for every non-resolved status
```

The problem is the decision boundary for resolution.

TL01G therefore changes instructions only.

A second issue must also be corrected: holdout V7 is not independent promotion evidence. It is a corrective replay of V6 with eight reused propositions and source spans. TL01G must create genuinely fresh promotion cohorts after the candidate prompt is frozen.

---

## §2 Selected capability

### Capability

```text
Given one candidate assertion and its owned evidence packet,
emit resolved only when proposition, lane, and value form one
fully grounded interpretation.

Otherwise select exactly one:
  not_applicable
  unresolved
  ambiguous
```

### Primary invariant

```text
Source time is never a substitute for missing fictional time.
```

### Resolution invariant

```text
resolved requires:
  temporal proposition
  + unique lane
  + grounded value
  + licensed normalization
```

### Abstention invariant

```text
not_applicable:
  the assertion itself does not express a useful temporal boundary

unresolved:
  the assertion is temporal and has one intended semantic reading,
  but owned evidence cannot safely ground its value

ambiguous:
  owned evidence supports at least two materially different readings
  and neither can be safely rejected
```

### Lane invariant

```text
event or transition assertion
→ occurrence_time

persistent-state assertion with explicit beginning
→ valid_time.start

persistent-state assertion with explicit ending
→ valid_time.end
```

### Grounding invariant

```text
source_phrase and raw_expression are copied, never paraphrased.
Evidence references remain owned by the assertion packet.
```

### Authority invariant

```text
Every output remains a non-authoritative shadow overlay and evaluation artifact.
```

### Freshness invariant

```text
Known cohorts may prove regression behavior.
Only fresh V8/V6 cohorts may prove independent promotion behavior.
```

---

## §3 Mission falsification test

The mission has widened beyond TL01G if implementation requires any of the following:

```text
TemporalPointV1 changes
TemporalEnvelopeV1 changes
TemporalAnnotationOverlayV1 changes
new interpretation statuses
new comparison classifications
calibration threshold changes
calibration retry or salvage behavior
packet V3
renderer V3
source-context representation changes
deterministic post-processing of model classifications
moving predictions between temporal lanes after generation
per-assertion repair
GraphContribution or World Graph writes
accepted temporal assertions
event or occurrence identity
participant-role storage
Timeline queries or surfaces
```

Stop rather than absorb those capabilities.

---

## §4 Mandatory first moves

Before implementation:

1. Read:

```text
AGENTS.md
.cursor/rules/external-agent-pr-loop.mdc
.cursor/skills/external-agent-pr-loop/SKILL.md
.cursor/rules/responses-api-structured-extraction.mdc
.cursor/rules/anti-oracle-leakage.mdc
.cursor/rules/corpus-pii-and-llm-payloads.mdc

Docs/Design/CONTRACT-temporal-envelope-v1.md
Docs/Design/CONTRACT-temporal-shadow-overlay-v1.md
Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md
Docs/Design/CONTRACT-temporal-prompt-calibration-v2.md

Docs/Reports/REPORT-tl01f-proposition-type-temporal-lane-gate.md
Docs/Plans/HANDOFF-tl01d-conservative-temporal-decision-gate.md
Docs/Plans/HANDOFF-tl01g-resolution-proof-abstention-gate.md
```

2. Record repository state:

```bash
git fetch origin
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git worktree list
```

3. Confirm the TL01F merge is in current main:

```bash
git merge-base --is-ancestor \
  e04a2126adc8fbb735a2a7052fb0ebeeda2791ef \
  origin/main
```

4. Confirm no overlapping TL01G implementation or temporal-prompt PR exists.

5. Inspect:

```text
src/graph_memory/temporal_shadow_extraction.py
src/graph_memory/temporal_shadow_extraction_schema.py
evals/graph_memory_layer/temporal_shadow_prompt_calibration.py
tests/test_temporal_shadow_extraction_tl01f.py
```

6. Inspect the exact TL01F aggregates before designing the prompt:

```text
evals/graph_memory_layer/artifacts/
  temporal_shadow_prompt_calibration/
    tl01f/
```

7. Preserve unrelated local, runtime, corpus, and generated state.

---

## §5 Frozen dependencies

The following are immutable in this slice:

```text
tl01b-v1
tl01c-v1
tl01d-v1
tl01e-v1
tl01f-v1

tl01b-packet-v1
tl01c-packet-v1

render_temporal_shadow_user_content_v1
render_temporal_shadow_user_content_v2

TemporalPointV1
TemporalEnvelopeV1
TemporalAnnotationOverlayV1
TemporalModelAnnotationBatchTransportV1

compare_temporal_overlays
EvaluationVerdict
CalibrationDecision
compute_calibration_decision
all READY thresholds
all safety counters
all failure-code routing
```

Retain the frozen TL01F identity:

```text
prompt version:
tl01f-v1

prompt SHA256:
7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143

packet:
tl01c-packet-v1

renderer:
render_temporal_shadow_user_content_v2
```

Do not edit any prior cohort’s:

```text
base-contribution.json
gold-overlay.json
evidence source
existing control/candidate case
GOLD-AUDIT.md
sealed digest
aggregate
report
```

Regression mirrors may add a new `temporal-case-tl01g.json`. They may not mutate the underlying fixture.

---

## §6 Prompt registry addition

Add a new instruction constant:

```python
TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS = """..."""
```

Register:

```python
"tl01g-v1": TemporalPromptSpec(
    version="tl01g-v1",
    instructions=TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS,
    packet_version=TL01C_PACKET_VERSION,
    render_user_content=render_temporal_shadow_user_content_v2,
)
```

Required identity:

```text
prompt version: tl01g-v1
packet version: tl01c-packet-v1
renderer: render_temporal_shadow_user_content_v2
```

Do not create a new packet or renderer.

After the candidate prompt is complete:

1. Freeze it.
2. Record a hardcoded SHA256 in tests.
3. Commit the prompt and tests.
4. Do not inspect or author fresh V8/V6 rows until that commit exists.

Any later semantic prompt edit requires a new version ID. Do not silently mutate `tl01g-v1`.

---

## §7 Candidate prompt: resolution-proof gate

The candidate instructions must make `resolved` the result of a proof, not the default for anything that happened near a known session.

Apply these gates in order.

### Gate A — Proposition proof

Determine the proposition made by the assertion itself using:

```text
assertion_kind
subject_node_id
target_node_id
predicate
label
semantic_value
```

Evidence supports the assertion proposition. It does not replace the proposition with a more convenient event or state.

Questions:

```text
What is the assertion claiming?

Is it:
  an event or transition,
  a persistent state,
  a state boundary,
  a structural/classification claim,
  a restatement,
  a future commitment,
  or a proposition with competing readings?
```

### Gate B — Temporal-eligibility proof

Determine whether the proposition itself licenses a temporal interpretation.

Eligible:

```text
bounded event
transition
explicit state beginning
explicit state ending
future event with a grounded temporal expression
```

Not eligible:

```text
static structure
containment
classification
identity alone
persistent state merely observed
role merely restated
scene framing
source-document observation
```

An eventive verb somewhere in the evidence does not make an ineligible assertion temporal.

### Gate C — Unique-lane proof

For a resolved annotation, exactly one lane must normally be justified:

```text
occurrence
valid-start
valid-end
```

If two materially different lanes or proposition readings remain plausible and neither is safely rejectable:

```text
ambiguous
```

Do not choose whichever lane is easiest to populate.

### Gate D — Grounded-value proof

A lane is not enough. The corresponding value must be supported.

A value may come from:

```text
eligible source_context.source_time
explicit structured session reference
explicit campaign date
grounded relative expression
grounded textual expression
```

A value may not come from:

```text
filename
path
evidence ID
assertion ID
source label
the mere existence of source_context.source_time
the session in which a promise was spoken
an invented event anchor
```

When the proposition is temporal and its intended lane is apparent but no safe value can be grounded:

```text
unresolved
```

### Gate E — Source-time licensing proof

`source_context.source_time` remains:

```text
provenance_only
```

It may be reused only when all are true:

```text
1. The assertion is an event or explicit state boundary.
2. Owned evidence states that same proposition.
3. The proposition occurs within the narrated source episode.
4. Evidence supplies no different fictional time.
```

A statement made during Session N is not evidence that the promised future action happens in Session N.

### Gate F — Copy-and-grounding proof

Before returning the batch:

```text
source_phrase:
  null or verbatim contiguous snippet substring

raw_expression:
  verbatim contiguous snippet substring

evidence_ref_ids:
  owned subset only

base_assertion_id:
  exactly one annotation for each requested ID

diagnostics:
  at least one nonblank reason
```

If the model cannot satisfy the copy requirement safely, it must omit the optional phrase where allowed or abstain. It must not paraphrase.

---

## §8 Candidate prompt: exact status taxonomy

### `resolved`

Use only when:

```text
the proposition is temporal
and
one lane is uniquely justified
and
one value is grounded
```

Resolved normally has exactly one populated lane.

### `not_applicable`

Use when the assertion proposition does not express a useful temporal boundary.

Examples:

```text
X contains Y
X is north of Y
X remains captain
As captain, X gives an order
X still belongs to the order
X is a moss farmer
the room contains a circle
```

The source episode occurred in time. The assertion still may be non-temporal.

### `unresolved`

Use when:

```text
the assertion is temporally meaningful
and
one basic event/state reading is intended
but
owned evidence cannot ground a safe temporal value
```

Examples:

```text
X promises to search the archives
X will investigate the disappearance
X departed, but evidence gives no usable time
```

Do not use source time to eliminate unresolved status.

### `ambiguous`

Use only when owned evidence leaves at least two materially different interpretations.

Examples:

```text
the entity may be the original or a duplicate
the assertion could describe possession beginning or an item being recovered
the evidence supports either an occurrence or state-boundary reading
```

Ambiguous is not:

```text
general uncertainty
low confidence
missing time
a synonym for unresolved
```

For all three non-resolved statuses:

```json
{
  "occurrence_time": null,
  "valid_time": null
}
```

No exception.

---

## §9 Candidate prompt: required semantic distinctions

Anti-oracle rule (hard): known Matrix B / V7 / V5 failures may inform **generic decision rules** only. They must never supply exact names, predicates, phrases, source spans, or expected outputs to `tl01g-v1`. Instructional prose, decision checklists, diagnostics vocabulary, and few-shots are all in scope. Keep observed V7/V5 rows only in the report and in post-generation regression assertions.

Rewrite every motivating failure as a synthetic analogue from a reserved TL01G vocabulary family. Do not reuse active-benchmark entities, places, objects, predicates, or high-signal source phrases.

### Future commitment versus timed forecast

```text
“He vows to revisit the harbor market.”
→ unresolved
```

No execution time is supplied.

```text
“The supply caravan will reach Millcross in four hours.”
→ resolved occurrence with grounded textual/relative time
```

### Stable state versus eventive surrounding prose

```text
assertion:
Mara keeps the quay keys

evidence:
Messengers hurry past Mara as she continues to keep the quay keys

→ not_applicable
```

Do not temporalize the assertion from the messengers’ action.

### State attribute versus transition event

```text
assertion:
The mill was shuttered

evidence:
It was only recently shuttered, no more than a week ago

→ valid_time.start textual
```

The assertion is the resulting shuttered state with an explicit beginning.

### Missing value versus competing readings

```text
one intended event, no grounded time
→ unresolved

two materially different interpretations
→ ambiguous
```

### Observation versus new boundary

```text
“As harbor clerk, Teren presents the quay keys.”
→ not_applicable
```

No appointment or start boundary is stated.

### Epistemic ambiguity versus world-line divergence

```text
Temporal ambiguity is epistemic, not branch divergence.

Resolved means one supported temporal interpretation within the
assertion’s supplied reality/canon scope.

Intentional alternate world lines must not be encoded as
ambiguous, unresolved, temporal points, or diagnostics.
```

World-line scope, named branch refs, multi-parent revisions, and merge semantics are explicitly deferred (see §25).

---

## §10 Few-shot requirements

Use at most eight synthetic examples.

Reserve a new vocabulary family exclusively for TL01G. It must not reuse names, places, objects, predicates, high-signal source phrases, or sentence templates from:

```text
all earlier prompt examples
all existing temporal cohorts
the fresh V8/V6 fixtures
observed V7/V5 Matrix B rows
```

This restriction applies to the **entire** `tl01g-v1` prompt (instructions and examples), not only few-shot blocks.

Required example classes:

1. Same-source bounded event → occurrence.
2. Explicit persistent-state start → valid-start.
3. Explicit persistent-state end → valid-end.
4. Future commitment without execution time → unresolved.
5. Future forecast with explicit relative phrase → resolved occurrence.
6. Genuine competing occurrence/state readings → ambiguous.
7. Eventive evidence surrounding a stable-state assertion → not_applicable.
8. State attribute with explicit historical beginning → textual valid-start.

Each example must have exactly one expected status, lane, and value class.

Forbidden example answers:

```text
not_applicable or unresolved
ambiguous or unresolved
relative or textual
occurrence or valid-start
```

Do not use names, predicates, phrases, or expected answers from V7, V5, or any fresh promotion row anywhere in `tl01g-v1`.

---

## §11 Experiment architecture

Use the existing generalized calibration runner unchanged.

### Control

```text
tl01f-v1
```

### Candidate

```text
tl01g-v1
```

### Shared inputs

```text
tl01c-packet-v1
render_temporal_shadow_user_content_v2
same base contribution
same gold overlay
same selected assertion IDs
same evidence registry
```

Control and candidate cases may differ only in:

```text
case_id
prompt_version
case filename
```

### Provider

Use the same model used for TL01F:

```text
gpt-5.4-mini
```

### Repetitions

```text
3 per lane and cohort
```

Do not selectively retry grounding or semantic failures.

Do not discard inconvenient repetitions.

A provider-infrastructure failure may invalidate a complete matrix only when the existing runner classifies it as `PROVIDER_FAILURE`. Document the invalidated execution rather than cherry-picking replacement calls.

---

## §12 Required evaluation matrices

Run four separate aggregates.

### Matrix A — lane regression

Purpose:

```text
Preserve TL01F’s successful occurrence/valid-time lane behavior.
```

Suggested artifact path:

```text
evals/graph_memory_layer/artifacts/
  temporal_shadow_prompt_calibration/
    tl01g/
      regression-lane/
        calibration/
          aggregate.json
```

Cases:

```text
development:
  temporal_shadow_cohort

holdout:
  temporal_shadow_holdout_v5

adversarial:
  temporal_shadow_adversarial_v3
```

Required observed checks include:

```text
authority/reporting relationship remains valid-start
historical founding remains occurrence
state restatement remains non-resolved
explicit alternate time still defeats source time
```

### Matrix B — abstention regression

Purpose:

```text
Directly test every known TL01F blocker that shaped tl01g-v1.
```

Suggested artifact path:

```text
.../tl01g/regression-abstention/calibration/aggregate.json
```

Cases:

```text
development:
  temporal_shadow_cohort

holdout:
  temporal_shadow_holdout_v7

adversarial:
  temporal_shadow_adversarial_v5
```

V7 must remain described as:

```text
corrective replay
not independent promotion evidence
```

### Matrix C — legacy safety regression

Purpose:

```text
Ensure the new abstention rules do not reopen earlier structural,
source-leakage, ambiguity, or invalid-output failures.
```

Suggested artifact path:

```text
.../tl01g/regression-legacy/calibration/aggregate.json
```

Cases:

```text
development:
  temporal_shadow_cohort

holdout:
  temporal_shadow_holdout

adversarial:
  temporal_shadow_adversarial_v2
```

Do not modify legacy gold to fit TL01G.

### Matrix D — independent promotion

Purpose:

```text
Measure generalization on rows that could not influence tl01g-v1.
```

Suggested artifact path:

```text
.../tl01g/promotion/calibration/aggregate.json
```

Cases:

```text
development:
  temporal_shadow_cohort

holdout:
  fresh temporal_shadow_holdout_v8

adversarial:
  fresh temporal_shadow_adversarial_v6
```

Only Matrix D may support:

```text
PROMPT_READY_FOR_BROADER_SHADOW
```

---

## §13 Regression mirror files

Add exactly these seven `temporal-case-tl01g.json` mirrors (no other regression cohorts):

```text
evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01g.json
evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01g.json
evals/graph_memory_layer/examples/temporal_shadow_holdout_v5/temporal-case-tl01g.json
evals/graph_memory_layer/examples/temporal_shadow_holdout_v7/temporal-case-tl01g.json
evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/temporal-case-tl01g.json
evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3/temporal-case-tl01g.json
evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5/temporal-case-tl01g.json
```

Fresh V8/V6 cases are created under their own cohort directories (already allowlisted) and are not part of this seven-file regression set.

Each mirror must:

```text
use tl01g-v1
retain identical base/gold digests
retain identical selected assertion order
retain identical evidence registry
retain identical snippet limit
```

Do not copy or rename assertion IDs merely to create novelty.

---

## §14 Fresh canonical holdout V8

Create:

```text
evals/graph_memory_layer/examples/
  temporal_shadow_holdout_v8/
```

Required files:

```text
README.md
GOLD-AUDIT.md
base-contribution.json
gold-overlay.json
temporal-case-tl01f.json
temporal-case-tl01g.json
```

### Minimum coverage

Use at least twelve canonical assertions from real project-owned sources.

Required classes:

| Class                                                                 | Minimum |
| --------------------------------------------------------------------- | ------: |
| Same-source occurrence event                                          |       1 |
| Explicit textual or relative forecast occurrence                      |       1 |
| Same-source valid-time start                                          |       1 |
| Source-different textual valid-time start                             |       1 |
| Valid-time end                                                        |       1 |
| Source-different historical occurrence                                |       1 |
| Persistent-state restatement → not_applicable                         |       1 |
| Static structure/classification → not_applicable                      |       1 |
| Future commitment with no execution time → unresolved                 |       1 |
| Temporal assertion with one reading but ungrounded value → unresolved |       1 |
| Competing temporal lanes/readings → ambiguous                         |       1 |
| Contradictory identity/state reading → ambiguous                      |       1 |

### Canonical-source rule

Use actual tracked DungeonBuddy source material.

Do not create synthetic prose for canonical V8.

### Independence rule

V8 must be semantically and evidentially disjoint from every prior temporal cohort.

Do not rely only on assertion or evidence IDs.

Prove the two claims **separately**. A combined proposition+span tuple may be retained as supplemental telemetry, but it cannot own the independence gate.

#### Semantic proposition fingerprints (must be disjoint)

Canonical proposition identity independent of evidence/provenance and of cosmetic label rewrites:

```text
assertion_kind
subject_node_id
target_node_id
predicate
semantic_assertion_value
  (provenance-only keys excluded; label rewrites alone must not create novelty)
```

Zero overlap with all prior canonical/development/holdout cohorts.

#### Source / evidence fingerprints (must be disjoint)

Minimally:

```text
source_artifact_path
content_sha256
start_line
end_line
hash of the resolved span text
```

Zero overlap with all prior canonical/development/holdout cohorts.

A reused source span fails even if the label or semantic value changed.
A reused proposition fails even if attached to another span.
A renamed evidence ID or assertion ID does not create independence.

### Selection timing

V8 row selection begins only after:

```text
tl01g-v1 is frozen
its hash test exists
the prompt-freeze commit exists
```

---

## §15 Fresh synthetic adversarial V6

Create:

```text
evals/graph_memory_layer/examples/
  temporal_shadow_adversarial_v6/
```

Required files:

```text
README.md
GOLD-AUDIT.md
base-contribution.json
gold-overlay.json
sources/*.md
temporal-case-tl01f.json
temporal-case-tl01g.json
```

Use at least ten rows.

Required adversarial classes:

1. Future promise spoken during a timed source; no execution time.
2. Future event with an explicit relative offset.
3. Eventive evidence surrounding a stable-state assertion.
4. Stative wording supporting an event assertion.
5. State attribute with an explicit textual start.
6. Explicit state end.
7. `still`, `again`, or `remains` without a new boundary.
8. Genuine occurrence-versus-valid-start ambiguity.
9. Explicit fictional time different from source time.
10. Grounding trap where a paraphrase would be invalid but a verbatim phrase is available.

### Synthetic independence

Use a new vocabulary family absent from:

```text
all prompt few-shots
all prior adversarial cohorts
all canonical holdouts
```

Tests must enforce:

```text
assertion ID disjointness
evidence ID disjointness
reserved-vocabulary disjointness
no copied sentence templates from tl01g-v1 examples
```

Synthetic V6 must be authored only after the prompt-freeze commit.

---

## §16 Gold-audit requirements

Both fresh cohorts require a sealed `GOLD-AUDIT.md`.

For every row record:

```text
assertion ID
plain-language assertion proposition
proposition type
gold interpretation status
gold temporal lane
gold temporal value class
exact supporting phrase
source time
whether source time is eligible
resolution-proof result
strongest competing status or lane
why that alternative is rejected
audit result
```

The resolution-proof audit must explicitly answer:

```text
Is the proposition temporal?
Is the lane unique?
Is the value grounded?
Is source-time reuse licensed?
Are all copied strings verbatim?
```

### Gold immutability

After the first provider execution:

```text
do not edit base
do not edit gold
do not edit cases
do not edit source spans
do not edit the audit to rationalize output
```

If a gold defect is discovered:

1. Mark the affected cohort retired.
2. Preserve it unchanged for audit history.
3. Create the next cohort version.
4. Reseal.
5. Rerun the complete promotion matrix.

Do not patch gold in place.

---

## §17 Commit and execution sequence

The PR history must preserve this order.

### Commit A — candidate freeze

Implement and test:

```text
tl01g-v1
registry entry
fixed prompt SHA
tl01f control hash preservation
packet/renderer identity
required prompt gates
few-shot uniqueness
```

No fresh V8/V6 fixtures yet.

### Commit B — regression mirrors

Add `temporal-case-tl01g.json` mirrors for known cohorts.

Do not edit known base, gold, evidence, or audits.

### Commit C — fresh cohort seal

After Commit A exists:

```text
author holdout V8
author adversarial V6
complete gold audits
run independence tests
freeze all digests
commit the cohorts
```

This commit is the fresh-cohort seal.

### Execution

From one clean commit containing A–C:

```text
run all four matrices
use three repetitions
use the same model and configuration
record one repository SHA
```

No prompt or fixture changes may occur between the first and last provider call.

### Commit D — durable evidence

Commit only:

```text
four aggregate.json files
TL01G report
necessary .gitignore allowlist entries
tests or documentation that do not alter executed prompt/fixtures
```

Do not commit raw provider response bodies unless existing repository policy explicitly requires them.

---

## §18 Required tests

### Prompt identity

Test:

```text
tl01f-v1 hash remains unchanged
tl01g-v1 has one fixed non-tautological hash
tl01g-v1 resolves through the registry
tl01g-v1 uses tl01c-packet-v1
tl01g-v1 uses renderer V2
unknown prompt versions fail closed
```

### Input equivalence

For every control/candidate pair:

```text
base contribution equal
gold overlay equal
selected assertion IDs equal and ordered
evidence registry equal
snippet limit equal
rendered user content byte-identical
only prompt_version/case_id differ
```

### Prompt-content guards

Test that `tl01g-v1` contains explicit versions of:

```text
resolution requires temporal proposition + unique lane + grounded value
source time is not a fallback
future commitment without execution time is unresolved
explicit timed forecast is resolved
ambiguous requires materially competing readings
missing value is unresolved, not ambiguous
stable-state restatement is not_applicable
state attribute with explicit beginning is valid-start
source_phrase and raw_expression must be verbatim
```

### Few-shot guards

Test:

```text
no more than eight examples
exactly one expected answer per example
reserved vocabulary appears in prompt
reserved vocabulary appears nowhere in evaluation fixtures
```

### Whole-prompt anti-oracle scan

Scan the **entire** frozen `tl01g-v1` prompt text (instructions + checklists + diagnostics + few-shots), not merely parsed examples, and assert zero hits for:

```text
every prior prompt’s reserved example vocabulary
every prior temporal cohort’s high-signal entity/place/object names
every high-signal source phrase from observed V7/V5 Matrix B rows
  (forest arrival; Corveth/ledger holding; abandoned restaurant;
   Ysanna-as-archivist; future contacts search; Lysandra pledge;
   Dustwalker cell; and equivalent high-signal spans)
evaluation-only cohort labels
```

Known failures may appear in the TL01G report and in regression assertions after generation. They must not appear in model-facing prompt material.

### Freshness guards

Test V8 against all prior canonical cohorts with **two independent gates**:

```text
semantic proposition fingerprint set ∩ prior == ∅
source/evidence fingerprint set ∩ prior == ∅
```

A combined fingerprint may be logged, but passing only the combined set is insufficient.

Test V6 against all prior adversarial cohorts using:

```text
IDs
vocabulary
source text
sentence-template checks where practical
```

Also test:

```text
V8 and V6 IDs are mutually disjoint
no evaluation-only cohort label enters assertion semantic_value
```

### Gold coverage

Test fresh gold contains every required class and that:

```text
not_applicable → null occurrence and valid time
unresolved → null occurrence and valid time
ambiguous → null occurrence and valid time
resolved occurrence → valid_time null
resolved valid-start → occurrence null and end null
resolved valid-end → occurrence null and start null
every annotation has nonblank diagnostics
```

### Focused commands

At minimum:

```bash
uv run pytest \
  tests/test_temporal_shadow_extraction.py \
  tests/test_temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow_extraction_tl01f.py \
  tests/test_temporal_shadow_extraction_tl01g.py \
  -q
```

Then run the broader temporal and Graph Kernel suite used by TL01F.

Finally:

```bash
git diff --check
```

No unrelated test or product repair belongs in this PR.

---

## §19 Semantic acceptance gates

### Matrix A — lane regression

Candidate must retain:

```text
authority/reporting valid-start:
  exact lane 3/3
  no occurrence leak

historical founding:
  occurrence lane 3/3

known valid-end rows:
  valid-end 3/3

known restatement rows:
  non-resolved 3/3
```

Candidate totals:

```text
unsafe over-resolution: 0
source leakage: 0
wrong temporal lane: 0
grounding failures: 0
```

Text-span-only normalization differences must be reported separately.

### Matrix B — abstention regression

The following must be stable in all three candidate repetitions:

```text
V7 restaurant:
  resolved
  valid_time.start textual
  occurrence null

V7 forest forecast:
  resolved
  occurrence textual
  source session not copied

V7 Lysandra pledge:
  unresolved
  both temporal lanes null

V7 Dustwalker cell:
  ambiguous
  both temporal lanes null

V5 Corveth stable ledger state:
  not_applicable
  both temporal lanes null

V5 competing hold/recovery reading:
  ambiguous
  both temporal lanes null
```

Candidate totals:

```text
unsafe over-resolution: 0
source leakage: 0
wrong temporal lane: 0
wrong temporal value: 0
grounding failures: 0
```

### Matrix C — legacy safety regression

Require:

```text
no unsafe over-resolution
no source→occurrence false positives
no source→valid-time false positives
no wrong temporal lane
no grounding failure
no invalid model output
```

Do not claim historical exact-value normalization is solved unless it actually is.

### Matrix D — independent promotion

The promotion aggregate must return:

```text
PROMPT_READY_FOR_BROADER_SHADOW
```

Additional human gates:

```text
candidate development success: 3/3
candidate holdout success: 3/3
candidate adversarial success: 3/3

candidate unsafe over-resolution: 0
candidate source leakage: 0
candidate grounding failures: 0
candidate model-output failures: 0
candidate evidence/case failures: 0
candidate wrong temporal lane: 0
candidate wrong temporal value: 0

candidate status accuracy per run: 1.0
candidate not-applicable accuracy per run: 1.0
```

`PROMPT_READY_FOR_BROADER_SHADOW` may be considered only when `wrong_temporal_value == 0` (and the other safety/semantic gates above). The existing machine decision can still emit readiness with a single wrong temporal value; the human report must not.

Recommendation precedence for residual value mismatches (see §20 / §22):

```text
wrong_temporal_value == 0
  → PROMPT_READY may be considered

wrong_temporal_value > 0
  and every mismatch is audited as textual-span-only
  → ADVANCE_TO_TEXTUAL_NORMALIZATION
  (not broader-shadow readiness)

any structured or semantically different temporal value
  → ITERATE_PROMPT / appropriate human recommendation
```

Every fresh `not_applicable`, `unresolved`, and `ambiguous` assertion must have one stable status across all three repetitions.

A fresh promotion result cannot be claimed from V7 or any other observed cohort.

---

## §20 Textual-normalization boundary

Wrong textual values must remain separate from semantic failures.

Examples:

```text
“about thirty years ago”
versus
“left the causeway about thirty years ago”
```

If all of these are zero:

```text
unsafe over-resolution
source leakage
grounding failures
wrong status
wrong lane
invalid output
```

but `wrong_temporal_value > 0` and every mismatch is audited as textual-span-only, do not mutate `tl01g-v1`.

Recommend:

```text
ADVANCE_TO_TEXTUAL_NORMALIZATION
```

Do **not** select `PROMPT_READY_FOR_BROADER_SHADOW` while any wrong temporal value remains, even if the machine decision does.

A future normalization slice must not reopen the abstention and lane semantics proven here.

---

## §21 Grounding boundary

Grounding failure remains prompt/model quality in this slice.

TL01G may improve grounding through:

```text
clearer verbatim-copy instructions
a final copy audit
short canonical diagnostic reasons
explicit permission to omit optional source_phrase rather than paraphrase
```

TL01G may not improve grounding through:

```text
automatic retries
per-assertion salvage
post-generation phrase correction
fuzzy substring acceptance
rewriting raw_expression
dropping failed assertions
changing grounding validation
```

If semantic behavior is green but candidate grounding failures remain, recommend:

```text
ISOLATE_GROUNDING_RELIABILITY
```

Do not bury a runner redesign inside this PR.

---

## §22 Human roadmap recommendation

The report must select exactly one recommendation.

### `PROMPT_READY_FOR_BROADER_SHADOW`

Use only when:

```text
promotion machine decision is PROMPT_READY_FOR_BROADER_SHADOW
candidate wrong_temporal_value == 0
all fresh semantic and safety gates pass
all candidate promotion runs succeed
known regressions remain green
```

Next work is a bounded broader-shadow acceptance slice. TL01 is not automatically DONE.

### `ADVANCE_TO_TEXTUAL_NORMALIZATION`

Use when:

```text
status, lane, safety, source-time, and grounding are green
wrong_temporal_value > 0
every residual mismatch is audited as textual-span-only
```

Precedence: this recommendation outranks broader-shadow readiness whenever any wrong temporal value remains.

### `ITERATE_ABSTENTION_PROMPT`

Use when any of these remain:

```text
unsafe resolution
wrong abstention status
future commitment resolved at source session
ambiguous collapsed into one reading
stable state temporalized from surrounding eventive prose
```

A successor prompt requires a new version ID.

### `ITERATE_LANE_PROMPT`

Use when:

```text
occurrence versus valid-start/valid-end errors remain
```

### `ISOLATE_GROUNDING_RELIABILITY`

Use when semantic gates pass but candidate grounding failures remain.

### `BLOCKED_BY_INPUT_REPRESENTATION`

Use only when the existing packet cannot represent information required for a defensible answer.

Do not use this for model failure to follow supplied evidence.

### `BLOCKED_BY_EVIDENCE`

Use when a trustworthy fresh canonical cohort cannot be assembled from owned sources.

### `BLOCKED_BY_CONTRACT`

Use only for a genuine schema or evaluator representation gap.

### `PROVIDER_FAILURE`

Use only for provider-level failure according to the existing runner.

---

## §23 Report requirements

Create:

```text
Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md
```

The report must include:

1. Executive result for all four matrices.
2. Frozen control and candidate prompt identities.
3. Packet and renderer identities.
4. Prompt-freeze commit.
5. Fresh V8/V6 seal commit.
6. Provider execution SHA and model.
7. Aggregate IDs and paths.
8. Explicit statement that V7 is corrective replay only.
9. Fresh-cohort independence proof.
10. Gold-audit summary.
11. Control-versus-candidate metric deltas.
12. Status-confusion table:

```text
gold resolved / not_applicable / unresolved / ambiguous
versus predicted statuses
```

13. Temporal-lane confusion table:

```text
occurrence
valid-start
valid-end
none
both
```

14. Assertion stability for every known target row.
15. Assertion stability for every fresh non-resolved row.
16. Source-time leakage totals.
17. Grounding failures and affected assertion IDs.
18. Textual-value mismatches separated from semantic failures.
19. Exact human roadmap recommendation.
20. Explicit statement of what the result does and does not authorize.

Do not describe corrective V7 evidence as fresh promotion authority.

---

## §24 Failure model

| Failure                                              | Classification           | Required response                                  |
| ---------------------------------------------------- | ------------------------ | -------------------------------------------------- |
| Provider refuses or errors                           | `PROVIDER_FAILURE`       | Record; do not cherry-pick                         |
| Fresh source span cannot be resolved                 | `BLOCKED_BY_EVIDENCE`    | Repair before seal or replace row                  |
| Prompt version missing                               | `BLOCKED_BY_CONTRACT`    | Stop before provider call                          |
| Candidate resolves an unresolved/ambiguous/NA row    | Prompt failure           | `ITERATE_ABSTENTION_PROMPT`                        |
| Candidate chooses wrong lane                         | Prompt failure           | `ITERATE_LANE_PROMPT`                              |
| Candidate copies source session without license      | Prompt failure           | Iterate prompt                                     |
| Candidate emits invalid phrase/evidence grounding    | Prompt failure           | `ISOLATE_GROUNDING_RELIABILITY` if otherwise green |
| Exact textual span differs but semantics are correct | Normalization debt       | Report separately                                  |
| Fresh cohort overlaps prior proposition/span         | Invalid promotion design | Replace before provider execution                  |
| Gold defect discovered after execution               | Retire cohort            | Create next version and rerun                      |
| Implementation needs packet/schema change            | Scope breach             | Stop and report                                    |

---

## §25 Explicit non-goals

Do not implement:

```text
authoritative temporal publication
graph revision creation
automatic promotion of model output
Temporal Kernel changes
packet V3
renderer V3
new statuses
new evaluator classifications
threshold weakening
retry policy
post-processing or deterministic repair
participant roles
event or occurrence nodes
timeline projection
timeline query API
Timeline UI
Hermes temporal tools
corpus-wide shadow rollout
textual normalization beyond reporting
world-line scope / named branch refs
multi-parent revisions
merge semantics for alternate realities
encoding intentional branch divergence as temporal ambiguity
```

---

## §26 Retained paths and demolition

Retain unchanged:

```text
all prior prompts
all prior packets/renderers
all prior sealed fixtures
all prior aggregates
all prior reports
all corrective/retired audit history
```

Add only:

```text
tl01g-v1 prompt registration
TL01G tests
TL01G regression case mirrors
fresh holdout V8
fresh adversarial V6
four TL01G aggregates
TL01G report
required artifact allowlist entries
```

Demolition in this PR:

```text
none
```

No production path is replaced.

---

## §27 Stop conditions

Stop and hand back immediately if:

1. `origin/main` does not contain the TL01F merge.
2. Another active PR owns TL01G.
3. A fresh cohort cannot satisfy semantic/source-span independence.
4. Prompt design requires inspecting fresh V8/V6 rows before prompt freeze.
5. A contract, packet, renderer, threshold, or evaluator change appears necessary.
6. A gold defect is discovered after execution.
7. Provider execution cannot be tied to one clean repository SHA.
8. Any proposed fix moves model output between lanes after generation.
9. Any proposed fix writes temporal output to the World Graph.
10. The PR begins implementing participant roles, occurrence identity, projection, or UI.

---

## §28 Definition of done

TL01G is complete when:

* `tl01g-v1` exists and is frozen by a fixed hash.
* `tl01f-v1` remains byte-stable.
* Packet V2 and renderer V2 remain unchanged.
* No kernel, schema, evaluator, threshold, or runner behavior changed.
* All required regression mirrors exist.
* Holdout V8 is genuinely independent.
* Adversarial V6 is genuinely independent.
* Both fresh cohorts were authored after prompt freeze.
* Both fresh cohorts were audited and sealed before provider execution.
* All four matrices ran three repetitions from one clean execution SHA.
* All four durable aggregates are committed.
* The TL01G report is committed.
* Known failures and fresh failures are reported without gold repair.
* The report chooses exactly one roadmap recommendation.
* No graph write or product-surface behavior was introduced.

---

## §29 Final handback template

```text
TL01G HANDOFF

Branch:
<name>

Base / required dependency:
<origin/main SHA>
PR #463 merge e04a2126adc8fbb735a2a7052fb0ebeeda2791ef confirmed: yes/no

Prompt:
control: tl01f-v1
control SHA: 7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143
candidate: tl01g-v1
candidate SHA: <sha>
packet: tl01c-packet-v1
renderer: render_temporal_shadow_user_content_v2
prompt-freeze commit: <sha>

Fresh cohorts:
holdout: temporal_shadow_holdout_v8
adversarial: temporal_shadow_adversarial_v6
seal commit: <sha>
semantic/source independence verified: yes/no
gold changed after execution: no

Execution:
model: gpt-5.4-mini
repository SHA: <sha>
repetitions: 3

Aggregates:
regression-lane: <path> / <calibration_id> / <decision>
regression-abstention: <path> / <calibration_id> / <decision>
regression-legacy: <path> / <calibration_id> / <decision>
promotion: <path> / <calibration_id> / <decision>

Known target stability:
authority relationship: <result>
restaurant valid-start: <result>
forest forecast occurrence: <result>
Lysandra unresolved: <result>
Dustwalker ambiguous: <result>
Corveth stable-state NA: <result>
adversarial dual-reading ambiguous: <result>

Candidate promotion totals:
successful development runs: <n>/3
successful holdout runs: <n>/3
successful adversarial runs: <n>/3
unsafe over-resolution: <n>
source→occurrence false positives: <n>
source→valid-time false positives: <n>
wrong temporal lane: <n>
wrong temporal value: <n>
grounding failures: <n>
model-output failures: <n>

Tests:
<commands and results>

Report:
Docs/Reports/REPORT-tl01g-resolution-proof-abstention-gate.md

Human roadmap recommendation:
<PROMPT_READY_FOR_BROADER_SHADOW |
 ADVANCE_TO_TEXTUAL_NORMALIZATION |
 ITERATE_ABSTENTION_PROMPT |
 ITERATE_LANE_PROMPT |
 ISOLATE_GROUNDING_RELIABILITY |
 BLOCKED_BY_INPUT_REPRESENTATION |
 BLOCKED_BY_EVIDENCE |
 BLOCKED_BY_CONTRACT |
 PROVIDER_FAILURE>

Authority statement:
No temporal model output was published to the World Graph.
```
