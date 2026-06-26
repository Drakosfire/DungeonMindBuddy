# UX Stories — Agent Interaction + Hermes

**Status:** Active design capture with post-P3 implementation status  
**Written:** 2026-06-23  
**Updated:** 2026-06-26  
**Source:** GM interview (plan-mode prep/review)  
**Branch context:** `docs/agent-interaction-post-p3-graph-aligned-reanchor` and forward  
**Related:** `Docs/Design/ANCHOR-agent-interaction-hermes.md`, `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`, `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`

## Design north star

Agent Interaction is the GM's **plan-mode desk companion**: ask campaign questions before session, ingest and review after. Hermes is the default backing agent — conversational, tool-capable, and inspectable when needed. Corpus remains canon; the agent orchestrates retrieval and the same operator tools the UI exposes (statblocks, NPC workflows, tables, etc.), not just Q&A.

Post-P3 status: the local `/plan` dogfood ladder now satisfies the core conversation, citation, named-thread, retrieval-freshness, and corpus-change-signal stories. R10/P4 app-level provider lift, full tool parity, and Hermes long-term memory remain future.

---

## Persona and context

**As a GM in plan mode**, I work at my desk before session (prep) and after session (ingestion + review). I am not optimizing for at-table live combat in this slice — though the bar and active thread should follow me if I change surfaces after the R10 provider lift.

---

## Example journey (acceptance anchor)

This scenario is now partially satisfied locally in `/plan` and becomes end-to-end after R10/P4 provider lift and later tool parity:

1. **Turn 1:** "What is the name of the Inn in Mireward Reach and who owns it, what are its prices and what does it offer?"
   - **Current:** prose answer, citation cards, and in-pane source reader are available.
   - **Still target:** Hermes as steady-state default with mature cite-or-abstain behavior.
2. **Turn 2 (same thread):** "Does the owner know Lysandra? If so how?"
   - **Current:** same-thread follow-up plumbing and retrieval-freshness metadata exist.
   - **Still target:** mature Hermes session continuity and robust agent policy around when to re-retrieve.
3. **Reload browser:** Full local thread returns.
   - **Current:** thread and turn payloads persist locally, including metadata and pointers.
   - **Still target:** app/user scoped provider persistence beyond `/plan`.
4. **Collapsed bar:** Shows thread **title only** — minimal, out of the way.
   - **Current:** named thread titles exist locally.
   - **Still target:** app-level collapsed bar after R10/P4.
5. **Older citation after corpus changes:** stored answer can warn when cited source changed, is unavailable, is unknown, or remains current.
   - **Current:** P3.1 adds explicit Check current source state through `CorpusChangeSignalPanel` and `/api/live/citation-freshness`.

---

## Story implementation status

| Phase | Story cluster | Status after P3.1 |
|-------|---------------|-------------------|
| **P0 — Conversational core** | S1.2, S1.5, S4.1, S3.3 partial | **Satisfied locally / partial target.** Thread/turn model, same-thread follow-up, local persistence, trace toggle, and Hermes session-handle seam exist. Full app/user provider persistence remains future. |
| **P1 — Citation trust surface** | S2.1, S2.2, S2.3, S3.1 | **Satisfied locally / partial target.** Answer-first UI, citation cards, Open source, and in-pane source reader exist. Cite-or-abstain policy remains a quality hardening target. |
| **P1.1 — Source reader hardening** | S2.1, S2.5 safety foundation | **Satisfied locally.** Source endpoint is allowlisted, read-only, tested for unsupported/missing/truncation behavior, and covered in OpenAPI. |
| **P2 — Thread management** | S1.3, S1.4, S1.6, S1.7, S1.8, S5.2 partial | **Satisfied locally / partial target.** Named thread index, create/rename/switch/delete, per-thread active state, and long-thread suggestion exist. Cross-surface continuity remains future. |
| **P3 — Smart retrieval and corpus coherence** | S2.4, S2.5, S6.5 read-side foundation | **Satisfied locally / partial target.** `retrieval_freshness` and explicit corpus source-currentness checks exist. Write/ingest fan-out and tool parity remain future. |
| **P4 / R10 — App hoist** | S5.1, S5.3 | **Future.** Move provider state above `/plan` and preserve pointer-only persistence. |
| **P5 — Tool parity** | S6.1–S6.4 | **Future.** Agent can use operator tools beyond retrieval; writes are preview → GM confirm only. |
| **P6 — Memory integration** | S4.3, S4.4 | **Future.** Hermes long-term memory is non-canon only; campaign facts remain corpus/tool grounded. |

---

## Epics and user stories

### Epic 1 — Plan-mode conversation (Hermes default)

| ID | Story | Acceptance sketch | Status |
|----|-------|-------------------|--------|
| **S1.1** | **As a GM**, I want to ask natural-language prep questions and get prose answers, **so that** I can prep without manually hunting corpus files. | Hermes is the default backend in steady state; no operator-facing "live vs hermes" toggle long term. | **Partial.** `/plan` asks and answers now; steady-state Hermes default remains future hardening. |
| **S1.2** | **As a GM**, I want my **active thread to continue** when I open Agent Interaction, **so that** follow-ups feel like talking to the same assistant. | Default view = active thread + ask box; new thread via explicit action or system auto-suggest. | **Satisfied locally.** |
| **S1.6** | **As a GM**, I want the system to **auto-suggest starting a new thread after N turns**, **so that** long arcs do not become muddy without me noticing. | Suggest, never force; one-click accept or dismiss; dismissal persists per thread. | **Satisfied locally.** |
| **S1.3** | **As a GM**, I want to **name threads**, **so that** I can find "Session 24 inn prep" vs "post-S23 ingestion review" later. | Create/rename thread; title shown in collapsed bar and thread list. | **Satisfied locally.** |
| **S1.4** | **As a GM**, I want **as many threads as I need**, **so that** I can parallelize prep topics without losing context. | Support 2–3 live arcs same day with sensible storage bounds. | **Satisfied locally.** |
| **S1.7** | **As a GM**, I want to **switch between parallel threads quickly** and **resume where I left off**, **so that** same-day multi-topic prep does not feel like losing my place. | Thread switcher surfaces named active arcs; restoring thread state is first-class. | **Satisfied locally.** |
| **S1.8** | **As a GM**, I want **every thread to read and write against live corpus state**, **so that** no thread shows stale canon after another thread ingests or commits. | Reads resolve current corpus; writes preview→confirm; cross-thread invalidation when sources change. | **Partial.** Read-side source-currentness checks exist; write/tool fan-out remains future. |
| **S1.5** | **As a GM**, I want follow-up questions in the same thread to use **conversation history**, **so that** "Does the owner know Lysandra?" does not require repeating the inn context. | Turn N includes prior Q/A in agent context; Hermes session id reused across turns when available. | **Partial.** Same-thread UI plumbing exists; Hermes session continuity remains a seam to harden. |

### Epic 2 — Corpus-grounded answers with rich citations

| ID | Story | Acceptance sketch | Status |
|----|-------|-------------------|--------|
| **S2.1** | **As a GM**, I want answers as **readable prose with deep-linked markdown** to corpus sources, **so that** I trust facts and drill into originals without leaving the agent surface. | Inline/carded citations; click opens current corpus doc inside Agent Interaction pane. | **Satisfied locally.** |
| **S2.2** | **As a GM**, when evidence is **partial**, I want to see **what was found** and whether the answer is expandable, **so that** thin retrieval is honest rather than silent failure. | UI shows admitted evidence summary and retrieval-freshness status. | **Satisfied locally.** |
| **S2.3** | **As a GM**, I want the agent to **cite or abstain** on thin claims, **so that** I am not given confident fiction. | Missing evidence → explicit uncertainty, not filler. | **Partial.** Trust surface exists; agent/skill quality hardening continues. |
| **S2.4** | **As a GM**, I want the agent to **decide when to re-retrieve** vs lean on thread context, **so that** follow-ups are fast and relevant without stale grounding. | Retrieval decision visible in dogfood UI. | **Satisfied locally.** `retrieval_freshness` exists. |
| **S2.5** | **As a GM**, when I open a citation from an older turn, I want the **corpus doc view inside the Agent Interaction pane** to show **current content**, **so that** I am not misled by a snapshot from before ingestion or a write. | Source reader reads live file; stale indicator or refresh affordance when content changed. | **Satisfied locally / partial target.** Current source reader plus explicit corpus-change signal exists. Automated fan-out remains future. |
| **S2.6** | **As a GM**, when I inspect an older answer, I want a compact **corpus change signal**, **so that** I can tell whether cited evidence still matches current source state. | Stored answer can show Current / Changed / Unknown / Unavailable based on metadata-only source checks. | **Satisfied locally.** P3.1 added `CorpusChangeSignalPanel` and `/api/live/citation-freshness`. |

### Epic 3 — Inspectability (dogfood → invisible)

| ID | Story | Acceptance sketch | Status |
|----|-------|-------------------|--------|
| **S3.1** | **As a GM**, I want **trace available when I choose**, **so that** I can audit grounding during dogfood without cluttering normal prep. | User toggle controls trace visibility. | **Satisfied locally.** |
| **S3.2** | **As a GM**, I want trace **off by default once I trust the surface**, **so that** the UI stays calm and citations remain the primary trust layer. | Toggle off hides trace panels; state persists. | **Satisfied locally / default policy can still tune.** |
| **S3.3** | **As a GM**, I want **rich tool/step trace** from Hermes runs, **so that** I can see lookup → get_document → answer, not a single opaque step. | `agent_trace.steps` reflects intermediate tool calls parsed from Hermes session artifacts. | **Partial.** Trace exists; richer Hermes parsing remains future. |

### Epic 4 — Memory policy (explicit layers)

| ID | Story | Acceptance sketch | Status |
|----|-------|-------------------|--------|
| **S4.1** | **As a GM**, I want **thread history persisted across reload**, **so that** I never lose a prep conversation mid-session. | Full local thread: questions, answers, citation pointers, trace ids, freshness metadata. | **Satisfied locally.** App/user provider persistence remains future. |
| **S4.2** | **As a GM**, I want **generous conversation memory** in v1, **so that** the agent feels like a continuous desk partner. | Bounded complete turn payloads; documented cap and eviction policy. | **Partial.** Local storage exists; app-level bounds/policy remain future. |
| **S4.3** | **As a GM**, I want **Hermes session memory integrated** over time, **so that** orchestration state survives across turns while **corpus remains canon via tools**. | Hermes session id continuity first; long-term memory later for non-canon preferences/thread continuity only. | **Future / partial seam.** |
| **S4.4** | **As a GM**, I want a **clear mental model** of what is remembered where, **so that** I know corpus ≠ chat ≠ Hermes ambient memory. | Visible policy indicators and `.hermes.md` rules reflected in product copy. | **Future.** |

**Memory layers (target model):**

| Layer | Contents | Canon? | Persist |
|-------|----------|--------|---------|
| UI thread | Q/A, titles, citation pointers, trace ids, freshness metadata | No (pointers to canon) | Yes, reload; app/user scope after R10 |
| Retrieval proof | Admitted evidence per turn | Evidence only | Per turn in thread |
| Evidence snapshots | Source locators, line ranges, hashes/status metadata | Evidence check metadata only | Per turn, no source bodies |
| Hermes session | Tool loop state, turn context | No | Session id reuse |
| Hermes long-term | Preferences, thread continuity helpers | No for campaign facts | Later integration |
| Corpus | Campaign truth | **Yes** | Corpus tools only |
| Graph memory | Derived semantics, graph IR, reports, shadow retrieval outputs | No by itself | Ontology/taxonomy workstream only; source evidence through `SourceUnit` envelopes |

### Epic 5 — App-level bar (R10) and cross-surface continuity

| ID | Story | Acceptance sketch | Status |
|----|-------|-------------------|--------|
| **S5.1** | **As a GM**, I want the **same active thread** when I move between surfaces (e.g. `/plan` → live), **so that** prep conversation is not trapped on one route. | `AgentInteractionProvider` holds thread state; surfaces publish ambient context only. | **Future / next likely code rung.** |
| **S5.2** | **As a GM**, I want the **collapsed bar to show only the thread title**, **so that** it stays minimal and out of the way. | No answer snippets or noisy turn counts in collapsed state. | **Partial.** Named thread titles exist locally; app-level collapsed bar remains future. |
| **S5.3** | **As a GM**, I want Agent Interaction to **follow me across projects/surfaces** as the user's continuity layer, **so that** it matches the architecture in `ANCHOR-plan-surface-agent-interaction.md`. | R10 lift: bar in `AppChrome`, pointers-only persistence. | **Future / next likely code rung.** |

### Epic 6 — Full operator tool parity (beyond retrieval)

| ID | Story | Acceptance sketch | Status |
|----|-------|-------------------|--------|
| **S6.1** | **As a GM**, I want the agent to use **all the same tools I have in the UI** (statblock generation, NPC workflows, tables, ingestion-adjacent reads, etc.), **so that** I can delegate any prep task in conversation—not only corpus Q&A. | Full operator tool parity is the goal; no artificial "retrieval first, other tools later" cap beyond engineering order. | **Future.** |
| **S6.2** | **As a GM**, I want **every write previewed and explicitly approved by me** before commit, **so that** nothing mutates canon without consent. | No autonomous writes in plan mode; two-phase preview → confirm always. | **Future.** |
| **S6.3** | **As a GM**, I want retrieval, ingestion review, statblock, NPC, and table tasks in the **same thread**, **so that** one prep evening is one conversation arc. | Thread mixes Q&A, tool invocations, and post-ingestion "what changed?" turns. | **Future.** |
| **S6.5** | **As a GM**, I want a **write in thread A to be visible to thread B on the next read**, **so that** parallel prep arcs stay coherent with live canon. | After approved commit, corpus fingerprint or change event propagates; other threads prefer fresh reads. | **Partial.** Read-side explicit source-currentness check exists; write fan-out remains future. |
| **S6.4** | **As a GM**, I want agent write/tool behavior **benchmarked before promotion**, **so that** confidence gates precede any loosening of consent rules. | Eval harness + rubric for tool calls and write previews. | **Future.** |

---

## Non-goals (from interview, still valid)

- **At-table live play** as primary UX for this slice (plan mode first).
- **Operator-facing "live only" backend** in steady state (retrieval ladder folds into trace/inspect under Hermes).
- **Collapsed bar clutter** (snippets, noisy turn counts) — title only.
- **Metadata-only history** as the final user experience — local full thread persistence exists; R10 should preserve pointer-only source/corpus discipline while making continuity app/user scoped.
- **Graph internals in Agent Interaction** — graph outputs must be consumed through source-vocabulary adapters.

---

## Recommended build sequence (maps stories → tracks)

| Phase | Stories | Track | Current status |
|-------|---------|-------|----------------|
| **P0 — Conversational core** | S1.2, S1.5, S4.1, S3.3 partial | Hermes session seam, conversation UI, persistence | Landed locally |
| **P1 — Trust surface** | S2.1, S2.2, S2.3, S3.1 | Citations in prose/cards, source reader, dogfood trace | Landed locally |
| **P1.1 — Source hardening** | S2.1, S2.5 safety | Citation-source API hardening | Landed locally |
| **P2 — Thread management** | S1.3, S1.4, S1.6, S1.7, S1.8, S5.2 partial | Parallel arcs, quick switch + resume, long-thread guardrail | Landed locally |
| **P3 — Smart retrieval / corpus signals** | S2.4, S2.5, S2.6 | Retrieval freshness, citation freshness, corpus-change signals | Landed locally |
| **P4 / R10 — App hoist** | S5.1, S5.3 | App-level provider, cross-surface continuity | **Next likely code rung** |
| **P5 — Tool parity** | S6.1–S6.4 | Statblock, NPC, tables, write previews via agent | Future |
| **P6 — Memory integration** | S4.3, S4.4 | Hermes long-term memory policy | Future |

---

## Round 2 decisions (locked)

| Topic | Decision |
|-------|----------|
| **Citation drill-in** | **B — full rendered/current doc in a side pane** inside Agent Interaction chrome |
| **New thread** | **Auto-suggest after N turns**; never silent fork |
| **Ingestion + ask** | **Same thread** — ingest Session 23 and "what changed?" continue the active conversation |
| **Tool parity scope** | **All operator tools** — retrieval, statblock, NPC, tables, etc.; no permanent "Q&A only" product ceiling |
| **Writes from agent** | **Never autonomous** — always preview + explicit GM approve; benchmark heavily before any policy relaxation |
| **Thread switching UX** | **B — 2–3 live arcs same day**, switch frequently; every thread read/write against live corpus in real time |

---

## Round 2b decisions (locked)

**Workflow pattern:** **B** — often **2–3 parallel prep arcs** in the same stretch (inn prep ↔ statblock ↔ ingestion); switch between them frequently, not only when returning days later.

**Real-time coherence (non-negotiable):**

- **Every thread** can **read** (retrieval, get document, operator tools) and **write** (preview → GM confirm) — no read-only thread tier.
- **Corpus is live:** a write or ingestion completed in thread A must be visible to thread B on the next read/ask — not served from frozen turn snapshots.
- **Conversation history is per-thread; canon is shared.** Thread memory holds Q/A and pointers; answers ground on **current** corpus unless explicitly historical ("what did we think before ingest?").
- **Citation side pane** loads current document body inside the **Agent Interaction pane**; source-change checks use metadata-only snapshots and never store corpus bodies in thread persistence.

**Implied architecture:**

- Shared corpus change signal (fingerprint, ingest-complete event, or write-commit hook) eventually fans out to all open threads.
- Per-thread: Hermes session id, scroll/turn focus, bounded complete turn payloads, citation/freshness metadata.
- Agent policy: on corpus change event, bias toward re-retrieval for factual questions; thread context still applies for operator intent ("continue the statblock we were editing").
- Graph-backed retrieval, when introduced, must produce/enrich source-vocabulary envelopes and cannot promote graph summaries as evidence.

---

## Round 3 decisions (locked)

| Topic | Decision |
|-------|----------|
| **Trace visibility** | **User toggle** — GM turns trace on/off; not env-only or automatic |
| **Auto-suggest trigger** | **N turns** in active thread (N configurable; pick default during implementation) |
| **Citation / doc drill-in** | **Inside Agent Interaction bar+pane** — build on existing `PlanAgentInteractionBar` design; no plan-canvas split/replace/overlay |
| **Corpus change signal** | **Explicit source-currentness check on stored turns** — metadata-only Current / Changed / Unknown / Unavailable signal |

**Existing UI to extend (do not redesign from scratch):**

- `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/components/RetrievalFreshnessPanel.tsx`
- `apps/live-control-ui/src/planSurface/components/CorpusChangeSignalPanel.tsx`
- `TraceDetailsPanel.tsx`, `ContextSufficiencyPanel.tsx`
- `apps/live-control-ui/src/planSurface/planSurface.css` — `.plan-agent-shell`, `.plan-agent-bar`, `.plan-agent-pane`

---

## Interview status

**Complete.** All Round 1–3 UX decisions captured. P0-P3.1 have now been implemented locally in `/plan`. Next artifact should be a scoped **R10/P4 provider-lift handoff** unless explicitly waived.

---

## Open questions (implementation-time only)

1. **Default N** for auto-suggest new thread after P2.1 dogfood.
2. **Trace toggle default** on first visit after citations/freshness feel trustworthy.
3. **R10 persistence boundary:** exact provider storage bounds and project/user scoping.
4. **Source freshness fan-out:** when write/ingest tooling lands, whether freshness updates should be event-driven, on-demand, or both.

---

## Verification hooks (story-level)

- **S1.5 / S2.4:** Two-turn dogfood script (inn → Lysandra) in same thread; retrieval-freshness panel states why retrieval was fresh/blended/thread/insufficient.
- **S2.1 / S2.5:** Citation click expands in-pane corpus reader; plan canvas unchanged.
- **S2.6:** Stored turn with evidence snapshots → Check current source state → Current / Changed / Unknown / Unavailable shown without source bodies.
- **S3.1:** Trace toggle off → trace panels hidden; on → full trace restored.
- **S4.1:** Reload restores local full thread payloads and pointers, not just question list.
- **S5.1:** Future R10 check: navigate `/plan` → another surface; same thread title and history visible.
- **S1.7 / S1.8:** Two named threads active; source reader resets on switch; factual read can check current corpus state.
- **S6.2 / S6.4:** Future tool parity check: write tool invoked → preview diff shown → no commit until GM confirms; benchmark rubric exists before ship.
