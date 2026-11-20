# DOGFOOD — Retain unsaved Play notes

Status: ACTIVE. Direct operator authority authorizes targeted UX repairs and independently reviewable PRs. DOGFOOD's red owning-UI regression at d7e32dbc proves typed note loss when resolving the same beat; the saved play-capture audit contains the original output.

Base: d7e32dbc0fee4d658c61221bfc21f13fe9bb4660. Branch: codex/dogfood-play-note-retention. Reused clean completed attached checkout: /home/drakosfire/.codex/worktrees/dogfood-reader-941/DungeonMindBuddy (prior #941 merged; no active runtime attached).

Topology: parallel-independent. Checked current open #927 docs-only Play conversation, #970 Graph reader, #979 Plan defaults, #985 recap target, #986 ConversationDock, #988 SceneLensReader; none overlap the expected writes. Prior TableDeck leases are completed/historical. PRIME notified before edits; any newly discovered overlap requires coordination.

Exclusive expected write set: apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx and RunbookTableDeck.test.tsx; this handoff. No other page, shared controller, schema, API, database, provider, global stylesheet or public contract changes.

Outcome: manual-save note drafts remain scoped to exact Run and element, survive unrelated acknowledged progress updates and local navigation, stay visible on conflict/unknown results, and clear only when that identical text is acknowledged. A different Run must never inherit the prior draft. Saved progress remains authoritative for clean fields. Later local edits must not be discarded by an older receipt.

Non-goals: autosave, crash persistence for unsaved local drafts, Run-level notepad, multi-choice/event log, v2 cockpit notes, server writes/retries or prototype adoption. This is one independently useful data-loss repair.

Verification: carry the failing regression into the owning tests, cover element navigation and Run identity, failed/conflicting writes, save acknowledgment and authoritative clean-field refresh. Run the TableDeck and adjacent cockpit/decision suites; inspect cumulative base-to-head diff; record inherited UI typecheck failure. Mocked UI tests only; no production server or database mutation.

Completion: commit, push, open one PR, attach it and give PRIME the exact head and evidence. Independent review and merge authority remain separate.

Author validation, 2026-10-07: the original isolated retention probe fails on base d7e32dbc (expected typed text, received empty); its integrated regression passes on this repair. All 72 tests pass across TableDeck (23), current-moment cockpit (37) and decision model (12). Coverage includes local navigation, conflict/unknown retention, exact save acknowledgment, inconsistent Run/source/revision receipts, World-route saves and clean-field authoritative refresh. Failure drafts stay read-only rather than disabled so their text can be selected/copied. Full UI typecheck still reports only the inherited ThreatPublicationPanel.tsx:553 TS2503 JSX namespace error. No live Run, provider request, database or product runtime was touched. Unsaved drafts remain in component memory and are not crash-durable.
