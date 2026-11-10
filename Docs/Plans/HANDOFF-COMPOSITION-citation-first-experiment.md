# COMPOSITION: citation-first schema experiment

ACTIVE authorized by the user's request to run the citation-first experiment.
Serial tooling slice after settled response-contract PR2356; branch
codex/writer-citation-first-experiment from f73fadcfd01005c9119d7b21209a3a1b5920bd5b.
Expected writes: this handoff, evals/buddy_benchmark/workflow.py,
tests/test_buddy_benchmark_workflow.py, Docs/Guides/ordinary-benchmark-workflow.md.
Current open UI/storage/CI lanes checked; no overlap. No production schema/default,
retrieval, database, deployment or primary-state effects. Evidence is retained in
out/response-writing-contract-v1/citation-first-experiment-v1; no per-question script.

Hypothesis: generating a segment's citation selectors before its prose reduces
unsupported strengthening and mismatched own-citations without more instructions.
Change only native claim property order through the existing context-tasting
workflow. Keep baseline Q15 input, tighter prompt/components, model, provider route,
schema constraints, reasoning/output settings and accounting fixed. Historical
formatv1 remains frozen; do not silently upgrade to current product formatv2.

One bounded PR extends existing tooling with an explicit schema-order experiment.
Verify at serialized HTTP request boundary that the native strict schema reaches
OpenRouter with selectors before text; retain raw body bytes/hash and property
order evidence, never authorization headers. Stop before dispatch if the treatment
is lost. Existing artifact JSON canonicalization sorts keys, so saved dictionary
order alone is not wire evidence. Current native runtime and historical readers
remain unchanged. Test original constraints unchanged, actual SDK wire ordering,
and refusal before HTTP when ordering differs; independent exact-head review.

Execute one candidate using the existing workflow, no unchanged baseline rerun.
Retain actual answer/output field order, usage, reported cost and timing. Assess
nine required concepts, grounding/attribution/chronology and each segment's own
selected support; user prose preference remains the tighter baseline. Acceptance:
9/9 coverage, no confirmed strengthening or own-citation gap, no new attribution
or chronology defect. Report resource changes, not causal timing conclusions from
one pair. If no positive signal or ordering is ignored, stop; no added instructions
or retry-until-pass. No production adoption from one Q15 result. Any promising
result needs a separately bounded repeated comparison before adoption.
