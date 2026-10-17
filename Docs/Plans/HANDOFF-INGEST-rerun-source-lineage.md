# INGEST: verify generic canonical recap lineage from an explicit title

**Status:** ACTIVE — PRIME dispatched this bounded successor on 2026-10-17.
**Base:** fetched `origin/main@1a9d1304f89132db9b54f4590210be1ffa7541d9`.
**Branch:** `codex/ingest-session10-normalization-provenance`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (existing assigned checkout; no new worktree).
**Topology:** serial successor to the integrated #1255 derivative-lineage work. One PR for this successor; PRIME owns independent review and merge.
**Runtime/data boundary:** disposable test corpus only. Preserve existing user/session/corpus data. Do not write retained recaps, live Corpus, World Graph, database, or 5202/5204; do not restart or switch the serving source. No provider calls.

## Predecessor state

PR #1255 (`INGEST: make recap derivative reruns provenance-safe`) head `9dc85143f301183c25a03f3914661187aecdf8a1` is an ancestor of the fetched main base. Its source-aware derivative and fail-closed Graph-readiness behavior is present in this base. The previous status in this handoff named the old branch/base and prohibited UI changes while #1237 owned them; those coordinates are superseded by this successor. Keep #1255's verification record below as predecessor evidence, not as verification of this slice.

## Mission

When a canonical recap has a generic title but the operator supplies a specific non-generic recap title or slug, status inspection and normalization must use that explicit input consistently to compute expected normalized content and its provenance. A valid existing derivative must no longer be reported as unknown solely because the source frontmatter title is generic. Stale, edited, or conflicting derivatives must remain visible and preserved until an explicit safe refresh.

The Session 10 rendered observation that motivated this successor showed canonical `title: "Session 10 - Recap:"`, an existing normalized recap titled `Session 10 - Festival Crafting Elementals` whose `normalized_from` points to that canonical file, and UI status `normalized_provenance_unknown` / `derivative_reconciliation_required` with graph preview blocked. The UI supplied the specific session title, but provenance inspection rejected the canonical title before using it. This observed source is evidence only; never modify it as part of this slice.

## Contract and invariants

- Canonical recap bytes remain the prose/source authority and are never rewritten by this slice.
- For a generic canonical frontmatter title, use the explicit non-generic title/slug from the request as a deterministic normalization input. Expected-output calculation, `inspect_status`, and explicit normalization must use the same effective title and normalization inputs.
- Recompute the complete deterministic expected derivative from the canonical source bytes, explicit normalization inputs, and current normalization schema, then compare all output bytes. A matching filename or self-reported output frontmatter alone never establishes provenance.
- A non-generic canonical title is authoritative. If a supplied non-generic title conflicts with it, fail closed with an actionable reconciliation status; do not silently override the canonical title or mark an unrelated derivative current. A slug without a title is a path hint and yields to a disk-resolved canonical/normalized pair, preserving the existing disk-chain resolution behavior.
- Preserve mismatched, edited, stale, and unverified derivatives by default. Existing explicit refresh/archive semantics remain intact.
- Status inspection must be read-only and must not call providers. Status and execution must agree on whether the derivative is current.
- No broad UI redesign or copy changes are included. Fix the source/provenance contract at the owning backend boundary.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-rerun-source-lineage.md`
- `src/live_play/recap_ingest_pipeline.py`
- `src/live_play/recap_ingest_status.py` (only if the owning status calculation requires it)
- `apps/live_control_server/routes/recap_ingest.py`
- `tests/test_live_recap_ingest_pipeline.py`
- `tests/test_live_recap_ingest_api.py`

No other paths are leased. Return for an explicit extension if another path is required. Do not touch the parked `stash@{0}` or other worktrees.

## Acceptance and failure cases

- On a disposable corpus, a generic canonical title plus an explicit specific title produces the exact expected normalized bytes; status reports current only when installed bytes match those bytes.
- A stale normalized body remains stale and is preserved by status inspection and ordinary rerun.
- A specific canonical title that conflicts with the supplied title/slug yields an actionable reconciliation result; neither source nor derivative is silently rewritten or accepted as current.
- Status and execution use identical effective title and deterministic normalization inputs, with matching digests for the same canonical bytes/request.
- Repeated unchanged status inspection performs no writes and no provider calls.
- An explicit permitted normalization refresh uses the same effective inputs, preserves the existing archive contract, and never changes canonical source bytes.

## Verification and release boundary

Implemented and verified on this lease:

- The pipeline suite plus the focused route-dispatch status check pass: 34 tests total, using disposable corpora. Coverage includes creating and reusing the exact derivative from a generic canonical title, read-only status and matching digests, preservation of stale derivative bytes, fail-closed specific-title conflicts, and source-byte preservation.
- Python `compileall`, cumulative `git diff --check`, and Ruff formatting checks for the changed code ranges pass. Ruff reports the same seven pre-existing findings as `origin/main` on these files (import ordering, three `datetime.UTC` suggestions, and two unused unpacked test variables); no new Ruff findings are present.
- The full ASGI/TestClient suite could not be verified in this checkout: `uv run` cannot build the environment because the local `out/hermes-agent` distribution is absent and package DNS is unavailable. Using cached dependencies, even a trivial FastAPI `TestClient` request hangs; direct dispatch through the Ingest route passes. Treat rendered/full API acceptance as outstanding.
- No retained recap, live Corpus, World Graph, database, provider, or serving runtime was modified. 5202 remains untouched.

The cumulative base-to-head diff is ready for independent PRIME review. Do not claim rendered end-to-end ingestion readiness from these backend checks; a later operator witness may verify the coherent flow without asking them to edit or submit this real recap.

## Predecessor verification — PR #1255

The #1255 implementation reported 137 passing tests across provenance, pipeline, seed, materializer, corpus-writer, and API suites; Ruff and cumulative diff check passed. Tests used disposable corpora. The PR did not alter retained recaps, live Corpus, providers, database, World Graph, or serving runtimes. Rendered Ingest acceptance remained outstanding. This evidence belongs to that predecessor and does not substitute for the successor checks above.
