# ROADMAP — Application State

**Status:** ACTIVE — AS0 merged; storage-topology correction before AS1
**Line of work / flow:** `APP-STATE`
**Created:** 2026-08-24
**Updated:** 2026-08-24
**Architecture authority:** [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md)
**Parent pickup:** [`../Plans/STEWARDS-ANCHOR-application-state.md`](../Plans/STEWARDS-ANCHOR-application-state.md)
**AS0 merge:** `4c90df353bfb5d0f6857357e00eb8b2b6e142257` (PR #636)
**AS0 accepted head:** `605445b3b839b494a82218758c465edbfe59bad9`
**This correction dispatch base:** `9782c05d506ee4be918ed2491ff63d9705ac97c9` (AS0.1 handoff/dispatch base; not a completed correction merge)

This roadmap is **capability-sequenced**. It is not a table-creation schedule.
Each implementation slice must leave a real consumer working on PostgreSQL, then
delete or fail-close the replaced file authority for that consumer.

AS0 established the shared substrate. This correction widens identity/asset
scope so later domains are not designed as an afterthought. **AS1 remains
Plan-only.**

---

## Sequence

```text
AS0   DESIGN                 DONE — PR #636 merge 4c90df35
AS0.1 STORAGE-TOPOLOGY       THIS PR — identity / asset / Ingest scope
AS1   PLAN DOCUMENTS         NEXT implementation — substrate + kind=plan
AS2   PLAYABLE               runbook WorkRevisions historically addressable
AS3   PLAY RUNTIME           Run + sealed manifest in one transaction
AS4   PLAY CONTINUITY        active Run + resume/reload
AS5   PLAY DEMOLITION        delete replaced Play file writers/locks/intents
AS6+  CANDIDATE FAMILIES     evidence-driven; not pre-authorized schemas
```

BF2/BF3 Play Runtime/cockpit deepening stays paused on the file-backed store
until AS3/AS4 land or the steward explicitly re-sequences.

Order after AS5 is evidence-driven and may interleave with Play/Agent/CUTOVER
work. Do not invent AS6/AS7 implementation handoffs or table names to fill this
list.

---

## AS0 — DESIGN

| Field | Content |
|---|---|
| Status | **DONE** — merged PR #636 at `4c90df353bfb5d0f6857357e00eb8b2b6e142257` (accepted head `605445b3b839b494a82218758c465edbfe59bad9`) |
| Independently useful outcome | Reviewed persistence architecture so later slices do not guess lifecycle, revision, isolation, or cutover rules |
| Primary consumer/story | Steward / implementation agents |
| Predecessor | Steward seed; CUTOVER #634; Play BF1 PR #628 |
| Durable/public contract introduced | `ARCHITECTURE-application-state-layer.md` v1.0 |
| Runtime/database collision boundary | None (design-only) |
| Required product + owning-boundary evidence | Architecture completeness vs original AS0 §6/§10; three-file lease |
| What remains false | No Buddy application-state database; Plan not migrated; identity law later widened by AS0.1 |

---

## AS0.1 — STORAGE-TOPOLOGY BOUNDARY

| Field | Content |
|---|---|
| Status | **this PR** (architecture correction before AS1) |
| Independently useful outcome | Durable Buddy objects have storage-independent identity; large bytes named to DungeonMindServer storage/CDN via Asset metadata; Ingest/generated artifacts are first-class future consumers; WorkObject stays Content-only |
| Primary consumer/story | Prevents AS1 from baking path/URL identity or a document-only substrate |
| Predecessor | AS0 #636 |
| Durable/public contract introduced | Architecture v1.1 four state classes + classification test |
| Runtime/database collision boundary | None (design-only). Open CUTOVER #638 does not lease these files. |
| Required product + owning-boundary evidence | Four-file lease; architecture/roadmap/anchor/AS1 consistency; no speculative tables |
| What remains false | Everything in AS1–AS6+ remains unimplemented; no Postgres, no Asset service, no Ingest schema |

---

## AS1 — PLAN DOCUMENTS (foundation + real consumer)

| Field | Content |
|---|---|
| Status | NEXT after **AS0.1** PASS/merge/re-anchor (not after AS0 alone) |
| Independently useful outcome | A Plan workspace document (`kind=plan`) can be created, autosaved as a WorkingCopy, committed as an immutable WorkRevision, reloaded after process restart, and CAS-conflicted — entirely on Buddy PostgreSQL |
| Primary consumer/story | Plan/Build authoring via existing `/api/live/workspace-documents*` + Tiptap commit for `kind=plan`; CR-U11/CR-U17 adjacent |
| Predecessor | Accepted architecture v1.1 (AS0 + this correction) |
| Durable/public contract introduced | Buddy application-state DSN + Alembic tree; `content.work_object` / `work_revision` / `working_copy`; plan-kind authority switch |
| Runtime/database collision boundary | New DSN and database `dungeonbuddy_application_state` on the existing local Postgres server; `pyproject.toml` / `uv.lock`; live-control-server plan write path. Serialize with CUTOVER if it leases those root files. World Graph DB is forbidden. |
| Required product + owning-boundary evidence | PostgreSQL integration tests through the plan domain service (and route); CAS 409; DB unavailable fail-closed; no file read after switch; existing plan snapshot import idempotency; baseline vs head save/load/commit latency captured (hypotheses in architecture §15) |
| What remains false | `runbook` still file-backed; Play Runs/manifests/active-run unchanged; Combat unchanged; Ingest/Asset/generated-artifact tables **must not exist**; `worldbuilding_source` unchanged; no Play historical pinning yet; corpus Session Prep files not auto-published; no DungeonMindServer CDN integration |

AS1 that only adds connection helpers, empty migrations, and unused tables is
**not** this slice. AS1 that adds `ingest.*`, `assets.*`, Play, Combat, or
generator tables is **scope expansion** — stop.

The substrate proved by Plan is intended for later domain services. WorkObject
is the Content primitive used by Plan, not a generic container those later
domains must use.

---

## AS2 — PLAYABLE RUNBOOKS

| Field | Content |
|---|---|
| Status | blocked on AS1 |
| Independently useful outcome | Runbook/Playable documents use the same WorkObject primitives; revision N remains loadable after N+1 is committed |
| Primary consumer/story | Plan edits Playable; Play will pin exact revisions (Runs still file-backed until AS3, but must be able to **read** historical WorkRevisions) |
| Predecessor | AS1 plan-kind substrate in production |
| Durable/public contract introduced | `kind=runbook` admitted; Playable committed vs working-copy rule; historical get-by-revision API |
| Runtime/database collision boundary | same Buddy DB, `content.*` only; runbook writer allowlist (currently eval Tiptap paths) |
| Required product + owning-boundary evidence | R17-pinned load after R18 commit; working copy is not Run-admissible; import honesty (no fabricated history); Playable save/load latency baseline/head |
| What remains false | Run/manifest still files; rebase intents still exist; active Run still file; Combat still files |

---

## AS3 — PLAY RUNTIME

| Field | Content |
|---|---|
| Status | blocked on AS2 |
| Independently useful outcome | Creating a Run seals its manifest in one PostgreSQL transaction; progress CAS is a single-row update; rebase is one transaction with no intent file |
| Primary consumer/story | Play Run create/list/get/progress; preserve-only rebase; CR-U17 table durability |
| Predecessor | AS2 historical Playable revisions |
| Durable/public contract introduced | `play.run` + `play.run_manifest`; SQL `run_revision` CAS |
| Runtime/database collision boundary | `out/runtime/play/` during pre-switch; same Buddy DB new `play` schema |
| Required product + owning-boundary evidence | create+manifest atomicity (crash leaves neither); CAS 409; rebase without intent files; import existing runs+manifests; Runtime mutation latency baseline/head |
| What remains false | active-run pointer may still be a file until AS4; Play file demolition not done; Combat not migrated; mutation-history table not created |

---

## AS4 — PLAY CONTINUITY

| Field | Content |
|---|---|
| Status | blocked on AS3 |
| Independently useful outcome | Resume/reload opens the selected Run at the pinned Playable revision and current Runtime without reading `active-run.json` |
| Primary consumer/story | Play entry/resume; CR-U17 |
| Predecessor | AS3 Runs in PostgreSQL |
| Durable/public contract introduced | `play.active_run` |
| Runtime/database collision boundary | `out/runtime/play/active-run.json` |
| Required product + owning-boundary evidence | set/get/clear active Run; resume E2E; restart restores exact current moment; resume latency baseline/head |
| What remains false | Play file writers may still exist until AS5; Combat still files; BF2/BF3 cockpit semantics not in scope |

---

## AS5 — PLAY DEMOLITION

| Field | Content |
|---|---|
| Status | blocked on AS4 |
| Independently useful outcome | Play boots and operates with `out/runtime/play/` writers, rebase intents, and Play file locks **absent** |
| Primary consumer/story | Operator dogfood: Play with old paths deleted or unreadable |
| Predecessor | AS2–AS4 switched |
| Durable/public contract introduced | negative: those paths are not product authority |
| Runtime/database collision boundary | deletion of Play registry/lock/intent modules; tests that previously used tmp files |
| Required product + owning-boundary evidence | suite + dogfood with `out/runtime/play` missing; old write attempts fail closed; no fallback toggle |
| What remains false | Combat file persistence remains; other workspace kinds may remain; Ingest/Asset/generated artifacts not migrated; CUTOVER graph-runtime demolition remains separate |

---

## AS6+ — candidate migration families

Re-anchor before each. These are families, **not** pre-authorized PRs or
schema names to create early:

| Family | Independently useful outcome when selected | Notes |
|---|---|---|
| Ingest processing-review | IngestRun and processing/review survive without path-as-id; accepted World-bearing proposals still publish through DungeonMind | First-class APP-STATE consumer; current recap ingest is topology-heavy |
| SourceArtifact identity | Source owns artifact identity, provenance, and asset reference without path-as-id | Distinct from IngestRun; large bytes stay behind Asset |
| Generated artifact lifecycles | Statblock, location, NPC, shop, encounter, and card **drafts/projects** have stable ids through review/use | Domain-owned schemas; not WorkObject unless document-like. Only reviewed World-bearing facts publish to DungeonMind; mechanics/cards/assets remain in their owning domain |
| Asset metadata + DungeonMindServer bytes | Consumers store `asset_id`; CDN URL is delivery, not identity | No byte columns in PostgreSQL for large binaries |
| Combat | Combat survives worktree/session_dir locality | Combat-owned schema; Play stores only a reference |
| Remaining content / worldbuilding_source | Build sources durable without becoming World truth | Distinct publish/corpus policy |
| Optional agent proposal/task durability | Only if product correctness requires it across reload | Do not migrate Hermes localStorage by default |
| Remaining plan publish-to-corpus | Explicit export of a WorkRevision to Session Prep.md | Must not be silent |
| Run mutation history | Optional audit rows committed with CAS | Not event sourcing; only if independently useful |

Do not start any of these by creating unused tables in AS1.

---

## Collision and pause rules

- CUTOVER D.2/D.3 may resume in parallel **if** write leases do not overlap.
  AS1's likely overlap is `pyproject.toml` / server bootstrap — serialize then.
- Open at this correction: CUTOVER PR #638 (`HANDOFF-CUTOVER-worldbuilding-authority-port.md` only) does not overlap these four files.
- PLAY-SURFACE BF2/BF3 remain paused on file-backed Runtime until AS3/AS4 or steward re-sequence.
- CON-READY stories are acceptance context, not a license to bundle Combat or Ingest into AS1.

---

## What "done" means for the workstream

The workstream succeeds when:

1. Buddy-owned durable product objects have stable domain identity independent of filesystem path, corpus path, CDN URL, bucket key, or table coordinate.
2. Those objects live behind domain services on the Buddy PostgreSQL substrate (metadata/relationships for assets; not necessarily bytes).
3. Large binary bytes are delivered through DungeonMindServer storage/CDN behind `asset_id`.
4. DungeonMind remains sole World Graph authority.
5. Derived/regenerable representations are not promoted into authority merely because they are persisted.
6. Replaced topology (paths/files/URL-as-id) is demolished, not toggled, for each switched domain.
7. Play resume/save/CAS meet measured (not hypothesized) latency gates.
8. Historical Playable revisions are real, not "current file equals the Run."
