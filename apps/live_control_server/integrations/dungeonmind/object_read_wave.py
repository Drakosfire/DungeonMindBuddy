"""One admitted Plan selection's exact native object read lifetime."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace

from . import world_graph_reads as reads


class ObjectReadWave:
    def __init__(self, projection, native):
        self._projection = deepcopy(projection)
        self._native = native

    def close(self):
        self._native = None

    def get_object_views(self, projection, *, object_id, bounds):
        if self._native is None:
            raise RuntimeError("object acquisition wave is closed")
        if projection != self._projection:
            raise ValueError("object acquisition projection differs")
        return self._native.get_object_views(object_id=object_id, bounds=bounds)


@contextmanager
def object_read_wave(services, request, *, object_ids):
    if (services.object_read_wave is not None or services.reviewed_source_wave is not None
            or services.source_anchor_wave is not None):
        raise ValueError("nested object acquisition wave")
    projection = reads._map_retrieval_context(request, services.binding)
    with services.retrieval.object_read_session(projection, object_ids=object_ids) as native:
        wave = ObjectReadWave(projection, native)
        try:
            yield replace(services, object_read_wave=wave)
        finally:
            wave.close()
