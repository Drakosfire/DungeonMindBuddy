"""File-backed World SuperGraph storage with immutable revisions and atomic head.

Production graph identity is ``world_id`` + graph head revision. Preview union
loaders, ingest-run registries, and latest-ingest selectors are not part of
this contract (retained temporarily for Graph Review until PR006–PR008).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from graph_memory.union_supergraph.load import (
    dump_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.validate import (
    UnionSupergraphValidationError,
    validate_union_supergraph_store_payload,
)
from graph_memory.world_supergraph.errors import (
    WorldGraphNotFoundError,
    WorldGraphRevisionExistsError,
    WorldGraphStaleParentError,
    WorldGraphValidationError,
)
from graph_memory.world_supergraph.model import (
    WorldGraphHead,
    WorldGraphPublishResult,
    WorldGraphRevision,
)
from graph_memory.world_supergraph import paths as world_paths

# Whole-world authority transfer (cutover): the tri-state authority selector.
# ``buddy_files`` (default) keeps the file-backed store as the durable World
# Graph authority. ``quiesced`` freezes all local mutation primitives while
# reads keep serving the file store (final pre-switch correspondence window).
# ``dungeonmind`` keeps local mutations frozen while reads/writes route to the
# DungeonMind-backed authority adapter. Unknown values fail closed.
WORLD_GRAPH_AUTHORITY_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY"
WORLD_GRAPH_AUTHORITY_BUDDY_FILES = "buddy_files"
WORLD_GRAPH_AUTHORITY_QUIESCED = "quiesced"
WORLD_GRAPH_AUTHORITY_DUNGEONMIND = "dungeonmind"
_WORLD_GRAPH_AUTHORITY_MODES = frozenset(
    {
        WORLD_GRAPH_AUTHORITY_BUDDY_FILES,
        WORLD_GRAPH_AUTHORITY_QUIESCED,
        WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
    }
)


class WorldGraphAuthorityQuiescedError(RuntimeError):
    """A local World Graph mutation was attempted while authority is not local."""

    code = "world_graph_authority_quiesced"

    def __init__(self, *, world_id: str, mode: str, operation: str) -> None:
        self.world_id = world_id
        self.mode = mode
        self.operation = operation
        super().__init__(
            f"local World Graph mutation {operation!r} refused for world "
            f"{world_id!r}: authority mode is {mode!r} "
            f"({WORLD_GRAPH_AUTHORITY_ENV})"
        )


def world_graph_authority_mode(environ: dict[str, str] | None = None) -> str:
    """Parse the process authority mode; unknown values fail closed."""
    source = os.environ if environ is None else environ
    raw = source.get(WORLD_GRAPH_AUTHORITY_ENV, "").strip().lower()
    if not raw:
        return WORLD_GRAPH_AUTHORITY_BUDDY_FILES
    if raw not in _WORLD_GRAPH_AUTHORITY_MODES:
        raise ValueError(
            f"unsupported {WORLD_GRAPH_AUTHORITY_ENV} value {raw!r}; "
            f"expected one of {sorted(_WORLD_GRAPH_AUTHORITY_MODES)}"
        )
    return raw


def assert_local_world_graph_mutation_allowed(
    world_id: str,
    *,
    operation: str,
    environ: dict[str, str] | None = None,
) -> None:
    """Fail-closed guard on every local World Graph mutation primitive.

    When the authority mode is not ``buddy_files`` the file-backed store is no
    longer the write authority, so any local mutation would fork a second
    history. Raising here keeps a forgotten caller from doing exactly that.
    """
    mode = world_graph_authority_mode(environ)
    if mode != WORLD_GRAPH_AUTHORITY_BUDDY_FILES:
        raise WorldGraphAuthorityQuiescedError(
            world_id=world_id, mode=mode, operation=operation
        )


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _exclusive_world_write_lock(root: Path, world_id: str) -> Iterator[None]:
    """Per-world exclusive lock covering head read → revision write → head advance.

    Serializes concurrent publishers for the same ``world_id`` so a stale-parent
    check cannot race past an unguarded head replace.
    """
    world_paths.assert_safe_world_id(world_id)
    world_paths.world_dir(root, world_id).mkdir(parents=True, exist_ok=True)
    lock_path = world_paths.write_lock_path(root, world_id)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _require_parent_matches(
    *,
    expected_parent_revision_id: str | None,
    current_parent: str | None,
) -> None:
    """Reject when the caller supplied a parent that no longer matches the head."""
    if (
        expected_parent_revision_id is not None
        and expected_parent_revision_id != current_parent
    ):
        raise WorldGraphStaleParentError(
            "stale parent: "
            f"expected_parent_revision_id={expected_parent_revision_id!r} "
            f"current_head_revision_id={current_parent!r}"
        )


def canonicalize_graph_payload(payload: dict[str, Any]) -> str:
    """Stable JSON serialization used for hashing and on-disk graph.json bytes."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_revision_id(
    *,
    world_id: str,
    parent_revision_id: str | None,
    operation_ids: list[str],
    canonical_graph_json: str,
) -> str:
    """Content-addressed revision id: ``rev:<sha256-prefix>``."""
    hasher = hashlib.sha256()
    hasher.update(world_id.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update((parent_revision_id or "").encode("utf-8"))
    hasher.update(b"\0")
    for operation_id in operation_ids:
        hasher.update(operation_id.encode("utf-8"))
        hasher.update(b"\0")
    hasher.update(canonical_graph_json.encode("utf-8"))
    return f"rev:{hasher.hexdigest()[:32]}"


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _write_text_atomic(path, text)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def open_world_graph_head(root: Path, world_id: str) -> WorldGraphHead:
    """Load the current graph head for ``world_id``. Raises if missing."""
    path = world_paths.head_path(root, world_id)
    if not path.is_file():
        raise WorldGraphNotFoundError(f"no world graph head for world_id={world_id!r}")
    return WorldGraphHead.model_validate(_read_json(path))


def try_open_world_graph_head(root: Path, world_id: str) -> WorldGraphHead | None:
    path = world_paths.head_path(root, world_id)
    if not path.is_file():
        return None
    return WorldGraphHead.model_validate(_read_json(path))


def load_world_graph_revision_manifest(
    root: Path, world_id: str, revision_id: str
) -> WorldGraphRevision:
    path = world_paths.revision_manifest_path(root, world_id, revision_id)
    if not path.is_file():
        raise WorldGraphNotFoundError(
            f"revision manifest missing for world_id={world_id!r} revision_id={revision_id!r}"
        )
    return WorldGraphRevision.model_validate(_read_json(path))


def load_world_graph_revision(
    root: Path, world_id: str, revision_id: str
) -> UnionSupergraphStore:
    """Load one coherent immutable revision payload (not the mutable head bytes)."""
    path = world_paths.graph_payload_path(root, world_id, revision_id)
    if not path.is_file():
        raise WorldGraphNotFoundError(
            f"graph payload missing for world_id={world_id!r} revision_id={revision_id!r}"
        )
    payload = _read_json(path)
    return parse_union_supergraph_store(payload)


def load_current_world_graph(
    root: Path, world_id: str
) -> tuple[WorldGraphHead, WorldGraphRevision, UnionSupergraphStore]:
    """Open current world graph using only ``root`` + ``world_id``."""
    head = open_world_graph_head(root, world_id)
    revision = load_world_graph_revision_manifest(root, world_id, head.head_revision_id)
    store = load_world_graph_revision(root, world_id, head.head_revision_id)
    return head, revision, store


def publish_world_graph_revision(
    root: Path,
    world_id: str,
    graph: UnionSupergraphStore,
    operation_ids: list[str],
    expected_parent_revision_id: str | None = None,
) -> WorldGraphPublishResult:
    """Validate, write an immutable revision directory, then atomically advance head.

    Failed validation never mutates ``head.json``. Head read → revision write →
    head advance runs under a per-world exclusive lock; a non-None
    ``expected_parent_revision_id`` is compare-and-swapped against the head
    observed under that lock (stale-parent reject).
    """
    world_paths.assert_safe_world_id(world_id)
    assert_local_world_graph_mutation_allowed(world_id, operation="publish_world_graph_revision")
    if not operation_ids:
        raise ValueError("operation_ids must be non-empty")

    # Validate outside the lock (CPU-bound); parent CAS happens under the lock.
    payload = dump_union_supergraph_store(graph)
    try:
        validate_union_supergraph_store_payload(payload)
    except UnionSupergraphValidationError as exc:
        raise WorldGraphValidationError(str(exc)) from exc

    canonical = canonicalize_graph_payload(payload)
    payload_sha = sha256_hex(canonical)
    op_ids = list(operation_ids)
    graph_schema = str(payload.get("schema") or graph.schema)

    with _exclusive_world_write_lock(root, world_id):
        current_head = try_open_world_graph_head(root, world_id)
        current_parent = (
            current_head.head_revision_id if current_head is not None else None
        )

        # None means "attach to current head" (or create the first revision).
        # A non-None expected parent must match the head under this lock (CAS).
        _require_parent_matches(
            expected_parent_revision_id=expected_parent_revision_id,
            current_parent=current_parent,
        )

        revision_id = compute_revision_id(
            world_id=world_id,
            parent_revision_id=current_parent,
            operation_ids=op_ids,
            canonical_graph_json=canonical,
        )
        world_paths.assert_safe_revision_id(revision_id)

        rev_dir = world_paths.revision_dir(root, world_id, revision_id)
        if rev_dir.exists():
            raise WorldGraphRevisionExistsError(
                f"revision directory already exists: {revision_id}"
            )

        created_at = _utc_now_iso()
        revision = WorldGraphRevision(
            world_id=world_id,
            revision_id=revision_id,
            parent_revision_id=current_parent,
            created_at=created_at,
            operation_ids=op_ids,
            graph_schema=graph_schema,
            graph_payload_sha256=payload_sha,
            graph_payload_path=world_paths.relative_graph_payload_path(revision_id),
            status="published",
        )

        # Write complete revision directory before touching head.json.
        rev_dir.mkdir(parents=True, exist_ok=False)
        graph_path = world_paths.graph_payload_path(root, world_id, revision_id)
        _write_text_atomic(graph_path, canonical)
        _write_json_atomic(
            world_paths.revision_manifest_path(root, world_id, revision_id),
            revision.model_dump(mode="json"),
        )

        # Re-check parent immediately before head advance (true CAS under lock).
        head_now = try_open_world_graph_head(root, world_id)
        parent_now = head_now.head_revision_id if head_now is not None else None
        if parent_now != current_parent:
            raise WorldGraphStaleParentError(
                "stale parent at head advance: "
                f"observed_parent_revision_id={current_parent!r} "
                f"current_head_revision_id={parent_now!r}"
            )

        new_head = WorldGraphHead(
            world_id=world_id,
            head_revision_id=revision_id,
            updated_at=created_at,
        )
        _write_json_atomic(
            world_paths.head_path(root, world_id),
            new_head.model_dump(mode="json"),
        )
        return WorldGraphPublishResult(head=new_head, revision=revision)


def rollback_world_graph_head(
    root: Path, world_id: str, revision_id: str
) -> WorldGraphHead:
    """Crude rollback: validate revision exists, then atomically repoint head."""
    world_paths.assert_safe_world_id(world_id)
    assert_local_world_graph_mutation_allowed(world_id, operation="rollback_world_graph_head")
    world_paths.assert_safe_revision_id(revision_id)

    graph_path = world_paths.graph_payload_path(root, world_id, revision_id)
    manifest_path = world_paths.revision_manifest_path(root, world_id, revision_id)
    if not graph_path.is_file() or not manifest_path.is_file():
        raise WorldGraphNotFoundError(
            f"cannot rollback: revision {revision_id!r} incomplete or missing"
        )

    # Re-validate target revision before taking the write lock.
    payload = _read_json(graph_path)
    try:
        validate_union_supergraph_store_payload(payload)
    except UnionSupergraphValidationError as exc:
        raise WorldGraphValidationError(str(exc)) from exc

    load_world_graph_revision_manifest(root, world_id, revision_id)

    with _exclusive_world_write_lock(root, world_id):
        # Ensure current head exists (world has been published at least once).
        open_world_graph_head(root, world_id)
        new_head = WorldGraphHead(
            world_id=world_id,
            head_revision_id=revision_id,
            updated_at=_utc_now_iso(),
        )
        _write_json_atomic(
            world_paths.head_path(root, world_id),
            new_head.model_dump(mode="json"),
        )
        return new_head


def list_revision_ids(root: Path, world_id: str) -> list[str]:
    rev_root = world_paths.revisions_dir(root, world_id)
    if not rev_root.is_dir():
        return []
    ids = [p.name for p in rev_root.iterdir() if p.is_dir() and p.name.startswith("rev:")]
    return sorted(ids)
