# Learnings: Corpus Layout for LLM-Grounded Planning

**Date:** April 2026
**Context:** Lysandra vertical-slice benchmark — restructuring NPC corpus files so that a planner model (gpt-5.4-mini via Responses API) autonomously navigates to the right files.
**Prescriptive rule:** `.cursor/rules/corpus-layout-conventions.mdc`  
**NPC hub template (Lysandra-shaped package):** `Docs/CONVENTION-NPC-Hub-Package.md`

---

## Background

DungeonMindBuddy's planner loop gives the model a **corpus tree** (file listing) and a `read_corpus_file` tool. The model must decide which files to open, in what order, to answer a GM's question grounded in campaign lore. The Lysandra vertical-slice eval gates require the model to open specific files (statblock, dossier, session recap) without being told which ones.

Starting state: files scattered across flat directories (`NPC Dossier/`, `NPCs/`, `Session Recaps/`). No indexing. The model guessed from filenames in the tree.

---

## Lesson 1 — Hub folders with README indexes

### What failed

Lysandra's statblock was in `Longmont Campaign/NPCs/` (flat, alongside other NPCs). Her dossier was in `Longmont Campaign/Campaign 2/NPC Dossier/`. The model had to infer from the tree that these two files related to the same entity and decide which to open first. It frequently skipped the statblock or opened a large campaign-notes ledger instead.

### What worked

Grouping all entity files into `captain_lysandra_ironveil/` with a `README.md` as a small, cheap-to-read index. The README costs ~1,600–3,000 chars to read (vs 7,000+ for a dossier or recap). The model reads the README first and gets a map to everything else.

### Principle

**One folder per entity. One README per folder. The README is the cheapest file that maps to every other file the model needs.**

---

## Lesson 2 — Suggested reads must be ordered, full-path, and annotated

### What failed

Early README drafts listed files by name only (`character_seed.md`, `statblock_cr2.md`). The model sometimes resolved these relative to the wrong folder — e.g. looking for `captain_lysandra_ironveil_statblock_cr2.md` under the C2 NPC folder when it only existed under the Mirathorn folder. Error returned by `read_corpus_file`, model answered without the statblock data.

### What worked

Numbered **Suggested reads (in order)** with **full corpus-relative paths** and a one-line annotation per item. The model copies the path exactly into the tool call. The ordering (most universally useful → situationally relevant) prevents the model from front-loading expensive, low-signal files.

### Principle

**Every path in a README must be the exact string the model passes to `read_corpus_file`. Annotate each with why it matters for that position in the list.**

---

## Lesson 3 — Mechanical sheets need an explicit priority table

### What failed

When the README mentioned "CR 2 statblock" in prose, the model sometimes treated the README's text as sufficient and skipped actually opening the `.md` file. It would answer "she's CR 2" without having read AC, HP, attacks, or saves from the statblock itself.

### What worked

A **Mechanical sheets (priority — highest first)** table in the README. Columns: Priority rank, Path, Role. Combined with a planner instruction rule: "you must `read_corpus_file` on the highest-priority statblock before answering CR/HP/AC/saves questions."

### Evidence

- Run without mandatory-read rule: model cited statblock path in answer but never opened it. Gate failed.
- Run with mandatory-read rule: model opened `captain_lysandra_ironveil_statblock_cr2.md` in round 2. Gate passed.

### Principle

**Separate "knowing a file exists" from "having read its contents." For mechanical data, README prose is not a substitute for reading the actual file. Encode this in the planner instructions.**

---

## Lesson 4 — Never embed globs or wildcards in paths

### What failed

A README priority-table row had: `captain_lysandra_ironveil_statblock_c2_*.md`. The model passed this literal string to `read_corpus_file`. The tool returned an error ("path must be a markdown file relative to the corpus root"). The model then answered CR/HP questions without the statblock.

### What worked

Replacing the glob with prose: "any `.md` whose name starts with `captain_lysandra_ironveil_statblock_c2_`". Plus a planner instruction: "never pass shell globs to `read_corpus_file`."

### Principle

**If a README covers a family of possible filenames, describe the pattern in prose and tell the model to resolve the exact path from the corpus tree. Never put `*` or `?` in a string the model might paste into a tool call.**

---

## Lesson 5 — No hardcoded "default" recap sessions

### What failed

Both Lysandra READMEs listed `Session 18 - Recap.md` as item 5 ("example recent C2 recap anchor"). Every run, the model opened Session 18 verbatim. When Session 19 was added to the corpus, the model still opened 18 because the README told it to — it was following instructions, not reasoning about recency.

### What worked

Replacing the pinned path with a **Session recaps (no pinned default)** section: "use the corpus tree, pick the file whose filename contains the largest session number." Plus a planner instruction: "for most recent recap, compare session numbers in filenames." First run after the change: model opened **Session 19**.

### Evidence

- Before: model opened Session 18 in 100% of runs (n=4). Session 19 existed on disk.
- After: model opened Session 19 on first run (largest number in tree).

### Principle

**Never hardcode a session number as a default in a README. Recency should be derived from the tree at query time, not baked into a static file. The model can count; it just needs the rule.**

---

## Lesson 6 — Setting vs table: two hubs, cross-linked

### What failed

All Lysandra files in one flat folder mixed world-bible facts (Mirathorn seed, setting-level statblock) with campaign-specific facts (C2 dossier, C2 timeline, played-session beats). No signal about which facts were "world-level truth" vs "table-level continuity."

### What worked

Two hub folders:
- **Mirathorn hub** (`Elderwyld/.../Mirathorn/NPCs/captain_lysandra_ironveil/`): world-bible seed, canonical CR 2 statblock export.
- **C2 hub** (`Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/`): table dossier, timeline, campaign-specific statblock overrides.

Each README cross-links to the other with full paths. Each defines its own priority table for "which statblock is canonical from this hub's perspective."

### Principle

**When an entity spans a world-bible layer and a campaign layer, give it two hub folders. Cross-link them. Let each hub define priority from its own perspective.**

---

## Lesson 7 — Planner instructions must encode navigation policy

### What failed

Perfect README structure alone was not enough. The model sometimes:
- Opened the dossier and recaps but skipped the statblock (README said to read it, model decided it wasn't needed)
- Tried to answer CR/HP from README prose alone
- Opened Session 18 because it was hardcoded

### What worked

Explicit rules in `src/prompts/corpus_session_planner.py`:
1. **README first**: when a hub folder has a `README.md`, prefer opening it in the first read batch.
2. **Mandatory statblock read**: if a README lists `*_statblock_*.md` for the entity in scope, you must `read_corpus_file` on it before answering mechanical questions.
3. **No globs**: use exact paths.
4. **Recency from the tree**: compare session numbers in filenames.

### Principle

**Corpus structure is necessary but not sufficient. The planner system prompt must encode the navigation policy that the corpus structure assumes. README breadcrumbs + planner rules = reliable navigation.**

---

## Lesson 8 — Fingerprint hygiene after corpus edits

### What failed

After adding README files to the corpus, the `step0_environment.json` `expected_fingerprint` was stale. Eval tests failed with "fingerprint mismatch" — a false alarm that obscured whether the planner behavior actually changed.

### Process

After every corpus content edit:
1. Recompute fingerprint.
2. Update `expected_fingerprint` in gold.
3. Run `test_lysandra_vertical_slice_step0.py` to confirm.

### Principle

**Corpus fingerprint is a blake3 hash of all markdown under the corpus root. Every edit — even whitespace — invalidates it. Treat fingerprint updates as part of the corpus edit, not a separate step.**

---

## Lesson 9 — Stochastic compliance needs multiple runs

### What failed

A single passing run after a corpus change was celebrated as "fixed." The next run failed because the model made a different stochastic choice (e.g. invented a C2-local statblock path instead of using the Mirathorn one).

### What worked

Running the trace 2–4 times before declaring a change robust. Observing which gate fails and whether the failure mode is the same or different across runs.

### Principle

**Autonomous planner evals are stochastic. A gate that passes 1/1 might fail 2/5. When tightening corpus layout or planner instructions, run the trace multiple times. The eval infrastructure should eventually track pass rates across N runs, not just single-shot pass/fail.**

---

## Lesson 10 — Clarification belongs in the turn envelope, not in a tool

### What failed

We added a `propose_clarification` planner tool so the model could surface "I need more information before I can plan." The tool was easy to write but hard to govern:

- The model called it on questions that already had enough corpus context, just to be safe.
- The model also skipped it when it should have used it (silently guessing instead).
- Eval gates had to special-case both directions (`must_call_propose_clarification`, `must_not_call_propose_clarification`) and the failure modes were noisy because the tool was a separate response branch.

### What worked

Removing the tool entirely (`88f02b6 Planner: JSON-only clarification; remove propose_clarification`). Clarification is now a structured field of the turn envelope: the model emits one JSON object per turn with `needs_clarification: true|false` plus a `clarification_question` string. Gates inspect a single object instead of branching on which tool happened to be called.

### Principle

**Prefer a structured field in the turn envelope to a dedicated tool when the only thing the "tool" does is surface a string of intent. Tools are for side effects (read corpus, attach context, write file); decisions belong in the JSON the model is already required to produce. Tests that need to assert legacy traces won't mis-fire should use `propose_clarification` only as a *negative* assertion (`assert "propose_clarification" not in tool_names`) or in legacy-tolerance helpers — never re-introduce the tool to "support older runs."**

---

## Lesson 11 — Some corpus files are character/world bible; the writer must refuse them

### What failed

The first sketch of a corpus writer treated all `.md` under the corpus root as fair game. Imagining a "session ended; update the dossier with what changed" flow led to a writer that could overwrite or append to `*_character_dossier.md`, `character_seed.md`, and `*_statblock*.md`. Three failure modes immediately surfaced in design review:

- **Statblock drift** — mechanical numbers were authored once (RulesIngestion export or hand-tuned sheet); LLM appends would silently rewrite AC/HP/CR baselines that other tools (`generate_statblock`, downstream pipelines) treat as canonical.
- **Voice drift** — dossiers are *character bibles* whose tone and bullet structure other prompts depend on; per-session edits accumulate into a dossier that no longer matches what the GM authored.
- **Time-confused canon** — "X is now Y" lines added directly to a dossier mix world-bible truths with table-state continuity. The reader (model or human) loses the boundary between "who they are" and "what happened to them in session N."

### What worked

A **server-side allowlist in `src/agent/corpus_writer.py`** that *denies* the basenames `*_character_dossier.md`, `character_seed.md`, `*_statblock*.md` regardless of mode, even when corpus writes are otherwise enabled. State changes from a session land in:

1. The **new recap file** (`Session Recaps/Session <N> - <slug>.md`) — long-form prose owns the "what happened."
2. The NPC's **`timeline.md` row** — one-line beat + recap pointer; the chronology grid stays current without rewriting the dossier.

The dossier and statblock are explicitly the **static** bibles; their update path is human, intentional, and out-of-band relative to a session writeup.

### Principle

**Every write tool needs an allowlist of *what it may touch* and a denylist of *what it must never touch*. Encode both in code (regex / basename match) and in docs (cursor rule + skill). Treat the denied set as immutable from any LLM's perspective: rejection is the correct answer, not a "feature gap." If session state needs to land somewhere, it lands in a *new* file (recap) or a *pointer* file (timeline), never in the bible.**

---

## Lesson 12 — Two-phase commit (`dry_run` → `confirm_token` → commit) for LLM writes

### What failed

The naive "model calls a write tool, file changes" loop fails three ways even with a perfect allowlist:

- The operator has no chance to read the prose before it lands on disk.
- The model has no way to recover if the file changed between its read and its write (concurrent edits, partial GM cleanup).
- A vague "looks good" reply from the operator can't be distinguished from explicit consent.

### What worked

`write_corpus_file` and `append_timeline_row` both implement a strict two-phase commit:

1. **Phase 1 — preview:** Tool is called with `dry_run=true` (the default). It builds the proposed content, computes a `confirm_token` = `blake3(path || mode || new_content || file_state_token(target))`, and returns `{phase: "preview", diff: <unified>, confirm_token: <hex>, ...}`. No bytes hit disk.
2. **Operator review:** The skill is required to surface the diff to the GM in chat as a fenced block and wait for an explicit `apply` (or `apply <path>` for per-file approval). Replies like "sure" or "looks good" are treated as not-yet-approved.
3. **Phase 2 — commit:** The tool is called again with `dry_run=false` and the `confirm_token` from phase 1. The token is recomputed; if the file changed in the meantime (its state-token shifted), the token mismatches and the commit is aborted with a `stale confirm_token` error. Otherwise the bytes are written and a `fingerprint_reminder` is included in the response.

This shape means a stale token is *informative* (someone or something edited the file under us; re-preview), not a footgun.

### Principle

**LLM-driven file mutations should never be one-shot. Use a two-phase commit where phase 1 returns a preview + a token bound to (path, mode, content, file-state). The operator must paste back the token (via an explicit `apply` reply that the skill turns into the second tool call). Bind the token to the file's current state so concurrent edits abort instead of silently overwriting. Generalize this pattern to every future write tool — config writes, corpus writes, eval-gold writes — not just session recaps.**

---

## Lesson 13 — Benchmarking the recap writer is in the backlog (and that's OK)

### Context

After the writer landed, we explored how to benchmark the `recap-write` skill **before** the next real raw-recap arrives. Four options were considered:

| Option | What it measures | Cost | Verdict |
|--------|------------------|------|---------|
| A. Structural gates (frontmatter shape, file in right folder, timeline row well-formed) | Mechanical correctness of the artifact | Low | Cheap and worth doing once we have one real recap to point at. |
| B. Time-rewind snapshot (delete Session N from corpus, feed prior raw notes back, compare to original) | End-to-end prose quality + path correctness | Medium (needs raw notes + golden recap) | Strong, but **we don't have the raw notes paired with the recaps** for sessions already in corpus. |
| C. Compress-then-expand (LLM summarizes existing recap into "synthetic raw notes," then we ask the skill to recover the recap) | Round-trip fidelity | Medium | Risk: the compressor's choices about what to omit silently shape what the expander is even *capable* of producing. We'd be benchmarking the compressor as much as the writer. |
| D. Mini-campaign (write a short toy campaign with paired notes ↔ recaps explicitly for the suite) | Same as B but with controlled inputs | High up-front, low recurring | Probably the right end state, but premature before we have one real raw-notes/recap pair to anchor expectations. |

### Decision (April 2026)

**Punt all four options to backlog** until the next real session writeup arrives. With one real raw → recap pair in hand, Option A becomes free, Option B becomes possible against a known-good target, and we get evidence about whether Options C/D are even worth building. Trying to benchmark in advance risks measuring our own assumptions.

The detailed option write-up lives in `Docs/Plans/BACKLOG-session-recap-benchmarking.md`.

### Principle

**Don't build a benchmark for a skill before you have at least one real input/output pair to anchor it.** Synthetic inputs + synthetic golds tell you whether the skill is self-consistent, not whether it does what humans actually want. When real data is on a near horizon (next session), waiting is cheaper than guessing.

---

## Anti-pattern quick reference

| Anti-pattern | Consequence | Fix |
|---|---|---|
| Flat NPC directories | Model can't associate files for same entity | Hub folder per entity with README |
| Filename-only paths in README | Model resolves to wrong folder | Full corpus-relative paths |
| Glob/wildcard in README path | Model pastes literal `*` into tool call | Prose pattern + "resolve from tree" |
| Hardcoded "Session 18" default | Model never discovers Session 19+ | "No pinned default" + largest-number rule |
| README says "CR 2" without mandatory-read rule | Model skips statblock file, answers from prose | Planner instruction: must read `*_statblock_*.md` |
| Mixed setting + campaign files in one folder | Ambiguous priority, wrong statblock opened | Two hubs, cross-linked, separate priority tables |
| Forgetting fingerprint update after corpus edit | Stale eval gold, false test failures | Recompute + update `expected_fingerprint` immediately |
| Declaring victory after 1 passing run | Stochastic regression on next attempt | Multiple runs before declaring robust |
| Modeling clarification as a tool call | Noisy gates, model uses or skips it stochastically | JSON `needs_clarification` field in the turn envelope |
| Letting a writer touch dossier / seed / statblock | Voice + mechanical drift; world-bible erosion | Server-side denylist (`*_character_dossier.md`, `character_seed.md`, `*_statblock*.md`) |
| One-shot LLM writes (no preview) | No operator review; can't detect concurrent edits | Two-phase commit with `confirm_token` bound to file state |
| Building a benchmark before any real input/output pair exists | Measures the synthesizer, not the skill | Wait for one real example, then add Option A first |

---

## README template (copy-paste for new entity hubs)

```markdown
# {Entity Display Name} — {Hub Context} ({setting seed | campaign table})

## Suggested reads (in order)

Use `read_corpus_file` with these paths **after** this README (corpus root = `eldyrwild-markdown/`):

1. `{full/path/to/primary_file.md}` — {one-line annotation}.
2. `{full/path/to/secondary_file.md}` — {annotation}.

## Session recaps (no pinned default)

Do **not** assume a fixed recap file. Under `{campaign}/Session Recaps/`, use the
**corpus tree** to see which `.md` recaps exist. For **latest played events**, open
the recap whose filename contains the **largest session number**. If `timeline.md`
names specific recaps for a beat, prefer those.

## Mechanical sheets (priority — highest first)

| Priority | Path | Role |
|----------|------|------|
| **1 — canonical** | `{path}` | Default authoritative sheet. |
| **2 — override** | In **this folder**: any `.md` starting with `{slug}_statblock_{campaign}_` | Most current when present. |
| **3 — archive** | Other `*_statblock_*.md` | Older drafts — cite only on request. |

## Cross-references

- **{Other hub}:** `{full/path/to/other/hub/README.md}`
```

---

*Last updated: April 2026. Update when new corpus-layout patterns emerge or existing ones prove insufficient.*
