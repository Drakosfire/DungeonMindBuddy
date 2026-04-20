---
title: "Session 21 — prep exercise agentic trace"
document_class: planning
canon_layer: campaign
campaign_id: longmont-c2
temporal_scope: session_specific
session: 21
origin_session: 21
last_updated_session: 21
source_class: process_log
gm_notes: "Meta-doc: tracks GM prep steps and how they mirror agentic / HITL loops. Not in-world canon."
---

# Session 21 prep — exercise trace (agentic parallels)

This file runs **in parallel** to brainstorm and prep artifacts. Each step below is something we *did* or *will do* in the prep exercise, with a short note on how it maps to **agentic loops** (observe → plan → act → verify, tool use, state drift, human gates, etc.).

## How to read the mapping

| Prep move | Agentic parallel (loose) |
|-----------|---------------------------|
| Raw dump before structure | High-entropy **observation** kept out of the compressed policy (avoid premature summarization). |
| Explicit “not canon” flags | **Schema / provenance** so downstream agents (or future you) don’t treat noise as ground truth. |
| Separate brainstorm vs trace doc | **Sidecar telemetry** — same run, different channel from the “answer.” |
| Frozen recap context before writes | **Snapshot state** before mutations so grading / guards don’t **drift** on re-read. |
| Preview then commit writes | **HITL gate** — human approves diff before irreversible corpus change. |
| Cohort N runs + commit rate metrics | **Eval harness** — pass/fail vs distribution of behaviors. |

---

## Log (append as we go)

### Step 1 — Brainstorming dump captured (unrefined)

- **What we did:** Stored verbatim GM prose in `Session 21 - brainstorming dump.md` with `source_class: brainstorming_unrefined` and NOT CANON flags.
- **Agentic tie-in:** Deliberately **no assistant refinement** = no “tool output” merged into state before you approve. Same idea as **withholding tool execution** until intent is clear, or logging **raw traces** before summarization so the loop can’t “lie” about what you actually thought.

### Step 2 — This trace doc started

- **What we did:** Opened a parallel **process log** (this file) tied to Session 21 prep.
- **Agentic tie-in:** **Observability** over the meta-loop itself — like `step_index`, `correlation_id`, or eval sidecars that record *how* a decision was reached, not only the final artifact. Helps when you later ask “why did we think the storm was literal vs metaphor?”

---

## Reserved headings (fill as the exercise continues)

### Step 3 — Faction dossier ingested into corpus (author file from Downloads)

- **What we did:** Copied `Raucous_Saints_of_the_Rolling_Longhouse.md` into the campaign tree as `Longmont Campaign/Campaign 2/Factions/Raucous_Saints_of_the_Rolling_Longhouse.md`, added YAML frontmatter (`faction_module`, C2 provenance, table_note for rumor vs Dustwalker), and added `Factions/README.md` as an index pointer.
- **Agentic tie-in:** **Tool output promotion** — external artifact (Downloads) becomes **durable state** in the repo the same way an agent would `write_corpus_file` after human approval: one canonical path, explicit metadata, discoverable for later `read_corpus_file` / RAG / prep loops.

### Step 4 — Story threads backlog doc (emergent hooks without ledger weight)

- **What we did:** Added `Longmont Campaign/Campaign 2/Story threads backlog.md` — table + optional scratch + promote/drop archive — and linked it from `Campaign 2 Notes.md`. Seeded **STB-001** (Mother of Fallen Branches hatchling possibly tailing the crew) as **P3 / dormant**.
- **Agentic tie-in:** **Buffer queue / backlog grooming** — high-volume agents dump candidates into a holding area; a separate process (you) assigns priority and promotes to “production” (narrative ledger) or drops. Prevents **context pollution** of the main state doc with every stray idea while still **persisting** them for optional retrieval.

### Step 5 — Drop-in scene module (Ephanna shop + rumor)

- **What we did:** Wrote `Session Prep/Session 21 - Mossford Saltfen rumor shop.md` — **Saltfen Dry Goods & Notions**, proprietor **Yulla Saltfen**, scripted rumor variants (Dustwalker-shaped vs hope-forward vs explicit Mirathorn callback), optional second customer beat, exit hooks, link to Raucous Saints dossier.
- **Agentic tie-in:** **Tool schema for play** — structured prompt with read-aloud blocks + branching beats: how an agent would hand a human operator a **runbook** (not just lore): *when X, offer Y* without merging into canon until the table commits.

### Step 6 — Session intro (recap → read-aloud)

- **What we did:** `Session Prep/Session 21 - Session intro.md` — GM reflection from Session 20 end state, full + short **player-facing** opens, camera handoff prompt, pointers to Saltfen shop + Tealeaf line.
- **Agentic tie-in:** **State summarization with provenance** — compress prior trajectory into an operator brief + user-facing narrative without inventing new canon; **branch** (camp vs town) explicit so execution doesn’t assume a single entry node.

### Step 7 — _(pending)_

---

## Open meta-questions (optional scratch)

- When does brainstorm get **promoted** to canon prep (explicit human edit / new doc)?
- Which beats are **single-turn** (resolve at table) vs **multi-turn** (storm across sessions)?
