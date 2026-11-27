"""Fixture-only saved primary-page observations, never an acquisition journal."""
from hashlib import sha256


def inspect_primary_page(world, work):
    """Read the current committed page outside the observed turn; retain no body."""
    from apps.live_control_server.services import build_related_pages
    from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot

    document = work["object_id"]
    snapshot = get_committed_page_snapshot(build_related_pages.root(), document)
    row = snapshot.record
    body = snapshot.markdown
    digest = sha256(body.encode("utf-8")).hexdigest()
    if (str(row.world_id) != world or str(row.document_id) != document
            or type(row.revision) is not int or row.revision < 1
            or snapshot.loaded_revision != row.revision or snapshot.content_sha256 != digest):
        raise ValueError("Primary saved page snapshot is unavailable or inconsistent")
    return {"world_id": world, "document_id": document,
            "registry_revision": row.revision, "content_sha256": digest}


def expected_primary_page(fixture, world, work):
    """Bind the actual pre-turn page to the frozen fixture and request."""
    body = fixture["page"]
    digest = sha256(body.encode("utf-8")).hexdigest()
    revision = work["expected_revision"]
    if (not isinstance(world, str) or not world or not isinstance(work["object_id"], str)
            or not work["object_id"] or type(revision) is not int or revision < 1
            or work["expected_content_sha256"] != digest):
        raise ValueError("Primary work does not match the frozen fixture")
    return {"world_id": world, "document_id": work["object_id"],
            "registry_revision": revision, "content_sha256": digest}


def validate_primary_page_record(record, fixture, request):
    """Return stable/changed for exact bound observations, otherwise reject."""
    if (not isinstance(record, dict) or set(record) != {"schema", "case_id", "status", "before", "after", "error_type"}
            or record["schema"] != "dmb_negative_retrieval_primary_page_v1"
            or record["case_id"] != fixture["id"] or record["status"] not in {"stable", "changed"}
            or record["error_type"] is not None):
        raise ValueError("Primary page observation is incomplete")
    before = expected_primary_page(fixture, request["owner_scope"]["world_id"], request["primary_work"])
    after = record["after"]
    if (record["before"] != before or not isinstance(after, dict) or set(after) != set(before)
            or after["world_id"] != before["world_id"] or after["document_id"] != before["document_id"]
            or type(after["registry_revision"]) is not int or after["registry_revision"] < 1
            or not isinstance(after["content_sha256"], str) or len(after["content_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in after["content_sha256"])
            or (record["status"] == "stable") != (before == after)):
        raise ValueError("Primary page observation is not bound to the captured request")
    return record["status"]
