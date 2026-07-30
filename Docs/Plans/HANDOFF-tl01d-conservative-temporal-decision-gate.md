# HANDOFF — TL01D: Conservative Temporal Decision Gate

**Created:** 2026-07-30
**Project:** DungeonBuddy / DungeonMindBuddy
**Repository:** `Drakosfire/DungeonMindBuddy`
**Status:** ACTIVE — next temporal prompt-calibration slice
**Suggested canonical path:** `Docs/Plans/HANDOFF-tl01d-conservative-temporal-decision-gate.md`
**Required dependency:** PR `#453`, merged as `14f7a0d385e1a986cee9edb007f670dc505f148d`
**Required implementation base:** clean current `origin/main` containing that merge
**Suggested branch:** `feat/tl01d-conservative-temporal-decision-gate`
**Expected PR count:** one
**Operating mode:** prompt-only semantic iteration plus bounded calibration-runner generalization
**Graph writes:** forbidden
**Temporal kernel changes:** forbidden
**Packet V2 changes:** forbidden
**Timeline API, UI, event nodes, and participant roles:** forbidden

---

## §0 Mission

Create and evaluate a new frozen temporal prompt:

```text
tl01d-v1
```

that places a strict temporal-eligibility decision gate before source-time normalization.

The completed capability is:

```text
frozen tl01c-v1 control
+ new tl01d-v1 candidate
+ identical packet V2 inputs
+ observed regression cohorts
+ fresh sealed canonical holdout
+ fresh sealed synthetic adversarial cohort
+ repeated paired provider runs
→ trustworthy prompt-only calibration decision
```

TL01D must answer:

```text
Does the assertion proposition itself have temporal semantics?

If yes:
  which lane and which boundary?

If no:
  not_applicable, ambiguous, or unresolved with null temporal extents.

Only after that:
  may source_context.source_time be considered.
```

This is not an input-representation experiment.

This is not an expansion of graph authority.

---

## §1 Why this slice exists

TL01C established that packet V2 is sufficient to recover several same-source temporal assertions:

```text
development resolved exact:
  baseline tl01b-v1: 0
  candidate tl01c-v1: 3

development exact median:
  baseline: 1
  candidate: 4
```

The remaining failures are primarily decision failures rather than missing temporal representation:

```text
candidate unsafe over-resolution:       12
source→occurrence false positives:       9
source→valid-time false positives:       5
model-output failures:                   2
holdout exact valid-time minimum:        0
holdout not-applicable minimum:          0.0
```

Observed failure classes include:

1. Structural containment resolved as temporal.
2. Scene framing resolved as temporal.
3. Name or identity ambiguity resolved as temporal.
4. Persistent state starts emitted as occurrence time.
5. Source session copied despite a different explicit fictional time.
6. Textual historical time converted into invented relative anchors.
7. `ambiguous` emitted with non-null temporal extents.

The temporal kernel already represents the correct outputs.

Packet V2 already supplies explicit provenance-only source context.

The next experiment must therefore change instructions, not the temporal contract or input packet.

---

## §2 Critical experimental correction

The following are no longer independent holdouts:

```text
evals/graph_memory_layer/examples/temporal_shadow_holdout/
evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/
```

Their predictions and failures have been inspected and directly inform TL01D.

They must be retained unchanged as:

```text
observed regression cohorts
```

They must not determine an independent promotion result.

TL01D requires:

```text
a new canonical holdout V2
and
a new synthetic adversarial V3
```

Both must be frozen before their first `tl01d-v1` provider execution.

---

## §3 Selected capability

### Capability

```text
Compare frozen tl01c-v1 against frozen tl01d-v1 using identical packet V2
inputs, then separate known-regression evidence from fresh promotion evidence.
```

### Prompt-only invariant

```text
tl01c-v1 and tl01d-v1 use:
  tl01c-packet-v1
  render_temporal_shadow_user_content_v2
  identical assertion packets
```

The only semantic treatment difference is the system instruction text.

### Authority invariant

```text
Every result remains a model-shadow overlay and evaluation artifact.
```

### Safety invariant

```text
No non-resolved annotation may carry occurrence_time or valid_time.
```

### Freshness invariant

```text
Observed cohorts may block promotion through regression,
but may not prove independent generalization.

Fresh sealed cohorts provide independent promotion evidence.
```

### Falsification test

The mission has widened beyond TL01D if implementation requires:

* modifying `TemporalPointV1`;
* modifying `TemporalEnvelopeV1`;
* modifying packet V2 source context;
* changing TL01B comparison classifications;
* weakening calibration thresholds;
* adding authoritative graph writes;
* adding accepted assertions;
* creating event identity;
* adding participant roles;
* adding Timeline surfaces;
* or modifying product APIs.

Stop rather than absorb those capabilities.

---

## §4 Mandatory first moves

Before coding:

1. Read:

```text
AGENTS.md
.cursor/rules/external-agent-pr-loop.mdc
.cursor/skills/external-agent-pr-loop/SKILL.md
.cursor/rules/responses-api-structured-extraction.mdc

Docs/Design/CONTRACT-temporal-envelope-v1.md
Docs/Design/CONTRACT-temporal-shadow-overlay-v1.md
Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md
Docs/Design/CONTRACT-temporal-prompt-calibration-v1.md

Docs/Reports/REPORT-tl01b-temporal-shadow-cohort.md
Docs/Reports/REPORT-tl01c-temporal-prompt-calibration.md

Docs/Plans/HANDOFF-tl01c-source-aware-temporal-prompt-calibration.md
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

3. Confirm PR 453 ancestry:

```bash
git merge-base --is-ancestor \
  14f7a0d385e1a986cee9edb007f670dc505f148d \
  origin/main
```

4. Confirm there is no overlapping TL01D pull request.

5. Inspect the committed TL01C aggregate and report.

6. Preserve unrelated worktree and runtime state.

---

## §5 Frozen dependencies

The following must remain immutable:

```text
tl01b-v1 instructions
tl01b-packet-v1
tl01c-v1 instructions
tl01c-packet-v1
render_temporal_shadow_user_content_v1
render_temporal_shadow_user_content_v2

TL01B comparison semantics
TL01C calibration thresholds
TL01C aggregate
TL01C report

temporal_shadow_cohort base/gold/evidence
temporal_shadow_holdout base/gold/evidence
temporal_shadow_adversarial_v2 base/gold/evidence
```

Do not edit old fixtures to improve TL01D results.

Do not overwrite the committed TL01C aggregate.

Retain the fixed baseline fingerprints:

```text
TL01B instructions:
c036558b52b8a44e5358fb7f3062dbf9db5b7f5bf86cb7fa2d986e7fddd0ceec

TL01B prompt:
c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51

TL01B V1 packet:
9925e9fb65c124a560cd231707b174139c5911e3f2eaab5d7088b001f80f8430

TL01C prompt:
86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3
```

Add a fixed fingerprint for `tl01d-v1` after candidate freeze.

---

## §6 Prompt registry addition

Add:

```python
TL01D_CONSERVATIVE_INSTRUCTIONS = """..."""
```

Register:

```python
"tl01d-v1": TemporalPromptSpec(
    version="tl01d-v1",
    instructions=TL01D_CONSERVATIVE_INSTRUCTIONS,
    packet_version=TL01C_PACKET_VERSION,
    render_user_content=render_temporal_shadow_user_content_v2,
)
```

Do not create a packet V3.

Do not create a renderer V3.

Do not mutate `tl01c-v1`.

Required identity behavior:

```text
prompt version: tl01d-v1
packet version: tl01c-packet-v1
renderer: render_temporal_shadow_user_content_v2
```

---

## §7 Candidate prompt: output-shape gate

The candidate prompt must begin with an explicit output-validity gate.

### Non-resolved statuses

For:

```text
not_applicable
ambiguous
unresolved
```

require:

```json
{
  "occurrence_time": null,
  "valid_time": null
}
```

No exception.

An ambiguous interpretation is not a partially resolved interpretation.

### Resolved status

For this experiment, resolved annotations should normally populate exactly one lane:

```text
event or change:
  occurrence_time non-null
  valid_time null

persistent-state boundary:
  occurrence_time null
  valid_time non-null
```

Do not emit both merely because an event creates a later state.

Use both only if the assertion proposition explicitly combines both semantics. None of the sealed TL01D evaluation cases should require that combined form.

---

## §8 Candidate prompt: temporal eligibility gate

Before examining source time, classify the assertion proposition into exactly one conceptual class.

### A. Bounded event or change

Examples:

```text
destroyed
arrived
killed
opened
collapsed
departed
discovered
revived
```

Expected lane:

```text
resolved + occurrence_time
```

### B. Persistent state with an explicit boundary

Examples:

```text
begins coordinating
becomes captain
starts controlling
first holds an office
ceases membership
relinquishes a role
stops owning
```

Expected lane:

```text
resolved + valid_time.start
or
resolved + valid_time.end
```

The selected assertion is the state, role, condition, ownership, or relationship—not the grammatical action used to establish its boundary.

### C. Static structure or topology

Examples:

```text
contains
connects
is north of
has a crypt
road between locations
```

Expected status:

```text
not_applicable
```

An eventive evidence sentence does not make a structural proposition temporal.

### D. Scene, section, or observation framing

Examples:

```text
party at a location
back at the inn
scene set in the guardhouse
observation during a recap
```

Expected status:

```text
not_applicable
```

The scene happened in time, but the extracted node or framing proposition does not express a useful temporal boundary.

### E. Mention or identity ambiguity

Examples:

```text
a name appears in a file
a word may be a person or password
an entity may or may not be identified
```

Expected status:

```text
ambiguous
```

Both temporal extents must remain null.

### F. Temporally relevant but insufficient

Use:

```text
unresolved
```

only when the assertion proposition is temporal but the evidence cannot safely identify its lane or value.

Do not use `unresolved` as a substitute for a clearly structural or scene-framing `not_applicable`.

---

## §9 Candidate prompt: source-time gate

Only after selecting the proposition class and temporal lane may the model inspect:

```text
source_context.source_time
```

Apply this sequence:

### Gate 1 — Is source time even eligible?

Source time is ineligible for:

```text
static structure
scene framing
observation scope
mention or identity ambiguity
re-attestation without boundary
background lore
quoted names or passwords
```

When ineligible:

```text
do not copy source time
```

### Gate 2 — Is another fictional time explicit?

When evidence states another time:

```text
Session 3
three winters earlier
about 30 years ago
before the expedition
after the coronation
```

then:

```text
reject source_context.source_time
```

The explicit fictional time wins.

### Gate 3 — Does the narrated source episode establish the selected proposition?

Source time may be copied only when:

1. The selected proposition is an event or explicit state boundary.
2. The evidence states that same proposition.
3. It occurs within the narrated source episode.
4. No different fictional time is supplied.

### Gate 4 — Copy, never reconstruct

When source time is eligible:

```text
copy the supplied TemporalPoint object as-is
```

Never reconstruct a session from:

* source filenames;
* evidence IDs;
* labels;
* path names;
* source-phrase strings;
* or invented `anchor_ref` values.

---

## §10 Candidate prompt: temporal normalization

### Session time

Use a session point only when it comes from:

```text
an eligible copied source_context.source_time
or
an explicit structured session reference supplied in the packet/evidence
```

Do not invent session IDs.

### Relative time

Use `kind="relative"` only when a valid structured relation and stable anchor are actually available.

Do not invent anchors such as:

```text
source_phrase:He left
session:session-11
event:the expedition
```

unless that exact stable reference is supplied in the packet.

### Textual time

When evidence provides an incomplete historical phrase but no stable structured anchor:

```text
use kind="textual"
```

`raw_expression` must be a verbatim contiguous substring of the cited evidence.

Preserve enough of the phrase to identify the temporal proposition.

Example:

```text
evidence:
"He left about 30 years ago."

preferred:
raw_expression = "left about 30 years ago"

not:
raw_expression = "around three decades earlier"
```

Do not paraphrase.

Do not discard the proposition-bearing verb when it is part of the complete temporal expression.

---

## §11 Candidate prompt: valid-time boundaries

### Start boundary

For propositions such as:

```text
begins coordinating guards
becomes watch captain
first holds the harbor keys
starts controlling the gate
```

emit:

```json
{
  "interpretation_status": "resolved",
  "occurrence_time": null,
  "valid_time": {
    "start": "<grounded point>",
    "end": null
  }
}
```

### End boundary

For propositions such as:

```text
relinquishes the keys
ceases being captain
leaves the faction
stops controlling the gate
```

emit:

```json
{
  "interpretation_status": "resolved",
  "occurrence_time": null,
  "valid_time": {
    "start": null,
    "end": "<grounded point>"
  }
}
```

Do not convert the boundary verb into occurrence time when the selected assertion represents the persistent state or relationship.

---

## §12 Few-shot requirements

Use synthetic examples only.

Reserve one vocabulary family exclusively for TL01D prompt examples, such as:

```text
Dessa
Orun
Caldrin
Glass Causeway
Lantern Court
Ivory Ledger
```

The fresh holdout and adversarial V3 must not use those names, nouns, or exact sentence patterns.

Include no more than eight examples.

Required classes:

1. Same-source bounded event.
2. Same-source valid-time start.
3. Same-source valid-time end.
4. Structural proposition despite eventive prose.
5. Scene framing.
6. Ambiguous identity with null extents.
7. Explicit alternate historical time overriding source.
8. Re-attestation without a new boundary.

Every example must have exactly one expected answer.

Do not use formulations such as:

```text
not_applicable or unresolved
relative or textual
```

Ambiguous examples in the prompt teach unstable behavior.

Each example must choose one exact output class and lane.

---

## §13 Calibration-runner generalization

The existing runner still hardcodes `tl01c-v1` as the candidate prompt.

Generalize it without replacing or forking the runner.

### Required behavior

Derive:

```text
control prompt version
candidate prompt version
```

from the loaded case files.

Require:

* every control case uses the same registered prompt version;
* every candidate case uses the same registered prompt version;
* control and candidate versions differ;
* candidate development, holdout, and adversarial cases agree;
* control development, holdout, and adversarial cases agree;
* paired cases differ only in permitted case identity and prompt-version fields.

For TL01D:

```text
control = tl01c-v1
candidate = tl01d-v1
```

Remove hardcoded uses of `tl01c-v1` from:

* expected manifest prompt maps;
* calibration ID construction;
* candidate hash generation;
* metrics slices;
* report metadata;
* CLI descriptions.

### Adversarial control lane

Add an optional control adversarial case so both prompts can be evaluated against fresh adversarial V3.

TL01D promotion runs require it.

Preserve compatibility with the committed TL01C invocation, where adversarial V2 was candidate-only.

### Aggregate identity

The aggregate must unambiguously preserve:

```text
control prompt version and hash
candidate prompt version and hash
all case IDs
all seal commits
all execution SHAs
all provider response IDs
```

Do not change comparison semantics or readiness thresholds merely to support generic prompt versions.

---

## §14 Observed regression matrix

The following cases are observed and non-independent:

### Original development

```text
control:
  temporal_shadow_cohort/temporal-case-tl01c.json

candidate:
  temporal_shadow_cohort/temporal-case-tl01d.json
```

### Prior canonical holdout

```text
control:
  temporal_shadow_holdout/temporal-case.json

candidate:
  temporal_shadow_holdout/temporal-case-tl01d.json
```

### Prior adversarial V2

```text
control:
  temporal_shadow_adversarial_v2/temporal-case.json

candidate:
  temporal_shadow_adversarial_v2/temporal-case-tl01d.json
```

Run three repetitions per prompt/case pair.

Write results under:

```text
evals/graph_memory_layer/artifacts/
  temporal_shadow_prompt_calibration/
    tl01d/
      regression/
```

These results may block promotion.

They may not establish independent readiness.

### Known regression expectations

Across every successful `tl01d-v1` repetition:

* Existing exact same-session events remain exact.
* Existing exact valid starts do not regress.
* Wolf Manor containment is always `not_applicable`.
* Copper and Quartz scene framing is always `not_applicable`.
* Sorin Holdrom mention is always `ambiguous`.
* Ambiguous output has null occurrence and valid time.
* Professor historical time receives no invented anchor.
* The prior adversarial V2 produces no schema-invalid output.
* Source-different cases do not copy source time.
* Valid-time end is emitted in the valid-time lane.
* Re-attestation does not invent a start boundary.

---

## §15 Fresh canonical holdout V2

Create:

```text
evals/graph_memory_layer/examples/
  temporal_shadow_holdout_v2/
```

Suggested case IDs:

```text
tl01d-temporal-shadow-holdout-v2-control
tl01d-temporal-shadow-holdout-v2-candidate
```

The paired cases must use:

```text
control prompt: tl01c-v1
candidate prompt: tl01d-v1
```

Both use packet V2.

### Holdout authoring order

1. Finalize `tl01d-v1`.
2. Commit the frozen prompt.
3. Record its hash.
4. Select canonical holdout assertions.
5. Author human gold without executing either prompt.
6. Create paired control/candidate case files.
7. Commit and seal the holdout.
8. Do not modify the candidate prompt or holdout afterward.

### Independence requirements

The new holdout must not reuse:

* development assertion IDs;
* prior holdout assertion IDs;
* prior evidence IDs;
* prior evidence spans;
* prompt-example entities or phrases;
* adversarial V2 entities;
* adversarial V3 entities.

Prefer source passages from sessions not used by the prior holdout.

### Target composition

Aim for 8–12 canonical assertions, including when safely available:

1. Two same-source bounded events.
2. One persistent valid-time start.
3. One persistent valid-time end.
4. One static structural proposition.
5. One scene or observation-framing proposition.
6. One ambiguous name or identity proposition.
7. One incomplete textual historical time.
8. One re-attestation without a boundary.
9. One explicit fictional time different from source time.

Do not fabricate canonical coverage.

If valid-time end or source-different occurrence cannot be found safely, report that absence and cover it only in adversarial V3.

---

## §16 Fresh synthetic adversarial V3

Create:

```text
evals/graph_memory_layer/examples/
  temporal_shadow_adversarial_v3/
```

Use a new vocabulary family that overlaps with neither prompt examples nor adversarial V2.

Required cases:

1. Source session differs from explicit occurrence session.
2. Source session differs from explicit valid-time start.
3. Valid-time end in the narrated source episode.
4. Structural assertion surrounded by eventive prose.
5. Scene framing with an obvious source session.
6. Re-attestation without a start or end.
7. Ambiguous identity that tempts the model to include extents.
8. Textual historical time with no stable structured anchor.

For the ambiguous case, the gold must require:

```text
interpretation_status = ambiguous
occurrence_time = null
valid_time = null
```

Create paired cases:

```text
control prompt: tl01c-v1
candidate prompt: tl01d-v1
```

Seal V3 before provider execution.

Synthetic V3 results remain separate from canonical results.

---

## §17 Promotion matrix

Run a second, independent calibration under:

```text
evals/graph_memory_layer/artifacts/
  temporal_shadow_prompt_calibration/
    tl01d/
      promotion/
```

Required pairs:

```text
control tl01c-v1 × original development
candidate tl01d-v1 × original development

control tl01c-v1 × fresh holdout V2
candidate tl01d-v1 × fresh holdout V2

control tl01c-v1 × fresh adversarial V3
candidate tl01d-v1 × fresh adversarial V3
```

Run three repetitions per pair using:

```text
gpt-5.4-mini
```

All runs must use one clean implementation commit.

The subsequent aggregate/report commit must be documentation-and-artifact-only.

---

## §18 Promotion decision

Retain the existing calibration decision enum and priority ordering.

A candidate cannot receive:

```text
PROMPT_READY_FOR_BROADER_SHADOW
```

unless all existing READY requirements pass.

Additional TL01D requirements:

### Safety and validity

Across every candidate promotion repetition:

```text
provider failures = 0
contract failures = 0
evidence/case failures = 0
grounding failures = 0
model-output failures = 0
unsafe over-resolution = 0
source→occurrence leakage = 0
source→valid-time leakage = 0
```

### Stable semantic coverage

Fresh holdout:

```text
min status accuracy >= 0.80
min not-applicable accuracy = 1.0
exact occurrence min >= 1
exact valid-time min >= 1
```

Additionally, human review must confirm:

* the ambiguous row is correct in all repetitions;
* its temporal extents are null in all repetitions;
* the textual historical row never invents an anchor;
* the valid-time start is exact in all repetitions;
* any canonical valid-time end is exact in all repetitions.

### Control comparison

Candidate must not regress relative to `tl01c-v1` on:

* exact same-session occurrence rows;
* exact valid-time rows;
* status accuracy;
* evidence grounding;
* payload validity.

Candidate must materially improve:

* unsafe over-resolution;
* source leakage;
* non-applicable stability;
* ambiguous-output validity;
* valid-time lane stability.

### Regression requirement

The observed regression matrix must meet §14 expectations.

A fresh holdout success cannot excuse regression on known unsafe cases.

---

## §19 Decision interpretation

### `PROMPT_READY_FOR_BROADER_SHADOW`

Use only when:

* all automated promotion thresholds pass;
* all TL01D-specific manual gates pass;
* observed regression expectations pass;
* all seals and manifests verify;
* every provider run uses the same implementation SHA.

### `ITERATE_PROMPT`

Use when:

* unsafe or leakage behavior remains;
* ambiguous or non-applicable decisions remain unstable;
* model-output failures remain;
* known regression cases fail;
* or fresh promotion quality is insufficient.

Freeze `tl01d-v1` after execution.

A further prompt attempt must use a new version ID.

### `BLOCKED_BY_INPUT_REPRESENTATION`

Use only when:

* proposition status and temporal lane are consistently correct;
* unsafe over-resolution and leakage are zero;
* but normalized values remain wrong because packet V2 lacks necessary explicit data.

Do not use this verdict while safety failures remain.

### Other decisions

Retain existing contract, evidence, and provider-failure meanings.

---

## §20 Expected changed paths

Likely modifications:

```text
MODIFY  src/graph_memory/temporal_shadow_extraction.py
MODIFY  evals/graph_memory_layer/temporal_shadow_prompt_calibration.py

MODIFY  tests/test_temporal_shadow_extraction_tl01c.py
MODIFY  tests/test_temporal_shadow_prompt_calibration.py
CREATE  tests/test_temporal_shadow_extraction_tl01d.py

CREATE  evals/graph_memory_layer/examples/
        temporal_shadow_cohort/temporal-case-tl01d.json

CREATE  evals/graph_memory_layer/examples/
        temporal_shadow_holdout/temporal-case-tl01d.json

CREATE  evals/graph_memory_layer/examples/
        temporal_shadow_adversarial_v2/temporal-case-tl01d.json

CREATE  evals/graph_memory_layer/examples/
        temporal_shadow_holdout_v2/*

CREATE  evals/graph_memory_layer/examples/
        temporal_shadow_adversarial_v3/*

CREATE  Docs/Design/CONTRACT-temporal-prompt-calibration-v2.md
CREATE  Docs/Reports/REPORT-tl01d-temporal-decision-gate.md
CREATE  Docs/Plans/HANDOFF-tl01d-conservative-temporal-decision-gate.md
```

Bounded committed aggregates:

```text
CREATE  evals/graph_memory_layer/artifacts/
        temporal_shadow_prompt_calibration/
        tl01d/regression/calibration/aggregate.json

CREATE  evals/graph_memory_layer/artifacts/
        temporal_shadow_prompt_calibration/
        tl01d/promotion/calibration/aggregate.json
```

If the regression aggregate cannot be clearly marked non-promotional using the existing schema, commit a bounded regression summary instead and state that it carries no promotion verdict.

---

## §21 Prohibited changes

Do not modify:

```text
src/graph_memory/kernel/temporal.py
src/graph_memory/temporal_shadow.py
src/graph_memory/kernel/contributions.py
src/graph_memory/kernel/contribution_models.py
src/graph_memory/candidate_graph_to_contribution.py
src/graph_memory/kernel/contribution_merge.py
src/graph_memory/kernel/world_projection.py

apps/live_control_server/
apps/live-control-ui/
production extraction prompts
runtime graph stores
```

Do not change:

* packet V2 structure;
* source-time derivation;
* TL01B comparator semantics;
* TL01C historical aggregate;
* prior gold overlays;
* readiness thresholds to accommodate model behavior.

---

## §22 Required tests

### Prompt registry

Prove:

* `tl01d-v1` resolves through the registry.
* It uses packet V2.
* It uses renderer V2.
* It has a fixed prompt hash.
* `tl01b-v1` and `tl01c-v1` fingerprints remain unchanged.
* Unknown prompt versions fail before provider invocation.

### Prompt-content contract

Prove the candidate instructions explicitly contain:

```text
non-resolved → null extents
proposition eligibility before source time
bounded event → occurrence
persistent state boundary → valid time
structural → not_applicable
scene framing → not_applicable
identity ambiguity → ambiguous
explicit other time rejects source time
no invented anchor_ref
textual raw expression must be verbatim
valid-time start
valid-time end
```

Prove every few-shot has one exact expected answer.

Prove prompt-example vocabulary is absent from:

* observed cohorts;
* fresh holdout V2;
* fresh adversarial V3.

### Generic calibration runner

Prove:

* control and candidate versions are derived from case files.
* No hardcoded `tl01c-v1` candidate remains.
* Mixed candidate prompt versions fail before provider calls.
* Mixed control prompt versions fail before provider calls.
* Control and candidate cases remain paired equivalents.
* Optional control adversarial works.
* TL01C historical invocation remains compatible.
* Aggregate hashes match the executed prompt versions.
* Manifest validation uses the derived versions.
* Calibration ID changes when either prompt changes.

### Cohort freshness

Prove:

* fresh holdout IDs and evidence do not overlap prior cohorts;
* fresh adversarial V3 vocabulary does not overlap prompt examples or V2;
* old holdout and adversarial V2 remain byte-stable;
* promotion uses fresh holdout V2 and adversarial V3;
* regression results cannot be mislabeled as independent promotion evidence.

### Output-shape regressions

Prove model batches fail closed when:

* ambiguous includes occurrence time;
* ambiguous includes valid time;
* not_applicable includes extents;
* unresolved includes extents;
* invented relative anchors violate transport or grounding rules;
* target sets differ.

### Required command

Run at minimum:

```bash
uv run pytest \
  tests/test_temporal_shadow_extraction.py \
  tests/test_temporal_shadow_extraction_tl01c.py \
  tests/test_temporal_shadow_extraction_tl01d.py \
  tests/test_temporal_shadow_prompt_calibration.py \
  tests/test_temporal_shadow.py \
  -q

git diff --check
```

Record exact results.

---

## §23 Live proof order

### Phase A — Implement and freeze prompt

1. Add `tl01d-v1`.
2. Complete prompt unit tests.
3. Commit prompt and runner generalization.
4. Record candidate prompt hash.
5. Do not edit prompt after this point.

### Phase B — Author fresh cohorts

1. Select new canonical holdout evidence.
2. Author candidate-only contribution and human gold.
3. Create control/candidate mirror cases.
4. Create independent adversarial V3.
5. Verify vocabulary and ID independence.
6. Commit and record both seal SHAs.

### Phase C — Regression run

Run three repetitions on observed cohorts.

Do not edit prompt based on regression results during this PR.

A regression failure produces an honest failed TL01D candidate.

### Phase D — Promotion run

From one clean implementation commit:

1. Verify fresh holdout and adversarial seals.
2. Verify development fixtures against execution blobs.
3. Run the full paired matrix.
4. Preserve every success and failure manifest.
5. Generate bounded aggregate.

### Phase E — Documentation-only commit

After provider execution:

* commit aggregate;
* write report;
* update PR body;
* make no execution-path code changes.

If execution-path code changes are required, rerun the matrix from the new implementation commit.

---

## §24 Required report

Create:

```text
Docs/Reports/REPORT-tl01d-temporal-decision-gate.md
```

Required sections:

```markdown
# TL01D Conservative Temporal Decision Gate

## Executive result

## Dependency and implementation SHAs

## Frozen control

## Frozen candidate

## Prompt-only comparison proof

## Candidate decision gate

## Runner generalization

## Observed regression cohorts

## Regression results

## Fresh holdout authoring and seal

## Fresh canonical holdout results

## Fresh adversarial V3 authoring and seal

## Fresh adversarial results

## Safety metrics

## Quality metrics

## Per-assertion stability

## Source-leakage analysis

## Valid-time lane analysis

## Ambiguous-output validity

## Textual-time normalization

## Provider metadata

## Coverage limitations

## Calibration decision

## Successor recommendation
```

The report must explicitly separate:

```text
observed regression evidence
from
fresh independent promotion evidence
```

Do not describe the prior TL01C holdout as independent for TL01D.

---

## §25 Explicit non-goals

TL01D does not:

* change packet V2;
* change temporal kernel schemas;
* modify source-time derivation;
* modify TL01B evaluator semantics;
* create authoritative temporal annotations;
* publish graph revisions;
* create event nodes;
* create participant-role annotations;
* expand to a broad canonical corpus;
* add API routes;
* add UI;
* modify Hermes;
* or promote model outputs into accepted graph state.

---

## §26 Acceptance criteria

TL01D is complete only when:

* [ ] PR 453 merge is in ancestry.
* [ ] Work begins from clean current `origin/main`.
* [ ] No overlapping TL01D PR exists.
* [ ] `tl01b-v1` remains frozen.
* [ ] `tl01c-v1` remains frozen.
* [ ] `tl01d-v1` is registered with packet V2 and renderer V2.
* [ ] Candidate prompt hash is fixed before cohort authoring.
* [ ] Non-resolved statuses require null temporal extents.
* [ ] Proposition classification precedes source-time use.
* [ ] Structural assertions map to `not_applicable`.
* [ ] Scene framing maps to `not_applicable`.
* [ ] Identity ambiguity maps to `ambiguous`.
* [ ] Valid starts use `valid_time.start`.
* [ ] Valid ends use `valid_time.end`.
* [ ] Explicit alternate time rejects source time.
* [ ] Textual time forbids invented anchors.
* [ ] Every few-shot has one exact expected answer.
* [ ] Runner no longer hardcodes the candidate prompt version.
* [ ] Control and candidate prompt versions are case-derived.
* [ ] Control adversarial execution is supported.
* [ ] Historical TL01C invocation remains compatible.
* [ ] Prior holdout and adversarial V2 remain unchanged.
* [ ] Prior cohorts are labeled regression-only.
* [ ] Fresh canonical holdout V2 is created and sealed.
* [ ] Fresh adversarial V3 is created and sealed.
* [ ] Fresh cohorts do not overlap prior IDs, evidence, or prompt vocabulary.
* [ ] Regression matrix runs three repetitions.
* [ ] Promotion matrix runs three repetitions.
* [ ] Every provider response ID is preserved.
* [ ] Every failure publishes a typed failure manifest.
* [ ] Every manifest uses the same implementation SHA.
* [ ] Regression and promotion aggregates are not conflated.
* [ ] No readiness threshold is weakened.
* [ ] No graph write occurs.
* [ ] No TL00 or TL01 kernel contract changes occur.
* [ ] Focused tests pass.
* [ ] `git diff --check` passes.

---

## §27 Stop conditions

Stop and report when:

* packet V2 must change to express the intended answer;
* the correct answer cannot be represented by TL00/TL01;
* a fresh canonical holdout cannot be created without reusing prior evidence;
* the candidate prompt was modified after holdout sealing;
* fresh cohort gold was altered after observing provider output;
* control and candidate cases are not exact A/B mirrors;
* runner generalization changes historical TL01C results;
* source-time derivation must be duplicated or bypassed;
* a non-ignored untracked input affects live execution;
* provider runs span multiple implementation SHAs;
* or an overlapping PR already owns the capability.

Use:

```text
Stop condition:
Repository SHA:
Prompt version:
Prompt SHA:
Case ID:
Assertion ID:
Evidence IDs:
Observed behavior:
Why TL01D cannot absorb it:
Required next decision:
Suggested successor:
```

---

## §28 Required PR body

```markdown
## Mission

Add frozen `tl01d-v1`, a conservative temporal-eligibility gate evaluated
against frozen `tl01c-v1` using identical packet V2 inputs.

## Dependency

PR #453 / merge `14f7a0d385e1a986cee9edb007f670dc505f148d`

## Prompt identity

- control: `tl01c-v1`
- control SHA: `<sha>`
- candidate: `tl01d-v1`
- candidate SHA: `<sha>`
- packet: `tl01c-packet-v1`
- renderer: `render_temporal_shadow_user_content_v2`

## Experiment separation

- observed regression:
  - original development
  - prior TL01C holdout
  - adversarial V2
- fresh promotion:
  - holdout V2
  - adversarial V3

## Seals

- holdout V2 seal: `<sha>`
- adversarial V3 seal: `<sha>`

## Live execution

- implementation SHA: `<sha>`
- model: `gpt-5.4-mini`
- repetitions: 3
- provider-run SHAs: `<list>`

## Results

| Metric | tl01c control | tl01d candidate |
| --- | ---: | ---: |
| Regression unsafe | | |
| Regression source leakage | | |
| Fresh holdout exact median | | |
| Fresh holdout valid-time min | | |
| Fresh holdout NA min | | |
| Fresh adversarial model-output failures | | |
| Fresh promotion unsafe | | |
| Fresh promotion source leakage | | |

## Calibration decision

`<decision>`

## Existing behavior preserved

- TL01B frozen
- TL01C frozen
- packet V2 unchanged
- comparator unchanged
- no graph writes
- no Timeline API or UI
- no participant roles

## Tests

<exact commands and results>
```

---

## §29 Required handback

The coding-agent handback must include:

1. Base SHA.
2. Head SHA.
3. Branch and worktree.
4. PR 453 ancestry confirmation.
5. Exact changed paths.
6. TL01B frozen hashes.
7. TL01C frozen hash.
8. TL01D prompt hash.
9. Confirmation that TL01C and TL01D use identical packet/rendering.
10. Candidate decision-gate summary.
11. Few-shot inventory and reserved vocabulary.
12. Runner-generalization summary.
13. Backward-compatibility confirmation.
14. Observed regression case IDs.
15. Regression run manifests.
16. Regression provider response IDs.
17. Regression metrics.
18. Fresh holdout V2 case IDs and file digests.
19. Fresh holdout seal SHA.
20. Fresh adversarial V3 case IDs and file digests.
21. Fresh adversarial seal SHA.
22. Confirmation prompt froze before cohort authoring.
23. Confirmation gold froze before execution.
24. Promotion implementation SHA.
25. Promotion provider-run SHAs.
26. Promotion provider response IDs.
27. Control aggregate metrics.
28. Candidate aggregate metrics.
29. Per-assertion stability summary.
30. Ambiguous-output validity summary.
31. Source-leakage summary.
32. Valid-time start/end summary.
33. Textual-time normalization summary.
34. Final calibration decision.
35. Exact test commands and results.
36. `git diff --check` result.
37. Paths outside allowlist, expected `none`.
38. Runtime graph state touched, expected `none`.
39. Confirmation TL00 unchanged.
40. Confirmation packet V2 unchanged.
41. Confirmation comparator unchanged.
42. Confirmation no graph write occurred.
43. Recommended successor slice.

---

## §30 Successor decision

### If `PROMPT_READY_FOR_BROADER_SHADOW`

Dispatch:

```text
TL01E — Broader Canonical Temporal Shadow Cohort
```

That slice should evaluate `tl01d-v1` across a larger canonical sample without changing the prompt.

Do not proceed directly to participant roles.

### If `ITERATE_PROMPT`

Freeze `tl01d-v1`.

A further prompt candidate must use a new version ID.

### If `BLOCKED_BY_INPUT_REPRESENTATION`

Design the smallest packet V3 amendment required by the evidence.

Do not disguise a packet limitation as more prompt wording.

### If `BLOCKED_BY_EVIDENCE`

Repair or replace the fresh cohort under a new version.

Do not modify observed gold after provider execution.

### If `BLOCKED_BY_CONTRACT` or `PROVIDER_FAILURE`

Resolve that dependency before further prompt iteration.

---

## §31 Final directive

The next prompt must learn that temporal extraction is not:

```text
find a date or session near the assertion
```

It is:

```text
decide whether the selected proposition has temporal semantics
then choose the correct lane
then decide whether source provenance is semantically eligible
then normalize only what the evidence actually supports
```

The model must reliably distinguish:

```text
an event from a state
a state boundary from an occurrence
a structure from an eventive sentence
a scene from a temporal assertion
a name mention from an identity event
source provenance from fictional time
textual history from an invented relative anchor
ambiguity from partial resolution
```

Preserve the contracts.

Preserve packet V2.

Use a fresh holdout.

Let failure remain visible.
