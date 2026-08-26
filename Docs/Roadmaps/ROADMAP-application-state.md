# ROADMAP — Application State

**Status:** ACTIVE — AS0 through AS3 merged; AS4 Play Continuity is this implementation PR
**Line of work / flow:** `APP-STATE`
**Created:** 2026-08-24
**Updated:** 2026-08-25
**Architecture authority:** [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md)
**Parent pickup:** [`../Plans/STEWARDS-ANCHOR-application-state.md`](../Plans/STEWARDS-ANCHOR-application-state.md)
**AS0 merge:** `4c90df353bfb5d0f6857357e00eb8b2b6e142257` (PR #636)
**AS0 accepted head:** `605445b3b839b494a82218758c465edbfe59bad9`
**AS0.1 merge:** `dd09f7f707e38f9f4348b759da8cfdbbe420fd60` (PR #639)
**AS0.1 accepted head:** `abb3fb15f9b56e8712c07c798674d0462827677f`
**AS0.1 review:** Review Cycle 2 PASS-equivalent, review `5014814402`

**AS1 merge:** `29ff1584b9f76bb5100a724a96bebbbcf8f08d12` (PR #641)
**AS1 accepted head:** `b42eb629e8924695af7af5a6c986f44a26dc3536`
**AS1 review:** 3 distinct-head cycles; final PASS-equivalent review `5023488870`
**AS1 execution evidence:** PR #641 comment `5415847095`

**AS2 merge:** `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0` (PR #643)
**AS2 accepted head:** `6b1c2e77648eee6180d293c92d2c97a428e9002f`
**AS2 review:** 3 distinct-head cycles; final PASS-equivalent review `5024971680`
**AS2 exact-head evidence:** PR #643 comment `5417774447`

**AS3 merge:** `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e` (PR #646)
**AS3 accepted head:** `913cfe0bbce4db27250afd8277e3af50712ee029`
**AS3 review:** 3 distinct-head cycles; final PASS-equivalent review `5026608908`
**AS3 exact-head evidence:** PR #646 comment `5420273265`

This roadmap is **capability-sequenced**. It is not a table-creation schedule.
Each implementation slice must leave a real consumer working on PostgreSQL, then
delete or fail-close the replaced file authority for that consumer.

AS0 established the shared substrate. AS0.1 / PR #639 widened identity/asset
scope. **AS1 is DONE.** **AS2 is DONE.** **AS3 is DONE.** **AS4 is this PR and
is unmerged.** Do not invent the AS4 merge SHA. AS5 remains false.

---

## Sequence

```text
AS0   DESIGN                 DONE — PR #636 merge 4c90df35
AS0.1 STORAGE-TOPOLOGY       DONE — PR #639 merge dd09f7f7
AS1   PLAN DOCUMENTS         DONE — PR #641 merge 29ff1584
AS2   PLAYABLE               DONE — PR #643 merge b4d63daa
AS3   PLAY RUNTIME           DONE — PR #646 merge 9c946cd8
AS4   PLAY CONTINUITY        THIS PR — active Run + resume/reload; unmerged
AS5   PLAY DEMOLITION        still false / blocked on AS4
AS6+  CANDIDATE FAMILIES     evidence-driven; not pre-authorized schemas
```

BF2/BF3 Play Runtime/cockpit deepening stays paused on the remaining
file-backed `active-run.json` pointer until this AS4 PR merges or the steward
explicitly re-sequences.

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
| Status | **DONE** — merged PR #639 at `dd09f7f707e38f9f4348b759da8cfdbbe420fd60` (accepted head `abb3fb15f9b56e8712c07c798674d0462827677f`; Review Cycle 2 review `5014814402`) |
| Independently useful outcome | Durable Buddy objects have storage-independent identity; large bytes named to DungeonMindServer storage/CDN via Asset metadata; Ingest/generated artifacts are first-class future consumers; WorkObject stays Content-only |
| Primary consumer/story | Prevents AS1 from baking path/URL identity or a document-only substrate |
| Predecessor | AS0 #636 |
| Durable/public contract introduced | Architecture v1.1 four state classes + classification test |
| Runtime/database collision boundary | None (design-only). Open CUTOVER #638 does not lease these files. |
| Required product + owning-boundary evidence | Four-file lease; architecture/roadmap/anchor/AS1 consistency; no speculative tables |
| What remains false | AS1–AS6+ remain unimplemented until this/next PRs land; no Asset service, no Ingest schema |

---

## AS1 — PLAN DOCUMENTS (foundation + real consumer)

| Field | Content |
|---|---|
| Status | **DONE** — merged PR #641 at `29ff1584b9f76bb5100a724a96bebbbcf8f08d12` (accepted head `b42eb629e8924695af7af5a6c986f44a26dc3536`; 3 review cycles; final PASS-equivalent review `5023488870`; evidence comment `5415847095`) |
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
| Status | **DONE** — merged PR #643 at `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0` (accepted head `6b1c2e77648eee6180d293c92d2c97a428e9002f`; 3 review cycles; final PASS-equivalent review `5024971680`; evidence comment `5417774447`) |
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
| Status | **DONE** — merged PR #646 at `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e` (accepted head `913cfe0bbce4db27250afd8277e3af50712ee029`; 3 review cycles; final PASS-equivalent review `5026608908`; evidence comment `5420273265`) |
| Independently useful outcome | Creating a Run seals its manifest in one PostgreSQL transaction; progress CAS is a single-row update; rebase is one transaction with no intent file |
| Primary consumer/story | Play Run create/list/get/progress; preserve-only rebase; CR-U17 table durability |
| Predecessor | AS2 historical Playable revisions |
| Durable/public contract introduced | `play.run` + `play.run_manifest`; SQL `run_revision` CAS |
| Runtime/database collision boundary | `out/runtime/play/` during pre-switch; same Buddy DB new `play` schema |
| Required product + owning-boundary evidence | create+manifest atomicity (crash leaves neither); CAS 409; rebase without intent files; import existing runs+manifests; Runtime mutation latency baseline/head |
| What remains false | active-run pointer remains a file until AS4; Play file demolition is AS5; Combat not migrated; mutation-history table not created |
| Measured latency (not a merge gate) | PostgreSQL Runtime CAS ~74 ms p95 vs 50 ms hypothesis and ~1 ms file baseline; Start Run + seal ~75 ms p95, inside the 250 ms hypothesis. Keep visible during interactive use. |

---

## AS4 — PLAY CONTINUITY

| Field | Content |
|---|---|
| Status | **this PR** — not merged; do not invent the AS4 merge SHA |
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
  Shared-file overlap remains `pyproject.toml` / server bootstrap — serialize then.
- CUTOVER #645 merged immediately before AS3 #646; first-world initialization is
  now behind DungeonMind authority. Open CUTOVER #647 is D.3 graph-engine
  demolition design and is disjoint from APP-STATE Play Continuity paths.
- PLAY-SURFACE BF2/BF3 remain paused on the remaining `active-run.json` file
  pointer until AS4 or steward re-sequence. Existing PLAY-SURFACE active-run
  continuity work is file-backed resume/serialize, not AS4 PostgreSQL dispatch.
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
