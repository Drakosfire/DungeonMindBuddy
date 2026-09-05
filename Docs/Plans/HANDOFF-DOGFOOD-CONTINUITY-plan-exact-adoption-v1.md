---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DFC-2a
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md`
  - Branch / PR: `agent/dogfood-continuity-plan-exact-adoption-v1` / `DOGFOOD-CONTINUITY: adopt historical Plans exactly`

  ## Verification pointer
  - Base/head: `8fc9989fb6da616f74876395514f4da26bd94609`
  - Changed paths: HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Historical Plan Exact Adoption v1

**Created:** 2026-09-04
**Status:** DONE / ACCEPTED
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-plan-exact-adoption-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / DFC-2a`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `8fc9989fb6da616f74876395514f4da26bd94609`  
**PR title:** `DOGFOOD-CONTINUITY: adopt historical Plans exactly`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).  
> Parent roadmap: [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md).  
> Predecessor handoff: [`HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`](HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md).  
> Predecessor evidence: [`../Reports/REPORT-dogfood-continuity-historical-material.md`](../Reports/REPORT-dogfood-continuity-historical-material.md).

Steward acceptance (backward-only, recorded by DFC-2c):

```text
PR #685                         MERGED
accepted exact head             076f875a8a0b8cd95932c53be730b169cd5f2818
merge commit                    7a73a5a154fa0b1c2bac9689f201dd64d2524aa5
formal review cycles            5
Review Cycle 5                  APPROVE-equivalent / merge-ready
review id                       5118642428
```

---

## §0 Steward design ruling

DFC-1 is complete and merged.

```text
PR #684                         MERGED
accepted exact head             f32f90ee1ccc9fac150ca8147c268c517a4ec8a6
merge commit                    8fc9989fb6da616f74876395514f4da26bd94609
formal review cycles            7
Review Cycle 7                  APPROVE-equivalent / merge-ready
review id                       5115921744
```

Its live ledger established the continuity problem precisely:

```text
current APP-STATE at inventory time
  Plans                          0
  Runbooks                       0
  ingest.run                     0
  Play Runs                      0

historical Plan evidence
  RECOVERABLE_EXACT              5
  NEEDS_ADAPTER                  2

historical Build evidence
  NEEDS_ADAPTER                  4

historical Ingest evidence
  RECOVERABLE_EXACT             53 manifest-era runs

historical Runbook / Play Run
  no admitted evidence in scanned roots
```

All five `RECOVERABLE_EXACT` Plans are under the DFC-1 `primary-checkout` historical root and have the registry metadata + bytes required by the existing exact/idempotent Plan importer.

The two orphan-byte-only Plans are **not** part of this slice. Build recovery, Ingest recovery, Runbook/Play archive hunting, and no-flash navigation remain separate capabilities.

### Chosen next slice

Make the already-proven Plan recovery path an explicit safe operator capability, then use it against the real DFC-1 candidates and prove the normal Plan product surface can see and open the adopted material without depending on the historical root afterward.

This is intentionally narrower than a generic migration framework.

### Real dogfood target set

The DFC-1 report identified exactly these importer-ready Plan IDs:

```text
00000000-0000-4000-8000-000000000000
61b3a73b-df4e-4133-9879-bb2096796055
80630cc2-33ee-40db-bf9d-fb5217085e17
c2121a99-d0da-4ba1-b1ef-511f4f2e3abf
d6ed9790-ebbf-401d-90ba-182aff80917d
```

Those IDs belong in the **dogfood invocation/report**, not as constants in production code. The operator tool must remain exact-ID driven and reusable.

The two known Plan identities below remain out of DFC-2a because DFC-1 classified them `NEEDS_ADAPTER`:

```text
0bcfbf24-6afd-4dff-8d3b-939ca2f86cab
0eab57a6-c1e1-4b07-a66b-b29e2ef50ed4
```

---

## §1 Mission and merge-ready invariant

**Mission:** An operator can explicitly adopt selected DFC-1-verified historical Plans into the currently configured APP-STATE authority, preserving their exact document identity, revision/content, and admitted WorkObject metadata, so the normal Plan surface lists and opens the real historical material without requiring the historical checkout afterward.

**Merge-ready invariant:**

> **DFC-2a writes only explicitly selected Plan UUIDs from one explicitly supplied historical root after re-observing current product authority and reclassifying each selected identity at execution time; `RECOVERABLE_EXACT` may be adopted through the existing exact importer, `CURRENT_EXACT` / `CURRENT_CONTAINS_HISTORY` are truthful no-ops, every other classification blocks the entire requested write set; no identity, metadata, revision, or bytes are synthesized; the historical root is never mutated; the importer transaction is the only product commit point; and after success the ordinary Plan product seam returns the exact adopted identities/content from APP-STATE and remains usable after hard reload/API restart without the historical root acting as authority.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Preview, apply, replay, conflict, and product visibility all concern exact adoption of selected Plan identities into APP-STATE. |
| Most likely adversarial sequence | Operator previews ID X as recoverable → current APP-STATE changes before apply → naive recovery overwrites or duplicates X. |
| Will §7 actually detect that failure? | Yes. Current-state conflict/replay tests plus importer fail-closed behavior and all-or-nothing transaction evidence are mandatory. |
| Easiest owning boundary to under-test | Product visibility after adoption. DB rows alone do not prove the Plan chooser/snapshot seam can use the recovered Plan. |
| Fact that forces stop/split | Any selected Plan needs inferred metadata/identity, is only orphan evidence, is absent from the explicit historical registry, or requires changing Plan UI/APP-STATE schema to become visible. Stop and rebrief rather than absorbing the adapter/UI work. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-con-ready.md`; DFC-1 handoff/report; APP-STATE Content authority |
| Base revision | `8fc9989fb6da616f74876395514f4da26bd94609` — `main` after merged PR #684 |
| Predecessor contract | DFC-1 `dmb_product_continuity_inventory_v1`; existing `import_plans_from_registry()` exact/idempotent importer |
| Exact input consumed | Current configured APP-STATE; one explicit historical root; exact repeated `--document-id` UUIDs; admitted `WorkspaceDocumentRecord` + target Markdown bytes |
| Named successor | **DFC-2b — Build adaptor / locator** for four `NEEDS_ADAPTER` Build identities |
| Additional successor | **DFC-2c — manifest-era Ingest exact adoption** for 53 recoverable runs |
| Parallel named successor | **DFC-NAV1 — persistent app-shell navigation without full document reload** |
| What remains false | Two orphan Plans remain unrecovered; Build and Ingest history remain undiscoverable; Runbook/Play archive continuity remains unresolved; navigation still flashes; Of Conks and Cons is not yet fully assembled |
| Explicit non-goals | No orphan Plan adapter, Build writes, Ingest writes, Runbook/Play recovery, generic all-domain migration framework, startup auto-import, filesystem fallback, UI library/history design, router/AppChrome work, BF3B/BF3C, Combat, Agent work |
| Branch / isolated checkout | `agent/dogfood-continuity-plan-exact-adoption-v1` + isolated worktree/equivalent |
| Parallel lanes / collision hotspots | At handoff creation no open PRs. APP-STATE local DB is shared runtime state: tests must use disposable DB; the real dogfood apply must be serialized and recorded. Root sequencing docs are shared write hotspots. |
| Runtime/state ownership | Tests: disposable APP-STATE DB + temp historical root. Dogfood: configured local APP-STATE + read-only historical `primary-checkout` root. Never mutate the historical root. |
| State-authority sync set | Phase 0 backward sync: DFC-1 handoff/report + CON-READY/Stewards anchor. After DFC-2a merge: guarded direct sync marks DFC-2a DONE and selects the next DFC capability. |

### Phase 0 — backward state sync before recovery code

Current `main` contains the merged DFC-1 implementation/report but its checked-in sequencing text intentionally stopped short of steward acceptance.

The first commit in this PR must record only facts already established:

```text
DFC-1                           DONE / ACCEPTED
PR #684                         MERGED
accepted exact head             f32f90ee1ccc9fac150ca8147c268c517a4ec8a6
merge commit                    8fc9989fb6da616f74876395514f4da26bd94609
formal review cycles            7
DFC-2a                          CURRENT
```

Sync only these authorities as needed:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md
Docs/Reports/REPORT-dogfood-continuity-historical-material.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
```

Do not mark DFC-2a complete in this PR before steward acceptance.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Preview selected recoverable Plans | Existing importer is library-only; operator has no bounded recovery command | Command re-observes authority, re-runs DFC-1 reconciliation for selected IDs, prints exact disposition, writes nothing | Yes | DFC adoption service/CLI |
| Apply selected recoverable Plans | Manual Python/library invocation required | Explicit `--apply` imports only `RECOVERABLE_EXACT` selected records through existing importer | Yes | adoption service → APP-STATE importer |
| Replay after successful adoption | Direct importer can conflict with advanced/current state semantics outside its narrow replay case | Adoption preflight sees `CURRENT_EXACT` / `CURRENT_CONTAINS_HISTORY` and reports no-op without rewriting | Yes | adoption service + current authority observation |
| Unsafe selected identity | No operator wrapper enforces DFC-1 classification | `NEEDS_ADAPTER`, `ORPHAN_EVIDENCE`, `CONFLICT`, `MALFORMED`, `COMPARISON_UNAVAILABLE`, missing/duplicate historical record → no product writes | Yes | adoption preflight |
| Product list/open after apply | APP-STATE currently lacks historical Plans | Existing Plan list/snapshot seam returns exact adopted identities/content | Yes | workspace-document / Content product seam |
| Hard reload / API restart | Historical root currently contains the only surviving Plan bytes | Adopted Plans remain listable/openable from APP-STATE without re-reading historical root | Yes | assembled Plan runtime |

### Required adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| preview RECOVERABLE_EXACT → apply same exact state | exact import; no generated ID; historical root unchanged | W2/W5 |
| apply → rerun same command | selected IDs classify current; zero duplicate writes | W3 |
| selected set contains one `NEEDS_ADAPTER` ID + one recoverable ID | **entire apply blocked**; recoverable ID is not partially imported | W4 |
| historical registry row exists but target bytes disappear/change before apply | preflight or importer fails closed; no partial requested-set commit | W4/W5 |
| APP-STATE gains conflicting same ID after preview but before commit | existing importer conflict rolls back transaction; no overwrite | W5 |
| apply → start normal Buddy runtime from current worktree → historical root unavailable to runtime | Plan chooser/list + open still work because APP-STATE is authority | W8/W9 |
| hard reload/API restart after apply | exact Plan remains product-visible and content-stable | W9 |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `src/product_continuity/plan_adoption.py` | Bounded preflight/apply orchestration over DFC-1 reconciliation + existing Plan importer |
| Create | `scripts/adopt_historical_plans.py` | Explicit operator CLI; preview by default, `--apply` required for writes |
| Create | `tests/product_continuity/test_plan_adoption.py` | Pure/adversarial selection, classification, CLI/preflight evidence |
| Create | `tests/product_continuity/test_plan_adoption_postgres.py` | Disposable PostgreSQL exact import/replay/rollback/product-seam evidence |
| Create | `Docs/Reports/REPORT-dogfood-continuity-plan-exact-adoption.md` | Sanitized real five-Plan adoption + product visibility/reload witness |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md` | Backward-only DFC-1 acceptance/merge sync |
| Modify | `Docs/Reports/REPORT-dogfood-continuity-historical-material.md` | Backward-only DFC-1 steward judgment/merge sync |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | Retire DFC-1 CURRENT; record DFC-1 DONE / DFC-2a current |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Align steward current slice to DFC-2a |

**Bounded discovery exception:**

```text
Directory: tests/application_state/
Maximum additional paths: 1
Allowed path kinds: test-only extension of existing Plan importer regression proof
Decision rule: only if the existing importer owning test must be strengthened to prove rollback/idempotency needed by §1; do not modify importer semantics merely for convenience.
```

A required production path outside this lease is a stop report. In particular, needing to change `import_plans.py`, APP-STATE migrations/schema, API routes, or frontend Plan code means the current assumption "existing exact importer + existing product seam are sufficient" was false and must be rebriefed before expansion.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/application_state/content/import_plans.py` | Existing exact importer is predecessor authority. Changing it silently turns recovery orchestration into importer redesign. Stop/rebrief if genuinely required. |
| `src/application_state/migrations/**` | No schema change is justified by DFC-1. |
| `apps/live_control_server/**` | Existing Plan product seam should already enumerate APP-STATE; UI/API repair is a separate finding if witness fails. |
| `frontend/**` / `App.tsx` / AppChrome/router code | DFC-NAV1 owns no-flash navigation; DFC-2a is recovery only. |
| `src/application_state/ingest/**` | DFC-2c owns Ingest recovery. |
| Build registry/source writers | DFC-2b owns Build recovery. |
| Runbook/Play importers | DFC-2d only after more historical evidence exists. |
| `src/product_continuity/inventory.py` | DFC-1 accepted classifier is predecessor evidence. Do not weaken/change classification to make adoption pass. |

---

## §6 Implementation contract

```text
Input:
  current_repo_root
  historical_root (exactly one explicit root per invocation)
  selected document_ids[] (one or more exact UUIDs)
  apply: bool (default false)

Output:
  deterministic per-ID disposition
  aggregate preview/apply result
  on apply success: exact selected recoverable Plans durably present in APP-STATE

Invariant:
  same §1 invariant

Failure behavior:
  missing historical root/registry → reject, zero writes
  selected ID absent from historical registry → reject, zero writes
  selected non-Plan ID → reject, zero writes
  selected identity has unsafe DFC-1 classification → reject entire set, zero writes
  current authority unavailable/integrity failure → reject, zero writes
  importer conflict/integrity failure → transaction rollback + explicit failure; never overwrite

Replay / idempotency:
  same selected IDs after successful apply → CURRENT_EXACT/CURRENT_CONTAINS_HISTORY no-op
  mixed already-current + recoverable → import recoverable subset only after every selected ID is safe
  changed historical evidence → reclassify live; conflict/unsafe state blocks apply
  retry after failed transaction → starts from current authority truth; no assumed partial success

Trust boundary:
  Verifies:
    exact selected IDs
    historical registry kind=plan
    admitted historical bytes/metadata through DFC-1 reconciliation
    current authority state immediately before importer call
    post-apply product-seam exact identity/content
  Records/trusts without proving:
    operator intent to adopt the selected exact IDs
    display usefulness of historical titles
```

### CLI contract

Preferred shape:

```bash
uv run python scripts/adopt_historical_plans.py \
  --historical-root /path/to/primary-checkout \
  --document-id <uuid> \
  --document-id <uuid>
```

Default is **preview only**.

Writes require explicit:

```bash
--apply
```

Rules:

- `--document-id` is repeatable and required; no `--all`, no title/session selectors in v1.
- No implicit sibling/worktree/home discovery.
- No generated IDs.
- No copying historical files into the current checkout as authority.
- No `--force` escape hatch.
- Output must not print secrets/full DSN.

### Commit model

```text
Commit point:
  commit of existing import_plans_from_registry() unit_of_work for the subset classified RECOVERABLE_EXACT

Before commit:
  every selected ID must have a safe live disposition
  historical records/bytes have been resolved from the explicit root
  current APP-STATE is readable/at-head
  CURRENT_EXACT/CURRENT_CONTAINS_HISTORY IDs are removed from the write subset as truthful no-ops

After commit:
  postcondition verification must read through the ordinary Plan product seam

Truthful result after post-commit verification failure:
  report "adoption committed; product verification failed" rather than pretending rollback occurred
  stop/rebrief the product-seam failure; do not delete the adopted state automatically
```

### State / fallback matrix

| Observable path | Preview | Exact success | Already current | Dependency unavailable | Integrity/conflict | Replay |
|---|---|---|---|---|---|---|
| selected Plan | classify only, no writes | imported through exact predecessor importer | no-op | whole apply blocked | whole apply blocked / importer rollback | no duplicate write |
| Plan product seam | unchanged | lists/opens exact ID | lists/opens existing exact ID | visible failure, no filesystem fallback | visible failure | same APP-STATE result |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact document UUID | only supported selector | missing/duplicate/unsafe evidence blocks | No |
| Title | display only | never used to select/match | No |
| Campaign/session | evidence/display only | never used as identity fallback | No |
| Historical target path | locator for bytes under explicit root only | never identity | No |
| Existing current ID | re-observe exact current authority | conflict/unsafe → block; exact/history → no-op | No |

### Predecessor → consumer mapping

**Grounding:** accepted DFC-1 ledger + `WorkspaceDocumentRecord` + `import_plans_from_registry()`.

| Predecessor field/outcome | Consumer behavior | Transformation | Proof |
|---|---|---|---|
| `LedgerItem.identity` | exact selection/adoption key | none | W1/W2 |
| `RECOVERABLE_EXACT` | eligible for importer write subset | resolve exact `WorkspaceDocumentRecord` from explicit root | W2 |
| `CURRENT_EXACT` | already represented | no write | W3 |
| `CURRENT_CONTAINS_HISTORY` | historical revision already retained | no write | W3 |
| any unsafe classification | block entire requested set | none | W4 |
| `WorkspaceDocumentRecord` | importer input | none beyond existing importer contract | W5 |
| target Markdown bytes | WorkRevision/WorkingCopy content | existing importer normalization only | W5/W7 |

---

## §7 Evidence required to merge

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| W1 | Preview is read-only and exact-ID only | CLI/service | contract | selected IDs + dispositions; APP-STATE counts unchanged | preview mutates or supports heuristic selection |
| W2 | Recoverable exact Plan preserves identity/revision/content/metadata | disposable PostgreSQL + product seam | integration | post-apply snapshot has same document_id, revision, digest, campaign/title/session/status | synthesized/changed durable evidence |
| W3 | Replay is idempotent | disposable PostgreSQL | integration | second invocation reports already-current/no-op; row/revision counts unchanged | duplicate revision/object/write |
| W4 | One unsafe selected ID blocks entire set | service + disposable PostgreSQL | adversarial | zero selected-set writes when mixed recoverable + NEEDS_ADAPTER/CONFLICT/missing | partial import |
| W5 | TOCTOU/current conflict fails closed | importer transaction boundary | adversarial/integration | no overwrite; transaction leaves no partial requested-set import | conflict overwrites or partially commits |
| W6 | Historical root is never mutated | temp root | mutation proof | before/after file tree/digests unchanged | any historical write/copy-back |
| W7 | Product seam can list/open adopted Plan | workspace-document/Content seam | integration | `list_workspace_documents(kind="plan")` + exact snapshot/open returns adopted ID/content | DB-only proof without product seam |
| W8 | Real five-candidate apply uses DFC-1 exact IDs only | local dogfood | operator witness | apply result enumerates exact five IDs; no orphan IDs | any adapter/inferred ID enters write set |
| W9 | Normal Plan surface survives hard reload + API restart without historical root authority | assembled runtime/browser | dogfood | adopted historical Plan appears in chooser, opens correct content, survives hard reload and API restart from current worktree | surface needs historical checkout/current-root files to see/open Plan |
| W10 | DFC-1 state sync is backward-only | docs | review | DFC-1 marked accepted/merged; DFC-2a remains active/pending | docs claim DFC-2a done before review |

### Exact verification commands

At minimum:

```bash
uv run pytest tests/product_continuity/test_plan_adoption.py tests/product_continuity/test_plan_adoption_postgres.py -q
uv run pytest tests/application_state/test_plan_existing_state_import.py -q
uv run python scripts/adopt_historical_plans.py --help
uv run ruff check src/product_continuity scripts/adopt_historical_plans.py tests/product_continuity
uv run python -m compileall -q src/product_continuity scripts/adopt_historical_plans.py
git diff --check
git diff --name-only 8fc9989fb6da616f74876395514f4da26bd94609...HEAD
```

If the bounded discovery exception modifies one importer test file, include it in the focused pytest command.

### Minimal live / dogfood proof

Use the actual DFC-1 `primary-checkout` historical root and configured local APP-STATE.

1. Record sanitized authority coordinates and pre-apply Plan count.
2. Run preview for the exact five IDs listed in §0; require all five to be `RECOVERABLE_EXACT` unless current state has already changed truthfully.
3. Run the exact same command with `--apply`.
4. Record per-ID outcome and post-apply Plan count.
5. Rerun without changing input; prove no duplicate writes.
6. Start the normal Buddy runtime from the DFC-2a/current worktree—not from the historical root.
7. In the Plan surface, confirm the recovered Plans are discoverable through the existing chooser/list. Open at least:
   - one `C2 Session 27 Prep` exact identity;
   - one `C2 Session 23 Prep` exact identity.
8. Confirm opened content corresponds to the imported historical bytes and record exact document ID/revision through a supported product/API seam.
9. Hard reload while one recovered Plan is open; confirm same Plan/content remains.
10. Restart the API and confirm the same Plan can be listed/opened again.
11. Do not mount/copy the historical root as the product's normal current workspace to make W9 pass.

Capture sanitized evidence in:

`Docs/Reports/REPORT-dogfood-continuity-plan-exact-adoption.md`

The report must explicitly distinguish:

```text
adoption source root
  one-time operator input used to recover exact historical evidence

current product authority after adoption
  APP-STATE PostgreSQL

current Buddy worktree/root
  normal runtime root; absence of historical files must not hide the adopted Plan
```

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. DFC-1 predecessor acceptance/merge sync disposition;
4. §7 W1–W10 required vs produced evidence + provenance;
5. exact dogfood selected IDs and per-ID preview/apply/replay outcome;
6. sanitized APP-STATE coordinates and before/after Plan counts;
7. product/browser W9 evidence including hard reload + API restart;
8. nano-commit/fix story;
9. base/head and actual changed paths vs §4;
10. baseline failures/waivers;
11. paths outside §4 (`none` or stop report);
12. named successors still false;
13. prior finding ledger on re-review.

---

## §9 Acceptance rubric

- [ ] DFC-1 is truthfully synced as accepted/merged and DFC-2a remains pending until this review.
- [ ] Exactly one independently useful capability is delivered: selected exact historical Plan adoption into APP-STATE.
- [ ] Preview is default/read-only; writes require explicit `--apply`.
- [ ] Selection uses exact UUIDs only; no title/session/path/latest fallback exists.
- [ ] Every selected identity is reclassified live immediately before adoption.
- [ ] Only `RECOVERABLE_EXACT` enters the importer write subset.
- [ ] `CURRENT_EXACT` / `CURRENT_CONTAINS_HISTORY` are truthful no-ops.
- [ ] Any unsafe selected classification blocks the entire requested set.
- [ ] Existing importer remains unchanged unless a stop/rebrief is raised.
- [ ] Historical root remains byte-for-byte unmodified.
- [ ] Exact identity/revision/content/admitted metadata survive round-trip through the normal Plan product seam.
- [ ] Replay is idempotent and conflict is fail-closed/all-or-nothing.
- [ ] Real DFC-1 Plans are visible/openable after hard reload and API restart from the current Buddy worktree.
- [ ] No orphan Plan, Build, Ingest, Runbook/Play, navigation, BF3B/BF3C, Combat, or Agent scope entered the PR.
- [ ] Actual changed paths remain inside §4/bounded test exception.

---

## Stop conditions

Stop and report rather than broadening when any of these appears:

- one of the five DFC-1 `RECOVERABLE_EXACT` Plans no longer reclassifies safely at execution time;
- exact adoption requires changing or weakening DFC-1 classification;
- exact adoption requires generated identity, inferred metadata, or title/session matching;
- existing Plan importer must change to make the five candidate records importable;
- APP-STATE schema/migration change appears necessary;
- existing Plan product seam cannot list/open correctly adopted WorkObjects without frontend/API changes;
- historical root must become mounted runtime authority to make the recovered Plan visible;
- selected-set all-or-nothing semantics cannot be proved;
- required path falls outside §4 or collides with another active lane;
- local shared APP-STATE cannot be safely serialized for the real dogfood apply;
- baseline/head regression requires an unapproved waiver.

Report:

```text
Stop condition:
Invariant clause affected:
Exact Plan ID(s) affected:
Current DFC-1 classification:
Why existing importer/product seam is insufficient:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor/rebrief:
State-authority update needed:
```
