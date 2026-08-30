"""Corpus-normalized session recap markdown loader (non-engine).


Rehomed from the retired UnionSupergraph projection adapter so World Graph
recap projection can load corpus markdown without importing
``graph_memory.union_supergraph``.
"""


from __future__ import annotations


import re
from pathlib import Path


from src.corpus.session_recap_paths import (
    campaign_number_from_id,
    normalized_recap_candidates,
)
from src.live_play.recap_stage_paths import corpus_root


class CorpusNormalizedRecapLoadError(ValueError):
    """Fail-closed corpus recap identity/read error for World Graph recap projection."""


    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _strip_yaml_frontmatter(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return markdown
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return markdown


def _normalized_recap_candidates(*, campaign_id: str, session_id: str) -> list[Path]:
    """Union padded + unpadded Session N filename forms via shared corpus helper."""
    match = re.fullmatch(r"session-(\d+)", session_id.strip())
    if not match:
        return []
    session = int(match.group(1))
    campaign_number = campaign_number_from_id(campaign_id)
    return normalized_recap_candidates(
        corpus_root(),
        campaign_number=campaign_number,
        session=session,
    )


def load_corpus_normalized_recap_markdown(
    *,
    campaign_id: str,
    session_id: str,
    on_ambiguous: str = "first",
) -> str | None:
    """Load stripped body markdown for a campaign session's normalized recap.


    ``on_ambiguous``:
      - ``first``: legacy first-file-wins.
      - ``fail``: raise ``CorpusNormalizedRecapLoadError`` with
        ``recap_source_ambiguous`` when more than one candidate matches
        across padded and unpadded Session N filename forms.
    """
    candidates = _normalized_recap_candidates(
        campaign_id=campaign_id,
        session_id=session_id,
    )
    if not candidates:
        return None
    if len(candidates) > 1 and on_ambiguous == "fail":
        names = ", ".join(path.name for path in candidates)
        raise CorpusNormalizedRecapLoadError(
            (
                f"Ambiguous normalized recap identity for {campaign_id} {session_id}: "
                f"{names}"
            ),
            code="recap_source_ambiguous",
            status_code=422,
        )
    try:
        return _strip_yaml_frontmatter(candidates[0].read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise CorpusNormalizedRecapLoadError(
            f"Normalized recap is not valid UTF-8 for {campaign_id} {session_id}.",
            code="recap_source_unreadable",
            status_code=500,
        ) from exc
