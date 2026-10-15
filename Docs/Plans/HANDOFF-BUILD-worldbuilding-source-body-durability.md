# BUILD: preserve worldbuilding source bytes for historical passage reads

**Status:** COMPLETE — Buddy PR #1185 merged at reviewed head `8f0d4cf980dc1b99751199f4ef1d3ac63f8e72c8`; merge commit `bef840c1d57dc58b52fb97217631a500e9ff6553`. PRIME implementation; ARCHITECTURE exact-head review passed.

- **Base:** Buddy `main@199a7404701d6a53fa8f4a1d68b2c7874df6771a`
- **Branch:** `codex/mirathorn-worldbuilding-source-durability`
- **PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/1185
- **Runtime:** none; no serving ports or operator databases

## Outcome

Build now adopts the exact committed Markdown bytes of a registered worldbuilding source into the existing immutable `source.revision` authority before canonical extraction-run creation. An admitted World Graph source-anchor read can use the exact stored body to rebuild the deterministic paragraph-span index and open the requested span after the source changes or local derived snapshot/index files disappear. It never substitutes the latest workspace text.

This strengthens historical source access using the existing storage contract. It does not make APP-STATE the authority for the Build document itself, source-catalog admission, graph facts, graph publication, or World selection.

## Invariants delivered

- The stored text is loaded from the registered source artifact and rehashed before persistence; the artifact digest is an assertion, not a replacement for hashing.
- Persistence is idempotent for the same artifact and digest. Different content remains a distinct immutable revision.
- Reads bind exact artifact ID and digest and verify `source_domain`, `campaign_id`, `session_id`, `world_id`, media type, encoding, and body hash against the registered artifact.
- World Graph passage reads validate Build ownership from registry metadata only; they do not require the mutable current Markdown file to remain present. The Build editor and stale-source navigation keep their existing current-file checks.
- Paragraph spans are deterministically reconstructed from the exact immutable Markdown. Span identity, line range, and digest must match the requested admitted span.
- Existing file-backed reads remain available when no durable body exists. Missing or changed files never authorize a read from the current workspace revision.
- Existing WorldGraph source admission, managed-to-native binding, evidence visibility, graph revision, and publication authority are unchanged.

## Verification and independent review

- PRIME: disposable PostgreSQL owning-boundary suite — 50 passed; Ruff and `git diff --check` passed.
- ARCHITECTURE: exact-head independent review found no production defects; 54 focused tests across its reviewed suites passed.
- The witness adopts one exact revision idempotently, saves a newer workspace revision, deletes the current source file and local frozen/index files, then opens the original passage in-process and in a fresh process with the original span ID, text, line range, and digest.
- Identity, scope, body, digest, missing-body, and persistence-before-run failure cases are covered.
- No provider calls, retained World publication, corpus edits, runtime restart, or operator-database changes.

## Limits and next gates

This closes only the source-body durability slice. It does not retroactively adopt existing pre-PR worldbuilding artifacts; those may continue using the verified file-backed path. It does not prove APP-STATE backup/full-stack restart recovery, source-catalog admission, Mirathorn extraction quality, publication, ordinary multi-hop Agent answers, or operator acceptance. The broader PRIME Mirathorn lifecycle goal remains active.

The implementation lease is released. Follow-on changes require a new bounded handoff and exact base/write set.
