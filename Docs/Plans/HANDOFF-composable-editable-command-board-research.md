---
document_id: dmb-handoff-composable-editable-command-board-research
title: "HANDOFF — Composable editable Command Board (Notion-class prep surface)"
document_class: planning
plan_kind: handoff
status: ready for primary-agent research + design spike
version: 0.2
created_at: "2026-06-13T00:00:00Z"
last_updated_at: "2026-06-15T00:00:00Z"
branch_anchor: cursor/c2s23-mireward-prep-ui
related_design:
  - Docs/Design/DESIGN-tiptap-role-in-command-board.md
  - Docs/Design/DESIGN-tiptap-command-board-architecture.md
  - Docs/Design/DESIGN-mireward-command-board-shell.md
  - Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md
  - Docs/Plans/PLAN-canvas-constructor.md
related_dogfood:
  - Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md
  - Docs/Plans/HANDOFF-pr115-statblock-mock-dogfood-then-api-wire.md
operator_intent: >-
  Upgrade the Mireward Command Board from read-only corpus drilldowns into a
  fully editable, composable GM workspace (Notion / Confluence / dynamic-markdown
  class). Evaluate whether existing DungeonMind Canvas work can be extended,
  and parallel-evaluate mature open-source editors we could adopt or fork.
---

# HANDOFF — Composable editable Command Board (research + design spike)

**Audience:** Primary planning agent (strong model). This is **not** an execution brief for a first coding slice yet. Deliver a written recommendation with evidence before implementation lands.

**Operator ask (verbatim intent):** We are dogfooding the static Command Board hard. The next major upgrade is a **fully editable and composable interface** — inline edits, drop-in blocks, line-level editing, media embeds — in the same product family as Notion, Confluence, and modern block markdown editors. **DungeonMind Canvas may already be far enough along to rejigger toward this.** Also **survey off-the-shelf open-source projects** we could use or fork instead of greenfield UI.

---

## §0 Mission

Produce a **build-vs-adopt decision** and a **phased migration plan** that:

1. Preserves what dogfood proved works (combat-first command board, fast drilldown, local persistence, corpus as source of truth).
2. Replaces read-only accordion + modal markdown preview with an **authoring surface** the GM can edit at the table.
3. Respects corpus safety (two-phase writes, allowlists, no silent dossier/statblock corruption).
4. Names concrete repos/files in DungeonMind monorepo **and** 3–5 OSS candidates with license + integration fit notes.

**Do not** start by rewriting the React `/surface` app as the product home. The static Command Board path (`evals/c2_live_prep/mireward-prep/`) is the dogfood harness that earned operator trust; any editor upgrade should either grow from that harness or replace it deliberately with a migration story.

---

## §1 How we are dogfooding today (ground truth)

### 1.1 Product shape that worked

| Surface | What the GM uses it for | Why it worked |
|---------|-------------------------|---------------|
| **Combat tracker** (`combat.html`) | Initiative, HP, turn order, statblock links | Operational layer first — rows in view, depth one click away |
| **Live Play hub** (`live-play.html`) | Launch cards for at-table tools | Clear primary vs reference panes |
| **Corpus index panes** (statblocks, NPCs, roll tables, locations) | Expand row → inline rendered markdown | No file hopping during prep |
| **Command toolbox drawer** | Statblock generator dogfood | Global tools without polluting list pages |
| **Markdown modal** | Quick preview of `data-repo` links | Context switching reduced vs opening raw files |

Evidence log: `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`  
Shell decisions: `Docs/Design/DESIGN-mireward-command-board-shell.md`  
Step-through dogfood script: `Docs/Plans/HANDOFF-pr115-statblock-mock-dogfood-then-api-wire.md`

### 1.2 Serving stack (current)

```text
Vite :5173  →  static mireward-prep/*.html + prep.js
           →  proxies /api  →  FastAPI :8000  (/api/live/*)
Corpus      →  git markdown under corpus/eldyrwild-markdown/
Indexes     →  allowlisted crawlers (*_corpus_index.py) → JSON → client-rendered HTML
Persistence →  combat + scratch + toolbox state in localStorage; canon via corpus writer API
```

### 1.3 What is intentionally read-only today

- Dynamic index rows render markdown via `data-md-embed` + `prep-markdown.js` — **no in-place edit**.
- Session-specific locks (S23 encounter mix, promotion previews) stay as hand-authored HTML folds below indexes.
- Corpus promotion (statblock generator → `Statblocks/generated/`) uses **two-phase preview/confirm** — must remain for autonomous and operator writes.

### 1.4 Friction the editable surface should solve

From dogfood notes and recent rework:

- Static HTML/card grids **duplicate corpus** and go stale when hubs promote.
- Nested scroll was fixed, but the GM still **cannot patch a table row, location blurb, or NPC note** without leaving the board.
- Each new entity type adds another **bespoke filesystem crawler** — editable UI will increase pressure for a unified document/query model (`Backlog.md` → corpus storage IDEA).
- `file://` vs served mode and `localhost` vs `127.0.0.1` localStorage splits already caused false bug reports — editor state must be explicit about save targets.

---

## §2 Target UX (operator vision)

Think **Notion / Confluence / block markdown editor**, adapted for TTRPG prep:

| Capability | Operator expectation |
|------------|---------------------|
| **Inline edit** | Click into prose and change it where it renders — not only in a separate modal or raw file view |
| **Block composition** | Drop in headings, callouts, tables, roll-table embeds, statblock cards, NPC chips, media |
| **Line / block granularity** | Small surgical edits during live play (HP notes adjacent, scene anchor tweak, table footnote) |
| **Media** | Images (maps, tokens, handouts), possibly audio/video links — corpus-relative or uploaded assets with clear provenance |
| **Composable pages** | GM assembles a session board from blocks + live widgets (combat strip, clock, open loops) — not fixed HTML templates |
| **Drilldown preserved** | Combat row → statblock → edit reinforcement statblock should stay one flow, not three apps |

**Non-goal for v0 of the editor spike:** full wiki permissions, multi-user realtime cursors, or replacing the planner agent's discovery model. GM-facing edits ≠ provisioning retrieval paths to the LLM (see `.cursor/rules/llm-context-discovery.mdc`).

---

## §3 “Canvas” in this repo — disambiguate before designing

The word **Canvas** appears in three places. The primary agent must inspect all three and say which (if any) is the right foundation.

### 3.1 Cursor Canvas (`.canvas.tsx` + `cursor/canvas` SDK)

- **Location:** `evals/*/canvas_templates/*.canvas.tsx`, emitters like `ingested_corpus_library_canvas_emit.py`
- **Today:** Benchmark review dashboards, corpus library telemetry, live-query trace visualization
- **Components:** `CollapsibleSection`, `Grid`, `Stat`, `Table`, `Callout`, `useCanvasState` from `cursor/canvas`
- **Fit for editable prep?** Good for **read-only operational dashboards** and structured review; **not** currently an inline markdown editor. Might still inspire layout/panel patterns for a composable board.

### 3.2 Canvas Constructor (internal standardization project)

- **Location:** `Docs/Plans/PLAN-canvas-constructor.md`, `Docs/Plans/CHECKLIST-canvas-constructor.md`
- **Thesis:** Benchmark JSON → normalized payload → generated canvas blocks with marker patching
- **Fit?** Relevant if prep pages become **projection-driven** (corpus index JSON → generated UI blocks). Less relevant for freeform GM authoring unless extended with editable block types.

### 3.3 DungeonMind Canvas / layout engine (monorepo sibling — verify on disk)

Engineering docs reference a **measurement-based canvas** pattern (component registry, dynamic locking, template hydration) used by StatblockGenerator / LandingPage-style services (`PATTERNS-Canvas.mdc` in parent `.cursor/rules/`, `LEARNINGS-Reusable-Engine-Development` anti-patterns).

**Primary agent action:** Search the **DungeonOverMind monorepo** (outside this Buddy repo if needed) for:

- Canvas / layout registry code
- Editable component patterns
- Export/PDF pipelines already wired to statblock templates

Report whether that engine is **(a)** reusable for GM markdown blocks, **(b)** statblock-layout-only, or **(c)** too coupled to consumer apps to lift without a extract phase.

---

## §4 Open-source landscape — mandatory survey

Before recommending greenfield React, evaluate **adopt or fork** candidates. The spike should produce a comparison table (license, React fit, markdown/block model, media, self-host, extension story, corpus export as markdown).

**Seed list to investigate (non-exhaustive — add others you find):**

| Project | Why look |
|---------|----------|
| [BlockNote](https://github.com/TypeCellOS/BlockNote) | Notion-style block editor on ProseMirror; React-first |
| [TipTap](https://github.com/ueberdosis/tiptap) | Headless ProseMirror toolkit; heavy extension ecosystem |
| [Milkdown](https://github.com/Milkdown/milkdown) | Markdown-centric WYSIWYG; plugin architecture |
| [Plate](https://github.com/udecode/plate) | Rich-text framework on Slate/TipTap patterns |
| [Novel](https://github.com/steven-tey/novel) | Notion-like UX on TipTap (good reference impl) |
| [AFFiNE](https://github.com/toeverything/AFFiNE) | Full workspace (may be heavy; study block + doc model) |
| [Outline](https://github.com/outline/outline) | Team wiki; strong doc model, heavier infra |
| [HedgeDoc](https://github.com/hedgedoc/hedgedoc) | Collaborative markdown (real-time bias) |
| [md-editor-v3 / similar](https://github.com/imzbf/md-editor-v3) | Simpler MD editors if block composition is overkill |

**Evaluation criteria (score each 1–5 with notes):**

1. Inline + block editing quality
2. Markdown round-trip fidelity (corpus files are markdown-first)
3. Custom block types (roll table embed, statblock card, corpus link chip)
4. Media handling (local assets, R2, relative corpus paths)
5. Self-host / no SaaS lock-in
6. License compatible with private campaign corpus
7. Effort to integrate with existing FastAPI + Vite stack
8. Mobile / at-table usability

---

## §5 Hard constraints (do not design around these)

| Constraint | Source |
|------------|--------|
| **Corpus markdown remains source of truth** for canon hubs | `corpus-layout-conventions.mdc`, hub README contracts |
| **Two-phase commit** for writes | `corpus_writer.py`, `corpus-two-phase-commit.mdc` |
| **Denied paths** for casual edits | dossiers, seeds, `*_statblock*.md` — session changes go through recaps / allowed paths |
| **Planner discovery** | Do not inject corpus bodies into agent prompts via editor shortcuts |
| **Cost / latency** | At-table edits must not require LLM calls to save |
| **Dogfood harness artifacts** | Benchmark disk artifacts rules still apply for eval surfaces |

Any editor design must show **where Save goes** (corpus path, session scratch, combat localStorage, generated lane) and **which validator** runs before commit.

---

## §6 Hypothesis paths (primary agent compares)

```text
Path A — Extend static Command Board incrementally
  prep.js index rows → editable embed component → save via existing writer API
  Pros: preserves dogfood URL stack; smallest seam
  Cons: may hit ceiling quickly for block composition + media

Path B — New React prep module in apps/live-control-ui (or sibling package)
  Vite route replaces static HTML panes one at a time
  Pros: component ecosystem, TipTap/BlockNote viable
  Cons: migration cost; risk of repeating /surface mistakes

Path C — Reuse / extract DungeonMind Canvas layout engine
  Register prep block types (markdown, embed, combat widget) in existing registry
  Pros: shared DNA with statblock/canvas export if engine fits
  Cons: unknown coupling — must be proven by reading sibling code

Path D — Fork/adopt OSS editor shell
  Embed BlockNote/TipTap/etc. with custom block extensions for corpus entities
  Pros: fastest path to Notion-like UX
  Cons: markdown round-trip, custom blocks, writer integration work

Path E — Hybrid
  OSS editor for prose blocks + existing combat tracker + Cursor-style canvas for telemetry/review only
  Pros: use the right tool per pane
  Cons: two UI stacks to maintain unless unified shell chrome (see shell design doc nav/toolbox)
```

**Deliverable:** Recommend **one primary path + one fallback**, with falsification tests (“if X fails, switch to Y”).

---

## §7 Suggested phased delivery (for the recommendation doc only)

The primary agent should refine these; do not treat as committed scope.

| Phase | Goal | Falsification |
|-------|------|---------------|
| **R0 Research** | OSS matrix + Canvas audit + write path map | No chosen path after R0 → stop and ask operator |
| **R1 Read-only parity** | One pane (e.g. Locations or Live notes) in chosen stack with same index API | If load/render slower than static HTML, justify |
| **R2 Inline edit scratch** | Editable scratch / session notes with local persistence | If GM still opens raw files, UX failed |
| **R3 Corpus-backed save** | One allowlisted write pattern (e.g. Session Prep append, timeline row) through writer | Any save without preview token is rejected |
| **R4 Composable blocks** | Custom embed blocks (roll table, statblock ref, image) | Round-trip markdown diff inspectable in git |
| **R5 Combat integration** | Editable notes on combat rows linked to corpus or session artifact | Combat dogfood regression vs `combat.html` baseline |

---

## §8 Files to read first (ordered)

### Dogfood + shell

1. `Docs/Design/DESIGN-mireward-command-board-shell.md`
2. `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`
3. `evals/c2_live_prep/mireward-prep/assets/prep.js` — `initMarkdownEmbeds`, `*CorpusIndex`, toolbox drawer
4. `evals/c2_live_prep/mireward-prep/live-play.html` — launch hierarchy

### Backend seams

5. `apps/live_control_server/routes/live.py` — `/api/live/*/index`, statblock workbench, writer endpoints
6. `src/agent/corpus_writer.py` — allowlist + two-phase commit
7. `apps/live_control_server/services/*_corpus_index.py` — index item shapes (likely become editor document metadata)

### Canvas references (Buddy repo)

8. `Docs/Plans/PLAN-canvas-constructor.md`
9. `evals/c2_live_prep/canvas_templates/ingested-corpus-library.canvas.tsx` — Cursor canvas SDK patterns
10. `.cursor/skills/benchmark-review-canvas/SKILL.md`

### Live-control React (legacy / idea mine — learn from, do not blindly promote)

11. `apps/live-control-ui/src/surface/` — InspectorPane, module registry
12. `Docs/Plans/archive/2026-06-22/handoffs/HANDOFF-pr84-l5f-read-only-pane-renderers.md` — read-only artifact renderers already built

### Backlog pressure

13. `Backlog.md` — `[IDEA] Corpus storage — DB or indexing/query layer`

---

## §9 Primary agent deliverables

Return a single design note (path TBD by agent; suggest `Docs/Design/DESIGN-composable-editable-command-board.md`) containing:

1. **Executive recommendation** — build / extend Canvas / adopt OSS / hybrid (1 page max).
2. **OSS comparison table** — at least 5 candidates scored against §4 criteria.
3. **DungeonMind Canvas audit** — what exists, reuse verdict, with file paths.
4. **Write-path diagram** — edit surface → validation → preview → corpus path (mermaid ok).
5. **Migration map** — static pane → editable equivalent; what stays static in v1.
6. **Risks** — markdown fidelity, PII in corpus, merge conflicts, localStorage vs server state.
7. **Next HANDOFF** — if operator approves, a narrow **implementation** handoff for Phase R1 only (with §4 allowlist + §7 verification commands per external-agent loop conventions).

**Explicitly out of scope for this spike:** implementing the editor, adding npm dependencies, or refactoring all index crawlers into a DB.

---

## §10 Open questions for operator (resolve in recommendation)

1. Should **canon hub files** (README, dossiers) ever be inline-edited from the board, or only **session-scoped** docs (prep, recaps, scratch)?
2. Are **images** stored in corpus git, object storage (R2), or both?
3. Is **real-time collaboration** a future requirement, or strictly single-GM local-first?
4. Should the editable surface **replace Cursor** for prep during live sessions, or complement it?
5. Minimum bar for **markdown round-trip**: exact byte preservation vs semantic equivalence?

---

## §11 Verification (research spike only)

No code ship gate. Research is done when:

- [ ] All §9 deliverables exist on disk and are linked from this handoff's status line.
- [ ] OSS table includes licenses and links.
- [ ] Canvas audit cites real file paths (or states "not found in monorepo" with search commands run).
- [ ] One path is recommended with falsification criteria.
- [ ] Operator open questions (§10) are either answered or flagged as blockers.

---

**Status after pickup:** _pending — primary agent sets `status:` in frontmatter and links the design doc._
