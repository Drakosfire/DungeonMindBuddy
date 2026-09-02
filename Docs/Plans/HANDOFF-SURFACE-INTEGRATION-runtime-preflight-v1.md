---
pr_body_template: |

## Handoff pointer

* Conversation/workstream: SURFACE-INTEGRATION / SI-1
* Flow: SURFACE-INTEGRATION
* Direction: DESIGN → CODE → REVIEW
* Handoff: `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-runtime-preflight-v1.md`
* Branch / PR: `agent/surface-integration-runtime-preflight-v1` / `SURFACE-INTEGRATION: prove assembled runtime readiness`

## Verification pointer

* Base: `24f7c25b49fdab8271b0d84d36e4a609b9832d69`
* Dogfood evidence: `dogfood/of-conks-end-to-end` at `b40d893f58f4aeeb0de605b7b13a3b18389a0908`
* Changed paths: HANDOFF §4
* Verification: HANDOFF §7

The checked-in handoff, cumulative diff, nano-commit story, and independently
rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Canonical assembled-runtime preflight v1

**Created:** 2026-09-01
**Status:** ACTIVE — first SURFACE-INTEGRATION implementation slice
**Canonical handoff path:** `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-runtime-preflight-v1.md`
**Conversation/workstream:** `SURFACE-INTEGRATION / SI-1`
**Flow / owner:** `SURFACE-INTEGRATION`
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** `24f7c25b49fdab8271b0d84d36e4a609b9832d69`
**Evidence branch:** `dogfood/of-conks-end-to-end` at `b40d893f58f4aeeb0de605b7b13a3b18389a0908`
**PR title:** `SURFACE-INTEGRATION: prove assembled runtime readiness`

> Repository law: [`AGENTS.md`](../../AGENTS.md). This slice consumes the failed Of Conks end-to-end demo as architecture evidence. It does not continue feature development on the dogfood branch.

---

## §0 Steward ruling — DungeonBuddy feature freeze

DungeonBuddy enters a temporary product-development freeze for the duration of the SURFACE-INTEGRATION program.

The failure that triggered this program is not classified as ordinary demo polish.

The 2026-09-01 Of Conks dogfood proved that independently correct subsystems and individually passing journey stations do not guarantee that the assembled product is runnable from a real developer/operator environment.

Three concrete failures expose one underlying problem:

```text
World Graph authority existed in DungeonMind PostgreSQL
but a fresh coding-agent/worktree could not identify where the authoritative
runtime data lived.

Ingested-world authority existed
but Ingest Review saw zero file-backed run manifests in that worktree.

A World Graph projection reached READY
but Plan Edit rendered a forever-loading panel because presentation publication
captured stale state across a non-reactive boundary.
```

Therefore:

> **DungeonBuddy does not yet have a sufficiently explicit contract for how an assembled runtime discovers its authorities, reports their availability, and supplies changing information to product Surfaces.**

Until that contract is proven, additional surface capability risks creating more local information-delivery mechanisms that will later need to be reconciled.

### Freeze rule

No new DungeonBuddy product capability slice may be dispatched outside SURFACE-INTEGRATION until the program reaches its assembled-runtime acceptance gate.

Paused work includes, but is not limited to:

* PLAY-SURFACE BF3C / additional contextual inventory;
* Roll interaction extraction;
* prepared Encounter extraction;
* additional Combat integration;
* source-relative asset productization;
* additional Ingest UX/capability;
* new Agent Interaction capability beyond disposition of the already-open #674;
* opportunistic Plan/Build/Play UX improvements.

Allowed work during the freeze:

* SURFACE-INTEGRATION implementation and design;
* fixes directly required by a SURFACE-INTEGRATION owning-boundary witness;
* investigation/mining of existing dogfood branches;
* critical correctness/security repair;
* backward-looking repository authority synchronization;
* independent DungeonMind library work that does not change DungeonBuddy's consumed contract.

### Existing active PR #674

PR #674, `AGENT-INTERACTION: enable truthful Play Ask`, is **PARKED**, not discarded.

Its existing branch and evidence remain valid inputs. Do not extend it while this slice is active.

Its changed paths are read-only to this lane unless the steward explicitly transfers ownership.

The eventual disposition of #674 occurs after the Surface Information Contract is established:

```text
rebase/adapt/merge
or
mine useful behavior into a successor
```

Do not merge #674 merely to clear the queue.

---

# §1 Mission and merge-ready invariant

## Mission

An operator or coding agent can run one canonical DungeonBuddy preflight against the environment they are actually about to use and receive a truthful, actionable description of whether the assembled runtime has the authorities and persistent data required to start product work.

## Merge-ready invariant

Given one explicit runtime environment, preflight must identify the actual configured authority/storage dependencies used by mounted DungeonBuddy, interrogate those dependencies through their accepted owning seams, and return:

```text
READY
```

only when the required runtime foundations are usable.

Otherwise it returns:

```text
NOT READY
```

with the specific failed dependency, observed configuration/location, and reason.

It must never convert:

```text
missing local files
wrong database
empty fresh database
unconfigured authority
dependency unavailable
invalid schema
unrecognized world
```

into a misleading success or generic “nothing found.”

### Critical distinction

This PR establishes:

```text
"What assembled runtime am I actually connected to,
and can its foundational authorities be used?"
```

It does **not** yet establish:

```text
"How does every React Surface subscribe to changing information?"
```

That is SI-2, the named successor.

### Pre-dispatch critique

| Question                                                | Answer                                                                                                                                                                                                          |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern every claimed observable path? | Yes. Every check answers whether this exact configured assembled runtime can truthfully identify/use a foundational dependency.                                                                                 |
| Most likely adversarial sequence                        | Fresh worktree → inherited/partial env → fresh PostgreSQL or missing ingest files → product starts anyway → operator assumes existing campaign data is gone.                                                    |
| Will §7 detect that failure?                            | Yes. Evidence must run preflight from an intentionally incomplete/fresh environment and prove NOT READY with the exact missing/misdirected dependency.                                                          |
| Easiest owning boundary to under-test                   | Database identity/content. Merely proving a TCP connection or schema exists is insufficient; expected world/head discovery must cross the accepted DungeonMind repository/application boundary.                 |
| Fact that forces stop/split                             | Implementing truthful discovery requires changing durable authority ownership, inventing a generic Surface state contract, or repairing Ingest persistence semantics rather than reporting their current state. |

---

# §2 Context, authority, and lane

| Field                    | Required content                                                                                                                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent authority         | `Docs/Roadmaps/ROADMAP-con-ready.md`; `Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md`; `AGENTS.md`                                                                                                |
| New program authority    | Create `Docs/Roadmaps/ROADMAP-surface-integration.md` in this PR as the active blocking child roadmap of CON-READY                                                                                     |
| Base revision            | `24f7c25b49fdab8271b0d84d36e4a609b9832d69`                                                                                                                                                             |
| Dogfood evidence         | `dogfood/of-conks-end-to-end` @ `b40d893f58f4aeeb0de605b7b13a3b18389a0908`; especially OC-020, OC-021, OC-022, OC-024 and §11                                                                          |
| Predecessor contract     | CUTOVER has made DungeonMind/PostgreSQL living World Graph authority; APP-STATE owns durable product state; mounted Buddy graph reads are DungeonMind-only                                             |
| Exact input consumed     | Current process environment + accepted Buddy configuration helpers + existing authority/application-state read seams + filesystem registry configuration where such state is currently file-discovered |
| Named successor          | SI-2 — Surface Information Contract v1                                                                                                                                                                 |
| What remains false       | A Surface can still receive stale/non-reactive state; Ingest persistence semantics remain unresolved; assembled browser journey is not yet the merge gate                                              |
| Branch                   | `agent/surface-integration-runtime-preflight-v1`                                                                                                                                                       |
| Parallel lanes           | #674 is parked/read-only; dogfood branch is evidence-only and must not be developed further                                                                                                            |
| Runtime/state ownership  | Preflight is read-only. It must not initialize, migrate, seed, adopt, repair, or mutate runtime state.                                                                                                 |
| State-authority sync set | `Docs/Roadmaps/ROADMAP-con-ready.md`, new `Docs/Roadmaps/ROADMAP-surface-integration.md`, and any current sequencing authority that explicitly claims another DungeonBuddy feature is active           |

### Governing architectural premise

Authorities remain separate:

```text
DungeonMind
  World Graph / source-evidence authority

Buddy APP-STATE
  Plan / Runbook / Run / Runtime application authority

Source/workspace storage
  product-local rich source bytes

Ingest execution/registry
  current ingest discovery mechanism

Combat
  separate Combat-owned runtime

Agent
  invocation/context/trace behavior
```

SI-1 does not consolidate these authorities.

It makes their presence and configured identity observable.

### DungeonMind enumeration dependency (Review Cycle 2 split)

SI-1 world enumeration in Buddy depends on read-only authority enumeration ports
(`list_heads`, `list_world_ids`) landing in DungeonMind first:

```text
DungeonMind PR: feature/authority-read-enumeration-v1 @ ef39120
Buddy pin:      reverted to pre-enumeration main (5ca5d68) until that PR merges
Buddy behavior: list_world_heads → enumeration_unavailable → NOT_CONFIGURED
Post-merge:     re-pin Buddy to the accepted enumeration revision
```

Until the DungeonMind enumeration slice merges, `--require-world` integration
witnesses against a live PostgreSQL DSN report `NOT_CONFIGURED` on
`dungeonmind_world` rather than `NOT_READY` for a missing world.

---

# §3 Observable paths and adversarial sequences

## 3.1 Canonical preflight invocation

Implement one supported command from the repository root.

Prefer an existing project CLI/tooling convention if one exists after bounded discovery.

Expected operator shape:

```bash
uv run <canonical-preflight-command>
```

Do not require bespoke Python snippets, `psql`, browser DevTools, or manually reading environment variables.

The command must exit:

```text
0  READY
non-zero  NOT READY
```

Machine-readable output may be provided as an option if cheap, but human-readable terminal output is required.

Do not introduce a network health endpoint in this slice unless the existing command seam cannot prove the mission.

## 3.2 Minimum checks

### A. Buddy application-state authority

Preflight must establish:

```text
configured APP-STATE database identity/location
connection usable
required schema/migrations usable
read-only representative application-state query succeeds
```

It does not require Plans/Runbooks/Runs to exist.

An empty but valid APP-STATE database may be READY.

The output must make emptiness visible.

### B. DungeonMind World authority

Preflight must establish:

```text
mounted authority mode == dungeonmind
configured DungeonMind authority DSN exists
connection/repositories usable
recognized worlds can be discovered
recognized genesis/head integrity holds
current heads can be read
```

For the operator's current development environment, output should list discovered worlds and current heads.

Example:

```text
DungeonMind World Graph       READY
  database                    postgresql://…/dungeonmind
  eldyrwild                   rev:680c...
  of-conks-cons               rev:9920...
```

Credentials/passwords must be redacted.

Do not hardcode those two worlds as readiness requirements.

A valid newly initialized environment with other worlds may still be structurally READY.

But a database with zero worlds must say so explicitly:

```text
READY — 0 worlds
```

rather than implying the expected campaign data is present.

Provide an optional expected-world check if an existing configuration/argument seam can support it without inventing a second capability.

Example:

```bash
... --require-world eldyrwild
```

Then zero/missing required world is NOT READY.

### C. Campaign/world registry

If the currently accepted mounted product can enumerate campaign/world bindings through an existing authority seam, preflight reports them.

Do not copy a frontend campaign map into the preflight.

If the only truthful implementation available is the currently dogfood-only OC-022 registry code, do not silently transplant that whole capability here. Stop and report whether it should be separately mined or can be consumed through an already accepted backend seam.

### D. Ingest discovery

Preflight must run the same discovery logic the mounted Ingest surface currently relies upon.

It reports:

```text
configured/search roots
number of discovered runs
whether roots exist
whether discovery itself errored
```

Example:

```text
Ingest registry              READY / EMPTY
  root                       /repo/evals/...
  discovered runs            0
```

Important:

```text
0 runs
```

is not automatically infrastructure failure.

But:

```text
configured root missing
registry unreadable
manifest parse/integrity failure
```

must be NOT READY for that dependency.

The command must make the distinction between:

```text
valid empty registry
and
registry unavailable/misconfigured
```

visible.

SI-1 does not decide whether file-backed ingest manifests are the correct durable architecture.

### E. Product-local source roots

Report currently configured source/workspace roots needed by mounted source-opening behavior, including whether they exist and are readable.

Do not scan arbitrary host filesystem locations.

Do not infer source authority from `out/`.

### F. Frontend/backend processes

Not a required SI-1 readiness dependency.

Preflight is primarily a **pre-start/runtime-foundation** check.

If process/port checking falls naturally out of an existing supported mechanism, it may be displayed as informational only.

Do not turn this slice into process supervision.

---

## 3.3 Required state vocabulary

Each dependency reports one of a small closed vocabulary:

```text
READY
EMPTY
NOT_CONFIGURED
UNAVAILABLE
INTEGRITY_ERROR
NOT_READY
```

Use fewer states if the implementation proves a smaller vocabulary is sufficient.

Do not expose raw internal exception classes as the primary operator contract.

Every non-ready state includes:

```text
dependency
observed location/configuration
stable reason/code
short operator-facing explanation
```

Sensitive values are redacted.

### Overall disposition

Overall:

```text
READY
```

only when all dependencies classified as **required runtime foundations** are READY or validly EMPTY according to their own contract.

Informational/optional dependencies do not fail the overall status.

The implementation must explicitly classify every check as required or informational.

---

## 3.4 Adversarial sequences

| Sequence                                                                | Required safe outcome                                                                                                         | Owning proof                                 |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Fresh worktree → ignored `out/` absent → preflight                      | Must not report missing World Graph. Mounted authority is DungeonMind; old Buddy files are irrelevant.                        | CLI integration test / live witness          |
| Correct code → wrong fresh DungeonMind DB → `--require-world eldyrwild` | NOT READY; name configured DB safely; report missing required world.                                                          | PostgreSQL integration                       |
| Correct persistent DungeonMind DB → no ingest manifests in worktree     | World Graph READY; Ingest registry EMPTY or NOT READY according to actual root validity. Never collapse into “graph missing.” | CLI integration/live witness                 |
| DungeonMind DSN unset                                                   | NOT_CONFIGURED / overall NOT READY. No fallback to Buddy files.                                                               | focused test                                 |
| DungeonMind DB unavailable                                              | UNAVAILABLE / NOT READY. No fallback.                                                                                         | failure injection                            |
| DB has head without recognized genesis                                  | INTEGRITY_ERROR / NOT READY.                                                                                                  | existing DungeonMind binder semantics reused |
| Ingest root does not exist                                              | explicit registry/path failure; no “0 runs” ambiguity                                                                         | focused test                                 |
| Source root missing                                                     | explicit source-root diagnostic                                                                                               | focused test                                 |
| Password-bearing DSN                                                    | output redacts secrets                                                                                                        | unit test                                    |
| Run preflight twice                                                     | same environment gives semantically equivalent result; zero writes                                                            | mutation/DB witness                          |

---

# §4 Files in scope — write lease

The implementation agent must perform bounded discovery before finalizing this list, but expected ownership is:

| Action             | Path                                                                                                      | Purpose                                                                                                    |
| ------------------ | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Create             | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-runtime-preflight-v1.md`                                          | This implementation contract                                                                               |
| Create             | `Docs/Roadmaps/ROADMAP-surface-integration.md`                                                            | Active blocking program roadmap/freeze authority                                                           |
| Modify             | `Docs/Roadmaps/ROADMAP-con-ready.md`                                                                      | Record SURFACE-INTEGRATION as blocking child before further feature dispatch                               |
| Create             | `apps/live_control_server/services/runtime_preflight.py` or nearest existing server-neutral tooling owner | Compose read-only preflight checks                                                                         |
| Create             | `scripts/<canonical-preflight-command>.py` or nearest existing CLI owner                                  | Supported operator entry point                                                                             |
| Create             | `tests/test_runtime_preflight.py` or owning equivalent                                                    | Core state/failure/redaction evidence                                                                      |
| Create             | `tests/integration/test_runtime_preflight_postgres.py` or nearest existing PostgreSQL integration suite   | Exact DB/world/head witness                                                                                |
| Modify if required | `apps/live_control_server/config.py`                                                                      | Consume/expose existing configuration through one stable read seam only; do not change authority semantics |
| Modify if required | existing Ingest registry discovery module                                                                 | Only to expose current read-only status in a reusable way; no persistence redesign                         |

### Bounded discovery exception

```text
Directories:
  apps/live_control_server/
  scripts/
  tests/
  Docs/Roadmaps/
  Docs/Plans/

Maximum additional production paths:
  8

Allowed path kinds:
  existing configuration readers
  existing APP-STATE repository/service constructors
  existing DungeonMind integration constructors
  existing ingest-run registry readers
  existing source/workspace-root configuration

Decision rule:
  a discovered path may be edited only when required to expose existing
  read-only status through the preflight. If the edit changes authority,
  persistence, product behavior, surface behavior, startup behavior, or
  durable schema, STOP/SPLIT.
```

Before editing an unlisted production path, record in the handoff:

```text
path
dependency/check requiring it
existing owner
why read-only composition cannot avoid the edit
whether #674 or another lane owns it
```

---

# §5 Explicitly out of scope / collision boundary

| Path / domain                                                                                  | Why this slice must not touch or claim it                                               |
| ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `dogfood/of-conks-end-to-end`                                                                  | Frozen evidence branch. Do not continue implementation there.                           |
| #674 leased paths under `agentInteraction/**`, Agent query/runtime services, Play Agent plugin | Parked active PR; Surface Information successor decides disposition                     |
| `apps/live-control-ui/**`                                                                      | No frontend Surface contract in SI-1                                                    |
| `playSurface/**`                                                                               | BF3B is accepted; BF3C frozen                                                           |
| `combat/**` / Combat persistence                                                               | Separate authority and later integration                                                |
| Markdown reader/source asset policy                                                            | OC-019 successor, frozen                                                                |
| Roll/table product implementation                                                              | OC-015 successor, frozen                                                                |
| Encounter projection implementation                                                            | OC-016 successor, frozen                                                                |
| DungeonMind schema/migrations                                                                  | Preflight consumes existing public/repository contracts; does not alter World authority |
| APP-STATE migrations/schema                                                                    | Read and report only                                                                    |
| Ingest persistence redesign                                                                    | SI-1 reports current truth; SI-4 resolves architecture                                  |
| Generic `SurfaceInformation<T>` implementation                                                 | SI-2                                                                                    |
| AppChrome rich-panel repair                                                                    | SI-2/SI-3 after contract decision; OC-020 remains a required design witness             |

### #674 collision

At minimum, treat these active areas as read-only while #674 remains open:

```text
apps/live-control-ui/src/agentInteraction/**
apps/live-control-ui/src/playSurface/PlayAgentInteractionPlugin*
apps/live-control-ui/src/playSurface/playAgentQueryContext*
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_query.py
apps/live_control_server/services/agent_play_surface_context.py
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_query.py
```

If current #674 changed-file truth differs, re-anchor from GitHub before editing.

---

# §6 Implementation contract

```text
Input:
  process environment
  Buddy accepted configuration
  existing APP-STATE read seam
  existing DungeonMind authority/repository read seam
  existing ingest-run discovery
  existing source/workspace root configuration

Output:
  one bounded RuntimePreflightReport
  one human-readable CLI rendering
  deterministic exit status

Invariant:
  report the actual configured assembled-runtime foundations truthfully;
  never infer success from repo files, defaults that are not mounted authority,
  or the mere presence of code.

Failure behavior:
  missing configuration      → NOT_CONFIGURED
  dependency connection fail → UNAVAILABLE
  durable integrity failure  → INTEGRITY_ERROR
  valid empty store          → EMPTY where explicitly legal
  required expected identity absent → NOT_READY

Replay / idempotency:
  same environment → semantically equivalent report
  changed environment → report reflects the new actual dependency
  retry after dependency recovery → READY when owning reads succeed

Trust boundary:
  Verifies:
    configured dependency can be reached through its accepted read seam
    required schema/repository read is usable
    discovered worlds/heads are real returned authority state
    ingest roots/runs are what current registry discovery observes
    configured filesystem roots exist/read where required

  Records/trusts without proving:
    semantic correctness of World content
    completeness of an ingest run
    usefulness of source prose
    browser UX correctness
    surface reactivity
    Combat readiness
    Agent correctness
```

## 6.1 No mutation

Preflight must be read-only.

Forbidden:

```text
alembic upgrade
schema creation
database creation
world adoption
world initialization
campaign creation
seed data
source import
ingest regeneration
Runbook bootstrap
Run creation
repair
fallback hydration
```

If readiness requires mutation, report the missing prerequisite and exit non-zero.

A later explicit setup command may perform mutations. Preflight is not that command.

## 6.2 Redaction

Never print passwords, tokens, API keys, or full secret-bearing DSNs.

Allowed diagnostic example:

```text
postgresql://dungeonmind:***@localhost:54329/dungeonmind
```

Prefer a normalized:

```text
host / port / database
```

representation over echoing the DSN.

## 6.3 Report shape

Use a typed internal result rather than constructing terminal strings throughout individual checks.

Illustrative only:

```text
RuntimePreflightReport
  status
  checks[]

RuntimePreflightCheck
  id
  label
  required
  status
  summary
  details
```

Do not freeze these names if an existing project convention is better.

The important contract is:

```text
typed result
→ rendering
```

rather than:

```text
every subsystem prints arbitrary text
```

This typed report is deliberately **not** the future Surface Information Contract. It is operator/runtime diagnostic state.

---

# §7 Evidence required to merge

| Guarantee                                             | Owning boundary               | Evidence                        | Required scenario                                                                   |
| ----------------------------------------------------- | ----------------------------- | ------------------------------- | ----------------------------------------------------------------------------------- |
| Preflight is read-only                                | DB/filesystem/runtime         | integration/adversarial         | Snapshot durable counts/heads before and after repeated preflight; unchanged        |
| Mounted World authority is identified correctly       | DungeonMind integration       | PostgreSQL integration          | Real adopted world → exact current head returned                                    |
| No Buddy-file fallback                                | config/integration            | adversarial                     | `out/` absent while valid DungeonMind DB exists → World check READY                 |
| Wrong/fresh DB is obvious                             | DungeonMind integration       | integration                     | Fresh valid DB + `--require-world eldyrwild` → NOT READY (or NOT_CONFIGURED while enumeration pin is split) |
| DB unavailable is truthful                            | dependency boundary           | failure injection               | unreachable DSN → UNAVAILABLE                                                       |
| Integrity failures stay fail-closed                   | DungeonMind binder/repository | integration or accepted fixture | contradictory genesis/head → INTEGRITY_ERROR                                        |
| APP-STATE read readiness is real                      | APP-STATE owning repository   | integration                     | valid empty DB may report READY/EMPTY without creating rows                         |
| Ingest empty vs broken are distinct                   | ingest registry               | focused test + live witness     | existing empty root != missing/unreadable root                                      |
| Source root status is explicit                        | filesystem config             | focused test                    | missing configured root is visible                                                  |
| Secrets are redacted                                  | renderer                      | unit test                       | secret-bearing DSN never appears raw                                                |
| Exit status is useful                                 | CLI                           | CLI test                        | READY=0; required failure !=0                                                       |
| Real current environment can explain today's incident | assembled runtime             | manual/live dogfood             | persistent DungeonMind data identified; ingest-run absence independently identified |

### Exact verification floor

Implementation agent resolves exact repository commands after bounded discovery, but minimum expected floor is:

```bash
uv run pytest tests/test_runtime_preflight.py -q
uv run pytest tests/integration/test_runtime_preflight_postgres.py -q
uv run ruff check <touched python paths>
uv run pyright
git diff --check
git diff --name-only 24f7c25b49fdab8271b0d84d36e4a609b9832d69...HEAD
```

If PostgreSQL integration requires a repository-standard test DSN, use that existing convention rather than inventing another one.

### Required real-environment witness

Against the development environment containing the migrated Eldyrwild authority:

```text
1. Run canonical preflight from the implementation worktree.
2. Record the redacted DungeonMind database identity.
3. Record discovered Eldyrwild current head.
4. Record whether Of Conks exists and its head if present.
5. Record APP-STATE status.
6. Record Ingest registry roots and discovered-run count.
7. Record source/workspace root status.
8. Confirm no mutation occurred.
```

Then run one adversarial witness using a fresh/empty or intentionally wrong designated database:

```text
--require-world eldyrwild
→ NOT READY (NOT_CONFIGURED on dungeonmind_world while Buddy awaits DungeonMind enumeration PR merge)
→ missing required world clearly identified once enumeration pin is restored
→ no fallback to repository graph_data or out/
```

**Split dependency note:** PostgreSQL integration for `--require-world` uses
`truncate_dungeonmind` on the cutover test DSN without mocking
`list_world_heads`. With the pre-enumeration Buddy pin, expect
`enumeration_unavailable` → `NOT_CONFIGURED`. Re-run after re-pinning to the
merged enumeration revision to witness `NOT_READY` / `required_world=eldyrwild`
on an empty migrated database.

This is mandatory.

### Dogfood acceptance statement

The PR is not merge-ready if a coding agent can still plausibly conclude:

```text
"The graph is gone."
```

when the actual condition is:

```text
"I am connected to the wrong/fresh database."
```

or:

```text
"I have not configured the authoritative database."
```

Likewise, it is not merge-ready if:

```text
0 ingest runs
```

cannot be distinguished from:

```text
ingest registry unavailable/misconfigured
```

---

# §8 Required roadmap artifact

Create:

`Docs/Roadmaps/ROADMAP-surface-integration.md`

It should remain concise and establish the program sequence without prematurely designing later slices.

Required sequence:

```text
SI-1  canonical assembled-runtime preflight       ← THIS PR

SI-2  Surface Information Contract v1
      derive authority/scope/status/generation/reactivity semantics
      from OC-020 + SI-1

SI-3  graph lens reference implementation
      Plan/Build rich panel consumes live information correctly

SI-4  Ingest information-provider disposition
      resolve durable registry vs execution artifact semantics

SI-5  cross-surface adoption
      Plan / Build / Play / Ingest / Agent / Combat-facing projections

SI-6  clean-start assembled-product witness
      canonical runtime → browser journey → restart/reload

SI-7  thaw + re-sequence paused feature roadmaps
```

The roadmap must state:

```text
No DungeonBuddy feature thaw before SI-6 acceptance.
```

Do not pre-mark any successor `DONE`.

## CON-READY intersection

Update `ROADMAP-con-ready.md` only enough to make this blocking relationship truthful:

```text
CON-READY remains the GM-visible acceptance authority.

SURFACE-INTEGRATION is its active blocking child program.

Existing feature stories remain valid but feature dispatch is frozen until
SI-6 proves the assembled runtime and information-delivery contract.
```

Do not rewrite CON-READY's user stories.

---

# §9 Required review handback

Record:

1. review cycle number and exact head SHA;
2. §1 invariant disposition;
3. actual canonical command;
4. exact typed report/status vocabulary;
5. actual checks classified required vs informational;
6. real development environment witness;
7. adversarial wrong/fresh-DB witness;
8. proof that preflight performed zero durable mutations;
9. redaction evidence;
10. actual changed paths vs §4;
11. #674 collision disposition;
12. baseline failures;
13. whether any current runtime assumption was discovered to be undocumented;
14. named successor SI-2 remains false;
15. whether the feature freeze still stands unchanged.

---

# §10 Acceptance rubric

* [ ] One canonical command reports assembled-runtime foundation readiness.
* [ ] World authority comes from mounted DungeonMind configuration, never repo-file inference.
* [ ] APP-STATE readiness is inspected through its accepted read boundary.
* [ ] World/campaign/head information reflects the actually connected database.
* [ ] Required-world absence can be asserted explicitly.
* [ ] Ingest EMPTY and ingest unavailable/misconfigured are distinguishable.
* [ ] Configured source/workspace roots are visible and truthful.
* [ ] No readiness check mutates state.
* [ ] Sensitive configuration is redacted.
* [ ] READY returns zero; required failure returns non-zero.
* [ ] Fresh worktree with absent `out/` does not imply missing World authority.
* [ ] Wrong/fresh database does not look like lost data.
* [ ] Current development environment witness explains the 2026-09-01 demo failure modes materially better than existing startup behavior.
* [ ] `ROADMAP-surface-integration.md` establishes SI-1 → SI-7 and the feature freeze.
* [ ] CON-READY remains parent product acceptance authority.
* [ ] #674 remains parked and unmodified unless explicitly transferred.
* [ ] No generic Surface Information API has been smuggled into SI-1.
* [ ] SI-2 remains the named successor.

---

# §11 Named successor — SI-2 Surface Information Contract v1

Do not implement this successor in SI-1.

SI-1 should leave concrete runtime evidence for the next steward to answer:

> How should a product Surface observe information from multiple independent authorities without knowing storage details, capturing stale presentation state, or fabricating availability?

SI-2 must explicitly consume:

```text
OC-020
  rich panel froze because changing state was captured into a deduped
  presentation publication

OC-022
  dynamic campaign/world discovery is superior to client hardcoding

OC-024
  product-visible information may be absent because environment-local
  discovery differs from durable authority

SI-1
  canonical runtime identity, dependency status, and authority discovery
```

Likely design dimensions to settle there:

```text
scope
authority/provider
exact revision/version where meaningful
loading / ready / empty / stale / unavailable / integrity error
observation generation / freshness
reactive update contract
provenance identity
inspection/navigation identity
diagnostics
separation of information from commands/actions
```

Do not assume the final abstraction is called `SurfaceInformation<T>`.

Earn the type from the evidence.

---

# Stop conditions

Stop instead of expanding if:

* preflight requires a durable schema or migration;
* an existing authority cannot be read without mutating it;
* truthful Ingest readiness requires deciding/rebuilding Ingest persistence;
* a new frontend state/provider is required;
* OC-020 must be repaired to complete SI-1;
* #674 paths must be changed;
* a generic process supervisor/startup manager begins emerging;
* a second setup/bootstrap command is required;
* readiness starts hardcoding Eldyrwild or Of Conks as universal product requirements;
* preflight reaches directly into DungeonMind PostgreSQL tables instead of accepted DungeonMind contracts;
* preflight treats filesystem `out/` as mounted World authority;
* implementation starts defining the generic Surface Information Contract;
* more than 8 unplanned production paths are required.

Report:

```text
Stop condition:
Invariant clause affected:
Why SI-1 cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor/re-brief:
State-authority update needed:
```

---

# Final steward intent

This slice is intentionally boring.

Its value is not a prettier startup experience.

Its value is establishing this product law:

> **Before a Surface, Agent, coding agent, or human reasons about DungeonBuddy state, the assembled application must be able to say which authorities it is actually connected to and whether those authorities are usable.**

Once that is true, SI-2 can define how those authoritative observations cross into the Surfaces themselves.

Until SI-6 proves that contract through the assembled product, the DungeonBuddy feature freeze remains in force.

The key scope decision is that this PR does **not** fix OC-020. It creates the runtime truth layer first. OC-020 then becomes the primary adversarial witness for SI-2/SI-3, where we define the reactive Surface contract instead of patching one stale panel.
