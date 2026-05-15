# Gates

## Gate 0 — KB boundary
- Passes if C1S1-C1S3 records load into one manifest
- Fails if any C1S4 source/session/path appears

## Gate 1 — Retrieval/context bundle smoke
- Passes if preplanning queries produce oracle-safe context bundles
- Fails if bundle contains C1S4 references

## Gate 2 — Oracle target authoring / beat-question target surface
- Partial.
- Passes when `gold/c1s4_beat_question_targets.json` exists and validates.
- Passes when Q1–Q38 are represented with authority labels, oracle-risk labels, known gaps, and must-not-include terms.
- Fails if the target artifact is planner-visible retrieval material.
- Does not yet grade planner output.

## Gate 3 — Live planner trace
- Future
- Not in this PR

## Gate 4 — Oracle grading
- Future
- Not in this PR

## Gate 1B — Prior plus support retrieval
- Passes when support records load into the same normalized retrieval surface as session memory.
- Passes when content-only and lexical-hint modes report separately.
- Fails if retrieval uses question IDs or eval-only fields.
- Fails if C1S4 oracle material enters planner-visible context.

## Gate 2B — Question context packet harness

Passes when:
- Q1–Q38 target questions can be loaded.
- Planner-facing questions produce context packets for each retrieval mode.
- Evaluator-only Q35 is skipped.
- Eval-only target fields are absent from packets.
- Packets preserve authority metadata.
- C1S4 oracle material remains excluded.
- `answer_slot` remains null.

Does not yet generate answers or grade output.


## Gate 3A — Answer packet schema / stub harness

Passes when:
- Step 3 builds answer packets from Step 2 context packets.
- Q35 remains skipped.
- `answer_text` and `structured_answer` remain null.
- eval-only fields are absent.
- authority, known-gap, expected-behavior, and oracle-risk fields are preserved.
- C1S4 oracle leakage checks still pass.

Does not yet generate answers.
Does not yet grade answers.

## Gate 3B — Generated answer packet harness

Passes when:
- Step 4 generates answer packets from planner-visible context.
- Q35 remains skipped.
- Generated packets preserve authority labels, known gaps, guardrails, and oracle-risk fields.
- Unsupported forbidden terms are detected.
- C1S4 oracle material remains excluded.
- No oracle grading is performed.

Does not yet judge answer quality against C1S4.

## Gate 4A — Synthetic prep packet aggregation

Passes when:
- Step 5 builds a synthetic prep packet from Step 4 generated answer packets.
- Required prep sections exist.
- Q35 remains skipped.
- Known gaps and guardrails are preserved.
- Oracle leakage and unsupported forbidden terms cause failure.
- The packet does not claim to match observed C1S4.

Does not yet grade against C1S4.
