"""File-backed store for authored campaign graph overlay documents."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.graph_memory.party_context import resolve_campaign_corpus
from src.live_play.live_store import load_json, write_json

from apps.live_control_server.models.graph_authoring_overlay import (
    AUTHORED_GRAPH_OVERLAY_SCHEMA,
    AuthoredGraphAssertion,
    AuthoredGraphOverlay,
    UnsafeCampaignRelError,
    create_empty_authored_graph_overlay,
    isoformat_z,
    validate_campaign_id,
    validate_campaign_rel,
)

GRAPH_AUTHORING_DIR = "_graph_authoring"
OVERLAYS_DIR = "overlays"
EVENTS_DIR = "events"
BACKUPS_DIR = "backups"
EXPORTS_DIR = "exports"
OVERLAY_FILENAME = "authored_graph_overlay.json"
EVENTS_FILENAME = "graph_authoring_events.jsonl"


class GraphAuthoringOverlayStoreError(ValueError):
    status_code = 422


class GraphAuthoringOverlayStore:
    """Isolated file store for authored graph overlay JSON under campaign corpus roots."""

    def __init__(self, corpus_root: Path) -> None:
        self._corpus_root = corpus_root.resolve()

    @property
    def corpus_root(self) -> Path:
        return self._corpus_root

    def _resolve_campaign_directory(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> Path:
        safe_campaign_id = validate_campaign_id(campaign_id)
        if campaign_rel is not None:
            rel = validate_campaign_rel(campaign_rel)
        else:
            _, rel = resolve_campaign_corpus(
                safe_campaign_id,
                corpus_root=self._corpus_root,
            )
            rel = validate_campaign_rel(rel)
        target = (self._corpus_root / rel).resolve()
        try:
            target.relative_to(self._corpus_root)
        except ValueError as exc:
            raise UnsafeCampaignRelError("campaign path escapes corpus root") from exc
        return target

    def campaign_graph_authoring_root(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> Path:
        return self._resolve_campaign_directory(campaign_id, campaign_rel=campaign_rel) / GRAPH_AUTHORING_DIR

    def overlay_path(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> Path:
        return (
            self.campaign_graph_authoring_root(campaign_id, campaign_rel=campaign_rel)
            / OVERLAYS_DIR
            / OVERLAY_FILENAME
        )

    def events_path(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> Path:
        return (
            self.campaign_graph_authoring_root(campaign_id, campaign_rel=campaign_rel)
            / EVENTS_DIR
            / EVENTS_FILENAME
        )

    def backups_dir(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> Path:
        return self.campaign_graph_authoring_root(campaign_id, campaign_rel=campaign_rel) / BACKUPS_DIR

    def exports_dir(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> Path:
        return self.campaign_graph_authoring_root(campaign_id, campaign_rel=campaign_rel) / EXPORTS_DIR

    def load_overlay(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> AuthoredGraphOverlay:
        safe_campaign_id = validate_campaign_id(campaign_id)
        path = self.overlay_path(safe_campaign_id, campaign_rel=campaign_rel)
        if not path.is_file():
            return create_empty_authored_graph_overlay(safe_campaign_id)
        payload = load_json(path)
        if payload.get("schema_version") != AUTHORED_GRAPH_OVERLAY_SCHEMA:
            raise GraphAuthoringOverlayStoreError(
                f"unsupported authored graph overlay schema in {path}"
            )
        return AuthoredGraphOverlay.model_validate(payload)

    def save_overlay(
        self,
        overlay: AuthoredGraphOverlay,
        *,
        campaign_rel: str | None = None,
    ) -> None:
        validate_campaign_id(overlay.campaign_id)
        path = self.overlay_path(overlay.campaign_id, campaign_rel=campaign_rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, overlay.model_dump(mode="json"))

    def append_assertions(
        self,
        campaign_id: str,
        assertions: list[AuthoredGraphAssertion],
        *,
        campaign_rel: str | None = None,
    ) -> AuthoredGraphOverlay:
        safe_campaign_id = validate_campaign_id(campaign_id)
        overlay = self.load_overlay(safe_campaign_id, campaign_rel=campaign_rel)
        if overlay.campaign_id != safe_campaign_id:
            raise GraphAuthoringOverlayStoreError("overlay campaign_id mismatch")
        for assertion in assertions:
            if assertion.campaign_id != safe_campaign_id:
                raise GraphAuthoringOverlayStoreError(
                    "assertion campaign_id must match overlay campaign_id"
                )
        updated_assertions = list(overlay.assertions)
        index_by_id = {
            assertion.assertion_id: index for index, assertion in enumerate(updated_assertions)
        }
        for assertion in assertions:
            if assertion.assertion_id in index_by_id:
                updated_assertions[index_by_id[assertion.assertion_id]] = assertion
            else:
                index_by_id[assertion.assertion_id] = len(updated_assertions)
                updated_assertions.append(assertion)
        updated = overlay.model_copy(
            update={
                "assertions": updated_assertions,
                "updated_at": isoformat_z(datetime.now(UTC)),
            }
        )
        if campaign_rel is not None:
            self.save_overlay(updated, campaign_rel=campaign_rel)
        else:
            self.save_overlay(updated)
        return updated

    def supersede_assertions(
        self,
        campaign_id: str,
        assertion_ids: set[str],
        *,
        campaign_rel: str | None = None,
    ) -> AuthoredGraphOverlay:
        if not assertion_ids:
            return self.load_overlay(campaign_id, campaign_rel=campaign_rel)
        safe_campaign_id = validate_campaign_id(campaign_id)
        overlay = self.load_overlay(safe_campaign_id, campaign_rel=campaign_rel)
        updated_assertions: list[AuthoredGraphAssertion] = []
        for assertion in overlay.assertions:
            if assertion.assertion_id in assertion_ids and assertion.status == "authored":
                updated_assertions.append(assertion.model_copy(update={"status": "superseded"}))
            else:
                updated_assertions.append(assertion)
        updated = overlay.model_copy(
            update={
                "assertions": updated_assertions,
                "updated_at": isoformat_z(datetime.now(UTC)),
            }
        )
        if campaign_rel is not None:
            self.save_overlay(updated, campaign_rel=campaign_rel)
        else:
            self.save_overlay(updated)
        return updated

    def list_assertions(
        self,
        campaign_id: str,
        *,
        campaign_rel: str | None = None,
    ) -> list[AuthoredGraphAssertion]:
        overlay = self.load_overlay(campaign_id, campaign_rel=campaign_rel)
        return list(overlay.assertions)
