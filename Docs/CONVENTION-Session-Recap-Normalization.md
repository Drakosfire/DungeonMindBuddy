# Convention: Session recap normalization (prepared corpus)

**Status:** Prescriptive for prepared recaps under `Longmont Campaign/Campaign N/Session Recaps/_normalized/`.
**Authority:** Play canon hierarchy in `Docs/CONVENTION-Corpus-Subject-Schemas.md` §1.5 (recap prose is canonical; prep chrome is not).
**Reference shape:** `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md` (frontmatter + H1 + flat narrative).

---

## 1. Purpose

Prepared recaps are **byte-stable narrative-only** copies of the table canon, suitable for strict downstream tooling (e.g. inline breadcrumb tagging that verifies tag-stripped text equals the source body). Original files under `Session Recaps/*.md` stay unchanged; `_normalized/` holds the prepared variant.

---

## 2. Path and filename

- **Directory:** `Longmont Campaign/Campaign N/Session Recaps/_normalized/`
- **Filename:** `Session NN - <Title Case Slug>.md` where `NN` is zero-padded (`01`–`20`).
- **Slug:** Words separated by spaces, Title Case, ASCII letters and spaces only, ≤ 6 words unless an existing session title already defines a longer canonical slug (trim only for length policy exceptions documented in `Docs/Plans/INDEX-Recap-Normalization.md`).

---

## 3. Frontmatter contract (`dmb_recap_normalized_v1`)

Required keys:

| Key | Rule |
|-----|------|
| `title` | `"Session N - <Title Case Slug>"` (must align with filename slug). |
| `document_class` | `play` |
| `canon_layer` | `campaign` |
| `campaign_id` | `longmont-c1` or `longmont-c2` |
| `temporal_scope` | `session_specific` |
| `session` | Integer session number. |
| `origin_session` | Same as `session` for this normalization pass. |
| `last_updated_session` | Same as `session` for this normalization pass. |
| `source_class` | `observed_session_recap` |
| `subject_class` | `null` (recap spans many subjects; see subject-schema doc). |
| `subject_doc_kind` | `recap` |
| `normalized_from` | Corpus-relative POSIX path to the **original** recap file. |
| `normalized_on` | ISO date (`YYYY-MM-DD`) of the normalization commit/pass. |
| `normalization_schema` | `dmb_recap_normalized_v1` |

Copy any other scalar frontmatter keys from the source unchanged if present (do not strip unknown keys unless they conflict with the above).

---

## 4. Body contract

1. **Single H1** after frontmatter: `# Session N Recap` or `# Session N - <Slug>` (consistent with `title`).
2. **Narrative only:** one or more paragraphs separated by a single blank line.
3. **Forbidden in body:** `##` / `###` headings, GM rubric sections (`Major Beats`, `Next Beats`, `Looking Ahead`, `Loot`, `Items`, `Into the Sewer`, etc.). Those belong in prep docs or are discarded—never copied into the prepared recap.
4. **Inline markup:** Preserve `**bold**`, `*italic*`, and similar from the source **recap** section verbatim.
5. **Lists:** Do not add markdown list syntax. If the source recap uses plain-text numbered lines (e.g. ritual Q&A), preserve them as plain lines; do not introduce `-` / `*` list blocks that were not in the source recap span.

---

## 5. Prose-preservation rule

The prepared body (below the H1) is **copy-paste** from the source file’s recap span, with **only** these mechanical transforms:

- Remove the recap **label** line(s) themselves (`Recap:`, `## Recap:`, `**Recap:**`, etc.).
- Normalize newlines: `\r\n` → `\n`.
- Remove lines that are markdown headings (`#` … `######` at line start).
- Trim trailing whitespace on each line.
- Collapse 3+ consecutive blank lines to at most 2.

**No** paraphrase, spelling changes, or punctuation edits.

This matches the strict equality expectation used by breadcrumb normalization (`verify_global_text_equal` in `evals/sentence_routing_retrieval_falsification/breadcrumb_normalize.py`) when the H1 line is handled consistently by the ingest pipeline.

---

## 6. Locating the recap span in the source

Typical patterns (first match wins when scanning top to bottom after frontmatter):

1. Line matching `## Recap:?\s*$` (heading).
2. Line matching `Recap\s*:?\s*$` (plain label, possibly `Recap :`).
3. Line matching `\*\*Recap\*\*\s*:?\s*$` or a split `**Recap:` / continuation — include narrative after the label; strip stray `**` that only wrapped the label.
4. **No label:** entire post-frontmatter body is the recap (after stripping an optional decorative `# Session N …` title line if it is not narrative).

Discard all lines **before** the start of the recap span (prep beats, loot notes, etc.) unless folded into frontmatter per operator choice (this convention does not require folding).

---

## 7. Corpus writes

New files under `_normalized/` MUST go through `write_corpus_file` (`src/agent/corpus_writer.py`) with `mode=create` and an allowlisted path: `**/Session Recaps/_normalized/Session \d+ - *.md`.

**Batch materialization:** `uv run python scripts/materialize_normalized_recaps.py` (writes all Longmont `Session Recaps/*.md` siblings into `_normalized/` using the extraction rules above). Re-run only when adding sessions or changing rules; edit curated slugs in `_SLUGS` in that script when a title is generic (`Session N - Recap`).

---

## 8. Related

- Subject schema: `Docs/CONVENTION-Corpus-Subject-Schemas.md`
- Destination index: `Docs/Plans/INDEX-Recap-Normalization.md`
- Writer allowlist: `src/agent/corpus_writer.py`
