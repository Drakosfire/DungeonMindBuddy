"""Ingestion utilities for DungeonMindBuddy."""

from importlib import import_module

_EXPORT_MODULES = {
    "docx_to_markdown": "src.ingestion.docx_converter",
    "markdown_passthrough": "src.ingestion.docx_converter",
    "AsyncOpenAIResponsesEntityClient": "src.ingestion.entity_extractor",
    "OpenAIResponsesEntityClient": "src.ingestion.entity_extractor",
    "UsageStats": "src.ingestion.entity_extractor",
    "extract_entities_batch": "src.ingestion.entity_extractor",
    "run_entity_extraction": "src.ingestion.entity_extractor",
    "AsyncOpenAIResponsesFactClient": "src.ingestion.fact_extractor",
    "OpenAIResponsesFactClient": "src.ingestion.fact_extractor",
    "extract_facts_batch": "src.ingestion.fact_extractor",
    "run_fact_extraction": "src.ingestion.fact_extractor",
    "build_mirathorn_event_slice": "src.ingestion.event_sourced_slice",
    "DocumentMetadata": "ingestion.frontmatter",
    "FrontmatterError": "ingestion.frontmatter",
    "FrontmatterParseError": "ingestion.frontmatter",
    "FrontmatterValidationError": "ingestion.frontmatter",
    "load_document_frontmatter": "ingestion.frontmatter",
    "parse_document_frontmatter": "ingestion.frontmatter",
    "render_frontmatter": "ingestion.frontmatter",
    "write_document_with_frontmatter": "ingestion.frontmatter",
    "OpenAIFrontmatterInferenceClient": "src.ingestion.frontmatter_inference",
    "infer_frontmatter_metadata": "src.ingestion.frontmatter_inference",
}
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module), name)
