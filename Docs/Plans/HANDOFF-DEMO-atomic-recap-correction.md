# DEMO: atomic recap semantic correction

Status: ACTIVE source implementation; PRIME activation 2026-10-08.
Base: 6d495773e0086543e0340b34bc91da38ba3a2006.
Branch: codex/demo-atomic-recap-correction. Topology: serial, one source PR.
Checkout: /home/drakosfire/.codex/worktrees/demo-plan-cards-url-reopen/DungeonMindBuddy.

Deliver one additive atomic held-child batch through the existing correction route,
canonical APPSTATE lifecycle, immutable manifest/replay and semantic decision boundary.
Bounds: 8 descriptions, 4 labels, 2 edge tuples, 2 one-to-one evidence refs,
3 edge omissions, 19 total. Exact parent/source/index/profile pins and original
preimages; derive evidence locators from frozen spans. Preserve V1–V6 behavior.

Write lease:
- apps/live_control_server/models/extract_promote.py
- apps/live_control_server/routes/extract_promote.py
- apps/live_control_server/services/extract_promote.py
- apps/live_control_server/services/recap_semantic_candidate_correction.py
- apps/live_control_server/services/recap_semantic_disposition.py
- src/application_state/ingest/service.py (new basis only, explicit owner transfer)
- tests/test_recap_semantic_candidate_correction.py
- tests/test_recap_semantic_disposition.py if needed
- tests/application_state/test_ingest_run_postgres.py
- Docs/Plans/HANDOFF-DEMO-atomic-recap-correction.md

No schema/storage framework change, provider, service startup, data execution,
World binding or Graph admission. S28 batch execution requires separately pinned
accepted source; existing original package and held quote child remain immutable.

Verification: exact cumulative diff; mixed batch mounted route/canonical lifecycle,
zero persistence on invalid or stale operations, deterministic repeat/replay,
canonical source-open locators, final tuple/native-kind/ref/duplicate checks,
explicit semantic hold and decision basis fences, V1–V6 regression suite.
Technical completion travels through one PR to independent ARCH review/PRIME merge.
No source or graph-semantic acceptance is inferred from a valid evidence quote.

Local verification: 120 correction/disposition checks passed. The complete
19-operation S28 recipe replayed in memory to candidate SHA
9b6d97af3eec2dfb610af287a4fef5cd296754fd665310070fbf9651766ff2f6.
No S28 child was created with this source. Targeted disposable PostgreSQL basis
verification and independent ARCH review remain pending at source publication.
