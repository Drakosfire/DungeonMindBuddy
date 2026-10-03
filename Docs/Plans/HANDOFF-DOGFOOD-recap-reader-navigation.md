# DOGFOOD — recap reader navigation

Status: ACTIVE, directly authorized by the operator. PRIME acknowledged the bounded three-file lease.
Base: fetched origin/main 3b70f5b78d2d41ed0272de393861ffc1781657e5 (merged PR882).
Branch: codex/dogfood-recap-reader-navigation. Topology: serial successor to PR882.
Write lease: this handoff; apps/live-control-ui/src/modules/IngestionModule.tsx and IngestionModule.test.tsx. No shared viewer or CSS edits. No overlapping current lease found.
Runtime: DOGFOOD UI5202/API7866; UI-only hot reload, no restart or Graph/provider writes.

Invariant: Ingest also reads the recap corpus. Opening a recap persists campaign/session/reader mode and, where available, exact saved extraction identity in the route. Refresh restores ordinary readable source even when the existing in-memory Graph credential is absent. Graph canvas still requires verified native snapshot identity. Route run identity is source-inspection-only; it never authorizes managed exact-run admission. No credential persistence, extraction, generated content, fake world binding or automatic graph mutation.

Invalid route and mismatched source identity fail visibly. Existing request epoch fences reject late foreign campaign/session/run responses. Existing processed recap catalog supplies chronological selection; no-run recap reads are explicitly canonical corpus reads. Layout changes are a separate successor after this slice is reviewable.

Verification: owning mounted remount, missing-auth source retention and credential retry, mismatched/malformed route, source and projection identity/race guards, canonical read without extraction, chronological selection. Existing managed World routing guards remain. Typecheck has inherited ThreatPublicationPanel.tsx JSX namespace failure.
