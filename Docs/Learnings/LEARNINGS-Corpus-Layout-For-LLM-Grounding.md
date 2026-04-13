# Learnings: Corpus Layout for LLM-Grounded Planning

**Date:** April 2026
**Context:** Lysandra vertical-slice benchmark — restructuring NPC corpus files so that a planner model (gpt-5.4-mini via Responses API) autonomously navigates to the right files.
**Prescriptive rule:** `.cursor/rules/corpus-layout-conventions.mdc`

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
