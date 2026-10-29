import pytest
from apps.live_control_server.services.tiptap_markdown_write import markdown_lossy_diagnostics, validate_saved_media_references, TiptapMarkdownWriteError


@pytest.mark.parametrize("title", ["", ' "dmb-image:v1 width=20 collapsed=true"', ' "dmb-image:v1 width=100 collapsed=false"'])
def test_saved_media_presentation_is_editor_admitted(title):
    source = f'![Map](dmb-media:ac6c15cc-8c68-4732-8ae2-d9f3f051393a{title})'
    assert markdown_lossy_diagnostics(source) == []


@pytest.mark.parametrize("title", ["ordinary", "dmb-image:v1 width=19 collapsed=false", "dmb-image:v1 width=101 collapsed=true", "dmb-image:v1 width=50 collapsed=1"])
def test_malformed_media_presentation_is_not_editor_admitted(title):
    source = f'![Map](dmb-media:ac6c15cc-8c68-4732-8ae2-d9f3f051393a "{title}")'
    assert markdown_lossy_diagnostics(source)


def test_presentation_requires_owned_integrity_verified_staged_asset(monkeypatch):
    from application_state import media
    calls = []
    def get_asset(asset_id, owner):
        calls.append((asset_id, owner))
        return {"state": "staged", "receipt": {"visibility": "public"}}
    monkeypatch.setattr(media, "get_asset", get_asset)
    source = '![Map](dmb-media:ac6c15cc-8c68-4732-8ae2-d9f3f051393a "dmb-image:v1 width=50 collapsed=true")'
    reads = []
    monkeypatch.setattr(media, "read_staged_bytes", lambda asset_id, owner: reads.append((asset_id, owner)) or b"original")
    validate_saved_media_references(source, "owner")
    assert reads == [("ac6c15cc-8c68-4732-8ae2-d9f3f051393a", "owner")]
    assert calls == [("ac6c15cc-8c68-4732-8ae2-d9f3f051393a", "owner")]
    calls.clear()
    with pytest.raises(TiptapMarkdownWriteError, match="Invalid saved image"):
        validate_saved_media_references(source.replace("width=50", "width=500"), "owner")
    assert not calls


@pytest.mark.parametrize("state", ["uploading", "unknown"])
def test_uncertain_image_state_still_refuses(monkeypatch, state):
    from application_state import media
    monkeypatch.setattr(media, "get_asset", lambda *_: {"state": state, "receipt": None})
    with pytest.raises(TiptapMarkdownWriteError, match="not ready"):
        validate_saved_media_references('![Map](dmb-media:ac6c15cc-8c68-4732-8ae2-d9f3f051393a)')
