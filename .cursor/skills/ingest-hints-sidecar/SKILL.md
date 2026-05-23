---
name: ingest-hints-sidecar
description: Generate a review-only ingest_hints_v1 JSON sidecar from raw or mechanically preprocessed session notes. Emits suggested title/slug, entities, open threads, spelling variants, and optional prep cross-refs with evidence. Never rewrites prose, never creates canon, never promotes hints to _SLUGS, timelines, hubs, breadcrumbs, or session memory.
---

# ingest-hints-sidecar — review-only metadata triage

Sibling to **recap-write**, not a pre-step inside it. Run this skill when the operator wants first-pass metadata hints before recap-write, or when documenting ingest architecture. The sidecar is **optional** and **non-authoritative**.

## Purpose

Generate `_ingest_staging/session_{N}_raw_notes.ingest_hints.json` — structured hints for downstream review. Hints may influence what the agent inspects next; they must **not** change prose, canon, normalized recaps, breadcrumb tags, session memory, `_SLUGS`, timelines, hubs, or plot artifacts without a later explicit operator review step.

## Inputs

- Raw or **mechanically preprocessed** session notes at `{campaign_hub}/_ingest_staging/session_{N}_raw_notes.md`.
- Optional: explicit prep draft paths/content if `prep_cross_refs` are desired (must be provided as inputs — do not infer from corpus globs).

## Outputs

- Strict JSON conforming to `ingest_hints_v1` (`src/agent/ingest_hints_output_schema.py`).
- Default sidecar path: same basename as raw notes with suffix `.ingest_hints.json`.

## Hard rules

- **Do not** rewrite, paraphrase, summarize, correct, or normalize recap prose.
- **Do not** emit canonical recap markdown or corrected prose bodies.
- **Do not** choose canon or apply slug/title/entity decisions to the corpus.
- **Do not** update `_SLUGS`, timelines, hubs, breadcrumbs, session memory, or recaps.
- **Every hint** that asserts a concrete claim must include evidence (source, block_id, short exact quote).
- **prep_cross_refs** must be empty unless prep draft inputs were explicitly provided.
- If prep cross-refs are requested without prep inputs, leave `prep_cross_refs` empty and add a warning.

## Workflow

1. Confirm raw notes path under `_ingest_staging/` (mechanical preprocess may have run separately).
2. Compute `raw_notes_sha256` of the ground-truth file the hints describe.
3. Build messages via `src/prompts/ingest_hints_sidecar.py::build_ingest_hints_messages`.
4. Call the LLM with strict JSON output (`ingest_hints_v1` schema when wired).
5. Validate with `validate_ingest_hints_payload`.
6. Write sidecar to disk for **operator review** — not via corpus writer allowlist in v1 unless a future slice adds an explicit staging sidecar path.

## What this skill does NOT do

- **Does not** call `assemble_recap_draft` or `write_corpus_file` for recaps.
- **Does not** replace recap-write `npc_audit` / `plot_artifacts` judgment (may seed them later when recap-write optionally reads an approved sidecar).
- **Does not** perform numbered-list layout repair — use deterministic preprocess first.

## See also

- `Docs/Plans/C2S21-S22-DEMO-ARCHITECT-SESSION-NOTES.md` §9.8 — sidecar path and authority boundary
- `.cursor/skills/recap-write/SKILL.md` — canonical recap write target
- `src/agent/ingest_hints_output_schema.py` — schema + validator
- `src/prompts/ingest_hints_sidecar.py` — prompt builder
