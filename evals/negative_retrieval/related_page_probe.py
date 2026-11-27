"""Opt-in process-local probe for two actual related-page acquisition owners.

Use only inside an isolated, serial evaluator process. This does not cover Graph,
corpus or every other source owner and is not a complete acquisition journal.
"""
from contextlib import contextmanager, ExitStack
from functools import wraps
from hashlib import sha256
from importlib import import_module
from threading import Lock
from unittest.mock import patch
from uuid import UUID

_lock = Lock()


@contextmanager
def observe_related_page_owners():
    """Record entry and completion without changing arguments or return values."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("Related-page observation requires a serial process")
    records = []
    record_lock = Lock()
    try:
        from apps.live_control_server.services import build_related_pages

        def watch(name, function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                row = {"owner": name, "state": "entered"}
                if name == "related_page_materialization" and args:
                    pointer = args[0]
                    get = pointer.get if isinstance(pointer, dict) else lambda key: getattr(pointer, key, None)
                    identity = get("document_id")
                    if isinstance(identity, (str, UUID)) and str(identity):
                        row["document_id"] = str(identity)
                    world = get("world_id")
                    revision = get("registry_revision")
                    if isinstance(world, str) and world:
                        row["world_id"] = world
                    if type(revision) is int and revision > 0:
                        row["registry_revision"] = revision
                with record_lock:
                    records.append(row)
                try:
                    result = function(*args, **kwargs)
                except BaseException:
                    with record_lock:
                        row["state"] = "raised"
                    raise
                with record_lock:
                    row["state"] = "returned"
                    # Store no body; record its digest only when the actual
                    # returned text and declared digest agree. Malformed
                    # results remain unproven without changing owner behavior.
                    if name == "related_page_materialization" and isinstance(result, dict):
                        body = result.get("markdown")
                        try:
                            body_hash = sha256(body.encode("utf-8")).hexdigest() if isinstance(body, str) else None
                        except UnicodeError:
                            body_hash = None
                        if body_hash is not None and result.get("content_sha256") == body_hash:
                            world, document, revision = (result.get("world_id"), result.get("document_id"),
                                                         result.get("registry_revision"))
                            if (isinstance(world, str) and world and isinstance(document, (str, UUID))
                                    and str(document) and type(revision) is int and revision > 0):
                                row.update(returned_world_id=world, returned_document_id=str(document),
                                           returned_registry_revision=revision, returned_content_sha256=body_hash)
                return result
            return wrapped

        # Older source lineages do not have the pending Build owner. Only the
        # absence of that module is optional; broken imports must still fail.
        module_name = "apps.live_control_server.services.build_pending_app_pages"
        try:
            pending = import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name:
                raise
            pending = None
        with ExitStack() as stack:
            stack.enter_context(patch.object(build_related_pages, "discover", watch("related_catalog_discovery", build_related_pages.discover)))
            stack.enter_context(patch.object(build_related_pages, "materialize", watch("related_page_materialization", build_related_pages.materialize)))
            direct = getattr(pending, "_lookup_current_saved_page", None)
            if callable(direct):
                stack.enter_context(patch.object(pending, "_lookup_current_saved_page", watch("current_page_metadata", direct)))
            yield records
    finally:
        _lock.release()


def acquisition_labels(records, *, label_by_document=None, completed_only=False, primary_pointer=None):
    """Project observed page-materialization attempts as unmapped reads.

    Document identity is host-side evidence, never model input. Materialization may be witnessed again
    in the trace; the case-level violation remains the same. With completed_only,
    only returned calls are included. No absence claim
    follows from this partial probe.
    """
    from .trace_observation import UNKNOWN
    if not isinstance(records, list) or any(
        not isinstance(row, dict)
        or row.get("owner") not in {"related_catalog_discovery", "related_page_materialization", "current_page_metadata"}
        or row.get("state") not in {"entered", "returned", "raised"}
        for row in records
    ):
        raise ValueError("Malformed related-page probe evidence")
    labels = label_by_document or {}
    def label(row):
        if (primary_pointer is not None and type(row.get("registry_revision")) is int
                and all(row.get(key) == value for key, value in primary_pointer.items())):
            return "current-page"
        document = row.get("document_id")
        return labels.get(document, UNKNOWN) if isinstance(document, str) else UNKNOWN
    return [label(row) for row in records
            if row["owner"] == "related_page_materialization"
            and (not completed_only or row["state"] == "returned")]


def fixture_related_labels(records, inventory, *, completed_only=False):
    """Bind attempts and proven returned bytes to exact verified fixture pointers."""
    from .trace_observation import UNKNOWN
    acquisition_labels(records)  # Validate the complete records first.
    pointers = {(row["world_id"], row["document_id"], row["registry_revision"]): row for row in inventory}
    labels = []
    for record in records:
        if record["owner"] != "related_page_materialization":
            continue
        world, document, revision = record.get("world_id"), record.get("document_id"), record.get("registry_revision")
        row = (pointers.get((world, document, revision)) if isinstance(world, str)
               and isinstance(document, str) and type(revision) is int else None)
        if completed_only:
            if (record["state"] != "returned" or row is None
                    or record.get("returned_world_id") != row["world_id"]
                    or record.get("returned_document_id") != row["document_id"]
                    or type(record.get("returned_registry_revision")) is not int
                    or record.get("returned_registry_revision") != row["registry_revision"]
                    or record.get("returned_content_sha256") != row["content_sha256"]):
                continue
        labels.append(row["label"] if row is not None else UNKNOWN)
    return labels


def catalog_discovery_count(records):
    """Count observed catalog attempts, including empty and failed attempts."""
    acquisition_labels(records)  # Validate the complete record shape first.
    return sum(row["owner"] == "related_catalog_discovery" for row in records)
