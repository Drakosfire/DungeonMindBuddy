---
name: session-summary-from-notes
description: Turn pasted raw session notes/transcript into a numbered next-`Session N` recap file plus appended NPC `timeline.md` rows; never edits dossier/seed/statblock; two-phase write with operator approval before any disk change.
---

# Session summary from notes (corpus-grounded write)

Use this skill when the GM **pastes raw session notes, GM scratch, or a recording transcript** into chat and asks for a **numbered session summary** with **related NPC docs updated**. The skill produces three things, in order:

1. A new `Session <N> - <slug>.md` recap file in the campaign’s `Session Recaps/` folder.
2. One appended row in each affected NPC’s campaign-hub `timeline.md`, pointing at the new recap.
3. (Optional) Append-only additions to a campaign-hub `README.md` *only* if a genuinely new pin is implied (rare).

**Never written by this skill:** `*_character_dossier.md`, `character_seed.md`, `*_statblock*.md`. They are the static character/world bible. If a session changed an NPC’s status, capture the change in the **recap prose** and let the timeline row + recap link carry it forward.

## Required runtime

The planner must be launched with corpus writes enabled:

- **CLI:** `dmb plan --allow-corpus-writes`
- **Or env:** `DUNGEONMIND_PLANNER_ALLOW_WRITES=1`

When enabled, `write_corpus_file` and `append_timeline_row` are registered as planner tools. Without them this skill stops at step 4 and surfaces the drafts only — no commits.

## Tools

| Tool | Role |
|------|------|
| `read_corpus_file` | Discovery: hub READMEs, current `timeline.md`, last 2–3 recaps for tone-mirroring. **Skip** dossier/seed/statblock — they are not consulted by this skill (use the `npc-power-increase` skill if mechanics matter). |
| `write_corpus_file` | Two-phase create of the new recap (`mode='create'`). Allowlist enforced server-side: only `**/Session Recaps/Session NN - <slug>.md` paths accept create. |
| `append_timeline_row` | Two-phase append of one row to `NPCs/<slug>/timeline.md`. Preferred over raw `write_corpus_file` so the table stays well-formed. |

## Two-phase commit (strict)

For every write tool call:

1. First call: `dry_run=true` (default). Tool returns `{phase: "preview", confirm_token, diff, …}`.
2. **Surface the diff to the GM in chat** as a fenced block; explain what will change in plain English.
3. Wait for the GM to type **`apply`** (or `apply <path>` to commit one at a time). Do not commit on “looks good,” “sure,” or any non-explicit reply.
4. Second call: same arguments + `dry_run=false` + the **exact** `confirm_token` from step 1.
5. If the tool replies with `stale confirm_token`, re-run dry-run (the file or content drifted) and present the new diff before retrying.

If the GM rejects a draft, regenerate it; do not commit a stale token after edits.

## Protocol

### 1. Identify the campaign hub

Default to the campaign whose `Session Recaps/` folder contains the most recent `Session NN` filename. If the notes plausibly belong to another campaign (e.g. they mention a different party / table), ask the GM in one sentence which hub. Common targets:

- `Longmont Campaign/Campaign 2/Session Recaps/`
- `Longmont Campaign/Campaign 1/Session Recaps/`

### 2. Pick the next session number

List the chosen `Session Recaps/` directory via `read_corpus_file` on the parent README *or* by reading enough recap filenames to compute:

```
next_session_number = max(parse_int_after("Session ") for name in dir) + 1
```

If the GM’s notes already specify a session number that does not match `next + 0/1`, ask for confirmation in one sentence before proceeding.

### 3. Mirror tone and structure

Read the **2–3 most recent recap files** with `read_corpus_file`. Note:

- YAML frontmatter shape: `title`, `document_class: play`, `canon_layer: campaign`, `campaign_id`, `session: N`, `origin_session: N`, `last_updated_session: N`, `source_class: observed_session_recap`.
- Length / paragraphing.
- Whether the GM uses a numbered TLDR up front (some sessions do; if recent sessions don’t, still emit one — the GM asked for a numbered summary).

### 4. Identify affected NPC slugs

For every NPC the notes name (by canonical name, alias, or clear description), open the campaign-hub `NPCs/<slug>/README.md` (skip dossier/seed/statblock per the skill rule) and the `timeline.md` so you have:

- The slug (from the folder name).
- The existing timeline format (column shape and row-count for ordering).
- The recap path the new row will reference.

If a slug cannot be resolved confidently from the manifest, **ask one disambiguation question** instead of guessing.

### 5. Draft everything (no writes yet)

Produce, all in one chat turn:

1. The **full new recap** body (frontmatter + numbered TLDR + long-form prose).
2. For each affected NPC, the **proposed timeline row** payload (`npc_slug`, `session`, one-cell `beat`, `recap_path`).
3. Optional: any README append-only additions (rare; only if the recap reveals a genuinely new pinned read).

Surface the recap as a fenced markdown block and the timeline rows as a short table (slug | session | beat | recap_path). Tell the GM what’s about to be written, in order.

### 6. Dry-run, show diffs, await approval

Call `write_corpus_file(dry_run=true)` for the recap and `append_timeline_row(dry_run=true)` for each NPC. For each preview, show the returned `diff` as a fenced block with `confirm_token` clearly labeled. Then ask the GM to type `apply` (or `apply <path>` per file).

### 7. Commit on `apply`

For each approved item, call the same tool with `dry_run=false` and the matching `confirm_token`. **Stop on first error** and report it; do not retry a stale token without a fresh dry-run.

### 8. Report fingerprint and follow-ups

After commits, state plainly:

- The new corpus fingerprint (use `recompute_corpus_fingerprint` from `src.agent.corpus_writer` mentally — the tool also includes a `fingerprint_reminder` in its response).
- One next step for the GM: update `evals/lysandra_vertical_slice/gold/step0_environment.json` → `expected_fingerprint`, then run `uv run pytest tests/test_lysandra_vertical_slice_step0.py`.

## Anti-patterns

- Committing a write without showing the diff and waiting for explicit `apply`.
- Editing a dossier, seed, or statblock “while we’re in there.” The tool will reject; do not work around it by rewriting the recap to embed mechanical numbers.
- Inventing a session number when the recaps folder already implies the next one.
- Padding the recap with un-grounded NPC backstory not present in the GM’s notes.
- Writing a “files used” section into the recap. The recap is in-world prose; tool traces capture sources.

## See also (sibling skills)

- **`npc-power-increase`** — read-only, mechanics-aware. If the GM's notes describe a power-tier shift (an NPC rose to a new threat level mid-session), summarize *what happened in fiction* in this skill's recap, then route the **mechanical follow-up** ("what should her sheet look like at the new tier?") to `npc-power-increase` in a separate turn. That skill attaches the canonical statblock via `load_context_markdown` and writes power-rise prose; it does **not** edit the statblock either. The two skills are complementary, never simultaneous: if you find yourself wanting to call both in one turn, finish the recap first, then start the upgrade conversation.

## Related repo wiring

- Writer module: `src/agent/corpus_writer.py` (allowlist + two-phase commit + timeline mutator).
- Planner registration (gated by `allow_corpus_writes`): `src/agent/planner.py`.
- Prompt addendum that documents the contract to the model: `_WRITE_TOOLS_ADDENDUM` in `src/prompts/corpus_session_planner.py`.
- Hub-format reference (timeline columns, README sections, dossier boundary): `Docs/CONVENTION-NPC-Hub-Package.md`.
- Lessons behind the dossier-immutability and two-phase-commit choices: `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md` Lessons 11 and 12.
