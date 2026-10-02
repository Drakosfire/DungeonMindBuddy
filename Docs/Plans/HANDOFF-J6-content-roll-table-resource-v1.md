# HANDOFF — J6 Content roll-table resource v1

**Status:** PROPOSED / BLOCKED. This is a design contract, not an implementation lease.

**Owner:** APP-STATE Content in DungeonMindBuddy. **Design authority:** PRIME's 2026-10-02 J6 routing decision, informed by ARCHITECTURE's exact-reference review and RAKE's read-only product audit. **Pinned design base:** Buddy `origin/main@cfec63c6df9bd14aa7a1b5963266f926c729f8ab`. The design branch owns this file only. PRIME must re-anchor, check collisions, assign a separate implementation owner and exact write/resource lease, and mark an implementation handoff ACTIVE before code work.

## Why this predecessor exists

J6 needs a physical roll to resolve against a table that belongs to the exact World Run and sealed Runbook revision. Content already retains exact immutable Runbook WorkRevisions, but admits only `plan` and `runbook` WorkObjects. The sealed Play manifest knows scenes, beats, choices, options, and transitions; it has no table member. The corpus table index uses mutable paths and timestamps, and `/api/live/resolve-roll` reads a session packet without a Run identity or durable receipt. Neither supplies a table basis for a Run.

Choose reusable, independently versioned **World-owned roll-table Content resources**. A Runbook will later reference an exact table revision. This follows the Playable authoring rule to reference reusable source truth instead of copying it into every Runbook. This first Content slice makes a table authorable, committed, and exactly retrievable; it does not make a table playable or persist a roll.

## First capability: committed World roll tables

1. Add `roll_table` as an admitted Content WorkObject kind for **World ownership only**. A roll table has a WorkObject UUID, title, active/discarded status, object CAS revision, working copy, and immutable numbered WorkRevisions with WorkRevision UUID and full SHA-256. Reject campaign ownership, session-file paths, corpus index IDs, and automatic conversion of an indexed table into a World object.
2. Support World-scoped create, draft/update, commit, current-read, and **exact committed revision** operations. Existing Content CAS and immutable-revision rules apply. A create or commit caller cannot assert an arbitrary World by naming a document from another World. The exact read requires World ID, table WorkObject UUID, revision number, WorkRevision UUID, and full content SHA; all must agree with stored authority. A current-read convenience route never substitutes for an exact pin.
3. Retain every committed table revision after a newer revision is committed or the WorkObject is discarded. An exact read of a retained revision remains possible for an already sealed Run; new authoring or new Run references to discarded resources fail according to the later manifest admission contract. No existing revision is rewritten to repair an invalid table.
4. Validate the **versioned table body before commit**. The first grammar is a single fenced `dmb-roll-table-v1` JSON document in the WorkRevision `markdown` text, with no non-whitespace text outside the fence. Its object has only `schema_version: "dmb_roll_table_v1"`, `die_sides`, and `rows`. `die_sides` is a strict integer from 2 through 1000. Each row has only `row_id`, `min`, `max`, and nonblank `outcome` text. `row_id` matches `row:[a-z0-9][a-z0-9._-]{0,127}` and is unique within that revision. `min` and `max` are strict positive integers, with `min <= max`; rows must cover every integer from 1 through `die_sides` exactly once, with no gap or overlap. A row ID is an authored stable handle within the pinned table revision. The table's durable identity is the WorkObject UUID, never a title or body marker.
5. Return a typed parsed table alongside the exact Content pin from the server-side resolver. Validation never trusts a client-supplied parsed row, title, path, or roll expression. The first grammar accepts one physical integer result in `1..die_sides`; modifiers, dice pools, randomness, weighted draws, and inferred rerolls are outside this slice. The later Run outcome service resolves the submitted integer deterministically against these rows.

The fenced JSON syntax is a small, explicit interchange grammar for an otherwise Markdown-backed Content revision. Its bytes remain the immutable Content source. A later editor or Agent can present a friendlier authoring surface, but it must commit this validated resource through Content rather than inventing a second table store.

## Authority and failure cases

The Content resolver verifies the WorkObject kind and World, exact revision number and WorkRevision UUID, raw content digest, and v1 grammar before returning rows. Wrong World, kind, object, revision, UUID, digest, discarded/unavailable current target, malformed grammar, duplicate row IDs, invalid dice domain, or incomplete/ambiguous coverage fail closed. An old exact revision is still retrievable after advance or discard when its pin is correct. No Graph node, mutable corpus path, Runbook prose, client locator, or session packet grants Content table authority.

The eventual Runbook reference must carry the table WorkObject UUID, revision number, WorkRevision UUID, full SHA, and grammar version. The later Run owner will verify same-World exact membership and seal that pin into a **new** manifest schema version; v1/v2 manifests and existing Runs remain unchanged. The manifest stores the reference, not copied table bytes. A Run never follows a table's floating current revision. If the exact reference is absent from the sealed manifest, that Run has no such table.

## Proposed implementation lease for PRIME to activate later

This design does not grant these paths. After a new re-anchor and collision check, the APP-STATE Content implementation handoff should name an exclusive allowlist drawn from:

- `src/application_state/content/types.py`, `service.py`, `repository.py`, `__init__.py`, and a Content-owned roll-table grammar/resolver module;
- one **new next-head** Alembic migration that admits World-owned `roll_table` while preserving existing `plan`/`runbook` rows and scope constraints;
- `apps/live_control_server/services/workspace_document_registry.py` and `apps/live_control_server/routes/workspace_documents.py` for World-scoped table authoring and exact-read transport;
- focused Content PostgreSQL, migration, registry, and route tests, including `tests/application_state/test_runbook_work_object_postgres.py` only if an existing shared Content invariant truly requires it.

PRIME must name exact new filenames and disposable PostgreSQL host/port/database/lifecycle before activation. Do not silently add `pyproject.toml`, lockfiles, Play, Agent runtime, UI, or Graph paths. If the generic Content store cannot admit this kind without another owner contract, return the specific schema/API need before editing. The expected topology is one Content PR, **parallel-independent by code paths** from the Agent Interaction runtime only after exact PR/path/resource checks; separate disposable databases are required. A single owner task may still choose serial execution for capacity.

Owning-boundary tests must prove strict body validation; same-World create/update/commit; wrong-World and wrong-kind rejection; object CAS and stale-write conflict; exact pin and parsed-row read; retained revision after advance/discard; wrong revision/UUID/hash rejection; migration of existing Content rows without changed meaning; and a new database upgraded to the single migration head. No provider or live product session is needed for this Content proof.

## Successors and J6 acceptance

1. **Play manifest reference predecessor:** a separate Play/Runbook owner extends the sealed manifest to a new schema version with exact external table pins, verifies same-World Content membership at Run sealing, and proves old v1/v2 Runs load unchanged. It does not copy table bodies into the manifest.
2. **Run-owned outcome ledger:** a separate append-only event/receipt records exact World + Run, expected/resulting Run revision, sealed Runbook/manifest and table pin, grammar version, submitted physical roll, stable row ID, and a small outcome snapshot. Same idempotency key and identical payload replays; changed payload conflicts without mutation; stale Run revision rejects. Reopen reads the receipt without re-resolving or rerolling. Existing Run progress/scratch semantics and legacy pure resolve-roll stay intact.
3. **DEMO Play integration:** after backend acceptance, name the first Play generation and prove the connected J6 journey in a new app instance. The first table path consumes already-authored, committed World table resources explicitly referenced by a sealed Runbook. AI-assisted Plan creation/admission of roll tables is a separately leased authoring capability and remains required for the broader planning experience.
4. **Combat linkage:** HP, initiative, conditions, and encounter state remain COMBAT-owned under `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`. J6 additionally needs a durable exact Run↔Combat handle/status association and wrong-World, stale, and reopen proofs. It must not move HP into Run progress or the roll outcome ledger. This is a separate contract and lane.

No Content, manifest, Run, Combat, Play UI, provider, corpus, or database implementation begins under this PROPOSED handoff. PRIME retains review and merge control for each bounded successor.
