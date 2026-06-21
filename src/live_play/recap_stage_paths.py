from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.corpus.session_recap_paths import campaign_number_from_id, session_recaps_prefix
from src.live_play.session_paths import repo_root


def corpus_root() -> Path:
    return repo_root() / "corpus" / "eldyrwild-markdown"


@dataclass(frozen=True)
class RecapStagePaths:
    campaign_id: str
    campaign_number: int
    campaign_root_rel: str
    staged_raw_notes_rel: str
    canonical_recap_rel: str
    canonical_basename: str
    normalized_recap_rel: str
    frontmatter_seed_rel: str
    breadcrumbed_recap_rel: str
    session_memory_jsonl_rel: str
    session_memory_meta_rel: str

    @classmethod
    def build(cls, *, campaign_id: str, session: int, slug_tail: str) -> "RecapStagePaths":
        campaign_number = campaign_number_from_id(campaign_id)
        campaign_root_rel = f"Longmont Campaign/Campaign {campaign_number}"
        session_prefix = session_recaps_prefix(campaign_number)
        canonical_basename = f"Session {session} - {slug_tail}"
        staged_raw_notes_rel = (
            f"{campaign_root_rel}/_ingest_staging/session_{session}_raw_notes.md"
        )
        canonical_recap_rel = f"{session_prefix}/{canonical_basename}.md"
        normalized_recap_rel = f"{session_prefix}/_normalized/Session {session:02d} - {slug_tail}.md"
        frontmatter_seed_rel = (
            f"{session_prefix}/_breadcrumbed/{canonical_basename}.frontmatter_seed.md"
        )
        breadcrumbed_recap_rel = (
            f"{session_prefix}/_breadcrumbed/{canonical_basename}.breadcrumbed.md"
        )
        session_memory_jsonl_rel = (
            f"{session_prefix}/_session_memory/{canonical_basename}.records_meta.jsonl"
        )
        session_memory_meta_rel = (
            f"{session_prefix}/_session_memory/{canonical_basename}.records_meta.json"
        )
        return cls(
            campaign_id=campaign_id,
            campaign_number=campaign_number,
            campaign_root_rel=campaign_root_rel,
            staged_raw_notes_rel=staged_raw_notes_rel,
            canonical_recap_rel=canonical_recap_rel,
            canonical_basename=canonical_basename,
            normalized_recap_rel=normalized_recap_rel,
            frontmatter_seed_rel=frontmatter_seed_rel,
            breadcrumbed_recap_rel=breadcrumbed_recap_rel,
            session_memory_jsonl_rel=session_memory_jsonl_rel,
            session_memory_meta_rel=session_memory_meta_rel,
        )
