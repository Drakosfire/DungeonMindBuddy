# HANDOFF — INGEST canonical recap text to category passes

**Status:** IMPLEMENTED — awaiting independent PRIME review and merge.
**Base:** Buddy `origin/main@2a3e2566e30256528486d391758a7ab0f1a92ad8`.
**Branch:** `codex/graph-ingest-canonical-source-text` in isolated `/tmp/buddy-c1s16-ge-deepseek-prep-r3`.
**Topology:** independent PR. Open #1108 has separate SERVER/UI paths; paused older PRs do not own this packaging path. PRIME reviews the cumulative diff before merge.

## Why and what

The canonical `dmb_source_span_index_v1` stores line bounds and content digests, not `text` or `text_excerpt`. GraphIngest had the exact normalized recap loaded as `recap_text`, but the category options factory did not pass it to `CategoryGraphExtractionOptions.source_text`. The extractor consequently built empty source rows for canonical indexes. R3 spent two bounded DeepSeek calls on that incomplete request and cannot support a conclusion about model quality on the recap. Its grant is consumed; its marker, raw response, ledger, and manifest remain preserved.

This slice passes the already loaded normalized `recap_text` through the existing category options factory into `source_text`. The extractor's existing line reconstruction then supplies the actual recap paragraphs while retaining canonical span IDs, source artifact identity, roster context, and existing prompts/schemas/provider routing. No schema, extractor algorithm, source index, retry policy, or admission boundary changes.

## Exclusive write lease

1. `src/graph_memory/extraction/graph_ingest_packaging.py`
2. `tests/test_graph_memory_category_graph_preview_runner.py`
3. This handoff

The separate `/tmp/HANDBACK-INGEST-c1s16-ge-deepseek-reconciled-r3-preparation.md` records the newly learned R3 limitation. R1/R2/R3 evidence and any retained database are read-only.

## Owning proof and limits

The new regression creates a real canonical line-only SourceSpanIndex through the SourceArtifact registry, then invokes `run_graph_preview_extraction` with a fake category client. It inspects the actual actor request prompt: the unique recap fact and exact canonical span ID are present alongside Baergrom from the checked-in C1 roster. The resulting candidate, packaged index, manifest, and provenance retain the admitted source artifact ID. No provider or database is involved.

The focused new regression passes. The two owning test files have 34 passes and three inherited fixture identity failures in the unrelated supplied-candidate branch (`candidate_graph.campaign_id is required`); the same failures are documented by the already merged #1107 handoff and are outside this lease. Review the cumulative diff, run focused checks, and preserve this limitation in the PR. No paid rerun, publication, or model comparison is authorized here.
