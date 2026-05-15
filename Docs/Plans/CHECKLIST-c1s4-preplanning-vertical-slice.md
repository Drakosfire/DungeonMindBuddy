# CHECKLIST — C1S4 preplanning vertical slice

- [ ] Canonical super-plan: `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` v32, especially `pilot_memory_ingest` and `synthetic_session4_prep_benchmark`.
- [ ] Planning rationale: `Docs/Plans/RATIONALE-c1s4-preplanning-vertical-slice.md`.
- [ ] Implementation handoff: `Docs/Plans/HANDOFF-next-c1s4-preplanning-vertical-slice-scaffold.md`.

## Deterministic scaffold completion

- [ ] C1S1–C1S3 are the only planner-visible KB inputs.
- [ ] C1S4 is held out as oracle-only.
- [ ] All C1S4 source/derivative surfaces are excluded from planner-visible context.
- [ ] Preferred oracle source is normalized C1S4 recap when present.
- [ ] Original C1S4 recap remains fallback oracle source and forbidden planner-visible source.
- [ ] Canonical session-memory ingestion location is `src/session_memory/`.

## Out-of-scope guardrails

- [ ] No retrieval tuning introduced in the scaffold PR.
- [ ] No corpus mutation.
- [ ] No baseline regeneration.
- [ ] No live planner/oracle grading in scaffold PR.
