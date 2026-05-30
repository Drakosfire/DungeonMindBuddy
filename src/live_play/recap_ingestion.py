from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

_OPEN_LOOP_RE = re.compile(
    r"\b(unresolved|open question|still open|next session|should|need to|plan to|tbd|follow[- ]?up)\b",
    re.IGNORECASE,
)
_ENTITY_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class RecapEntityMention(BaseModel):
    name: str
    slug: str
    context_line: str


class RecapOpenLoop(BaseModel):
    loop_id: str
    title: str
    summary: str
    source_line: str


class RecapPlanningBeat(BaseModel):
    beat_id: str
    label: str
    summary: str
    time_hint: str | None = None
    table_ready_prompt: str


class RecapIngestionResult(BaseModel):
    campaign_id: str
    source_session: int | None
    planning_session: int
    recap_path: str
    recap_title: str
    recap_excerpt: str
    candidate_entities: list[RecapEntityMention] = Field(default_factory=list)
    candidate_open_loops: list[RecapOpenLoop] = Field(default_factory=list)
    candidate_planning_beats: list[RecapPlanningBeat] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


def _slugify(text: str, *, max_len: int = 48) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug[:max_len] or "item"


def _first_heading_title(lines: list[str]) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


def _strip_existing_frontmatter(text: str) -> tuple[str, bool]:
    if not text.startswith("---"):
        return text, False
    end = text.find("\n---", 3)
    if end == -1:
        return text, False
    body_start = end + len("\n---")
    if body_start < len(text) and text[body_start] == "\n":
        body_start += 1
    return text[body_start:].lstrip("\n"), True


def ingest_recap_markdown(
    *,
    recap_path: Path,
    campaign_id: str,
    planning_session: int,
    source_session: int | None = None,
) -> RecapIngestionResult:
    raw = recap_path.read_text(encoding="utf-8")
    body, had_frontmatter = _strip_existing_frontmatter(raw)
    if not body.strip():
        raise ValueError("recap is empty after removing frontmatter")

    lines = body.splitlines()
    diagnostics: list[str] = []
    if had_frontmatter:
        diagnostics.append("source_recap_had_frontmatter_stripped_for_heuristics_only")

    title = _first_heading_title(lines) or f"Session {planning_session} planning recap"
    excerpt = "\n".join(line.strip() for line in lines if line.strip())[:400]

    entities: list[RecapEntityMention] = []
    seen_entity: set[str] = set()
    for line in lines:
        for match in _ENTITY_RE.finditer(line):
            name = match.group(1)
            if name in seen_entity:
                continue
            seen_entity.add(name)
            entities.append(
                RecapEntityMention(
                    name=name,
                    slug=_slugify(name),
                    context_line=line.strip()[:200],
                )
            )

    open_loops: list[RecapOpenLoop] = []
    seen_loop: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not _OPEN_LOOP_RE.search(stripped):
            continue
        title_text = stripped.lstrip("-* ").strip()[:120]
        loop_id = _slugify(title_text)
        if loop_id in seen_loop:
            continue
        seen_loop.add(loop_id)
        open_loops.append(
            RecapOpenLoop(
                loop_id=loop_id,
                title=title_text[:80] or loop_id,
                summary=stripped[:240],
                source_line=stripped[:200],
            )
        )

    planning_beats: list[RecapPlanningBeat] = []
    seen_beat: set[str] = set()
    current_heading: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##"):
            current_heading = stripped.lstrip("#").strip()
            beat_id = _slugify(current_heading)
            if beat_id not in seen_beat:
                seen_beat.add(beat_id)
                planning_beats.append(
                    RecapPlanningBeat(
                        beat_id=beat_id,
                        label=current_heading,
                        summary=current_heading,
                        time_hint=None,
                        table_ready_prompt=f"What should the table resolve for {current_heading}?",
                    )
                )
            continue
        if stripped.startswith("-") or stripped.startswith("*"):
            bullet = stripped.lstrip("-* ").strip()
            if len(bullet) < 8:
                continue
            beat_id = _slugify(bullet)
            if beat_id in seen_beat:
                continue
            seen_beat.add(beat_id)
            planning_beats.append(
                RecapPlanningBeat(
                    beat_id=beat_id,
                    label=bullet[:80],
                    summary=bullet[:240],
                    time_hint=current_heading,
                    table_ready_prompt=f"Review prep for: {bullet[:100]}",
                )
            )

    if not planning_beats:
        diagnostics.append("no_planning_beats_from_headings_or_bullets")
        planning_beats.append(
            RecapPlanningBeat(
                beat_id="review-recap",
                label="Review recap for next session",
                summary=excerpt[:200] or title,
                time_hint="Planning",
                table_ready_prompt="What is the first beat to prep from this recap?",
            )
        )

    return RecapIngestionResult(
        campaign_id=campaign_id,
        source_session=source_session,
        planning_session=planning_session,
        recap_path=str(recap_path),
        recap_title=title,
        recap_excerpt=excerpt,
        candidate_entities=entities[:12],
        candidate_open_loops=open_loops[:8],
        candidate_planning_beats=planning_beats[:12],
        diagnostics=diagnostics,
    )
