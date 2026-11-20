import hashlib
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from apps.live_control_server.services import guest_release_sources as source


def test_excerpt_is_exact_and_omits_private_identity(monkeypatch):
    markdown = "A small carnival awaits."
    _fake_page(monkeypatch, markdown, "player_safe")
    digest = hashlib.sha256(markdown.encode()).hexdigest()
    result, binding = source.selected_page_excerpt(world_id="private-world", document_id="private-document", revision_n=1,
        expected_sha256=digest, start=2, end=7, expected_excerpt="small")
    assert result["text"] == "small" and "private" not in str(result)
    assert str(binding[0]) == result["id"] and binding[1:] == ("id", 0, 0, 1, digest, 2, 7, 8, "player_safe")
    with pytest.raises(source.GuestReleaseSourceError):
        source.selected_page_excerpt(world_id="private-world", document_id="private-document", revision_n=1,
            expected_sha256=digest, start=2, end=7, expected_excerpt="wrong")


def test_internal_page_can_be_selected_for_private_review(monkeypatch):
    _fake_page(monkeypatch, "x", "internal")
    excerpt, binding = source.selected_page_excerpt(world_id="private-world", document_id="doc", revision_n=1,
        expected_sha256=hashlib.sha256(b"x").hexdigest(), start=0, end=1, expected_excerpt="x")
    assert excerpt["text"] == "x" and binding[-1] == "internal"


def _fake_page(monkeypatch, markdown, visibility):
    @contextmanager
    def unit(_):
        yield SimpleNamespace(execute=lambda *_: SimpleNamespace(fetchone=lambda: (0, 0)))
    monkeypatch.setattr(source, "unit_of_work", unit)
    monkeypatch.setattr(source.pages, "_dsn", lambda: "synthetic")
    monkeypatch.setattr(source.pages, "_state", lambda *a, **k: SimpleNamespace(
        page=SimpleNamespace(status="active", work_object_id="id", current_revision_id="revision-id", object_revision=8),
        metadata=SimpleNamespace(visibility_state=visibility)))
    monkeypatch.setattr(source.repository, "get_work_revision_by_n", lambda *a, **k: SimpleNamespace(
        markdown=markdown, work_object_id="id", work_revision_id="revision-id", world_id="private-world"))


@pytest.mark.parametrize("text", ["[map](https://private.example/a)", "dmb-media:abc", "signed.example/path?sig=x"])
def test_link_and_media_destinations_are_rejected(monkeypatch, text):
    _fake_page(monkeypatch, text, "player_safe")
    with pytest.raises(source.GuestReleaseSourceError):
        source.selected_page_excerpt(world_id="private-world", document_id="doc", revision_n=1,
            expected_sha256=hashlib.sha256(text.encode()).hexdigest(), start=0, end=len(text), expected_excerpt=text)
