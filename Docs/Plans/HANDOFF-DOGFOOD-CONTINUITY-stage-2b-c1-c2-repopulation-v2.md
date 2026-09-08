---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DEMO-R2 Stage 2B
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE/OPERATOR RECOVERY → REVIEW → MERGE → HUMAN DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v2.md`
  - Branch / PR: `dogfood-continuity/stage-2b-c1-c2-repopulation-v2` / `DOGFOOD-CONTINUITY: repopulate durable C1/C2 application state`

  ## Verification pointer
  - Exact base: `1ed1b6c484d898a2216330258be2897dc0588f74`
  - Predecessor: PR #692 Stage 2A closure sync
  - Verification: §7 exact recovery + assembled Buddy↔World witness + post-repopulation backup/restore parity

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and real 54331/54330 witness are the review contract.
  The PR description is transport metadata only.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 2B exact C1/C2 repopulation v2

**Created:** 2026-09-07  
**Status:** READY TO DISPATCH  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v2.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / DEMO-R2 Stage 2B`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE/OPERATOR RECOVERY → REVIEW → MERGE → HUMAN DOGFOOD  
**Exact base:** `1ed1b6c484d898a2216330258be2897dc0588f74` — `main` after merged PR #692  
**PR title:** `DOGFOOD-CONTINUITY: repopulate durable C1/C2 application state`  
**Implementation branch:** `dogfood-continuity/stage-2b-c1-c2-repopulation-v2`  

> Repository law: `AGENTS.md`. Product sequence: `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`. Buddy persistence authority: `Docs/Design/ARCHITECTURE-application-state-layer.md`. World authority: `Docs/Design/ARCHITECTURE-campaign-supergraph.md`. Recovery locator: `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md`.

---

## §0 Steward ruling

PR #692 is merged and is the completed predecessor:

```text
PR #692                         MERGED
reviewed exact head             2bb9384099f7408cb8859c43ba98e3d8f28768aa
merge commit                    1ed1b6c484d898a2216330258be2897dc0588f74
formal review cycles            3
Stage 2A                        DONE
Stage 2 / STOP 2                OPEN
Stage 2B                        CURRENT — this handoff
```

PR #691 established the durable Buddy APP-STATE substrate on `127.0.0.1:54331`. The human drill then proved recognizable product state across container replacement, real host reboot, deliberate named-volume destruction, and independently verified restore of the same Plan identity. PR #692 landed that closure and the standing persistence standard.

The pre-#692 draft branch `dogfood-continuity/stage-2b-c1-c2-repopulation-v1` is superseded and is not authority. Do not implement from it.

### §0A Backward-looking predecessor sync

The first implementation commit must record only facts already true after PR #692:

```text
PR #692                         DONE / MERGED
merge                           1ed1b6c484d898a2216330258be2897dc0588f74
formal review cycles            3
Stage 2A closure                DONE
Stage 2B                        CURRENT
Stage 2 / STOP 2                OPEN
```

Sync only these mutable authorities unless a factual current-state update becomes necessary later in the PR:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
```

Do not pre-mark Stage 2B DONE. Do not dispatch a successor from this PR.

### §0B Authority split — non-negotiable

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

There are not separate durable C1/C2 graph stores. Campaign is scope inside the World Supergraph. Worldbuilding contributes governed world truth; played recaps contribute campaign-scoped truth. Stage 2B must not copy World objects into Buddy or rebuild graph truth from recap files.

**Hard stop:** any DungeonMind graph write, contribution replay, re-ingestion, graph-head advancement, Buddy-owned graph persistence, or generated historical identity/content requires rebrief before continuing.

---

## §1 Mission and merge-ready invariant

**Mission:** Re-establish the exact previously accepted C1/C2 Buddy-side continuity set on durable `54331`, prove ordinary Buddy product surfaces can use it, and prove that recovered Buddy context rejoins the already-durable DungeonMind World authority through the controlled read contract.

**Merge-ready invariant:**

> An operator first captures a verified pre-write backup/fingerprint of the live durable `54331` authority; then, through the already-accepted recovery seams, restores the exact 53 historical C1/C2 `ingest.run` identities, the one proven exact C2 Session 27 Plan, and the previously accepted C2 Session 25 source artifact/revision without generating identity or rewriting content; replay is idempotent; the non-canon durability-witness Plan remains unchanged; the normal Ingest and Plan product seams expose the recovered material; C2 Session 25 reads from APP-STATE source authority and projects/clicks current World objects through the unchanged `54330` World head; and a post-repopulation external backup restores into a second clean target with an identical APP-STATE fingerprint.

This is one capability: **exact repopulation of the lost Buddy continuity set plus proof of the restored Buddy↔World join**.

It is not “finish Stage 2.” Bulk relocation of candidate graphs/span indexes/provenance bundles, all recap sources, Build recovery, Runbook/Play archaeology, remote hosting, and rich node-card redesign remain later work after dogfood.

### Pre-dispatch critique

| Question | Ruling |
| --- | --- |
| Can one invariant govern the whole PR? | Yes. Every write restores a previously accepted Buddy identity/byte binding lost with `54329`; World work is read-only proof that restored context addresses the existing graph authority. |
| Most likely adversarial failure | Rows come back, but with regenerated Plan/source identity or a silently different World head, giving the appearance of continuity without preserving authority. |
| Owning proof | Exact IDs/digests, explicit source revision assertion, pre/post fingerprints, replay no-ops, normal product list/open, and unchanged World-head witness. |
| Easiest boundary to under-test | The assembled join. `53 rows inserted` is not enough unless a real historical recap loads from APP-STATE and its graph object resolves through DungeonMind. |
| Split signal | Any accepted Plan/Ingest importer needs redesign; exact source revision cannot be restored safely; graph mutation is needed; current World head differs without an explained legitimate advancement; or recovery needs guessed content/identity. |

---

## §2 Exact recovery target

### §2.1 Existing live state that must survive

Before any Stage 2B write, fingerprint and externally back up the live `54331` authority.

The non-canon drill Plan is legitimate existing APP-STATE and must remain untouched:

```text
title         Durability Witness — Delete Me Later
document_id   3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d
```

Plan has no supported delete/archive operation. Do not invent SQL/curl cleanup in this PR.

### §2.2 Ingest — exact 53 historical run identities

Reuse the accepted PR #686 operator path unchanged:

```text
explicit historical roots
  → scripts/adopt_historical_ingest_runs.py preview
  → exact target_set_sha256 handshake
  → --apply through accepted one-transaction importer
  → APP-STATE ingest.run
```

Expected final identity shape:

```text
historical ingest.run identities        53
longmont-c1                             24
longmont-c2                             29
validated                               36
prepared                                17
reviewable                               0
sorted run_id identity SHA-256          59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1
```

Do not modify the accepted Ingest importer/adoption semantics merely for convenience. Select by exact evidence, not title/session/latest/path/timestamp.

### §2.3 Plan — exact C2 Session 27 document

Reuse the accepted PR #685 operator path unchanged:

```text
document_id      80630cc2-33ee-40db-bf9d-fb5217085e17
title            C2 Session 27 Prep
revision         2
bytes            2631
content sha256   d8a8595d5211d00a57731354ea06bce25aa6236332b66dece59870ed9d77a511
```

Use the explicit historical root and exact document ID. The four historical Plan identities whose admitted target bytes were absent remain absent. No blank shells.

### §2.4 Source authority — exact C2 Session 25 revision

Restore the source authority PR #689 had already proven before the tmpfs loss:

```text
run_id               graph-ingest:longmont-c2:session-25:20260808T005650Z
run lifecycle        validated
source_artifact_id    artifact:recap:longmont-c2:session-25:fd38b5915b32
source_revision_id    8ed1e034-23c6-4295-b2ff-05d5cdd643a9
content sha256        fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
world_id              eldyrwild
source domain         recap
```

The prior revision UUID is known. Recovery must preserve it; “same Markdown with a new UUID” is not exact continuity.

The current `persist_source_markdown()` API accepts an optional `source_revision_id`, but replay currently does not make a caller-supplied revision UUID an exact assertion. Tighten this at the Source authority boundary.

Required semantics when `source_revision_id` is supplied:

- absent artifact/digest → insert with that exact UUID after normal scope/digest checks;
- same artifact/digest + same UUID → truthful no-op;
- same artifact/digest + different UUID → conflict/block;
- requested UUID already belongs to different source state → conflict/block;
- malformed UUID at operator boundary → fail before write.

Extend the existing historical source adoption operator with:

```text
--source-revision-id <uuid>
--check-only
```

`--check-only` must execute all filesystem/digest/run/scope/revision preconditions and perform zero APP-STATE writes. Preserve existing behavior for invocations that do not use the new recovery options; do not introduce runtime filesystem fallback.

### §2.5 DungeonMind World — read-only assembled witness

Stage 2B does not repopulate `54330`.

Expected recovered World baseline from the earlier DungeonMind recovery:

```text
world             eldyrwild
accepted head     rev:680c246047d67f9fe0293ee90526f670
parent            rev:34b1f8e2625d5ba693fc726a2a1a4720
objects           469 at recovery witness
contributions     95 at recovery witness
```

At A0, start/read the durable World authority and record its current head. If it differs from the expected head, STOP and determine whether a legitimate World advancement occurred; do not overwrite or “repair” it from Buddy.

Required assembled witness:

```text
C2S25 ingest.run + source.revision on 54331
  → historical recap projection
  → world=eldyrwild / campaign=longmont-c2 / focus=session-25
  → current immutable DungeonMind snapshot
  → canonical pill/object identity
  → open the existing World object card
```

Use Orik if the same accepted witness remains present. Record the snapshot/head used by the request. Prove the World head is identical before and after Stage 2B.

If the existing read contract directly allows a world-global identity check under both C1 and C2 projection scopes, record one shared-object sanity witness (Mirathorn is preferred). This is diagnostic only; do not expand the PR merely to build a new cross-campaign comparison UI.

---

## §3 Observable user effects

| Before Stage 2B | After Stage 2B |
| --- | --- |
| Ingest history selector lost the 53 C1/C2 DB rows | Ordinary Ingest catalog shows the historical C1/C2 run set again |
| Plan contains the durability witness but historical C2S27 is gone | Plan chooser opens exact `C2 Session 27 Prep` with the old document ID/revision/content |
| C2S25 source rows are gone | C2S25 recap loads from durable APP-STATE source authority with the original source revision UUID |
| Stage 1 historical recap chrome has no catalog/source fuel | C2S25 can be read through the real historical recap path again |
| World is a separate durable authority | Clicking a recap object resolves through the unchanged DungeonMind World snapshot |
| `54331` durability proven only with the synthetic witness | A post-recovery backup/clean restore proves the valuable C1/C2 state itself is recoverable |

The user should be able to observe recognizable campaign material returning. Stage 2B is not accepted on database counts alone.

---

## §4 Write lease

Expected cumulative changed paths:

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v2.md` | This implementation authority |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Backward sync #692; Stage 2B CURRENT; keep Stage 2/STOP 2 open |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Re-anchor to post-#692 main and Stage 2B current |
| Modify | `Docs/Operations/CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` | After real apply, record current durable APP-STATE locators/status without rewriting historical evidence |
| Create | `Docs/Reports/REPORT-stage-2b-c1-c2-repopulation.md` | Sanitized exact operator/product/World/backup witness |
| Modify | `src/application_state/source/service.py` | Make supplied source revision UUID an exact authority assertion |
| Modify | `src/application_state/source/repository.py` | Only the minimum lookup/conflict support needed for exact revision identity |
| Modify | `apps/live_control_server/services/historical_recap_source_adoption.py` | Add exact revision recovery input + check-only preflight |
| Modify | `tests/application_state/test_source_content_postgres.py` | Owning PostgreSQL proof of exact UUID insert/no-op/conflict |
| Modify | `tests/test_historical_recap_source_adoption.py` | Operator preflight/apply/malformed/conflict proof |

Bounded discovery exception:

```text
Directory: tests/
Maximum additional paths: 2
Allowed: existing historical recap projection/API tests only
Reason: strengthen an existing owning test if needed to prove C2S25 reads APP-STATE and preserves World read-only behavior.
```

A required production path outside this lease is a stop/split signal. In particular, do not modify:

```text
scripts/adopt_historical_ingest_runs.py
src/product_continuity/ingest_adoption.py
scripts/adopt_historical_plans.py
src/product_continuity/plan_adoption.py
APP-STATE migrations
frontend UI code
DungeonMind repository/code/storage
promotion/extraction code
```

unless the handoff assumption is proven false and steward rebriefs the slice.

---

## §5 Runtime/state ownership and collision law

- Implementation uses an isolated branch/worktree.
- Unit/integration tests use disposable APP-STATE databases, never live `54331`.
- The real Stage 2B apply to `54331` is serialized and recorded in the report.
- Historical roots are read-only evidence.
- `54330` is read-only for this lane. Capture its head before/after the assembled witness.
- Do not run `down -v` against the live post-repopulation `54331` volume. Disaster proof after repopulation is a restore to a second clean target, not another live-volume destruction drill.
- Any parallel graph-object usefulness lane may read the same authorities but must not mutate these source/APP-STATE paths or the real recovery target during the apply window.

---

## §6 Implementation / operator sequence

### Phase 0 — re-anchor and predecessor sync

1. Re-read `main`; exact expected base is `1ed1b6c484d898a2216330258be2897dc0588f74`.
2. Confirm no newer merge or active lease collision. If `main` moved, re-anchor and update this handoff before implementation.
3. First implementation commit: update only roadmap + steward anchor with #692 merged / Stage 2B CURRENT.

### Phase 1 — make exact source revision recovery safe

1. Add Source authority tests first.
2. Enforce caller-supplied `source_revision_id` as an exact assertion.
3. Add historical source-adoption `--source-revision-id` and `--check-only`.
4. Preserve old callers and no-filesystem-runtime behavior.

### Phase 2 — preflight the real authorities with zero writes

Record sanitized coordinates and state.

1. `54331`: compute live fingerprint and take external backup + SHA/fingerprint sidecars.
2. Confirm witness Plan `3c8c6f8b-…` still exists.
3. Ingest: preview exact historical set; require 53 and the accepted identity shape; capture preview `target_set_sha256`.
4. Plan: preview only `80630cc2-…5e17`; require exact recoverable content/digest.
5. Source: `--check-only` C2S25 with exact source revision UUID; require digest/scope/run match and zero source rows written.
6. `54330`: bring up/read current World head. If unexpected, STOP and investigate rather than mutate.

If any preflight blocks, do not partially apply safe siblings. Report and rebrief.

### Phase 3 — apply exact Buddy recovery

Apply in this order:

```text
1. 53 Ingest runs
2. C2 Session 27 Plan
3. C2 Session 25 source artifact/revision
```

Why: source adoption depends on the exact run existing; Plan is independent; all preflights already passed.

Immediately verify:

- 53 recovered historical run IDs with expected campaign/status mix and sorted identity digest;
- C2S27 exact Plan document/revision/content;
- C2S25 exact artifact + exact old revision UUID + exact SHA + world/campaign/session scope;
- durability witness Plan still exists unchanged.

### Phase 4 — replay/idempotency

Re-run the exact recovery commands.

Expected:

- Ingest: all selected rows `CURRENT_EXACT` / no-op; no duplicate or mutation;
- Plan: exact current/no-op; no new revision;
- Source: same artifact/digest/revision UUID no-op;
- APP-STATE fingerprint unchanged by replay.

### Phase 5 — ordinary product witness

Start Buddy normally against `54331`.

User-visible checks:

1. `/ingest` exposes recovered C1/C2 history.
2. Open C2 Session 25 through the normal historical recap path; actual recap prose renders.
3. `/plan` lists and opens exact `C2 Session 27 Prep` while retaining the non-canon witness Plan.
4. Restart Buddy API; repeat list/open without recovery roots becoming runtime authority.

### Phase 6 — Buddy↔World assembled witness

With `54330` up and read-only:

1. record World head immediately before request;
2. open C2S25 recap through normal product path;
3. confirm projection binds `eldyrwild` + `longmont-c2` + `session-25`;
4. click a canonical pill (prefer Orik if present) and open the existing World object card;
5. record the World snapshot/head returned;
6. record World head again; it must be unchanged.

A useful object card is desirable, but node-card richness is not this PR's merge boundary. Record thin/missing context as immediate post-Stage-2B dogfood input rather than widening the lease.

### Phase 7 — prove the valuable post-recovery state is recoverable

1. Fingerprint live repopulated `54331`.
2. Take a new external backup and record dump SHA-256 + fingerprint sidecar.
3. Restore into a second clean target.
4. Require restored fingerprint equality with live post-repopulation fingerprint.
5. Verify representative identities in the restored target: witness Plan, C2S27 Plan, 53 Ingest rows, C2S25 source revision.
6. Do **not** destroy the live volume again.

### Phase 8 — report and current-state ledger

Create `REPORT-stage-2b-c1-c2-repopulation.md` with sanitized exact evidence:

- implementation/review head;
- pre-write fingerprint + backup SHA;
- ingest preview target-set hash and final identity digest/count/status mix;
- exact Plan identity/revision/SHA;
- exact source artifact/revision/SHA/scope;
- replay no-op result/fingerprint;
- ordinary product list/open witness;
- World pre/request/post head and selected object;
- post-repopulation fingerprint + backup SHA + second-clean-target parity;
- explicit remaining partial/missing artifact debt.

Update `CAMPAIGN-MATERIAL-LIBRARY-c1-c2.md` only with facts actually observed after apply. Preserve the historical loss record; do not rewrite history as though the loss never happened.

---

## §7 Verification

### Automated

At minimum:

```bash
uv run pytest -q \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/test_historical_recap_world_projection.py \
  tests/test_graph_run_registry.py \
  tests/product_continuity/test_ingest_adoption_postgres.py \
  tests/product_continuity/test_plan_adoption_postgres.py

uv run ruff check \
  src/application_state/source/service.py \
  src/application_state/source/repository.py \
  apps/live_control_server/services/historical_recap_source_adoption.py \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_source_adoption.py
```

Run broader relevant APP-STATE/product-continuity tests if the implementation touches a shared Source behavior used outside historical recovery.

### Mandatory adversarial proofs

- explicit source UUID first insert persists that UUID;
- same artifact/digest/same UUID is no-op;
- same artifact/digest/different requested UUID blocks;
- same requested UUID already bound to different source state blocks;
- malformed UUID/check-only performs zero writes;
- changed source bytes/digest block before write;
- one failed preflight prevents starting the real multi-domain apply;
- recovery replay changes no APP-STATE fingerprint;
- World head does not change during the assembled witness;
- post-recovery backup restores to second clean target with exact fingerprint parity.

### Real owning-boundary acceptance witness

A merge-ready PR must record, on one exact reviewed head:

```text
54331 pre-write backup + fingerprint
        ↓
53 exact Ingest identities recovered
+ exact C2S27 Plan recovered
+ exact C2S25 source revision recovered
        ↓
ordinary Ingest + Plan product list/open works
        ↓
C2S25 recap opens from APP-STATE
        ↓
DungeonMind 54330 current World projection resolves
        ↓
canonical object pill/card opens
        ↓
World head unchanged
        ↓
post-recovery 54331 backup
        ↓
second clean target restores identical fingerprint
```

Database rows alone are insufficient.

---

## §8 Explicitly still false after Stage 2B

Even after this PR lands:

- Stage 2 is not necessarily complete;
- STOP 2 is not complete;
- only C2S25 recap source is guaranteed durable in APP-STATE by this slice;
- historical candidate graph/span/provenance/validation bundles may still depend on old `out/` storage;
- Build historical recovery remains unresolved;
- no historical Play Run/Runbook is fabricated;
- graph-object usefulness/richness may still be thin;
- navigation/remount issues remain;
- Agent integration remains later;
- VPC/object-storage migration remains later.

Missing remains missing. No re-ingestion is authorized as recovery.

---

## §9 Acceptance checklist

- [ ] Exact base/re-anchor is current; no silent main drift.
- [ ] Cumulative paths match §4 or an explicit steward-approved split exists.
- [ ] #692 is recorded backward-only as merged; Stage 2B is not pre-marked DONE.
- [ ] Pre-write live `54331` fingerprint + independently verified backup captured.
- [ ] Witness Plan survives unchanged.
- [ ] Exactly 53 historical Ingest identities restored with accepted identity/count/status evidence.
- [ ] Exact C2S27 Plan ID/revision/content restored; no blank sibling Plans invented.
- [ ] Exact C2S25 source artifact + original source revision UUID + digest/scope restored.
- [ ] Recovery replay is no-op and fingerprint-stable.
- [ ] Ordinary Ingest/Plan product paths expose/open the recovered material after API restart.
- [ ] C2S25 historical recap reads APP-STATE source content.
- [ ] Read-only DungeonMind World witness resolves current snapshot + canonical object; World head unchanged.
- [ ] Post-recovery backup restores to second clean target with exact fingerprint parity.
- [ ] Recovery report and material library are truthful and sanitized.
- [ ] No re-ingestion, graph mutation, historical-root mutation, runtime filesystem fallback, or generated historical content/identity.

---

## §10 Merge and STOP law

Do not merge automatically. Review every distinct head until merge-ready.

After merge:

1. re-anchor on the actual Stage 2B merge SHA;
2. because the next action is human dogfood rather than an automatically dispatched implementation successor, perform a direct guarded backward sync if needed to mark Stage 2B DONE and record its final review-cycle count/merge SHA;
3. **do not dispatch the next artifact-storage or UI PR yet**;
4. restore Stage 1 assembled historical recap dogfood immediately using real C1/C2 material;
5. record the first user-visible failures, especially node usefulness, session navigation, missing artifact bytes, and whether World/global-vs-campaign context feels correct;
6. only then choose the next Stage 2/Stage 3/interaction slice.

Human checkpoint:

> Can I open real C1/C2 history from durable Buddy state, inspect the canonical Eldyrwild World through the controlled DungeonMind contract, restart things without losing that context, and trust that the recovered valuable state itself has a tested backup/restore path?

Stage 2B landing reopens real dogfood. It does not authorize skipping it.
