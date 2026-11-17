"""Hosted owner-only boundary contracts with offline synthetic persistence.

The middleware, DmsPrincipalResolver, owner checks, managed binding resolution,
explorer routes and native Core/WorldKeeper operations are real. Only DMS HTTP
transport, APP catalog reads/journal storage, and Core repository storage are
synthetic. These tests do not prove PostgreSQL, real DMS cookies, or deployment.
"""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

from application_state import pdf_statblock_review
from apps.live_control_server.routes.agent import (
    _pdf_review_creature_draft_id, get_pdf_statblock_publication, get_pdf_statblock_review,
    get_saved_turn_graph_evidence, get_published_pdf_statblock, post_accept_pdf_statblock_review, post_append_pdf_statblock_review,
    post_pdf_statblock_creature_draft, post_pdf_statblock_publication,
)
from application_state.errors import ApplicationStateUnavailableError
from application_state.world_catalog import service as catalog
from application_state.world_catalog.service import StoredWorld
from application_state.world_catalog.types import (
    NativeGraphBindingRecord,
    WorldAccessGrant,
    WorldContainerRecord,
    WorldPermission,
)
from apps.live_control_server.routes.native_graph_explorer import (
    router as explorer_router,
)
from apps.live_control_server.routes import extract_promote, graph_preview, live, workspace_documents
from apps.live_control_server.routes.world_containers import router as worlds_router
from apps.live_control_server.routes.native_graph_inspection import (
    router as inspection_router,
)
from apps.live_control_server.services import (
    native_graph_inspection as inspection_service,
)
from apps.live_control_server.services import hosted_native_graph_access as access
from apps.live_control_server.services import native_graph_explorer as explorer_service
from apps.live_control_server.services.dms_principal import (
    DMS_CURRENT_USER_PATH,
    DMS_SESSION_COOKIE_NAME,
    DmsPrincipalResolver,
)
from apps.live_control_server.services.hosted_auth import (
    AUTH_MODE_ENV,
    DEPLOYMENT_ENVIRONMENT_ENV,
    HOSTED_WORLD_ACCESS_ENV,
    TRUSTED_FRONTEND_ORIGINS_ENV,
    install_hosted_request_boundary,
)
from tests.test_native_graph_explorer import InMemoryExplorerStore, _snapshot
from tests.test_native_recap_preparation import TOKEN, lane as recap_lane  # noqa: F401
from tests.test_combat_mechanics_adoption import adoption_case  # noqa: F401
from tests.test_world_mechanics_associations import prepared as mechanics_prepared  # noqa: F401
from tests.test_statblock_saved_revisions import revision_case, prepared  # noqa: F401
from tests.test_combat_exact_world_mechanics import combat  # noqa: F401
from tests.test_statblock_saved_revisions import revision_case  # noqa: F401
from tests.test_world_mechanics_associations import prepared  # noqa: F401


FRONTEND_ORIGIN = "https://buddy.dungeonmind.net"
DMS_ORIGIN = "https://synthetic-dms.example.test"
OWNER = "synthetic-owner-alpha"
HOSTED_OWNER = f"hosted_dms:{OWNER}"
OTHER_OWNER = "synthetic-owner-beta"
OUTSIDER = "synthetic-outsider"
EXPLORER = "/api/live/native-graph-explorer"
COLLECTION = "/api/live/world-containers"
INSPECTION = "/api/live/native-graph-inspection/read"
PDF_REVIEW = access.BUILD_PDF_SOURCES_PATH + "/statblock-reviews/{review_id}"
OPERATIONS = ("graph", "prepare", "confirm", "operations/read")
# recap_lane substitutes binding for its own test scope; restore the actual
# function here so the real catalog-to-native binding validator is exercised.
_REAL_NATIVE_BINDING = explorer_service.native.binding


class _OfflineClient:
    """One request-scoped real DMS resolver backed only by MockTransport."""

    def __init__(self, application):
        self.application = application
        self.dms_requests = []
        self.peer = "127.0.0.1"
        self.subjects = {
            "owner-session": OWNER,
            "other-session": OTHER_OWNER,
            "outsider-session": OUTSIDER,
            "all-session": "synthetic-grantee-all",
            **{
                f"{permission}-session": f"synthetic-grantee-{permission}"
                for permission in WorldPermission
            },
        }

    def request(
        self,
        method,
        path,
        *,
        session="owner-session",
        origin=FRONTEND_ORIGIN,
        headers=None,
        **kwargs,
    ):
        outgoing = dict(headers or {})
        if session is not None:
            outgoing["Cookie"] = f"{DMS_SESSION_COOKIE_NAME}={session}"
        if origin is not None:
            outgoing["Origin"] = origin
        return asyncio.run(self._request(method, path, headers=outgoing, **kwargs))

    async def _request(self, method, path, **kwargs):
        def introspect(request):
            self.dms_requests.append(request)
            cookie = request.headers.get("cookie", "")
            session = cookie.removeprefix(f"{DMS_SESSION_COOKIE_NAME}=")
            if session == "unavailable-session":
                return httpx.Response(503, json={"sub": OWNER})
            if session == "timeout-session":
                raise httpx.ReadTimeout("Synthetic DMS timeout", request=request)
            if session == "redirect-session":
                return httpx.Response(302, headers={"location": "https://foreign.test"})
            if session == "malformed-session":
                return httpx.Response(200, json={"sub": 7, "role": "gm"})
            subject = self.subjects.get(session)
            return (
                httpx.Response(200, json={"sub": subject})
                if subject
                else httpx.Response(401)
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(introspect)) as dms:
            self.application.state.dms_principal_resolver = DmsPrincipalResolver(
                api_origin=DMS_ORIGIN,
                http_client=dms,
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=self.application,
                    client=(self.peer, 50000),
                ),
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

    def post(self, operation, **kwargs):
        return self.request("POST", f"{EXPLORER}/{operation}", **kwargs)


def _record(world_id, owner, native_world_id, *, name=None, grants=()):
    return WorldContainerRecord(
        world_id=world_id,
        name=name or f"Private {world_id}",
        source_root_relpath=f"corpus/{world_id}-markdown",
        created_at="2026-11-10T00:00:00Z",
        owner_subject=owner,
        access_grants=list(grants),
        native_graph_binding=NativeGraphBindingRecord(
            native_world_id=native_world_id,
            binding_version=3,
            status="active",
            validated_at="2026-11-10T00:00:00Z",
            validated_head_revision_id=f"private-head-{world_id}",
        ),
    )


@pytest.fixture
def hosted(monkeypatch, request):
    lane = request.getfixturevalue("recap_lane")
    records = {
        "managed": _record(
            "managed",
            OWNER,
            lane.bound["native_world_id"],
            name="Shared display name",
            grants=[
                WorldAccessGrant(
                    subject=f"synthetic-grantee-{permission}",
                    permissions=(permission,),
                    granted_by_subject=OWNER,
                )
                for permission in WorldPermission
            ]
            + [
                WorldAccessGrant(
                    subject="synthetic-grantee-all",
                    permissions=tuple(WorldPermission),
                    granted_by_subject=OWNER,
                )
            ],
        ),
        "foreign": _record(
            "foreign", OTHER_OWNER, "native-foreign", name="Shared display name"
        ),
        "unowned": _record("unowned", None, "native-unowned"),
        "not-allowlisted": _record("not-allowlisted", OWNER, "native-hidden"),
    }
    catalog_reads = []

    def get_world(world_id):
        catalog_reads.append(world_id)
        record = records.get(world_id)
        return StoredWorld(copy.deepcopy(record), 1) if record else None

    def list_worlds():
        catalog_reads.append("*")
        return [StoredWorld(copy.deepcopy(record), 1) for record in records.values()]

    monkeypatch.setattr(catalog, "get_world", get_world)
    monkeypatch.setattr(catalog, "list_worlds", list_worlds)
    monkeypatch.setattr(catalog, "list_owned_worlds", lambda subject, ids: [
        stored for stored in list_worlds()
        if stored.record.owner_subject == subject and stored.record.world_id in ids
    ])
    monkeypatch.setattr(explorer_service.native, "binding", _REAL_NATIVE_BINDING)
    monkeypatch.setattr(explorer_service.native, "repository", lambda: lane.repo)
    monkeypatch.setattr(explorer_service.native, "read_repository", lambda: lane.repo)
    monkeypatch.setattr(
        explorer_service, "NativeGraphExplorerStore", InMemoryExplorerStore
    )
    InMemoryExplorerStore.rows.clear()
    InMemoryExplorerStore.locks.clear()
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(TRUSTED_FRONTEND_ORIGINS_ENV, FRONTEND_ORIGIN)
    subjects = [OWNER, OTHER_OWNER, OUTSIDER, "synthetic-grantee-all"] + [
        f"synthetic-grantee-{p}" for p in WorldPermission
    ]
    allowlist = {world_id: subjects for world_id in ("managed", "foreign", "unowned")}
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps(allowlist))

    from apps.live_control_server.routes.media_images import router as media_router

    app = FastAPI()
    app.include_router(media_router)
    app.include_router(explorer_router)
    app.include_router(worlds_router)
    app.include_router(inspection_router)

    from apps.live_control_server.routes.agent import get_build_pdf_sources, post_build_pdf_source

    app.add_api_route(access.BUILD_PDF_SOURCES_PATH, get_build_pdf_sources, methods=["GET"])
    app.add_api_route(access.BUILD_PDF_SOURCES_PATH, post_build_pdf_source, methods=["POST"])

    from apps.live_control_server.routes import play_prepared_tables, play_runs

    from apps.live_control_server.routes import statblock_candidates, threat_drafts, world_mechanics_associations

    app.include_router(statblock_candidates.router)
    from apps.live_control_server.routes import combat_encounters

    from apps.live_control_server.routes import agent as agent_routes, conversation_library

    app.add_api_route("/api/live/agent/worlds/{world_id}/conversation", agent_routes.get_world_conversation_history, methods=["GET"])
    app.add_api_route("/api/live/agent/worlds/{world_id}/conversation/new", agent_routes.post_new_world_conversation, methods=["POST"])
    app.add_api_route("/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}", agent_routes.get_new_world_conversation_status, methods=["GET"])
    app.add_api_route("/api/live/agent/turn", agent_routes.post_agent_turn, methods=["POST"])
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-body-excerpts/{citation_index}",
        agent_routes.get_world_turn_native_body_excerpt, methods=["GET"],
    )
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace",
        agent_routes.get_world_turn_context_trace, methods=["GET"],
    )
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/build-proposals",
        agent_routes.list_build_document_proposals, methods=["GET"],
    )
    from apps.live_control_server.routes.media_images import image_preparation, image_preparations

    app.add_api_route("/api/live/media/images/preparations/list", image_preparations, methods=["GET"])
    app.add_api_route("/api/live/media/images/preparations/{action_id}", image_preparation, methods=["GET"])



    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/rules-passages/{support_id}",
        agent_routes.get_world_historical_rules_passage, methods=["GET"],
    )
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/source-passages/{source_read_event_id}",
        agent_routes.get_world_historical_source_passage, methods=["GET"],
    )
    replay_path = "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}"
    app.add_api_route(replay_path + "/identities", agent_routes.get_world_replay_identities, methods=["GET"])
    authored_path = "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}"
    app.add_api_route(authored_path + "/related-pages/{read_id}", agent_routes.get_world_turn_related_page, methods=["GET"])
    from apps.live_control_server.routes import workspace_lifecycle

    app.include_router(workspace_lifecycle.router)
    from apps.live_control_server.routes import rules_lookup

    app.include_router(rules_lookup.router)
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/connected-page-origin",
        agent_routes.get_world_turn_connected_page_origin, methods=["GET"],
    )
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}",
        agent_routes.get_build_document_proposal, methods=["GET"],
    )
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/review",
        agent_routes.get_plan_authoring_review, methods=["GET"],
    )
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/review",
        agent_routes.post_plan_authoring_review, methods=["POST"],
    )
    from apps.live_control_server.routes import build_proposal_reviews

    app.include_router(build_proposal_reviews.router, prefix="/api/live/agent")
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/build-source-withdrawals",
        agent_routes.withdraw_build_source, methods=["POST"], status_code=204,
    )
    app.include_router(conversation_library.router)
    from apps.live_control_server.routes import conversation_work_plans

    app.include_router(conversation_work_plans.router)
    from apps.live_control_server.routes.live import get_plan_action_terminal_diagnostic

    app.add_api_route(
        "/api/live/world-plan-edit/actions/{action_id}/terminal-diagnostic",
        get_plan_action_terminal_diagnostic, methods=["GET"],
    )
    from apps.live_control_server.routes import native_source_inspection

    app.include_router(native_source_inspection.router)
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-source-sections/{citation_index}",
        agent_routes.get_world_turn_native_source_section, methods=["GET"],
    )
    app.include_router(combat_encounters.router)
    app.include_router(threat_drafts.router)
    app.include_router(world_mechanics_associations.router)
    app.include_router(play_runs.router)
    app.include_router(play_prepared_tables.router)
    app.include_router(workspace_documents.router)
    from apps.live_control_server.routes import graph_authoring

    app.add_api_route("/api/live/graph-authoring/object-kinds", graph_authoring.get_graph_object_authoring_kinds, methods=["GET"])
    app.add_api_route("/api/live/graph-authoring/document-relationship/native-prepare", graph_authoring.post_native_relationship_prepare, methods=["POST"])
    app.add_api_route("/api/live/graph-authoring/document-relationship/native-confirm", graph_authoring.post_native_relationship_confirm, methods=["POST"])
    app.include_router(extract_promote.router)
    app.include_router(live.router)
    app.include_router(graph_preview.router)
    app.add_api_route(PDF_REVIEW, get_pdf_statblock_review, methods=["GET"])
    app.add_api_route(f"{PDF_REVIEW}/publication", get_pdf_statblock_publication, methods=["GET"])
    app.add_api_route(f"{PDF_REVIEW}/publication", post_pdf_statblock_publication, methods=["POST"])
    app.add_api_route(f"{PDF_REVIEW}/publication/statblock", get_published_pdf_statblock, methods=["GET"])
    app.add_api_route(f"{PDF_REVIEW}/creature-draft", post_pdf_statblock_creature_draft, methods=["POST"])
    app.add_api_route(f"{PDF_REVIEW}/accept/{{draft_id}}", post_accept_pdf_statblock_review, methods=["POST"])
    app.add_api_route(f"{PDF_REVIEW}/append/{{draft_id}}", post_append_pdf_statblock_review, methods=["POST"])
    app.add_api_route(
        "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/graph-evidence",
        get_saved_turn_graph_evidence, methods=["GET"],
    )
    install_hosted_request_boundary(
        app,
        world_scope_resolvers={
            **{
                (
                    "POST",
                    f"{EXPLORER}/{operation}",
                ): access.resolve_hosted_explorer_world
                for operation in OPERATIONS
            },
            ("POST", INSPECTION): access.resolve_hosted_explorer_world,
            ("POST", "/api/live/native-graph-inspection/complete-object"): access.resolve_hosted_explorer_world,
            ("POST", "/api/live/native-source-inspection/published-recap"): access.resolve_hosted_explorer_world,
            ("POST", "/api/live/native-graph-inspection/recap-page"): access.resolve_hosted_explorer_world,
            ("POST", "/api/live/native-graph-inspection/authoring-identities"): access.resolve_hosted_explorer_world,
            ("POST", "/api/live/native-graph-inspection/related-recaps"): access.resolve_hosted_explorer_world,
            ("POST", access.FIRST_WORLD_PREPARE_PATH): access.resolve_hosted_first_world,
            ("POST", access.FIRST_WORLD_CONFIRM_PATH): access.resolve_hosted_first_world,
            ("GET", access.BUILD_PDF_SOURCES_PATH): access.resolve_hosted_build_pdf_world,
            ("POST", access.BUILD_PDF_SOURCES_PATH): access.resolve_hosted_build_pdf_world,
            ("GET", access.BUILD_PAGE_INVENTORY_PATH): access.resolve_hosted_build_page_inventory,
            ("POST", "/api/live/graph-preview/extraction-runs"): access.resolve_hosted_build_extraction,
            ("GET", "/api/live/graph-preview/extraction-runs"): access.resolve_hosted_saved_recap,
            ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection"): access.resolve_hosted_saved_recap,
            ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/candidate-projection"): access.resolve_hosted_saved_recap,
            ("GET", "/api/live/graph-preview/extraction-runs/{run_id}"): access.resolve_hosted_build_extraction,
            ("GET", "/api/live/rules/catalog"): access.resolve_hosted_rules_lookup,
            ("GET", "/api/live/rules/query"): access.resolve_hosted_rules_lookup,
            ("GET", "/api/live/rules/passages/{citation_id}"): access.resolve_hosted_rules_lookup,
            ("GET", "/api/live/connected-pages/{operation_id}"): access.resolve_hosted_connected_page,
            ("GET", "/api/live/graph-authoring/object-kinds"): access.resolve_hosted_plan_world_context,
            ("POST", "/api/live/graph-authoring/document-relationship/native-prepare"): access.resolve_hosted_native_relationship,
            ("POST", "/api/live/graph-authoring/document-relationship/native-confirm"): access.resolve_hosted_native_relationship,
            ("POST", "/api/live/connected-pages/prepare"): access.resolve_hosted_connected_page,
            ("POST", "/api/live/connected-pages/confirm"): access.resolve_hosted_connected_page,
            ("GET", "/api/live/plan-view"): access.resolve_hosted_plan_world_context,
            ("GET", "/api/live/world-workspace/trash"): access.resolve_hosted_plan_world_context,
            ("POST", "/api/live/world-workspace/documents/{document_id}/trash"): access.resolve_hosted_workspace_lifecycle,
            ("POST", "/api/live/world-workspace/documents/{document_id}/restore"): access.resolve_hosted_workspace_lifecycle,
            ("POST", "/api/live/world-workspace/sessions/{run_id}/trash"): access.resolve_hosted_workspace_lifecycle,
            ("POST", "/api/live/world-workspace/sessions/{run_id}/restore"): access.resolve_hosted_workspace_lifecycle,
            ("GET", "/api/live/workspace-documents/world-plans"): access.resolve_hosted_plan_world_context,
            ("GET", "/api/live/workspace-documents/{document_id}/committed-revision"): access.resolve_hosted_committed_plan,
            ("GET", "/api/live/workspace-documents/{document_id}/committed-revision/{revision_n}"): access.resolve_hosted_committed_plan,
            ("POST", "/api/live/workspace-documents/world-plans"): access.resolve_hosted_plan_create,
            ("POST", "/api/live/world-play-runs/v2/preparation"): access.resolve_hosted_play_preparation,
            ("PUT", "/api/live/world-play-runs/v2/{run_id}"): access.resolve_hosted_play_creation,
            ("GET", "/api/live/world-play-runs/v2"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/active"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/reference-manifest"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/content/proposals"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}"): access.resolve_hosted_play_read,
            ("POST", "/api/live/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}"): access.resolve_hosted_play_command,
            ("GET", "/api/live/world-session-evidence"): access.resolve_hosted_plan_world_context,
            ("GET", "/api/live/world-session-evidence/{run_id}/revisions/{revision}"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/review"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/content"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/prepared-tables"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/prepared-tables/receipts"): access.resolve_hosted_play_roll_receipts,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/content/revisions/{revision_n}"): access.resolve_hosted_play_read,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/content/commands/{command_id}"): access.resolve_hosted_play_read,
            ("PUT", "/api/live/world-play-runs/v2/{run_id}/content/commands/{command_id}"): access.resolve_hosted_play_command,
            ("PUT", "/api/live/world-play-runs/v2/{run_id}/review/commands/{command_id}"): access.resolve_hosted_play_command,
            ("PUT", "/api/live/world-play-runs/v2/{run_id}/prepared-tables/commands/{command_id}"): access.resolve_hosted_play_command,
            ("GET", "/api/live/world-play-runs/v2/{run_id}/creation"): access.resolve_hosted_play_creation,
            ("POST", "/api/live/world-play-runs/v2/{run_id}/creation:cancel"): access.resolve_hosted_play_creation,
            ("GET", "/api/live/media/images/preparations/list"): access.resolve_hosted_image_history,
            ("GET", "/api/live/media/images/preparations/{action_id}"): access.resolve_hosted_image_world,
            ("POST", "/api/live/media/images/preparations/{action_id}/asset"): access.resolve_hosted_image_world,
            ("GET", "/api/live/media/images/{asset_id}/metadata"): access.resolve_hosted_saved_artwork,
            ("POST", "/api/live/media/images/{asset_id}/save"): access.resolve_hosted_saved_artwork,
            ("POST", "/api/live/media/images/{asset_id}/regenerate"): access.resolve_hosted_saved_artwork,
            ("GET", "/api/live/media/images/{asset_id}"): access.resolve_hosted_saved_artwork,
            ("GET", "/api/live/media/images/library"): access.resolve_hosted_media_library,
            ("GET", "/api/live/media/images/capabilities"): access.resolve_hosted_image_world,
            ("GET", "/api/live/media/images/catalog"): access.resolve_hosted_image_world,
            ("POST", "/api/live/media/images/generate"): access.resolve_hosted_image_world,
            ("GET", "/api/live/media/images/{asset_id}/original"): access.resolve_hosted_saved_artwork,
            ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/build-context"): access.resolve_hosted_build_extraction,
            ("POST", "/api/live/extract-promote/runs/{run_id}/selection-context"): access.resolve_hosted_recap_selection,
            ("POST", "/api/live/extract-promote/runs/{run_id}/recap-evidence-corrections"): access.resolve_hosted_recap_correction,
            ("GET", "/api/live/extract-promote/runs/{run_id}/review-package"): access.resolve_hosted_build_extraction,
            ("GET", "/api/live/extract-promote/runs/{run_id}/frozen-source-spans"): access.resolve_hosted_build_extraction,
            ("POST", "/api/live/extract-promote/runs/{run_id}/evidence-corrections"): access.resolve_hosted_build_extraction,
            ("POST", "/api/live/workspace-documents"): access.resolve_hosted_build_page_create,
            ("GET", "/api/live/workspace-documents/{document_id}"): access.resolve_hosted_build_page,
            ("GET", "/api/live/workspace-documents/{document_id}/snapshot"): access.resolve_hosted_build_page,
            ("GET", "/api/live/workspace-documents/{document_id}/native-world-source"): access.resolve_hosted_build_native_source,
            ("GET", "/api/live/threat-drafts"): access.resolve_hosted_statblock_inventory,
            ("POST", "/api/live/agent/turn"): access.resolve_hosted_chat_turn,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation"): access.resolve_hosted_conversation_world,
            ("POST", "/api/live/agent/worlds/{world_id}/conversation/new"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/active/messages"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id:uuid}/messages"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/turns"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/retry-context"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/name"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/retry-attempts"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/world-plan-edit/actions/{action_id}/terminal-diagnostic"): access.resolve_hosted_plan_world_context,
            ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/work-plans/{source_turn_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/build-proposals"): access.resolve_hosted_conversation_world,
            ("POST", "/api/live/agent/worlds/{world_id}/build-source-withdrawals"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/review"): access.resolve_hosted_conversation_world,
            ("POST", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/review"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/review"): access.resolve_hosted_conversation_world,
            ("POST", "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/review"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-source-sections/{citation_index}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/related-pages/{read_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/connected-page-origin"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/saved-sections/{segment_index}/{section_event_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/source-passages/{source_read_event_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/rules-passages/{support_id}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/identities"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/steps/{sequence}/assertion"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/native-steps/{sequence}/assertion"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-body-excerpts/{citation_index}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/source-passages/{citation_index}"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/graph-evidence"): access.resolve_hosted_conversation_world,
            ("GET", "/api/live/combat/encounters"): access.resolve_hosted_combat_encounter,
            ("POST", "/api/live/combat/encounters"): access.resolve_hosted_combat_encounter,
            ("POST", "/api/live/combat/encounters/saved-mechanics/preview"): access.resolve_hosted_combat_encounter,
            ("POST", "/api/live/combat/encounters/accepted-mechanics/preview"): access.resolve_hosted_combat_encounter,
            ("POST", "/api/live/combat/encounters/world-mechanics/preview"): access.resolve_hosted_combat_encounter,
            ("GET", "/api/live/combat/encounters/{encounter_id}"): access.resolve_hosted_combat_encounter,
            ("POST", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions"): access.resolve_hosted_combat_encounter,
            ("POST", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions:cancel"): access.resolve_hosted_combat_encounter,
            ("GET", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions/{operation_id}"): access.resolve_hosted_combat_encounter,
            ("GET", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions"): access.resolve_hosted_combat_encounter,
            ("PUT", "/api/live/combat/encounters/{encounter_id}"): access.resolve_hosted_combat_encounter,
            ("GET", "/api/live/threat-drafts/{draft_id}/mechanics-revisions/{revision_id}"): access.resolve_hosted_saved_statblock,
            ("GET", "/api/live/threat-drafts/{draft_id}/native-creature"): access.resolve_hosted_native_creature,
            ("POST", "/api/live/threat-drafts/{draft_id}/native-creature/prepare"): access.resolve_hosted_native_creature,
            ("POST", "/api/live/threat-drafts/{draft_id}/native-creature/confirm"): access.resolve_hosted_native_creature,
            ("GET", "/api/live/threat-drafts/{draft_id}/mechanics-revisions"): access.resolve_hosted_saved_statblock,
            ("DELETE", "/api/live/threat-drafts/{draft_id}/saved-statblock"): access.resolve_hosted_saved_statblock,
            ("POST", "/api/live/threat-drafts/{draft_id}/mechanics-revisions"): access.resolve_hosted_statblock_revision_save,
            ("GET", "/api/live/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}"): access.resolve_hosted_saved_statblock,
            ("POST", "/api/live/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}:recover"): access.resolve_hosted_saved_statblock,
            ("GET", "/api/live/world-mechanics/associations"): access.resolve_hosted_statblock_inventory,
            ("POST", "/api/live/world-mechanics/associations"): access.resolve_hosted_mechanics_association,
            ("GET", "/api/live/world-mechanics/associations/creatures"): access.resolve_hosted_plan_world_context,
            ("GET", "/api/live/world-mechanics/associations/requests/{request_id}"): access.resolve_hosted_plan_world_context,
            ("POST", "/api/live/tiptap/markdown-write/prepare"): access.resolve_hosted_build_page,
            ("POST", "/api/live/tiptap/markdown-write/commit"): access.resolve_hosted_build_page,
            ("GET", PDF_REVIEW): access.resolve_hosted_build_pdf_world,
            ("POST", f"{PDF_REVIEW}/accept/{{draft_id}}"): access.resolve_hosted_build_pdf_world,
            ("POST", f"{PDF_REVIEW}/append/{{draft_id}}"): access.resolve_hosted_build_pdf_world,
            ("GET", f"{PDF_REVIEW}/publication"): access.resolve_hosted_build_pdf_world,
            ("POST", f"{PDF_REVIEW}/publication"): access.resolve_hosted_build_pdf_world,
            ("GET", f"{PDF_REVIEW}/publication/statblock"): access.resolve_hosted_build_pdf_world,
            ("POST", f"{PDF_REVIEW}/creature-draft"): access.resolve_hosted_build_pdf_world,
            ("GET", access.WORLD_LOOKUP_PATH): access.resolve_hosted_world_lookup,
        },
        collection_authorizers={("GET", COLLECTION): access.hosted_owner_collection},
    )
    unrelated_calls = []

    @app.api_route("/api/live/graph-authoring/confirm", methods=["POST"])
    @app.api_route("/api/provider", methods=["POST"])
    def unrelated():
        unrelated_calls.append(True)
        return {"secret": "must never be reached"}

    client = _OfflineClient(app)
    return SimpleNamespace(**locals())


def _payload(x, operation, world_id="managed"):
    if operation == "graph":
        return {"managed_world_id": world_id}
    body = {"managed_world_id": world_id, "operation_id": str(uuid4())}
    if operation == "prepare":
        body.update(
            native_world_id=x.lane.bound["native_world_id"],
            binding_version=3,
            expected_revision_id=x.lane.repo.get_head(
                x.lane.bound["native_world_id"]
            ).head_revision_id,
            kind="create_object",
            name="Synthetic hosted person",
            object_kind="person",
        )
    return body


def _prepare(x):
    body = _payload(x, "prepare")
    response = x.client.post("prepare", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "prepared"
    return {key: body[key] for key in ("managed_world_id", "operation_id")}


def _assert_unchanged(x, before, journal):
    assert _snapshot(x.lane.repo) == before
    assert InMemoryExplorerStore.rows == journal


def test_owner_collection_returns_only_allowlisted_owned_sanitized_records(hosted):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request("GET", COLLECTION)
    assert response.status_code == 200, response.text
    result = response.json()
    assert [record["world_id"] for record in result["records"]] == ["managed"]
    record = result["records"][0]
    assert record["name"] == "Shared display name"
    assert set(record) == {
        "schema_version",
        "world_id",
        "name",
        "source_root_relpath",
        "created_at",
        "native_graph_binding",
    }
    assert record["native_graph_binding"] == {"status": "active", "binding_version": 3}
    for secret in (
        OWNER,
        OTHER_OWNER,
        OUTSIDER,
        "private-head",
        "native-foreign",
        "unowned",
        "not-allowlisted",
    ):
        assert secret not in response.text
    _assert_unchanged(x, before, {})


def test_alternate_owner_collection_does_not_confuse_equal_world_names(hosted):
    response = hosted.client.request("GET", COLLECTION, session="other-session")
    assert response.status_code == 200, response.text
    assert [r["world_id"] for r in response.json()["records"]] == ["foreign"]
    assert OWNER not in response.text and "managed-markdown" not in response.text


@pytest.mark.parametrize(
    "session",
    ["outsider-session", "all-session"] + [f"{p}-session" for p in WorldPermission],
)
def test_nonowners_including_each_action_grantee_get_empty_collection(hosted, session):
    response = hosted.client.request("GET", COLLECTION, session=session)
    assert response.status_code == 200, response.text
    assert response.json()["records"] == []


def test_introspected_owner_reads_actual_native_graph_without_writes(hosted):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post("graph", json=_payload(x, "graph"))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["managed_world_id"] == "managed"
    assert result["native_world_id"] == x.lane.bound["native_world_id"]
    assert result["binding_version"] == 3
    assert (
        result["graph"]["revision_id"]
        == x.lane.repo.get_head(result["native_world_id"]).head_revision_id
    )
    assert result["graph"]["nodes"] == []
    assert result["graph"]["capabilities"] == {
        "create": False,
        "connect": False,
        "rename": False,
        "delete": False,
        "object_kinds": [],
    }
    assert x.app.dependency_overrides == {}
    assert x.catalog_reads and len(x.client.dms_requests) == 1
    outbound = x.client.dms_requests[0]
    assert str(outbound.url) == f"{DMS_ORIGIN}{DMS_CURRENT_USER_PATH}"
    assert outbound.headers["cookie"] == f"{DMS_SESSION_COOKIE_NAME}=owner-session"
    _assert_unchanged(x, before, {})


def test_owner_prepare_confirm_recovery_use_native_receipt_and_subject_scope(hosted):
    x = hosted
    body = _prepare(x)
    assert (HOSTED_OWNER, "managed", body["operation_id"]) in InMemoryExplorerStore.rows
    committed = x.client.post("confirm", json=body)
    assert committed.status_code == 200, committed.text
    first = committed.json()
    assert first["status"] == "committed"
    assert first["created_node_id"].startswith("ent:")
    assert first["created_node_id"] in {
        node["id"] for node in first["graph"]["graph"]["nodes"]
    }
    after = _snapshot(x.lane.repo)
    recovered = x.client.post("operations/read", json=body)
    replayed = x.client.post("confirm", json=body)
    for response in (recovered, replayed):
        assert response.status_code == 200, response.text
        assert response.json()["created_node_id"] == first["created_node_id"]
        assert response.json()["status"] == "committed"
    assert _snapshot(x.lane.repo) == after



def _interrupted_owner_prepare(x, monkeypatch):
    request = _payload(x, "prepare")
    original = InMemoryExplorerStore.mark_prepared

    def interrupted(*args, **kwargs):
        raise RuntimeError("synthetic interruption before the review journal write")

    monkeypatch.setattr(InMemoryExplorerStore, "mark_prepared", interrupted)
    response = x.client.post("prepare", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "unknown"
    monkeypatch.setattr(InMemoryExplorerStore, "mark_prepared", original)
    return request, {key: request[key] for key in ("managed_world_id", "operation_id")}


def test_owner_interrupted_prepare_recovers_exact_draft_without_duplicate_admission(
    hosted, monkeypatch
):
    x = hosted
    request, lookup = _interrupted_owner_prepare(x, monkeypatch)
    after_admission = _snapshot(x.lane.repo)
    result = x.client.post("operations/read", json=lookup)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "unknown"
    assert result.json()["recovery_action"] == "retry_prepare"
    assert _snapshot(x.lane.repo) == after_admission
    changed = x.client.post("prepare", json={**request, "name": "Different request"})
    assert changed.status_code == 409
    assert changed.json()["detail"]["code"] == "operation_id_conflict"
    recovered = x.client.post("prepare", json=request)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "prepared"
    assert recovered.json()["operation_id"] == request["operation_id"]
    assert _snapshot(x.lane.repo) == after_admission
    committed = x.client.post("confirm", json=lookup)
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert sum(node["name"] == request["name"] for node in committed.json()["graph"]["graph"]["nodes"]) == 1


@pytest.mark.parametrize("session", ["other-session", "all-session"])
def test_nonowner_cannot_discover_or_retry_an_interrupted_owner_prepare(
    hosted, monkeypatch, session
):
    x = hosted
    request, lookup = _interrupted_owner_prepare(x, monkeypatch)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    for operation, body in (("operations/read", lookup), ("prepare", request)):
        response = x.client.post(operation, session=session, json=body)
        assert response.status_code == 403, response.text
        assert "recovery_action" not in response.json()
        _assert_unchanged(x, before, journal)


@pytest.mark.parametrize("revoke", ["owner", "binding"])
def test_interrupted_prepare_retry_advice_is_withheld_after_midread_revocation(
    hosted, monkeypatch, revoke
):
    x = hosted
    _, lookup = _interrupted_owner_prepare(x, monkeypatch)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    original = InMemoryExplorerStore.get_operation
    record = x.records["managed"]

    def get_operation_and_revoke(store, operation_id):
        result = original(store, operation_id)
        change = {"owner_subject": OTHER_OWNER} if revoke == "owner" else {
            "native_graph_binding": record.native_graph_binding.model_copy(
                update={"native_world_id": "native-foreign", "binding_version": 4}
            )
        }
        x.records["managed"] = record.model_copy(update=change)
        return result

    monkeypatch.setattr(InMemoryExplorerStore, "get_operation", get_operation_and_revoke)
    response = x.client.post("operations/read", json=lookup)
    assert response.status_code == (403 if revoke == "owner" else 409), response.text
    assert "recovery_action" not in response.json() and "status" not in response.json()
    _assert_unchanged(x, before, journal)

def test_hosted_subject_cannot_recover_local_operator_journal(hosted, monkeypatch):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    local_body = _payload(x, "prepare")
    local = x.client.post(
        "prepare",
        session=None,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=local_body,
    )
    assert local.status_code == 200, local.text
    assert local.json()["status"] == "prepared"
    local_key = ("local_operator", "managed", local_body["operation_id"])
    local_row = copy.deepcopy(InMemoryExplorerStore.rows[local_key])

    # An opaque DMS subject may equal a local identity string, but the two
    # authentication domains must never share operations or native receipt IDs.
    x.client.subjects["owner-session"] = "local_operator"
    x.records["managed"] = x.records["managed"].model_copy(
        update={"owner_subject": "local_operator"}
    )
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(
        HOSTED_WORLD_ACCESS_ENV, json.dumps({"managed": ["local_operator"]})
    )
    lookup = {key: local_body[key] for key in ("managed_world_id", "operation_id")}
    before = _snapshot(x.lane.repo)
    for operation in ("operations/read", "confirm"):
        response = x.client.post(operation, json=lookup)
        assert response.status_code == (
            200 if operation == "operations/read" else 404
        ), response.text
        if operation == "operations/read":
            assert response.json()["status"] == "not_found"
        else:
            assert response.json()["detail"]["code"] == "operation_not_found"
        assert "review" not in response.json() and "graph" not in response.json()
    assert _snapshot(x.lane.repo) == before

    hosted_body = _payload(x, "prepare")
    hosted_body["operation_id"] = local_body["operation_id"]
    prepared = x.client.post("prepare", json=hosted_body)
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == "prepared"
    hosted_row = InMemoryExplorerStore.rows[
        ("hosted_dms:local_operator", "managed", local_body["operation_id"])
    ]
    assert hosted_row["source_admission_id"] != local_row["source_admission_id"]
    assert InMemoryExplorerStore.rows[local_key] == local_row


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "session",
    ["other-session", "outsider-session", "all-session"]
    + [f"{p}-session" for p in WorldPermission],
)
def test_allowlist_or_action_grants_never_make_a_nonowner_native_gm(
    hosted, operation, session
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(operation, session=session, json=_payload(x, operation))
    assert response.status_code == 403, response.text
    assert "Synthetic hosted person" not in response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "world_id", ["foreign", "unowned", "not-allowlisted", "does-not-exist"]
)
def test_owned_id_cannot_select_foreign_unowned_hidden_or_missing_world(
    hosted, operation, world_id
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(operation, json=_payload(x, operation, world_id))
    assert response.status_code == 403, response.text
    assert "private-head" not in response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("operation", ["confirm", "operations/read"])
def test_guessed_operation_does_not_cross_principal_or_world(hosted, operation):
    x = hosted
    prepared = _prepare(x)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    # Another real owner can enter their own World, but cannot recover alpha's journal.
    response = x.client.post(
        operation,
        session="other-session",
        json={**prepared, "managed_world_id": "foreign"},
    )
    if operation == "confirm":
        assert response.status_code == 404, response.text
    else:
        assert response.status_code == 200, response.text
        assert response.json() == {
            "schema": "dmb_native_graph_explorer_v1",
            "operation_id": prepared["operation_id"],
            "managed_world_id": "foreign",
            "native_world_id": "native-foreign",
            "binding_version": 3,
            "status": "not_found",
        }
    assert "Synthetic hosted person" not in response.text
    assert "review" not in response.json()
    _assert_unchanged(x, before, journal)


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("origin", [None, "https://foreign.example.test", "null"])
def test_all_hosted_explorer_posts_require_trusted_origin(hosted, operation, origin):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(operation, origin=origin, json=_payload(x, operation))
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    ("session", "status"),
    [
        (None, 401),
        ("expired-session", 401),
        ("unavailable-session", 503),
        ("timeout-session", 503),
        ("redirect-session", 503),
        ("malformed-session", 503),
    ],
)
@pytest.mark.parametrize("collection", [False, True])
def test_expired_or_failed_dms_never_reaches_app_or_native_authority(
    hosted, session, status, collection
):
    x = hosted
    before = _snapshot(x.lane.repo)
    if collection:
        response = x.client.request("GET", COLLECTION, session=session)
    else:
        response = x.client.post("graph", session=session, json=_payload(x, "graph"))
    assert response.status_code == status, response.text
    assert x.catalog_reads == []
    assert len(x.client.dms_requests) == (0 if session is None else 1)
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("session", [None, "outsider-session"])
def test_caller_identity_role_and_local_bearer_cannot_replace_dms_owner(
    hosted, session
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(
        "graph",
        session=session,
        json=_payload(x, "graph"),
        headers={
            "X-User-ID": OWNER,
            "X-Subject": OWNER,
            "X-Role": "gm",
            "X-Forwarded-User": OWNER,
            "Authorization": f"Bearer {TOKEN}",
        },
    )
    assert response.status_code == (401 if session is None else 403), response.text
    for outbound in x.client.dms_requests:
        assert "authorization" not in outbound.headers
        assert "x-user-id" not in outbound.headers
        assert "x-role" not in outbound.headers
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"managedWorldId": "managed"},
        {"managed_world_id": ["managed"]},
        {"managed_world_id": " managed"},
        {"managed_world_id": "managed", "role": "gm"},
        {"managed_world_id": "managed", "world_id": "foreign"},
        {"managed_world_id": "managed", "nested": {"worldId": "foreign"}},
    ],
)
def test_hostile_graph_payload_is_denied_before_catalog_or_graph(hosted, body):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post("graph", json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    "raw",
    [
        '{"managed_world_id":"managed","managed_world_id":"foreign"}',
        '{"managed_world_id":"managed","managed_world_id":"managed"}',
        '{"managed_world_id":"managed"',
        "[]",
        "null",
    ],
)
def test_malformed_or_duplicate_json_never_reaches_catalog(hosted, raw):
    response = hosted.client.post(
        "graph", content=raw, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 403, response.text
    assert hosted.catalog_reads == []


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "query",
    [
        "world_id=foreign",
        "managed_world_id=managed&managed_world_id=foreign",
        "managed_world_id=managed&managed_world_id=managed",
        "worldId=managed",
        "native_world_id=native-foreign",
        "unexpected=ignored",
    ],
)
def test_query_selector_cannot_override_typed_body_scope(hosted, operation, query):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request(
        "POST", f"{EXPLORER}/{operation}?{query}", json=_payload(x, operation)
    )
    assert response.status_code == 403, response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    "query",
    ["world_id=foreign", "managed_world_id=managed", "worldId=managed&worldId=foreign"],
)
def test_collection_cannot_be_used_as_a_world_selector_bypass(hosted, query):
    response = hosted.client.request("GET", f"{COLLECTION}?{query}")
    assert response.status_code == 403, response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", COLLECTION),
        ("PUT", f"{COLLECTION}/managed/native-graph-binding"),
        ("POST", f"{COLLECTION}/managed/native-graph-binding/deactivate"),
        ("GET", f"{COLLECTION}/"),
        ("HEAD", COLLECTION),
        ("GET", f"{EXPLORER}/graph"),
        ("POST", f"{EXPLORER}/graph/"),
        ("POST", "/api/live/native-graph-inspection/catalog"),
        ("POST", "/api/live/native-graph-inspection/source"),
        ("POST", "/api/live/graph-authoring/confirm"),
        ("POST", "/api/provider"),
    ],
)
def test_exact_route_registration_does_not_open_other_capabilities(
    hosted, method, path
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request(method, path, json={"managed_world_id": "managed"})
    assert response.status_code == 403, response.text
    assert x.unrelated_calls == [] and x.catalog_reads == []
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("collection", [False, True])
def test_catalog_failure_is_closed_and_does_not_reveal_internal_error(
    hosted, monkeypatch, collection
):
    def unavailable(*_):
        raise ApplicationStateUnavailableError("synthetic-private-catalog-coordinate")

    monkeypatch.setattr(catalog, "get_world", unavailable)
    monkeypatch.setattr(catalog, "list_owned_worlds", unavailable)
    response = (
        hosted.client.request("GET", COLLECTION)
        if collection
        else hosted.client.post("graph", json=_payload(hosted, "graph"))
    )
    assert response.status_code in {403, 503}, response.text
    assert "synthetic-private-catalog-coordinate" not in response.text


@pytest.mark.parametrize("operation", ["confirm", "operations/read"])
@pytest.mark.parametrize("revoke", ["owner", "allowlist"])
def test_revocation_after_prepare_denies_confirm_and_recovery_without_effects(
    hosted, monkeypatch, operation, revoke
):
    x = hosted
    body = _prepare(x)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    if revoke == "owner":
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )
    else:
        monkeypatch.setenv(
            HOSTED_WORLD_ACCESS_ENV, json.dumps({"managed": [OTHER_OWNER]})
        )
    response = x.client.post(operation, json=body)
    assert response.status_code == 403, response.text
    assert "review" not in response.json()
    _assert_unchanged(x, before, journal)


def test_owner_transfer_cannot_recover_previous_owners_operation(hosted):
    x = hosted
    body = _prepare(x)
    x.records["managed"] = x.records["managed"].model_copy(
        update={"owner_subject": OTHER_OWNER}
    )
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    response = x.client.post("operations/read", json=body, session="other-session")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "schema": "dmb_native_graph_explorer_v1",
        "operation_id": body["operation_id"],
        "managed_world_id": "managed",
        "native_world_id": x.lane.bound["native_world_id"],
        "binding_version": 3,
        "status": "not_found",
    }
    assert "Synthetic hosted person" not in response.text
    _assert_unchanged(x, before, journal)


def test_local_native_bearer_behavior_remains_available_only_on_loopback(
    hosted, monkeypatch
):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    response = x.client.post(
        "graph",
        session=None,
        origin=None,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=_payload(x, "graph"),
    )
    assert response.status_code == 200, response.text
    assert x.client.dms_requests == []
    denied = x.client.post(
        "graph", session=None, origin=None, json=_payload(x, "graph")
    )
    assert denied.status_code == 401


@pytest.mark.parametrize(
    "proxy_header",
    [
        "Forwarded",
        "X-Forwarded-For",
        "X-Forwarded-Host",
        "X-Forwarded-Proto",
        "X-Real-IP",
    ],
)
def test_local_bearer_is_not_usable_through_forwarding_proxy(
    hosted, monkeypatch, proxy_header
):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    response = x.client.post(
        "graph",
        session=None,
        headers={"Authorization": f"Bearer {TOKEN}", proxy_header: "127.0.0.1"},
        json=_payload(x, "graph"),
    )
    assert response.status_code == 403, response.text
    assert x.catalog_reads == [] and x.client.dms_requests == []


def test_local_bearer_cannot_cross_nonloopback_peer(hosted, monkeypatch):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    x.client.peer = "203.0.113.42"
    response = x.client.post(
        "graph",
        session=None,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=_payload(x, "graph"),
    )
    assert response.status_code == 403, response.text
    assert x.catalog_reads == [] and x.client.dms_requests == []


def test_collection_revalidates_ownership_after_middleware_admission(
    hosted, monkeypatch
):
    x = hosted
    original = catalog.list_owned_worlds
    calls = []

    def transfer_after_snapshot(*args):
        result = original(*args)
        calls.append(True)
        if len(calls) == 1:
            x.records["managed"] = x.records["managed"].model_copy(
                update={"owner_subject": OTHER_OWNER}
            )
        return result

    monkeypatch.setattr(catalog, "list_owned_worlds", transfer_after_snapshot)
    response = x.client.request("GET", COLLECTION)
    assert response.status_code == 200, response.text
    assert response.json()["records"] == []
    assert len(calls) >= 2


def test_graph_result_is_withheld_when_owner_changes_during_native_read(
    hosted, monkeypatch
):
    x = hosted
    before = _snapshot(x.lane.repo)

    def read_repository_and_revoke():
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )
        return x.lane.repo

    monkeypatch.setattr(
        explorer_service.native, "read_repository", read_repository_and_revoke
    )
    response = x.client.post("graph", json=_payload(x, "graph"))
    assert response.status_code == 403, response.text
    assert "graph" not in response.json()
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("operation", ["prepare", "confirm"])
def test_revocation_at_journal_checkpoint_prevents_next_native_publication(
    hosted, monkeypatch, operation
):
    x = hosted
    body = _payload(x, "prepare") if operation == "prepare" else _prepare(x)
    before = _snapshot(x.lane.repo)
    checkpoints = []

    def revoke_at_checkpoint(_store):
        checkpoints.append(True)
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )

    monkeypatch.setattr(InMemoryExplorerStore, "checkpoint", revoke_at_checkpoint)
    response = x.client.post(operation, json=body)
    assert checkpoints
    assert response.status_code == 403, response.text
    assert "review" not in response.json() and "graph" not in response.json()
    assert _snapshot(x.lane.repo) == before
    # A retained uncertainty marker is allowed; it cannot imply publication.
    assert (
        InMemoryExplorerStore.rows[(HOSTED_OWNER, "managed", body["operation_id"])][
            "status"
        ]
        == "unknown"
    )


@pytest.mark.parametrize("operation", ["prepare", "confirm", "operations/read"])
def test_operation_payloads_cannot_smuggle_extra_authority_fields(hosted, operation):
    x = hosted
    body = _payload(x, operation)
    body["principal_subject"] = OWNER
    response = x.client.post(operation, json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == [] and InMemoryExplorerStore.rows == {}


@pytest.mark.parametrize("field", ["native_world_id", "binding_version"])
def test_owner_cannot_supply_a_foreign_native_binding_for_prepare(hosted, field):
    x = hosted
    body = _payload(x, "prepare")
    body[field] = "native-foreign" if field == "native_world_id" else 4
    before = _snapshot(x.lane.repo)
    response = x.client.post("prepare", json=body)
    assert response.status_code == 409, response.text
    _assert_unchanged(x, before, {})


def test_collection_rejects_body_even_when_selector_matches_owner(hosted):
    response = hosted.client.request(
        "GET", COLLECTION, json={"managed_world_id": "managed"}
    )
    assert response.status_code == 403, response.text
    assert hosted.catalog_reads == []


@pytest.mark.parametrize(
    ("operation", "committed"),
    [
        ("confirm", False),
        ("confirm", True),
        ("operations/read", True),
    ],
)
def test_revocation_during_runtime_setup_prevents_commit_or_recovery_dispatch(
    hosted, monkeypatch, operation, committed
):
    x = hosted
    body = _prepare(x)
    if committed:
        response = x.client.post("confirm", json=body)
        assert response.status_code == 200 and response.json()["status"] == "committed"
    before = _snapshot(x.lane.repo)
    original = explorer_service.transport.runtime
    setups, dispatches = [], []

    def runtime_and_revoke(*args, **kwargs):
        runtime = original(*args, **kwargs)
        setups.append(True)
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )

        def dispatch(*dispatch_args, **dispatch_kwargs):
            dispatches.append(True)
            return runtime.commit_prepared_change(*dispatch_args, **dispatch_kwargs)

        return SimpleNamespace(commit_prepared_change=dispatch)

    monkeypatch.setattr(explorer_service.transport, "runtime", runtime_and_revoke)
    response = x.client.post(operation, json=body)
    assert setups
    assert response.status_code == 403, response.text
    assert "graph" not in response.json() and "review" not in response.json()
    assert dispatches == []
    assert _snapshot(x.lane.repo) == before


def test_owner_change_after_dispatch_hides_committed_result_and_denies_retry(
    hosted, monkeypatch
):
    x = hosted
    body = _prepare(x)
    original = explorer_service.transport.runtime
    dispatched = []

    def runtime_revoking_after_commit(*args, **kwargs):
        runtime = original(*args, **kwargs)

        def dispatch(*dispatch_args, **dispatch_kwargs):
            result = runtime.commit_prepared_change(*dispatch_args, **dispatch_kwargs)
            dispatched.append(result)
            x.records["managed"] = x.records["managed"].model_copy(
                update={"owner_subject": OTHER_OWNER}
            )
            return result

        return SimpleNamespace(commit_prepared_change=dispatch)

    monkeypatch.setattr(
        explorer_service.transport, "runtime", runtime_revoking_after_commit
    )
    response = x.client.post("confirm", json=body)
    assert response.status_code == 403, response.text
    assert len(dispatched) == 1
    assert "graph" not in response.json() and "created_node_id" not in response.json()
    # The documented race permits a publication dispatched while still owned to
    # finish. It does not permit its data to be returned after owner revocation.
    assert (
        x.lane.repo.get_head(x.lane.bound["native_world_id"]).head_revision_id
        == dispatched[0].child_revision_id
    )
    after = _snapshot(x.lane.repo)
    for operation in ("confirm", "operations/read"):
        denied = x.client.post(operation, json=body)
        assert denied.status_code == 403, denied.text
    assert len(dispatched) == 1
    assert _snapshot(x.lane.repo) == after


@pytest.mark.parametrize("collection", [False, True])
def test_successful_hosted_graph_and_selector_responses_are_not_cacheable(
    hosted, collection
):
    response = (
        hosted.client.request("GET", COLLECTION)
        if collection
        else hosted.client.post("graph", json=_payload(hosted, "graph"))
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "change",
    [
        {"status": "inactive"},
        {"native_world_id": "native-foreign"},
        {"binding_version": 4},
    ],
)
@pytest.mark.parametrize("hook", ["native_read", "journal_read"])
def test_prepared_status_is_withheld_when_binding_changes_during_request(
    hosted, monkeypatch, change, hook
):
    x = hosted
    body = _prepare(x)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    record = x.records["managed"]

    def change_binding():
        x.records["managed"] = record.model_copy(
            update={
                "native_graph_binding": record.native_graph_binding.model_copy(
                    update=change
                ),
            }
        )

    if hook == "native_read":

        def read_repository():
            change_binding()
            return x.lane.repo

        monkeypatch.setattr(explorer_service.native, "read_repository", read_repository)
    else:
        original = InMemoryExplorerStore.get_operation

        def get_operation(store, operation_id):
            result = original(store, operation_id)
            change_binding()
            return result

        monkeypatch.setattr(InMemoryExplorerStore, "get_operation", get_operation)

    response = x.client.post("operations/read", json=body)
    assert response.status_code == 409, response.text
    assert "review" not in response.json() and "graph" not in response.json()
    _assert_unchanged(x, before, journal)


@pytest.mark.parametrize("state", ["not_found", "rejected"])
def test_early_operation_status_rechecks_binding_before_disclosure(
    hosted, monkeypatch, state
):
    x = hosted
    if state == "not_found":
        body = _payload(x, "operations/read")
    else:
        body = _prepare(x)
        InMemoryExplorerStore(HOSTED_OWNER, "managed").mark_rejected(
            body["operation_id"],
            code="synthetic_rejection",
            error="Private rejection explanation",
            updated_at="2026-11-10T00:00:00Z",
        )
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    original = InMemoryExplorerStore.get_operation
    record = x.records["managed"]

    def get_operation_and_rebind(store, operation_id):
        result = original(store, operation_id)
        x.records["managed"] = record.model_copy(
            update={
                "native_graph_binding": record.native_graph_binding.model_copy(
                    update={"native_world_id": "native-foreign", "binding_version": 4}
                ),
            }
        )
        return result

    monkeypatch.setattr(
        InMemoryExplorerStore, "get_operation", get_operation_and_rebind
    )
    response = x.client.post("operations/read", json=body)
    assert response.status_code == 409, response.text
    assert "status" not in response.json() and "Private rejection" not in response.text
    _assert_unchanged(x, before, journal)


def test_allowlisted_world_without_app_catalog_record_is_not_authorized(
    hosted, monkeypatch
):
    x = hosted
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({"missing-world": [OWNER]}))
    response = x.client.post("graph", json={"managed_world_id": "missing-world"})
    assert response.status_code == 403, response.text
    assert x.catalog_reads == ["missing-world"]
    assert InMemoryExplorerStore.rows == {}


def test_catalog_identity_must_match_the_exact_requested_world(hosted, monkeypatch):
    x = hosted
    original = catalog.get_world

    def confused_catalog(world_id):
        stored = original(world_id)
        if stored is not None:
            return StoredWorld(
                stored.record.model_copy(update={"world_id": "foreign"}),
                stored.revision,
            )
        return None

    monkeypatch.setattr(catalog, "get_world", confused_catalog)
    response = x.client.post("graph", json=_payload(x, "graph"))
    assert response.status_code == 403, response.text
    assert InMemoryExplorerStore.rows == {}


def _inspection_payload(x, entity_id="ent:guessed"):
    return {
        "scope": {
            "managed_world_id": "managed",
            "native_world_id": x.lane.bound["native_world_id"],
            "binding_version": 3,
            "revision_id": x.lane.repo.get_head(
                x.lane.bound["native_world_id"]
            ).head_revision_id,
            "scope_mode": "world",
            "campaign_id": None,
        },
        "selection": {"kind": "entity", "entity_id": entity_id},
    }


def _create_entity(x):
    response = x.client.post("confirm", json=_prepare(x))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "committed"
    return response.json()["created_node_id"]


def test_owner_inspects_actual_loaded_entity_without_source_body_prefetch(
    hosted, monkeypatch
):
    x = hosted
    entity_id = _create_entity(x)
    body = _inspection_payload(x, entity_id)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)

    def forbidden_source_open(*_, **__):
        pytest.fail("Entity inspection must not prefetch source body")

    monkeypatch.setattr(
        inspection_service, "open_admitted_native_text", forbidden_source_open
    )
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["schema"] == "dmb_native_graph_entity_v1"
    assert response.json()["scope"] == body["scope"]
    assert entity_id in response.text and "Synthetic hosted person" in response.text
    assert "source" not in response.json()
    assert response.headers["cache-control"] == "no-store"
    _assert_unchanged(x, before, journal)


@pytest.mark.parametrize(
    "session",
    ["other-session", "outsider-session", "all-session"]
    + [f"{p}-session" for p in WorldPermission],
)
def test_entity_inspection_requires_owner_not_nonowner_action_grants(hosted, session):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request(
        "POST", INSPECTION, session=session, json=_inspection_payload(x)
    )
    assert response.status_code == 403, response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("field", ["native_world_id", "binding_version", "revision_id"])
def test_entity_inspection_requires_exact_native_binding_and_revision_pin(
    hosted, field
):
    x = hosted
    entity_id = _create_entity(x)
    body = _inspection_payload(x, entity_id)
    body["scope"][field] = 4 if field == "binding_version" else "foreign:identity"
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 409, response.text
    assert "entity" not in response.json()
    _assert_unchanged(x, before, journal)


def test_foreign_or_missing_entity_cannot_be_opened_from_owned_world_pin(hosted):
    x = hosted
    body = _inspection_payload(x, "ent:foreign-owner-entity")
    before = _snapshot(x.lane.repo)
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 409, response.text
    assert "entity" not in response.json()
    _assert_unchanged(x, before, {})


def test_hosted_entity_read_returns_pdf_reference_without_rendering(hosted, monkeypatch):
    from types import SimpleNamespace

    entity_id = "ent:pdf-backed"
    evidence_id = "pdf-region:fixture"
    request = _inspection_payload(hosted, entity_id)

    def pinned(scope, principal):
        return inspection_service.native.binding(scope.managed_world_id), None, None, scope, None

    class FixtureEntityReader:
        def list_entities(self, read):
            return SimpleNamespace(entities=[SimpleNamespace(entity_id=entity_id)])

        def get_complete_entity(self, read, selected_id):
            assert selected_id == entity_id
            return {"evidence": [{"evidence_ref_id": evidence_id, "evidence_role": "support"}]}

    def forbidden_render(*args, **kwargs):
        pytest.fail("Hosted entity inspection must not render PDF evidence")

    monkeypatch.setattr(inspection_service, "_pinned", pinned)
    monkeypatch.setattr(inspection_service, "EntityReadService", FixtureEntityReader)
    monkeypatch.setattr(inspection_service, "render_admitted_pdf_evidence", forbidden_render)

    response = hosted.client.request("POST", INSPECTION, json=request)
    assert response.status_code == 200, response.text
    assert response.json()["entity"]["evidence"][0]["evidence_ref_id"] == evidence_id



@pytest.mark.parametrize(("session", "status"), [("owner-session", 200), ("other-session", 403)])
def test_hosted_chronology_requires_world_owner(hosted, session, status):
    body = _inspection_payload(hosted)
    body["selection"] = {"kind": "chronology"}
    response = hosted.client.request("POST", INSPECTION, session=session, json=body)
    assert response.status_code == status, response.text
    if status == 200:
        packet = response.json()
        assert packet["scope"] == body["scope"]
        assert packet["schema"] == "dmb_native_graph_chronology_v1"
        assert packet["assertions"] == []


def test_hosted_owner_opens_exact_admitted_source_span(hosted):
    from datetime import UTC, datetime
    from worldkeeper.application import contracts as wk
    from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS

    lane = hosted.lane
    evidence_id = lane.support_ids["first"]
    meta = wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, lane.run.campaign_id),),
        visibility=wk.Visibility("labels_any", ("dungeonbuddy.visibility:gm",)),
        epistemic_basis="speculative",
        claim_mode="dungeonbuddy.claim:belief",
        standing="provisional",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(evidence_id,),
    )
    runtime = explorer_service.transport.runtime(
        lane.repo, lane.domain, lane.profile,
        now=datetime.now(UTC), operation_id="hosted-chronology-evidence",
    )
    intent = wk.WorldChangeIntent(
        lane.bound["native_world_id"], "fixture", (
            wk.CreateObject("fixture", (
                wk.CreateFact("name", "dnd5e:name", wk.LiteralFactValue("Fixture"), meta),
                wk.CreateFact("classification", "dnd5e:classification", wk.TermRefFactValue("dungeonbuddy:event"), meta),
            )),
        ),
    )
    result = runtime.commit_prepared_change(runtime.prepare_change(intent), confirmed_by="local_operator")
    body = _inspection_payload(hosted)
    chronology = hosted.client.request(
        "POST", INSPECTION, json={**body, "selection": {"kind": "chronology"}},
    )
    assert chronology.status_code == 200, chronology.text
    assert any(row["predicate"] == "dnd5e:name" for row in chronology.json()["assertions"])
    body["selection"] = {
        "kind": "source", "assertion_id": next(row.durable_assertion_id for row in result.assertion_results if row.client_op_id == "name"),
        "evidence_ref_id": evidence_id,
    }
    response = hosted.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet["scope"] == body["scope"]
    assert packet["source"]["text"] == lane.text.splitlines(keepends=True)[0]
    assert "body_text" not in packet["source"]
    denied = hosted.client.request("POST", INSPECTION, session="other-session", json=body)
    assert denied.status_code == 403, denied.text


def test_guessed_source_selection_cannot_open_source(
    hosted, monkeypatch
):
    x = hosted
    body = _inspection_payload(x)
    body["selection"] = {
        "kind": "source",
        "assertion_id": "assertion:guessed",
        "evidence_ref_id": "evidence:guessed",
    }

    def forbidden_source_open(*_, **__):
        pytest.fail("Guessed evidence must not reach the source reader")

    monkeypatch.setattr(
        inspection_service, "open_admitted_native_text", forbidden_source_open
    )
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 409, response.text
    assert set(x.catalog_reads) == {"managed"}
    assert "source" not in response.json()


@pytest.mark.parametrize("mutation", ["campaign", "extra_authority", "query"])
def test_inspection_scope_is_closed_world_entity_only(hosted, mutation):
    x = hosted
    body = _inspection_payload(x)
    path = INSPECTION
    if mutation == "campaign":
        body["scope"].update(scope_mode="campaign", campaign_id="campaign:synthetic")
    elif mutation == "extra_authority":
        body["selection"]["owner_subject"] = OWNER
    else:
        path += "?managed_world_id=managed&managed_world_id=managed"
    response = x.client.request("POST", path, json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []


@pytest.mark.parametrize(
    ("session", "origin", "status"),
    [
        (None, FRONTEND_ORIGIN, 401),
        ("expired-session", FRONTEND_ORIGIN, 401),
        ("unavailable-session", FRONTEND_ORIGIN, 503),
        ("owner-session", None, 403),
        ("owner-session", "https://foreign.test", 403),
    ],
)
def test_inspection_preserves_dms_and_origin_boundary(hosted, session, origin, status):
    x = hosted
    response = x.client.request(
        "POST", INSPECTION, session=session, origin=origin, json=_inspection_payload(x)
    )
    assert response.status_code == status, response.text
    assert x.catalog_reads == []


@pytest.mark.parametrize("revoke", ["owner", "binding"])
def test_entity_inspection_result_is_withheld_after_midread_revocation(
    hosted, monkeypatch, revoke
):
    x = hosted
    body = _inspection_payload(x, _create_entity(x))
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    record = x.records["managed"]

    def read_repository_and_revoke():
        update = (
            {"owner_subject": OTHER_OWNER}
            if revoke == "owner"
            else {
                "native_graph_binding": record.native_graph_binding.model_copy(
                    update={"binding_version": 4}
                )
            }
        )
        x.records["managed"] = record.model_copy(update=update)
        return x.lane.repo

    monkeypatch.setattr(
        explorer_service.native, "read_repository", read_repository_and_revoke
    )
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == (403 if revoke == "owner" else 409), response.text
    assert "entity" not in response.json()
    _assert_unchanged(x, before, journal)


def test_exact_world_lookup_returns_the_same_public_record(hosted):
    response = hosted.client.request("GET", f"{COLLECTION}/lookup?managed_world_id=managed")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == hosted.client.request("GET", COLLECTION).json()["records"][0]


@pytest.mark.parametrize("query", [
    "managed_world_id=unowned",
    "managed_world_id=managed&managed_world_id=managed",
    "managed_world_id=managed&extra=1",
])
def test_exact_world_lookup_rejects_unowned_or_ambiguous_selection(hosted, query):
    response = hosted.client.request("GET", f"{COLLECTION}/lookup?{query}")
    assert response.status_code == 403, response.text


def test_exact_world_lookup_denies_ownership_transfer_after_admission(hosted, monkeypatch):
    original = catalog.get_world

    def transfer_after_admission(world_id):
        record = original(world_id)
        hosted.records[world_id] = hosted.records[world_id].model_copy(update={"owner_subject": OTHER_OWNER})
        return record

    monkeypatch.setattr(catalog, "get_world", transfer_after_admission)
    response = hosted.client.request("GET", f"{COLLECTION}/lookup?managed_world_id=managed")
    assert response.status_code == 403, response.text
    assert hosted.catalog_reads == ["managed", "managed"]


@pytest.mark.parametrize("session, suffix, expected", [
    ("owner-session", "", 200),
    ("other-session", "", 403),
    ("owner-session", "?world_id=foreign", 403),
    ("owner-session", "/statblock-reviews", 403),
])
def test_hosted_pdf_read_is_exact_and_owner_scoped(hosted, monkeypatch, session, suffix, expected):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as sources

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(sources, "_source_world_binding", lambda *_: SimpleNamespace(native_world_id="managed-native"))
    monkeypatch.setattr(sources, "_repository", lambda: SimpleNamespace(
        list_public_native_pdf_revisions=lambda *_a, **_kw: [],
    ))
    path = access.BUILD_PDF_SOURCES_PATH.format(world_id="managed") + suffix
    response = hosted.client.request("GET", path, session=session)
    assert response.status_code == expected, response.text
    if expected == 200:
        assert response.json() == {"documents": [], "next": None}


@pytest.mark.parametrize("query, session, expected", [
    ("world_id=managed", "owner-session", 200),
    ("world_id=managed", "other-session", 403),
    ("world_id=foreign", "owner-session", 403),
    ("world_id=managed&world_id=foreign", "owner-session", 403),
    ("", "owner-session", 403),
])
def test_build_page_inventory_is_scoped_to_owned_world(hosted, monkeypatch, query, session, expected):
    calls = []

    def list_pages(_root, *, world_id, **_filters):
        calls.append(world_id)
        return []

    monkeypatch.setattr(workspace_documents, "list_workspace_documents", list_pages)
    monkeypatch.setattr(workspace_documents, "list_workspace_page_campaign_tags", lambda **_: [])
    response = hosted.client.request("GET", f"{access.BUILD_PAGE_INVENTORY_PATH}?{query}", session=session)
    assert response.status_code == expected, response.text
    assert calls == (["managed"] if expected == 200 else [])
    if expected == 200:
        assert response.headers["cache-control"] == "no-store"


def test_hosted_build_inventory_denies_ownership_transfer_during_read(hosted, monkeypatch):
    def list_pages(*_, **__):
        hosted.records["managed"] = hosted.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER},
        )
        return []

    monkeypatch.setattr(workspace_documents, "list_workspace_documents", list_pages)
    monkeypatch.setattr(workspace_documents, "list_workspace_page_campaign_tags", lambda **_: ["private-tag"])
    response = hosted.client.request("GET", f"{access.BUILD_PAGE_INVENTORY_PATH}?world_id=managed")
    assert response.status_code == 403, response.text
    assert "private-tag" not in response.text

def test_hosted_pdf_list_denies_ownership_transfer_during_read(hosted, monkeypatch):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as sources

    def list_revisions(*_args, **_kwargs):
        hosted.records["managed"] = hosted.records["managed"].model_copy(update={"owner_subject": OTHER_OWNER})
        return []

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(sources, "_source_world_binding", lambda *_: SimpleNamespace(native_world_id="managed-native"))
    monkeypatch.setattr(sources, "_repository", lambda: SimpleNamespace(list_public_native_pdf_revisions=list_revisions))
    path = access.BUILD_PDF_SOURCES_PATH.format(world_id="managed")
    response = hosted.client.request("GET", path)
    assert response.status_code == 403, response.text
    assert "documents" not in response.json()


@pytest.mark.parametrize("session, origin, suffix, expected", [
    ("owner-session", FRONTEND_ORIGIN, "", 200),
    ("other-session", FRONTEND_ORIGIN, "", 403),
    ("owner-session", "https://outside.example", "", 403),
    ("owner-session", FRONTEND_ORIGIN, "?world_id=foreign", 403),
    ("owner-session", FRONTEND_ORIGIN, "/open", 403),
])
def test_binary_pdf_body_only_reaches_authorized_upload(hosted, monkeypatch, session, origin, suffix, expected):
    from hashlib import sha256
    from apps.live_control_server.routes import agent
    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as sources

    calls = []

    def retain(command, raw):
        calls.append(raw)
        return SimpleNamespace(source_revision_id="retained", content_sha256=sha256(raw).hexdigest())

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(sources, "_source_world_binding", lambda *_: SimpleNamespace(native_world_id="managed-native"))
    monkeypatch.setattr(sources, "_repository", lambda: SimpleNamespace(retain_native_pdf_source=retain))
    path = access.BUILD_PDF_SOURCES_PATH.format(world_id="managed") + suffix
    path += ("&" if "?" in path else "?") + f"admission_id={uuid4()}"
    payload = b"%PDF-1.7\n"
    response = hosted.client.request(
        "POST", path, session=session, origin=origin,
        headers={"Content-Type": "application/pdf", "X-Pdf-Created-At": "2026-11-15T00:00:00Z"}, content=payload,
    )
    assert response.status_code == expected, response.text
    assert calls == ([payload] if expected == 200 else [])
    if expected == 200:
        assert response.json()["source_revision_id"] == "retained"


@pytest.mark.parametrize("session, suffix, expected", [
    ("owner-session", "", 200),
    ("other-session", "", 403),
    ("owner-session", "/unregistered", 403),
])
def test_hosted_pdf_review_checks_owner_before_read(hosted, monkeypatch, session, suffix, expected):
    review_id = uuid4()
    reads = []

    def read_review(*, world_id, review_id):
        reads.append((world_id, review_id))
        return {"regions": [], "revision": 1}

    monkeypatch.setattr(pdf_statblock_review, "read_review", read_review)
    monkeypatch.setattr("apps.live_control_server.routes.agent._verified_world_id", lambda world: world)
    response = hosted.client.request(
        "GET", PDF_REVIEW.format(world_id="managed", review_id=review_id) + suffix, session=session,
    )
    assert response.status_code == expected, response.text
    assert reads == ([("managed", review_id)] if expected == 200 else [])
    if expected == 200:
        assert response.headers["cache-control"] == "no-store"


def test_hosted_pdf_review_denies_ownership_transfer_during_read(hosted, monkeypatch):
    def read_review(**_scope):
        hosted.records["managed"] = hosted.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER},
        )
        return {"regions": [], "revision": 1, "definition": {"secret": "private-draft"}}

    monkeypatch.setattr(pdf_statblock_review, "read_review", read_review)
    monkeypatch.setattr("apps.live_control_server.routes.agent._verified_world_id", lambda world: world)
    path = PDF_REVIEW.format(world_id="managed", review_id=uuid4())
    response = hosted.client.request("GET", path)
    assert response.status_code == 403, response.text
    assert "private-draft" not in response.text


@pytest.mark.parametrize("session, expected_revision, expected", [
    ("owner-session", 1, 200),
    ("owner-session", 2, 409),
    ("other-session", 1, 403),
])
def test_hosted_pdf_prepares_only_its_canonical_draft(hosted, monkeypatch, session, expected_revision, expected):
    from apps.live_control_server.routes import agent, statblock_storage
    from apps.live_control_server.services import threat_draft_store

    review_id = uuid4()
    draft_id = _pdf_review_creature_draft_id("managed", review_id)
    calls = []
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(statblock_storage, "statblock_data_root", lambda _: None)
    monkeypatch.setattr(pdf_statblock_review, "read_review", lambda **_: {
        "revision": 1, "regions": [],
        "definition": {"identity": {"name": "Synthetic creature"}, "ruleset": {"system": "dnd5e", "edition": "2024"}},
    })

    def create(_root, body, *, stable_id):
        calls.append((body.world_id, stable_id))
        return SimpleNamespace(draft_id=stable_id, version=1)

    monkeypatch.setattr(threat_draft_store, "create_threat_draft", create)
    path = PDF_REVIEW.format(world_id="managed", review_id=review_id)
    response = hosted.client.request(
        "POST", f"{path}/creature-draft?expected_revision={expected_revision}", session=session,
    )
    assert response.status_code == expected, response.text
    assert calls == ([("managed", draft_id)] if expected == 200 else [])

@pytest.mark.parametrize("session, expected", [("owner-session", 404), ("other-session", 403)])
def test_hosted_pdf_accept_refuses_unrelated_draft_before_storage(hosted, monkeypatch, session, expected):
    from apps.live_control_server.routes import agent, statblock_storage

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(statblock_storage, "statblock_data_root", lambda _: pytest.fail("unexpected draft access"))
    validation = json.loads((Path(__file__).parent / "fixtures/statblocks/v1/validate-response.json").read_text())
    path = PDF_REVIEW.format(world_id="managed", review_id=uuid4())
    response = hosted.client.request("POST", f"{path}/accept/{uuid4()}", session=session, json={
        "operation_id": str(uuid4()),
        "expected_draft_version": 1,
        "expected_revision": 1,
        "validation_receipt": validation["validation_receipt"],
        "validation_definition_digest": validation["definition_digest"],
    })
    assert response.status_code == expected, response.text


@pytest.mark.parametrize(
    "session, origin, expected",
    [("owner-session", FRONTEND_ORIGIN, 200), ("other-session", FRONTEND_ORIGIN, 403),
     ("owner-session", None, 403)],
)
def test_hosted_pdf_append_requires_world_owner_and_origin(hosted, monkeypatch, session, origin, expected):
    from apps.live_control_server.routes import agent, statblock_candidates
    from apps.live_control_server.services.statblock_saved_revision import append_pdf_review

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    review_id, draft_id = uuid4(), uuid4()
    calls = []

    def append(callback, **kwargs):
        assert callback is append_pdf_review
        calls.append((kwargs["world_id"], kwargs["review_id"], kwargs["draft_id"]))
        return {"state": "committed"}

    monkeypatch.setattr(statblock_candidates, "_revision_call", append)
    path = PDF_REVIEW.format(world_id="managed", review_id=review_id)
    response = hosted.client.request("POST", f"{path}/append/{draft_id}", session=session, origin=origin, json={
        "operation_id": str(uuid4()), "expected_revision": 1,
        "base": {"provider": "dungeonmind", "statblock_id": "sb_saved", "revision_id": "rev_published",
                 "contract": "dungeonmind.dungeonbuddy-statblocks", "contract_version": "1.0.0",
                 "definition_digest": "sha256:" + "a" * 64},
    })
    assert response.status_code == expected, response.text
    assert calls == ([("managed", review_id, str(draft_id))] if expected == 200 else [])


@pytest.mark.parametrize("session, expected", [("owner-session", 200), ("other-session", 403)])
def test_hosted_publication_status_only_reads_the_owners_review(hosted, monkeypatch, session, expected):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import native_threat_creation as creature

    review_id = uuid4()
    reads = []

    def read_review(*, world_id, review_id):
        reads.append((world_id, review_id))
        return {"regions": [], "revision": 1}

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(pdf_statblock_review, "read_review", read_review)
    monkeypatch.setattr(creature.native, "binding", lambda world: world)
    monkeypatch.setattr(creature.native, "read_repository", lambda: None)
    monkeypatch.setattr(creature, "existing", lambda *_: None)
    path = PDF_REVIEW.format(world_id="managed", review_id=review_id)
    response = hosted.client.request("GET", f"{path}/publication", session=session)
    assert response.status_code == expected, response.text
    assert reads == ([("managed", review_id)] if expected == 200 else [])

@pytest.mark.parametrize("session, exact_review, expected", [
    ("owner-session", True, 200),
    ("owner-session", True, 503),
    ("owner-session", False, 409),
    ("other-session", True, 403),
])
def test_hosted_pdf_publish_recovers_only_exact_review(hosted, monkeypatch, session, exact_review, expected):
    from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
    from application_state.world_mechanics.types import MechanicsLocator
    from apps.live_control_server.models.statblock_mechanics_acceptance import MechanicsLocatorV1
    from apps.live_control_server.routes import agent, native_threat_creation, world_mechanics_associations
    from apps.live_control_server.services import native_threat_creation as creature

    review_id = uuid4()
    draft_id = _pdf_review_creature_draft_id("managed", review_id)
    provenance = {"world_id": "managed", "review_id": str(review_id), "revision": 1 if exact_review else 2, "regions": []}
    through = {PDF_REVIEW_PROVENANCE: provenance}
    source_locator = MechanicsLocatorV1(
        provider="dungeonmind", statblock_id="sb_saved", revision_id="rev_published",
        contract="dungeonmind.dungeonbuddy-statblocks", contract_version="1.0.0",
        definition_digest="sha256:" + "a" * 64,
    )
    locator = MechanicsLocator.model_validate(source_locator.model_dump())
    draft = SimpleNamespace(accepted_mechanics_ref=SimpleNamespace(to_mechanics_locator=lambda: source_locator))
    calls = []
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(pdf_statblock_review, "read_review", lambda **_: {"revision": 1, "regions": []})
    monkeypatch.setattr(native_threat_creation, "statblock_data_root", lambda _: None)
    monkeypatch.setattr(creature, "owned_draft", lambda *_: draft)
    def resolve_saved_source(_root, *, world_id, draft_id, locator: MechanicsLocator):
        assert locator == MechanicsLocator.model_validate(source_locator.model_dump())
        return draft, locator, "acceptance", None, SimpleNamespace(provenance={"accepted_through": through})

    monkeypatch.setattr(creature, "resolve_saved_source", resolve_saved_source)
    monkeypatch.setattr(creature, "get_acceptance_operation", lambda *_, **__: SimpleNamespace(
        request_body={"accepted_through": through},
    ))

    def status(_root, actual_draft_id, world_id, principal):
        calls.append((actual_draft_id, world_id, principal.subject))
        return {"state": "published", "node_id": "published-creature"}

    monkeypatch.setattr(creature, "status", status)
    monkeypatch.setattr(world_mechanics_associations, "list_associations", lambda *_: [
        SimpleNamespace(request=SimpleNamespace(
            draft_id=draft_id, target=SimpleNamespace(node_id="published-creature", campaign_scope=None),
        ), proof=SimpleNamespace(locator=locator)),
    ])
    if expected == 503:
        from apps.live_control_server.services import world_creature_selection

        monkeypatch.setattr(world_mechanics_associations, "list_associations", lambda *_: [])

        def unavailable(_world):
            raise ApplicationStateUnavailableError("Creature catalog unavailable")

        monkeypatch.setattr(world_creature_selection, "catalog", unavailable)
    path = PDF_REVIEW.format(world_id="managed", review_id=review_id)
    response = hosted.client.request("POST", f"{path}/publication?expected_revision=1", session=session)
    assert response.status_code == expected, response.text
    assert calls == ([(draft_id, "managed", HOSTED_OWNER)] if expected in {200, 503} else [])
    if expected == 200:
        assert response.json() == {"draft_id": str(draft_id), "revision_id": locator.revision_id}

@pytest.mark.parametrize("session, match, transfer, expected", [
    ("owner-session", True, False, 200),
    ("owner-session", False, False, 404),
    ("other-session", True, False, 403),
    ("owner-session", True, True, 403),
])
def test_hosted_build_reads_only_exact_published_statblock(hosted, monkeypatch, session, match, transfer, expected):
    from apps.live_control_server.routes import agent, statblock_candidates

    review_id = uuid4()
    draft_id = _pdf_review_creature_draft_id("managed", review_id)
    monkeypatch.setattr(agent, "get_pdf_statblock_publication",
                        lambda *_: {"draft_id": draft_id, "revision_id": "rev_exact"})
    reads = []

    def open_saved(draft, revision, world, request):
        reads.append((draft, revision, world))
        if transfer:
            hosted.records["managed"] = hosted.records["managed"].model_copy(
                update={"owner_subject": OTHER_OWNER},
            )
        return {"pdf_portrait": "retained-artwork"}

    monkeypatch.setattr(statblock_candidates, "open_saved_revision", open_saved)
    path = PDF_REVIEW.format(world_id="managed", review_id=review_id)
    revision = "rev_exact" if match else "rev_other"
    response = hosted.client.request(
        "GET", f"{path}/publication/statblock?draft_id={draft_id}&revision_id={revision}", session=session,
    )
    assert response.status_code == expected, response.text
    assert reads == ([(str(draft_id), revision, "managed")] if expected == 200 or transfer else [])
    if expected == 200:
        assert response.json() == {"pdf_portrait": "retained-artwork"}
    else:
        assert "retained-artwork" not in response.text


def test_hosted_first_world_prepare_uses_stored_world_and_rechecks_before_preparing(hosted, monkeypatch):
    from apps.live_control_server.services import promotable_ingest_run

    monkeypatch.setattr(
        promotable_ingest_run, "resolve_promotable_ingest_run",
        lambda run_id, *, root: SimpleNamespace(world_id="managed" if run_id in {"owned", "changed"} else "foreign"),
    )
    prepared = []

    def prepare(payload, *, authorize_world):
        authorize_world("foreign" if payload.run_id == "changed" else "managed")
        prepared.append(payload.run_id)
        raise extract_promote.ExtractPromoteError("probe reached", code="probe_reached", status_code=409)

    monkeypatch.setattr(extract_promote, "prepare_first_world", prepare)
    payload = {"runId": "owned", "decisions": [{"assertionId": "source-assertion", "decision": "create_new"}]}
    route = access.FIRST_WORLD_PREPARE_PATH

    assert hosted.client.request("POST", route, json=payload).status_code == 409
    assert hosted.client.request("POST", route, json=payload, session="other-session").status_code == 403
    assert hosted.client.request("POST", route, json={**payload, "runId": "foreign"}).status_code == 403
    assert hosted.client.request("POST", route, json=payload, origin="https://untrusted.example").status_code == 403
    assert hosted.client.request("POST", route, json={**payload, "runId": "changed"}).status_code == 403
    assert prepared == ["owned"]


def test_hosted_turn_evidence_checks_owner_and_exact_selectors(hosted, monkeypatch):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import agent_source_passages as passages

    turn_id = uuid4()
    calls = []

    def read(*, world_id, turn_id, claim_id, anchor_id, service):
        calls.append((world_id, turn_id, claim_id, anchor_id))
        raise passages.SourcePassageOpenError("source_passage_not_found", 404)

    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(passages, "open_saved_turn_graph_evidence", read)
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn_id}/graph-evidence?claim_id=claim&anchor_id=anchor"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&anchor_id=foreign").status_code in (403, 422)
    assert not calls
    result = hosted.client.request("GET", path)
    assert result.status_code == 404, result.text
    assert calls == [("managed", turn_id, "claim", "anchor")]


    def recap(*, continuation, **coords):
        calls.append((coords["anchor_id"], continuation))
        raise passages.SourcePassageOpenError("source_passage_not_found", 404)

    monkeypatch.setattr(passages, "open_saved_turn_related_recap", recap)
    assert hosted.client.request("GET", path + "&continuation=invalid").status_code == 422
    recap_path = path.replace("anchor_id=anchor", "anchor_id=dm-context-anchor%3Av2%3Arecap")
    recap_path += "&continuation=recap-page%3Av2%3Asecond"
    result = hosted.client.request("GET", recap_path)
    assert result.status_code == 404, result.text
    assert calls[-1] == ("dm-context-anchor:v2:recap", "recap-page:v2:second")

def test_hosted_recap_selection_requires_world_owner_and_origin(hosted, monkeypatch):
    from apps.live_control_server.services import ingest_selection_context

    run_id = str(uuid4())
    calls = []

    def select(run, request, *, operator_subject):
        calls.append((run, request.expected_world_id, operator_subject))
        return {"run_id": run}

    monkeypatch.setattr(ingest_selection_context, "resolve_ingest_selection_context", select)
    path = f"/api/live/extract-promote/runs/{run_id}/selection-context"
    body = {
        "schema": "dmb_ingest_native_review_request_v2", "expected_run_revision": 1,
        "expected_candidate_sha256": "a" * 64, "expected_source_sha256": "b" * 64,
        "expected_span_index_sha256": "c" * 64, "expected_world_id": "managed",
        "node_ids": ["node"], "edge_ids": [], "inspect_source_support": True,
    }
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert not calls
    result = hosted.client.request("POST", path, json=body)
    assert result.status_code == 200, result.text
    assert calls == [(run_id, "managed", f"hosted_dms:{OWNER}")]


def test_hosted_recap_correction_checks_exact_parent_in_owned_world(hosted, monkeypatch):
    from apps.live_control_server.services import exact_run_candidate_projection as projection

    checks, writes = [], []

    def verify(root, run_id, world_id):
        checks.append((run_id, world_id))
        if run_id != "owned-run":
            raise projection.CandidateProjectionError("Wrong World.")

    def correct(payload):
        writes.append(payload.parent_run_id)
        raise extract_promote.ExtractPromoteError("Correction reached.", code="probe_reached", status_code=409)

    monkeypatch.setattr(projection, "build_exact_run_candidate_projection", verify)
    monkeypatch.setattr(extract_promote, "correct_recap_run_evidence", correct)
    prefix = "/api/live/extract-promote/runs/"
    suffix = "/recap-evidence-corrections?managed_world_id=managed"
    body = {
        "parentRunId": "owned-run", "parentCandidateSha256": "a" * 64,
        "corrections": [{"assertionId": "claim", "evidenceIndex": 0, "sourceSpanRefId": "span",
                         "quoteIndex": 0, "originalQuote": "old", "replacementQuote": "new"}],
    }
    path = prefix + "owned-run" + suffix
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert not checks
    denied = hosted.client.request("POST", prefix + "foreign-run" + suffix, json={**body, "parentRunId": "foreign-run"})
    assert denied.status_code == 403, denied.text
    accepted = hosted.client.request("POST", path, json=body)
    assert accepted.status_code == 409, accepted.text
    assert checks == [("foreign-run", "managed"), ("owned-run", "managed")]
    assert writes == ["owned-run"]


def test_hosted_build_page_create_save_reopen_and_scope(hosted, application_state_dsn, monkeypatch):
    from application_state.content import pages

    monkeypatch.setattr(pages, "get_world", hosted.get_world)
    documents = "/api/live/workspace-documents"
    editor = "/api/live/tiptap/markdown-write"
    create = {
        "title": "First source", "kind": "worldbuilding_source",
        "authority_state": "draft", "visibility_state": "internal",
        "source_domain": "worldbuilding", "document_class": "lore",
        "world_id": "managed", "campaign_id": "managed",
    }
    assert hosted.client.request("POST", documents, json=create, session="other-session").status_code == 403
    assert hosted.client.request("POST", documents, json={**create, "campaign_id": "foreign"}).status_code == 403
    created = hosted.client.request("POST", documents, json=create)
    assert created.status_code == 200, created.text
    record = created.json()
    document = f"{documents}/{record['document_id']}"
    from io import BytesIO

    from PIL import Image
    from application_state import media

    image = BytesIO()
    Image.new("RGB", (2, 2)).save(image, format="PNG")
    asset = media.stage_image(image.getvalue(), access.hosted_world_media_owner("managed"), {})
    foreign = media.stage_image(image.getvalue(), access.hosted_world_media_owner("foreign"), {})
    markdown = f"# First source\n\nThe pilot town has a well.\n\n![The well](dmb-media:{asset['asset_id']})\n"
    request = {
        "document_id": record["document_id"], "markdown": markdown,
        "expected_revision": record["revision"],
    }

    assert hosted.client.request("GET", document, session="other-session").status_code == 403
    assert hosted.client.request("GET", f"{document}/snapshot?world_id=foreign").status_code == 403
    assert hosted.client.request("POST", f"{editor}/prepare", json=request, session="other-session").status_code == 403
    foreign_request = {**request, "markdown": markdown.replace(str(asset["asset_id"]), str(foreign["asset_id"]))}
    denied = hosted.client.request("POST", f"{editor}/prepare", json=foreign_request)
    assert denied.status_code == 422, denied.text
    prepared = hosted.client.request("POST", f"{editor}/prepare", json=request)
    assert prepared.status_code == 200, prepared.text
    token = prepared.json()["writer_confirm_token"]
    commit = {**request, "writer_confirm_token": token}
    assert hosted.client.request("POST", f"{editor}/commit", json=commit, session="other-session").status_code == 403
    committed = hosted.client.request("POST", f"{editor}/commit", json=commit)
    assert committed.status_code == 200, committed.text
    reopened = hosted.client.request("GET", f"{document}/snapshot")
    assert reopened.status_code == 200, reopened.text
    assert reopened.headers["cache-control"] == "no-store"
    assert "The pilot town has a well." in reopened.json()["markdown"]
    assert f"dmb-media:{asset['asset_id']}" in reopened.json()["markdown"]


    from apps.live_control_server.services import graph_preview_runner, graph_run_registry

    runs = {}

    def run_extraction(*, source_artifact_id, **kwargs):
        run_id = str(uuid4())
        run = SimpleNamespace(
            run_id=run_id, source_artifact_id=source_artifact_id, source_domain="worldbuilding",
            model_dump=lambda **kwargs: {"run_id": run_id},
        )
        runs[run_id] = run
        return SimpleNamespace(run=run, failure_kind=None, diagnostics=[])

    monkeypatch.setattr(graph_preview_runner, "run_worldbuilding_production_extraction", run_extraction)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", runs.__getitem__)
    launch = "/api/live/graph-preview/extraction-runs"
    snapshot = reopened.json()
    extraction = {
        "document_id": record["document_id"],
        "expected_revision": snapshot["record"]["revision"],
        "expected_content_sha256": snapshot["content_sha256"],
    }
    native_source = f"{document}/native-world-source"
    revision = snapshot["record"]["revision"]
    native_reads = []

    def read_native_source(_root, document_id, *, expected_revision):
        native_reads.append((document_id, expected_revision))
        return workspace_documents.NativeWorldSourceAdmissionStatus(
            state="pending", world_id="managed", document_id=document_id,
            loaded_revision=revision, body_sha256=snapshot["content_sha256"],
            admission_id="test-admission", space_id="native-managed",
        )

    monkeypatch.setattr(workspace_documents, "read_native_world_source_status", read_native_source)
    assert hosted.client.request("GET", native_source, session="other-session").status_code == 403
    assert hosted.client.request("GET", native_source + "?world_id=managed").status_code == 403
    assert hosted.client.request("GET", native_source + "?expected_revision=1&expected_revision=2").status_code == 403
    assert not native_reads
    for query, expected in (("", None), (f"?expected_revision={revision}", revision)):
        status = hosted.client.request("GET", native_source + query)
        assert status.status_code == 200, status.text
        assert status.json()["document_id"] == record["document_id"]
        assert status.json()["loaded_revision"] == revision
        assert status.headers["cache-control"] == "no-store"
        assert native_reads[-1] == (record["document_id"], expected)

    assert snapshot["record"]["target_relpath"] is None
    assert hosted.client.request("POST", launch, json=extraction, session="other-session").status_code == 403
    assert not runs
    started = hosted.client.request("POST", launch, json=extraction)
    assert started.status_code == 200, started.text
    exact_run = f"{launch}/{started.json()['run']['run_id']}"
    for route in (exact_run, f"{exact_run}/build-context"):
        assert hosted.client.request("GET", route, session="other-session").status_code == 403
        read = hosted.client.request("GET", route)
        assert read.status_code == 200, read.text
        assert read.headers["cache-control"] == "no-store"

    reviewed_runs = []

    def read_review_package(run_id):
        reviewed_runs.append(run_id)
        raise extract_promote.ExtractPromoteError(
            "Review package is still being prepared.",
            code="review_package_pending",
            status_code=409,
        )

    monkeypatch.setattr(extract_promote, "get_exact_run_review_package", read_review_package)
    run_id = started.json()["run"]["run_id"]
    review_route = f"/api/live/extract-promote/runs/{run_id}/review-package"
    assert hosted.client.request("GET", review_route, session="other-session").status_code == 403
    assert not reviewed_runs
    read = hosted.client.request("GET", review_route)
    assert read.status_code == 409, read.text
    assert reviewed_runs == [run_id]
    assert read.headers["cache-control"] == "no-store"


    reviewed_runs.clear()
    monkeypatch.setattr(extract_promote, "get_worldbuilding_frozen_spans", read_review_package)
    spans_route = f"/api/live/extract-promote/runs/{run_id}/frozen-source-spans"
    assert hosted.client.request("GET", spans_route, session="other-session").status_code == 403
    assert not reviewed_runs
    read = hosted.client.request("GET", spans_route)
    assert read.status_code == 409, read.text
    assert reviewed_runs == [run_id]
    assert read.headers["cache-control"] == "no-store"
    corrections_route = f"/api/live/extract-promote/runs/{run_id}/evidence-corrections"
    source_id = runs[run_id].source_artifact_id
    digest = "a" * 64
    correction = {
        "parentRunId": run_id,
        "expectedParentRevision": 1,
        "worldId": "managed",
        "sourceArtifactId": source_id,
        "sourceSha256": digest,
        "spanIndexSha256": digest,
        "parentCandidateSha256": digest,
        "corrections": [{
            "assertionId": "assertion",
            "evidenceIndex": 0,
            "expectedRefSha256": digest,
            "parts": [{
                "sourceSpanRefId": "span",
                "quoteAssignments": [{"originalQuoteIndex": 0, "replacementQuote": "Exact evidence"}],
            }],
        }],
    }
    corrections = []

    def correct(payload):
        corrections.append((payload.world_id, payload.parent_run_id, payload.source_artifact_id))
        raise extract_promote.ExtractPromoteError("Correction reached service.", code="probe_reached", status_code=409)

    monkeypatch.setattr(extract_promote, "correct_exact_run_evidence", correct)
    assert hosted.client.request("POST", corrections_route, session="other-session", json=correction).status_code == 403
    mismatch = hosted.client.request("POST", corrections_route, json={**correction, "parentRunId": "different"})
    assert mismatch.status_code == 422, mismatch.text
    assert not corrections
    result = hosted.client.request("POST", corrections_route, json=correction)
    assert result.status_code == 409, result.text
    assert corrections == [("managed", run_id, source_id)]


def test_hosted_saved_artwork_owner_and_original(hosted, application_state_dsn):
    from io import BytesIO

    from PIL import Image
    from application_state import media

    world_id = next(iter(access.hosted_auth.hosted_world_access()))
    image = BytesIO()
    Image.new("RGB", (2, 2)).save(image, format="PNG")
    payload = image.getvalue()
    asset = media.stage_image(payload, access.hosted_world_media_owner(world_id), {})
    path = f"/api/live/media/images/{asset['asset_id']}"
    media.stage_image(payload, access.hosted_world_media_owner("foreign"), {})
    library_path = f"/api/live/media/images/library?world_id={world_id}"
    library = hosted.client.request("GET", library_path)
    assert library.status_code == 200, library.text
    assert [str(asset["asset_id"])] == [item["asset_id"] for item in library.json()["items"]]
    assert hosted.client.request("GET", library_path, session="other-session").status_code == 403
    assert hosted.client.request("GET", library_path + "&world_id=foreign").status_code == 403
    capabilities = hosted.client.request("GET", f"/api/live/media/images/capabilities?world_id={world_id}")
    assert capabilities.status_code == 200, capabilities.text
    assert capabilities.json()["library_ready"] is True
    preview = hosted.client.request("GET", path)
    assert preview.status_code == 200, preview.text
    assert preview.json()["data_url"].startswith("data:image/png;base64,")
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    metadata = hosted.client.request("GET", f"{path}/metadata")
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["asset_id"] == str(asset["asset_id"])
    original = hosted.client.request("GET", f"{path}/original")
    assert original.status_code == 200, original.text
    assert original.content == payload
    assert original.headers["cache-control"] == "no-store"
    for suffix in ("metadata", "original"):
        assert hosted.client.request("GET", f"{path}/{suffix}", session="other-session").status_code == 403
        assert hosted.client.request("GET", f"{path}/{suffix}?world_id={world_id}").status_code == 403


def test_hosted_plan_context_requires_exact_owned_world(hosted):
    world_id = next(iter(access.hosted_auth.hosted_world_access()))
    for query, version in ((f"world_id={world_id}", "v1"), (f"scope_mode=world&world_id={world_id}", "v2")):
        path = f"/api/live/plan-view?{query}"
        response = hosted.client.request("GET", path)
        assert response.status_code == 200, response.text
        assert response.json()["world_id"] == world_id
        assert response.json()["schema_version"] == f"dmb_managed_world_plan_context_{version}"
        assert response.headers["cache-control"] == "no-store"
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
    for query in ("", f"?world_id={world_id}&world_id={world_id}", f"?world_id={world_id}&campaign_id=other"):
        assert hosted.client.request("GET", f"/api/live/plan-view{query}").status_code == 403


def test_hosted_plan_inventory_reopens_an_exact_owned_plan(hosted, application_state_dsn, tmp_path):
    from apps.live_control_server.services.workspace_document_registry import create_world_owned_plan_v2

    plan = create_world_owned_plan_v2(tmp_path, world_id="managed", title="Hosted session plan")
    base = "/api/live/workspace-documents"
    inventory = f"{base}/world-plans?world_id=managed"
    snapshot = f"{base}/{plan.document_id}/snapshot"
    listed = hosted.client.request("GET", inventory)
    assert listed.status_code == 200, listed.text
    assert [r["document_id"] for r in listed.json()["records"]] == [plan.document_id]
    read = hosted.client.request("GET", snapshot)
    assert read.status_code == 200, read.text
    assert read.json()["record"]["document_id"] == plan.document_id
    assert read.json()["record"]["world_id"] == "managed"
    for path in (inventory, snapshot):
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
    for path in (inventory + "&scope_mode=world", snapshot + "?view=committed", f"{base}/{plan.document_id}"):
        assert hosted.client.request("GET", path).status_code == 403


def test_hosted_owner_saves_exact_world_plan(hosted, application_state_dsn, tmp_path):
    from apps.live_control_server.services.workspace_document_registry import create_world_owned_plan_v2

    plan = create_world_owned_plan_v2(tmp_path, world_id="managed", title="Before")
    editor = "/api/live/tiptap/markdown-write"
    body = {
        "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
        "scope_mode": "world",
        "world_id": "managed",
        "document_id": plan.document_id,
        "title": "After",
        "markdown": "# After\n\nA saved Plan.\n",
        "expected_revision": plan.revision,
    }
    assert hosted.client.request("POST", f"{editor}/prepare", json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", f"{editor}/prepare", json={**body, "world_id": "foreign"}).status_code == 403
    prepared = hosted.client.request("POST", f"{editor}/prepare", json=body)
    assert prepared.status_code == 200, prepared.text
    commit = {
        **body,
        "schema_version": "dmb_tiptap_markdown_write_commit_v2",
        "expected_revision": prepared.json()["registry_revision"],
        "writer_confirm_token": prepared.json()["writer_confirm_token"],
    }
    assert hosted.client.request("POST", f"{editor}/commit", json=commit, session="other-session").status_code == 403
    saved = hosted.client.request("POST", f"{editor}/commit", json=commit)
    assert saved.status_code == 200, saved.text
    snapshot = hosted.client.request("GET", f"/api/live/workspace-documents/{plan.document_id}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["record"]["title"] == "After"
    assert snapshot.json()["markdown"] == body["markdown"]
    path = f"/api/live/workspace-documents/{plan.document_id}/committed-revision"
    committed = hosted.client.request("GET", path)
    assert committed.status_code == 200, committed.text
    assert committed.json()["world_id"] == "managed"
    assert committed.json()["document_id"] == plan.document_id
    assert committed.json()["markdown"] == body["markdown"]
    assert committed.json()["content_sha256"] == saved.json()["normalized_content_sha256"]
    assert committed.headers["cache-control"] == "no-store"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=managed").status_code == 403


def test_hosted_owner_creates_lists_and_reopens_plan(hosted, application_state_dsn):
    base = "/api/live/workspace-documents"
    create = f"{base}/world-plans"
    body = {
        "schema_version": "dmb_workspace_document_create_v2",
        "scope_mode": "world",
        "world_id": "managed",
        "title": "New hosted Plan",
    }
    assert hosted.client.request("POST", create, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", create, json={**body, "world_id": "foreign"}).status_code == 403
    assert hosted.client.request("POST", create + "?world_id=managed", json=body).status_code == 403
    created = hosted.client.request("POST", create, json=body)
    assert created.status_code == 200, created.text
    record = created.json()
    assert record["world_id"] == "managed"
    assert record["campaign_id"] is None
    assert created.headers["cache-control"] == "no-store"
    listed = hosted.client.request("GET", create + "?world_id=managed")
    assert listed.status_code == 200, listed.text
    assert [row["document_id"] for row in listed.json()["records"]] == [record["document_id"]]
    snapshot = hosted.client.request("GET", f"{base}/{record['document_id']}/snapshot")
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["record"]["title"] == body["title"]


def test_hosted_owner_prepares_exact_saved_plan_for_play(hosted, application_state_dsn, tmp_path, monkeypatch):
    from application_state.content.service import commit_plan
    from apps.live_control_server.services.workspace_document_registry import create_world_owned_plan_v2
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN

    from tests.test_prepared_tables import source

    plan = create_world_owned_plan_v2(tmp_path, world_id="managed", title="Play source")
    commit_plan(plan.document_id, V2_SOURCE_MARKDOWN + "\n\n" + source(), expected_world_id="managed", expected_revision=plan.revision)
    saved = hosted.client.request("GET", f"/api/live/workspace-documents/{plan.document_id}/committed-revision")
    assert saved.status_code == 200, saved.text
    record = saved.json()
    body = {
        "playable_artifact_id": plan.document_id,
        "expected_playable_revision": record["revision_n"],
        "expected_playable_work_revision_id": record["work_revision_id"],
        "expected_playable_content_sha256": record["content_sha256"],
    }
    path = "/api/live/world-play-runs/v2/preparation?world_id=managed"
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path + "&world_id=managed", json=body).status_code == 403
    assert hosted.client.request("POST", path.replace("managed", "foreign"), json=body).status_code == 403
    result = hosted.client.request("POST", path, json=body)
    assert result.status_code == 200, result.text
    assert {k: result.json()["request"][k] for k in body} == body
    assert result.json()["scenes"]
    assert result.headers["cache-control"] == "no-store"
    from uuid import uuid4

    run_id = str(uuid4())
    base = f"/api/live/world-play-runs/v2/{run_id}"
    run_path = f"{base}?world_id=managed"
    receipt_path = f"{base}/creation?world_id=managed"
    intent = result.json()["request"]
    assert hosted.client.request("PUT", run_path, json=intent, session="other-session").status_code == 403
    assert hosted.client.request("PUT", run_path.replace("managed", "foreign"), json=intent).status_code == 403
    created = hosted.client.request("PUT", run_path, json=intent)
    assert created.status_code == 200, created.text
    receipt = created.json()
    assert receipt["run"]["run_id"] == run_id
    assert receipt["run"]["playable_work_revision_id"] == body["expected_playable_work_revision_id"]
    assert hosted.client.request("PUT", run_path, json=intent).json() == receipt
    assert hosted.client.request("GET", receipt_path).json() == receipt
    assert hosted.client.request("GET", receipt_path, session="other-session").status_code == 403
    assert hosted.client.request("POST", f"{base}/creation:cancel?world_id=managed", json=intent).json() == receipt

    runs = "/api/live/world-play-runs/v2"
    for path in (f"{runs}?world_id=managed", f"{runs}/active?world_id=managed", run_path):
        response = hosted.client.request("GET", path)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
        assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    opened = hosted.client.request("GET", run_path).json()
    assert opened["run_id"] == run_id
    assert opened["playable_work_revision_id"] == body["expected_playable_work_revision_id"]
    listed = hosted.client.request("GET", f"{runs}?world_id=managed").json()
    assert [record["run_id"] for record in listed["records"]] == [run_id]
    active = hosted.client.request("GET", f"{runs}/active?world_id=managed").json()
    assert active["world_id"] == "managed"

    commit_plan(plan.document_id, V2_SOURCE_MARKDOWN + "\nA newer Plan revision.\n", expected_world_id="managed", expected_revision=record["object_revision"])
    manifest_path = f"{base}/reference-manifest?world_id=managed"
    content_path = f"{base}/content?world_id=managed"
    pinned_path = f"/api/live/workspace-documents/{plan.document_id}/committed-revision/{record['revision_n']}"
    for path in (manifest_path, content_path, pinned_path):
        response = hosted.client.request("GET", path)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
    review_path = f"{base}/review?world_id=managed"
    review = hosted.client.request("GET", review_path)
    assert review.status_code == 200, review.text
    assert review.headers["cache-control"] == "no-store"
    assert hosted.client.request("GET", review_path, session="other-session").status_code == 403
    assert hosted.client.request("GET", review_path + "&world_id=foreign").status_code == 403
    evidence_path = "/api/live/world-session-evidence?world_id=managed"
    evidence = hosted.client.request("GET", evidence_path)
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()["sessions"] == []
    assert hosted.client.request("GET", evidence_path, session="other-session").status_code == 403
    revision_path = f"/api/live/world-session-evidence/{run_id}/revisions/1?world_id=managed"
    assert hosted.client.request("GET", revision_path, session="other-session").status_code == 403
    assert hosted.client.request("GET", revision_path + "&world_id=foreign").status_code == 403
    missing_revision = hosted.client.request("GET", revision_path)
    assert missing_revision.status_code == 404, missing_revision.text
    proposals = f"{base}/content/proposals"
    inventory = hosted.client.request("GET", proposals + "?world_id=managed")
    assert inventory.status_code == 200, inventory.text
    assert inventory.json() == {"proposals": []}
    exact_proposal = proposals + f"/{uuid4()}?world_id=managed"
    assert hosted.client.request("GET", exact_proposal, session="other-session").status_code == 403
    assert hosted.client.request("GET", exact_proposal + "&world_id=foreign").status_code == 403
    missing_proposal = hosted.client.request("GET", exact_proposal)
    assert missing_proposal.status_code == 404, missing_proposal.text
    manifest = hosted.client.request("GET", manifest_path).json()
    assert manifest["playable_content_sha256"] == body["expected_playable_content_sha256"]
    pinned = hosted.client.request("GET", pinned_path).json()
    assert pinned["markdown"] == record["markdown"]
    assert pinned["work_revision_id"] == body["expected_playable_work_revision_id"]

    from uuid import UUID

    from application_state.play_scene_edit.service import PlaySceneEditProposalService
    from apps.live_control_server.models.play_scene_edit_proposal import PlaySceneEditProposalRequest
    from apps.live_control_server.services.agent_play_surface_context import resolve_world_play_session_turn_snapshot

    edit = PlaySceneEditProposalRequest(
        run_revision=opened["run_revision"], scene_id=result.json()["scenes"][0]["scene_id"],
        instruction="Clarify what the party sees at the gate.",
        content_basis={
            "edition_revision": 0, "edition_revision_id": None,
            "content_sha256": body["expected_playable_content_sha256"],
        },
    )
    _, context_receipt = resolve_world_play_session_turn_snapshot(
        root=tmp_path, world_id="managed", run_id=run_id,
        run_revision=edit.run_revision, content_basis=edit.content_basis,
    )
    proposal_id = uuid4()
    PlaySceneEditProposalService().reserve(
        world_id="managed", run_id=UUID(run_id), proposal_id=proposal_id,
        request=edit.model_dump(mode="json"), context_receipt=context_receipt,
    )
    listed_proposals = hosted.client.request("GET", proposals + "?world_id=managed")
    assert listed_proposals.status_code == 200, listed_proposals.text
    saved_proposal = hosted.client.request("GET", proposals + f"/{proposal_id}?world_id=managed")
    assert saved_proposal.status_code == 200, saved_proposal.text
    assert saved_proposal.json()["proposal_id"] == str(proposal_id)
    assert saved_proposal.json()["status"] == "pending"
    assert listed_proposals.json()["proposals"] == [saved_proposal.json()]

    proposal_path = proposals + f"/{proposal_id}?world_id=managed"
    proposal_body = edit.model_dump(mode="json")
    assert hosted.client.request("POST", proposal_path, json=proposal_body, session="other-session").status_code == 403
    assert hosted.client.request("POST", proposal_path, json=proposal_body, origin=None).status_code == 403
    retry = hosted.client.request("POST", proposal_path, json=proposal_body)
    assert retry.status_code == 200, retry.text
    assert retry.json() == saved_proposal.json()

    from apps.live_control_server import config
    from apps.live_control_server.services import play_scene_edit_proposal
    from tests.test_play_scene_edit_proposal import Generator

    markdown = V2_SOURCE_MARKDOWN + "\n\n" + source()
    start, end = play_scene_edit_proposal.scene_body_range(markdown, edit.scene_id)
    generator = Generator(markdown[start:end] + "\nThe party sees an open gate and a watchful guard.\n")
    monkeypatch.setattr(config, "managed_world_data_root", lambda: tmp_path)
    monkeypatch.setattr(play_scene_edit_proposal.GenerationClient, "from_env", lambda: generator)
    monkeypatch.setattr(play_scene_edit_proposal, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(
        play_scene_edit_proposal, "load_buddy_model_policy",
        lambda **kwargs: {"actions": {"structured_generation": "writer"}, "models": {"writer": "test-model"}},
    )
    fresh_path = proposals + f"/{uuid4()}?world_id=managed"
    assert hosted.client.request("POST", fresh_path, json=proposal_body, origin=None).status_code == 403
    assert generator.calls == []
    generated = hosted.client.request("POST", fresh_path, json=proposal_body)
    assert generated.status_code == 200, generated.text
    assert generated.json()["status"] == "ready", generated.text
    assert hosted.client.request("POST", fresh_path, json=proposal_body).json() == generated.json()
    assert len(generator.calls) == 1


    tables_path = f"{base}/prepared-tables?world_id=managed"
    table_response = hosted.client.request("GET", tables_path)
    assert table_response.status_code == 200, table_response.text
    inventory = table_response.json()
    table = inventory["tables"][0]
    assert table["title"] == "Weather"
    assert hosted.client.request("GET", tables_path, session="other-session").status_code == 403
    roll_path = f"{base}/prepared-tables/commands/{uuid4()}?world_id=managed"
    roll = {
        "expected_run_revision": inventory["run"]["run_revision"],
        **inventory["source"],
        "table_id": table["table_id"],
        "table_sha256": table["table_sha256"],
        "physical_value": 2,
    }
    assert hosted.client.request("PUT", roll_path, json=roll, session="other-session").status_code == 403
    recorded = hosted.client.request("PUT", roll_path, json=roll)
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["receipt"]["outcome"] == "Dry"
    receipts_path = f"{base}/prepared-tables/receipts?world_id=managed&limit=1"
    receipts_response = hosted.client.request("GET", receipts_path)
    assert receipts_response.status_code == 200, receipts_response.text
    assert receipts_response.json()["receipts"] == [recorded.json()["receipt"]]
    assert hosted.client.request("GET", receipts_path, session="other-session").status_code == 403
    assert hosted.client.request("GET", receipts_path + "&world_id=foreign").status_code == 403
    command_path = f"{base}/content/commands/{uuid4()}?world_id=managed"
    assert hosted.client.request("GET", command_path, session="other-session").status_code == 403
    missing_command = hosted.client.request("GET", command_path)
    assert missing_command.status_code == 404, missing_command.text
    assert hosted.client.request("PUT", roll_path, json=roll).json()["receipt"] == recorded.json()["receipt"]

    from apps.live_control_server.services.play_run_edition import read_content

    content = read_content(run_id=run_id, world_id="managed")
    reflections = "The party returned safely after scouting the gate."
    review_command_path = f"{base}/review/commands/{uuid4()}?world_id=managed"
    review_command = {
        "action": "end", "expected_revision": 0,
        "expected_run_revision": content.observed_run_revision,
        "expected_content_sha256": content.content_sha256, "final_thoughts": reflections,
    }
    assert hosted.client.request("PUT", review_command_path, json=review_command, origin=None).status_code == 403
    assert hosted.client.request("PUT", review_command_path, json=review_command, session="other-session").status_code == 403
    ended = hosted.client.request("PUT", review_command_path, json=review_command)
    assert ended.status_code == 200, ended.text
    assert hosted.client.request("PUT", review_command_path, json=review_command).json() == ended.json()
    indexed = hosted.client.request("GET", evidence_path)
    assert indexed.status_code == 200, indexed.text
    assert [item["run_id"] for item in indexed.json()["sessions"]] == [run_id]
    saved = hosted.client.request("GET", revision_path)
    assert saved.status_code == 200, saved.text
    assert saved.headers["cache-control"] == "no-store"
    packet = saved.json()
    assert (packet["world_id"], packet["run_id"], packet["review_revision"]) == ("managed", run_id, 1)
    assert [(item["kind"], item["text"]) for item in packet["sources"]] == [
        ("closing_reflections", reflections),
    ]
    denied = hosted.client.request("GET", revision_path, session="other-session")
    assert denied.status_code == 403
    assert reflections not in denied.text

    save_review_path = f"{base}/review/commands/{uuid4()}?world_id=managed"
    review_basis = {
        "expected_run_revision": content.observed_run_revision,
        "expected_content_sha256": content.content_sha256,
    }
    save_review = {
        **review_basis, "action": "save", "expected_revision": 1,
        "draft_markdown": "# Session notes\n\nThe gate was open.",
    }
    saved_review = hosted.client.request("PUT", save_review_path, json=save_review)
    assert saved_review.status_code == 200, saved_review.text
    assert saved_review.json()["checkpoint"] == ended.json()["checkpoint"]
    assert saved_review.json()["draft_markdown"] == save_review["draft_markdown"]
    reopen_path = f"{base}/review/commands/{uuid4()}?world_id=managed"
    reopen_review = {**review_basis, "action": "reopen", "expected_revision": 2}
    assert hosted.client.request("PUT", reopen_path, json=reopen_review, origin=None).status_code == 403
    reopened_review = hosted.client.request("PUT", reopen_path, json=reopen_review)
    assert reopened_review.status_code == 200, reopened_review.text
    assert reopened_review.json()["status"] == "playing"
    assert reopened_review.json()["draft_markdown"] == save_review["draft_markdown"]
    assert hosted.client.request("GET", revision_path).json() == packet

    from tests.integration.test_build_images_postgres import saved_image

    artwork = saved_image(access.hosted_world_media_owner("managed"))
    foreign_artwork = saved_image(access.hosted_world_media_owner("foreign"))
    edition_path = f"{base}/content/commands/{uuid4()}?world_id=managed"
    edition = {
        "schema_version": "dmb_world_play_run_content_commit_v1",
        "expected_origin": content.origin.model_dump(mode="json"),
        "expected_edition_revision": content.edition_revision,
        "expected_content_sha256": content.content_sha256,
        "markdown": content.markdown + f"\n\n![Gate](dmb-media:{artwork['asset_id']})\n",
    }
    assert hosted.client.request("PUT", edition_path, json=edition, session="other-session").status_code == 403
    assert hosted.client.request("PUT", edition_path, json=edition, origin=None).status_code == 403
    foreign_edition = {
        **edition,
        "markdown": edition["markdown"].replace(str(artwork["asset_id"]), str(foreign_artwork["asset_id"])),
    }
    denied = hosted.client.request("PUT", edition_path, json=foreign_edition)
    assert denied.status_code == 422, denied.text
    committed_edition = hosted.client.request("PUT", edition_path, json=edition)
    assert committed_edition.status_code == 200, committed_edition.text
    assert hosted.client.request("PUT", edition_path, json=edition).json() == committed_edition.json()
    reopened_edition = hosted.client.request("GET", content_path)
    assert reopened_edition.status_code == 200, reopened_edition.text
    assert reopened_edition.json()["markdown"] == edition["markdown"]

    session_path = f"/api/live/world-workspace/sessions/{run_id}"
    lifecycle = {
        "expected_revision": reopened_edition.json()["observed_run_revision"],
        "expected_content_revision": reopened_edition.json()["edition_revision"],
    }
    moved = hosted.client.request("POST", f"{session_path}/trash?world_id=managed", json=lifecycle)
    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "trashed"
    restore = {**lifecycle, "expected_revision": moved.json()["revision"]}
    restored = hosted.client.request("POST", f"{session_path}/restore?world_id=managed", json=restore)
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "active"
    assert hosted.client.request("GET", content_path).json()["markdown"] == edition["markdown"]


def test_hosted_statblock_picker_reads_only_owned_world(hosted, application_state_dsn, tmp_path, monkeypatch):
    from apps.live_control_server.models.threat_draft import CreateWorldThreatDraftRequest
    from apps.live_control_server.routes import threat_drafts, world_mechanics_associations
    from apps.live_control_server.services.threat_draft_store import create_threat_draft

    monkeypatch.setattr(threat_drafts, "statblock_data_root", lambda _root: tmp_path)
    monkeypatch.setattr(world_mechanics_associations, "resolve_managed_world_binding", lambda _world: None)
    for world_id in ("managed", "foreign"):
        create_threat_draft(tmp_path, CreateWorldThreatDraftRequest(
            scope_mode="world", world_id=world_id, campaign_id=None,
            name=f"{world_id} creature", description="An authored creature.",
            threat_kind="creature", created_by="gm",
            generation_intent={"ruleset": {"system": "dnd5e", "edition": "2024"}},
            graph_context_snapshot={"graph_revision_id": None},
        ))
    drafts = "/api/live/threat-drafts?world_id=managed&limit=100&offset=0"
    associations = "/api/live/world-mechanics/associations?world_id=managed"
    for path in (drafts, associations):
        result = hosted.client.request("GET", path)
        assert result.status_code == 200, result.text
        assert result.headers["cache-control"] == "no-store"
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
        assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    assert [row["world_id"] for row in hosted.client.request("GET", drafts).json()["drafts"]] == ["managed"]


def test_hosted_exact_statblock_read_authorizes_world_and_preserves_portrait(hosted, monkeypatch):
    from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
    from apps.live_control_server.routes import agent, statblock_candidates
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    draft = "12345678-1234-1234-1234-123456789abc"
    revision = "rev_exact"
    review = "87654321-1234-1234-1234-123456789abc"
    regions = [{"page": 2}]
    calls = []

    def read_exact(_root, **selectors):
        calls.append(selectors)
        return {"resource": {"provenance": {"accepted_through": {PDF_REVIEW_PROVENANCE: {
            "world_id": "managed", "review_id": review, "regions": regions,
        }}}}}

    def read_review(world_id, review_id, request):
        require_build_pdf_access(request, world_id)
        assert str(review_id) == review
        return {"regions": regions, "artwork": {"jpeg_base64": "portrait"}}

    monkeypatch.setattr(statblock_candidates, "statblock_data_root", lambda root: root)
    monkeypatch.setattr(statblock_candidates.saved_versions, "open_version", read_exact)
    monkeypatch.setattr(agent, "get_pdf_statblock_review", read_review)
    path = f"/api/live/threat-drafts/{draft}/mechanics-revisions/{revision}?world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    assert hosted.client.request("GET", path + "&other=selector").status_code == 403
    assert calls == []
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["pdf_portrait"] == "portrait"
    assert calls == [{"world_id": "managed", "draft_id": draft, "revision_id": revision}]


def test_hosted_ingest_lists_and_reopens_saved_source_in_owned_world(hosted, monkeypatch):
    from uuid import UUID
    from apps.live_control_server.models.saved_recap_runs import (
        SavedRecapRun, SavedRecapRunsResponse, SavedRecapSourceResponse,
    )
    from apps.live_control_server.services import ingest_run_catalog

    source = UUID("12345678-1234-1234-1234-123456789abc")
    scope = {"managed_world_id": "managed", "native_world_id": "world:managed", "binding_version": 1}
    run = SavedRecapRun(
        run_id="recap-run", run_revision=2, run_status="reviewable", source_artifact_id="recap",
        campaign_id="campaign", session_id=None, profile_id=None, created_at=None, updated_at=None,
        source_revision_id=source, source_sha256="a" * 64,
    )
    calls = []

    def list_runs(*, root, **selectors):
        calls.append(selectors)
        return SavedRecapRunsResponse(**scope, runs=[run])

    def read_source(*, root, **selectors):
        calls.append(selectors)
        return SavedRecapSourceResponse(**scope, run=run, source_prose="Frozen recap.")

    monkeypatch.setattr(ingest_run_catalog, "list_saved_recap_runs", list_runs)
    monkeypatch.setattr(ingest_run_catalog, "read_saved_recap_source", read_source)
    base = "/api/live/graph-preview/extraction-runs"
    catalog = f"{base}?managed_world_id=managed&campaign_id=campaign"
    inspection = (
        f"{base}/{run.run_id}/recap-inspection?managed_world_id=managed"
        f"&expected_run_revision=2&source_revision_id={source}"
    )
    for path in (catalog, inspection):
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
        assert hosted.client.request("GET", path + "&unexpected=1").status_code == 403
        assert hosted.client.request("GET", path + "&managed_world_id=managed").status_code == 403
    assert calls == []
    response = hosted.client.request("GET", catalog)
    assert response.status_code == 200, response.text
    assert response.json()["runs"][0]["sourceRevisionId"] == str(source)
    response = hosted.client.request("GET", inspection)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["sourceProse"] == "Frozen recap."
    assert calls == [
        {"managed_world_id": "managed", "campaign_id": "campaign"},
        {"managed_world_id": "managed", "run_id": run.run_id,
         "expected_run_revision": 2, "source_revision_id": source},
    ]


def test_hosted_ingest_candidate_projection_is_owned_and_exact(hosted, monkeypatch):
    from apps.live_control_server.services import exact_run_candidate_projection

    calls = []

    def read_candidate(_root, run_id, world_id):
        calls.append((run_id, world_id))
        return SavedCandidate()

    class SavedCandidate:
        def model_dump(self, *, mode, by_alias):
            return {"runId": "recap-run", "managedWorldId": "managed"}

    monkeypatch.setattr(exact_run_candidate_projection, "build_exact_run_candidate_projection", read_candidate)
    path = "/api/live/graph-preview/extraction-runs/recap-run/candidate-projection?managed_world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&campaign_id=foreign").status_code == 403
    assert hosted.client.request("GET", path + "&managed_world_id=foreign").status_code == 403
    assert calls == []
    result = hosted.client.request("GET", path)
    assert result.status_code == 200, result.text
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {"runId": "recap-run", "managedWorldId": "managed"}
    assert calls == [("recap-run", "managed")]


def test_hosted_combat_lists_and_reopens_only_owned_encounters(hosted, application_state_dsn, monkeypatch):
    from application_state.combat_encounters.service import create_encounter
    from application_state.combat_encounters.types import CreateCombatEncounterRequest
    from apps.live_control_server.routes import combat_encounters

    monkeypatch.setattr(combat_encounters, "_verified_world", lambda world_id: world_id)
    owned = create_encounter(world_id="managed", request=CreateCombatEncounterRequest(title="Owned encounter"))
    foreign = create_encounter(world_id="foreign", request=CreateCombatEncounterRequest(title="Foreign encounter"))
    base = "/api/live/combat/encounters"
    catalog = f"{base}?world_id=managed"
    detail = f"{base}/{owned.encounter_id}?world_id=managed"
    for path in (catalog, detail):
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
        assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    result = hosted.client.request("GET", catalog)
    assert result.status_code == 200, result.text
    assert result.json() == [owned.model_dump(mode="json", by_alias=True)]
    result = hosted.client.request("GET", detail)
    assert result.status_code == 200, result.text
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == owned.model_dump(mode="json", by_alias=True)
    assert hosted.client.request("GET", f"{base}/{foreign.encounter_id}?world_id=managed").status_code == 404
    assert hosted.client.request("POST", catalog, origin=None, json={"title": "Denied"}).status_code == 403


def test_hosted_combat_create_save_and_reload_require_owned_world_and_origin(
    hosted, application_state_dsn, monkeypatch,
):
    from application_state.combat_encounters.service import create_encounter
    from application_state.combat_encounters.types import CreateCombatEncounterRequest
    from apps.live_control_server.routes import combat_encounters

    monkeypatch.setattr(combat_encounters, "_verified_world", lambda world_id: world_id)
    base = "/api/live/combat/encounters"
    catalog = f"{base}?world_id=managed"
    create = {"title": "Hosted rehearsal"}
    assert hosted.client.request("POST", catalog, origin=None, json=create).status_code == 403
    assert hosted.client.request("POST", catalog, session="other-session", json=create).status_code == 403
    assert hosted.client.request("GET", catalog).json() == []
    result = hosted.client.request("POST", catalog, json=create)
    assert result.status_code == 200, result.text
    created = result.json()
    detail = f"{base}/{created['encounter_id']}?world_id=managed"
    save = {"expected_revision": 1, "draft": {**created["draft"], "title": "Saved rehearsal"}}
    assert hosted.client.request("PUT", detail, origin=None, json=save).status_code == 403
    foreign = create_encounter(world_id="foreign", request=CreateCombatEncounterRequest(title="Foreign"))
    assert hosted.client.request("PUT", f"{base}/{foreign.encounter_id}?world_id=managed", json=save).status_code == 404
    result = hosted.client.request("PUT", detail, json=save)
    assert result.status_code == 200, result.text
    assert result.json()["revision"] == 2
    assert result.json()["draft"]["title"] == "Saved rehearsal"
    assert hosted.client.request("GET", detail).json() == result.json()
    assert hosted.client.request("PUT", detail, json=save).status_code == 409


def test_hosted_combat_saved_revision_selection_and_preview(hosted, monkeypatch):
    from apps.live_control_server.routes import combat_encounters, statblock_candidates
    from application_state.errors import ApplicationStateConflictError

    draft = "12345678-1234-1234-1234-123456789abc"
    history = f"/api/live/threat-drafts/{draft}/mechanics-revisions?world_id=managed&offset=0"
    preview = "/api/live/combat/encounters/saved-mechanics/preview?world_id=managed"
    locator = {
        "provider": "dungeonmind", "contract": "dungeonmind.dungeonbuddy-statblocks",
        "contract_version": "1.0.0", "statblock_id": "sb_example", "revision_id": "rev_example",
        "definition_digest": "sha256:" + "a" * 64,
    }
    body = {"draft_id": draft, "locator": locator}
    calls = []

    def list_versions(_root, **selectors):
        calls.append(selectors)
        return {"original": locator, "operations": []}

    def read_preview(*, world_id, draft_id, locator):
        calls.append((world_id, str(draft_id), locator.revision_id))
        raise ApplicationStateConflictError("No exact proof for that revision")

    monkeypatch.setattr(statblock_candidates, "statblock_data_root", lambda root: root)
    monkeypatch.setattr(statblock_candidates.saved_versions, "list_versions", list_versions)
    monkeypatch.setattr(combat_encounters, "_verified_world", lambda world_id: world_id)
    monkeypatch.setattr(combat_encounters.combat_mechanics, "preview_saved_override", read_preview)
    assert hosted.client.request("GET", history, session="other-session").status_code == 403
    assert hosted.client.request("GET", history + "&offset=1").status_code == 403
    assert hosted.client.request("POST", preview, origin=None, json=body).status_code == 403
    assert hosted.client.request("POST", preview, session="other-session", json=body).status_code == 403
    assert calls == []
    listed = hosted.client.request("GET", history)
    assert listed.status_code == 200, listed.text
    assert listed.headers["cache-control"] == "no-store"
    assert listed.json()["original"] == locator
    refused = hosted.client.request("POST", preview, json=body)
    assert refused.status_code == 409, refused.text
    assert calls == [
        {"world_id": "managed", "draft_id": draft, "limit": 50, "offset": 0},
        ("managed", draft, "rev_example"),
    ]


def test_hosted_combat_adoption_applies_and_reopens_exact_receipt(
    adoption_case, hosted, monkeypatch,
):
    p = adoption_case
    hosted.records["elderwyld"] = _record("elderwyld", OWNER, p.binding.native_world_id)
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({"elderwyld": [OWNER, OTHER_OWNER]}))
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(p.root))
    history = p.adopt_url
    operation = p.intent["operation_id"]
    inspect = history.replace("mechanics-adoptions?", f"mechanics-adoptions/{operation}?")
    assert hosted.client.request("POST", history, origin=None, json=p.intent).status_code == 403
    assert hosted.client.request("POST", history, session="other-session", json=p.intent).status_code == 403
    assert hosted.client.request("GET", history).json()["receipts"] == []
    result = hosted.client.request("POST", history, json=p.intent)
    assert result.status_code == 200, result.text
    outcome = result.json()
    assert outcome["receipt"]["operation_id"] == operation
    assert outcome["receipt"]["committed_revision"] == 3
    assert outcome["encounter"]["draft"]["entities"][0]["mechanics_snapshot"]["locator"] == p.locator
    assert hosted.client.request("GET", p.encounter_url).json() == outcome["encounter"]
    assert hosted.client.request("GET", inspect, session="other-session").status_code == 403
    assert hosted.client.request("GET", inspect).json() == outcome
    assert hosted.client.request("GET", history).json()["receipts"] == [outcome["receipt"]]
    assert hosted.client.request("GET", history + f"&before_operation_id={operation}").json()["receipts"] == []
    assert hosted.client.request("POST", p.cancel_url, json=p.intent).json() == outcome


@pytest.mark.parametrize("preview_kind", ["accepted-mechanics", "world-mechanics"])
def test_hosted_combat_adds_actor_from_exact_preview(combat, hosted, monkeypatch, preview_kind):
    from apps.live_control_server.routes import combat_encounters
    from tests.test_combat_direct_mechanics import body as direct_body
    from tests.test_combat_exact_world_mechanics import body as linked_body

    p = combat
    record = _record("elderwyld", OWNER, p.binding.native_world_id)
    hosted.records["elderwyld"] = record.model_copy(update={
        "native_graph_binding": record.native_graph_binding.model_copy(
            update={"binding_version": p.binding.binding_version},
        ),
    })
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({"elderwyld": [OWNER, OTHER_OWNER]}))
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(p.root))
    monkeypatch.setattr(combat_encounters, "_verified_world", lambda world_id: world_id)
    path = f"/api/live/combat/encounters/{preview_kind}/preview?world_id=elderwyld"
    if preview_kind == "accepted-mechanics":
        selection = {"draft_id": p.draft.draft_id, "draft_version": p.draft.version}
        build_save = direct_body
    else:
        selection = p.selection
        build_save = linked_body
    assert hosted.client.request("POST", path, origin=None, json=selection).status_code == 403
    assert hosted.client.request("POST", path, session="other-session", json=selection).status_code == 403
    assert hosted.client.request("POST", path + "&world_id=foreign", json=selection).status_code == 403
    result = hosted.client.request("POST", path, json=selection)
    assert result.status_code == 200, result.text
    assert result.headers["cache-control"] == "no-store"
    snapshot = result.json()
    assert snapshot["locator"]["revision_id"] == p.revision.revision_id
    saved = hosted.client.request("PUT", p.url, json=build_save(p, snapshot, count=1))
    assert saved.status_code == 200, saved.text
    assert saved.json()["draft"]["entities"][0]["mechanics_snapshot"] == snapshot
    assert hosted.client.request("GET", p.url).json() == saved.json()


def test_hosted_conversation_starts_and_reopens_in_exact_world(hosted, application_state_dsn, monkeypatch):
    from apps.live_control_server.routes import agent, conversation_library

    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    monkeypatch.setattr(conversation_library, "_verified_world_id", lambda world_id: world_id)
    base = "/api/live/agent/worlds/managed/conversation"
    command = str(uuid4())
    body = {
        "command_id": command, "expected_pointer_revision": 0,
        "expected_active_conversation_id": None,
    }
    assert hosted.client.request("GET", base, session=None).status_code == 401
    assert hosted.client.request("GET", base, session="other-session").status_code == 403
    assert hosted.client.request("POST", base + "/new", origin=None, json=body).status_code == 403
    assert hosted.client.request("POST", base + "/new", session="other-session", json=body).status_code == 403
    response = hosted.client.request("POST", base + "/new", json=body)
    assert response.status_code == 200, response.text
    created = response.json()
    conversation_path = f"{base}s/{created['conversation_id']}"
    assert hosted.client.request("GET", conversation_path + "/name").status_code == 200
    assert hosted.client.request("GET", conversation_path + "/name", session="other-session").status_code == 403
    assert hosted.client.request("GET", conversation_path + f"/turns/{uuid4()}/retry-attempts").status_code == 404
    retry_context = f"{base}s/{created['conversation_id']}/retry-context"
    retry_query = f"?turn_ids={uuid4()}"
    assert hosted.client.request("GET", retry_context + retry_query, session="other-session").status_code == 403
    missing_turn = hosted.client.request("GET", retry_context + retry_query)
    assert missing_turn.status_code == 404, missing_turn.text
    assert missing_turn.headers["cache-control"] == "no-store"
    assert created["world_id"] == "managed"
    assert created["conversation_id"] == created["active_conversation_id"]
    reopened = hosted.client.request("GET", base)
    assert reopened.status_code == 200, reopened.text
    assert reopened.headers["cache-control"] == "no-store"
    assert reopened.json()["conversation_id"] == created["conversation_id"]
    status = hosted.client.request("GET", base + f"/commands/{command}?expected_pointer_revision=0&expected_active_conversation_id=null")
    assert status.status_code == 200, status.text
    for path in (base + "s", base + "s/active/messages", base + f"s/{created['conversation_id']}/messages"):
        response = hosted.client.request("GET", path)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert hosted.client.request("GET", path, session="other-session").status_code == 403


def test_hosted_citation_read_binds_world_and_saved_turn(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import agent_native_source_sections

    turn_id = uuid4()
    conversation_service = object()
    opened = Mock()
    opened.return_value.model_dump.return_value = {"text": "Saved passage"}
    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: conversation_service)
    monkeypatch.setattr(agent_native_source_sections, "open_native_source_section", opened)
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn_id}/native-source-sections/0"
    assert hosted.client.request("GET", path, session=None).status_code == 401
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?source_id=other").status_code == 422
    opened.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"text": "Saved passage"}
    opened.assert_called_once_with(
        world_id="managed", turn_id=turn_id, citation_index=0, service=conversation_service,
    )


def test_hosted_chat_turn_reaches_executor_with_exact_world_principal(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent

    execute = Mock()
    execute.return_value.model_dump.return_value = {"status": "completed"}
    monkeypatch.setattr(agent, "execute_agent_turn", execute)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: None)
    path = "/api/live/agent/turn"
    body = {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread", "turn_id": "turn",
        "surface": {"surface_id": "build", "instance_id": "build"},
        "owner_scope": {"kind": "world", "world_id": "managed"},
        "primary_work": None, "client_work_state": "none",
        "graph_request": {"mode": "none"}, "graph_selection": None,
        "message": "Open the saved source",
    }
    assert hosted.client.request("POST", path, session=None, json=body).status_code == 401
    assert hosted.client.request("POST", path, session="other-session", json=body).status_code == 403
    assert hosted.client.request("POST", path, origin=None, json=body).status_code == 403
    assert hosted.client.request("POST", path, json={**body, "owner_scope": None}).status_code == 403
    execute.assert_not_called()
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"status": "completed"}
    assert execute.call_count == 1
    principal = execute.call_args.kwargs["native_principal"]
    assert principal.managed_world_id == "managed"
    assert principal.subject == execute.call_args.kwargs["operator_subject"]


def test_hosted_native_excerpt_passes_exact_world_principal(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import agent_native_source_sections

    opened = Mock()
    opened.return_value.model_dump.return_value = {"content": "Saved excerpt"}
    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: None)
    monkeypatch.setattr(agent_native_source_sections, "open_native_body_excerpt", opened)
    turn_id = uuid4()
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn_id}/native-body-excerpts/0"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    opened.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.json() == {"content": "Saved excerpt"}
    assert response.headers["cache-control"] == "no-store"
    params = opened.call_args.kwargs
    assert params["world_id"] == params["principal"].managed_world_id == "managed"
    assert params["turn_id"] == turn_id


def test_hosted_saved_trace_requires_exact_world(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent

    service = Mock()
    service.list_context_trace_attempts.return_value = []
    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: service)
    turn_id = uuid4()
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn_id}/context-trace"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=foreign").status_code == 403
    service.list_context_trace_attempts.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    service.list_context_trace_attempts.assert_called_once_with(world_id="managed", turn_id=turn_id)


def test_hosted_build_proposal_history_is_world_scoped(hosted, monkeypatch):
    from unittest.mock import Mock

    from application_state.build_proposal import service
    from apps.live_control_server.routes import agent

    proposal_service = Mock()
    proposal_service.list.return_value = []
    monkeypatch.setattr(service, "BuildProposalService", lambda: proposal_service)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    conversation_id = uuid4()
    path = f"/api/live/agent/worlds/managed/build-proposals?conversation_id={conversation_id}"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&conversation_id=" + str(uuid4())).status_code == 422
    proposal_service.list.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["records"] == []
    proposal_service.list.assert_called_once_with("managed", conversation_id)


def test_hosted_image_history_passes_exact_owner(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import media_images

    service = Mock()
    service.list.return_value = []
    monkeypatch.setattr(media_images, "BuildImageService", lambda: service)
    conversation_id = uuid4()
    path = f"/api/live/media/images/preparations/list?world_id=managed&conversation_id={conversation_id}"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    service.list.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.json() == {"items": []}
    assert response.headers["cache-control"] == "no-store"
    world, conversation, subject = service.list.call_args.args
    assert (world, conversation) == ("managed", conversation_id)
    assert subject.startswith("hosted_dms:")



@pytest.mark.parametrize("source", [False, True])
def test_hosted_historical_passages_bind_saved_turn(hosted, monkeypatch, source):
    from unittest.mock import Mock

    from application_state.errors import ApplicationStateNotFoundError
    from apps.live_control_server.routes import agent

    service = Mock()
    read = service.read_historical_source_passage if source else service.inspect_rules_passage
    read.side_effect = ApplicationStateNotFoundError("Passage unavailable")
    monkeypatch.setattr(agent, "_verified_world_id", lambda world_id: world_id)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: service)
    turn, conversation, support = uuid4(), uuid4(), uuid4()
    digest = "a" * 64
    base = f"/api/live/agent/worlds/managed/conversation/turns/{turn}"
    if source:
        path = f"{base}/context-trace/{uuid4()}/source-passages/{support}"
        query = f"?conversation_id={conversation}&attempt=1&source_read_id={uuid4()}&content_sha256={digest}"
    else:
        path = f"{base}/rules-passages/{support}"
        query = f"?conversation_id={conversation}&attempt=1&support_sha256={digest}"
    assert hosted.client.request("GET", path + query, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + query + "&world_id=foreign").status_code == 403
    assert hosted.client.request("GET", path).status_code == 422
    read.assert_not_called()
    response = hosted.client.request("GET", path + query)
    assert response.status_code == 404, response.text
    assert response.headers["cache-control"] == "no-store"
    reference, = read.call_args.args
    assert (reference.world_id, reference.turn_id, reference.conversation_id) == ("managed", turn, conversation)
def test_hosted_saved_replay_binds_trace_before_read(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import agent_replay_identities

    read = Mock(return_value={"identities": []})
    monkeypatch.setattr(agent_replay_identities, "replay_identities", read)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: None)
    turn, trace = uuid4(), uuid4()
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn}/context-trace/{trace}/identities"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=foreign").status_code == 403
    assert hosted.client.request("GET", path + "?label=foreign").status_code == 422
    read.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    params = read.call_args.kwargs
    assert params["world_id"] == params["principal"].managed_world_id == "managed"
    assert (params["turn_id"], params["trace_id"]) == (turn, trace)


def test_hosted_related_page_read_binds_saved_turn(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import build_related_pages

    read = Mock(return_value={"page": "Saved passage"})
    monkeypatch.setattr(build_related_pages, "open_page", read)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    service = object()
    monkeypatch.setattr(agent, "_conversation_service", lambda request: service)
    turn, read_id = uuid4(), uuid4()
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn}/related-pages/{read_id}"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=foreign").status_code == 403
    assert hosted.client.request("GET", path + "?revision=foreign").status_code == 422
    read.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    read.assert_called_once_with(service, "managed", turn, read_id)
def test_hosted_trash_inventory_requires_world_owner(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import workspace_lifecycle

    root = object()
    inventory = Mock(return_value={"world_id": "managed", "documents": [], "sessions": []})
    monkeypatch.setattr(workspace_lifecycle, "_root", lambda: root)
    monkeypatch.setattr(workspace_lifecycle, "list_world_workspace_trash", inventory)
    path = "/api/live/world-workspace/trash?world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    inventory.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    inventory.assert_called_once_with(root, world_id="managed")
def test_hosted_rules_lookup_requires_owned_world(hosted):
    path = "/api/live/rules/catalog?world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert any(source["available"] for source in response.json()["sources"])


def test_hosted_related_recaps_bind_pinned_world(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.services import native_graph_inspection

    read = Mock(return_value={"targets": []})
    monkeypatch.setattr(native_graph_inspection, "related_recaps", read)
    path = "/api/live/native-graph-inspection/related-recaps"
    scope = {"managed_world_id": "managed", "native_world_id": "native", "binding_version": 1,
             "revision_id": "rev_exact", "scope_mode": "world", "campaign_id": None}
    body = {"scope": scope, "assertion_id": "assertion:1"}
    assert hosted.client.request("POST", path, session="other-session", json=body).status_code == 403
    assert hosted.client.request("POST", path, origin=None, json=body).status_code == 403
    read.assert_not_called()
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 200, response.text
    pin, principal, assertion = read.call_args.args
    assert pin.managed_world_id == principal.managed_world_id == "managed"
    assert pin.revision_id == "rev_exact"
    assert assertion == "assertion:1"


def test_hosted_complete_object_requires_exact_world_pin(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.services import native_graph_inspection

    read = Mock(return_value={"found": True})
    monkeypatch.setattr(native_graph_inspection, "complete_object", read)
    path = "/api/live/native-graph-inspection/complete-object"
    scope = {
        "managed_world_id": "managed",
        "native_world_id": "native",
        "binding_version": 1,
        "revision_id": "rev_exact",
        "scope_mode": "world",
        "campaign_id": None,
    }
    selector = {
        "schema": "dmb_world_graph_object_projection_request_v1",
        "worldId": "managed",
        "scopeMode": "world",
        "campaignId": "",
        "revisionPin": "rev_exact",
        "nodeId": "object:1",
        "admissibility": "gm",
    }
    body = {"scope": scope, "request": selector}
    assert hosted.client.request("POST", path, session="other-session", json=body).status_code == 403
    assert hosted.client.request("POST", path, origin=None, json=body).status_code == 403
    for changes in ({"worldId": "foreign"}, {"revisionPin": "other"}, {"campaignId": "campaign"}):
        invalid = {**body, "request": {**selector, **changes}}
        assert hosted.client.request("POST", path, json=invalid).status_code == 403
    read.assert_not_called()
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    request, principal = read.call_args.args
    assert request.scope.revision_id == request.request.revision_pin == "rev_exact"
    assert request.request.world_id == principal.managed_world_id == "managed"


def test_hosted_published_recap_requires_owned_world(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.services import native_source_inspection

    read = Mock(return_value={"source": {"status": "available"}})
    monkeypatch.setattr(native_source_inspection, "published_recap", read)
    path = "/api/live/native-source-inspection/published-recap"
    body = {"managed_world_id": "managed", "campaign_id": "campaign", "session_id": "session"}
    assert hosted.client.request("POST", path, session="other-session", json=body).status_code == 403
    assert hosted.client.request("POST", path, origin=None, json=body).status_code == 403
    read.assert_not_called()
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    selector, principal = read.call_args.args
    assert selector.managed_world_id == principal.managed_world_id == "managed"
    assert (selector.campaign_id, selector.session_id) == ("campaign", "session")


def test_hosted_saved_work_plan_reads_exact_turn(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import conversation_library, conversation_work_plans

    read = Mock(return_value={"status": "review"})
    monkeypatch.setattr(conversation_work_plans.work_plan, "read", read)
    monkeypatch.setattr(conversation_library, "_verified_world_id", lambda world: world)
    conversation, turn = uuid4(), uuid4()
    path = f"/api/live/agent/worlds/managed/conversations/{conversation}/work-plans/{turn}"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=foreign").status_code == 403
    read.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    read.assert_called_once_with("managed", conversation, turn)


def test_hosted_plan_terminal_diagnostic_reads_owned_action(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import live
    from apps.live_control_server.services import plan_action_terminal_diagnostic

    read = Mock(return_value={"availability": "unavailable"})
    monkeypatch.setattr(plan_action_terminal_diagnostic, "terminal_diagnostic", read)
    monkeypatch.setattr(live, "get_world_container", lambda world: world)
    action = uuid4()
    path = f"/api/live/world-plan-edit/actions/{action}/terminal-diagnostic?world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    read.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    read.assert_called_once_with("managed", action)


def test_hosted_image_preparation_binds_world_and_owner(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import media_images

    service = Mock()
    record = service.get.return_value
    record.reservation.basis.world_id = "managed"
    record.model_dump.return_value = {"prompt": "A gate at dusk"}
    monkeypatch.setattr(media_images, "BuildImageService", lambda: service)
    action = uuid4()
    path = f"/api/live/media/images/preparations/{action}?world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    service.get.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    identifier, owner = service.get.call_args.args
    assert identifier == action
    assert owner.startswith("hosted_dms:")
    record.reservation.basis.world_id = "foreign"
    denied = hosted.client.request("GET", path)
    assert denied.status_code == 404
    assert "A gate at dusk" not in denied.text


def test_hosted_generated_artwork_is_readable_in_its_world(hosted, application_state_dsn, monkeypatch):
    from io import BytesIO
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from PIL import Image
    from application_state import media
    from apps.live_control_server.routes import media_images

    output = BytesIO()
    Image.new("RGB", (2, 2)).save(output, format="PNG")
    payload = output.getvalue()
    provider = SimpleNamespace(
        generate_image=AsyncMock(return_value=SimpleNamespace(
            images=[SimpleNamespace(content=payload, media_type="image/png")],
            observation=SimpleNamespace(model_dump=lambda **kwargs: {"provider": "fixture"}),
        )),
        aclose=AsyncMock(),
    )
    monkeypatch.setattr(media_images, "_fal_key", lambda: "fixture")
    monkeypatch.setattr(media_images, "_image_client", lambda: provider)
    path = "/api/live/media/images/generate?world_id=managed"
    body = {"prompt": "A gate at dusk", "model": "flux-2-pro"}
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert hosted.client.request("POST", path.replace("managed", "foreign"), json=body).status_code == 403
    provider.generate_image.assert_not_called()
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 200, response.text
    asset_id = response.json()["images"][0]["asset_id"]
    assert media.get_asset(asset_id, access.hosted_world_media_owner("managed"))["state"] == "staged"
    original = hosted.client.request("GET", f"/api/live/media/images/{asset_id}/original")
    assert original.status_code == 200, original.text
    assert original.content == payload
    provider.generate_image.assert_awaited_once()

    from tests.integration.test_build_images_postgres import ready

    owner = access.hosted_world_media_owner("managed")
    save = AsyncMock(side_effect=lambda identifier, scope: ready(media.get_asset(identifier, scope)))
    monkeypatch.setattr(media_images.media_storage, "save_asset", save)
    save_path = f"/api/live/media/images/{asset_id}/save"
    assert hosted.client.request("POST", save_path, json={}, session="other-session").status_code == 403
    assert hosted.client.request("POST", save_path, json={}, origin=None).status_code == 403
    assert hosted.client.request("POST", save_path, json={"unexpected": True}).status_code == 403
    save.assert_not_called()
    saved = hosted.client.request("POST", save_path, json={})
    assert saved.status_code == 200, saved.text
    assert saved.json()["state"] == "ready"
    assert media.get_asset(asset_id, owner)["state"] == "ready"
    save.assert_awaited_once_with(UUID(asset_id), owner)

    provider.generate_image.reset_mock()
    parent = media.get_asset(asset_id, owner)
    edit_path = f"/api/live/media/images/{asset_id}/regenerate"
    edit = {"mode": "new", "instructions": "Paint the gate at dawn.", "expected_content_sha256": parent["content_sha256"]}
    assert hosted.client.request("POST", edit_path, json=edit, session="other-session").status_code == 403
    assert hosted.client.request("POST", edit_path, json=edit, origin=None).status_code == 403
    assert hosted.client.request("POST", edit_path, json={**edit, "expected_content_sha256": "0" * 64}).status_code == 409
    provider.generate_image.assert_not_called()
    regenerated = hosted.client.request("POST", edit_path, json=edit)
    assert regenerated.status_code == 200, regenerated.text
    child = regenerated.json()["asset_id"]
    assert child != asset_id
    assert regenerated.json()["parent_asset_id"] == asset_id
    assert media.get_asset(child, owner)["state"] == "staged"
    assert media.get_asset(asset_id, owner) == parent
    assert hosted.client.request("GET", f"/api/live/media/images/{child}/original").content == payload
    provider.generate_image.assert_awaited_once()


def test_hosted_prepared_image_association_uses_world_asset_owner(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import media_images
    from apps.live_control_server.services import build_document_proposal

    service = Mock()
    service.get.return_value.reservation.basis.world_id = "managed"
    service.associate.return_value.model_dump.return_value = {"revision": 2}
    monkeypatch.setattr(media_images, "BuildImageService", lambda: service)
    monkeypatch.setattr(build_document_proposal, "_source", Mock())
    action, asset = uuid4(), uuid4()
    path = f"/api/live/media/images/preparations/{action}/asset?world_id=managed"
    body = {"asset_id": str(asset), "expected_revision": 1}
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    service.get.assert_not_called()
    service.get.return_value.reservation.basis.world_id = "foreign"
    assert hosted.client.request("POST", path, json=body).status_code == 404
    service.associate.assert_not_called()
    service.get.return_value.reservation.basis.world_id = "managed"
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 200, response.text
    _, owner = service.get.call_args.args
    assert owner.startswith("hosted_dms:")
    service.associate.assert_called_once_with(action, asset, owner, 1, asset_owner="hosted_world:managed")


def test_hosted_connected_page_reads_exact_world_operation(hosted, monkeypatch, tmp_path):
    from unittest.mock import Mock

    from apps.live_control_server.routes import workspace_documents

    read = Mock(return_value={"phase": "complete"})
    monkeypatch.setattr(workspace_documents, "_managed_world_root", lambda: tmp_path)
    monkeypatch.setattr(workspace_documents, "get_connected_page", read)
    operation = uuid4()
    path = f"/api/live/connected-pages/{operation}?world_id=managed"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
    read.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert read.call_args.args == (tmp_path, operation, "managed")
    assert read.call_args.kwargs["principal"].managed_world_id == "managed"


def test_hosted_connected_page_writes_use_same_world_principal(hosted, monkeypatch, tmp_path):
    from unittest.mock import Mock

    from apps.live_control_server.routes import workspace_documents

    prepare = Mock(return_value={"phase": "prepared"})
    confirm = Mock(return_value={"phase": "complete"})
    monkeypatch.setattr(workspace_documents, "_managed_world_root", lambda: tmp_path)
    monkeypatch.setattr(workspace_documents, "prepare_connected_page", prepare)
    monkeypatch.setattr(workspace_documents, "confirm_connected_page", confirm)
    operation = str(uuid4())
    intent = {
        "operation_id": operation, "world_id": "managed", "title": "Gate",
        "place": {"label": "Gate", "kind": "location"}, "mode": "scaffold",
        "origin": {
            "kind": "saved_page_excerpt", "document_id": str(uuid4()), "revision": 1,
            "content_sha256": "a" * 64, "line_start": 1, "line_end": 1,
            "selected_text": "The gate.",
        },
    }
    confirmation = {"operation_id": operation, "world_id": "managed", "confirm_token": "fixture"}
    for action, body, call in (("prepare", intent, prepare), ("confirm", confirmation, confirm)):
        path = f"/api/live/connected-pages/{action}"
        assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
        assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
        assert hosted.client.request("POST", path, json={**body, "world_id": "foreign"}).status_code == 403
        call.assert_not_called()
        response = hosted.client.request("POST", path, json=body)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
    principals = [call.call_args.kwargs["principal"] for call in (prepare, confirm)]
    assert principals[0] == principals[1]
    assert principals[0].managed_world_id == "managed"
    assert principals[0].subject.startswith("hosted_dms:")


def test_hosted_authoring_identities_require_owned_world(hosted):
    path = "/api/live/native-graph-inspection/authoring-identities"
    scope = {"managed_world_id": "managed", "scope_mode": "world", "campaign_id": None}
    assert hosted.client.request("POST", path, json=scope, session="other-session").status_code == 403
    assert hosted.client.request("POST", path, json=scope, origin=None).status_code == 403
    assert hosted.client.request("POST", path, json={**scope, "scope_mode": "campaign", "campaign_id": "other"}).status_code == 403
    response = hosted.client.request("POST", path, json=scope)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["scope"]["managed_world_id"] == "managed"
    assert isinstance(response.json()["identities"], list)


def test_hosted_connected_page_origin_reads_exact_saved_turn(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import agent_connected_page_origin

    service = Mock()
    read = Mock(return_value={"kind": "saved_page_excerpt"})
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: service)
    monkeypatch.setattr(agent_connected_page_origin, "open_origin", read)
    turn = uuid4()
    path = f"/api/live/agent/worlds/managed/conversation/turns/{turn}/connected-page-origin"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=foreign").status_code == 403
    read.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    read.assert_called_once_with(service, "managed", turn)


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_hosted_exact_proposal_read_binds_world(hosted, monkeypatch, surface):
    from unittest.mock import Mock

    from application_state.build_proposal import service as build
    from application_state.errors import ApplicationStateNotFoundError
    from application_state.plan_action_dialogue import authoring_review as plan
    from apps.live_control_server.routes import agent

    read = Mock(side_effect=ApplicationStateNotFoundError("Proposal not found"))
    if surface == "build":
        monkeypatch.setattr(build, "BuildProposalService", lambda: SimpleNamespace(get=read))
    else:
        monkeypatch.setattr(plan, "read_review", read)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    action = uuid4()
    path = f"/api/live/agent/worlds/managed/{surface}-proposals/{action}"
    if surface == "plan":
        path += "/review"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "?world_id=foreign").status_code == 403
    read.assert_not_called()
    assert hosted.client.request("GET", path).status_code == 404
    read.assert_called_once_with("managed", action)


def test_hosted_plan_proposal_command_binds_exact_world_and_action(hosted, monkeypatch):
    from unittest.mock import Mock

    from application_state.errors import ApplicationStateNotFoundError
    from application_state.plan_action_dialogue import authoring_review
    from apps.live_control_server.routes import agent

    execute = Mock(side_effect=ApplicationStateNotFoundError("Proposal not found"))
    monkeypatch.setattr(authoring_review, "execute_review_command", execute)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    action, command = uuid4(), uuid4()
    path = f"/api/live/agent/worlds/managed/plan-proposals/{action}/review"
    body = {"operation": "open", "command_id": str(command), "origin_sha256": "a" * 64, "expected_revision": 0}
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path + "?world_id=foreign", json=body).status_code == 403
    execute.assert_not_called()
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 404, response.text
    world, saved_action, submitted = execute.call_args.args
    assert (world, saved_action, submitted.command_id) == ("managed", action, command)


def test_hosted_build_review_binds_world_and_action(hosted, monkeypatch):
    from unittest.mock import Mock

    from application_state.errors import ApplicationStateNotFoundError
    from apps.live_control_server.routes import agent, build_proposal_reviews

    service = Mock()
    service.get.side_effect = ApplicationStateNotFoundError("Proposal not found")
    service.execute.side_effect = ApplicationStateNotFoundError("Proposal not found")
    monkeypatch.setattr(build_proposal_reviews, "BuildProposalReviewService", lambda **kwargs: service)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    action = uuid4()
    path = f"/api/live/agent/worlds/managed/build-proposals/{action}/review"
    body = {"operation": "open", "expected_revision": 0}
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert hosted.client.request("POST", path + "?world_id=foreign", json=body).status_code == 403
    service.get.assert_not_called()
    service.execute.assert_not_called()
    assert hosted.client.request("GET", path).status_code == 404
    service.get.assert_called_once_with("managed", action)
    assert hosted.client.request("POST", path, json=body).status_code == 404
    world, saved_action, command = service.execute.call_args.args
    assert (world, saved_action, command.operation) == ("managed", action, "open")


def test_hosted_creature_catalog_and_association_read_are_world_scoped(hosted, monkeypatch):
    from unittest.mock import Mock

    from apps.live_control_server.routes import world_mechanics_associations as routes

    catalog = Mock(return_value=SimpleNamespace(response=lambda: {"world_id": "managed", "items": []}))
    find = Mock(return_value=None)
    monkeypatch.setattr(routes.creatures, "catalog", catalog)
    monkeypatch.setattr(routes, "resolve_managed_world_binding", lambda world: world)
    monkeypatch.setattr(routes.state, "find_request", find)
    request_id = uuid4()
    base = "/api/live/world-mechanics/associations"
    for suffix in ("creatures", f"requests/{request_id}"):
        path = f"{base}/{suffix}?world_id=managed"
        assert hosted.client.request("GET", path, session="other-session").status_code == 403
        assert hosted.client.request("GET", path + "&world_id=foreign").status_code == 403
        response = hosted.client.request("GET", path)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
    catalog.assert_called_once_with("managed")
    find.assert_called_once_with(world_id="managed", request_id=request_id)


def test_hosted_mechanics_association_binds_actor_and_world(hosted, monkeypatch):
    from unittest.mock import Mock

    from application_state.errors import ApplicationStateNotFoundError
    from apps.live_control_server.routes import world_mechanics_associations as routes

    write = Mock(side_effect=ApplicationStateNotFoundError("Saved mechanics not found"))
    monkeypatch.setattr(routes, "associate", write)
    path = "/api/live/world-mechanics/associations?world_id=managed"
    body = {
        "request_id": str(uuid4()), "draft_id": str(uuid4()),
        "expected_draft_version": 1, "expected_version": 0,
        "target": {
            "managed_world_id": "managed", "native_world_id": "native",
            "binding_version": 3, "graph_revision_id": "revision", "node_id": "creature",
            "label": "Creature", "kind": "creature", "role": "npc", "campaign_scope": None,
        },
        "locator": {
            "provider": "dungeonmind", "statblock_id": "sb_fixture", "revision_id": "rev_fixture",
            "contract": "dungeonmind.dungeonbuddy-statblocks", "contract_version": "1.0.0",
            "definition_digest": "sha256:" + "a" * 64,
        },
    }
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", path.replace("managed", "foreign"), json=body).status_code == 403
    write.assert_not_called()
    result = hosted.client.request("POST", path, json=body)
    assert result.status_code == 404, result.text
    assert write.call_args.kwargs["actor"] == f"hosted_dms:{OWNER}"
    assert write.call_args.kwargs["request"].model_dump(mode="json") == body


def test_hosted_persists_and_reopens_exact_mechanics_association(mechanics_prepared, hosted, monkeypatch):
    from apps.live_control_server.services import statblock_saved_revision, world_creature_selection

    fixture = mechanics_prepared
    world = "elderwyld"
    hosted.records[world] = _record(world, OWNER, fixture.view.native_world_id)
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({world: [OWNER]}))
    monkeypatch.setattr(world_creature_selection.native, "binding", lambda world_id: vars(fixture.binding).copy())
    base = "/api/live/world-mechanics/associations"
    path = f"{base}?world_id={world}"
    assert hosted.client.request("POST", path, json=fixture.body, origin=None).status_code == 403
    first = hosted.client.request("POST", path, json=fixture.body)
    assert first.status_code == 200, first.text
    record = first.json()["association"]
    assert record["actor"] == f"hosted_dms:{OWNER}"
    assert record["proof"]["locator"] == fixture.body["locator"]
    assert first.json()["replayed"] is False
    assert fixture.dms.calls == 1
    monkeypatch.setattr(statblock_saved_revision, "get_threat_draft", lambda *args: pytest.fail("Replay read external state"))
    retry = hosted.client.request("POST", path, json=fixture.body)
    assert retry.json() == {"association": record, "replayed": True}
    assert fixture.dms.calls == 1
    status = f"{base}/requests/{fixture.body['request_id']}?world_id={world}"
    assert hosted.client.request("GET", status).json() == record
    assert hosted.client.request("GET", status, session="other-session").status_code == 403


def test_hosted_portrait_revision_recovers_exact_save(revision_case, hosted, monkeypatch):
    import json

    from tests.integration.test_build_images_postgres import ready, saved_image

    fixture = revision_case
    world = "elderwyld"
    hosted.records[world] = _record(world, OWNER, fixture.view.native_world_id)
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({world: [OWNER]}))
    asset = ready(saved_image(f"hosted_world:{world}"))
    body = {**fixture.request, "portrait_asset_id": str(asset["asset_id"])}
    assert hosted.client.request("POST", fixture.url, json=body, origin=None).status_code == 403
    fixture.manual.timeout = True
    unknown = hosted.client.request("POST", fixture.url, json=body)
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["state"] == "outcome_unknown"
    operation = fixture.url.replace("mechanics-revisions", "mechanics-revision-operations") + "/" + body["operation_id"]
    status = hosted.client.request("GET", f"{operation}?world_id={world}")
    assert status.status_code == 200, status.text
    assert status.json()["operation"]["state"] == "outcome_unknown"
    assert hosted.client.request("POST", f"{operation}:recover?world_id={world}", origin=None).status_code == 403
    recovered = hosted.client.request("POST", f"{operation}:recover?world_id={world}")
    assert recovered.status_code == 200, recovered.text
    result = recovered.json()
    assert result["state"] == "committed"
    assert fixture.manual.appends == 1
    revision_id = result["result"]["revision_id"]
    opened = hosted.client.request("GET", f"{fixture.url}/{revision_id}?world_id={world}")
    assert opened.status_code == 200, opened.text
    assert opened.json()["resource"]["provenance"]["accepted_through"]["buddy_portrait_asset_id"] == str(asset["asset_id"])


def test_hosted_native_creature_routes_bind_exact_draft_and_principal(hosted, monkeypatch, tmp_path):
    from unittest.mock import Mock

    from apps.live_control_server.routes import native_threat_creation as routes

    status = Mock(return_value=None)
    prepare = Mock(return_value={"status": "prepared"})
    confirm = Mock(return_value={"status": "published"})
    monkeypatch.setattr(routes, "statblock_data_root", lambda root: tmp_path)
    for name, handler in (("status", status), ("prepare", prepare), ("confirm", confirm)):
        monkeypatch.setattr(routes.service, name, handler)
    draft_id = uuid4()
    path = f"/api/live/threat-drafts/{draft_id}/native-creature"
    preparation = {"world_id": "managed", "expected_draft_version": 1}
    review = {
        "world_id": "managed", "draft_id": str(draft_id), "draft_version": 1,
        "label": "Keeper", "body_sha256": "a" * 64, "binding": {},
        "publication_id": "fixture", "source_evidence_id": "evidence",
        "source_artifact_id": "source", "source_revision_id": "revision",
        "prepared_digest": "b" * 64, "principal": f"hosted_dms:{OWNER}",
        "expires_at": "2027-01-01T00:00:00Z",
    }
    confirmation = {"review": review, "prepared": {}, "token": "fixture"}
    assert hosted.client.request("GET", path + "?world_id=managed", session="other-session").status_code == 403
    assert hosted.client.request("POST", path + "/prepare", json=preparation, origin=None).status_code == 403
    wrong_draft = {**confirmation, "review": {**review, "draft_id": str(uuid4())}}
    assert hosted.client.request("POST", path + "/confirm", json=wrong_draft).status_code == 403
    for handler in (status, prepare, confirm):
        handler.assert_not_called()
    for method, suffix, body in (
        ("GET", "?world_id=managed", None),
        ("POST", "/prepare", preparation),
        ("POST", "/confirm", confirmation),
    ):
        response = hosted.client.request(method, path + suffix, **({"json": body} if body else {}))
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
    for handler in (status, prepare, confirm):
        root, draft, _, principal = handler.call_args.args
        assert (root, draft) == (tmp_path, draft_id)
        assert principal.managed_world_id == "managed"
        assert principal.subject == f"hosted_dms:{OWNER}"


def test_hosted_image_catalog_binds_world_and_cursor(hosted, monkeypatch):
    from unittest.mock import AsyncMock

    from apps.live_control_server.routes import media_images

    provider = SimpleNamespace(
        list_image_models=AsyncMock(return_value=SimpleNamespace(model_dump=lambda **kwargs: {"models": []})),
        aclose=AsyncMock(),
    )
    monkeypatch.setattr(media_images, "_image_client", lambda: provider)
    monkeypatch.setattr(media_images, "_fal_key", lambda: "fixture")
    path = "/api/live/media/images/catalog?world_id=managed&cursor=next&limit=7"
    assert hosted.client.request("GET", path, session="other-session").status_code == 403
    assert hosted.client.request("GET", path + "&cursor=foreign").status_code == 403
    provider.list_image_models.assert_not_called()
    response = hosted.client.request("GET", path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    provider.list_image_models.assert_awaited_once_with(category="text-to-image", cursor="next", limit=7)


def test_hosted_archives_exact_statblock_and_preserves_saved_revision(mechanics_prepared, hosted):
    from apps.live_control_server.services import threat_draft_store

    fixture = mechanics_prepared
    world = "elderwyld"
    hosted.records[world] = _record(world, OWNER, fixture.view.native_world_id)
    from apps.live_control_server.services import hosted_auth

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(hosted_auth.HOSTED_WORLD_ACCESS_ENV, json.dumps({world: [OWNER]}))
        draft_id = fixture.draft.draft_id
        version = fixture.draft.version
        base = f"/api/live/threat-drafts/{draft_id}/saved-statblock?world_id={world}"
        path = f"{base}&expected_version={version}"
        assert hosted.client.request("DELETE", path, session="other-session").status_code == 403
        assert hosted.client.request("DELETE", path, origin=None).status_code == 403
        assert hosted.client.request("DELETE", f"{base}&expected_version={version + 1}").status_code == 409
        before, _ = threat_draft_store.list_threat_drafts(fixture.root, world_id=world)
        assert len(before) == 1
        archived = hosted.client.request("DELETE", path)
        assert archived.status_code == 204, archived.text
        after, _ = threat_draft_store.list_threat_drafts(fixture.root, world_id=world)
        assert after == []
        assert threat_draft_store.get_threat_draft(fixture.root, draft_id).accepted_mechanics_ref == fixture.draft.accepted_mechanics_ref
        assert hosted.client.request("DELETE", path).status_code == 204


def test_hosted_document_trash_and_restore_preserve_identity(hosted, application_state_dsn, monkeypatch):
    from application_state.content import pages

    monkeypatch.setattr(pages, "get_world", hosted.get_world)
    created = hosted.client.request("POST", "/api/live/workspace-documents", json={
        "title": "Recoverable page", "kind": "worldbuilding_source",
        "authority_state": "draft", "visibility_state": "internal",
        "source_domain": "worldbuilding", "document_class": "lore",
        "world_id": "managed", "campaign_id": "managed",
    })
    assert created.status_code == 200, created.text
    record = created.json()
    base = f"/api/live/world-workspace/documents/{record['document_id']}"
    move = f"{base}/trash?world_id=managed"
    body = {"expected_revision": record["revision"]}
    assert hosted.client.request("POST", move, json=body, session="other-session").status_code == 403
    assert hosted.client.request("POST", move, json=body, origin=None).status_code == 403
    moved = hosted.client.request("POST", move, json=body)
    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "trashed"
    restore = f"{base}/restore?world_id=managed"
    assert hosted.client.request("POST", restore, json=body).status_code == 409
    restored = hosted.client.request("POST", restore, json={"expected_revision": moved.json()["revision"]})
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "active"
    assert restored.json()["id"] == record["document_id"]


@pytest.mark.parametrize("kind", ["pdf", "text"])
def test_hosted_source_withdrawal_binds_exact_world_revision(hosted, monkeypatch, kind):
    from unittest.mock import Mock

    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import native_source_inspection

    repo = Mock()
    repo.get_native_pdf_source.return_value = (SimpleNamespace(
        source_artifact_id="artifact", status="active", visibility=SimpleNamespace(kind="public"),
    ),)
    catalog = Mock(return_value={
        "scope": {"native_world_id": "space"},
        "catalogue": {"sources": [{
            "source_artifact": {"source_artifact_id": "artifact"},
            "source_revision": {"source_revision_id": "revision"},
        }]},
    })
    monkeypatch.setattr(native_world_source_admission, "_repository", lambda: repo)
    monkeypatch.setattr(native_world_source_admission, "_source_world_binding", lambda root, world: SimpleNamespace(native_world_id="space"))
    monkeypatch.setattr(native_source_inspection, "catalog", catalog)
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    path = "/api/live/agent/worlds/managed/build-source-withdrawals"
    body = {"kind": kind, "revision_id": "revision"}
    assert hosted.client.request("POST", path, json=body, origin=None).status_code == 403
    assert hosted.client.request("POST", path, json=body, session="other-session").status_code == 403
    catalog.assert_not_called()
    assert not repo.mock_calls
    response = hosted.client.request("POST", path, json=body)
    assert response.status_code == 204, response.text
    repo.withdraw_native_source.assert_called_once_with(
        space_id="space", source_artifact_id="artifact", source_revision_id="revision",
    )
    if kind == "text":
        scope, principal = catalog.call_args.args
        assert scope.managed_world_id == principal.managed_world_id == "managed"
