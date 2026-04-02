from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.contracts.schema_validation import validate_many
from src.contracts.entity_tags import normalize_entity_tags
from src.reducer.canon_projection import project_entity_state


class FactStore:
    """JSON-backed store for evidence units, entities, and facts."""

    _PRONOUN_ALIASES = {
        "he",
        "she",
        "they",
        "it",
        "him",
        "her",
        "them",
        "his",
        "hers",
        "their",
        "theirs",
    }
    _MAX_ALIASES_PER_ENTITY = 20
    _MAX_ENTITY_TAGS_MERGED = 20

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = Path(store_dir)
        self.logs_dir = self.store_dir / "logs"
        self.evidence_units: list[dict[str, Any]] = []
        self.entities: list[dict[str, Any]] = []
        self.facts: list[dict[str, Any]] = []
        self.canon_decisions: list[dict[str, Any]] = []
        self.ingest_index: dict[str, dict[str, Any]] = {}

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
        canon_path = self._path("canon_decisions")
        if canon_path.exists():
            self.canon_decisions = self._read_json_list(canon_path)
        else:
            self.canon_decisions = []
        ingest_index_path = self._path("ingest_index")
        if ingest_index_path.exists():
            payload = json.loads(ingest_index_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self.ingest_index = payload
            else:
                self.ingest_index = {}
        else:
            self.ingest_index = {}

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
        self._path("canon_decisions").write_text(
            json.dumps(self.canon_decisions, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._path("ingest_index").write_text(
            json.dumps(self.ingest_index, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    def add_evidence_units(self, units: list[dict[str, Any]]) -> None:
        validate_many(units, "evidence_unit.schema.json")
        self.evidence_units.extend(deepcopy(units))

    def has_ingest_fingerprint(self, ingest_key: str) -> bool:
        return ingest_key in self.ingest_index

    def record_ingest_fingerprint(self, ingest_key: str, metadata: dict[str, Any]) -> None:
        self.ingest_index[ingest_key] = deepcopy(metadata)

    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
        return re.sub(r"\s+", " ", normalized).strip()

    @classmethod
    def _filtered_entity_names(cls, entity: dict[str, Any]) -> set[str]:
        names = {
            cls._normalize_name(str(entity.get("display_name", ""))),
            *[
                cls._normalize_name(str(alias))
                for alias in entity.get("aliases", [])
                if isinstance(alias, str)
            ],
        }
        return {name for name in names if name and name not in cls._PRONOUN_ALIASES}

    def _audit_entity_merge(
        self,
        *,
        action: str,
        reason_code: str,
        existing: dict[str, Any],
        candidate: dict[str, Any],
        overlap: list[str],
    ) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        audit_path = self.logs_dir / "entity_merge_audit.jsonl"
        payload = {
            "action": action,
            "reason_code": reason_code,
            "existing_entity_id": existing.get("entity_id"),
            "candidate_entity_id": candidate.get("entity_id"),
            "existing_type": existing.get("entity_type"),
            "candidate_type": candidate.get("entity_type"),
            "overlap": sorted(overlap),
        }
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _resolve_entity_match(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        names = self._filtered_entity_names(candidate)
        if not names:
            return None
        candidate_type = str(candidate.get("entity_type", "other")).strip().lower() or "other"

        for existing in self.entities:
            existing_names = self._filtered_entity_names(existing)
            overlap = names & existing_names
            if not overlap:
                continue

            existing_type = str(existing.get("entity_type", "other")).strip().lower() or "other"
            if (
                existing_type != candidate_type
                and existing_type != "other"
                and candidate_type != "other"
            ):
                self._audit_entity_merge(
                    action="blocked",
                    reason_code="entity_type_mismatch",
                    existing=existing,
                    candidate=candidate,
                    overlap=list(overlap),
                )
                continue

            if all(token in self._PRONOUN_ALIASES for token in overlap):
                self._audit_entity_merge(
                    action="blocked",
                    reason_code="pronoun_only_overlap",
                    existing=existing,
                    candidate=candidate,
                    overlap=list(overlap),
                )
                continue

            if all(len(token) <= 2 for token in overlap):
                self._audit_entity_merge(
                    action="blocked",
                    reason_code="weak_overlap_token",
                    existing=existing,
                    candidate=candidate,
                    overlap=list(overlap),
                )
                continue

            self._audit_entity_merge(
                action="merged",
                reason_code="validated_overlap",
                existing=existing,
                candidate=candidate,
                overlap=list(overlap),
            )
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
            all_sorted = sorted(merged_aliases, key=len)
            matched["aliases"] = all_sorted[: self._MAX_ALIASES_PER_ENTITY]
            mention_ids = {
                *[str(mid) for mid in matched.get("source_mention_ids", [])],
                *[str(mid) for mid in candidate.get("source_mention_ids", [])],
            }
            matched["source_mention_ids"] = sorted(mention_ids)
            merged_tags = list(matched.get("entity_tags") or []) + list(
                candidate.get("entity_tags") or []
            )
            matched["entity_tags"] = normalize_entity_tags(
                merged_tags, max_tags=self._MAX_ENTITY_TAGS_MERGED
            )
            if (
                matched.get("entity_status") == "provisional"
                and candidate.get("entity_status") in {"canonical", "ambiguous"}
            ):
                matched["entity_status"] = candidate["entity_status"]
                matched["canonical_name"] = candidate.get("canonical_name")

    def add_facts(self, facts: list[dict[str, Any]]) -> None:
        validate_many(facts, "fact.schema.json")
        self.facts.extend(deepcopy(facts))

    def add_canon_decisions(self, decisions: list[dict[str, Any]]) -> None:
        validate_many(decisions, "canon_decision.schema.json")
        self.canon_decisions.extend(deepcopy(decisions))

    def merge_quality_signals(self) -> dict[str, Any]:
        """Lightweight merge-hygiene metrics (alias cardinality; audit tail)."""
        alias_counts: list[tuple[str, int]] = []
        for entity in self.entities:
            eid = str(entity.get("entity_id", ""))
            aliases = [a for a in entity.get("aliases", []) if isinstance(a, str)]
            alias_counts.append((eid, len(aliases)))
        alias_counts.sort(key=lambda row: row[1], reverse=True)
        top = [{"entity_id": eid, "alias_count": n} for eid, n in alias_counts[:8]]
        max_aliases = alias_counts[0][1] if alias_counts else 0
        heavy = sum(1 for _, n in alias_counts if n >= 8)
        audit_path = self.logs_dir / "entity_merge_audit.jsonl"
        merge_events = 0
        blocked_events = 0
        if audit_path.exists():
            tail = audit_path.read_text(encoding="utf-8").strip().splitlines()[-200:]
            for line in tail:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("action") == "merged":
                    merge_events += 1
                elif row.get("action") == "blocked":
                    blocked_events += 1
        return {
            "max_alias_count": max_aliases,
            "entities_with_alias_count_ge_8": heavy,
            "top_alias_counts": top,
            "merge_audit_tail_merged": merge_events,
            "merge_audit_tail_blocked": blocked_events,
        }

    @staticmethod
    def _fact_compaction_key(fact: dict[str, Any]) -> tuple[str, str, str]:
        value = fact.get("value", {})
        normalized_or_label = value.get("normalized") or value.get("label", "")
        return (
            str(fact.get("subject_entity_id", "")).strip(),
            str(fact.get("attribute", "")).strip(),
            str(normalized_or_label).strip().lower(),
        )

    def compact(self) -> dict[str, int]:
        evidence_by_id: dict[str, dict[str, Any]] = {}
        for unit in self.evidence_units:
            evidence_id = str(unit.get("evidence_id", "")).strip()
            if evidence_id and evidence_id not in evidence_by_id:
                evidence_by_id[evidence_id] = deepcopy(unit)

        fact_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        for fact in self.facts:
            key = self._fact_compaction_key(fact)
            if key not in fact_by_key:
                fact_by_key[key] = deepcopy(fact)
                continue

            existing = fact_by_key[key]
            merged_evidence_ids = list(
                dict.fromkeys(
                    [*existing.get("evidence_ids", []), *fact.get("evidence_ids", [])]
                )
            )
            existing["evidence_ids"] = merged_evidence_ids

            existing_label = str(existing.get("value", {}).get("label", ""))
            incoming_label = str(fact.get("value", {}).get("label", ""))
            if len(incoming_label) > len(existing_label):
                existing["value"]["label"] = incoming_label

        before_evidence = len(self.evidence_units)
        before_facts = len(self.facts)
        self.evidence_units = list(evidence_by_id.values())
        self.facts = list(fact_by_key.values())
        return {
            "evidence_before": before_evidence,
            "evidence_after": len(self.evidence_units),
            "facts_before": before_facts,
            "facts_after": len(self.facts),
        }

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
            canon_decisions=self.canon_decisions,
            campaign_id=campaign_id,
        )
