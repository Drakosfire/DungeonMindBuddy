"""Keep the distinct sources and target of the joined Build image benchmark."""
import json
from pathlib import Path


def test_conversation_image_fixture_requires_both_sources_and_one_target():
    fixture_path = Path(__file__).resolve().parents[2] / "evals/buddy_benchmark/fixtures/conversation-image.json"
    fixture = json.loads(fixture_path.read_bytes())
    page = fixture["page"]
    chat = " ".join(f"{turn['user_text']} {turn['assistant_text']}" for turn in fixture["history"])
    direction = fixture["direction_request"]
    assert fixture["page_detail"] in page and fixture["page_detail"] not in chat
    assert fixture["conversation_detail"] in chat and fixture["conversation_detail"] not in page
    assert all(fixture[key] not in direction for key in ("page_detail", "conversation_detail"))
    paragraphs = page.strip().split("\n\n")
    anchor = fixture["placement_anchor"]
    preserved = fixture["preserved_paragraph"]
    assert paragraphs.count(anchor) == paragraphs.count(preserved) == 1
    assert paragraphs[paragraphs.index(anchor) + 1] == preserved
