---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / AS1 — PostgreSQL foundation + Plan WorkObject consumer
  - Flow: APP-STATE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Architecture: Docs/Design/ARCHITECTURE-application-state-layer.md (v1.1)
  - Predecessor: AS0.1 storage-topology correction merge on main after re-anchor
  - Production consumer: kind=plan workspace documents
  - Empty-table PRs are not this slice

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — AS1: Buddy PostgreSQL foundation with Plan WorkObject consumer

**Created:** 2026-08-24
**Status:** BLOCKED ON STORAGE-TOPOLOGY CORRECTION — dispatch only after `HANDOFF-APP-STATE-storage-topology-boundary.md` PASS/merge/re-anchor
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md`
**Conversation/workstream:** `APP-STATE`
**Flow / owner:** `APP-STATE`
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** merge commit of the AS0.1 storage-topology correction on `main` after steward re-anchor. Do not invent that merge SHA. Do not fork from pre-correction architecture text.
**PR title:** `APP-STATE: persist Plan documents on PostgreSQL`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Architecture: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md). Roadmap: [`../Roadmaps/ROADMAP-application-state.md`](../Roadmaps/ROADMAP-application-state.md).

---

## §1 Mission and merge-ready invariant

**Mission:** A GM can create, autosave, commit, and reload a Plan workspace document (`kind=plan`) through the existing live-control workspace-document API so that committed Markdown and recoverable drafts survive process restart on Buddy-owned PostgreSQL rather than `out/` files.

**Merge-ready invariant:**

> **After AS1, `kind=plan` durable state is owned by the Content domain service over the Buddy application-state unit of work: WorkObject identity is the existing document UUID, WorkingCopy is the recoverable draft, WorkRevision is immutable committed Markdown with SHA-256, CAS conflicts fail closed, PostgreSQL unavailable never reads leftover plan files, existing current-bytes import is exact/idempotent, and tests prove this at the PostgreSQL + domain-service/route boundary — not via unused tables.**

A PR that only adds connection helpers, Alembic scaffolding, and unused `content.*` tables does **not** satisfy this invariant.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes: every AS1 path is plan-kind persistence. Runbook/Play/Combat stay on files. |
| Most likely adversarial sequence | Implement substrate without wiring routes; tests hit repositories only; production Plan save still writes `out/workspace/plan`. |
| Will §7 actually detect that failure? | Route/domain-service tests must create/commit/reload a plan **without** a workspace Markdown file after switch; a repository-only green is insufficient. |
| Easiest owning boundary to under-test | Import of existing registry+bytes with honest single current revision; corpus Session Prep `target_relpath` treated as publish metadata, not a second authority. |
| Fact that forces stop/split | Need to migrate `runbook`, Play Runs, or Combat to make the consumer "feel real"; or Docker compose becomes mandatory contrary to architecture. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-application-state-layer.md` v1.1 (post AS0.1 correction) |
| Base revision | AS0.1 storage-topology correction merge on `main` after re-anchor |
| Predecessor contract | AS0 #636 + AS0.1 identity/asset scope; `CONTRACT-workspace-document-identity-v1.md` identity rules (UUID, discard-not-delete, kind enum) |
| Exact input consumed | Current `kind=plan` registry records + snapshot Markdown bytes; existing `/api/live/workspace-documents*` and Tiptap prepare/commit for plan |
| Named successor | AS2 — Playable/`runbook` historical WorkRevisions (`ROADMAP-application-state.md`) |
| What remains false | runbook/Play Run/manifest/active-run/Combat still file-backed; Ingest/Asset/generated-artifact schemas unimplemented; no historical fabrication; corpus Session Prep not auto-rewritten; World Graph untouched; path/URL not used as shared API identity |
| Explicit non-goals | Play domain semantics; CUTOVER D.2/D.3; `worldbuilding_source`; second Postgres server; migrate-on-boot; generic JSON store; `ingest.*` / `assets.*` / generated-artifact / Combat / Play Run tables; DungeonMindServer CDN integration; path/URL as domain identity in shared APIs |
| Branch / isolated checkout | `agent/app-state-postgres-foundation` in an isolated worktree |
| Parallel lanes / collision hotspots | Re-check at dispatch. `pyproject.toml` / `uv.lock` / server bootstrap are hotspots vs CUTOVER implementation. Open CUTOVER PR #638 (handoff-only; no overlap with this lease). |
| Runtime/state ownership | Isolated Buddy logical database `dungeonbuddy_application_state` (or worktree override). **Never** `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL`, `dungeonmind_cutover_live`, or `DMB_CUTOVER_TEST_DATABASE_URL`. Tests use ephemeral DBs from `DMB_APPLICATION_STATE_TEST_DATABASE_URL`. Do not mutate operator plan files except via documented import against a disposable root. |
| State-authority sync set after merge | `Docs/Roadmaps/ROADMAP-application-state.md`; `Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md` (AS0 archive); `Docs/Plans/STEWARDS-ANCHOR-application-state.md` (record AS0.1 merge; AS1 active; do **not** mark AS1 DONE). Record AS0.1 PR/merge SHA and review-cycle count once known. |

Read the architecture before changing code. If base, lease, or consumer differs, stop.

The shared substrate (config, migrations, UoW, CAS, isolation) serves later domain
services. WorkObject / WorkRevision / WorkingCopy is a **Content-domain** primitive for
document-like authored material — not a generic `application_object (id, type, jsonb)`
container. If AS1 seems to need Ingest, Asset, generated-artifact, Combat, or Play Run
tables, stop — the slice is over-generalized. Source owns SourceArtifact identity;
Ingest owns IngestRun and processing/review. Neither schema is AS1.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| `POST /api/live/workspace-documents` `kind=plan` | registry JSON + optional path | insert WorkObject (`content_status` draft equivalent); no plan Markdown file as authority | Yes | Content service + Postgres |
| snapshot GET plan | registry + current file bytes | WorkObject + WorkingCopy or current WorkRevision bytes | Yes | Content service + Postgres |
| Tiptap prepare/commit plan | file write + registry revision++ | WorkingCopy upsert / WorkRevision insert + CAS | Yes | Content service + Tiptap route adapter |
| autosave/reload process restart | localStorage + file | server WorkingCopy is recoverable without the file | Yes | Content service + Postgres |
| CAS mismatch | registry `expected_revision` 409 | `object_revision` / working-copy CAS 409 | Yes | Content service + Postgres |
| DB unavailable after plan switch | files still work | fail closed; **no** file fallback | Yes | config + service |
| `kind=runbook` same routes | files | **unchanged files** | Yes | existing registry/writer |
| existing plan import | n/a | current bytes → one WorkRevision at current `revision_n`; replay match; digest mismatch fail closed | Yes | import command/service |
| corpus Session Prep `target_relpath` | file is authority | imported bytes in Postgres; corpus file not silently rewritten; not read authority after switch | Yes | import + read path |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| commit → crash before COMMIT → reload | previous committed revision or prior working copy; no half-written revision | transaction test |
| two commits with same expected CAS | one 200, one 409 | CAS test |
| identical replay after success | no-op success iff digest already stored at that revision | replay test |
| import twice | second pass no-ops on matching digest | import idempotency |
| import conflict (same id, different digest) | fail closed; no switch | import conflict test |
| switch then delete `out/workspace/plan/<id>.md` | snapshot still loads from DB | post-switch file-absent test |
| unset/wrong DSN after switch | named error; no file read | failure matrix test |
| World Graph DSN supplied as app-state URL | isolation guard refuses | isolation guard test |
| runbook commit during AS1 | still file-backed | regression on runbook path |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `src/application_state/__init__.py` | Package export |
| Create | `src/application_state/config.py` | `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` parse; no World Graph fallback |
| Create | `src/application_state/errors.py` | Named fail-closed errors |
| Create | `src/application_state/naming.py` | Database-name denylist / isolation guards |
| Create | `src/application_state/engine.py` | psycopg connection factory |
| Create | `src/application_state/unit_of_work.py` | Transaction boundary |
| Create | `src/application_state/cli.py` | Explicit `upgrade` / head-check; **no** migrate-on-boot |
| Create | `src/application_state/alembic.ini` | Buddy Alembic config |
| Create | `src/application_state/migrations/env.py` | Alembic env using Buddy DSN |
| Create | `src/application_state/migrations/script.py.mako` | Alembic template |
| Create | `src/application_state/migrations/versions/*.py` | `content` WorkObject/WorkRevision/WorkingCopy tables |
| Create | `src/application_state/content/__init__.py` | Content primitives |
| Create | `src/application_state/content/types.py` | Pydantic WorkObject / WorkRevision / WorkingCopy |
| Create | `src/application_state/content/repository.py` | SQL for admitted kinds |
| Create | `src/application_state/content/service.py` | Content domain service (plan admitted) |
| Create | `src/application_state/content/import_plans.py` | Exact existing-state import |
| Modify | `pyproject.toml` | Direct `psycopg` + `alembic` deps; do **not** replace `dungeonmind[postgres]` World extra |
| Modify | `uv.lock` | Lockfile for those deps |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | Dispatch `kind=plan` to Content service after switch |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Plan prepare/commit through Content service after switch |
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | Stop being plan-kind authority after switch; keep runbook/worldbuilding |
| Create | `tests/application_state/conftest.py` | Ephemeral DB fixture + guards |
| Create | `tests/application_state/test_isolation_guards.py` | Denylist / no World Graph DSN |
| Create | `tests/application_state/test_plan_work_object_postgres.py` | Create/commit/reload/CAS/unavailable/file-absent |
| Create | `tests/application_state/test_plan_existing_state_import.py` | Idempotent exact import |
| Modify | `Docs/Roadmaps/ROADMAP-application-state.md` | Backward-looking AS0 completion only (sync set) |
| Modify | `Docs/Plans/HANDOFF-APP-STATE-application-state-architecture.md` | AS0 archive/completion |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-application-state.md` | Record AS0 merge/review; AS1 active; AS1 not DONE |

**Bounded discovery exception:**

```text
Directory: tests/application_state/
Maximum additional paths: 8
Allowed path kinds: pytest modules proving §7 rows
Decision rule: only if a required adversarial sequence cannot live in the named tests without a new module

Directory: src/application_state/migrations/versions/
Maximum additional paths: 3
Allowed path kinds: additional Alembic revisions required to reach the content schema without squash
Decision rule: first revision should be sufficient; extra only for a failed revision that cannot be edited after share
```

A required path outside this lease is a stop report. Especially: Docker compose, DungeonMind repo, Play Run modules, `kind=runbook` product rewrite.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live_control_server/services/play_run_*.py` | AS3 |
| `apps/live_control_server/services/play_active_run.py` | AS4 |
| `apps/live_control_server/services/combat_*.py` | later Combat slice |
| DungeonMind schema / `DUNGEONMIND_*` World DSNs as app-state | World authority |
| Docker/compose files | Architecture: same server, `CREATE DATABASE`; stop if that is impossible |
| `out/**` product mutation | Import may read a **test fixture** copy; do not rewrite the operator registry as a side effect of tests |
| CUTOVER D.2/D.3 modules | Separate demolition line |
| `kind=runbook` / `worldbuilding_source` switch | AS2 / AS6+ |
| Event sourcing / `play_run_mutation` | Rejected for AS1 |
| `ingest.*` / `assets.*` / generated-artifact schemas | AS6+ candidate families; stop if AS1 needs them |
| DungeonMindServer storage/CDN integration | Asset boundary is named in architecture only |
| Path/URL/bucket as domain identity in shared APIs | Storage-topology correction forbids |
| `apps/live_control_server/config.py` World Graph helpers | Keep World config separate; app-state config lives in `src/application_state/config.py`. Touch `config.py` only if a one-line re-export is unavoidable — stop and report if more is required. |

---

## §6 Implementation contract

```text
Input:
  Architecture-application-state-layer.md WorkObject contract
  Existing plan document_id UUID, title, campaign_id, target_relpath metadata,
  snapshot Markdown bytes, registry revision_n

Output:
  PostgreSQL content.work_object / work_revision / working_copy
  Plan API behavior preserved for clients (UUID identity, discard, snapshot shape)
  Switched plan reads/writes do not require out/workspace/plan/*.md

Invariant:
  same §1 invariant

Failure behavior:
  CAS mismatch → 409, no write
  DB unavailable after switch → named 503/500, no file fallback
  import digest conflict → abort import, no switch
  missing historical revisions → do not fabricate; only current bytes become revision_n

Replay / idempotency:
  same commit + matching digest after success → no-op success
  changed bytes + stale CAS → 409
  import replay matching digest → no-op
  import replay conflicting digest → fail closed

Trust boundary:
  Verifies: UUID identity, digest of stored bytes, CAS, isolation denylist,
            alembic head, plan-kind only
  Records/trusts without proving: Play/Combat/World; browser cache as non-authority
```

Commit point: PostgreSQL `COMMIT` of the unit of work. Before commit, files are not plan authority after switch. After commit, snapshot load must return the committed bytes. Post-commit crash: next load reads committed rows.

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Plan snapshot | DSN + migrated head | WorkObject + bytes | 404 | fail closed | 500 | 409 on write | read idempotent |
| Plan commit | same | new WorkRevision | 404 | fail closed | abort | 409 | digest no-op |
| Plan import | files still authority until switch | rows match ids/digests | skip empty markdown per architecture (record still imports metadata) | fail import | fail closed | conflict stop | idempotent |
| Runbook snapshot | files | files | files | files | files | files | files |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact document UUID | preserved 1:1 as `work_object_id` | invalid UUID 422 | No |
| Title | metadata, may collide | stored as-is | No silent merge |
| `target_relpath` | metadata / optional publish pointer after switch | illegal path rejected on create as today | Not byte authority |
| Discard | status discarded, row kept | restore supported | No hard delete |
| Kind | `plan` admitted; others not switched | dispatch by kind | No |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| Autosave | `working_copy` row | bytes round-trip UTF-8 | last write wins with CAS | n/a | discard working copy |
| Commit | insert `work_revision` | digest + bytes | no-op if same digest+CAS already applied | n/a | history immutable; next commit is N+1 |
| Import | one revision at current `revision_n` | digest matches captured file | matching replay no-op | no fabricated R1..R(n-1) | abort import |

### D. Predecessor → consumer mapping

**Grounding source:** `WorkspaceDocumentRecord` + `WorkspaceDocumentSnapshot` in `workspace_document_registry.py`

| Predecessor field | Real shape | Consumer | Transformation | Proof |
|---|---|---|---|---|
| `document_id` | UUID string | `work_object_id` | identity copy | import + create tests |
| `kind` | `plan` | `kind` | admit only plan | dispatch tests |
| `title` / `campaign_id` / `target_session` | strings/ints | WorkObject metadata | copy | round-trip |
| `target_relpath` | optional path | metadata, not read path after switch | copy; do not write corpus | import + file-absent |
| `status` | active/discarded | WorkObject status | copy | discard/restore |
| `content_status` | draft/committed | current_revision_id null vs set | draft → working copy only; committed → WorkRevision | snapshot tests |
| `revision` | int CAS | `revision_n` of imported current bytes **and** `object_revision` | current bytes become that `revision_n`; no prior rows | import honesty |
| `markdown` / `content_sha256` | snapshot | WorkRevision bytes + sha256 | exact bytes | digest compare |
| `file_fingerprint` | file token | not an authority after switch | drop as authority | file-absent test |

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Plan create/commit/reload uses PostgreSQL | Content service + route + real Postgres | owning-boundary integration | pytest module below | commit then new connection loads same bytes | repository-only tests |
| CAS conflict | Content service + Postgres | adversarial | two writers same expected revision | one success, one 409 | last-write-wins without CAS |
| DB unavailable after switch | service | failure injection | DSN down / invalid | no `out/workspace/plan` read | file fallback |
| Isolation denylist | naming/config | contract | World Graph DSN / `dungeonmind_cutover_live` | refuse | tests pointed at live World DB |
| Import exact + idempotent | import_plans | persistence | fixture registry+markdown | counts/ids/digests match; second pass no-op | new UUIDs issued |
| Import conflict fail closed | import_plans | adversarial | same id different digest | abort | best-effort overwrite |
| Runbook unchanged | existing writer/registry | regression | runbook snapshot still file path | file still authority | accidental kind-all switch |
| No migrate-on-boot | cli / app startup | contract | boot with behind-head DB | fail closed, schema unchanged | alembic at import of FastAPI app |
| Performance hypotheses labeled | test or script artifact | measurement | capture file-path baseline vs postgres head for plan load/commit | numbers recorded as baseline/head, not as architecture fiction | "should be fast" only |
| Lease held | git | regression | `git diff --name-only <AS0_1_MERGE_SHA>...HEAD` | §4 / bounded discovery only | extras |

Exact verification commands (implementation fills the pytest node ids if split):

```bash
uv run pytest tests/application_state/test_isolation_guards.py \
  tests/application_state/test_plan_work_object_postgres.py \
  tests/application_state/test_plan_existing_state_import.py \
  -q

# Default suite must not require the operator product DB
uv run pytest tests/application_state -q

git diff --check
git diff --name-only <AS0_1_MERGE_SHA>...HEAD
```

`<AS0_1_MERGE_SHA>` is the actual AS0.1 storage-topology correction merge on main after re-anchor.

### Minimal live / dogfood proof

```text
Existing surface: Plan workspace document create + Tiptap save/commit + reload
Smallest realistic scenario: one kind=plan document, commit Markdown, restart
  live-control-server, reopen snapshot; then remove out/workspace/plan/<id>.md
  if it exists and reopen again
Expected observation: committed bytes survive; no file fallback after switch
Evidence captured: command output + snapshot content_sha256
```

If live UI dogfood is unavailable, the route-level pytest against ephemeral Postgres
is required and the UI dogfood is recorded as operator-followup, not skipped
silently. Repository-only tests cannot replace the route/service proof.

### Baseline failure handling

Record the same pytest commands on AS0.1-merge base (expect collection miss / no
tests) versus head. Do not rename missing tests on base as a product failure.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence + provenance;
4. nano-commit/fix story;
5. base/head and actual changed paths vs §4;
6. baseline failures/waivers;
7. paths outside §4 (`none` or stop report);
8. stop conditions and resolution;
9. named successor still false (AS2 runbook historical revisions);
10. prior finding ledger on re-review.

---

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] The §1 invariant holds across every claimed §3 path/adversarial sequence.
- [ ] Exact PR/head, evidence provenance, and review-cycle number are recorded.
- [ ] No second public/durable contract was silently introduced (runbook switch, Play Run, Combat, World, Ingest, Asset, generated-artifact).
- [ ] Applicable §6 state/identity/persistence/predecessor semantics hold.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Baseline failures and waivers are truthful.
- [ ] Parallel write/runtime ownership did not drift silently (no World Graph DB use).
- [ ] Named successor AS2 remains unimplemented/unclaimed.
- [ ] Direct Buddy `psycopg` + `alembic` deps exist; app-state DSN is not the DungeonMind extra.
- [ ] Ordinary app boot does not mutate schema.
- [ ] After plan switch, leftover plan files are not read authority.
- [ ] No CDN integration, path/URL identity in shared APIs, or speculative domain tables.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- second independently useful outcome (runbook, Play Run, Combat, Ingest, Asset, generated-artifact);
- need for `ingest.*`, `assets.*`, generated-artifact, Combat, or Play Run tables;
- invariant cannot govern every claimed path;
- owning-boundary evidence cannot be produced without a live operator DB;
- Docker compose required because `CREATE DATABASE` on existing server is impossible;
- unresolved working-copy vs commit semantics;
- required path outside §4 or another lane's write lease (`pyproject.toml` leased by CUTOVER);
- unsafe shared runtime/state collision with World Graph DB;
- migrate-on-boot sneaks in;
- generic JSON document table without admitted `kind=plan` invariant;
- WorkObject generalized into universal object store.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
