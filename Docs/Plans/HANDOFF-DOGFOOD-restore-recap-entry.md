# DOGFOOD — Restore recap entry

Status: ACTIVE. Authority: operator directly requested restoration on 2026-10-02; PRIME scope approval is not a gate.

Topology: serial, one restoration PR. Base: origin/main at 1e050dc8a856743748c315b68e1e6d799932af33. Branch: codex/dogfood-restore-recap-workbench. Checkout: /home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy.

Expected write lease: this handoff; apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx and MemoryIngestPage.test.tsx; apps/live-control-ui/src/modules/IngestionModule.tsx and IngestionModule.test.tsx (explicit initial source session only). No API, authentication, native Graph projection, migration, registry or roadmap edits. DEMO owns the separate managed/native projection correction.

Invariant: bare Elderwyld Ingest exposes the established Longmont recap pipeline with Campaign 2 / Session 29 initial context and editable existing controls. World identity is never passed as a narrative campaign. Other Worlds never inherit Longmont. Exact managed extraction-run review retains its verified World boundary. This is a bounded dogfood restoration of the existing fixed corpus pipeline, not a generic managed-World ingestion contract.

Verification: page boundary tests for bare entry, C1/C2 campaign URL compatibility, foreign and matching exact runs; existing IngestionModule tests. Inspect cumulative diff before commit. Runtime 5202 may receive only this UI patch on its existing compatible checkout; no API restart or database upgrade.

Known limits: selected World persistence and graph credential/binding repair remain separate. Existing pipeline output locations and Graph admission behavior are unchanged. Runtime database remains schema 0012. Session 29 recap has not been submitted.
