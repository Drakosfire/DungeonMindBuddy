"""Bounded head-following projection recipe registry and replay (OPT03)."""


from __future__ import annotations


import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionRequest,
)
from graph_memory.world_projection_cache import projection_cache_enabled


logger = logging.getLogger(__name__)


RecipeStatus = Literal[
    "registered",
    "refreshed",
    "warm_hit",
    "warm_built",
    "warm_coalesced",
    "superseded",
    "failed",
]


def _dungeonmind_authority_active() -> bool:
    """R.3: in ``dungeonmind`` mode reads execute natively in DungeonMind.


    Projection recipes exist only to warm the Buddy projection cache, which
    has no consumer on the direct read path; registration and replay are
    no-ops in this mode.
    """
    from apps.live_control_server import config


    return (
        config.world_graph_authority_mode()
        == config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )


_DEFAULT_MAX_ENTRIES = 16
_DEFAULT_TTL_S = 900.0
_DEFAULT_WARM_BATCH = 4
_OBSERVATION_CAP = 256
_OBSERVATION_TRIM = 128


@dataclass(frozen=True)
class RecipeKey:
    resolved_root: str
    world_id: str
    campaign_id: str
    focus_kind: str
    focus_session_id: str
    focus_campaign_id: str
    admissibility: str
    scope_mode: str


@dataclass
class _RecipeEntry:
    key: RecipeKey
    request: WorldGraphProjectionRequest
    last_used_at: float


@dataclass(frozen=True)
class RecipeObservation:
    event: str
    resolved_root: str
    world_id: str
    campaign_id: str
    scope_mode: str
    focus_kind: str
    focus_session_id: str
    revision_id: str
    status: RecipeStatus
    cache_status: str | None = None
    warm_ms: float | None = None
    error_type: str | None = None


    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "resolved_root": self.resolved_root,
            "world_id": self.world_id,
            "campaign_id": self.campaign_id,
            "scope_mode": self.scope_mode,
            "focus_kind": self.focus_kind,
            "focus_session_id": self.focus_session_id,
            "revision_id": self.revision_id,
            "status": self.status,
            "cache_status": self.cache_status,
            "warm_ms": self.warm_ms,
            "error_type": self.error_type,
        }


_REGISTRY: OrderedDict[RecipeKey, _RecipeEntry] = OrderedDict()
_REGISTRY_LOCK = threading.Lock()
_OBSERVATIONS: list[RecipeObservation] = []
_OBS_LOCK = threading.Lock()


_MAX_ENTRIES = _DEFAULT_MAX_ENTRIES
_TTL_S = _DEFAULT_TTL_S
_WARM_BATCH = _DEFAULT_WARM_BATCH
_CLOCK: Callable[[], float] = time.monotonic
_WARM_BLOCK: threading.Event | None = None
_WARM_BLOCK_RELEASE: threading.Event | None = None


def _now() -> float:
    return _CLOCK()


def _is_eligible(request: WorldGraphProjectionRequest) -> bool:
    return (
        request.revision_pin is None
        and request.query_text is None
        and projection_cache_enabled()
    )


def _recipe_key(*, root: Path, request: WorldGraphProjectionRequest) -> RecipeKey:
    focus = request.focus
    return RecipeKey(
        resolved_root=str(root.resolve()),
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus_kind=focus.kind,
        focus_session_id=str(focus.session_id or ""),
        focus_campaign_id=str(getattr(focus, "campaign_id", None) or ""),
        admissibility=str(request.admissibility),
        scope_mode=str(getattr(request, "scope_mode", "campaign") or "campaign"),
    )


def _normalized_request(request: WorldGraphProjectionRequest) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus.model_copy(deep=True),
        admissibility=request.admissibility,
        scope_mode=request.scope_mode,
        revision_pin=None,
        query_text=None,
    )


def _emit_observation(observation: RecipeObservation) -> None:
    with _OBS_LOCK:
        _OBSERVATIONS.append(observation)
        if len(_OBSERVATIONS) > _OBSERVATION_CAP:
            del _OBSERVATIONS[:-_OBSERVATION_TRIM]
    logger.info("world_graph_projection_recipe", extra=observation.as_dict())


def _prune_expired(now: float) -> None:
    expired = [
        key
        for key, entry in _REGISTRY.items()
        if now - entry.last_used_at > _TTL_S
    ]
    for key in expired:
        _REGISTRY.pop(key, None)


def register_projection_recipe(
    request: WorldGraphProjectionRequest,
    *,
    root: Path,
) -> None:
    """Best-effort register or refresh one eligible projection recipe."""
    try:
        if _dungeonmind_authority_active():
            return
        if not _is_eligible(request):
            return
        key = _recipe_key(root=root, request=request)
        now = _now()
        with _REGISTRY_LOCK:
            _prune_expired(now)
            existing = _REGISTRY.get(key)
            normalized = _normalized_request(request)
            if existing is not None:
                existing.last_used_at = now
                existing.request = normalized
                _REGISTRY.move_to_end(key)
                status: RecipeStatus = "refreshed"
            else:
                _REGISTRY[key] = _RecipeEntry(
                    key=key,
                    request=normalized,
                    last_used_at=now,
                )
                while len(_REGISTRY) > _MAX_ENTRIES:
                    _REGISTRY.popitem(last=False)
                status = "registered"
        _emit_observation(
            RecipeObservation(
                event="world_graph_projection_recipe",
                resolved_root=key.resolved_root,
                world_id=key.world_id,
                campaign_id=key.campaign_id,
                scope_mode=key.scope_mode,
                focus_kind=key.focus_kind,
                focus_session_id=key.focus_session_id,
                revision_id="",
                status=status,
            )
        )
    except Exception:
        logger.exception("projection recipe registration failed")


def _head_matches(*, root: Path, world_id: str, revision_id: str) -> bool:
    """Buddy head matching retired; recipes never warm against filesystem graphs."""
    del root, world_id, revision_id
    return False


def _snapshot_recipes(*, root: Path, world_id: str) -> list[_RecipeEntry]:
    resolved = str(root.resolve())
    now = _now()
    with _REGISTRY_LOCK:
        _prune_expired(now)
        # OrderedDict end is most-recently used; replay MRU-first.
        selected: list[_RecipeEntry] = []
        for entry in reversed(_REGISTRY.values()):
            if entry.key.resolved_root != resolved:
                continue
            if entry.key.world_id != world_id:
                continue
            selected.append(entry)
            if len(selected) >= _WARM_BATCH:
                break
        return selected


def warm_projection_recipes_for_ready_revision(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    still_current: Callable[[], bool],
) -> None:
    """Replay bounded eligible recipes against one exact ready revision."""
    try:
        if _dungeonmind_authority_active():
            return
        if not projection_cache_enabled():
            return
        if not still_current():
            return
        if not _head_matches(root=root, world_id=world_id, revision_id=revision_id):
            return


        recipes = _snapshot_recipes(root=root, world_id=world_id)
        for entry in recipes:
            if not still_current():
                return
            if not _head_matches(root=root, world_id=world_id, revision_id=revision_id):
                _emit_observation(
                    RecipeObservation(
                        event="world_graph_projection_recipe",
                        resolved_root=entry.key.resolved_root,
                        world_id=entry.key.world_id,
                        campaign_id=entry.key.campaign_id,
                        scope_mode=entry.key.scope_mode,
                        focus_kind=entry.key.focus_kind,
                        focus_session_id=entry.key.focus_session_id,
                        revision_id=revision_id,
                        status="superseded",
                    )
                )
                return


            block = _WARM_BLOCK
            release = _WARM_BLOCK_RELEASE
            if block is not None and release is not None:
                block.wait(timeout=30.0)
                release.wait(timeout=30.0)


            warm_request = entry.request.model_copy(
                update={"revision_pin": revision_id},
            )
            started = time.perf_counter()
            try:
                from apps.live_control_server.services.world_graph_projection import (
                    project_world_graph,
                )


                project_world_graph(warm_request, root=root)
                observation = None
                cache_status = (
                    observation.projection_cache_status if observation is not None else None
                )
                if cache_status == "hit":
                    status: RecipeStatus = "warm_hit"
                elif cache_status == "coalesced":
                    status = "warm_coalesced"
                else:
                    status = "warm_built"
                warm_ms = (time.perf_counter() - started) * 1000.0
                _emit_observation(
                    RecipeObservation(
                        event="world_graph_projection_recipe",
                        resolved_root=entry.key.resolved_root,
                        world_id=entry.key.world_id,
                        campaign_id=entry.key.campaign_id,
                        scope_mode=entry.key.scope_mode,
                        focus_kind=entry.key.focus_kind,
                        focus_session_id=entry.key.focus_session_id,
                        revision_id=revision_id,
                        status=status,
                        cache_status=cache_status,
                        warm_ms=warm_ms,
                    )
                )
                # Replay must not mutate demand recency (TTL / MRU).
            except Exception as exc:
                _emit_observation(
                    RecipeObservation(
                        event="world_graph_projection_recipe",
                        resolved_root=entry.key.resolved_root,
                        world_id=entry.key.world_id,
                        campaign_id=entry.key.campaign_id,
                        scope_mode=entry.key.scope_mode,
                        focus_kind=entry.key.focus_kind,
                        focus_session_id=entry.key.focus_session_id,
                        revision_id=revision_id,
                        status="failed",
                        error_type=type(exc).__name__,
                    )
                )
    except Exception:
        logger.exception("projection recipe warm batch failed")


def get_recipe_observations() -> list[RecipeObservation]:
    with _OBS_LOCK:
        return list(_OBSERVATIONS)


def clear_recipe_observations() -> None:
    with _OBS_LOCK:
        _OBSERVATIONS.clear()


def reset_projection_recipes_for_tests(
    *,
    max_entries: int | None = None,
    ttl_s: float | None = None,
    warm_batch: int | None = None,
    clock: Callable[[], float] | None = None,
) -> None:
    """Reset registry, observations, and test hooks."""
    global _MAX_ENTRIES, _TTL_S, _WARM_BATCH, _CLOCK, _WARM_BLOCK, _WARM_BLOCK_RELEASE
    with _REGISTRY_LOCK:
        _REGISTRY.clear()
    clear_recipe_observations()
    _MAX_ENTRIES = _DEFAULT_MAX_ENTRIES if max_entries is None else max(1, int(max_entries))
    _TTL_S = _DEFAULT_TTL_S if ttl_s is None else max(0.0, float(ttl_s))
    _WARM_BATCH = _DEFAULT_WARM_BATCH if warm_batch is None else max(1, int(warm_batch))
    _CLOCK = time.monotonic if clock is None else clock
    _WARM_BLOCK = None
    _WARM_BLOCK_RELEASE = None


def projection_recipe_registry_stats() -> dict[str, int]:
    with _REGISTRY_LOCK:
        return {"size": len(_REGISTRY), "max_entries": _MAX_ENTRIES}


def list_projection_recipe_keys_for_tests() -> list[RecipeKey]:
    with _REGISTRY_LOCK:
        return list(_REGISTRY.keys())


def set_recipe_warm_block_for_tests(
    *,
    block: threading.Event,
    release: threading.Event,
) -> None:
    global _WARM_BLOCK, _WARM_BLOCK_RELEASE
    _WARM_BLOCK = block
    _WARM_BLOCK_RELEASE = release


__all__ = [
    "RecipeKey",
    "RecipeObservation",
    "RecipeStatus",
    "clear_recipe_observations",
    "get_recipe_observations",
    "list_projection_recipe_keys_for_tests",
    "projection_recipe_registry_stats",
    "register_projection_recipe",
    "reset_projection_recipes_for_tests",
    "set_recipe_warm_block_for_tests",
    "warm_projection_recipes_for_ready_revision",
]
