from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .model import (
    AliasCandidate,
    ContextVocabularyPacket,
    ContainmentHint,
    DoNotMergeDecision,
    LexicalObservation,
    SourceArtifactRef,
    VocabularyEntry,
)

MODEL_REGISTRY: dict[str, type[Any]] = {
    "SourceArtifactRef": SourceArtifactRef,
    "LexicalObservation": LexicalObservation,
    "VocabularyEntry": VocabularyEntry,
    "AliasCandidate": AliasCandidate,
    "DoNotMergeDecision": DoNotMergeDecision,
    "ContainmentHint": ContainmentHint,
    "ContextVocabularyPacket": ContextVocabularyPacket,
}

_MODEL_TO_BUNDLE_FIELD = {
    "SourceArtifactRef": "source_artifacts",
    "LexicalObservation": "lexical_observations",
    "VocabularyEntry": "vocabulary_entries",
    "AliasCandidate": "alias_candidates",
    "DoNotMergeDecision": "do_not_merge_decisions",
    "ContainmentHint": "containment_hints",
}


@dataclass(slots=True)
class VocabularyArtifactManifestFile:
    path: str
    model: str
    count: int
    purpose: str | None = None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VocabularyArtifactManifestFile":
        row = cls(
            path=payload.get("path", ""),
            model=payload.get("model", ""),
            count=payload.get("count", -1),
            purpose=payload.get("purpose"),
        )
        row.validate()
        return row

    def validate(self) -> None:
        if not self.path.strip():
            raise ValueError("manifest file path must be non-empty")
        if not self.model.strip():
            raise ValueError(f"manifest file {self.path} model must be non-empty")
        if self.model not in MODEL_REGISTRY:
            raise ValueError(f"unknown model in manifest for {self.path}: {self.model}")
        if not isinstance(self.count, int) or self.count < 0:
            raise ValueError(f"manifest file {self.path} count must be >= 0")


@dataclass(slots=True)
class VocabularyArtifactManifest:
    schema: str
    fixture_id: str | None = None
    artifact_id: str | None = None
    authority_class: str = "vocabulary_contract_fixture"
    candidate_graph_comparison: bool = False
    status: str | None = None
    description: str | None = None
    files: list[VocabularyArtifactManifestFile] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VocabularyArtifactManifest":
        files_payload = payload.get("files", [])
        if not isinstance(files_payload, list):
            raise ValueError("manifest files must be a list")
        manifest = cls(
            schema=payload.get("schema", ""),
            fixture_id=payload.get("fixture_id"),
            artifact_id=payload.get("artifact_id"),
            authority_class=payload.get("authority_class", "vocabulary_contract_fixture"),
            candidate_graph_comparison=payload.get("candidate_graph_comparison", False),
            status=payload.get("status"),
            description=payload.get("description"),
            files=[VocabularyArtifactManifestFile.from_dict(item) for item in files_payload],
            non_goals=list(payload.get("non_goals", [])),
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not self.schema.strip():
            raise ValueError("manifest schema must be non-empty")
        if not self.authority_class.strip():
            raise ValueError("manifest authority_class must be non-empty")
        if self.candidate_graph_comparison is not False:
            raise ValueError("vocabulary artifact candidate_graph_comparison must be false")
        paths: set[str] = set()
        for file_row in self.files:
            file_row.validate()
            if file_row.path in paths:
                raise ValueError(f"duplicate manifest file path: {file_row.path}")
            paths.add(file_row.path)


@dataclass(slots=True)
class VocabularyArtifactSummary:
    source_artifact_count: int
    lexical_observation_count: int
    vocabulary_entry_count: int
    alias_candidate_count: int
    do_not_merge_decision_count: int
    containment_hint_count: int
    has_context_vocabulary_packet: bool
    entity_kind_counts: dict[str, int] = field(default_factory=dict)
    risk_flag_counts: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class VocabularyArtifactBundle:
    root: Path
    manifest: VocabularyArtifactManifest
    source_artifacts: list[SourceArtifactRef] = field(default_factory=list)
    lexical_observations: list[LexicalObservation] = field(default_factory=list)
    vocabulary_entries: list[VocabularyEntry] = field(default_factory=list)
    alias_candidates: list[AliasCandidate] = field(default_factory=list)
    do_not_merge_decisions: list[DoNotMergeDecision] = field(default_factory=list)
    containment_hints: list[ContainmentHint] = field(default_factory=list)
    context_vocabulary_packet: ContextVocabularyPacket | None = None

    def summary(self) -> VocabularyArtifactSummary:
        entity_kind_counts: dict[str, int] = {}
        for entry in self.vocabulary_entries:
            entity_kind_counts[entry.entity_kind] = entity_kind_counts.get(entry.entity_kind, 0) + 1

        risk_flag_counts: dict[str, int] = {}
        for alias in self.alias_candidates:
            for risk_flag in alias.risk_flags:
                risk_flag_counts[risk_flag] = risk_flag_counts.get(risk_flag, 0) + 1

        return VocabularyArtifactSummary(
            source_artifact_count=len(self.source_artifacts),
            lexical_observation_count=len(self.lexical_observations),
            vocabulary_entry_count=len(self.vocabulary_entries),
            alias_candidate_count=len(self.alias_candidates),
            do_not_merge_decision_count=len(self.do_not_merge_decisions),
            containment_hint_count=len(self.containment_hints),
            has_context_vocabulary_packet=self.context_vocabulary_packet is not None,
            entity_kind_counts=entity_kind_counts,
            risk_flag_counts=risk_flag_counts,
        )

    def to_diagnostics(self) -> dict[str, Any]:
        summary = self.summary()
        return {
            "root": str(self.root),
            "schema": self.manifest.schema,
            "authority_class": self.manifest.authority_class,
            "candidate_graph_comparison": self.manifest.candidate_graph_comparison,
            "counts": {
                "source_artifacts": summary.source_artifact_count,
                "lexical_observations": summary.lexical_observation_count,
                "vocabulary_entries": summary.vocabulary_entry_count,
                "alias_candidates": summary.alias_candidate_count,
                "do_not_merge_decisions": summary.do_not_merge_decision_count,
                "containment_hints": summary.containment_hint_count,
                "context_vocabulary_packet": 1 if summary.has_context_vocabulary_packet else 0,
            },
            "entity_kind_counts": summary.entity_kind_counts,
            "risk_flag_counts": summary.risk_flag_counts,
        }


def load_vocabulary_artifact_bundle(root: str | Path) -> VocabularyArtifactBundle:
    artifact_root = Path(root)
    manifest_path = artifact_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing vocabulary artifact manifest.json: {manifest_path}")

    manifest_payload = _load_json(manifest_path)
    if not isinstance(manifest_payload, Mapping):
        raise ValueError("manifest.json must contain a JSON object")
    manifest = VocabularyArtifactManifest.from_dict(manifest_payload)

    bundle = VocabularyArtifactBundle(root=artifact_root, manifest=manifest)
    for file_row in manifest.files:
        payload_path = artifact_root / file_row.path
        if not payload_path.exists():
            raise FileNotFoundError(f"missing vocabulary artifact file: {payload_path}")
        payload = _load_json(payload_path)
        model_cls = MODEL_REGISTRY[file_row.model]

        if file_row.model == "ContextVocabularyPacket":
            if isinstance(payload, list):
                raise ValueError("ContextVocabularyPacket payload must be a single JSON object, not a list")
            if not isinstance(payload, Mapping):
                raise ValueError("ContextVocabularyPacket payload must be a JSON object")
            _validate_count(file_row, 1)
            bundle.context_vocabulary_packet = model_cls.from_dict(payload)
            continue

        if not isinstance(payload, list):
            raise ValueError(f"{file_row.model} payload {file_row.path} must be a list")
        _validate_count(file_row, len(payload))
        setattr(bundle, _MODEL_TO_BUNDLE_FIELD[file_row.model], [model_cls.from_dict(item) for item in payload])

    return bundle


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in {path}: {exc.msg}") from exc


def _validate_count(file_row: VocabularyArtifactManifestFile, actual_count: int) -> None:
    if actual_count != file_row.count:
        raise ValueError(
            f"manifest count mismatch for {file_row.path}: expected {file_row.count}, got {actual_count}"
        )
