# A10a Dogfood Report — Graph Object Authoring User Stories

Generated: 2026-07-07  
Dogfood session: C1S2 (`longmont-c1` / `session-2`)  
Branch tested: `codex/authored-graph-gold-eval-export-foundation` (includes merged A8 + A9a)  
Commit: `280eca2dd1b2067566500b3a4e8d6b5e8c8c607f`  
UI: `http://localhost:5173/ingest?campaign=longmont-c1&session=session-2`  
API: `http://127.0.0.1:8000`

---

## Executive verdict

The Graph Object Authoring workflow is **implemented and partially usable**, but it does **not yet tell the intended GM product stories cleanly**. A cautious operator can commit authored memory safely and see some results after reload, yet the loop still reads more like a developer graph editor than a campaign memory tool.

**Headline:** Safe enough to harden; not ready to declare victory.

| Story | Verdict | Primary issue | Recommended next PR |
|---|---|---|---|
| Teach graph fact | PARTIAL | Alias enrichment does not re-project source prose (`gang` stays plain text); creating a new object vs aliasing is unclear | A10b: alias→prose projection + clearer object-vs-link copy |
| Link existing object | PARTIAL | Cross-scope picker works; committed link (`gang` → `the group`) is correct in node view but prose anchor unchanged | A10b: post-commit prose grounding feedback |
| Stage relationship | PARTIAL | Relationship commit works mechanically; dogfood relationship (`Glowkindle same_as Glowkindle`) is not useful campaign language | A10b: relationship type guidance + campaign-facing labels |
| Useful node detail | PARTIAL | Summary and adjacency chips are useful; Authored overlay block and assertion IDs dominate before game info | A10b: node detail hierarchy pass |
| Quiet evidence | PARTIAL | Evidence/Debug collapsed by default; authoring selection panel and authored overlay card still metadata-heavy | A10b: demote assertion IDs; tighten selected-source fields |
| Visibility safety | PARTIAL | `gm_private` default is good; backend filtering verified; UI merges table/player; no non-GM surface to dogfood in UI | A10b: split table vs player visibility copy; optional dev filter toggle |
| Write safety | PASS | Prepare/commit guarantees visible; overlay + event log + backups written; source markdown and ingest artifacts unchanged | No action |
| Developer export | PASS | No gold/eval UI; no export dir until explicitly flagged; fixtures untouched | Defer A9b until A10b UX hardening |
| Reload/query loop | PARTIAL | Authored overlay reloads; enriched node findable by pill; alias text not discoverable from prose search path | A10b: alias mention resolution in projection/search |

---

## Environment / branch / commit tested

| Item | Value |
|---|---|
| Git branch | `codex/authored-graph-gold-eval-export-foundation` |
| Git commit | `280eca2d` — `fix(graph-authoring): refuse export overwrite and sanitize created_at filenames` |
| Live Control UI | Vite dev server at `:5173` |
| Live Control API | Uvicorn at `:8000` |
| Campaign / session | `longmont-c1` / `session-2` (C1S2) |
| Graph ingest run | `out/graph_memory/runs/longmont-c1/session-2/20260706T023949Z/` |
| Run id | `graph-ingest:longmont-c1:session-2:20260706T024026Z` |
| Source recap | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md` |
| Authored overlay | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_graph_authoring/overlays/authored_graph_overlay.json` |
| Event log | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_graph_authoring/events/graph_authoring_events.jsonl` |
| Backups | 4 timestamped overlay backups under `_graph_authoring/backups/` |

Automated checks run during this pass:

```bash
uv run pytest tests/test_graph_authoring_visibility.py \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_authoring_overlay_projection.py -q
# 70 passed
```

---

## Dogfood material used

**Primary:** C1S2 — *Session 2 - Finishing the Job* with live graph ingest (23 nodes, 19 edges, 48 evidence refs). This session was chosen because:

1. It has a real ingested graph run on disk (`preview_union_store_ready`).
2. It contains an obvious under-linked phrase: **“the gang”** (opening line) while the extracted graph already has **`the group`** as a party/group node.
3. Prior authoring commits already exist on this session from A7/A8 development, providing reload evidence.

**Not used:** C2S23 Mireward (fallback was unnecessary). Synthetic fixtures were not used.

**Canonical design example mismatch:** Design doc §9 uses “gang → Questionable Company.” C1S2 corpus uses **`the group`**, not Questionable Company (a C2 party name). Dogfood therefore tested **alias/link-existing to `the group`**, which is the honest corpus-grounded variant of the story.

---

## Story 1 — Teach the graph a missed campaign fact

**Verdict: PARTIAL**

### What I tried

1. Loaded C1S2 graph review with live ingest projection.
2. Used prior committed work: selected prose anchor **“gang”**, staged **link-existing** to **`the group`**, prepared, committed, reloaded.
3. Inspected whether the graph now “knows” the missed fact in normal review.

### What happened

- Commit succeeded; event log records `Link existing: gang → the group`.
- After reload, **`the group`** node shows aliases **`the group, gang`** and source anchor **`gang`** in the node detail dialog.
- Opening line prose still renders **`The gang survived`** as plain text — **not** a pill.
- Overlay summary banner reads: `Authored overlay loaded: 2 assertions · 1 object · 1 relationship` even though one assertion is **link-existing**, not a new object (misleading count).

### Evidence

- Overlay assertion `assert-e29968bcf24df5b7`: `link_existing`, `selected_text: "gang"`, target `group_the_group`.
- Projection API node view: `aliases: ['the group', 'gang']`, `authored: True` on `group_the_group`.
- Browser snapshot: first paragraph still shows unlinked **“gang”**; **`the group`** appears as pill later in recap.
- Event log line: `"summary": "Link existing: gang → the group"`.

### Friction

- **Object draft vs link-existing** tabs exist, but the product story “teach the graph a missed fact” maps awkwardly to link-existing aliasing when an approximate node already exists.
- No post-commit visual confirmation in the source sentence itself.
- Authored overlay summary mislabels link-existing as “object.”

### Bugs

- **UX miscount:** `GraphAuthoredOverlaySummary` labels `projected_node_count` as “object” even when the enrichment came from link-existing alias merge (`GraphAuthoredOverlaySummary.tsx`).

### Product read

Mechanically committed and reloadable, but **does not feel like teaching campaign memory from prose**. It feels like editing graph metadata attached to an existing node. The GM must infer success by opening the node card, not by reading the recap.

### Recommended next action

- **Needs dedicated PR (A10b):** alias→prose mention projection or explicit “this alias now grounds this text span” feedback.
- **Tiny fix:** overlay summary copy should distinguish link-existing from new object assertions.

---

## Story 2 — Connect authored knowledge to existing campaign objects

**Verdict: PARTIAL**

### What I tried

1. Selected **“gang”** in recap prose (prior pass).
2. Switched to **Link existing** tab.
3. Used cross-scope object picker to choose **`the group`** (`group_the_group`).
4. Committed and reloaded.

Also inspected existing-object resolver UI by clicking **`the group`** pill (search phrase pre-filled, cross-scope copy visible).

### What happened

- Link-existing commit persisted correctly without creating a duplicate group node.
- Node detail shows alias enrichment; no identity-merge language observed.
- Cross-scope resolver panel copy is honest: *“Suggestions are read-only… No link or merge has been written.”*
- Picker groups candidates by scope labels (current recap / authored / campaign / worldbuilding — per component design).

### Evidence

- Overlay `existing_object_ref.node_id: group_the_group`, `label: the group`.
- Browser dialog copy: *“Search across current recap, authored memory, party / PC data, worldbuilding, campaign memory, and GM-private graph sources.”*
- No “merge,” “canon,” or “identity resolved” strings in visible UI.

### Friction

- **Duplicate Glowkindle nodes** (character + faction) remain in graph; relationship dogfood used `same_as` between them — confusing adjacent to link-existing story.
- Candidate rows can be dense (`label · kind · aliases · reason`); scope labels help but require parsing.
- Link-existing success is invisible in the prose where the GM started.

### Bugs

None blocking. Product confusion between **alias link** and **same_as relationship** is a design gap, not a crash.

### Product read

**Connect-without-duplicating works** at the data layer. The UI does not accidentally imply permanent identity merge. Scope labels are present but the overall flow still requires graph-literacy.

### Recommended next action

- **Needs dedicated PR (A10b):** clearer link-existing success state tied to source selection.
- **Needs product/design decision:** when to recommend alias link vs new object vs relationship for phrases like “the gang.”

---

## Story 3 — Stage a relationship that is useful at the table

**Verdict: PARTIAL**

### What I tried

1. Staged and committed relationship **`Glowkindle same_as Glowkindle`** between `character_glowkindle` and `faction_glowkindle` (prior development pass on this session).
2. Reloaded graph review; inspected relationship from node detail adjacency chips.

### What happened

- Relationship assertion committed (`assert-bb58605931aa0b97`).
- Event log: `"Relationship: Glowkindle same_as Glowkindle"`.
- Node detail shows multiple adjacency chips (negotiated with Glowkindle, stash gear, decision points) — **extracted edges are more table-useful than the authored `same_as` edge**.

### Evidence

- Overlay: `relationship_type: same_as`, `direction: undirected`, both refs `character_glowkindle` / `faction_glowkindle`.
- `GraphObjectAuthoringRelationshipForm` exposes preset types + custom entry; lede says *“Stage a relationship between two objects… Nothing is written until a later authoring step.”*
- Clicking **`the group`** shows relationship chips like `the group negotiated with Glowkindle` — useful campaign language.

### Friction

- **`same_as` between two labels both named “Glowkindle”** reads as implementation noise, not “Bonogo member_of Questionable Company”-class campaign knowledge.
- Relationship form is usable but **does not steer toward campaign-facing predicates** (`member_of`, `protects`, `commands`, etc.) in the dogfood path taken.
- Direction/source/target understandable in form; less obvious in committed summary string.

### Bugs

None crashed. The dogfood relationship is a **product unforced error** (possible in UI) rather than a strict bug.

### Product read

Relationship authoring is **implemented but not yet storytelling**. A GM can create edges; the tool does not yet reliably produce **situation-aware** relationships.

### Recommended next action

- **Needs dedicated PR (A10b):** campaign-facing relationship presets + examples in form helper text.
- **Needs product/design decision:** guardrails or warnings on low-value predicates like `same_as` between same-label cross-kind nodes.

---

## Story 4 — Useful node detail beats metadata

**Verdict: PARTIAL**

### What I tried

1. Clicked **`the group`** pill in C1S2 live projection.
2. Reviewed node game card ordering and content.
3. Checked for statblock / encounter / gameplay enrichment paths.

### What happened

Dialog opens with:

1. Lane kicker (`Live Run · read-only`)
2. Label + kind (`group / group`)
3. **Authored overlay** block: Label, Aliases, Visibility, Source anchor, **Assertion ID**
4. **Then** useful summary: *“The adventuring collective that cleared the tower basement…”*
5. Review status section (*“No comparison status is available yet.”*)
6. Connected objects / relationship chips (useful)
7. Evidence / Debug (collapsible)

Statblock / encounter buttons from the older gold workbench dogfood are **not present** in current `GraphReviewNodeGameCard` — only **“Open evidence/debug”** under Useful surfaces.

### Evidence

- Browser snapshot headings: `Authored overlay` → `Review status` → `Connected objects / relationships` → `Evidence / Debug`.
- Authored overlay shows `Assertion ID: assert-e29968bcf24df5b7` in primary card flow.
- Adjacency chips include readable phrases (`the group negotiated with Glowkindle`, decision points).

### Friction

- **Metadata before game summary** for authored nodes (Authored overlay block precedes narrative summary).
- **Review status** adds little in live-only C1S2 mode.
- No statblock/encounter surfacing for threats/NPCs even when campaign corpus may have richer material elsewhere.

### Bugs

None blocking.

### Product read

**Half the story:** relationship chips and summaries help at the table; the panel still trains the GM to read implementation fields first.

### Recommended next action

- **Needs dedicated PR (A10b):** node detail hierarchy — summary + adjacency first; collapse Authored overlay + assertion IDs into debug.

---

## Story 5 — Evidence is available, but quiet by default

**Verdict: PARTIAL**

### What I tried

1. Opened **`the group`** node detail; toggled **Evidence / Debug**.
2. Reviewed authoring **Selected source** panel fields during graph object authoring mode.

### What happened

- Evidence / Debug is a `<details>` section (collapsed by default in component design).
- Collapsed summary line: `1 evidence badge; recap, authored_overlay.` — acceptable quiet signal.
- **Authored overlay** block in main card is **not quiet** — exposes assertion ID and visibility without requiring an explicit drill-down.
- Authoring selected-source panel shows: Selected text, Selection kind, Campaign/session, **Lane role**, **Graph id**, Source artifact, Context, Paragraph — useful for developers, noisy for GM trust-building.

### Evidence

- `GraphReviewNodeGameCard.tsx`: `Evidence / Debug` in `<details>`; Authored overlay section inline when `node.authored`.
- `GraphObjectAuthoringSelectedSource.tsx`: full metadata field list in primary authoring flow.

### Friction

- Scores/diagnostics not forced on GM in recap view — good.
- Assertion IDs and graph ids appear **before** the GM asks for them — bad for product story.

### Bugs

None blocking.

### Product read

Evidence is **discoverable** but not yet **quiet by default** for authored objects. The trust story is undermined by showing internal IDs in the primary card.

### Recommended next action

- **Needs dedicated PR (A10b):** move assertion ID / graph id / lane role to debug-tier panels.

---

## Story 6 — Visibility feels safe

**Verdict: PARTIAL**

### What I tried

1. Reviewed visibility dropdown in authoring forms (`GraphObjectAuthoringVisibilitySection`).
2. Inspected committed assertions (both **`gm_private`** in overlay).
3. Ran backend audience filter on loaded overlay.

### What happened

- Default visibility: **`gm_private`** (confirmed in draft defaults and both committed assertions).
- UI options: `GM private`, `Table known / player visible`, `Character-specific` (stub note), `Hidden until revealed`.
- Backend filter on overlay: **GM=2, table=0, player=0** assertions — gm_private assertions correctly excluded from table/player views.
- **No player-facing UI** exists to visually confirm table/player experience; verification is backend-only (acceptable for A8 scope).

### Evidence

```python
# filter_authored_overlay_for_audience on C1S2 overlay
# gm: 2, table: 0, player: 0
```

- Visibility options combine **table_known and player_visible** into one label: *“Table known / player visible”* (`graphObjectAuthoringDraft.ts`).

### Friction

- Combined table/player option creates **ambiguity** for future player views.
- `character_specific` shows honest stub note — good — but also signals incomplete product.
- Dogfood did not commit a **`table_known`** assertion in this pass (prior commits were gm_private only).

### Bugs

None blocking. A8 backend semantics verified by tests (31 cases).

### Product read

**Safe defaults with conservative backend filtering**, but UI does not yet make non-GM visibility feel first-class or testable by a GM without dev helpers.

### Recommended next action

- **Needs dedicated PR (A10b):** split table vs player visibility labels; add optional dev “preview as table” toggle before any player UI.

---

## Story 7 — Write safety is believable

**Verdict: PASS**

### What I tried

1. Identified write targets before/after commits:
   - Source recap markdown
   - Graph ingest run artifacts (`out/graph_memory/runs/.../20260706T023949Z/`)
   - Candidate graph gold fixtures (`evals/graph_memory_layer/examples/session_1_candidate_graph_gold/` — not C1S2-specific)
   - Authored overlay + event log + backups
2. Reviewed prepare/commit panel copy and paths.
3. Hashed source markdown and ingest artifacts (post-dogfood read-only verification).

### What happened

- Prepare panel exposes explicit **no-mutation guarantees**:
  - `Prepare wrote nothing.`
  - `Source markdown was not mutated.`
  - `Extracted live run artifacts were not mutated.`
  - `Candidate graph gold was not mutated.`
- Commit summary shows **overlay path**, **event log path**, **backup path**, overlay token, assertion/event counts, and the same no-mutation list.
- Overlay and event log appended; 4 backups present.
- Source markdown and ingest artifact SHA256 stable (read-only verification pass).

### Evidence

| Path | SHA256 (verification pass) |
|---|---|
| `Session 2 - Finishing the Job.md` | `12aac2b0f386248deb4928a4b629d207338bd48c3c52dd69355e1235f4a11355` |
| `projection_payload.json` | `e876145071fd43dcb1279550f3a296d423f9aceea5e9381487594708cc66a7c3` |
| `candidate_graph.json` | `898da0748f12cbcb0d57517c65b3cc5d39dc4038538b63c32aa201a2a1b45fc8` |

- Prepare guarantees source: `graph_object_authoring_prepare.py` `NO_MUTATION_GUARANTEES_PREPARE`.
- Event log records overlay token before/after for each commit.

### Friction

- Operator must scroll to prepare/commit panel (below prose + authoring forms) to see guarantees — but the copy itself is clear once found.
- Run directory timestamp (`20260706T023949Z`) ≠ run_id suffix (`20260706T024026Z`) — confusing when correlating paths manually.

### Bugs

None blocking for write safety.

### Product read

**This story lands.** The cautious-operator write safety narrative is believable and verified.

### Recommended next action

- **No action** on safety mechanics.
- **Tiny fix (optional):** surface run_id ↔ directory mapping in load controls helper text.

---

## Story 8 — Eval export is clearly developer-only

**Verdict: PASS**

### What I tried

1. Searched live-control UI for `include_in_gold_eval`, `gold_eval`, export controls — **zero matches**.
2. Checked normal authoring prepare/commit payloads and panels for gold-promotion language.
3. Verified `_graph_authoring/exports/` does not exist until explicit export.
4. Confirmed all overlay assertions have `include_in_gold_eval: false`.

### What happened

- No UI path suggests gold promotion during normal authoring.
- Export directory absent: `corpus/.../Campaign 1/_graph_authoring/exports/` not created.
- Gold eval export remains backend-only (`graph_authoring_gold_eval_export.py`), consistent with A9a note.
- Candidate graph gold fixtures unchanged (C1S2 has no dedicated candidate graph gold fixture; nearest is session_1 example from 2026-07-05).

### Evidence

- A9a note: *“No UI opt-in… Nothing writes unless export function is called.”*
- Overlay assertions: `"include_in_gold_eval": false` on all entries.
- `gold_eval_eligible_assertions(overlay)` → **0**.

### Friction

None for the developer-only boundary — that's the intended state.

### Bugs

None.

### Product read

**Clear separation** between authored campaign memory and eval export bridge. Normal authoring does not smell like gold promotion.

### Recommended next action

- **Defer A9b** (UI opt-in for `include_in_gold_eval`) until A10b UX hardening completes.

---

## Story 9 — Reload/query/explore closes the loop

**Verdict: PARTIAL**

### What I tried

1. Reloaded C1S2 graph review after prior commits.
2. Searched for authored memory via:
   - Authored overlay banner
   - Clicking **`the group`** pill
   - Reading opening line for **`gang`**
3. Checked projection API node views after reload.

### What happened

- Reload works: banner `Authored overlay loaded: 2 assertions · 1 object · 1 relationship`.
- **`the group`** findable as pill; node card shows authored alias **`gang`**.
- **`gang`** in opening sentence **not** findable as pill or search target in prose — GM must know to inspect **`the group`**.
- Relationship reload visible via adjacency chips on nodes (extracted edges more discoverable than authored `same_as`).

### Evidence

- Projection API: `group_the_group.aliases` includes `gang`; markdown still contains plain `The gang survived`.
- Browser: status region shows overlay loaded counts after page load without manual cache busting.

### Friction

- Loop closes for **node-centric** recall, not **prose-centric** recall.
- Authored overlay summary miscount obscures what was written.
- No explicit “show authored assertions” list in main review surface beyond banner counts.

### Bugs

- Alias-not-projected-into-markdown is the main functional gap (same as Story 1).

### Product read

**Retrievable if you know where to click**, not retrievable if you reread the opening paragraph and expect “gang” to be grounded.

### Recommended next action

- **Needs dedicated PR (A10b):** prose mention resolution for authored aliases + authored assertion browse panel.

---

## Safety checks (cross-cutting)

| Check | Result |
|---|---|
| Source markdown mutated | **No** (SHA256 stable) |
| Extracted ingest artifacts mutated | **No** (SHA256 stable) |
| Candidate graph gold mutated | **No** (no C1S2 fixture; session_1 example untouched) |
| Overlay written | **Yes** (`authored_graph_overlay.json`, 2 assertions) |
| Event log appended | **Yes** (4 event records) |
| Backup created on commit | **Yes** (4 backups) |
| Authored overlay reload | **Yes** |
| Backend visibility filter | **Yes** (gm-only assertions hidden from table/player) |
| Gold eval export side effect | **No** |

---

## UX friction log (ordered by severity)

1. **Prose grounding gap:** authored aliases do not re-render as pills in source text (`gang` stays plain).
2. **Node detail metadata-first** for authored nodes (assertion ID, overlay block before summary).
3. **Long scroll authoring layout** — prepare/commit/staging remain far below prose (inherits session-1 dogfood finding; not fully retested end-to-end in this pass but layout unchanged).
4. **Overlay summary miscounts** link-existing as “object.”
5. **Visibility dropdown merges** table and player visibility.
6. **Relationship authoring lacks campaign predicate coaching** — easy to commit low-value edges.
7. **Toolbox clutter** — `Author Draft` tab still present beside new graph object authoring mode; multiple graph tools in toolbox.
8. **Run dir vs run_id timestamp mismatch** complicates manual path verification.

---

## Bugs found

| ID | Severity | Description | Recommendation |
|---|---|---|---|
| B1 | UX | `GraphAuthoredOverlaySummary` calls link-existing enrichments “object” | Tiny fix in A10b |
| B2 | Product | Authored alias `gang` not projected into markdown mentions | Dedicated A10b projection work |
| B3 | UX | Assertion ID shown in primary node card | Dedicated A10b node detail pass |
| B4 | UX | `table_known` and `player_visible` combined in one visibility option | Design + tiny copy fix |

No crashers, data loss, or source mutation bugs found.

---

## Tiny fixes made in this PR

**None.** This PR is report-only. Issues above are documented for follow-up PRs.

---

## Recommended next PRs

### A10b — Dogfood hardening (do this next)

1. **Prose alias grounding** — show authored aliases as pills or highlighted mentions in projected markdown.
2. **Node detail hierarchy** — game summary + adjacency first; demote assertion IDs to debug.
3. **Overlay summary accuracy** — count link-existing separately from new object assertions.
4. **Relationship form coaching** — campaign-facing presets (`member_of`, `protects`, `commands`, …) and warnings on weak types.
5. **Visibility label split** — separate table vs player visibility options.
6. **Authoring layout** — pull staging/prepare/commit closer to selection context (carry forward session-1 finding).

### A9b — Eval export UI (defer)

After A10b. Backend foundation (A9a) is sufficient for developer bridge; UI opt-in should not precede legible GM authoring.

### Optional cleanup

- Toolbox deprecation labels for legacy `Author Draft` / `Graph Gold Review` tabs.
- Run id ↔ directory helper in load controls.

---

## Final go/no-go

| Gate | Decision | Rationale |
|---|---|---|
| **Continue to A10b?** | **GO** | Core write path is safe; product stories are partially told; friction is specific and actionable. |
| **Start A9b now?** | **NO-GO** | Eval export boundary is fine; GM-facing authoring UX should harden first. |
| **Skip hardening and build new features?** | **NO-GO** | Workflow is implemented but not yet a convincing GM memory tool. |

**Bottom line:** DungeonMindBuddy graph authoring is **technically correct and write-safe**, but still **more graph editor than campaign teacher**. A10b should focus on prose grounding, node detail hierarchy, and relationship/visibility clarity before LLM assist or eval export UI.
