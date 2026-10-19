# PLAY: durable Run-local content editions

Status: SETTLED — server PR #1422 merged as `7b73ffb07d21899c9007035a4b93ee9dcd455d18`, Architecture cycle 1 PASS on `6080d1a306aa96a404d19c9f5f108c37e30b81e1`. PRIME completed the separately owned schema/runtime adoption. UI/Agent adoption and Live editing remain successor work.

## Lane and ownership

Base origin/main 3dfa43f946837d4ffb1a1a1d3c84b33d497e0b31, migration head 20261018_0034. Re-fetch/check before changes. Serial one PR on codex/play-run-content-editions in existing buddy-context-loop checkout. PRIME transfers exclusive implementation ownership of this checkout and paths below to DOGFOOD for this slice; ROOT and Architecture read/review only until worker releases it. The 996b checkout remains frozen with its unique edits preserved; do not reset, rebase or develop there. No new checkout, source export or environment, no /tmp task directory. Existing dependencies reused. Current media PR1421 merged3dfa43f94 and its lease ended; floating notes1420 settled09b1b3de. Prior historical Play service/route reservations superseded for these exact paths under current operator authority; preserve old branches and unrelated work. No other worker is active on these paths per current PR/agent census; recheck on actual collision.

## Exact expected writes

- This handoff.
- src/application_state/authority.py and tests/application_state/test_application_state_authority.py (PRIME amendment: include both edition tables in the stable recovery fingerprint; prove content/receipt sensitivity and restored parity only).
- New src/application_state/play/edition_types.py, edition_repository.py, edition_service.py.
- New apps/live_control_server/services/play_run_edition.py and play_run_edition_structure.py.
- apps/live_control_server/routes/play_runs.py (new edition routes only).
- src/application_state/play/service.py (edition-bearing rebase guard only).
- New src/application_state/migrations/versions/20261018_0035_play_run_editions.py (only if0034 is still sole parent).
- New tests/application_state/test_play_run_editions_postgres.py.
- New tests/test_world_play_run_content_api.py and tests/test_play_run_edition_structure.py.
- tests/application_state/test_play_runtime_world_runs_postgres.py (edition rebase guard/compatibility assertions only).

Any additional path is a scope/collision return to PRIME before editing. No frontend/types/media/Agent/provider/content-domain generic writer, fixture-global or dependency edits. Do not edit unrelated files, update lockfiles or weaken existing tests to pass.

## Storage and authority

Reuse Play unit_of_work, lock_run, exact pinned-revision ownership/integrity and current canonical playable derivation. Do not disguise a session edition as the originating Plan or a legacy Runbook or widen AdmittedKind. Add two Play-owned tables: run_edition (Run FK/World, immutable accepted-origin tuple, grammar v2, origin structure SHA, current edition head and creation time); run_edition_revision (Run/revision PK, unique revision UUID, previous same-Run revision, exact Markdown UTF8 and hash, server time, unique Run/command UUID and canonical request hash, expected base and observed Run revision). Enforce same-Run head/chain with DB constraints and service integrity checks. Repositories never commit. Edition history is immutable through product APIs; no delete/reset endpoint.

Before first edit, effective edition is revision0 = exact retained Run pin, never latest Plan. Reads do not create copies. For previously rebased Runs, origin is their current accepted pin when first edited; do not invent unavailable creation history. First actual accepted content edit creates revision1, later commits append. Preserve original Run playable_* fields and sealed manifest. Freeze origin once edition exists; reject rebase for edition-bearing Runs inside the existing locked transaction, including calls through legacy/campaign entry points. Non-edition rebase remains unchanged. Edition writes do not increment Run progress revision or alter notes/choices/current scene; note/progress writes do not stale edition content CAS. Existing World v2 Plan- and Runbook-backed Runs supported; v1/campaign edition writes explicitly unsupported and unchanged in legacy reads.

## API contract

All new routes under /api/live/world-play-runs/v2/{run_id}, with exact World selector and explicit local GM authentication on new content/history/command endpoints (use existing enforce_native_graph_gm); do not imply public/tenant auth.

- GET /content?world_id=W: dmb_world_play_run_content_v1 with World/Run, origin tuple (artifact ID, revision N, WorkRevision ID, SHA), source pinned|edition, edition revision0-or-positive, nullable edition revision UUID, exact Markdown/hash, server committed time, observed Run revision and structural SHA.
- GET /content/revisions/{revision_n}?world_id=W: origin at0 or exact immutable edition; owner fenced.
- PUT /content/commands/{command_id}?world_id=W: strict dmb_world_play_run_content_commit_v1 body: expected_origin tuple, expected_edition_revision, expected_content_sha256, exact Markdown. No extra fields; canonical IDs/digests, body max1MiB UTF8.
- GET /content/commands/{command_id}?world_id=W: exact accepted receipt, or404 if absent. Receipt dmb_world_play_run_content_receipt_v1 includes command/request hash, World/Run/origin, expected base, accepted edition revision/UUID/hash/server time and observed Run revision. Include exact accepted content or make it available by immutable revision GET.

Canonical request digest covers schema, World, Run, command, origin, expected revision/hash and exact Markdown via unambiguous canonical JSON. Same command+same payload returns the SAME durable receipt after later edits/progress; same command+different payload409. Check replay after owner/pin integrity but before stale-head CAS. A lost response is reconciled by same command/identical bytes or command GET, not a fresh command.404 is absence at that read, not proof an in-flight command cannot still commit. No-op content returns422 without edition or receipt creation.

## Transactions and structure

One UoW: lock Run FIRST, verify exact World/pin/manifest integrity, then lock edition if present; replay lookup; expected-origin and edition revision/hash CAS; validate candidate; insert revision + head atomically. Concurrent first edits yield one winner or same-command replay. Rollback on any partial failure; progress/rebase races serialize on same Run. Do not use extra client locks as the owning invariant.

Guard against the ORIGIN and sealed manifest, not current Plan. Existing set-based membership comparisons alone are insufficient. Derive a canonical ordered signature preserving all Beat/Scene/Choice/Option IDs/order/parents/beat_kind/activation/suppression edges and actual attachment boundaries. Reject add/delete/duplicate/ID rename/reparent/reorder/edge changes, mixed/changed grammar, and markers swallowed by code/quotes. Preserve frontmatter/structural marker envelopes; titles and body content may change. Use existing owning parser/derivation; no regex patching of canonical content or client JSON trust. Ordinary unmarked headings cannot alter attachment interpretation unnoticed. Pure guard lives at the service/parser boundary, with domain service invoking it as current Play patterns permit.

Supported edits cover existing grammar prose/tables/callouts/media references/order/width/authored collapse. This server slice is not a port of all JS semantic Markdown admission. Store bounded exact bytes and protect Run structure; later editor must retain renderability admission. Do not claim arbitrary Markdown or metadata mutation supported. No provider/CDN calls, asset creation/deletion, Graph claims/publication or scene restructuring.

## Integrity, migration and rollback

Effective reads verify stored origin/head/chain/content hashes and structure; corruption fails closed, never falls back silently. New APIs coexist with unchanged legacy Run/manifest/progress DTOs, so server merge does not claim UI/Agent adoption. Agent still sees original pin until later explicit edition-aware context work; do not misrepresent it.

Additive migration after0034; no eager copy/backfill or existing row rewrite. Downgrade refuses when edition history/receipts exist. Existing Runs/notes stay unchanged after upgrade. A future live adoption needs backup/schema/runtime alignment and a compatible rollback strategy: an old binary ignores editions, so do not call old-UI rollback full continuity after edits exist. No serving DB migration, service restart or live data writes in this implementation slice.

## Verification and completion

Use existing disposable PostgreSQL fixtures against established fixture port54329; no production database. Reuse known runtime/libraries; no environment install by default. Fresh unique synthetic DB per test, guaranteed cleanup; do not put new task files under /tmp (set TMPDIR to the established private /home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016 location if library temp paths are needed).

Required owning proofs: real PostgreSQL Plan and Runbook sources -> exact Run -> initial note/progress -> Plan changes -> Live first edit still bases on Run pin; only edition rows change. Other Run and Plan working/committed state + original Run/manifest remain unchanged. Version2/fresh-service/history reads; replay receipt1 after version2; concurrent first commits and same-command races on real connections; stale revision/hash, command mismatch, rollback fault injection; races with progress and rebase; wrong owner/origin/grammar; no-op/strict/size constraints; corrupt head/chain/hash; migration old-Run compatibility and data-preserving downgrade refusal. Structural negative cases cover every ID/order/parent/edge/attachment invariant and positive Markdown/table/callout/media edits. Actual HTTP/ASGI API proof for auth, ownership, commit/read/replay/history backed by real persistence, plus legacy Play/progress/rebase/manifest tests. Report missing proof/skips honestly; do not claim mocks prove database or HTTP behavior.

Inspect cumulative diff, commit intended changes, push and open ONE PR; include exact base/head, gates and evidence. Architecture independently reviews; PRIME alone merges and owns runtime delivery. No blanket success or full-goal completion. Report back here when PR ready, blockers concrete, or path change required. Do not message other chats without separate operator authorization; PRIME coordinates review.

PRIME verification clarification: port 54329 is the existing dungeonbuddy-review-fixture-pg container. Use only fixture-created unique dungeonbuddy_app_state_test_<uuid> databases with guaranteed cleanup. No existing database or container changes. Plan replaces the retired Prep surface; legacy Runbook APIs/storage names are unchanged.

## Implementation / review checkpoint

The server implementation was independently reviewed and merged; the subsequent PRIME-owned runtime adoption is recorded below.
The edition transaction locks the Run first, verifies the retained origin and
sealed v2 manifest, checks every stored chain/content/request hash, then resolves
command replay before testing the current content CAS. All content writes use
only the two Play edition tables. The existing Run pin, manifest, progress,
notes, originating Plan/legacy Runbook and other Runs remain unchanged.
The rebase guard lives in the common locked service path. Repositories do not
commit. Ordered guard admission also preserves unmarked top-level heading
boundaries and exact frontmatter (including a leading BOM); it intentionally
is not general Markdown/editor admission.

Verification in the existing fixture container on 54329:

- Corrected-runtime broad Play/World/manifest/rebase/migration/recovery run:
  **183 passed, 1 deselected**. The deselected latency benchmark creates a
  historical worktree and is outside this slice's permitted execution model.
- Final owning suite after the exact-byte/BOM and static-SQL refinements:
  **83 passed** (structure, real PostgreSQL editions/concurrency/recovery,
  authenticated ASGI production routes, and authority fingerprint/restore).
  This includes separate-process history/receipt recovery; Plan and legacy
  Runbook controls; first-edit/rebase/progress races; same-command races/replay;
  stale origins/bases, fault rollback, same-Run FK constraints, corrupt pins,
  head/chain/digests, no-op/strict/body bounds and exact UTF8/CRLF readback.
- Actual `pg_dump`/`pg_restore` run through `docker exec` in the already-existing
  `dungeonbuddy-review-fixture-pg` container copied only fresh synthetic fixture
  DBs. Restored fingerprint parity includes both edition tables. Production
  backup transport is unchanged; no host tool installation or container change.
- Existing v1 fingerprint envelopes remain readable. Older envelopes omitting
  edition domains fail parity deliberately, even when the envelope schema is v1.
- Ruff and cumulative diff whitespace checks pass.

Evidence retained in the existing private directory
`/home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016`:
`play-editions-verification.log`,
`play-editions-corrected-runtime-verification.log`, and
`play-editions-final-owning-verification.log`.
The first run reused an older dependency set: 174 passed, 9 full-app import errors
because its GenerationEngine lacked `ImageOptions`, and one historical latency
helper failure from missing Alembic in its child process. That helper unexpectedly
created a temporary historical worktree; its finally cleanup removed the worktree
and synthetic DB. This was an execution mistake, not a capability requirement;
it was excluded from the corrected-runtime run and is not rerun.
The compatible existing `buddy-main-a044ac4e/runtime/bin/python` then passed the
broader tests with explicit assigned-checkout PYTHONPATH and private TMPDIR.
No dependency/environment changes were made.

The implementation worker performed no serving schema migration, service restart, real content write, provider/Graph or media-asset mutation. The frozen 996b checkout was not changed.
UI and Agent context remain edition-unaware until a later separately bounded
adoption; no full shared-writing-goal completion is claimed here.


## PRIME delivery receipt — 2026-10-18

PRIME reports the reviewed nine Python files adopted in the existing API root,
APP-STATE schema 0035 on the owned 54331 authority, healthy API behind 5202
(checkpoint PID 1593413), and restart retention of all edition tables/history/
receipts. Backup digest begins `9b9b516f`; actual restore and clone-upgrade proof
preserved prior rows. Authenticated 5202 current/history GET succeeded; absent
auth returned 401 and wrong World returned 404.

The existing disposable Run `1beaf255-56b1-438f-8062-176bd223ca19` has two
editions; latest content SHA256 is
`3d65db8a54b5feaed9bcb1386caced386854d9b8dcca17228861e689a919c9cd`.
Exact command-1 replay after edition 2 succeeded. Its originating Plan 3aa3
snapshot and entire fixture Run pin/progress/notes, plus the real Edge Run,
were unchanged. No provider/Graph or new real content writes occurred.
The transient unit disappeared on stop and PRIME recreated it using the same
bootstrap settings; a repeated restart succeeded. This is a dated receipt,
not a new worker runtime lease.

Evidence in the established private directory: `run-editions-server-adoption.json`,
`run-editions-adoption-preservation.json`, `run-editions-http-proof.json`.
The UI still uses the original pin until the separately active effective-content
projection successor is accepted. The full Live editing goal is not complete.
