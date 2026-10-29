"""Original dossier bytes and Core-owned source admission; registry selects cohort only."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re

import yaml
from dungeonmind.application.vnext import (
    EntityReadService,
    EvidenceReadService,
    SearchReadService,
    open_admitted_native_text,
    open_native_text_source_access_context,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.native_source import (
    NativeTextEvidenceSpanRequestV1,
    NativeTextSourceAdmissionV1,
    NativeTextSourceOriginV1,
)
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresNativeSourceEvidenceRepository,
)
from apps.live_control_server import config
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding,
)
from graph_memory.vnext.domain_runtime import (
    GM_LABEL,
    PLAYER_LABEL,
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_read_context,
    resolve_dungeonbuddy_descriptors,
)
from apps.live_control_server.integrations.worldkeeper.registry_standing_consumer import (
    digest,
)


def repository():
    return PostgresNativeSourceEvidenceRepository(
        PostgresDatabase(config.world_graph_authority_database_url())
    )


def descriptors(repo, space_id, revision_id):
    snapshot = repo.get_revision(space_id, revision_id)
    if snapshot is None:
        raise ValueError("Selected native World revision is missing")
    return resolve_dungeonbuddy_descriptors(
        domain_ref=snapshot.revision.domain_contract_ref,
        profile_ref=snapshot.revision.semantic_profile_ref,
    )


def binding(managed_world_id):
    return asdict(resolve_managed_world_binding(managed_world_id))


def _contained(root, relative):
    result = (root / relative).resolve(strict=True)
    if not result.is_relative_to(root.resolve()):
        raise ValueError("source path escapes managed root")
    return result


def load_sources(request, bound):
    root = config.managed_world_data_root()
    corpus = _contained(root, bound["source_root_relpath"])
    registry = _contained(corpus, "Longmont Campaign/Campaign 1/_party_registry.json")
    raw = registry.read_bytes()
    if hashlib.sha256(raw).hexdigest() != request.registry_sha256:
        raise ValueError("cohort registry bytes changed")
    data = json.loads(raw)
    if (
        data.get("schema") != "party_registry_v1"
        or data.get("campaign_id") != "longmont-c1"
    ):
        raise ValueError("unsupported cohort registry")
    slugs = data.get("session_pc_rosters", {}).get(request.roster_key, [])
    if (
        len(slugs) != 6
        or len(set(slugs)) != 6
        or set(slugs) != set(request.dossier_sha256)
    ):
        raise ValueError("expected exactly six cohort dossier hashes")
    rows = []
    for slug in sorted(slugs):
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9_]+", slug):
            raise ValueError("invalid registry subject")
        path = _contained(
            corpus,
            f"Longmont Campaign/Campaign 1/PCs/{slug}/{slug}_character_dossier.md",
        )
        body = path.read_bytes()
        sha = hashlib.sha256(body).hexdigest()
        if sha != request.dossier_sha256[slug]:
            raise ValueError("dossier bytes changed")
        text = body.decode("utf-8")
        parts = text.split("---\n", 2)
        if len(parts) != 3 or parts[0]:
            raise ValueError("dossier frontmatter required")
        meta = yaml.safe_load(parts[1])
        expected = {
            "campaign_id": "longmont-c1",
            "temporal_scope": "campaign_stateful",
            "session": None,
            "source_class": "authored_dossier",
            "subject_class": "pc",
        }
        if any(k not in meta or meta[k] != v for k, v in expected.items()):
            raise ValueError("unsupported dossier qualification")
        # This intentionally supports the exact existing dossier sentence, not general prose extraction.
        matches = list(
            re.finditer(
                r"\*\*([^*\n]+)\*\* is a core PC in Longmont Campaign 1\.", parts[2]
            )
        )
        if len(matches) != 1:
            raise ValueError("one explicit campaign PC-role sentence required")
        name = matches[0].group(1)
        if name.casefold() != slug.replace("_", " ").casefold():
            raise ValueError("dossier name does not match cohort subject")
        span = matches[0].group().encode("utf-8")
        if body.count(span) != 1:
            raise ValueError("ambiguous dossier support span")
        start = body.index(span)
        rows.append(
            {
                "slug": slug,
                "name": name,
                "path": str(path.relative_to(root)),
                "sha256": sha,
                "span_start": start,
                "span_end": start + len(span),
                "span_sha256": hashlib.sha256(span).hexdigest(),
                "span_text": span.decode(),
                "qualification": expected,
                "body_text": text,
            }
        )
    return rows


def access_context(repo, space_id):
    head = repo.get_head(space_id)
    if head is None:
        raise ValueError("native World has no head")
    domain, _ = descriptors(repo, space_id, head.head_revision_id)
    access = open_native_text_source_access_context(
        repository=repo,
        space_id=space_id,
        revision_id=head.head_revision_id,
        domain_contract=domain,
        audience_labels=(GM_LABEL, PLAYER_LABEL),
    )
    p = access.parsed
    context = {
        "space_id": space_id,
        "revision_id": p.revision_id,
        "graph_sha256": p.graph_payload_sha256,
        "source_epoch": access.source_view.epoch,
        "domain_ref": {
            "authority_id": p.domain_contract_ref.domain_id,
            "revision": p.domain_contract_ref.domain_revision,
            "descriptor_sha256": p.domain_contract_ref.descriptor_sha256,
        },
        "profile_ref": {
            "authority_id": p.semantic_profile_ref.profile_id,
            "revision": p.semantic_profile_ref.profile_revision,
            "descriptor_sha256": p.semantic_profile_ref.descriptor_sha256,
        },
    }
    return context, access


def alternatives(repo, context, access, rows):
    read = build_dungeonbuddy_read_context(
        parsed_revision=access.parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id=context["space_id"],
            scope_mode="world",
            role="gm",
            standing_selector=("established", "provisional"),
            revision_id=context["revision_id"],
        ),
        source_reader=access.source_view,
    )
    result = {}
    from fastapi.encoders import jsonable_encoder

    for row in rows:
        found = SearchReadService().search_entities(read, row["name"])
        targets = []
        for hit in found.hits:
            entity = EntityReadService().get_entity(read, hit.entity.entity_id)
            support = [
                EvidenceReadService().get_assertion_evidence(read, a.assertion_id)
                for a in entity.assertions
            ]
            targets.append(
                {
                    "entity_id": hit.entity.entity_id,
                    "entity": jsonable_encoder(entity),
                    "support": jsonable_encoder(support),
                    "supported": bool(entity.assertions)
                    and all(s.available and bool(s.evidence) for s in support),
                }
            )
        result[row["slug"]] = {
            "search": jsonable_encoder(found),
            "targets": targets,
            "search_is_advisory": True,
            "identity_approved": False,
        }
    return result


def admit_sources(repo, request, bound, rows, principal):
    parent = request.expected_parent_revision_id
    domain, profile = descriptors(repo, bound["native_world_id"], parent)
    admitted = []
    for row in rows:
        admission_id = "dmb-dossier:" + digest(
            {
                "actor": principal,
                "world": bound["native_world_id"],
                "operation": str(request.operation_id),
                "slug": row["slug"],
            }
        )
        receipt = publish_native_text_source_evidence(
            repository=repo,
            domain_contract=domain,
            semantic_profile=profile,
            request=NativeTextSourceAdmissionV1(
                space_id=bound["native_world_id"],
                admission_id=admission_id,
                expected_parent_revision_id=parent,
                created_at=request.created_at,
                body_text=row["body_text"],
                expected_body_sha256=row["sha256"],
                source_classification="dungeonbuddy.source:authored_dossier",
                authority="primary",
                visibility={"kind": "labels_any", "labels": [GM_LABEL]},
                origin=NativeTextSourceOriginV1(
                    namespace="dungeonbuddy.pc-dossier",
                    object_id=bound["managed_world_id"] + ":" + row["path"],
                    revision_id=row["sha256"],
                ),
                spans=[
                    NativeTextEvidenceSpanRequestV1(
                        client_ref=row["slug"],
                        evidence_role="support",
                        start_byte=row["span_start"],
                        end_byte=row["span_end"],
                        expected_slice_sha256=row["span_sha256"],
                    )
                ],
            ),
        )
        if len(receipt.bindings) != 1 or receipt.bindings[0].client_ref != row["slug"]:
            raise ValueError("source receipt binding mismatch")
        public = {k: v for k, v in row.items() if k != "body_text"}
        public.update(
            receipt=receipt.model_dump(mode="json"),
            evidence_ref_id=receipt.bindings[0].evidence_ref_id,
        )
        admitted.append(public)
        parent = receipt.published_revision_id
    return admitted


def verify_sources(access, rows):
    for row in rows:
        opened = open_admitted_native_text(access, row["evidence_ref_id"])
        if (
            opened.status != "available"
            or opened.body_sha256 != row["sha256"]
            or opened.span_sha256 != row["span_sha256"]
            or opened.span_start_byte != row["span_start"]
            or opened.span_end_byte != row["span_end"]
            or opened.source_artifact_id != row["receipt"]["source_artifact_id"]
            or opened.source_revision_id != row["receipt"]["source_revision_id"]
            or opened.body_text.encode()[row["span_start"] : row["span_end"]].decode()
            != row["span_text"]
        ):
            raise ValueError("admitted dossier support no longer available")
