"""Durable, product-owned source content authority."""

from application_state.source.service import (
    get_source_markdown,
    persist_source_markdown,
)
from application_state.source.types import SourceMarkdownRecord

__all__ = [
    "SourceMarkdownRecord",
    "get_source_markdown",
    "persist_source_markdown",
]
