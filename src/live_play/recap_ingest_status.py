from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecapIngestStatus:
    campaign_id: str
    session: int
    status: str = "initialized"
    states: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    paths: dict[str, str | None] = field(default_factory=dict)
    authority: dict[str, str] = field(
        default_factory=lambda: {
            "staged_raw_notes": "pre_canonical_evidence",
            "canonical_recap": "canon_play",
            "normalized_recap": "canon_play_prepared",
            "frontmatter_seed": "reviewable_route_allowlist",
            "breadcrumbed_recap": "canon_play_routed",
            "session_memory": "derived_memory",
        }
    )
    ingest_report: dict[str, Any] = field(default_factory=dict)
    entity_spelling_audit: list[dict[str, Any]] = field(default_factory=list)

    def add_state(self, value: str) -> None:
        if value not in self.states:
            self.states.append(value)

    def add_warning(self, value: str) -> None:
        if value not in self.warnings:
            self.warnings.append(value)

    def add_error(self, value: str) -> None:
        if value not in self.errors:
            self.errors.append(value)

    def add_next_action(self, value: str) -> None:
        if value not in self.next_actions:
            self.next_actions.append(value)

    def resolve_status(self) -> None:
        if self.errors:
            self.status = "error"
            return
        if "normalized_recap_duplicates" in self.states:
            self.status = "needs_reconciliation"
            return
        if "breadcrumb_required" in self.states:
            self.status = "breadcrumb_required"
            return
        if "ready_for_planning_activation" in self.states:
            self.status = "ready_for_planning_activation"
            return
        if "recap_applied" in self.states or "recap_reused" in self.states:
            self.status = "recap_applied"
            return
        if "recap_preview_created" in self.states:
            self.status = "recap_preview_created"
            return
        self.status = "initialized"

    def to_dict(self) -> dict[str, Any]:
        self.resolve_status()
        return {
            "schema": "dmb_raw_recap_ingest_status_v1",
            "campaign_id": self.campaign_id,
            "session": self.session,
            "status": self.status,
            "states": list(self.states),
            "paths": dict(self.paths),
            "authority": dict(self.authority),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "next_actions": list(self.next_actions),
            "ingest_report": dict(self.ingest_report),
            "entity_spelling_audit": list(self.entity_spelling_audit),
        }
