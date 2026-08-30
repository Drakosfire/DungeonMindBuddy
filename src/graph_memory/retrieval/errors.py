"""Stable World Graph retrieval error contract (storage-neutral)."""

from __future__ import annotations

from graph_memory.retrieval.models import WorldGraphRetrievalDiagnostic


class WorldGraphRetrievalError(Exception):
    """Stable retrieval failure with an API-safe code and diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[WorldGraphRetrievalDiagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])
