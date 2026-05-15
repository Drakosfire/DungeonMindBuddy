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
