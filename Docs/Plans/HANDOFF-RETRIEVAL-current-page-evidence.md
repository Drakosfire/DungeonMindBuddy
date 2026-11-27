# RETRIEVAL: exact current-page benchmark evidence

Status: ACTIVE. The user authorized continuing the over-retrieval goal. Serial evaluator-only slice, based on fetched origin/main `192706c4eff0400dd90793145bbcba4edc014414`, branch `codex/negative-current-evidence`, checkout `Projects/.codex/negative-heldout-regressions/DungeonMindBuddy`. No runtime, ports, provider, or database changes are assigned.

Outcome: an explicit saved-current-page control can prove the exact requested page was returned, without inferring a read from its ID or an attempted call. The missing-page, wrong World, revision, document, body, raised and unfinished cases remain unknown; a partial journal cannot prove absence. Required semantic support, acquisition completeness, independent review and overall qualification remain separate.

Write lease: this handoff, `evals/negative_retrieval/report.py`, `evals/negative_retrieval/fixtures/development-private.json`, `evals/negative_retrieval/README.md`, and `tests/evals/test_negative_retrieval_assessment.py`. The open stored-evidence release #4884 owns pending runtime paths and is independent of this evaluator slice.

Verification: focused report-boundary tests of an exact frozen fixture pointer and returned digest, mismatched identity/body, no fixture binding, attempted/failed materialization and untrusted legacy records. Inspect the cumulative diff and obtain independent exact-head review; no clone or provider is required for these tests. This supports the later serial runtime fix; it does not itself fix Buddy or qualify the full benchmark.
