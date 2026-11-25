from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging
import os
import re
from pathlib import Path
from time import perf_counter
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from apps.live_control_server.routes.conversation_library import router as conversation_library_router
from apps.live_control_server.routes.conversation_work_plans import router as conversation_work_plans_router
from apps.live_control_server.routes.rules_lookup import router as rules_lookup_router

from apps.live_control_server.routes.media_images import router as media_images_router

from apps.live_control_server.routes.graph_authoring import router as graph_authoring_router
from apps.live_control_server.routes.agent_graph_local_session import (
    router as agent_graph_local_session_router,
)
from apps.live_control_server.routes.combat_encounters import router as combat_encounters_router
from apps.live_control_server.routes.combat_run_encounters import router as combat_run_encounters_router
from apps.live_control_server.routes.combat_scene_templates import router as combat_scene_templates_router
from apps.live_control_server.routes.world_mechanics_associations import router as world_mechanics_router
from apps.live_control_server.routes.live import router as live_router
from apps.live_control_server.routes.party_registry import router as party_registry_router
from apps.live_control_server.routes.play_runs import router as play_runs_router
from apps.live_control_server.routes.source_statements import router as source_statements_router
from apps.live_control_server.routes.native_profile_transition import router as native_profile_transition_router
from apps.live_control_server.routes.pdf_adventure_events import router as pdf_adventure_events_router
from apps.live_control_server.routes.native_graph_inspection import router as native_graph_inspection_router
from apps.live_control_server.routes.native_source_inspection import router as native_source_inspection_router
from apps.live_control_server.routes.play_prepared_tables import router as play_prepared_tables_router
from apps.live_control_server.routes.recap_ingest import router as recap_ingest_router
from apps.live_control_server.routes.world_graph_bootstrap import (
    router as world_graph_bootstrap_router,
)
from apps.live_control_server.routes.extract_promote import (
    router as extract_promote_router,
)
from apps.live_control_server.routes.world_graph_projection import (
    router as world_graph_projection_router,
)
from apps.live_control_server.routes.world_graph_retrieval import (
    router as world_graph_retrieval_router,
)
from apps.live_control_server.routes.workspace_documents import (
    router as workspace_documents_router,
)
from apps.live_control_server.routes.workspace_lifecycle import (
    router as workspace_lifecycle_router,
)
from apps.live_control_server.routes.world_containers import (
    router as world_containers_router,
)
from apps.live_control_server.routes.guest_releases import (
    router as guest_releases_router,
    resolve_hosted_guest_release_world,
)
from apps.live_control_server.routes.guest_release_public import router as guest_release_public_router
from apps.live_control_server.routes.statblock_integration import (
    router as statblock_integration_router,
)
from apps.live_control_server.routes.threat_drafts import (
    router as threat_drafts_router,
)
from apps.live_control_server.routes.threat_publication import (
    router as threat_publication_router,
)
from apps.live_control_server.routes.threat_publication_identity import (
    router as threat_publication_identity_router,
)
from apps.live_control_server.routes.threat_publication_proposals import (
    router as threat_publication_proposals_router,
)
from apps.live_control_server.routes.threat_publication_commits import (
    router as threat_publication_commits_router,
)
from apps.live_control_server.routes.threat_query_hydration import (
    router as threat_query_hydration_router,
)
from apps.live_control_server.routes.statblock_candidates import (
    router as statblock_candidates_router,
)
from apps.live_control_server.routes.source_navigation import (
    router as source_navigation_router,
)
from apps.live_control_server.routes.index_graph import router as index_graph_router
from apps.live_control_server.routes.native_graph_explorer import (
    router as native_graph_explorer_router,
)
from apps.live_control_server.services.hermes_graph_agent_host import (
    get_hermes_graph_agent_host,
    shutdown_hermes_graph_agent_host,
)
from apps.live_control_server.services.dms_principal import (
    DMS_SESSION_COOKIE_NAME,
    DmsPrincipalResolver,
    fixed_dms_api_origin,
)
from apps.live_control_server.services.hosted_auth import (
    AUTH_SESSION_PATH,
    CURRENT_USER_PATH,
    DMS_API_ORIGIN_ENV,
    HOSTED_MODE,
    LOGIN_PATH,
    LOGOUT_PATH,
    PRODUCTION_ENVIRONMENT,
    auth_mode,
    deployment_environment,
    install_hosted_request_boundary,
    safe_hosted_return_path,
    validate_hosted_auth_configuration,
)
from apps.live_control_server.services.trusted_cookie_origin import require_cookie_write_origin
from apps.live_control_server.services.hosted_native_graph_access import (
    BUILD_PDF_SOURCES_PATH,
    BUILD_PAGE_INVENTORY_PATH,
    EXPLORER_PREFIX,
    FIRST_WORLD_CONFIRM_PATH,
    FIRST_WORLD_PREPARE_PATH,
    COMPLETE_OBJECT_PATH,
    INSPECTION_READ_PATH,
    WORLD_COLLECTION_PATH,
    WORLD_LOOKUP_PATH,
    hosted_owner_collection,
    hosted_owner_creation,
    resolve_hosted_build_pdf_world,
    resolve_hosted_saved_artwork,
    resolve_hosted_build_extraction,
    resolve_hosted_worldbuilding_write_plan,
    resolve_hosted_worldbuilding_review_context,
    resolve_hosted_recap_review_context,
    resolve_hosted_native_profile_transition,
    resolve_hosted_native_manual,
    resolve_hosted_worldbuilding_evidence_correction,
    resolve_hosted_exact_extraction_read,
    resolve_hosted_build_recap_recovery,
    resolve_hosted_saved_recap,
    resolve_hosted_recap_correction,
    resolve_hosted_recap_selection,
    resolve_hosted_build_page,
    resolve_hosted_build_native_source,
    resolve_hosted_statblock_inventory,
    resolve_hosted_saved_statblock,
    resolve_hosted_statblock_revision_save,
    resolve_hosted_combat_encounter,
    resolve_hosted_connected_page,
    resolve_hosted_conversation_world,
    resolve_hosted_source_evidence_extension,
    resolve_hosted_native_publication,
    resolve_hosted_source_statement_publication,
    resolve_hosted_native_creature,
    resolve_hosted_mechanics_association,
    resolve_hosted_build_insertion_ack,
    resolve_hosted_managed_projection,
    resolve_hosted_source_statement_proposal,
    resolve_hosted_source_statement_review,
    resolve_hosted_source_statement_subject,
    resolve_hosted_image_history,
    resolve_hosted_image_world,
    resolve_hosted_image_preparation,
    resolve_hosted_rules_lookup,
    resolve_hosted_agent_readiness,
    resolve_hosted_image_catalog,
    resolve_hosted_media_library,
    resolve_hosted_chat_turn,
    resolve_hosted_build_page_create,
    resolve_hosted_build_page_inventory,
    resolve_hosted_explorer_world,
    resolve_hosted_threat_hydration,
    resolve_hosted_first_world,
    resolve_hosted_manual_knowledge,
    resolve_hosted_native_relationship,
    resolve_hosted_plan_world_context,
    resolve_hosted_plan_inventory_page,
    resolve_hosted_committed_plan,
    resolve_hosted_plan_create,
    resolve_hosted_runbook_create,
    resolve_hosted_runbook_write,
    resolve_hosted_play_preparation,
    resolve_hosted_play_creation,
    resolve_hosted_play_read,
    resolve_hosted_runbook_read,
    resolve_hosted_recap_name_review,
    resolve_hosted_play_scene_proposal,
    resolve_hosted_play_table_roll,
    resolve_hosted_play_command,
    resolve_hosted_workspace_lifecycle,
    resolve_hosted_play_table_receipts,
    resolve_hosted_world_lookup,
)
from apps.live_control_server.routes.build_extraction import router as build_extraction_router
from bootstrap_env import load_dungeonmindbuddy_dotenv

load_dungeonmindbuddy_dotenv()


def _load_graph_preview_router():
    """Keep fixture-backed gold review out of the hosted production package.

    This developer surface imports evaluation fixtures containing campaign
    material. Production images exclude evals; local source checkouts retain
    the route when those tracked sources are present.
    """
    if deployment_environment() == PRODUCTION_ENVIRONMENT:
        return None
    try:
        from apps.live_control_server.routes.graph_preview import router
    except ModuleNotFoundError as exc:
        if exc.name == "evals" or (exc.name and exc.name.startswith("evals.")):
            return None
        raise
    return router


HOSTED_WORLD_COLLECTION_AUTHORIZERS = {
    ("GET", WORLD_COLLECTION_PATH): hosted_owner_collection,
    ("POST", WORLD_COLLECTION_PATH): hosted_owner_creation,
}

PDF_STATBLOCK_REVIEWS_PATH = f"{BUILD_PDF_SOURCES_PATH}/statblock-reviews"
PDF_STATBLOCK_REVIEW_PATH = f"{PDF_STATBLOCK_REVIEWS_PATH}/{{review_id}}"

HOSTED_WORLD_SCOPE_RESOLVERS = {
    ("POST", "/api/live/worlds/{world_id}/guest-releases"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/status"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/selection-options"): resolve_hosted_guest_release_world,
    ("POST", "/api/live/worlds/{world_id}/guest-releases/selection-context"): resolve_hosted_guest_release_world,
    ("POST", "/api/live/worlds/{world_id}/guest-releases/selection-media/list"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/selection-media/{asset_id}"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/candidates"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/published"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/candidates/{release_id}"): resolve_hosted_guest_release_world,
    ("GET", "/api/live/worlds/{world_id}/guest-releases/candidates/{release_id}/assets/{asset_id}"): resolve_hosted_guest_release_world,
    ("POST", "/api/live/worlds/{world_id}/guest-releases/candidates/{release_id}/publish"): resolve_hosted_guest_release_world,
    ("POST", "/api/live/worlds/{world_id}/guest-releases/candidates/{release_id}/revoke"): resolve_hosted_guest_release_world,
    ("POST", "/api/live/worlds/{world_id}/guest-releases/candidates/{release_id}/restore"): resolve_hosted_guest_release_world,
    ("POST", "/api/live/graph-authoring/native-manual/context"): resolve_hosted_native_manual,
    ("POST", "/api/live/graph-authoring/native-manual/prepare"): resolve_hosted_native_manual,
    ("POST", "/api/live/graph-authoring/native-manual/confirm"): resolve_hosted_native_manual,
    ("POST", "/api/live/graph-authoring/native-profile-transition/prepare"): resolve_hosted_native_profile_transition,
    ("POST", "/api/live/graph-authoring/native-profile-transition/confirm"): resolve_hosted_native_profile_transition,
    ("POST", "/api/live/extract-promote/runs/{run_id}/selection-context"): resolve_hosted_recap_selection,
    ("POST", "/api/live/extract-promote/runs/{run_id}/recap-evidence-corrections"): resolve_hosted_recap_correction,
    ("POST", "/api/live/source-statements/prepare"): resolve_hosted_source_statement_publication,
    ("POST", "/api/live/source-statements/confirm"): resolve_hosted_source_statement_publication,
    ("POST", "/api/live/source-statements/extend-evidence"): resolve_hosted_source_evidence_extension,
    ("POST", "/api/live/extract-promote/runs/{run_id}/recap-candidate-corrections"): resolve_hosted_recap_correction,
    ("POST", "/api/live/extract-promote/runs/{run_id}/semantic-disposition"): resolve_hosted_recap_correction,
    ("POST", "/api/live/extract-promote/native-prepare"): resolve_hosted_native_publication,
    ("POST", "/api/live/extract-promote/native-confirm"): resolve_hosted_native_publication,
    ("POST", "/api/live/extract-promote/worldbuilding/prepare"): resolve_hosted_worldbuilding_write_plan,
    ("POST", "/api/live/extract-promote/worldbuilding/confirm"): resolve_hosted_worldbuilding_write_plan,
    ("POST", "/api/live/extract-promote/native-worldbuilding-context"): resolve_hosted_worldbuilding_review_context,
    ("POST", "/api/live/extract-promote/native-recap-context"): resolve_hosted_recap_review_context,
    ("POST", "/api/live/threats/query-hydration"): resolve_hosted_threat_hydration,
    ("POST", "/api/live/recap-name-review"): resolve_hosted_recap_name_review,
    ("GET", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/review"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/review"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/build-image-moves/{action_id}/review"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/build-image-moves/{action_id}/review"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/review"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/review"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/work-plans/{source_turn_id}"): resolve_hosted_conversation_world,
    ("PUT", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/work-plans/{source_turn_id}"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/work-plans/{source_turn_id}/continue"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/plan-proposals/{action_id}/graph-evidence"): resolve_hosted_conversation_world,
    ("GET", "/api/live/world-plan-edit/actions/{action_id}/terminal-diagnostic"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/graph-evidence"): resolve_hosted_conversation_world,
    ("GET", "/api/live/connected-pages/{operation_id}"): resolve_hosted_connected_page,
    ("POST", "/api/live/connected-pages/prepare"): resolve_hosted_connected_page,
    ("POST", "/api/live/connected-pages/confirm"): resolve_hosted_connected_page,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/prompt/{provider_attempt_id}"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/prompts"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/name"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/resume"): resolve_hosted_conversation_world,
    ("GET", "/api/live/media/images/capabilities"): resolve_hosted_image_world,
    ("POST", "/api/live/media/images/generate"): resolve_hosted_image_world,
    ("POST", "/api/live/media/images/preparations/{action_id}/asset"): resolve_hosted_image_world,
    ("POST", "/api/live/graph-authoring/prepare"): resolve_hosted_manual_knowledge,
    ("POST", "/api/live/graph-authoring/commit"): resolve_hosted_manual_knowledge,
    ("GET", "/api/live/graph-authoring/object-kinds"): resolve_hosted_plan_world_context,
    ("POST", "/api/live/graph-authoring/document-relationship/request"): resolve_hosted_native_relationship,
    ("POST", "/api/live/graph-authoring/document-relationship/native-prepare"): resolve_hosted_native_relationship,
    ("POST", "/api/live/graph-authoring/document-relationship/native-confirm"): resolve_hosted_native_relationship,
    ("GET", "/api/live/media/images/preparations/{action_id}"): resolve_hosted_image_preparation,
    ("GET", "/api/live/media/images/catalog"): resolve_hosted_image_catalog,
    ("GET", "/api/live/media/images/library"): resolve_hosted_media_library,
    ("GET", "/api/live/media/images/{asset_id}"): resolve_hosted_saved_artwork,
    ("POST", "/api/live/world-graph/managed-projection"): resolve_hosted_managed_projection,
    ("GET", "/api/live/source-statements/proposals/{operation_id}"): resolve_hosted_source_statement_proposal,
    ("POST", "/api/live/source-statements/proposals/{operation_id}/review"): resolve_hosted_source_statement_review,
    ("GET", "/api/live/source-statements/{world_id}/subjects/{entity_id}"): resolve_hosted_source_statement_subject,
    ("GET", "/api/live/graph-preview/build-recap-launches/{request_id}"): resolve_hosted_build_recap_recovery,
    ("GET", "/api/live/graph-preview/build-worldbuilding-launches/{request_id}"): resolve_hosted_build_recap_recovery,
    ("GET", "/api/live/media/images/preparations/list"): resolve_hosted_image_history,
    ("GET", "/api/live/rules/catalog"): resolve_hosted_rules_lookup,
    ("GET", "/api/live/rules/query"): resolve_hosted_rules_lookup,
    ("GET", "/api/live/rules/passages/{citation_id}"): resolve_hosted_rules_lookup,

    ("GET", "/api/live/agent/readiness"): resolve_hosted_agent_readiness,
    ("POST", "/api/live/agent/turn"): resolve_hosted_chat_turn,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversation/new"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}/resolve"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/commands/{command_id}/resolutions/{operation_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/active/messages"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id:uuid}/messages"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/turns"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/retry-attempts"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/retry-context"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/variant-approval"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/discussion-retry-input"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}"): resolve_hosted_conversation_world,
    ("PUT", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}/variant-reviews/{review_id}"): resolve_hosted_conversation_world,
    ("PUT", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}/variant-reviews/{review_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}/variant-reviews/{review_id}/saved"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}/variant-reviews/{review_id}/saved/portrait"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}/variant-reviews/{review_id}/confirm"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/build-proposals"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/inserted"): resolve_hosted_build_insertion_ack,
    ("GET", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/build-proposals/{action_id}/prompt"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-source-sections/{citation_index}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/related-pages/{read_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/saved-sections/{segment_index}/{section_event_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversation/lore-pages/review"): resolve_hosted_conversation_world,
    ("POST", "/api/live/agent/worlds/{world_id}/conversation/lore-pages/confirm"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/connected-page-origin"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/source-passages/{source_read_event_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/rules-passages/{support_id}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/identities"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/steps/{sequence}/assertion"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/native-steps/{sequence}/assertion"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-body-excerpts/{citation_index}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-assertion-sources/{citation_index}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/native-source-clauses/{citation_index}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/agent/worlds/{world_id}/conversation/turns/{turn_id}/source-passages/{citation_index}"): resolve_hosted_conversation_world,
    ("GET", "/api/live/plan-view"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/world-workspace/trash"): resolve_hosted_plan_world_context,
    ("POST", "/api/live/world-workspace/documents/{document_id}/trash"): resolve_hosted_workspace_lifecycle,
    ("POST", "/api/live/world-workspace/documents/{document_id}/restore"): resolve_hosted_workspace_lifecycle,
    ("POST", "/api/live/world-workspace/sessions/{run_id}/trash"): resolve_hosted_workspace_lifecycle,
    ("POST", "/api/live/world-workspace/sessions/{run_id}/restore"): resolve_hosted_workspace_lifecycle,
    ("GET", "/api/live/workspace-documents/world-runbooks"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/workspace-documents/world-runbooks/{document_id}"): resolve_hosted_runbook_read,
    ("GET", "/api/live/workspace-documents/world-runbooks/{document_id}/snapshot"): resolve_hosted_runbook_read,
    ("GET", "/api/live/workspace-documents/world-runbooks/{document_id}/committed-revision"): resolve_hosted_runbook_read,
    ("GET", "/api/live/workspace-documents/world-runbooks/{document_id}/committed-revision/{revision_n}"): resolve_hosted_runbook_read,
    ("GET", "/api/live/extract-promote/worldbuilding/capabilities"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/workspace-documents/world-plans"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/workspace-documents/world-plans/page"): resolve_hosted_plan_inventory_page,
    ("GET", "/api/live/workspace-documents/{document_id}/committed-revision"): resolve_hosted_committed_plan,
    ("GET", "/api/live/workspace-documents/{document_id}/committed-revision/{revision_n}"): resolve_hosted_committed_plan,
    ("POST", "/api/live/workspace-documents/world-plans"): resolve_hosted_plan_create,
    ("POST", "/api/live/workspace-documents/world-runbooks"): resolve_hosted_runbook_create,
    ("POST", "/api/live/workspace-documents/world-runbooks/{document_id}/tiptap/prepare"): resolve_hosted_runbook_write,
    ("POST", "/api/live/workspace-documents/world-runbooks/{document_id}/tiptap/commit"): resolve_hosted_runbook_write,
    ("POST", "/api/live/world-play-runs/v2/preparation"): resolve_hosted_play_preparation,
    ("PUT", "/api/live/world-play-runs/v2/{run_id}"): resolve_hosted_play_creation,
    ("PUT", "/api/live/world-play-runs/v2/{run_id}/rebase"): resolve_hosted_play_command,
    ("PUT", "/api/live/world-play-runs/v2/{run_id}/progress"): resolve_hosted_play_command,
    ("PUT", "/api/live/world-play-runs/v2/{run_id}/content/commands/{command_id}"): resolve_hosted_play_command,
    ("PUT", "/api/live/world-play-runs/v2/{run_id}/review/commands/{command_id}"): resolve_hosted_play_command,
    ("POST", "/api/live/combat/scene-templates"): resolve_hosted_play_command,
    ("POST", "/api/live/combat/scene-templates/cancel"): resolve_hosted_play_command,
    ("GET", "/api/live/combat/scene-templates/operations/{operation_id}"): resolve_hosted_play_read,
    ("GET", "/api/live/combat/scene-templates/{document_id}/scenes/{scene_id}"): resolve_hosted_play_read,
    ("GET", "/api/live/combat/scene-templates/{document_id}/scenes/{scene_id}/versions/{revision}"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/active"): resolve_hosted_play_read,
    ("PUT", "/api/live/world-play-runs/v2/active"): resolve_hosted_play_command,
    ("GET", "/api/live/world-play-runs/v2/{run_id}"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/reference-manifest"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/review"): resolve_hosted_play_read,
    ("GET", "/api/live/world-session-evidence"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/world-session-evidence/{run_id}/revisions/{revision}"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/content/proposals"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}"): resolve_hosted_play_read,
    ("POST", "/api/live/world-play-runs/v2/{run_id}/content/proposals/{proposal_id}"): resolve_hosted_play_scene_proposal,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/content"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/prepared-tables"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/content/revisions/{revision_n}"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/content/commands/{command_id}"): resolve_hosted_play_read,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/prepared-tables/receipts"): resolve_hosted_play_table_receipts,
    ("PUT", "/api/live/world-play-runs/v2/{run_id}/prepared-tables/commands/{command_id}"): resolve_hosted_play_table_roll,
    ("GET", "/api/live/world-play-runs/v2/{run_id}/creation"): resolve_hosted_play_creation,
    ("POST", "/api/live/world-play-runs/v2/{run_id}/creation:cancel"): resolve_hosted_play_creation,
    ("GET", "/api/live/media/images/{asset_id}/metadata"): resolve_hosted_saved_artwork,
    ("POST", "/api/live/media/images/{asset_id}/save"): resolve_hosted_saved_artwork,
    ("POST", "/api/live/media/images/{asset_id}/regenerate"): resolve_hosted_saved_artwork,
    ("GET", "/api/live/media/images/{asset_id}/original"): resolve_hosted_saved_artwork,
    ("POST", FIRST_WORLD_PREPARE_PATH): resolve_hosted_first_world,
    ("POST", FIRST_WORLD_CONFIRM_PATH): resolve_hosted_first_world,
    ("POST", "/api/live/worlds/{world_id}/pdf-adventure-events/prepare"): resolve_hosted_build_pdf_world,
    ("POST", "/api/live/worlds/{world_id}/pdf-adventure-events/confirm"): resolve_hosted_build_pdf_world,
    ("POST", "/api/live/agent/worlds/{world_id}/build-source-withdrawals"): resolve_hosted_conversation_world,
    ("GET", PDF_STATBLOCK_REVIEWS_PATH): resolve_hosted_build_pdf_world,
    ("GET", PDF_STATBLOCK_REVIEW_PATH): resolve_hosted_build_pdf_world,
    ("GET", f"{PDF_STATBLOCK_REVIEW_PATH}/publication"): resolve_hosted_build_pdf_world,
    ("GET", f"{PDF_STATBLOCK_REVIEW_PATH}/publication/statblock"): resolve_hosted_build_pdf_world,
    ("POST", f"{PDF_STATBLOCK_REVIEW_PATH}/publication"): resolve_hosted_build_pdf_world,
    ("PUT", PDF_STATBLOCK_REVIEW_PATH): resolve_hosted_build_pdf_world,
    ("POST", f"{PDF_STATBLOCK_REVIEW_PATH}/from-regions"): resolve_hosted_build_pdf_world,
    ("POST", f"{PDF_STATBLOCK_REVIEW_PATH}/validate"): resolve_hosted_build_pdf_world,
    ("POST", f"{PDF_STATBLOCK_REVIEW_PATH}/creature-draft"): resolve_hosted_build_pdf_world,
    ("POST", f"{PDF_STATBLOCK_REVIEW_PATH}/accept/{{draft_id}}"): resolve_hosted_build_pdf_world,
    ("POST", f"{PDF_STATBLOCK_REVIEW_PATH}/append/{{draft_id}}"): resolve_hosted_build_pdf_world,
    ("POST", f"{BUILD_PDF_SOURCES_PATH}/statblock:validate"): resolve_hosted_build_pdf_world,
    ("GET", BUILD_PDF_SOURCES_PATH): resolve_hosted_build_pdf_world,
    ("POST", BUILD_PDF_SOURCES_PATH): resolve_hosted_build_pdf_world,
    ("POST", f"{BUILD_PDF_SOURCES_PATH}/open"): resolve_hosted_build_pdf_world,
    ("POST", f"{BUILD_PDF_SOURCES_PATH}/region:validate"): resolve_hosted_build_pdf_world,
    ("GET", BUILD_PAGE_INVENTORY_PATH): resolve_hosted_build_page_inventory,
    ("POST", "/api/live/workspace-documents"): resolve_hosted_build_page_create,
    ("GET", "/api/live/workspace-documents/{document_id}"): resolve_hosted_build_page,
    ("GET", "/api/live/workspace-documents/{document_id}/snapshot"): resolve_hosted_build_page,
    ("GET", "/api/live/workspace-documents/{document_id}/native-world-source"): resolve_hosted_build_native_source,
    ("POST", "/api/live/workspace-documents/{document_id}/native-world-source"): resolve_hosted_build_native_source,
    ("GET", "/api/live/threat-drafts"): resolve_hosted_statblock_inventory,
    ("GET", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/preview"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/cancel"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/inspect"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/encounters/{encounter_id}"): resolve_hosted_combat_encounter,
    ("PUT", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/encounters/{encounter_id}"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/encounters/{encounter_id}/mechanics-adoptions"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/encounters/{encounter_id}/mechanics-adoptions:cancel"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/encounters/{encounter_id}/mechanics-adoptions/{operation_id}"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/run-encounters/{run_id}/scenes/{scene_id}/encounters/{encounter_id}/mechanics-adoptions"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/saved-statblocks/lookup"): resolve_hosted_statblock_inventory,
    ("GET", "/api/live/combat/encounters"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters/saved-mechanics/preview"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters/accepted-mechanics/preview"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters/conversation-variant/preview"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters/world-mechanics/preview"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/encounters/{encounter_id}"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/encounters/{encounter_id}/participants/{participant_id}/corpus-sheet"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions"): resolve_hosted_combat_encounter,
    ("POST", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions:cancel"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions/{operation_id}"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/combat/encounters/{encounter_id}/mechanics-adoptions"): resolve_hosted_combat_encounter,
    ("PUT", "/api/live/combat/encounters/{encounter_id}"): resolve_hosted_combat_encounter,
    ("GET", "/api/live/threat-drafts/{draft_id}/mechanics-revisions/{revision_id}"): resolve_hosted_saved_statblock,
    ("GET", "/api/live/threat-drafts/{draft_id}/mechanics-revisions"): resolve_hosted_saved_statblock,
    ("GET", "/api/live/threat-drafts/{draft_id}/native-creature"): resolve_hosted_native_creature,
    ("POST", "/api/live/threat-drafts/{draft_id}/native-creature/prepare"): resolve_hosted_native_creature,
    ("POST", "/api/live/threat-drafts/{draft_id}/native-creature/confirm"): resolve_hosted_native_creature,
    ("DELETE", "/api/live/threat-drafts/{draft_id}/saved-statblock"): resolve_hosted_saved_statblock,
    ("POST", "/api/live/threat-drafts/{draft_id}/mechanics-revisions"): resolve_hosted_statblock_revision_save,
    ("GET", "/api/live/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}"): resolve_hosted_saved_statblock,
    ("POST", "/api/live/threat-drafts/{draft_id}/mechanics-revision-operations/{operation_id}:recover"): resolve_hosted_saved_statblock,
    ("GET", "/api/live/world-mechanics/associations"): resolve_hosted_statblock_inventory,
    ("POST", "/api/live/world-mechanics/associations"): resolve_hosted_mechanics_association,
    ("GET", "/api/live/world-mechanics/associations/creatures"): resolve_hosted_plan_world_context,
    ("GET", "/api/live/world-mechanics/associations/requests/{request_id}"): resolve_hosted_plan_world_context,
    ("POST", "/api/live/tiptap/markdown-write/prepare"): resolve_hosted_build_page,
    ("POST", "/api/live/tiptap/markdown-write/commit"): resolve_hosted_build_page,
    ("POST", "/api/live/graph-preview/extraction-runs"): resolve_hosted_build_extraction,
    ("POST", "/api/live/graph-preview/build-recap-launches"): resolve_hosted_build_extraction,
    ("POST", "/api/live/graph-preview/build-worldbuilding-launches"): resolve_hosted_build_extraction,
    ("GET", "/api/live/graph-preview/extraction-runs"): resolve_hosted_saved_recap,
    ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection"): resolve_hosted_saved_recap,
    ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/usage"): resolve_hosted_saved_recap,
    ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/candidate-projection"): resolve_hosted_saved_recap,
    ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/recap-projection"): resolve_hosted_saved_recap,
    ("GET", "/api/live/graph-preview/extraction-runs/{run_id}"): resolve_hosted_exact_extraction_read,
    ("GET", "/api/live/graph-preview/extraction-runs/{run_id}/build-context"): resolve_hosted_exact_extraction_read,
    ("GET", "/api/live/extract-promote/runs/{run_id}/review-package"): resolve_hosted_exact_extraction_read,
    ("GET", "/api/live/extract-promote/runs/{run_id}/worldbuilding-publication-coverage"): resolve_hosted_build_extraction,
    ("GET", "/api/live/extract-promote/runs/{run_id}/frozen-source-spans"): resolve_hosted_build_extraction,
    ("POST", "/api/live/extract-promote/runs/{run_id}/evidence-corrections"): resolve_hosted_worldbuilding_evidence_correction,
    ("GET", WORLD_LOOKUP_PATH): resolve_hosted_world_lookup,
    ("POST", COMPLETE_OBJECT_PATH): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-graph-inspection/authoring-identities"): resolve_hosted_explorer_world,
    ("POST", INSPECTION_READ_PATH): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-graph-inspection/recap-page"): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-graph-inspection/related-recaps"): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-graph-inspection/catalog"): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-source-inspection/catalog"): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-source-inspection/read"): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-source-inspection/published-recap"): resolve_hosted_explorer_world,
    ("POST", "/api/live/native-source-inspection/published-recap/objects"): resolve_hosted_explorer_world,
    ("POST", f"{EXPLORER_PREFIX}/graph"): resolve_hosted_explorer_world,
}


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Prepare local Agent dependencies and own deterministic host shutdown."""
    dms_http_client: httpx.AsyncClient | None = None
    if deployment_environment() == PRODUCTION_ENVIRONMENT:
        config_errors = validate_hosted_auth_configuration(
            world_scope_resolvers=HOSTED_WORLD_SCOPE_RESOLVERS
        )
        if config_errors:
            raise RuntimeError(
                "hosted_auth_configuration_invalid:" + ",".join(config_errors)
            )
        dms_http_client = httpx.AsyncClient(timeout=5.0, follow_redirects=False)
        _application.state.dms_principal_resolver = DmsPrincipalResolver(
            api_origin=os.environ[DMS_API_ORIGIN_ENV],
            http_client=dms_http_client,
        )
        _application.state.dms_http_client = dms_http_client
    from apps.live_control_server.services.agent_turn_trace import configure_turn_trace_logging
    configure_turn_trace_logging()
    from apps.live_control_server.services.build_jev_runtime import prepare_default_build_runtime
    _application.state.build_jev_runtime_factory = prepare_default_build_runtime()
    get_hermes_graph_agent_host()
    try:
        yield
    finally:
        shutdown_hermes_graph_agent_host()
        _application.state.build_jev_runtime_factory = None
        if dms_http_client is not None:
            await dms_http_client.aclose()


class HostedRequestTiming:
    """Log application time to response headers using bounded route templates."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("uvicorn.error")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        status = 500
        headers_at = None

        async def observe(message: Message) -> None:
            nonlocal status, headers_at
            if message["type"] == "http.response.start":
                status = message["status"]
                headers_at = perf_counter()
            await send(message)

        try:
            await self.app(scope, receive, observe)
        finally:
            route = getattr(scope.get("route"), "path", "<unmatched>")
            elapsed_ms = ((headers_at if headers_at is not None else perf_counter()) - started) * 1000
            self.logger.info(
                "buddy_request method=%s route=%s status=%d response_start_ms=%.1f",
                scope["method"], route, status, elapsed_ms,
            )


def create_app() -> FastAPI:
    graph_preview_router = _load_graph_preview_router()
    hosted = deployment_environment() == PRODUCTION_ENVIRONMENT
    application = FastAPI(
        title="DungeonMindBuddy Live Control",
        version="0.1.0",
        description="L3 live-play API over file-backed session state (query spine + surface/jobs).",
        lifespan=lifespan,
        openapi_url=None if hosted else "/openapi.json",
    )
    application.include_router(live_router)
    application.include_router(conversation_library_router)
    application.include_router(conversation_work_plans_router)
    application.include_router(combat_encounters_router)
    application.include_router(combat_scene_templates_router)
    application.include_router(combat_run_encounters_router)
    application.include_router(world_mechanics_router)
    application.include_router(media_images_router)
    application.include_router(agent_graph_local_session_router)
    if graph_preview_router is not None:
        application.include_router(graph_preview_router)
    else:
        application.include_router(build_extraction_router, prefix="/api/live/graph-preview")
    application.include_router(graph_authoring_router)
    application.include_router(recap_ingest_router)
    application.include_router(party_registry_router)
    application.include_router(play_runs_router)
    application.include_router(play_prepared_tables_router)
    application.include_router(world_graph_bootstrap_router)
    application.include_router(extract_promote_router)
    application.include_router(source_statements_router)
    application.include_router(native_profile_transition_router)
    application.include_router(pdf_adventure_events_router)
    application.include_router(native_graph_inspection_router)
    application.include_router(native_source_inspection_router)
    application.include_router(world_graph_projection_router)
    application.include_router(world_graph_retrieval_router)
    application.include_router(rules_lookup_router)
    application.include_router(workspace_documents_router)
    application.include_router(workspace_lifecycle_router)
    application.include_router(world_containers_router)
    application.include_router(guest_releases_router)
    application.include_router(guest_release_public_router)
    application.include_router(statblock_integration_router)
    application.include_router(threat_drafts_router)
    application.include_router(threat_publication_router)
    application.include_router(threat_publication_identity_router)
    application.include_router(threat_publication_proposals_router)
    application.include_router(threat_publication_commits_router)
    application.include_router(threat_query_hydration_router)
    application.include_router(statblock_candidates_router)
    application.include_router(source_navigation_router)
    application.include_router(index_graph_router)
    application.include_router(native_graph_explorer_router)

    install_hosted_request_boundary(
        application, world_scope_resolvers=HOSTED_WORLD_SCOPE_RESOLVERS,
        collection_authorizers=HOSTED_WORLD_COLLECTION_AUTHORIZERS,
    )
    if hosted:
        application.add_middleware(HostedRequestTiming)

    @application.get(CURRENT_USER_PATH, include_in_schema=False)
    async def current_user(request: Request) -> dict[str, str]:
        principal = getattr(request.state, "dms_principal", None)
        if principal is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return {"sub": principal.subject}

    @application.get(LOGIN_PATH, include_in_schema=False)
    async def hosted_login(request: Request) -> Response:
        environment = deployment_environment()
        mode = auth_mode()
        if environment in {"local", "development", "dev"} and mode == "local_operator":
            return JSONResponse(
                status_code=409,
                content={"detail": {"code": "hosted_login_not_required"}},
            )
        if environment != PRODUCTION_ENVIRONMENT or mode != HOSTED_MODE:
            return JSONResponse(
                status_code=503,
                content={"detail": {"code": "hosted_auth_unavailable"}},
            )
        api_origin = fixed_dms_api_origin(os.environ.get(DMS_API_ORIGIN_ENV, ""))
        if api_origin is None:
            return JSONResponse(
                status_code=503,
                content={"detail": {"code": "hosted_auth_unavailable"}},
            )
        return_values = request.query_params.getlist("return_to")
        return_to = safe_hosted_return_path(
            return_values[0] if len(return_values) == 1 else "/"
        )
        query = urlencode({"frontend": "buddy", "redirect": return_to})
        return RedirectResponse(
            url=f"{api_origin}/api/auth/login?{query}",
            status_code=302,
        )

    @application.get(AUTH_SESSION_PATH, include_in_schema=False)
    async def auth_session(request: Request) -> Response:
        environment = deployment_environment()
        mode = auth_mode()
        if environment in {"local", "development", "dev"} and mode == "local_operator":
            return JSONResponse(content={"status": "local_operator"})
        if environment != PRODUCTION_ENVIRONMENT or mode != HOSTED_MODE:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable"},
            )
        resolver = getattr(request.app.state, "dms_principal_resolver", None)
        if resolver is None or not hasattr(resolver, "resolve"):
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        result = await resolver.resolve(request)
        if result.status == "authenticated" and result.principal is not None:
            return JSONResponse(
                content={
                    "status": "authenticated",
                    "subject": result.principal.subject,
                    "display_name": result.principal.display_name,
                },
                headers={"Cache-Control": "no-store"},
            )
        if result.status == "signed_out":
            return JSONResponse(status_code=401, content={"status": "signed_out"})
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    @application.post(LOGOUT_PATH, status_code=204, include_in_schema=False)
    async def logout(request: Request) -> Response:
        if deployment_environment() != PRODUCTION_ENVIRONMENT or auth_mode() != HOSTED_MODE:
            raise HTTPException(status_code=503, detail="Hosted logout is unavailable")
        require_cookie_write_origin(
            request,
            trusted_origins=tuple(
                item.strip()
                for item in os.environ.get("AUTH_TRUSTED_FRONTEND_ORIGINS", "").split(",")
                if item.strip()
            ),
        )
        origins = request.headers.getlist("origin")
        cookie_value = request.cookies.get(DMS_SESSION_COOKIE_NAME)
        headers = {"Origin": origins[0]}
        if cookie_value:
            headers["Cookie"] = f"{DMS_SESSION_COOKIE_NAME}={cookie_value}"
        client: httpx.AsyncClient | None = getattr(request.app.state, "dms_http_client", None)
        if client is None:
            raise HTTPException(status_code=503, detail="Hosted logout is unavailable")
        dms_url = f"{os.environ[DMS_API_ORIGIN_ENV].rstrip('/')}/api/auth/logout"
        try:
            response = await client.post(dms_url, headers=headers, follow_redirects=False)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc
        try:
            if response.status_code != 204:
                raise HTTPException(
                    status_code=response.status_code if response.status_code in {401, 403} else 503,
                    detail="Authentication service rejected logout",
                )
            outgoing = Response(status_code=204)
            for name, value in response.headers.multi_items():
                if name.lower() == "set-cookie":
                    outgoing.headers.append(name, value)
            return outgoing
        finally:
            await response.aclose()

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @application.get("/health/ready", response_model=None)
    def health_ready() -> dict[str, str] | Response:
        if deployment_environment() != PRODUCTION_ENVIRONMENT:
            return {"status": "ready"}
        config_errors = validate_hosted_auth_configuration(
            world_scope_resolvers=HOSTED_WORLD_SCOPE_RESOLVERS
        )
        if config_errors:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "code": "hosted_configuration_invalid"},
            )
        from apps.live_control_server.services.runtime_preflight import run_runtime_preflight
        from apps.live_control_server.config import repo_root

        report = run_runtime_preflight(
            repo_root=repo_root(), load_env=False, include_runbooks=False,
            include_operator_diagnostics=False,
        )
        if report.status != "READY":
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "code": "runtime_preflight_failed"},
            )
        return {"status": "ready"}

    async def serve_frontend(request: Request, spa_path: str = "") -> Response:
        if deployment_environment() != PRODUCTION_ENVIRONMENT:
            return PlainTextResponse("Not found", status_code=404)
        static_root = (Path(__file__).resolve().parents[1] / "live-control-ui" / "dist").resolve()
        index_path = static_root / "index.html"
        if not index_path.is_file():
            return PlainTextResponse("Frontend build is unavailable", status_code=503)
        requested = (static_root / spa_path).resolve()
        if not requested.is_relative_to(static_root):
            return PlainTextResponse("Not found", status_code=404)
        if requested.is_file():
            cache_control = "no-cache"
            if requested.parent == static_root / "assets" and re.fullmatch(
                r".+-[A-Za-z0-9_-]{8}\.[A-Za-z0-9]+", requested.name
            ):
                cache_control = "public, max-age=31536000, immutable"
            return FileResponse(requested, headers={"Cache-Control": cache_control})
        if spa_path == "assets" or spa_path.startswith("assets/"):
            return PlainTextResponse("Not found", status_code=404)
        if request.headers.get("accept", "").lower().find("text/html") >= 0:
            return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
        return PlainTextResponse("Not found", status_code=404)

    application.add_api_route(
        "/", serve_frontend, methods=["GET", "HEAD"], include_in_schema=False
    )
    application.add_api_route(
        "/{spa_path:path}", serve_frontend, methods=["GET", "HEAD"], include_in_schema=False
    )

    return application


app = create_app()
