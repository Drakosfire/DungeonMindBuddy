"""``_source_artifact_compatible`` must only allow session_id-only drift for
campaign-stable source domains (``party_registry``). Session-scoped domains
(e.g. ``recap``) disagreeing on ``session_id`` are a real provenance conflict,
not additive re-promotion, and must still be rejected.
"""

from __future__ import annotations

from graph_memory.candidate_graph_to_contribution import CAMPAIGN_STABLE_SOURCE_DOMAINS
from graph_memory.kernel.contribution_merge import _source_artifact_compatible


def _artifact(*, source_domain: str, session_id: str | None, content_sha256: str = "abc123") -> dict:
    payload: dict = {
        "source_artifact_id": "artifact:test",
        "source_domain": source_domain,
        "content_sha256": content_sha256,
        "uri": "repo://extract/artifact:test",
    }
    if session_id is not None:
        payload["session_id"] = session_id
    return payload


def test_exact_match_is_always_compatible_regardless_of_domain() -> None:
    existing = _artifact(source_domain="recap", session_id="session-1")
    assert _source_artifact_compatible(existing, dict(existing)) is True


def test_campaign_stable_domain_allows_session_id_only_drift() -> None:
    assert "party_registry" in CAMPAIGN_STABLE_SOURCE_DOMAINS
    existing = _artifact(source_domain="party_registry", session_id="session-1")
    incoming = _artifact(source_domain="party_registry", session_id="session-2")
    assert _source_artifact_compatible(existing, incoming) is True


def test_campaign_stable_domain_with_missing_session_id_on_one_side_is_compatible() -> None:
    existing = _artifact(source_domain="party_registry", session_id="session-1")
    incoming = _artifact(source_domain="party_registry", session_id=None)
    assert _source_artifact_compatible(existing, incoming) is True


def test_session_scoped_domain_rejects_session_id_only_drift() -> None:
    """A ``recap`` artifact disagreeing only on session_id is a real conflict."""
    existing = _artifact(source_domain="recap", session_id="session-1")
    incoming = _artifact(source_domain="recap", session_id="session-2")
    assert _source_artifact_compatible(existing, incoming) is False


def test_mismatched_domain_rejects_even_when_one_side_is_stable() -> None:
    existing = _artifact(source_domain="party_registry", session_id="session-1")
    incoming = _artifact(source_domain="recap", session_id="session-2")
    assert _source_artifact_compatible(existing, incoming) is False


def test_content_digest_mismatch_rejects_even_for_stable_domain() -> None:
    existing = _artifact(
        source_domain="party_registry", session_id="session-1", content_sha256="aaa"
    )
    incoming = _artifact(
        source_domain="party_registry", session_id="session-2", content_sha256="bbb"
    )
    assert _source_artifact_compatible(existing, incoming) is False


def test_missing_content_digest_rejects_even_for_stable_domain() -> None:
    existing = _artifact(source_domain="party_registry", session_id="session-1", content_sha256="")
    incoming = _artifact(source_domain="party_registry", session_id="session-2", content_sha256="")
    assert _source_artifact_compatible(existing, incoming) is False
