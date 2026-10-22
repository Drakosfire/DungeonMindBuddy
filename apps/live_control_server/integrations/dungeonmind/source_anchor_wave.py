"""Operation-scoped native anchor metadata; source bodies remain separately authorized."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace

from dungeonmind.application.world_graph_retrieval import (
    SourceAnchorBatchRequest,
    SourceAnchorBatchResolution,
)

from . import world_graph_reads as reads


class SourceAnchorWave:
    def __init__(self, projection, resolutions, snapshot):
        self._projection = deepcopy(projection)
        self._resolutions = {item.anchor_id: deepcopy(item) for item in resolutions}
        self._snapshot = deepcopy(snapshot)

    def close(self):
        self._resolutions = None
        self._snapshot = None

    def resolve(self, projection, anchor_ids):
        if self._resolutions is None:
            raise RuntimeError("source anchor acquisition wave is closed")
        # Validate the same native request contract even for a cached subset.
        request = SourceAnchorBatchRequest(projection, anchor_ids)
        if projection != self._projection or any(
            key not in self._resolutions for key in request.anchor_ids
        ):
            raise ValueError("source anchor acquisition selector differs")
        return SourceAnchorBatchResolution(
            deepcopy(self._snapshot),
            tuple(deepcopy(self._resolutions[key]) for key in request.anchor_ids),
        )


@contextmanager
def source_anchor_wave(services, request, anchor_ids):
    """Resolve admitted metadata once; close before any provider dispatch."""
    if (
        services.reviewed_source_wave is not None
        or services.source_anchor_wave is not None
    ):
        raise ValueError("nested source anchor acquisition wave")
    if not anchor_ids or len(set(anchor_ids)) != len(anchor_ids):
        raise ValueError("source anchor acquisition requires distinct selectors")
    projection = reads._map_retrieval_context(request, services.binding)
    ids = tuple(reads._dnd_anchor_id(key) for key in anchor_ids)
    resolutions = []
    snapshot = None
    # Core's existing request capacity; no change to body authorizations.
    for offset in range(0, len(ids), 128):
        batch = ids[offset : offset + 128]
        result = services.retrieval.resolve_source_anchors(
            SourceAnchorBatchRequest(projection, batch)
        )
        if (
            result.snapshot.world_id != projection.world_id
            or result.snapshot.revision_id != projection.revision_pin
            or snapshot is not None
            and snapshot != result.snapshot
            or tuple(item.anchor_id for item in result.resolutions) != batch
            or any(
                item.snapshot != result.snapshot
                or item.found != (item.anchor is not None)
                or item.anchor is not None
                and item.anchor.anchor_id != item.anchor_id
                for item in result.resolutions
            )
        ):
            raise ValueError("native source anchor acquisition identity differs")
        snapshot = result.snapshot
        resolutions.extend(result.resolutions)
    wave = SourceAnchorWave(projection, resolutions, snapshot)
    try:
        yield replace(services, source_anchor_wave=wave)
    finally:
        wave.close()
