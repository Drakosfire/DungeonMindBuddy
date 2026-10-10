# HANDOFF — SERVER source admission replay

**Status:** ACTIVE implementation lease from PRIME on 2026-10-10; implementation ready for PRIME's independent review. PRIME owns review and merge.

**Authority:** Buddy `origin/main@6a58b18897bcba506e725a57d1edaa910855cccf`, after #1069. [PRIME's exact lease](https://github.com/Drakosfire/DungeonMindBuddy/pull/1069#issuecomment-6098107030) governs this branch, `codex/server-source-admission-replay`, as one serial PR against `main`. Relevant open PRs have no leased-path collision. The architectural ruling requires a full stored-pair identity proof before replay; pair existence alone is insufficient.

## Primary question

Can a confirmable recap source whose artifact/revision pair already exists in DungeonMind be replayed from a separately byte-verified local input without issuing Core puts, changing catalog metadata, or substituting the local mirror URI for the catalog locator in sealed citations?

## Bounded implementation

Expected writes are the source-admission adapter and port, candidate-admission service, extract-promote prepare, governed-write reproof, their three focused test files, and this handoff. The source adapter resolves catalog-aware collision IDs, reads the stored pair, and compares its World/campaign, mapped source domain/protection/body, current revision, and SHA-256 identity. A complete match reuses the pair without Core puts. A missing pair follows first admission. Partial pairs, changed material fields, and unverified alternate URIs fail closed. Catalog-only metadata is preserved. Confirm re-proves the sealed catalog fingerprint and locator.

The candidate producer verifies local bytes, then seals the catalog revision locator into accepted assertions and the reconstructed contribution while retaining the local URI solely as the byte-verification input. This keeps the source admission pair and contribution citations aligned with DungeonMind. There is no Core/catalog rewrite, private C1 call, provider/runtime change, or unrelated Graph feature.

## Stop conditions and acceptance witness

Stop if a Core schema/API change, a path outside the lease, or a second independent capability is needed. Accept only with: zero puts on an existing complete pair; a verified local mirror preserving the catalog URI in the sealed effect and reconstructed contribution; missing pair admission; partial/material drift rejection; collision mapping; and confirm-time reproof. Verify through focused synthetic tests and a disposable PostgreSQL read-only replay. Review the exact base-to-head cumulative diff and check the unchanged dependency lock.

## Implementation and evidence

Implementation base: `6a58b18897bcba506e725a57d1edaa910855cccf`. Implementation code commit: `033a2d96bc15c16db28be6e57eb432f8b77db27b`. The final handoff commit's head is recorded in the PR handback because this file cannot name its own commit.

- Focused source admission, candidate provenance, extract-promote target, candidate contract, and source-to-contribution suites: **103 passed, 5 deselected**, one existing Pydantic `schema` warning. Deselections: three D.3A tests require `DMB_CUTOVER_TEST_DATABASE_URL`, one integration producer binding test requires the same variable, and one inherited source-pin fixture fails because its synthetic native result lacks `objects` in unchanged `world_graph_reads.py`.
- One disposable pgvector PostgreSQL catalog was seeded with the source pair, switched to database-default read-only mode, then replayed from an alternate verified URI. Replay succeeded with the original locator and fingerprint; Core puts would have failed under the read-only setting. The disposable database was removed. An initial non-pgvector local PostgreSQL attempt could not run Core migrations because its server lacks the `vector` extension; its disposable database was also removed.
- `uv lock --check` passed after linking the already prepared ignored Hermes source from the previous isolated worktree; the committed lock and dependency pins did not change. Changed-file Ruff and `git diff --check` passed. The inherited source-pin fixture failure was observed on the first focused run and its failing files are unchanged by this PR.
- A direct read-only PostgreSQL replay witnesses the Core catalog boundary. The larger D.3A publication fixtures were attempted with local PostgreSQL but stopped at their explicit missing `DMB_CUTOVER_TEST_DATABASE_URL` precondition; they are not claimed as passing.

No rollout or merge performed. PRIME owns exact-head review and merge.
