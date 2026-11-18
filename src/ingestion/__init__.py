"""Ingestion utilities for DungeonMindBuddy."""

from importlib import import_module

_EXPORT_MODULES = {
    "docx_to_markdown": "ingestion.docx_converter",
    "markdown_passthrough": "ingestion.docx_converter",
    "AsyncOpenAIResponsesEntityClient": "ingestion.entity_extractor",
    "OpenAIResponsesEntityClient": "ingestion.entity_extractor",
    "UsageStats": "ingestion.entity_extractor",
    "extract_entities_batch": "ingestion.entity_extractor",
    "run_entity_extraction": "ingestion.entity_extractor",
    "AsyncOpenAIResponsesFactClient": "ingestion.fact_extractor",
    "OpenAIResponsesFactClient": "ingestion.fact_extractor",
    "extract_facts_batch": "ingestion.fact_extractor",
    "run_fact_extraction": "ingestion.fact_extractor",
    "build_mirathorn_event_slice": "ingestion.event_sourced_slice",
    "DocumentMetadata": "ingestion.frontmatter",
    "FrontmatterError": "ingestion.frontmatter",
    "FrontmatterParseError": "ingestion.frontmatter",
    "FrontmatterValidationError": "ingestion.frontmatter",
    "load_document_frontmatter": "ingestion.frontmatter",
    "parse_document_frontmatter": "ingestion.frontmatter",
    "render_frontmatter": "ingestion.frontmatter",
    "write_document_with_frontmatter": "ingestion.frontmatter",
    "OpenAIFrontmatterInferenceClient": "ingestion.frontmatter_inference",
    "infer_frontmatter_metadata": "ingestion.frontmatter_inference",
}
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module), name)
