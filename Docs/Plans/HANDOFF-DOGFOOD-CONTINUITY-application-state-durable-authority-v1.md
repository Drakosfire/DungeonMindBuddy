---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DEMO-R2 durable APP-STATE
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-application-state-durable-authority-v1.md
  - Branch: dogfood-continuity/application-state-durable-authority-v1

  ## Verification pointer
  - Prepared from accepted PR #690 head: 01e0addbdc55eb00c0c5a0c104a718259751084d
  - Implementation base: re-anchor to main after PR #690 merges
  - Verification: §7 durable restart + backup/clean-restore witness

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. The PR description is transport
  metadata only.
---

# HANDOFF — DOGFOOD-CONTINUITY: durable Buddy application-state authority v1

**Created:** 2026-09-07  
**Status:** ACTIVE — rebased on post-#690 `main`; source-lost rebrief recorded in §0A  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-application-state-durable-authority-v1.md`  
**Conversation/workstream:** DOGFOOD-CONTINUITY / DEMO-R2 durable APP-STATE  
**Flow / owner:** DOGFOOD-CONTINUITY  
**Direction:** DESIGN → CODE → REVIEW  
**Prepared from:** accepted PR #690 head `01e0addbdc55eb00c0c5a0c104a718259751084d`  
**Implementation base:** `08c4052e3e662d94936c37cf8837cdb01a9507ca` (PR #690 squash merge to `main`, 2026-09-07)  
**Suggested PR title:** `DOGFOOD-CONTINUITY: make Buddy APP-STATE recoverable`  
**Suggested implementation branch:** this branch after re-anchor/rebase, or a fresh isolated worktree at the post-#690 base

> Repository law: `AGENTS.md`. Persistence authority: `Docs/Design/ARCHITECTURE-application-state-layer.md`. Product sequence: `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`.

## §0A Rebrief — source authority destroyed before capture (2026-09-07)

At dispatch, the A0 re-anchor found the handoff's own most-adversarial sequence had already fired in production:

```text
2026-09-07 ~15:11 local: both DungeonMind PostgreSQL containers exited.
dungeonmind-postgres-dev (127.0.0.1:54329) holds /var/lib/postgresql/data on tmpfs
with no volume. The stop wiped it. On restart it initialized empty:
`dungeonbuddy_application_state` does not exist; the `dungeonmind` DB has zero user tables.
```

Verified loss sweep:

- no APP-STATE `pg_dump` ever existed (this handoff's §3: backup was "not a demonstrated product recovery contract");
- no docker volume contains a Buddy APP-STATE data dir (all 21 volumes inspected; only `dungeonmind_world_authority_data` is relevant and it is DungeonMind World, intact on 54330);
- `.env-backup/` holds DungeonMind World dumps only;
- the `dungeonmind` database on 54329 contains no Buddy schemas.

Lost rows: the 53-run C1/C2 `ingest.run` catalog, Content work objects (including the DFC-2a adopted C2S27 plan), Play runs, and the #689-adopted C2S25 `source.artifact`/`source.revision` rows. Corpus Markdown remains safe in git; the product-loadable database rows are gone.

**Steward ruling (2026-09-07):** the transfer invariant below cannot execute — there is no source to transfer. This slice is rebriefed to **birth the durable authority empty** and prove the recovery tooling on it:

1. The durable substrate, fingerprint, backup/restore, and isolation tooling in this handoff are still exactly the right deliverables — the loss is the proof.
2. The authority is born empty at Alembic head on the durable substrate. The §7 witness becomes: birth → fingerprint → external backup → restore into a second clean target → fingerprint parity → container replacement survival.
3. Repopulating APP-STATE through the supported product seams (`import_extraction_runs_from_registry`, `bootstrap_local_play` imports, the #689 source-adoption boundary) is **reconstruction from files** — explicitly out of scope here. It becomes the Stage 2B successor, executed on the durable substrate, with its own witness.
4. "Known C1/C2 state survives the switch" (§7/§9) is void — no C1/C2 rows exist to survive. The equivalent gate moves to Stage 2B after repopulation.
5. `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` currently claims a live 53-row APP-STATE catalog at 54329. That claim is now false; this PR must record the loss event there (§4 row is no longer migration-conditional).

The original transfer design is preserved below as the standing contract for any future source-bearing migration and as the design record of what the tooling must support.

## Roadmap ruling

This is the first structural slice of **Stage 2 — Durable historical artifact authority**.

STOP 1 dogfood exposed a separate presentation defect: graph objects are reachable but no longer feel as useful as the earlier rich card experiments. That finding does **not** replace Stage 2. A separate UI/projection lane may repair graph-object usefulness in parallel under a disjoint lease.

The ordering for this period is therefore:

```text
PR #690 merge
→ Stage 2A durable Buddy APP-STATE substrate   ┐
                                               ├─ may run in parallel
→ narrow graph-object usefulness repair       ┘
→ shared human dogfood STOP
→ continue Stage 2 artifact adoption/resolution
```

Do not interpret this handoff as closing Stage 1 / STOP 1, completing all of Stage 2, or starting Stage 8 remote hosting.

## §1 Mission and merge-ready invariant

**Mission (as rebriefed in §0A):** An operator can birth a dedicated durable local Buddy APP-STATE authority on persistent storage, fingerprint every durable domain deterministically, take an external backup, restore that backup into a second clean target with identical verified state, and survive ordinary container replacement — with the tooling that a future source-bearing migration will reuse.

**Merge-ready invariant (rebriefed):** The durable Buddy APP-STATE PostgreSQL service uses persistent named/bind storage on a distinct local port; the authority born on it is fingerprinted across every durable domain (schema-at-head alone is never READY); an external custom-format backup restores into a second clean target with identical fingerprint; container replacement preserves the fingerprint; runtime continues to read exactly the configured APP-STATE DSN with no fallback; and no Buddy domain semantics, DungeonMind World authority, historical content, or lifecycle state are rewritten. Transfer of a pre-existing source database is void per §0A — there is no source.

**Original mission (superseded by §0A, preserved as the transfer contract):** An operator can move the current Buddy APP-STATE database off the ephemeral local PostgreSQL substrate onto a dedicated durable local authority and recover the same application state after container replacement and clean backup/restore.

**Merge-ready invariant:** The exact current Buddy logical database is transferred by database backup/restore—not reconstructed from corpus/files—into one explicitly configured durable PostgreSQL authority; the target survives ordinary container replacement, an external backup restores into a second clean target with the same verified domain state, runtime uses only the configured APP-STATE DSN, and no Buddy domain semantics, DungeonMind World authority, historical content, or lifecycle state are rewritten to accomplish the move.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path proves that one exact Buddy logical database remains the authority before and after storage relocation/recovery. |
| Most likely adversarial sequence | Source DB on 54329 is ephemeral → operator creates an empty durable DB → migrations make it look healthy → product silently starts against the empty DB and historical state appears lost. |
| Would §7 detect that failure? | Yes. Source fingerprint is captured before mutation; target READY requires exact domain inventory/fingerprint parity, not merely schema-at-head. |
| Easiest owning boundary to under-test | Backup→restore fidelity for mutable Play/Content state; schema readiness alone can hide lost rows. |
| What fact forces stop/split? | Source APP-STATE is unavailable or internally inconsistent; target cannot be isolated from DungeonMind; recovery requires recreating product rows from files; or verification discovers a current APP-STATE domain that cannot be fingerprinted safely. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-demo-ready-c1-c2-to-of-conks.md` Stage 2; `ARCHITECTURE-application-state-layer.md` |
| Repository rules | `AGENTS.md`; exact base/head; checked-in HANDOFF; one capability; owning-boundary evidence; no destructive source cleanup |
| Prepared base | PR #690 accepted head `01e0addbdc55eb00c0c5a0c104a718259751084d` |
| Dispatch base | Exact `main` after PR #690 merge; record before implementation |
| Predecessor contract | APP-STATE migrations through current head; `scripts/bootstrap_local_play.py`; PR #689 `source.artifact` / `source.revision`; current Ingest authority in `ingest.run` |
| Current dangerous substrate | Configured APP-STATE has been operated as `dungeonbuddy_application_state` on `127.0.0.1:54329`; that PostgreSQL server is DungeonMind's development-only `tmpfs` service and is explicitly non-durable |
| Exact input consumed | The currently configured Buddy APP-STATE logical database as observed at dispatch time; not the historical ledger as a reconstruction recipe |
| Named successor | Stage 2B: adopt/resolve remaining digest-proven historical Ingest artifacts on the durable substrate |
| Parallel lane | Graph-object usefulness recovery on UI/projection-only paths; it must not touch APP-STATE substrate/operator files in this lease |
| What remains false | Remote/VPC hosting; HA/PITR; all historical `out/` artifacts adopted; missing C1/C2 components recovered; Stage 1/2 STOPs complete |
| Explicit non-goals | No schema/domain redesign; no new Ingest artifact tables; no corpus re-ingestion; no World/DungeonMind migration; no UI work; no deletion of the old source DB/container/volume; no secret-bearing DSNs committed |

Read authoritative inputs in order:

1. `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` — Stage 2 and STOP law.
2. `Docs/Design/ARCHITECTURE-application-state-layer.md` — storage-independent identity + backup/restore law.
3. `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` — known C1/C2 APP-STATE witnesses; evidence only, never reconstruction authority.
4. `scripts/bootstrap_local_play.py` and `src/application_state/**` — existing APP-STATE configuration/migration seams.
5. DungeonMind `compose.postgres.yml` — proves port 54329's current server is tmpfs/dev-only.
6. DungeonMind's accepted durable World authority recovery pattern as operational design evidence only; do not couple the databases.

### Dispatch gate A0 — re-anchor before mutation

Before writing code or touching a database, record:

```text
DungeonMindBuddy main
PR #690 merged state + merge commit
current configured DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL coordinates (redacted)
current APP-STATE Alembic head
current DungeonMind World authority DSN coordinates (redacted; isolation witness only)
```

If PR #690 is not merged, stop. Do not implement on a speculative base.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Start local APP-STATE | Logical DB commonly lives on 54329 dev/tmpfs PostgreSQL | Dedicated Buddy APP-STATE PostgreSQL uses persistent named/bind storage and a distinct service/port | Yes | Compose/operator substrate |
| Existing runtime | Reads configured APP-STATE DSN | Same; no path/database-name fallback | Yes | APP-STATE config/runtime |
| Initial migration | Current rows exist only in source DB | `pg_dump`/`pg_restore` transfers exact logical DB into durable target | Yes | Operator CLI/runbook |
| Ordinary container replacement | 54329 tmpfs loses data | Durable target container can be removed/recreated without deleting data volume; APP-STATE remains READY | Yes | Durable PostgreSQL service |
| Backup | Not a demonstrated product recovery contract | External custom-format dump + SHA-256 + source fingerprint recorded | Yes | Operator CLI/runbook |
| Clean restore | Not currently proved | Backup restores into second clean DB and produces the same verified APP-STATE fingerprint | Yes | Recovery preflight |
| Source unavailable | Historical data can disappear with server | Fail closed; do not create/bless empty replacement authority | Yes | Recovery preflight |
| Target schema healthy but rows missing | Could look superficially READY | NOT_READY because domain fingerprint differs | Yes | Recovery preflight |

Adversarial sequences:

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Capture source → start empty target → migrate schema only | Target remains NOT_READY; cannot be designated authority | Fingerprint mismatch integration test |
| Backup source → restore target → restart/replace container | Same target fingerprint and READY after replacement | Durable restart witness |
| Backup durable target → restore second clean target | Second target fingerprint equals source durable authority | Clean restore witness |
| Environment still points at 54329 after durable target is ready | Product preflight/report makes configured coordinates visible; operator must explicitly switch DSN | Manual/runtime witness |
| Target DSN equals DungeonMind authority DB | Block before migration/restore | Isolation test |
| Source DB changes after fingerprint/backup begins | Stop and recapture; never claim a stale dump is current authority | Operator preflight generation/fingerprint check |

## §4 Files in scope — write lease

Expected focused lease:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-application-state-durable-authority-v1.md` | This implementation/review authority |
| Create | `compose.postgres.app-state.yml` | Dedicated durable local Buddy APP-STATE PostgreSQL substrate; persistent volume, distinct port/service |
| Create | `scripts/application_state_authority.py` | Supported check / fingerprint / backup / restore operator entry point |
| Create | `src/application_state/authority.py` | Testable read-only fingerprint + recovery verification logic |
| Create | `tests/application_state/test_application_state_authority.py` | Fingerprint, isolation, mismatch, redaction/unit evidence |
| Create | `tests/integration/test_application_state_authority_postgres.py` | Real PostgreSQL backup/restore/restart owning-boundary proof |
| Create | `Docs/Runbooks/RUNBOOK-application-state-authority-recovery.md` | Supported operator procedure and recovery contract |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record Stage 2A substrate as current structural lane; Stage 1 dogfood repair may run in parallel; neither STOP auto-closes |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Record current parallel-lane ownership and collision boundary |
| Modify | `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` | Record the 2026-09-07 tmpfs loss event and the durable authority coordinates abstractly; never secrets/home paths |

Bounded discovery exception:

```text
Directory: tests/application_state/ and tests/integration/
Maximum additional paths: 2
Allowed path kinds: existing tests whose only failure is an exact operator/preflight contract changed by this slice
Decision rule: add only when the new supported authority command or durable DSN posture invalidates a directly owning assertion; report the path before editing
```

Any runtime domain-service, migration, UI, DungeonMind, corpus, or graph path outside the table is a STOP/rebrief.

## §5 Explicitly out of scope / parallel collision boundary

| Path/layer | Why this slice must not touch or claim it |
|---|---|
| `src/application_state/migrations/**` | No domain/schema change is required to relocate the existing logical database |
| `src/application_state/content/**`, `play/**`, `ingest/**`, `source/**` domain semantics | Recovery verifies them; it does not redesign them |
| `apps/live-control-ui/**` | Reserved for the parallel graph-object usefulness/dogfood lane |
| `apps/live-control-ui/src/graphObjectCard/**` | Explicit parallel UI lease; no collision |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Explicit parallel recap/object interaction lease |
| `apps/live-control-ui/src/worldGraph/**` | Explicit parallel projection-adapter lease |
| DungeonMind repository / World DB | Separate authority already recovered; APP-STATE must remain isolated |
| historical `out/` component adoption | Stage 2B successor after safe substrate exists |
| new Ingest writes to artifact storage | Separate durable-domain capability |
| remote/VPC PostgreSQL, HA, PITR | Stage 8 / operational successor |
| deleting old 54329 DB/container or local backups | Destructive cleanup is not required for success and is prohibited here |

## §6 Implementation contract and matrices

### Operator contract

```text
Input:
  source APP-STATE DSN (existing configured authority)
  target APP-STATE DSN (dedicated durable local service)
  operator-selected backup path outside the repository

Output:
  source fingerprint
  verified backup SHA-256
  target fingerprint + READY/NOT_READY
  second-target clean-restore fingerprint

Invariant:
  target and restored target represent the same Buddy logical application state
  captured from the source; schema health alone is never sufficient.

Failure behavior:
  unavailable/inconsistent source → STOP, no empty authority blessing
  target overlaps DungeonMind/source DB unexpectedly → BLOCK
  backup/restore command failure → NOT_READY
  fingerprint mismatch → NOT_READY
  secret-bearing DSN → redact from output/docs

Replay:
  check/fingerprint → read-only
  repeated backup → new operator artifact, same logical fingerprint permitted
  repeated restore into clean target → same verified fingerprint
  restore into non-empty target → reject unless an explicit destructive operator mode is separately approved (not in this slice)
```

### Durable local substrate

The compose file must:

- use a deliberately pinned PostgreSQL image;
- expose a distinct local service identity and port from 54329 (DungeonMind dev) and 54330 (DungeonMind durable World authority); suggested port: **54331**;
- use a named or explicit bind volume for `/var/lib/postgresql/data`, never `tmpfs`;
- create/use the logical database `dungeonbuddy_application_state` by configuration, not as identity;
- support ordinary `down` / container replacement without deleting the volume;
- make volume deletion an explicit destructive operation outside ordinary instructions;
- state that local persistence is not remote backup/HA.

Do not add automatic migrate-on-start behavior. Existing explicit APP-STATE migration/bootstrap law remains.

### APP-STATE fingerprint

READY must compare domain state, not merely connectivity. The application seam should produce a deterministic fingerprint/inventory over the APP-STATE domains that exist at dispatch time, using domain/public repository seams where practical.

At minimum include:

```text
Alembic revision/head
Content: WorkObject/WorkRevision/WorkingCopy identity + content digest state
Play: Run + manifest + active-run identity/current mutable state
Ingest: sorted run identities + lifecycle/revision/components/lineage state
Source: artifact/revision identities + exact content SHA bindings
```

The fingerprint must include mutable current state where product trust depends on it (for example Play progress/revision), not only row counts. It must be deterministic and secret-free.

If another durable APP-STATE domain/table exists at dispatch and cannot be represented safely through current public seams, STOP and expand the lease explicitly before claiming whole-database recovery.

### A. State/fallback matrix

| State | Required behavior |
|---|---|
| Source configured + reachable + internally valid | fingerprint allowed |
| Source missing/unreachable | STOP; no target blessing |
| Target empty | restore permitted only through explicit recovery command |
| Target schema at head but fingerprint differs | NOT_READY |
| Target fingerprint matches | READY |
| Target container restarted/replaced with volume intact | same fingerprint / READY |
| Second clean target restored from backup | same fingerprint / READY |
| Any DSN equals configured DungeonMind World authority | BLOCK isolation failure |
| No durable target configured | product may remain on old source temporarily, but Stage 2A is not complete |

No fallback database is permitted. The runtime reads exactly the configured APP-STATE DSN.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback? |
|---|---|---|---|
| Buddy APP-STATE authority | DSN selects one logical DB; stable domain IDs remain product identity | Multiple candidate DBs are operator configuration, never auto-selected | No |
| Database name | `dungeonbuddy_application_state` is conventional locator metadata, not product identity | Same name on another server is not automatically same authority | No |
| Filesystem/corpus | Evidence/backup source only | Never reconstruct DB rows from it during recovery | No |
| DungeonMind DB | Must remain distinct | Same DSN/database is isolation failure | No |

### C. Persistence/replay matrix

| Operation | Durable representation | Round-trip guarantee | Replay behavior | Rollback/reversion |
|---|---|---|---|---|
| Source backup | operator-selected PostgreSQL custom-format dump + SHA-256 + fingerprint record | restore can recreate verified APP-STATE | creating another backup is safe | keep previous backup |
| Durable local authority | PostgreSQL volume + logical DB | container replacement preserves same verified state | restart/recreate container is safe | point DSN back only as explicit emergency operator action; do not automate fallback |
| Clean restore | second independent logical DB/volume | fingerprint equals source authority | repeated into a new clean target is safe | discard scratch target only after proof |

### D. Predecessor-to-consumer mapping

| Predecessor field/outcome | Real shape | Recovery use | Proof |
|---|---|---|---|
| `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` | one PostgreSQL DSN | sole runtime APP-STATE locator | isolation/config tests |
| Alembic APP-STATE head | explicit revision | target must be at compatible/current head after restore | authority check |
| `ingest.run` | canonical APP-STATE ExtractionRun rows | fingerprint exact current run state | migration witness |
| `source.artifact` / `source.revision` | immutable source identity + exact SHA/content | prove #689 adopted source survives migration | C2S25 witness |
| Content/Play APP-STATE rows | current durable product state | prove migration does not only preserve Ingest | integration fingerprint |
| 54329 dev PostgreSQL | DungeonMind compose declares tmpfs/dev-only | source to escape, never target durability | runbook/preflight |

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Target is physically durable | compose/PostgreSQL | integration/manual | start target → fingerprint → remove/recreate container without volume deletion → check | same fingerprint / READY | state lost |
| Source is not silently replaced by empty DB | recovery application | adversarial | source fingerprint vs schema-only empty target | NOT_READY | empty target READY |
| Backup is usable | CLI/PostgreSQL | integration/manual | `backup` then restore to clean target | backup SHA recorded; restore succeeds | dump/restore error |
| Restore preserves whole APP-STATE semantics | authority fingerprint | integration | source vs first target vs second target | same deterministic fingerprint | any domain mismatch |
| World isolation preserved | authority CLI | contract | pass World authority DSN as target | BLOCK | operation proceeds |
| Secrets not leaked | CLI/docs | regression | DSN with password | output redacted | secret appears |
| Known C1/C2 state survives | real operator DB | manual/dogfood | VOID per §0A — no C1/C2 rows exist; repopulation witness moves to Stage 2B | n/a | n/a |
| Existing product still runs | assembled Buddy | manual | point runtime at durable DSN, run existing APP-STATE preflight and open Ingest/Plan/Play | normal reads succeed | hidden dependency on 54329 |

Required automated commands, adjusted only for repository-standard markers:

```bash
uv run pytest -q \
  tests/application_state/test_application_state_authority.py \
  tests/integration/test_application_state_authority_postgres.py

uv run pytest -q tests/application_state/test_local_play_bootstrap.py
uv run ruff check scripts/application_state_authority.py src/application_state/authority.py \
  tests/application_state/test_application_state_authority.py \
  tests/integration/test_application_state_authority_postgres.py

git diff --check
git diff --name-only <post-#690-main>...HEAD
```

### Required real authority-birth witness (rebriefed per §0A)

Do not merge on synthetic tests alone.

1. Start the durable APP-STATE service on the distinct local port with its persistent volume.
2. Birth the authority: create the logical database and run explicit migrations to head (no migrate-on-start).
3. Fingerprint the birthed authority; record it.
4. Take an external custom-format backup; record SHA-256.
5. Restore the backup into a **second clean target** (second logical database); require fingerprint parity → READY.
6. Demonstrate the adversarial gate: a schema-only empty target compared against a populated authority is NOT_READY (covered by integration test; note it in the handback).
7. Remove/recreate the durable database container without deleting the volume; require the same fingerprint.
8. Demonstrate isolation: passing the DungeonMind World authority DSN as a target is BLOCKed.
9. Keep all targets and backups intact. No cleanup of old containers/volumes in this PR.

The original transfer witness (fingerprint configured source → dump → restore → C1/C2 survival) is void per §0A; its equivalent runs in Stage 2B after repopulation.

Record redacted coordinates, exact commits, dump SHAs, and fingerprints in the handback/runbook. Do not commit dump bytes.

### Original required real migration witness (superseded by §0A, preserved for future source-bearing migration)

1. Fingerprint the currently configured APP-STATE source before mutation.
2. Create an external source backup and record SHA-256.
3. Start the durable APP-STATE service on the distinct local port.
4. Restore into a clean durable target and run migrations only as required by supported restore/bootstrap semantics.
5. Require target fingerprint == source fingerprint.
6. Point Buddy at the durable target and prove existing C1/C2 Ingest catalog plus the already-adopted C2S25 source still resolve.
7. Remove/recreate the durable database container without deleting the volume; require the same fingerprint.
8. Back up the durable target to a new external dump with SHA-256.
9. Restore that dump into a **second clean target** and require the same fingerprint.
10. Keep the original/source DB and backups intact. No cleanup in this PR.

### Minimal human dogfood proof

After the operator switches the runtime DSN to the durable authority (Stage 2B repopulates content first):

```text
Open DungeonBuddy normally.
Confirm the APP-STATE preflight reports the durable coordinates (redacted).
Open Ingest/Plan/Play enough to prove the birthed authority serves reads.
Restart the Buddy API and repeat the read.
```

The C1/C2 catalog and C2S25 recap return only after Stage 2B repopulation; their absence at this stage is expected, not a failure of this PR. The graph-object card may still be visually thin; that is the parallel dogfood lane, not a failure of this durability PR.

## §8 Required review handback

Record:

1. Exact post-#690 base SHA (`08c4052e3e662d94936c37cf8837cdb01a9507ca`) and reviewed head SHA.
2. §1 mission/invariant verbatim, including the §0A rebrief.
3. Actual changed paths against §4.
4. Nano-commit story.
5. §0A loss event confirmation (source unavailable; no backup; no volume).
6. Birthed authority redacted coordinates + fingerprint.
7. Container replacement witness + same fingerprint.
8. Authority backup SHA-256.
9. Second clean restore fingerprint parity.
10. Isolation proof against DungeonMind World authority.
11. Every automated command and exact result/provenance.
12. Baseline failures/waivers (`none` when none).
13. Paths outside lease (`none` or STOP report).
14. What remains false: remote hosting, APP-STATE repopulation (Stage 2B), artifact batch adoption, graph-object usefulness, Stage 1/2 STOP completion.

## §9 Acceptance rubric

- [ ] Dedicated Buddy APP-STATE service is persistent and isolated from both DungeonMind PostgreSQL services.
- [ ] §0A loss event is recorded in the material library; no false live-catalog claim remains.
- [ ] Target cannot be READY on schema health alone.
- [ ] Deterministic fingerprint covers every current durable APP-STATE domain or implementation stopped for explicit lease expansion.
- [ ] Birthed authority fingerprint is stable across repeated computation.
- [ ] External backup restores to a second clean target with the same fingerprint.
- [ ] Ordinary container replacement preserves target fingerprint.
- [ ] Runtime uses the durable target via the existing APP-STATE DSN contract, with no fallback database.
- [ ] No source/corpus re-ingestion, lifecycle rewrite, DungeonMind mutation, UI work, or destructive old-authority cleanup occurred.
- [ ] Parallel graph-object usefulness work remains disjoint and unclaimed.
- [ ] Stage 2B repopulation, Stage 2 artifact adoption, and Stage 8 remote hosting remain explicitly incomplete.

## Stop conditions

Stop and report instead of expanding if:

- PR #690 is not merged or the implementation base cannot be re-anchored cleanly;
- the currently configured APP-STATE source is unavailable or fails domain integrity checks;
- source and target fingerprint semantics cannot cover an existing durable APP-STATE domain;
- a restore requires recreating rows from filesystem/corpus material;
- the target overlaps DungeonMind authority;
- a schema/domain migration becomes necessary merely to relocate the database;
- large/binary asset storage or object-store design becomes necessary;
- the parallel graph-object UI lane requires a path in this lease;
- backup or second-target restore cannot be proved before merge;
- any destructive cleanup of the old DB/volume is proposed.

```text
STOP_REASON = <stable reason>
Source authority fingerprint:
Target state:
Invariant clause affected:
Evidence missing:
Required lease/architecture change:
Proposed successor or rebrief:
```
