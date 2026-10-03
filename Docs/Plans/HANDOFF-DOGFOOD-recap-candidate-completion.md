# DOGFOOD — Validated recap candidate completion

Status: ACTIVE. Operator authority: fix Run ingest failing after direct operator dispatch, 2026-10-02. Serial successor to merged PR877. Base a4e1166a16906d411e6864221513632a90dc2dae; branch codex/dogfood-recap-candidate-completion; checkout /home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy.

Write lease: this handoff; HANDOFF-DOGFOOD-recap-content-root.md (predecessor settlement); recap_graph_preview_ingest.py and routes/recap_ingest.py under apps/live_control_server; IngestionModule.tsx/test and ingestReadiness.ts/test under apps/live-control-ui/src/modules; tests/test_live_recap_ingest_graph_preview_api.py.

Invariant: existing validated reviewable ExtractionRun candidate, with lineage and source linkage gates, completes without calling retired UnionSupergraph materialization. Candidate success means review/admission pending, never native Graph or memory/planning readiness. Invalid/missing-lineage candidates stay blocked. Same-source recovery reuses durable run/artifacts with zero provider dispatch; source bytes/IDs/URIs/digests preserved.

Verification: unmocked owning route recovery with pre-existing synthetic validated production extraction, forbidden retired materializer/provider dispatch, repeated recovery preserving run/source identity; existing invalid-candidate boundary; mounted UI completion toast/readiness distinct from admission. Inspect cumulative diff and finish one PR. Merge separate.

Runtime: existing schema0012 API7866/UI5202 compatible lane; preserve actual reviewable run ab150e5c-674f-49b8-8cf2-9157b14e852e and SourceArtifact artifact:recap:longmont-c2:session-29:f8e373a166f0. No model change, provider replay, migration, revived preview store, new admission transition or selection/source rewriting. Actual provider extracted37nodes/23edges/6beats; post-extraction retired materializer caused500. Costs unknown unless existing telemetry proves them.
