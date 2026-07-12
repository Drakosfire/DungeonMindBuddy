# HANDOFF — PR007A World Graph read snapshot

**Slice:** PR007A — revision-pinned World Graph read snapshot
**Branch:** `campaign-supergraph/pr007a-world-graph-read-snapshot`
**IMPLEMENTATION_BASE:** `96bc45ad7e09952b6de8b7ada9c4fd3c36e8246a`
**Tracker:** [`PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md)
**Roadmap:** [`ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)

---

## 0 — Mission

Deliver the first production **read-only** World Graph projection API: revision-pinned,
campaign-scoped, GM-admissible snapshot over the PR006D2-published Eldyrwild graph.
Unblocks Plan dogfood (PR008) without `/ingest` UI (PR006D3 deferred).

---

## 1 — Non-goals

- `apps/live-control-ui/**` (no Plan wiring, no preview selectors)
- World graph bootstrap models/routes/services changes
- `contribution_merge` / `world_initialization` changes
- Approved contribution bundle contents
- LLM calls, preview selectors, ingest UI

---

## 2 — Allowlist (touch ONLY these)

```
Docs/Plans/HANDOFF-pr007a-world-graph-read-snapshot.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
src/graph_memory/projection/world_projection.py
src/graph_memory/projection/__init__.py
src/graph_memory/kernel/world_projection.py
src/graph_memory/kernel/__init__.py
src/graph_memory/kernel/contracts.py
apps/live_control_server/services/world_graph_projection.py
apps/live_control_server/routes/world_graph_projection.py
apps/live_control_server/main.py
tests/test_graph_kernel_world_projection.py
tests/test_world_graph_projection_service.py
tests/test_world_graph_projection_routes.py
tests/test_graph_kernel_public_api.py
tests/test_graph_kernel_boundaries.py
```

---

## 3 — API contract

### Request `dmb_world_graph_projection_request_v1`

- `worldId`, `campaignId`, `focus`, `admissibility`, optional `revisionPin`, optional `queryText`
- `focus.kind` ∈ `{none, session}`; `sessionId` required iff `session`
- `admissibility` v0: `"gm"` only
- **No query params** on the route

### Response `dmb_world_graph_projection_v1`

- Snapshot metadata: `worldId`, `campaignId`, `revisionId`, `headRevisionId`, `isHead`, `focus`, `admissibility`
- Summary counts + `projectionTruncated`
- Nodes (from `build_node_view`), relationships, attributes (revision-bound reconstruction)
- Evidence + source artifact metadata (`locatorStatus: unverified`)
- `trustBoundary`, `diagnostics`, optional `queryContext`

### Error `dmb_world_graph_projection_error_v1`

Codes: `invalid_request`, `world_graph_unavailable`, `revision_not_found`,
`campaign_scope_mismatch`, `unsupported_admissibility`, `projection_integrity_error`,
`projection_internal_error`

---

## 4 — Kernel opening rules

- No pin → `open_current_world_graph`
- Pin → `open_world_graph_head` + `load_world_graph_revision` + manifest via Kernel-internal `load_world_graph_revision_manifest`
- Campaign must match `store.campaign_id` → else `campaign_scope_mismatch`
- Admissibility validated before content (`unsupported_admissibility` if not `gm`)
- Missing world/head → `world_graph_unavailable`; missing pin → `revision_not_found`

---

## 5 — Assertion reconstruction (§8.4 CRITICAL)

For each `DurableAssertionSupport` with `assertion_kind == attribute` in the selected revision:

1. Use **only** `support.active_contribution_ids` from that revision
2. `load_contribution_record(root, world_id, cid)` (Kernel-internal `contribution_store`)
3. Find matching `assertion_id` in `contribution.accepted_assertions`
4. Fail whole projection with `projection_integrity_error` on:
   - missing contribution
   - missing assertion
   - `graph_object_id` mismatch
   - unresolved evidence/source refs referenced by support
5. **Do not** use contribution index active set as historical authority

---

## 6 — Nodes & relationships

- Nodes: `build_node_view` / `build_focus_overlay` / identity context from `recap_projection`; projectable nodes only
- Session focus: pass `session_id` into node view when `focus.kind == session`
- Relationships: projectable edges; visibility/campaignScope/epistemicKind from `edge.state` if present

---

## 7 — Search (§9)

Deterministic casefolded lexical match across node id/label/aliases/kind/role/summary +
attribute predicate/label/text. Caps: nodes 12, relationships 24, attributes 32,
evidence 32, source artifacts 24. `matchedNodeIds` + same snapshot `revisionId`.

Acceptance query: `"positional controller"` → `threat:tripod-null-calf`.

---

## 8 — Trust boundary

`cannotTrust` must include: no locator verification, no source text reads,
single-campaign v0 limitation.

`canTrust`: revision pin identity, selected revision payload, revision-bound support+contribution reconstruction.

---

## 9 — App boundary

- Service binds `world_graph_root()`; calls Kernel only
- **Never** imports `world_supergraph.*`
- Route: `POST /api/live/world-graph/projection`
- Register in `main.py`

---

## 10 — Tests (required proofs)

Reuse approved-bundle init helpers from `test_graph_kernel_world_initialization.py`.

- Head vs pin vs invalid pin
- Tripod `threat:tripod-null-calf` + `battlefield_role` + `challenge_expectation`
- Relationship to `event:longmont-c2:session-23:mireward-gate-battle`
- Search `"positional controller"` → tripod, same `revisionId`
- Unsupported admissibility fails closed
- Campaign mismatch fails
- Integrity failure when contribution file removed after init
- Service uses configured root / kernel boundary
- Routes: camelCase, no query params, forbidden fields, real graph after init
- `test_graph_kernel_public_api.py`: projection APIs exported (not reserved)

---

## 11 — Verification

```bash
cd /tmp/dmb-pr007a
export IMPLEMENTATION_BASE="96bc45ad7e09952b6de8b7ada9c4fd3c36e8246a"
git merge-base --is-ancestor "${IMPLEMENTATION_BASE}" HEAD

uv run pytest -q \
  tests/test_graph_kernel_world_projection.py \
  tests/test_world_graph_projection_service.py \
  tests/test_world_graph_projection_routes.py

uv run pytest -q \
  tests/test_graph_kernel_public_api.py \
  tests/test_graph_kernel_boundaries.py \
  tests/test_graph_kernel_world_initialization.py \
  tests/test_world_graph_bootstrap_service.py \
  tests/test_world_graph_bootstrap_routes.py \
  tests/test_activate_eldyrwild_world_bootstrap_cli.py

uv run pytest -q \
  tests/test_graph_authoring_overlay_projection.py \
  tests/test_graph_authoring_overlay_projection_merge.py

uv run ruff check <allowlist paths>
```

### §14.5 smoke

Activate Eldyrwild into `mktemp` root, project with `queryText: positional controller`,
confirm tripod match and stable `revisionId`.

---

## 12 — Tracker updates (post-merge)

- PR006D2 → DONE (#337, `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`)
- PR006D3A/D3B → DEFERRED (not dogfood blocker)
- PR007A → DONE after merge
- PR008 blocked on PR007A only

---

## 13 — Commit message

```
feat(graph-memory): add revision-pinned World Graph read snapshot
```

Do not push from implementation agent; parent reviews then opens PR.
