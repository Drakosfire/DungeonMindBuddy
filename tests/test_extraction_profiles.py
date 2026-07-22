from __future__ import annotations

import pytest

from src.graph_memory.extraction.extraction_profile import (
    InadmissibleExtractionProfileError,
    UnknownExtractionProfileError,
    get_extraction_profile,
    require_admitted_profile,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_EXTRACTION_PROFILE,
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
    resolve_legacy_graph_extraction_profile,
)
from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
    WORLDBUILDING_PLUMBING_PROFILE,
    WORLDBUILDING_PLUMBING_PROFILE_ID,
    WORLDBUILDING_PLUMBING_PROFILE_VERSION,
)


def test_recap_profile_preserves_pass_order_and_instructions() -> None:
    profile = get_extraction_profile(RECAP_PROFILE_ID, RECAP_PROFILE_VERSION)
    assert profile is RECAP_EXTRACTION_PROFILE
    assert [spec.pass_id for spec in profile.node_passes] == [
        "actor_pass",
        "location_pass",
        "collective_pass",
        "object_pass",
        "thread_pass",
    ]
    assert profile.beat_pass is not None
    assert profile.edge_pass.pass_id == "edge_pass"
    assert "evidence_refs" in profile.evidence_rule
    assert profile.allow_null_session is False


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(UnknownExtractionProfileError):
        get_extraction_profile("no_such_profile", "9.9")


def test_require_admitted_profile_rejects_worldbuilding_on_recap_profile() -> None:
    with pytest.raises(InadmissibleExtractionProfileError):
        require_admitted_profile(
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            source_domain="worldbuilding",
            session_id=None,
        )


def test_worldbuilding_plumbing_admits_null_session() -> None:
    profile = require_admitted_profile(
        profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
        profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
        source_domain="worldbuilding",
        document_class="lore",
        session_id=None,
    )
    assert profile is WORLDBUILDING_PLUMBING_PROFILE
    assert profile.allow_null_session is True


def test_worldbuilding_plumbing_rejects_missing_document_class() -> None:
    with pytest.raises(InadmissibleExtractionProfileError, match="document_class"):
        require_admitted_profile(
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
            profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            source_domain="worldbuilding",
            document_class=None,
            session_id=None,
        )


def test_worldbuilding_plumbing_rejects_fabricated_session() -> None:
    with pytest.raises(InadmissibleExtractionProfileError):
        require_admitted_profile(
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
            profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            source_domain="worldbuilding",
            document_class="lore",
            session_id="session-1",
        )


def test_legacy_profile_aliases_resolve_to_recap_profile() -> None:
    assert resolve_legacy_graph_extraction_profile(None) == (
        RECAP_PROFILE_ID,
        RECAP_PROFILE_VERSION,
    )
    assert resolve_legacy_graph_extraction_profile("current_default") == (
        RECAP_PROFILE_ID,
        RECAP_PROFILE_VERSION,
    )
    assert resolve_legacy_graph_extraction_profile("category_encounter_job_preview") == (
        "recap_category_encounter_job_preview",
        "1.0",
    )
