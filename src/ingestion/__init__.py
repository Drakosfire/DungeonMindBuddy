"""Ingestion utilities for DungeonMindBuddy."""

from src.ingestion.docx_converter import docx_to_markdown, markdown_passthrough
from src.ingestion.entity_extractor import (
    AsyncOpenAIResponsesEntityClient,
    OpenAIResponsesEntityClient,
    UsageStats,
    extract_entities_batch,
    run_entity_extraction,
)
from src.ingestion.fact_extractor import (
    AsyncOpenAIResponsesFactClient,
    OpenAIResponsesFactClient,
    extract_facts_batch,
    run_fact_extraction,
)
from src.ingestion.event_sourced_slice import build_mirathorn_event_slice
from src.ingestion.frontmatter import (
    DocumentMetadata,
    FrontmatterError,
    FrontmatterParseError,
    FrontmatterValidationError,
    load_document_frontmatter,
    parse_document_frontmatter,
    render_frontmatter,
    write_document_with_frontmatter,
)
from src.ingestion.frontmatter_inference import (
    OpenAIFrontmatterInferenceClient,
    infer_frontmatter_metadata,
)

__all__ = [
    "docx_to_markdown",
    "markdown_passthrough",
    "AsyncOpenAIResponsesEntityClient",
    "OpenAIResponsesEntityClient",
    "UsageStats",
    "extract_entities_batch",
    "run_entity_extraction",
    "AsyncOpenAIResponsesFactClient",
    "OpenAIResponsesFactClient",
    "extract_facts_batch",
    "run_fact_extraction",
    "build_mirathorn_event_slice",
    "DocumentMetadata",
    "FrontmatterError",
    "FrontmatterParseError",
    "FrontmatterValidationError",
    "load_document_frontmatter",
    "parse_document_frontmatter",
    "render_frontmatter",
    "write_document_with_frontmatter",
    "OpenAIFrontmatterInferenceClient",
    "infer_frontmatter_metadata",
]
