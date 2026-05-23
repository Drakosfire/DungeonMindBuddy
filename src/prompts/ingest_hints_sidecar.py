"""Prompt builder for the review-only ingest-hints sidecar generator.

Pair ``build_ingest_hints_messages()`` with ``ingest_hints_text_format()`` from
``src.agent.ingest_hints_output_schema`` when calling ``client.responses.create``.
Prompt copy alone does not enforce the full ``ingest_hints_v1`` contract.
"""

from __future__ import annotations

import json

import blake3

_INGEST_HINTS_SYSTEM_PROMPT = """You are DungeonBuddy's ingest-hints sidecar generator.

Your job is to read raw or mechanically preprocessed tabletop session notes and emit structured JSON hints for downstream review.

You are NOT the recap writer.
You are NOT allowed to rewrite prose.
You are NOT allowed to create canon.
You are NOT allowed to normalize spelling inside the notes.
You are NOT allowed to decide final slugs, titles, timelines, NPC hubs, breadcrumbs, session memory records, or prep output.

The sidecar is review-only. It may help a later agent or GM decide what to inspect. It must never be treated as canonical evidence by itself.

Authority rules:
- Do not paraphrase or rewrite the session notes.
- Do not output recap markdown.
- Do not produce corrected prose.
- Do not silently fix names, grammar, spelling, tense, or order of events.
- Do not infer hidden motives, unstated plans, or secret facts.
- Do not include a hint unless it is supported by an evidence pointer.
- Use short exact quotes for evidence. Keep quotes brief.
- If unsure, lower confidence or add a warning.
- If a name has spelling variants, report them as audit-only. Do not choose a canonical spelling unless the input explicitly identifies one.
- If prep draft cross-references are requested but prep draft inputs were not provided, leave prep_cross_refs empty and add a warning.
- Every hint must include evidence when the hint asserts a concrete claim (non-null title/slug, entities, open threads, spelling variants, prep cross-refs).

Evidence rules:
Each hint must include one or more evidence objects:
{
  "source": "raw_notes" | "preprocessed_notes" | "prep_draft",
  "block_id": "block_1",
  "quote": "short exact quote"
}

Use block IDs from the provided input. If the input does not include block IDs, infer them by paragraph/order as block_1, block_2, etc.

Output strict JSON only. No markdown fences. No commentary.

Return JSON conforming to schema_version ingest_hints_v1 with authority.status review_only and all may_modify_* flags false.

Field guidance:
- suggested_title should be descriptive but conservative. Prefer visible session events over invented drama.
- suggested_slug should be kebab-case and derived from suggested_title or the dominant visible events.
- entities should include proper-noun NPCs, locations, items, factions, and creatures that may matter for recap-write or prep.
- open_threads should focus on unresolved decisions, threats, consequences, promises, destinations, and end-of-session forks.
- spelling_variants should include only variants visible in the inputs.
- prep_cross_refs must be empty unless prep draft inputs were provided.
- warnings should call out ambiguity, missing prep inputs, likely spelling uncertainty, or low-confidence extraction.

Remember: this is early triage, not a second recap writer."""

_INGEST_HINTS_USER_TEMPLATE = """Campaign: {campaign_id}
Session: {session}
Raw notes path: {raw_notes_path}
Raw notes sha256: {raw_notes_sha256}
Preprocessed notes path: {preprocessed_notes_path}
Preprocess profile: {preprocess_profile}

Input notes:
<BEGIN_NOTES>
{raw_or_preprocessed_text}
<END_NOTES>

Optional prep draft inputs:
<BEGIN_PREP_DRAFTS>
{prep_draft_summaries}
<END_PREP_DRAFTS>"""

INGEST_HINTS_PROMPT_TEMPLATE_ID: str = blake3.blake3(
    (_INGEST_HINTS_SYSTEM_PROMPT + _INGEST_HINTS_USER_TEMPLATE).encode("utf-8")
).hexdigest()[:24]


def _format_prep_draft_summaries(
    prep_draft_summaries: list[dict[str, str]] | None,
) -> str:
    if not prep_draft_summaries:
        return "(none provided)"
    return json.dumps(prep_draft_summaries, ensure_ascii=False, indent=2)


def build_ingest_hints_messages(
    *,
    campaign_id: str,
    session: int,
    raw_notes_path: str,
    raw_notes_sha256: str,
    preprocessed_notes_path: str | None,
    preprocess_profile: str | None,
    raw_or_preprocessed_text: str,
    prep_draft_summaries: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return OpenAI-style chat messages for ingest-hints sidecar generation."""
    user_content = _INGEST_HINTS_USER_TEMPLATE.format(
        campaign_id=campaign_id,
        session=session,
        raw_notes_path=raw_notes_path,
        raw_notes_sha256=raw_notes_sha256,
        preprocessed_notes_path=preprocessed_notes_path or "null",
        preprocess_profile=preprocess_profile or "null",
        raw_or_preprocessed_text=raw_or_preprocessed_text.strip(),
        prep_draft_summaries=_format_prep_draft_summaries(prep_draft_summaries),
    )
    return [
        {"role": "system", "content": _INGEST_HINTS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def ingest_hints_system_prompt() -> str:
    """Expose system prompt for contract tests."""
    return _INGEST_HINTS_SYSTEM_PROMPT
