# INGEST: preserve World scope in semantic correction children

Status: COMPLETE — PR #1399 merged as
803c1ece8869f9a3253dff0f0c646bbcf645fc75 after one independent ARCHITECTURE
PASS on exact head 4b308b393a49daad2844f478ba2094dbe917c910. PRIME reports the
service deployed at SHA 1bc22348877cb3a92187c439042614b28c2222c99e2f6a6ff113ad55ec5424b3
(API process 493137). This is a truthful handoff settlement; this lane did not
independently probe the deployment. No implementation lease remains.
Historical base: origin/main@0b5b473babe1f512196d009de61830d6aca964c0 (parent
of initial ACTIVE handoff commit a55f7b4d8d879ef729bd8ca5e1c856a4b98fa7f6).
Historical branch: codex/ingest-semantic-world-scope.
Owner: DOGFOOD; reused checkout 996b and established dependencies.
Topology: serial, one implementation PR; no stacked dependency. ROOT's
separate UI evidence PR #1397 was already merged into the historical base.

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

## Completed write set (historical)

- This handoff
- apps/live_control_server/services/recap_semantic_candidate_correction.py
- tests/test_recap_semantic_candidate_correction.py

No route, schema, registry, literal-correction helper, UI, dependency, telemetry
or retained data writes were included. The three-path write lease ended when
PR #1399 merged. Any source-component binding repair belongs to a separately
designed successor; this handoff grants no paths for that work.

## Settlement record

The implementation copied and validated frozen World scope, retained it in the
held child, and bound replay to the parent's exact scope. Its focused service
suite passed 155 tests; one unrelated app-construction test was excluded because
the available shared environment's `generationengine` package lacked
`ImageOptions`. Service Ruff, Python compilation and `git diff --check` passed.
ARCH independently passed the exact merged head and a canonical-source control;
its independent service suite passed 156 tests.

PRIME reports that retained ingestion state, the new Edge candidate, the ledger,
and six attempts were unchanged, with no live correction run. No historical run
was backfilled, rewritten or grandfathered, and no publication occurred.

This completion is limited to World-scope propagation. ARCH separately found a
production source-component URI binding failure when a semantic child relocates
its candidate while retaining the parent's run-local source snapshot. That
behavior is not fixed by PR #1399, and this handoff makes no claim that every
production semantic child can now be created. The exact production reproduction
remains in private ARCH evidence. Addressing it requires a separate BLOCKED
design and later ROOT activation; this completed handoff grants no authority or
write paths for that successor.
