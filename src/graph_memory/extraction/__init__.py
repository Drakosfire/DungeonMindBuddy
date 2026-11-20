'Public category-extraction contracts; no alternate compact extractor.'

from importlib import import_module

_EXPORT_MODULES = {
    "CategoryGraphExtractionError": "category_candidate_graph_extractor",
    "CategoryGraphExtractionOptions": "category_candidate_graph_extractor",
    "CategoryGraphExtractionResult": "category_candidate_graph_extractor",
    "CategoryGraphPassClient": "category_candidate_graph_extractor",
    "FixtureCategoryGraphPassClient": "category_candidate_graph_extractor",
    "OpenAICategoryGraphPassClient": "category_candidate_graph_extractor",
    "extract_category_candidate_graph": "category_candidate_graph_extractor",
    "resolve_category_graph_model": "category_candidate_graph_extractor",
    "category_pass_text_format": "category_candidate_graph_schema",
    "schema_for_pass": "category_candidate_graph_schema",
}
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f".{_EXPORT_MODULES[name]}", __name__), name)
