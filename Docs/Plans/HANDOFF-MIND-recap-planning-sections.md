# MIND: preserve explicit recap planning sections outside played extraction

Status: ACTIVE. Owner: PRIME; solo implementation. No provider, database or serving writes.
Remote main: `c9f5c21f3b835f35660b85fbd2e9a38312c401d4`.
Topology: stacked on frozen #1143 head `b2825de88b717b04b492c229fea8b40128c0d5d8`; merge/rebase #1143 first. PRIME transfers the shared extractor write lease to this successor; #1143 is frozen for review. #1142 and #1144 have disjoint paths.
Branch: `codex/recap-explicit-planning-sections-stacked`; isolated non-serving checkout.

Outcome: explicit Markdown planning sections and inline Looking Ahead paragraphs are retained as deferred source material, excluded from recap played-event prompts and positive assertions. Raw source bytes and span identities remain unchanged. Mixed planning/played spans are deferred for review rather than silently relabeled. This is structural source selection, not general prophecy or truth inference; unknown prose remains subject to semantic review. Worldbuilding extraction is unaffected.

Exact write set:
- `src/graph_memory/extraction/recap_source_authority.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `tests/test_recap_source_authority.py`
- `tests/test_recap_planning_section_pipeline.py`
- this handoff

Verify explicit planning, nested headings, section exit, inline prefix, quoted/fenced text, mixed spans and ordinary recap preservation. Exercise the owning pipeline with a synthetic pass attempting to emit a withheld planning citation: it must not survive as positive played evidence, and deferred material remains readable. Preserve original line references and source text. Run neighboring category/profile tests, lint and cumulative diff inspection; commit, push and open a stacked PR. Independent review required before merge. Preserve private real-source regression evidence outside Git.
