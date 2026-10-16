# DOGFOOD — Validated recap candidate completion

Status: MERGED / HISTORICAL. PR #878 merged as `67b0df1a478f50ff324b919d13f299c276b89198`; the Run-ingest implementation lease is closed. Preserved candidate acceptance and source fidelity remain under the active Ingest mandate, outside this completed implementation slice.

Write lease: this handoff; HANDOFF-DOGFOOD-recap-content-root.md (predecessor settlement); recap_graph_preview_ingest.py and routes/recap_ingest.py under apps/live_control_server; IngestionModule.tsx/test and ingestReadiness.ts/test under apps/live-control-ui/src/modules; tests/test_live_recap_ingest_graph_preview_api.py.

Invariant: existing validated reviewable ExtractionRun candidate, with lineage and source linkage gates, completes without calling retired UnionSupergraph materialization. Candidate success means review/admission pending, never native Graph or memory/planning readiness. Invalid/missing-lineage candidates stay blocked. Same-source recovery reuses durable run/artifacts with zero provider dispatch; source bytes/IDs/URIs/digests preserved.

Verification: unmocked owning route recovery with pre-existing synthetic validated production extraction, forbidden retired materializer/provider dispatch, repeated recovery preserving run/source identity; existing invalid-candidate boundary; mounted UI completion toast/readiness distinct from admission. Inspect cumulative diff and finish one PR. Merge separate.

Runtime: existing schema0012 API7866/UI5202 compatible lane; preserve actual reviewable run ab150e5c-674f-49b8-8cf2-9157b14e852e and SourceArtifact artifact:recap:longmont-c2:session-29:f8e373a166f0. No model change, provider replay, migration, revived preview store, new admission transition or selection/source rewriting. Actual provider extracted37nodes/23edges/6beats; post-extraction retired materializer caused500. Costs unknown unless existing telemetry proves them.
