# CI: additive PR verification

Status: ACTIVE under Alan's five-stage plan and coordinator's explicit parallel
stage3 authorization. Owner: CI worker. Base f6e174e407ab83b4632160771412b77c09833ed0;
branch codex/ci-additive-fast-gate; isolated ci-additive-fast-gate checkout.
Topology parallel-independent with2288 and all product lanes: no dependency on
its workflow, graph behavior or unmerged native repair. No current gates change.

Exclusive expected writes: .github/workflows/additive-pr.yml; scripts/ci_fast.py;
tests/test_ci_fast_gate.py; this handoff; ci/test-classification.json only the
additive new guard entry. CI2288 classification writes are frozen during this
lease; transfer before edits by another CI lane. No graph/product/runtime source,
lockfile, database fixture, deployment, protection or live-data writes.

Run discovered frontend defaults (all Vitest tests, no allowlist), full type/build,
existing auth denial tests and four real template-clone PostgreSQL witnesses for
wrong principal, stale CAS, rollback and draft/save/history. Local World/graph draft
regressions remain within discovered frontend coverage. Use unchanged session
migration/per-test clone fixture. Every job and aggregate fails on real failure;
no continue-on-error or source path filtering. Publish source SHA and measured
command durations. Existing hosted/ownership gates stay authoritative. Current
full frontend qualification is red173cases; this lane does not manufacture green.
The five-minute aspiration is unproven and never permits coverage reduction.

Before delivery: exact command/file guards, real isolated database run, hosted
measurements, independent exact-head review and coordinator disposition. Stage2
main graph qualification remains HOLD. This lane cannot enable selection or claim
that the full regression baseline has been repaired.
