# INGEST: preserve World scope in semantic correction children

Status: BLOCKED — design and critique are pinned, but implementation dispatch
was rejected by automatic approval review for missing destination authorization.
No implementation write lease is active until the user authorizes coordination
and PRIME dispatches this contract. The underlying defect is reproduced.
Base: origin/main@1b6258e304e96cd87b485785422310e0b4801120.
Branch: codex/ingest-semantic-world-scope.
Intended owner: DOGFOOD; reuse996b checkout and established dependencies. No new worktree.
Topology: parallel-independent of ROOT UI evidence PR1397; no overlapping paths,
no unmerged dependency. One implementation PR for this capability only.

## Invariant and bounded scope

Semantic correction of an exact World-bound recap must retain its validated
parent World scope. ROOT reproduced actual correct_recap_candidate accepting a
bound in-memory parent but creating a held child whose missing scope is rejected
by validate_recap_source_run_world_binding. Existing literal correction already
copies frozen scope; semantic correction constructs fresh lineage without it.

Copy only the exact frozen context or supported explicit legacy World/campaign
fields. Validate source/run agreement before writing a child candidate or run.
Use existing source authority and validator, never infer from campaign, current
selection, current head or a default. Malformed/incomplete/contradictory context
must fail before writes. Do not copy semantic acceptance or unrelated mutable
parent lineage. Child remains held. Candidate semantics and parent stay unchanged.
Reuse established scope helper where correct; if shared-helper changes are needed,
return for an explicit lease expansion instead of editing a new path.

Replay must bind child scope to parent scope, including rejection of stripped or
forged scope, while preserving old byte/component/digest checks. Identical retry
must reuse only a fully matching child, including full frozen scope; an existing
unbound conflicting child is not silently repaired. Define and test this conflict
explicitly; no weakening deterministic child identity or automatic migration.

## Historical limit

S26 root c856413b and children d72d1faf/15d1c774 already lack World scope while
their canonical source has native World eldyrwild. This forward fix MUST NOT
backfill, rewrite, infer, grandfather or bind that ancestry. It is not its repair.
Do not claim historical projection is fixed until a separately authorized safe
historical disposition exists. No stored candidate is edited or executed here.
Unbound legacy fixtures may remain supported only when their canonical source is
also unbound; source-bound + unbound run must fail, not acquire scope by inference.

## Critique / required failure cases

A helper that only copies a native_world_id string does not prove the complete
frozen context or its canonical source binding. Validate before candidate writes,
not only at registry create after the file is already written. Preserve distinct
managed/native World IDs. Never copy a changed current binding/head as history.
Prove exact context/campaign/source mismatch and malformed context rejection;
prove scope-tampered child is rejected by replay/decision boundary as applicable.
Do not reclassify legacy semantic data or broaden publication authority.

## Exclusive write set

- This handoff
- apps/live_control_server/services/recap_semantic_candidate_correction.py
- tests/test_recap_semantic_candidate_correction.py

No route, schema, registry, literal-correction helper, UI, dependency, telemetry
or retained data writes. Ask PRIME for a justified expansion if boundary proof
requires another owning test; do not silently widen scope.

## Verification and delivery

Focused service tests use actual correction and replay with source-binding checks:
valid frozen/legacy scope retained; exact retry; parent unchanged; held child;
forged/stripped existing child conflict; malformed/missing/source-mismatched scope
rejected before writes; correctly unbound legacy behavior explicit. Prove real
APP-STATE registration/historical read boundary on a disposable fixture where
required; no tests against retained54330/54331. Reuse the established environment.
No provider calls or new Process run. No S26 correction POST, decision, prepare,
publication or data migration. Review exact cumulative diff, commit/push/open PR,
then independent review before PRIME merge and separately verified API rollout.
No root export, source clone or temporary-path evidence. Keep private semantic
review packet work separate from implementation; neither counts as acceptance.
