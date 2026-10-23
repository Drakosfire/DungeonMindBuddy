# STATBLOCK — durable manual revisions of saved mechanics

## ACTIVE serial implementation authority

PRIME activates slice A of adopted #1618 under the operator's revised active goal.
Base `05a6fe0c95d68e337ce589677012bdb0e32da08c`, existing buddy-context-loop
checkout, branch `codex/statblock-manual-revisions`. Fresh remote/open-PR census
found no overlapping implementation. One implementation PR; no new environment.
Architecture critique turn `01a165fa-9f37-7e62-a952-1760e30e92bd` is adopted.

DMS main/live `f95e92cb0fb50949260534b12c063ab1811eaf30` already provides
AppendRevisionRequestV1, POST statblocks/{id}/revisions, exact/list reads, linear
parent CAS and same-key replay/conflict. Buddy's generated models already contain
append/list DTOs; only its integration client lacks methods. DMS source/API remains
unchanged. Producer tests establish stale-parent/idempotency behavior. Buddy owns
this product integration and operation recovery; DMS owns immutable mechanics.

## Capability and authority

Use the existing shared definition editor to manually revise an exact saved
mechanics version, validate and save an immutable DMS successor, then reopen either
version. No AI call, combat adoption, tracker edits, scene links or World publication.

Preserve ThreatDraft.accepted_mechanics_ref, its original acceptance proof, World
associations and every fight. New saved revisions have separate **Buddy-validated
revision receipts**; ancestry alone never extends original acceptance authority.
The explicit validated Save authorizes one exact producer append. Later slice B
must separately authorize selecting this proven saved version for an encounter.

Use APP-owned versioned operation receipts in new mechanics_revision.operation;
these retain exact intent/base/request/result provenance, not a second mechanics
source of truth. Normal version reads resolve only the original acceptance proof
or a committed revision receipt, then use DMS exact get/integrity. No latest lookup,
name match, arbitrary producer revision enumeration or imported control-plane config.

Claim before dispatch, binding World/draft/statblock, original acceptance anchor,
exact parent locator/digest, immutable submitted input and canonical DMS request.
States: prepared, outcome_unknown, committed, refused. Mark unknown durably before
network entry. Only verified exact DMS result commits. Timeout, malformed success,
unknown errors or crash leave unknown; explicit recovery uses the same key/body.
Only producer-proven stale-parent/parent-mismatch/validation/idempotency refusal
may become refused; do not infer nonapplication from a generic409/422.

APP also records cancellation tombstones under the operation-key lock when an
explicit recovery finds no claim. This fences a still-running preflight: an absent
GET alone never proves nonapplication or unlocks edits. Recovery returns no
operation only after that atomic fence. Metadata inspection remains read-only.

APP serializes active operations per logical statblock, with immutable key/body
replay and no new-key Save while an operation is unresolved. DMS remains final
parent CAS. No network operation runs inside an APP transaction. Reopen/list uses
indexed paginated receipt metadata; reuse existing page bounds, add no arbitrary
character/token/history cap. Receipts and cancellation fences remain retained with
application state; there is no automatic TTL/purge. A prior version can be inspected or edited, but stale
parent rejection never becomes automatic rebase/fork. Preserve exact source asset
bindings and protected definition structure when appending.

Shared UI shows source and saved versions, validation, Save and understandable
outcome/recovery. Browser-writer/World/draft/base-qualified local recovery retains working copy
and exact operation ID/body; it is never accepted authority. Pending/unknown Save
freezes its submitted payload until resolved. Late responses cannot target another
World/draft/base. Reopening old versions never silently updates a fight.

## Exclusive expected writes

This handoff; predecessor HANDOFF-COMBAT-scene-encounter-revision.md settlement;
Docs/Roadmaps/ROADMAP-demo.md; existing integration
apps/live_control_server/integrations/dungeonmind_statblocks/client.py;
new apps/live_control_server/models/statblock_saved_revision.py and
services/statblock_saved_revision.py; existing routes/statblock_candidates.py;
new src/application_state/mechanics_revisions/{__init__,types,service}.py;
new migrations/versions/20261022_0049_mechanics_revision_operations.py;
UI api/liveApi.ts, new statblocks/revision/SavedMechanicsRevisionEditor.tsx and
its test, optional colocated typed API/recovery helper and tests;
surface/modules/StatblockWorkbenchModule.tsx and its affected test;
statblocks/editor/StatblockDefinitionEditor.tsx if recovery disclosure must reflect
controlled persistence; focused new tests/test_statblock_saved_revisions.py,
tests/application_state/test_mechanics_revisions_postgres.py and existing
statblock integration client/HTTP route tests as named before changes.
Lease amendment before edit: `apps/live-control-ui/src/statblocks/revision/StatblockRevisePanels.tsx`
removes only the unused, now-obsolete append-unavailable notice export.
No old migration, generated DTO, lockfile, DMS source or Combat/scene writer edits.
Amend before expanding paths.

## Verification and delivery

Synthetic client/APP/service/HTTP tests: exact parent/content/digest; wrong owner,
statblock or ruleset; changed same-key payload; two writers/stale parent; timeout
or crash after remote commit with exact replay returning one revision; corrupted
result never falsely committed; unknown blocks new-key dispatch; immutable original
accepted proof/associations/fights. UI validates before Save, exposes original/new
versions, retains edits on conflict/reload and exact pending recovery, rejects
late/foreign results, and never implies encounter adoption.

Exact cumulative Bugbot review, PRIME merge and guarded8000/5202 delivery. APP0049
is additive; retain native0017/Core617635c/DMSf95e. Preserve current APP/native rows,
sources, drafts, mechanics and frozen components. Ordinary UI manual edit→validate
→save→old/new reopen→reload/API restart witnesses the slice with zero AI calls.
Conks/Sheep full connected workflow, adoption, scene links and all other roadmap
acceptance remain open. No private source prose enters Git/PR fixtures.
