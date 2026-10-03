# DOGFOOD — Confined recap snapshot storage

Status: ACTIVE. Direct operator authority: patch the failing Run ingest workflow, 2026-10-02. Topology: serial successor to merged PR875. Base: fetched origin/main 420b59b1629b9399dbb480baa9479d654f1ed659; branch codex/dogfood-recap-content-root; owning checkout /home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy.

Write lease: this handoff; HANDOFF-DOGFOOD-recap-runs-root.md (predecessor settlement); apps/live_control_server/services/source_artifact_registry.py; tests/test_recap_source_content_root.py; tests/test_live_recap_ingest_graph_preview_api.py (configured immutable snapshot route witness).

Invariant: recap snapshots remain digest-keyed, immutable, repository-contained and source-preserving. Existing default URI prefix unchanged. A local operator may configure DUNGEONMIND_RECAP_SOURCE_CONTENT_ROOT as a repo-relative confined prefix; traversal, file URIs, absolute paths and external symlink escape rejected. Existing source IDs/URIs are not rewritten. Span/index/registry authority behavior unchanged. No auth bypass, migration, provider/model changes, generic framework or Graph admission claim.

Verification: real registry write/read/idempotency tests with shared out symlink; malicious root rejection; mounted recap preview source-bundle production with configured content prefix and no provider. Inspect current operation state before any retry. Review cumulative diff, commit/push/open one PR; merge separate.

Runtime lease: existing API7866/UI5202, compatible schema0012 checkout /tmp/prime-buddy-current-main-20261002. Add only .dogfood/recap-source-content prefix to existing environment; preserve shared out, original corpus bytes and active browser draft. Runtime evidence separate from provider extraction/admission outcomes.
