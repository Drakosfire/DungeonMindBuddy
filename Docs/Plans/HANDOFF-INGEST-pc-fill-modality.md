# INGEST: preserve source modality in party fill

**Status:** Active — PRIME approved the exact four-path write lease, including the shared deterministic provider fixture in `tests/test_party_claimed_fill.py`.
**Base:** `origin/main@ae394d6d3b98e49a4111c9e268efaa9174d24eca` (fetched 2026-10-17).
**Branch:** `codex/ingest-pc-fill-modality` in the existing clean `996b` checkout.
**Topology:** Serial; one Ingestion implementation PR. ARCHITECTURE has reviewed the design; PRIME retains exact-head review, merge, and rollout authority.

## Mission and invariant

Prevent the PC claimed-fill pass from turning intended, conditional, hypothetical,
negated, or reported actions into completed actions. In Session 29, the accepted
evidence quote says Ephanna “will use Eldritch Blast,” while the generated
description and action list say she used/cast it. Matching a quote to a paragraph
proves provenance, not that a rewritten description is entailed by it.

The provider selects source-addressable, context-bearing recap rows for each
claimed party node. The host requires each selected row to be linked to that
claim, binds its original source-span ID, and renders the existing public
`description`, `session_actions`, and evidence quote from the complete source
row. The private provider schema accepts only node identity and row selections;
it cannot supply public prose, action fragments, importance, or source IDs.
Require the complete selected context row, not a fragment that can strip a
modal qualifier. Preserve complete-coverage and atomic rejection: malformed,
partial, cross-claim, or context-free fills keep the candidate baseline and emit
a diagnostic. Do not trust a model-provided modality label as proof.

This protects the wording and scope of selected source context; it does not prove
semantic entailment, speaker attribution, or actor identity. The deliberate tradeoff
is longer, less polished source wording in party descriptions/actions for bounded
modality preservation; the same complete selected rows appear in both existing
fields, which increases candidate payload size. Preserve all wording for mixed
passages, including a valid completed action beside a planned action, and preserve
negation, conditions, and reported instructions. No global keyword regex or
spell/name-specific rule.

## Exact write lease (approved by PRIME)

- `Docs/Plans/HANDOFF-INGEST-pc-fill-modality.md` — this contract, lease, and truthful verification record.
- `src/graph_memory/extraction/party_claimed_fill.py` — private provider schema, row binding, and host rendering; public candidate field types remain unchanged.
- `tests/test_party_fill_source_binding.py` — owning source-row/binder/producer boundary tests.
- `tests/test_party_claimed_fill.py` — update its deterministic shared provider fixture and expected public projection; the source-binding pipeline test imports this fixture, so the contract change requires both test files. PRIME explicitly approved this test-lease expansion.

No other paths are in scope. In particular, no public candidate schema, UI consumer,
Graph publication, storage, model/provider call, real extraction, source/gold data,
saved run, database, service, environment, worktree, or temporary output changes.
The exact saved run `f43e48e6-c775-4960-824f-fb398fe50bb9` remains untouched.

## Failure cases and acceptance

- A selected source row is bound to its host-owned row and source-span ID, then copied verbatim into public description, action context, and evidence.
- Planned, conditional, hypothetical, negated, reported, and mixed wording stays exactly as sourced; the private schema has no provider-authored description or action fields to rewrite it.
- A short/unknown row index, row linked to another claim, malformed selection, invented identity, duplicate/partial claim, or missing context rejects the whole fill, leaves baseline nodes unchanged, and records why.
- Synthetic mixed-context coverage preserves both a neighboring valid past action and an intended action, plus conditional, negated, reported-instruction, and mixed-case wording. Output description, action strings, and citations are derived from the selected complete source rows.
- Provider input and baseline objects remain unchanged. Existing host-owned source-row binding remains authoritative.
- The public candidate graph still exposes `description: string`, `session_actions: string[]`, and normal evidence references. Consumer inspection confirms this implementation does not change that contract.

## Predecessor settlement and known evidence

- PR #1375 (`codex/ingest-source-to-enriched-review`) merged as `4144e98ece3e14f5b3470e77b40a513cf0698f3b`; this branch starts from current main after #1376 at `ae394d6d3b98e49a4111c9e268efaa9174d24eca`.
- PR #1206 closed the original party-fill source-binding lease. It already guarantees row-index selection, host-owned source IDs, quote matching within a selected row, atomic baseline preservation, and explicitly states that quote matching is not semantic entailment. This follow-up adds complete-row rendering and per-claim source-row scope.
- The 10/15 f43 run has 10 unresolved-warning occurrences across eight shortened refs on three `pc_claimed_fill_pass` nodes. Current main has source-proven legacy alias repair for that historical ID shape; the old stored artifact is not modified by this work.
- The genuine next gap is the Ephanna modality contradiction above. The separate active Session 29 gold handoff owns qualified warehouse/children links and gold-level intended-encounter relationships; it does not own this PC-fill producer or these tests.

## Verification

Implementation checks completed on the active branch: the producer/binding,
claimed-fill integration, and planning-source authority suites report **32
passed**; focused Ruff and `git diff --check` pass. The planning-source suite
also confirms a claimed fill cannot reintroduce a withheld planning row.

Use the existing Python runtime and repository cache only; do not install packages
or create another environment:

```bash
TMPDIR=$PWD/.pytest_cache PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 \
  /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime/bin/python \
  -m pytest --basetemp=.pytest_cache/ingest-pc-fill-modality \
  tests/test_party_fill_source_binding.py tests/test_party_claimed_fill.py \
  tests/test_recap_planning_section_pipeline.py

PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 \
  /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime/bin/python \
  -m ruff check --no-cache src/graph_memory/extraction/party_claimed_fill.py \
  tests/test_party_fill_source_binding.py tests/test_party_claimed_fill.py

git diff --check
```

Only synthetic deterministic source packets and fake providers are permitted.
Inspect the exact cumulative base-to-head diff against `ae394d6d`; commit, push,
and open the assigned PR after checks pass. Do not merge or change 5202.
