# C1S4 Preplanning Vertical Slice

## Purpose
Deterministic scaffold proving planner-visible context can be built from C1S1-C1S3 only.

## Scope
Build bounded KB manifest + retrieval smoke context bundles for Longmont Campaign 1.

## What this proves
- This slice proves that a planner-visible context bundle can be built from C1S1–C1S3 only.
- C1S4 oracle surfaces are blocked by policy and leakage checks.

## What this does not prove
- It does not run a live planner.
- It does not grade prep against C1S4 yet.
- It does not tune retrieval.

## How to run Step 0
`uv run python evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py`

## How to run Step 1
`uv run python evals/c1s4_preplanning_vertical_slice/step1_retrieval_context.py`

## Oracle boundary policy
Policy lives in `gold/kb_policy.json`, distinguishing forbidden planner-visible C1S4 surfaces from preferred/fallback grader oracle source paths.

## Expected next PRs
- Oracle target authoring for C1S4.
- Live planner trace generation.
- Oracle grading harness.

## Step 1B — Prior plus support retrieval

Step 1B loads C1S1-C1S3 session memory plus hand-authored support knowledge cards.

It has two diagnostic modes:

- `prior_plus_support_content_only`
- `prior_plus_support_content_plus_lexical_hints`

The retriever must not use `usable_for_questions`, question IDs, oracle-risk labels, expected context, or benchmark target metadata.


## Beat/question target artifact

`gold/c1s4_beat_question_targets.json` defines Q1–Q38, the planning-question target surface for synthetic C1S4 prep.

This artifact is not planner-visible retrieval material. It is a benchmark/evaluation specification.

It separates:
- prior-recap-supported questions,
- worldbuilding-required questions,
- support-knowledge-required questions,
- creative-generation questions,
- oracle-only / must-not-predict details.

Validation:
`uv run python evals/c1s4_preplanning_vertical_slice/validate_beat_question_targets.py`

## Step 2 — Question context packets

Step 2 reads the planner-forbidden beat/question target artifact as controller input, retrieves context using one selected retrieval mode, and emits planner-visible question context packets.

It does not generate answers.

It does not grade.

It does not load target metadata into retrieval.

Evaluator-only questions such as Q35 are skipped for planner-facing packet generation.


## Step 3 — Stub answer packets

Step 3 converts Step 2 question context packets into answer packets without generating answers.

This locks the answer-output schema expected by future generated-answer work.

Step 3 does not:
- call an LLM,
- generate answer text,
- grade against C1S4,
- read oracle material.

All answer packets must have `answer_generation_status: stubbed_not_generated`.

## Step 4 — Generated answer packets

Step 4 converts planner-visible context packets into generated answer packets.

The default generator is `template_stub`, which is deterministic and does not call an LLM.

Step 4 does not grade against C1S4 and does not read oracle material.

Generated answer packets must preserve authority labels, known gaps, guardrails, and oracle leakage checks.

## Step 5 — Synthetic prep packet

Step 5 aggregates generated answer packets into a structured synthetic C1S4 prep packet.

It does not read C1S4 oracle material.

It does not grade against observed C1S4.

It does not claim the prep matches what happened.

The prep packet preserves retrieval mode, authority labels, known gaps, must-not-include guardrails, and oracle-risk warnings.

## Step 6 — Oracle comparison scaffold

Step 6 is the first oracle-side stage.

It loads held-out C1S4 oracle material only inside the comparison harness and compares the synthetic prep packet to the oracle at a coarse structural/lexical level.

Step 6 does not:
- feed oracle material back into retrieval,
- modify planner-visible packets,
- tune generation,
- produce a final quality score.

The output is a comparison report, not a pass/fail grade.

## Step 2C — Expected context benchmark

Step 2C benchmarks whether Step 2 question context packets retrieve the expected context for each planning question and retrieval mode.

The benchmark grades retrieved context, not generated answers.

The expected-context gold file is eval-only and planner-forbidden. It must never be used to retrieve records or build context packets.

Step 2C reports required context group recall, forbidden context hits, known-gap handling, and mode deltas between prior-only and support-enabled retrieval.
