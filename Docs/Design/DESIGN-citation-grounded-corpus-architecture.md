# Citation-Grounded Corpus Architecture

**Date created:** 2026-04-23
**Status:** Partially implemented. `SourceAnchor` now ships on `evidence_units` and propagates to `facts` during ingestion; remaining scope covers `event_records`, render-surface citations, and stale-anchor linting. Captures decisions reached in the [Canonicalize benchmark deflation antipattern](9406c41d-809c-45e3-b485-6b3d9a017076) discussion thread.
**Scope:** End-to-end change to how the corpus, fact store, and benchmarks treat provenance. Affects ingestion (`src/ingestion/`), the fact store (`src/store.py`), every recap-derived render artifact (timeline.md, dossier prose, hub paragraphs), and the Stage A / Stage B benchmark surfaces.
**Replaces / supersedes:** No prior doc. The design's load-bearing antipattern is canonicalized in `.cursor/rules/gold-realignment-vs-deflation.mdc`; the build-time contract intuition is in `.cursor/rules/verify-before-debug.mdc`.

---

## 1. The problem this solves

The current pipeline paraphrases recap prose **twice** and grades the second paraphrase:

1. **Stage A** (recap → events): an LLM reads recap prose and emits structured `event_record` JSON whose `outcomes[]` field is the LLM's gloss of what each sentence means. Not the source sentence — its interpretation.
2. **Stage B** (events → beat): a second LLM reads only Stage A's events for one slug and emits a single beat-cell paragraph for the timeline row. A second paraphrase, of an already-paraphrased input.
3. **Grader** (TP1 in `evals/session_recap_timeline_pass_vertical_slice/`): substring-matches a curated `anchor_words` list against the union of beat-cell text. After two paraphrase layers, did some specific recap-distinctive token survive?

This produces three failure modes that compound on each other:

- **Information loss is invisible.** Each paraphrase drops content that was in the input, but nothing flags it because the only check is "did the *next* layer preserve a few tokens we picked."
- **The benchmark gold becomes deflation-prone.** The anchor-word grader is a paraphrase-quality test masquerading as a capture-quality test. When the grader trips, the path of least resistance is to swap the anchor for one the model happens to preserve. This was committed 4-for-4 in the C1 S3 gold tunes on 2026-04-23 — see `gold-realignment-vs-deflation.mdc`.
- **Claims are unsourced.** Given a beat in `karsemine/timeline.md`, there is no machine-checkable way to trace it back to a recap sentence. The link recap-line → event → beat exists conceptually but is not addressable.

The chunker (`src/ingestion/chunker.py`) already computes `line_start` / `line_end` per AST node, but those line addresses are not propagated end-to-end into the fact store. Evidence units carry a content hash (`evid_<blake3:16>`) which protects against silent drift but does not give you "click-through to the source line."

---

## 2. Decision

**Adopt a two-mode citation contract:**

| Mode | When | Source-of-truth | Contract |
|------|------|-----------------|----------|
| **Extraction-mode** | Recap → events → timeline / dossier / hub paragraph; any LLM call whose input is an existing corpus document | The upstream document | **Strict.** Every emitted record carries `source_anchors` whose content hashes match source bytes. No anchor → record rejected at ingest. |
| **Authorship-mode** | Live-planning chat that mutates a hub; hand-edits to any markdown; LLM-collaborated edits during a planning thread | The git commit | **Loose.** Records are tagged `source_type: human_direct` (or `live_planning_collab`); `git blame` IS the citation. No upstream document required. |

The two modes share the same data structures and citation schema; they differ in `source_type` discriminator and what the lint enforces.

This decision was made because **the architecture has to fit the dominant workflow, not the benchmark**. Live planning is the hot path; recap extraction is post-hoc batch work. Forcing extraction-mode discipline (mandatory upstream doc, mandatory citation lint) onto live planning would block the GM's primary loop, which is the wrong tradeoff. Forcing authorship-mode looseness onto extraction gives back the deflation-resistance the design exists to gain.

---

## 3. Schema

### 3.1 `SourceAnchor`

```python
@dataclass
class SourceAnchor:
    source_type: Literal[
        "recap_extracted",        # LLM extracted from a recap or other source doc
        "human_direct",           # human typed this directly into the markdown
        "live_planning_collab",   # LLM-collaborated authorship inside a planning thread
        "derived_from_transcript",# LLM extracted from a saved planning transcript
    ]
    path: str              # corpus-relative
    line_start: int        # 1-indexed, inclusive
    line_end: int          # 1-indexed, inclusive
    content_hash: str      # blake3 of the literal source bytes at L<start>..L<end>
    commit_sha: str        # git HEAD at extraction time; enables git-blame semantics
    agent: str | None      # for human_direct / live_planning_collab: the human's name
    thread_id: str | None  # for live_planning_collab: the planning thread reference
```

### 3.2 What carries anchors

- **`evidence_units`** — gain `source_anchors` (the chunker already knows line ranges; just plumb them through; `evidence_id` becomes a derived index for "facts grouped by source span" rather than the canonical link).
- **`event_records`** — `source_anchors: list[SourceAnchor]` (multi-anchor for cross-sentence events).
- **`facts`** — every attribute claim cites the span(s) supporting it.
- **Render artifacts** (`wiki_pages`, timeline beats, dossier paragraphs) — cite the *fact ids* they paraphrase (transitive provenance: render → fact → evidence → recap span).

### 3.3 Anchors per fact: multi, not single

A fact like "Karsemine arrived in Stonebridge with the party" can be implied by 3 different sentences (roster line, wagon-arrival paragraph, later callback). Use multi-anchor; require at least one but accept many. Single-anchor would force an arbitrary "primary source" pick.

### 3.4 Anchors are commit-pinned AND validated against HEAD

Store `commit_sha` (immortal pointer) AND validate `content_hash` against current HEAD bytes on read. If HEAD bytes hash differently, the fact is flagged stale; rebind path is described in §5.

---

## 4. Render-layer separation

`timeline.md` / dossier markdown stop being treated as the sole canonical store. They become **derived views** of the fact store.

- The fact store is the canonical store of "what happened in C1S3 from Karsemine's POV."
- `timeline.md` is one render of that — short, scannable, GM-facing.
- A future Q&A surface, hub assembly, recap regenerate, etc. are other renders.
- All renders share the same fact base; they differ in compression / formatting / audience.

**The LLM still writes and updates render artifacts.** No change there. The change is that:

- LLM-generated render prose carries citation tokens (HTML comments inline, or a `citations:` frontmatter block — choice deferred to §6).
- Hand-edits to render markdown are first-class and tagged `human_direct`. The next fact-store rebuild ingests them as new evidence units sourced to the git commit.
- A render can be regenerated from facts on demand. Hand-edits survive (re-ingested as `human_direct` evidence on the next pass) and can themselves be reviewed in `git diff`.

---

## 5. Build / lint contract

The fact store becomes a **derived build artifact** with cache invalidation:

1. `git diff <prev>..<head> -- corpus/**/*.md` → list of changed source files.
2. For each fact whose `source_anchor.path` is in that list:
   - Re-hash bytes at `line_start..line_end`.
   - **Hash matches** → fact valid; line numbers may have shifted (find new range by hash search), update line numbers, no semantic change.
   - **Hash doesn't match, range relocated** → rebind by hash search elsewhere in the file.
   - **Hash doesn't match, no relocation** → fact is stale. Triage: re-extract the new span content; flag the fact for review.
   - **Range deleted entirely** → fact is orphaned; flag for review.
3. Re-run extraction only on stale spans (incremental rebuild, not full re-ingest).

Lint is contextual by `source_type`:

- **Extraction-mode artifacts** (timeline beats from Stage B, wiki pages from a render pass, auto-summaries) → must cite fact ids; `human_direct` not allowed because no human typed them.
- **Hub paragraphs, dossier prose, manual timeline edits** → may be `human_direct`, `live_planning_collab`, or `derived_from_transcript`. All three are valid.
- **Stale anchor detection** fires across all `source_type`s. Hand-edits that re-edit prose just become the new citation — no flag.

---

## 6. Citation rendering format (open question)

Three shapes considered; pick one before retrofit:

| Shape | Pro | Con |
|-------|-----|-----|
| HTML comments at end of each cited sentence (`<!-- cite: fact_id -->`) | Invisible to readers, visible to tools, precise per-sentence | Clutters source markdown; survives copy-paste in unintended ways |
| Frontmatter `citations:` block (single block at top of file) | Source markdown stays clean | Citation disconnected from the sentence it cites |
| Markdown footnotes (`[^fact_id]`) with reference list at file bottom | Standard markdown; visible-but-discreet | Visible to readers (may not be desirable for hub prose); footnote namespace collisions across files |

**Tentative pick:** HTML comments inline + a frontmatter `citations:` summary block. Hidden in normal reading; visible in `git diff` and to tools. Decision to be confirmed when the schema lands; see Backlog action item.

---

## 7. Live-planning workflow under this design

GM says: *"Add to Bonogo's hub: he picks up a tendency to grumble about flooded boots after S3."*

1. LLM opens `Longmont Campaign/Campaign 1/PCs/bonogo/bonogo_character_dossier.md`, appends the line.
2. The new line carries an inline citation comment: `<!-- cite: type=live_planning_collab agent=sean thread=<thread-id> ts=2026-04-23T... -->`.
3. Git commit lands; `git blame` records the human as the originating author.
4. Next fact-store rebuild ingests the new line as a new evidence unit with `source_type: live_planning_collab` (or `human_direct` if Sean hand-typed without LLM collaboration), anchored to the git commit + line range.
5. Later: *"Where did we say Bonogo grumbles about boots?"* → fact store query returns the hub line + "added during live planning, 2026-04-23, no upstream extraction."

**Planning transcripts are opt-in** (default OFF). When the GM wants the *reasoning* preserved (a meaningful character-arc decision worth revisiting), a one-line affordance saves the thread to `Longmont Campaign/.../Planning Transcripts/<date>-<topic>.md`, and the hub edit retroactively cites the transcript span (`source_type: derived_from_transcript`). Most edits don't need this. The failure mode of opt-in is "lost reasoning," not "blocked workflow."

---

## 8. Benchmark implications

The Stage A / Stage B grading surface evolves:

### 8.1 Capture-layer gate (replaces TP1 anchor-word substring)

Gold lists the recap line ranges that mention or implicate each slug; grader checks that those ranges are attached as `source_anchors` to event records whose `participants[]` includes the slug.

```json
{
  "npc_slug": "stafl",
  "expected_anchored_spans": [
    {
      "path": "Session 3 - The Stone Bridge Flood.md",
      "line_range": [22, 24],
      "rationale": "bard-song scene retelling Wizard's Tower Brewery"
    },
    {
      "path": "Session 3 - The Stone Bridge Flood.md",
      "line_range": [89, 91],
      "rationale": "Stafl helps Baergrom set the upriver net"
    }
  ]
}
```

The deflation antipattern shrinks dramatically: removing an entry is a visible diff with the rationale field calling out exactly which coverage is being silenced. "Picking an anchor *because* the model produced it" is structurally hard when the unit of measure is "did you attach this span," not "did your prose contain this token."

### 8.2 Render-layer gate (separate, qualitative)

Anchor-word substring gates still belong somewhere — but they belong to the **render** layer, not the capture layer. Does `karsemine/timeline.md`'s S3 row read well? Did the render preserve searchable vocabulary? Render is cheap to re-run (facts are already there; just re-prompt the renderer), so this gate iterates independently of capture stability.

The `gold-realignment-vs-deflation.mdc` rule applies in both gates, but the capture-layer gold is dramatically harder to deflate.

### 8.3 What does NOT improve from this design

Honest accounting:

- **Attribution is still LLM work.** "Karsemine is the implicit subject of this sentence" requires the same comprehension Stage A is doing now. The participant-completeness flake (`Backlog.md` 2026-04-23 entry — Karsemine dropped from S3 wagon-ride event) doesn't disappear; it becomes *cleanly testable* as "was line 45 attached to her events?" rather than ambient anchor-word noise.
- **Compression still happens at render time.** A GM scrolling Karsemine's S3 row doesn't want five recap sentences; they want a beat. The render layer still paraphrases — but with cited facts as input, and graded as a separate concern.
- **Cross-sentence synthesis.** "Stafl performs a song *referencing the previous session's job*" comes from joining two spans, not capturing one. Multi-anchor handles this; the *render* still has to surface the joining (and that's a render-quality gate, not a capture gate).

---

## 9. Costs and risks

1. **Schema discipline.** Every record-emitting LLM call needs to be retrofitted to emit anchors. Stage A (`step1_session_events_run.py`) is the obvious one; the recap-write skill, dossier-update skill, hub-creation skill all have to learn to cite.
2. **Anchor-resolution policy when bytes shift.** Hand-edits will rename/move spans. The `git blame` analogue (rebind by hash, fall back to fuzzy match, fall back to flag-for-review) needs an actual implementation.
3. **Render-layer citation format.** Per §6 — pick one, commit, retrofit.
4. **GM hand-edits to render artifacts.** When Sean adjusts a beat by hand, citations may go stale. The lint should be advisory (warn, don't block) — the GM is the source of truth, not the citation.
5. **Existing corpus retrofit.** Every existing fact in the store needs anchors backfilled. Probably feasible because the chunker already knows line ranges; this is a one-time migration script that re-walks evidence_units and attaches anchors via section_path + text match.
6. **Recap mutability.** Recaps do get edited after the fact (the `recap-write` skill exists). Span-grounded gold needs the rebind policy to handle this gracefully.

---

## 10. Open design questions

1. Single-anchor or multi-anchor per fact? **Provisional: multi.** (§3.3)
2. Commit-pinned or HEAD-relative anchors? **Provisional: both — store commit_sha, validate against HEAD on read.** (§3.4)
3. Where does the citation live in rendered markdown? **Provisional: HTML comments inline + frontmatter `citations:` block.** (§6)
4. Does this replace or augment the current `evidence_id` linkage? **Provisional: replaces — `evidence_id` becomes derived.** (§3.2)
5. What's the lint enforcement boundary for `human_direct`? Block, warn, or audit-only? **Tentative: warn for unsourced render prose; never block; audit for `human_direct` claims that appear without a corresponding git commit (catches LLM forgery of `source_type`).**

---

## 11. Sequencing (deferred to Backlog)

This doc captures the decision; concrete implementation steps live in `Backlog.md` as `[READY]` entries:

1. Revert the C1 S3 gold deflations and let the affected gates go red as documented pressure for the new design.
2. Prototype the `SourceAnchor` schema on `evidence_units` end-to-end (chunker → fact_extractor → store). One PR; no consumer changes.
3. Decide citation rendering format (§6) before retrofitting render artifacts.

The capture-layer benchmark gold rewrite, render-layer gate split, and Stage A / Stage B prompt updates follow once the schema is proven on a small slice.

---

## 12. References

- `.cursor/rules/gold-realignment-vs-deflation.mdc` — the antipattern this design defeats structurally
- `.cursor/rules/verify-before-debug.mdc` — the build-time contract intuition
- `Docs/Plans/EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md` — current Stage A / Stage B benchmark whose TP1 grader is the case study driving this design
- `Docs/Plans/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md` — operational checklist that keeps canonical-vs-derived boundaries and stage contracts enforced in day-to-day changes
- `Docs/Plans/EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md` — falsification suite plan (Stage A deterministic capture → Stage B hub routing → Stage D scoped retrieval fit; see `PLAN-Sentence-Routing-Stages-B-through-D.md` §3 for explicit harness / artifact names)
- `src/ingestion/chunker.py` — already computes line_start/line_end per AST node; not currently propagated
- `src/store.py:FactStore` — current fact store schema; `evidence_units`, `entities`, `facts`, `event_records`, `claims`
- `src/ingestion/fact_extractor.py` — Phase C pass-2 fact extraction; would gain anchor emission
- `Backlog.md` — `[READY]` items for sequenced implementation
