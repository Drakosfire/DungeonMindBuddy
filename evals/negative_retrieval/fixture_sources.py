"""Read-only preflight of the synthetic related-page fixture in an isolated World."""
from hashlib import sha256

# Host-side label for the exact primary work, not a related fixture source.
CURRENT_PAGE_LABEL = "current-page"


def inspect_related_pages(request, fixture):
    """Require exact catalog membership, title, body and snapshot hashes.

    This helper calls the same read-only registry owners used by Build. The
    caller must first establish an isolated synthetic World and ensure this
    preflight runs outside the product turn's acquisition probe.
    """
    from apps.live_control_server.services import build_related_pages

    expected = fixture["related_pages"]
    if not isinstance(expected, list) or any(not isinstance(x, dict) for x in expected):
        raise ValueError("Invalid expected related-page fixture")
    by_title = {}
    labels = set()
    for row in expected:
        label, title, body = row["label"], row["title"], row["body"]
        if (not all(isinstance(x, str) and x.strip() for x in (label, title, body))
                or title in by_title or label in labels or label == CURRENT_PAGE_LABEL):
            raise ValueError("Related-page fixtures need unique nonblank titles and nonreserved labels")
        labels.add(label)
        by_title[title] = row
    offered = build_related_pages.discover(request)
    if (not isinstance(offered, list) or len(offered) != len(expected)
            or {p.get("title") for p in offered} != set(by_title)):
        raise ValueError("Related-page catalog differs from the frozen fixture")
    results = []
    documents = set()
    for pointer in offered:
        document_id = pointer.get("document_id")
        if (pointer.get("world_id") != request.owner_scope.world_id
                or not isinstance(document_id, str) or not document_id
                or document_id == request.primary_work.object_id or document_id in documents
                or type(pointer.get("registry_revision")) is not int or pointer["registry_revision"] < 1):
            raise ValueError("Related-page catalog identity differs from the requested World")
        documents.add(document_id)
        actual = build_related_pages.materialize(pointer)
        row = by_title[pointer["title"]]
        body_hash = sha256(row["body"].encode("utf-8")).hexdigest()
        if (actual["title"] != row["title"] or actual["markdown"] != row["body"]
                or actual["content_sha256"] != body_hash
                or actual["document_id"] != pointer["document_id"]
                or actual["registry_revision"] != pointer["registry_revision"]
                or actual["world_id"] != pointer["world_id"]):
            raise ValueError("Related-page snapshot differs from the frozen fixture")
        results.append({"label": row["label"], "title": row["title"], "world_id": actual["world_id"], "document_id": str(actual["document_id"]),
                        "registry_revision": actual["registry_revision"], "content_sha256": body_hash})
    return sorted(results, key=lambda row: row["label"])


def verify_related_record(request, fixture, record):
    """Validate pre/post source inventory against the evaluator fixture."""
    if (record.get("schema") != "dmb_negative_retrieval_fixture_sources_v1"
            or record.get("case_id") != fixture["id"] or record.get("status") != "stable"
            or record.get("before") != record.get("after")
            or not isinstance(record.get("before"), list)):
        raise ValueError("Fixture source record is missing, changed, or belongs to another case")
    expected = fixture["related_pages"]
    if not isinstance(expected, list) or len(expected) != len(record["before"]):
        raise ValueError("Fixture source inventory size differs")
    by_label = {row["label"]: row for row in expected}
    if len(by_label) != len(expected) or CURRENT_PAGE_LABEL in by_label:
        raise ValueError("Duplicate or reserved related fixture label")
    found, documents = set(), set()
    for row in record["before"]:
        label = row["label"]
        if label not in by_label or label in found:
            raise ValueError("Unexpected or repeated fixture source")
        digest = sha256(by_label[label]["body"].encode("utf-8")).hexdigest()
        document_id = row["document_id"]
        if (row["title"] != by_label[label]["title"]
                or row["world_id"] != request["owner_scope"]["world_id"]
                or not isinstance(document_id, str) or not document_id
                or document_id == request["primary_work"]["object_id"] or document_id in documents
                or type(row["registry_revision"]) is not int or row["registry_revision"] < 1
                or row["content_sha256"] != digest):
            raise ValueError("Fixture source identity or content differs")
        found.add(label)
        documents.add(document_id)
    return True


def related_trace_labels(trace, record):
    """Map related-read trace items only through a validated fixture inventory.

    Call after verify_related_record. The trace display item is generated by the
    product from the committed title, revision and read UUID. Ambiguous or
    malformed items remain unmapped rather than being guessed.
    """
    from uuid import UUID
    from .trace_observation import RELATED_POLICY

    result = {}
    for attempt in trace.get("attempts", []):
        for event in attempt.get("observations", []):
            if (event.get("kind") != "context_decision" or event.get("action") != "retrieved"
                    or event.get("policy_version") != RELATED_POLICY):
                continue
            for item in event.get("item_ids", []):
                if not isinstance(item, str):
                    continue
                matches = []
                for row in record["before"]:
                    prefix = f"{row['title']} · saved revision {row['registry_revision']} · "
                    if item.startswith(prefix):
                        try:
                            UUID(item[len(prefix):])
                        except ValueError:
                            continue
                        matches.append(row["label"])
                if len(matches) == 1:
                    result[item] = matches[0]
    return result
