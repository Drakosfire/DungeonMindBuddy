---
pr_body_template: |
  ## Handoff pointer
  - Workstream: STATBLOCK / wire-and-digest compatibility
  - Direction: STEWARD → CODE → PRIME
  - Handoff: Docs/Plans/HANDOFF-STATBLOCK-explains-wire-compatibility-v1.md
  - PR topology: parallel-independent from DEMO #785; code/tests only, no shared runtime
  ## Review contract
  Buddy omits unset nested optional fields in create requests while preserving explicit empty/populated lists, and its revision digest logic distinguishes an absent `explains` field from an explicit empty list.

# HANDOFF — STATBLOCK: preserve optional explains wire and digest semantics

**Created:** 2026-09-28
**Status:** ACTIVE — bounded Buddy implementation authorized; merge gated on owner-contract reconciliation
**Handoff locator:** `codex/handoff-statblock-explains-wire-compatibility` at the handoff commit
**Workstream / owner:** STATBLOCK / DungeonMindBuddy consumer integration
**Direction:** STEWARD → CODE → PRIME
**Design authority base:** Buddy main `132cb80bea50ef2814074a52832ab763286a1900`
**Activation:** PRIME re-anchored Buddy main and open PRs; exact source symptom and disjoint paths confirmed.
**PR topology:** `parallel-independent` from DEMO #785 only: no leased-path overlap; this lane is source/tests only and uses no API, UI, DB, provider or shared runtime.
**PR authorization:** The worker may open/update exactly this assigned Buddy PR without another prompt after fresh pre-dispatch re-anchor; no follow-on PR is authorized.
**Title:** `STATBLOCK: preserve optional explains wire and digest semantics`

## §1 Mission and invariant

Correct the Buddy-owned statblock client serialization and canonical digest behavior for the existing optional, non-null `RuleElement.explains` array.

**Invariant:** an unset `explains` value is omitted recursively from the create wire body, matching preview validation; an explicitly empty array remains `[]`; populated edges remain present. Canonicalization preserves the distinction between an absent `explains` field and explicit `explains: []`, so old sealed revisions retain their exact digest while explicitly stored empty lists remain stable.

Source evidence: current preview validation serializes recursively with `exclude_none=True`; the create builder uses `exclude_none=False` and only strips top-level None values. The acceptance journal read showed nested `explains: null` on all three rule elements and `extra_forbidden` ×3. The prior local-only validation route is pure/in-memory and is not part of this implementation proof.

## §2 Concurrent lanes and contract dependencies

- DEMO #785, exact current head `07ec031ab5b62b8dbcd34f51ed4b6eaf0fa25262`, retains its own ACTIVE serial handoff and sole DEMO implementation PR status. This is a separate STATBLOCK consumer-compatibility workstream, not a DEMO successor.
- Buddy paths below do not overlap #785's §4 lease. This handoff authorizes no update to #785 or its handoff.
- SERVER currently has open #28 (stacked on feature branch `feat/statblocks-v1-prompt-and-schema-guidance`) and #29 (main-based). Neither has an accepted review. #29 currently has failing Red-team checks; #28 has no reported checks. The SERVER owner must reconcile them and settle a strict optional non-null field plus presence-preserving canonical bytes. PRIME controls their review/merge.
- Buddy may implement/test its side against the currently checked-in generated contract. Do not deploy or run a product acceptance until SERVER's accepted contract and canonical digest behavior are compatible. Any need to accept JSON null, alter public contract/version policy, reseal existing revisions, or change graph-pinned digests is a stop/rebrief condition.
- Keep the existing cloud candidate and acceptance journal untouched. No Firestore, PostgreSQL, API, browser, provider/model, or credential operations in this lane.

## §3 Write lease

Modify:
- `apps/live_control_server/integrations/dungeonmind_statblocks/client.py` — recursively omit unset None from create wire serialization without dropping empty or populated values.
- `apps/live_control_server/integrations/dungeonmind_statblocks/definition_digest.py` — preserve absence versus explicit empty `explains`; do not change other established server-default list behavior.
- `tests/test_dungeonmind_statblocks_client.py` — request serialization regression: absent/null omitted at nested depth, explicit empty and populated arrays preserved, preview/create shape agreement.

Add:
- `tests/test_dungeonmind_statblocks_definition_digest.py` — regression vectors for omitted, explicit null (if accepted by the generated input DTO), explicit empty and populated `explains`, plus a control proving other server-default empty lists retain current semantics.

Only these four paths are in the lease. No lockfile, generated contract, UI, handoff beyond completion facts, roadmap, schema, Server repo, persistence, migration, or deployment changes.

## §4 Verification and merge gates

Use source-level/unit tests only. Prove the exact create body and digest output from the owning Buddy functions; inspect exact cumulative base→head diff and run scoped lint/tests. Tests must not call API 8817/7861, external services, Firestore, PostgreSQL, or a model.

Before merge, PRIME must independently confirm:
1. SERVER's accepted contract permits omission and a non-null list, and defines how absence versus explicit [] preserves historical digest bytes.
2. The Buddy digest tests match that exact rule, including old absent-field and explicit-empty vectors.
3. The cumulative PR contains only the four leased paths and tests pass.
4. No cloud/database or live product operation was used.

After merge, record this completed source-only capability in this handoff. A later authorized demo rehearsal is a different workstream and requires exact-target authorization and its own witness.

## §5 Stop conditions

Stop and return to PRIME for any change to server-owned contract, generated schemas, field nullability/versioning, historical revision migration/resealing, graph bindings, additional Buddy paths, failed ownership-boundary tests, or any need for runtime/database/product calls. This handoff grants no merge authority; PRIME owns merge control.
