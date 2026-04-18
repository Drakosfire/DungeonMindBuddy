---
name: recap-write
description: Take pasted raw session notes and write ONE canonical `Session N - Recap.md` (frontmatter + de-duplicated GM prose, voice preserved verbatim). Also extracts a structured follow-up surface (timeline-append candidates, new-hub proposals, plot artifacts, prep-doc pointer, dismissed NPCs) for the GM to act on later. Never edits dossier/seed/statblock. Two-phase commit. Does NOT propose any other writes itself.
---

# recap-write — write one recap, surface follow-ups as structured data

This skill has **one write target**: a new `Session <N> - Recap.md` file. Everything else it produces is **structured output** for the GM (or downstream skills) to act on. It does not append timeline rows, create new NPC hubs, place plot artifacts, or write prep-doc pointers. Each of those is a separate decision and (for timeline rows) a separate skill.

This decomposition exists because earlier passes asked one prompt to draft the recap **and** enumerate a multi-category review surface in the same turn; the recap landed reliably, the review surface flapped between "two items" and "none." See `Docs/Plans/PROCESSING-NOTES-Session-20-Manual-Ingest.md` §4 (deterministic vs. judgment) and §6 (review-surface inventory) for the analysis behind the cut.

## Inputs

- **Raw session notes** in the user message (the GM's prose, possibly with a leading title line, possibly with duplicate paragraphs, possibly with single-`\n` paragraph breaks).
- **A campaign hub** the planner can resolve from the notes (see Protocol §1). Defaults to the campaign whose `Session Recaps/` folder contains the most recent `Session NN`.

## Outputs (in this order, in the same turn)

1. A **two-phase preview** of `Session <N> - Recap.md` via `write_corpus_file` (`mode='create'`, `dry_run=true`). The recap follows the surveyed shape: 8-field frontmatter, one H1, then GM prose verbatim with duplicates removed (and the removal **surfaced**, not silent).
2. A **structured follow-up payload** as a fenced ```json block inside the planner reply `message`, conforming to `src/agent/recap_write_output_schema.py::recap_write_output_json_schema()`. Fields:
   - `recap_preview` — path, mode, `confirm_token`.
   - `duplicate_paragraphs` — line numbers, paragraph preview, recommended action.
   - `npc_audit.timeline_append_candidates` — slugs with existing hubs that warrant a row (consumed by the future `recap-timeline-append` skill).
   - `npc_audit.new_hub_proposals` — first-appearance NPCs that look hub-worthy (text only; **no write tool covers new-hub creation today**).
   - `npc_audit.dismissed` — named NPCs explicitly considered and not proposed, with reason. Audit trail.
   - `plot_artifacts` — major new in-world objects, with 2–3 candidate placement paths (text only; no allowlist for arbitrary `Plot Artifacts/` or `Locations/` files today).
   - `prep_pointer_proposal` — proposed bidirectional pointer text if a `Session Prep/session_<N>_*.md` companion file was found (text only; prep-doc paths are **outside** the writer allowlist today).
   - `notes_for_gm` — free-form caveats.

The **recap commit** (second writer call with `dry_run=false`) only happens after the GM types `apply` (or `apply <recap-path>`). Without explicit approval, the skill stops at the dry-run preview.

## What this skill does NOT do

- It **does not** call `append_timeline_row`. That belongs to the future `recap-timeline-append` skill (one slug per call; surveys per-hub row richness; one row preview per call).
- It **does not** call `write_corpus_file` for any file other than the recap. New-hub proposals, plot-artifact files, and prep-doc pointer appends are **text only** in the structured payload — for the GM to act on by hand or for a future skill (gated on writer-allowlist extension).
- It **does not** read `*_character_dossier.md`, `character_seed.md`, or `*_statblock*.md`. The skill says "skip"; the corpus reader (or this skill's discipline) enforces it. See **Lesson 11** in `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md`.
- It **does not** read recaps from a different campaign. If you're ingesting a Campaign-2 session, do not pull Campaign-1 recaps.
- It **does not** rewrite, "tidy," normalize quotes, fix grammar, or otherwise touch the GM prose. Identity transform on the body after de-duplication.
- It **does not** write a TLDR, internal section headings, dialogue speaker labels, or a "files used" trailer in the recap body.
- It **does not** invent a session number when the recaps folder already implies the next one.

## Required runtime

- **CLI:** `dmb plan --allow-corpus-writes`
- **Or env:** `DUNGEONMIND_PLANNER_ALLOW_WRITES=1`

When enabled, `get_recap_context`, `assemble_recap_draft`, and `write_corpus_file` are registered as planner tools. Without it, this skill stops at the proposed-content step and surfaces only the structured payload — no commit possible.

## Tools

| Tool | Role |
|------|------|
| `get_recap_context` | **Always call first.** Returns the active campaign, `target_session`, the **3 most recent** prior recaps (by frontmatter `session: N`, not filename), the unique companion prep doc path (or `null`), and the campaign hub / `NPCs/` paths. Source of truth for "which prior files to read." Pass `campaign_id` only if the GM explicitly named a different campaign than the active one; pass `target_session` only for an out-of-order or re-ingest case. |
| `read_corpus_file` | Open every path the context tool returned: each `recent_recaps[].path` (for shape / frontmatter / length survey) and `prep_doc_path` (if non-null, for surnames + intent). May also open the affected `NPCs/<slug>/README.md` (under `npcs_dir`) when an NPC is mentioned and you need to confirm whether a hub exists. **Skip** dossier/seed/statblock — they are not consulted by this skill. **Do not** read recaps from a different campaign than the one `get_recap_context` returned. **Do not** list `Session Recaps/` yourself, glob for prep docs, or pick recaps by filename. **Do not** `read_corpus_file` the raw-notes staging path — use `assemble_recap_draft` instead. |
| `assemble_recap_draft` | **After reads**, call once with the corpus-relative `raw_notes_path` (staging file named in the user message), plus `target_session` and `campaign_id` from `get_recap_context`. Returns `recap_body` (full markdown: frontmatter + H1 + de-duplicated prose). Pass that string to `write_corpus_file` `content` — do not re-run duplicate detection or rebuild frontmatter by hand. |
| `write_corpus_file` | Two-phase create of the new recap (`mode='create'`). Allowlist enforced server-side by `src/agent/corpus_writer.py`: only `**/Session Recaps/Session NN - <slug>.md` paths accept create. |

`append_timeline_row` is **not** part of this skill. Listing it in `npc_audit.timeline_append_candidates` is the handoff to the future per-NPC skill.

## Two-phase commit (strict)

For the recap write:

1. First call: `dry_run=true` (default). Tool returns `{phase: "preview", confirm_token, diff, …}`.
2. **Surface the diff to the GM in chat** as a fenced block above the structured payload; explain what will change in plain English.
3. Wait for the GM to type **`apply`** (or `apply <recap-path>`). Do not commit on "looks good," "sure," or any non-explicit reply.
4. Second call: same arguments + `dry_run=false` + the **exact** `confirm_token` from step 1.
5. If the tool replies with `stale confirm_token`, re-run dry-run (the file or content drifted) and present the new diff before retrying.

If the GM rejects the draft, regenerate it; do not commit a stale token after edits.

## Protocol

### 1. Get the canonical context (one tool call, no guessing)

Call **`get_recap_context()`** once with **no arguments**. Pass `campaign_id` only if the GM explicitly named a different campaign than the auto-detected active one (e.g. ingesting an out-of-order Campaign 1 session). Pass `target_session` only for an explicit re-ingest of an existing session.

The tool returns:

- `campaign_id` (e.g. `"longmont-c2"`) and `campaign_hub` (corpus-relative, e.g. `Longmont Campaign/Campaign 2`).
- `target_session` — **the** session number being ingested. Use this. Do not invent a different number from the raw notes.
- `recent_recaps` — **exactly the prior recaps you should read**, sorted descending by frontmatter `session: N`, capped at 3. Each entry has `path`, `session`, `title`, `campaign_id`.
- `prep_doc_path` — the unique companion prep doc (or `null`). Convention: one prep doc per session named `session_<N>_*.md`; the tool raises if more than one matches.
- `session_recaps_dir`, `session_prep_dir`, `npcs_dir` — corpus-relative directory paths for downstream operations.
- `notes` — non-fatal observations (e.g. "fewer than 3 prior recaps available") that you should surface to the GM in `notes_for_gm` if relevant.

If `get_recap_context` returns an `Error: …` string (e.g. "Multiple prep docs match…"), **stop and surface the error verbatim to the GM**. Do not try to recover by listing directories yourself — the error is an operator-fixable corpus-state problem, not a modeling problem.

### 2. Read exactly what the context tool gave you

`read_corpus_file` each path in `recent_recaps[].path` (all of them) and `prep_doc_path` (if non-null). Do **not** open any other recap, do **not** open recaps from a different campaign, and do **not** re-list `Session Recaps/` to second-guess the tool's selection.

### 3. Survey the canonical shape from the recaps you just read

Confirm against the recaps the tool returned:

- **Frontmatter field set** (invariant across the surveyed recaps): `title`, `document_class: play`, `canon_layer: campaign`, `campaign_id`, `temporal_scope: session_specific`, `session: N`, `origin_session: N`, `last_updated_session: N`, `source_class: observed_session_recap`. Reproduce exactly with `target_session` substituted for `N` and the tool's `campaign_id` substituted in.
- **Title styling.** Existing recaps may be **inconsistent** (some have trailing colons, descriptive subtitles, omitted H1, body-duplicated titles). Choose the **cleanest exemplar's form** as canonical (typically `title: "Session <N> - Recap"` and `# Session <N> Recap`). Do **not** replicate prior typos.
- **Body structure.** Canonical recaps are a single H1 followed by interleaved-thread prose paragraphs separated by blank lines. **No internal section headings, no numbered TLDR, no checklists, no dialogue speaker labels.** If the surveyed recaps don't have a TLDR, the new one doesn't get one either.
- **Voice.** The GM's prose voice is already correct. Mirror length and present-tense beat-by-beat shape; do not rewrite it.

### 4. Use the prep doc (if `get_recap_context` returned one)

When `prep_doc_path` is non-null, the file you read in §2 is the companion prep doc. It often gives **surnames the recap omits**, **planned beats that may or may not have fired**, and **NPC character notes** the recap won't repeat.

- Surface a **prep ↔ recap pointer proposal** in the structured payload (`prep_pointer_proposal`). Do **not** silently merge prep-doc material into the recap body — they can disagree, and the disagreement is itself continuity.
- Prep-doc paths are **outside the writer allowlist today**, so the pointer text is for the GM to apply by hand.

### 5. Build the canonical recap (mechanical — planner tool)

Do **not** paste raw notes into `write_corpus_file` or re-implement paragraph logic in prose.

1. Call **`assemble_recap_draft`** with the staging `raw_notes_path` from the user message, `target_session`, and `campaign_id` from §1. The server runs `recap_ingest_helpers.assemble_recap` (strip leading title line, robust paragraph split, deterministic duplicate removal, frontmatter + H1 + body).
2. Use the returned **`recap_body`** as the `content` for `write_corpus_file` `mode='create'` (two-phase).
3. Map the tool's `ingest_report` (duplicate line ranges) into the structured payload's `duplicate_paragraphs` for the GM — do not contradict what the tool removed.

### 6. Build the structured follow-up payload (extractor)

Walk the recap once and populate the structured payload fields:

- `npc_audit.timeline_append_candidates` — every named NPC for whom a `NPCs/<slug>/README.md` already exists (i.e. has a hub) **and** who took an action this session worth a timeline row.
- `npc_audit.new_hub_proposals` — first-appearance, named, hub-worthy NPCs (power-center, recurring potential, named role). For each: proposed slug, campaign-hub vs setting-hub recommendation, initial files (typically `README.md`, `<slug>_character_dossier.md`, `timeline.md`).
- `npc_audit.dismissed` — every other named NPC considered: walk-on, sidekick, town-functionary, faction. With one-sentence reason. **PCs are skipped silently — do not list them.**
- `plot_artifacts` — major new in-world objects (named locations, blueprints, relics, maps). For each: a short evidence quote from the recap and 2–3 candidate placement paths.
- `prep_pointer_proposal` — populated when a companion prep doc was found in §4; otherwise `null`.
- `notes_for_gm` — caveats, ambiguities, anything you noticed that doesn't fit the structured fields.

The follow-up payload is **the entire judgment surface for this skill**. Do not also enumerate it in narrative prose; the GM reads the JSON. A short prelude line in `message` ("Drafted Session 20 recap. Structured follow-ups below.") is fine.

### 7. Two-phase commit on the recap

Per the contract above. After the GM approves with `apply`, call `write_corpus_file` again with `dry_run=false` and the exact `confirm_token`. Report the new corpus fingerprint from the writer's response.

## Anti-patterns

- **Skipping `get_recap_context`** and listing `Session Recaps/` yourself, parsing filenames for the next session number, or globbing for prep docs. The tool is the source of truth; bypassing it is how earlier runs read the wrong prep doc and picked recaps by lexicographic filename order instead of session number.
- Calling `append_timeline_row` from this skill. (That's the next skill, not this one.)
- Calling `write_corpus_file` against any path other than the new recap. The writer will reject; do not work around it.
- Reading dossier/seed/statblock files "for context." This skill's contract excludes them. The recap is the wrong place to mirror their content; the timeline row is the right place to encode session-driven status.
- Reading recaps from a different campaign than the one `get_recap_context` returned, or opening additional recaps beyond the 3 it returned. If you need older context, surface it in `notes_for_gm` instead.
- Rewriting, "tidying," or grammar-fixing the GM's prose. Identity transform after de-dup.
- Emitting a numbered TLDR or section headings the surveyed recaps don't use.
- Replicating a typo from a prior recap (trailing colons in titles, body-duplicated titles).
- Silently stripping a duplicate paragraph. Report it in `duplicate_paragraphs` with source line numbers.
- Silently merging prep-doc material into the recap body.
- Auto-creating a new NPC hub. New hubs are a multi-file proposal in `npc_audit.new_hub_proposals` only.
- Inventing a session number when the recaps folder already implies the next one.
- Writing a "files used" section into the recap body. The recap is in-world prose; tool traces capture sources.
- Putting the structured payload anywhere other than a fenced ```json block inside `message`. Graders parse the block; arbitrary prose locations will fail.

## See also

- **Context resolver:** `src/agent/recap_context.py` — `resolve_recap_context()`, the deterministic source of truth the `get_recap_context` tool wraps. K=3 is hard-coded there.
- **Schema:** `src/agent/recap_write_output_schema.py` — `recap_write_output_json_schema()`, `extract_recap_write_payload(message_text)`.
- **Helpers:** `src/agent/recap_ingest_helpers.py` — title strip, robust paragraph split, duplicate detection.
- **Writer contract:** `src/agent/corpus_writer.py` — two-phase commit, allowlist, `append_timeline_row` for the future per-NPC skill.
- **Prompt addendum:** `_WRITE_TOOLS_ADDENDUM` in `src/prompts/corpus_session_planner.py`.
- **Hub-format reference:** `Docs/CONVENTION-NPC-Hub-Package.md` (timeline column shape, README sections, dossier boundary).
- **Read-only rationale:** `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md` Lessons 11 and 12.
- **Manual-ingest reference (the analysis that drove this cut):** `Docs/Plans/PROCESSING-NOTES-Session-20-Manual-Ingest.md`.
- **Sibling skill (read-only, mechanics-aware):** `.cursor/skills/npc-power-increase/SKILL.md`. If a recap implies a power-tier shift, finish the recap commit first, then start a separate turn with `npc-power-increase`. Never run the two simultaneously.
- **Future sibling (judgment, per-NPC, write-enabled):** `recap-timeline-append` (not yet authored). Will consume `npc_audit.timeline_append_candidates[]` from this skill's payload, one slug per call.
