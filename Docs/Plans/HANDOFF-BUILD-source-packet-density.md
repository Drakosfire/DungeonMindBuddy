# BUILD: source packet density

Status: ACTIVE. PRIME implements under the Mirathorn ingestion/efficiency goal; ARCHITECTURE reviews. Base4462783b214ecee091b5e242663f2d7935f0f6b0; branch codex/ingestion-source-packet-density; non-serving /tmp/buddy-worldbuilding-passage-composition.

One capability: avoid printing identical source_span_ref_id/source_unit_id twice in extraction prompt rows. Preserve canonical span IDs, distinct unit IDs, text and line coordinates. Missing unit IDs print the canonical span alone. No aliases, evidence decoder, source selection or schema changes.

Write set: this handoff; only _source_packet_md in src/graph_memory/extraction/category_candidate_graph_extractor.py; tests/test_source_packet_density.py. PRIME owns this bounded helper lease. Frozen open recap1143/1145/1148/1149 touch other extractor functions; do not merge/rebase their stale extractor bytes over this accepted helper. No unmerged dependency. Serial BUILD successor after merged1159.

Verify equal/distinct/missing unit ID prompt rows, canonical evidence reference preservation, neighboring worldbuilding/category tests and same-tokenizer before/after real-source local counts. No model, runtime, corpus or retained database writes. Prompt savings do not prove inference fidelity or context-budget safety. Independent exact-head review required before merge.
