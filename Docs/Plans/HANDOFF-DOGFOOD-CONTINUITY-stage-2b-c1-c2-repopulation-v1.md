---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DEMO-R2 Stage 2B
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE/OPERATOR RECOVERY → REVIEW → DOGFOOD STOP
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v1.md
  - Branch: dogfood-continuity/stage-2b-c1-c2-repopulation-v1

  ## Verification pointer
  - Prepared from post-#691 main: 35269f087cf1dcee52f169f339d1de79599b3374
  - Predecessor: PR #691 / Stage 2A durable APP-STATE authority
  - Verification: §7 exact repopulation + assembled Buddy↔World witness + post-repopulation recovery proof

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and real 54331/54330 witness are the review contract.
  The PR description is transport metadata only.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 2B exact C1/C2 repopulation v1

**Created:** 2026-09-07  
**Status:** READY TO DISPATCH — Stage 2A is DONE; Stage 2 / STOP 2 remain OPEN  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / DEMO-R2 Stage 2B`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE/OPERATOR RECOVERY → REVIEW → DOGFOOD STOP  
**Prepared base:** `35269f087cf1dcee52f169f339d1de79599b3374` — `main` after merged PR #691  
**Suggested PR title:** `DOGFOOD-CONTINUITY: repopulate durable C1/C2 application state`  
**Suggested implementation branch:** `dogfood-continuity/stage-2b-c1-c2-repopulation-v1`  

> Repository law: `AGENTS.md`. Product sequence: `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`. Buddy persistence authority: `Docs/Design/ARCHITECTURE-application-state-layer.md`. World/graph authority: `Docs/Design/ARCHITECTURE-campaign-supergraph.md`. Recovery locator: `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`.

---

## §0 Steward ruling — what Stage 2B is, and what it is not

PR #691 is merged:

```text
PR #691                         MERGED
accepted exact head             b0114501ac1a9a10d58e01a51f8979823d59b7fd
merge commit                    35269f087cf1dcee52f169f339d1de79599b3374
formal review cycles            2
Stage 2A                        DONE
Stage 2 / STOP 2                OPEN
Stage 2B                        NEXT / this handoff
```

Stage 2A has also passed a real human-operated durability drill on the durable Buddy APP-STATE authority (`127.0.0.1:54331`):

- recognizable Plan `Durability Witness — Delete Me Later` survived PostgreSQL container replacement;
- a real host reboot (`2026-09-07 18:49` local) preserved the same named-volume state;
- destroying `dungeonbuddy_app_state_data` was real, and external backup/restore recovered the same Plan `document_id`;
- the post-seed fingerprint was `57e74f3f…`;
- the disaster-recovery backup SHA-256 was `49f7260a98838d8189b071239e0c1d39a7979c4b491118693c856c4a7afad08a`;
- DungeonMind World authority on `54330` remained down throughout that reboot drill.

The standing persistence standard is therefore:

> Persistence is not proven by choosing a persistent substrate. It is proven by recognizable product state surviving process and host lifecycle, then surviving deliberate storage destruction through an independently verified backup/restore that recreates the same product identity.

### §0A Predecessor authority-sync transfer gate

The Stage 2A drill closure was intentionally kept as a local, uncommitted steward authority set after #691 merged. Do **not** open a routine docs-only PR for it. Per `AGENTS.md`, the Stage 2B implementation PR consumes that predecessor and must carry the backward-looking sync in its first implementation commit.

The exact predecessor sync set is:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-application-state-durable-authority-v1.md
Docs/Reports/REPORT-application-state-durability-drill.md
Docs/Design/ARCHITECTURE-application-state-layer.md
Docs/Runbooks/RUNBOOK-application-state-authority-recovery.md
```

The steward checkout also contains an uncommitted drill pickup that is explicitly **PASSED / not a Stage 2B dispatch**. It is not part of this PR. Unrelated corpus edits are also not part of this PR.

Before implementation:

1. locate the exact local Stage 2A closure set;
2. transfer/reconcile only those six authority/report paths into this lane;
3. preserve their real drill facts exactly;
4. do not recreate them from memory if the source edits are unavailable — STOP and transfer from the steward checkout;
5. do not include the drill pickup or unrelated corpus files.

### §0B The two durable authorities must remain separate

Stage 2B restores **Buddy continuity**, not the World Graph.

```text
DungeonMind World authority — 127.0.0.1:54330
  one Eldyrwild World Supergraph
  world-global identity + setting/world canon
  campaign-scoped played assertions/evidence/chronology
  graph revisions + graph head

                ↓ controlled read/projection contract

DungeonBuddy APP-STATE — 127.0.0.1:54331
  source.artifact / source.revision exact prose bytes
  ingest.run identity + lifecycle
  Plan / Runbook / Play application state
  bindings/context needed to request the correct World projection
```

Architecturally there are not separate durable C1 and C2 graph stores. Eldyrwild has one World Supergraph. Campaign is scope on assertions/evidence/chronology/visibility. Worldbuilding is a source domain contributing world-global or otherwise governed World truth; played recaps contribute campaign-scoped truth. Stage 2B must not copy World objects into Buddy or rebuild campaign graph state from recap files.

**Hard boundary:** every Stage 2B graph/World operation is read-only. If Stage 2B requires a DungeonMind graph write, contribution replay, re-ingestion, graph-head advancement, or Buddy-owned graph persistence, STOP and rebrief.

---

## §1 Mission and merge-ready invariant

**Mission:** Re-establish the exact previously accepted C1/C2 Buddy-side continuity set on the now-proven durable APP-STATE authority, then prove that restored Buddy state rejoins the already-durable DungeonMind World authority through the controlled read contract.

**Merge-ready invariant:**

> From the durable `54331` authority, an operator can preserve the current pre-Stage-2B state with a verified backup, re-adopt the exact 53 historical C1/C2 `ingest.run` identities, the one proven exact C2 Session 27 Plan, and the previously accepted exact C2 Session 25 recap source without generating identity or rewriting content; the ordinary Buddy product can then list the recovered history, open the exact Plan, read the exact C2S25 recap, and project/click current World objects through the unchanged `54330` World head; a post-repopulation external backup restores into a second clean target with identical APP-STATE fingerprint; replay is idempotent; the non-canon durability-witness Plan is preserved rather than deleted; no historical source root is mutated; and no ingestion or World/graph write occurs.

This is one capability: **exact repopulation of the lost Buddy continuity set onto the durable authority plus proof of the restored Buddy↔World join**.

It is not “finish Stage 2.” Historical candidate graphs, span indexes, validation/provenance bundles, all recap sources, Build recovery, and remote storage remain subsequent Stage 2 work.

### Pre-dispatch critique

| Question | Ruling |
| --- | --- |
| Can one invariant govern the whole PR? | Yes. Every write restores a previously accepted Buddy-side identity/byte binding lost with `54329`; every World operation proves the restored state can address the unchanged graph authority. |
| Most likely adversarial sequence | We restore the 53 run rows, then silently regenerate Plan/source identity or use recap files to rebuild graph truth, creating a product that looks recovered while changing authority semantics. |
| What catches it? | Exact target IDs/digests, source revision identity assertion, pre/post APP-STATE fingerprints, historical-root immutability, and unchanged World-head witness. |
| Easiest boundary to under-test | The assembled join. “53 rows exist” is not enough unless `/ingest` opens the exact recap from APP-STATE and its pills resolve through current DungeonMind World. |
| What forces a split? | Any target needs guessed identity/content, any accepted Plan/Ingest importer must be redesigned, the C2S25 source cannot be restored without weakening exactness, World head changed unexpectedly, or graph mutation is required. |

---

## §2 Exact target set and authority

### 2.1 Buddy APP-STATE authority — `54331`

The operator target is the durable logical database configured by `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` on the dedicated Buddy PostgreSQL service. Do not infer the target from port alone; verify the configured redacted coordinates and database name before writes.

The durability-witness Plan already present on `54331` is **not campaign canon**. It is not part of the Stage 2B recovery set, but it is legitimate existing application state and must survive Stage 2B unchanged. Plan currently has no supported archive/delete operation, so this PR must not invent one merely to clean the witness up.

### 2.2 Historical Ingest target — exact 53-run set

Recovery authority is the existing accepted DFC-2c path:

```text
admitted historical GraphIngestRunManifest evidence
  → accepted adapter
  → canonical ExtractionRun
  → scripts/adopt_historical_ingest_runs.py
  → existing one-transaction importer
  → APP-STATE ingest.run
```

Required final set:

```text
historical ingest.run identities        53
longmont-c1                             24
longmont-c2                             29
validated                               36
prepared                                17
reviewable                               0
sorted run_id identity SHA-256          59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1
```

Do not select runs by title/session/latest/path/timestamp. Use the accepted `--all-historical-ingest` preview against explicit admitted roots and require the preview target-set handshake before apply.

### 2.3 Historical Plan target — exact one recoverable document

Re-adopt only the one Plan that DFC-2a proved had admitted bytes:

```text
document_id      80630cc2-33ee-40db-bf9d-fb5217085e17
title            C2 Session 27 Prep
revision         2
bytes            2631
content sha256   d8a8595d5211d00a57731354ea06bce25aa6236332b66dece59870ed9d77a511
```

Use `scripts/adopt_historical_plans.py` against the explicit `primary-checkout` historical root. The four historical Plan identities whose target bytes were absent remain absent. Do not recreate blank shells.

### 2.4 Historical recap source target — exact C2 Session 25 source

Re-establish the source authority that PR #689 had already proven before the tmpfs loss:

```text
run_id               graph-ingest:longmont-c2:session-25:20260808T005650Z
run lifecycle        validated
source_artifact_id    artifact:recap:longmont-c2:session-25:fd38b5915b32
source_revision_id    8ed1e034-23c6-4295-b2ff-05d5cdd643a9
content sha256        fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
world_id              eldyrwild
source domain          recap
```

The stable source recovery identity for this already-adopted record is not merely “same prose.” Because the prior `source_revision_id` is recorded, Stage 2B should restore that exact revision UUID rather than silently generate a new surrogate identity.

The underlying `persist_source_markdown()` service already accepts an optional `source_revision_id`; the current one-time source-adoption operator boundary does not expose/assert it. This PR may extend only that narrow seam so explicit recovery can preserve the known revision identity.

Required semantics when an exact `source_revision_id` is supplied:

- absent artifact/digest → insert with that exact revision UUID after all existing digest/scope checks;
- same artifact/digest + same revision UUID → truthful no-op;
- same artifact/digest + different revision UUID → conflict/block, never silently accept the different current identity;
- supplied revision UUID already belongs to different source state → conflict/block;
- malformed UUID → input failure before write.

A validation-only / dry-run mode must be available at the operator boundary so this real recovery can be preflighted before mutation. Preserve the existing write behavior for callers that do not request dry-run; do not turn runtime reads into filesystem fallback.

### 2.5 DungeonMind World authority — `54330` read-only witness

Stage 2B does not repopulate DungeonMind. The accepted recovery baseline was:

```text
world             eldyrwild
accepted head     rev:680c246047d67f9fe0293ee90526f670
parent            rev:34b1f8e2625d5ba693fc726a2a1a4720
objects           469 at accepted recovery witness
contributions     95 at accepted recovery witness
```

At Stage 2B A0, start/read the accepted durable World authority using its own runbook and record its **current** head. Because `54330` remained down through the Stage 2A reboot drill and Stage 2B performs no World writes, the accepted head above is the expected baseline. If the current head differs, do not assume corruption and do not overwrite anything: STOP and determine whether a legitimate World advancement occurred before continuing the assembled witness.

The required assembled witness is C2 Session 25:

```text
Buddy ingest.run + source.revision on 54331
  → historical recap projection
  → DungeonMind world=eldyrwild / campaign=longmont-c2 / focus=session-25
  → current immutable World snapshot
  → canonical pill/object identity (Orik is the accepted prior witness)
```

Record the World snapshot/head used by the request and prove it is still the current head. The World head before and after Stage 2B must be identical unless a separately authorized World write occurred outside this lane.

---

## §3 Observable paths and adversarial sequences

| Path | Current state after #691 | Required Stage 2B result | Owning boundary |
| --- | --- | --- | --- |
| Stage 2A predecessor truth | Real drill closure exists only as local steward edits | First implementation commit transfers exactly the six-file backward sync; no pickup/corpus leakage | Repository authority |
| Pre-recovery Buddy state | Durable `54331` contains the non-canon durability witness but lost C1/C2 APP-STATE | Capture exact fingerprint + external backup before any Stage 2B write | APP-STATE authority tooling |
| Ingest history | 53 accepted historical identities absent after tmpfs loss | Preview exact 53, target-set handshake, apply exact 53, replay no-op | DFC ingest adoption → `ingest.run` |
| Historical Plan | C2S27 exact WorkObject/revision lost | Re-adopt `80630…5e17`; existing durability witness remains untouched | DFC Plan adoption → Content APP-STATE |
| C2S25 recap source | #689 source rows lost | Dry-run exact bytes/digest/scope/revision UUID; apply exact old source revision; replay no-op | source adoption → `source.artifact/revision` |
| Ingest product catalog | Stage 1 history selector lost its APP-STATE catalog | Ordinary `/ingest` history exposes exact C1/C2 runs again | product API/UI |
| Plan product | only current non-canon witness is guaranteed | Plan chooser opens exact C2S27 historical Plan with same document ID/revision/content | product API/UI |
| Historical recap reading | C2S25 durable source missing | C2S25 loads from APP-STATE source bytes, not runtime filesystem | historical inspection route |
| World join | World authority exists separately and was down during Stage 2A drill | Bring `54330` up read-only; C2S25 projection resolves current World snapshot and object pill/card | DungeonMind controlled read contract |
| Post-recovery durability | Stage 2A proved substrate only with witness state | Back up repopulated `54331`, restore into a second clean target, require identical APP-STATE fingerprint | authority backup/restore |
| Restart/reload | reconstructed state not yet tested | API restart + hard reload preserve catalog, Plan, recap source, and World join | assembled product |

### Required adversarial sequences

| Sequence | Safe outcome |
| --- | --- |
| 53-run preview → historical manifest changes before apply | target-set/observation handshake blocks; zero new run writes from the stale preview |
| one same `run_id` already exists with conflicting durable payload | existing importer blocks; do not overwrite or regenerate |
| selected C2S27 Plan bytes missing/different | Plan adoption blocks; do not create blank shell or infer content |
| C2S25 recap file differs from recorded digest | source adoption blocks; do not re-ingest or normalize/repair prose |
| C2S25 exact artifact/digest exists under a different source revision UUID | block and report; do not silently relabel it as the historical revision |
| source revision UUID collides with different source state | block before/at owning persistence boundary; no overwrite |
| a later recovery step fails after earlier exact imports committed | report truthful partial state; do not destructively roll back good exact rows; repair/replay idempotently after the blocker is resolved |
| `54330` unavailable | Buddy repopulation state may remain safely committed, but Stage 2B is not merge-ready until the assembled World witness succeeds |
| World head differs unexpectedly from accepted baseline | STOP before claiming the join; determine whether a legitimate World advancement occurred; never reset World from Buddy |
| post-repopulation backup clean-restore fingerprint differs | NOT_READY; Stage 2B cannot merge |
| operator notices `Durability Witness — Delete Me Later` | preserve it; do not invent Plan deletion/archive in this PR |

### Transaction / replay ruling

The three accepted adoption seams do not need to be redesigned into one cross-domain SQL transaction. Stage 2B is **serialized and idempotently resumable**:

1. all target domains are previewed/preflighted before the first product write;
2. pre-recovery APP-STATE is externally backed up;
3. Ingest, Plan, then Source are applied through their owning exact seams;
4. each successful exact write is durable and replay-safe;
5. if a later domain blocks, keep the earlier exact state and report the partial truth;
6. merge readiness requires the complete final target set plus the assembled/recovery witnesses.

Do not add a generic multi-domain migration framework merely to manufacture all-or-nothing semantics for this one recovery event.

---

## §4 Files in scope — write lease

Expected cumulative Stage 2B lease:

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v1.md` | This implementation/review authority |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Consume Stage 2A closure; make Stage 2B current; keep Stage 2 / STOP 2 open |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Consume Stage 2A closure and name Stage 2B as current forcing function |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-application-state-durable-authority-v1.md` | Backward-only Stage 2A DONE/merge/drill sync |
| Create/transfer | `Docs/Reports/REPORT-application-state-durability-drill.md` | Exact human Stage 2A container/reboot/destructive-restore witness |
| Modify | `Docs/Design/ARCHITECTURE-application-state-layer.md` | Transfer the already-approved Stage 2A persistence-proof standard only; no new Stage 2B architecture invention |
| Modify | `Docs/Runbooks/RUNBOOK-application-state-authority-recovery.md` | Transfer the already-approved Stage 2A operating-law §8 durability standard only |
| Modify | `apps/live_control_server/services/historical_recap_source_adoption.py` | Explicit source revision UUID assertion + dry-run preflight for exact recovery |
| Modify | `src/application_state/source/service.py` | Honor a supplied exact source revision identity on idempotent replay/conflict instead of silently returning a different revision UUID |
| Modify | `tests/test_historical_recap_source_adoption.py` | Dry-run, exact revision restore, replay, malformed/conflict evidence |
| Modify | `tests/application_state/test_source_content_postgres.py` | Owning persistence proof for supplied source revision identity semantics |
| Create | `Docs/Reports/REPORT-stage-2b-c1-c2-repopulation.md` | Sanitized real 54331 repopulation + 54330 read-only join + post-recovery restore witness |
| Modify | `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` | Replace lost/live historical claims with actual post-Stage-2B locators/status where proven |

The first six mutable authority/report paths above are the pre-existing local Stage 2A closure set. Transfer them exactly; Stage 2B does not get to rewrite the drill narrative.

### Bounded discovery exception

```text
Directory: tests/
Maximum additional paths: 2
Allowed path kinds:
  - existing source-adoption/source-authority test needed to prove exact revision identity
  - existing product-continuity test needed only to re-run/strengthen a directly owning Stage 2B postcondition
Decision rule:
  test-only unless the handoff assumption about an existing accepted seam is false.
```

If Stage 2B requires modifying these production areas, STOP/rebrief before editing:

```text
src/product_continuity/ingest_adoption.py
scripts/adopt_historical_ingest_runs.py
src/product_continuity/plan_adoption.py
scripts/adopt_historical_plans.py
src/application_state/content/import_plans.py
src/application_state/ingest/**
src/application_state/migrations/**
DungeonMind repository code
apps/live-control-ui/**
```

Those are predecessor or parallel authorities, not convenience edit surfaces for this recovery.

---

## §5 Explicit non-goals / collision boundary

| Area | Stage 2B ruling |
| --- | --- |
| DungeonMind World graph writes | **Forbidden.** Read/projection witness only. |
| Re-ingestion / LLM extraction | **Forbidden.** Exact surviving evidence only. |
| Candidate graph / span index / validation / provenance bundle adoption | Later Stage 2 artifact-authority work after the human checkpoint. |
| Bulk adoption of all 53 recap source bytes | Not this PR. Re-establish the previously proven C2S25 source only. |
| C1S10 / C2S23 / additional rich recap durable sources | Not automatically included. These are the next Stage 2 source/artifact adoption targets after the checkpoint. |
| Build recovery | Separate evidence/adapter work. |
| Runbook / historical Play recovery | No admitted C1/C2 historical authority to fabricate. |
| Durability-witness Plan deletion | No supported Plan lifecycle operation exists; preserve it. |
| Graph-object usefulness repair | Parallel UI/projection lane; no overlap with this lease. |
| Threat/statblock redesign | Stage 4/product interaction work. |
| Persistent shell / navigation | Stage 5. |
| Remote/VPC hosting, HA, PITR | Stage 8. |

### Parallel lane rule

A graph-object usefulness PR may proceed in parallel on disjoint UI/projection paths. It must not edit the roadmap/Stewards anchor while Stage 2B owns those authority paths without an explicit serialization/transfer decision. Stage 2B must not touch `apps/live-control-ui/**` merely to make its dogfood screenshot prettier.

---

## §6 Implementation / operator contract

### 6.1 A0 — re-anchor and transfer predecessor truth

Before code or product writes, record:

```text
Buddy main SHA                          35269f087cf1dcee52f169f339d1de79599b3374 or later legitimate main
PR #691 merged state + merge SHA
Stage 2A local closure-set source status
configured APP-STATE DSN coordinates   redacted
APP-STATE schema head
current APP-STATE fingerprint
current durable World DSN coordinates  redacted
current World head
historical roots supplied              labels only
```

If `main` advanced after this handoff was authored, re-anchor and determine whether the diff affects this lease before continuing.

Transfer the exact local Stage 2A closure set as the first implementation commit. Do not mark Stage 2B DONE.

### 6.2 Protect the current durable Buddy authority before recovery

Before the first Stage 2B write:

1. fingerprint `54331` and save the fingerprint outside committed source;
2. take an external custom-format backup with SHA-256 + fingerprint sidecars;
3. record that the durability-witness Plan is present and its `document_id`;
4. do not delete/reset/empty the database to make repopulation easier.

If the backup cannot be independently verified, STOP. Valuable repopulation does not begin without a rollback/recovery artifact.

### 6.3 Preflight all three target domains

**Ingest**

Run accepted exact preview against explicit historical roots. Require:

```text
selected_count = 53
identity digest = 59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1
blocked = false
all selected dispositions ∈ {RECOVERABLE_EXACT/adopt, CURRENT_EXACT/noop}
```

Record the preview `target_set_sha256`.

**Plan**

Preview exactly:

```text
80630cc2-33ee-40db-bf9d-fb5217085e17
```

Require `RECOVERABLE_EXACT/adopt` or an already-current exact no-op with the same revision/content SHA. The non-canon durability-witness Plan is outside the selected set and must remain untouched.

**Source**

Dry-run the exact C2S25 source with:

```text
run_id              graph-ingest:longmont-c2:session-25:20260808T005650Z
world_id             eldyrwild
source_revision_id   8ed1e034-23c6-4295-b2ff-05d5cdd643a9
```

Require the exact recorded source artifact ID and SHA-256 before apply.

If any domain blocks, perform zero *new* Stage 2B writes until the blocker is understood. If an earlier exact write already happened because the failure appeared later than preflight, preserve/report it and resume idempotently after correction; do not destructively roll it back.

### 6.4 Apply in deterministic order

Apply in this order:

```text
1. 53 Ingest identities
2. exact C2S27 Plan
3. exact C2S25 source revision
```

Why this order:

- the source-adoption boundary resolves an exact `ingest.run` record;
- restoring Ingest first makes the source write address the canonical product identity;
- Plan is independent but belongs before assembled source/World dogfood;
- Source is last product write before the assembled projection witness.

### 6.5 Replay immediately

Re-run all three exact recovery commands after apply.

Required result:

```text
Ingest   CURRENT_EXACT/noop for all 53
Plan     CURRENT_EXACT/noop for 80630…5e17
Source   exact same artifact/digest/revision UUID; no duplicate revision
```

Any revision churn or duplicate row on replay is a merge blocker.

### 6.6 Verify product state on `54331`

Prove through owning product seams, not direct SQL alone:

**Ingest**

- normal catalog contains the exact 53 historical run IDs;
- counts are C1=24 / C2=29;
- lifecycle counts are validated=36 / prepared=17 / reviewable=0;
- selected C2S25 run has the expected stable run/source identity.

**Plan**

- Plan chooser/list includes `80630cc2-…` / `C2 Session 27 Prep`;
- opening it returns revision 2, 2631 bytes, exact SHA `d8a8595…a511`;
- the durability-witness Plan still exists separately and is not presented as campaign canon by this recovery.

**Source / recap**

- C2S25 historical inspection resolves APP-STATE `source.revision`, not filesystem bytes;
- `source_revision_id` is exactly `8ed1e034-23c6-4295-b2ff-05d5cdd643a9`;
- content SHA is exactly `fd38b591…26d0d`.

Restart the Buddy API and hard reload the UI; repeat the representative checks.

### 6.7 Rejoin the durable World authority

Bring up/read `54330` using the accepted DungeonMind authority procedure. Record the current `eldyrwild` graph head before the assembled request.

From the normal C2S25 historical recap experience:

1. load the exact restored `graph-ingest:longmont-c2:session-25:20260808T005650Z` run;
2. render the exact APP-STATE recap prose;
3. require World status healthy/Ready;
4. record projection `world_id`, `campaign_id`, focus/session, snapshot/head, and `isHead`;
5. click at least one canonical graph pill; **Orik** is the known accepted prior witness if still present in the current projection;
6. open the shared graph object card;
7. verify the request used the current durable World snapshot rather than a candidate graph or ingest-run-local graph;
8. re-read World head after the witness and require no Stage 2B advancement/mutation.

If World is unavailable, the Buddy recovery rows remain legitimate durable state, but the PR remains **not merge-ready** because Stage 2B must prove the two recovered durability spines actually rejoin.

### 6.8 Protect the newly valuable repopulated state

After all Stage 2B writes and assembled product checks:

1. fingerprint primary `54331`;
2. take a new external custom-format backup and record SHA-256;
3. create a second clean APP-STATE logical database target;
4. restore the new backup using SHA verification + trusted fingerprint parity;
5. require identical complete APP-STATE fingerprint;
6. verify at least the target-set identities on the restored target through application-state services/tests;
7. do not delete the witness database or backup as part of this PR unless the user explicitly authorizes destructive cleanup.

This is the Stage 2B application of the Stage 2A persistence standard: recognizable real campaign state must itself be demonstrably recoverable before we pile more historical bytes onto the authority.

---

## §7 Required evidence

### 7.1 Automated evidence on exact PR head

At minimum rerun:

```bash
uv run pytest -q \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/product_continuity/test_ingest_adoption_postgres.py \
  tests/product_continuity/test_plan_adoption_postgres.py \
  tests/test_historical_recap_world_projection.py \
  tests/test_graph_run_registry.py \
  tests/application_state/test_application_state_authority.py \
  tests/integration/test_application_state_authority_postgres.py

pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx

uv run ruff check \
  apps/live_control_server/services/historical_recap_source_adoption.py \
  src/application_state/source/service.py \
  tests/test_historical_recap_source_adoption.py \
  tests/application_state/test_source_content_postgres.py
```

If a named test path has moved legitimately on current `main`, use the owning successor path and report the substitution. Do not silently drop the owning boundary.

### 7.2 Real operator evidence — mandatory

The PR report must record, sanitized:

**Pre-state**

- exact Buddy base/head;
- redacted `54331` coordinates;
- pre-Stage2B APP-STATE fingerprint;
- pre-Stage2B backup SHA-256;
- durability-witness Plan ID/presence;
- redacted `54330` coordinates and current World head.

**Ingest**

- preview selected count;
- preview target-set SHA;
- applied/imported/no-op/conflict counts;
- final 53-run identity digest;
- C1/C2 and lifecycle counts;
- replay no-op.

**Plan**

- exact selected document ID;
- title/revision/bytes/SHA;
- apply disposition;
- replay no-op;
- durability-witness Plan preserved.

**Source**

- exact C2S25 run ID;
- source artifact ID;
- exact source revision UUID;
- exact content SHA;
- dry-run result;
- apply result;
- replay no-op.

**Assembled Buddy↔World**

- C2S25 product route/session/run;
- APP-STATE source revision loaded;
- World projection campaign/focus;
- World snapshot/head + `isHead`;
- pill/object witness (Orik preferred if current);
- World head unchanged after the request;
- no candidate graph used as product authority.

**Post-state durability**

- primary post-Stage2B fingerprint;
- new backup SHA-256;
- second-clean-target restore READY;
- identical fingerprint;
- representative target identities verified on restored target.

### 7.3 Human observable outcome

A human should be able to see, without knowing IDs/paths:

```text
Ingest history is back
  → old C1/C2 sessions/runs are visible again

Plan history is back
  → C2 Session 27 Prep opens with the exact old prose

C2 Session 25 recap is back
  → exact recap prose opens from durable Buddy state
  → graph pills resolve through the current Eldyrwild World
  → clicking Orik opens the current World object
```

The non-canon durability witness may remain visible in Plan because Plan has no supported management/delete capability. Its presence is not a Stage 2B failure; treating it as campaign canon would be.

---

## §8 Handback contract

The implementation handback must include:

1. exact base and exact PR head SHA;
2. cumulative changed-path list vs §4;
3. nano-commit story;
4. Stage 2A predecessor-sync transfer provenance and confirmation that drill pickup/unrelated corpus files were excluded;
5. every automated command + exact result;
6. pre-Stage2B APP-STATE fingerprint + backup SHA;
7. 53-run target-set SHA, identity digest, counts, apply/replay results;
8. exact Plan ID/revision/content SHA + replay result;
9. exact source artifact/revision/content SHA + dry-run/apply/replay result;
10. World head before/after and assembled projection/object witness;
11. post-Stage2B APP-STATE fingerprint + backup SHA + clean-restore parity;
12. runtime restart/hard-reload observations;
13. historical-root unchanged evidence;
14. paths outside lease (`none` or STOP report);
15. baseline failures/waivers (`none` when none);
16. what remains false after merge.

Do not put secrets, absolute home paths, or dump bytes in committed reports.

---

## §9 Acceptance rubric

- [ ] Exact post-#691 `main` re-anchor recorded.
- [ ] Exact six-file Stage 2A local closure set transferred as backward-looking predecessor sync; pickup/corpus leakage absent.
- [ ] Stage 2A is recorded DONE; Stage 2 and STOP 2 remain OPEN; Stage 2B is not pre-marked DONE before merge.
- [ ] Pre-recovery `54331` fingerprint + independently verified external backup exist.
- [ ] Existing durability-witness Plan survives Stage 2B unchanged.
- [ ] Exactly 53 historical Ingest identities are current in APP-STATE with identity digest `59508725…f5f1`, C1=24, C2=29, validated=36, prepared=17, reviewable=0.
- [ ] Exact C2S27 Plan `80630cc2-…5e17` is current with revision 2 and SHA `d8a8595d…a511`; no byte-less sibling Plan is fabricated.
- [ ] Exact C2S25 source artifact/digest is restored with source revision UUID `8ed1e034-…643a9` and world `eldyrwild`.
- [ ] Source dry-run is write-free; malformed/conflicting exact revision identity fails closed; replay creates no duplicate revision.
- [ ] Historical roots are unchanged.
- [ ] No ingestion/LLM call occurs.
- [ ] No DungeonMind graph write/contribution/head advancement occurs.
- [ ] C2S25 opens from APP-STATE and resolves at least one canonical pill/object through the current durable World snapshot.
- [ ] World head before and after Stage 2B is unchanged unless a separately authorized external World advancement is explicitly reconciled.
- [ ] Buddy API restart/hard reload preserves the recovered catalog/Plan/recap/World join.
- [ ] Post-Stage2B external backup SHA is recorded and restores into a second clean target with identical APP-STATE fingerprint.
- [ ] Candidate graph/span/provenance bundle adoption, additional recap source adoption, Build/Play recovery, graph-object usefulness, remote hosting, Stage 2 completion, and STOP 2 completion remain explicitly false.

### Merge / STOP law

This PR is the **second implementation PR in the current durability/recovery period** after #691. After merge:

1. do not automatically dispatch candidate-graph/artifact adoption;
2. do not automatically dispatch the rest of the recap-source corpus;
3. run the assembled product against recovered C1/C2 state;
4. record the first user-visible failures;
5. align with the product owner on whether the next Stage 2 artifact slice is still the right move;
6. the next dependent implementation PR, if any, carries backward-looking Stage 2B acceptance/merge sync.

Stage 2B landing therefore ends at a **human dogfood checkpoint**, not at an automatically pre-authored Stage 2C.

---

## §10 What remains false after Stage 2B

Even after a successful merge:

- Stage 2 is not DONE;
- STOP 2 is not passed;
- only the previously proven C2S25 source is guaranteed durable in APP-STATE by this slice;
- the rest of the C1/C2 recap source corpus is not yet adopted into durable product source authority;
- historical candidate graphs, source-span indexes, validation reports, provenance indexes, and other `out/` bundles remain transitional/local where they survive;
- 21 / 53 historical Ingest bundles may remain partial;
- Build historical identities remain unresolved/adapter work;
- no historical C1/C2 Runbook/Play state is fabricated;
- the durability-witness Plan remains until Plan gains a supported management lifecycle;
- graph-object presentation usefulness remains a separate UI/projection dogfood repair;
- remote/VPC hosting and off-laptop authority migration remain later roadmap work.

The next decision is made from dogfood, not from this handoff.