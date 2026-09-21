# HANDOFF — reconcile Eldyrwild PC identity continuity

**Created:** 2026-09-21
**Status:** ACTIVE — prerequisite to finishing DungeonMindBuddy PR #742
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-eldyrwild-pc-identity-reconciliation-v1.md`
**Primary implementation repository:** `Drakosfire/DungeonMind`
**Blocked consumer:** DungeonMindBuddy PR #742
**Suggested branch:** `recovery/eldyrwild-pc-identity-reconciliation-v1`
**PR title:** `RECOVERY: reconcile Eldyrwild PC identities`

> Land this handoff durably on DungeonMindBuddy `main` before worker dispatch.
>
> This is a live World-authority repair. DungeonMind owns the mutation. DungeonMindBuddy must not revive local graph authority, rewrite IDs in the resolver, or silently translate one durable identity namespace into another.

## §1 Mission

Reconcile the six long-running player-character identities in the live `eldyrwild` World so that the governed World, canonical identity sources, projections, and authoring clients all name the same durable PC identities without losing relationships, evidence, history, or replayability.

**Merge-ready invariant:**

```text
For each of the six C1 PCs there is exactly one current canonical durable
World identity; every existing relationship/evidence/history path remains
attached or traceably redirected to that identity; the reconciliation is
represented through governed replayable World history; and exact replay
reconstructs the same current World without client-side ID rewriting.
```

The intended downstream result is that #742 can resolve:

```text
"Ephanna the Kenku Warlock"
→ canonical existing Ephanna
→ governed alias/write
```

instead of failing `orphan_accepted_assertion`.

## §2 Frozen evidence and reason for this PR

#742 dogfood stopped correctly at its Case B gate.

Observed live authority:

```text
world:
  eldyrwild

head:
  rev:e570042d33a30d07e053c578dedbc804

Ephanna resolver target:
  pc:ephanna

live lineage:
  node:ephanna exists
  pc:ephanna does not exist
  pc:ephanna never appears across all 45 revisions

broader cohort:
  all six C1 PCs use node:* identities from root through current head

failed governed write:
  governed_write_inexpressible
  orphan_accepted_assertion
```

No World mutation or identity rewrite occurred.

Repository authority simultaneously contains later accepted PC identity material using `pc:*`, including world-owned `pc:ephanna`, while current party/PC resolution also emits `pc:ephanna`.

Therefore the problem is not “Ephanna has never been ingested.”

The problem is:

```text
accepted/current identity contract
          !=
live durable Eldyrwild identity
```

The exact historical cause is not yet assumed.

## §3 CHECKPOINT A — classify the divergence before mutation

Before writing anything, establish the exact chronology for the six PCs.

For every PC, record:

```text
display name
live current node ID
live root node ID
expected/canonical ID from party registry
ID in sealed/adopted World input
ID in later accepted pc:* contribution material
first artifact/operation that claims pc:* authority
whether that operation was ever published into this live lineage
```

Cohort:

```text
Baergrom
Bonogo
Caelynn
Ephanna
Karsemine
Stafl
```

Expected namespace under current Buddy identity contracts is `pc:<slug>`, but that is a hypothesis to be proven against the complete accepted authority chronology before mutation.

Classify the divergence as exactly one of:

### A — recovery/adoption omission

The `pc:*` identity transition was already accepted/published as authority, but the lineage restored/adopted into the present DungeonMind authority omitted it.

### B — accepted but never published transition

The repository contains accepted `pc:*` identity material, but that transition never actually advanced the authoritative Eldyrwild lineage.

### C — `node:*` is still authoritative

Current authority explicitly retained `node:*` as canonical and later `pc:*` material/resolvers are wrong.

If C is proven, **STOP and rebrief**. Do not mutate the World.

Do not decide between these cases from labels, filenames, or intent prose alone. Use exact revisions, receipts, contribution/identity records, and publication history.

## §4 Capability boundary

If CHECKPOINT A proves that `pc:*` is the intended current durable identity contract, this PR owns one outcome:

> reconcile exactly these six live PC identities to that contract through DungeonMind's governed identity/revision machinery.

This PR does **not** own a general identity migration framework.

The preferred conceptual result is:

```text
legacy current identity
  node:<pc>

        ↓ governed identity reconciliation

canonical current identity
  pc:<pc>

legacy identity
  retained only as inspectable historical/redirect identity
```

The exact existing DungeonMind primitive may be merge/reconciliation/identity-decision based. Reuse it.

Do not implement this as:

```text
if id == pc:ephanna:
    actually use node:ephanna
```

Do not solve it with aliases alone.

Do not mutate raw PostgreSQL rows or graph JSON.

## §5 Atomicity requirement

The six PCs are one cohort and one identity-contract defect.

The live World must never intentionally stop in:

```text
3 PCs migrated
3 PCs legacy
```

The application must produce one governed, expected-parent operation whose observable publication either:

```text
all six reconciled
```

or:

```text
no live World change
```

If existing DungeonMind identity/publication machinery cannot express the six-PC reconciliation atomically and replayably, **STOP**. Do not implement sequential live cleanup merely to make progress.

## §6 Required resulting identity behavior

After successful publication, for all six PCs:

| Situation                | Required state                                                    |
| ------------------------ | ----------------------------------------------------------------- |
| Current canonical lookup | `pc:<slug>` resolves exactly                                      |
| Legacy `node:*` ID       | Historical/redirect state only; not a second current canonical PC |
| Label lookup             | May discover the PC, but label is never durable identity          |
| Alias lookup             | Follows governed identity semantics; no first-win rebinding       |
| Relationships            | Preserve prior endpoints semantically under canonical identity    |
| Evidence                 | Preserve all existing evidence/support                            |
| Campaign scopes          | C1/C2 history remains scoped exactly as before                    |
| Source history           | Preserved                                                         |
| Identity history         | Explicitly records reconciliation                                 |
| Replay                   | Reconstructs the reconciled state                                 |
| Retry                    | Exact same operation is already-applied/no-op                     |
| #742 resolver            | `pc:ephanna` names a real current World object                    |

No duplicate active PC may survive.

## §7 Files in scope

Primary repository: `Drakosfire/DungeonMind`.

Expected application-level lease:

| Action             | Suggested path                                                            | Purpose                                                     |
| ------------------ | ------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Create             | `src/dungeonmind/application/eldyrwild_pc_identity_reconciliation.py`     | Exact-six preflight + governed reconciliation orchestration |
| Create             | `scripts/eldyrwild_pc_identity_reconciliation.py`                         | Operator inspect/apply entry point                          |
| Create             | `tests/unit/test_eldyrwild_pc_identity_reconciliation.py`                 | Exact cohort, mismatch, idempotency and atomicity proof     |
| Create             | `tests/integration/test_postgres_eldyrwild_pc_identity_reconciliation.py` | Real PostgreSQL parent→child→reload→replay proof            |
| Modify if required | existing public DungeonMind identity/publication composition root only    | Wire existing governed primitive; no new architecture       |

### Bounded discovery exception

```text
Directories:
  src/dungeonmind/application/
  src/dungeonmind/domain/
  src/dungeonmind/infrastructure/postgres/

Maximum additional production paths:
  4

Allowed:
  existing read-only identity/history inspection
  existing identity-decision invocation
  existing atomic World publication/CAS composition

Not allowed:
  new generic identity model
  new durable decision kind
  direct SQL mutation
  new graph store
  Buddy-owned persistence
```

If a new generic DungeonMind identity primitive is required, stop and rebrief.

## §8 Preflight before live apply

Against the actual current `eldyrwild` head, prove:

1. the parent is still exactly the expected live head or explicitly re-anchor to the newer head;
2. all six legacy identities exist;
3. no `pc:*` target is already current under a conflicting identity;
4. every relationship touching the six is inventoried;
5. all evidence/support attached to the six is inventoried;
6. redirects/merge history involving the six are inventoried;
7. no unrelated world identities collide with any canonical target;
8. CHECKPOINT A still proves `pc:*` is the intended target contract;
9. the operation can be committed atomically;
10. rollback/replay behavior is understood before mutation.

Any unexpected identity state is a STOP, not permission to “repair until green.”

## §9 Required proof before merge

### Synthetic / isolated owning-boundary proof

Starting from a faithful fixture or isolated PostgreSQL copy of the current parent:

```text
current:
  node:ephanna
  ...
  six legacy PCs

apply reconciliation
        ↓
one child revision
        ↓
current canonical:
  pc:ephanna
  ...
  six canonical PCs

legacy IDs:
  redirects/history only
```

Prove:

* six and only six PCs are reconciled;
* no unrelated node changes identity;
* relationships are preserved;
* evidence/support is preserved;
* campaign scopes are preserved;
* no duplicate active PC survives;
* exact retry is idempotent;
* stale-parent apply fails with zero mutation;
* failure injected before commit leaves parent unchanged;
* reload produces the same result;
* full durable replay reconstructs equivalent current identity state.

### Live exit

Only after implementation review/merge:

```text
re-anchor actual eldyrwild head
→ rerun complete preflight
→ explicit operator apply
→ expected-parent CAS
→ one governed child revision
→ reload
→ exact identity inspection
→ full replay/equivalence proof
→ exact retry proof
```

Record exact parent and resulting child revision.

The PR is not operationally DONE merely because unit/integration tests pass. The live exit is required before #742 resumes.

## §10 Cross-repo acceptance witness

After the live identity repair succeeds, return to DungeonMindBuddy.

Do **not** modify #742 as part of this PR.

Re-anchor #742 onto the repaired authority/main state and rerun its existing-object witness:

```text
real C1 recap
→ highlight "Ephanna the Kenku Warlock"
→ resolver target = pc:ephanna
→ exact World lookup finds pc:ephanna
→ stage link_existing / alias
→ prepare succeeds
→ confirm succeeds
→ World child revision
→ reload
→ same pc:ephanna contains durable authored result
```

Then #742 must still complete its independent Create New witness.

This reconciliation PR is the prerequisite. It is not a substitute for either #742 dogfood case.

## §11 Explicit non-goals

Do not include:

* #742 implementation changes;
* resolver translation from `pc:*` to `node:*`;
* automatic label rebinding;
* general identity migration tooling;
* unrelated NPC/location identity cleanup;
* re-ingestion of C1/C2 recaps;
* new per-campaign Worlds;
* duplicate PC creation left active;
* raw graph/SQL repair;
* corpus prose edits;
* Agent work;
* derived-gold/V2-3 work.

V2-3 remains unauthorized.

## §12 Stop conditions

STOP and return to stewardship if:

* CHECKPOINT A proves `node:*` is actually the current intended canonical contract;
* authoritative chronology is insufficient to decide which namespace wins;
* any of the six has a materially different identity history requiring individual adjudication;
* reconciliation would lose or duplicate relationships/evidence;
* existing DungeonMind primitives cannot preserve redirects/history;
* the six cannot be committed atomically;
* a new generic identity decision kind or persistence model is required;
* replay cannot reproduce the reconciled child;
* a newer live World head changes the measured cohort;
* repair requires Buddy graph persistence or client-side ID rewriting.

Return:

```text
Stop condition:
Exact identity/invariant affected:
Authority evidence found:
Authority evidence still missing:
Current World mutation performed: yes/no
Strongest safe repair available:
Required successor/rebrief:
Impact on #742:
```

## §13 Required review handback

Record:

1. exact DungeonMind PR/head/base;
2. CHECKPOINT A classification: A, B, or STOP-C;
3. authoritative evidence establishing the canonical identity target;
4. exact six before/after IDs;
5. exact parent and child World revisions;
6. relationship/evidence counts and preservation proof;
7. identity-decision/redirect result;
8. replay-equivalence result;
9. retry/idempotency result;
10. actual changed paths;
11. every test command and exact result;
12. live-exit evidence;
13. any stop encountered;
14. confirmation that #742 remains blocked until re-anchor and both dogfood witnesses pass.

## §14 Acceptance rubric

* [ ] Canonical identity authority is proven before mutation.
* [ ] Exactly six intended PC identities are reconciled.
* [ ] One current canonical PC exists per character.
* [ ] No client-side durable-ID translation is introduced.
* [ ] Relationships and evidence survive unchanged in meaning.
* [ ] Legacy IDs remain inspectable through governed history/redirect semantics rather than becoming parallel current nodes.
* [ ] C1/C2 scopes survive.
* [ ] Publication is atomic against an exact parent.
* [ ] Stale/failing apply leaves the parent unchanged.
* [ ] Exact retry is idempotent.
* [ ] Full replay reconstructs the reconciled World.
* [ ] Live Eldyrwild exit is proven.
* [ ] #742 remains unmodified by this PR.
* [ ] #742 is explicitly handed back for Ephanna existing-object dogfood, then Create New dogfood.
* [ ] No V2-3 work begins.

## Sequence after this PR

```text
#742 HOLD
    ↓
this handoff lands on main
    ↓
DungeonMind identity reconciliation PR
    ↓
review + merge
    ↓
canonical live Eldyrwild apply + replay proof
    ↓
re-anchor #742
    ↓
Ephanna existing-object publish witness
    ↓
new-object publish witness
    ↓
#742 review / merge
    ↓
state sync
    ↓
only then consider V2-3
```
