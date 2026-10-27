# INGEST — retain independently validated multi-paragraph beat excerpts

Status: ACTIVE, serial PRIME-owned regression fix. Base a0eb30093b4fa8246351586d001a3fe7536f7938; branch codex/recap-multispan-excerpts; existing buddy-context-loop checkout. Operator authorizes runtime regression ownership and PRIME merge/delivery after independent review and gates.

## Critique and bounded contract

ADVERSARY's frozen post-fix Luna S1 raw beat-6 cites paragraphs24/26 and contains the reward; host rejects the entire beat as multi_span_nomination. Haiku independently exhibits the same packaging loss. Original evidence and frozen comparison remain unchanged. The producer permits multiple references. The historical single-paragraph rule deliberately prevented model summaries and joined-source inference; simply deleting its guard would weaken provenance.

Resolve each nomination independently with the existing pinned digest, eligible paragraph, exact bounds, unique exact quote and nominated-span agreement checks. Emit one entire unchanged host paragraph per distinct valid nominated paragraph within each raw beat. Never join text, expose generated title/summary, relax invalid evidence, or promote beats to occurred events. Invalid references get separate deterministic deferrals even alongside valid references. Duplicate valid nominations emit one excerpt; duplicate invalid nominations remain observable. Digest failure defers the whole raw beat.

Host child IDs bind raw beat ordinal and canonical paragraph; source_beat_id retains the raw model beat identity explicitly. IDs do not depend on nomination order. Preserve model order/participants as existing preview-only metadata; sort sibling excerpts by source index, without asserting chronological/causal linkage. Missing/repeated raw IDs cannot collide between raw beats. The typed host preview carries optional source_beat_id (non-excerpt beats have no such lineage); no provider schema or prompt changes.

## Exclusive writes and ownership

- This handoff; HANDOFF-INGEST-extractive-beat-summaries.md (explicit supersession of only multi-span blanket deferral).
- src/graph_memory/extraction/category_candidate_graph_extractor.py (recap host normalization only).
- src/graph_memory/candidate_graph_preview.py (host excerpt lineage field only).
- tests/test_recap_source_quote_beat_summary.py (owning-boundary regression).
- HANDOFF-INGEST-openai-schema-projection.md (truthful merged predecessor settlement).

Open PR1828 owns hosted deployment/config; old held extractor PR1148/1149 reserve no current-main lease under predecessor contract. No overlapping active PR; no schema, prompt, gold, target, publication, migrations, dependencies, UI or harness writes. Existing API8000/UI5202 and retained data stay unchanged until separately protected delivery after review/merge. No provider calls in this implementation. ADVERSARY owns independent frozen evaluation and later separate-phase replay, never silent pooling/regrading.

## Verification and delivery gates

Exercise actual category extraction through typed preview and contribution mapping: two real paragraphs, reversed/duplicate nominations, repeated raw IDs, missing/forged/mismatched/ambiguous/stale/bad-bound refs including mixed valid/invalid, contradictory model prose and no occurred-event promotion. Run existing owning extractor/preview/contribution tests, Ruff and cumulative base-to-head diff review. Replay captured raw/source shapes offline if available, preserve original hashes. Commit/push/open one bounded PR, independent Bugbot exact-head review, required hosted checks, PRIME merge and protected same-port API delivery. Tests/replay do not establish model quality or full adventure acceptance.

## Author verification

Owning extractor, typed-preview/IR, contribution mapper, default semantic-state and quote-integrity suites: 83 passed. Extractor/test Ruff passes. Typed preview module has 29 pre-existing E701/E702 diagnostics; pinned-base versus head JSON comparison is identical excluding shifted line numbers. No lint suppression or unrelated reformatting was added.

Exact captured Luna host-selector replay: 7 raw beats produce 6 excerpts plus multi_span_nomination on pinned base; patched selector produces 8 excerpts, no deferrals, two independently cited whole-paragraph children for beat-6 including reward. Source/index/response/original candidate hashes unchanged. This is selector-boundary proof, not full pipeline or future model/answer-quality proof. Private receipt: /home/drakosfire/.local/state/dungeonmindbuddy/experiments/recap-multispan-excerpt-replay.json, SHA256 d0e14bfcacfc7169e079b0adb520c1c83617cd966009fb91bf2d3a8c9eab0865. Zero provider calls and no database mutation.
