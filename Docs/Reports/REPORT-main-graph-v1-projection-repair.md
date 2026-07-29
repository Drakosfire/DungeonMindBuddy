# Main Graph V1 Projection Repair Report

**Created:** 2026-07-28  
**Lane:** Primary-tree Graph V1 product continuity  
**Branch:** `fix/graph-v1-projection-blocking-edge`  
**Repo base SHA:** `0f6f48ed6502a9a4e69b57f351ae9c795da54694` (`origin/main`)  
**Governing handoff:** `Docs/Plans/HANDOFF-main-graph-v1-projection-recovery-dogfood.md`  
**Prior forensics:** `Docs/Reports/REPORT-active-edge-semantic-disagreement-investigation.md`

---

## Executive result

The projection-blocking active assertion state on `edge:pc:baergrom:serves:pc:caelynn` was corrected through the governed Graph V1 write path (`kernel.supersede_graph_contribution`), then proven by full `rebuild_from_contributions(publish=True)`.

The named product projection path now consumes the validated replacement revision:

```text
rev:a3262c8102f61f490e11444d9fc28068
```

Strict projection disagreement validation remains intact (unit tests still pass). First-wins tolerance from open PR `#444` was **not** used.

This report does **not** claim the entire Eldyrwild graph is semantically clean. It claims only that the projection-blocking Baergrom→Caelynn active-support disagreement was removed truthfully under V1 contracts, and that the previously failing projection request now succeeds.

---

## Repository and runtime baseline

| Item | Value |
| --- | --- |
| Branch before work | `main` @ `817427bd` (behind `origin/main`) |
| Implementation base | `origin/main` @ `0f6f48ed6502a9a4e69b57f351ae9c795da54694` |
| Repair branch | `fix/graph-v1-projection-blocking-edge` (tracks `origin/main`) |
| Unrelated local files preserved (not staged) | `evals/c2_live_prep/live/session_22/current_state.json` (modified); `Docs/Runbooks/SCRIPT-R0-A-statblock-live-dependency-proof.md` (untracked); `Docs/Reports/REPORT-active-edge-semantic-disagreement-investigation.md` (untracked) |
| Worktrees | Multiple sibling worktrees present; no temporal-worktree writes into primary `out/graph_memory/worlds/eldyrwild/` |
| PR `#444` | OPEN, CONFLICTING; body includes first-wins edge-map tolerance — **not merged, not copied** |
| Graph head at start | `rev:5017a20164555f11d4508f67661058f1` |
| World | `eldyrwild` |
| Node/edge counts at start | 432 / 344 |

---

## Reproduced failure

**Kernel (authoritative):**

```text
WorldGraphProjectionError
Active edge assertions disagree on semantic fields.
graph_object_id='edge:pc:baergrom:serves:pc:caelynn'
active_assertion_ids=['assertion:134135a4f3a2487b', 'assertion:b6ec355852102812']
```

Request:

```json
{
  "schema": "dmb_world_graph_projection_request_v1",
  "world_id": "eldyrwild",
  "campaign_id": "longmont-c2",
  "scope_mode": "campaign",
  "focus": {"kind": "none", "session_id": null},
  "admissibility": "gm"
}
```

**Correction to the “nine label-differing edges” claim:** forensics showed **nine multi-active edges**, but only **one** fingerprint disagreement under `_edge_core_semantic_fingerprint`. That one edge was the sole `409` cause. See investigation report §8.1.

---

## Blocking edge and assertion inventory

| Field | Assertion A | Assertion B |
| --- | --- | --- |
| Assertion ID | `assertion:134135a4f3a2487b` | `assertion:b6ec355852102812` |
| Contribution | `contribution:2807888820d76c78` | `contribution:9080eb4963640ec5` |
| Contribution status (pre-repair) | active | active (supersedes `contribution:dba1d85c7eeae8b5`) |
| Source kind | `source_extraction` | `source_extraction` |
| Source artifact | `artifact:recap:longmont-c1:session-10` | `artifact:recap:longmont-c1:session-12:7184000a8cfb` |
| Session | session-10 | session-12 |
| Subject / object | `pc:baergrom` / `pc:caelynn` | same |
| Predicate | `serves` | `serves` |
| Label | `serves` | `revives` |
| Direction | outbound | outbound |
| Durable edge ID | `edge:pc:baergrom:serves:pc:caelynn` | same |
| Evidence | `…session-10…paragraph:009` | `…session-12…span:7184000a8cfb:29-29` |

---

## Source-evidence analysis

### Assertion A (session-10)

Literal support (run span `recap_paragraph_009.md`):

> … Caelynn is knocked unconscious … **Bargrom uses a health potion on Caelynn** …

| Question | Answer |
| --- | --- |
| Subject correct? | Yes (Baergrom / Bargrom spelling variant in prose) |
| Object correct? | Yes (Caelynn) |
| Predicate `serves` supported? | **No** — prose describes a heal action, not a durable serve relationship |
| Label consistent with predicate? | Yes (`serves`/`serves`), but both unsupported by prose |
| Event vs relationship? | **Event-like** combat heal |
| Classification | **Malformed** durable-edge packaging of an event |

### Assertion B (session-12)

Literal support (`recap_paragraph_007.md`):

> **Baergrom revives Caelynn with a potion** then hits and kills another guard …

| Question | Answer |
| --- | --- |
| Subject/object correct? | Yes |
| Predicate `serves` supported? | **No** |
| Label `revives` supported? | **Yes** as event wording |
| Label vs predicate? | **Inconsistent** (`revives` ≠ `serves`) while edge identity follows predicate |
| Event vs relationship? | **Event-like** combat revive |
| Classification | **Malformed** durable `serves` edge; free-text label closer to truth than predicate |

### Decision basis

Source chronology was **not** used as a tie-breaker. Both active packages fail as durable `serves` relationships. V1 has no event-occurrence identity in this lane. Truthful V1 active state: **neither** assertion remains active support for that edge.

---

## Repair decision

**Preferred path used: A / B hybrid — supersede each parent contribution with a corrective contribution that rejects the unsupported edge assertion and retains all other accepted assertions.**

Not used:

- Full contribution retract (would discard many unrelated accepted assertions — 55–56 each)
- In-place `graph.json` edit
- First-wins / projection tolerance
- Temporal/event modeling
- New edge identity

---

## Governed operation performed

For each parent:

1. `create_graph_contribution(...)` with:
   - same source artifact/revision/profile/campaign scope
   - `authored_by='operator:graph-v1-projection-repair'`
   - `supersedes_contribution_id=<parent>`
   - `selection_digest=f'reject:{bad_assertion_id}'`
   - accepted set = parent accepted minus bad assertion
   - rejected set = parent rejected + bad assertion (`acceptance_state='rejected'`)
   - diagnostics include repair reason
2. `kernel.supersede_graph_contribution(..., expected_parent_revision_id=<current head>)`

| Parent | Bad assertion removed | Correction contribution |
| --- | --- | --- |
| `contribution:2807888820d76c78` | `assertion:134135a4f3a2487b` | `contribution:d3d244474789879c` |
| `contribution:9080eb4963640ec5` | `assertion:b6ec355852102812` | `contribution:4c89cbbf15da5d10` |

Then:

3. `kernel.rebuild_from_contributions(publish=True)` to prove replay survival.

---

## Old and new immutable revisions

| Stage | Revision | Notes |
| --- | --- | --- |
| Pre-repair head | `rev:5017a20164555f11d4508f67661058f1` | Post stale-field rebuild |
| After supersede #1 | `rev:4d0636a05841efd6958014b655ccf40e` | session-10 correction |
| After supersede #2 | `rev:bbf29b974f0162dc8b8fbe080d93ae00` | session-12 correction |
| After rebuild publish | `rev:a3262c8102f61f490e11444d9fc28068` | **Current authoritative head** |

Head file after repair:

```json
{
  "head_revision_id": "rev:a3262c8102f61f490e11444d9fc28068",
  "world_id": "eldyrwild"
}
```

---

## Rebuild and replay proof

- `rebuild_from_contributions(publish=True)` → `rev:a3262c8102f61f490e11444d9fc28068`
- Diagnostics include `rebuild_published_new_head`, `rebuild_equivalent_to_published_head`, `rebuild_equivalent_to_head`
- Node/edge counts remain **432 / 344**
- Bad assertions remain `support_state=unsupported`, `active_contribution_ids=[]`
- Edge retained with `memory_state=unsupported_assertion` (history inspectable; omitted from projectable relationships)
- Parent contributions remain loadable with status `superseded` and still contain the original accepted bad assertions in historical records

**Idempotency:** re-creating the same correction yields the same contribution id `contribution:d3d244474789879c`. Re-running `supersede_graph_contribution` against the already-superseded parent does **not** publish (`published=False`, diagnostic `contribution source digest already bound with a different value`). No duplicate active correction.

---

## Projection proof

| Path | Result |
| --- | --- |
| Kernel `project_world_graph` after repair | Success; snapshot `rev:a3262c8102f61f490e11444d9fc28068`; 45 nodes / 33 relationships in campaign C2 none-focus projection |
| HTTP `POST /api/live/world-graph/projection` | `200`; same revision |
| Baergrom→Caelynn relationship in projection | **0 hits** (unsupported edge omitted) |

---

## Restart proof

1. Stopped Buddy API process on `:8000`
2. Restarted `uv run uvicorn apps.live_control_server.main:app --host 127.0.0.1 --port 8000 --reload`
3. Re-ran the same projection request → `200`, revision `rev:a3262c8102f61f490e11444d9fc28068`

---

## Surface smoke results

| Existing surface | Route / action | Observation | Unrelated defects |
| --- | --- | --- | --- |
| World graph projection API | `POST /api/live/world-graph/projection` | `200`, repaired head | none for this path |
| Plan view API | `GET /api/live/plan-view` | `200` | none observed |
| Live surface catalog | `GET /api/live/surface` | `200` | none observed |
| Live Control UI | `http://127.0.0.1:5173/` | `200` HTML shell | Manual UI traversal of Graph Review / Hermes left to resumed dogfood (API projection unblocked) |
| Statblock readiness | not required for this repair | — | DungeonMindServer may be down; out of scope |

---

## Count and integrity comparison

| Metric | Before | After supersedes | After rebuild |
| --- | ---: | ---: | ---: |
| Nodes | 432 | 432 | 432 |
| Edges | 344 | 344 | 344 |
| Bad assertion active support | yes (both) | no | no |

Unexpected count changes: **none**.

Note: pre-rebuild head `rev:bbf29…` was not byte-identical to a dry rebuild fingerprint (`rebuild_differs_from_head` with identical counts). Publishing the rebuild made the authoritative head equal to the replayed store (`rebuild_equivalent_to_head`). Active repaired semantics (unsupported bad assertions; projectable) held across both.

---

## Unresolved disagreement cohort

After repair, multi-active edges remaining: **8** (all fingerprint-**agree** under current gate). Fingerprint-disagree set: **empty**.

| Edge | Assertion labels | Source-supported classification | Blocks required dogfood path? | Proposed minimal action |
| --- | --- | --- | ---: | --- |
| `edge:pc:baergrom:member_of:node:heroes-party` | identical long label ×3 | standing/recap re-attestation (session stamps differ) | No | Leave; temporal/additive observation model owns long-term clarity |
| `edge:pc:bonogo:member_of:node:heroes-party` | identical ×3 | same | No | Leave |
| `edge:pc:caelynn:member_of:node:heroes-party` | identical ×3 | same | No | Leave |
| `edge:pc:ephanna:member_of:node:heroes-party` | identical ×3 | same | No | Leave |
| `edge:pc:karsemine:member_of:node:heroes-party` | identical ×3 | same | No | Leave |
| `edge:pc:stafl:member_of:node:heroes-party` | identical ×3 | same | No | Leave |
| `edge:pc:bonogo:attacks:node:wolf` | `attacks` ×3 | separate valid combat events collapsed to one durable edge; gate allows via session-strip | No | Defer to temporal/event lane |
| `edge:pc:bonogo:carries:item:session17:dagger` | `carries` ×2 | possible identity packaging smell (S12 assertion → session17 item id); fingerprints agree | No | Successor data-quality review if dogfood hits it |

**Related non-blocking anomaly (not multi-active):** `assertion:809518e50178f15c` on `edge:pc:karsemine:serves:pc:stafl` also has `label=revives` / `predicate=serves` from session-12. Single active support — does not 409. Same packaging pattern; deferred (would require new semantic decision or same supersede pattern if it becomes blocking).

---

## Dogfood blockers remaining

- Graph V1 projection for Plan/Ingest/Build/Graph Review/Hermes: **unblocked** for the previously failing request.
- Broader semantic cleanliness of event-like predicates: **not** claimed solved.
- Statblock provider / `R0-A`: independent of this repair; start DMS if dogfooding Workbench.
- Open PR `#444` first-wins: still open; must not be treated as product authority.

---

## Temporal or Graph V2 findings explicitly deferred

- Event occurrence identity for heal/revive/attack
- Valid-time / timeline projection
- Whether `label` should participate in durable edge identity
- Write-time edge semantic agreement (nodes already refuse; edges do not)
- General corpus predicate rejuvenation

---

## Commands and evidence provenance

| Command / observation | Provenance |
| --- | --- |
| Kernel reproduce failure | author-local |
| `supersede_graph_contribution` ×2 | author-local (operator-approved mutation) |
| `rebuild_from_contributions(publish=True)` | author-local (operator-approved mutation) |
| Kernel projection success | author-local + independently rerun after rebuild |
| HTTP projection `200` | author-local |
| API restart + re-projection | author-local |
| `pytest tests/test_edge_core_semantic_fingerprint.py` + supersede/retract filter | author-local — 10 passed |
| Idempotent supersede re-run non-publish | author-local |
| UI HTML `200` | author-local (shell only) |

---

## Unexpected paths or state changes

Repository paths intended for this repair:

- `Docs/Reports/REPORT-main-graph-v1-projection-repair.md` (this file)
- `Docs/Plans/HANDOFF-main-graph-v1-projection-recovery-dogfood.md` (status snapshot)

Runtime (normally gitignored):

- `out/graph_memory/worlds/eldyrwild/contributions/contribution__d3d244474789879c.json`
- `out/graph_memory/worlds/eldyrwild/contributions/contribution__4c89cbbf15da5d10.json`
- updated parent contribution records (status superseded)
- new revisions under `out/graph_memory/worlds/eldyrwild/revisions/`
- `out/graph_memory/worlds/eldyrwild/head.json`
- `out/graph_memory/worlds/eldyrwild/contribution_index.json`
- `out/graph_memory/worlds/eldyrwild/contribution_rebuild/latest.json`

No production Python/TS code changes. No first-wins tolerance. No temporal-worktree writes into the primary Eldyrwild store.

---

## Final disposition

```text
The projection-blocking active assertion state was corrected through the governed Graph V1 write path, and the named product projection paths now consume the validated replacement revision.
```

**Strict projection integrity:** remains enabled and tested.  
**Temporal / Graph V2:** remain unimplemented in this lane.  
**Product dogfood:** may resume on the repaired head without claiming Graph V1 semantics are generally solved.
