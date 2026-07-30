# Instructions — Reboot dogfood (`R0-A` then `R0-B`)

**Status:** ACTIVE operator pickup  
**Created:** 2026-07-28  
**Repo tip at write:** `686ccb7e` on `main`  
**Sequencing authority:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md) + [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Result template / gate rules:** [`RUNBOOK-authored-world-object-magic-moment-dogfood.md`](RUNBOOK-authored-world-object-magic-moment-dogfood.md)

This is the **start-here** brief after Graph V1 projection recovery. Do not advance `SBW06d` / `AOW*` / graph-publication slices until both reboot gates have recorded reports.

---

## 0. Current-state hypothesis (reanchor)

| Fact | Truth now |
|---|---|
| Implementation through | `SBW06c` MERGED `#439` — Workbench revise UX exists |
| Blocking work before new slices | Recorded **`R0-A`** and **`R0-B`** dogfood reports |
| Graph projection | Restored. Blocking edge `baergrom:serves:caelynn` governed-superseded. See [`../Reports/REPORT-main-graph-v1-projection-repair.md`](../Reports/REPORT-main-graph-v1-projection-repair.md) |
| Integrity gates | Still strict — do **not** treat PR `#444` first-wins as authority |
| Deeper event/label design | Parked: backlog `[READY] Event-vs-relationship and label/predicate packaging` + temporal / Graph V2 |
| Hermes “list all sessions” | **Retrieval budget**, not merge miss. Agent search caps at 12 nodes (`graph_query_truncated_nodes`). Session-1/2 **are** in the contribution index |
| Product door | Always start at `http://127.0.0.1:5173/` — never deep-link as the dogfood door |

**Concrete next action:** run **`R0-A`** end-to-end and write `Docs/Reports/MAGIC-MOMENT-R0-A-<YYYY-MM-DD>.md`. Only then run **`R0-B`**.

---

## 1. Environment (verify before touching UI)

Three processes must be up:

| Process | URL | Check |
|---|---|---|
| DungeonMindServer | `http://127.0.0.1:7860` | `curl -fsS …/statblocks/health/live` → live |
| Buddy live-control API | `http://127.0.0.1:8000` | surface 200; readiness `configured/available` true |
| Live Control UI | `http://127.0.0.1:5173` | HTTP 200 |

Suggested API session dir (matches recent C2 dogfood):

```bash
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22
```

Record into every report:

```bash
git rev-parse HEAD
git show -s --format='%h %s' HEAD
# and current Eldyrwild head
python3 -c 'import json;from pathlib import Path;print(json.loads(Path("out/graph_memory/worlds/eldyrwild/head.json").read_text())["head_revision_id"])'
```

If projection returns `409 projection_integrity_error` again, **stop dogfood** and reopen the repair path — do not soft-pass Hermes on a broken graph.

---

## 2. Gate order (do not skip)

```text
R0-A  Statblock live dependency proof   ← do this first
  ↓  report + verdict
R0-B  Unioned graph sensemaking proof
  ↓  report + verdict
Re-anchor next implementation handoff from observed friction only
```

`MAGIC-D1`…`D5` stay blocked until reboot reports exist.

---

## 3. `R0-A` — follow the operator script

**Full step-by-step:** [`SCRIPT-R0-A-statblock-live-dependency-proof.md`](SCRIPT-R0-A-statblock-live-dependency-proof.md)

Short checklist (every step must be the **Workbench** path, not Statblock View):

1. Open `http://127.0.0.1:5173/` → `/surface` → enable **Statblock Workbench**.
2. Create a **real** C2/Eldyrwild ThreatDraft (nontrivial concept).
3. **Create & generate** via real provider (readiness must be available).
4. Edit ≥1 **dedicated numeric** combat field — primary AC, HP scalar, or ability score (not rename / `rules_text`-only; typed mechanics are out of scope for R0-A).
5. **Validate working copy** — clean preview receipt.
6. **Accept/Save mechanics** — capture `(statblock_id, revision_id, digest)`. (AI revise deferred — note `DEFERRED_REVISE_UX`.)
7. Hard browser reload → reopen exact accepted identity.
8. Write `Docs/Reports/MAGIC-MOMENT-R0-A-<YYYY-MM-DD>.md` from the runbook template.

| Verdict | When |
|---|---|
| `PASS` | Hard path (no revise) + exact locator survives reload |
| `PASS_WITH_FRICTION` | Works but reopen/browse is painful (likely **AUTHORING-LIBRARY**) |
| `FAIL_PRODUCT` / `FAIL_ARCHITECTURE` | Workbench/contract wrong while provider is up |
| `BLOCKED_DEPENDENCY` | DM `:7860` / auth / provider down |

Do **not** count corpus-promotion Statblock View, mocks, or “draft exists but generate failed” as pass.

---

## 4. `R0-B` — unioned graph → editable Threat description

**Protocol authority:** runbook §5. No separate SCRIPT yet — follow this section.

### 4.1 Choose the question

Must be:

- partly forgotten / not one obvious recent file;
- needs relationships or multi-session context;
- useful for designing a Threat;
- **not** answered by naming a source path yourself.

Example shape (adapt, don’t copy blindly):

> What do we actually know about the buried or singing creatures connected to Mireward, the Shepherds, and the recovered meat-goo magic? What is established, what is inferred, and what kind of creature description follows from that?

### 4.2 How to ask (honest retrieval)

1. Start at launcher → Plan / Agent Interaction (Hermes) for campaign **`longmont-c2`** / world **`eldyrwild`**.
2. Prefer a **focused** or **specific** question over “what sessions exist?” Meta-inventory questions hit the **12-node** search cap and look like missing merges.
3. If probing early sessions, set **session focus** or ask about concrete objects (e.g. session-2 alchemy room), not “can you see session 1?”
4. Allow Hermes to open admitted sources when the graph points there. Graph IDs are navigation, not citation authority.
5. Require the answer to separate: **established / inferred / creative proposal / unknown**.

### 4.3 Pass artifacts to capture

Write `Docs/Reports/MAGIC-MOMENT-R0-B-<YYYY-MM-DD>.md` with:

- question text;
- graph `revision_id` (and whether head);
- retrieval session id if shown;
- selected / matched durable node IDs;
- admitted source anchors opened (or why none);
- acceptance / warning codes (`partial_coverage`, `graph_query_truncated_nodes`, `source_anchor_unreadable`, etc.);
- the **editable Threat description** Hermes produced (paste as the description candidate);
- gaps Hermes disclosed;
- verdict + smallest next slice if fail/friction.

Pass only when you get a grounded, editable description you would actually paste into a ThreatDraft — even though automated Hermes→ThreatDraft handoff (`AOW02` / `MAGIC-D1`) does not exist yet.

### 4.4 Known non-failures (do not mis-grade)

| Observation | Correct reading |
|---|---|
| `graph_query_truncated_nodes` | Search budget (12 nodes), not “session not merged” |
| Hermes abstains on “sessions 1 and 2?” | Truncation / ranking; contributions for S1/S2 are active |
| `partial_coverage` + `source_anchor_unreadable` | Expected today’s grounding honesty — not automatic fail |
| `graph_context_detail_not_persisted` | UI kept summary only for the turn — expected |
| Empty `selected_node_ids` on Workbench create | Known gap; R0-B records what envelope `AOW01` must carry |

---

## 5. After both reports

1. Link both report paths from the PR tracker dogfood ledger (or note them in the next handoff).
2. Re-anchor **one** next slice from friction only:

| Friction seen | Likely smallest slice |
|---|---|
| Provider/OpenAPI/fixture mismatch | Narrow contract-sync / readiness |
| Reload/reopen needs remembered IDs | `AUTHORING-LIBRARY` (list client + Workbench browse) |
| Hermes answer good but no draft handoff | `AOW01` then `AOW02` |
| Revise-from-accepted-locator needed | Re-anchor `SBW06d` |
| Event/label ontology pain mid-query | Stay on dogfood; park in temporal / Graph V2 — do not soften main integrity |

3. Do **not** auto-start `SBW08` or combat integration ahead of `MAGIC-D2` / `MAGIC-D3` sequencing.

---

## 6. Links (keep this brief short)

| Doc | Role |
|---|---|
| [`SCRIPT-R0-A-statblock-live-dependency-proof.md`](SCRIPT-R0-A-statblock-live-dependency-proof.md) | R0-A click-path |
| [`RUNBOOK-authored-world-object-magic-moment-dogfood.md`](RUNBOOK-authored-world-object-magic-moment-dogfood.md) | Gate rules + report template |
| [`../Reports/REPORT-main-graph-v1-projection-repair.md`](../Reports/REPORT-main-graph-v1-projection-repair.md) | Why Plan/Hermes graph path is usable again |
| [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md) | Product lifecycle north star |
