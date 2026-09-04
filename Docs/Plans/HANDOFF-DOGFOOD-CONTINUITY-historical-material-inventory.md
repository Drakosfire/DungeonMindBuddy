---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DFC-1
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`
  - Branch / PR: `agent/dogfood-continuity-historical-inventory-v1` / `DOGFOOD-CONTINUITY: inventory historical product material`

  ## Verification pointer
  - Base/head: `0c598439084986fbb85f43000719d5a67b5ecc9f`
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Historical Product Material Inventory v1

**Created:** 2026-09-04  
**Status:** DONE / ACCEPTED — PR #684 merged  
**Accepted exact head:** `f32f90ee1ccc9fac150ca8147c268c517a4ec8a6`  
**Merge commit:** `8fc9989fb6da616f74876395514f4da26bd94609`  
**Formal review cycles:** 7 (Review Cycle 7 APPROVE-equivalent, review `5115921744`)  
**Successor:** DFC-2a — [`HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md) (CURRENT; not complete)  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / DFC-1`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `0c598439084986fbb85f43000719d5a67b5ecc9f`  
**PR title:** `DOGFOOD-CONTINUITY: inventory historical product material`

> Repository law: [`AGENTS.md`](../../AGENTS.md).  
> Parent product roadmap: [`ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md).  
> Completed blocking program: [`ROADMAP-surface-integration.md`](../Roadmaps/ROADMAP-surface-integration.md).  
> Application-state authority: [`ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md).  
> Play authority: [`ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md).

---

## §0 Steward design ruling

The first post-SURFACE-INTEGRATION dogfood session exposed a continuity failure that SI-6 did not attempt to prove.

The desired experience is:

> Turn DungeonBuddy on and see the Plans, Build experiments, Ingest work, Runbooks, and Play Runs already created while developing and dogfooding the product, then use that real accumulated material to assemble **Of Conks and Cons**.

The accepted SI-6 witness proved a clean-start assembled runtime. It intentionally used a newly bootstrapped APP-STATE database, seeded witness Ingest runs, and created a blank Runbook. It therefore did **not** prove historical product-material continuity.

Current implementation facts make several historical gaps plausible:

- Plan and Runbook enumeration now comes from APP-STATE PostgreSQL; leftover file rows are not mounted authority.
- Plan has an exact/idempotent legacy importer, but no normal product fallback and no automatic startup migration.
- Runbook bootstrap imports only legacy rows visible beneath the root against which the bootstrap is run.
- Build `worldbuilding_source` enumeration still depends on the current checkout's workspace registry / source records.
- Ingest now lists only canonical APP-STATE `ingest.run`; the existing importer consumes `out/registries/extraction_runs.json`, while older `GraphIngestRunManifest` artifacts may predate that registry and require adaptation.
- Legacy Play Run files under `out/runtime/play/**` are no longer production authority after AS5.

Do **not** begin by writing recovery/migration code. We do not yet know which identities are absent, which are already present under later revisions, which historical roots contain the only surviving records, or where same-ID conflicts exist.

### Chosen first slice

Build one **read-only historical continuity inventory** that compares the product's current authorities with explicitly supplied historical roots and produces an exact recovery ledger.

The inventory is a diagnostic/reconciliation tool. It must not migrate, adopt, restore, overwrite, delete, or create product state.

### Separate dogfood finding: whole-screen navigation flash

The whole-screen flash when changing Plan / Build / Ingest / Play is real and separately actionable: AppChrome navigation currently uses normal `<a href>` document navigation, so app-scoped React providers and chrome remount between surfaces.

That is **not DFC-1**. It has an independent UI/navigation invariant and write lease. Name it as successor **DFC-NAV1 — persistent app-shell navigation without full document reload**. Do not touch `App.tsx`, `AppChrome.tsx`, router/navigation code, or UI tests in this PR.

---

## §1 Mission and merge-ready invariant

**Mission:** An operator can run one read-only command against the currently configured DungeonBuddy authorities plus one or more explicitly named historical repository/worktree roots and receive a deterministic ledger showing which exact historical Plan, Build, Ingest, Runbook, and Play Run identities are already represented, safely recoverable, conflicting, malformed, or not yet comparable.

**Merge-ready invariant:**

> **DFC-1 compares historical material to current product authority only by exact durable identity and exact revision/content evidence where available; it never infers sameness from title, campaign/session label, file path, timestamp, or scan order; it never mutates product state; equivalent duplicate observations collapse only when their durable evidence agrees; same-ID disagreement is an explicit conflict; and an unavailable current authority produces COMPARISON_UNAVAILABLE rather than falsely classifying historical material as missing or recoverable.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every domain is an observation/reconciliation path; no migration or surface UX is claimed. |
| Most likely adversarial sequence | Historical root A contains ID X → root B contains the same ID with different bytes → current authority also contains X → naive scanner chooses newest/first and calls it recovered. |
| Will §7 detect that failure? | Yes. Same-ID multi-root conflict, current-authority conflict, unavailable-authority, and older-revision witnesses are mandatory. |
| Easiest owning boundary to under-test | Ingest manifest-era adaptation and legacy Play Run comparison, because both survive after their old file authorities were retired. |
| Fact that forces stop/split | A domain cannot be inventoried without introducing a new durable migration/write contract or guessing identity from non-authoritative metadata. Record `NEEDS_ADAPTER` / `ORPHAN_EVIDENCE` and rebrief instead. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-con-ready.md`; `ARCHITECTURE-application-state-layer.md`; accepted SI-6 witness; 2026-09-04 dogfood continuity notes |
| Base revision | `0c598439084986fbb85f43000719d5a67b5ecc9f` — current `main` after merged PR #683 local launcher |
| Predecessor contract | PR #682 merged @ `86296a4021816862b1ee82cbf7478b2882493963`; accepted witness head `9349cb4b64d8a4849c4f379277ddb15df1fdc81a`; Review Cycle 2 `5109075232` accepted SI-6 |
| Exact input consumed | Current configured APP-STATE + current repo root + explicit `--historical-root` directories; known legacy registry/manifest/runtime artifact shapes listed below |
| Named successor | **DFC-2 — exact historical recovery/adoption slices derived from the ledger** |
| Parallel named successor | **DFC-NAV1 — persistent app-shell navigation without full document reload**; separate UI lease |
| What remains false | Historical material is not recovered or surfaced by this PR; Of Conks and Cons is not assembled; no-flash navigation remains false |
| Explicit non-goals | No DB writes, migrations, Build registry writes, file copying, ID regeneration, UI library/history screen, navigation/router changes, PROMOTED Ingest inspection, BF3B/BF3C, Combat, Agent work |
| Branch / isolated checkout | `agent/dogfood-continuity-historical-inventory-v1` + isolated worktree/equivalent |
| Parallel lanes / collision hotspots | Re-anchor before dispatch. At handoff creation GitHub had no open PRs. Root docs are shared sequencing hotspots; `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` is shared runtime state and must be treated read-only. |
| Runtime/state ownership | Inventory may read the configured APP-STATE database and explicit historical roots. Tests use disposable APP-STATE DB + temp roots. No production database writes. |
| State-authority sync set | `ROADMAP-surface-integration.md`, SI-6 report, finish-SI handoff, `ROADMAP-con-ready.md`, `STEWARDS-ANCHOR-con-ready.md` as backward-looking predecessor/re-sequencing sync in this implementation PR |

### Backward-looking predecessor sync required in this PR

The repository still contains pre-review SI-6 language because PR #682 correctly left acceptance to the steward. Those facts are now known.

The implementation PR must record, without marking DFC-1 complete:

```text
PR #682 merged
merge SHA             86296a4021816862b1ee82cbf7478b2882493963
accepted witness head 9349cb4b64d8a4849c4f379277ddb15df1fdc81a
formal review cycles  2
SI-6 judgment         ACCEPTED
SURFACE-INTEGRATION   CLOSED
SI-7                  DONE — thaw/re-sequence decision now points to DOGFOOD-CONTINUITY DFC-1
old BF3B "CURRENT"    retired as stale sequencing; remains a later product capability
```

Sync behavior:

- `Docs/Roadmaps/ROADMAP-surface-integration.md` → SI-6 DONE, SI-7 DONE/re-sequenced, program CLOSED, temporary feature freeze lifted.
- `Docs/Reports/REPORT-surface-integration-si6-clean-start.md` → steward ACCEPTED with exact review + merge facts.
- `Docs/Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md` → COMPLETE.
- `Docs/Roadmaps/ROADMAP-con-ready.md` → no active SURFACE-INTEGRATION blocker; DFC-1 current before resuming BF3B/BF3C/Combat sequencing.
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` → remove stale BF3B CURRENT claim and point at DFC-1 / Of Conks and Cons continuity forcing function.

Do not churn stable architecture documents merely to record closure.

---

## §3 Observable inputs and required classification

### §3.1 Current product authority view

The tool must use/read the same current seams the product relies on, not inspect SQL tables and then pretend the UI would necessarily see the same thing.

At minimum inventory:

```text
Plan WorkObjects / revisions
  product seam: workspace-document / Content APP-STATE services

Runbook WorkObjects / revisions
  product seam: workspace-document / Content APP-STATE services

Play Runs
  product seam: Play Run registry/service backed by APP-STATE

Ingest ExtractionRuns
  product seam: application_state.ingest list/read service

Build worldbuilding_source records
  product seam: current workspace-document registry behavior
```

The report must record **sanitized current authority coordinates** sufficient to answer “what is Buddy actually pointed at?” without printing credentials:

```text
APP-STATE configured: yes/no
host
port
database name
schema/head status if cheaply available
current repo root
current Build registry locator
```

Never print password, full DSN, API keys, or secrets.

### §3.2 Historical roots

CLI accepts repeatable explicit roots:

```bash
--historical-root /path/to/old/checkout
--historical-root /path/to/another/worktree
```

No recursive home-directory discovery. No implicit sibling traversal. The operator decides which roots may be inspected.

For each supplied root inspect, when present:

```text
out/registries/workspace_documents.json
out/registries/extraction_runs.json
out/graph_memory/runs/**/graph_ingest_run_manifest.json
evals/graph_memory_layer/artifacts/graph_ingest_runs/**/graph_ingest_run_manifest.json
out/runtime/play/runs/*.json
out/runtime/play/reference-manifests/*.json

orphan candidate bytes with stable ID encoded by known product layout:
out/workspace/plan/<uuid>.md
out/workspace/worldbuilding/<uuid>.md
corpus/*-markdown/_dungeonbuddy/sources/<uuid>/source.md
```

Runbook target paths are primarily registry-led because historical Runbook names were not universally UUID-based. Do not guess Runbook identity from an arbitrary Markdown filename.

### §3.3 Admitted historical parsers

Reuse current checked-in contracts where they still truthfully describe the historical artifact:

- `WorkspaceDocumentRegistryDocument` / `WorkspaceDocumentRecord` for workspace registry rows.
- `ExtractionRunRegistryDocument` / canonical `ExtractionRun` for `extraction_runs.json`.
- `GraphIngestRunManifest` plus `adapt_recap_manifest_to_extraction_run()` for manifest-era candidate reconciliation.
- `PlayRunRecord` for legacy `out/runtime/play/runs/*.json` when the payload validates as that schema.
- current reference-manifest parser/type where a legacy Play Run sidecar is required to establish coherent recoverability.

Do not resurrect retired file persistence services as production authority merely to read a historical artifact.

### §3.4 Ledger item schema

Create a small internal schema, e.g. `dmb_product_continuity_inventory_v1`, with one normalized item shape carrying at least:

```text
domain
  plan | build | ingest | runbook | play_run

identity_kind
  document_id | run_id

identity
campaign_id?
session_id?
title?

historical_observations[]
  source_kind
  root
  relative_locator
  claimed_revision?
  content_sha256?
  durable_fingerprint?
  parse_status

current_authority
  status
  matching_revision?
  matching_content_sha256?
  product_discoverable

classification
reason[]
```

Stable classifications:

```text
CURRENT_EXACT
  exact identity and exact claimed revision/content/durable fields are already represented by current authority

CURRENT_CONTAINS_HISTORY
  exact identity exists and the historical claimed committed revision/content is preserved as a real historical revision even though current head advanced

RECOVERABLE_EXACT
  exact historical identity + sufficient bytes/durable fields exist; current authority is authoritatively readable and does not contain that identity

NEEDS_ADAPTER
  useful exact historical identity/evidence exists but current code has no proven safe adoption mapping for all required durable fields

ORPHAN_EVIDENCE
  bytes/evidence survive but no safe exact product identity can be established from admitted metadata

CONFLICT
  same durable identity disagrees across roots or with current authority in a way that cannot be explained by preserved historical revision semantics

MALFORMED
  claimed historical artifact cannot be parsed/validated under its admitted schema

COMPARISON_UNAVAILABLE
  current product authority cannot be authoritatively observed, so absence/recoverability cannot be claimed
```

`RECOVERABLE_EXACT` is a classification, **not permission to write**. It means a later recovery slice has enough exact evidence to design an idempotent adoption path.

### §3.5 Identity rules

Never use any of these as identity fallback:

```text
title
session label
campaign + session tuple
filename without an admitted embedded stable ID
mtime / created_at / updated_at
"latest"
first root scanned
most recently modified root
```

For Plan/Runbook historical committed rows, do not call a later current revision a conflict if the exact historical revision + digest remains preserved in APP-STATE history.

For same ID across multiple historical roots:

```text
same admitted durable fields + same relevant content digest
  → one ledger identity with multiple equivalent observations

different admitted durable fields or relevant digest
  → CONFLICT
```

For manifest-era Ingest:

```text
adapter succeeds + canonical run absent in readable APP-STATE
  → candidate RECOVERABLE_EXACT

adapter cannot establish source_artifact_id / required canonical fields
  → NEEDS_ADAPTER or ORPHAN_EVIDENCE
  → never invent a new run_id/source_artifact_id
```

For legacy Play Run files:

- compare exact `run_id` to current APP-STATE Play Runs;
- verify admitted binding fields and sidecar coherence where possible;
- absence of a current supported Play-Run importer does not permit writing one in DFC-1;
- classify enough evidence as `NEEDS_ADAPTER` unless an already-existing exact idempotent adoption seam is proven during implementation reconnaissance.

### §3.6 Output contract

CLI:

```bash
uv run python scripts/inventory_product_continuity.py \
  --historical-root /path/to/root-a \
  --historical-root /path/to/root-b \
  --output-dir out/product_continuity
```

Required outputs:

```text
stdout
  concise authority coordinates + per-domain classification counts + output paths

out/product_continuity/inventory.json
  machine-readable full ledger

out/product_continuity/inventory.md
  human-readable grouped ledger suitable for steward review
```

`out/` output is generated evidence, not authority and not committed by default.

The checked-in report in §4 captures the sanitized real dogfood result used to choose DFC-2. It must not contain credentials or unnecessary absolute home paths; use root labels / repo-relative locators in the committed report.

### §3.7 Failure behavior

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Current APP-STATE unavailable → historical roots contain records | Generate partial historical inventory, mark APP-STATE-backed comparisons `COMPARISON_UNAVAILABLE`, exit non-zero/incomplete; never say absent/recoverable | W1 |
| Same ID in roots A+B with conflicting bytes | One `CONFLICT` identity containing both observations; scan order irrelevant | W2 |
| Historical Plan rev 3, current same document at rev 7 with preserved rev 3 digest | `CURRENT_CONTAINS_HISTORY`, not conflict | W3 |
| Historical Plan ID absent from readable APP-STATE and bytes present | `RECOVERABLE_EXACT` | W4 |
| Historical Build record absent from current Build registry but exact record+bytes survive | `RECOVERABLE_EXACT` or `NEEDS_ADAPTER` according to whether an existing safe adoption seam is actually proven; never create record | W5 |
| Ingest `extraction_runs.json` row absent from readable APP-STATE | `RECOVERABLE_EXACT`; note existing explicit registry importer as candidate successor mechanism | W6 |
| Valid manifest-era Ingest adapts to canonical ExtractionRun absent from APP-STATE | `RECOVERABLE_EXACT`; note no write occurs | W7 |
| Manifest lacks required stable source identity | `NEEDS_ADAPTER`/`ORPHAN_EVIDENCE`; no generated ID | W8 |
| Legacy Play Run exact ID absent from APP-STATE | record exact binding/evidence; normally `NEEDS_ADAPTER`; no file fallback or import | W9 |
| Malformed historical artifact among valid artifacts | Keep valid ledger items; emit `MALFORMED` finding with locator; do not silently skip | W10 |
| Inventory run against product DB and roots | Product DB row counts/content and source registries unchanged after command | W11 |
| Same inputs rerun | Same normalized identities/classifications/order, excluding generated timestamp/output-path metadata | W12 |

---

## §4 Files in scope — exclusive write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `src/product_continuity/__init__.py` | Narrow exports for inventory types/runner |
| Create | `src/product_continuity/inventory.py` | Read-only authority observation, historical parsing, exact reconciliation, deterministic ledger |
| Create | `scripts/inventory_product_continuity.py` | Operator CLI; explicit roots; sanitized output |
| Create | `tests/product_continuity/test_inventory.py` | Exact identity, duplicate, malformed, manifest, orphan, classification witnesses |
| Create | `tests/product_continuity/test_inventory_postgres.py` | Current APP-STATE comparison + no-mutation + unavailable witnesses |
| Create | `Docs/Reports/REPORT-dogfood-continuity-historical-material.md` | Sanitized real dogfood ledger summary and DFC-2 disposition evidence |
| Modify | `Docs/Roadmaps/ROADMAP-surface-integration.md` | Backward sync: SI-6 ACCEPTED, SI-7 re-sequenced, program CLOSED |
| Modify | `Docs/Reports/REPORT-surface-integration-si6-clean-start.md` | Backward sync: accepted review/merge facts |
| Modify | `Docs/Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md` | Backward sync: stewardship COMPLETE |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | Thaw/re-sequence to DFC-1 continuity forcing function; BF3B no longer CURRENT |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Current pickup state points to DFC-1 / Of Conks and Cons dogfood |

**Bounded discovery exception:**

```text
Directory: tests/**
Maximum additional paths: 2
Allowed path kinds: existing tests only
Decision rule: direct regression consumers of a parser/service reused by inventory where adding one focused assertion to the owning existing test is materially stronger than duplicating the proof in tests/product_continuity.
```

A required production path outside this lease is a stop report.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/App.tsx` | DFC-NAV1 owns no-full-document-reload navigation |
| `apps/live-control-ui/src/chrome/**` | DFC-NAV1 / existing Surface Interaction ownership |
| `apps/live-control-ui/src/**` generally | No UI/library/history product surface in DFC-1 |
| `src/application_state/migrations/**` | No schema change or migration |
| `src/application_state/**/repository.py` | Existing authorities are read, not redesigned |
| `src/application_state/content/import_plans.py` | Read/reference only; no recovery execution in DFC-1 |
| `src/application_state/content/import_runbooks.py` | Read/reference only; no recovery execution in DFC-1 |
| `src/application_state/ingest/import_legacy.py` | Read/reference existing importer; do not broaden it yet |
| `apps/live_control_server/services/workspace_document_registry.py` | Read/reference product behavior; no Build authority redesign in inventory PR |
| `apps/live_control_server/services/play_run_registry.py` | Read/reference DTO/service behavior; no legacy Play persistence revival |
| `out/**` product artifacts | Read only except generated `out/product_continuity/**` reports |
| DungeonMind DB/repository | World authority is not migrated/reconciled in DFC-1; optional cross-reference belongs in later evidence if needed |

If inventory proves a required exact parser/adaptor cannot live without changing one of these production modules, stop and rebrief rather than expanding the lease.

---

## §6 Implementation contract

```text
Input:
  current repo root
  configured Buddy APP-STATE authority
  zero or more explicit historical roots
  admitted legacy artifact contracts

Output:
  dmb_product_continuity_inventory_v1 JSON ledger
  deterministic Markdown rendering of the same ledger
  concise stdout summary

Invariant:
  exact-identity, read-only, fail-closed reconciliation from §1

Failure behavior:
  APP-STATE unavailable
    → partial scan + COMPARISON_UNAVAILABLE + incomplete/non-zero result

  requested historical root missing/unreadable
    → explicit root error; no silent skip

  malformed artifact
    → MALFORMED ledger finding; continue other admitted artifacts

  same identity conflict
    → CONFLICT; never root-order/latest selection

Replay / idempotency:
  same inputs → same normalized ledger classifications/order
  changed historical root → only affected observations/classifications change
  rerun → overwrites generated report files only; product state unchanged

Trust boundary:
  Verifies:
    exact IDs, admitted schema parsing, known content digests, current product-authority observation,
    preserved exact committed revision where available, historical-root locator existence.

  Records/trusts without proving:
    that a later migration is safe beyond the evidence required for its classification;
    that raw prose without stable identity belongs to a particular WorkObject;
    that DungeonMind publication proves the corresponding Ingest run lifecycle survived.
```

### Current-authority status matrix

| Authority state | Historical item outcome |
|---|---|
| Readable + exact present/equivalent | `CURRENT_EXACT` / `CURRENT_CONTAINS_HISTORY` |
| Readable + exact absent + sufficient evidence | `RECOVERABLE_EXACT` or `NEEDS_ADAPTER` based on existing mapping support |
| Readable + exact ID disagrees | `CONFLICT` |
| Unavailable / schema behind / integrity failure | `COMPARISON_UNAVAILABLE`; never `RECOVERABLE_EXACT` based on assumed absence |

---

## §7 Evidence required to merge

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Required proof |
|---|---|---|---|---|
| W1 | Unavailable APP-STATE never becomes false absence | inventory + disposable DB | adversarial integration | disable/mispoint DB; historical rows scan; all APP-STATE comparisons unavailable |
| W2 | Same-ID conflict is scan-order independent | inventory reconciler | unit/adversarial | A→B and B→A produce identical `CONFLICT` |
| W3 | Older exact Plan/Runbook revision preserved in current history is not conflict | APP-STATE Content + inventory | PostgreSQL integration | current rev N+1 with exact historical rev N/digest → `CURRENT_CONTAINS_HISTORY` |
| W4 | Truly absent exact Plan/Runbook with bytes is identified | inventory | PostgreSQL + temp root | exact ID absent, committed bytes valid → `RECOVERABLE_EXACT` |
| W5 | Build historical record is compared against current product registry, not APP-STATE assumptions | inventory + workspace registry | temp roots | current root absent; historical exact record+bytes found; truthful classification |
| W6 | Canonical extraction registry row compares by exact run_id/durable payload | inventory + Ingest APP-STATE | PostgreSQL integration | absent exact run → recoverable; same-ID disagreement → conflict |
| W7 | Manifest-era Ingest uses admitted adapter, never synthesized identity | inventory | unit/adversarial | valid manifest adapts exact run_id; absent DB → recoverable |
| W8 | Incomplete manifest identity fails closed | inventory | unit/adversarial | missing source identity → `NEEDS_ADAPTER`/`ORPHAN_EVIDENCE`, no generated IDs |
| W9 | Legacy Play Run is inventory-only | inventory + Play APP-STATE | PostgreSQL/temp root | exact legacy run observed; no import/write; truthful current/needs-adapter result |
| W10 | Malformed artifacts remain visible | inventory | unit/adversarial | malformed + valid artifacts → valid rows plus explicit MALFORMED finding |
| W11 | Command is product-state read-only | product DB + registries | owning integration | before/after APP-STATE row/fingerprint + current registry digests identical |
| W12 | Output deterministic | renderer/reconciler | unit | shuffled root/input observation order produces stable normalized ledger |
| W13 | Real dogfood inventory answers the user's continuity question | CLI on local roots | manual/dogfood | sanitized report records actual counts/dispositions for Plan, Build, Ingest, Runbook, Play Run and configured authority coordinates |

Exact verification floor:

```bash
uv run pytest tests/product_continuity/test_inventory.py -q
uv run pytest tests/product_continuity/test_inventory_postgres.py -q
uv run python scripts/inventory_product_continuity.py --help
uv run ruff check src/product_continuity scripts/inventory_product_continuity.py tests/product_continuity
uv run python -m compileall -q src/product_continuity scripts/inventory_product_continuity.py
git diff --check
git diff --name-only 0c598439084986fbb85f43000719d5a67b5ecc9f...HEAD
```

Run the repository's normal applicable focused baseline if the new code imports production services with existing tests that may regress. Do not claim the whole UI suite as proof of this non-UI capability.

### Minimal live / dogfood proof — mandatory

Use the real configured local APP-STATE database in **read-only behavior** plus every known relevant historical DungeonMindBuddy root available to the operator.

Do not scan the user's home directory automatically. Explicitly pass roots.

At minimum capture:

```text
Current APP-STATE sanitized coordinates
Current repo root
Historical roots supplied (sanitized labels)

Plan:
  current exact
  current contains historical revision
  recoverable exact
  conflict / malformed / orphan counts

Build:
  same classification counts

Ingest:
  APP-STATE run count
  extraction_runs.json observations
  GraphIngestRunManifest observations
  exact IDs missing from current authority

Runbook:
  current vs historical exact IDs/revisions

Play Run:
  current APP-STATE Runs
  legacy file Run observations

Top recovery candidates:
  exact IDs + relative locators + reason

Conflicts:
  exact IDs + all observations; never auto-resolve
```

The committed `REPORT-dogfood-continuity-historical-material.md` must answer these questions explicitly:

1. Are we pointed at the APP-STATE database that actually contains prior product work?
2. How many prior Plan objects are already there vs only historical-file candidates?
3. How many Build source records are discoverable from the current root vs historical roots/orphan source files?
4. Of the historical Ingest sessions/runs discovered, how many are already canonical `ingest.run`, how many are importable from `extraction_runs.json`, and how many exist only as older manifests/evidence?
5. How many Runbooks and Play Runs are already in APP-STATE vs only legacy artifacts?
6. What exact recovery slices are warranted next?

If the worker cannot access any real historical roots containing prior dogfood material, the code/tests may be complete but **W13 is not**. Stop and hand back the command plus the missing live-evidence requirement; do not invent counts from fixtures.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. exact current APP-STATE sanitized coordinates used for W13;
4. historical roots supplied, using sanitized labels in the handback;
5. per-domain classification counts and top exact recovery/conflict IDs;
6. §7 required vs produced evidence + provenance;
7. proof that DB/registries were unchanged by inventory;
8. nano-commit/fix story;
9. base/head and actual changed paths vs §4;
10. paths outside §4 (`none` or stop report);
11. prior finding ledger on re-review;
12. DFC-2 proposed slices derived from evidence only;
13. DFC-NAV1 remains separate and unimplemented.

---

## §9 Acceptance rubric

- [ ] One read-only historical continuity capability is delivered; no migration or UI feature is smuggled in.
- [ ] Current product-authority coordinates are reported without credentials.
- [ ] Plan, Build, Ingest, Runbook, and Play Run domains all appear in the ledger even when empty/unavailable.
- [ ] Exact identity governs reconciliation; titles/sessions/paths/timestamps never decide equivalence.
- [ ] Preserved historical revisions are distinguished from same-ID conflicts.
- [ ] Same-ID disagreement across roots is explicit and scan-order independent.
- [ ] Manifest-era Ingest never synthesizes missing stable identity.
- [ ] Legacy Play Run files remain historical evidence, not mounted authority.
- [ ] APP-STATE unavailable produces `COMPARISON_UNAVAILABLE`, not false missing/recoverable claims.
- [ ] Inventory leaves product DB and current registries unchanged.
- [ ] Real dogfood W13 produces a sanitized checked-in continuity report.
- [ ] Backward SI-6/SI-7/CON-READY state sync is complete and does not pre-mark DFC-1 done.
- [ ] Whole-screen navigation flash remains named DFC-NAV1 and untouched by this PR.

---

## Stop conditions

Stop and report instead of expanding when any of these appears:

- recovering a domain requires a write/migration before its inventory can be truthful;
- historical material lacks exact stable identity and the only proposed match is title/session/path similarity;
- same ID disagrees and the implementation is tempted to choose newest/first;
- APP-STATE is unavailable and code attempts to classify DB absence anyway;
- a historical artifact requires resurrecting retired production file authority rather than parsing it as evidence;
- a required production change falls outside §4;
- navigation/UI work is pulled into this PR;
- DungeonMind World-state reconciliation becomes necessary to answer a separate question from product-material inventory;
- W13 cannot be run against real historical roots and the PR attempts to substitute fixtures for the dogfood claim.

Report:

```text
Stop condition:
Domain / exact identity affected:
Invariant clause affected:
What evidence exists:
Why DFC-1 cannot safely decide recovery:
Affected paths/authority layers:
Proposed DFC-2 recovery/adaptor slice:
State-authority update needed:
```
