# COMPOSITION: response-writing contract

ACTIVE: user armed the response-writing goal: separate voice/task/evidence/native
schema; remove inactive capabilities; remove host bookkeeping at owners and factor
exact qualification repetition; make frozen experiments routine; assess independent
quality dimensions and calibrate a judge before trusting scores.

## Serial delivery

Predecessor PR2334 merged a236fbfa6de55c442799a620c1a3cd16dde4f2b3.
Its flat format remains an experiment: input -10.1%,9/9 concepts,2 citation gaps.

Slice1: response prompt compiler and versioned frozen-prompt workflow. Branch
codex/response-writing-contract from fetched origin/main; same existing isolated
checkout. Exclusive write lease: this handoff;
src/application_state/agent_conversation/response_prompt.py;
apps/live_control_server/services/plan_jev_writer.py;
evals/buddy_benchmark/workflow.py; tests/test_response_prompt.py;
tests/test_buddy_benchmark_workflow.py; tests/test_plan_jev_writer.py;
Docs/Guides/ordinary-benchmark-workflow.md.
No active open PR overlaps these backend paths. No runtime/port/database writes.
Local tests and actual SDK mock request verification; independent exact-head review.
Keep product activation, native schema, evidence projection and all
author/image/clarify operations unchanged in this slice. The actual product owner
integration follows cleaned-context prompt comparisons; it must remove superseded
discussion assembly rather than override an already-built oversized prompt.
Component/version records are host-only. This ordering avoids known bookkeeping
exposure in another paid call and avoids changing prompt plus evidence in one test.

Subsequent serial slices remain required, not fulfilled by slice1:
- Trace and remove bookkeeping at qualification creation/projection owners; do not
  regex-scrub mixed semantic prose. Factor byte-identical qualification blocks while
  preserving distinct meaning, support and traceability. No factual pruning.
- Qualify other active ordinary response owners with the same contract, leaving
  capability instructions only where actually granted/selected.
- Freeze cleaned context/model/route/schema; compare component changes separately
  through existing tooling, retaining exact requests, failures, answers, usage,
  cost/timing and assessments. No retrieval replay or per-question launchers.
- Calibrate a native-schema judge against retained independently reviewed pass,
  omission, chronology and citation-failure examples; report disagreement/stability
  before using its multidimensional scores. Human prose preference stays separate.

## Completion evidence still required

One inspectable actual response assembly path; a defensible measured initial prompt;
no model-visible host bookkeeping; lossless shared qualification references;
versioned component/configuration control; frozen reproducible response experiments;
separate completeness/grounding/attribution/chronology/citation/directness/prose
assessments; calibrated judge limitations; obsolete assembly paths removed.
Paid writer comparisons wait for known context bookkeeping leakage to be resolved.
Primary data and all historical evidence remain unchanged. Goal stays active until
the full objective is verified, not merely this first implementation slice.
