"""Pure reviewed-intent compilation; live eligibility remains the B2 owner's job."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from dungeonmind.application.vnext.model import ParsedKnowledgeRevision
from dungeonmind.contracts.vnext.contribution import ContributionDisposition
from dungeonmind.contracts.vnext.native_source import MAX_NATIVE_TEXT_BYTES, NativeUtf8SpanProofV1
from dungeonmind.contracts.vnext.prospective_aliases import ProspectiveAliasContributionV1
from dungeonmind.contracts.vnext.source import SourceRevisionV2

from apps.live_control_server.models.native_first_world_compilation import (
    BoundFirstWorldNativeCompilation, FirstWorldCompilationError,
    FirstWorldNativeIntent, FirstWorldNativeSpanBinding,
)
from apps.live_control_server.services.native_first_world_effects import (
    FirstWorldEffectInputError, inventory_first_world_native_effects,
)
from graph_memory.source_span import (
    SourceSpanIndex, SourceSpanIndexEntry, source_span_index_to_dict,
    validate_source_span_index,
)
from graph_memory.vnext.domain_runtime import (
    DUNGEONBUDDY_DOMAIN_ID, DUNGEONBUDDY_DOMAIN_REVISION, DUNGEONBUDDY_DOMAIN_DIGEST,
    DUNGEONBUDDY_PROFILE_ID, DUNGEONBUDDY_PROFILE_DIGEST,
    DUNGEONBUDDY_CUSTOM_PROFILE_DIGEST, GM_LABEL, PLAYER_LABEL,
)

POLICY = "dmb_native_first_world_compiler_v1"
_CONTEXT = "dungeonbuddy.domain_metadata:world_context_v1"
_LOCAL = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_KINDS = frozenset({"npc", "pc", "item", "location", "party", "faction", "organization",
                    "event", "threat", "mystery", "thread", "job", "encounter"})


def _fail(code, field=""):
    raise FirstWorldCompilationError(code, field)


def _require(condition, code, field=""):
    if not condition:
        _fail(code, field)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _id(role, *parts):
    # Caller-owned correlations only. Allocated entity/assertion IDs remain opaque.
    return "dmb-first-world:" + role + ":" + _sha(_json(list(parts)))


def _predicate(raw):
    fixed = {"located_in": "dnd5e:located_in", "dnd5e:located_in": "dnd5e:located_in",
             "allied_with": "dungeonbuddy:allied_with", "dungeonbuddy:allied_with": "dungeonbuddy:allied_with"}
    if raw in fixed:
        return fixed[raw], False
    _require(type(raw) is str and _LOCAL.fullmatch(raw), "unsupported_predicate")
    return "dungeonbuddy.custom:" + raw, True


def _span_requirements(effect, source_text, span_index, world_id):
    _require(type(source_text) is str, "invalid_source_text")
    try:
        body = source_text.encode("utf-8")
    except UnicodeError as exc:
        raise FirstWorldCompilationError("invalid_source_text") from exc
    _require(0 < len(body) <= MAX_NATIVE_TEXT_BYTES, "source_size_limit")
    digest = hashlib.sha256(body).hexdigest()
    meta = effect["contribution_meta"]
    artifact = meta["source_artifact_id"]
    _require(meta["source_revision_id"] == "sha256:" + digest, "source_revision_mismatch")
    _require(meta["campaign_scope"] == world_id, "world_scope_mismatch")
    _require(isinstance(span_index, SourceSpanIndex), "invalid_span_index")
    _require(type(span_index.spans) is tuple and all(isinstance(s, SourceSpanIndexEntry)
             and type(s.start_line) is int and type(s.end_line) is int for s in span_index.spans), "invalid_span_index")
    try:
        validate_source_span_index(span_index, source_artifact_id=artifact, content_sha256=digest)
    except (ValueError, TypeError) as exc:
        raise FirstWorldCompilationError("invalid_span_index") from exc
    by_span = {s.source_span_id: s for s in span_index.spans}
    _require(len(by_span) == len(span_index.spans), "duplicate_source_span")
    lines, retained = source_text.splitlines(), source_text.splitlines(keepends=True)
    offsets = [0]
    for line in retained:
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    for span in span_index.spans:
        _require(type(span.start_line) is int and type(span.end_line) is int
                 and 1 <= span.start_line <= span.end_line <= len(lines), "span_out_of_bounds")
    requirements = {}
    for row in effect["accepted_proposals"]:
        _require(row["source_artifact_id"] == artifact and row["source_revision_id"] == "sha256:" + digest,
                 "assertion_source_mismatch")
        value = row["value"]
        _require(value.get("source_domains") == ["worldbuilding"], "unsupported_source_domain")
        artifacts = value.get("source_artifacts")
        _require(type(artifacts) is list and len(artifacts) == 1, "source_artifact_inventory")
        raw_artifact = artifacts[0]
        expected_artifact = {"source_artifact_id": artifact, "source_domain": "worldbuilding",
                             "content_sha256": digest, "campaign_id": world_id}
        _require(all(raw_artifact.get(k) == v for k, v in expected_artifact.items())
                 and raw_artifact.get("session_id") is None, "source_artifact_mismatch")
        evidence = value.get("evidence")
        _require(type(evidence) is list and evidence, "missing_reviewed_evidence")
        _require(all(type(ref) is dict and all(type(ref.get(k)) is str and bool(ref[k].strip())
                 for k in ("evidence_ref_id", "source_span_ref_id", "source_ref_id", "source_artifact_id"))
                 for ref in evidence), "invalid_reviewed_evidence")
        refs = [ref.get("evidence_ref_id") for ref in evidence]
        _require(refs == row["evidence_ref_ids"] and len(refs) == len(set(refs)), "evidence_inventory_mismatch")
        for ref in evidence:
            span = by_span.get(ref.get("source_span_ref_id"))
            _require(span is not None, "unknown_reviewed_span")
            _require(ref.get("source_artifact_id") == artifact
                     and ref.get("source_domain") == "worldbuilding"
                     and ref.get("source_ref_id") == span.source_ref_id
                     and ref.get("locator") == span.source_span_id,
                     "reviewed_span_identity_mismatch")
            start = offsets[span.start_line - 1]
            end = offsets[span.end_line - 1] + len(lines[span.end_line - 1].encode("utf-8"))
            expected = {"reviewed_evidence_ref_id": ref["evidence_ref_id"],
                        "source_artifact_id": artifact, "source_revision_id": "sha256:" + digest,
                        "source_span_ref_id": span.source_span_id, "start_byte": start,
                        "end_byte": end, "slice_sha256": hashlib.sha256(body[start:end]).hexdigest()}
            optional = {"source_revision_id": "sha256:" + digest,
                        "source_content_sha256": digest, "span_content_sha256": expected["slice_sha256"],
                        "span_index_sha256": _sha(_json(source_span_index_to_dict(span_index))),
                        "campaign_id": world_id, "session_id": None,
                        "can_open_source": True, "can_highlight_span": True, "evidence_role": "support"}
            _require(all(k not in ref or ref[k] == v for k, v in optional.items()), "reviewed_evidence_metadata_mismatch")
            _require(start < end, "empty_reviewed_span")
            prior = requirements.get(ref["evidence_ref_id"])
            _require(prior is None or prior == expected, "ambiguous_reviewed_evidence")
            requirements[ref["evidence_ref_id"]] = expected
    return digest, [requirements[k] for k in sorted(requirements)]


def compile_first_world_native_intent(effect, *, world_id, source_text, span_index):
    """Compile exact reviewed effects without source admission or executable placeholders."""
    _require(type(world_id) is str and bool(world_id.strip()), "invalid_world_id")
    try:
        inventory = inventory_first_world_native_effects(effect)
    except (FirstWorldEffectInputError, ValueError, TypeError, KeyError) as exc:
        raise FirstWorldCompilationError("invalid_reviewed_effect") from exc
    if inventory.status == "unsupported":
        for blocker in inventory.blockers:
            if blocker.code in {"unsupported_effect_field", "unsupported_graph_effect", "existing_identity_unsupported", "identity_effect_unsupported"}:
                _fail(blocker.code, blocker.field_path)
    effect = inventory.inventory.reviewed_effect
    _require(not effect["deferred_candidate_ids"] and not effect["unresolved_mentions"], "unsupported_deferred_identity")
    decisions_by_candidate = {choice["assertion_id"]: choice for choice in effect["decision_snapshot"]}
    _require(len(decisions_by_candidate) == len(effect["decision_snapshot"]), "duplicate_reviewed_decision")
    for choice in effect["decision_snapshot"]:
        expected = {"node": {"create_new", "reject"}, "edge": {"accept", "reject"}}
        _require(choice["candidate_kind"] in expected
                 and choice["decision"] in expected[choice["candidate_kind"]]
                 and choice.get("target_node_id") is None, "unsupported_decision")
    digest, requirements = _span_requirements(effect, source_text, span_index, world_id)
    nodes, edges = [], []
    owner_by_assertion = {identifier: candidate for candidate, identifiers in effect["candidate_effect_map"].items() for identifier in identifiers}
    custom = False
    for row in effect["accepted_proposals"]:
        owner = owner_by_assertion[row["assertion_id"]]
        choice = decisions_by_candidate[owner]
        _require(choice["candidate_kind"] == row["assertion_kind"]
                 and choice["decision"] == ("create_new" if row["assertion_kind"] == "node" else "accept"),
                 "assertion_owner_decision_mismatch", row["assertion_id"])
        value = row["value"]
        _require(row["campaign_scope"] == world_id and row["temporal_scope"] is None
                 and row["epistemic_kind"] == "source_derived_candidate"
                 and row["visibility"] in {"gm", "internal", "player"}
                 and value.get("canon_state") == "canonical" and value.get("approval_state") == "accepted",
                 "unsupported_assertion_metadata", row["assertion_id"])
        _require(type(row["label"]) is str and bool(row["label"].strip()), "invalid_label")
        native = {"assertion_id": row["assertion_id"], "subject": row["subject_node_id"],
                  "evidence_ref_ids": row["evidence_ref_ids"],
                  "visibility_label": PLAYER_LABEL if row["visibility"] == "player" else GM_LABEL}
        if row["assertion_kind"] == "node":
            _require(owner in effect["node_id_map"] and type(row["subject_node_id"]) is str
                     and bool(row["subject_node_id"].strip())
                     and row["subject_node_id"] == effect["node_id_map"][owner],
                     "node_subject_candidate_mismatch", row["assertion_id"])
            kind = value.get("kind")
            _require(type(kind) is str and kind in _KINDS and value.get("role") == kind and row["target_node_id"] is None
                     and row["predicate"] is None and row["identity_resolution_outcome"] == "created_new",
                     "unsupported_node_effect")
            classification = ("dnd5e:" if kind in {"npc", "location"} else "dungeonbuddy:") + kind
            _require(("dm_kind" not in value or value["dm_kind"] == classification)
                     and ("label" not in value or value["label"] == row["label"]), "conflicting_node_operands")
            aliases, seen = [], set()
            _require(type(value.get("aliases")) is list, "invalid_aliases")
            for alias in value["aliases"] or [row["label"]]:
                _require(type(alias) is str, "invalid_aliases")
                if alias.strip() and alias.casefold() not in seen:
                    seen.add(alias.casefold())
                    aliases.append(alias)
            _require(aliases, "invalid_aliases")
            summary = value.get("summary")
            _require(summary is None or type(summary) is str and bool(summary.strip()), "invalid_summary")
            native.update(label=row["label"], classification=classification,
                          aliases=aliases, summary=summary)
            nodes.append(native)
        else:
            _require(row["identity_resolution_outcome"] == "accepted_by_operator"
                     and value.get("direction") == "outbound" and value.get("predicate") == row["predicate"],
                     "unsupported_edge_effect")
            predicate, needs_custom = _predicate(row["predicate"])
            _require(value.get("edge_id") == f"edge:{row['subject_node_id']}:{row['predicate']}:{row['target_node_id']}"
                     and value.get("extract_edge_id") == owner_by_assertion[row["assertion_id"]]
                     and ("dm_predicate" not in value or value["dm_predicate"] == predicate), "conflicting_edge_operands")
            custom |= needs_custom
            native.update(target=row["target_node_id"], predicate=predicate)
            edges.append(native)
    subjects = [n["subject"] for n in nodes]
    _require(len(subjects) == len(set(subjects)), "duplicate_node_identity")
    _require(all(e["subject"] in subjects and e["target"] in subjects for e in edges), "edge_endpoint_not_created")
    audit = {"policy": POLICY, "world_id": world_id, "reviewed_effect": effect,
             "effect_sha256": inventory.inventory.effect_sha256,
             "source_text": source_text, "source_body_sha256": digest,
             "source_span_index": source_span_index_to_dict(span_index),
             "source_span_index_sha256": _sha(_json(source_span_index_to_dict(span_index))),
             "source_requirements": requirements, "nodes": nodes, "edges": edges,
             "required_profile_revision": "2" if custom else "1"}
    wire = _json(audit)
    return FirstWorldNativeIntent(wire, _sha(wire))


def _revalidate_intent(intent):
    _require(isinstance(intent, FirstWorldNativeIntent), "invalid_native_intent")
    try:
        audit = intent.audit
        index = audit["source_span_index"]
        index = SourceSpanIndex(**{**index, "spans": tuple(SourceSpanIndexEntry(**s) for s in index["spans"])})
        rebuilt = compile_first_world_native_intent(audit["reviewed_effect"], world_id=audit["world_id"],
                                                   source_text=audit["source_text"], span_index=index)
    except (KeyError, TypeError, ValueError) as exc:
        raise FirstWorldCompilationError("invalid_native_intent") from exc
    _require(rebuilt == intent, "native_intent_commitment_mismatch")
    return audit


def bind_first_world_native_intent(intent, *, parent, native_space_id, bindings, produced_at):
    """Bind immutable source proofs, not live admission or initialization authority."""
    audit = _revalidate_intent(intent)
    _require(audit["nodes"], "non_publishing_intent")
    _require(isinstance(parent, ParsedKnowledgeRevision) and parent.space_id == native_space_id
             and type(native_space_id) is str and bool(native_space_id.strip()), "native_space_mismatch")
    _require(not parent.entities_by_id and not parent.assertions_by_id and not parent.aliases_by_id
             and parent.migration_origin_ref is None, "parent_not_source_only")
    domain, profile = parent.domain_contract_ref, parent.semantic_profile_ref
    _require((domain.domain_id, domain.domain_revision, domain.descriptor_sha256) ==
             (DUNGEONBUDDY_DOMAIN_ID, DUNGEONBUDDY_DOMAIN_REVISION, DUNGEONBUDDY_DOMAIN_DIGEST), "descriptor_drift")
    _require(profile.profile_id == DUNGEONBUDDY_PROFILE_ID and
             (profile.profile_revision, profile.descriptor_sha256) in
             {("1", DUNGEONBUDDY_PROFILE_DIGEST), ("2", DUNGEONBUDDY_CUSTOM_PROFILE_DIGEST)}, "descriptor_drift")
    _require(audit["required_profile_revision"] != "2" or profile.profile_revision == "2", "profile_transition_required")
    _require(isinstance(produced_at, datetime) and produced_at.utcoffset() is not None, "invalid_produced_at")
    expected = {r["reviewed_evidence_ref_id"]: r for r in audit["source_requirements"]}
    resolved, proofs, owners, source_pairs, source_records = {}, {}, {}, set(), {}
    for binding in bindings:
        _require(isinstance(binding, FirstWorldNativeSpanBinding), "invalid_native_binding")
        ref = binding.reviewed_evidence_ref_id
        _require(type(ref) is str, "invalid_reviewed_evidence_ref")
        _require(ref in expected and ref not in resolved, "binding_inventory_mismatch")
        try:
            proof = NativeUtf8SpanProofV1.model_validate_json(binding.proof_json)
            source_revision = SourceRevisionV2.model_validate_json(binding.source_revision_json)
        except ValueError as exc:
            raise FirstWorldCompilationError("invalid_native_proof") from exc
        req = expected[ref]
        _require((proof.start_byte, proof.end_byte, proof.slice_sha256) ==
                 (req["start_byte"], req["end_byte"], req["slice_sha256"]), "native_proof_interval_mismatch")
        evidence = parent.evidence_by_id.get(proof.evidence_ref_id)
        _require(evidence is not None and evidence.source_revision_id == proof.source_revision_id
                 and evidence.source_span_ref_id == proof.span_id and evidence.can_open_source
                 and evidence.can_highlight_span and evidence.evidence_role == "support", "native_evidence_mismatch")
        _require(source_revision.source_artifact_id == evidence.source_artifact_id
                 and source_revision.source_revision_id == proof.source_revision_id
                 and source_revision.content_sha256 == audit["source_body_sha256"]
                 and source_revision.body_storage == "dm_native_utf8_body_v1", "native_source_revision_mismatch")
        # Multiple raw references may share one native ID only for the exact same
        # proof and source interval. Different raw IDs are not themselves ambiguity.
        identity = (evidence.source_artifact_id, proof.source_revision_id, proof.start_byte,
                    proof.end_byte, proof.slice_sha256)
        prior = owners.get(proof.evidence_ref_id)
        _require(prior is None or prior == (identity, proof.model_dump_json()), "conflicting_native_proofs")
        owners[proof.evidence_ref_id] = (identity, proof.model_dump_json())
        source_key = (evidence.source_artifact_id, proof.source_revision_id)
        source_record = source_revision.model_dump_json()
        _require(source_key not in source_records or source_records[source_key] == source_record, "conflicting_native_source_revision")
        source_records[source_key] = source_record
        source_pairs.add(source_key)
        resolved[ref] = proof.evidence_ref_id
        proofs[ref] = {"proof": proof.model_dump(mode="json"),
                       "source_revision": source_revision.model_dump(mode="json")}
    _require(set(resolved) == set(expected) and len(source_pairs) == 1, "binding_inventory_mismatch")
    source_artifact, _source_revision = next(iter(source_pairs))
    items, aliases = [], []
    def entity_ref(subject):
        return {"kind": "result_of", "client_op_id": _id("entity-op", intent.sha256, subject)}
    def refs(row):
        return list(dict.fromkeys(resolved[r] for r in row["evidence_ref_ids"]))
    def metadata(row):
        return {"scope": [], "visibility": {"kind": "labels_all", "labels": [row["visibility_label"]]},
                "epistemic_basis": "inferred", "claim_mode": "dungeonbuddy.claim:fact",
                "standing": "established", "evidence_ref_ids": refs(row), "temporal_scope": {"kind": "unknown"},
                "domain_metadata": [{"schema": _CONTEXT, "payload": {"compiler_policy": POLICY,
                   "reviewed_effect_sha256": audit["effect_sha256"], "reviewed_assertion_id": row["assertion_id"]}}]}
    def assertion(row, role, predicate, value):
        token = _id("assertion-op", intent.sha256, row["assertion_id"], role)
        items.append({"kind": "create_assertion", "item_id": _id("item", token), "client_op_id": token,
                      "subject": entity_ref(row["subject"]), "predicate": predicate, "value": value,
                      "metadata": metadata(row)})
    for node in audit["nodes"]:
        op = entity_ref(node["subject"])["client_op_id"]
        items.append({"kind": "create_entity", "item_id": _id("item", op), "client_op_id": op})
        assertion(node, "name", "dnd5e:name", {"kind": "literal", "value": node["label"]})
        assertion(node, "classification", "dnd5e:classification", {"kind": "term_ref", "term": node["classification"]})
        if node["summary"] is not None:
            assertion(node, "summary", "dnd5e:summary", {"kind": "literal", "value": node["summary"]})
        for ordinal, alias in enumerate(node["aliases"]):
            aid = _id("alias", intent.sha256, node["subject"], ordinal, alias)
            aliases.append({"kind": "create_alias", "item_id": _id("alias-item", aid), "alias_id": aid,
                            "entity": entity_ref(node["subject"]), "alias_text": alias,
                            "evidence_ref_ids": refs(node), "standing": "established"})
    for edge in audit["edges"]:
        assertion(edge, "relationship", edge["predicate"], {"kind": "entity_ref", "entity": entity_ref(edge["target"])})
    # Diagnostics are a real, validated DomainMetadataEntry in the frozen public
    # contribution and therefore part of Core's complete prospective request hash.
    commitment = {"compiler_policy": POLICY, "intent_sha256": intent.sha256,
                  "reviewed_effect_sha256": audit["effect_sha256"], "reviewed_effect": audit["reviewed_effect"],
                  "source_span_index_sha256": audit["source_span_index_sha256"],
                  "source_body_sha256": audit["source_body_sha256"], "bindings": proofs,
                  "parent_revision_id": parent.revision_id, "parent_semantic_digest": parent.semantic_digest}
    request = ProspectiveAliasContributionV1.model_validate({"contribution": {
        "contribution_id": _id("contribution", intent.sha256), "space_id": native_space_id,
        "producer": POLICY, "produced_at": produced_at, "source_refs": [source_artifact],
        "status": "finalized", "items": items, "diagnostics": [{"schema": _CONTEXT, "payload": commitment}]},
        "aliases": aliases})
    item_ids = [i.item_id for i in request.contribution.items] + [a.item_id for a in request.aliases]
    operations = [i.client_op_id for i in request.contribution.items]
    _require(len(operations) == len(set(operations)), "operation_id_collision")
    decisions = [ContributionDisposition(item_id=i, disposition="accepted") for i in item_ids]
    wire = _json(request.model_dump(mode="json"))
    dispositions = _json([d.model_dump(mode="json") for d in decisions])
    return BoundFirstWorldNativeCompilation(intent.sha256, wire, dispositions,
              _sha(_json({"request": json.loads(wire), "dispositions": json.loads(dispositions)})),
              parent.revision_id, parent.semantic_digest)
