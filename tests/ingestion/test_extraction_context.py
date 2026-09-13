from pathlib import Path

from src.ingestion.entity_extractor import _build_batched_entity_user_prompt, _cache_key
from src.ingestion.extraction_context import active_document_context


def test_default_context_preserves_evidence_unit_prompt(monkeypatch) -> None:
    monkeypatch.delenv("DMB_EXTRACTION_CONTEXT_MODE", raising=False)
    prompt = _build_batched_entity_user_prompt([{"text": "Local evidence"}], [])
    assert "full_document" not in prompt
    assert "Local evidence" in prompt


def test_whole_document_uses_exact_frontmatter_stripped_body_and_changes_cache(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "---\ntitle: Example\ncanon_layer: world\nsource_class: seed_reference\n"
        "document_class: world\ntemporal_scope: evergreen\n---\n"
        "# People\n\nStacy was already here.\n",
        encoding="utf-8",
    )
    unit = {"text": "Stacy was already here."}
    monkeypatch.setenv("DMB_EXTRACTION_CONTEXT_MODE", "evidence_unit")
    local_key = _cache_key(unit, "model")
    monkeypatch.setenv("DMB_EXTRACTION_CONTEXT_MODE", "whole_document")
    monkeypatch.setenv("DMB_EXTRACTION_DOCUMENT_PATH", str(source))
    mode, body = active_document_context()
    prompt = _build_batched_entity_user_prompt([unit], [])
    assert mode == "whole_document"
    assert body == "# People\n\nStacy was already here.\n"
    assert "title: Example" not in prompt
    assert "# People" in prompt
    assert _cache_key(unit, "model") != local_key


def test_whole_document_fails_closed_without_source_path(monkeypatch) -> None:
    monkeypatch.setenv("DMB_EXTRACTION_CONTEXT_MODE", "whole_document")
    monkeypatch.delenv("DMB_EXTRACTION_DOCUMENT_PATH", raising=False)
    try:
        active_document_context()
    except ValueError as exc:
        assert "requires DMB_EXTRACTION_DOCUMENT_PATH" in str(exc)
    else:
        raise AssertionError("whole_document mode must fail closed without an exact source")
