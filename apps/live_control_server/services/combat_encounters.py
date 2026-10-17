"""HTTP-boundary orchestration for durable World-owned Combat encounters."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from application_state.combat_encounters import service as encounter_state
from application_state.combat_encounters.types import (
    AddGeneratedStatblockRequest,
    AddGeneratedStatblockResponse,
    CombatEncounterDraft,
    CombatEncounterProvenance,
    CombatEncounterRecord,
    CombatEntity,
    CombatEntityProvenance,
    CombatGroup,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateValidationError,
)
from apps.live_control_server.config import repo_root, session_dir
from apps.live_control_server.services.statblock_view import (
    StatblockViewError,
    read_generated_statblock,
)


def list_world_combat_encounters(*, world_id: str) -> list[CombatEncounterRecord]:
    return encounter_state.list_encounters(world_id=world_id)


def create_world_combat_encounter(
    *, world_id: str, request: CreateCombatEncounterRequest
) -> CombatEncounterRecord:
    return encounter_state.create_encounter(world_id=world_id, request=request)


def get_world_combat_encounter(
    *, world_id: str, encounter_id: str
) -> CombatEncounterRecord:
    return encounter_state.get_encounter(world_id=world_id, encounter_id=encounter_id)


def save_world_combat_encounter(
    *, world_id: str, encounter_id: str, request: SaveCombatEncounterRequest
) -> CombatEncounterRecord:
    return encounter_state.save_encounter(
        world_id=world_id, encounter_id=encounter_id, request=request
    )


def add_generated_statblock_to_world_combat_encounter(
    *,
    world_id: str,
    encounter_id: str,
    artifact_id: str,
    request: AddGeneratedStatblockRequest,
) -> AddGeneratedStatblockResponse:
    encounter = get_world_combat_encounter(world_id=world_id, encounter_id=encounter_id)
    if encounter.revision != request.expected_revision:
        raise ApplicationStateConflictError(
            "Combat encounter changed since it was selected; reload before adding a statblock"
        )
    detail = read_generated_statblock(
        base=session_dir(), root=repo_root(), artifact_id=artifact_id
    )
    combat = detail.combat_defaults
    if combat is None:
        raise StatblockViewError("generated statblock combat_defaults are missing")
    base_name = next(
        (
            value.strip()
            for value in (request.name_override, combat.name, detail.title)
            if isinstance(value, str) and value.strip()
        ),
        "Generated Statblock",
    )
    hp = request.hp_override if request.hp_override is not None else combat.hit_points
    max_hp = request.max_hp_override if request.max_hp_override is not None else combat.hit_points
    retrieval = detail.retrieval
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    provenance = CombatEntityProvenance(
        source="generated_statblock_view",
        artifact_id=detail.artifact_id,
        draft_id=detail.draft_id,
        corpus_display_path=detail.corpus_display_path,
        corpus_file_fingerprint=detail.corpus_file_fingerprint,
        retrieval_status=str(retrieval.get("status") or "unknown"),
        retrieval_verified_at=(
            None if retrieval.get("verified_at") is None else str(retrieval.get("verified_at"))
        ),
        added_at=now,
    )
    added: list[CombatEntity] = []
    next_order = max((entity.order for entity in encounter.draft.entities), default=0) + 1
    for index in range(request.count):
        suffix = _copy_suffix(index)
        name = base_name if request.count == 1 else f"{base_name} {suffix}"
        added.append(
            CombatEntity(
                id=f"{_slug(name)}-{uuid.uuid4().hex[:8]}",
                name=name,
                team=request.team,
                order=next_order + index,
                init=request.initiative,
                ac=combat.armor_class,
                hp=hp,
                max_hp=max_hp,
                notes=request.notes
                if request.notes is not None
                else f"Added from generated Statblock View; review warnings: {len(detail.warnings)}.",
                tags=["generated_statblock", "corpus_backed", "statblock_view"],
                statblock_path=detail.corpus_display_path,
                statblock_artifact_id=detail.artifact_id,
                statblock_title=detail.title,
                corpus_fingerprint=detail.corpus_file_fingerprint,
                source="corpus",
                provenance=[provenance],
            )
        )
    entities = list(encounter.draft.entities)
    if request.insert_after_entity_id:
        after = next(
            (index for index, item in enumerate(entities) if item.id == request.insert_after_entity_id),
            None,
        )
        if after is None:
            raise ApplicationStateValidationError(
                "insert_after_entity_id must reference a combatant in this encounter"
            )
        entities[after + 1 : after + 1] = added
    else:
        entities.extend(added)
    entities = [item.model_copy(update={"order": index}) for index, item in enumerate(entities, 1)]
    groups = list(encounter.draft.groups)
    group_key = request.group_key or (
        f"generated-{_slug(detail.artifact_id)}-{uuid.uuid4().hex[:6]}"
        if request.count > 1
        else None
    )
    if group_key:
        groups.append(
            CombatGroup(
                group_key=group_key,
                label=base_name,
                statblock_path=detail.corpus_display_path,
                member_ids=[entity.id for entity in added],
                collapsed=False,
            )
        )
    draft = CombatEncounterDraft(
        **encounter.draft.model_dump(exclude={"entities", "groups", "provenance"}),
        entities=entities,
        groups=groups,
        provenance=[
            *encounter.draft.provenance,
            CombatEncounterProvenance(
                source="statblock_combat_add",
                artifact_id=detail.artifact_id,
                added_entity_ids=[entity.id for entity in added],
                added_at=now,
            ),
        ],
    )
    updated = save_world_combat_encounter(
        world_id=world_id,
        encounter_id=encounter_id,
        request=SaveCombatEncounterRequest(
            expected_revision=request.expected_revision,
            draft=draft,
        ),
    )
    updated_by_id = {entity.id: entity for entity in updated.draft.entities}
    return AddGeneratedStatblockResponse(
        added_entities=[updated_by_id[entity.id] for entity in added],
        encounter=updated,
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "combatant"


def _copy_suffix(index: int) -> str:
    chars: list[str] = []
    while True:
        chars.append(chr(ord("A") + index % 26))
        index = index // 26 - 1
        if index < 0:
            return "".join(reversed(chars))
