# PLAY: durable Run-local content editions

Status: ACTIVE. PRIME adopts Architecture's current-code examination and the operator's decisions: Live edits save to this session's copy; Prep stays unchanged; first release edits within existing scenes. This is a server-only capability, followed by a separately bounded Live editor adapter. No serving migration or runtime adoption is authorized by this implementation lease.

## Lane and ownership

Base origin/main 3dfa43f946837d4ffb1a1a1d3c84b33d497e0b31, migration head 20261018_0034. Re-fetch/check before changes. Serial one PR on codex/play-run-content-editions in existing buddy-context-loop checkout. PRIME transfers exclusive implementation ownership of this checkout and paths below to DOGFOOD for this slice; ROOT and Architecture read/review only until worker releases it. The 996b checkout remains frozen with its unique edits preserved; do not reset, rebase or develop there. No new checkout, source export or environment, no /tmp task directory. Existing dependencies reused. Current media PR1421 merged3dfa43f94 and its lease ended; floating notes1420 settled09b1b3de. Prior historical Play service/route reservations superseded for these exact paths under current operator authority; preserve old branches and unrelated work. No other worker is active on these paths per current PR/agent census; recheck on actual collision.

## Exact expected writes

- This handoff.
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

Reuse Play unit_of_work, lock_run, exact pinned-revision ownership/integrity and current canonical playable derivation. Do not disguise a session edition as a Prep runbook or widen AdmittedKind. Add two Play-owned tables: run_edition (Run FK/World, immutable accepted-origin tuple, grammar v2, origin structure SHA, current edition head and creation time); run_edition_revision (Run/revision PK, unique revision UUID, previous same-Run revision, exact Markdown UTF8 and hash, server time, unique Run/command UUID and canonical request hash, expected base and observed Run revision). Enforce same-Run head/chain with DB constraints and service integrity checks. Repositories never commit. Edition history is immutable through product APIs; no delete/reset endpoint.

Before first edit, effective edition is revision0 = exact retained Run pin, never latest Prep. Reads do not create copies. For previously rebased Runs, origin is their current accepted pin when first edited; do not invent unavailable creation history. First actual accepted content edit creates revision1, later commits append. Preserve original Run playable_* fields and sealed manifest. Freeze origin once edition exists; reject rebase for edition-bearing Runs inside the existing locked transaction, including calls through legacy/campaign entry points. Non-edition rebase remains unchanged. Edition writes do not increment Run progress revision or alter notes/choices/current scene; note/progress writes do not stale edition content CAS. Existing World v2 Plan- and Runbook-backed Runs supported; v1/campaign edition writes explicitly unsupported and unchanged in legacy reads.

## API contract

All new routes under /api/live/world-play-runs/v2/{run_id}, with exact World selector and explicit local GM authentication on new content/history/command endpoints (use existing enforce_native_graph_gm); do not imply public/tenant auth.

- GET /content?world_id=W: dmb_world_play_run_content_v1 with World/Run, origin tuple (artifact ID, revision N, WorkRevision ID, SHA), source pinned|edition, edition revision0-or-positive, nullable edition revision UUID, exact Markdown/hash, server committed time, observed Run revision and structural SHA.
- GET /content/revisions/{revision_n}?world_id=W: origin at0 or exact immutable edition; owner fenced.
- PUT /content/commands/{command_id}?world_id=W: strict dmb_world_play_run_content_commit_v1 body: expected_origin tuple, expected_edition_revision, expected_content_sha256, exact Markdown. No extra fields; canonical IDs/digests, body max1MiB UTF8.
- GET /content/commands/{command_id}?world_id=W: exact accepted receipt, or404 if absent. Receipt dmb_world_play_run_content_receipt_v1 includes command/request hash, World/Run/origin, expected base, accepted edition revision/UUID/hash/server time and observed Run revision. Include exact accepted content or make it available by immutable revision GET.

Canonical request digest covers schema, World, Run, command, origin, expected revision/hash and exact Markdown via unambiguous canonical JSON. Same command+same payload returns the SAME durable receipt after later edits/progress; same command+different payload409. Check replay after owner/pin integrity but before stale-head CAS. A lost response is reconciled by same command/identical bytes or command GET, not a fresh command.404 is absence at that read, not proof an in-flight command cannot still commit. No-op content returns422 without edition or receipt creation.

## Transactions and structure

One UoW: lock Run FIRST, verify exact World/pin/manifest integrity, then lock edition if present; replay lookup; expected-origin and edition revision/hash CAS; validate candidate; insert revision + head atomically. Concurrent first edits yield one winner or same-command replay. Rollback on any partial failure; progress/rebase races serialize on same Run. Do not use extra client locks as the owning invariant.

Guard against the ORIGIN and sealed manifest, not current Prep. Existing set-based membership comparisons alone are insufficient. Derive a canonical ordered signature preserving all Beat/Scene/Choice/Option IDs/order/parents/beat_kind/activation/suppression edges and actual attachment boundaries. Reject add/delete/duplicate/ID rename/reparent/reorder/edge changes, mixed/changed grammar, and markers swallowed by code/quotes. Preserve frontmatter/structural marker envelopes; titles and body content may change. Use existing owning parser/derivation; no regex patching of canonical content or client JSON trust. Ordinary unmarked headings cannot alter attachment interpretation unnoticed. Pure guard lives at the service/parser boundary, with domain service invoking it as current Play patterns permit.

Supported edits cover existing grammar prose/tables/callouts/media references/order/width/authored collapse. This server slice is not a port of all JS semantic Markdown admission. Store bounded exact bytes and protect Run structure; later editor must retain renderability admission. Do not claim arbitrary Markdown or metadata mutation supported. No provider/CDN calls, asset creation/deletion, Graph claims/publication or scene restructuring.

## Integrity, migration and rollback

Effective reads verify stored origin/head/chain/content hashes and structure; corruption fails closed, never falls back silently. New APIs coexist with unchanged legacy Run/manifest/progress DTOs, so server merge does not claim UI/Agent adoption. Agent still sees original pin until later explicit edition-aware context work; do not misrepresent it.

Additive migration after0034; no eager copy/backfill or existing row rewrite. Downgrade refuses when edition history/receipts exist. Existing Runs/notes stay unchanged after upgrade. A future live adoption needs backup/schema/runtime alignment and a compatible rollback strategy: an old binary ignores editions, so do not call old-UI rollback full continuity after edits exist. No serving DB migration, service restart or live data writes in this implementation slice.

## Verification and completion

Use existing disposable PostgreSQL fixtures against established fixture port54329; no production database. Reuse known runtime/libraries; no environment install by default. Fresh unique synthetic DB per test, guaranteed cleanup; do not put new task files under /tmp (set TMPDIR to an owning checkout evidence directory if library temp paths needed).

Required owning proofs: real PostgreSQL Plan and Runbook sources -> exact Run -> initial note/progress -> Prep changes -> Live first edit still bases on Run pin; only edition rows change. Other Run and Prep working/committed state + original Run/manifest remain unchanged. Version2/fresh-service/history reads; replay receipt1 after version2; concurrent first commits and same-command races on real connections; stale revision/hash, command mismatch, rollback fault injection; races with progress and rebase; wrong owner/origin/grammar; no-op/strict/size constraints; corrupt head/chain/hash; migration old-Run compatibility and data-preserving downgrade refusal. Structural negative cases cover every ID/order/parent/edge/attachment invariant and positive Markdown/table/callout/media edits. Actual HTTP/ASGI API proof for auth, ownership, commit/read/replay/history backed by real persistence, plus legacy Play/progress/rebase/manifest tests. Report missing proof/skips honestly; do not claim mocks prove database or HTTP behavior.

Inspect cumulative diff, commit intended changes, push and open ONE PR; include exact base/head, gates and evidence. Architecture independently reviews; PRIME alone merges and owns runtime delivery. No blanket success or full-goal completion. Report back here when PR ready, blockers concrete, or path change required. Do not message other chats without separate operator authorization; PRIME coordinates review.
