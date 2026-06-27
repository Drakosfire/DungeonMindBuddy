# UX Stories — Agent Interaction + Hermes

**Status:** Active design capture
**Written:** 2026-06-23
**Source:** GM interview (plan-mode prep/review)
**Branch context:** post-P3.1 Agent Interaction roadmap and forward
**Related:** `Docs/Plans/HANDOFF-self-continuity-hermes-agent-interaction-bar.md`, `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`, **`Docs/Design/ANCHOR-agent-interaction-hermes.md`** (re-anchor entry point)

## Design north star

Agent Interaction is becoming DungeonBuddy's app-level GM companion. The local `/plan` implementation has proven the interaction model through P3.1, but `/plan` is only the first intentional surface. Corpus remains canon; Hermes long-term memory is future and non-canon; graph/ontology work is sibling infrastructure consumed through source-vocabulary adapters, not owned by Agent Interaction.

---

## Current phase status after local P3.1

| Phase | Story status | Roadmap meaning |
|-------|--------------|-----------------|
| **P0 — conversational core** | Satisfied locally / partial target | Thread/turn model, same-thread follow-up, local persistence, trace toggle, and Hermes session seam exist in `/plan`; mature Hermes continuity remains future. |
| **P1 — citation trust surface** | Satisfied locally / partial target | Citation cards and in-pane source reader exist; cite-or-abstain policy hardening remains future. |
| **P1.1 — source reader hardening** | Satisfied locally | `/api/live/citation-source` and safe read-only lookup are covered as trust infrastructure. |
| **P2 — thread management** | Satisfied locally / partial target | Named thread create/rename/switch/delete and long-thread guardrails exist locally; app-level persistence waits for R10/P4. |
| **P3 — retrieval freshness and source-currentness** | Satisfied locally / partial target | `retrieval_freshness`, `RetrievalFreshnessPanel`, `/api/live/citation-freshness`, `CorpusChangeSignalPanel`, evidence snapshots, and metadata-only source-line hash/status checks exist; automated corpus-change fan-out remains future. |
| **P4 / R10 — app-level provider lift** | Future / next likely code rung | Move `AgentInteractionProvider` above routes/surfaces while preserving current `/plan` UX. |
| **P5 — tool parity** | Future | Full operator tools in conversation; all writes remain preview -> GM confirm. |
| **P6 — Hermes memory integration** | Future | Hermes long-term memory may help continuity/preferences only; campaign facts remain source-grounded corpus canon. |

React `/play` follows R10/P4 as the second-surface proof. Runtime graph retrieval is future adapter work, not a prerequisite for the provider lift. Agent Interaction consumes `SourceArtifact -> SourceAnchor -> SourceUnit` envelopes and must not treat graph summaries as source evidence.

---

## Persona and context

**As a GM in plan mode**, I work at my desk before session (prep) and after session (ingestion + review). I am not optimizing for at-table live combat in this slice — though the bar and active thread should follow me if I change surfaces.

---

## Example journey (acceptance anchor)

This scenario should eventually pass end-to-end:

1. **Turn 1:** "What is the name of the Inn in Mireward Reach and who owns it, what are its prices and what does it offer?"
   - **Good enough:** Prose answer covering name, owner, prices, offerings — each fact **linked to corpus source**; click opens **full rendered doc inside the Agent Interaction pane** (not plan canvas).
2. **Turn 2 (same thread):** "Does the owner know Lysandra? If so how?"
   - **Good enough:** Answer uses **thread context** from turn 1; does **not** unnecessarily re-run full retrieval; still links claims to sources where new evidence is cited.
3. **Reload browser:** Full thread returns (Q/A, links, trace pointers).
4. **Collapsed bar:** Shows thread **title only** — minimal, out of the way.

---

## Epics and user stories

### Epic 1 — Plan-mode conversation (Hermes default)

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| **S1.1** | **As a GM**, I want to ask natural-language prep questions and get prose answers, **so that** I can prep without manually hunting corpus files. | Hermes is the default backend; no operator-facing "live vs hermes" toggle in steady state. |
| **S1.2** | **As a GM**, I want my **active thread to continue** when I open Agent Interaction, **so that** follow-ups feel like talking to the same assistant. | Default view = active thread + ask box; new thread via explicit action **or system auto-suggest** (see S1.6). |
| **S1.6** | **As a GM**, I want the system to **auto-suggest starting a new thread after N turns**, **so that** long arcs do not become muddy without me noticing. | Suggest (not force) when active thread reaches **N turns** (N configurable, default TBD); one-click accept or dismiss; never silent fork. |
| **S1.3** | **As a GM**, I want to **name threads** (not just timestamps), **so that** I can find "Session 24 inn prep" vs "post-S23 ingestion review" later. | Create/rename thread; title shown in collapsed bar and thread list. |
| **S1.4** | **As a GM**, I want **as many threads as I need**, **so that** I can parallelize prep topics without losing context. | Support **2–3 live arcs same day** (inn prep, statblock, ingestion) with frequent switching; no artificial single-thread limit beyond sensible storage bounds. |
| **S1.7** | **As a GM**, I want to **switch between parallel threads quickly** and **resume where I left off**, **so that** same-day multi-topic prep does not feel like losing my place. | Thread switcher surfaces named active arcs; restoring scroll/turn focus per thread; switching is a first-class action (not buried archive). |
| **S1.8** | **As a GM**, I want **every thread to read and write against live corpus state**, **so that** no thread shows stale canon after another thread ingests or commits. | Reads always resolve current corpus (fresh retrieval / `get_document`); writes available in any thread with preview→confirm; cross-thread invalidation when underlying sources change. |
| **S1.5** | **As a GM**, I want follow-up questions in the same thread to use **conversation history**, **so that** "Does the owner know Lysandra?" does not require repeating the inn context. | Turn N includes prior Q/A in agent context; Hermes session id reused across turns (not `--oneshot` per message). |

### Epic 2 — Corpus-grounded answers with rich citations

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| **S2.1** | **As a GM**, I want answers as **readable prose with deep-linked markdown** to corpus sources, **so that** I trust facts and drill into originals without leaving the agent surface. | Inline links in the answer; click opens **full rendered corpus doc inside the Agent Interaction pane** (expand/split within bar+pane chrome — **not** plan canvas replacement). Build on existing `PlanAgentInteractionBar` / pane layout. |
| **S2.2** | **As a GM**, when evidence is **partial**, I want to see **what was found** and whether the answer is expandable, **so that** thin retrieval is honest rather than silent failure. | UI shows admitted evidence summary alongside answer; no blocked empty state when partial evidence exists; optional "retrieve more" when agent chooses. |
| **S2.3** | **As a GM**, I want the agent to **cite or abstain** on thin claims, **so that** I am not given confident fiction. | Skill/policy: claims tied to evidence ids or paths; missing evidence → explicit uncertainty, not filler. |
| **S2.4** | **As a GM**, I want the agent to **decide when to re-retrieve** vs lean on thread context, **so that** follow-ups are fast and relevant without stale grounding. | Follow-up after inn question should not re-fetch full inn docs unless the new question requires new sources; **re-retrieve when corpus may have changed** (write/ingest in any thread); decision visible in trace when dogfooding. |
| **S2.5** | **As a GM**, when I open a citation from an older turn, I want the **corpus doc view inside the Agent Interaction pane** to show **current content**, **so that** I am not misled by a snapshot from before ingestion or a write. | In-pane doc reader reads live file; stale indicator when content changed since turn timestamp; re-ask/refresh affordance. |
| **S2.6** | **As a GM**, when I inspect an older answer, I want a **compact corpus change signal**, **so that** I can tell whether cited evidence still matches current source state. | Stored answer can show **Current / Changed / Unknown / Unavailable** based on metadata-only source checks through `/api/live/citation-freshness` and `CorpusChangeSignalPanel`. |

### Epic 3 — Inspectability (dogfood → invisible)

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| **S3.1** | **As a GM**, I want **trace available when I choose**, **so that** I can audit grounding during dogfood without cluttering normal prep. | **User toggle** controls trace visibility (default TBD); when on, full trace per turn (retrieved text, prompt, steps, tokens). |
| **S3.2** | **As a GM**, I want trace **off by default once I trust the surface**, **so that** the UI stays calm and citations remain the primary trust layer. | Toggle off hides trace panels; toggle state persists per user/campaign; citations in prose always available. |
| **S3.3** | **As a GM**, I want **rich tool/step trace** from Hermes runs, **so that** I can see lookup → get_document → answer, not a single opaque step. | `agent_trace.steps` reflects intermediate tool calls parsed from Hermes session artifacts. |

### Epic 4 — Memory policy (explicit layers)

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| **S4.1** | **As a GM**, I want **thread history persisted across reload**, **so that** I never lose an prep conversation mid-session. | Full thread: questions, answers, citation pointers, trace ids — not metadata-only. |
| **S4.2** | **As a GM**, I want **generous conversation memory** in v1 (pare down later), **so that** the agent feels like a continuous desk partner. | Server or client stores bounded but complete turn payloads; document cap and eviction policy. |
| **S4.3** | **As a GM**, I want **Hermes session memory integrated** over time, **so that** orchestration state survives across turns while **corpus remains canon via tools**. | Phase 1: UI + Hermes session id continuity. Phase 2: Hermes long-term memory for non-canon preferences + thread continuity; campaign facts only via corpus tools. |
| **S4.4** | **As a GM**, I want a **clear mental model** of what is remembered where, **so that** I know corpus ≠ chat ≠ Hermes ambient memory. | Visible policy indicators (e.g. thread memory on, Hermes memory mode); `.hermes.md` rules reflected in product copy. |

**Memory layers (target model):**

| Layer | Contents | Canon? | Persist |
|-------|----------|--------|---------|
| UI thread | Q/A, titles, citation pointers, trace ids, freshness metadata | No — pointers to canon | Yes, local reload now; app/user scope after R10 |
| Retrieval proof | Admitted evidence per turn, retrieval decision metadata, `retrieval_freshness` | Evidence only when tied to source-grounded units | Per turn in thread |
| Evidence snapshots / source-currentness metadata | Citation locators, line ranges, source-line hashes, Current / Changed / Unknown / Unavailable status | No — metadata-only check against canon | Per turn; must not store source bodies |
| Hermes session | Tool loop state, turn context, orchestration continuity | No | Session id reuse / future hardening |
| Hermes long-term | Preferences and thread-continuity helpers | No for campaign facts | Future only |
| Corpus | Campaign truth in markdown and promoted canonical artifacts | **Yes** | Corpus tools / explicit write APIs only |
| Graph memory | Derived semantics, graph IR, validation reports, shadow retrieval outputs | No by itself; source evidence must come through `SourceUnit` envelopes | Ontology/taxonomy workstream; future adapter consumption only |

Agent Interaction may use graph-backed retrieval only when it emits or enriches source-grounded `SourceUnit` envelopes. Graph summaries may help navigation or display, but they are not source evidence for factual claims.

### Epic 5 — App-level bar (R10) and cross-surface continuity

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| **S5.1** | **As a GM**, I want the **same active thread** when I move between surfaces (e.g. `/plan` → live), **so that** prep conversation is not trapped on one route. | `AgentInteractionProvider` holds thread state; surfaces publish ambient context only. |
| **S5.2** | **As a GM**, I want the **collapsed bar to show only the thread title**, **so that** it stays minimal and out of the way. | No answer snippets or turn counts in collapsed state unless user expands. |
| **S5.3** | **As a GM**, I want Agent Interaction to **follow me across projects/surfaces** as the user's continuity layer, **so that** it matches the architecture in `ANCHOR-plan-surface-agent-interaction.md`. | R10 lift: bar in `AppChrome`, pointers-only persistence. |

### Epic 6 — Full operator tool parity (beyond retrieval)

| ID | Story | Acceptance sketch |
|----|-------|-------------------|
| **S6.1** | **As a GM**, I want the agent to use **all the same tools I have in the UI** (statblock generation, NPC workflows, tables, ingestion-adjacent reads, etc.), **so that** I can delegate any prep task in conversation—not only corpus Q&A. | Full operator tool parity is the goal; no artificial "retrieval first, other tools later" cap beyond engineering order. |
| **S6.2** | **As a GM**, I want **every write previewed and explicitly approved by me** before commit, **so that** nothing mutates canon without consent. | **No autonomous writes** in plan mode; two-phase preview → confirm always; autonomous/agent-commit paths are out of scope until benchmarked and trusted. |
| **S6.3** | **As a GM**, I want retrieval, ingestion review, statblock, NPC, and table tasks in the **same thread**, **so that** one prep evening is one conversation arc. | Thread mixes Q&A, tool invocations, and post-ingestion "what changed?" turns; trace distinguishes step kinds. |
| **S6.5** | **As a GM**, I want a **write in thread A to be visible to thread B on the next read**, **so that** parallel prep arcs stay coherent with live canon. | After approved commit (any thread), corpus fingerprint or change event propagates; other threads' agents prefer fresh reads over stale cited excerpts when answering new questions. |
| **S6.4** | **As a GM**, I want agent write/tool behavior **benchmarked before promotion**, **so that** confidence gates precede any loosening of consent rules. | Eval harness + rubric for tool calls and write previews; no production shortcut around measurement. |

---

## Non-goals (from interview)

- **At-table live play** as primary UX for this slice (plan mode first).
- **Operator-facing "live only" backend** in steady state (retrieval ladder folds into trace/inspect under Hermes).
- **Collapsed bar clutter** (snippets, turn counts) — title only.
- **Metadata-only history** on reload — full thread persistence required.

---

## Recommended build sequence (maps stories → tracks)

| Phase | Stories | Current status | Track |
|-------|---------|----------------|-------|
| **P0 — Conversational core** | S1.2, S1.5, S4.1, S3.3 (partial) | Satisfied locally / partial target | Local `/plan` thread/turn core; mature Hermes continuity remains future. |
| **P1 — Trust surface** | S2.1, S2.2, S2.3, S3.1 | Satisfied locally / partial target | Citation cards, source drill-in, trace; cite-or-abstain hardening remains future. |
| **P1.1 — Source reader hardening** | S2.1, S2.5 | Satisfied locally | Hardened read-only source endpoint and allowlisted lookup. |
| **P2 — Thread management** | S1.3, S1.4, S1.6, S1.7, S1.8, S5.2 | Satisfied locally / partial target | Named local threads and long-thread guardrails; app-level persistence waits for R10/P4. |
| **P3 — Smart retrieval and source freshness** | S2.4, S2.5, S2.6, S4.3 (session) | Satisfied locally / partial target | Retrieval freshness and metadata-only corpus change signal; robust re-retrieval policy/fan-out remain future. |
| **P4 / R10 — App hoist** | S5.1, S5.3 | Future / next likely code rung | App-level `AgentInteractionProvider`, cross-surface continuity. |
| **P5 — Tool parity** | S6.1–S6.3 | Future | Statblock, NPC, tables, ingestion-adjacent tools via agent; no autonomous writes. |
| **P6 — Memory integration** | S4.3, S4.4 | Future | Hermes long-term memory policy for non-canon continuity/preferences. |

P0-P3.1 are landed locally in `/plan`; fresh agents should not start from P0. R10/P4 is the next likely code rung, and React `/play` follows as the second-surface proof.

---

## Round 2 decisions (locked)

| Topic | Decision |
|-------|----------|
| **Citation drill-in** | **B — full rendered doc in a side pane** |
| **New thread** | **Auto-suggest after N turns** (N configurable; value TBD); never silent fork |
| **Ingestion + ask** | **Same thread** — ingest Session 23 and "what changed?" continue the active conversation |
| **Tool parity scope** | **All operator tools** — retrieval, statblock, NPC, tables, etc.; no permanent "Q&A only" product ceiling |
| **Writes from agent** | **Never autonomous** — always preview + explicit GM approve; benchmark heavily before any policy relaxation |
| **Thread switching UX** | **B — 2–3 live arcs same day**, switch frequently; **every thread read/write against live corpus in real time** |

---

## Round 2b decisions (locked)

**Workflow pattern:** **B** — often **2–3 parallel prep arcs** in the same stretch (inn prep ↔ statblock ↔ ingestion); switch between them frequently, not only when returning days later.

**Real-time coherence (non-negotiable):**

- **Every thread** can **read** (retrieval, get document, operator tools) and **write** (preview → GM confirm) — no read-only thread tier.
- **Corpus is live:** a write or ingestion completed in thread A must be visible to thread B on the next read/ask — not served from frozen turn snapshots.
- **Conversation history is per-thread; canon is shared.** Thread memory holds Q/A and pointers; answers ground on **current** corpus unless explicitly historical ("what did we think before ingest?").
- **Citation side pane** loads **current** document body inside the **Agent Interaction pane**; stale-turn indicators when source changed since the answer was generated. **Does not** take over or split the plan canvas — extends existing bar/pane design (`PlanAgentInteractionBar`, `plan-agent-pane` in `planSurface.css`).

**Implied architecture (for implementers, not UI prescription):**

- Shared corpus change signal (fingerprint, ingest-complete event, or write-commit hook) fan-out to all open threads.
- Per-thread: Hermes session id, scroll/turn focus, full turn payloads.
- Agent policy: on corpus change event, bias toward re-retrieval for factual questions; thread context still applies for operator intent ("continue the statblock we were editing").
- Future graph-backed retrieval must produce or enrich `SourceUnit` envelopes. Graph summaries are navigation/display material, not source evidence.

---

## Open question — Round 2b (thread switching)

*Resolved — see Round 2b decisions above.*

---

## Round 3 decisions (locked)

| Topic | Decision |
|-------|----------|
| **Trace visibility** | **User toggle** — GM turns trace on/off; not env-only or automatic |
| **Auto-suggest trigger** | **N turns** in active thread (N configurable; pick default during implementation) |
| **Citation / doc drill-in** | **Inside Agent Interaction bar+pane** — build on existing `PlanAgentInteractionBar` design; **no** plan-canvas split/replace/overlay |

**Existing UI to extend (do not redesign from scratch):**

- `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
- `TraceDetailsPanel.tsx`, `ContextSufficiencyPanel.tsx`, `agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/planSurface.css` — `.plan-agent-shell`, `.plan-agent-bar`, `.plan-agent-pane`

---

## Interview status

**Complete.** All Round 1–3 UX decisions captured, and local `/plan` dogfood has landed through P3.1. Next artifact/code slice should point at **R10/P4 provider lift**, not a new P0 restart.

---

## Open questions (implementation-time only)

1. **Default N** for auto-suggest new thread (e.g. 15 vs 25 turns)?
2. **Trace toggle default** on first visit (on for dogfood, off later — or user chooses once)?

---

## Verification hooks (story-level)

- **S1.5 / S2.4:** Two-turn dogfood script (inn → Lysandra) on same Hermes session; trace shows no redundant full retrieval on turn 2 unless agent opts in.
- **S2.1 / S2.5:** Citation click expands **in-pane** corpus reader; plan canvas unchanged.
- **S3.1:** Trace toggle off → trace panels hidden; on → full trace restored.
- **S4.1:** Reload restores full thread, not just question list.
- **S5.1:** Navigate `/plan` → another surface; same thread title and history visible.
- **S1.7 / S1.8:** Two named threads active; write/ingest in thread A → ask factual question in thread B → answer reflects new canon.
- **S2.5:** Open citation on pre-ingest turn after ingest → side pane shows current doc + "source updated" affordance.
- **S2.6:** Stored turn with evidence snapshots → Check current source state → Current / Changed / Unknown / Unavailable shown without returning or persisting source bodies.
- **S6.2 / S6.4:** Write tool invoked → preview diff shown → no commit until GM confirms; benchmark rubric exists before ship.
