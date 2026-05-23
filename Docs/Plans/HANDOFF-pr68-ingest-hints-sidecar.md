# HANDOFF — PR #68: Review-only ingest hints sidecar (ingest_hints_v1)

**Created:** 2026-05-23 (UTC).
**Status:** ACTIVE — in-IDE slice on `feature/ingest-hints-sidecar-v1`.
**Branch:** `feature/ingest-hints-sidecar-v1`

---

## §1 Mission

Add a **review-only** LLM sidecar contract for raw session notes:

`_ingest_staging/session_{N}_raw_notes.ingest_hints.json`

Hints may triage metadata before recap-write. They must **not** rewrite prose, mutate staging canon, or silently promote into `_SLUGS`, timelines, hubs, breadcrumbs, or session memory.

## §2 Why

C2S21 exposed a clean split:

- **Mechanical** numbered-list layout repair → deterministic preprocess (separate slice).
- **Metadata triage** → optional LLM sidecar with evidence + operator review.

This PR formalizes the sidecar only. It does **not** wire the sidecar into recap-write automatically.

## §3 Files in scope (allowlist)

| Action | Path |
|--------|------|
| Create | `src/agent/ingest_hints_output_schema.py` |
| Create | `src/prompts/ingest_hints_sidecar.py` |
| Create | `.cursor/skills/ingest-hints-sidecar/SKILL.md` |
| Create | `tests/test_ingest_hints_output_schema.py` |
| Create | `tests/test_ingest_hints_prompt_contract.py` |
| Create | `Docs/Plans/HANDOFF-pr68-ingest-hints-sidecar.md` |
| Modify | `Docs/Plans/C2S21-S22-DEMO-ARCHITECT-SESSION-NOTES.md` |
| Modify | `Docs/Plans/HANDOFF-prep-agent-c2-ingest-s21-plan-s22-cursor-first.md` |

## §4 Explicitly out of scope

- `assemble_recap_draft` / mechanical preprocess implementation
- `src/agent/planner_skill_output_schema.py` wiring (sibling skill first)
- `_SLUGS`, corpus writer, recap-write behavior changes
- C2 live-prep retrieval
- Automatic promotion of hints to canon

## §5 Verification (§7)

```bash
uv run pytest tests/test_ingest_hints_output_schema.py -q
uv run pytest tests/test_ingest_hints_prompt_contract.py -q
```

## §6 Acceptance criteria

- [x] Prompt importable via `build_ingest_hints_messages`
- [x] `ingest_hints_v1` schema + validator require evidence on concrete hints
- [x] Authority flags enforce review-only (`may_modify_prose: false`, etc.)
- [x] Forbidden canon keys rejected (`recap_body`, `normalized_body`, …)
- [x] Docs link §9.8 to this implementation
- [x] No recap-write or assemble_recap behavior change

## §7 Existing contracts preserved

- recap-write: one write target (`Session N - Recap.md`); prose identity transform only
- assemble_recap_draft: sole recap body assembler
- Sidecar: non-authoritative; operator review before promotion
