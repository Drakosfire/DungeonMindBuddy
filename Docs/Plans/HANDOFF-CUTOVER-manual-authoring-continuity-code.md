---
pr_body_template: |

  ## Handoff pointer

  * Workstream: CUTOVER / D.2C4 — manual Graph Review authoring continuity
  * Flow: CUTOVER
  * Direction: CODE → REVIEW
  * Branch: `cutover/manual-authoring-continuity`
  * PR title: `CUTOVER: preserve Graph Review authoring on DungeonMind`
  * Handoff: `Docs/Plans/HANDOFF-CUTOVER-manual-authoring-continuity-code.md`
  * Frozen design authority: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §5
  * Exact dispatch base: `84f3401b23fcac32a57416d5419dc7d33cf6eabc`

  ## Completed predecessor

  * D.2C3 / PR #651: COMPLETE / MERGED
  * Accepted head: `9508b71655665005df8f12da74c239fe7eb17c0c`
  * Merge SHA: `84f3401b23fcac32a57416d5419dc7d33cf6eabc`
  * Formal review cycles: 4
  * DungeonMind pin: `5ca5d688612349034f8ca490d465af166d883e6e`

  ## Mission

  Preserve the existing GM-facing Graph Review correction workflow while replacing
  Buddy overlay / UnionSupergraph durable mutation with governed DungeonMind
  publication. Expressible reviewed edits publish exactly one DungeonMind child
  revision; unsupported merge semantics fail closed with zero durable graph side
  effect.

  ## Verification pointer

  See §7. The owning proof must exercise real Graph Review prepare → confirm against
  PostgreSQL, prove object / link_existing / relationship publication, prove
  merge_objects is inexpressible, prove retry/recovery, and prove the legacy Buddy
  graph writer is not invoked.

  The checked-in handoff, cumulative diff, nano-commit story, and exact verification
  output are the review contract. The PR body is transport metadata.
---

# HANDOFF — CUTOVER D.2C4: preserve Graph Review authoring on DungeonMind

**Created:** 2026-08-28
**Status:** CODE → REVIEW — Review Cycle 1 submitted (PR #662)
**Canonical handoff:** `Docs/Plans/HANDOFF-CUTOVER-manual-authoring-continuity-code.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Flow / owner:** CUTOVER
**Direction:** CODE → REVIEW
**Branch:** `cutover/manual-authoring-continuity`
**PR title:** `CUTOVER: preserve Graph Review authoring on DungeonMind`
**Exact dispatch base:** `84f3401b23fcac32a57416d5419dc7d33cf6eabc`
**Named successor:** D.3A — mounted Buddy graph-engine excision

> D.2C4 is the last replacement-capability slice before demolition.
>
> The existing Graph Review UX remains an intentional DungeonBuddy product surface.
> What changes is the durable destination beneath its prepare / confirm workflow.
>
> After this slice, a GM-confirmed Graph Review edit is either:
>
> 1. a governed DungeonMind publication with exact revision identity, or
> 2. an explicit fail-closed result.
>
> It is never an authoritative Buddy overlay, an authoritative
> `UnionSupergraphStore` append, or a hidden fallback to the legacy graph engine.

---

## §8.3 CODE → REVIEW handback

This is the review contract for Review Cycle 1.

### 1. PR / branch / Review Cycle 1 head

* Branch: `cutover/manual-authoring-continuity`
* PR number: **#662** — https://github.com/Drakosfire/DungeonMindBuddy/pull/662
* Review Cycle 1 head SHA: `4945b426abb7732617870f1ce29fb1fd28035923`

### 2. Exact dispatch base

`84f3401b23fcac32a57416d5419dc7d33cf6eabc`

### 3. #651 predecessor

* Accepted head: `9508b71655665005df8f12da74c239fe7eb17c0c`
* Merge SHA: `84f3401b23fcac32a57416d5419dc7d33cf6eabc`
* Formal review cycles: **4**

### 4. Current DungeonMind pin

`5ca5d688612349034f8ca490d465af166d883e6e`

### 5. Open-PR collision check

AGENT-INTERACTION #659 is disjoint except regression-only overlap on
`tests/test_live_query_hermes_graph.py`. No overlapping §4 production-path lease was
taken by this implementation.

### 6. Cumulative changed-path list (working tree vs dispatch base)

```text
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
Docs/Plans/HANDOFF-CUTOVER-manual-authoring-continuity-code.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.test.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/services/graph_object_authoring_prepare.py
tests/test_cutover_graph_review_authoring_continuity.py
tests/test_graph_object_authoring_commit.py
tests/test_graph_object_authoring_prepare.py
tests/test_graph_object_authoring_routes.py
```

`apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCorrectionModal.tsx`
was not required.

### 7. Bounded exceptions used

* `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py`
  — added `graph_review_authority_operation_id(...)` returning `grauth:{sha256}`
  from frozen schema `dmb_graph_review_authoring_authority_operation_v1`.
  No new DungeonMind provider contract.

### 8. Nano-commit list and purpose

1. `f69959e0` CUTOVER: hand off Graph Review DungeonMind authoring
2. `e140591d` CUTOVER: bind Graph Review prepare to governed publication intent
3. `9458a46a` CUTOVER: publish confirmed Graph Review edits through DungeonMind
4. `93a318db` CUTOVER: align Graph Review API and UI to DungeonMind publication
5. `4945b426` CUTOVER: prove manual-authoring continuity and legacy-writer absence

### 9. State-authority sync result

Backward-looking status records:

```text
D.2C3 native genesis continuity
  COMPLETE / MERGED
  PR #651
  accepted head 9508b716...
  merge 84f3401b...
  formal review cycles 4

D.2C4 manual Graph Review authoring continuity
  DOING / this PR

D.3A
  BLOCKED

D.3B
  BLOCKED

D.3
  NOT DONE
```

Tracker and roadmap mirrors are byte-identical after this implementation.

### 10. Exact operation classification implemented

| Graph Review operation | Classification | DungeonMind meaning |
| --- | --- | --- |
| `object` | EXPRESSIBLE | `NodeContribution` (`assertion_kind="node"`, `created_new`) |
| `link_existing` | EXPRESSIBLE | `AliasContribution` (`assertion_kind="alias"`, `resolved_existing`) |
| `relationship` | EXPRESSIBLE | `EdgeContribution` (`assertion_kind="edge"`) |
| `merge_objects` | INEXPRESSIBLE | prepare explains; confirm returns `governed_write_inexpressible` |
| unknown action | INEXPRESSIBLE / invalid | Pydantic/prepare fail closed; no publication path |

No operation remains `AMBIGUOUS`.

### 11. Exact source-resolution behavior

Order:

1. explicit injected `resolved_source` (tests) or request `sourceRunId`
2. `resolve_promotable_ingest_run(run_id)`
3. campaign/world mismatch → `source_inadmissible`
4. `WorldGraphSourceAdmissionAuthority` / `admit_source` / SourceRepository snapshot
5. unresolved → `source_unresolved` before any durable write

Historical `sourceRunId` is not itself durable provenance authority. The prepared
artifact binds admitted `source_artifact_id` + `source_revision_id`.

### 12. Prepare side-effect proof

`test_prepare_writes_nothing` and owning PostgreSQL prepare steps prove:

* no overlay
* no event log
* no backup
* DungeonMind head not advanced

### 13. Prepared binding fields

HMAC-signed `v1.{body}.{digest}` token binds:

```text
schema
world_id
campaign_id
campaign_rel
source_run_id
source_artifact_id
source_revision_id
expected_parent_revision_id
authority_operation_id
expressibility
actor
assertions_digest
contribution_digest
expires_at
```

`contribution_digest` excludes `produced_at`. Translate uses
`STABLE_ASSERTION_TIMESTAMP` so retry does not treat wall-clock metadata as a
different reviewed contribution.

### 14. Actor derivation

`graph-review:{campaign_id}`

### 15. Expected-parent derivation

`WorldGraphAuthority.current_head(world_id).revision_id` at prepare time.
Confirm uses that exact revision as expected parent. No silent rebase.

### 16. Object publication result

Owning PostgreSQL witness
`test_graph_review_authoring_continuity_one_world_sequence`:

* parent: reviewed-init `D_0`
* child: exactly one `D_1`
* contribution type: node / `created_new`
* native `read_revision(D_1)` contains the authored node

### 17. Link_existing publication result

* parent `D_1` → child `D_2`
* alias / `resolved_existing` against existing node `obj_session22_vial`
* native read still contains that existing node; no duplicate authored node

### 18. Relationship publication result

* parent `D_2` → child `D_3`
* edge `associated_with` from authored node to `obj_session22_vial`
* native read sees the edge

### 19. merge_objects result + zero-side-effect proof

Prepare returns `expressibility="INEXPRESSIBLE"`. Forced confirm returns
`409 governed_write_inexpressible`. Revision count remains 4 (`D_0`–`D_3`).
Head remains `D_3`. Tripwired overlay/UnionSupergraph writers are not invoked.

### 20. Unknown-action result + zero-side-effect proof

Unknown `proposalKind` is rejected at prepare (`422`). Head remains `D_3`.
Revision count unchanged.

### 21. Stale-parent result

`test_graph_review_stale_parent_fails_closed`: prepare at `D_0`, intervening
publication creates `D_1`, stale confirm returns `stale_parent`, revision count
stays 2, head is the intervening child.

### 22. Confirmation tamper result

`test_commit_tampered_proposals_fail` → `confirmation_invalid`; `publish_calls == 0`.

### 23. Confirmation expiry result

`test_commit_expired_token_fails` → `confirmation_expired`; `publish_calls == 0`.

### 24. Source-unresolved result

`test_prepare_object_without_source_run_fails` and owning missing-`sourceRunId`
path → `source_unresolved` / `409|422`. No durable write.

### 25. source_artifact_not_found result

`test_prepare_missing_source_artifact_fails_closed` → `source_artifact_not_found`.

### 26. source_inadmissible result

* unit: `test_commit_source_inadmissible_fails` (wrong campaign)
* unit: `test_prepare_wrong_world_source_fails_closed` (wrong world)

### 27. Exact retry result

Owning witness: retry of object confirm returns same `D_1`,
`idempotency_status="already_applied"`, revision count still 2.

Unit: `test_commit_exact_retry_recovers_same_child`.

### 28. Provider-commit/client-response-loss recovery result

Unit: `test_commit_recovers_lost_provider_response` recovers `rev:d1` /
`already_applied` without a second publish.

### 29. Final revision topology from owning PostgreSQL witness

```text
D_0 → D_1 → D_2 → D_3
no D_4
one head
```

### 30. Native read/retrieval proof after publications

`DungeonMindWorldGraphAuthorityAdapter.read_revision` after each expressible
publication observes the authored object, existing node, and relationship.

### 31. Legacy writer tripwire result

Owning tests patch:

* `GraphAuthoringOverlayStore.append_assertions`
* `GraphAuthoringOverlayStore.save_overlay`
* `write_union_supergraph_store`
* `apply_union_supergraph_merge_plan_to_file`

and raise immediately if invoked. Sequence passed with tripwires armed.

### 32. Proof Graph Review confirm does not call legacy graph-patch/entity-merge

Confirm path is `commit_graph_object_authoring_write` →
`WorldGraphAuthority.recover` / `publish` only. Legacy
`POST /worlds/{world_id}/graph/patch` and `/entities/merge` are not called.
Kernel explode from D.2C3 `_explode_kernel` remains armed during the owning sequence.

### 33. `mergeIntoUnion` compatibility treatment

* omitted / true: governed DungeonMind publication
* explicit `false`: `governed_write_inexpressible`
* frontend no longer presents “merge into union” as an authority choice
* `test_commit_legacy_merge_into_union_false_fails_closed` covers the server branch

### 34. Frontend UX/copy outcome

* prepare remains preview-only
* confirmation token returned unchanged
* parent/published DungeonMind revisions displayed
* old “Merged directly into the union graph” wording removed
* no authority-destination toggle
* stale_parent, inexpressible merge, and source failure are distinguishable
* recovered publication is not shown as a second write

### 35. Every §7 test command and exact totals

Provenance for all automated results below: **author-local**.

#### 7.2 Owning server cohort

```text
uv run pytest \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_object_authoring_commit.py \
  tests/test_graph_object_authoring_routes.py \
  tests/test_cutover_graph_review_authoring_continuity.py \
  -q
```

`45 passed, 10 warnings`

Owning PostgreSQL witness: **0 skips**.

`tests/test_graph_object_authoring_routes.py` did not exist on the dispatch base.
It was added in this slice as the exact prescribed route-boundary path.

#### 7.3 Legacy/public regression cohort

```text
uv run pytest \
  tests/test_live_query_hermes_graph.py \
  tests/test_cutover_worldbuilding_authority_port_integration.py \
  tests/test_cutover_native_genesis_continuity.py \
  -q
```

`64 passed, 10 warnings`

Prescribed `tests/test_graph_native_authoring.py` **does not exist** on the dispatch
base or this branch. D.2C3 native genesis continuity is the existing substitute
(`tests/test_cutover_native_genesis_continuity.py`). This is recorded, not waived.

#### 7.4 Frontend Graph Review cohort

```text
npm test -- --run \
  src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.test.tsx \
  src/api/liveApi.test.ts
```

`85 passed` (2 files)

`npm run typecheck` — pass
`npm run build` — pass

### 36. Ruff result

```text
uv run ruff check \
  apps/live_control_server/routes/graph_authoring.py \
  apps/live_control_server/services/graph_object_authoring_prepare.py \
  apps/live_control_server/services/graph_object_authoring_commit.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_writes.py \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_object_authoring_commit.py \
  tests/test_graph_object_authoring_routes.py \
  tests/test_cutover_graph_review_authoring_continuity.py
```

All checks passed.

### 37. Frontend typecheck result

Pass.

### 38. Frontend build result

Pass.

### 39. `git diff --check`

Pass.

### 40. Dependency immutability result

```text
git diff --exit-code \
  84f3401b23fcac32a57416d5419dc7d33cf6eabc...HEAD \
  -- pyproject.toml uv.lock
```

PASS / no diff. DungeonMind pin unchanged.

### 41. Tracker/roadmap mirror results

```text
cmp Docs/Plans/PR-TRACKER-campaign-supergraph.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
cmp Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
    Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
```

Both identical.

### 42. Verification provenance

| Evidence family | Provenance |
| --- | --- |
| Owning server / PostgreSQL witness | author-local |
| Legacy/public regression | author-local |
| Frontend tests / typecheck / build | author-local |
| Ruff / diff / mirrors / lockfiles | author-local |
| CI | none |
| Manual dogfood | BLOCKED_DEPENDENCY |

### 43. Manual dogfood result

`BLOCKED_DEPENDENCY`

Local UI reached Graph Review / Ingest, but no reviewable projection / ingest run
was available (`World · Unavailable`; Load recap disabled). Automated publication
proof is not waived.

### 44. Baseline failures/comparisons

None on the required available cohorts. The missing
`tests/test_graph_native_authoring.py` path is a base absence, not a head
regression.

### 45. Explicit operator waivers

none

### 46. Paths outside §4

none, other than the bounded exception in §7.

### 47. Stop conditions encountered

none

### 48. D.3A / D.3B remain unimplemented

Confirmed. This slice does not delete `graph_native_authoring.py`,
`union_supergraph`, `graph_memory.kernel`, prewarm, bootstrap, or change
authority-selector defaults.

---

## Remaining merge-ready work (not code)

1. Formal Review Cycle 1 on PR #662.
2. Do not mark D.2C4 `DONE` before merge.
