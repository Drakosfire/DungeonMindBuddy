Upstream activation SHA-256: `1529a19f816f831b44b99c4e9e5ab7c300ef02a8a1c84319af345321c6c230c6`.

Buddy implementation lane: `codex/server-reviewed-corpus-publication` in `/tmp/buddy-agent-source-targets`; initial base `6dd0bda0dc10e65808ad536425ee3a6595d45703`, re-anchored final base `ace0cc21a1030f432d52852db5a51fc6a850c21d` after disjoint citation-append #1100 and APP-STATE #1101, installed Core `d8798a5d5d6b46efa3e485e5b493a8fc3d4a94f7`. Open PR/lease inventory has no collision with these six new paths. RAKE owns S28 and MIND settled S20. No retained execution is authorized.

# SERVER — resumable reviewed corpus publication

Status: REVIEW under PRIME dispatch, 2026-10-12; implementation/evidence ready for independent review, no execution authority. One capability: carry an
unchanged reviewed corpus packet through existing Core source admission,
review finalization and publication, resume by exact receipts, and verify its
readable result without hand-written global table-count expectations.

Authority: re-fetch Buddy main (last observed 6dd0bda0dc10e65808ad536425ee3a6595d45703)
and inspect active leases/PRs before edits. Core dependency remains the merged
d8798a5d5d6b46efa3e485e5b493a8fc3d4a94f7. Runtime implementation belongs to Buddy.
Core owns source/review/publication records, World locks and revision CAS;
Buddy owns managed-World resolution, operational orchestration and readiness
verification. A local progress journal is not another graph or approval store.

Exact write set:

- apps/live_control_server/services/reviewed_corpus_publication.py
- apps/live_control_server/services/reviewed_corpus_publication_store.py
- scripts/resume_reviewed_corpus_publication.py
- tests/test_reviewed_corpus_publication.py
- tests/integration/test_reviewed_corpus_publication.py
- Docs/Plans/HANDOFF-reviewed-corpus-publication-procedure.md

Use existing typed Core APIs and Buddy selected-World/binding resolution.
Accept already-reviewed immutable inputs; never fabricate review authority or
derive approval from a journal flag. Pin managed/native World, binding, source
hashes, profile and expected parent. Persist original operation identities,
input digests and first actual attempt timestamps atomically before dispatch.
Probe exact durable receipts before resuming each stage. Distinguish rejected,
committed and unknown outcomes; stop on changed input, conflicting identity or
parent/source drift without rebase, deletion, rollback or extraction.

Derive expected operation effects from distinct approved evidence/source IDs
and materialization. Unrelated concurrent rows are not automatically defects;
validate this operation and preservation at the owning boundary. Preserve
committed source/review stages if a later stage fails. Do not claim all-stage
atomicity. Published is distinct from query/source verification, and direct
Core verification is distinct from actual selected-World Buddy route readiness.

Schema migration and backup are explicit external prerequisites, not automatic
CLI upgrades. Reuse current Graph/read/source adapters; do not add source
reader, graph store, API endpoint, model call, new semantic adjudication or
runtime launcher. CLI must explain status/next action without secrets or
private corpus bodies. Use synthetic fixtures for committed tests.

Required proof: uninterrupted sequence; exact resume after each committed
stage; unknown-result receipt probe without duplicate effects; changed-input
and stale-parent stops preserving existing work; derived evidence-row effects;
publication receipt plus selected-World query and source-open verification;
no mutations from read-only inspection. PostgreSQL proof uses a separately
named disposable database. No retained authority writes or runtime restart
are authorized by this implementation dispatch.

Evidence: settled Session20 handback at
/home/drakosfire/.local/state/dungeonmind/recovery/native-live-20261011/session20-retained-v1/terminal-evidence.json
and independent read proof /tmp/prime-session20-independent-read-check.json.
These private files are reference evidence; do not commit their bodies.

Complete implementation, focused verification, cumulative diff review,
commit/push/PR. PRIME independently reviews before merge. Rebrief before any
additional path, durable contract or capability. Do not repeat the retained
Session20 operation or commission fresh extraction.

Implementation decisions: existing typed Core submission/policy and source records are accepted unchanged in an internal CLI envelope. The progress file contains only pinned identities/digests/times and observations, never semantic approval or payload bodies. After an unresolved attempted dispatch, a missing receipt does not prove it was unsent: resume probes and stops until an exact receipt resolves the outcome. Schema/backup flags are explicit caller attestations to separately completed prerequisites, not CLI validation or upgrades. Buddy service verification and independent mounted-route test evidence remain distinct; product readiness is never inferred.

## Owning evidence and limits

Focused unit gate: 26 passed. It covers all committed-stage resume boundaries,
source/review/publication lost responses with exact receipt recovery and one
dispatch, unresolved missing-receipt stop, original timestamp/identity retention,
read-only inspection without journal writes, changed packet/body/source authority,
stale parent preserving source/review, prerequisites/selected binding, local
executor exclusion, untrusted journal flags, unrelated catalog rows, derived
unique evidence effects, and CLI private-packet error masking.

Disposable PostgreSQL/mounted route proof: 2 passed, no skips (node/relationship and standing observation-only variants). A separately named
`dmb_reviewed_corpus_test_*` database at loopback 55443 was created, initialized
with exact Core115 migrations as an external fixture prerequisite, and cleaned
after the test. The actual procedure resumes after finalized review, verifies
materialization/publication and immutable input source records, and performs
existing selected-World Buddy service query and digest-bound source opening. An
independent ASGITransport proof mounts existing routes, denies unauthenticated
managed queries, permits the exact managed/native/binding/revision query, and
opens its actual admitted source. This test is not a runtime/operator readiness
claim. An existing Alembic configuration deprecation warning remains.

The initial synthetic graph seed lacked Buddy's required adoption authority; the
fixture now uses Core's existing typed adoption API. Its reviewed evidence now
explicitly pins its source revision and uses the existing heading locator syntax.
No production guard/reader was changed. Changed Python paths pass Ruff. Cumulative
tracked diff is confined to the exact six leased paths; citation-append changes
are inherited only through the new base, not included in this capability diff.
No provider, retained APP/native query/write, private corpus export, fresh
extraction, Session20 replay, production schema migration or runtime restart was
used. No acceptance token is asserted by SERVER. PRIME owns exact-head review.

Updated implementation/test head: `72ece137431da2e84f243870fd3297f04442068d`. The final PR head adds only this exact-head evidence line; obtain that final SHA from the PR handback.

PRIME HOLD `6132919288` on original head `bfd04364` is addressed within the
same six-path lease: accepted applied assertion/session-observation targets are
derived and read through existing complete observation/evidence adapters, with
exact reviewed lineage/text digest/support. Observation-only publications verify
standing subjects/source reads despite byte-identical graph objects and reused
evidence IDs. Every changed relationship must have an enough outcome, exact
requested/returned target and its own admitted support; shared node evidence
cannot mask its absence. Receipt probes precede local source loading on inspection
and committed resume. Missing/changed source after publication reports the
committed publication plus unavailable source, without redispatch; all uncommitted
writes still revalidate immutable source bytes. Positive/negative unit tests and
the observation-only disposable PG/mounted proof pass. No legacy recap-format
reader change or private C1S16 packet is included. APP migration0020 is inherited
from the new base; this procedure accesses Core and file binding authority, not
APP storage, and creates no production migration. Changed-path Ruff and exact
cumulative six-path diff checks pass. Final head adds only handoff evidence.
