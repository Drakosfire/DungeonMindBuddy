# ROADMAP — Application State

**Status:** ACTIVE — sequenced after AS0 architecture gate  
**Line of work / flow:** `APP-STATE`  
**Created:** 2026-08-24  
**Architecture authority:** [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md)  
**Parent pickup:** [`../Plans/STEWARDS-ANCHOR-application-state.md`](../Plans/STEWARDS-ANCHOR-application-state.md)  
**Dispatch base at authoring:** `5e596e1e90c156573da602f1f9591ee4828c3aee`

This roadmap is **capability-sequenced**. It is not a table-creation schedule.
Each slice must leave a real consumer working on PostgreSQL, then delete or
fail-close the replaced file authority for that consumer.

The steward seed's AS0→AS7 hypothesis is re-evaluated below. The standalone
"existing-state mega-cutover" slice is removed: each domain slice imports and
switches its own consumer. Demolition remains a dedicated Play-file removal
slice after Play consumers have switched.

---

## Sequence

```text
AS0  DESIGN          architecture + this roadmap + AS1 handoff
AS1  PLAN DOCUMENTS  substrate + first real consumer (kind=plan)
AS2  PLAYABLE        runbook WorkRevisions historically addressable
AS3  PLAY RUNTIME    Run + sealed manifest in one transaction
AS4  PLAY CONTINUITY active Run + resume/reload
AS5  PLAY DEMOLITION delete replaced Play file writers/locks/intents
AS6+ OTHER SURFACES  Combat, worldbuilding_source, remaining file state
```

BF2/BF3 Play Runtime/cockpit deepening stays paused on the file-backed store
until AS3/AS4 land or the steward explicitly re-sequences.

---

## AS0 — DESIGN

| Field | Content |
|---|---|
| Status | **this PR** (architecture gate) |
| Independently useful outcome | Reviewed persistence architecture so AS1 does not guess lifecycle, revision, isolation, or cutover rules |
| Primary consumer/story | Steward / implementation agents; CON-READY durability stories enabled but not implemented |
| Predecessor | Steward seed `STEWARDS-ANCHOR-application-state.md`; CUTOVER #634; Play BF1 PR #628 |
| Durable/public contract introduced | `ARCHITECTURE-application-state-layer.md` |
| Runtime/database collision boundary | None (design-only) |
| Required product + owning-boundary evidence | Architecture completeness vs AS0 §6/§10; steward preflight; three-file lease |
| What remains false | No Buddy application-state database, migrations, route wiring, data import, Play cutover, or file demolition |

---

## AS1 — PLAN DOCUMENTS (foundation + real consumer)

| Field | Content |
|---|---|
| Status | NEXT after AS0 PASS/merge/re-anchor |
| Independently useful outcome | A Plan workspace document (`kind=plan`) can be created, autosaved as a WorkingCopy, committed as an immutable WorkRevision, reloaded after process restart, and CAS-conflicted — entirely on Buddy PostgreSQL |
| Primary consumer/story | Plan/Build authoring via existing `/api/live/workspace-documents*` + Tiptap commit for `kind=plan`; CR-U11/CR-U17 adjacent |
| Predecessor | Accepted AS0 architecture |
| Durable/public contract introduced | Buddy application-state DSN + Alembic tree; `content.work_object` / `work_revision` / `working_copy`; plan-kind authority switch |
| Runtime/database collision boundary | New DSN and database `dungeonbuddy_application_state` on the existing local Postgres server; `pyproject.toml` / `uv.lock`; live-control-server plan write path. Serialize with CUTOVER if it leases those root files. World Graph DB is forbidden. |
| Required product + owning-boundary evidence | PostgreSQL integration tests through the plan domain service (and route); CAS 409; DB unavailable fail-closed; no file read after switch; existing plan snapshot import idempotency; baseline vs head save/load/commit latency captured (hypotheses in architecture §15) |
| What remains false | `runbook` still file-backed; Play Runs/manifests/active-run unchanged; Combat unchanged; `worldbuilding_source` unchanged; no Play historical pinning yet; corpus Session Prep files not auto-published |

AS1 that only adds connection helpers, empty migrations, and unused tables is
**not** this slice.

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
| What remains false | Combat file persistence remains; other workspace kinds may remain; CUTOVER graph-runtime demolition remains separate |

---

## AS6+ — OTHER SURFACES

Re-anchor before each. Candidates, not pre-authorized PRs:

| Candidate | Independently useful outcome | Notes |
|---|---|---|
| Combat current + saves | Combat survives worktree/session_dir locality | Combat-owned schema; Play stores only a reference |
| `worldbuilding_source` | Build sources on WorkObject | Distinct publish/corpus policy; not World truth |
| Remaining plan publish-to-corpus | Explicit export of a WorkRevision to Session Prep.md | Must not be silent |
| Source asset metadata | Identity/digest/locator in Postgres | Bytes stay external |
| Run mutation history | Optional audit rows committed with CAS | Not event sourcing; only if independently useful |

Do not start AS6+ by creating unused tables for every candidate.

---

## Collision and pause rules

- CUTOVER D.2/D.3 may resume in parallel **if** write leases do not overlap.
  AS1's likely overlap is `pyproject.toml` / server bootstrap — serialize then.
- Open at AS0 authoring: CUTOVER PR #635 (`HANDOFF-CUTOVER-threat-authority-port.md` only) does not overlap AS0's three files.
- PLAY-SURFACE BF2/BF3 remain paused on file-backed Runtime until AS3/AS4 or steward re-sequence.
- CON-READY stories are acceptance context, not a license to bundle Combat into AS1.

---

## What "done" means for the workstream

The workstream succeeds when:

1. Buddy-owned durable state that product correctness depends on lives behind domain services on this substrate.
2. DungeonMind remains sole World Graph authority.
3. Replaced file authorities are deleted, not toggled.
4. Play resume/save/CAS meet measured (not hypothesized) latency gates.
5. Historical Playable revisions are real, not "current file equals the Run."
