# BUDDY — explicit local source-inspection fixture

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane.
Authority: operator finish-vNext implementation/review/merge authorization and
explicit lane ownership without a PRIME coordination prerequisite.
Base475f65d92411e380c7881a2b7a394fa38e7e65b7; branch
codex/v9-source-inspection-fixture. Serial: this test-only repair → separate
historical comparison-fixture repair → resume qualification4041.

## Outcome and two-path lease

Only this handoff and tests/test_native_source_inspection.py. Add explicit
DMB_DEPLOYMENT_ENVIRONMENT=local and DMB_AUTH_MODE=local_operator to its existing
inspection fixture. It already supplies Graph bearer credentials and loopback.
Current auth contract225pass/36fail all local source-inspection cases; default
production fail-closed behavior must not be changed or overridden with a fake.
Keep exact anonymous401/player denial, source-only sentinels, body/span hashes,
withdrawal, foreign selectors, metadata privacy and revision-stability assertions.
No runtime, auth implementation, selector, schema or provider change.

## Existing work and boundary

The exact two-line fixture hunk already exists in integration draft3824. Adopt
that identical local-test setup independently; do not absorb its102-path hosted
integration or change any runtime. Its other source-test dependency migration is
already in current main. The older source-browser lease is explicitly closed in
its handoff; source passages delivered in2088/b7b0150c4 and attachment is marked
MERGED_AND_DELIVERED. Their stale ACTIVE headings do not restart those delivered
features. Current open source/hosted candidates were inspected; this bounded hunk
creates no divergent behavior. Preserve3824's broader ownership and provenance.

## Validation and full-goal continuity

Run the owning module, then complete auth-app contract at frozen published SHA;
independent exact-head review, clean scoped lint, unmodified repo-owned hosted
frontend verifier/canonical validation/shared lock and normal checks before merge.
No frozen retrieval baseline rerun. Historical0139 test remains separate; never
upgrade it to later schema merely to run current content code.

CurrentV9 browser/forward-write rollback proof passed on owned restore at0274;
latest ownedhead48384a4b has602 revisions/sourceepoch195. No old dump restored over
it. All owned canaries/workers stopped before this branch. Live sources unchanged.
V9 acceptance, actual live activation, V10 retirement and V11 serving baseline
remain required. Do not claim this fixture repair completes them.

Storage/resources: existing taskroot under Projects UUID
48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and verified executor access; scratch/v9-buddy,
existing venv/cache without sync, uniquely owned test databases on32903 only.
No new worktree/container, live DB/serving5202/otherlane8000 changes. Retain refs,
logs/receipts owner Elderwyld lane for qualification; cleanup followup after scope
approval and active process/mount/dirty/unique-data checks. No manual deletion.
