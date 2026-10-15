# MIND: preserve explicit recap planning sections outside played extraction

Status: ACTIVE. Owner: PRIME; solo implementation. No provider, database or serving writes.
Remote main: `55d1add6c80e5ad86d747e624c39b734ba15e64b`, including merged #1143.
Topology: standalone after #1143 merged at `55d1add6c80e5ad86d747e624c39b734ba15e64b`. #1143 now seeds the configured party endpoint before raw-edge checks while keeping source-backed edges ahead of evidence-free membership anchors. This slice owns the shared extractor lease from here; #1189 follows after this slice because it also edits the extractor and preview runner. #1139 and #1144 have disjoint paths.
Branch: `codex/recap-explicit-planning-sections-restack`; isolated non-serving checkout.

Outcome: explicit Markdown planning sections and inline Looking Ahead paragraphs are retained as deferred source material, excluded from recap played-event prompts and positive assertions. Raw source bytes and span identities remain unchanged. Mixed planning/played spans are deferred for review rather than silently relabeled. This is structural source selection, not general prophecy or truth inference; unknown prose remains subject to semantic review. Worldbuilding extraction is unaffected.

Exact write set:
- `src/graph_memory/extraction/recap_source_authority.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `tests/test_recap_source_authority.py`
- `tests/test_recap_planning_section_pipeline.py`
- this handoff

Verify explicit planning, nested headings, section exit, inline prefix, quoted/fenced text, mixed spans and ordinary recap preservation. Exercise the owning pipeline with a synthetic pass attempting to emit a withheld planning citation: it must not survive as positive played evidence, and deferred material remains readable. Preserve original line references and source text. Source-backed party membership must retain its citation when deduped against a standing roster anchor. Run neighboring category/profile tests, lint and cumulative diff inspection; commit, push and open a standalone PR against main. Independent review required before merge. Preserve private real-source regression evidence outside Git.
