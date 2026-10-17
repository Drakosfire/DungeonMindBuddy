"""Buddy-owned acquisition lifetime around Core's exact-source read session."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from typing import Protocol

from dungeonmind.application.world_graph_retrieval import (
    ReviewedObservationSelectionRequest,
    ReviewedObservationSelectionResult,
    ReviewedSourceSessionRequest,
    SourceAnchorBatchResolution,
)
from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2
from graph_memory.retrieval.models import WorldGraphObservationSelectionRequest

from . import world_graph_reads as reads


class _NativeSession(Protocol):
    def select_observations(
        self, assertion_ids: tuple[str, ...], *, max_bytes: int = 262144,
    ) -> ReviewedObservationSelectionResult: ...

    def resolve_anchors(self, anchor_ids: tuple[str, ...]) -> SourceAnchorBatchResolution: ...


class ReviewedSourceWave:
    """Bound facade; refuses retargeting and retained use after wave exit."""

    def __init__(self, request: ReviewedSourceSessionRequest, session: _NativeSession):
        self.__request = deepcopy(request)
        self.__session: _NativeSession | None = session

    def close(self) -> None:
        self.__session = None

    def _active(self, projection: WorldGraphProjectionRequestV2) -> _NativeSession:
        if self.__session is None:
            raise RuntimeError("reviewed source acquisition wave is closed")
        if projection != self.__request.projection:
            raise ValueError("reviewed source acquisition projection differs")
        return self.__session

    def select(self, request: ReviewedObservationSelectionRequest) -> ReviewedObservationSelectionResult:
        session = self._active(request.projection)
        if (request.source_artifact_id != self.__request.source_artifact_id
                or request.source_revision_id != self.__request.source_revision_id):
            raise ValueError("reviewed source acquisition source differs")
        return session.select_observations(request.assertion_ids, max_bytes=request.max_bytes)

    def resolve(
        self, projection: WorldGraphProjectionRequestV2, anchor_ids: tuple[str, ...],
    ) -> SourceAnchorBatchResolution:
        return self._active(projection).resolve_anchors(anchor_ids)


@contextmanager
def reviewed_source_wave(
    services: reads.DirectWorldGraphReadServices,
    request: WorldGraphObservationSelectionRequest,
) -> Iterator[reads.DirectWorldGraphReadServices]:
    """Use only around synchronous source acquisition, never provider dispatch."""
    if services.reviewed_source_wave is not None:
        raise ValueError("nested reviewed source acquisition wave")
    projection = reads._map_retrieval_context(request, services.binding)
    captured = ReviewedSourceSessionRequest(
        projection, request.source_artifact_id, request.source_revision_id,
    )
    with services.retrieval.reviewed_source_session(captured) as native:
        wave = ReviewedSourceWave(captured, native)
        try:
            yield replace(services, reviewed_source_wave=wave)
        finally:
            wave.close()
