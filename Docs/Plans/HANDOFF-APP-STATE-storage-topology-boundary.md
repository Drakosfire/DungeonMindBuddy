---
pr_body_template: |
  ## Handoff pointer
  - Workstream: APP-STATE / architecture correction before AS1
  - Flow: APP-STATE
  - Direction: DESIGN → REVIEW
  - Handoff: Docs/Plans/HANDOFF-APP-STATE-storage-topology-boundary.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Verification pointer
  - Current architecture: Docs/Design/ARCHITECTURE-application-state-layer.md
  - Current roadmap: Docs/Roadmaps/ROADMAP-application-state.md
  - Steward anchor: Docs/Plans/STEWARDS-ANCHOR-application-state.md
  - AS1 handoff: Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md
  - This PR changes architecture/document authority only; AS1 remains the first implementation consumer.

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — APP-STATE storage-topology boundary correction

**Created:** 2026-08-24  
**Status:** READY — steward-designated architecture correction before AS1 dispatch  
**Canonical handoff path:** `Docs/Plans/HANDOFF-APP-STATE-storage-topology-boundary.md`  
**Conversation/workstream:** `APP-STATE`  
**Flow / owner:** `APP-STATE`  
**Direction:** DESIGN → REVIEW  
**Design base:** `main` `28daea7e90b396c1b9e9b5fcc12a0b9427674d8c` (merge of CUTOVER #637)  
**PR title:** `APP-STATE: generalize durable object and asset boundaries`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Existing architecture: [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Correct the accepted APP-STATE architecture before AS1 implementation so it governs all foreseeable Buddy-owned durable product objects—not only documents and Play—while preserving separate ownership for large binary bytes and World truth.

**Merge-ready invariant:**

> **The active APP-STATE authorities must state one storage-independent product law: durable Buddy-owned product objects have stable domain identity and are accessed through owning domain services; PostgreSQL owns their durable application state and asset metadata/relationships; large binary bytes are stored through DungeonMindServer's existing storage/CDN capability behind an asset-service boundary; DungeonMind remains sole World Graph authority; derived/regenerable representations are not promoted into authority merely because they are persisted. AS1 remains a Plan-only proving slice and must not create speculative Ingest, asset, generator, or Play tables.**

This is a conceptual widening of accepted AS0, not a restart of AS0 and not an implementation PR.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| What new evidence invalidated the narrower framing? | Repository/product review shows Ingest, location/corpus indexing, statblock generation, cards/assets, and foreseeable media workflows also expose storage topology as product identity/lifecycle. |
| Does this reverse AS0? | No. Shared PostgreSQL substrate + domain-owned services remains correct. The correction widens scope and sharpens the asset/derived-state boundary. |
| Does AS1 need to become bigger? | No. Plan remains the first consumer because it is the smallest real proof of configuration, migrations, UoW, CAS, revisions, import, and fail-closed behavior. |
| Biggest architecture trap | Turning `WorkObject` into a universal `id/type/jsonb` object store, or treating CDN URLs/corpus paths as permanent domain identity. |
| Biggest scope trap | Rewriting every existing Ingest/statblock/location/card design in this PR. Do not. Update the four APP-STATE authorities and leave domain migrations to future reviewed slices. |

---

## §2 Why this correction exists

AS0 correctly established:

```text
surface
  → domain service
  → Buddy Application State Layer
  → PostgreSQL
```

and correctly separated Buddy application state from DungeonMind World Graph truth.

The architecture is still too document/Play-centric in two ways:

1. It does not make **storage-independent domain identity** the explicit product law.
2. It treats large binary storage only as a non-goal rather than naming the intended durable boundary: Buddy stores asset identity/metadata/relationships; DungeonMindServer's existing storage/CDN capability stores the large bytes.

Current repository examples prove this matters beyond Play:

### Ingest

The recap/Ingest lifecycle currently reasons directly about staged raw paths, normalized recap paths, frontmatter seed files, breadcrumb files, candidate graph paths, graph-preview manifests, and preview stores. The product concept should converge toward stable `SourceArtifact` / `IngestRun` / processed-output identities rather than "the file at this path is the run/artifact."

The publication boundary remains unchanged:

```text
Buddy SourceArtifact / IngestRun / reviewed proposal
  → governed publication contract
  → DungeonMind World Graph
```

Ingest state is not World truth merely because it eventually proposes World truth.

### Generated game artifacts

The statblock lifecycle already describes a durable Buddy-side draft artifact with review/lifecycle/provenance state. Location, NPC, shop, encounter, and card generation foresee the same need: generated work must survive review and later use without being identified by the Markdown/PNG/PDF path that happens to represent it.

### Binary outputs

Cards, maps, images, PDFs, audio recordings, and future generated media need durable identity but should not be forced into PostgreSQL byte columns. DungeonMindServer already provides cloud storage/CDN facilities that Buddy can lean on. APP-STATE must define the authority split without designing or duplicating that storage implementation.

---

## §3 Settled architecture correction

The PR must encode the following model in the active authority set.

### 3.1 Four state classes

```text
A. BUDDY DURABLE APPLICATION OBJECTS

   Plan / Runbook / Play Run / Combat Runtime
   SourceArtifact / IngestRun / reviewed processing state
   generated Statblock / Location / NPC / Shop / Encounter drafts
   CardProject / agent proposals / other user-relied-on product objects

        durable domain identity + lifecycle + relationships
                            ↓
                 Buddy Application State PostgreSQL


B. LARGE / BINARY ASSETS

   images / maps / PDFs / audio / rendered cards / other large blobs

        Buddy PostgreSQL owns:
          asset identity
          digest
          media metadata
          provenance
          ownership/relationships
          storage locator metadata

        DungeonMindServer storage/CDN owns:
          large bytes
          delivery


C. WORLD TRUTH

   durable campaign-world identity, facts, relationships,
   governed World publication/history
                            ↓
                         DungeonMind


D. DERIVED / REGENERABLE STATE

   projections / indexes / thumbnails / rendered HTML / previews /
   caches / search results / exports that can be reproduced

   May be persisted for speed, but persistence alone does not make it authority.
```

### 3.2 Storage-independent identity law

Add an explicit invariant equivalent to:

> **A product object is addressed by a stable domain-level ID. Filesystem paths, corpus paths, CDN URLs, bucket/object keys, database table coordinates, and temporary generator output locations are storage locators or projections—not product identity.**

Examples the architecture should make obviously wrong as terminal design:

```text
location_id = "corpus/.../Mireward_Location_Dossiers/Foo.md"
card.image = "https://cdn.example/..." as permanent identity
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

The owning service resolves storage details.

### 3.3 Asset boundary

The architecture must name an **Asset domain/service boundary** without inventing its production API in this PR.

Minimum durable concept:

```text
AssetRecord
  asset_id
  media_type
  sha256
  size_bytes
  provenance / created_by as appropriate
  storage_provider
  storage_locator metadata
  created_at
```

Exact fields/names are not frozen here. The important authority law is:

```text
consumer stores asset_id
  → Asset service resolves storage/delivery
  → DungeonMindServer storage/CDN handles bytes
```

A CDN URL may be returned as a delivery projection (including signed/expiring URLs). It must not become the stable cross-domain reference.

Do not add an asset table or CDN client in this PR or AS1 solely because the architecture names this boundary.

### 3.4 WorkObject is not the universal object model

Preserve WorkObject / WorkRevision / WorkingCopy as the strong Content-domain primitive for document-like authored material such as Plan and Runbook.

Explicitly reject this generalization:

```text
application_object
  id
  type
  jsonb
```

for every domain.

Expected direction:

```text
shared substrate:
  configuration
  migrations
  unit of work
  transaction/CAS conventions
  failure/isolation rules

content.*
  WorkObject / WorkRevision / WorkingCopy

play.*
  Run / manifest / active Run

ingest.*
  future SourceArtifact / IngestRun / processing-review state

assets.*
  future asset identity/metadata

statblock.* / combat.* / other domain schemas
  only when a real consumer earns them
```

Schema names remain provisional until their implementation slice. The architecture should describe domain ownership, not pre-create tables.

---

## §4 Product classification test

Add a decision test that future stewards can apply before choosing persistence.

For a candidate state/object, ask in order:

1. **Is this World truth?**  
   Yes → DungeonMind authority. Buddy may reference the public World ID; do not duplicate authority in APP-STATE.

2. **Does product correctness or user trust depend on this Buddy-owned thing existing later across reload/restart/worktree/deploy?**  
   Yes → give it stable Buddy domain identity and durable application-state ownership.

3. **Are the authoritative bytes large/binary?**  
   Yes → Buddy PostgreSQL owns identity/metadata/digest/relationships; bytes go through the Asset service to DungeonMindServer storage/CDN.

4. **Can this representation be regenerated exactly enough from durable inputs?**  
   Yes → treat it as derived/cache/output unless a separate product requirement makes the particular representation itself user-owned durable state.

5. **Does it have domain-specific lifecycle/invariants?**  
   Yes → domain-owned schema/service. Do not force it into Content WorkObject or a generic JSON table.

Include at least these examples in the authority docs:

| Product concept | Classification |
|---|---|
| Plan document | Buddy durable Content object |
| Runbook | Buddy durable Content/Playable object |
| Play Run | Buddy durable Play Runtime |
| Combat encounter state | Buddy durable Combat Runtime |
| raw uploaded/recorded session audio | SourceArtifact metadata + Asset bytes |
| transcript text | Buddy durable source/processed artifact; may live in PostgreSQL if appropriately sized |
| IngestRun status/review/provenance | Buddy durable Ingest state |
| accepted World object/fact | DungeonMind World truth |
| generated statblock draft | Buddy durable generated artifact / domain state |
| location/NPC/shop draft before World publication | Buddy durable generated/authored state |
| card project/specification | Buddy durable state |
| rendered card PNG/PDF | Asset or derived render linked to exact project revision |
| projection/search index/thumbnail | Derived/cache unless a product requirement says otherwise |

---

## §5 Required updates to existing authorities

### A. `Docs/Design/ARCHITECTURE-application-state-layer.md`

Revise the architecture in place; do not create a competing architecture file.

Required changes:

- bump document version (expected `1.1`) and `updated_at`;
- widen Purpose/In-scope from document + Play persistence to durable Buddy-owned product objects;
- preserve the existing shared-substrate/distinct-domain model;
- add the four state classes from §3.1;
- add the storage-independent identity law from §3.2;
- name DungeonMindServer storage/CDN as the intended large-byte provider behind an Asset service/port;
- clarify that PostgreSQL owns asset metadata/identity/relationships, not necessarily bytes;
- explicitly state that CDN URL/storage key/path is locator metadata, not stable product identity;
- add Ingest and generated-artifact examples to the ownership/inventory discussion;
- clarify WorkObject is a Content primitive, not a universal object table;
- add the §4 classification test;
- keep World Graph boundaries unchanged: no Buddy SQL FK into DungeonMind; no direct surface SQL;
- keep AS1 implementation assumptions intact unless the widened architecture reveals a concrete contradiction.

Do not design the DungeonMindServer asset API, object-storage provider, retention policy, or CDN signing contract here.

### B. `Docs/Roadmaps/ROADMAP-application-state.md`

Required changes:

- record AS0 as completed/merged rather than `this PR`;
- insert this architecture-correction PR as the immediate design checkpoint before AS1;
- keep AS1 Plan as the next implementation slice;
- preserve AS2–AS5 Play sequencing;
- replace the vague AS6+ list with explicit **candidate migration families**, not pre-authorized schemas:
  - Ingest / SourceArtifact / processing-review state;
  - generated artifact lifecycles (statblock, location, NPC, shop, encounter, card project/specification);
  - Asset metadata/identity integration using DungeonMindServer storage/CDN for large bytes;
  - Combat;
  - remaining worldbuilding/content state;
  - optional agent proposal/task durability when product correctness requires it;
- state that order after AS5 is evidence-driven and may interleave with Play/Agent work;
- update workstream done language so storage-independent identity and old-topology demolition are part of success.

Do not invent AS6/AS7 implementation handoffs or table names merely to fill the roadmap.

### C. `Docs/Plans/STEWARDS-ANCHOR-application-state.md`

Required changes:

- update the mission/north star to include all durable Buddy-owned product objects;
- preserve DungeonMind World authority;
- add the four state classes and classification test in concise steward form;
- name Ingest as a first-class future consumer, not an incidental `AS6+` afterthought;
- name generated artifacts and Asset metadata as foreseeable consumers;
- state that DungeonMindServer storage/CDN is the intended large-byte backend and that APP-STATE should use a stable asset identity boundary rather than permanent URLs/paths;
- make clear WorkObject is not the universal application object;
- record AS0 completion and this correction as backward-looking authority state;
- keep AS1 as next implementation dispatch after this PR is accepted.

### D. `Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md`

AS1 remains intentionally narrow. Amend only enough to prevent the first implementation from baking in the old narrow assumptions.

Required changes:

- change status from `BLOCKED ON AS0` to blocked on **this architecture correction PASS/merge/re-anchor**;
- preserve Plan `kind=plan` as the only migrated product consumer;
- explicitly state the substrate being proved is intended for later domain services beyond Content;
- state WorkObject is a Content-domain primitive, not a generic container all future domains must use;
- add an out-of-scope line: no `ingest.*`, `assets.*`, generated-artifact, Combat, Runbook, or Play tables in AS1;
- state AS1 must not introduce path/URL/storage-locator identity assumptions in shared substrate APIs;
- do **not** add DungeonMindServer storage/CDN integration to AS1;
- preserve the existing Plan route/domain/PostgreSQL evidence and latency requirements.

If widening the architecture requires AS1 to implement a generic asset service or Ingest schema to remain valid, **stop**: that means the design has over-generalized the foundation.

---

## §6 Files in scope — exact write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Design/ARCHITECTURE-application-state-layer.md` | Widen accepted APP-STATE authority and asset/identity boundary |
| Modify | `Docs/Roadmaps/ROADMAP-application-state.md` | Re-sequence authority checkpoint; expose future consumer families |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-application-state.md` | Update steward north star and current state |
| Modify | `Docs/Plans/HANDOFF-APP-STATE-postgres-foundation.md` | Keep AS1 valid under widened architecture |

No other path is leased.

Specifically out of scope:

```text
Docs/Design/DESIGN-ingest-surface.md
Docs/Design/DESIGN-graph-object-authoring-surface.md
Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md
location/card/domain-specific design docs
production Python/TypeScript
pyproject.toml / uv.lock
SQL / Alembic migrations
Docker / deployment config
DungeonMind or DungeonMindServer repository changes
asset/CDN implementation
```

Those domain docs may later reference this architecture when their real migration slice is designed. Rewriting them now would turn one cross-domain law into an unbounded documentation sweep.

---

## §7 Evidence and review contract

This is a design-only PR. Evidence is document consistency and repository grounding, not pytest.

Before requesting formal review, the Agent must provide:

1. `git diff --check` clean.
2. Exact four-file lease only.
3. Search/read proof that the revised architecture does not still claim:
   - APP-STATE is only documents/Play;
   - large binary bytes belong in PostgreSQL;
   - filesystem path or CDN URL is stable product identity;
   - WorkObject is the universal application object.
4. Cross-document consistency proof:
   - Architecture north star == steward north star.
   - Roadmap keeps AS1 Plan-only.
   - AS1 references the widened architecture but adds no speculative domain implementation.
   - DungeonMind remains sole World Graph authority everywhere.
5. Concrete example matrix covering at least Plan, Play Run, Ingest source/run, statblock draft, location/card generation, binary asset, derived projection, and World fact.
6. Re-read current repository examples that motivated the correction:
   - `apps/live_control_server/routes/recap_ingest.py`
   - `apps/live_control_server/services/location_corpus_index.py`
   - `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
   Use them as evidence of foreseeable consumers; do not edit them.

### Reviewer questions

Formal review should answer:

- Does this make storage topology an implementation concern rather than a product identity concern?
- Is the Postgres vs Asset storage vs DungeonMind World authority split unambiguous?
- Does the design avoid a universal JSON object store?
- Does it avoid forcing every binary byte into PostgreSQL?
- Does it avoid making DungeonMindServer CDN URLs stable domain identity?
- Is Ingest now clearly inside APP-STATE's future scope while its World publication remains DungeonMind-owned?
- Are generated artifacts first-class foreseeable Buddy objects without pre-authorizing schemas?
- Is AS1 still one bounded, independently useful Plan migration?

One formal reviewer judgment against one exact distinct head is one review cycle per `AGENTS.md`.

---

## §8 Collision and sequencing

At dispatch base `28daea7e…`, CUTOVER D.2B design PR #638 is open. Its PR body explicitly excludes APP-STATE authority docs and implementation dependencies, so this docs-only lease is non-overlapping.

If current repository truth differs at dispatch, re-check open PRs and leases.

Sequence:

```text
AS0 architecture                                DONE (#636)
D.2A Threat authority port                      DONE (#637)

THIS PR
APP-STATE architecture scope correction
  storage-independent identity
  Ingest/generated-artifact future scope
  Asset metadata ↔ DungeonMindServer byte-store boundary

        ↓ formal PASS + merge + re-anchor

AS1 Plan PostgreSQL foundation                  NEXT IMPLEMENTATION
```

Do not dispatch AS1 from the pre-correction handoff text.

---

## §9 What remains false after this PR

After merge, all of the following remain intentionally false:

- no Buddy application-state PostgreSQL database exists yet;
- no Plan document is migrated yet;
- Ingest is still topology-heavy/file-backed where current code says it is;
- no `SourceArtifact` / `IngestRun` PostgreSQL schema exists;
- no AssetRecord schema/service exists;
- no DungeonMindServer storage/CDN integration is added;
- no generated statblock/location/NPC/shop/card artifact is migrated;
- Playable/Run/Combat persistence remains where current code puts it;
- no domain-specific old file path is demolished by this PR.

The PR succeeds by making the **authority documents tell the right future truth before AS1 lays foundation code**.

---

## §10 Steward disposition after merge

After a formal PASS and merge:

1. Re-anchor current `main`.
2. Record the merge/review cycle in the normal backward-looking APP-STATE authority sync.
3. Re-read `HANDOFF-APP-STATE-postgres-foundation.md` from merged `main`.
4. Dispatch AS1 as the first implementation consumer if no new lease collision exists.
5. Do not separately design Ingest/assets/generated-artifact schemas until a real migration/product slice is selected.

The corrected long-term north star is:

> **DungeonBuddy product objects have stable domain identity independent of storage topology. Buddy PostgreSQL owns durable Buddy application state and asset metadata; DungeonMindServer storage/CDN owns large binary bytes behind stable asset identity; DungeonMind owns World truth; derived representations remain derived.**
