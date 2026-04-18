---
name: session-summary-from-notes
description: Take pasted raw session notes / GM scratch / transcript and produce a canonical `Session N - Recap.md` (frontmatter + de-duplicated GM prose, voice preserved verbatim) plus a review surface of proposed organizational follow-ups (NPC timeline appends, new-hub proposals, plot-artifact placements, prep ↔ recap pointers). Never edits dossier/seed/statblock. Two-phase write with operator approval before any disk change.
---

# Session summary from notes (corpus-grounded structurer + extractor)

Use this skill when the GM **pastes raw session notes, GM scratch, or a recording transcript** into chat and asks for a canonical recap on disk plus the related continuity updates. The skill is a **structurer and extractor**, not a composer:

- The GM's prose is already in the right voice. Don't rewrite, restructure, or "improve" it. Identity transform on the body after de-duplication.
- The skill mechanically wraps the prose in canonical frontmatter + H1, removes obvious quality issues (duplicate paragraphs, title-line repetition), and writes the recap.
- The skill *also* extracts a **review surface** of proposed organizational follow-ups (timeline rows, new hubs, plot artifacts, prep-doc cross-links) for the GM to approve **individually**. These are LLM-judgment calls, not mechanical writes.

The skill produces, in order:

1. A canonical `Session <N> - Recap.md` (frontmatter + H1 + GM prose verbatim, de-duplicated). **Mechanical.**
2. A **review surface** of proposed follow-ups (zero or more): timeline-row appends, new NPC hub proposals, plot-artifact placement proposals, prep ↔ recap pointer proposals. **Judgment — GM approves each separately.**

**Never written by this skill:** `*_character_dossier.md`, `character_seed.md`, `*_statblock*.md`. They are the static character/world bible. If a session changed an NPC's status, it lives in the recap prose; the timeline row + recap link carry it forward.

## Required runtime

The planner must be launched with corpus writes enabled:

- **CLI:** `dmb plan --allow-corpus-writes`
- **Or env:** `DUNGEONMIND_PLANNER_ALLOW_WRITES=1`

When enabled, `write_corpus_file` and `append_timeline_row` are registered as planner tools. Without them this skill stops at the draft step and surfaces the recap + review surface only — no commits.

## Tools

| Tool | Role |
|------|------|
| `read_corpus_file` | Discovery: hub READMEs, current `timeline.md`, last 2–3 recaps for shape-matching, **and any `Session Prep/session_<N>_*.md` companion file**. **Skip** dossier/seed/statblock — they are not consulted by this skill. |
| `write_corpus_file` | Two-phase create of the new recap (`mode='create'`). Allowlist enforced server-side: only `**/Session Recaps/Session NN - <slug>.md` paths accept create. |
| `append_timeline_row` | Two-phase append of one row to `NPCs/<slug>/timeline.md`. Preferred over raw `write_corpus_file` so the table stays well-formed. |

## Two-phase commit (strict)

For every write tool call:

1. First call: `dry_run=true` (default). Tool returns `{phase: "preview", confirm_token, diff, …}`.
2. **Surface the diff to the GM in chat** as a fenced block; explain what will change in plain English.
3. Wait for the GM to type **`apply`** (or `apply <path>` to commit one at a time). Do not commit on "looks good," "sure," or any non-explicit reply.
4. Second call: same arguments + `dry_run=false` + the **exact** `confirm_token` from step 1.
5. If the tool replies with `stale confirm_token`, re-run dry-run (the file or content drifted) and present the new diff before retrying.

If the GM rejects a draft, regenerate it; do not commit a stale token after edits.

## Protocol

### 1. Identify the campaign hub

Default to the campaign whose `Session Recaps/` folder contains the most recent `Session NN` filename. If the notes plausibly belong to another campaign (different party / table mentioned), ask the GM in one sentence which hub. Common targets:

- `Longmont Campaign/Campaign 2/Session Recaps/`
- `Longmont Campaign/Campaign 1/Session Recaps/`

### 2. Pick the next session number

List the chosen `Session Recaps/` directory and compute:

```
next_session_number = max(parse_int_after("Session ") for name in dir) + 1
```

If the GM's notes explicitly specify a number that doesn't match `next + 0/1`, ask for confirmation in one sentence before proceeding.

### 3. Survey the canonical shape from the last 2–3 recaps

Read the most recent recap files with `read_corpus_file` and confirm:

- **Frontmatter field set** (this is invariant across the surveyed recaps): `title`, `document_class: play`, `canon_layer: campaign`, `campaign_id`, `temporal_scope: session_specific`, `session: N`, `origin_session: N`, `last_updated_session: N`, `source_class: observed_session_recap`. Reproduce exactly with `N` substituted.
- **Title styling.** Existing recaps may be **inconsistent** (some have trailing colons, descriptive subtitles, omitted H1, body-duplicated titles). Choose the **cleanest exemplar's form** as canonical (typically `title: "Session <N> - Recap"` and `# Session <N> Recap`). Do **not** replicate prior typos.
- **Body structure.** Canonical recaps are a single H1 followed by interleaved-thread prose paragraphs separated by blank lines. **No internal section headings, no numbered TLDR, no checklists, no dialogue speaker labels.** If the surveyed recaps don't have a TLDR, the new one doesn't get one either.
- **Voice.** The GM's prose voice is already correct. Mirror length and present-tense beat-by-beat shape; do not rewrite it.

### 4. Locate companion documents

Check `<campaign>/Session Prep/` for any file whose name encodes the same session number (e.g. `session_<N>_*.md`). If one exists:

- Read it. It often gives **surnames the recap omits**, **planned beats that may or may not have fired**, and **NPC character notes** the recap won't repeat.
- Surface this to the GM as part of the review surface (step 7): propose a bidirectional pointer between the recap and the prep doc, especially when the prep predicted beats that didn't land in actual play.
- Do **not** silently merge prep-doc material into the recap. The recap is what happened at the table; the prep doc is what the GM had ready. They can disagree, and that disagreement is itself continuity.

### 5. Build the canonical recap (mechanical)

Operate on the raw notes:

1. **Strip leading title line.** If the notes' first non-blank line is a plain-text version of the title (e.g. `Session 20 Recap`), drop it — the H1 will replace it. Do not let the title duplicate into the body prose.
2. **Detect duplicate paragraphs.** Split the body into paragraphs robustly: break on blank lines **and** on isolated single newlines that sit between two sentence-complete blocks. (Raw GM notes are inconsistent about whether paragraphs are separated by `\n\n` or just `\n`; a naive blank-line-only split can glue two paragraphs together and hide a duplicate elsewhere in the file.) After splitting, if any two paragraphs are byte-for-byte (or near-identical after whitespace normalization) duplicates, **surface them to the GM with source line numbers** and recommend removing one (almost always correct). Do not silently strip — the GM should see the catch. Wait for explicit confirmation, then remove.
3. **Preserve all other prose verbatim.** No grammar fixes, no quote normalization, no spelling corrections (e.g. `Karsemine`/`Karesmine` variation stays). The GM voice is the canon.
4. **Assemble the file:** YAML frontmatter (the 8 fields from step 3) → `---` → `# Session <N> Recap` → blank line → de-duplicated body paragraphs → trailing newline.

### 6. Identify affected NPC slugs (for the review surface)

For every NPC the notes name (canonical name, alias, or clear description), check `NPCs/<slug>/README.md` to see if a hub already exists. Categorize:

- **Existing hub, recurring NPC:** propose a `timeline.md` row append (step 7).
- **No hub, first appearance, looks like a power-center / recurring character** (named, has a defined role, ended unresolved, etc.): propose **new-hub creation** (step 7). Do *not* create the hub silently.
- **No hub, walk-on / one-scene NPC:** log explicitly in the review surface as **"considered, no hub proposed, reason: …"** so the GM sees the call and can override.
- **PC:** never gets NPC-hub treatment. Skip silently.

If a slug cannot be resolved confidently from the manifest, **ask one disambiguation question** instead of guessing.

### 7. Emit the review surface (no writes yet)

In one chat turn, after presenting the canonical recap diff, emit a structured **review surface** containing zero or more of the following items, each independently approvable:

1. **Recap create.** The `write_corpus_file` dry-run preview for the new `Session <N> - Recap.md`.
2. **Timeline row appends.** One `append_timeline_row` dry-run preview per affected NPC with an existing hub. Match the **prose richness of the existing rows** — these are not always one-line beats; some hubs use multi-clause prose with bold/italic emphasis. Mirror the local convention.
3. **New-hub proposals.** For each first-appearance NPC who looks hub-worthy: state proposed slug, proposed location (campaign-hub vs setting-hub vs both — see `Docs/CONVENTION-NPC-Hub-Package.md`), and proposed initial files (README + dossier from the prep doc + timeline). **Do not call `write_corpus_file` for these yet** — the writer's allowlist currently only covers Session Recaps create and NPCs timeline/README append; new-hub creation is a multi-file decision the GM should sanction explicitly.
4. **Plot-artifact placement proposals.** For each major new in-world object (a map, a blueprint, a relic, a named location not previously known): propose 2–3 placement options (e.g. `Locations/<name>.md` in the campaign hub, escalation to a setting-hub `Elderwyld/<region>/Locations/`, a `Plot Artifacts/` folder if one exists). The GM picks.
5. **Prep ↔ recap pointer proposal.** If a companion prep doc exists (step 4): propose appending one bidirectional pointer line to each. **Note** that prep-doc paths are outside the writer allowlist; this is hand-edit territory unless/until the allowlist extends.
6. **NPCs explicitly considered and dismissed.** A short table of named NPCs with no hub proposal and the reason. This is the audit trail; it lets the GM override calls the model didn't make.

Surface each item as a fenced block (the recap), a fenced diff (timeline rows), or a labeled bullet (proposals), with `confirm_token` clearly labeled where applicable. Then ask the GM to type `apply <item-id>` per item. Do not commit anything until each item is independently approved.

### 8. Commit on `apply`

For each approved item with a writer-allowed path, call the matching tool with `dry_run=false` and the exact `confirm_token`. **Stop on first error** and report it; do not retry a stale token without a fresh dry-run.

For approved items outside the writer allowlist (new hubs, prep-doc pointers, plot-artifact files), state plainly that the writer cannot commit them and either:

- Hand the GM the proposed file contents to paste/save manually, OR
- Note them as a follow-up that requires extending the writer allowlist.

### 9. Report fingerprint and follow-ups

After commits, state plainly:

- The new corpus fingerprint (the writer also includes a `fingerprint_reminder` in its response).
- One next step for the GM: update `evals/lysandra_vertical_slice/gold/step0_environment.json` → `expected_fingerprint`, then run `uv run pytest tests/test_lysandra_vertical_slice_step0.py`.

## Anti-patterns

- Committing a write without showing the diff and waiting for explicit `apply`.
- Rewriting, "tidying," or grammar-fixing the GM's prose. Identity transform after de-dup; that's it.
- Emitting a numbered TLDR or section headings the surveyed recaps don't use. The recap is one H1 followed by interleaved prose; nothing more.
- Replicating a typo from a prior recap (trailing colons in titles, body-duplicated titles) just because it's "consistent." Choose the cleanest exemplar's form.
- Silently stripping a duplicate paragraph. Surface the catch to the GM with line numbers; let them confirm.
- Silently merging prep-doc material into the recap. The two documents are siblings, not parent/child.
- Editing a dossier, seed, or statblock "while we're in there." The tool will reject; do not work around it by rewriting the recap to embed mechanical numbers.
- Auto-creating a new NPC hub for every named character. Walk-on NPCs do not get hubs; surface the call as part of the review surface.
- Inventing a session number when the recaps folder already implies the next one.
- Writing a "files used" section into the recap. The recap is in-world prose; tool traces capture sources.

## See also (sibling skills)

- **`npc-power-increase`** — read-only, mechanics-aware. If the GM's notes describe a power-tier shift (an NPC rose to a new threat level mid-session), summarize *what happened in fiction* in this skill's recap, then route the **mechanical follow-up** ("what should her sheet look like at the new tier?") to `npc-power-increase` in a separate turn. That skill attaches the canonical statblock via `load_context_markdown` and writes power-rise prose; it does **not** edit the statblock either. The two skills are complementary, never simultaneous: if you find yourself wanting to call both in one turn, finish the recap first, then start the upgrade conversation.

## Related repo wiring

- Writer module: `src/agent/corpus_writer.py` (allowlist + two-phase commit + timeline mutator).
- Planner registration (gated by `allow_corpus_writes`): `src/agent/planner.py`.
- Prompt addendum that documents the contract to the model: `_WRITE_TOOLS_ADDENDUM` in `src/prompts/corpus_session_planner.py`.
- Hub-format reference (timeline columns, README sections, dossier boundary): `Docs/CONVENTION-NPC-Hub-Package.md`.
- Lessons behind the dossier-immutability and two-phase-commit choices: `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md` Lessons 11 and 12.
- **Manual-ingest reference (this skill's first real artifact):** `Docs/Plans/PROCESSING-NOTES-Session-20-Manual-Ingest.md` — the deterministic-vs-judgment bucket analysis that drove this skill's structurer/extractor reframing. Read before extending the protocol or adding new ingestion tools.
