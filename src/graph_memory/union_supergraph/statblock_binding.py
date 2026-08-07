"""Strict graph-owned contracts for pinned DungeonMind statblock bindings."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

EXTERNAL_RESOURCE_SCHEMA = "dmb_external_resource_v1"
THREAT_STATBLOCK_BINDING_SCHEMA = "dmb_threat_statblock_binding_v1"
WORLD_OBJECT_STATBLOCK_BINDING_SCHEMA = "dmb_world_object_statblock_binding_v1"
PROVIDER = "dungeonmind"
CONTRACT = "dungeonmind.dungeonbuddy-statblocks"
CONTRACT_VERSION = "1.0.0"

WorldObjectStatblockKind = Literal["threat", "npc"]
StatblockBindingRole = Literal[
    "primary", "alternate", "phase", "encounter_variant", "template"
]

MECHANICS_ELIGIBLE_WORLD_OBJECT_KINDS: frozenset[str] = frozenset({"threat", "npc"})

_STATBLOCK_ID_PATTERN = r"^sb_[a-z0-9]+$"
_REVISION_ID_PATTERN = r"^rev_[a-z0-9]+$"
_DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"
_EXTERNAL_NODE_PREFIX = "external:dungeonmind:statblock:"
FORBIDDEN_MECHANICS_KEYS = frozenset(
    {
        "definition",
        "rules_elements",
        "rendered_markdown",
        "markdown",
        "assets",
        "mechanics",
        "statblock_definition",
    }
)
_PROVENANCE_VALUE_KEYS = frozenset(
    {
        "source_domain",
        "source_domains",
        "source_artifact_id",
        "source_artifacts",
        "source_revision_id",
        "evidence",
        "evidence_ref_ids",
    }
)
_USES_STATBLOCK_VALUE_KEYS = frozenset(
    {
        "edge_id",
        "direction",
        "threat_statblock_binding",
        "statblock_binding",
    }
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExternalResourceV1(_StrictModel):
    schema_: Literal["dmb_external_resource_v1"] = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    provider: Literal["dungeonmind"]
    resource_type: Literal["statblock"]
    resource_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    contract: Literal["dungeonmind.dungeonbuddy-statblocks"]
    contract_version: Literal["1.0.0"]


class ThreatStatblockBindingV1(_StrictModel):
    schema_: Literal["dmb_threat_statblock_binding_v1"] = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    binding_id: str
    provider: Literal["dungeonmind"]
    statblock_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    revision_id: str = Field(pattern=_REVISION_ID_PATTERN)
    contract: Literal["dungeonmind.dungeonbuddy-statblocks"]
    contract_version: Literal["1.0.0"]
    definition_digest: str = Field(pattern=_DIGEST_PATTERN)
    role: StatblockBindingRole
    phase_key: str | None = None
    variant_label: str | None = None

    @model_validator(mode="after")
    def _validate_role_metadata(self) -> ThreatStatblockBindingV1:
        if self.role == "phase" and not (self.phase_key or "").strip():
            raise ValueError("phase_key is required when role is phase")
        if self.role != "phase" and self.phase_key is not None:
            raise ValueError("phase_key is only allowed when role is phase")
        return self


class WorldObjectStatblockBindingV1(_StrictModel):
    """Generic exact statblock binding for mechanics-eligible world objects.

    Additive to ``ThreatStatblockBindingV1``. Eligible source kinds are Threat
    and NPC only. PlayerCharacter and other kinds must fail closed.
    """

    schema_: Literal["dmb_world_object_statblock_binding_v1"] = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    binding_id: str
    world_object_kind: WorldObjectStatblockKind
    provider: Literal["dungeonmind"]
    statblock_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    revision_id: str = Field(pattern=_REVISION_ID_PATTERN)
    contract: Literal["dungeonmind.dungeonbuddy-statblocks"]
    contract_version: Literal["1.0.0"]
    definition_digest: str = Field(pattern=_DIGEST_PATTERN)
    role: StatblockBindingRole
    phase_key: str | None = None
    variant_label: str | None = None

    @model_validator(mode="after")
    def _validate_role_metadata(self) -> WorldObjectStatblockBindingV1:
        if self.role == "phase" and not (self.phase_key or "").strip():
            raise ValueError("phase_key is required when role is phase")
        if self.role != "phase" and self.phase_key is not None:
            raise ValueError("phase_key is only allowed when role is phase")
        return self


@dataclass(frozen=True)
class ExactSourceStatblockAttachment:
    """Normalized exact source attachment shared by legacy and generic schemas."""

    source_schema: Literal["legacy_threat", "world_object"]
    binding_id: str
    world_object_kind: WorldObjectStatblockKind
    provider: str
    statblock_id: str
    revision_id: str
    contract: str
    contract_version: str
    definition_digest: str
    role: StatblockBindingRole
    phase_key: str | None
    variant_label: str | None

    def semantic_key(self) -> tuple[Any, ...]:
        """Order-independent attachment semantics for duplicate detection."""
        return (
            self.statblock_id,
            self.revision_id,
            self.definition_digest,
            self.role,
            self.phase_key,
            self.variant_label,
        )


def external_statblock_node_id(statblock_id: str) -> str:
    ExternalResourceV1.model_validate(
        {
            "schema": EXTERNAL_RESOURCE_SCHEMA,
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": statblock_id,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        }
    )
    return f"{_EXTERNAL_NODE_PREFIX}{statblock_id}"


def compute_binding_id(
    *,
    threat_node_id: str,
    provider: str,
    statblock_id: str,
    revision_id: str,
    contract: str,
    contract_version: str,
    definition_digest: str,
    role: str,
    phase_key: str | None,
    variant_label: str | None,
) -> str:
    payload = {
        "threat_node_id": threat_node_id,
        "provider": provider,
        "statblock_id": statblock_id,
        "revision_id": revision_id,
        "contract": contract,
        "contract_version": contract_version,
        "definition_digest": definition_digest,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"threat-statblock-binding:{digest}"


def compute_world_object_statblock_binding_id(
    *,
    world_object_node_id: str,
    world_object_kind: str,
    provider: str,
    statblock_id: str,
    revision_id: str,
    contract: str,
    contract_version: str,
    definition_digest: str,
    role: str,
    phase_key: str | None,
    variant_label: str | None,
) -> str:
    payload = {
        "world_object_node_id": world_object_node_id,
        "world_object_kind": world_object_kind,
        "provider": provider,
        "statblock_id": statblock_id,
        "revision_id": revision_id,
        "contract": contract,
        "contract_version": contract_version,
        "definition_digest": definition_digest,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"world-object-statblock-binding:{digest}"


def edge_id_from_binding_id(binding_id: str) -> str:
    return f"edge:{binding_id}"


def reject_mechanics_keys(value: Mapping[str, Any], *, context: str) -> None:
    forbidden: set[str] = set()

    def collect(candidate: Any) -> None:
        if isinstance(candidate, Mapping):
            forbidden.update(FORBIDDEN_MECHANICS_KEYS.intersection(candidate))
            for nested in candidate.values():
                collect(nested)
        elif isinstance(candidate, list):
            for nested in candidate:
                collect(nested)

    collect(value)
    if forbidden:
        raise ValueError(
            f"{context} must not contain mechanics fields: {sorted(forbidden)}"
        )


def _reject_mechanics_keys(value: Mapping[str, Any], *, context: str) -> None:
    reject_mechanics_keys(value, context=context)


def _reject_unsupported_value_fields(
    value: Mapping[str, Any],
    *,
    allowed: set[str],
    context: str,
) -> None:
    _reject_mechanics_keys(value, context=context)
    unsupported = sorted(set(value) - allowed - _PROVENANCE_VALUE_KEYS)
    if unsupported:
        raise ValueError(f"{context} has unsupported value fields: {unsupported}")


def normalize_legacy_threat_binding(
    binding: ThreatStatblockBindingV1,
) -> ExactSourceStatblockAttachment:
    return ExactSourceStatblockAttachment(
        source_schema="legacy_threat",
        binding_id=binding.binding_id,
        world_object_kind="threat",
        provider=binding.provider,
        statblock_id=binding.statblock_id,
        revision_id=binding.revision_id,
        contract=binding.contract,
        contract_version=binding.contract_version,
        definition_digest=binding.definition_digest,
        role=binding.role,
        phase_key=binding.phase_key,
        variant_label=binding.variant_label,
    )


def normalize_world_object_binding(
    binding: WorldObjectStatblockBindingV1,
) -> ExactSourceStatblockAttachment:
    return ExactSourceStatblockAttachment(
        source_schema="world_object",
        binding_id=binding.binding_id,
        world_object_kind=binding.world_object_kind,
        provider=binding.provider,
        statblock_id=binding.statblock_id,
        revision_id=binding.revision_id,
        contract=binding.contract,
        contract_version=binding.contract_version,
        definition_digest=binding.definition_digest,
        role=binding.role,
        phase_key=binding.phase_key,
        variant_label=binding.variant_label,
    )


def parse_external_resource_assertion(
    *,
    subject_node_id: str | None,
    value: Mapping[str, Any],
) -> ExternalResourceV1 | None:
    if value.get("kind") != "external_resource":
        return None
    _reject_unsupported_value_fields(
        value,
        allowed={"kind", "role", "external_resource"},
        context="external resource assertion",
    )
    if value.get("role") != "statblock":
        raise ValueError("external resource assertion role must be statblock")
    resource = ExternalResourceV1.model_validate(value.get("external_resource"))
    expected = external_statblock_node_id(resource.resource_id)
    if subject_node_id != expected:
        raise ValueError(
            "external resource subject_node_id must match its provider/resource id"
        )
    return resource


def _validate_legacy_threat_binding_identity(
    *,
    subject_node_id: str,
    target_node_id: str | None,
    edge_id: Any,
    binding: ThreatStatblockBindingV1,
) -> None:
    expected_target = external_statblock_node_id(binding.statblock_id)
    if target_node_id != expected_target:
        raise ValueError("statblock binding target does not match binding statblock_id")
    expected_binding_id = compute_binding_id(
        threat_node_id=subject_node_id,
        provider=binding.provider,
        statblock_id=binding.statblock_id,
        revision_id=binding.revision_id,
        contract=binding.contract,
        contract_version=binding.contract_version,
        definition_digest=binding.definition_digest,
        role=binding.role,
        phase_key=binding.phase_key,
        variant_label=binding.variant_label,
    )
    if binding.binding_id != expected_binding_id:
        raise ValueError("statblock binding_id does not match immutable semantic identity")
    if edge_id != edge_id_from_binding_id(binding.binding_id):
        raise ValueError("statblock edge_id does not match deterministic binding_id")


def _validate_world_object_binding_identity(
    *,
    subject_node_id: str,
    target_node_id: str | None,
    edge_id: Any,
    binding: WorldObjectStatblockBindingV1,
) -> None:
    if binding.world_object_kind not in MECHANICS_ELIGIBLE_WORLD_OBJECT_KINDS:
        raise ValueError(
            "world_object_kind must be threat or npc for generic statblock bindings"
        )
    expected_target = external_statblock_node_id(binding.statblock_id)
    if target_node_id != expected_target:
        raise ValueError("statblock binding target does not match binding statblock_id")
    expected_binding_id = compute_world_object_statblock_binding_id(
        world_object_node_id=subject_node_id,
        world_object_kind=binding.world_object_kind,
        provider=binding.provider,
        statblock_id=binding.statblock_id,
        revision_id=binding.revision_id,
        contract=binding.contract,
        contract_version=binding.contract_version,
        definition_digest=binding.definition_digest,
        role=binding.role,
        phase_key=binding.phase_key,
        variant_label=binding.variant_label,
    )
    if binding.binding_id != expected_binding_id:
        raise ValueError("statblock binding_id does not match immutable semantic identity")
    if edge_id != edge_id_from_binding_id(binding.binding_id):
        raise ValueError("statblock edge_id does not match deterministic binding_id")


def parse_uses_statblock_binding_assertion(
    *,
    subject_node_id: str | None,
    target_node_id: str | None,
    predicate: str | None,
    value: Mapping[str, Any],
) -> tuple[ThreatStatblockBindingV1 | None, WorldObjectStatblockBindingV1 | None]:
    """Parse exactly one recognized uses_statblock binding payload.

    Returns ``(legacy, generic)`` where exactly one is set for a valid
    ``uses_statblock`` edge. Returns ``(None, None)`` when the assertion is not a
    uses_statblock / typed-binding edge.
    """
    raw_legacy = value.get("threat_statblock_binding")
    raw_generic = value.get("statblock_binding")
    has_legacy = raw_legacy is not None
    has_generic = raw_generic is not None
    is_uses = predicate == "uses_statblock"

    if not is_uses and not has_legacy and not has_generic:
        return None, None

    _reject_unsupported_value_fields(
        value,
        allowed=set(_USES_STATBLOCK_VALUE_KEYS),
        context="statblock binding assertion",
    )

    if has_legacy and has_generic:
        raise ValueError(
            "uses_statblock edge must not carry both threat_statblock_binding "
            "and statblock_binding"
        )

    if not is_uses:
        raise ValueError("typed statblock binding requires uses_statblock predicate")

    if value.get("direction") != "outbound":
        raise ValueError("statblock binding direction must be outbound")
    if not subject_node_id:
        raise ValueError("statblock binding requires a source world-object node id")

    if not has_legacy and not has_generic:
        raise ValueError(
            "uses_statblock requires exactly one of threat_statblock_binding "
            "or statblock_binding"
        )

    if has_legacy:
        binding = ThreatStatblockBindingV1.model_validate(raw_legacy)
        _validate_legacy_threat_binding_identity(
            subject_node_id=subject_node_id,
            target_node_id=target_node_id,
            edge_id=value.get("edge_id"),
            binding=binding,
        )
        return binding, None

    binding = WorldObjectStatblockBindingV1.model_validate(raw_generic)
    _validate_world_object_binding_identity(
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        edge_id=value.get("edge_id"),
        binding=binding,
    )
    return None, binding


def parse_threat_statblock_binding_assertion(
    *,
    subject_node_id: str | None,
    target_node_id: str | None,
    predicate: str | None,
    value: Mapping[str, Any],
) -> ThreatStatblockBindingV1 | None:
    """Parse a historical Threat binding, or None when the edge uses the generic form.

    Compatibility wrapper over ``parse_uses_statblock_binding_assertion``.
    """
    legacy, _generic = parse_uses_statblock_binding_assertion(
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        value=value,
    )
    return legacy


def parse_world_object_statblock_binding_assertion(
    *,
    subject_node_id: str | None,
    target_node_id: str | None,
    predicate: str | None,
    value: Mapping[str, Any],
) -> WorldObjectStatblockBindingV1 | None:
    """Parse a generic world-object binding, or None when the edge uses legacy Threat form."""
    _legacy, generic = parse_uses_statblock_binding_assertion(
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        value=value,
    )
    return generic
