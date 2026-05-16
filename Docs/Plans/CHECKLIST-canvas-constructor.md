# CHECKLIST — Canvas Constructor

## Phase 0 — Planning

- [ ] `PLAN-canvas-constructor.md` exists.
- [ ] `CHECKLIST-canvas-constructor.md` exists.
- [ ] Existing canvas emitters are inventoried.
- [ ] Cursor-managed canvas path convention is documented.
- [ ] Generated-block convention is documented.
- [ ] Canonical JSON vs projection boundary is documented.

## Phase 1 — First conforming adapter

- [ ] C1S4 Step 2D canvas payload exists.
- [ ] C1S4 Step 2D canvas emitter exists.
- [ ] Payload has a schema.
- [ ] Payload includes source pointers.
- [ ] Payload includes stat tiles.
- [ ] Payload includes row-level failure detail.
- [ ] Payload includes detail cards.
- [ ] Payload includes guardrail rows.
- [ ] Emitter supports `--check`.
- [ ] Emitter supports `--payload-out`.
- [ ] Emitter patches generated block markers.
- [ ] Tests pass.

## Phase 2 — Shared helpers

- [ ] Common generated-block renderer exists.
- [ ] Common marker replacement helper exists.
- [ ] Common canvas path helper is reused.
- [ ] Common `--check` behavior is standardized.
- [ ] Common `--payload-out` behavior is standardized.
- [ ] Missing marker errors are consistent and helpful.

## Phase 3 — Common review payload schema

- [ ] Shared payload schema is drafted.
- [ ] Summary/stat tile contract is defined.
- [ ] Row contract is defined.
- [ ] Detail card contract is defined.
- [ ] Guardrail row contract is defined.
- [ ] Delta row contract is defined.
- [ ] Source pointer contract is defined.

## Phase 4 — Shared TSX shell/components

- [ ] Standard canvas shell exists.
- [ ] Stat tile component exists.
- [ ] Mode table component exists.
- [ ] Question/scenario card component exists.
- [ ] Retrieved evidence component exists.
- [ ] Failure callout component exists.
- [ ] Guardrail section component exists.

## Phase 5 — Backport existing canvases

- [ ] C1S2 benchmark canvas reviewed.
- [ ] C1S13 benchmark canvas reviewed.
- [ ] Breadcrumb query canvas payload reviewed.
- [ ] Old emitters either conform or are explicitly grandfathered.
