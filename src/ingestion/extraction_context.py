from __future__ import annotations

import os
from pathlib import Path

import blake3

from src.ingestion.docx_converter import docx_to_markdown, markdown_passthrough
from src.ingestion.frontmatter import parse_document_frontmatter


def active_document_context() -> tuple[str, str | None]:
    mode = os.environ.get("DMB_EXTRACTION_CONTEXT_MODE", "evidence_unit").strip()
    if mode == "evidence_unit":
        return mode, None
    if mode != "whole_document":
        raise ValueError(f"unsupported extraction context mode: {mode}")
    raw_path = os.environ.get("DMB_EXTRACTION_DOCUMENT_PATH", "").strip()
    if not raw_path:
        raise ValueError("whole_document extraction context requires DMB_EXTRACTION_DOCUMENT_PATH")
    path = Path(raw_path)
    if not path.is_file():
        raise ValueError(f"whole_document extraction context path is not a file: {path}")
    markdown = markdown_passthrough(path) if path.suffix.lower() == ".md" else docx_to_markdown(path)
    metadata, body = parse_document_frontmatter(markdown)
    return mode, body if metadata is not None else markdown


def context_cache_suffix() -> str:
    mode, context = active_document_context()
    if context is None:
        return mode
    return f"{mode}:{blake3.blake3(context.encode('utf-8')).hexdigest()}"


def prepend_document_context(prompt: str) -> str:
    mode, context = active_document_context()
    if mode == "evidence_unit" or context is None:
        return prompt
    return (
        "Shared full-document semantic context follows. Use it to resolve names, aliases, "
        "relationships, references, and facts across the document. Attribute each result only "
        "to the numbered evidence unit that directly supports it; do not treat broader context "
        "as that unit's evidence.\n\n"
        f"--- full_document ---\n{context}\n--- end_full_document ---\n\n{prompt}"
    )
