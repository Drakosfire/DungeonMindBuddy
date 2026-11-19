# BUDDY — preflight admission of reused saved-statblock PDF support

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane.
Authority: operator finish-vNext implementation/review/merge authorization.
Base063c91de8441cad82d0db906c3b017e9c942ebf4 (accepted4053).
Branch codex/v9-admitted-pdf-reuse; serial repair→merge→resume4041 qualification.
Frozen accepted base avoids chasing unrelated main changes. No unmerged parent.

## Outcome and exclusive three-path lease

Only this handoff, apps/live_control_server/services/plan_jev_driver.py and
 tests/test_surface_native_build_ordinary.py. A historical R0 PDF can be admitted
by an explicit first-turn selection while source authority is already R1. Later
turns drop that selection. Existing reuse compares unchanged authorities/epochs
and association, but copies R0 support, which final validation correctly rejects.
No revision change between turns is necessary.

After existing validate_prior_read, preflight a new temporary execution containing
the candidate event against the CURRENT receipt using existing
validate_context_binding. Do not mutate the live execution. Catch only existing
ValueError reuse rejection and proceed to ordinary fresh acquisition. Preserve
final validation/freshness checks and the original retained PDF pin; no relabel,
authority relaxation or new public contract. The validator reconstructs/joins
pure in-memory models; it grants no IO authority. Verify candidate shape equals
what append validates. An extra bounded validation walk occurs on attempted
reuse; no latency improvement claim is made for this repair.

Ownership checkpoint: open3307 actually owns native_execution.py. Do not edit or
factor that file. Readonly independent design review approves this alternate
caller-preflight boundary, contingent on purity/shape proof. Other checked4050,
4017,3867,3729,3290,1764 current own diffs do not overlap these paths; recheck
relevant exact path ownership before implementation if state changes.4053 merged;
its150passed/2failed owning run preserves the two real continuation regressions.

## Validation and full-goal boundary

Keep both existing consecutive HTTP regressions and assert one fresh R1 acquisition
after the initially selected R0, then same-pin reuse on later turns. Keep explicit
historical first-turn admission, original evidence/citations and final guard.
Invalid fresh evidence identities must still fail closed. Run prior-read negative
identity/epoch/conversation/association tests, owning cohorts, scoped lint,
independent exact-head review, repo-owned exact-SHA hosted frontend verifier and
canonical validation, and normal automatic checks. No frozen baseline rerun.
Other auth/profile/registry fixture failures remain separate V9 blockers. This
repair is not V9 acceptance, live activation, V10 retirement or V11 baseline.

## Resources

Reuse existing taskroot /home/drakosfire/Projects/.codex/v7-elderwyld-scope,
Projects UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and executor write access verified.
Use scratch/v9-buddy and existing caches/venv without sync; uniquely owned test DB
fixtures on32903 only. No owned canary or prior worker uses checkout at start.
No live DB/serving5202/otherlane8000/provider change. Retain refs/evidence for
qualification, owner Elderwyld lane; cleanup followup after explicit scope and
active process/mount/dirty/unique-data checks. No manual deletion/reclaimed bytes.

Targeted discovery: the first preflight cohort passed12 cases, including all four
invalid fresh identities, but both consecutive cases reached a later fake-provider
400: the fixture compared the callable initial requested_work rather than its
current resolved value when asserting reasoning effort. Move the existing current
work computation before that exact assertion; retain medium-for-draft/low-for-
discussion checks. This is a necessary fixture correction in the already leased
test file, with no provider/runtime policy change. Preserve the failed receipt.
