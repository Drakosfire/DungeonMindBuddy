---
document_id: dmb-architecture-application-state-layer
title: Application State Layer — Architecture Authority
document_class: architecture_authority
status: active
version: 1.1
created_at: "2026-08-24"
updated_at: "2026-08-24"
workstream: APP-STATE
as0_merge: "4c90df353bfb5d0f6857357e00eb8b2b6e142257"
as0_accepted_head: "605445b3b839b494a82218758c465edbfe59bad9"
design_authority_base: "31f2885cc18f96b98a1028304ae98914d1139fa3"
dispatch_base: "9782c05d506ee4be918ed2491ff63d9705ac97c9"
parent_anchor: "../Plans/STEWARDS-ANCHOR-application-state.md"
companion_authorities:
  playable_runtime: "ARCHITECTURE-playable-material-and-runtime.md"
  play_cockpit: "DESIGN-play-current-moment-cockpit.md"
  playable_authoring: "DESIGN-playable-authoring-and-adoption.md"
  workspace_identity: "CONTRACT-workspace-document-identity-v1.md"
  campaign_supergraph: "ARCHITECTURE-campaign-supergraph.md"
  cutover_anchor: "../Plans/STEWARDS-ANCHOR-cutover.md"
  con_ready_anchor: "../Plans/STEWARDS-ANCHOR-con-ready.md"
---

# Application State Layer — Architecture Authority

## 1. Purpose, scope, and non-goals

DungeonBuddy owns **one transactional application-state substrate**, not one
universal domain model. Surfaces call domain services. Domain services own
invariants. PostgreSQL owns durable Buddy application state and asset
metadata/relationships. DungeonMind owns World Graph truth. Large binary bytes
live in DungeonMindServer storage/CDN behind an Asset service boundary.

### Storage-independent identity law

A product object is addressed by a **stable domain-level ID**. Filesystem paths,
corpus paths, CDN URLs, bucket/object keys, database table coordinates, and
temporary generator output locations are **storage locators or projections** —
not product identity. The owning domain service resolves locators.

Examples that must remain obviously wrong as terminal design:

```text
location_id = "corpus/.../Mireward_Location_Dossiers/Foo.md"
card.image = "https://cdn.example/..." as permanent cross-domain identity
run_id = "out/runtime/play/runs/123.json"
source_artifact = Path(...)
```

Preferred shape:

```text
location_draft_id = <stable id>
image_asset_id = <stable id>
run_id = <stable id>
source_artifact_id = <stable id>
```

### Four state classes

```text
(A) Buddy durable application objects
    Plan / Runbook / Play Run / Combat Runtime
    SourceArtifact (Source-owned) / IngestRun (Ingest-owned) / reviewed processing state
    generated Statblock / Location / NPC / Shop / Encounter drafts
    CardProject / agent proposals / other user-relied-on product objects
        → durable domain identity + lifecycle + relationships
        → Buddy Application State PostgreSQL

(B) Large / binary assets
    images / maps / PDFs / audio / rendered cards / other large blobs
        → Buddy PostgreSQL: asset identity, digest, media metadata,
          provenance, ownership/relationships, storage locator metadata
        → DungeonMindServer storage/CDN: large bytes and delivery

(C) World truth
    durable campaign-world identity, facts, relationships,
    governed World publication/history
        → DungeonMind PostgreSQL

(D) Derived / regenerable state
    projections / indexes / thumbnails / rendered HTML / previews /
    caches / search results / exports reproducible from durable inputs
        → may be persisted for speed; persistence alone does not make authority
```

### Product classification test

For a candidate state/object, ask in order:

1. **Is this World truth?** → DungeonMind authority. Buddy may reference the
   public World ID; do not duplicate authority in APP-STATE.
2. **Does product correctness or user trust depend on this Buddy-owned thing
   existing later across reload/restart/worktree/deploy?** → stable Buddy domain
   identity and durable application-state ownership.
3. **Are the authoritative bytes large/binary?** → Buddy PostgreSQL owns
   identity/metadata/digest/relationships; bytes go through the Asset service
   to DungeonMindServer storage/CDN.
4. **Can this representation be regenerated exactly enough from durable
   inputs?** → derived/cache/output unless a separate product requirement makes
   the particular representation itself user-owned durable state.
5. **Does it have domain-specific lifecycle/invariants?** → domain-owned
   schema/service. Do not force it into Content WorkObject or a generic JSON
   table.

| Product concept | Classification |
|---|---|
| Plan document | Buddy durable Content object |
| Runbook | Buddy durable Content/Playable object |
| Play Run | Buddy durable Play Runtime |
| Combat encounter state | Buddy durable Combat Runtime |
| raw uploaded/recorded session audio | SourceArtifact metadata (Source) + Asset bytes |
| transcript text | Buddy durable Source/processed artifact; Ingest may attach review outputs |
| IngestRun status/review/provenance | Buddy durable Ingest state |
| accepted World object/fact | DungeonMind World truth |
| generated statblock draft | Buddy durable Mechanics/generated-artifact state; not World truth (World may reference mechanics identity) |
| location/NPC/shop draft | Buddy durable generated/authored state; only reviewed World-bearing facts may publish to DungeonMind |
| card project/specification | Buddy durable owning-domain state; not World truth |
| rendered card PNG/PDF | Asset or derived render linked to exact project revision |
| projection/search index/thumbnail | Derived/cache unless product says otherwise |

DungeonMind publication is not a default promotion. Only reviewed **World-bearing
facts** cross the governed DungeonMind publication contract. Mechanics/statblock
artifacts, card projects/renders, assets, and other non-World domains remain in
their owning Buddy domain; World may reference them without absorbing them as
World truth.

This document is the persistence/revision/transaction/migration authority for
Buddy-owned durable application state. After it is reviewed, later
implementation slices must not invent a second database lifecycle, a second
revision model, a permanent file fallback, or a generic JSON object store.

### In scope

- Buddy PostgreSQL logical ownership, configuration, and isolation
- schema migration ownership
- repository/transaction layering
- WorkObject / WorkRevision / WorkingCopy
- Play Run + manifest + active-Run target transaction model
- exact existing-state migration, switch, fail-closed, and demolition rules
- backup/restore posture and speed/"pop" measurement vocabulary

### Non-goals

- production code, SQL migrations, dependency pins, Docker edits, or database writes in AS0
- Play Beat / Scene / Decision / Option semantics
- Combat HP/initiative/condition schema details
- DungeonMind schema, World Graph writes, or CUTOVER D.2/D.3 demolition
- event sourcing
- high-availability / multi-operator account systems
- storing PDF/image/audio bytes inside PostgreSQL pages

### Persistence assumption superseded

`ARCHITECTURE-playable-material-and-runtime.md` §14 currently says the Play
architecture does not require a new database before workspace documents prove
insufficient. That **storage** assumption is superseded here. File-backed
registry + current Markdown bytes have been proven insufficient for historical
revision pinning, multi-file transactions, and worktree-local durability.
Play **domain** semantics remain owned by the Play authorities and are not
redesigned by this document.

---

## 2. Authority diagram and ownership matrix

```text
 Plan / Build / Play / Combat / Ingest / Recap / Hermes
                      │
                      ▼
              domain services
         (Content, Play, Combat, Source, Ingest, Asset, …)
                      │
                      ▼
        Buddy Application State Layer
         unit of work + repositories
                      │
                      ▼
     PostgreSQL  dungeonbuddy_application_state
         content.*   play.*   combat.*
         ingest.*   assets.*   statblock.*   (created when earned, not AS1)
                      │
                      │  stable public IDs / governed service contracts
                      │  NO SQL FK into DungeonMind tables
                      ▼
              DungeonMind PostgreSQL
           World Graph living authority

Asset service (domain) → DungeonMindServer storage/CDN (large bytes; no SQL FK)
```

| Concern | Authority after AS0 |
|---|---|
| Buddy persistence substrate | this document |
| storage-independent domain identity law | this document |
| durable work/revision lifecycle (Content) | this document |
| asset identity/metadata boundary (concept) | this document |
| transaction / repository boundary | this document |
| schema migration / deployment | this document |
| application-state cutover / demolition | this document |
| DB failure / isolation / backup | this document |
| Playable vs Runtime meaning | `ARCHITECTURE-playable-material-and-runtime.md` |
| Beat / Scene / Decision / Option / Run behavior | Play design authorities |
| workspace document UUID identity | `CONTRACT-workspace-document-identity-v1.md` (identity rules preserved; file persistence superseded) |
| World identity, graph reads/writes, contribution/publication | DungeonMind / Campaign Supergraph / CUTOVER |
| Surface chrome / projection host | `ARCHITECTURE-surface-interaction-layer.md` |

| Domain | Owns | Must not own |
|---|---|---|
| Content | Plan/Runbook WorkObjects, committed revisions, working copies | World assertions, Combat HP, Play progress, Ingest runs, asset bytes |
| Play | Run aggregate, sealed manifest, active-Run pointer, Runtime CAS | Playable bytes, Combat encounter state, World truth |
| Combat | current encounter, save slots, combatant HP/init/conditions | Play progress, Playable revisions, World nodes |
| Ingest | IngestRun identity, processing/review outputs and lifecycle | SourceArtifact identity, World truth, Play progress, generic document WorkObjects |
| Asset | asset identity, digest, locator metadata, delivery resolution | Domain lifecycle invariants, World truth, PostgreSQL byte pages |
| World | DungeonMind graph identity and governed mutation | Buddy documents, Runs, Combat boards, Ingest staging |
| Source | SourceArtifact identity, provenance, and asset reference | IngestRun lifecycle, Playable interpretation, Runtime selections, World truth, large bytes |
| Mechanics | immutable statblock/revision identity in its owning service | Combat runtime HP, Play notes |

A shared database does not collapse these domains.

---

## 3. Current-state persistence inventory

Grounded on AS0.1 handoff/dispatch base `9782c05d506ee4be918ed2491ff63d9705ac97c9`
(not a completed correction merge). Design-authority predecessor: CUTOVER #634
`31f2885c…`. AS0 / PR #636 merge on `main` is
`4c90df353bfb5d0f6857357e00eb8b2b6e142257`; accepted PR head was
`605445b3b839b494a82218758c465edbfe59bad9`. This correction re-read `apps/live_control_server/routes/recap_ingest.py`,
`apps/live_control_server/services/location_corpus_index.py`, and
`Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md` for path-keyed and
`artifact_id`-keyed durable state beyond Plan/Play. This is evidence, not
one-table-per-row.

### 3.1 Inventory

| Durable/product state | Current owner | Current representation | Real consumers | Concurrency / recovery | Historical revisions? | Target disposition |
|---|---|---|---|---|---|---|
| Workspace document metadata | Content / authoring | `out/registries/workspace_documents.json` via `workspace_document_registry.py` | `routes/workspace_documents.py`; Plan/Build/Play; Hermes authoring | registry file lock + monotonic `revision` CAS (`registry_file_lock.py`) | No — `revision` is a CAS token, not an archive | WorkObject row in `content` |
| Workspace document bytes | Content / authoring | Markdown at `target_relpath` via `tiptap_markdown_write.py` | snapshot GET; Tiptap commit/prepare; Play Run create (runbook) | per-document lock; `content_sha256` / `file_fingerprint` on snapshot | **No.** Commit increments registry revision and overwrites the file. Loaded revision is always current bytes. | Immutable `WorkRevision` + recoverable `WorkingCopy` |
| Plan kind | Content | kinds `plan`; legal paths `out/workspace/plan/<uuid>.md` **or** corpus `Session N Prep.md` | Plan/Build save/load/commit | same as workspace docs | No | **AS1 consumer.** Bytes become WorkRevisions. `target_relpath` becomes optional publish metadata, not read authority. |
| Runbook / Playable kind | Playable / Content | kind `runbook`; writer currently allowlists `evals/c2_live_prep/mireward-prep/content/tiptap/*.md` | Play Run create/rebase; Plan edits the same object | snapshot must be `committed` + sha match | No. Play architecture states v1 Runs stay openable only while bound digest is still the **current** file. | **AS2.** Same WorkObject primitives. Historical revision N remains loadable after N+1. |
| Worldbuilding source kind | Content / Build | kind `worldbuilding_source`; `_dungeonbuddy/sources/` or `out/workspace/worldbuilding/` | Build source authoring | extra metadata (`authority_state`, `visibility_state`, `world_id`) | No | Later Content slice. Do not admit in AS1. Not World Graph truth. |
| Play Run | Play Runtime | `out/runtime/play/runs/<run_id>.json` (`play_run_registry.py`) | `routes/play_runs.py`; Play surface | per-run file lock + `run_revision` CAS; create is replay-safe if binding matches | Run CAS history not retained; progress overwritten | `play.run` aggregate; JSONB progress; DB CAS |
| Play Run manifest | Play integrity | sidecar JSON next to the Run (`play_run_reference_manifest.py`) | Run admit/rebase/Play | coordinated with Run under separate file writes | Sealed per binding; file-replace on rebase | `play.run_manifest`; insert with Run in **one transaction** |
| Play active Run | Play continuity | `out/runtime/play/active-run.json` (`play_active_run.py`) | Play entry/resume | file lock; single-operator; `run_id` + `selected_at` pair | No | `play.active_run` singleton scoped to local operator/campaign until accounts exist |
| Play rebase recovery | Play Runtime | `out/runtime/play/rebase-intents/<run_id>.json` (`play_run_rebase.py`) | rebase prepare/commit; Run read/list refuse pending intents (503) | durable intent + forward recovery because two files cannot commit together | Intent is the transaction substitute | **Delete** once Run+manifest+Playable revision share one DB transaction |
| Combat current encounter | Combat | `combat/current_combat.json` under `session_dir()` (`combat_state.py`) | Combat surface; Play may link later | single-file replace via `live_store.write_json` | No (backups are separate files) | Future `combat.*` schema. Session-dir locality is a product defect, not a model to preserve. |
| Combat save slots | Combat | `combat/saves/<save_id>.json` + `combat/backups/` (`combat_saves.py`) | Combat roster load/unload | destructive transitions snapshot first | Backup files, not a revision API | Combat-owned tables later; not Play progress |
| Browser workspace drafts | Content UI | `localStorage` keyed by document id (`useWorkspaceDocumentAuthoring.ts`) | Plan/Build editor recovery | browser semantics | No | After a kind switches, **server WorkingCopy is authority**. localStorage may cache, never be the only recoverable draft. |
| Hermes / Plan thread UI | Agent interaction | localStorage thread index/active thread | Plan agent bar | browser | No | Not product-correctness durability. Defer. Do not migrate in AS1–AS5. |
| Build last-campaign convenience | Build UI | localStorage | Build entry | browser | No | Remains client convenience. |
| Recap / Ingest run lifecycle | Ingest | path-keyed staged raw, normalized recap, frontmatter seed, candidate graph, preview manifests (`recap_ingest.py`, pipeline helpers) | Ingest UI, graph preview, publication proposals | path + digest coordination | Run identity tied to corpus paths today | future `ingest.*` IngestRun identity; paths become locators, not terminal IDs |
| Source artifact identity | Source | path-keyed corpus trees, `_dungeonbuddy/sources/`, eval fixtures, ingest staging paths used as IDs | ingest, Hermes, worldbuilding | path + digest | Artifact identity tied to paths today | future Source-owned SourceArtifact identity; Asset reference for large bytes; paths become locators |
| Location corpus index | Build / Content | path-keyed location dossier index (`location_corpus_index.py`) | Build location authoring, corpus navigation | filesystem scan + path display | No durable draft identity separate from corpus path | future Buddy durable location-draft identity; index may remain derived |
| Generated statblock draft | Mechanics / Build | durable `artifact_id` lifecycle per `DESIGN-statblock-lifecycle-agentic-workbench.md` | statblock workbench, combat activation | review/lifecycle state | Review/provenance history where implemented | future `statblock.*` or domain schema when consumer earns it; not WorkObject |
| Source / artifact bytes | Asset, referenced by SourceArtifact | corpus trees, `_dungeonbuddy/sources/`, eval fixtures | ingest, Hermes, worldbuilding | path + digest | Bytes currently path-located | Asset identity/metadata in PostgreSQL; large bytes via DungeonMindServer storage/CDN. SourceArtifact holds the asset reference, not the bytes. |
| World Graph | DungeonMind | DungeonMind PostgreSQL via `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` | production reads after #633/#634; governed writes | DungeonMind transactions | DungeonMind mutation history | **Out of Buddy application state.** No Buddy World tables. No SQL FK. |

`src/live_play/live_store.py` is a JSON file helper, not a Combat domain store.

### 3.2 Call-path tracing (authority crossings)

| Path | Current crossing | Target crossing |
|---|---|---|
| Workspace create/load/save | route → registry JSON + optional Markdown file | route → Content domain service → unit of work → `content.*` |
| Plan / Runbook committed load | snapshot = registry row + **current** file bytes (`loaded_revision=record.revision`) | snapshot = WorkObject + addressed WorkRevision bytes |
| Play Run create | lock Run file; lock Playable doc; read **current** snapshot; require kind=`runbook`, committed, revision+sha match; write Run JSON; seal manifest in a later/separate file | one transaction: lock/select Playable **WorkRevision**; insert Run + manifest |
| Run progress replace | file lock + `expected_run_revision` CAS overwrite | `UPDATE play.run WHERE run_id AND run_revision` |
| Manifest seal/load | sidecar file coordinated with Run | row in same transaction as Run create/rebase |
| Active Run get/set | `active-run.json` lock | `play.active_run` row; FK-by-ID to Run inside Buddy DB only |
| Rebase prepare/commit/recovery | write intent file; later replace Run+manifest; recover from intent if interrupted | single `BEGIN…COMMIT`; no durable intent |
| Play entry/resume | active-run pointer → get Run → load **current** Playable file if digest still matches | active-run → Run → pinned WorkRevision (historical OK) |
| Combat current | `session_dir()/combat/current_combat.json` | later Combat service; Play stores only a Combat runtime id |

### 3.3 Existing PostgreSQL posture

Buddy currently receives PostgreSQL **drivers** only as a transitive extra:

```text
dungeonmind[postgres]  in pyproject.toml
```

used by the World Graph authority adapter. Application-state DSN is **not**
`DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL`. AS1 must add **direct** Buddy
dependencies (`psycopg`, `alembic`) rather than treating DungeonMind's extra as
the application-state driver contract. Do not edit `pyproject.toml` in AS0.

Known local World/Cutover server (do not reuse these database names):

```text
127.0.0.1:54329
  dungeonmind
  dungeonmind_cutover_live
  dmb_cutover_test
```

---

## 4. Logical deployment and configuration

### 4.1 One Buddy database, domain schemas

| Layer | Decision |
|---|---|
| PostgreSQL server | May be the same server as DungeonMind. Authority must not depend on co-location. |
| Logical database | Buddy owns `dungeonbuddy_application_state` (local product name). Tests use distinct names (§13). |
| Schemas inside that database | `content`, `play`, `combat` (created when that domain first lands), plus `application_state` for migration bookkeeping. Future `ingest.*`, `assets.*`, `statblock.*` only when a real consumer earns them — **not in AS1**. |
| DungeonMind database | Separate logical database. Never a schema inside Buddy's DB. Never a schema inside DungeonMind's DB. |

Same server, two databases is the intended local layout. A second PostgreSQL
**server/container** is not required for AS1.

### 4.2 Configuration contract

| Env | Role |
|---|---|
| `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` | Product/runtime DSN for Buddy application state. Owned by `src/application_state/config.py`. |
| `DMB_APPLICATION_STATE_TEST_DATABASE_URL` | Admin/template DSN used only to create ephemeral test databases. |
| `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` / `DUNGEONMIND_DATABASE_URL` | World Graph only. **Forbidden** as application-state fallback. |

Startup:

1. Parse application-state URL independently of World Graph URL.
2. If a switched domain operation is requested and the URL is missing/unusable → named fail-closed error. Do not read leftover files.
3. Ordinary app boot **checks** migration head and fails closed if behind. It does **not** run `alembic upgrade` as a side effect of serving traffic.
4. Developers apply schema with an explicit guarded CLI (`uv run python -m src.application_state.cli upgrade` or equivalent).

### 4.3 Local / test / production-like

| Environment | Database | How it is created |
|---|---|---|
| Local operator | `dungeonbuddy_application_state` on the existing local server (default port 54329 if that is the operator Postgres) | `CREATE DATABASE` + explicit upgrade |
| Worktree / parallel agent | distinct database name derived from worktree identity or an explicit URL override | never share the operator product DB for destructive tests |
| pytest | ephemeral database cloned from a migrated template | fixture-owned create/drop |
| Production-like | dedicated Buddy logical database, distinct DSN | explicit migrate during deploy/maintenance, not request handling |

---

## 5. Migration and schema ownership

| Question | Frozen answer |
|---|---|
| Framework | Alembic. Direct Buddy dependency. Separate Alembic tree from DungeonMind. |
| Location | `src/application_state/alembic.ini` + `src/application_state/migrations/` |
| Version recording | Alembic version table `application_state.schema_migrations` (not DungeonMind's `alembic_version`) |
| Migration style | Explicit SQL (or SQLAlchemy Core in revision files). Autogenerate is an authoring aid, never authority. |
| Connection/session owner | `src/application_state` unit of work. Domain services receive a UoW; they do not open ad-hoc connections. |
| Runtime driver | `psycopg` (v3) as a **direct** `dungeonmindbuddy` dependency. SQLAlchemy is allowed as Alembic's engine dependency, not as the domain ORM. |
| Local/dev upgrade | Explicit CLI. App boot verifies head. |
| Test upgrade | Test fixture migrates the ephemeral DB. |
| Automatic production schema mutation at ordinary boot | **Prohibited.** |
| Rollback | Forward-fix migrations are the default. Restoration uses PostgreSQL dump/restore (§14), not a folklore down-revision of product data. |

Avoid both extremes:

```text
every repository opens its own connection and invents migrations
one god service that knows Play, Combat, and Content invariants
```

The substrate owns transactions, CAS helpers, and schema evolution. Domain
packages own invariants and SQL for **their** tables.

---

## 6. Domain-service / repository / transaction layering

```text
React / FastAPI route / Hermes capability
        ↓
domain service   (Content Plan, Play Run, later Combat)
        ↓
unit of work     (one PostgreSQL transaction)
        ↓
domain repository
        ↓
PostgreSQL
```

Forbidden:

```text
surface component → SQL
domain service → filesystem after that domain has switched
application_state generic blob API → untyped JSON as the product model
```

Transaction rules:

- One user-visible commit = one database transaction unless an **external**
  authority is involved (DungeonMind write, blob store, corpus publish).
- If an external authority is involved, design that exact saga later. Do not
  keep file-intent protocols inside Buddy-owned state "just in case."
- Repositories do not commit. The domain service / UoW commits.

---

## 7. Shared primitives and admission criteria

The shared substrate owns **configuration, migrations, unit of work, transaction/CAS
conventions, and failure/isolation rules**. It does not own a universal
`application_object (id, type, jsonb)` row type.

Accepted shared Content primitives:

```text
WorkObject
WorkRevision
WorkingCopy
unit of work / CAS helper
```

These are **Content-domain** primitives for document-like authored material.
They are not a universal row type for Ingest runs, generated statblock drafts,
card projects, or asset metadata.

Future domain schemas (created only when earned):

```text
ingest.*     IngestRun / processing-review outputs and lifecycle
             (SourceArtifact is Source-owned; do not put that identity in ingest.*)
assets.*     asset identity/metadata
statblock.*  generated-artifact lifecycle when a consumer proves it
combat.*     Combat runtime when migrated
```

### Admission — use WorkObject when all of these are true

1. The thing is GM-authored (or adopted) document-like material.
2. Product correctness needs a stable identity across surfaces (Plan edits, Play pins).
3. Committed bytes must remain addressable after a later commit.
4. A recoverable draft must be distinct from committed truth.

### Do not use WorkObject for

| Thing | Why | Where it lives |
|---|---|---|
| Play Run / progress | high-frequency runtime aggregate; not an authored document | `play.run` |
| Sealed manifest | Run integrity artifact | `play.run_manifest` |
| Active Run pointer | continuity singleton | `play.active_run` |
| Combat encounter / save | Combat-owned live mechanics state | `combat.*` later |
| World node / assertion | DungeonMind | DungeonMind DB |
| Source PDF/image bytes | large immutable blob | Asset service + metadata row; bytes in DungeonMindServer storage/CDN |
| IngestRun | domain lifecycle, not document revisions | future `ingest.*` |
| SourceArtifact | identity/provenance/asset reference, not document revisions | future Source-owned schema; not `ingest.*` |
| Generated statblock / location / NPC / shop draft | domain lifecycle + review state | future domain schema; not WorkObject |
| Card project / rendered PNG | project state + asset link | future domain + `assets.*` |
| Hermes chat threads | UI session, not Buddy durable product state yet | remains client until a later justified slice |

### Kind is not an ontology

`WorkObject.kind` is a closed, migration-gated enum. Adding a kind is an
implementation slice with a domain owner, not a free-form string. AS1 admits
`plan` only. AS2 admits `runbook`. `worldbuilding_source` is explicitly **not**
admitted until a later Content slice.

---

## 8. WorkObject / WorkRevision / WorkingCopy contract

**Accepted**, with the revisions below. This is the replacement for
"registry row + current file bytes + browser localStorage draft."

### 8.1 Identities

| Object | Identity | Mutability |
|---|---|---|
| WorkObject | `work_object_id` UUID, equal to today's `document_id` | Identity never reused. Discard retains the row. |
| WorkRevision | `work_revision_id` UUID **and** integer `revision_n` unique per object | Insert-only. Never update bytes. |
| WorkingCopy | one per WorkObject (nullable) | Mutable. Not Run-admissible. |

`kind` and `campaign_id` are immutable after create. `world_id` is optional and
immutable if set (Content/Build later). Title is metadata on the object, not a
new content revision by itself.

`revision_n` starts at 1 for the first committed revision. It is **not**
fabricated for missing history (§12).

Object-level CAS uses `object_revision` (integer), covering metadata and
working-copy races that are not content commits. Content commits also bump
`object_revision`.

### 8.2 Canonical content and digest

- Canonical committed representation is UTF-8 Markdown bytes (today's Tiptap
  commit payload).
- Digest is SHA-256 of those exact bytes (`content_sha256`), lowercase hex.
- A WorkRevision stores bytes + digest + `revision_n` + provenance
  (`created_at`, optional actor/source).
- Playable/Run binding addresses `(work_object_id, revision_n, content_sha256)`
  and should also store `work_revision_id` once AS2 exists.

### 8.3 Current pointer vs history

- `WorkObject.current_revision_id` points at the latest committed revision, or
  null if none exists yet (`content_status=draft` equivalent).
- Historical revisions remain queryable forever unless a future explicit purge
  slice exists (none now).
- **A Run may pin historical revision N after N+1 exists.** Loading that Run
  reads revision N bytes, not current. This is a required product capability
  and the reason the current file model is rejected.

### 8.4 Working copy

- Stores draft Markdown, `base_revision_id` (null if never committed), digest,
  and `working_copy_revision` CAS.
- Autosave upserts WorkingCopy. It does **not** move `current_revision_id`.
- WorkingCopy is not Play-admissible. Run create/rebase requires a committed
  WorkRevision.

### 8.5 Save / commit meaning

| Operator action | Durable effect |
|---|---|
| Autosave / recover | upsert WorkingCopy |
| Explicit Save / commit | insert WorkRevision from WorkingCopy (or request body); set `current_revision_id`; rebase or clear WorkingCopy onto the new revision |
| Discard | `status=discarded`; revisions retained; WorkingCopy retained until restore or explicit clear |
| Restore | `status=active` |
| Hard delete | **Not offered** (preserves `CONTRACT-workspace-document-identity-v1.md`) |

Commit CAS:

```text
expected object_revision matches
expected base revision matches current_revision_id
insert WorkRevision
update WorkObject current_revision_id + object_revision
WorkingCopy.base_revision_id = new revision
COMMIT
```

Mismatch → 409, no write. Replay of an identical successful commit (same bytes,
same expected CAS that now sees the already-written revision) is a no-op success
only when the stored digest already equals the request digest at that revision.
A changed body after commit is a new working copy, not a silent rewrite of
history.

### 8.6 Metadata vs content

Title / status / target_session / optional publish path live on WorkObject.
Changing title does not create a WorkRevision. Changing Markdown does.

`target_relpath` after switch is **publish metadata**, not byte authority.
Reading a switched kind from the filesystem is forbidden. Optional later export
to a corpus Session Prep path is a separate capability and must be explicit.

---

## 9. Play target transaction model

Play domain semantics stay in the Play authorities. This section freezes
**storage**.

```text
Playable committed WorkRevision
    → Run create + sealed manifest   (one DB transaction)
    → mutable Run CAS
    → active Run selection
    → preserve-only rebase           (one DB transaction)
```

### 9.1 Run aggregate

```text
play.run
  run_id UUID PK
  campaign_id
  playable_work_object_id     -- Buddy UUID, not a World id
  playable_revision_n
  playable_work_revision_id
  playable_content_sha256
  run_revision INTEGER
  progress JSONB              -- PlayRunProgress shape unchanged
  rebased_from_run_revision
  created_at / updated_at
```

Normalize only columns that need constraints or lookup. Do not explode notes or
selections into tables for aesthetic purity.

CAS:

```text
UPDATE play.run
SET progress = $progress, run_revision = run_revision + 1, updated_at = now()
WHERE run_id = $id AND run_revision = $expected
RETURNING *
```

Zero rows → 409. Identical replay of a completed replace (expected revision
already applied and progress equal) is a no-op success. Mutation/audit history
(`play_run_mutation`) is **excluded** until a later independently justified
slice. Current Run row remains authority. This is not event sourcing.

### 9.2 Manifest

Keep sealed-manifest meaning from BF1. Store as `play.run_manifest` bound 1:1
to `run_id` + Playable revision/digest. Manifest bytes/JSONB are immutable for
that binding; rebase inserts/replaces inside the rebase transaction.

No observable state where a READY-capable Run exists without its required
manifest.

### 9.3 Create transaction

```text
BEGIN
  SELECT WorkRevision FOR SHARE
    WHERE object_id + revision_n + sha match AND kind=runbook AND committed
  INSERT play.run
  INSERT play.run_manifest
COMMIT
```

Create replay (same `run_id` + same binding) returns the existing row.
Different binding on an existing `run_id` → 409.

### 9.4 Rebase transaction

```text
BEGIN
  SELECT run WHERE run_id AND run_revision = expected FOR UPDATE
  load target WorkRevision (immutable historical OK)
  derive/validate target manifest
  prove preserved Runtime references remain admitted (Play domain rule)
  UPDATE run binding + run_revision
  replace manifest
COMMIT
```

Durable rebase-intent files **disappear**. No external side effect remains
inside Buddy-owned state. A crash before COMMIT leaves the previous Run+manifest
unchanged.

### 9.5 Active Run

Single-operator product: one active `run_id` (nullable) per campaign scope.
Do not invent user accounts. Store in `play.active_run`. Setting an active Run
requires the Run to exist. Clearing is explicit.

### 9.6 File concepts that vanish vs remain

| Current mechanism | After Play cutover |
|---|---|
| `out/runtime/play/runs/*.json` | deleted |
| manifest sidecars | deleted |
| `active-run.json` | deleted |
| rebase-intent files | deleted |
| per-run file locks | deleted |
| registry CAS for Runs | replaced by SQL `run_revision` |
| workspace document lock spanning Run create | replaced by row locks in one transaction |
| DungeonMind / blob external calls | still outside the Play transaction |

---

## 10. Cross-authority reference rules

Buddy application tables reference other authorities by **stable public
identity**, never by storage coupling.

| From | To | Rule |
|---|---|---|
| Play Run | Playable | Buddy `work_object_id` + `revision_n` + `content_sha256` (+ `work_revision_id`) |
| Play / Content | World | public node/object ids and World revision tokens as **strings**; no SQL FK into DungeonMind |
| Play / Combat | Mechanics | immutable statblock revision id from the mechanics contract; Combat instantiates mutable combatant state |
| Play | Combat runtime | Play stores a Combat encounter/runtime id; Combat owns HP/init/conditions |
| Content | Source / assets | source artifact id + digest; asset_id for large bytes; Asset service resolves locators |
| Application state | DungeonMind tables | **No SQL foreign keys. No joins. No shared migrations.** |

### AssetRecord concept (not implemented)

Minimum durable concept for class (B) assets — exact fields/names are not frozen
here; no table or CDN client is required in AS1:

```text
AssetRecord
  asset_id
  media_type
  sha256
  size_bytes
  provenance / created_by as appropriate
  storage_provider
  locator                    -- bucket/key or provider coordinates; not domain identity
  created_at
```

Authority law:

```text
consumer stores asset_id
  → Asset service resolves storage/delivery
  → DungeonMindServer storage/CDN handles bytes
```

A CDN URL may be returned as a delivery projection (including signed/expiring
URLs). It must not become the stable cross-domain reference.

Large bytes: PostgreSQL stores `asset_id`, digest, media type, locator metadata.
Object storage/corpus remains the byte home when the payload is not UTF-8
document content.

World pinning: when exact World revision matters, store the public revision
identifier DungeonMind already exposes. Do not copy World rows into Buddy.

---

## 11. Failure / fallback matrix

| Observable path | Loading | Exact success | Ordinary miss | DB unavailable | Integrity failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Switched kind read | require DSN + migrated head | domain row | 404 | **fail closed**; never read old files | 500; do not repair from files | CAS 409 | read is idempotent |
| Switched kind write | same | commit | 404 | fail closed | abort transaction | 409 | identical CAS replay may no-op |
| Unswitched kind | current file authority | current behavior | current | N/A (files) | current | current | current |
| During import, before switch | files still authority | import is additive | skip empty | fail import; leave files authoritative | fail closed; no partial switch | conflict → stop | import is idempotent (§12) |
| After switch | DB only | DB | 404 | fail closed | fail closed | 409 | no file toggle |
| World Graph down | app state still serves Buddy rows | n/a | n/a | World ops fail separately | n/a | n/a | do not substitute Buddy rows for World |

There is no environment toggle that keeps both authorities live for the same
kind after switch. Dual-running during dogfood is a **named pre-switch**
compare window, not a production fallback.

---

## 12. Existing-state migration, switch, demolition

Standard lifecycle for **each** domain slice (not one mega-import later):

```text
inventory exact old authority
→ CAS-safe capture (locks / expected revisions)
→ import exact identity / revision_n / bytes / digests / state
→ verify counts + identities + digests + semantic invariants
→ exercise new read/write path against imported rows
→ switch authority for that kind/domain
→ old writes fail closed (409/410/503 named)
→ dogfood / reload proof
→ delete the replaced file writers and allowlists
```

### 12.1 Identity and idempotency

- Durable IDs (`document_id`, `run_id`) are imported unchanged. **No silent new-ID remapping.**
- Replaying the same old snapshot succeeds when DB row identity, `revision_n`,
  and digest already match.
- If a DB row exists with the same id and a **different** digest/binding →
  fail closed. Operator repair is explicit, not "best effort."
- Partial import does not switch authority.

### 12.2 Historical bytes that were never stored

The filesystem never archived Playable/Plan revisions. Import **must not
fabricate** R1…R(n-1).

Honest representation:

```text
current file bytes + current registry revision_n
        ↓
one WorkRevision at that revision_n with those bytes and digest
```

A Run that pins revision 17 with matching sha can load after import of current
revision 17. A Run that pins revision 16 when only revision 17 bytes exist
fails closed with a named "historical revision bytes were never retained"
error. Future commits then retain history going forward.

### 12.3 Plan-kind special case (AS1)

Plan `target_relpath` may be a workspace file or a corpus Session Prep path.
AS1 imports **snapshot bytes** into WorkRevision. After switch:

- reads/writes go to PostgreSQL
- corpus Session Prep files are **not** silently rewritten
- they remain corpus/source files until an explicit publish slice
- `out/workspace/plan/<uuid>.md` is no longer read authority and is demolished
  after the plan-kind switch criteria in §12.4

### 12.4 Switch and demolition criteria

A domain may switch when:

1. import verification passed
2. new path served dogfood reload
3. old writers are fail-closed in the same slice or the immediate demolition
   successor named by the roadmap

Demolition is required. Success is not "Postgres + leftover file fallback."
After Play demolition, `out/runtime/play/` is not product authority. After plan
demolition, plan Markdown is not read from `out/workspace/plan/` or corpus as
the Plan document.

CUTOVER D.2/D.3 demolition of Buddy **World Graph** runtime remains a separate
line. APP-STATE must not couple its PRs to those deletions.

---

## 13. Test / worktree / database isolation

Source isolation is not database isolation.

| Situation | Policy |
|---|---|
| Default pytest | Never use operator product DB, `dungeonmind*`, `dungeonmind_cutover_live`, or World Graph DSN |
| Per-test / per-session DB | Fixture `CREATE DATABASE dungeonbuddy_app_state_test_<unique>` from a migrated template, drop at end |
| Parallel pytest (`xdist`) | Unique database (not schema-in-shared-DB) per worker |
| Two worktrees | Distinct `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` values; default product name is not shared for destructive migrate/test |
| Local developer DB | `dungeonbuddy_application_state` |
| Destructive guards | Refuse migrate/drop/test when DSN database name matches a denylist (`dungeonmind`, `dungeonmind_cutover_live`, `postgres`, names containing `cutover_live`) or equals the World Graph URL |
| Cleanup | Test fixture owns drop. Worktree leftover DBs are operator-deleted; document the name pattern |
| CUTOVER tests | Continue using `DMB_CUTOVER_TEST_DATABASE_URL` for World Graph only |

AS1 must implement these guards as executable tests, not comments.

---

## 14. Backup, restore, portability

Proportionate personal-project posture:

| Item | Decision |
|---|---|
| What to back up | the Buddy logical database; plus any external blob locators' byte stores; corpus git remains corpus backup |
| Mechanism | `pg_dump` / `pg_restore` of `dungeonbuddy_application_state` is the first supported mechanism |
| Blobs | dump does not include object-store bytes; restore verifies metadata digests and reports missing locators |
| Post-restore verify | row counts for admitted kinds; sample digest checks; alembic head; one document load + one Run load when those domains exist |
| Not required | HA, replicas, PITR, multi-region, automated enterprise failover |

"Database is durable" is not the whole story; dump/restore plus digest verify is.

---

## 15. Speed and "pop" measurement

Persistence succeeds only when durability improves **without** making the GM
administer the software or wait long enough to leave the table moment.

### Vocabulary

| Metric | Meaning |
|---|---|
| Owning-boundary latency | service/repository call, excluding browser paint |
| End-to-end surface latency | click/key → usable UI |
| Orientation / recovery time | reload/restart → exact current moment usable |
| Interaction depth | extra confirmations, pickers, or "where did it go?" steps introduced |
| Software-caused interruption | stall that pulls attention off the table |
| External-tool abandonment | GM leaves Buddy for files/notes because resume/save/search was too slow or untrustworthy |

### Hypothesis budgets (not measured baselines)

Label: **hypothesis**. AS1+ must capture real baseline (file path) and head
(Postgres path) at the owning boundary before claiming improvement.

| Operation | Hypothesis owning-boundary p95 | Hypothesis E2E p95 | Slice that must measure |
|---|---|---|---|
| Load plan snapshot / commit typical plan | 100 ms / 200 ms | 400 ms / 500 ms | AS1 |
| Load pinned Playable revision | 150 ms | 400 ms | AS2 |
| Runtime CAS mutation | 50 ms | 200 ms | AS3 |
| Start Run + seal manifest | 250 ms | 600 ms | AS3 |
| Resume Play → current moment usable | — | 500 ms | AS4 |
| Reload/restart → exact current moment | — | 700 ms | AS4 |

A software-caused wait **> 2s** on these paths is a pop failure even if
integrity is perfect. Correctness-only migration acceptance is insufficient.

---

## 16. Relationship to Play, CUTOVER, and CON-READY

### Play

- BF1 Beat-first grammar + v2 manifest remain predecessor truth (PR #628 `b850b9f8…`).
- BF2/BF3 stay paused from deepening **file-backed** Runtime/cockpit until this
  persistence direction is implemented or the steward re-sequences.
- This document does not change Beat/Scene/Decision contracts; it maps them
  onto storage.

### CUTOVER

- Design-authority base is #634 (`31f2885c…`): production World reads are native
  DungeonMind; governed writes no longer require Buddy graph hydration.
- APP-STATE does not create a Buddy World store.
- APP-STATE does not perform D.2/D.3 demolition.
- Shared future collision hotspots (`pyproject.toml`, server bootstrap) must be
  serialized if a CUTOVER implementation lease overlaps AS1.

### CON-READY

This substrate exists to serve product stories, especially:

```text
CR-U11 durable/reopenable playable prep
CR-U12 governed agent use of saved playable material
CR-U13 prepared combat durability
CR-U14 fast unexpected combat setup
CR-U15 faster/safer than memory/manual search
CR-U17 reload/restart preserves relied-on state
```

AS1 advances durable Plan authoring (prep documents). Playable/Run/Combat
stories wait for their slices.

### Workspace identity contract

UUID identity, discard-not-delete, and kind enum remain. File path
`out/registries/workspace_documents.json` as persistence is superseded per
admitted kind as that kind switches.

---

## 17. Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Generic JSON object table | Domain invariants would move into callers; steward seed forbids it |
| Everything in DungeonMind schemas | Second World authority / FK coupling; CUTOVER forbids it |
| Bespoke `play.db` | Other surfaces cannot reuse substrate; Play becomes a snowflake |
| SQLAlchemy ORM as the product model | Couples domain to ORM; Alembic may use SQLAlchemy as a tool only |
| Depend on `dungeonmind[postgres]` for Buddy app-state drivers | Accidental coupling; World extra is not Buddy lifecycle |
| Automatic migrate on app boot | Surprise production mutation |
| Permanent file fallback / env toggle after switch | Split authority; untrue durability |
| Event sourcing for Runs | Current-state authority is enough; mutation log is a later optional capability |
| Fabricating historical revisions on import | Dishonest; fails the R16-missing case the wrong way |
| Second PostgreSQL server for AS1 | Unnecessary operator ceremony; same server, different database |
| Migrating all kinds/tables in AS1 | Multiple independently useful outcomes; split |
| Treating localStorage as durable authority after switch | Fails worktree/browser-loss (C2S27 residual) |
| SQL FK into DungeonMind | Authority bleed |
| Keeping rebase-intent files after DB transactions exist | Compatibility theater |
| CDN URL / corpus path / filesystem path as domain identity | Locators are not stable product IDs |
| Forcing large binary bytes into PostgreSQL pages | Asset boundary + DungeonMindServer storage/CDN |
| Ingest / Asset / generated-artifact schemas in AS1 | Speculative tables; AS1 is Plan-only |
| Universal WorkObject / `application_object (id, type, jsonb)` | Domain invariants belong in domain schemas |

---

## 18. Deliberately deferred

| Decision | Why later |
|---|---|
| `worldbuilding_source` on WorkObject | Extra World-adjacent metadata and corpus `_dungeonbuddy` publish policy |
| Combat schema columns | Combat-owned slice; freeze boundary only |
| Play→Combat wire shape | Play architecture leaves this unfrozen |
| `play_run_mutation` audit table | Not required to prove substrate |
| Account/multi-operator active-Run | Single-operator product |
| Explicit corpus publish from WorkRevision | Must not silently mutate corpus during AS1 |
| Object-store vendor choice | Policy only: metadata in Postgres, bytes external when large |
| Purging old WorkRevisions | Retention is keep-all until a real need |
| Event/outbox for DungeonMind-spanning sagas | No current Buddy-only workflow needs it |
| Docker-compose service addition | Only if the existing local server cannot `CREATE DATABASE`; default is no compose change |
| Ingest schema (`ingest.*`) | First-class future consumer for IngestRun/processing-review; path-keyed ingest today. SourceArtifact identity is Source-owned. |
| Asset service + CDN integration API | Named boundary only; no production API in AS1 |
| Generated-artifact schemas (`statblock.*`, location/NPC/shop drafts) | Earned when a real consumer slice lands |
| Card project / render lifecycle | Future domain slice |

AS1 is dispatchable after this correction without resolving these. AS1 admits
`kind=plan` only and does not require Asset, Ingest, or generated-artifact
tables.
