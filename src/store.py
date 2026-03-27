from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.contracts.schema_validation import validate_many
from src.reducer.canon_projection import project_entity_state


class FactStore:
    """JSON-backed store for evidence units, entities, and facts."""

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = Path(store_dir)
        self.evidence_units: list[dict[str, Any]] = []
        self.entities: list[dict[str, Any]] = []
        self.facts: list[dict[str, Any]] = []

    def _path(self, name: str) -> Path:
        return self.store_dir / f"{name}.json"

    def _read_json_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON array")
        return payload

    def load(self) -> None:
        self.evidence_units = self._read_json_list(self._path("evidence_units"))
        self.entities = self._read_json_list(self._path("entities"))
        self.facts = self._read_json_list(self._path("facts"))

    def save(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._path("evidence_units").write_text(
            json.dumps(self.evidence_units, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._path("entities").write_text(
            json.dumps(self.entities, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._path("facts").write_text(
            json.dumps(self.facts, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_evidence_units(self, units: list[dict[str, Any]]) -> None:
        validate_many(units, "evidence_unit.schema.json")
        self.evidence_units.extend(deepcopy(units))

    def _resolve_entity_match(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        names = {
            str(candidate.get("display_name", "")).strip().lower(),
            *[str(alias).strip().lower() for alias in candidate.get("aliases", [])],
        }
        names.discard("")
        if not names:
            return None
        for existing in self.entities:
            existing_names = {
                str(existing.get("display_name", "")).strip().lower(),
                *[str(alias).strip().lower() for alias in existing.get("aliases", [])],
            }
            existing_names.discard("")
            if names & existing_names:
                return existing
        return None

    def add_entities(self, entities: list[dict[str, Any]]) -> None:
        validate_many(entities, "entity.schema.json")
        for candidate in deepcopy(entities):
            matched = self._resolve_entity_match(candidate)
            if matched is None:
                self.entities.append(candidate)
                continue

            merged_aliases = {
                *[str(alias) for alias in matched.get("aliases", [])],
                *[str(alias) for alias in candidate.get("aliases", [])],
                str(matched.get("display_name", "")),
                str(candidate.get("display_name", "")),
            }
            merged_aliases.discard("")
            matched["aliases"] = sorted(merged_aliases)
            mention_ids = {
                *[str(mid) for mid in matched.get("source_mention_ids", [])],
                *[str(mid) for mid in candidate.get("source_mention_ids", [])],
            }
            matched["source_mention_ids"] = sorted(mention_ids)
            if (
                matched.get("entity_status") == "provisional"
                and candidate.get("entity_status") in {"canonical", "ambiguous"}
            ):
                matched["entity_status"] = candidate["entity_status"]
                matched["canonical_name"] = candidate.get("canonical_name")

    def add_facts(self, facts: list[dict[str, Any]]) -> None:
        validate_many(facts, "fact.schema.json")
        self.facts.extend(deepcopy(facts))

    def get_entity_by_name(self, name: str) -> dict[str, Any] | None:
        needle = name.strip().lower()
        if not needle:
            return None
        for entity in self.entities:
            display = str(entity.get("display_name", "")).strip().lower()
            aliases = [str(alias).strip().lower() for alias in entity.get("aliases", [])]
            if needle == display or needle in aliases:
                return deepcopy(entity)
        return None

    def list_entities(self) -> list[dict[str, Any]]:
        return deepcopy(self.entities)

    def project(self, campaign_id: str | None) -> dict[str, Any]:
        return project_entity_state(
            evidence_units=self.evidence_units,
            facts=self.facts,
            conflicts=[],
            canon_decisions=[],
            campaign_id=campaign_id,
        )
