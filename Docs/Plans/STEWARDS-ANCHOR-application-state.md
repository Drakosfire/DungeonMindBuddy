# STEWARD'S ANCHOR — APPLICATION STATE

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT
**Line of work / flow:** `APP-STATE`
**Created:** 2026-08-24
**Updated:** 2026-08-25
**Repository:** `Drakosfire/DungeonMindBuddy`
**Creation anchor:** `main` `54779636750ebf7a639aef8a6184cc61ead9c860` (merge of CUTOVER PR #632)
**AS0 merge:** PR #636 @ `4c90df353bfb5d0f6857357e00eb8b2b6e142257`
**AS0 accepted head:** `605445b3b839b494a82218758c465edbfe59bad9`
**AS0.1 merge:** PR #639 @ `dd09f7f707e38f9f4348b759da8cfdbbe420fd60`
**AS0.1 accepted head:** `abb3fb15f9b56e8712c07c798674d0462827677f`
**AS0.1 review:** Review Cycle 2 PASS-equivalent, review `5014814402`
**AS1 merge:** PR #641 @ `29ff1584b9f76bb5100a724a96bebbbcf8f08d12`
**AS1 accepted head:** `b42eb629e8924695af7af5a6c986f44a26dc3536`
**AS1 review:** 3 distinct-head cycles; final PASS-equivalent review `5023488870`
**AS1 execution evidence:** PR #641 comment `5415847095`
**AS2 merge:** PR #643 @ `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0`
**AS2 accepted head:** `6b1c2e77648eee6180d293c92d2c97a428e9002f`
**AS2 review:** 3 distinct-head cycles; final PASS-equivalent review `5024971680`
**AS2 exact-head evidence:** PR #643 comment `5417774447`
**AS3 merge:** PR #646 @ `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e`
**AS3 accepted head:** `913cfe0bbce4db27250afd8277e3af50712ee029`
**AS3 review:** 3 distinct-head cycles; final PASS-equivalent review `5026608908`
**AS3 exact-head evidence:** PR #646 comment `5420273265`
**Current implementation:** AS4 Play Continuity — this PR; do not mark AS4 DONE
**Named successor still false:** AS5 Play persistence demolition
**Repository law:** [`../../AGENTS.md`](../../AGENTS.md)
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)
**Primary adjacent authorities:**
[`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md),
[`../Design/DESIGN-play-current-moment-cockpit.md`](../Design/DESIGN-play-current-moment-cockpit.md),
[`../Design/DESIGN-playable-authoring-and-adoption.md`](../Design/DESIGN-playable-authoring-and-adoption.md),
[`STEWARDS-ANCHOR-cutover.md`](STEWARDS-ANCHOR-cutover.md),
[`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md)

---

## 0. Why this document exists

This is the pickup document for the steward who owns the transition from
feature-by-feature filesystem persistence to a shared DungeonBuddy application-state
substrate backed by PostgreSQL.

The project was activated while Play was frozen around the final World Graph CUTOVER.
The immediate trigger was Play: its durable state is logically well separated but is
physically spread across workspace-registry JSON, Markdown files, Run JSON records,
manifest sidecars, active-Run JSON, rebase-intent files, file locks, fingerprints, and
CAS tokens. Those mechanisms have become application-level transaction machinery.

The larger conclusion is not "move Play JSON into SQL." It is:

> **DungeonBuddy surfaces should not each invent their own persistence system. They
> should consume domain services backed by one shared transactional application-state
> substrate. PostgreSQL is the durable implementation of that substrate.**

Play is the first demanding migration consumer because it exercises immutable authored
revisions, mutable Runtime state, exact revision binding, optimistic concurrency,
transactional sealing, re-entry continuity, migration/rebase, and live-session latency.
The substrate must nevertheless be designed to serve other Buddy-owned surfaces without
turning them into Play or into one generic JSON store.

A fresh steward is expected to own this line through architecture, decomposition,
dispatch, review, migration, dogfood, and demolition of replaced filesystem authority.
Do not hand the project back after producing one schema diagram.

---

## 1. Steward mission

The steward owns this outcome:

> **Establish a Buddy-owned PostgreSQL Application State Layer through which product
> surfaces persist durable application state using domain-owned services and shared
> transaction/revision primitives; migrate Play/Playable onto it first; then use proven
> seams to move other Buddy-owned durable state without collapsing domain authority or
> rebuilding a generic filesystem in SQL.**

The successful end state is not defined by table count. It is defined by product and
authority behavior:

```text
stable domain identity for every user-relied-on Buddy object
  ↓
PostgreSQL owns durable state + asset metadata/relationships
  ↓
DungeonMindServer storage/CDN owns large binary bytes (via Asset service)
  ↓
DungeonMind owns World truth
  ↓
derived/regenerable representations remain derived unless product says otherwise
```

```text
Surface
  ↓
domain capability / service
  ↓
domain invariant + transaction boundary
  ↓
Buddy Application State Layer
  ↓
PostgreSQL (+ Asset metadata; bytes external)
```

The application state layer is not the World Graph and is not a second knowledge graph.
DungeonMind remains the durable World Graph authority.

---

## 2. Settled decisions — do not re-litigate without contradictory evidence

These decisions are the seed of the project. A design steward may refine their exact
implementation, but should not silently reverse them.

### 2.1 Shared substrate, distinct domain authorities

Accepted:

```text
one Buddy application-state substrate
→ multiple domain-owned persistence models
→ shared transaction/revision/concurrency infrastructure
```

Rejected:

```text
one generic object table
→ every surface stores arbitrary JSON
→ domain semantics move into callers
```

A shared database does not imply a shared domain model.

### 2.2 DungeonMind remains World Graph authority

The World Graph CUTOVER has crossed the authority boundary. DungeonMind PostgreSQL owns
the adopted durable World Graph and governed mutation history. Buddy continues to own
product composition and non-World application concerns.

Do **not** put Play/Plan/Combat state into DungeonMind graph tables merely because both
systems use PostgreSQL. Do **not** create SQL foreign keys from Buddy application tables
into DungeonMind authority tables. Cross-authority references use stable public IDs and
governed service contracts.

The steward must preserve the CUTOVER rule:

```text
WORLD truth → DungeonMind authority
Buddy product/runtime state → Buddy authority
```

### 2.3 Plan is the first implementation consumer; Play is the first demanding acceptance migration

Plan (`kind=plan`) is the smallest real proof of configuration, migrations, unit of
work, CAS, WorkObject/WorkRevision/WorkingCopy, import, and fail-closed behavior.
Dispatch AS1 as Plan-only after the storage-topology correction lands.

Play exposes the strongest current evidence that filesystem topology has leaked
into the product model. Use Play as the first **demanding acceptance migration**
(Run + manifest transactions, historical Playable revisions, rebase, continuity)
—not as the first implementation slice.

Do not solve Play by creating a bespoke `play.db` architecture that other surfaces
cannot reuse. Conversely, do not make the shared substrate so generic that Play
loses its exact Run/Playable semantics.

### 2.4 Keep the Play domain model unless evidence falsifies it

The reviewed Play design remains conceptually valid:

```text
SOURCE
WORLD
PLAYABLE
RUNTIME

PROJECTION sits over them
```

Beat-first Playable structure, stable semantic element identity, explicit Decisions and
Options, immutable Run binding, Runtime selections/notes/progress, derived relevance,
explicit Playable→World promotion, and Combat-owned combat state all survive this
persistence reset unless a real storage constraint disproves them.

BF1's Beat-first grammar/manifest foundation is completed predecessor infrastructure.
The persistence reset is intentionally placed before deepening BF2/BF3 Runtime and
cockpit implementation on the current file-backed store.

### 2.5 Durable Buddy application state should be database-governed

Default direction:

> **If product correctness depends on a Buddy-owned value surviving process restart,
> browser reload, checkout/worktree changes, or concurrent access, its authority should
> live behind the application-state service rather than an `out/` path, registry JSON,
> localStorage key, or ad hoc sidecar.**

Large immutable binary assets are a separate storage question. PostgreSQL should own
asset identity, metadata, digest, provenance, and references; the steward may retain an
external/blob byte store when justified. "Application state in Postgres" does not require
forcing every PDF/image/audio byte into a PostgreSQL page.

### 2.6 Domain services own invariants; surfaces never query SQL directly

Target dependency direction:

```text
React / route / Hermes capability
→ domain service
→ repository / transaction
→ PostgreSQL
```

Forbidden target architecture:

```text
surface component
→ arbitrary SQL
```

Also avoid a generic persistence API that makes every domain reconstruct its invariant
from untyped blobs.

### 2.7 PostgreSQL transactions replace application-level multi-file transactions

The current Play implementation contains forward-recovery and locking machinery because
several authoritative files must move coherently. When the relevant state lives inside
one database transaction, use the database commit boundary rather than preserving
file-intent protocols for compatibility theater.

In particular, the target architecture should eliminate the need for durable Play
rebase-intent files once Run + manifest + target Playable revision can be changed under
one database transaction.

### 2.8 Migration is not successful until replacement paths are deleted

The repository already carries the general rule that replacement paths are removed when
their replacement becomes production-ready unless a named consumer remains.

Do not end with:

```text
Postgres path + permanent file fallback + environment toggle
```

The expected pattern is:

```text
introduce
→ migrate
→ compare/dogfood
→ switch
→ fail closed on old authority
→ delete old authority/runtime machinery
```

### 2.9 Storage-independent identity law

A product object is addressed by a stable domain-level ID. Filesystem paths, corpus
paths, CDN URLs, bucket/object keys, database table coordinates, and temporary
generator output locations are storage locators or projections — not product
identity. The owning domain service resolves locators.

Do not treat path-keyed ingest staging, location corpus paths, CDN URLs, or
`out/runtime/play/*.json` filenames as terminal domain identity.

### 2.10 Four state classes and classification

Buddy durable application objects (Plan, Runbook, Run, SourceArtifact,
IngestRun, generated drafts, card projects, …) → PostgreSQL with domain-owned
schemas.

Large/binary assets → PostgreSQL metadata + digest + relationships; bytes through
Asset service to DungeonMindServer storage/CDN.

World truth → DungeonMind only.

Derived/regenerable (indexes, projections, thumbnails, caches) → may persist for
speed; persistence alone does not make authority.

Before choosing persistence, apply the classification test in
`ARCHITECTURE-application-state-layer.md` §1 (World? reload-relied-on Buddy
object? large binary? regenerable? domain lifecycle?).

WorkObject / WorkRevision / WorkingCopy remain **Content-domain** primitives for
document-like authored material — not a universal `application_object (id, type,
jsonb)` for every domain. Source owns SourceArtifact identity; Ingest is a
first-class **future** consumer with its own `ingest.*` schema (IngestRun /
processing-review) when earned.

---

## 3. Current repository truth at project creation

Re-anchor before every dispatch; the facts below are the creation snapshot, not eternal
truth.

### 3.1 World Graph CUTOVER context

Creation `main` is `54779636750ebf7a639aef8a6184cc61ead9c860`, merge of PR
#632 (`CUTOVER: pin optimized DungeonMind R.3a native reads`). The R.3a pin is
`SWITCH_READY`; DungeonMind is already living World Graph authority and Buddy local World
Graph writes are fail-closed in DungeonMind-authority mode.

This project must not compete with or reverse the final native-read switch / Buddy graph
runtime demolition. The Application State Layer is for Buddy-owned non-World state.

### 3.2 Current Play/Playable persistence inventory

At creation, inspect at minimum these seams before designing migration:

```text
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/tiptap_markdown_write.py
apps/live_control_server/routes/workspace_documents.py

apps/live_control_server/services/play_run_registry.py
apps/live_control_server/services/play_run_reference_manifest.py
apps/live_control_server/services/play_active_run.py
apps/live_control_server/services/play_run_rebase.py
apps/live_control_server/routes/play_runs.py

apps/live_control_server/services/registry_file_lock.py
src/live_play/live_store.py
```

Known durable locations include:

```text
out/registries/workspace_documents.json
out/workspace/plan/<document-id>.md
other workspace target_relpath Markdown
out/runtime/play/runs/<run-id>.json
out/runtime/play/reference-manifests/...
out/runtime/play/active-run.json
out/runtime/play/rebase-intents/<run-id>.json
```

Do not assume this list is complete. Use repository search/SymDex and runtime tracing to
inventory every product-visible persistence dependency before freezing the architecture.

### 3.3 Current logical Play state worth preserving

Current Run concepts already include:

```text
runId
campaignId
playableArtifactId
playableRevision
playableContentSha256
runRevision
progress
  currentBeatId
  currentSceneId
  resolvedBeatIds
  selections
  notesByElementId
rebasedFromRunRevision
createdAt / updatedAt
```

The v2 reference manifest separately seals Playable identity, membership, parentage, and
transition edges. Its purpose is architectural integrity, not "because files exist"; the
concept should survive even if its durable representation becomes a transactional row.

### 3.4 Current workspace document mismatch

`WorkspaceDocumentRegistry` currently combines metadata/revision identity in JSON with
content bytes in separate filesystem Markdown targets. Playable authoring therefore
relies on coherent file + registry snapshots, file fingerprints, target path authority,
and mutation locks.

The project should explicitly decide whether the shared substrate replaces path-keyed
persistence with domain-owned identity. WorkObject / WorkRevision / WorkingCopy is the
**Content-domain** primitive for document-like authored material (Plan, Runbook). It is
not a universal object model for Ingest, generated artifacts, or assets.

The starting recommendation is **yes for Content**: use WorkObject primitives for Plan
and later Runbook. Other domains earn their own schemas when a consumer proves them.

---

## 4. Target conceptual architecture

This is a design target, not permission to code tables before the first architecture gate.

### 4.1 Logical deployment

```text
                         DUNGEONBUDDY

 Plan ───────┐
 Build ──────┤
 Play ───────┤
 Combat ─────┤── domain services ── Buddy Application State Layer
 Ingest ─────┤                         │
 Recap ──────┤                         ▼
 Hermes ─────┘                     PostgreSQL
                                      │
                                      │ stable governed references
                                      ▼
                                  DUNGEONMIND
                                  World Graph authority
```

Whether Buddy and DungeonMind use one PostgreSQL server/cluster, separate databases in
one server, or separate deployable instances is a deployment decision. Authority must not
depend on physical co-location.

### 4.2 Candidate Buddy persistence families

A starting decomposition to interrogate:

```text
content.*
  work_object
  work_revision
  working_copy
  asset metadata / references (if warranted)

play.*
  run
  run_manifest
  active_run
  run_mutation        # candidate, not mandatory for first slice

combat.*
  combat_runtime
  combatant
  condition / turn state / other owned live state

other domain schemas only when a proven consumer needs them
```

Names are provisional. The steward owns the reviewed schema/API contract.

### 4.3 Work-object/revision thesis

The strongest candidate cross-surface primitive is:

```text
WorkObject
  stable identity
  kind / owner
  campaign/world scope as applicable
  title/status/metadata
  current committed revision

WorkRevision
  immutable revision identity
  canonical content
  content digest
  provenance/origin metadata
  created_at

WorkingCopy
  recoverable mutable draft
  exact base revision
  not Run-admissible committed truth
```

This model should allow:

```text
Plan edits Playable work object A
→ autosaved recoverable working copy
→ explicit Save creates immutable revision 18
→ Play projects revision 18
→ Run pins revision 18 forever
→ revision 19 may later exist without invalidating the Run
```

If the steward rejects this model, the replacement must still solve historical-revision
availability, working-copy recovery, CAS, and cross-surface reuse without reintroducing
filesystem topology as authority.

### 4.4 Run transaction thesis

A Run may remain one domain aggregate rather than immediately normalizing every progress
field into separate tables.

A valid first relational posture may be:

```text
play.run
  identity/binding columns
  run_revision
  progress JSONB
  timestamps
```

with optimistic CAS enforced by the database:

```text
UPDATE ...
WHERE run_id = ? AND run_revision = expected
RETURNING ...
```

The steward should normalize only fields that need independent constraints/queryability.
Do not relationalize creative/runtime state for aesthetic purity.

### 4.5 Manifest thesis

Keep the sealed manifest concept but make Run creation/sealing one transaction when
possible:

```text
read exact committed Playable revision
→ validate semantic structure
→ derive sealed manifest
→ insert Run
→ insert manifest
→ commit
```

There should be no observable state where a newly READY-capable Run exists without the
manifest required to admit it.

### 4.6 Rebase thesis

Target:

```text
BEGIN
→ lock/select Run at expected run_revision
→ load target immutable Playable revision
→ derive/validate target manifest
→ prove preserved Runtime references remain admitted
→ update Run binding + manifest + run_revision
COMMIT
```

Do not automatically preserve a durable rebase-intent protocol after the database owns
the complete commit boundary. If a future workflow truly spans external authorities and
needs a saga/outbox, design that exact boundary separately.

### 4.7 Mutation-history thesis

The earlier tick/ledger exploration becomes more plausible once the current-state update
and its audit record can commit together.

Candidate later capability:

```text
play_run_mutation
  run_id
  from_run_revision
  to_run_revision
  semantic delta
  recorded_at
```

Current Run state remains authority; this is **not event sourcing**. Do not include this
in the first database slice unless it is necessary to prove the substrate or migration.

---

## 5. Product and quality objectives

This project is infrastructure only insofar as infrastructure makes the product better.
It must advance the parent CON-READY stories, especially:

```text
CR-U11  durable/reopenable playable prep
CR-U12  governed agent use of saved playable material
CR-U13  prepared combat durability
CR-U14  fast unexpected combat setup
CR-U15  DungeonBuddy faster/safer than memory/manual search
CR-U17  reload/restart preserves relied-on state
```

### 5.1 Durability objective

Committed Buddy-owned state must survive:

- process restart;
- browser reload;
- branch/worktree/checkout changes;
- ordinary application deploy/restart;
- concurrent requests consistent with each domain's CAS/transaction contract.

A worktree may change code; it must not silently change which committed Playable/Run
state exists.

### 5.2 Failure objective

PostgreSQL unavailable means the owning application-state operation is unavailable or
fails truthfully.

Do not silently resurrect stale file-backed state as fallback after cutover.

### 5.3 Speed objective

The steward must make latency a first-class migration gate.

Before moving a surface, capture a realistic baseline for its high-frequency operations.
Every migration handoff should name measurable end-to-end and owning-boundary latency
budgets. Correctness-only acceptance is insufficient if the new path interrupts the GM.

For Play in particular, measure at minimum:

```text
resume active Run → current moment usable
load Run + pinned Playable revision
Runtime CAS mutation
Decision selection acknowledgement
Save committed Playable revision
Start Run + seal manifest
reload/restart → exact current moment restored
```

Do not invent universal numeric SLAs before baseline evidence. The architecture/design
gate should propose explicit budgets and the first migration slice should capture them.

### 5.4 "Pop" / perceived leverage objective

Persistence work must not degrade the current-moment product objective into visible
administration. Autosave/recovery, Resume, Save, Run start, Decision selection, and
Combat handoff should feel immediate and preserve context.

The steward should treat UI-visible stalls, "where did my work go?", re-selection after
reload, duplicate Run creation, and external-tool abandonment as product failures even
when database integrity is perfect.

---

## 6. Design gate status

**AS0 is complete** — merged PR #636 @ `4c90df353bfb5d0f6857357e00eb8b2b6e142257` (accepted head `605445b3b839b494a82218758c465edbfe59bad9`).

**AS0.1 is complete** — merged PR #639 @ `dd09f7f707e38f9f4348b759da8cfdbbe420fd60`
(accepted head `abb3fb15…`; Review Cycle 2 review `5014814402`). Architecture v1.1
is living authority.

**AS1 is complete** — merged PR #641 @ `29ff1584b9f76bb5100a724a96bebbbcf8f08d12`
(accepted head `b42eb629…`; 3 review cycles; final PASS-equivalent review `5023488870`;
evidence comment `5415847095`).

**AS2 is complete** — merged PR #643 @ `b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0`
(accepted head `6b1c2e77…`; 3 review cycles; final PASS-equivalent review `5024971680`;
evidence comment `5417774447`).

**AS3 is complete** — merged PR #646 @ `9c946cd8c24effccec8d06cfc1cb5e310c9edc5e`
(accepted head `913cfe0b…`; 3 review cycles; final PASS-equivalent review `5026608908`;
evidence comment `5420273265`).

AS3 dogfood note to retain: PostgreSQL Runtime CAS measured about **74 ms p95**
versus the 50 ms hypothesis and ~1 ms file baseline. Start Run + seal was about
**75 ms p95**, inside the 250 ms hypothesis. The CAS figure was not a merge
gate; keep it visible during interactive use.

**AS4 is the active implementation slice** (this PR). Do not mark AS4 DONE and do
not invent its merge SHA. AS5 remains false.

Expected artifacts (canonical owners):

```text
Docs/Design/ARCHITECTURE-application-state-layer.md   (v1.1 after AS0.1)
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md
Docs/Plans/STEWARDS-ANCHOR-application-state.md
```

A steward-designated design/architecture PR is appropriate when the design itself
is a durable cross-surface contract. Keep it narrowly documentation/design scoped
per `AGENTS.md`; do not revive a generic DOCUMENTS flow.

### 6.1 The architecture gate must answer

At minimum:

1. What is the exact ownership boundary between DungeonMind World state and Buddy
   application state?
2. What one Buddy PostgreSQL configuration/deployment contract exists in local,
   test, and production-like use?
3. What migration framework owns schema evolution?
4. What are the canonical repository/service abstractions and transaction boundaries?
5. Is `WorkObject + immutable WorkRevision + WorkingCopy` accepted, revised, or rejected?
6. Which current workspace-document kinds migrate onto that substrate and in what order?
7. What is Playable committed authority versus recoverable working copy?
8. How are historical Playable revisions retained and addressed?
9. How do Run + manifest + progress + active selection persist transactionally?
10. Which current file-lock/recovery concepts disappear and which remain because they
    span external authorities?
11. How is existing state migrated exactly and idempotently?
12. What is the switch/fallback posture before and after migration commit?
13. What filesystem paths become forbidden product authority after each cutover?
14. What data belongs in PostgreSQL versus external immutable blob storage?
15. How do tests isolate databases across worktrees/parallel agents?
16. How are backups/restore and local developer startup handled?
17. What performance metrics and regression budgets gate each migration?
18. What consumer proves the first substrate slice independently useful?

Unanswered material questions are design work, not implementation-agent discretion.

---

## 7. Sequencing — living capability families

Re-anchor against `ROADMAP-application-state.md` before dispatch. This is the
current sequence, not pre-authorized PR scope.

```text
AS0    DESIGN                      DONE — PR #636 merge 4c90df35
AS0.1  STORAGE-TOPOLOGY            DONE — PR #639 merge dd09f7f7
AS1    PLAN DOCUMENTS              DONE — PR #641 merge 29ff1584
AS2    PLAYABLE                    DONE — PR #643 merge b4d63daa
AS3    PLAY RUNTIME                DONE — PR #646 merge 9c946cd8
AS4    PLAY CONTINUITY             THIS PR — active Run + resume/reload; unmerged
AS5    PLAY DEMOLITION             still false / blocked on AS4
AS6+   CANDIDATE FAMILIES          Ingest, Asset, statblock, Combat, card, …
                                   evidence-driven; not pre-authorized schemas
```

Do not combine slices merely because one SQL migration could create all tables at
once. Each slice needs one independently useful invariant and owning-boundary proof.

The steward may discover that AS1 and AS2 should be split differently. Make that
decision from repository evidence, not architectural symmetry.

---

## 8. Interaction with active workstreams

### 8.1 PLAY-SURFACE

BF1 Beat-first grammar/manifest foundation is predecessor truth.

Default steering decision:

> **Do not deepen BF2/BF3 Runtime/cockpit implementation on `active-run.json`
> until AS4 lands or the steward explicitly re-sequences.**

The remaining Play persistence pause is the selected/active Run pointer, not
the architecture or the Run/manifest aggregate. AS4 is the point where that
pause ends. Existing PLAY-SURFACE file-backed active-run continuity work is
not AS4 PostgreSQL dispatch.

This is a sequencing decision, not permission for APP-STATE to redesign Beat/Scene/
Decision semantics.

### 8.2 CUTOVER

CUTOVER remains higher priority while final native DungeonMind read switch / old graph
runtime demolition is active.

APP-STATE design work may proceed during a product freeze when write leases do not
collide. Implementation involving root database config, shared startup lifecycle,
requirements/lockfiles, or server bootstrap must be checked explicitly against CUTOVER
and any other active lane before dispatch.

Do not couple Buddy application-state migration to the DungeonMind graph-runtime
retirement in one PR.

### 8.3 CON-READY

CON-READY remains product acceptance authority. APP-STATE is an enabling workstream, not
a replacement product roadmap.

Each migration should name which user-visible falsehood becomes more true. `CR-U17` is
especially central, but durability that makes the product slower or harder to operate is
not sufficient.

### 8.4 Combat

Combat should eventually become a first-class consumer of the shared PostgreSQL
substrate while retaining Combat-owned state.

Do not put HP/initiative/conditions into Play Runtime merely to reuse the first migrated
schema. Play may link to a Combat runtime ID; Combat owns the combat aggregate.

### 8.5 Ingest, Source, and generated artifacts

Source and Ingest are distinct first-class future consumers of the shared
substrate — not afterthoughts to Plan/Play:

- **Source** owns `SourceArtifact` identity, provenance, and asset reference.
- **Ingest** owns `IngestRun` identity and the processing/review lifecycle,
  including reviewed outputs and World-bearing proposals.

Generated game artifacts (statblock, location, NPC, shop, encounter, card drafts)
are also first-class future consumers of the shared substrate.

Current repository evidence is path-keyed (`recap_ingest.py`,
`location_corpus_index.py`) or uses durable `artifact_id`
(`DESIGN-statblock-lifecycle-agentic-workbench.md`). The correction names the target
without pre-creating `ingest.*`, `assets.*`, or `statblock.*` tables.

World publication is not a default promotion for every durable Buddy artifact:

```text
reviewed World-bearing facts
  → governed DungeonMind publication contract
  → DungeonMind World Graph

mechanics/statblock artifacts, card projects/renders, assets,
and other non-World domains
  → remain in their owning Buddy domain
  → World may reference them; they do not become World truth
```

Ingest state is not World truth merely because a run may eventually propose
World-bearing facts. Location/NPC/shop drafts remain Buddy durable state except
for the reviewed World-bearing facts that actually cross that publication
boundary.

---

## 9. Steward operating loop

A fresh APP-STATE steward should follow this loop.

### Step 1 — re-anchor

Establish current:

```text
Buddy main SHA
active CUTOVER / PLAY / COMBAT / CON-READY PRs and handoffs
current DB dependencies/configuration
all file-backed application-state authorities
current Play/Workspace route → service → persistence call graph
current runtime-state collision points across worktrees
```

Read repository authority before relying on this creation snapshot.

### Step 2 — inventory persistence by authority, not extension

Build an inventory such as:

| Durable state | Domain owner | Current representation | Product consumers | Concurrency/recovery mechanism | Candidate target |
|---|---|---|---|---|---|
| Runbook | Playable | registry + Markdown file | Plan/Play/Hermes | file lock + revision/digest | content work object |
| Run | Play Runtime | JSON | Play | file lock + CAS | play aggregate |
| Manifest | Play Runtime integrity | JSON sidecar | Play | coordinated file writes | immutable transactional row |
| Active Run | Play | JSON | Play entry | file lock | scoped pointer row |
| Combat | Combat | inspect current truth | Play/Combat | inspect | combat schema |

Do not infer that every file is authoritative or every Postgres candidate deserves its
own table.

### Step 3 — design and formally review AS0

Create the architecture + roadmap + first bounded implementation handoff. Review the
design against current code and product stories. The architecture should make future
implementation agents answer fewer questions, not simply relocate uncertainty into a
schema appendix.

### Step 4 — dispatch one implementation capability

Use the normal `AGENTS.md` / `STEWARD-CYCLE.md` process. Name exact base, write lease,
runtime/database isolation, migrations, failure modes, performance proof, and backward
state-authority sync.

### Step 5 — review at the owning persistence boundary

For database work, helper/unit tests are insufficient on their own. Prove actual
transaction behavior against PostgreSQL where the invariant depends on PostgreSQL.

Trace:

- concurrent CAS/update;
- transaction rollback;
- restart/reload;
- exact revision retrieval;
- migration retry/idempotency;
- unavailable database;
- old-authority fail-closed behavior after switch;
- realistic surface latency.

### Step 6 — migrate one consumer, then delete its old authority

The steward owns demolition as part of migration completion. Do not accumulate a second
permanent path "for safety."

### Step 7 — learn before extracting another generic primitive

If Play and Combat prove the same bounded transaction/revision abstraction, hoist it.
Do not speculate a universal event store, rules engine, or entity framework in advance.

---

## 10. Review principles specific to this project

### 10.1 PostgreSQL presence is not proof of correctness

Ask:

> Is the database transaction the actual authority boundary, or did we merely store the
> same multi-file protocol inside rows while retaining duplicated sources of truth?

### 10.2 Historical revision availability is a product capability

One expected improvement over file-backed Playable storage is that a Run pinned to
revision R can keep reading R after revision R+1 exists.

Do not preserve the current "bound revision must still be current workspace bytes"
limitation merely for migration compatibility unless a bounded transitional reader needs
it.

### 10.3 Working-copy recovery must not blur committed authority

Autosaved/recoverable draft state is valuable. It must not silently become the committed
revision that a Run or Hermes treats as deliberately saved prep.

### 10.4 One physical database does not erase authority

A transaction spanning two Buddy-owned domains may be legitimate only when one product
operation truly owns both. A transaction cannot grant Buddy authority to mutate
DungeonMind World Graph tables.

### 10.5 Avoid SQL-driven product ontology

Do not create universal `npc`, `scene`, `shop`, `event`, or `adventure` tables merely
because relational modeling makes them easy to sketch. Domain schemas are justified by
product authority and query/mutation needs.

### 10.6 Preserve exact identity through migration

Migration should preserve stable public IDs, revisions, digests, Run IDs, semantic
Playable IDs, and user-visible continuity unless the design explicitly defines a new
identity contract and migration mapping.

---

## 11. Stop / split conditions

Stop and return to steward design when any implementation slice discovers:

- a second independently useful domain contract hiding inside the slice;
- a required cross-authority transaction with DungeonMind World Graph state;
- need to change Beat/Scene/Decision semantics to make persistence convenient;
- need for a generic event-sourcing architecture to finish a bounded CRUD/CAS migration;
- need to migrate Combat and Play atomically without a product invariant requiring it;
- a new persistent format/API not covered by the reviewed architecture;
- a file path currently leased by CUTOVER/PLAY/another active lane;
- test/database instances shared across worktrees in a way that can corrupt evidence;
- a migration that cannot be made idempotent or safely resumable;
- a proposal to retain permanent file fallback without a named remaining consumer;
- measurable product latency regression that invalidates the surface acceptance story.

---

## 12. Evidence philosophy

This project should leave unusually strong evidence because persistence failures are
expensive and deceptive.

Each migration capability should have evidence in these classes where applicable:

```text
schema/migration proof
repository contract proof
real PostgreSQL transaction/concurrency proof
route/domain-service proof
migration round-trip / exact identity proof
restart/reload proof
old-authority absence/fail-closed proof
surface dogfood
latency baseline vs migrated path
```

For a surface migration, the final proof should include running with the old authoritative
files physically absent or inaccessible when that is the claimed end state.

---

## 13. Definition of project success

The APP-STATE project is successful when:

1. Buddy has one documented, supported PostgreSQL application-state substrate with
   storage-independent domain identity law.
2. Surfaces consume it through domain services rather than owning persistence mechanics.
3. PostgreSQL owns durable Buddy state and asset metadata; DungeonMindServer
   storage/CDN owns large bytes via an Asset service boundary.
4. Playable committed revisions are immutable, historically addressable, and independent
   of checkout/worktree filesystem state.
5. Recoverable working copies do not blur committed Playable authority.
6. Play Runs, manifests, Runtime progress, and active selection use transactional durable
   authority with database-native CAS/concurrency semantics.
7. Rebase no longer requires a durable application-level multi-file recovery intent when
   all owned state is inside one transaction.
8. Play reload/restart restores the exact current moment without file-backed authority.
9. Combat, Ingest, and generated-artifact domains have proven migration paths that reuse
   shared substrate primitives rather than inventing new registries.
10. DungeonMind remains the sole World Graph governance authority and no Buddy application
    table becomes a shadow graph.
11. Replaced filesystem persistence paths are deleted or have an explicitly named,
    reviewed remaining consumer.
12. Product speed and table usability are measured and do not regress merely to achieve
    architectural cleanliness.
13. Path/URL/bucket locators are not used as stable cross-domain product identity.

The project is **not** complete merely because Play tables exist in PostgreSQL.

---

## 14. First pickup checklist

A new steward should be able to begin with this exact sequence:

```text
1. Read AGENTS.md and STEWARD-CYCLE.md.
2. Re-anchor current main, AS0 merge (#636 @ 4c90df35), AS0.1 merge (#639 @ dd09f7f7), and active lanes.
3. Read this anchor and ARCHITECTURE-application-state-layer.md v1.1.
4. Read Playable/Runtime architecture + current-moment cockpit + authoring/adoption.
5. Read CUTOVER steward anchor so World authority is not accidentally reopened.
6. Trace current workspace-document + Play Run persistence end to end.
7. Inventory path-keyed Ingest, location index, and generated-artifact durable state.
8. Treat AS3 as DONE — PR #646 merge `9c946cd8…`, accepted head `913cfe0b…`.
9. Treat AS4 as this unmerged Play Continuity implementation; keep AS5 (Play file demolition) unimplemented.
```

If a fresh steward cannot answer "what remains false after the first implementation
slice?", AS1 is not ready for dispatch. Do not dispatch AS1 from pre-correction
architecture text.
