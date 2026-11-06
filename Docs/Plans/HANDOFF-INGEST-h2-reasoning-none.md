# INGEST: H2 explicit no-reasoning treatment

Status ACTIVE for implementation/testing/PR only. Paid execution remains gated by
H2 design v4 and exact activation pins. This is an unmerged experimental candidate,
not adopted product default.

Branch `codex/ingest-h2-reasoning-none`; stack parent #2164 exact
`7fdb1a14d1c459bee2fb31f04906e967a4a18f0c`, whose parent is #2152.
Merge order, only if later authorized: #2152 → #2164 → this child. Evaluator
#2165 is a separate stack. Do not merge or deploy the treatment before the study
acceptance decision; rejected behavior remains history, no active fallback.

Only production delta: ordinary recap owning limits construction changes
`reasoning_effort="low"` to `"none"`. No flags, injected clients, producer,
representation, retry policy, pass topology, prompts, model/route or output/deadline
change. Both H2 arms use the shared corrected beat-rank contract and donor-inclusive
baseline. Preserve original immutable baseline and historical H1 evidence.

Write lease: `apps/live_control_server/services/graph_preview_runner.py`,
`tests/test_recap_reasoning_allocation.py`, and this handoff. No active lane
edits these paths; existing WRITER and evaluator lanes are disjoint. No ports,
providers, source/Gold, databases, migrations, primary state or heldouts affected.

Verification: exercise owning wrapper with inert collaborators through the
constructed production request; prove exact existing limits and default-owned
client path. Exercise existing bounded provider-request/telemetry boundary for
both low/none using a fake engine. Inspect cumulative diff and independently
review exact head, commit/push/open PR. Compose treatment by exact patch onto
verified common runtime, preserving all donor members; pin and independently
verify the one-setting behavioral difference before any capture. Catalogue
support or fake-engine success alone does not prove routed provider enforcement.

## Verification evidence

Author: 3 new inert tests pass; 42 focused allocation/recap-excerpt/schema checks
pass. Initial fake-engine tests omitted the existing semantic engine fixture and
failed before a usable receipt; the failure reproduced outside sandbox, so it
was not a demonstrated sandbox defect. Reusing that existing fixture fixes the
test without changing product code or adding a harness.

Independent working-diff review: no actionable findings; 3 new inert tests pass.
The reviewer mistakenly included the broader bounded execution suite, producing
92 passes and 16 blocked DB-fixture setup errors before database creation.
Do not report that suite green or infer a product regression from setup errors.
No provider calls or successful database effects occurred. Exact-head review
follows commit. Fake-engine success is not routed-provider enforcement evidence.

Composed-runtime qualification exposed one additional test isolation gap: the
retained known-character donor legitimately reads graph context after construction.
The allocation-only unit fixture now supplies that existing context port inertly;
no product or donor behavior changes. Preserve the initial composed v1 manifest
and failed synthetic test as evidence, then qualify an additive v2 composition.
