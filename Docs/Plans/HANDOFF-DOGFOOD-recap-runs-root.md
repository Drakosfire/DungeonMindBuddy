# DOGFOOD — Confined recap runs root

Status: COMPLETE. PR875 merged at c2d9078b8d700c9a6c3f081d87c50cf7967ddfb5 after independent 28-test verification; no outstanding write lease. Authority: operator ongoing patch-it-up / do-not-ask direction, 2026-10-02. Topology: serial successor to merged PR873 and PR874. Base: fetched origin/main e4d02ca03003877064f7a323a20b8230325d11cf. Branch: codex/dogfood-recap-runs-root. Checkout: /home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy.

Expected write lease: this handoff; HANDOFF-DOGFOOD-restore-recap-entry.md (truthful predecessor settlement); apps/live_control_server/services/graph_ingest_run_registry.py; apps/live_control_server/services/recap_graph_preview_ingest.py; tests/test_recap_graph_runs_root.py; tests/test_live_recap_ingest_graph_preview_api.py (configured-root mounted route witness).

Invariant: recap writer and run discovery share DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT, confined to the owning repository after symlink resolution. Reject file URIs, traversal and external symlink escapes before extraction. Default remains out/graph_memory/runs. Existing shared runtime out symlink is preserved; dedicated runtime .dogfood/recap-runs is a local directory. No Graph admission claim, source rewriting, model changes, migration or global framework.

Verification: owning recap graph route tests plus configured/default writer-root and malicious-root tests. Inspect current session29 manifests before any provider operation. Live read-only inspect after configuring root; no automatic provider retry while pasted Session28 heading vs operator Session29 selection remains unresolved. Commit/push/open one implementation PR; merge separate.

Runtime lease: DOGFOOD existing7866 API/5202 UI, runtime /tmp/prime-buddy-current-main-20261002 with schema0012. Keep source corpus/output/draft untouched; API restart inherits existing environment with only runs-root override. DEMO Graph read bridge disjoint.
