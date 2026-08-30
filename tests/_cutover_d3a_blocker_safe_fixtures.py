"""Blocker-safe D.3A fixture helpers (no graph_memory.kernel/world/union import).


Imported only after the legacy import blocker is armed in the owning witness.
"""


from __future__ import annotations


import hashlib
import json
from dataclasses import replace
from pathlib import Path


from apps.live_control_server.ports.world_graph_authority import (
    AuthorityEvidenceRef,
    AuthorityObject,
    AuthorityRelationship,
    WorldGraphAuthorityError,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
    WorldGraphRevisionView,
    WorldGraphVerificationResult,
)
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
)
from graph_memory.extract_promote_ops import DEFAULT_WORLD_ID
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    mutation_context_with_sealed_identity,
)


CAMPAIGN_ID = "longmont-c2"
SESSION_ID = "session-22"
GLASS_ORCHARD_WORLD_ID = "the-glass-orchard"
WORLD_ID = GLASS_ORCHARD_WORLD_ID
FIRST_WORLD_PREPARE_URL = "/api/live/extract-promote/worldbuilding/first-world/prepare"
FIRST_WORLD_CONFIRM_URL = "/api/live/extract-promote/worldbuilding/first-world/confirm"
PREPARE_URL = "/api/live/graph-authoring/prepare"
COMMIT_URL = "/api/live/graph-authoring/commit"
REVIEWED_OBJECT_ID = "d2c4-reviewed-object"
EXISTING_NODE_ID = "obj_session22_vial"
REJECTED_NODE_ID = "obj_rejected_extra"


TEST_DSN_ENV = "DMB_CUTOVER_TEST_DATABASE_URL"
TRUNCATE_SQL = """
TRUNCATE TABLE
    dungeonmind.semantic_documents,
    dungeonmind.active_embedding_runs,
    dungeonmind.embedding_runs,
    dungeonmind.mind_turns,
    dungeonmind.mind_threads,
    dungeonmind.retrieval_sessions,
    dungeonmind.finalized_review_publications,
    dungeonmind.contribution_reviews,
    dungeonmind.identity_decisions,
    dungeonmind.graph_contributions,
    dungeonmind.evidence_refs,
    dungeonmind.source_revisions,
    dungeonmind.source_artifacts,
    dungeonmind.existing_world_adoptions,
    dungeonmind.reviewed_world_initializations,
    dungeonmind.world_graph_head_events,
    dungeonmind.world_graph_heads,
    dungeonmind.graph_revisions,
    dungeonmind.campaigns,
    dungeonmind.worlds
RESTART IDENTITY CASCADE
"""


def require_test_dsn() -> str:
    import os


    dsn = os.environ.get(TEST_DSN_ENV, "").strip()
    if not dsn:
        raise AssertionError(f"{TEST_DSN_ENV} must be set for D.3A PG witness (zero required skips)")
    db_name = dsn.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name:
        raise AssertionError(
            f"{TEST_DSN_ENV} database name {db_name!r} must contain 'test'"
        )
    return dsn


def ensure_migrated(dsn: str) -> None:
    import psycopg


    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'dungeonmind' AND table_name = 'worlds'"
        ).fetchone()
        init_row = conn.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'dungeonmind' "
            "AND table_name = 'reviewed_world_initializations'"
        ).fetchone()
    if row is None or init_row is None:
        raise AssertionError("dmb_cutover_test is not migrated (worlds / reviewed_world_initializations missing)")


def truncate_dungeonmind(dsn: str) -> None:
    from dungeonmind.infrastructure.postgres import PostgresDatabase


    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()


def register_glass_orchard(repo: Path):
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )


    return create_world_container(repo, name="The Glass Orchard")


def first_world_decisions(
    *,
    vial: str = "create_new",
    puddles: str = "create_new",
    edge: str = "accept",
) -> list[dict[str, str]]:
    return [
        {"assertionId": "obj_session22_vial", "decision": vial},
        {"assertionId": "mystery_puddles", "decision": puddles},
        {"assertionId": "e33", "decision": edge},
    ]


def first_world_prepare_body(run_id: str, decisions: list[dict[str, str]]) -> dict:
    return {
        "schema": "dmb_first_world_graph_prepare_request_v1",
        "runId": run_id,
        "decisions": decisions,
    }


def first_world_confirm_body(plan: dict) -> dict:
    return {
        "schema": "dmb_first_world_graph_confirm_request_v1",
        "plan": plan,
    }


def write_glass_orchard_bld08_run(repo: Path) -> tuple[str, Path]:
    register_glass_orchard(repo)
    return _write_bld08_reviewable_run(
        repo,
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        world_id=GLASS_ORCHARD_WORLD_ID,
    )


def object_proposal() -> dict[str, object]:
    return {
        "localProposalId": REVIEWED_OBJECT_ID,
        "proposalKind": "object",
        "status": "staged_local",
        "objectRef": {
            "label": "D2C4 Reviewed Object",
            "kind": "party",
            "aliases": ["reviewed object"],
            "summary": "Graph Review authored object",
        },
        "visibility": {"visibility": "gm_private", "revealState": "unrevealed"},
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": {
            "origin": "human_authored",
            "authoringSurface": "memory_ingest_graph_authoring",
        },
    }


def authoring_body(run_id: str, proposals: list[dict[str, object]], **extra) -> dict[str, object]:
    payload: dict[str, object] = {
        "campaignId": GLASS_ORCHARD_WORLD_ID,
        "campaignRel": "The Glass Orchard",
        "worldId": GLASS_ORCHARD_WORLD_ID,
        "sessionId": "session-d2c4",
        "sourceRunId": run_id,
        "proposals": proposals,
    }
    payload.update(extra)
    return payload


def write_post_genesis_graph_review_run(repo: Path) -> str:
    """Distinct Buddy ingest run for Graph Review after genesis."""
    from apps.live_control_server.services.graph_run_registry import (
        create_extraction_run,
        update_extraction_run_status,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
        source_span_index_relpath,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE,
    )


    (repo / f"corpus/{GLASS_ORCHARD_WORLD_ID}-markdown").mkdir(parents=True, exist_ok=True)
    document = create_workspace_document(
        repo,
        title="D2C4 Graph Review source",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        world_id=GLASS_ORCHARD_WORLD_ID,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        repo, document.document_id, expected_revision=document.revision
    )
    source = repo / committed.target_relpath
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "# D2C4 Graph Review\n\nPost-genesis source for manual authoring.\n",
        encoding="utf-8",
    )
    artifact = create_source_artifact_from_workspace_document(
        repo, document_id=committed.document_id, expected_revision=committed.revision
    )
    span_rel = source_span_index_relpath(artifact.source_artifact_id)
    span_path = repo / span_rel
    span_index = json.loads(span_path.read_text(encoding="utf-8"))
    span_ref_id = str(span_index["spans"][0]["source_span_id"])
    run_dir = repo / "out" / "graph_memory" / "runs" / "extraction" / "d2c4"
    run_dir.mkdir(parents=True, exist_ok=True)
    candidate_payload = _candidate_graph_payload(
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        session_id="",
    )
    candidate_payload["session_id"] = None
    candidate_payload["source_artifact_ids"] = [artifact.source_artifact_id]
    worldbuilding_semantic = dict(WORLDBUILDING_PLUMBING_PROFILE.default_semantic_state)
    for holder in (
        *(candidate_payload.get("nodes") or []),
        *(candidate_payload.get("edges") or []),
    ):
        holder["semantic_state"] = dict(worldbuilding_semantic)
        for ref in holder.get("evidence_refs") or []:
            ref["source_artifact_id"] = artifact.source_artifact_id
            ref["source_span_ref_id"] = span_ref_id
            ref["anchor_quotes"] = ["Post-genesis source for manual authoring."]
    candidate_path = run_dir / "candidate_graph.json"
    candidate_path.write_text(json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8")


    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact.uri,
            sha256=artifact.content_sha256,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=f"repo://{span_rel}",
            sha256=_digest(span_path),
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=f"repo://{candidate_path.relative_to(repo).as_posix()}",
            sha256=_digest(candidate_path),
        ),
    }
    run = create_extraction_run(
        repo,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        session_id=None,
        profile_id="worldbuilding_plumbing_v0@0.1",
    )
    for step in (
        ExtractionRunStatus.PREPARED,
        ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED,
        ExtractionRunStatus.REVIEWABLE,
    ):
        run = update_extraction_run_status(
            repo,
            run.run_id,
            status=step,
            expected_revision=run.revision,
            components=components if step == ExtractionRunStatus.PREPARED else None,
        )
    return run.run_id


def _contribution_fingerprint(contribution: object) -> str:
    if contribution is None:
        return ""
    if isinstance(contribution, dict):
        return repr(sorted(contribution.items()))
    parts = [str(getattr(contribution, "contribution_id", "") or "")]
    for item in list(getattr(contribution, "accepted_assertions", None) or []):
        if isinstance(item, dict):
            parts.append(repr(sorted(item.items())))
            continue
        parts.append(
            "|".join(
                str(getattr(item, key, "") or "")
                for key in (
                    "assertion_id",
                    "assertion_kind",
                    "predicate",
                    "subject_node_id",
                    "target_node_id",
                )
            )
        )
    return "\n".join(parts)


class FakeWorldGraphAuthority:
    def __init__(self) -> None:
        self.heads: dict[str, str] = {}
        self.revisions: dict[tuple[str, str], WorldGraphRevisionView] = {}
        self.publications: dict[tuple[str, str], WorldGraphPublicationReceipt] = {}
        self._bindings: dict[tuple[str, str], tuple[str, str]] = {}
        self.identity: dict[str, dict[str, object]] = {}
        self.publish_calls = 0
        self.unavailable = False


    def current_head(self, world_id: str) -> WorldGraphHead:
        if self.unavailable:
            raise WorldGraphAuthorityError("authority down", code="authority_unavailable")
        revision_id = self.heads.get(world_id)
        if not revision_id:
            raise WorldGraphAuthorityError("no head", code="revision_unavailable")
        return WorldGraphHead(world_id=world_id, revision_id=revision_id)


    def read_revision(self, world_id: str, revision_id: str) -> WorldGraphRevisionView:
        if self.unavailable:
            raise WorldGraphAuthorityError("authority down", code="authority_unavailable")
        view = self.revisions.get((world_id, revision_id))
        if view is None:
            raise WorldGraphAuthorityError("missing revision", code="revision_unavailable")
        return view


    def mutation_context(
        self,
        world_id: str,
        revision_id: str,
        *,
        sealed_identity_snapshot=None,
    ) -> WorldGraphMutationContext:
        view = self.read_revision(world_id, revision_id)
        objects = {
            object_id: MutationObject(
                object_id=obj.object_id,
                label=obj.label,
                kind=obj.kind,
                aliases=obj.aliases,
                canon_state="canonical",
                memory_state="graph_read_model",
            )
            for object_id, obj in view.objects.items()
        }
        head_id = self.heads.get(world_id, revision_id)
        base = WorldGraphMutationContext(
            world_id=world_id,
            revision_id=revision_id,
            head_revision_id=head_id,
            objects=objects,
        )
        if sealed_identity_snapshot is not None:
            from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
                _identity_decision_prefix_key,
            )
            live_decisions = [
                dict(item)
                for item in list((self.identity.get(world_id) or {}).get("decisions") or [])
                if isinstance(item, dict)
            ]
            sealed_decisions = [
                dict(item)
                for item in list(sealed_identity_snapshot.get("decisions") or [])
                if isinstance(item, dict)
            ]
            if len(sealed_decisions) > len(live_decisions):
                raise WorldGraphAuthorityError(
                    "sealed identity snapshot invents decisions absent from the ledger",
                    code="inexpressible",
                )
            for index, sealed in enumerate(sealed_decisions):
                if _identity_decision_prefix_key(sealed) != _identity_decision_prefix_key(
                    live_decisions[index]
                ):
                    raise WorldGraphAuthorityError(
                        "sealed identity snapshot is not the prepare-time ledger prefix",
                        code="inexpressible",
                    )
            return mutation_context_with_sealed_identity(base, sealed_identity_snapshot)
        live = dict(self.identity.get(world_id) or {})
        redirects = {
            str(source): str(target)
            for source, target in dict(live.get("identity_redirects") or {}).items()
        }
        alias_owners = {
            str(alias): tuple(str(owner) for owner in list(owners))
            for alias, owners in dict(live.get("alias_owners") or {}).items()
        }
        ledger = tuple(dict(item) for item in list(live.get("decisions") or []))
        return WorldGraphMutationContext(
            world_id=world_id,
            revision_id=revision_id,
            head_revision_id=head_id,
            objects=objects,
            alias_owners=alias_owners,
            identity_redirects=redirects,
            identity_ledger_records=ledger,
        )


    def publish(self, request: WorldGraphPublishRequest) -> WorldGraphPublicationReceipt:
        self.publish_calls += 1
        key = (request.world_id, request.authority_operation_id)
        existing = self.publications.get(key)
        if existing is not None:
            stored_parent, stored_fp = self._bindings.get(key, (existing.parent_revision_id, ""))
            request_fp = _contribution_fingerprint(request.contribution)
            if stored_parent != request.expected_parent_revision_id or (
                stored_fp and stored_fp != request_fp
            ):
                raise WorldGraphAuthorityError(
                    "existing publication does not match the current request",
                    code="integrity_failure",
                )
            return replace(existing, outcome="already_applied")
        head = self.current_head(request.world_id)
        if head.revision_id != request.expected_parent_revision_id:
            raise WorldGraphAuthorityError("stale parent", code="stale_parent")
        child = f"rev:child-{self.publish_calls}"
        fingerprint = _contribution_fingerprint(request.contribution)
        receipt = WorldGraphPublicationReceipt(
            world_id=request.world_id,
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=request.expected_parent_revision_id,
            published_revision_id=child,
            reviewed_contribution_id=request.authority_operation_id,
            accepted_assertion_ids=request.accepted_assertion_ids,
            published=True,
            outcome="published",
            reviewed_contribution_sha256=hashlib.sha256(
                fingerprint.encode("utf-8")
            ).hexdigest(),
        )
        self.publications[key] = receipt
        self._bindings[key] = (
            request.expected_parent_revision_id,
            _contribution_fingerprint(request.contribution),
        )
        self.heads[request.world_id] = child
        parent_view = self.revisions.get(
            (request.world_id, request.expected_parent_revision_id)
        )
        objects = dict(parent_view.objects) if parent_view is not None else {}
        relationships = dict(parent_view.relationships) if parent_view else {}
        evidence_refs = dict(parent_view.evidence_refs) if parent_view else {}
        contribution_id = str(
            getattr(request.contribution, "contribution_id", "") or receipt.reviewed_contribution_id
        )
        for assertion in list(getattr(request.contribution, "accepted_assertions", None) or []):
            kind = str(getattr(assertion, "assertion_kind", "") or "")
            subject = str(getattr(assertion, "subject_node_id", "") or "")
            target = str(getattr(assertion, "target_node_id", "") or "")
            predicate = str(getattr(assertion, "predicate", "") or "")
            assertion_id = str(getattr(assertion, "assertion_id", "") or "")
            value = getattr(assertion, "value", None) or {}
            if not isinstance(value, dict):
                value = dict(getattr(value, "__dict__", {}) or {})
            if kind == "node" and subject:
                objects[subject] = AuthorityObject(
                    object_id=subject,
                    label=str(value.get("label") or subject),
                    kind=str(value.get("kind") or "object"),
                )
            elif kind == "attribute" and subject:
                existing = objects.get(subject)
                if existing is None:
                    continue
                evidence_ids = [
                    str(item).strip()
                    for item in list(getattr(assertion, "evidence_ref_ids", None) or [])
                    if str(item).strip()
                ]
                if not evidence_ids:
                    evidence_ids = [
                        f"evidence:{receipt.reviewed_contribution_id}:{subject}"
                    ]
                for evidence_id in evidence_ids:
                    evidence_refs[evidence_id] = AuthorityEvidenceRef(
                        evidence_ref_id=evidence_id,
                        evidence_role="support",
                        locator=f"contribution/{contribution_id}/{subject}",
                    )
            elif kind == "alias" and subject:
                existing = objects.get(subject)
                if existing is None:
                    continue
                alias = str(value.get("alias") or getattr(assertion, "label", "") or "")
                aliases = list(existing.aliases)
                if alias and alias not in aliases:
                    aliases.append(alias)
                objects[subject] = replace(existing, aliases=tuple(aliases))
            elif kind == "edge" and subject and target:
                rel_id = assertion_id or f"rel:{subject}:{predicate}:{target}"
                relationships[rel_id] = AuthorityRelationship(
                    relationship_id=rel_id,
                    subject_object_id=subject,
                    target_object_id=target,
                    predicate=predicate,
                )
        self.revisions[(request.world_id, child)] = WorldGraphRevisionView(
            world_id=request.world_id,
            revision_id=child,
            parent_revision_id=request.expected_parent_revision_id,
            objects=objects,
            relationships=relationships,
            evidence_refs=evidence_refs,
        )
        return receipt


    def recover(
        self,
        world_id: str,
        authority_operation_id: str,
        *,
        expected_parent_revision_id: str | None = None,
        contribution: object | None = None,
        actor: str | None = None,
        operation_namespace: str = "threat",
    ) -> WorldGraphPublicationReceipt | None:
        del actor, operation_namespace
        existing = self.publications.get((world_id, authority_operation_id))
        if existing is None:
            return None
        stored_parent, stored_fp = self._bindings.get(
            (world_id, authority_operation_id),
            (existing.parent_revision_id, ""),
        )
        if (
            expected_parent_revision_id is not None
            and stored_parent != expected_parent_revision_id
        ):
            raise WorldGraphAuthorityError(
                "recovered publication parent does not match the durable request",
                code="integrity_failure",
            )
        if contribution is not None and stored_fp:
            if stored_fp != _contribution_fingerprint(contribution):
                raise WorldGraphAuthorityError(
                    "recovered publication contribution does not match the durable request",
                    code="integrity_failure",
                )
        return existing


    def verify_child(self, *, receipt, expected) -> WorldGraphVerificationResult:
        del expected
        self.read_revision(receipt.world_id, receipt.published_revision_id)
        return WorldGraphVerificationResult(status="passed")


def _empty_parent(world_id: str = DEFAULT_WORLD_ID, revision_id: str = "rev:d-a") -> WorldGraphRevisionView:
    return WorldGraphRevisionView(
        world_id=world_id,
        revision_id=revision_id,
        parent_revision_id=None,
        objects={},
        relationships={},
    )


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(suffix: str) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": "artifact:recap:longmont-c2:session-22",
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-22:recap:paragraph:{suffix}",
        "anchor_quotes": ["quote"],
    }


def _candidate_graph_payload(
    *,
    campaign_id: str = CAMPAIGN_ID,
    session_id: str = SESSION_ID,
) -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:http-promote-vial",
        "session_id": session_id,
        "campaign_id": campaign_id,
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            {
                "node_id": "obj_session22_vial",
                "label": "vial",
                "node_type": "item",
                "description": "Puddle sample vial",
                "importance": "medium",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("006")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
            {
                "node_id": "mystery_puddles",
                "label": "Magic puddles",
                "node_type": "mystery",
                "description": "Delayed reflections",
                "importance": "medium",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }


def _write_reviewable_extraction_run(
    repo: Path,
    *,
    status: str = "reviewable",
    campaign_id: str | None = CAMPAIGN_ID,
    world_id: str | None = None,
    invent_session_in_candidate: bool = False,
    candidate_campaign_id: str | None = ...,  # type: ignore[assignment]
    pin_noncanonical_span_index: bool = False,
) -> tuple[str, Path]:
    """Build a canonical worldbuilding ExtractionRun through its owning services.


    Nothing is hand-written into a registry file: the workspace document, its
    committed bytes, the SourceArtifact, the span index, and every run status
    transition go through the same code paths production uses, so the fixture
    cannot drift away from the registry's own validators.


    ``campaign_id=None`` produces a campaignless worldbuilding run/artifact
    (worldbuilding SourceArtifacts may omit campaign). The workspace document
    still needs a storage campaign for the file write; the artifact/run are
    then rewritten to drop that campaign before promotion.


    ``pin_noncanonical_span_index=True`` writes a second valid index for the same
    artifact (different span IDs) and pins the ExtractionRun component to that
    path — used to prove review/prepare load the run-pinned URI, not the
    registry canonical path.
    """
    from apps.live_control_server.services.graph_run_registry import (
        create_extraction_run,
        supersede_extraction_run,
        update_extraction_run_status,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryDocument,
        create_source_artifact_from_workspace_document,
        get_source_artifact,
        source_artifacts_path,
        source_span_index_relpath,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )
    from graph_memory.source_span import (
        source_span_index_to_dict,
    )
    from src.live_play.live_store import load_json, write_json


    if candidate_campaign_id is ...:
        candidate_campaign_id = campaign_id


    storage_campaign = world_id or campaign_id or CAMPAIGN_ID
    if world_id is not None:
        (repo / f"corpus/{world_id}-markdown").mkdir(parents=True, exist_ok=True)
    document = create_workspace_document(
        repo,
        title="Worldbuilding lore",
        campaign_id=storage_campaign,
        world_id=world_id,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        repo, document.document_id, expected_revision=document.revision
    )
    source = repo / committed.target_relpath
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "# Lore\n\nWorldbuilding source for promote.\n\nA second paragraph.\n",
        encoding="utf-8",
    )
    artifact = create_source_artifact_from_workspace_document(
        repo, document_id=committed.document_id, expected_revision=committed.revision
    )


    if campaign_id is None:
        # Worldbuilding SourceArtifacts may omit campaign; rewrite the registry
        # record so the ExtractionRun binds to a truly campaignless artifact.
        path = source_artifacts_path(repo)
        document_payload = SourceArtifactRegistryDocument.model_validate(load_json(path))
        rewritten = []
        for row in document_payload.records:
            if row.source_artifact_id == artifact.source_artifact_id:
                rewritten.append(
                    row.model_copy(update={"campaign_id": None, "world_id": None})
                )
            else:
                rewritten.append(row)
        write_json(
            path,
            SourceArtifactRegistryDocument(
                schema_version=document_payload.schema_version,
                records=rewritten,
            ).model_dump(mode="json"),
        )
        artifact = get_source_artifact(repo, artifact.source_artifact_id)
        assert artifact.campaign_id is None


    span_rel = source_span_index_relpath(artifact.source_artifact_id)
    span_path = repo / span_rel
    span_index = json.loads(span_path.read_text(encoding="utf-8"))
    source_lines = source.read_text(encoding="utf-8").splitlines()
    span_ref_id = str(span_index["spans"][0]["source_span_id"])
    for span in span_index["spans"]:
        start = int(span["start_line"])
        end = int(span["end_line"])
        paragraph = "\n".join(source_lines[start - 1 : end])
        if "Worldbuilding source for promote." in paragraph:
            span_ref_id = str(span["source_span_id"])
            break


    run_dir = repo / "out" / "graph_memory" / "runs" / "extraction" / "wb1"
    run_dir.mkdir(parents=True, exist_ok=True)


    if pin_noncanonical_span_index:
        # Whole-document span → different stable span IDs than the registry
        # paragraph index, but still digest-valid for the same artifact bytes.
        from graph_memory.source_span import (
            SOURCE_SPAN_INDEX_SCHEMA,
            SOURCE_SPAN_INDEX_VERSION,
            SourceSpanIndex,
            SourceSpanIndexEntry,
            build_stable_source_span_id,
            document_source_ref_id,
        )


        digest = artifact.content_sha256 or ""
        n_lines = max(1, len(source_lines))
        source_ref = document_source_ref_id(artifact.source_artifact_id)
        alt_span_id = build_stable_source_span_id(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=digest,
            start_line=1,
            end_line=n_lines,
        )
        canonical_ids = {str(span["source_span_id"]) for span in span_index["spans"]}
        assert alt_span_id not in canonical_ids
        alt_index = SourceSpanIndex(
            schema=SOURCE_SPAN_INDEX_SCHEMA,
            version=SOURCE_SPAN_INDEX_VERSION,
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=digest,
            source_ref_id=source_ref,
            spans=(
                SourceSpanIndexEntry(
                    source_span_id=alt_span_id,
                    source_ref_id=source_ref,
                    source_artifact_id=artifact.source_artifact_id,
                    content_sha256=digest,
                    start_line=1,
                    end_line=n_lines,
                ),
            ),
        )
        alt_rel = "out/graph_memory/runs/extraction/wb1/alt_source_span_index.json"
        alt_path = repo / alt_rel
        write_json(alt_path, source_span_index_to_dict(alt_index))
        span_component_uri = f"repo://{alt_rel}"
        span_component_path = alt_path
        span_ref_id = alt_span_id
    else:
        span_component_uri = f"repo://{span_rel}"
        span_component_path = span_path


    candidate_payload = _candidate_graph_payload(
        campaign_id=candidate_campaign_id or "",
        session_id="session-99" if invent_session_in_candidate else "",
    )
    if not invent_session_in_candidate:
        candidate_payload["session_id"] = None
    if candidate_campaign_id is None:
        candidate_payload["campaign_id"] = None
    candidate_payload["source_artifact_ids"] = [artifact.source_artifact_id]
    # Stamp the real worldbuilding profile default — not played_canon. BLD-07
    # narrowed worldbuilding to inspect-only; fixtures must not hide the gate.
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE,
    )


    worldbuilding_semantic = dict(WORLDBUILDING_PLUMBING_PROFILE.default_semantic_state)
    for holder in (
        *(candidate_payload.get("nodes") or []),
        *(candidate_payload.get("edges") or []),
    ):
        holder["semantic_state"] = dict(worldbuilding_semantic)
        for ref in holder.get("evidence_refs") or []:
            ref["source_artifact_id"] = artifact.source_artifact_id
            ref["source_span_ref_id"] = span_ref_id
            ref["anchor_quotes"] = ["Worldbuilding source for promote."]


    candidate_path = run_dir / "candidate_graph.json"
    candidate_path.write_text(
        json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8"
    )


    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact.uri,
            sha256=artifact.content_sha256,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=span_component_uri,
            sha256=_digest(span_component_path),
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=f"repo://{candidate_path.relative_to(repo).as_posix()}",
            sha256=_digest(candidate_path),
        ),
    }


    run = create_extraction_run(
        repo,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=campaign_id,
        session_id=None,
        profile_id="worldbuilding_plumbing_v0@0.1",
    )
    reachable = [
        ExtractionRunStatus.PREPARED,
        ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED,
        ExtractionRunStatus.REVIEWABLE,
    ]
    stop_at = (
        ExtractionRunStatus.REVIEWABLE
        if status == "superseded"
        else ExtractionRunStatus(status)
    )
    for step in reachable:
        run = update_extraction_run_status(
            repo,
            run.run_id,
            status=step,
            expected_revision=run.revision,
            components=components if step == ExtractionRunStatus.PREPARED else None,
        )
        if step == stop_at:
            break
    if status == "superseded":
        supersede_extraction_run(repo, run.run_id, expected_revision=run.revision)
    return run.run_id, source


def _write_bld08_reviewable_run(
    repo: Path,
    *,
    campaign_id: str | None = CAMPAIGN_ID,
    world_id: str | None = None,
    profile_id: str = "worldbuilding_shepherds_flock_v0@0.1",
    session_id: str | None = None,
) -> tuple[str, Path]:
    """Adapt the canonical run fixture to the checked-in BLD-08 profile."""
    from apps.live_control_server.services.graph_run_registry import (
        extraction_runs_path,
        get_extraction_run,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        _resolve_extraction_component_path,
    )
    from src.live_play.live_store import load_json, write_json
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        DEFAULT_SEMANTIC_STATE,
    )


    resolved_id, source = _write_reviewable_extraction_run(
        repo,
        campaign_id=campaign_id,
        world_id=world_id,
    )
    run = get_extraction_run(repo, resolved_id)
    candidate_path = _resolve_extraction_component_path(
        repo,
        run.components["candidate_graph"].uri,
        label="candidate_graph",
    )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["session_id"] = session_id
    for index, node in enumerate(candidate.get("nodes") or []):
        node["node_type"] = "character" if index == 0 else "location"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
    for edge in candidate.get("edges") or []:
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()


    registry_path = extraction_runs_path(repo)
    registry = load_json(registry_path)
    for record in registry["records"]:
        if record["run_id"] == resolved_id:
            record["profile_id"] = profile_id
            record["components"]["candidate_graph"]["sha256"] = digest
            break
    write_json(registry_path, registry)
    return resolved_id, source


def _mutate_extraction_candidate(repo, run_id: str, mutator) -> None:
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from apps.live_control_server.services.promotable_ingest_run import (
        _resolve_extraction_component_path,
    )


    run = get_extraction_run(repo, run_id)
    candidate_path = _resolve_extraction_component_path(
        repo, run.components["candidate_graph"].uri, label="candidate_graph"
    )
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    mutator(payload)
    candidate_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # Digest must match the component seal or reviewable evidence fails before
    # our span checks. Re-seal the component digest on the registry record.
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    from apps.live_control_server.services.graph_run_registry import (
        extraction_runs_path,
    )
    from src.live_play.live_store import load_json, write_json


    path = extraction_runs_path(repo)
    document = load_json(path)
    for record in document["records"]:
        if record["run_id"] == run_id:
            record["components"]["candidate_graph"]["sha256"] = digest
            break
    write_json(path, document)


def _preview_node(
    artifact_id: str, *, node_id: str, label: str, node_type: str, span: str
) -> dict:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": f"{label}.",
        "importance": "low",
        "semantic_state": {
            "canon_state": "played_canon",
            "lifecycle_state": "candidate",
            "evidence_role": "source_evidence",
            "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "evidence_refs": [
            {
                "source_ref_id": f"ref:{node_id}",
                "source_artifact_id": artifact_id,
                "source_anchor_id": f"anchor:{node_id}",
                "label": "span",
                "evidence_role": "source_evidence",
                "can_open_source": True,
                "can_highlight_span": True,
                "source_span_ref_id": span,
                "anchor_quotes": [label],
            }
        ],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _seal_tinker_package(
    mutation_context,
    tmp_path: Path,
    *,
    preview_slug: str,
    node_id: str,
    label: str,
    extra_nodes: list[dict] | None = None,
    edges: list[dict] | None = None,
) -> tuple[dict, list[str]]:
    """Build a real sealed Buddy review package against native DND identity facts."""
    from graph_memory.candidate_graph_preview import (
        CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        CANDIDATE_GRAPH_PREVIEW_VERSION,
        candidate_graph_preview_from_dict,
    )
    from graph_memory.extract_identity_gate import gate_candidate_graph_against_head
    from graph_memory.extract_promote_proposal import (
        build_contribution_effect_slice,
        contribution_meta_from_contribution,
        seal_multi_contribution_promote_proposal,
    )


    parent = mutation_context.revision_id
    source = tmp_path / f"{preview_slug}-recap.md"
    source.write_text(f"{label} arrives in Mireward.\n")
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = f"artifact:recap:longmont-c2:{preview_slug}"
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": f"preview:{preview_slug}",
        "session_id": "session-26",
        "campaign_id": CAMPAIGN_ID,
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "nodes": [
            _preview_node(
                artifact_id,
                node_id=node_id,
                label=label,
                node_type="npc",
                span="session-26:recap:paragraph:001",
            ),
            *list(extra_nodes or []),
        ],
        "edges": list(edges or []),
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        mutation_context=mutation_context,
        world_id=mutation_context.world_id,
        source_artifact_id=artifact_id,
        source_revision_id=source_revision,
        source_uri=str(source),
        source_kind="source_extraction",
        source_domain="recap",
        campaign_scope=CAMPAIGN_ID,
    )
    assert gate.parent_revision_id == parent
    slice_body = build_contribution_effect_slice(
        source_revision_id=gate.source_revision_id,
        source_artifact_id=gate.source_artifact_id,
        verified_source_uri=str(gate.verified_source_uri),
        candidate_preview_id=gate.candidate_preview_id,
        candidate_schema=gate.candidate_schema,
        candidate_version=gate.candidate_version,
        contribution_meta=contribution_meta_from_contribution(gate.contribution),
        accepted_proposals=gate.accepted_proposals,
        rejected_assertions=gate.rejected_assertions,
        unresolved_mentions=gate.unresolved_mentions,
        node_id_map=gate.node_id_map,
        identity_outcome_snapshot=gate.identity_outcome_snapshot,
    )
    package = seal_multi_contribution_promote_proposal(
        world_id=mutation_context.world_id,
        parent_revision_id=parent,
        contribution_slices=[slice_body],
        prepared_by="gm@prepare",
        diagnostics=["cutover_write_test"],
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        bind_identity_ledger_to_package,
    )


    package = bind_identity_ledger_to_package(package, mutation_context)
    return package, [a.assertion_id for a in gate.accepted_proposals]
