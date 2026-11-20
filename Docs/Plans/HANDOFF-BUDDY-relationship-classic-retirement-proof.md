# Relationship review — prove classic preparation retirement

Status: ACTIVE. Owner MIND under the operator's full-lane authority. Two-path
stacked test-only slice. Parent PR4222 branch
`codex/v10-native-worldkeeper-adoption`, base
`62b9f40752a9ae6dd1a89251756819be4b66a0d0`; checkout is the existing clean task
Buddy lane on `codex/v10-relationship-classic-retirement-proof`. Pin this brief
before the test edit. Merge order: Core246 -> Buddy4222 -> this PR; retarget only
after inspecting the actual parent merge. Do not merge against an unaccepted parent.

Outcome: preserve the current document-relationship review request and its exact
source/meaning assertions while proving the old classic prepare continuation is
retired with zero publication/source mutation. Current BuildRelationshipReview
uses native-prepare/native-confirm; those implementation and existing proof cases
remain unchanged. No product endpoint is retired by this test-only assignment.

Exact write lease:
1. This handoff.
2. `tests/test_graph_document_relationship.py`, only
   `test_request_preview_and_explicit_confirmation_reuse_existing_writer`, renamed
   to describe review preservation and classic preparation refusal.

Open3824 touches this file. MIND explicitly allocates only the named function
under full operator lane authority; no other auth/fixture/native test changes.
Do not change runtime, source registry, schema, dependencies, CI or other tests.
The old successful classic confirm/replay assertions are intentionally superseded
by accepted4215 retirement and the existing actual native writer/recovery cases;
do not resurrect a fresh classic HTTP publisher just to pass the old test.

Evidence: parent4222 preservation375PASS1FAIL of376. The one failure is410
classic_manual_prepare_retired vs stale200. Identical parent apps/src/tests blobs
with untouched oldWKef9/Core90a5 reproduce that failure. Hubble accepted the bounded
three-path dependency adoption and requires this separate repair before cutover.
Do not relabel the parent cohort green or erase the failed diagnostic.

Discovery boundary: `tests/test_graph_document_source.py` also contains historical
fresh-classic HTTP expectations and supplies the unchanged fixture. That broader
cohort has not been qualified here; its callers require explicit historical/test
retirement disposition before full writer retirement. Do not absorb it or claim
full repository tests green. No fixture/helper changes in this two-path slice.

Run the entire24-case owning relationship file using the accepted WK348/Core90a5
installed environment; preserve native cases. Inspect exact function-only diff and
cumulative two-path scope, obtain independent review, and perform required final
exact-source qualification after integrating the actual accepted parent. The
repo-owned hosted/build/canonical verifier remains required at final SHA; do not
reuse parent evidence as if it executed the child. Working diagnostics are not
that final acceptance. No retrieval baseline rerun or new full-discovered run.

Keep full V10/current-public retirement, compatible deployment/rollback and V11
open. MIND retains task checkouts/env/logs for the active full goal; no newworktree,
manual deletion or reclaimed bytes. Approved-scoped cleanup follow-up requires
process/mount, dirty/unique-data and unique-commit checks.
