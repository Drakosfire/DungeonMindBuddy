# HANDOFF — INGEST bounded schema-failure evidence

**Status:** IMPLEMENTED — awaiting independent PRIME review; no paid provider call or replay.
**Base:** Buddy `origin/main` at `1fb127f8a0a2f0456eb385186e54cecff6f58b33`.
**Branch:** `codex/bounded-schema-failure-evidence` in isolated `/tmp/buddy-bounded-schema-failure-evidence`.
**Topology:** independent PR. PRIME reviews the exact cumulative head before merge.

## Why this slice exists

The authorized C1S16 GE/DeepSeek R2 run produced five completed provider responses, but the fifth (`thread_pass`) failed local JSON-schema validation. The bounded client stopped correctly and its ledger recorded `ValidationError`; however it discarded the returned response before the existing GraphIngest packaging boundary could preserve a `raw_model_response` artifact. The original R2 response is gone and **cannot be reconstructed or diagnosed more specifically** from the ledger. Both attempt markers, outputs, and ledgers remain immutable; this code change does not spend another call or claim a historical recovery.

## One capability and five-path lease

For a completed response that fails local JSON parsing, object-shape checking, or DeepSeek pass-schema validation, `BoundedRecapPassClient` raises `CategoryGraphExtractionError` with `raw_model_response` set to the exact returned text. The existing owning packaging writer can then store that text in its private `raw_model_response.txt` artifact and seal the manifest reference with the exact written-file SHA256. The ledger records only error kind, a whitelisted validator, and schema-known/redacted instance/schema paths; it never includes response values, prompt/source text, or credentials. The client remains stopped before a next call. GE request, route, prompts, schemas, caps, retry/fallback policy, and acceptance rules are unchanged.

Exclusive changed paths:

1. `src/graph_memory/extraction/bounded_recap_execution.py`
2. `src/graph_memory/extraction/graph_ingest_packaging.py` — PRIME-approved essential fifth path, only the existing raw-response `_artifact` callsite digest
3. `tests/test_bounded_recap_execution.py`
4. `tests/test_graph_ingest_packaging_live_call_shape.py`
5. `Docs/Plans/HANDOFF-INGEST-bounded-schema-failure-evidence.md`

The packaging callsite was added by explicit PRIME rebrief after the test exposed its existing null manifest SHA. No other packaging behavior, schema, artifact kind, or validation changes are leased.

## Proof and stop lines

Fake-GE tests prove schema-invalid, invalid-JSON and non-object responses retain exact private raw text on the exception, emit safe validation metadata in the ledger, and stop before a second call. An owning GraphIngest packaging test drives a real bounded client with one fake GE response and proves the actual `raw_model_response.txt` file/digest matches the sealed manifest SHA while the manifest and ledger omit the private value and no candidate is produced. Focused suites (`test_bounded_recap_execution.py` and `test_graph_ingest_packaging_live_call_shape.py`) pass 36/36. Ruff passes the client/test paths; packaging passes with `--ignore F401` because current `main` already has an unrelated unused `FixtureCategoryGraphPassClient` import at line 38. That baseline import is left untouched under the callsite-only lease.

The adjacent legacy `test_graph_memory_category_graph_preview_runner.py` suite has three current-main candidate-fixture identity failures (`candidate_graph.campaign_id is required`) in an unmodified candidate-path branch; 19 other tests pass. No fix to that unrelated fixture or packaging behavior is leased. No provider execution, DB/World mutation, publication, runtime change, model rerun, or new diagnostic framework is authorized by this PR.
