"""Independent lifecycle assessment. V1 and historical scores are unchanged.

The native adapter performs read-only acquisitions, never publication. Callers
retain actual prepare/confirm/read responses; reviewed meaning is a separate
input. Native publication IDs/digests are not harness correspondence IDs/digests.
This is component evidence, not semantic entailment or full-system acceptance.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .source_statement_contract import correspondence_key, semantic_digest

SCHEMA = "buddy_source_statement_lifecycle_capture_v2"
UNIQUE_EXTENT = "unique-byte-extent:v1"


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def harness_statement(payload):
    """Lossless logical-source encoding; extent disambiguation is not meaning."""
    clause = deepcopy(payload["clause"])
    clause["logical_source"] = canonical(clause["logical_source"])
    clause["disambiguator"] = UNIQUE_EXTENT
    return {
        "clause": clause,
        **{
            key: deepcopy(payload[key])
            for key in (
                "meaning",
                "episode",
                "mode",
                "reporter",
                "uncertainty",
                "qualifications",
                "referents",
                "embedded_content_factive",
                "assertion_target",
            )
        },
    }


def native_semantic_digest(payload):
    return digest({key: value for key, value in payload.items() if key != "proof"})


def native_publication_id(payload):
    return "dmb-statement:v1:" + digest(payload["clause"])


def _context(snapshot, campaign, visibility):
    revision = snapshot.revision
    return {
        "authority": "native_vnext",
        "world": revision.space_id,
        "campaign": campaign,
        "visibility": visibility,
        "revision": revision.revision_id,
        "domain_ref": revision.domain_contract_ref.model_dump(mode="json"),
        "profile_ref": revision.semantic_profile_ref.model_dump(mode="json"),
    }


def _header(snapshot):
    revision = snapshot.revision
    return {
        "world": revision.space_id,
        "revision": revision.revision_id,
        "parent": revision.parent_revision_id,
        "graph_sha256": snapshot.graph_payload_sha256,
        "operation_ids": list(revision.operation_ids),
        "domain_ref": revision.domain_contract_ref.model_dump(mode="json"),
        "profile_ref": revision.semantic_profile_ref.model_dump(mode="json"),
    }


def capture_native_lifecycle(repository, records, subject_response, principal):
    """Acquire real headers, source bytes, authorized edges and child payloads.

    records contains actual {prepare, confirm} responses, one per original
    publication. No retry is invented; recovery remains unassessed unless a
    separately recorded experiment is supplied to the evaluator. Exceptions
    acquiring evidence are retained, not converted to empty successful reads.
    Native imports stay inside this explicit runtime adapter.
    """
    from fastapi.encoders import jsonable_encoder
    import dungeonmind
    import worldkeeper
    from dungeonmind.application.vnext import (
        EntityReadService,
        open_admitted_native_text,
    )
    from dungeonmind.application.vnext.prospective import get_prospective_publication
    from apps.live_control_server.services import source_statements as runtime
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        decode_publication_intent,
    )

    response = deepcopy(subject_response)
    space, campaign, read_revision = (
        response[k] for k in ("space_id", "campaign_id", "revision_id")
    )
    result = {
        "schema": SCHEMA,
        "execution": {
            "core_module": dungeonmind.__file__,
            "wk_module": worldkeeper.__file__,
        },
        "records": [],
        "read_response": response,
        "read_context": None,
        "headers": [],
        "edges": None,
        "source_bytes": {},
        "acquisition_errors": [],
        "recovery": None,
    }
    headers = {}
    try:
        read, access, _, _ = runtime._context(
            repository, space, read_revision, campaign, principal.role
        )
        snapshot = repository.get_revision(space, read_revision)
        result["read_context"] = _context(
            snapshot, campaign, "gm" if principal.role == "gm" else "player"
        )
        subject = EntityReadService().get_complete_entity(read, response["entity_id"])
        result["native_read_status"] = subject.completeness.status
        result["edges"] = [
            {
                "edge_id": a.assertion_id,
                "statement_id": a.subject_entity_id,
                "entity_id": a.value.entity_id,
                "predicate": a.predicate,
                "direction": "incoming",
                "context": result["read_context"],
                "scope": jsonable_encoder(a.metadata.scope),
                "visibility": jsonable_encoder(a.metadata.visibility),
                "evidence_ref_ids": list(a.metadata.evidence_ref_ids),
            }
            for a in subject.assertions
            if a.predicate == runtime.mapping.ABOUT
            and getattr(a.value, "entity_id", None) == response["entity_id"]
        ]
    except Exception as exc:
        result["acquisition_errors"].append(
            {"stage": "read", "error": type(exc).__name__}
        )
    for record in records:
        captured = deepcopy(record)
        captured["signed_selection_verified"] = False
        try:
            prepared = record["prepare"]
            envelope = prepared["envelope"]
            signed = decode_publication_intent(
                prepared["token"], allow_expired_recovery=True
            )
            captured["signed_selection_verified"] = (
                signed == envelope
                and envelope["principal"] == principal.subject
                and envelope["prepared_digest"] == digest(prepared["prepared"])
            )
            payload = envelope["payload"]
            receipt = record["confirm"]["result"]["receipt"]
            aggregate = get_prospective_publication(
                space, native_publication_id(payload), repository=repository
            )
            if aggregate is not None:
                captured["original_receipt"] = jsonable_encoder(
                    aggregate.publication_receipt
                )
                captured["original_bindings"] = jsonable_encoder(
                    aggregate.prospective_result.results
                )
            parent = envelope["parent_context"]["revision_id"]
            child = receipt["published_revision_id"]
            original = record["confirm"]["result"]["bundle"]["statement_id"]
            captured["selection_context"] = _context(
                repository.get_revision(space, parent), campaign, "gm"
            )
            captured["publication_context"] = _context(
                repository.get_revision(space, child), campaign, "gm"
            )
            # The child is independently read, not copied from the confirmation.
            captured["published_bundle"] = jsonable_encoder(
                runtime._bundle(repository, space, child, campaign, original)
            )
            _, source_access, _, _ = runtime._context(
                repository, space, child, campaign
            )
            opened = open_admitted_native_text(
                source_access, payload["proof"]["evidence_ref_id"]
            )
            if opened.status == "available":
                result["source_bytes"][payload["clause"]["source_sha256"]] = (
                    opened.body_text.encode()
                )
            # Acquire the entire actual parent chain without an arbitrary depth cap.
            cursor, seen = read_revision, set()
            while cursor is not None:
                if cursor in seen:
                    raise ValueError("cyclic native ancestry")
                seen.add(cursor)
                snap = repository.get_revision(space, cursor)
                headers[cursor] = _header(snap)
                cursor = headers[cursor]["parent"]
            for revision in (parent, child):
                headers[revision] = _header(repository.get_revision(space, revision))
            before_graph = repository.get_revision(space, parent).graph_payload
            after_graph = repository.get_revision(space, child).graph_payload
            delta = {"added": {}, "removed_or_changed": {}}
            for section, identity in (
                ("assertions", "assertion_id"),
                ("entities", "entity_id"),
                ("evidence", "evidence_ref_id"),
                ("aliases", "alias_id"),
            ):
                before_rows = {r[identity]: r for r in before_graph[section]}
                after_rows = {r[identity]: r for r in after_graph[section]}
                delta["removed_or_changed"][section] = sorted(
                    k for k, v in before_rows.items() if after_rows.get(k) != v
                )
                delta["added"][section] = [
                    deepcopy(v) for k, v in after_rows.items() if k not in before_rows
                ]
            captured["graph_delta"] = delta
        except Exception as exc:
            result["acquisition_errors"].append(
                {"stage": "publication", "error": type(exc).__name__}
            )
        result["records"].append(captured)
    result["headers"] = list(headers.values())
    return result


def observe_lost_ack_retry(
    packet, lost_ack_call, retry_call, original_result_lookup, head_lookup
):
    """Execute a controlled lost-ack experiment and observe its actual retry.

    Callbacks must use the same disposable test authority. The first callback
    invokes the real publication and injects acknowledgment loss; it must raise.
    The lookup reads the durable original result independently before retry.
    This helper never infers execution from a product ``recovered`` flag.
    """
    before = deepcopy(packet)
    prior = deepcopy(original_result_lookup())
    error = None
    try:
        lost_ack_call(packet)
    except Exception as exc:
        error = type(exc).__name__
    original = deepcopy(original_result_lookup())
    head_before = deepcopy(head_lookup())
    retried = retry_call(packet)
    return {
        "schema": "buddy_observed_lost_ack_retry_v2",
        "lost_ack_error": error,
        "result_before_first_call": prior,
        "packet_before": before,
        "packet_after": deepcopy(packet),
        "original_result": original,
        "retry_result": deepcopy(retried),
        "head_before_retry": head_before,
        "head_after_retry": deepcopy(head_lookup()),
    }


def evaluate_lifecycle(review, capture):
    """Review rows pin independently selected payload and parent context.

    A check is pass/fail only with evidence to assess it; absent acquisitions
    are unassessed. Expectations must never be built from the observed output.
    """
    if not isinstance(review, list) or not review:
        raise ValueError("nonempty independently reviewed lifecycle required")
    expected = {}
    for row in review:
        statement = harness_statement(row["payload"])
        key = correspondence_key(statement["clause"])
        semantic_digest(statement)
        if key in expected:
            raise ValueError("duplicate reviewed clause")
        expected[key] = row
    checks = {}

    def check(name, value, reason=""):
        checks[name] = {
            "status": "unassessed" if value is None else ("pass" if value else "fail"),
            "reason": reason,
        }

    check("capture_schema", capture.get("schema") == SCHEMA)
    rows = capture.get("records", [])
    by_key = {}
    try:
        for row in rows:
            payload = row["prepare"]["envelope"]["payload"]
            key = correspondence_key(harness_statement(payload)["clause"])
            if key in by_key:
                raise ValueError("aliased capture clause")
            by_key[key] = row
        check("selected_clause_inventory", set(by_key) == set(expected))
    except (KeyError, TypeError, ValueError):
        check("selected_clause_inventory", False)
    headers = {}
    duplicate_header = False
    for header in capture.get("headers", []):
        revision = header["revision"]
        duplicate_header |= revision in headers
        headers[revision] = header
    check("unique_headers", not duplicate_header)
    response = capture.get("read_response", {})
    read_context = capture.get("read_context")
    read_bundles = response.get("statements")
    native_ids = []
    expected_edges = []
    order_endpoints = {}
    for key, expected_row in expected.items():
        payload = expected_row["payload"]
        clause = payload["clause"]
        order_endpoints[
            (
                clause["source_sha256"],
                clause["start_byte"],
                clause["end_byte"],
                clause["clause_sha256"],
            )
        ] = key
    for key, expected_row in expected.items():
        prefix = key + ":"
        row = by_key.get(key)
        if row is None:
            check(prefix + "selected_payload", None, "missing selection capture")
            continue
        envelope = row["prepare"]["envelope"]
        selected = envelope["payload"]
        expected_payload = expected_row["payload"]
        check(prefix + "selected_payload", selected == expected_payload)
        check(
            prefix + "signed_selection",
            row.get("signed_selection_verified"),
            "adapter signature acquisition required",
        )
        parent_context = row.get("selection_context")
        check(
            prefix + "parent_context",
            None
            if parent_context is None
            else parent_context == expected_row["parent_context"],
        )
        pinned_parent = envelope.get("parent_context", {})

        def native_ref(ref, kind):
            return {
                "authority_id": ref[kind + "_id"],
                "revision": ref[kind + "_revision"],
                "descriptor_sha256": ref["descriptor_sha256"],
            }

        expected_context = expected_row["parent_context"]
        check(
            prefix + "prepared_parent_binding",
            pinned_parent.get("space_id") == expected_context["world"]
            and pinned_parent.get("revision_id") == expected_context["revision"]
            and pinned_parent.get("domain_ref")
            == native_ref(expected_context["domain_ref"], "domain")
            and pinned_parent.get("profile_ref")
            == native_ref(expected_context["profile_ref"], "profile")
            and envelope.get("prepared_digest") == digest(row["prepare"]["prepared"]),
        )
        try:
            publication = row["confirm"]["result"]
            receipt, bindings = publication["receipt"], publication["bindings"]
            child = receipt["published_revision_id"]
            parent = expected_row["parent_context"]["revision"]
            child_header = headers.get(child)
            parent_header = headers.get(parent)
            check(
                prefix + "native_header_context",
                None
                if child_header is None or parent_header is None
                else all(
                    header["world"] == expected_context["world"]
                    and header["domain_ref"] == expected_context["domain_ref"]
                    and header["profile_ref"] == expected_context["profile_ref"]
                    for header in (parent_header, child_header)
                )
                and parent_header["graph_sha256"] == pinned_parent.get("graph_sha256"),
            )
            check(
                prefix + "publication_parent",
                None
                if child_header is None
                else child_header["parent"] == parent
                and child != parent
                and child_header["world"] == expected_payload["clause"]["world"]
                and receipt.get("expected_parent_revision_id") == parent
                and receipt.get("space_id") == child_header["world"]
                and receipt.get("graph_payload_sha256") == child_header["graph_sha256"]
                and receipt.get("publication_id") in child_header["operation_ids"],
            )
            check(
                prefix + "original_receipt",
                None
                if row.get("original_receipt") is None
                else receipt == row["original_receipt"]
                and bindings == row.get("original_bindings"),
            )
            publication_context = row.get("publication_context")
            check(
                prefix + "publication_context",
                None
                if publication_context is None
                else publication_context
                == {**expected_row["parent_context"], "revision": child},
            )
            operation = native_publication_id(expected_payload)
            check(
                prefix + "native_publication_identity",
                receipt.get("publication_id") == operation,
            )
            objects = [
                b["durable_id"]
                for b in bindings
                if b["result_kind"] == "entity" and b["client_op_id"] == "statement"
            ]
            bundle = row.get("published_bundle")
            check(
                prefix + "published_payload",
                None if bundle is None else bundle["payload"] == expected_payload,
            )
            check(
                prefix + "native_semantic_digest",
                None
                if bundle is None
                else bundle["semantic_digest"]
                == native_semantic_digest(expected_payload),
            )
            statement_id = objects[0] if len(objects) == 1 else None
            native_ids.append(statement_id)
            expected_ops = {
                "statement",
                "qualified-payload",
                *("about:" + str(i) for i in range(len(expected_payload["referents"]))),
            }
            if expected_payload["reporter"]:
                expected_ops.add("reporter")
            assertion_ids = [
                b["durable_id"] for b in bindings if b["result_kind"] == "assertion"
            ]
            check(
                prefix + "native_mappings",
                bundle is not None
                and statement_id == bundle["statement_id"]
                and bundle["revision_id"] == child
                and len(bindings) == len(expected_ops)
                and {b["client_op_id"] for b in bindings} == expected_ops
                and len(set(assertion_ids)) == len(assertion_ids)
                and set(assertion_ids) == set(bundle["assertion_ids"]),
            )
            delta = row.get("graph_delta")
            check(
                prefix + "valid_data_preserved",
                None
                if delta is None
                else not any(delta["removed_or_changed"].values())
                and not delta["added"]["aliases"]
                and not delta["added"]["evidence"],
            )
            new_assertions = [] if delta is None else delta["added"]["assertions"]
            check(
                prefix + "no_direct_event_leakage",
                None
                if delta is None
                else {a["assertion_id"] for a in new_assertions} == set(assertion_ids)
                and len(new_assertions) == len(assertion_ids)
                and all(
                    a["subject_entity_id"] == statement_id
                    and a["predicate"]
                    in {
                        "dnd5e:summary",
                        "dungeonbuddy.custom:about",
                        "dungeonbuddy.custom:reported_by",
                    }
                    for a in new_assertions
                )
                and [e["entity_id"] for e in delta["added"]["entities"]]
                == [statement_id],
            )
            cursor, seen, ancestry = response.get("revision_id"), set(), None
            while cursor is not None:
                if cursor in seen:
                    ancestry = False
                    break
                seen.add(cursor)
                if cursor == child:
                    ancestry = True
                    break
                if cursor not in headers:
                    break
                header = headers[cursor]
                if (
                    child_header is None
                    or header["world"] != expected_payload["clause"]["world"]
                    or header["domain_ref"]
                    != expected_row["parent_context"]["domain_ref"]
                    or header["profile_ref"]
                    != expected_row["parent_context"]["profile_ref"]
                ):
                    ancestry = False
                    break
                cursor = header["parent"]
                if cursor is None:
                    ancestry = False
            check(
                prefix + "read_descends_from_child",
                ancestry,
                "missing lineage is not proven descent",
            )
            check(
                prefix + "read_context",
                None
                if read_context is None
                else read_context
                == {
                    **expected_row["parent_context"],
                    "revision": response.get("revision_id"),
                }
                and response.get("space_id") == read_context["world"]
                and response.get("campaign_id") == read_context["campaign"],
            )
            matches = (
                []
                if read_bundles is None
                else [b for b in read_bundles if b["statement_id"] == statement_id]
            )
            check(
                prefix + "read_payload",
                None
                if read_bundles is None
                else len(matches) == 1
                and matches[0]["payload"] == expected_payload
                and matches[0]["revision_id"] == response.get("revision_id")
                and matches[0]["semantic_digest"]
                == native_semantic_digest(expected_payload),
            )
            check(
                prefix + "read_mapping_identity",
                None
                if read_bundles is None
                else len(matches) == 1
                and set(matches[0]["assertion_ids"]) == set(assertion_ids)
                and len(matches[0]["assertion_ids"]) == len(assertion_ids),
            )
            edges = capture.get("edges")
            about = (
                []
                if edges is None
                else [e for e in edges if e["statement_id"] == statement_id]
            )
            binding_by_op = {b["client_op_id"]: b for b in bindings}
            relevant = [
                (index, entity)
                for index, entity in enumerate(expected_payload["referents"])
                if entity == response.get("entity_id")
            ]
            for index, entity in relevant:
                expected_edges.append(
                    {
                        "edge_id": binding_by_op["about:" + str(index)]["durable_id"],
                        "statement_id": statement_id,
                        "entity_id": entity,
                        "predicate": "dungeonbuddy.custom:about",
                        "direction": "incoming",
                        "context": read_context,
                        "scope": [
                            {
                                "axis": "dungeonbuddy.scope:campaign",
                                "value": expected_context["campaign"],
                            }
                        ],
                        "visibility": {
                            "kind": "labels_any",
                            "labels": ["dungeonbuddy.visibility:gm"],
                        },
                        "evidence_ref_ids": [
                            expected_payload["proof"]["evidence_ref_id"]
                        ],
                    }
                )
            check(
                prefix + "authorized_about_discovery",
                None
                if edges is None or read_context is None
                else any(
                    e["entity_id"] == response.get("entity_id")
                    and e["entity_id"] in expected_payload["referents"]
                    and e["predicate"] == "dungeonbuddy.custom:about"
                    and e["direction"] == "incoming"
                    and e["context"] == read_context
                    and e in expected_edges
                    for e in about
                ),
            )
        except (KeyError, TypeError, IndexError):
            check(
                prefix + "publication_capture",
                None,
                "missing or malformed native evidence",
            )
        clause = expected_payload["clause"]
        body = capture.get("source_bytes", {}).get(clause["source_sha256"])
        check(
            prefix + "source_bytes",
            None
            if body is None
            else isinstance(body, bytes)
            and hashlib.sha256(body).hexdigest() == clause["source_sha256"]
            and body[clause["start_byte"] : clause["end_byte"]].decode(
                "utf-8", errors="replace"
            )
            == expected_payload["quote"]
            and hashlib.sha256(
                body[clause["start_byte"] : clause["end_byte"]]
            ).hexdigest()
            == clause["clause_sha256"],
        )
        for index, order in enumerate(expected_payload["source_order"]):
            endpoints = [
                (
                    clause["source_sha256"],
                    order[side + "_start"],
                    order[side + "_end"],
                    order[side + "_sha256"],
                )
                for side in ("before", "after")
            ]
            check(
                prefix + "source_order:" + str(index),
                None
                if any(e not in order_endpoints for e in endpoints) or body is None
                else endpoints[0][1]
                < endpoints[0][2]
                <= endpoints[1][1]
                < endpoints[1][2]
                and all(
                    hashlib.sha256(body[e[1] : e[2]]).hexdigest() == e[3]
                    for e in endpoints
                ),
                "source-byte order only; unselected endpoint is unassessed",
            )
    check(
        "distinct_native_statements",
        len(native_ids) == len(expected)
        and None not in native_ids
        and len(native_ids) == len(set(native_ids)),
    )
    edges = capture.get("edges")
    check(
        "exact_typed_edge_inventory",
        None
        if edges is None or read_context is None
        else sorted(map(canonical, edges)) == sorted(map(canonical, expected_edges)),
    )
    check(
        "complete_discovery",
        None
        if capture.get("edges") is None or capture.get("native_read_status") is None
        else capture["native_read_status"] == "complete"
        and response.get("status") == "complete"
        and not response.get("gap_codes")
        and read_bundles is not None
        and {b["statement_id"] for b in read_bundles} == set(native_ids)
        and len(read_bundles) == len(native_ids),
    )
    check("no_false_absence", response.get("universal_absence_claimed") is False)
    # A read-only acquisition cannot establish that a retry was executed.
    recovery = capture.get("recovery")
    recovery_fields = {
        "schema",
        "lost_ack_error",
        "result_before_first_call",
        "packet_before",
        "packet_after",
        "original_result",
        "retry_result",
        "head_before_retry",
        "head_after_retry",
    }
    if (
        not isinstance(recovery, dict)
        or not recovery_fields.issubset(recovery)
        or not recovery.get("lost_ack_error")
        or recovery.get("original_result") is None
    ):
        check(
            "executed_original_packet_recovery",
            None,
            "requires observed lost-ack/retry and durable original receipt",
        )
    else:
        # Membership in two independent inventories is insufficient: packet B
        # and receipt A can each be genuine while describing different commits.
        same_publication = [
            row
            for row in rows
            if row["prepare"] == recovery["packet_before"]
            and row["confirm"]["result"] == recovery["original_result"]
        ]
        check(
            "executed_original_packet_recovery",
            recovery.get("schema") == "buddy_observed_lost_ack_retry_v2"
            and recovery.get("result_before_first_call") is None
            and recovery["packet_before"] == recovery["packet_after"]
            and len(same_publication) == 1
            and recovery["original_result"]["receipt"]["publication_id"]
            == native_publication_id(recovery["packet_before"]["envelope"]["payload"])
            and recovery["retry_result"].get("result") == recovery["original_result"]
            and recovery["head_before_retry"] == recovery["head_after_retry"],
        )
    counts = {
        status: sum(c["status"] == status for c in checks.values())
        for status in ("pass", "fail", "unassessed")
    }
    return {
        "schema": "buddy_source_statement_lifecycle_result_v2",
        "checks": checks,
        "counts": {**counts, "assessed": counts["pass"] + counts["fail"]},
        "identities": [
            {
                "harness_key": key,
                "harness_semantic_digest": semantic_digest(
                    harness_statement(row["payload"])
                ),
                "native_publication_id": native_publication_id(row["payload"]),
                "native_semantic_digest": native_semantic_digest(row["payload"]),
            }
            for key, row in expected.items()
        ],
        "semantic_entailment_verified": False,
        "full_system_ingestion_verified": False,
        "historical_scores_changed": False,
        "runtime_acceptance_verified": False,
    }
