"""Authenticated read/write projection of the selected managed native World.

Core remains the graph and receipt authority. APP-STATE stores only a bounded
principal/World-scoped operation journal, while WorldKeeper prepares and commits
the supported typed create/connect intents.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import re
import unicodedata
from typing import Any, Iterator

from dungeonmind.application.vnext import (
    open_admitted_native_text,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.common import LabelsAnyVisibility
from dungeonmind.contracts.vnext.native_source import (
    NativeTextEvidenceSpanRequestV1,
    NativeTextSourceAdmissionV1,
    NativeTextSourceOriginV1,
)
from dungeonmind.domain.errors import (
    PersistenceIntegrityError,
    PersistenceUnavailableError,
    StaleParentRevisionError,
)
from worldkeeper.application import contracts as wk
from worldkeeper.application.commit import (
    CommitAuthorityIntegrityFailure,
    CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationIntegrityFailure,
    CommittedChangeVerificationUnavailable,
    PreparedChangeConflict,
    PreparedChangeIntegrityFailure,
    PreparedChangeStale,
)
from worldkeeper.application.preparation import InvalidWorldChange

from application_state.errors import ApplicationStateError
from application_state.native_graph_explorer import (
    NativeGraphExplorerStore,
    NativeGraphExplorerStoreUnavailable,
    canonical_json,
    sha256_text,
)
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from apps.live_control_server.models.native_graph_explorer import (
    NativeGraphExplorerOperationRequest,
    NativeGraphExplorerPrepareRequest,
    NativeGraphExplorerGraphRequest,
    canonical_operation_id,
)
from apps.live_control_server.models.native_graph_inspection import (
    InspectionPin,
    InspectionScope,
)
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    require_native_graph_gm,
)
from apps.live_control_server.services import native_graph_inspection
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from graph_memory.vnext.domain_runtime import GM_LABEL


PRODUCER = "dungeonbuddy:native-graph-explorer-v1"
SOURCE_NAMESPACE = "dungeonbuddy.native_graph_explorer"
SOURCE_CLASSIFICATION = "dungeonbuddy.source:worldbuilding"
MAX_NAME_BYTES = 128
MAX_LABEL_BYTES = 128
MAX_GRAPH_RESPONSE_BYTES = 8 * 1024 * 1024
_CUSTOM_LABEL = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class NativeGraphExplorerError(Exception):
    """Safe user-facing failure without provider/database exception details."""

    def __init__(self, code: str, message: str, status: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def _now() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return _now().isoformat()


def _parse_operation_id(value: str) -> str:
    try:
        return canonical_operation_id(value)
    except (ValueError, TypeError, AttributeError):
        raise NativeGraphExplorerError(
            "invalid_operation_id", "operation_id must be a canonical UUID.", 422
        ) from None


def _require_gm(principal: NativeGraphPrincipal) -> NativeGraphPrincipal:
    try:
        return require_native_graph_gm(principal)
    except Exception:
        raise NativeGraphExplorerError(
            "graph_gm_required",
            "GM authority is required for native Graph access.",
            403,
        ) from None


def _resolve_binding(managed_world_id: str) -> dict[str, Any]:
    try:
        bound = native.binding(managed_world_id)
    except WorldGraphProjectionServiceError as exc:
        raise NativeGraphExplorerError(
            getattr(exc, "code", "managed_world_unavailable"),
            "The selected managed World has no usable native Graph binding.",
            getattr(exc, "status_code", 409),
        ) from None
    except Exception:
        raise NativeGraphExplorerError(
            "managed_world_unavailable",
            "The selected managed World could not be verified.",
            503,
        ) from None
    if (
        bound.get("managed_world_id") != managed_world_id
        or not isinstance(bound.get("native_world_id"), str)
        or not bound.get("native_world_id")
        or type(bound.get("binding_version")) is not int
        or bound["binding_version"] < 1
    ):
        raise NativeGraphExplorerError(
            "managed_world_binding_invalid",
            "The selected managed World binding could not be verified.",
            503,
        )
    return bound


def _assert_binding(expected: dict[str, Any]) -> None:
    current = _resolve_binding(expected["managed_world_id"])
    if current != expected:
        raise NativeGraphExplorerError(
            "binding_changed",
            "The selected World binding changed. Refresh the selection before continuing.",
            409,
        )


@contextmanager
def _open_store(
    principal: NativeGraphPrincipal, managed_world_id: str
) -> Iterator[NativeGraphExplorerStore]:
    store: NativeGraphExplorerStore | None = None
    try:
        store = NativeGraphExplorerStore(principal.subject, managed_world_id)
        yield store
    except NativeGraphExplorerStoreUnavailable:
        raise NativeGraphExplorerError(
            "application_state_unavailable",
            "Buddy application state is unavailable. The operation outcome could not be verified; keep the same operation ID and check its status before retrying.",
            503,
        ) from None
    except ApplicationStateError:
        raise NativeGraphExplorerError(
            "application_state_unavailable",
            "Buddy application state is unavailable. The operation outcome could not be verified; keep the same operation ID and check its status before retrying.",
            503,
        ) from None
    finally:
        if store is not None:
            store.close()


def _profile_capabilities(profile: Any) -> dict[str, Any]:
    predicates = {
        item.term: set(item.allowed_value_kinds)
        for item in getattr(profile, "predicates", ())
    }
    classifications = set(getattr(profile, "classification_terms", ()))
    name_supported = "literal" in predicates.get("dnd5e:name", set())
    classification_supported = "term_ref" in predicates.get(
        "dnd5e:classification", set()
    )
    object_kinds = []
    if name_supported and classification_supported and "dnd5e:npc" in classifications:
        object_kinds.append("person")
    if (
        name_supported
        and classification_supported
        and "dnd5e:location" in classifications
    ):
        object_kinds.append("location")
    custom_relationships = any(
        item.namespace == "dungeonbuddy.custom"
        and "entity_ref" in item.allowed_value_kinds
        for item in getattr(profile, "open_predicate_namespaces", ())
    )
    predicate_labels = [
        predicate.split(":", 1)[1]
        for predicate, value_kinds in predicates.items()
        if "entity_ref" in value_kinds and ":" in predicate
    ]
    label_counts = Counter(predicate_labels)
    allowed_predicates = sorted(
        label for label, count in label_counts.items() if count == 1
    )
    return {
        "create": bool(object_kinds),
        "connect": bool(allowed_predicates or custom_relationships),
        "rename": False,
        "delete": False,
        "object_kinds": object_kinds,
        "allowed_predicates": allowed_predicates,
        "allows_custom_predicates": bool(custom_relationships),
    }


def _native_predicate(label: str, profile: Any) -> str:
    matches = [
        predicate.term
        for predicate in getattr(profile, "predicates", ())
        if "entity_ref" in set(getattr(predicate, "allowed_value_kinds", ()))
        and predicate.term.split(":", 1)[-1] == label
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise NativeGraphExplorerError(
            "ambiguous_predicate",
            "The selected World descriptor has multiple predicates with that label. Choose an unambiguous registered label.",
            409,
        )
    allows_custom = any(
        item.namespace == "dungeonbuddy.custom"
        and "entity_ref" in item.allowed_value_kinds
        for item in getattr(profile, "open_predicate_namespaces", ())
    )
    if allows_custom:
        return f"dungeonbuddy.custom:{label}"
    raise NativeGraphExplorerError(
        "unsupported_predicate",
        "The selected World descriptor does not permit that relationship label.",
        409,
    )


def _node_kind(terms: set[str]) -> str:
    if terms == {"dnd5e:npc"}:
        return "person"
    if terms == {"dnd5e:location"}:
        return "location"
    return "object"


def _safe_graph_from_catalogue(
    bound: dict[str, Any], catalogue: dict[str, Any], profile: Any
) -> dict[str, Any]:
    try:
        scope = catalogue["scope"]
        listing = catalogue["catalogue"]
        assertions = catalogue["assertions"]
        revision_id = scope["revision_id"]
        native_world_id = scope["native_world_id"]
        digest = listing["identity"]["graph_payload_sha256"]
        listed_entities = listing["entities"]
        complete = listing["completeness"]["status"] == "complete"
        if (
            scope["managed_world_id"] != bound["managed_world_id"]
            or native_world_id != bound["native_world_id"]
            or scope["binding_version"] != bound["binding_version"]
            or listing["identity"]["space_id"] != native_world_id
            or listing["identity"]["revision_id"] != revision_id
        ):
            raise ValueError("catalogue identity changed")
    except (KeyError, TypeError, ValueError):
        raise NativeGraphExplorerError(
            "native_graph_integrity_failure",
            "The native Graph catalogue could not be verified at its pinned revision.",
            503,
        ) from None

    try:
        name_values: dict[str, dict[str, set[str]]] = {}
        class_terms: dict[str, dict[str, set[str]]] = {}
        edge_rows: list[dict[str, str]] = []
        all_assertion_ids: set[str] = set()
        represented_assertion_ids: set[str] = set()
        entity_ids = {row["entity_id"] for row in listed_entities}
        for row in assertions:
            assertion_id = row["assertion_id"]
            subject = row["subject_entity_id"]
            predicate = row["predicate"]
            value = row["value"]
            if not isinstance(assertion_id, str) or not isinstance(subject, str):
                raise ValueError("invalid admitted assertion")
            all_assertion_ids.add(assertion_id)
            if predicate == "dnd5e:name" and value.get("kind") == "literal":
                literal = value.get("value")
                if isinstance(literal, str):
                    name_values.setdefault(subject, {}).setdefault(
                        assertion_id, set()
                    ).add(literal)
            elif (
                predicate == "dnd5e:classification" and value.get("kind") == "term_ref"
            ):
                term = value.get("term")
                if isinstance(term, str):
                    class_terms.setdefault(subject, {}).setdefault(
                        assertion_id, set()
                    ).add(term)
            elif value.get("kind") == "entity_ref":
                target = value.get("entity_id")
                if (
                    subject in entity_ids
                    and target in entity_ids
                    and isinstance(predicate, str)
                ):
                    label = predicate.removeprefix("dungeonbuddy.custom:")
                    if ":" in label:
                        label = label.rsplit(":", 1)[1]
                    edge_rows.append(
                        {
                            "id": assertion_id,
                            "source_id": subject,
                            "target_id": target,
                            "predicate": label,
                        }
                    )
                    represented_assertion_ids.add(assertion_id)

        nodes: list[dict[str, Any]] = []
        reason_codes: set[str] = set()
        limitations: set[str] = {
            "Native rename and deletion are unavailable in the current WorldKeeper operation contract."
        }
        capabilities = _profile_capabilities(profile)
        if "event" not in capabilities["object_kinds"]:
            limitations.add(
                "Event creation is unavailable because the selected native descriptor does not declare an event classification."
            )
        for entity_id in sorted(entity_ids):
            entity_names = {
                value
                for values in name_values.get(entity_id, {}).values()
                for value in values
            }
            entity_terms = {
                value
                for values in class_terms.get(entity_id, {}).values()
                for value in values
            }
            if len(entity_names) == 1:
                name = next(iter(entity_names))
                represented_assertion_ids.update(name_values.get(entity_id, {}).keys())
            elif not entity_names:
                name = f"Unnamed object · {entity_id[-8:]}"
                reason_codes.add("entity_name_missing")
            else:
                name = f"Multiple recorded names · {entity_id[-8:]}"
                reason_codes.add("entity_name_conflict")
            if len(entity_terms) == 1:
                represented_assertion_ids.update(class_terms.get(entity_id, {}).keys())
            elif len(entity_terms) > 1:
                reason_codes.add("entity_classification_ambiguous")
            nodes.append(
                {
                    "id": entity_id,
                    "name": name,
                    "kind": _node_kind(entity_terms),
                }
            )
        omitted_assertions = max(0, len(all_assertion_ids - represented_assertion_ids))
        if omitted_assertions:
            reason_codes.add("non_graph_assertions")
            limitations.add(
                "Some admitted native assertions are not displayed by the current node-and-edge canvas."
            )
        if "entity_name_missing" in reason_codes:
            limitations.add(
                "Some native objects have no admitted name assertion; stable identity remains visible."
            )
        if "entity_name_conflict" in reason_codes:
            limitations.add(
                "Some native objects have multiple admitted names; the canvas does not choose one as authoritative."
            )
        if "entity_classification_ambiguous" in reason_codes:
            limitations.add(
                "Some native objects have multiple admitted classifications; they are shown as generic objects."
            )
        projection_complete = complete and not omitted_assertions and not reason_codes
        graph = {
            "world_id": native_world_id,
            "revision_id": revision_id,
            "graph_sha256": digest,
            "nodes": sorted(
                nodes, key=lambda item: (item["name"].casefold(), item["id"])
            ),
            "edges": sorted(edge_rows, key=lambda item: item["id"]),
            "storage": "postgres",
            "capabilities": capabilities,
            "limitations": sorted(limitations),
            "completeness": {
                "status": "complete" if projection_complete else "partial",
                "listed_entities": len(nodes),
                "omitted_entities": 0,
                "unexamined_entities": 0,
                "listed_assertions": len(represented_assertion_ids),
                "omitted_assertions": omitted_assertions,
                "unexamined_assertions": 0 if complete else len(all_assertion_ids),
                "reasons": sorted(
                    reason_codes | (set() if complete else {"core_listing_incomplete"})
                ),
            },
        }
        body_size = len(canonical_json(graph).encode("utf-8"))
        if body_size > MAX_GRAPH_RESPONSE_BYTES:
            raise NativeGraphExplorerError(
                "native_graph_response_limit",
                "The selected World graph is too large for one safe explorer response.",
                413,
            )
        return graph
    except NativeGraphExplorerError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError):
        raise NativeGraphExplorerError(
            "native_graph_integrity_failure",
            "The native Graph catalogue could not be safely projected.",
            503,
        ) from None


def _graph_envelope(
    bound: dict[str, Any],
    principal: NativeGraphPrincipal,
    *,
    revision_id: str | None = None,
) -> dict[str, Any]:
    try:
        scope = (
            InspectionScope(managed_world_id=bound["managed_world_id"])
            if revision_id is None
            else InspectionPin(
                managed_world_id=bound["managed_world_id"],
                native_world_id=bound["native_world_id"],
                binding_version=bound["binding_version"],
                revision_id=revision_id,
            )
        )
        catalogue = native_graph_inspection.catalog(scope, principal)
        repo = native.read_repository()
        graph = _safe_graph_from_catalogue(
            bound,
            catalogue,
            native.descriptors(
                repo, bound["native_world_id"], catalogue["scope"]["revision_id"]
            )[1],
        )
    except NativeGraphExplorerError:
        raise
    except Exception:
        raise NativeGraphExplorerError(
            "native_graph_unavailable",
            "The selected native World graph is unavailable or its readback could not be verified.",
            503,
        ) from None
    _assert_binding(bound)
    return {
        "schema": "dmb_native_graph_explorer_v1",
        "managed_world_id": bound["managed_world_id"],
        "native_world_id": bound["native_world_id"],
        "binding_version": bound["binding_version"],
        "graph": graph,
    }


def graph(
    request: NativeGraphExplorerGraphRequest, principal: NativeGraphPrincipal
) -> dict[str, Any]:
    _require_gm(principal)
    bound = _resolve_binding(request.managed_world_id)
    return _graph_envelope(bound, principal)


def _normalize_request(
    request: NativeGraphExplorerPrepareRequest,
) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    payload["operation_id"] = _parse_operation_id(payload["operation_id"])
    if payload["kind"] == "create_object":
        name = payload["name"].strip()
        try:
            encoded = name.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise NativeGraphExplorerError(
                "invalid_name", "Object name must be valid UTF-8.", 422
            ) from None
        if (
            not name
            or len(encoded) > MAX_NAME_BYTES
            or any(unicodedata.category(character) == "Cc" for character in name)
        ):
            raise NativeGraphExplorerError(
                "invalid_name",
                f"Object names must contain 1–{MAX_NAME_BYTES} UTF-8 bytes and no control characters.",
                422,
            )
        payload["name"] = name
    else:
        predicate = payload["predicate"].strip()
        if len(
            predicate.encode("utf-8")
        ) > MAX_LABEL_BYTES or not _CUSTOM_LABEL.fullmatch(predicate):
            raise NativeGraphExplorerError(
                "invalid_predicate",
                "Relationship labels may use lowercase letters, numbers, dots, underscores, and hyphens.",
                422,
            )
        payload["predicate"] = predicate
    return payload


def _validate_write_capability(
    payload: dict[str, Any], graph_value: dict[str, Any]
) -> None:
    capabilities = graph_value["graph"]["capabilities"]
    if payload["kind"] == "create_object":
        if (
            not capabilities["create"]
            or payload["object_kind"] not in capabilities["object_kinds"]
        ):
            raise NativeGraphExplorerError(
                "write_capability_unavailable",
                "The selected World descriptor does not support creating that typed object.",
                409,
            )
    elif not capabilities["connect"]:
        raise NativeGraphExplorerError(
            "write_capability_unavailable",
            "The selected World descriptor does not support graph relationships.",
            409,
        )
    elif (
        not capabilities["allows_custom_predicates"]
        and payload["predicate"] not in capabilities["allowed_predicates"]
    ):
        raise NativeGraphExplorerError(
            "unsupported_predicate",
            "Choose a relationship label registered by the selected World descriptor.",
            409,
        )
    elif payload["source_id"] not in {
        node["id"] for node in graph_value["graph"]["nodes"]
    } or payload["target_id"] not in {
        node["id"] for node in graph_value["graph"]["nodes"]
    }:
        raise NativeGraphExplorerError(
            "unknown_endpoint",
            "Choose both relationship endpoints from the selected World graph.",
            409,
        )


def _summary(payload: dict[str, Any]) -> str:
    if payload["kind"] == "create_object":
        return f"Create {payload['object_kind']} “{payload['name']}” in the selected World."
    return (
        f"Connect native object {payload['source_id']} to {payload['target_id']} "
        f"with “{payload['predicate']}” in the selected World."
    )


def _existing_edge(payload: dict[str, Any], graph_value: dict[str, Any]) -> bool:
    return any(
        edge["source_id"] == payload["source_id"]
        and edge["target_id"] == payload["target_id"]
        and edge["predicate"] == payload["predicate"]
        for edge in graph_value["graph"]["edges"]
    )


def _scoped_native_operation_id(
    operation_id: str, principal_subject: str, bound: dict[str, Any]
) -> str:
    scope = canonical_json(
        {
            "principal_subject": principal_subject,
            "managed_world_id": bound["managed_world_id"],
            "native_world_id": bound["native_world_id"],
            "binding_version": bound["binding_version"],
            "operation_id": operation_id,
        }
    )
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()


def _source_admission_id(
    operation_id: str, principal_subject: str, bound: dict[str, Any]
) -> str:
    return f"dmb-native-graph-explorer-source:v1:{_scoped_native_operation_id(operation_id, principal_subject, bound)}"


def _publication_id(
    operation_id: str, principal_subject: str, bound: dict[str, Any]
) -> str:
    return f"dmb-native-graph-explorer:v1:{_scoped_native_operation_id(operation_id, principal_subject, bound)}"


def _source_body(payload: dict[str, Any]) -> str:
    if payload["kind"] == "create_object":
        return (
            f"Authored World graph object: {payload['name']} "
            f"(classification: {payload['object_kind']}).\n"
        )
    return (
        f"Authored World graph relationship between native objects {payload['source_id']} "
        f"and {payload['target_id']} using predicate {payload['predicate']}.\n"
    )


def _receipt_payload(receipt: Any, body_digest: str) -> dict[str, Any]:
    return {
        "space_id": receipt.space_id,
        "admission_id": receipt.admission_id,
        "expected_parent_revision_id": receipt.publication_receipt.expected_parent_revision_id,
        "published_revision_id": receipt.published_revision_id,
        "source_artifact_id": receipt.source_artifact_id,
        "source_revision_id": receipt.source_revision_id,
        "evidence_ref_id": receipt.bindings[0].evidence_ref_id
        if len(receipt.bindings) == 1
        else None,
        "body_sha256": body_digest,
    }


def _source_matches(
    repo: Any,
    bound: dict[str, Any],
    payload: dict[str, Any],
    principal_subject: str,
    access: Any,
    receipt: Any,
) -> dict[str, Any]:
    body = _source_body(payload)
    encoded = body.encode("utf-8")
    body_digest = hashlib.sha256(encoded).hexdigest()
    expected_origin = NativeTextSourceOriginV1(
        namespace=SOURCE_NAMESPACE,
        object_id=payload["operation_id"],
        revision_id=payload["expected_revision_id"],
    )
    if (
        receipt is None
        or receipt.space_id != bound["native_world_id"]
        or receipt.admission_id
        != _source_admission_id(payload["operation_id"], principal_subject, bound)
        or receipt.status != "published"
        or receipt.origin != expected_origin
        or receipt.publication_receipt.expected_parent_revision_id
        != payload["expected_revision_id"]
        or repo.get_publication_receipt(bound["native_world_id"], receipt.admission_id)
        != receipt.publication_receipt
        or len(receipt.bindings) != 1
        or receipt.bindings[0].client_ref != payload["operation_id"]
    ):
        raise NativeGraphExplorerError(
            "native_source_receipt_invalid",
            "The exact authored source receipt for this review could not be verified.",
            503,
        )
    opened = open_admitted_native_text(access, receipt.bindings[0].evidence_ref_id)
    if (
        opened.status != "available"
        or opened.body_sha256 != body_digest
        or opened.body_text != body
        or opened.source_artifact_id != receipt.source_artifact_id
        or opened.source_revision_id != receipt.source_revision_id
        or opened.span_start_byte != 0
        or opened.span_end_byte != len(encoded)
        or opened.span_sha256 != body_digest
    ):
        raise NativeGraphExplorerError(
            "native_source_readback_invalid",
            "The authored source for this review could not be read back exactly.",
            503,
        )
    return _receipt_payload(receipt, body_digest)


def _intent(
    payload: dict[str, Any], evidence_ref_id: str, native_world_id: str, profile: Any
) -> wk.WorldChangeIntent:
    metadata = wk.AssertionMetadata(
        scope=(),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(evidence_ref_id,),
    )
    if payload["kind"] == "create_object":
        classification = (
            "dnd5e:npc" if payload["object_kind"] == "person" else "dnd5e:location"
        )
        operations = (
            wk.CreateObject(
                "new-object",
                (
                    wk.CreateFact(
                        "new-object-name",
                        "dnd5e:name",
                        wk.LiteralFactValue.from_json(payload["name"]),
                        metadata,
                    ),
                    wk.CreateFact(
                        "new-object-classification",
                        "dnd5e:classification",
                        wk.TermRefFactValue(classification),
                        metadata,
                    ),
                ),
            ),
        )
    else:
        operations = (
            wk.CreateRelationship(
                "new-relationship",
                wk.DurableObjectRef(payload["source_id"]),
                _native_predicate(payload["predicate"], profile),
                wk.DurableObjectRef(payload["target_id"]),
                metadata,
            ),
        )
    return wk.WorldChangeIntent(
        space_id=native_world_id,
        producer=PRODUCER,
        operations=operations,
    )


def _prepared_json(prepared: Any) -> str:
    return transport.canonical(transport.encode_prepared(prepared)).decode("utf-8")


def _decode_prepared(record: dict[str, Any], bound: dict[str, Any]) -> Any:
    try:
        prepared = transport.decode_prepared(record["prepared"])
        payload = record["request"]
        expected_id = _publication_id(
            record["operation_id"], record["principal_subject"], bound
        )
        if (
            prepared.space_id != bound["native_world_id"]
            or prepared.producer != PRODUCER
            or prepared.prepared_change_id != expected_id
            or prepared.dungeonmind_publication_id != expected_id
            or prepared.expected_parent_revision_id != record["parent_revision_id"]
            or record["native_world_id"] != bound["native_world_id"]
            or record["binding_version"] != bound["binding_version"]
            or payload["managed_world_id"] != bound["managed_world_id"]
        ):
            raise ValueError("stored preparation identity changed")
        receipt = record["source_receipt"]
        if not isinstance(receipt, dict) or not receipt.get("evidence_ref_id"):
            raise ValueError("stored source receipt is incomplete")
        read_repo = native.read_repository()
        domain, profile = native.descriptors(
            read_repo, bound["native_world_id"], prepared.expected_parent_revision_id
        )
        expected_intent = _intent(
            payload, receipt["evidence_ref_id"], bound["native_world_id"], profile
        )
        if prepared.prepared_operations != expected_intent.operations:
            raise ValueError("prepared operations differ from exact submitted intent")
        return prepared
    except NativeGraphExplorerError:
        raise
    except Exception:
        raise NativeGraphExplorerError(
            "prepared_operation_integrity_failure",
            "The saved native review failed verification. No new publication was attempted.",
            503,
        ) from None


def _publication_state(
    repo: Any, bound: dict[str, Any], prepared: Any
) -> tuple[str, Any | None]:
    try:
        publication_id = prepared.dungeonmind_publication_id
        aggregate = repo.get_prospective_publication(
            bound["native_world_id"], publication_id
        )
        receipt = repo.get_publication_receipt(bound["native_world_id"], publication_id)
    except Exception:
        return "uncertain", None
    if aggregate is None and receipt is None:
        return "absent", None
    result = None if aggregate is None else aggregate.prospective_result
    if (
        aggregate is None
        or receipt is None
        or aggregate.publication_receipt != receipt
        or receipt.space_id != bound["native_world_id"]
        or receipt.publication_id != publication_id
        or result.publication_id != publication_id
        or receipt.expected_parent_revision_id != prepared.expected_parent_revision_id
        or receipt.published_revision_id != result.published_revision_id
    ):
        return "uncertain", None
    return "committed", aggregate


def _prepared_parent_context(access: Any, native_world_id: str) -> dict[str, Any]:
    parsed = access.parsed
    return {
        "space_id": native_world_id,
        "revision_id": parsed.revision_id,
        "graph_sha256": parsed.graph_payload_sha256,
        "source_epoch": access.source_view.epoch,
        "domain_ref": {
            "authority_id": parsed.domain_contract_ref.domain_id,
            "revision": parsed.domain_contract_ref.domain_revision,
            "descriptor_sha256": parsed.domain_contract_ref.descriptor_sha256,
        },
        "profile_ref": {
            "authority_id": parsed.semantic_profile_ref.profile_id,
            "revision": parsed.semantic_profile_ref.profile_revision,
            "descriptor_sha256": parsed.semantic_profile_ref.descriptor_sha256,
        },
    }


def _verify_wk_result_matches(verified: Any, prepared: Any, aggregate: Any) -> None:
    receipt = aggregate.publication_receipt
    result = aggregate.prospective_result
    expected_bindings = [
        (item.client_op_id, item.result_kind, item.durable_id)
        for item in result.results
    ]
    actual_bindings = [
        (item.client_op_id, "entity", item.durable_object_id)
        for item in verified.object_results
    ] + [
        (item.client_op_id, "assertion", item.durable_assertion_id)
        for item in verified.assertion_results
    ]
    if (
        not verified.verification.exact_child_read_back
        or verified.prepared_change_id != prepared.prepared_change_id
        or verified.dungeonmind_publication_id != prepared.dungeonmind_publication_id
        or verified.expected_parent_revision_id != receipt.expected_parent_revision_id
        or verified.child_revision_id != receipt.published_revision_id
        or verified.child_revision_id != result.published_revision_id
        or verified.child_graph_payload_sha256 != receipt.graph_payload_sha256
        or len(actual_bindings) != len(expected_bindings)
        or sorted(actual_bindings) != sorted(expected_bindings)
    ):
        raise ValueError("WorldKeeper result differs from exact native publication")


def _verify_existing_publication(
    record: dict[str, Any],
    bound: dict[str, Any],
    principal: NativeGraphPrincipal,
    prepared: Any,
    aggregate: Any,
) -> Any:
    """Run WK's exact idempotent verifier only for an already durable receipt."""
    repo = native.repository()
    receipt = repo.get_publication_receipt(
        bound["native_world_id"], prepared.dungeonmind_publication_id
    )
    result = aggregate.prospective_result
    if (
        receipt is None
        or receipt != aggregate.publication_receipt
        or receipt.space_id != bound["native_world_id"]
        or result.space_id != bound["native_world_id"]
        or receipt.publication_id != prepared.dungeonmind_publication_id
        or result.publication_id != prepared.dungeonmind_publication_id
        or receipt.expected_parent_revision_id != prepared.expected_parent_revision_id
        or result.published_revision_id != receipt.published_revision_id
    ):
        raise ValueError("native publication receipt identity differs")
    expected_source_id = _source_admission_id(
        record["operation_id"], principal.subject, bound
    )
    if record.get("source_admission_id") != expected_source_id:
        raise ValueError("stored source admission identity differs")
    _read, access, domain, profile = native.read_context(
        repo,
        bound["native_world_id"],
        prepared.expected_parent_revision_id,
        None,
        principal.role,
        scope_mode="world",
    )
    transport.verify_prepared_parent(
        prepared, _prepared_parent_context(access, bound["native_world_id"])
    )
    source = repo.get_native_source_admission_receipt(
        bound["native_world_id"], expected_source_id
    )
    source_projection = _source_matches(
        repo, bound, record["request"], principal.subject, access, source
    )
    if source_projection != record.get("source_receipt"):
        raise ValueError("stored source receipt differs from native admission")
    if (
        repo.get_prospective_publication(
            bound["native_world_id"], prepared.dungeonmind_publication_id
        )
        != aggregate
        or repo.get_publication_receipt(
            bound["native_world_id"], prepared.dungeonmind_publication_id
        )
        != receipt
    ):
        raise ValueError("native publication changed during exact recovery")
    _assert_binding(bound)

    # The durable Core receipt is a necessary precondition. The existing WK
    # commit path recompiles this exact prepared value and verifies the full
    # prospective request, result bindings, immutable receipt and child graph;
    # replay of that same publication ID is idempotent and cannot create a new
    # child revision.
    verified = transport.runtime(
        repo,
        domain,
        profile,
        now=prepared.prepared_at,
        operation_id=prepared.dungeonmind_publication_id,
    ).commit_prepared_change(prepared, confirmed_by=principal.subject)
    _verify_wk_result_matches(verified, prepared, aggregate)
    _assert_binding(bound)
    return verified


def _expected_results(record: dict[str, Any], aggregate: Any) -> dict[str, Any]:
    request = record["request"]
    rows = aggregate.prospective_result.results
    if request["kind"] == "create_object":
        matches = [row for row in rows if row.client_op_id == "new-object"]
        if len(matches) != 1 or matches[0].result_kind != "entity":
            raise NativeGraphExplorerError(
                "native_publication_integrity_failure",
                "The native publication receipt does not contain the reviewed object result.",
                503,
            )
        return {"created_node_id": matches[0].durable_id}
    matches = [row for row in rows if row.client_op_id == "new-relationship"]
    if len(matches) != 1 or matches[0].result_kind != "assertion":
        raise NativeGraphExplorerError(
            "native_publication_integrity_failure",
            "The native publication receipt does not contain the reviewed relationship result.",
            503,
        )
    return {"assertion_id": matches[0].durable_id}


def _record_commit(
    store: NativeGraphExplorerStore,
    record: dict[str, Any],
    bound: dict[str, Any],
    aggregate: Any,
) -> dict[str, Any]:
    results = _expected_results(record, aggregate)
    result = aggregate.prospective_result
    committed = {
        "publication_id": result.publication_id,
        "parent_revision_id": aggregate.publication_receipt.expected_parent_revision_id,
        "child_revision_id": result.published_revision_id,
        "graph_sha256": aggregate.publication_receipt.graph_payload_sha256,
        **results,
    }
    store.mark_committed(
        record["operation_id"],
        committed_json=canonical_json(committed),
        updated_at=_now(),
    )
    return committed


def _verify_committed_record(
    record: dict[str, Any], bound: dict[str, Any], aggregate: Any
) -> dict[str, Any]:
    expected = _expected_results(record, aggregate)
    result = aggregate.prospective_result
    actual = {
        "publication_id": result.publication_id,
        "parent_revision_id": aggregate.publication_receipt.expected_parent_revision_id,
        "child_revision_id": result.published_revision_id,
        "graph_sha256": aggregate.publication_receipt.graph_payload_sha256,
        **expected,
    }
    if record["committed"] != actual:
        raise NativeGraphExplorerError(
            "native_publication_integrity_failure",
            "The saved operation outcome differs from its exact native receipt.",
            503,
        )
    child = native.read_repository().get_revision(
        bound["native_world_id"], actual["child_revision_id"]
    )
    if (
        child is None
        or child.revision.revision_id != actual["child_revision_id"]
        or child.graph_payload_sha256 != actual["graph_sha256"]
    ):
        raise NativeGraphExplorerError(
            "native_publication_integrity_failure",
            "The committed native child revision failed exact readback verification.",
            503,
        )
    return actual


def _operation_identity(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_id": record["operation_id"],
        "managed_world_id": record["managed_world_id"],
        "native_world_id": record["native_world_id"],
        "binding_version": record["binding_version"],
    }


def _status_response(
    record: dict[str, Any],
    status: str,
    *,
    review: dict[str, str] | None = None,
    graph_value: dict[str, Any] | None = None,
    message: str | None = None,
    rejection: dict[str, str] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "schema": "dmb_native_graph_explorer_v1",
        "status": status,
        **_operation_identity(record),
    }
    if record.get("parent_revision_id"):
        response["parent_revision_id"] = record["parent_revision_id"]
    if review is not None:
        response["review"] = review
    if graph_value is not None:
        response["graph"] = graph_value
    if message is not None:
        response["message"] = message
    if rejection is not None:
        response.update(rejection)
    return response


def _rejected(record: dict[str, Any]) -> dict[str, Any]:
    return _status_response(
        record,
        "rejected",
        rejection=record.get("rejected")
        or {
            "code": "operation_rejected",
            "error": "This operation was rejected. Review the current graph before preparing a new change.",
        },
    )


def _operation_lookup(
    record: dict[str, Any],
    bound: dict[str, Any],
    principal: NativeGraphPrincipal,
    store: NativeGraphExplorerStore,
) -> dict[str, Any]:
    if record["status"] == "rejected":
        return _rejected(record)
    if record["status"] in {"reserved"} or record["prepared"] is None:
        return _status_response(
            record,
            "unknown",
            message="This operation was interrupted before a complete review was saved. Retry the exact same request with this operation ID; no replacement was created.",
        )
    prepared = _decode_prepared(record, bound)
    state, aggregate = _publication_state(native.read_repository(), bound, prepared)
    if state == "committed" and aggregate is not None:
        try:
            _verify_existing_publication(record, bound, principal, prepared, aggregate)
            if record["status"] == "committed":
                _verify_committed_record(record, bound, aggregate)
            else:
                store.mark_committed(
                    record["operation_id"],
                    committed_json=canonical_json(_commit_payload(record, aggregate)),
                    updated_at=_now(),
                )
                record = store.get_operation(record["operation_id"]) or record
        except Exception:
            store.mark_unknown(record["operation_id"], updated_at=_now())
            return _status_response(
                record,
                "unknown",
                message="The exact native publication could not be verified against its saved review. Its outcome remains uncertain; keep this operation ID.",
            )
        return _committed_response(record, bound, principal, aggregate)
    if state == "uncertain" or record["status"] == "committed":
        return _status_response(
            record,
            "unknown",
            message="The native publication receipt could not be verified against this saved review. Its outcome remains uncertain; keep this operation ID.",
        )
    if record["status"] == "prepared":
        return _status_response(
            record,
            "prepared",
            review={"summary": _summary(record["request"])},
        )
    return _status_response(
        record,
        "unknown",
        message=(
            "The native publication receipt is incomplete; the outcome remains uncertain. Keep this operation ID."
            if state == "uncertain"
            else "No publication receipt is currently visible. Confirm the same prepared operation to recover or replay its exact native ID."
        ),
    )


def _commit_payload(record: dict[str, Any], aggregate: Any) -> dict[str, Any]:
    result = aggregate.prospective_result
    return {
        "publication_id": result.publication_id,
        "parent_revision_id": aggregate.publication_receipt.expected_parent_revision_id,
        "child_revision_id": result.published_revision_id,
        "graph_sha256": aggregate.publication_receipt.graph_payload_sha256,
        **_expected_results(record, aggregate),
    }


def _committed_response(
    record: dict[str, Any],
    bound: dict[str, Any],
    principal: NativeGraphPrincipal,
    aggregate: Any,
) -> dict[str, Any]:
    _verify_committed_record(record, bound, aggregate)
    current = _graph_envelope(bound, principal)
    response = _status_response(record, "committed", graph_value=current)
    if record["request"]["kind"] != "create_object":
        return response
    created_node_id = (record.get("committed") or {}).get("created_node_id")
    if not isinstance(created_node_id, str):
        raise NativeGraphExplorerError(
            "native_publication_integrity_failure",
            "The committed create receipt has no verified entity identity.",
            503,
        )
    exact = _graph_envelope(
        bound,
        principal,
        revision_id=(record.get("committed") or {}).get("child_revision_id"),
    )["graph"]
    exact_complete = (
        exact["completeness"]["omitted_entities"] == 0
        and exact["completeness"]["unexamined_entities"] == 0
    )
    current_ids = {node["id"] for node in current["graph"]["nodes"]}
    exact_ids = {node["id"] for node in exact["nodes"]}
    if (
        exact_complete
        and created_node_id in exact_ids
        and created_node_id in current_ids
    ):
        response["created_node_id"] = created_node_id
    else:
        response["message"] = (
            "The object is committed, but the current native graph readback cannot safely identify it for canvas placement."
        )
    return response


def prepare(
    request: NativeGraphExplorerPrepareRequest,
    principal: NativeGraphPrincipal,
) -> dict[str, Any]:
    _require_gm(principal)
    payload = _normalize_request(request)
    bound = _resolve_binding(payload["managed_world_id"])
    if (
        payload["native_world_id"] != bound["native_world_id"]
        or payload["binding_version"] != bound["binding_version"]
    ):
        raise NativeGraphExplorerError(
            "binding_changed",
            "The selected World binding changed. Reload the graph before reviewing this operation.",
            409,
        )
    graph_value = _graph_envelope(bound, principal)
    _validate_write_capability(payload, graph_value)

    request_json = canonical_json(payload)
    request_sha = sha256_text(request_json)
    operation_id = payload["operation_id"]
    with _open_store(principal, payload["managed_world_id"]) as store:
        with store.atomic():
            record = store.get_operation(operation_id)
            if record is not None:
                if (
                    record["request_sha256"] != request_sha
                    or record["request_json"] != request_json
                ):
                    raise NativeGraphExplorerError(
                        "operation_id_conflict",
                        "This operation ID is already bound to different input in the selected World.",
                        409,
                    )
                if (
                    record["native_world_id"] != bound["native_world_id"]
                    or record["binding_version"] != bound["binding_version"]
                ):
                    return _status_response(
                        record,
                        "unknown",
                        message="The World binding changed after this operation was saved. The operation remains retained and will not be sent to another World.",
                    )
                if record["status"] == "rejected":
                    return _rejected(record)
                if record["status"] == "committed":
                    return _operation_lookup(record, bound, principal, store)
                if record["prepared"] is not None:
                    return _operation_lookup(record, bound, principal, store)
            else:
                if (
                    graph_value["graph"]["revision_id"]
                    != payload["expected_revision_id"]
                ):
                    raise NativeGraphExplorerError(
                        "stale_revision",
                        "The selected World graph changed. Refresh it and prepare a new review.",
                        409,
                    )
                if payload["kind"] == "connect" and _existing_edge(
                    payload, graph_value
                ):
                    return {
                        "schema": "dmb_native_graph_explorer_v1",
                        "operation_id": payload["operation_id"],
                        "managed_world_id": bound["managed_world_id"],
                        "native_world_id": bound["native_world_id"],
                        "binding_version": bound["binding_version"],
                        "status": "already_exists",
                        "message": "That directed native relationship already exists. Existing independent assertions were left unchanged.",
                        "graph": graph_value,
                    }
                if store.operation_count() >= store.max_operations:
                    raise NativeGraphExplorerError(
                        "operation_limit_reached",
                        "This World has reached its retained native graph operation limit.",
                        409,
                    )
                store.reserve_operation(
                    operation_id=operation_id,
                    native_world_id=bound["native_world_id"],
                    binding_version=bound["binding_version"],
                    expected_revision_id=payload["expected_revision_id"],
                    request_json=request_json,
                    updated_at=_now(),
                )
                record = store.get_operation(operation_id)
                if record is None:
                    raise NativeGraphExplorerError(
                        "operation_journal_unavailable",
                        "The operation reservation could not be read back.",
                        503,
                    )

            if record["prepared"] is not None and record["status"] == "unknown":
                return _status_response(
                    record,
                    "unknown",
                    message="The exact native publication outcome is uncertain. Check this same operation ID before retrying; no replacement will be created.",
                )

            # Persist uncertainty before source dispatch. The same source
            # admission ID is reused if this response is lost.
            store.mark_unknown(operation_id, updated_at=_now())
            store.checkpoint()
            try:
                _assert_binding(bound)
                repo = native.repository()
                source_id = _source_admission_id(operation_id, principal.subject, bound)
                receipt = repo.get_native_source_admission_receipt(
                    bound["native_world_id"], source_id
                )
                if receipt is None:
                    head = repo.get_head(bound["native_world_id"])
                    if (
                        head is None
                        or head.head_revision_id != payload["expected_revision_id"]
                    ):
                        rejected = {
                            "code": "stale_revision",
                            "error": "The graph changed before the authored source could be saved. Refresh it and prepare again.",
                        }
                        store.mark_rejected(operation_id, **rejected, updated_at=_now())
                        saved = store.get_operation(operation_id)
                        return _rejected(saved or record)
                    domain, profile = native.descriptors(
                        repo, bound["native_world_id"], payload["expected_revision_id"]
                    )
                    body = _source_body(payload)
                    encoded = body.encode("utf-8")
                    body_digest = hashlib.sha256(encoded).hexdigest()
                    origin = NativeTextSourceOriginV1(
                        namespace=SOURCE_NAMESPACE,
                        object_id=operation_id,
                        revision_id=payload["expected_revision_id"],
                    )
                    source_request = NativeTextSourceAdmissionV1(
                        space_id=bound["native_world_id"],
                        admission_id=source_id,
                        expected_parent_revision_id=payload["expected_revision_id"],
                        created_at=_now(),
                        body_text=body,
                        expected_body_sha256=body_digest,
                        source_classification=SOURCE_CLASSIFICATION,
                        authority="primary",
                        visibility=LabelsAnyVisibility(labels=[GM_LABEL]),
                        origin=origin,
                        spans=(
                            NativeTextEvidenceSpanRequestV1(
                                client_ref=operation_id,
                                evidence_role="support",
                                start_byte=0,
                                end_byte=len(encoded),
                                expected_slice_sha256=body_digest,
                            ),
                        ),
                    )
                    _assert_binding(bound)
                    try:
                        receipt = publish_native_text_source_evidence(
                            repository=repo,
                            domain_contract=domain,
                            semantic_profile=profile,
                            request=source_request,
                        )
                    except Exception:
                        # Check the exact deterministic receipt before deciding
                        # whether the source admission response was lost.
                        receipt = repo.get_native_source_admission_receipt(
                            bound["native_world_id"], source_id
                        )
                        if receipt is None:
                            raise
                _assert_binding(bound)
                current_head = repo.get_head(bound["native_world_id"])
                if (
                    receipt is None
                    or current_head is None
                    or current_head.head_revision_id != receipt.published_revision_id
                    or receipt.publication_receipt.expected_parent_revision_id
                    != payload["expected_revision_id"]
                ):
                    rejected = {
                        "code": "stale_revision",
                        "error": "The selected World changed while source evidence was prepared. The source receipt is retained; refresh and prepare a new review.",
                    }
                    store.mark_rejected(operation_id, **rejected, updated_at=_now())
                    saved = store.get_operation(operation_id)
                    return _rejected(saved or record)
                context, access = native.access_context(repo, bound["native_world_id"])
                receipt_payload = _source_matches(
                    repo, bound, payload, principal.subject, access, receipt
                )
                domain, profile = native.descriptors(
                    repo, bound["native_world_id"], current_head.head_revision_id
                )
                intent = _intent(
                    payload,
                    receipt_payload["evidence_ref_id"],
                    bound["native_world_id"],
                    profile,
                )
                publication_id = _publication_id(operation_id, principal.subject, bound)
                prepared = transport.runtime(
                    repo,
                    domain,
                    profile,
                    now=_now(),
                    operation_id=publication_id,
                ).prepare_change(intent)
                transport.verify_prepared_parent(prepared, context)
                if (
                    prepared.prepared_change_id != publication_id
                    or prepared.dungeonmind_publication_id != publication_id
                    or prepared.prepared_operations != intent.operations
                ):
                    raise NativeGraphExplorerError(
                        "prepared_operation_integrity_failure",
                        "WorldKeeper returned a review that differs from the exact submitted graph change.",
                        503,
                    )
                _assert_binding(bound)
                encoded_prepared = _prepared_json(prepared)
                receipt_json = canonical_json(receipt_payload)
                store.mark_prepared(
                    operation_id,
                    source_admission_id=source_id,
                    source_receipt_json=receipt_json,
                    parent_revision_id=prepared.expected_parent_revision_id,
                    prepared_json=encoded_prepared,
                    updated_at=_now(),
                )
                record = store.get_operation(operation_id)
                if record is None:
                    raise NativeGraphExplorerError(
                        "operation_journal_unavailable",
                        "The prepared operation could not be read back from Buddy state.",
                        503,
                    )
                return _status_response(
                    record,
                    "prepared",
                    review={"summary": _summary(payload)},
                )
            except NativeGraphExplorerError:
                raise
            except (StaleParentRevisionError, PreparedChangeStale):
                rejected = {
                    "code": "stale_revision",
                    "error": "The graph changed while WorldKeeper prepared the operation. Refresh it and prepare again.",
                }
                store.mark_rejected(operation_id, **rejected, updated_at=_now())
                saved = store.get_operation(operation_id)
                return _rejected(saved or record)
            except (PersistenceUnavailableError, PersistenceIntegrityError):
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="Native source or review persistence could not be verified. Keep this same operation ID and check its status before retrying.",
                )
            except (InvalidWorldChange, ValueError, TypeError):
                rejected = {
                    "code": "native_change_rejected",
                    "error": "WorldKeeper could not prepare this exact graph change. The source record, if already admitted, is retained.",
                }
                store.mark_rejected(operation_id, **rejected, updated_at=_now())
                saved = store.get_operation(operation_id)
                return _rejected(saved or record)
            except Exception:
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="Native review preparation could not be confirmed. Keep this same operation ID and check its status before retrying.",
                )


def confirm(
    request: NativeGraphExplorerOperationRequest,
    principal: NativeGraphPrincipal,
) -> dict[str, Any]:
    _require_gm(principal)
    operation_id = _parse_operation_id(request.operation_id)
    bound = _resolve_binding(request.managed_world_id)
    with _open_store(principal, request.managed_world_id) as store:
        with store.atomic():
            record = store.get_operation(operation_id)
            if record is None:
                raise NativeGraphExplorerError(
                    "operation_not_found",
                    "No prepared operation with this ID exists in the selected World.",
                    404,
                )
            if (record["native_world_id"], record["binding_version"]) != (
                bound["native_world_id"],
                bound["binding_version"],
            ):
                return _status_response(
                    record,
                    "unknown",
                    message="The selected World binding changed after review. The operation is retained and will not be sent to a different World.",
                )
            if record["status"] == "rejected":
                return _rejected(record)
            if record["prepared"] is None:
                return _status_response(
                    record,
                    "unknown",
                    message="This operation has no complete WorldKeeper review yet. Retry its exact prepare request with the same operation ID.",
                )
            prepared = _decode_prepared(record, bound)
            repo = native.repository()
            state, aggregate = _publication_state(repo, bound, prepared)
            if state == "committed" and aggregate is not None:
                try:
                    _verify_existing_publication(
                        record, bound, principal, prepared, aggregate
                    )
                    if record["status"] != "committed":
                        _record_commit(store, record, bound, aggregate)
                        record = store.get_operation(operation_id) or record
                    else:
                        _verify_committed_record(record, bound, aggregate)
                except Exception:
                    store.mark_unknown(operation_id, updated_at=_now())
                    return _status_response(
                        record,
                        "unknown",
                        message="The exact native publication could not be verified against its saved review. Its outcome remains uncertain; keep this operation ID.",
                    )
                return _committed_response(record, bound, principal, aggregate)
            if state == "uncertain":
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="The native publication receipt is incomplete. No new publication was attempted; keep this operation ID and check again.",
                )

            current_head = repo.get_head(bound["native_world_id"])
            if (
                current_head is None
                or current_head.head_revision_id != prepared.expected_parent_revision_id
            ):
                rejected = {
                    "code": "stale_revision",
                    "error": "The selected World graph changed after review. Refresh and prepare a new review.",
                }
                store.mark_rejected(operation_id, **rejected, updated_at=_now())
                return _rejected(store.get_operation(operation_id) or record)

            context, access = native.access_context(repo, bound["native_world_id"])
            transport.verify_prepared_parent(prepared, context)
            receipt_row = record["source_receipt"]
            source = repo.get_native_source_admission_receipt(
                bound["native_world_id"], record["source_admission_id"]
            )
            source_projection = _source_matches(
                repo, bound, record["request"], principal.subject, access, source
            )
            if source_projection != receipt_row:
                raise NativeGraphExplorerError(
                    "native_source_receipt_invalid",
                    "The reviewed source receipt no longer matches this operation.",
                    503,
                )
            _assert_binding(bound)
            domain, profile = native.descriptors(
                repo, bound["native_world_id"], prepared.expected_parent_revision_id
            )
            # Unknown is durably committed before any native WorldKeeper dispatch.
            store.mark_unknown(operation_id, updated_at=_now())
            store.checkpoint()
            try:
                result = transport.runtime(
                    repo,
                    domain,
                    profile,
                    now=prepared.prepared_at,
                    operation_id=prepared.dungeonmind_publication_id,
                ).commit_prepared_change(prepared, confirmed_by=principal.subject)
                if not result.verification.exact_child_read_back:
                    store.mark_unknown(operation_id, updated_at=_now())
                    return _status_response(
                        record,
                        "unknown",
                        message="WorldKeeper did not confirm exact native child readback. The operation remains recoverable under this same ID.",
                    )
                state, aggregate = _publication_state(repo, bound, prepared)
                if state != "committed" or aggregate is None:
                    store.mark_unknown(operation_id, updated_at=_now())
                    return _status_response(
                        record,
                        "unknown",
                        message="The commit response arrived, but the exact native publication receipt is unavailable. Keep this same operation ID for recovery.",
                    )
                _verify_wk_result_matches(result, prepared, aggregate)
                committed = _record_commit(store, record, bound, aggregate)
                record = store.get_operation(operation_id) or record
                if committed["child_revision_id"] != result.child_revision_id:
                    store.mark_unknown(operation_id, updated_at=_now())
                    return _status_response(
                        record,
                        "unknown",
                        message="The commit response and exact publication receipt differ. The operation remains uncertain and was not replayed.",
                    )
                _assert_binding(bound)
                return _committed_response(record, bound, principal, aggregate)
            except PreparedChangeStale:
                rejected = {
                    "code": "stale_revision",
                    "error": "The selected World graph changed after review. Refresh and prepare a new review.",
                }
                store.mark_rejected(operation_id, **rejected, updated_at=_now())
                saved = store.get_operation(operation_id) or record
                return _rejected(saved)
            except PreparedChangeConflict:
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="WorldKeeper reported a publication conflict. The operation remains retained for exact receipt recovery.",
                )
            except (
                CommittedChangeOutcomeUnknown,
                CommittedChangeVerificationUnavailable,
                PersistenceUnavailableError,
                PersistenceIntegrityError,
            ):
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="Native publication could not be confirmed. The exact review is retained for recovery; do not create a replacement operation.",
                )
            except (
                PreparedChangeIntegrityFailure,
                CommitAuthorityIntegrityFailure,
                CommittedChangeVerificationIntegrityFailure,
            ):
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="WorldKeeper could not verify this exact prepared publication. The outcome remains uncertain; keep this same operation ID.",
                )
            except Exception:
                # Any exception after dispatch is uncertain. A retry can only
                # use the exact prepared/publication ID after receipt checks.
                state, aggregate = _publication_state(repo, bound, prepared)
                if state == "committed" and aggregate is not None:
                    try:
                        _verify_existing_publication(
                            record, bound, principal, prepared, aggregate
                        )
                        _record_commit(store, record, bound, aggregate)
                        saved = store.get_operation(operation_id) or record
                        return _committed_response(saved, bound, principal, aggregate)
                    except Exception:
                        store.mark_unknown(operation_id, updated_at=_now())
                        return _status_response(
                            record,
                            "unknown",
                            message="The exact native publication could not be verified after dispatch. Its outcome remains uncertain; keep this same operation ID.",
                        )
                store.mark_unknown(operation_id, updated_at=_now())
                return _status_response(
                    record,
                    "unknown",
                    message="Native publication could not be confirmed. The exact prepared operation remains recoverable under this ID.",
                )


def operation(
    request: NativeGraphExplorerOperationRequest,
    principal: NativeGraphPrincipal,
) -> dict[str, Any]:
    _require_gm(principal)
    operation_id = _parse_operation_id(request.operation_id)
    bound = _resolve_binding(request.managed_world_id)
    with _open_store(principal, request.managed_world_id) as store:
        with store.atomic():
            record = store.get_operation(operation_id)
            if record is None:
                return {
                    "schema": "dmb_native_graph_explorer_v1",
                    "operation_id": operation_id,
                    "managed_world_id": request.managed_world_id,
                    "native_world_id": bound["native_world_id"],
                    "binding_version": bound["binding_version"],
                    "status": "not_found",
                }
            if (record["native_world_id"], record["binding_version"]) != (
                bound["native_world_id"],
                bound["binding_version"],
            ):
                return _status_response(
                    record,
                    "unknown",
                    message="The selected World binding changed after this operation was saved. Its record is retained and no action was sent to the new binding.",
                )
            return _operation_lookup(record, bound, principal, store)
