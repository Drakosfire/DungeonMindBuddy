# PLAY — prepared tables and recorded physical rolls

ACTIVE serial implementation lease. PRIME, authorized by the standing local
adventure goal, owns branch codex/play-prepared-table-receipts in the existing
buddy-context-loop checkout from 112f8fbcaa3ad7f9d1630d67c0a550a63adaf710.
Authority: HANDOFF-PLAY-recorded-tables.md at that ref (reviewed design #1596).
The current open PR census has no overlapping prepared-table implementation.

## Bounded outcome and failure critique

Deliver the complete first useful capability in the design: ordinary lossless
shared authoring of explicit tables, exact Run-pinned source membership,
deterministic entered physical values and append-only Play receipts in a lazy
Surface tool. Replay must precede fresh lifecycle/source/CAS checks after owner
verification. A whole-progress writer cannot erase receipts. A transport failure
cannot mint another command or roll. Shared hosting does not transfer save
ownership. No provider or RNG is involved. Examples nested in longer fences are
not tables. Invalid typed blocks cannot pass the writing fidelity gate.

## Exclusive expected paths

- This handoff, HANDOFF-PLAY-recorded-tables.md, Docs/Roadmaps/ROADMAP-demo.md.
- src/application_state/play/prepared_tables.py and prepared_table_service.py.
- src/application_state/migrations/versions/20261022_0044_prepared_table_receipts.py.
- apps/live_control_server/routes/play_prepared_tables.py and main.py.
- pyproject.toml and uv.lock (explicit existing CommonMark dependency).
- apps/live-control-ui/src/api/liveApi.ts and liveApi.preparedTables.test.ts.
- apps/live-control-ui/src/preparedTables/{tableGrammar.ts,PreparedTableNode.ts,PreparedTablesTool.tsx,preparedTablesProjection.tsx,preparedTables.test.ts,PreparedTablesTool.test.tsx}.
- apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx,
  tiptap/markdown/markdownAdmission.ts, tiptap/markdown/calloutMarkdown.ts,
  tiptap/markdown/semanticMarkdownSafety.ts, markdownReader/ReadOnlyBodyContent.tsx,
  playSurface/PlaySurfacePage.tsx, playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
  and playSurface/content/PlaySessionContentEditor.tsx.
- tests/test_prepared_tables.py, tests/test_prepared_tables_api.py,
  tests/application_state/test_prepared_table_receipts_postgres.py.

One implementation PR, exact cumulative Bugbot review, PRIME merge and settlement.
Disposable APP54329 owns migration/integration verification; retained APP54331,
native54330 and API8000/UI5202 remain untouched until reviewed guarded adoption.
Private source/rehearsal evidence stays in existing ignored .pytest_cache and the
established private artifact root; no licensed source rows in tracked fixtures.
Ordinary Build→Plan→Play Conks table plus reload/restart is required live evidence.

Typed table integer values use the shared JavaScript exact-integer range (up to
2^53−1); this is a representation/fidelity boundary, not a content or usage cap.
