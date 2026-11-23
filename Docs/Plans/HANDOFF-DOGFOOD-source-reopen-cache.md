# DOGFOOD: reuse immutable source parsing during citation reopen

ACTIVE, Alan authorized4459 latency fixes and deployment. DOGFOOD owns this bounded
Buddy composition change; Core's existing cache/access contract is unchanged.
Stacked implementation/serial delivery, parent4500 exact
173c8c6a7675084a4692739ab0d6c81d50f64e60; branch
codex/dogfood-source-reopen-cache, same isolated checkout. Merge order4484(merged),
4496,4499,4500,this PR. No runtime write lease. Prior source is frozen for exact
qualification in separate clean clones; no other writer owns these paths.

Outcome: default source-context preparation adopts the same existing
verified immutable-revision and parsed-revision caches already used by Plan.
Each call still resolves the current managed binding and principal, opens a NEW
Core access/source view and refreshes source withdrawal/access epochs. Never cache
an access context, principal, grant, mutable head or unavailable result. Explicit
trusted repository/parser dependencies retain their current behavior. No body
acquisition, new data/cache contract, provider/model, prompt or migration change.

Exclusive writes: this handoff; native_corpus_source.py only default repository/
parsed-cache composition; tests/test_native_corpus_source_access.py for actual
Core warm-cache/new-principal/source-withdrawal/new-head/binding proof. No Core,
locks, capacity, semantic routing, citation identities, frontend or unrelated
source publication changes. Existing Plan composition remains unchanged.

Validation: actual Core cache reuse shares only immutable parsed revision;
new access/source views and principals for each call; withdrawal after warm cache
refuses existing source, latest revision changes, foreign/player/binding denial
before body access. Existing source-access, direct-source and citation reader
contracts plus full retained-page HTTP/save. Exact-source owning backend suites,
frontend verifier and independent review before merge. Unpatched real-provider
page replay measures draft/save separately, no-search and source semantics, and
final deployment must preserve current serving5647/0192 and coordinated schema
lineage. No prototype performance result substitutes for exact product evidence.

Diagnostic scope correction: the first implementation also selected the read-only
repository connection factory. That unplanned connection-policy change broke
ordinary source-reader dependency seams (direct-support reopen409). Keep the
existing repository factory/connection policy and add only its already-supported
immutable verification cache plus parsed cache. Source preparation remains a read
operation; this slice grants no write or role change. Retain the43pass/1failure
diagnostic, and rerun source/direct-source access after this correction.

Corrected working-tree source/direct checks:81 passed,1 inherited batch-full-read
failure,14 warnings in60.44s. The sole failure ID is in the exacta5c baseline's
32 retained failures; do not call the full diagnostic green. Warm parsed-cache
reuse, distinct fresh principals/access views, withdrawal refusal, latest head
change and pre-repository foreign/player/binding denials all pass. No new source
or provider IO is supplied by the cache. Exact-head qualification remains pending.
