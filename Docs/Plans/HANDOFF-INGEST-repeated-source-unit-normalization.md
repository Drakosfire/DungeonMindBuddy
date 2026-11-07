# INGEST: normalize repeated exact source-unit citations

Status: ACTIVE. Root adopts this bounded owning-defect correction under the
user's resumed DeepSeek regression/consolidation goal. Independent contract review
approved exact-unit normalization; root implements and subagent reviews.

## Outcome, topology and lease

Stacked on PR #2190 head `c03a3b1fb93cfebe7f8728d668710e3260927614`.
Merge/rebase ancestor stack first, then this successor; no merge authority.
Branch `codex/ingest-repeated-source-unit-normalization` reuses this checkout.
Remote main and open PRs were inspected. PR #2123 contains the completed original
source-handle capability; root adopts its owning-path corrective lease here.
No other implementation worker owns these paths; review agents are read-only.

Exclusive write set:
- `Docs/Plans/HANDOFF-INGEST-repeated-source-unit-normalization.md`
- `src/graph_memory/extraction/source_sentence_evidence.py`
- `tests/test_source_sentence_evidence.py`

No inference, prompts, database/schema, fallback, Gold or model-config changes.
No services/ports are allocated. Evidence remains in the retained study workspace.

## Confirmed boundary and critique

Actual C1S1 run `1cc0f4dd-28de-4e32-8a9d-61cf3583ad1d` returned valid JSON
with known Q016 cited in two separate groups. The wire schema's uniqueItems rule
is per group; the materializer imposed an extra global rejection. It already
flattens groups into exact quotations. Normalize repeated known unit IDs once per
item, preserving first occurrence order and immutable raw producer output.

Keep membership and within-group uniqueness checks before deduplication, including
in later groups. Do not deduplicate by quote text or span: distinct positions and
same-span sentences must survive. Validate packet identity first; preserve atomic
input deep-copy behavior, malformed-ref rejection and empty-observation rejection.
This does not repair semantic claims, regrade Gold or turn a failed run into a
successful retained candidate. Frozen baseline/runtime evidence stays unchanged.

## Verification and delivery

Exercise all three collections, repeated groups, later-group invalid/unknown
handles after repeated valid handles, distinct units with identical text and
same-span sentences, exact quote bytes/order, unchanged raw input and canonical
schema validation. Replay the exact retained response offline against its pinned
packet; prove the only normalization difference is redundant source citation.
Run owning source/extractor tests; inspect cumulative diff; obtain independent
exact-head review; commit/push/open one bounded PR. No new capture until the
owning defect is verified and ordinary runtime qualification is renewed.
