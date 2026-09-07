---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY — Eldyrwild World authority recovery
  - Flow: WORLD-RECOVERY / WR1
  - Direction: STEWARD → CODE/OPERATE → REVIEW
  - Handoff: DungeonMindBuddy `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-eldyrwild-world-authority-recovery-v1.md`
  - Primary implementation repository: `Drakosfire/DungeonMind`
  - Suggested branch: `recovery/eldyrwild-world-authority-v1`
  - Suggested PR title: `RECOVERY: restore durable Eldyrwild World authority`

  ## Verification pointer
  - Buddy authority base: `a692dbe2bd3dd53a385891ae4ed4c83668bd58ec`
  - DungeonMind implementation base: `c8368d65d3122f8367d9c11f1be3a16d5b916f94`
  - Completed consumer: Buddy PR #689 MERGED (`0912ce4010655655b1f7b4966ee071e043b47721`)
  - DungeonMind recovery: PR #51 MERGED (`e82e790e011773369f07b1b431482d5026d4dd3e`)
  - Verification: exact D_A/D_B lineage + durable restart + backup/restore + #689 C2 Session 25 dogfood witness

  The checked-in handoff, cumulative diff, exact recovery evidence, destructive
  recovery witness, and independently rerun review evidence are the review
  contract. This body is transport metadata.
---

# HANDOFF — restore durable Eldyrwild World authority

**Created:** 2026-09-06  
**Status:** COMPLETE — DungeonMind PR #51 MERGED; Buddy PR #689 unblocked and MERGED  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-eldyrwild-world-authority-recovery-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY — Eldyrwild World authority recovery`  
**Flow / owner:** `WORLD-RECOVERY / WR1`  
**Direction:** STEWARD → CODE/OPERATE → REVIEW  
**Buddy authority base:** `a692dbe2bd3dd53a385891ae4ed4c83668bd58ec`  
**DungeonMind implementation base:** `c8368d65d3122f8367d9c11f1be3a16d5b916f94` (DungeonMind PR #50 merge)  
**DungeonMind recovery PR:** #51 MERGED `e82e790e011773369f07b1b431482d5026d4dd3e` (2026-09-07) — `RECOVERY: restore durable Eldyrwild World authority`  
**Completed consumer:** DungeonMindBuddy PR #689 MERGED `0912ce4010655655b1f7b4966ee071e043b47721` (2026-09-07)  
**Dispatch-time blocked consumer (historical):** DungeonMindBuddy PR #689 held at dogfood gate; reviewed head at dispatch `d550e877820fcb0de125a949013672c06e5e398c`  
**Primary implementation repository:** `Drakosfire/DungeonMind`  
**Suggested branch:** `recovery/eldyrwild-world-authority-v1`  
**Suggested PR title:** `RECOVERY: restore durable Eldyrwild World authority`

> Recovery and the blocked consumer are complete. This record does **not** mark Stage 1 / STOP 1 complete. STOP 1 remains the assembled DEMO-R1 dogfood close.

> This is a recovery operation, not a new migration and not a Buddy graph-storage feature. DungeonMind remains the sole owner of living World Graph persistence and publication. Buddy remains a controlled consumer.

---

## §0 Why this handoff exists

Dogfood of Buddy PR #689 reached the correct governed World boundary and failed with `503 authority_unavailable`.

The failure exposed an assumption error in the cutover program:

```text
successful migration/cutover
!=
present-day durable recoverability
```

Historical evidence strongly establishes that the migration and live cutover happened:

- DungeonMind PR #34 proved exact Eldyrwild adoption into PostgreSQL at the owning boundary.
- Buddy PR #620 completed the World authority transfer and published the first DungeonMind-owned child.
- Buddy PR #633 later recorded live native reads against that child revision.

Current environment evidence is different:

- the expected live World database is absent;
- the surviving local `dungeonmind` database is empty;
- there is no surviving mounted volume/backup presently establishing the live World state;
- DungeonMind's checked-in `compose.postgres.yml` explicitly uses `tmpfs` and says it is development-only ephemeral storage, not a durability/backup contract.

The correct product interpretation is:

> The historical migration and cutover were real. The durable authority they created was not itself preserved in the current environment.

Do not reopen the migration design. Repair recoverability.

---

## §1 Mission and merge-ready invariant

### Mission

An operator can start from **no usable DungeonMind World database**, restore the exact last recoverable Eldyrwild authoritative lineage into one explicitly designated durable PostgreSQL authority, verify that authority without ad-hoc Buddy graph access, restart the database/container without losing it, and restore an independently backed-up copy into a second clean database with the same verified head.

The restored authority must then unblock the existing Buddy #689 C2 Session 25 dogfood path.

### Merge-ready invariant

```text
No operation may call an Eldyrwild database "restored authority" unless:

1. its lineage is proven from accepted recovery inputs;
2. its exact head is the last known recoverable authoritative head;
3. its adoption/membership/history invariants pass independently;
4. it survives ordinary container replacement through durable storage;
5. a backup can recreate the same verified authority in a clean target;
6. Buddy reads it only through the existing DungeonMind contract; and
7. no C1/C2 re-ingestion, Buddy graph fallback, approximate reconstruction,
   or silent head substitution is used.
```

If the exact last-known head cannot be reconstructed from surviving evidence, **STOP**. Do not silently bless an older head.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes: only exact, independently verifiable World authority may be restored/blessed. |
| Most likely adversarial sequence | Empty DB → restore D_A → fail to reconstruct D_B → declare D_A "good enough" → Buddy resumes on stale lineage. |
| Will §7 detect that failure? | Yes: exact expected-head and parentage checks are mandatory before the authority may be designated READY. |
| Easiest owning boundary to under-test | Recovery of post-adoption `D_B`, because the sealed adoption bundle reconstructs `D_A` but not automatically the post-cutover child. |
| Fact that forces stop/split | No exact D_B recovery input; evidence of a later authoritative head; recovery requires inventing/re-ingesting data; or only graph payload survives without the durable history required by DungeonMind authority. |

---

## §2 Frozen historical truth

These are recovery invariants, not approximate documentation.

### 2.1 Adopted Eldyrwild parent — D_A

```text
world_id:
  eldyrwild

sealed adoption bundle SHA-256:
  90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f

accepted adopted-membership SHA-256:
  538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890

DungeonMind adopted revision D_A:
  rev:34b1f8e2625d5ba693fc726a2a1a4720

shape at adoption:
  469 objects
  323 relationships
  3 secondary aspects
  5 aspect-selected relationships

history at adoption:
  83 source artifacts
  83 source revisions
  93 GraphContributionV2 records
  13 IdentityDecisionRecordV2 records
```

Canonical sealed bundle currently lives in DungeonMind history at:

`tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json`

Do not rewrite or regenerate it.

### 2.2 First DungeonMind-owned child — D_B

```text
D_A:
  rev:34b1f8e2625d5ba693fc726a2a1a4720

D_B:
  rev:680c246047d67f9fe0293ee90526f670

required parent:
  parent(D_B) == D_A
```

`D_B` was the first real post-cutover governed mutation. Its canary node was later ruled **operational history, not campaign content**. The canary does not need to become queryable product data, but `D_B`/`D_A` lineage remains accepted operational history.

Known canary identities include:

```text
node:cutover-canary
artifact:recap:longmont-c2:session-26-cutover-live-canary
```

Do not manufacture the missing source artifact merely to make the canary queryable.

### 2.3 Last-known-head rule

Repository evidence after cutover continued to identify `D_B` as the Eldyrwild head, including the later native-read work.

That is **evidence**, not permission to assume there was never a later authoritative revision.

Before restoration mutation, search the surviving repository/local authority evidence for any later published Eldyrwild revision.

Acceptable evidence includes:

- DungeonMind/Buddy checked-in authority records;
- published revision receipts / governed publication receipts;
- exact operation records;
- surviving database dumps/backups;
- surviving local database/volume state;
- exact review/publication artifacts;
- tracked or otherwise digest-verifiable operator artifacts.

If a later authoritative head than `D_B` is found, **STOP and rebrief using that exact lineage**. Do not continue with `D_B` as target.

---

## §3 CHECKPOINT A — prove the recovery target before mutation

This checkpoint is mandatory and comes before creating or blessing the designated authority database.

### A1. Re-anchor both repositories

Record exact:

```text
DungeonMind main
DungeonMindBuddy main
Buddy PR #689 head
all relevant recovery artifact locations
```

Do not assume the SHAs in this handoff are still current after dispatch.

### A2. Find exact D_B reconstruction evidence

The agent must determine whether the exact post-cutover child can be recovered.

Search at minimum:

- DungeonMind Git history and merged cutover PRs;
- Buddy cutover PRs/handoffs/review receipts;
- current and historical worktrees;
- tracked fixtures/artifacts;
- surviving `out/`/operator artifacts where identity is recorded;
- local PostgreSQL dumps/backups;
- Docker volumes or other surviving database state;
- exact governed review/publication inputs or receipts.

The objective is **not** to find prose describing D_B. It is to find an exact replay/restore input.

### Acceptable D_B recovery inputs

At least one of:

1. an exact database backup containing D_B and its required durable history;
2. an exact governed-publication input/receipt that can be replayed through current DungeonMind from D_A and deterministically produces D_B;
3. another accepted exact durable representation that current DungeonMind can verify as the complete D_B authority state.

### Not sufficient

Do not accept:

- `node:cutover-canary` label/id alone;
- a prose description of the canary;
- manually recreated source text;
- re-ingestion of Session 26 or any C1/C2 recap;
- graph-shape similarity;
- current labels/aliases matching expectations;
- a D_B graph payload without the durable source/contribution/identity/publication history DungeonMind requires;
- creating a new child and calling it D_B;
- restoring D_A and silently using it as current head.

### STOP A — D_B input unavailable

If exact D_B cannot be reconstructed:

```text
STOP_REASON = LAST_KNOWN_HEAD_RECOVERY_INPUT_MISSING
```

Return an evidence report containing:

- exact sources searched;
- what survives for D_A;
- what survives for D_B;
- whether D_B graph payload survives;
- whether its governed operation/publication input survives;
- whether a database backup survives;
- whether any later head evidence exists;
- the strongest exact state we can recover without invention.

Do **not** point Buddy at a newly restored D_A database. Product-owner alignment is required to decide whether to bless an older recovery point and create a new descendant.

A disposable scratch D_A reconstruction is allowed solely to prove the sealed bundle still works. It is not the designated authority.

---

## §4 Implementation lane if CHECKPOINT A passes

If and only if the exact target lineage is recoverable, implement one capability in `Drakosfire/DungeonMind`.

### 4.1 Durable local authority substrate

Preserve existing:

`compose.postgres.yml`

It is intentionally ephemeral and useful for clean development/integration testing.

Create a **separate** durable local authority composition, suggested path:

`compose.postgres.authority.yml`

Required posture:

- PostgreSQL/pgvector image remains pinned deliberately;
- data directory uses a named/bind volume, never `tmpfs`;
- World authority database is explicitly named/configured;
- defaults do not collide accidentally with the ephemeral integration database;
- operator can tear down/recreate the container without deleting the data volume;
- deleting the volume is explicit, never part of ordinary `down`/restart;
- file comments say local durability is not equivalent to remote backup/production HA.

Prefer a separate local port/service identity from the ephemeral substrate if that makes DB ownership obvious.

The database **name is not authority**. The DSN is.

Buddy's runtime connection remains:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL=<designated World DSN>
```

Buddy APP-STATE remains separate:

```text
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=<Buddy APP-STATE DSN>
```

Do not migrate Buddy APP-STATE in this PR.

### 4.2 Recovery/preflight application boundary

Create a bounded operator recovery/preflight seam in DungeonMind.

Suggested shape:

```text
scripts/eldyrwild_world_authority_recovery.py
```

with testable application logic below it if needed.

Minimum modes:

```text
check
restore/bootstrap
```

A useful command contract is conceptually:

```bash
uv run python scripts/eldyrwild_world_authority_recovery.py check \
  --database-url "$DUNGEONMIND_DATABASE_URL" \
  --world-id eldyrwild \
  --expected-head rev:680c246047d67f9fe0293ee90526f670
```

and an explicit restore/bootstrap mode that consumes only accepted exact recovery inputs.

Do not hardcode secret-bearing DSNs into source or docs.

### 4.3 Preflight must verify authority, not connectivity

`READY` requires all applicable recovery facts, not merely `SELECT 1`.

At minimum verify:

```text
PostgreSQL reachable
DungeonMind schema/migrations at expected head
world_id == eldyrwild
existing-world adoption receipt is present and valid
sealed/adopted membership checkpoint matches accepted value
D_A exists
last-known target head exists
current head == exact target head
parent(target head) == expected parent
adoption graph/history cardinalities match accepted recovery baseline
source artifact/revision history is present
contribution/identity history is present
current DungeonMind projection/read succeeds
```

Use existing DungeonMind public repository/application ports. DungeonMind PR #50 already added read-only authority enumeration for preflight consumers.

Do not build the verifier from Buddy ad-hoc SQL.

A narrowly bounded DungeonMind read-only port may be added only if an exact required invariant cannot be obtained through current public/application repositories.

### 4.4 Restore D_A through the accepted adoption seam

Against a migrated empty target:

- consume exact sealed bundle bytes;
- independently recompute/verify the sealed bundle digest;
- invoke current DungeonMind `adopt_existing_world`/current accepted adoption service;
- require exact D_A identity;
- require the accepted membership digest/checkpoint under the current receipt schema;
- require accepted adoption cardinalities/history;
- retry the exact adoption and prove no duplication.

Do not insert DungeonMind tables directly.

### 4.5 Restore D_B through an accepted exact seam

Use the exact recovery input established at CHECKPOINT A.

Preferred ordering:

1. restore a complete accepted database backup if one survives; or
2. replay the exact governed publication from D_A through current DungeonMind if exact replay input survives and deterministically reproduces D_B.

Required result:

```text
current head == rev:680c246047d67f9fe0293ee90526f670
parent(D_B) == rev:34b1f8e2625d5ba693fc726a2a1a4720
```

If current DungeonMind correctly represents the historical child with a newer receipt/schema wrapper while retaining exact public revision identity/content/history, record that compatibility explicitly.

Do not create a substitute child revision.

---

## §5 Backup and destructive recovery contract

A named Docker volume is persistence, not backup.

This PR must prove both.

### 5.1 Backup

After exact authority is restored and preflight is READY:

- create a PostgreSQL backup using standard supported PostgreSQL tooling (`pg_dump` custom format is acceptable);
- store it at an operator-selected path **outside the Git repository**;
- record SHA-256, timestamp, source database identity, DungeonMind version/commit, world id, and expected head in the review handback;
- never commit the dump or credentials.

No universal backup service is required in this PR.

### 5.2 Ordinary restart witness

Prove:

```text
restored authority READY
→ stop/remove authority container without deleting volume
→ recreate/start container against same volume
→ preflight READY
→ exact head unchanged
```

### 5.3 Clean restore witness

Create a **second clean database/volume** and restore the backup there.

Then require the same preflight:

```text
world == eldyrwild
head == exact target head
parentage correct
receipt/membership correct
history/cardinalities correct
projection/read succeeds
```

This second target is the destructive-recovery proof. Do not delete the newly designated primary authority merely to demonstrate restoration.

### STOP B — backup cannot reproduce authority

If backup restoration cannot produce the same verified authority, stop. Persistence without demonstrated recovery does not satisfy this handoff.

---

## §6 Buddy boundary and #689 consumer witness

This recovery PR must not add Buddy graph-storage logic.

After the DungeonMind authority is restored locally, use existing Buddy configuration:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind
DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL=<restored designated World DSN>
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=<existing separate Buddy APP-STATE DSN>
```

Do not point both authority variables at the same logical database.

Do not restore C1/C2 graph state from Buddy APP-STATE. It is not the World Graph authority.

### Required cross-repo dogfood witness

Use Buddy PR #689's exact historical recap path with the already adopted C2 Session 25 source:

```text
run_id:
  graph-ingest:longmont-c2:session-25:20260808T005650Z

source_artifact_id:
  artifact:recap:longmont-c2:session-25:fd38b5915b32

source_sha256:
  sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
```

Required observed path:

```text
exact historical run
→ durable Buddy source revision
→ governed DungeonMind current World projection
→ exact World snapshot/head identity
→ projected recap Markdown
→ at least one real graph pill
→ click pill
→ existing graph object card opens
```

Record:

```text
Buddy PR/head
DungeonMind PR/head
World database identity (redacted DSN; no password)
world_id
DungeonMind graph snapshot revision
source_revision_id
pill node_id + label
object-card identity
```

No `503 authority_unavailable` is acceptable at this checkpoint.

### STOP C — World restored but Buddy witness fails

If DungeonMind preflight is READY but #689 still fails, the failure has crossed back into Buddy integration/product code.

Stop this recovery lane. Do not expand the DungeonMind PR to repair Buddy UI/projection behavior.

Return the exact failing Buddy boundary for #689 re-review/repair.

---

## §7 Files in scope — DungeonMind PR write lease

Primary repository: `Drakosfire/DungeonMind`.

Expected lease:

| Action | Path | Purpose |
|---|---|---|
| Create | `compose.postgres.authority.yml` | Separate durable local World-authority PostgreSQL substrate; preserve ephemeral `compose.postgres.yml`. |
| Create | `scripts/eldyrwild_world_authority_recovery.py` | Explicit operator check/restore entry point. |
| Create | `src/dungeonmind/application/world_authority_recovery.py` | Testable recovery/preflight orchestration if script-only logic would duplicate authority rules. |
| Create | `tests/unit/test_world_authority_recovery.py` | Exact identity, fail-closed, target-head, and no-substitution contract proof. |
| Create | `tests/integration/test_postgres_world_authority_recovery.py` | Empty DB → D_A → exact child → preflight/replay PostgreSQL owning-boundary proof. |
| Create | `Docs/Runbooks/RUNBOOK-eldyrwild-world-authority-recovery.md` | Operator bootstrap/restart/backup/restore procedure and DSN separation. |

### Bounded discovery exception — read-only verification ports only

```text
Directory:
  src/dungeonmind/application/
  src/dungeonmind/infrastructure/postgres/

Maximum additional production-code paths:
  4

Allowed path kinds:
  existing repository/application read-only enumeration or receipt/history
  verification seams required to prove §1; tests for those seams

Decision rule:
  Add only when an exact §4.3 preflight invariant cannot be observed through
  existing public/application repositories. No new write path, schema, or
  generalized backup framework under this exception.
```

### Recovery-input artifact exception

An exact D_B recovery artifact may be added to a tracked recovery/fixture location **only if** CHECKPOINT A proves the exact bytes/identity already survive and the new file is a relocation/copy of those exact bytes with independent digest evidence.

Do not synthesize a new D_B artifact from documentation.

Any such path must be reported before implementation continues and added explicitly to the PR lease/review handback.

---

## §8 Explicitly out of scope / collision boundary

| Path/domain | Why |
|---|---|
| DungeonMindBuddy PR #689 implementation files | #689 is held consumer work; recovery lane does not modify it. |
| `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` contents/schema | Buddy APP-STATE is separate authority and not being migrated here. |
| C1/C2 recap re-ingestion | Not a World recovery mechanism. |
| Buddy local World Graph store/kernel | Retired/non-authoritative; must not become fallback. |
| New DungeonMind graph write/publication architecture | Existing governed publication seam remains authority. |
| New universal migration framework | Eldyrwild recovery only. |
| Remote/VPC production deployment | Later roadmap stage. This PR proves the recovery contract locally. |
| HA/replication/PITR orchestration | Later operational maturity; standard backup/restore proof is enough here. |
| Historical extraction/candidate artifact recovery | Separate Buddy DOGFOOD-CONTINUITY concern. |
| Making `node:cutover-canary` queryable | Explicitly retired as product data; do not fabricate provenance. |

---

## §9 State / fallback matrix

| Observable path | Required behavior |
|---|---|
| World DSN unreachable | `NOT_READY / authority unavailable`; no fallback. |
| Empty migrated DB | `NOT_READY / world missing`; no automatic implicit adoption on product startup. |
| D_A restored but target is D_B | `NOT_READY / stale recovery point`; never call READY. |
| Exact target head restored | READY only after receipt/membership/history checks pass. |
| Receipt/member digest mismatch | Integrity failure; fail closed. |
| Parentage mismatch | Integrity failure; fail closed. |
| Later authoritative head discovered | STOP/rebrief; do not restore D_B as current. |
| Backup missing | Running authority may be locally usable but this handoff remains incomplete. |
| Backup restore differs | STOP; do not claim recoverability. |
| Buddy #689 sees 503 while DungeonMind preflight READY | STOP C; Buddy integration owns next repair. |
| APP-STATE unavailable | Separate Buddy failure; never substitute World DB for APP-STATE. |

---

## §10 Persistence / replay contract

| Operation | Durable representation | Replay rule |
|---|---|---|
| D_A adoption | DungeonMind PostgreSQL + accepted adoption receipt/membership | Exact bundle retry is idempotent; different bundle conflicts/fails closed. |
| D_B restoration | Exact accepted recovery input established at CHECKPOINT A | Must reproduce exact public revision/parentage; no substitute child. |
| Container restart | Named/bind PostgreSQL volume | Ordinary container replacement leaves verified head unchanged. |
| Backup | External PostgreSQL dump + recorded SHA-256/metadata | Restore into clean target must reproduce verified authority. |
| Buddy read | Controlled DungeonMind projection/retrieval contract | Read-only; failure fails closed; no Buddy graph fallback. |

---

## §11 Evidence required to merge

Every row is required unless CHECKPOINT A stops the lane before implementation.

| Guarantee | Owning boundary | Evidence |
|---|---|---|
| Historical target truth established | Recovery investigation | Exact D_A/D_B/later-head ledger with sources and artifact identities. |
| No mutation without D_B input | Operator workflow | CHECKPOINT A handback before designated authority creation. |
| Durable substrate is distinct from ephemeral test DB | Docker/compose | `compose.postgres.yml` remains ephemeral; authority compose uses durable volume. |
| Exact D_A restored | DungeonMind PostgreSQL | Bundle digest, D_A revision, receipt/membership, counts/history. |
| Exact D_A replay idempotent | DungeonMind adoption | Same input → no duplicate durable state. |
| Exact D_B restored | DungeonMind publication/restore | Head exact D_B; parent exact D_A; recovery input provenance recorded. |
| Stale D_A cannot be READY | Recovery preflight | Adversarial test with expected D_B returns NOT_READY. |
| Membership/receipt tamper fails | Recovery preflight | Tamper/failure-injection test. |
| Ordinary restart survives | PostgreSQL volume | down/recreate container → same READY head. |
| Backup independently restores | PostgreSQL backup/restore | Clean second DB → same exact preflight and head. |
| Current World read works | DungeonMind public read | Projection/retrieval against restored authority returns exact snapshot/head. |
| Buddy integration works | Buddy #689 assembled product | C2 Session 25 recap → real pill → object card; exact graph snapshot recorded. |
| APP-STATE remains separate | Configuration/process | Distinct logical database URLs; no schema/data crossover. |

### Suggested focused verification

The implementation agent must replace/add exact commands appropriate to the final paths, but the evidence must include the equivalent of:

```bash
uv run pytest -q \
  tests/unit/test_world_authority_recovery.py \
  tests/integration/test_postgres_world_authority_recovery.py

# Existing adoption/regression owning boundary
uv run pytest -q tests/integration/test_postgres_eldyrwild_existing_world_adoption.py

# Existing authority enumeration/preflight dependencies
uv run pytest -q tests/integration/test_postgres_authority_enumeration_conformance.py

uv run ruff check <changed-python-paths>
uv run ruff format --check <changed-python-paths>
git diff --check
git diff --name-only <DUNGEONMIND_BASE>...HEAD
```

### Manual/destructive evidence

Record exact commands/results for:

```text
1. CHECKPOINT A recovery-input proof
2. start durable authority DB
3. migrate empty DB
4. restore D_A
5. restore exact target child/head
6. preflight READY
7. container down/up without volume deletion
8. preflight READY, same head
9. pg_dump backup + SHA-256
10. restore backup to a second empty DB/volume
11. preflight READY, same head
12. Buddy #689 C2 Session 25 real pill/object-card witness
```

Do not record passwords or full secret-bearing DSNs.

---

## §12 Explicit check-ins / STOPs

### CHECK-IN A — before authority mutation

Report to the product owner:

```text
last known authoritative head
whether any later head exists
exact D_B recovery input found/not found
exact artifact/receipt/backup provenance
whether full durable history is recoverable
```

No designated authority restoration before this check passes.

### CHECK-IN B — restored local authority

After exact target head is reconstructed:

```text
D_A identity
D_B/target identity
parentage
receipt schema
membership digest
counts/history
current projection/read result
```

Do not run Buddy dogfood until DungeonMind itself says READY.

### CHECK-IN C — destructive recovery proof

After container restart + second clean backup restore:

```text
primary persistent restart result
backup SHA-256
second clean restore result
exact head comparison
any differences
```

A database that merely survived because the original container still existed does not pass.

### CHECK-IN D — #689 dogfood

Run the real C2 Session 25 path and record:

```text
exact source revision
exact World snapshot revision
real pill identity
object card opened
first user-visible failure, if any
```

Then STOP.

Do not automatically merge #689 or dispatch the next demo-roadmap stage. Return to product-owner alignment.

---

## §13 Required review handback

Record:

1. `Review Cycle <N>` and exact DungeonMind PR/branch/head SHA;
2. exact Buddy `main` and #689 head used for cross-repo dogfood;
3. CHECKPOINT A recovery-target ledger;
4. exact D_A recovery evidence;
5. exact target-head/D_B recovery evidence and input provenance;
6. receipt schema + membership digest observed after restore;
7. accepted counts/history observed after restore;
8. restart witness;
9. backup file SHA-256 + redacted location + clean-restore witness;
10. Buddy #689 C2 Session 25 witness;
11. actual changed paths vs §7;
12. bounded-discovery paths, if any;
13. baseline failures/waivers;
14. all STOP conditions encountered and disposition;
15. what remains false: remote hosting/HA, generalized recovery, unrelated historical artifact recovery, STOP 1 completion. #689 merge is no longer remaining-false.

---

## §14 Acceptance rubric

- [ ] CHECKPOINT A proves the exact recovery target before designated-authority mutation.
- [ ] Exact D_A bundle/digest/revision/membership are independently verified.
- [ ] Exact last-known recoverable head is restored; no stale-head substitution occurs.
- [ ] Parentage/history integrity is verified through DungeonMind-owned seams.
- [ ] Existing ephemeral `compose.postgres.yml` remains available for disposable testing.
- [ ] New authority substrate uses persistent storage and survives container replacement.
- [ ] Backup/restore into a second clean target reproduces the same verified authority.
- [ ] Buddy APP-STATE and DungeonMind World authority remain separate logical authorities/DSNs.
- [ ] Buddy does not gain graph persistence/fallback logic.
- [ ] No C1/C2 re-ingestion or approximate reconstruction occurs.
- [ ] #689's real C2 Session 25 path reaches a real DungeonMind snapshot and interactive graph pill/object card.
- [ ] Product owner receives CHECK-IN D before #689 or roadmap sequencing resumes.

---

## Stop conditions

Stop and report instead of expanding when any of these appears:

- exact D_B/last-known-head recovery input does not survive;
- evidence of a later authoritative Eldyrwild head appears;
- recovery requires inventing source/candidate/canary data;
- only graph payload survives but required durable history does not;
- current DungeonMind cannot replay/restore accepted historical state without a new write architecture;
- a schema change is required merely to support this one recovery;
- backup/restore cannot reproduce the verified authority;
- restoring requires mutating Buddy APP-STATE or reviving Buddy graph authority;
- another active lane owns a required path/runtime/volume;
- required path exceeds §7 bounded discovery;
- #689 remains broken after DungeonMind preflight is READY (STOP C — hand back to Buddy);
- baseline/head gate requires an unapproved waiver.

Report:

```text
Stop condition:
Exact invariant affected:
Evidence found:
Evidence missing:
Strongest exact state recoverable without invention:
Affected repository/path/runtime ownership:
Whether designated authority was mutated:
Whether any backup/volume was created:
Proposed rebrief/product decision:
```
