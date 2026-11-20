# CI: classify the merged writer assessment test

ACTIVE PRIME serial prerequisite from18359e0713763e55d986daa8a7966c3371aa09c5,
branch codex/ci-writer-assessment-inventory in existing context-loop checkout.
PR2349 source/UI review passed, but independent review held integration because
merged2348 added tests/test_writer_assessment.py without classification. This
main-only omission is separate from the frozen References implementation.

Expected writes: this handoff and exactly one fast-lane entry in
ci/test-classification.json. The file tests local synthetic judge-input/schema and
calibration functions, without DB/provider effects. Fast matches these pure local
functions; benchmark-workflow orchestration remains domain integration. No selectors, workflows, tests, runtime or judge/gold
behavior changes. Keep original main inventory failure in retained evidence.

Verify exact clean CI guards/inventory and actual writer assessment tests;
independent review before PRIME merge. Source-only; no service restart. Then
return to unchanged reviewed Reference04f5f0adcb9627605312343b8fc3c7af482ddf95
and verify prospective merge/UI tree equivalence. No ADVERSARY coordination.
