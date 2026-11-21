"""Transactional storage for prepared guest releases.

This is not an HTTP authorization or content-sanitization boundary. Callers must
authenticate the subject and prepare the complete, allowlisted release first.
"""
from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work


def _dsn() -> str:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    return dsn


def _owner(conn, world_id: str, subject: str) -> int:
    if not isinstance(subject, str) or not subject or subject != subject.strip():
        raise ApplicationStateNotFoundError("World unavailable")
    row = conn.execute(
        "SELECT owner_subject FROM workspace.managed_world "
        "WHERE world_id=%s FOR UPDATE", (world_id,)
    ).fetchone()
    if row is None or row[0] != subject:
        raise ApplicationStateNotFoundError("World unavailable")
    generation = conn.execute(
        "SELECT generation FROM workspace.guest_world_owner_generation WHERE world_id=%s",
        (world_id,),
    ).fetchone()
    return generation[0] if generation else 0


def _canonical(manifest: dict) -> tuple[bytes, str]:
    if not isinstance(manifest, dict):
        raise ApplicationStateValidationError("Invalid release manifest")
    try:
        data = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ApplicationStateValidationError("Invalid release manifest") from exc
    if len(data) > 10_000_000:
        raise ApplicationStateValidationError("Release manifest too large")
    return data, hashlib.sha256(data).hexdigest()


def _check_sources(conn, world_id: str, bindings: list[tuple], sources: list[dict], *, require_current_origin: bool = False) -> None:
    """Lock source eligibility until the caller's staging/promotion commits."""
    if len(bindings) > 500 or len({item[0] for item in bindings}) != len(bindings):
        raise ApplicationStateValidationError("Invalid release source bindings")
    source_text = {item["id"]: item.get("text") for item in sources}
    for excerpt_id, document_id, visibility_generation, status_generation, revision_n, digest, start, end, registry_revision, selected_visibility, native_evidence_id in sorted(bindings, key=lambda v: str(v[1])):
        row = conn.execute(
            "SELECT w.world_id,w.status,m.visibility_state,m.guest_visibility_generation,w.object_revision,w.current_revision_id "
            "FROM content.work_object w JOIN content.page_metadata m ON m.work_object_id=w.work_object_id "
            "WHERE w.work_object_id=%s FOR UPDATE OF w,m", (document_id,),
        ).fetchone()
        status = conn.execute(
            "SELECT generation FROM workspace.guest_source_status_generation WHERE work_object_id=%s",
            (document_id,),
        ).fetchone()
        if (selected_visibility not in {"internal", "player_safe"}
            or row is None or row[:4] != (world_id, "active", selected_visibility, visibility_generation)
            or (status[0] if status else 0) != status_generation):
            raise ApplicationStateConflictError("Release source eligibility changed")
        revision = conn.execute(
            "SELECT markdown,content_sha256,world_id,work_revision_id FROM content.work_revision "
            "WHERE work_object_id=%s AND revision_n=%s", (document_id, revision_n),
        ).fetchone()
        if (revision is None or revision[2] != world_id or revision[1] != digest
            or hashlib.sha256(revision[0].encode("utf-8")).hexdigest() != digest
            or type(start) is not int or type(end) is not int or start < 0 or end <= start
            or end > len(revision[0]) or revision[0][start:end] != source_text.get(str(excerpt_id))):
            raise ApplicationStateConflictError("Release source evidence differs")
        if require_current_origin and (row[4] != registry_revision or row[5] != revision[3]):
            raise ApplicationStateConflictError("Release source origin changed")


def owner_generation(*, world_id: str, subject: str) -> int:
    """Capture ownership before preparation; stage rechecks it afterwards."""
    with unit_of_work(_dsn()) as conn:
        return _owner(conn, world_id, subject)


def _check_graph_binding(conn, world_id: str, native_world_id: str, binding_version: int) -> None:
    row = conn.execute(
        "SELECT native_world_id,binding_version,status FROM workspace.world_native_binding "
        "WHERE world_id=%s FOR UPDATE", (world_id,),
    ).fetchone()
    if row != (native_world_id, binding_version, "active"):
        raise ApplicationStateConflictError("Native Graph binding changed")


def review(*, world_id: str, subject: str, release_id: UUID) -> tuple[dict, str]:
    """Read the exact staged manifest only while its owner binding is valid."""
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        row = conn.execute(
            "SELECT manifest,manifest_sha256 FROM workspace.guest_release "
            "WHERE release_id=%s AND world_id=%s AND owner_subject=%s "
            "AND owner_generation=%s AND state IN ('candidate','published')",
            (release_id, world_id, subject, generation),
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release unavailable")
        if _canonical(row[0])[1] != row[1]:
            raise ApplicationStateConflictError("Release manifest integrity failed")
        return row[0], row[1]


def list_candidates(*, world_id: str, subject: str) -> list[dict]:
    """List only this owner's current private candidates, newest first."""
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        rows = conn.execute(
            "SELECT release_id,created_at FROM workspace.guest_release "
            "WHERE world_id=%s AND owner_subject=%s AND owner_generation=%s AND state='candidate' "
            "ORDER BY created_at DESC,release_id DESC LIMIT 100", (world_id, subject, generation),
        ).fetchall()
        return [{"release_id": str(release_id), "created_at": created_at.isoformat()}
                for release_id, created_at in rows]


def list_published(*, world_id: str, subject: str) -> list[dict]:
    """List restorable copies plus the current copy the owner may revoke."""
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        rows = conn.execute(
            "SELECT r.release_id,r.published_at,(p.release_id=r.release_id) AS current,"
            "(r.owner_subject=%s AND r.owner_generation=%s) AS reviewable "
            "FROM workspace.guest_release r LEFT JOIN workspace.guest_release_pointer p ON p.world_id=r.world_id "
            "WHERE r.world_id=%s AND r.state='published' AND "
            "((r.owner_subject=%s AND r.owner_generation=%s) OR p.release_id=r.release_id) "
            "ORDER BY r.published_at DESC,r.release_id DESC LIMIT 100",
            (subject, generation, world_id, subject, generation),
        ).fetchall()
        return [{"release_id": str(release_id), "published_at": published_at.isoformat(),
                 "current": bool(current), "reviewable": bool(reviewable)}
                for release_id, published_at, current, reviewable in rows]


def review_source_visibility(*, world_id: str, subject: str, release_id: UUID) -> dict[str, str]:
    """Owner-only release-local labels for explicit private-copy review."""
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        candidate = conn.execute(
            "SELECT 1 FROM workspace.guest_release WHERE release_id=%s AND world_id=%s "
            "AND owner_subject=%s AND owner_generation=%s AND state IN ('candidate','published')",
            (release_id, world_id, subject, generation),
        ).fetchone()
        if candidate is None:
            raise ApplicationStateNotFoundError("Release unavailable")
        rows = conn.execute(
            "SELECT excerpt_id,selected_visibility FROM workspace.guest_release_source_binding WHERE release_id=%s",
            (release_id,),
        ).fetchall()
        return {str(excerpt_id): visibility for excerpt_id, visibility in rows}


def review_asset(*, world_id: str, subject: str, release_id: UUID,
                 asset_id: UUID) -> tuple[str, bytes]:
    """Show staged asset bytes to the candidate's currently authorized owner."""
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        row = conn.execute(
            "SELECT a.mime_type,a.content,a.content_sha256 "
            "FROM workspace.guest_release r JOIN workspace.guest_release_asset a "
            "ON a.release_id=r.release_id WHERE r.release_id=%s AND r.world_id=%s "
            "AND r.owner_subject=%s AND r.owner_generation=%s AND r.state IN ('candidate','published') AND a.asset_id=%s",
            (release_id, world_id, subject, generation, asset_id),
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release asset unavailable")
        content = bytes(row[1])
        if hashlib.sha256(content).hexdigest() != row[2]:
            raise ApplicationStateConflictError("Release asset integrity failed")
        return row[0], content


def validation_material(*, world_id: str, subject: str, release_id: UUID, digest: str) -> dict:
    """Load private candidate coordinates for fresh native proof validation.

    These values must remain server-side and are never a guest or model payload.
    Promotion repeats APP-owned checks atomically after native validation.
    """
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        row = conn.execute(
            "SELECT native_world_id,native_binding_version,graph_revision,manifest,manifest_sha256 "
            "FROM workspace.guest_release WHERE release_id=%s AND world_id=%s AND owner_subject=%s "
            "AND owner_generation=%s AND state='candidate'", (release_id, world_id, subject, generation),
        ).fetchone()
        if row is None or row[4] != digest or _canonical(row[3])[1] != digest:
            raise ApplicationStateNotFoundError("Release candidate unavailable")
        _check_graph_binding(conn, world_id, row[0], row[1])
        source_bindings = conn.execute(
            "SELECT excerpt_id,work_object_id,visibility_generation,status_generation,revision_n,content_sha256,span_start,span_end,registry_revision,selected_visibility,native_evidence_id "
            "FROM workspace.guest_release_source_binding WHERE release_id=%s", (release_id,),
        ).fetchall()
        _check_sources(conn, world_id, source_bindings, row[3].get("sources", []))
        node_bindings = conn.execute(
            "SELECT node_id,native_entity_id,name_assertion_id,name_evidence_id,name_excerpt_id,"
            "kind_assertion_id,kind_evidence_id,kind_excerpt_id "
            "FROM workspace.guest_release_node_binding WHERE release_id=%s", (release_id,),
        ).fetchall()
        evidence_bindings = conn.execute(
            "SELECT edge_id,native_assertion_id,native_evidence_id,excerpt_id "
            "FROM workspace.guest_release_evidence_binding WHERE release_id=%s", (release_id,),
        ).fetchall()
        return {"native_world_id": row[0], "binding_version": row[1], "graph_revision": row[2],
                "manifest": row[3], "source_bindings": source_bindings,
                "node_bindings": node_bindings, "evidence_bindings": evidence_bindings}


def pointer_status(*, world_id: str, subject: str) -> tuple[UUID | None, int]:
    """Read the current CAS basis without allocating a public identifier."""
    with unit_of_work(_dsn()) as conn:
        _owner(conn, world_id, subject)
        row = conn.execute(
            "SELECT public_id,version FROM workspace.guest_release_pointer WHERE world_id=%s",
            (world_id,),
        ).fetchone()
        return (None, 0) if row is None else (row[0], row[1])


def recover_publication(*, world_id: str, subject: str, release_id: UUID, digest: str,
                        expected_version: int, operation_id: UUID) -> tuple[UUID, int] | None:
    """Return an existing operation outcome without modifying release state."""
    with unit_of_work(_dsn()) as conn:
        _owner(conn, world_id, subject)
        row = conn.execute(
            "SELECT release_id,world_id,owner_subject,manifest_sha256,expected_pointer_version,public_id,result_pointer_version "
            "FROM workspace.guest_release_publication_receipt WHERE operation_id=%s", (operation_id,),
        ).fetchone()
        if row is None:
            return None
        if row[:5] != (release_id, world_id, subject, digest, expected_version):
            raise ApplicationStateConflictError("Publication operation differs")
        return row[5], row[6]


def stage(*, world_id: str, subject: str, expected_owner_generation: int,
          native_world_id: str, native_binding_version: int, graph_revision: str, manifest: dict,
          assets: list[tuple[UUID, str, bytes]], source_bindings: list[tuple] | None = None,
          evidence_bindings: list[tuple] | None = None, node_bindings: list[tuple] | None = None) -> tuple[UUID, str]:
    """Store a fully prepared candidate; never pass unvalidated client content."""
    _, digest = _canonical(manifest)
    if len(assets) > 100:
        raise ApplicationStateValidationError("Too many release assets")
    if (not isinstance(native_world_id, str) or not native_world_id.strip()
        or type(native_binding_version) is not int or native_binding_version < 1
        or not isinstance(graph_revision, str) or not graph_revision.strip()):
        raise ApplicationStateValidationError("Invalid native Graph binding")
    checked = []
    seen: set[UUID] = set()
    for asset_id, mime_type, content in assets:
        if (not isinstance(asset_id, UUID) or asset_id in seen
            or mime_type not in {"image/png", "image/jpeg", "image/webp"}
            or not isinstance(content, bytes) or not 0 < len(content) <= 10_000_000):
            raise ApplicationStateValidationError("Invalid release asset")
        seen.add(asset_id)
        checked.append((asset_id, mime_type, content, hashlib.sha256(content).hexdigest()))
    # Approval covers the exact copied bytes and media types, not merely the
    # textual projection. The preparer assigns release-local asset IDs.
    expected_assets = sorted(
        ({"id": str(asset_id), "mime_type": mime_type, "sha256": content_digest}
         for asset_id, mime_type, _, content_digest in checked),
        key=lambda item: item["id"],
    )
    if manifest.get("assets") != expected_assets:
        raise ApplicationStateValidationError("Manifest asset bindings do not match copied bytes")
    bindings = source_bindings or []
    sources = manifest.get("sources", [])
    if (not isinstance(sources, list) or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in sources)
        or {item.get("id") for item in sources} != {str(item[0]) for item in bindings}
        or len(sources) != len(bindings)):
        raise ApplicationStateValidationError("Manifest source bindings do not match excerpts")
    from application_state.guest_release_example import validate_example
    validate_example(manifest, bindings)
    graph = manifest.get("graph")
    evidence = evidence_bindings or []
    nodes = node_bindings or []
    expected_edges = {}
    expected_nodes = {}
    if graph is not None:
        if not isinstance(graph, dict) or not isinstance(graph.get("edges"), list) or not isinstance(graph.get("nodes"), list):
            raise ApplicationStateValidationError("Invalid release Graph")
        for node in graph["nodes"]:
            if (not isinstance(node, dict) or not isinstance(node.get("id"), str) or node["id"] in expected_nodes
                or not isinstance(node.get("name_citations"), list) or len(node["name_citations"]) != 1
                or not isinstance(node.get("kind_citations"), list) or len(node["kind_citations"]) != 1
                or not isinstance(node["name_citations"][0], str) or not isinstance(node["kind_citations"][0], str)
                or node["name_citations"][0] not in {item["id"] for item in sources}
                or node["kind_citations"][0] not in {item["id"] for item in sources}):
                raise ApplicationStateValidationError("Invalid release Graph node")
            expected_nodes[node["id"]] = (node["name_citations"][0], node["kind_citations"][0])
        source_ids = {item["id"] for item in sources}
        for edge in graph["edges"]:
            if (not isinstance(edge, dict) or not isinstance(edge.get("citations"), list)
                or not isinstance(edge.get("id"), str) or len(edge["citations"]) != 1
                or any(not isinstance(c, str) or c not in source_ids for c in edge["citations"])):
                raise ApplicationStateValidationError("Release Graph citation is not closed")
            if edge["id"] in expected_edges:
                raise ApplicationStateValidationError("Duplicate release Graph edge")
            expected_edges[edge["id"]] = edge["citations"][0]
    if (len(nodes) != len(expected_nodes)
        or any(len(item) != 8 or not isinstance(item[0], UUID) or str(item[0]) not in expected_nodes
               or any(not isinstance(item[i], str) or not item[i] for i in (1, 2, 3, 5, 6))
               or expected_nodes[str(item[0])] != (str(item[4]), str(item[7])) for item in nodes)
        or len({item[0] for item in nodes}) != len(nodes)
        or len({item[1] for item in nodes}) != len(nodes)):
        raise ApplicationStateValidationError("Release Graph node bindings are incomplete")
    if (len(evidence) != len(expected_edges)
        or any(len(item) != 4 or not isinstance(item[0], UUID) or not isinstance(item[1], str)
               or not item[1] or not isinstance(item[2], str) or not item[2]
               or expected_edges.get(str(item[0])) != str(item[3]) for item in evidence)
        or len({item[0] for item in evidence}) != len(evidence)):
        raise ApplicationStateValidationError("Release Graph evidence bindings are incomplete")
    release_id = uuid4()
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        if type(expected_owner_generation) is not int or generation != expected_owner_generation:
            raise ApplicationStateConflictError("World ownership changed during preparation")
        _check_graph_binding(conn, world_id, native_world_id, native_binding_version)
        _check_sources(conn, world_id, bindings, sources, require_current_origin=True)
        conn.execute(
            "INSERT INTO workspace.guest_release "
            "(release_id,world_id,owner_subject,owner_generation,native_world_id,native_binding_version,graph_revision,manifest_sha256,manifest) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (release_id, world_id, subject, generation, native_world_id, native_binding_version, graph_revision, digest, Jsonb(manifest)),
        )
        for asset_id, mime_type, content, content_digest in checked:
            conn.execute(
                "INSERT INTO workspace.guest_release_asset "
                "(release_id,asset_id,mime_type,content_sha256,content) VALUES (%s,%s,%s,%s,%s)",
                (release_id, asset_id, mime_type, content_digest, content),
            )
        for excerpt_id, document_id, visibility_generation, status_generation, revision_n, content_sha256, start, end, registry_revision, selected_visibility, native_evidence_id in bindings:
            conn.execute(
                "INSERT INTO workspace.guest_release_source_binding "
                "(release_id,excerpt_id,work_object_id,visibility_generation,status_generation,revision_n,content_sha256,span_start,span_end,registry_revision,selected_visibility,native_evidence_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (release_id, excerpt_id, document_id, visibility_generation, status_generation, revision_n, content_sha256, start, end, registry_revision, selected_visibility, native_evidence_id),
            )
        for node_id, native_entity_id, name_assertion, name_evidence, name_excerpt, kind_assertion, kind_evidence, kind_excerpt in nodes:
            conn.execute(
                "INSERT INTO workspace.guest_release_node_binding "
                "(release_id,node_id,native_entity_id,name_assertion_id,name_evidence_id,name_excerpt_id,"
                "kind_assertion_id,kind_evidence_id,kind_excerpt_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (release_id, node_id, native_entity_id, name_assertion, name_evidence, UUID(str(name_excerpt)),
                 kind_assertion, kind_evidence, UUID(str(kind_excerpt))),
            )
        for edge_id, assertion_id, evidence_id, excerpt_id in evidence:
            conn.execute(
                "INSERT INTO workspace.guest_release_evidence_binding "
                "(release_id,edge_id,native_assertion_id,native_evidence_id,excerpt_id) VALUES (%s,%s,%s,%s,%s)",
                (release_id, edge_id, assertion_id, evidence_id, UUID(str(excerpt_id))),
            )
    return release_id, digest


def commit_validated_promotion(*, world_id: str, subject: str, release_id: UUID,
            digest: str, expected_version: int, operation_id: UUID, source_epoch: int) -> tuple[UUID, int]:
    """Internal storage operation; caller must freshly validate Core first.

    Never expose this function directly to an HTTP request. The epoch is
    produced by server-owned validation, not accepted from a client.
    """
    if (type(expected_version) is not int or expected_version < 0
        or not isinstance(operation_id, UUID) or type(source_epoch) is not int or source_epoch < 0):
        raise ApplicationStateValidationError("Invalid pointer version")
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        previous = conn.execute(
            "SELECT release_id,world_id,owner_subject,manifest_sha256,expected_pointer_version,public_id,result_pointer_version "
            "FROM workspace.guest_release_publication_receipt WHERE operation_id=%s", (operation_id,),
        ).fetchone()
        if previous is not None:
            if previous[:5] != (release_id, world_id, subject, digest, expected_version):
                raise ApplicationStateConflictError("Publication operation differs")
            # Recovery reports the historical outcome only; it never moves a
            # pointer or reactivates a subsequently revoked release.
            return previous[5], previous[6]
        row = conn.execute(
            "SELECT owner_subject,owner_generation,manifest_sha256,state,native_world_id,native_binding_version,manifest,graph_revision "
            "FROM workspace.guest_release WHERE release_id=%s AND world_id=%s FOR UPDATE",
            (release_id, world_id),
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release unavailable")
        if row[:4] != (subject, generation, digest, "candidate"):
            raise ApplicationStateConflictError("Release candidate changed or is unavailable")
        if _canonical(row[6])[1] != digest:
            raise ApplicationStateConflictError("Release manifest integrity failed")
        _check_graph_binding(conn, world_id, row[4], row[5])
        bindings = conn.execute(
            "SELECT excerpt_id,work_object_id,visibility_generation,status_generation,revision_n,content_sha256,span_start,span_end,registry_revision,selected_visibility,native_evidence_id "
            "FROM workspace.guest_release_source_binding WHERE release_id=%s", (release_id,),
        ).fetchall()
        _check_sources(conn, world_id, bindings, row[6].get("sources", []))
        conn.execute(
            "INSERT INTO workspace.guest_release_pointer (world_id,public_id) VALUES (%s,%s) "
            "ON CONFLICT (world_id) DO NOTHING", (world_id, uuid4())
        )
        pointer = conn.execute(
            "UPDATE workspace.guest_release_pointer SET release_id=%s,version=version+1 "
            "WHERE world_id=%s AND version=%s RETURNING public_id,version",
            (release_id, world_id, expected_version),
        ).fetchone()
        if pointer is None:
            raise ApplicationStateConflictError("Release pointer changed")
        conn.execute(
            "UPDATE workspace.guest_release SET state='published',published_at=clock_timestamp() "
            "WHERE release_id=%s", (release_id,)
        )
        conn.execute(
            "INSERT INTO workspace.guest_release_publication_receipt "
            "(operation_id,release_id,world_id,owner_subject,manifest_sha256,native_world_id,graph_revision,source_epoch,expected_pointer_version,public_id,result_pointer_version) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (operation_id, release_id, world_id, subject, digest, row[4], row[7], source_epoch,
             expected_version, pointer[0], pointer[1]),
        )
        return pointer[0], pointer[1]


def revoke(*, world_id: str, subject: str, release_id: UUID) -> None:
    """Permanently revoke a published release and unpublish its pointer if current."""
    with unit_of_work(_dsn()) as conn:
        _owner(conn, world_id, subject)
        row = conn.execute(
            "UPDATE workspace.guest_release SET state='revoked',revoked_at=clock_timestamp() "
            "WHERE release_id=%s AND world_id=%s AND state='published' RETURNING release_id",
            (release_id, world_id),
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release unavailable")
        conn.execute(
            "UPDATE workspace.guest_release_pointer SET release_id=NULL,version=version+1 "
            "WHERE world_id=%s AND release_id=%s", (world_id, release_id)
        )


def restore(*, world_id: str, subject: str, release_id: UUID,
            expected_version: int) -> tuple[UUID, int]:
    """Point back to an unrevoked release approved under the current ownership."""
    if type(expected_version) is not int or expected_version < 0:
        raise ApplicationStateValidationError("Invalid pointer version")
    with unit_of_work(_dsn()) as conn:
        generation = _owner(conn, world_id, subject)
        row = conn.execute(
            "SELECT 1 FROM workspace.guest_release WHERE release_id=%s AND world_id=%s "
            "AND owner_subject=%s AND owner_generation=%s AND state='published' FOR UPDATE",
            (release_id, world_id, subject, generation),
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release unavailable")
        pointer = conn.execute(
            "UPDATE workspace.guest_release_pointer SET release_id=%s,version=version+1 "
            "WHERE world_id=%s AND version=%s RETURNING public_id,version",
            (release_id, world_id, expected_version),
        ).fetchone()
        if pointer is None:
            raise ApplicationStateConflictError("Release pointer changed")
        return pointer[0], pointer[1]


def public_manifest(public_id: UUID) -> tuple[UUID, dict]:
    """Read only a currently pointed-to, published release copy."""
    with unit_of_work(_dsn()) as conn:
        row = conn.execute(
            "SELECT r.release_id,r.manifest,r.manifest_sha256 FROM workspace.guest_release_pointer p "
            "JOIN workspace.guest_release r ON r.release_id=p.release_id AND r.world_id=p.world_id "
            "WHERE p.public_id=%s AND r.state='published'", (public_id,)
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release unavailable")
        if _canonical(row[1])[1] != row[2]:
            raise ApplicationStateConflictError("Release manifest integrity failed")
        return row[0], row[1]


def public_asset(public_id: UUID, release_id: UUID, asset_id: UUID) -> tuple[str, bytes]:
    """Read only an asset copied into the currently published release."""
    with unit_of_work(_dsn()) as conn:
        row = conn.execute(
            "SELECT a.mime_type,a.content,a.content_sha256 "
            "FROM workspace.guest_release_pointer p "
            "JOIN workspace.guest_release r ON r.release_id=p.release_id AND r.world_id=p.world_id "
            "JOIN workspace.guest_release_asset a ON a.release_id=r.release_id "
            "WHERE p.public_id=%s AND r.release_id=%s AND r.state='published' AND a.asset_id=%s",
            (public_id, release_id, asset_id),
        ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Release asset unavailable")
        content = bytes(row[1])
        if hashlib.sha256(content).hexdigest() != row[2]:
            raise ApplicationStateConflictError("Release asset integrity failed")
        return row[0], content
