---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  An authorized caller can submit one verified response-carried
  `dmb_worldbuilding_write_plan_v1` and have the server commit exactly that
  sealed effect to the World Graph so the reviewed worldbuilding decisions
  become durable without repeating identity inference.

  ## Merge-ready invariant
  For one exact verified worldbuilding write plan pinned to one parent World
  Graph revision, the server either advances the head exactly once with a
  contribution materialized only from rebuild-verified authority, or refuses
  without mutation. Client-mutated presentation fields cannot alter the write;
  stale parent and exact retry are truthful; existing recap `/confirm` remains
  unchanged and continues to reject the worldbuilding plan schema.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Happy-path prepare→confirm advances head once | HTTP + Kernel | owning API test | {{TODO}} |
  | Rebuild-as-verify before any write | service | adversarial reseal tests | {{TODO}} |
  | Presentation tamper does not change write | service | summary/diagnostics/confirmable reseal | {{TODO}} |
  | Stale parent → 409, no mutation | HTTP | concurrent-head / wrong-parent tests | {{TODO}} |
  | Exact retry → already_applied, no second revision | HTTP | retry after commit | {{TODO}} |
  | Recap `/confirm` still rejects plan schema | HTTP | regression | {{TODO}} |
  | Recap prepare/confirm unchanged | regression suite | owning suite | {{TODO}} |

  ## Scope and explicit deferrals
  Base: origin/main after PR #411. Successors still false: BLD-10c UI, plan
  registry, identity merge/split UI, recap confirm redesign.

  ## Evidence produced
  ### Automated
  {{TODO}}
  ### Adversarial
  {{TODO}}
  ### Regression
  {{TODO}}
  ### Manual / dogfood
  Not required for merge — API contract proof is sufficient.

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence, operator waiver, and stop condition}}
---

# HANDOFF — BLD-10b worldbuilding plan confirm and graph commit

**Created:** 2026-07-26.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr415-bld10b-worldbuilding-write-plan-confirm.md`
**Implementation base:** `b4f3f56488c17f2b6043739ecf51e0d9d7a223f6` — `origin/main` after PR #411 (BLD-10a) merged (`66f171f0311fbab038bd464624259771812e2b4a` is the BLD-10a merge commit; re-anchor if `main` moved).
**Required predecessors:** PR #411 / BLD-10a (merged), PR #394 / BLD-08, PR #393 / BLD-07.
**Suggested branch:** `agent/bld10b-worldbuilding-write-plan-confirm`
**Planned PR:** #415 (next after open #414).

> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, the merge-ready invariant and required evidence survive critique, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Independently useful outcome** | An outcome that provides value or establishes a reusable contract even if neighboring work never ships. |
| **Public/durable contract** | A persisted format, identifier, API, event, schema, file representation, caller-facing type, or externally consumed interface that must remain interpretable beyond one call stack. |
| **Observable path** | A user-visible or externally observable route through the behavior, including success, miss, error, retry, persistence, and operator paths. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved: serializer, store, service, route, component, workflow, CLI, or equivalent. |
| **Invariant** | The single property every changed layer and observable path establishes or proves. |
| **Evidence ledger** | The mapping from each invariant clause to its owning boundary, required proof, produced result, provenance, and merge-blocking stop condition. |
| **Stop condition** | A discovered fact that invalidates the current slice boundaries or required proof and must be reported before implementation continues. |
| **Authority rebuild** | Re-run the producer from the exact pinned inputs and require exact equality of digests and effect. Selected-field checks are not a trust boundary. |
| **Sealed write plan** | A response-carried `dmb_worldbuilding_write_plan_v1` object produced by BLD-10a prepare. |
| **Commit authority** | Digests + effect produced by rebuild-as-verify against server-resolved trusted context — never client presentation fields. |

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User/operator surface? | Failure model changed? | Independently testable? | Decision |
|---|---|---|---|---|---|---|
| Confirm a verified worldbuilding write plan and advance the World Graph head | Yes | Yes (confirm API + durable contribution/revision) | API only | Yes | Yes | **Include** |
| Dedicated confirm route under extract-promote | No — required boundary for the selected capability | Yes | API only | Yes | Yes | **Include** |
| Graph Review disposition / prepare UX | Yes | Yes | Yes | Yes | Yes | **BLD-10c** |
| Durable plan registry / recovery journal | Yes | Yes | Yes | Yes | Yes | **Successor if dogfood proves needed** |
| Identity merge/split/redirect management | Yes | Yes | Yes | Yes | Yes | **Reject from this slice** |
| Recap `/confirm` redesign or shared package acceptance | Yes | Yes | Yes | Yes | Yes | **Reject** |
| Projection/reload UX of newly committed objects | Yes | Possibly | Yes | No | Yes | **Successor / BLD-10c** |

**Selected capability:** an authorized caller can submit one verified `dmb_worldbuilding_write_plan_v1` and receive either a committed World Graph revision for exactly that sealed effect, or a stable refusal without mutation.

**Named successors:** BLD-10c Graph Review disposition/publication UX; optional plan persistence; identity-decision management; graph projection polish for new objects.

## §1 Mission and merge-ready invariant

```text
An authorized caller can submit one verified response-carried
dmb_worldbuilding_write_plan_v1 and have the server commit exactly that
sealed effect to the World Graph so the reviewed worldbuilding decisions
become durable without repeating identity inference.
```

**Merge-ready invariant:** For one exact verified worldbuilding write plan pinned to one parent World Graph revision, the server either advances the head exactly once with a contribution materialized only from rebuild-verified authority, or refuses without mutation. Client-mutated presentation fields cannot alter the write; stale parent and exact retry are truthful; existing recap `/confirm` remains unchanged and continues to reject the worldbuilding plan schema.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — every path is “verify sealed plan against trusted context + parent head, then one Kernel merge or refuse.” |
| What adversarial sequence is most likely to falsify it? | Prepare succeeds → client rewrites summary/diagnostics/confirmableReason and/or effect fields with resealed digests → confirm must refuse, or if effect is authentic but head advanced → 409 stale_parent without a second contribution. Exact retry after success must return `already_applied` without a second revision. |
| Would the proposed §7 evidence actually detect that failure? | Yes — HTTP owning-boundary tests for happy path, presentation-only reseal, effect reseal, stale parent, exact retry; plus unit tests that confirm materializes from rebuilt authority, not raw client assertions. |
| Which owning boundary is easiest to under-test? | Service confirm path that trusts client `effect.accepted_proposals` after a digest check that omitted presentation/rebuild equality. |
| What fact would force this slice to stop or split? | Discovering that Kernel merge requires recap-only gates (`played_canon`, session scope, assertion_ids subset) that cannot admit the sealed worldbuilding contribution without redesigning Kernel promote; or that exact retry needs a new durable plan registry rather than contribution-ledger identity. |

Do not dispatch until the invariant and evidence plan survive this critique.

### Locked ownership decisions

1. **Dedicated confirm route.** Add `POST /api/live/extract-promote/worldbuilding/confirm` under the existing extract-promote router/service. Do **not** accept `dmb_worldbuilding_write_plan_v1` on existing `/api/live/extract-promote/confirm`.
2. **Full sealed effect.** Confirm commits the entire verified accepted effect. No second `assertion_ids` subset selection — dispositions already decided at prepare; a subset would reopen selection and identity inference.
3. **Rebuild-as-verify is the trust boundary.** Confirm must re-resolve the exact ExtractionRun, rebuild trusted context, call `verify_worldbuilding_write_plan`, and materialize the `GraphContribution` from the **rebuilt** verified plan — never from unverified client assertion bodies.
4. **Prepare remains inert.** Keep prepare `confirmable=false` and the BLD-10a `confirmable_reason`. “Confirmable” means the prepare response itself does not mutate the graph. Mutation exists only on the new confirm route.
5. **Kernel merge is the only write.** Use `kernel.merge_contribution_to_revision` (or the Kernel public equivalent already used by recap confirm). No direct world_supergraph storage imports from application code beyond existing exempted patterns; prefer Kernel public API.
6. **Recap paths unchanged.** `prepare_extract_promote`, recap semantic matrix, and `/confirm` behavior for `dmb_extract_promote_proposal_v*` remain byte- and behavior-compatible.
7. **No UI, no plan registry, no identity merges.**

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-build-surface-worldbuilding-ingest.md` Phase 6 publication exit; BLD-10a handoff successors |
| Repository rules | `external-agent-pr-loop.mdc`, `CONTRACT-graph-kernel-boundary.md`, Kernel public import boundary |
| Base revision | Re-anchor to current `origin/main` at dispatch; must contain PR #411 |
| Predecessor contract | `dmb_worldbuilding_write_plan_v1` + `verify_worldbuilding_write_plan` + `WorldbuildingWritePlanVerificationContext` from PR #411 |
| Exact input consumed | Full response-carried write plan; server-resolved exact run + parent head |
| Named successor | BLD-10c Graph Review UX |
| What remains false | No disposition UI; no plan registry; no identity merge/split; no recap confirm acceptance of worldbuilding plans |
| Explicit non-goals | PDF/OCR; extraction-quality work; Hermes tools; corpus mutation; eval-gold; Build-surface prepare button UX |

Read authoritative inputs in order before changing code:

1. `Docs/Plans/HANDOFF-bld10a-worldbuilding-write-plan-prepare.md` (predecessor contract)
2. `src/graph_memory/worldbuilding_write_plan.py` (verify + effect shape)
3. `apps/live_control_server/services/extract_promote.py` (`prepare_worldbuilding`, recap `confirm`)
4. `src/graph_memory/extract_promote_ops.py` (`confirm_extract_promote` merge/idempotency patterns)
5. Owning tests: `tests/test_worldbuilding_write_plan.py`, `tests/test_live_extract_promote_api.py`, `tests/test_extract_promote_ops_atomic.py`

If the base moved, an authority conflicts, the predecessor shape differs, or the invariant cannot be preserved, stop and report before implementation.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| `POST .../worldbuilding/confirm` with unmodified prepare package while parent current | 404 / missing | Verify → merge → `committed` with new head | Yes | route + service + Kernel |
| Confirm with rewritten presentation only (summary/diagnostics/confirmable*) | N/A | 422/409 verification failure; no mutation | Yes | service verify |
| Confirm with resealed effect tamper | N/A | verification failure; no mutation | Yes | service verify |
| Confirm when parent head advanced | N/A | `409 stale_parent_revision`; no mutation | Yes | service |
| Exact retry of same verified plan after successful commit | N/A | `already_applied`; head unchanged on retry | Yes | service + Kernel ledger |
| Existing `/confirm` with worldbuilding plan schema | `422 invalid_request` | unchanged rejection | Yes | service `confirm` |
| Recap prepare→confirm | works | unchanged | Yes | regression |
| Missing/unknown run or non-reviewable run at confirm | N/A | stable fail-closed (422/404 as prepare family); no mutation | Yes | service |
| World not initialized | N/A | `409 world_not_initialized`; no mutation | Yes | service |

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| prepare → confirm success → confirm identical package again | second call `already_applied`; one contribution; one head advance total | §7 retry test |
| prepare → concurrent head advance → confirm | `409 stale_parent_revision`; world store unchanged by confirm | §7 stale-parent test |
| prepare → mutate summary counts / insert diagnostics / omit confirmable / rewrite confirmableReason → confirm | refuse; no mutation | §7 presentation adversarial |
| prepare → rewrite accepted assertion body + reseal digests → confirm | refuse; no mutation | §7 effect adversarial |
| prepare → confirm → reload exact committed revision | contribution active; accepted nodes/edges present at committed revision | §7 post-commit reload (API/Kernel level, not UI) |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `src/graph_memory/worldbuilding_write_plan.py` | Add materialize-from-verified-plan helper (contribution from rebuild authority); keep verify as sole trust gate |
| Modify | `apps/live_control_server/models/extract_promote.py` | Confirm request/receipt models for worldbuilding plan |
| Modify | `apps/live_control_server/services/extract_promote.py` | `confirm_worldbuilding` service: resolve run, trusted context, verify, merge, stale/already_applied |
| Modify | `apps/live_control_server/routes/extract_promote.py` | `POST /worldbuilding/confirm` route |
| Modify | `tests/test_worldbuilding_write_plan.py` | Unit/contract proofs for materialize + verify-before-write helpers |
| Modify | `tests/test_live_extract_promote_api.py` | HTTP owning-boundary: commit, stale, retry, presentation/effect refuse, recap `/confirm` rejection |
| Modify | `tests/test_extract_promote_ops_atomic.py` | Only if Kernel merge wiring needs an ops-level atomic proof for worldbuilding; otherwise leave untouched |

**Bounded discovery exception:**

```text
Directory: apps/live_control_server/
Maximum additional paths: 2
Allowed path kinds: error-mapping helpers or __init__/exports strictly required by the new route/models
Decision rule for including one: compile/import failure without it; no new product surface
```

Unrestricted globs are prohibited. If another path is needed, stop and report.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/**` | BLD-10c |
| Recap `prepare_extract_promote` / `/confirm` package shape | Must remain unchanged; only continue rejecting worldbuilding schema |
| `src/prompts/**` | No prompt work |
| `evals/**/gold/**` | No gold edits |
| Plan registry / disk journal under world root | Successor |
| Identity merge/split/redirect APIs | Separate Kernel/product work |
| `candidate_semantic_promote_matrix` recap path | Must not broaden recap `played_canon` rules |
| Build extraction toolbar / dogfood markdown canvas | Not publication |
| BLD-09 PDF/OCR | Separate workstream |

## §6 Implementation contract and conditional matrices

```text
Input:
  full dmb_worldbuilding_write_plan_v1 response package (camelCase or snake_case aliases as verify already accepts)
  server principal (same extract-promote confirming principal pattern)
  server-resolved: DEFAULT_WORLD_ID, world_graph_root(), exact ExtractionRun for plan.run_id

Output:
  worldbuilding confirm receipt:
    outcome: committed | already_applied
    world_id, plan_id, plan_digest, decision_digest
    parent_revision_id, committed_revision_id
    head_advanced: bool
    contribution_id
    applied_assertion_count (from verified accepted assertions)
  On success committed: World Graph head == committed_revision_id
  On already_applied: head unchanged by this call; contribution already active

Invariant:
  same as §1

Failure behavior:
  malformed package → 422 invalid_request
  verification failure (tamper/mismatch) → 422 or 409 with code plan_verification_failed (or existing verify codes); no mutation
  stale parent (head ≠ plan.parent_revision_id) → 409 stale_parent_revision; no mutation
  unknown / non-reviewable run → same family as prepare (422/404); no mutation
  world not initialized → 409 world_not_initialized; no mutation
  merge refused → 409 merge_did_not_publish (or Kernel-mapped code); no silent success

Replay / idempotency:
  same verified plan after successful commit → already_applied (contribution ledger)
  changed plan / different digests → not already_applied; verify or merge as a distinct contribution
  retry after stale parent when contribution not applied → 409 stale_parent_revision

Trust boundary:
  Verifies:
    plan envelope identity vs trusted context from server-resolved run
    rebuild-as-verify digests + effect + summary + diagnostics + confirmable contract
    parent head == plan.parent_revision_id immediately before merge
  Records or trusts without proving:
    nothing from client presentation fields as write authority
  Response-/client-carried authority:
    rebuild producer from pinned inputs → exact digest/effect equality
    not selected-field hand checks of a deterministic mapper
```

### Commit model

```text
Commit point:
  successful kernel.merge_contribution_to_revision with published=true

Before commit:
  resolve exact run for plan.run_id
  build WorldbuildingWritePlanVerificationContext from server-resolved values
    (world_id, parent from plan only after it matches current head check —
     preferred order: require head == plan.parent_revision_id first, then verify)
  verify_worldbuilding_write_plan(plan, preview=typed_preview, world_root, context)
  materialize GraphContribution from rebuilt verified effect/meta
    (accepted/rejected/unresolved from rebuilt plan, proposal_digest=decision_digest,
     authored_by and source_kind from worldbuilding constants)

After commit:
  return committed receipt with committed_revision_id and contribution_id

Truthful result after a post-commit audit failure:
  follow recap confirm precedent: if published, do not claim clean failure that invites unsafe retry;
  prefer published_audit_degraded / equivalent truthful receipt if audit fails after head advance
```

### A. State and fallback matrix

| Observable path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| worldbuilding confirm | N/A | committed + head advanced | unknown run → not-found family | world missing → 409 | plan_verification_failed | stale_parent 409 | exact → already_applied |
| recap confirm | unchanged | unchanged | unchanged | unchanged | unchanged | unchanged | unchanged |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Bind targets | Already sealed in plan; revalidated only via rebuild against pinned parent | Rebuild failure | No label/alias inference |
| create_new node ids | From sealed/rebuilt effect only | N/A | No |
| Labels / aliases | Never used to choose merge targets at confirm | Reject if client tries to inject via tamper | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| confirm commit | Kernel contribution record + world revision + head | contribution_id deterministic from sealed contribution identity | already_applied when active | consume `dmb_worldbuilding_write_plan_v1` only | no automatic rollback; head advance is the commit |
| prepare | still response-carried only | unchanged from BLD-10a | rebuild same plan | v1 | N/A |

### D. Predecessor-to-consumer mapping

**Grounding source:** BLD-10a `WorldbuildingWritePlanResponse` / `_plan_mapping` fields and `verify_worldbuilding_write_plan` API.

| Predecessor field / outcome | Real shape | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `schema` | `dmb_worldbuilding_write_plan_v1` | required | reject other schemas | API test |
| `planId` / digests | strings | verified by rebuild | none | adversarial tests |
| `parentRevisionId` | string | must equal current head before merge | compare to Kernel head | stale-parent test |
| `runId` | extraction run id | resolve run; trusted context | server resolve | mismatch tests |
| `effect` | sealed contribution projection | rebuild equality; materialize from rebuilt | GraphContribution | unit + API |
| `summary` / `diagnostics` / `confirmable*` | presentation | verified; never write inputs | ignored for merge payload | presentation tamper tests |
| Existing `/confirm` | recap package | continues to reject worldbuilding schema | unchanged | regression |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Prepare→confirm commits exactly once and advances head | HTTP | contract | API test happy path | `committed`, head changed once, contribution active | head unchanged or double advance |
| Contribution matches rebuilt accepted effect | service/unit | contract | materialize + reload assertions at committed revision | accepted assertion ids/labels/kinds match rebuilt plan | any client-only field survives into durable contribution |
| Presentation-only tamper refuses without mutation | HTTP/service | adversarial | mutate summary/diagnostics/confirmable*/reason | non-2xx; world bytes unchanged | any accept |
| Effect reseal refuses without mutation | HTTP/service | adversarial | rewrite accepted assertion + reseal digests | verification failure; no mutation | accept |
| Stale parent → 409 | HTTP | adversarial | advance head between prepare and confirm | `409 stale_parent_revision` | 500 or silent write |
| Exact retry → already_applied | HTTP | adversarial | confirm twice | second `already_applied`; one revision | second revision |
| Recap `/confirm` rejects worldbuilding schema | HTTP | regression | post plan to `/confirm` | `422 invalid_request` | accept |
| Recap prepare/confirm still green | regression | regression | owning suite | no new failures vs base waiver set | new recap failures |
| Kernel boundary tests | regression | regression | `test_graph_kernel_boundaries` | no new violations; baseline waiver explicit | new violations on head |

Run and record:

```bash
uv run pytest \
  tests/test_worldbuilding_write_plan.py \
  tests/test_live_extract_promote_api.py \
  tests/test_promotable_ingest_run.py \
  tests/test_worldbuilding_profile_pipeline.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_graph_kernel_boundaries.py \
  tests/test_graph_kernel_public_api.py \
  -q --tb=line

git diff --check
git diff --stat <base>...HEAD -- <§4 paths>
git diff --name-only <base>...HEAD
```

### Minimal live / dogfood proof

```text
Not applicable — API owning-boundary tests prove commit/refuse/retry.
UI dogfood is BLD-10c.
```

### Baseline failure protocol

If `test_graph_kernel_boundaries.py` still fails identically on base (known BLD-10a waiver set), record base vs head comparison and explicit operator waiver. Do not call the suite green. New boundary violations on head are merge-blocking.

## §8 Required PR description and handback

The PR description must remain current and include:

1. §1 Mission copied exactly.
2. §1 merge-ready invariant copied exactly.
3. The §7 evidence ledger: required evidence, produced result, and provenance.
4. Base SHA/revision and head SHA/revision.
5. Actual changed paths and focused diff stat limited to §4.
6. Every §7 command/scenario and exact result.
7. Provenance of each result: author-local, independently rerun local, CI, or manual/dogfood.
8. Baseline failures with base/head comparison.
9. Explicit operator waivers; `none` when none exist.
10. Paths outside §4; `none` or a stop report.
11. Stop conditions encountered and resolution; `none` when none exist.
12. Successor capabilities deferred and still false (BLD-10c, plan registry, identity UI).
13. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 was delivered — proved by happy-path prepare→confirm API test.
- [ ] The merge-ready invariant holds across every observable path and adversarial sequence in §3 — proved by §7 stale/retry/tamper/regression rows.
- [ ] The PR description restates the exact invariant and exposes a complete, truthful evidence ledger.
- [ ] Every required proof has a produced result and provenance, or an explicit operator waiver.
- [ ] No second public/durable contract was silently introduced beyond the worldbuilding confirm request/receipt — proved by diff inspection + contract tests.
- [ ] State, fallback, identity, persistence, and predecessor behavior follow every applicable §6 matrix — proved by §7 proofs.
- [ ] Response-/client-carried authority is proved by rebuild equality after reseal — not selected-field checks alone — proved by presentation and effect adversarial tests.
- [ ] Real predecessor vocabulary and shapes are used — proved by consuming `dmb_worldbuilding_write_plan_v1` from prepare.
- [ ] No path outside §4 changed — proved by `git diff --name-only`.
- [ ] Baseline failures are reported truthfully and any required waiver is explicit — proved by base/head evidence.
- [ ] Minimal live proof did not grow into an unacknowledged product surface — Not applicable reason holds.
- [ ] Named successors (BLD-10c UI, plan registry, identity merge UI) remain unimplemented and unclaimed.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- Kernel merge cannot accept worldbuilding `source_extraction` contributions without recap-only gates that require a Kernel redesign;
- exact retry requires a new durable plan registry rather than contribution-ledger identity;
- confirm cannot rebuild trusted context because run artifacts are insufficient after prepare;
- a need for assertion_ids subset selection or UI disposition controls;
- a temptation to accept worldbuilding plans on recap `/confirm`;
- a response-/client-carried plan verified only by selected-field checks rather than authority rebuild;
- a required path outside §4;
- new Kernel-boundary violations introduced by application imports.

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
