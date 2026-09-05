---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DFC-2c
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ingest-manifest-adoption-v1.md`
  - Branch / PR: `agent/dogfood-continuity-ingest-manifest-adoption-v1` / `DOGFOOD-CONTINUITY: adopt historical Ingest runs exactly`

  ## Verification pointer
  - Base/head: `7a73a5a154fa0b1c2bac9689f201dd64d2524aa5`
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Manifest-era Ingest Exact Adoption v1

**Created:** 2026-09-04  
**Status:** ACTIVE — one recovery capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ingest-manifest-adoption-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / DFC-2c`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `7a73a5a154fa0b1c2bac9689f201dd64d2524aa5`  
**PR title:** `DOGFOOD-CONTINUITY: adopt historical Ingest runs exactly`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).  
> Parent roadmap: [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md).  
> Inventory predecessor: [`HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`](HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md).  
> Inventory evidence: [`../Reports/REPORT-dogfood-continuity-historical-material.md`](../Reports/REPORT-dogfood-continuity-historical-material.md).  
> Plan-recovery predecessor: [`HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md).  
> Plan-recovery evidence: [`../Reports/REPORT-dogfood-continuity-plan-exact-adoption.md`](../Reports/REPORT-dogfood-continuity-plan-exact-adoption.md).

---

## §0 Steward design ruling

DFC-2a is complete, accepted, and merged.

```text
PR #685                         MERGED
accepted exact head             076f875a8a0b8cd95932c53be730b169cd5f2818
merge commit                    7a73a5a154fa0b1c2bac9689f201dd64d2524aa5
formal review cycles            5
Review Cycle 5                  APPROVE-equivalent / merge-ready
review id                       5118642428
```

DFC-2a also corrected an important continuity assumption. Of the five Plan identities DFC-1 had classified `RECOVERABLE_EXACT`, only one had surviving admitted Markdown bytes at apply time:

```text
80630cc2-33ee-40db-bf9d-fb5217085e17    recovered exactly

00000000-0000-4000-8000-000000000000    registry identity survives; bytes absent
61b3a73b-df4e-4133-9879-bb2096796055    registry identity survives; bytes absent
c2121a99-d0da-4ba1-b1ef-511f4f2e3abf    registry identity survives; bytes absent
d6ed9790-ebbf-401d-90ba-182aff80917d    registry identity survives; bytes absent
```

Those four are now an archive/evidence-recovery problem. Do **not** fill them with blank shells, guessed prose, title/session matching, or reconstructed content. A later Plan archive slice may search coherent historical Git snapshots or additional roots, but there is no safe write to perform now.

Build is in the same evidence posture: DFC-1 found four Build identities, all `NEEDS_ADAPTER` because each is missing either recoverable bytes or registry metadata.

Ingest is different. DFC-1 established a large exact recovery set whose canonical payload can already be derived without inventing identity:

```text
historical manifest-era Ingest identities   53 RECOVERABLE_EXACT
campaign longmont-c1                         24
campaign longmont-c2                         29
canonical APP-STATE ingest.run at DFC-1      0
legacy extraction_runs.json observations     0
historical conflict / malformed              0 in the accepted W13 set
```

The accepted adaptation path is already production code:

```text
GraphIngestRunManifest
  → adapt_recap_manifest_to_extraction_run()
  → canonical ExtractionRun
```

The accepted APP-STATE write path is also already production code:

```text
canonical ExtractionRun records
  → import_extraction_runs_from_registry()
  → one APP-STATE transaction
  → ingest.run
```

### Chosen next slice

**Re-sequence DFC-2c ahead of DFC-2b.** Recover the 53 exact historical Ingest run records into canonical APP-STATE before spending another implementation PR on domains whose evidence is still incomplete.

Why this is the next highest-value safe slice:

1. The user explicitly wants **all ingestion history** back.
2. It restores 53 real historical identities instead of one or four speculative/adaptor cases.
3. DFC-1 has already proven exact stable `run_id` and canonical `ExtractionRun` payload adaptation for all 53.
4. SI-4 and SI-5B already made APP-STATE the only normal Ingest catalog authority, so successful adoption immediately restores normal product discovery without reviving a file fallback.
5. Plan-byte archaeology and Build archaeology remain useful successors, but neither currently has a safe complete write payload.

This is a **record/catalog adoption** slice. It does not claim to relocate every historical candidate-graph/component file into new durable storage. Missing component bytes must not hide the canonical DB row; artifact-byte recovery, if needed for useful historical review, is a separate evidence-driven successor.

---

## §1 Mission and merge-ready invariant

**Mission:** An operator can explicitly preview and adopt the exact manifest-era historical Ingest run set from explicitly supplied historical roots into the currently configured APP-STATE authority, preserving each canonical `ExtractionRun.run_id` and durable adapted payload, so the normal Ingest catalog shows the historical run history after restart without consulting manifest files for product existence.

**Merge-ready invariant:**

> **DFC-2c discovers only admitted `graph_ingest_run_manifest.json` evidence under explicitly supplied historical roots; reuses the accepted DFC-1 parser/adapter and current-authority reconciliation; refuses malformed, adaptation-failed, conflicting, or comparison-unavailable Ingest identities; binds every selected run to the exact canonical adapted payload fingerprint observed during preview; requires an explicit preview target-set fingerprint for bulk apply; commits only a pinned canonical `ExtractionRun` snapshot through the existing one-transaction registry importer; treats already `CURRENT_EXACT` runs as truthful no-ops; never generates or matches run identity by campaign/session/path/timestamp; never mutates historical roots; never revives manifest/filesystem product fallback; and after commit the normal APP-STATE-backed Ingest catalog exposes the exact adopted run IDs across API restart/hard reload even when historical manifests are not runtime authority.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Discovery, bulk preview, apply, replay, conflict, and product visibility all concern exact canonical adoption of historical Ingest run records. |
| Most likely adversarial sequence | Preview sees 53 exact payloads → one manifest or APP-STATE row changes before apply → naive bulk recovery commits a different set or overwrites current truth. |
| Will §7 actually detect that failure? | Yes. Target-set fingerprint handshake, observation-bound payload pinning, pre-commit revalidation, importer rollback, and replay tests are mandatory. |
| Easiest owning boundary to under-test | Product catalog continuity. `53 rows inserted` is insufficient unless the ordinary `/ingest` catalog/API sees those exact IDs after restart with no manifest fallback. |
| Fact that forces stop/split | Any of the accepted 53 cannot be re-adapted to the same canonical durable fingerprint, requires generated source/run identity, requires modifying the accepted adapter/importer, or requires copying artifact bytes merely to make the catalog row exist. Stop and rebrief. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-con-ready.md`; DFC-1 inventory; DFC-2a accepted recovery lessons; SI-4/SI-5B Ingest APP-STATE authority |
| Base revision | `7a73a5a154fa0b1c2bac9689f201dd64d2524aa5` — `main` after merged PR #685 |
| Accepted predecessor seams | `run_inventory()` / DFC-1 exact classification; `GraphIngestRunManifest`; `adapt_recap_manifest_to_extraction_run()`; `import_extraction_runs_from_registry()`; normal APP-STATE Ingest catalog |
| Historical inputs | Explicit roots only; DFC-1 W13 roots were `primary-checkout`, `of-conks`, `stewardship-si6`; admitted manifest patterns only |
| Real target | Accepted W13 historical Ingest set: 53 exact run IDs, longmont-c1=24 / longmont-c2=29 |
| Named successor | **DFC-2b — Build archive/adapter** for four `NEEDS_ADAPTER` Build identities, after bytes/metadata can be established safely |
| Additional Plan successor | **DFC-2p — Plan archive evidence recovery** for the four exact registry identities with absent target bytes plus the two orphan-byte-only Plans; no write until coherent evidence exists |
| Additional successor | **DFC-2d — Runbook/Play archive hunt** only if additional admitted roots/evidence are found |
| Parallel named successor | **DFC-NAV1 — persistent app-shell navigation without full document reload** |
| What remains false | Historical Ingest records are not yet in APP-STATE; historical component/artifact bytes are not guaranteed runtime-openable; four Plans still lack bytes; four Builds remain `NEEDS_ADAPTER`; Runbook/Play history remains unlocated; navigation still flashes |
| Explicit non-goals | No ingestion rerun, no LLM calls, no graph/canon mutation, no artifact copying, no SourceArtifact creation, no Build/Plan/Runbook/Play recovery, no generic migration framework, no startup auto-import, no manifest fallback, no UI redesign, no router/AppChrome, BF3B/BF3C, Combat, Agent work |
| Branch / isolated checkout | `agent/dogfood-continuity-ingest-manifest-adoption-v1` + isolated worktree/equivalent |
| Collision hotspots | No open PRs at handoff creation. Shared APP-STATE local DB is mutable runtime state; tests must use disposable PostgreSQL. Roadmap/anchor docs are serialized state-authority writes. |
| Runtime/state ownership | Tests: disposable APP-STATE + temp historical roots. Dogfood: configured local APP-STATE + read-only historical roots. Historical roots are evidence, never product authority. |

### Phase 0 — backward state sync before recovery code

The first commit in the implementation PR must record only facts already established:

```text
DFC-2a                          DONE / ACCEPTED
PR #685                         MERGED
accepted exact head             076f875a8a0b8cd95932c53be730b169cd5f2818
merge commit                    7a73a5a154fa0b1c2bac9689f201dd64d2524aa5
formal review cycles            5
DFC-2c                          CURRENT
DFC-2b                          LATER — evidence incomplete, re-sequenced behind DFC-2c
```

Sync only these authorities as needed:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md
Docs/Reports/REPORT-dogfood-continuity-plan-exact-adoption.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
```

Do not mark DFC-2c complete before steward acceptance.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Preview all historical Ingest from explicit roots | DFC-1 can inventory them, but there is no write-oriented operator workflow | Explicit `--all-historical-ingest` preview re-runs DFC-1/current comparison and prints exact sorted target IDs/payload fingerprints plus deterministic `target_set_sha256`; zero writes | Yes | DFC adoption service/CLI |
| Preview selected run IDs | No bounded manifest-era adoption command | Repeated exact `--run-id` limits the set; no campaign/session/title/path selectors | Yes | DFC adoption service/CLI |
| Bulk apply | Existing importer expects `extraction_runs.json`, which scanned roots do not have | `--apply` requires `--expected-set-sha256` from preview; adapter records are pinned/materialized into a throwaway canonical registry and passed to existing importer | Yes | adoption service → APP-STATE importer |
| Replay | No manifest-era operator replay | Historical rows classify `CURRENT_EXACT`; zero duplicate writes; target set remains explainable | Yes | DFC-1 reconciliation + importer |
| Unsafe historical observation | Inventory can report it but no recovery guard exists | Any selected/bulk-domain `MALFORMED`, `NEEDS_ADAPTER`, `CONFLICT`, `COMPARISON_UNAVAILABLE`, or missing exact observation blocks the entire requested apply | Yes | adoption preflight |
| Historical manifest changes after preview | Preview and manual import are currently separate | Recomputed set hash mismatch or observation-bound pin/revalidation blocks before importer commit | Yes | adoption preflight |
| APP-STATE changes after preview | Existing importer can conflict if given canonical registry | Re-observe current authority before commit; same-ID durable disagreement blocks/rolls back all new writes | Yes | DFC-1 + importer UoW |
| Product catalog after apply | APP-STATE catalog currently lacks historical runs | Normal DB-backed extraction-run catalog returns adopted exact IDs; no file fallback | Yes | Ingest catalog API/product seam |
| Runtime restart/reload | Historical manifests are currently the only surviving run records | Catalog remains present from APP-STATE after API restart/hard reload; historical roots need not be mounted for product existence | Yes | assembled Ingest runtime |
| Missing historical component bytes | A DB run may reference old component locators | Missing bytes do not hide/delete the canonical catalog row; report this as artifact-continuity debt rather than rewriting `exists` or inventing files | Yes | catalog/product seam |

### Required adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| preview 53-run bulk set → apply same roots/state/hash | one transaction imports exact absent runs; exact current runs no-op; no generated IDs | W3/W4 |
| preview bulk set → one manifest canonical payload changes before apply | `target_set_sha256` mismatch and/or observation pin mismatch; zero product writes | W5 |
| inventory → payload changes between classification and pin creation | pin must match DFC-1 adapted durable fingerprint or block; changed payload cannot become the new pin silently | W5 |
| pin created → live historical manifest changes/deletes | importer consumes pinned temporary registry, never the live root; committed payload remains the classified pin | W5 |
| selected set contains one adaptation-failed/malformed/conflicting identity plus safe IDs | entire set blocked; safe siblings are not partially imported | W6 |
| APP-STATE gains conflicting same run_id before commit | existing importer conflict rolls back the whole transaction | W7 |
| apply → replay | 53 exact current rows no-op; no duplicate/revision churn | W8 |
| apply → API restart → historical roots unavailable to runtime | normal catalog still returns exact adopted run IDs from APP-STATE | W10/W11 |
| post-commit product verification fails | truthful `applied=true` / verification failed result; do not delete committed runs; secret-safe detail | W12 |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `src/product_continuity/ingest_adoption.py` | Bounded exact manifest discovery, target-set fingerprinting, pin/revalidation, apply/report orchestration |
| Create | `scripts/adopt_historical_ingest_runs.py` | Explicit operator CLI; preview default; exact `--run-id` or explicit `--all-historical-ingest`; `--apply` requires expected set fingerprint |
| Create | `tests/product_continuity/test_ingest_adoption.py` | Pure/adversarial set selection, fingerprint, malformed/adaptation/conflict, CLI safety evidence |
| Create | `tests/product_continuity/test_ingest_adoption_postgres.py` | Disposable PostgreSQL exact import/replay/rollback/TOCTOU/product-seam evidence |
| Create | `Docs/Reports/REPORT-dogfood-continuity-ingest-manifest-adoption.md` | Sanitized real 53-run preview/apply/replay/catalog/restart witness |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md` | Backward-only DFC-2a acceptance/merge sync |
| Modify | `Docs/Reports/REPORT-dogfood-continuity-plan-exact-adoption.md` | Backward-only DFC-2a steward judgment/merge sync |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | Record DFC-2a DONE; re-sequence DFC-2c CURRENT before evidence-incomplete DFC-2b |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Align steward current forcing function and successor order |

**Bounded discovery exception:**

```text
Directory: tests/application_state/
Maximum additional paths: 1
Allowed purpose: strengthen existing ingest importer regression proof only if §1 rollback/idempotency cannot be proven from current tests.
```

A required production path outside this lease is a stop report. In particular, needing to modify any of the accepted predecessor seams below means the design assumption was false and requires rebrief:

```text
src/product_continuity/inventory.py
src/graph_memory/ingestion/graph_ingest_run.py
src/application_state/ingest/import_legacy.py
src/application_state/ingest/repository.py
src/application_state/migrations/**
apps/live_control_server/** production routes
apps/live-control-ui/** production UI
```

Do not weaken accepted classifier/adapter/importer semantics merely to make historical data fit.

---

## §5 Explicitly out of scope / collision boundary

| Path/domain | Why this slice must not touch or claim it |
|---|---|
| DFC-1 classifier | Accepted exactness authority; this PR consumes it. |
| `adapt_recap_manifest_to_extraction_run()` | Accepted manifest→canonical mapping; this PR consumes it. |
| Existing ingest registry importer | Accepted one-transaction exact/noop/conflict persistence seam; this PR supplies it a pinned canonical snapshot. |
| APP-STATE schema/migrations | `ingest.run` already exists; no schema change is justified. |
| Ingest API/UI | SI-5B already made normal catalog DB-backed. Failure of that witness is a separate product finding, not permission to expand recovery scope. |
| Historical artifact/component copying | Catalog continuity first. Do not copy candidate graphs, pass telemetry, source spans, or other files into ad hoc locations. |
| Re-running extraction / LLM work | Recovery preserves historical run records; it does not regenerate history. |
| DungeonMind/World writes | Historical Ingest record recovery is not graph canon publication. |
| SourceArtifact synthesis | Existing `source_artifact_id` must be preserved; missing source identity would be `NEEDS_ADAPTER`, not generated. |
| Plan archive recovery | Four registry identities still need coherent bytes; two orphan Plans still need metadata. Separate evidence slice. |
| Build recovery | Four identities are still `NEEDS_ADAPTER`; separate archive/adapter slice. |
| Runbook/Play archive | No admitted evidence in scanned roots. |
| AppChrome/router/navigation | DFC-NAV1. |
| BF3B/BF3C/Combat/Agent | Separate product lanes. |

---

## §6 Implementation contract

### 6.1 Operator input

```text
current_repo_root
historical_roots[]:
  root_label     required, unique, explicit
  path           required, existing directory
selection:
  repeated exact --run-id
  XOR
  explicit --all-historical-ingest
apply: false by default
expected_set_sha256: required only when apply=true
```

No selection by campaign, session, title, path, timestamp, “latest”, scan order, or root order.

### 6.2 Historical admission

Use the same admitted DFC-1 manifest patterns and parsers:

```text
out/graph_memory/runs/**/graph_ingest_run_manifest.json
evals/graph_memory_layer/artifacts/graph_ingest_runs/**/graph_ingest_run_manifest.json
```

For each exact run identity:

```text
GraphIngestRunManifest.model_validate(raw)
adapt_recap_manifest_to_extraction_run(manifest)
canonical durable payload fingerprint
DFC-1 current-authority classification
```

Equivalent duplicate observations collapse only under the accepted DFC-1 rules. Same `run_id` + differing canonical durable payload is `CONFLICT` and blocks apply.

### 6.3 Target-set fingerprint

Bulk recovery of 53 IDs must not require hand-pasting 53 UUIDs, but it also must not permit a changing implicit write set.

Preview emits a deterministic `target_set_sha256` over the selected canonical desired set, independent of root/scan order. The digest input must be equivalent to sorted tuples of:

```text
run_id
canonical adapted durable fingerprint
```

Do not include display-only locator/root ordering. Equivalent duplicate roots must produce the same target-set digest.

Apply must recompute the desired set from current historical evidence and reject before product mutation unless:

```text
provided expected_set_sha256 == recomputed target_set_sha256
```

For `--all-historical-ingest`, **every** admitted Ingest identity under the supplied roots is part of the truth surface. Unsafe identities must be reported and block apply; do not silently drop malformed/adaptation-failed/conflicting items while claiming “all history recovered.”

### 6.4 Pin canonical payloads before commit

For each `RECOVERABLE_EXACT` selected run:

1. Resolve the exact DFC-1 `HistoricalObservation`/locator that produced the adapted fingerprint.
2. Re-read and validate the manifest.
3. Re-adapt it using the accepted adapter.
4. Require the resulting durable fingerprint to equal the DFC-1 observation fingerprint and the preview target-set member.
5. Freeze the canonical `ExtractionRun` object in memory.
6. Immediately before commit, revalidate that live admitted evidence still maps to the same fingerprint.
7. Materialize only the pinned canonical records into a throwaway `out/registries/extraction_runs.json` root.
8. Invoke `import_extraction_runs_from_registry(snapshot_root, dry_run=False)`.
9. Delete the throwaway root after the importer returns; never mutate historical roots.

The existing importer is the only product commit point.

### 6.5 Classification/action map

```text
RECOVERABLE_EXACT   → adopt exact pinned canonical payload
CURRENT_EXACT       → truthful no-op
anything else       → block entire selected set
```

There is no `CURRENT_CONTAINS_HISTORY` concept for `ingest.run`; current exact durable payload is the relevant replay state.

### 6.6 Transaction and post-commit truth

Pre-commit failure:

```text
applied=false
zero new product writes from this invocation
```

Importer conflict/integrity failure:

```text
entire importer transaction rolls back
applied=false
```

After importer success:

```text
applied=true
```

From that point onward, product verification or historical-root immutability-probe failure must not erase durable-write truth or imply rollback. Follow the DFC-2a lesson:

```text
applied=true
product_verification=failed
sanitized detail explaining post-commit observation failure
committed APP-STATE rows remain untouched
```

Do not print full DSNs/passwords/secrets in operator-visible errors.

### 6.7 Product verification

After commit, verify through normal current product seams, not direct SQL alone:

1. APP-STATE ingest authority is readable.
2. Every selected `RECOVERABLE_EXACT` / `CURRENT_EXACT` run ID is present in canonical catalog with the exact durable payload fingerprint expected.
3. `GET /api/live/graph-preview/extraction-runs` (or the current normal extraction-run catalog route if renamed) enumerates the adopted DB rows without manifest fallback.
4. Missing historical component files do not remove the DB row.
5. API restart preserves the catalog.
6. `/ingest` hard reload still lists the historical runs from APP-STATE.

Do not require historical roots to be mounted as runtime product authority after adoption.

### 6.8 Output/report shape

At minimum:

```text
mode: preview | apply
historical roots: sanitized labels only in report
selected_count
target_set_sha256
per-run:
  run_id
  campaign_id
  session_id
  classification
  action: adopt | noop | block
  durable_fingerprint
aggregate:
  blocked
  applied
  importer_imported
  importer_noop
  importer_conflict
  product_verification
  historical_roots_unchanged: true | false | unknown
```

Output ordering is deterministic by `run_id`.

---

## §7 Verification contract — merge gate

### W1 — preview is read-only and explicit

Prove:

- no selection means input error;
- `--all-historical-ingest` is explicit;
- exact `--run-id` selection works;
- preview writes no APP-STATE rows and does not mutate roots;
- no campaign/session/latest/path selectors exist.

### W2 — accepted adaptation is reused exactly

Fixture manifest → canonical `ExtractionRun` payload must match direct `adapt_recap_manifest_to_extraction_run()` output field-for-field. No second adapter implementation.

### W3 — deterministic bulk target set

Across reordered roots and equivalent duplicate observations:

```text
same selected run IDs
same canonical durable fingerprints
same target_set_sha256
```

Changing one canonical durable field changes the set digest.

### W4 — exact batch import at APP-STATE owning boundary

Against disposable PostgreSQL:

```text
N RECOVERABLE_EXACT selected
→ one apply
→ N exact ingest.run rows
→ importer imported=N
→ no generated run_id/source_artifact_id
```

Test mixed current+recoverable too: current exact no-ops; absent exact imports.

### W5 — preview/pin TOCTOU fail-closed

Owning adversarial witnesses:

1. manifest canonical payload A during inventory → payload B before pin → zero writes;
2. pin A → live manifest B/delete before commit → importer still consumes pinned A only if revalidation contract allows exact A; otherwise zero writes, but B must never silently become the commit payload;
3. preview set hash A → apply recomputes set hash B → reject before product mutation.

### W6 — unsafe historical evidence blocks the set

At least:

- malformed manifest;
- adapter failure due missing stable `source_artifact_id`;
- same `run_id` / differing adapted payload across roots;
- selected run absent from admitted historical evidence;
- current authority unavailable.

Any one unsafe selected/all-domain item blocks safe siblings; zero partial writes.

### W7 — current APP-STATE conflict rolls back

Seed one same `run_id` with differing durable payload, plus one absent safe sibling. Apply must conflict/rollback and leave the sibling absent.

### W8 — replay is idempotent

After successful apply:

```text
all adopted IDs → CURRENT_EXACT / noop
imported=0
row count unchanged
canonical durable fingerprints unchanged
```

### W9 — historical roots remain evidence-only

Digest admitted manifest evidence before/after preview/apply/replay. No historical file is created, modified, renamed, or deleted.

### W10 — normal catalog sees adopted runs

Use the same product seam `/ingest` consumes. Prove exact run IDs are returned from APP-STATE and that disabling/poisoning manifest discovery cannot hide or replace them.

### W11 — assembled restart/reload witness

From the DFC-2c worktree against the recovered authority:

```text
start Buddy API + UI
open /ingest
confirm historical run catalog visible
inspect/select representative longmont-c1 run
inspect/select representative longmont-c2 run
hard reload /ingest
stop API
restart API against same APP-STATE
same exact run IDs remain visible
```

The historical roots are not the runtime catalog authority.

### W12 — truthful post-commit failure + secret-safe output

Inject product-seam failure after a successful importer commit and prove:

```text
applied=true
verification=failed
rows remain durable
replay sees CURRENT_EXACT
operator output contains no injected fake DSN/password secret
```

### W13 — missing artifact bytes are not catalog deletion

Adopt an exact run whose component URI is unavailable from the current worktree. The canonical catalog row remains present. Report component/artifact availability debt without rewriting the durable payload or hiding the run.

### W14 — real 53-run dogfood witness

Against the exact historical roots used by DFC-1 W13, first prove in an isolated clean APP-STATE authority:

```text
selected exact historical Ingest identities    53
longmont-c1                                     24
longmont-c2                                     29
unsafe selected identities                       0
preview target_set_sha256                        recorded
apply with expected hash                         success
replay                                            53 CURRENT_EXACT/noop
```

Then run the same preview against the configured local APP-STATE. If it remains safe, perform the explicit real adoption and record imported/noop counts and final catalog count. Do not claim 53 imported if some are legitimately already `CURRENT_EXACT`; claim 53 exact historical target identities represented.

The report must include representative exact run IDs from both campaigns, but it must not dump secrets or absolute home paths.

### W15 — backward-only state sync and scope

Before review handback:

- DFC-2a is recorded DONE/ACCEPTED with PR #685, 5 review cycles, accepted head and merge SHA;
- DFC-2c remains CURRENT, not DONE;
- DFC-2b is LATER because its evidence is incomplete;
- actual changed paths remain inside §4 + bounded test exception;
- `git diff --check origin/main...HEAD` passes;
- focused ruff/compile/type checks pass as applicable.

---

## §8 Review handback contract

The implementation agent must leave one PR comment containing:

1. exact PR head SHA;
2. current `origin/main` SHA;
3. nano-commit story;
4. actual changed paths vs §4;
5. focused unit/PostgreSQL test commands + counts;
6. ruff/compile/type/diff-check results;
7. exact target-set fingerprint semantics and preview hash;
8. W14 real 53-run counts and campaign split;
9. imported/noop/final catalog counts for isolated and configured APP-STATE witnesses;
10. historical-root immutability evidence;
11. representative normal catalog/API/UI restart/reload evidence;
12. explicit artifact-byte non-claim and any unavailable-component count discovered;
13. secret-safe post-commit failure witness;
14. prior-finding ledger if review cycles occur;
15. statement that no DFC-1 classifier, manifest adapter, ingest importer, migration, production API/UI, Build, Plan archive, Runbook/Play, navigation, Combat, or Agent code changed.

Formal review is against one exact distinct head. Do not merge without explicit user direction.

---

## §9 Stop conditions

Stop and report instead of widening scope if any of these become true:

1. any of the accepted W13 53 target identities cannot be reproduced from admitted manifests with the same stable `run_id` and canonical adapted payload fingerprint;
2. safe adoption requires generated `run_id`, `source_artifact_id`, campaign/session inference, or title/path/timestamp matching;
3. the accepted DFC-1 classifier or manifest adapter must be changed to call the evidence exact;
4. the existing registry importer cannot commit the canonical pinned set atomically without production changes;
5. APP-STATE schema changes are required;
6. the normal Ingest catalog still depends on manifests for product existence;
7. component/artifact files must be copied or rewritten merely to keep a canonical DB run visible;
8. the configured local APP-STATE contains conflicting same-ID historical runs that cannot be reconciled exactly;
9. root mutation would be required;
10. a production path outside §4 is required.

The correct outcome in those cases is a precise successor handoff, not a larger DFC-2c PR.

---

## §10 Successor decision after DFC-2c

After acceptance, re-run continuity observation and choose from evidence rather than returning automatically to the old roadmap order.

Likely next choices:

```text
DFC-2p
  Plan archive evidence recovery
  → coherent Git snapshot/additional-root search for four registry IDs with missing bytes
  → metadata adapter for two orphan-byte-only Plans only if exact metadata can be recovered

DFC-2b
  Build archive/adapter
  → locate bytes for three registry-only Build identities
  → recover registry metadata for one orphan-byte Build identity

DFC-2d
  Runbook/Play archive hunt
  → only if additional historical roots/evidence are found

DFC-NAV1
  persistent app-shell navigation
  → independent UI lane

then
  Of Conks and Cons assembled dogfood
  → re-sequence BF3B / retrieval / Combat / Agent from observed product gaps
```

Do not let successful catalog recovery silently imply historical artifact bytes, Play history, Build history, or no-flash navigation are solved.
