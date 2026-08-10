---
pr_body_template: |
  ## Handoff pointer
  - Conversation: Eldyrwild Contribution Integrity Heal
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-eldyrwild-contribution-integrity-heal.md
  - PR / branch: build/eldyrwild-contribution-integrity-heal
  - Docs authority sync: this handoff must land on main before BUILD dispatch
  - Merge-ready ≠ complete: clone heal + Kernel guard make the package merge-ready;
    slice DONE requires post-merge canonical live heal exit proof

  ## Verification pointer
  - Base/head: record exact implementation base and head in review handback
  - Changed paths: only §4 allowlist plus the single conditional recovery artifact
  - Verification: execute every applicable §7 command/scenario and report exact results
  - Rebuild: pinned and unpinned rebuild after clone heal are NOT WAIVABLE
  - Forbidden: hash-patching, rewriting immutable revisions, inventing D*, relaxing digest checks

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation; this docs sync is a
  prerequisite before BUILD and the implementation PR must not invent the
  contract.
---

# HANDOFF — Eldyrwild revision-bound contribution integrity heal

**Created:** 2026-08-09.  
**Status:** READY FOR BUILD — this handoff is the dispatchable contract for `eldyrwild-contribution-integrity-heal`. It lands on `main` with this docs sync; BUILD may dispatch only against an `origin/main` that descends from PR #538 merge `5dae4183…` and contains this file. Tracker must still show heal READY and Lysandra BLOCKED on it.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-contribution-integrity-heal.md`  
**Conversation name:** `Eldyrwild Contribution Integrity Heal`  
**Flow / agent:** `BUILD`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** DungeonBuddy design steward — 2026-08-09  
**Code agent:** fresh BUILD code agent using the same conversation name  
**PR title:** `BUILD: heal Eldyrwild contribution replay integrity`  
**Branch:** `build/eldyrwild-contribution-integrity-heal`

> **Dispatch gate:** PR #538 merged to `main` as `5dae41830220c50b162fe76c349101c4955aff0c`. Before the first implementation change, record the exact `origin/main` SHA and prove it is a descendant of `5dae4183…`; prove this handoff exists on that base; re-read `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; and prove `eldyrwild-contribution-integrity-heal` remains READY while `eldyrwild-lysandra-threat-direction-correction` remains blocked on it.
>
> This slice is **forensic first, repair second**. Do not edit a digest, relax replay verification, change an immutable revision, or manufacture a plausible contribution payload. The only acceptable recovered payload is one that is independently grounded and whose lifecycle-neutral source digest exactly equals the immutable revision-bound authority already carried by Eldyrwild.
>
> The current source strongly suggests a concrete corruption mechanism: `GraphContribution` identity does not include `produced_at`, the source-authority digest does include it, `supersede_graph_contribution` currently writes a pending same-ID contribution to the mutable ledger before `stamp_contribution_source_digest` rejects a different already-bound digest, and `write_contribution_record` unconditionally replaces the ledger file. That causal chain must be reproduced before the generic guard is changed. If the observed live corruption is not explained by that sequence, stop and return to DESIGN rather than forcing this handoff onto a different defect.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Revision-bound source authority** | The immutable contribution source digest and lifecycle status recorded in a World Graph revision's `contribution_source_payload_sha256` / `contribution_replay_manifest`. For an already-bound contribution ID, this outranks mutable ledger bytes. |
| **Mutable contribution ledger** | The current on-disk `GraphContribution` record and contribution index under the world store. These are durable operational records, but they may be rewritten by lifecycle operations and therefore are not allowed to redefine an already-bound immutable source payload. |
| **Lifecycle-neutral source digest** | `compute_contribution_source_payload_sha256(...)`. It excludes `status` and diagnostics, but includes source payload fields such as `produced_at`; therefore two contributions may have the same `contribution_id` yet different source-authority digests. |
| **D** | Exact corrupted contribution ID `contribution:d3d244474789879c`. |
| **D\*** | The exact recovered source payload for D whose lifecycle-neutral digest equals immutable revision-bound authority. D\* is not accepted because it “looks right”; it is accepted only when provenance and the immutable digest prove it. |
| **Parent contribution A** | `contribution:2807888820d76c78`, the Session-10 source contribution superseded by D during the July Graph V1 projection repair. |
| **Rejected assertion X** | `assertion:134135a4f3a2487b`, the unsupported `pc:baergrom --serves--> pc:caelynn` assertion removed by D. |
| **Historical repair chain** | `rev:5017a20164555f11d4508f67661058f1` → `rev:4d0636a05841efd6958014b655ccf40e` → `rev:bbf29b974f0162dc8b8fbe080d93ae00` → replay-published `rev:a3262c8102f61f490e11444d9fc28068`. |
| **Expected digest E** | The source payload SHA256 bound to D by immutable revision authority. Its value is discovered from the actual revisions at implementation time and must agree across the historical/current authority checks below. Do not guess or hard-code it from a mutable ledger. |
| **Actual digest A_now** | The source digest recomputed from the current mutable ledger record for D before repair. The current known failure is `A_now != E`. |
| **Source-bound collision retry** | A retry/recreation that produces the same contribution ID as an already-bound contribution but a different source payload digest, for example because `produced_at` differs. |
| **Heal** | Replace only the corrupt mutable ledger/index representation of D with D\* / the revision-bound lifecycle state; do not publish a graph revision or change graph semantics. |
| **Merge-ready proof** | The implementation + recovery artifact are proved on a clone of the real Eldyrwild store. |
| **Live exit proof** | After merge, an operator runs the fixed heal against canonical Eldyrwild with explicit live opt-in and exact expected head; the head revision stays unchanged and pinned/unpinned rebuild become equivalent. Only then is this slice DONE. |

## Agent flow and nano-commit contract

Use `BUILD`. Keep the work in nano commits. Recommended story:

1. **Forensic reproduction:** capture the exact current D mismatch on a clone; prove immutable E vs ledger `A_now`; reproduce the same-ID/different-source overwrite sequence in a focused test.
2. **Kernel prevention:** make already-bound source authority win before any ledger/index write on supersede retry; prove rejected retries leave head, ledger bytes, and index byte/semantic-equivalent.
3. **Authority recovery:** recover D\* from independently grounded historical material; prove contribution ID, transformation from parent A, and exact source digest E. If D\* cannot be proven, stop.
4. **Fixed one-off heal:** add a headless maintenance CLI for exactly D; inspect is read-only; apply is fixed-target, expected-head fenced, live-root fenced, and does not publish a World Graph revision.
5. **Real-clone replay proof:** heal a clone of current Eldyrwild and prove current head bytes/semantics unchanged while pinned and unpinned contribution rebuild become equivalent.
6. **Post-merge live exit:** not part of the implementation diff. Apply the merged fixed tool to canonical Eldyrwild, capture before/after evidence, then doc-sync tracker/status so heal becomes DONE and Lysandra becomes READY.

Do not broaden this into a generic contribution repair registry, arbitrary ledger editor, new server API, repair UI, or world migration framework.

## §1 Mission and merge-ready invariant

**Mission:** An operator can restore Eldyrwild contribution D to its immutable revision-bound source authority so that contribution replay is trustworthy again and the same corruption path cannot overwrite an already-bound contribution on retry.

**Merge-ready invariant:** For any contribution ID already source-bound in the current revision, a caller-supplied payload with a different lifecycle-neutral source digest is rejected before any contribution-ledger or index write; for D specifically, one independently proven payload D\* with digest exactly E can replace only D's corrupted mutable ledger/index state on an exact expected head, leaving all immutable World Graph revision bytes and graph semantics unchanged, after which pinned and unpinned rebuild are equivalent to that same head; if D\* or E cannot be uniquely proven, no heal mutation is permitted.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Prevention and repair share one authority rule: immutable revision-bound source authority must dominate mutable ledger state. The generic retry guard makes the one-time repair durable rather than immediately re-corruptible. |
| What adversarial sequence is most likely to falsify it? | D is already bound → caller recreates same deterministic ID with a new `produced_at` → pending record overwrites ledger → digest stamp detects mismatch → failure path writes the differing record again / marks index failed → graph head never moved but replay later fails. |
| Would §7 detect that failure? | **Yes.** The regression fingerprints ledger bytes/index/head before retry and requires exact equality afterward; the real-clone heal then requires both pinned and unpinned rebuild equivalence without a revision change. |
| Which owning boundary is easiest to under-test? | The ordering boundary between immutable digest validation and `write_contribution_record(...)`. A test that checks only `published=False` misses ledger corruption. |
| What fact would force this slice to stop or split? | Historical revisions disagree on E; D\* cannot be uniquely reconstructed; the live mismatch is not explained by the source-bound collision path; more than D is corrupted; repairing safely requires changing immutable revision data or digest semantics; or a new public generic maintenance API is required. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/STATUS-world-graph-continuity-spine.md`; PR #538 merge `5dae4183…` |
| Repository rules | Revision-bound graph state is immutable; graph/source authority must fail closed on mismatch; no hash-patching; apps do not directly own contribution ledger; no server route/UI for this maintenance slice |
| Design anchor | `5dae41830220c50b162fe76c349101c4955aff0c` — PR #538 merge |
| Implementation base | Exact `origin/main` at BUILD dispatch; must descend from `5dae4183…` and contain this handoff |
| Predecessor contracts | PR #534 source-digest/replay integrity behavior; current `compute_contribution_source_payload_sha256`; current `supersede_graph_contribution`; current pinned rebuild |
| Exact input consumed | Current Eldyrwild world root; exact D; immutable revisions/current head carrying D's replay authority; parent A; July repair report; one fixed recovered D\* only after proof |
| Named successor | `eldyrwild-lysandra-threat-direction-correction` |
| What remains false | Lysandra relationship is still uncorrected; no formal descendant conformance re-anchor; no general contribution recovery framework |
| Explicit non-goals | Changing historical revision JSON; changing E; weakening digest comparison; excluding `produced_at` from digest to make this pass; changing D's semantic correction; re-running the July repair as a new contribution; repairing unrelated ledger records; server API/UI; Graph Review changes; DungeonMind changes |

Read authoritative inputs in order:

1. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
2. `Docs/Design/STATUS-world-graph-continuity-spine.md`
3. this handoff
4. `Docs/Reports/REPORT-main-graph-v1-projection-repair.md`
5. `src/graph_memory/kernel/contributions.py`
6. `src/graph_memory/kernel/contribution_merge.py`
7. `src/graph_memory/world_supergraph/contribution_store.py`
8. `src/graph_memory/kernel/contribution_rebuild.py`
9. `tests/test_graph_kernel_contribution_merge.py`
10. `tests/test_graph_kernel_contribution_rebuild.py`
11. `tests/test_graph_kernel_contribution_source_authority.py`
12. `Docs/Plans/HANDOFF-eldyrwild-lysandra-threat-direction-correction.md` — consumer contract only; do not implement it here

### Known historical facts that must be preserved

The July repair report records:

```text
world:
  eldyrwild

parent contribution A:
  contribution:2807888820d76c78

bad assertion X removed from A:
  assertion:134135a4f3a2487b

repair contribution D:
  contribution:d3d244474789879c

A source artifact:
  artifact:recap:longmont-c1:session-10

repair construction:
  same source artifact/revision/profile/campaign scope as A
  authored_by = operator:graph-v1-projection-repair
  supersedes_contribution_id = contribution:2807888820d76c78
  selection_digest = reject:assertion:134135a4f3a2487b
  accepted = A.accepted - X
  rejected = A.rejected + X (rejected)

historical revisions:
  pre-repair:
    rev:5017a20164555f11d4508f67661058f1
  after D supersedes A:
    rev:4d0636a05841efd6958014b655ccf40e
  after second independent repair:
    rev:bbf29b974f0162dc8b8fbe080d93ae00
  replay-published authoritative repair head:
    rev:a3262c8102f61f490e11444d9fc28068
```

The report also records that recreating the same correction yielded the same contribution ID D while a retry was rejected because that ID's source digest was already bound with a different value. That historical observation is consistent with the current code shape and must be reproduced, not merely cited.

### Current code fact that motivates the prevention guard

At the design anchor:

- contribution ID intentionally does not include `produced_at`;
- the lifecycle-neutral source digest excludes only status and diagnostics, so `produced_at` participates in the source digest;
- `supersede_graph_contribution` persists `pending_new` before source-digest stamping;
- `write_contribution_record` atomically replaces the record at that contribution ID without an authority check;
- therefore same-ID/different-source retries can overwrite the mutable ledger before immutable revision authority rejects the graph operation.

This is the expected root cause. The implementation must prove the sequence against current code. If a different mechanism produced the live D mismatch, stop.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---|---|
| Supersede, genuinely new contribution ID | Pending contribution is persisted before graph mutation; normal publish/recovery semantics | Existing behavior preserved | Yes | Kernel merge |
| Supersede retry, same ID + same source digest | May traverse existing supersede path | Idempotent/no-op or existing supported recovery behavior; must not rewrite authoritative ledger bytes merely because diagnostics/lifecycle metadata on caller differ | Yes | Kernel merge |
| Supersede retry, same ID + different source digest | Can write differing pending/failed record before digest rejection | Reject before any ledger/index mutation; head/ledger/index unchanged | Yes | Kernel merge |
| Already-bound ID but ledger missing | Existing recovery protections vary by path | Integrity failure; never synthesize authoritative source payload from caller input | Yes | Kernel merge |
| Already-bound ID but ledger digest differs from revision E | Pinned rebuild fails closed | Integrity failure on normal mutation paths; only fixed D heal CLI may repair after D\* proof | Yes | Kernel + one-off CLI |
| Heal status on clone/canonical root | No dedicated tool | Read-only forensic report: head, E, `A_now`, ledger raw SHA, manifest status, index status, D\* digest/provenance eligibility | Yes | one-off CLI |
| Heal apply on temp clone | No dedicated tool | Exact-head + exact D\* repair; no graph revision; rebuild equivalent | Yes | one-off CLI + internal ledger store |
| Heal apply on canonical root without opt-in | No dedicated tool | Fail closed; no mutable write | Yes | one-off CLI |
| Heal apply on canonical root with stale expected head | No dedicated tool | Fail closed before ledger/index write | Yes | one-off CLI |
| Heal exact retry after success | n/a | `already_healed`; no file churn; head unchanged | Yes | one-off CLI |
| Pinned rebuild after heal | Fails on D source digest mismatch | Equivalent to exact unchanged head | Yes | Kernel rebuild |
| Unpinned rebuild after heal | May also be affected by mutable index/ledger drift | Equivalent to exact unchanged head; proves index lifecycle is coherent with head manifest | Yes | Kernel rebuild |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Bound D → recreate same ID with different `produced_at` → supersede retry | Reject before first ledger write; raw D file, index, and head remain exact-equal | focused Kernel regression |
| Heal status H → unrelated writer advances head R → heal apply expected H | No ledger/index write; R remains head | stale-head CLI test |
| Candidate D\* ID is correct but source digest != E | `ineligible` / `integrity_failure`; no write | artifact/CLI test |
| Historical `rev:4d0636…` and current head disagree on D's bound digest | Stop; no repair authority | historical authority test |
| Ledger write succeeds but index update/verification fails | Repair operation restores pre-heal ledger/index snapshot or reports a retryable partial state with no claim of success; never publish a graph revision | failure-injection test |
| Heal succeeds → exact retry | no-op; raw recovered ledger bytes/index/head remain stable | retry test |
| Heal succeeds → pinned + unpinned rebuild | both equivalent to same unchanged head | real-clone replay proof |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/graph_memory/kernel/contribution_merge.py` | Reject already-bound same-ID/different-source retries before ledger/index writes; preserve existing success/recovery behavior |
| Modify | `tests/test_graph_kernel_contribution_merge.py` | Reproduce and permanently guard the ledger-overwrite corruption sequence |
| Create | `scripts/heal_eldyrwild_contribution_integrity.py` | Fixed-target forensic status / apply maintenance CLI for D only |
| Create | `tests/test_eldyrwild_contribution_integrity_heal.py` | Exact D authority, stale-head/live-fence, clone heal, idempotency, and rebuild proofs |
| Create, conditional | `graph_data/maintenance/eldyrwild/recovered-contribution-d3d244474789879c.json` | One exact existing-schema `GraphContribution` D\* after forensic recovery proves digest E |

**Bounded recovery-artifact rule:**

- The `graph_data` path is created only if D\* is proven.
- It contains exactly one `GraphContribution` JSON for D.
- It is not a general repair registry or new schema.
- If the repository already has an obviously canonical one-off maintenance-data location on the implementation base, use that exact existing location instead, but do not create two authorities. Report the substituted path in handback.
- Maximum recovery artifacts: **1**.

No other production path is authorized. In particular, do not modify `contribution_store.py`, `contribution_rebuild.py`, `kernel/__init__.py`, or a server service/route unless the current invariant cannot be implemented without a new contract; if so, stop for DESIGN.

## §5 Files and capabilities explicitly out of scope

| Path/layer/capability | Why out of scope |
|---|---|
| Any `out/graph_memory/worlds/eldyrwild/revisions/*.json` historical revision | Immutable authority; never rewrite |
| `src/graph_memory/kernel/contributions.py` digest field selection | Changing digest semantics would redefine existing revision authority instead of healing the ledger |
| `src/graph_memory/kernel/contribution_rebuild.py` | Rebuild is the verifier. Do not special-case D or weaken mismatch rejection |
| `src/graph_memory/world_supergraph/contribution_store.py` | Unconditional storage is internal primitive; authority guard belongs before the write in the owning Kernel operation for this defect |
| World Graph projection/conformance/adjudication code | Graph semantics are not changing |
| Session recap/source artifacts | Historical source not implicated |
| D's parent or sibling contribution payloads | Only D is in repair scope |
| `contribution:4c89cbbf15da5d10` | Separate July repair contribution; audit for equality but do not mutate |
| Lysandra correction implementation | Blocked successor |
| Generic “repair any contribution” CLI/API | New management capability; explicitly not this slice |
| tracker/status/roadmap edits | Separate doc sync after live exit proof |

## §6 Implementation contract and conditional matrices

### A. Kernel source-bound retry guard

```text
Input:
  current World Graph store/revision
  incoming new_contribution
  superseded_contribution_id

Authority:
  if current revision already binds incoming contribution_id, its source digest is immutable authority

Required behavior before any write_contribution_record(new_contribution):
  compute incoming source digest
  look for existing revision-bound digest for incoming contribution_id

  if no existing revision-bound digest:
    preserve current normal supersede behavior

  if existing digest != incoming digest:
    fail/no-op before ledger or index mutation

  if existing digest == incoming digest:
    do not blindly replace the existing ledger source record
    if ledger record exists and its source digest == bound digest:
      preserve existing idempotent/recovery behavior
    if ledger record is missing or its source digest != bound digest:
      integrity failure
      do not synthesize/overwrite it from caller payload

Invariant:
  caller payload cannot redefine already-bound source authority

Failure behavior:
  source-bound collision → published=false or existing stable exception/result;
                           no head/ledger/index mutation
  missing/mismatched bound ledger → integrity failure; no caller-payload recovery

Replay/idempotency:
  exact already-bound source → existing safe no-op/recovery
  same ID, changed source → rejected before write
```

Do not prescribe a new public result type unless existing `ContributionMergeResult` / existing errors cannot express the failure. A new public error contract is a DESIGN stop.

### B. Forensic recovery contract for D\*

Before authoring the recovery JSON, capture:

```text
current live head H0
current D manifest entry:
  contribution_id
  status
  source_payload_sha256 = E_manifest

current H0 contribution_source_payload_sha256[D] = E_map

historical:
  rev:4d0636... D digest/status
  rev:bbf29b... D digest/status
  rev:a3262c... D digest/status

current ledger D:
  raw file SHA256
  compute_contribution_source_payload_sha256 = A_now
  full payload
  status
  produced_at
  source/campaign/supersession/assertion fields

current contribution index:
  bucket/status for D
```

Required authority relationship:

```text
E_manifest == E_map
E_manifest == digest(D) in rev:4d0636...
E_manifest == digest(D) in rev:bbf29b...
E_manifest == digest(D) in rev:a3262c...
A_now != E_manifest  # baseline corruption to heal
```

If any immutable revision digest differs, stop.

#### Acceptable D\* recovery sources, strongest first

1. A byte-exact historical copy of D from a durable backup/artifact whose provenance predates the corrupting retry.
2. Deterministic reconstruction from parent A + the documented July repair transform + independently recovered metadata, where the resulting candidate hashes exactly to E.
3. A bounded reconstruction against E only when all semantic fields are already proven, the remaining variable field(s) and search domain are derived from authoritative timestamps/metadata, exactly one candidate matches E, and the handback records the method and search domain.

**Not acceptable:**

- editing E;
- changing digest exclusions;
- accepting a candidate only because the graph semantics look the same;
- using the current corrupted ledger as authority;
- taking a new retry-generated contribution and stamping its digest into graph history;
- brute-force search over unconstrained semantic fields;
- creating a new contribution ID to bypass D;
- copying from an unproven temp/worktree artifact.

D\* must additionally prove the July transform from A:

```text
D*.contribution_id == contribution:d3d244474789879c
D*.supersedes_contribution_id == contribution:2807888820d76c78
D*.authored_by == operator:graph-v1-projection-repair
D*.selection identity corresponds to reject:assertion:134135a4f3a2487b
D*.accepted_assertions == A.accepted_assertions minus assertion:134135a4f3a2487b
D*.rejected_assertions == A.rejected_assertions plus that assertion as rejected
D* preserves the source artifact/revision/profile/campaign fields documented as copied from A
compute_contribution_source_payload_sha256(D*) == E
```

If exact D\* cannot be proven, **STOP**. The generic prevention fix may be proposed as a separate slice, but this heal PR must not claim completion.

### C. Fixed one-off heal CLI

Recommended modes:

```text
status
  fixed world: eldyrwild
  fixed contribution: contribution:d3d244474789879c
  read-only
  --root optional
  --expected-head-revision-id optional for inspection
  no live-write flag required
  prints:
    head
    immutable E
    historical E agreement
    current ledger A_now/raw sha/status
    index status
    D* raw sha/source digest if artifact exists
    eligible | already_healed | ineligible | integrity_failure

apply
  fixed world + fixed D + fixed repository recovery artifact
  requires --expected-head-revision-id
  --root optional
  if resolved root == configured canonical world_graph_root():
    requires --allow-live-world
  no arbitrary contribution-id/file/digest/status flags
```

**Apply preconditions:**

- exact current head equals expected head;
- head is a descendant of the historical repaired line or otherwise carries the same immutable D authority with proven continuity;
- current head's digest map and replay manifest agree on E and D lifecycle status;
- historical repair revisions agree on E;
- D\* validates, has exact D identity/repair transform, and hashes to E;
- current ledger/index are either the known corrupt state or already healed;
- every other contribution record is out of mutation scope.

**Apply effect:**

- replace only mutable ledger record D with exact D\*
- set D's mutable contribution-index lifecycle bucket to the revision-bound status
- do not alter `baseline_revision_id` or contribution ordering
- do not publish a World Graph revision
- do not rewrite any revision file

The operator action must serialize against graph writers. Re-read the expected head inside the same maintenance lock immediately before the ledger/index replacement. If the existing internal world write lock cannot be used safely from this fixed script without adding a new generic maintenance API, stop for DESIGN rather than inventing a second locking scheme.

**Post-write verification before success:**

- head revision id unchanged
- all revision files unchanged
- ledger digest(D) == E
- manifest/map E unchanged
- index D lifecycle == manifest lifecycle
- all other contribution ledger raw hashes unchanged
- pinned rebuild(`compare_revision_id=head`, `publish=False`) equivalent
- unpinned rebuild(`publish=False`) equivalent to same head

If post-write verification fails, restore the captured pre-heal ledger/index state before reporting failure when restoration is safely possible. Never publish a graph revision as rollback.

### D. State/fallback matrix

| Path | Loading | Success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Kernel supersede new ID | existing | unchanged behavior | existing | existing | existing | existing CAS | existing |
| Kernel same-ID different-source retry | current head digest | reject before write | n/a | fail closed | no ledger/index write | no write | deterministic reject |
| Heal status | current head + historical revisions + D ledger + D\* | eligible/already_healed | ineligible | fail closed | integrity_failure | report | read-only |
| Heal apply clone | exact expected head | ledger/index healed, head unchanged | no fallback | fail closed | rollback/fail closed | no write | already_healed |
| Heal apply canonical | same + live opt-in | same | no fallback | fail closed | same | no write | already_healed |
| Rebuild proof | exact unchanged head | equivalent | n/a | fail | mismatch blocks | exact pin | deterministic |

No fallback authority is permitted for E, D identity, or D\*.

### E. Identity matrix

| Situation | Rule | Ambiguity | Fallback |
|---|---|---|---|
| Contribution D | literal `contribution:d3d244474789879c` | any other ID = fail | No |
| Parent A | literal `contribution:2807888820d76c78` | missing = stop | No |
| Rejected assertion X | literal `assertion:134135a4f3a2487b` | missing/duplicate = stop | No |
| Expected digest E | exact immutable revision-bound value | immutable disagreement = stop | No |
| D\* | exact D ID + exact E digest + exact transform | multiple candidate payloads matching authority/provenance = stop | No |
| Current head | exact expected revision for apply | stale = fail | No |

### F. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Retry | Migration | Rollback |
|---|---|---|---|---|---|
| Kernel retry guard | existing ledger/revision formats | already-bound source cannot be overwritten | deterministic reject/no-op | none | n/a |
| Recovery artifact | existing `GraphContribution` schema JSON | model load preserves exact D\*; source digest E | immutable checked-in bytes | no schema | Git revert affects future tool availability only |
| Temp heal | copied ledger/index | exact D\* + manifest lifecycle | already_healed | none | restore pre-heal copy |
| Live heal | canonical mutable ledger/index only | pinned/unpinned replay equals unchanged head | already_healed | none | restore pre-heal mutable state on verified failure; never rewrite revisions |

## §7 Evidence required to merge

| Guarantee | Boundary | Evidence | Scenario | Expected | Stop |
|---|---|---|---|---|---|
| Current bug mechanism is real | Kernel merge/store | adversarial regression | same ID, different `produced_at`/source digest retry | pre-fix reproduces ledger overwrite; test would fail before fix | live defect not reproducible by this mechanism |
| Different-source retry cannot mutate | Kernel merge | contract/adversarial | retry after bound contribution | published=false/failure; head, raw ledger, index equal | any mutable drift |
| Exact-source retry still safe | Kernel merge | regression | retry same ID + same source digest | existing idempotent/recovery semantics preserved | new regression |
| Missing/corrupt bound ledger not synthesized | Kernel merge | integrity | delete/tamper bound ledger then retry caller payload | fail closed; no reconstruction | caller payload becomes authority |
| Historical E is coherent | forensic CLI/test | integrity | load historical revisions + current head | exact same E/status lineage as allowed | immutable disagreement |
| D\* is exact recovered authority | artifact/test | contract | validate artifact and transform | exact D/A/X fields; digest E | digest/provenance mismatch |
| Artifact tamper fails | CLI/test | integrity | alter recovered copy | ineligible/integrity failure | accepted |
| Status is read-only | CLI | contract | status against real clone/canonical | tree/ledger/index raw hashes unchanged | any write |
| Stale head cannot heal | CLI | adversarial | status H → advance clone → apply H | no ledger/index write | mutation |
| Live root requires opt-in | CLI | adversarial | canonical apply without flag | fail closed | mutation |
| Heal touches only D/index membership | CLI/store | integration | real clone apply | all other ledger raw hashes equal; head/revisions equal | unrelated drift |
| D index lifecycle restored | CLI/store | contract | compare manifest vs index after heal | same status/bucket; ordering/baseline unchanged | index disagreement |
| Pinned replay healed | rebuild | merge gate | compare exact current head after clone heal | `rebuild_equivalent_to_pinned_revision` | failure — **NOT WAIVABLE** |
| Unpinned replay healed | rebuild | merge gate | rebuild `publish=False` after clone heal | equivalent to same head | failure |
| Heal retry stable | CLI | adversarial | apply again | `already_healed`; no raw-byte churn | second mutation |
| Existing Kernel suites remain green | Kernel | regression | owning suites | green | new head-only failures |
| No semantic graph mutation | graph/revision | integration | fingerprint before/after clone heal | same head/revision tree/projection/effective counts | any semantic/revision change |

### Required commands

```bash
uv sync --locked

uv run ruff check \
  src/graph_memory/kernel/contribution_merge.py \
  scripts/heal_eldyrwild_contribution_integrity.py \
  tests/test_eldyrwild_contribution_integrity_heal.py \
  tests/test_graph_kernel_contribution_merge.py

uv run pytest \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_kernel_contribution_rebuild.py \
  tests/test_graph_kernel_contribution_source_authority.py \
  -q

uv run pytest tests/test_eldyrwild_contribution_integrity_heal.py -q

git diff --check
git diff --name-only <implementation-base>...HEAD
git diff --stat <implementation-base>...HEAD
```

### Mandatory real-clone proof

Use a temporary clone of the real configured Eldyrwild world store. Do not mutate canonical `out/` during PR verification.

```text
1. clone current Eldyrwild world directory and required run/source anchors
2. record clone head H
3. hash complete clone revision tree, contribution ledger, and index
4. run heal status
5. record:
   E
   historical E checks
   A_now
   corrupt ledger raw SHA
   current index status
   D* raw SHA/source digest/provenance
6. require status eligible
7. run apply --expected-head-revision-id H against clone
8. require:
   head still H
   revision-tree digest unchanged
   D ledger source digest == E
   D index lifecycle == manifest lifecycle
   every other contribution raw SHA unchanged
9. pinned rebuild compare H → equivalent
10. unpinned rebuild publish=False → equivalent to H
11. run exact apply again → already_healed/no mutation
12. reproduce source-bound collision retry against healed clone → no ledger/index/head mutation
13. run the Lysandra correction status/preflight read-only if its branch/tool is available only as an optional smoke; do not depend on unmerged PR #537 for this slice
```

### Post-merge canonical live exit proof — required for slice DONE

The implementation PR merges after the clone proof. Do not mark the tracker slice DONE yet.

On canonical Eldyrwild:

```text
1. record merged implementation SHA
2. run status read-only
3. capture exact P_live = current head
4. capture:
   revision tree digest
   D ledger raw SHA / A_now
   E from P_live map + manifest
   contribution index digest/status
5. require eligible
6. run:
   heal_eldyrwild_contribution_integrity.py apply \
     --expected-head-revision-id P_live \
     --allow-live-world
7. capture post-heal state
8. require:
   head is still exactly P_live
   revision tree digest unchanged
   D source digest == E
   D index lifecycle == manifest lifecycle
   all non-D contribution records unchanged
   pinned rebuild(P_live) equivalent
   unpinned rebuild equivalent to P_live
9. exact retry → already_healed/no mutation
10. only now doc-sync:
    eldyrwild-contribution-integrity-heal = DONE
    eldyrwild-lysandra-threat-direction-correction = READY
```

This live heal is an operational metadata repair, not a new World Graph revision. The evidence must make that distinction obvious.

### Baseline failure protocol

The current D mismatch is the defect this slice owns, so its pre-heal pinned rebuild failure is expected evidence, not a waiver. The merge gate is that the same clone succeeds after the bounded repair.

No waiver may excuse:

- inability to prove E;
- inability to prove D\*;
- mutable ledger/index drift on rejected same-ID retry;
- revision/head mutation during heal;
- pinned rebuild failure after heal;
- unpinned rebuild failure after heal;
- unrelated contribution mutation.

## §8 Required review handback

The review handback must include:

1. Exact PR/branch/head SHA.
2. Exact implementation-base SHA; proof it descends from `5dae4183…` and contains this handoff.
3. §1 mission and merge-ready invariant copied exactly.
4. Nano-commit list and story.
5. Actual changed paths and focused diff stat.
6. Root-cause reproduction:
   - first bound source digest;
   - retry same ID;
   - changed field(s), especially `produced_at` if confirmed;
   - proof pre-fix ledger/index corruption;
   - proof post-fix no mutation.
7. Current real-clone H.
8. Immutable E from:
   - current H map;
   - current H replay manifest;
   - `rev:4d0636…`;
   - `rev:bbf29b…`;
   - `rev:a3262c…`.
9. Current corrupt D:
   - raw SHA;
   - `A_now`;
   - lifecycle/index state;
   - exact semantic/source diff against D\*.
10. D\* recovery provenance:
    - source/method;
    - raw SHA;
    - source digest;
    - transform proof from A/X;
    - any bounded reconstruction search domain and uniqueness proof.
11. Real-clone before/after ledger/index fingerprints.
12. Proof all non-D contribution records are unchanged.
13. Proof head/revision tree is unchanged.
14. Pinned rebuild exact result.
15. Unpinned rebuild exact result.
16. Heal retry result.
17. Stale-head and live-root-fence results.
18. Every required test/lint command and exact result with provenance.
19. Baseline failures and waivers; waivers must be none for all non-waivable gates.
20. Paths outside §4; none or stop report.
21. Stop conditions encountered/resolved.
22. Confirmation that Lysandra correction remains unimplemented/unclaimed by this PR.
23. Confirmation that tracker/status/roadmap were not marked DONE/READY in this implementation PR.
24. Explicit statement: live canonical heal is still pending after merge, or its separately recorded post-merge exit evidence if review occurs after that operation.

## §9 Acceptance rubric

Accept only when all are true:

- [ ] The same-ID/different-source overwrite defect is reproduced and fixed at the pre-write authority boundary.
- [ ] A rejected source-bound retry leaves graph head, contribution ledger bytes, and contribution index unchanged.
- [ ] Exact-source retry/recovery behavior from existing Kernel contracts remains correct.
- [ ] Missing/corrupt already-bound ledger is never reconstructed from caller payload.
- [ ] E agrees across current revision authority and historical repair revisions.
- [ ] D\* is independently recovered, exact-ID, exact-transform, and hashes exactly to E.
- [ ] No hash/digest/revision semantics were changed to make D\* pass.
- [ ] The fixed maintenance CLI accepts only exact D and fixed checked-in D\*.
- [ ] Canonical writes require exact expected head + explicit live opt-in.
- [ ] Clone heal changes only D's mutable ledger/index state and publishes no revision.
- [ ] Every other contribution record is byte-identical after clone heal.
- [ ] Current head and revision tree are byte/identity-equivalent before/after.
- [ ] Pinned rebuild is equivalent after heal — **NOT WAIVABLE**.
- [ ] Unpinned rebuild is equivalent after heal — **NOT WAIVABLE**.
- [ ] Exact heal retry is no-op/stable.
- [ ] No generic repair API/UI/registry was introduced.
- [ ] No Lysandra/source/conformance semantics changed.
- [ ] Implementation PR remains merge-ready proof only; tracker slice is not called DONE until the post-merge canonical live exit proof succeeds.

## Stop conditions

Stop and report instead of broadening if:

- current `origin/main` does not descend from PR #538 merge `5dae4183…`;
- tracker no longer marks this heal as the next READY semantic predecessor;
- current live D mismatch is absent (already healed elsewhere) without an auditable successor state;
- immutable current/historical revisions disagree on E or D lifecycle;
- D does not appear in the historical repair chain described above;
- the actual corruption mechanism is materially different from same-ID/different-source pre-write overwrite;
- more than D is source-digest corrupt;
- D\* cannot be uniquely recovered from trustworthy evidence;
- recovery requires changing E, digest exclusions, contribution identity, or immutable revision files;
- recovery requires inventing a new contribution rather than restoring D;
- safe prevention requires a new public Kernel maintenance API/result/schema;
- safe heal requires modifying `contribution_store.py` or `contribution_rebuild.py` beyond the current bounded design;
- a fixed-target script cannot serialize safely against world writers with existing lock authority;
- pinned or unpinned rebuild still differs after candidate heal;
- any graph node/edge/assertion support/evidence/source-artifact semantic changes as a result of the heal;
- any contribution other than D must be rewritten;
- a path outside §4/bounded single-artifact rule is required;
- a required acceptance gate needs an operator waiver.

Use this stop report:

```text
Stop condition:
Observed evidence:
Why immutable revision authority cannot currently be honored:
Invariant clause affected:
Mutation that was NOT performed:
Required new contract or predecessor:
Proposed successor slice:
tracker/status change required:
```

## Named successor — remains false in this PR

`eldyrwild-lysandra-threat-direction-correction`

After this implementation merges and the canonical live heal exit proof succeeds, perform a separate docs sync that marks this slice DONE and Lysandra READY. Then rebase/rework the Lysandra correction implementation onto that healed main. Do not merge or live-apply the Lysandra correction while contribution replay remains untrustworthy.
