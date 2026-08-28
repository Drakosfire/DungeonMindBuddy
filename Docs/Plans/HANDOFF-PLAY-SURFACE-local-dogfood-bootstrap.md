---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: PLAY-SURFACE / DF0
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md
  - Branch / PR: agent/play-local-dogfood-bootstrap / PLAY-SURFACE: make local Play dogfood reachable

  ## Verification pointer
  - Base/head: record exact SHAs in the PR
  - Changed paths: HANDOFF §5
  - Verification: HANDOFF §8

  The checked-in handoff, cumulative diff, nano-commit story, operator dogfood
  evidence, and independently rerun evidence are the review contract.
  This body is transport metadata.
---

# HANDOFF — Local Play dogfood bootstrap (DF0)

**Created:** 2026-08-26
**Status:** DONE — merged as GitHub **PR #657** (`87a769d05605ff021d28f0b69c5d7ab0b8205440`); do not dispatch.
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md`
**Workstream:** `PLAY-SURFACE / DF0`
**Flow / owner:** `PLAY-SURFACE`
**Handoff direction:** DESIGN → CODE
**Suggested branch:** `agent/play-local-dogfood-bootstrap`
**PR title:** `PLAY-SURFACE: make local Play dogfood reachable`

> **Dispatch base:** `4d82f12ad9c6d679b5dbce83db527eb7dbd27957`
>
> This is current `main`, containing merged PR #655 / BF3A.
>
> Re-fetch `main` and inspect active leases immediately before branch creation.
> Do not silently absorb unrelated upstream changes.

Parent authorities:

- `AGENTS.md`
- `Docs/Design/ARCHITECTURE-application-state-layer.md`
- `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
- `Docs/Design/DESIGN-play-current-moment-cockpit.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`

Completed predecessors:

```text
BF2 / PR #652
accepted head:
  9dffcab96ad3f527efedc3981aea805a63deb4df
merge:
  39ef105d3996ef0062dd45a089fecada14915436
review cycles:
  5

BF3A / PR #655
accepted head:
  3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7
merge:
  4d82f12ad9c6d679b5dbce83db527eb7dbd27957
review cycles:
  2
```

Parallel lanes at dispatch design time:

```text
#654 AGENT-INTERACTION
  apps/live_control_server/services/agent_turn_trace.py
  Hermes agent/host/query paths
  related Agent tests

#651 CUTOVER
  DungeonMind world_graph reads/writes/authority adapter
  Campaign Supergraph/CUTOVER authorities
  related CUTOVER tests
```

Neither overlaps this proposed write lease.

---

## §0 Why this PR exists

### 0.1 Dogfood discovered a false end-to-end assumption

BF3A proved this path:

```text
PostgreSQL application state exists
→ Runbook exists
→ exact Run exists / can be started
→ v2 READY
→ Current Moment cockpit
```

That path is valid.

It did **not** prove:

```text
normal developer checkout
→ normal documented server startup
→ /play
→ choose or start a Run
→ Current Moment
```

Manual dogfood on merged `main` instead produced:

```text
Choose a Run

Resume state is unavailable.
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL is not set;
Plan kind cannot use application state

Existing Runs
Run recovery is pending.

Start a Run
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL is not set;
Plan kind cannot use application state
```

The cockpit exists behind a prerequisite the normal local startup path does not
prepare or explain.

### 0.2 Current architecture is not the bug

Do **not** repair this by weakening APP-STATE.

The architecture intentionally requires:

```text
Buddy application-state logical database
  dungeonbuddy_application_state

separate from:

DungeonMind World Graph database
```

The same PostgreSQL **server** may host both databases.

The following remain required:

```text
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
```

And remain forbidden:

```text
missing DSN → silently use files
missing DSN → silently use DungeonMind database
server boot → silently migrate database
server boot → silently import legacy state
server boot → silently create database
```

The correction is an explicit operator bootstrap/readiness path.

### 0.3 Existing pieces already exist

Repository truth already contains:

```text
load_runtime_dsn()
  → independent APP-STATE configuration
  → isolation guards
  → World Graph collision rejection

application_state.cli
  check
  upgrade

capture_legacy_runbook_snapshots()
  → freezes leftover Runbook identity + bytes safely

import_runbooks_from_snapshots()
  → exact/idempotent adoption
  → preserves UUID/revision/digest
  → no fabricated history

StartRunPanel
  → lists Content-owned Runbooks
  → resolves committed WorkRevision
  → starts exact Run
```

DF0 composes these existing pieces into one supported local workflow.

It does not redesign them.

---

## §1 Capability decomposition

| Candidate                                               | Decision                                              |
| ------------------------------------------------------- | ----------------------------------------------------- |
| Explicit local APP-STATE readiness command              | **KEEP — core mission**                               |
| Explicit local APP-STATE bootstrap command              | **KEEP — core mission**                               |
| Safe creation of the local Buddy logical DB when absent | **KEEP — explicit bootstrap only**                    |
| Explicit Alembic upgrade during bootstrap               | **KEEP — explicit operator action**                   |
| Adopt leftover legacy Runbooks                          | **KEEP — required to recover real Playable material** |
| Verify at least one startable committed Runbook         | **KEEP — Play readiness proof**                       |
| Genericize obsolete “Plan kind” APP-STATE failure copy  | **KEEP — same discovered defect**                     |
| Document normal local product startup                   | **KEEP — same operator path**                         |
| Dev-only Play setup hint                                | **KEEP — bounded usability correction**               |
| Auto-run bootstrap when FastAPI starts                  | **REJECT**                                            |
| Migrate-on-boot                                         | **REJECT**                                            |
| File fallback                                           | **REJECT**                                            |
| World Graph DSN fallback                                | **REJECT**                                            |
| Automatically start PostgreSQL                          | **REJECT**                                            |
| Automatically create a Run                              | **REJECT**                                            |
| Automatically select active Run                         | **REJECT**                                            |
| Seed fake/sample Runbook content                        | **REJECT**                                            |
| Import arbitrary Markdown as a Runbook                  | **REJECT**                                            |
| Legacy Plan migration                                   | **SPLIT — not required for Play dogfood**             |
| BF3B Decision interaction                               | **SPLIT**                                             |
| BF3C object categories                                  | **SPLIT**                                             |
| Finder / Combat / Agent work                            | **SPLIT**                                             |

---

## §2 Mission and merge-ready invariant

### 2.1 Mission

> **Make merged BF3A reachable through a coherent local developer workflow:
> after the operator configures one safe Buddy application-state DSN, one
> explicit idempotent bootstrap command can provision the Buddy logical
> database if necessary, upgrade it to the current schema, honestly adopt any
> available legacy Runbooks, and prove whether Play has a startable committed
> Runbook. Standard FastAPI + Vite startup then reaches Play without requiring
> knowledge of internal migration/import modules.**

### 2.2 Merge-ready invariant

> **A developer with PostgreSQL running and a safe
> `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` configured can run one explicit
> DF0 bootstrap command. That command never targets or derives authority from a
> World Graph database, never drops/resets data, explicitly creates only an
> allowed Buddy local logical database when missing, explicitly migrates it to
> Alembic head, idempotently adopts honest leftover Runbook state, and reports
> whether at least one active committed Runbook can be used by Play. Re-running
> it is semantically idempotent. After a READY result, the documented ordinary
> server/UI startup allows `/play` to list/start the Runbook and reach the
> BF3A Current Moment cockpit.**

### 2.3 What becomes true

```text
configured safe APP-STATE DSN
→ bootstrap check explains exact state

bootstrap apply
→ database exists
→ schema at head
→ leftover Runbooks adopted if present
→ startable Runbook count known
→ clear READY / BLOCKED result

READY
→ uvicorn
→ Vite
→ /play
→ choose Runbook
→ Start exact Run
→ BF3A Current Moment
```

### 2.4 What remains false

```text
FastAPI boot mutates schema
FastAPI boot imports old files
missing DSN gets an implicit default
World Graph DB is reused for Buddy state
bootstrap invents historical revisions
bootstrap invents a Runbook
bootstrap starts a Run
bootstrap changes current Beat/Scene
bootstrap touches Combat
bootstrap touches Agent state
BF3B Decision controls exist
```

---

## §3 Operator contract

Create:

```text
scripts/bootstrap_local_play.py
```

Supported commands:

```bash
uv run python scripts/bootstrap_local_play.py check
uv run python scripts/bootstrap_local_play.py apply
```

### 3.1 `check`

`check` is read-only.

It must:

1. load the normal DungeonBuddy dotenv chain;
2. inspect `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL`;
3. validate the DSN through existing APP-STATE isolation rules;
4. identify the target database without printing credentials;
5. determine whether the target database exists/replies;
6. determine whether APP-STATE is at Alembic head;
7. inspect available legacy Runbook snapshots without importing them;
8. when schema is usable, count active committed Runbooks already in Content;
9. report Play readiness;
10. make no database/schema/content/Run mutation.

Representative output:

```text
DungeonBuddy Local Play Readiness

Application state DSN
  configured: yes
  host: 127.0.0.1
  port: 54329
  database: dungeonbuddy_application_state
  isolation: safe

Database
  exists: yes
  reachable: yes

Schema
  current: <revision>
  head: <revision>
  status: ready

Legacy Runbooks
  available for adoption: 1

Content
  active startable Runbooks: 0

PLAY READINESS: NEEDS BOOTSTRAP

Run:
  uv run python scripts/bootstrap_local_play.py apply
```

No password.

No full DSN.

### 3.2 Missing configuration

When the DSN is absent:

```text
PLAY READINESS: NEEDS CONFIGURATION

Set this in repo .env or .env.development:

DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=<postgresql URL for a separate Buddy database>

Recommended local database name:
  dungeonbuddy_application_state

Do not point this at:
  dungeonmind
  dungeonmind_cutover_live
  the configured World Graph database

Then run:
  uv run python scripts/bootstrap_local_play.py apply
```

Exit non-zero.

Do not invent connection coordinates from:

```text
DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL
DUNGEONMIND_DATABASE_URL
DMB_CUTOVER_TEST_DATABASE_URL
```

### 3.3 `apply`

`apply` is an explicit mutating operator command.

Its mutation sequence is:

```text
load + validate safe target DSN
        ↓
ensure target logical database exists
        ↓
explicit application-state Alembic upgrade
        ↓
capture leftover legacy Runbooks
        ↓
idempotent exact Runbook adoption
        ↓
verify Content state
        ↓
report Play readiness
```

No mutation occurs before DSN/isolation validation succeeds.

### 3.4 Local logical database provisioning

The architecture permits DungeonMind and Buddy to use the same PostgreSQL
server while requiring separate logical databases.

Therefore `apply` may create the target logical database when it does not yet
exist.

This is allowed **only** because `apply` itself is an explicit operator action.

Creation rules:

```text
target database missing
AND target name is:
  dungeonbuddy_application_state
  OR dungeonbuddy_application_state_<safe-suffix>
→ bootstrap may attempt CREATE DATABASE
```

Use the connection coordinates/credentials from the explicitly configured
Buddy DSN.

Do not derive them from a World Graph DSN.

A maintenance connection to PostgreSQL's `postgres` database is only an
administrative connection used to issue `CREATE DATABASE`; it is never treated
as application-state authority.

The bootstrap must never:

```text
DROP DATABASE
DROP SCHEMA
TRUNCATE
DELETE existing content
reset migration state
overwrite an existing database
```

If CREATE DATABASE permission is unavailable, fail cleanly and print a safe,
actionable creation instruction.

Example:

```text
Database dungeonbuddy_application_state does not exist and could not be created
with the configured PostgreSQL user.

Create that logical database with an account that has CREATEDB permission,
then rerun:

  uv run python scripts/bootstrap_local_play.py apply
```

Do not print passwords.

### 3.5 Existing custom safe database

If the configured database already exists and passes existing APP-STATE
isolation rules, it may be used even if its name is not the standard local
prefix.

However:

```text
bootstrap MAY USE existing safe custom DB
bootstrap MUST NOT CREATE arbitrary custom DB names
```

This prevents an explicit local helper from becoming a generic
`CREATE DATABASE <whatever the DSN says>` tool.

---

## §4 Runbook adoption and readiness

### 4.1 Preserve existing adoption authority

Use the existing:

```text
capture_legacy_runbook_snapshots(root)
import_runbooks_from_snapshots(snapshots)
```

Do not reimplement legacy mapping in the bootstrap script.

Do not read arbitrary Markdown and manufacture:

```text
document UUID
revision_n
content SHA
historical lineage
```

### 4.2 Import semantics

Preserve existing laws:

```text
legacy document UUID
→ exact WorkObject UUID

legacy committed current bytes
→ one honest WorkRevision

legacy revision N
→ WorkRevision revision_n N

older unseen revisions
→ absent

draft legacy bytes
→ WorkingCopy only

same import repeated
→ noop

same identity + different semantic content
→ conflict / fail closed
```

### 4.3 Startable Runbook definition

DF0 readiness is stronger than:

```text
list_runbooks() returned something
```

A Runbook is startable only if the existing Play/Content committed-revision
seam can truthfully resolve a current committed WorkRevision.

Conceptually:

```text
active Runbook WorkObject
AND current committed WorkRevision exists
AND exact revision/digest resolves
→ startable
```

A draft-only Runbook does not count.

### 4.4 Zero Runbooks

If bootstrap succeeds structurally but no startable Runbook exists:

```text
Application state: READY
Play content: NOT READY

No active committed Runbook is available.
No sample or fake Runbook was created.
```

This must be a distinct truthful result.

Do not silently seed a fixture merely to make the readiness command green.

### 4.5 Existing Run state

Bootstrap does not require an existing Run.

After bootstrap:

```text
existing durable Run
→ Play may resume it normally

no existing Run
→ operator chooses a Runbook
→ operator explicitly Start exact Run
```

Do not create or activate a Run during bootstrap.

---

## §5 Error and product-facing contract

### 5.1 Remove the obsolete Plan-specific failure

Current shared APP-STATE configuration emits:

```text
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL is not set;
Plan kind cannot use application state
```

That text is now wrong on Play.

Change shared configuration failure semantics to a domain-neutral message,
for example:

```text
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL is not set;
DungeonBuddy application state is unavailable
```

Do not change status/fail-closed semantics merely to change the copy.

### 5.2 Play local-development hint

When Play cannot list/resume/start because application state is unavailable,
the Vite development build should expose one short actionable hint:

```text
Local Play setup is incomplete.

Run:
uv run python scripts/bootstrap_local_play.py check
```

Constraints:

* development-only;
* no password/DSN rendering;
* no automatic bootstrap button;
* no browser-triggered migration;
* no browser-triggered database creation;
* no raw stack trace.

Production presentation remains a normal application-state unavailable error.

Do not invent a new public readiness API merely for this hint.

---

## §6 Normal local startup contract

The supported path becomes:

### First setup / after APP-STATE schema changes

```bash
# 1. Configure repo .env or .env.development
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=postgresql://.../dungeonbuddy_application_state

# 2. Explicit bootstrap
uv run python scripts/bootstrap_local_play.py apply
```

Then normal runtime:

```bash
# Terminal 1
uv run uvicorn apps.live_control_server.main:app --reload

# Terminal 2
pnpm --dir apps/live-control-ui dev
```

Then:

```text
http://127.0.0.1:5173/play
```

Ordinary subsequent readiness inspection:

```bash
uv run python scripts/bootstrap_local_play.py check
```

Do not require bootstrap every time servers restart.

### Documentation hierarchy

Create:

```text
Docs/Runbooks/RUNBOOK-local-play-dogfood.md
```

Update:

```text
README.md
apps/live-control-ui/README.md
```

The root README should make APP-STATE a visible prerequisite for product-local
startup instead of burying it inside architecture/handoffs.

The UI README's current:

```text
uvicorn
pnpm dev
```

manual smoke instructions must no longer imply that those two commands alone
constitute a complete first-time Play setup.

---

## §7 Architecture boundaries

### 7.1 APP-STATE remains authority

Do not change:

```text
WorkObject / WorkRevision ownership
Play Run tables
Run CAS
manifest ownership
active Run ownership
migration model
```

DF0 is operator composition, not a storage redesign.

### 7.2 No runtime fallback

These continue to fail closed:

```text
application-state DSN missing
database unreachable
schema behind
Runbook import conflict
historical bytes unavailable
```

No fallback to:

```text
out/registries workspace rows as live authority
old Run JSON files
current Runbook Markdown
World Graph PostgreSQL
```

### 7.3 No migrate-on-boot

This PR must not call:

```text
upgrade_to_head()
```

from:

```text
FastAPI lifespan
route handlers
Content service ordinary reads/writes
Play service ordinary reads/writes
frontend
```

Only the explicit bootstrap/operator path may invoke it.

### 7.4 No new persistence

The bootstrap has no durable state of its own.

Do not add:

```text
bootstrap table
bootstrap JSON file
bootstrap completion flag
migration receipt outside Alembic
```

Read current authority every time.

### 7.5 Existing legacy dogfood script

Do not repurpose:

```text
scripts/live_dogfood_check.py
```

It is a read-only statblock/combat/session-dir readiness tool for a different
dogfood path.

DF0 needs a dedicated application-state / Play bootstrap composition.

---

## §8 Write lease

### 8.1 Handoff

| Action | Path                                                         |
| ------ | ------------------------------------------------------------ |
| Create | `Docs/Plans/HANDOFF-PLAY-SURFACE-local-dogfood-bootstrap.md` |

### 8.2 Operator/bootstrap implementation

| Action | Path                              | Purpose                                   |
| ------ | --------------------------------- | ----------------------------------------- |
| Create | `scripts/bootstrap_local_play.py` | explicit `check` / `apply` composition    |
| Modify | `src/application_state/config.py` | domain-neutral APP-STATE unavailable copy |

The script may import existing production APIs from:

```text
src/application_state/
apps/live_control_server/services/workspace_document_registry.py
```

Importing a module does not lease it for modification.

### 8.3 Tests

| Action | Path                                                   |
| ------ | ------------------------------------------------------ |
| Create | `tests/application_state/test_local_play_bootstrap.py` |
| Modify | `apps/live-control-ui/src/App.test.tsx`                |

### 8.4 Development Play hint

| Action | Path                                                       |
| ------ | ---------------------------------------------------------- |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` |

If the existing unavailable-state ownership is actually in a smaller
Play-specific component, STOP and report the exact path before substituting it.

One bounded replacement inside:

```text
apps/live-control-ui/src/playSurface/
```

is allowed if it is demonstrably the existing owner of the error presentation.

Do not create a general notification framework.

### 8.5 Operator documentation

| Action | Path                                          |
| ------ | --------------------------------------------- |
| Create | `Docs/Runbooks/RUNBOOK-local-play-dogfood.md` |
| Modify | `README.md`                                   |
| Modify | `apps/live-control-ui/README.md`              |

### 8.6 BF3A completion/state sync

| Action | Path                                                                      |
| ------ | ------------------------------------------------------------------------- |
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit.md`               |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md`                                      |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md`         |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`                                 |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` |

Append BF3A completion facts; do not rewrite the historical dispatch.

### 8.7 Explicitly unleased

Do not modify:

```text
src/application_state/content/import_runbooks.py
src/application_state/content/import_plans.py
src/application_state/content/repository.py
src/application_state/content/service.py
src/application_state/play/
src/application_state/migrations/
apps/live_control_server/main.py
apps/live_control_server/routes/play_runs.py
apps/live_control_server/services/play_run_registry.py
scripts/live_dogfood_check.py
Combat
Agent Interaction
CUTOVER
DungeonMind adapters
```

If bootstrap cannot be implemented using the existing public adoption/service
seams, stop and report the missing seam rather than silently widening ownership.

---

## §9 Command behavior tests

### 9.1 Read-only `check`

Prove:

```text
missing DSN
→ nonzero
→ actionable configuration message
→ zero DB writes

World Graph DSN supplied as APP-STATE DSN
→ rejected

forbidden dungeonmind* database
→ rejected

unreachable PostgreSQL
→ named unavailable result

database missing
→ reports missing
→ check does not CREATE DATABASE

schema behind
→ reports behind
→ check does not migrate

schema at head + committed Runbook
→ READY

schema at head + zero committed Runbooks
→ APP-STATE ready / Play content not ready
```

### 9.2 `apply`

Prove:

```text
unsafe DSN
→ zero mutation

missing standard Buddy DB
→ explicitly creates database

missing dungeonbuddy_application_state_<suffix>
→ explicitly creates database

missing arbitrary custom DB name
→ refuses automatic creation

existing safe database
→ never DROP/replace

schema behind
→ explicit upgrade reaches head

legacy committed Runbook
→ exact WorkObject/WorkRevision adoption

legacy draft Runbook
→ not counted as startable

missing committed legacy bytes
→ fail closed

identity/content conflict
→ fail closed / no overwrite

second apply
→ no new semantic revision
→ importer reports noop
→ existing Run remains untouched
```

### 9.3 Secret hygiene

Tests must prove command output does not contain:

```text
password
full configured DSN when it contains credentials
```

The following may be shown:

```text
database name
host
port
username
```

---

## §10 Real PostgreSQL evidence

This PR exists because mocked/unit architecture evidence did not prove the
ordinary local path.

A real disposable PostgreSQL witness is mandatory.

Use the existing APP-STATE disposable database fixture/guardrails.

Do not point pytest at the operator product DB.

Required witness:

```text
temporary legacy repository root
  out/registries/workspace_documents.json
    one committed v2 Runbook record
  target Runbook Markdown bytes

+

fresh disposable PostgreSQL target
```

Run the same bootstrap implementation used by the operator command.

Then prove:

```text
bootstrap apply
→ database/schema usable
→ legacy Runbook imported
→ exact UUID preserved
→ revision_n preserved
→ digest preserved

workspace Runbook listing
→ imported Runbook visible

current committed revision
→ exact imported bytes available

existing Play start/admission production seams
→ can consume that Runbook truthfully
```

The strongest preferred witness is:

```text
bootstrap
→ workspace Runbook listing
→ exact committed revision
→ Run create + manifest
→ native-ready Run GET
```

against the disposable PostgreSQL database.

Do not create a parallel bootstrap-only fake service to satisfy this test.

---

## §11 Frontend evidence

If the Play development hint is implemented, run:

```bash
pnpm --dir apps/live-control-ui exec vitest run src/App.test.tsx
```

Required:

```text
APP-STATE unavailable in development
→ Play remains fail-closed
→ actionable bootstrap check hint visible

normal available state
→ no bootstrap warning

BF3A v2 READY
→ Current Moment still renders

v1 regression
→ unchanged
```

No frontend test may pretend that displaying a setup hint means the database is
ready.

---

## §12 Full verification

### Bootstrap focused

```bash
uv run pytest tests/application_state/test_local_play_bootstrap.py -q
```

### APP-STATE regression

Run the relevant real-PostgreSQL APP-STATE suites affected by config/bootstrap
behavior.

At minimum:

```bash
uv run pytest tests/application_state/ -q
```

Do not convert required PostgreSQL evidence into skips.

### Existing Play regression

Run the Play Run/progress/native-ready suites that consume APP-STATE.

Use the exact current test paths discovered on the implementation base.

### Frontend

```bash
pnpm --dir apps/live-control-ui exec vitest run src/App.test.tsx
pnpm --dir apps/live-control-ui run build
```

### Python quality

```bash
uv run ruff check \
  scripts/bootstrap_local_play.py \
  src/application_state/config.py \
  tests/application_state/test_local_play_bootstrap.py
```

### Diff

```bash
git diff --check
git diff --name-only <BASE>...HEAD
git diff --stat <BASE>...HEAD
```

### Mirrors

```bash
cmp Docs/Roadmaps/ROADMAP-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md

cmp Docs/Plans/STEWARDS-ANCHOR-con-ready.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

---

## §13 Mandatory operator dogfood evidence

Automated tests are not sufficient for DF0.

Before merge-ready review, run the actual supported workflow from a normal
developer checkout.

### Starting condition A — current discovered failure

With APP-STATE DSN absent:

```bash
uv run python scripts/bootstrap_local_play.py check
```

Must produce an actionable nonzero result.

Starting FastAPI + Vite without fixing it may still fail closed. That is correct.

### Starting condition B — configured local Buddy database

Configure:

```text
DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
```

to the real local Buddy logical database.

Then:

```bash
uv run python scripts/bootstrap_local_play.py apply
```

Capture redacted output.

Required:

```text
DSN safe
database exists/created
schema at head
legacy Runbook import result
active startable Runbook count
PLAY READINESS: READY
```

Run again:

```bash
uv run python scripts/bootstrap_local_play.py apply
```

Required:

```text
no duplicate semantic revision
no Run mutation
no destructive reset
READY remains true
```

### Start the actual product

```bash
uv run uvicorn apps.live_control_server.main:app --reload
pnpm --dir apps/live-control-ui dev
```

Navigate normally:

```text
launcher
→ Play
```

Required observation:

```text
no DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL unavailable banner

Existing Runs
→ loads normally

Start a Run
→ real active committed Runbook appears
```

If there is no existing Run:

```text
select the real Runbook
→ Start exact Run
→ BF3A Current Moment cockpit
```

Then:

```text
Make Scene Current
→ reload
→ exact Scene resumes
```

That final interaction is not new DF0 behavior; it proves the bootstrap actually
reaches merged BF3A rather than a bootstrap-only success condition.

Record this operator evidence in the PR.

Do not include secrets or full DSNs in PR comments.

---

## §14 BF3A completion/state-authority sync

The current CON-READY authority is stale after PR #655 merge.

Append to:

```text
Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit.md
```

approximately:

```text
## Completion

PR #655 merged.

Accepted implementation head:
  3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7

Merge:
  4d82f12ad9c6d679b5dbce83db527eb7dbd27957

Formal review cycles:
  2

BF3A outcome:
  DONE

Dogfood discovery:
  The Current Moment cockpit is implemented, but ordinary local startup on a
  checkout without configured Buddy application state cannot reach it.

Successor:
  DF0 — Local Play dogfood bootstrap/readiness

BF3B remains intentionally deferred until DF0 proves the merged cockpit is
reachable through the supported local operator path.
```

### Roadmap target state

Update the sequence to:

```text
BF2 / PR #652
DONE

BF3A / PR #655
DONE — Current Moment
accepted head 3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7
merge 4d82f12ad9c6d679b5dbce83db527eb7dbd27957
review cycles: 2

DF0 / PR #657
DONE — local Play dogfood gateway
accepted head dc20fe8e63eec691265e75eb73c69f441ffd779d
merge 87a769d05605ff021d28f0b69c5d7ab0b8205440
review cycles: 3

PLAN-BLANK-SHELL
CURRENT — zero-material Plan authoring + local→durable promotion

BF4A
BLOCKED ON PLAN-BLANK-SHELL — native Runbook reopen/save

BF3B
BLOCKED ON BF4A — Decision interaction and visible relevance

BF3C / BF3.x
later

P4
later
```

Do not mark DF0 DONE in its own implementation PR before review/merge.

### CR-U15 wording

The roadmap should stop saying the Current Moment cockpit itself is absent.

Preferred truth:

```text
CR-U15 — PARTIAL

BF3A Current Moment is implemented and merged.
DF0 merged local Play dogfood gateway.
Decision interaction and later cockpit capabilities remain false.
```

---

## §15 Minimal acceptance scenario

Use one real v2 Runbook equivalent to:

```text
Beat: Survive the Current Breach
  Scene: Tunnel Breach
  Scene: North Gate
  Scene: Courtyard
```

Start from:

```text
safe APP-STATE DSN configured
Buddy logical database does not exist
legacy Runbook record + exact Markdown exist locally
no Play Run exists
```

Required:

```text
1. bootstrap check
   → DB missing
   → zero mutation

2. bootstrap apply
   → creates Buddy DB
   → upgrades schema
   → adopts exact Runbook
   → READY

3. bootstrap apply again
   → no duplicate revision
   → READY

4. start FastAPI
5. start Vite
6. open /play
7. Runbook is listed
8. select Runbook
9. Start exact Run
10. v2 native READY succeeds
11. BF3A Beat-only Current Moment appears
12. Make Tunnel Breach Current
13. reload
14. Tunnel Breach resumes exactly
```

That is the first supported **Play dogfood gateway**.

---

## §16 Adversarial acceptance

### Wrong DB

```text
APP-STATE DSN → dungeonmind
→ reject before CREATE/migration/import
```

### Same DB as World Graph under different URL spelling

Where existing comparison logic can establish the collision:

```text
→ reject
```

Do not weaken existing guards.

### Missing PostgreSQL server

```text
→ clear unavailable result
→ no fallback
```

### Schema behind

```text
check
→ behind, zero mutation

apply
→ explicit upgrade
```

### Existing database with user data

```text
→ no reset
→ no DROP
→ migrations only
→ import replay/conflict laws preserved
```

### Legacy Runbook conflict

```text
same document UUID
different persisted semantic truth
→ conflict
→ no overwrite
```

### No legacy Runbook

```text
DB/schema READY
Runbook count 0
→ Play content NOT READY
→ no fake seed
```

### Existing Run

```text
bootstrap
→ does not alter Run
→ normal Play resume remains authoritative
```

---

## §17 Acceptance rubric

Merge only when all are true:

* [ ] BF3A completion is recorded truthfully.
* [ ] CON-READY roadmap/steward mirrors are synchronized.
* [ ] DF0 is sequenced before BF3B.
* [ ] One explicit `check` command exists.
* [ ] `check` is demonstrably read-only.
* [ ] One explicit `apply` command exists.
* [ ] Missing DSN remains fail-closed.
* [ ] World Graph DSN is never used as fallback.
* [ ] Full DSN/password is never printed.
* [ ] Standard missing local Buddy DB can be explicitly provisioned.
* [ ] Arbitrary missing DB names are not automatically created.
* [ ] No database/schema reset path exists.
* [ ] Migration remains explicit operator action.
* [ ] Server startup does not migrate.
* [ ] Server startup does not import legacy state.
* [ ] Existing Runbook importer is reused rather than reimplemented.
* [ ] Legacy identity/revision/digest are preserved.
* [ ] Import replay is idempotent.
* [ ] Import conflict fails closed.
* [ ] Bootstrap never fabricates a Runbook.
* [ ] Bootstrap never creates/selects a Play Run.
* [ ] Startable committed Runbook readiness is checked.
* [ ] Zero-Runbook state is truthful.
* [ ] Obsolete “Plan kind cannot use application state” copy is removed.
* [ ] Local developer setup is discoverable from normal docs.
* [ ] Play gives an actionable development hint when APP-STATE is unavailable.
* [ ] Real disposable PostgreSQL evidence passes.
* [ ] Actual workspace/Play production seams consume bootstrapped state.
* [ ] Actual operator dogfood reaches BF3A Current Moment.
* [ ] Reload proves the current Scene remains durable.
* [ ] No BF3B Decision UI landed.
* [ ] No Combat/Agent/CUTOVER scope landed.
* [ ] Every changed file is inside §8.
* [ ] Exact-head evidence is recorded before review.

---

## §18 Stop conditions

Stop and report if implementation requires:

* changing the APP-STATE database authority model;
* making the DSN optional at runtime;
* deriving Buddy authority from World Graph configuration;
* migrating on ordinary FastAPI startup;
* importing on ordinary FastAPI startup;
* changing Alembic revisions already applied;
* changing WorkObject / WorkRevision schemas;
* changing Play Run schema;
* changing manifest schema;
* modifying existing Runbook import semantics;
* seeding arbitrary Markdown as a Runbook;
* creating a new public backend readiness endpoint;
* a new frontend global notification framework;
* Plan migration work;
* BF3B controls;
* Combat;
* Agent Interaction;
* CUTOVER paths;
* any active-lane lease collision.

Report:

```text
Stop condition:
Observed dogfood path:
Why DF0 cannot absorb it:
Owning authority:
Missing seam:
Mutation required:
Evidence that would prove it:
Proposed successor/split:
```

Do not widen silently.

---

## §19 Named successor

### PLAN-BLANK-SHELL — zero-material Plan authoring + local→durable promotion

DF0 proved:

```text
normal local setup
→ Play
→ real Runbook
→ real Run
→ BF3A
```

PLAN-BLANK-SHELL owns the Plan-side prerequisite for BF4A native Runbook
reopen/save: bare `/plan` must be a valid editable shell before Runbook authoring
can reuse the same Surface Interaction contract.

### BF3B — Decision interaction and visible relevance

BF3B remains blocked on BF4A after PLAN-BLANK-SHELL completes.

```text
Decision
→ Options
→ explicit select/change/clear
→ authored consequence
→ re-derived emphasis
→ no automatic navigation
```

The rationale for the sequencing correction is simple:

> **Do not add more table capability behind a door the operator cannot yet
> reliably open.**

---

## Review amendments — Cycle 1

Reviewed against head `d811d1ed2400122dbb465357f1ea4f529c2825ee` as GitHub review `5042593573`.

Do not treat this section as a rewrite of the original dispatch. The original
body above remains the DF0 bootstrap contract. These amendments correct the
zero-to-first-Runbook product path that the original “no fake Runbook” rule
over-constrained.

### Preserved prohibition

Bootstrap `check` / `apply` must **not** silently seed content. Legacy import
must not fabricate history. Zero leftover committed Runbooks remains a truthful
`PLAY CONTENT NOT READY` / `NOT READY` bootstrap result.

### Required product path

Empty Play must offer an explicit first-class action through existing Content /
workspace APIs, not through bootstrap:

```text
Start a Run

No active Runbooks are available.

[ Create blank Runbook ]
```

“Blank” is the smallest legitimate Playable document, not an empty WorkObject:

```text
Blank Runbook
└── Untitled Beat
    ├── no Scenes
    ├── no Decisions
    ├── no Options
    └── no campaign/example content
```

Create/commit a Runbook WorkObject and one canonical v2 Beat with a generated
stable Beat ID. Do **not** automatically start a Play Run. `Start exact Run`
remains the operator's Runtime transition.

Campaign identity comes from real current product context (World Graph lens
only when focus validation is `valid`) or an explicit operator choice. Do not
hardcode `longmont-c2` and do not infer a campaign from fixture paths.

### Cycle 2 operator witness

```text
bootstrap apply
→ /play
→ no Runbooks
→ Create blank Runbook
→ committed Runbook appears
→ Start exact Run
→ native READY
→ current Beat = Untitled Beat
→ current Scene = null
→ BF3A Beat-only Current Moment
→ reload/resume
```

### Additional write lease

| Action | Path | Purpose |
| ------ | ---- | ------- |
| Create | `apps/live-control-ui/src/playSurface/blankRunbook.ts` | blank v2 markdown + create/commit composition |
| Create | `apps/live-control-ui/src/playSurface/blankRunbook.test.ts` | starter shape and campaign-required proof |
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.tsx` | Create blank Runbook control |
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | blank-create campaign field layout |
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx` | empty-state create; does not start a Run |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | pass real product campaign context when valid |
| Modify | `Docs/Runbooks/RUNBOOK-local-play-dogfood.md` | Cycle 2 empty-Play create path |
| Create | `tests/test_blank_runbook_play_path.py` | HTTP create/commit then standard Start Run path |

The original §8 denylist still holds: do not modify import seams, Content
repository/service, play schema, FastAPI lifespan, Combat, Agent, or CUTOVER.
Creating a blank Runbook uses existing `POST /workspace-documents` and TipTap
prepare/commit. Pathless Runbook Content receipts are already supported.

### Still forbidden

```text
migrate-on-boot
import-on-boot
bootstrap fake/sample Runbook
auto-start after create
hardcoded longmont-c2
fixture-path campaign inference
APP-STATE schema change
new backend persistence model
BF3B / Combat / Agent / CUTOVER
```

## Review amendments — Cycle 2

Reviewed against head `a9dccd57baca51f01da26ef33fcd5dc6228f10ca` as GitHub review `5046232550`.

Do not treat this section as a rewrite of the original dispatch or the Cycle 1
product-path correction. Cycle 1 remains the blank-Runbook contract. These
amendments make that create path retry-safe after the first WorkObject exists,
and require the real zero-content browser witness on the PR.

### Retry-safe Create blank Runbook

After `POST /workspace-documents` returns an ID, retain

```text
{documentId, beatId, markdown, expectedRevision, campaignId}
```

and retry/reconcile that exact document. Do not POST a replacement WorkObject
because a later prepare, commit, or list-refresh step failed or lost its
response.

Contract:

```text
create WorkObject once
→ retain exact document + starter bytes
→ retry prepare/commit against that document
→ if commit response is uncertain, GET the exact document and
  accept matching committed bytes as success
→ once commit succeeds, that is success
→ list refresh is reconciliation, not part of the create transaction
```

A list-refresh failure must not present create failure or invite a duplicate
POST. The committed record is shown and selected locally so Start exact Run
remains available.

The pre-existing generic case where the initial create POST itself succeeds
but its response is lost is out of scope. This blocker starts once the client
has received the first document ID.

### Cycle 3 operator witness

The Cycle 1 amendment's zero-content path remains mandatory and must be
recorded on the PR for the reviewed head, not only as local HTTP tests:

```text
bootstrap apply
→ /play
→ no Runbooks
→ Create blank Runbook
→ committed Runbook appears
→ Start exact Run
→ native READY
→ current Beat = Untitled Beat
→ current Scene = null
→ BF3A Beat-only Current Moment
→ reload/resume
```

### Additional tests on the Cycle 1 lease

Focused failure tests live in the already-leased Play files:

- prepare failure then retry of the same WorkObject
- lost/uncertain commit reconciliation of the exact document
- commit success with failed Runbook list refresh

No new backend persistence model. No bootstrap fake content. No auto-start.

## Completion

PR #657 merged.

Accepted implementation head:
  dc20fe8e63eec691265e75eb73c69f441ffd779d

Merge:
  87a769d05605ff021d28f0b69c5d7ab0b8205440

Formal review cycles:
  3

DF0 outcome:
  DONE

Real operator witness:
  zero startable Runbooks
  → Create blank Runbook
  → Start exact Run
  → Beat-only Current Moment
  → reload/resume

Successor sequencing discovery:
  BF3B remains the next table capability, but its real Decision-bearing
  dogfood material is not product-reachable yet.

Immediate predecessor:
  BF4A — native Runbook authoring gateway

