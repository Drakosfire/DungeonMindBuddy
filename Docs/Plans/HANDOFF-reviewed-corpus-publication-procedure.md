# INGEST — retire the classic corpus publication CLI

Status: ACTIVE under PRIME’s operator-authorized cleanup goal, 2026-11-04.
Owner: PRIME. Topology: serial, no unmerged parent.
Base: `704b46ebb874e5793d1643a3bda55e6f4fa284b9` (remote main after
merged/delivered description-extent fix #2070).
Lane: `codex/retire-classic-corpus-cli` in the existing Buddy checkout.

## Outcome and boundary

Remove the CLI-only classic publication procedure. It still reads source bodies
from local files and calls classic review finalization/materialization/publication.
No product route imports it. Retained Elderwyld publication uses the existing
native source admission and exact WorldKeeper preparation/confirmation routes.
No new publication path or compatibility command replaces the retired CLI.

Keep `reviewed_corpus_publication_store.py`: native recap source admission uses
its local mutex. Native source intent and receipts remain database-authoritative.
Do not change its schema, locks, recovery behavior, source admission, WorldKeeper
contracts, databases, source/candidate bytes, retained receipts or user drafts.

## Exclusive expected write set

- `apps/live_control_server/services/reviewed_corpus_publication.py` (delete)
- `scripts/resume_reviewed_corpus_publication.py` (delete)
- `tests/test_reviewed_corpus_publication.py` (delete retired-path tests)
- `tests/integration/test_reviewed_corpus_publication.py` (delete retired-path tests)
- `.github/workflows/world-ownership-core.yml` (remove deleted-file entries)
- `Docs/Plans/HANDOFF-reviewed-corpus-publication-procedure.md` (this contract)

ADVERSARY’s merged #2068 reasoning and #2070 description-extent changes are inherited and disjoint. No runtime, database or port
lease is required for code edits. Verification may create only fixture-named
disposable APP test databases on the existing review-fixture service at 54329
and `dmb_recap_source_test_*` Core fixture databases on the existing vector
server at 54330. Never connect tests to a retained database. The 54329 server
is plain PostgreSQL and cannot initialize Core’s vector extension. Use Core
migrations from the exact installed `466c5433e103f474b431d2a4a2632877f60ff45d`
UV cache checkout, not a mutable unrelated Core checkout.

## Verification and delivery gates

Trace all imports/commands/CI callers, then remove the entire unused procedure.
Run native preparation tests plus ordinary native admission, process contention/
crash recovery and read-only status tests using disposable APP/Core fixtures.
The active source-admission lock store must still work. Inspect the cumulative
six-path diff, obtain independent Bugbot review and pass applicable CI before
merge. Re-anchor before merge and settle delivery under standing PRIME authority.
No provider calls, fresh ingestion or retained-data migration are needed.

The former procedure and its historical settlement evidence remain in Git at
this document’s parent revision. This retirement does not delete stored evidence
or claim ingestion/answer quality or complete semantic corpus coverage.

Author verification: 135 native preparation tests passed; 3 actual native
admission/status/process-crash recovery tests passed with disposable APP/Core
databases and exact installed Core migrations. The initial plain-PostgreSQL
fixture attempt failed during schema setup (`vector` unavailable); the corrected
fixture run passed without changing product code. Remaining symbol search finds
no procedure/CLI caller; the native source-admission progress-store import remains.
CI workflow YAML parses. Independent review and CI remain merge gates.

Re-anchor after #2068: the same six-path deletion is based on its delivered
merge, not the earlier main. All 138 native preparation/admission/status/crash
checks passed again on this base. Independent exact-head review and CI are
required for the rebased cleanup head.

Re-anchor after #2070: the six-path CLI retirement now inherits the delivered
exact description selector. All 169 refreshed native preparation, actual
admission, process crash/recovery and read-only status checks passed, including
the inherited real Core PostgreSQL extent-persistence test, with disposable
fixtures and the exact installed Core migration source. The earlier 138-test
result remains historical. Exact-head review and CI are required on this base.
