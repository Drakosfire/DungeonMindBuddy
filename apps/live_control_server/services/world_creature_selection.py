"""Creature selection over Core-admitted native records, never a classic projection.

Callers are the existing GM-authorized mechanics/encounter boundaries. This view
owns consumer eligibility and selection equality; Core owns evidence admission.
"""

from dataclasses import dataclass

from dungeonmind.application.vnext import EntityReadService
from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS
from dungeonmind.domain.errors import DungeonMindError
from psycopg import Error as DatabaseError
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateUnavailableError,
)
from application_state.world_mechanics.types import WorldMechanicsTarget
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)


# Current published recap actors and authored NPC declarations. These are
# consumer eligibility terms, not a second source-admission vocabulary.
_ACTOR_KINDS = {
    "dungeonbuddy:creature": "creature",
    "dungeonbuddy:character": "character",
    "dnd5e:npc": "npc",
}


@dataclass(frozen=True)
class CreatureCatalog:
    managed_world_id: str
    native_world_id: str
    binding_version: int
    revision_id: str
    head_revision_id: str
    targets: tuple[WorldMechanicsTarget, ...]
    completeness: str

    def response(self):
        return dict(
            schema="dmb_native_world_creatures_v1",
            managed_world_id=self.managed_world_id,
            native_world_id=self.native_world_id,
            binding_version=self.binding_version,
            revision_id=self.revision_id,
            completeness=self.completeness,
            targets=[target.model_dump(mode="json") for target in self.targets],
        )


def catalog(world_id, *, revision_id=None):
    try:
        bound = native.binding(world_id)
        repo = native.read_repository()
        head = repo.get_head(bound["native_world_id"])
        if head is None:
            raise ApplicationStateUnavailableError("Native World has no published head")
        revision = revision_id or head.head_revision_id
        read, access, _, _ = native.read_context(
            repo, bound["native_world_id"], revision, None, "gm", scope_mode="world"
        )
        listing = EntityReadService().list_entities(read)
        names, actors, campaigns = {}, {}, {}
        # Do not admit records or aliases here. Only Core's admitted IDs from the
        # same read context can contribute the classification/name witness.
        for identity in listing.admitted_assertion_ids:
            assertion = access.parsed.get_assertion(identity)
            value = assertion.value
            if (
                assertion.predicate == "dnd5e:classification"
                and value.kind == "term_ref"
                and value.term in _ACTOR_KINDS
            ):
                actors.setdefault(assertion.subject_entity_id, set()).add(value.term)
                scopes = {
                    item.value
                    for item in assertion.metadata.scope
                    if item.axis == CAMPAIGN_SCOPE_AXIS
                }
                campaigns.setdefault(assertion.subject_entity_id, set()).update(
                    scopes or {None}
                )
            elif (
                assertion.predicate == "dnd5e:name"
                and value.kind == "literal"
                and isinstance(value.value, str)
                and value.value.strip()
            ):
                names.setdefault(assertion.subject_entity_id, set()).add(value.value)
        targets = tuple(
            WorldMechanicsTarget(
                managed_world_id=world_id,
                native_world_id=bound["native_world_id"],
                binding_version=bound["binding_version"],
                graph_revision_id=revision,
                node_id=entity.entity_id,
                label=" / ".join(sorted(names.get(entity.entity_id, ())))
                or entity.entity_id,
                kind=next(
                    _ACTOR_KINDS[term]
                    for term in _ACTOR_KINDS
                    if term in actors[entity.entity_id]
                ),
                role="",
                campaign_scope=next(iter(campaigns[entity.entity_id]))
                if len(campaigns[entity.entity_id]) == 1
                else None,
            )
            for entity in listing.entities
            if entity.entity_id in actors
        )
        view = CreatureCatalog(
            world_id,
            bound["native_world_id"],
            bound["binding_version"],
            revision,
            head.head_revision_id,
            targets,
            listing.completeness.status,
        )
        require_binding(view)
        return view
    except (DungeonMindError, DatabaseError, ValueError) as exc:
        raise ApplicationStateUnavailableError(
            "Native creature contents are unavailable"
        ) from exc


def require_binding(view):
    bound = native.binding(view.managed_world_id)
    if (bound["native_world_id"], bound["binding_version"]) != (
        view.native_world_id,
        view.binding_version,
    ):
        raise ApplicationStateConflictError(
            "World mapping changed; load creatures and confirm again"
        )


def require_target(target, view, *, head=False):
    if (
        (
            target.managed_world_id,
            target.native_world_id,
            target.binding_version,
            target.graph_revision_id,
        )
        != (
            view.managed_world_id,
            view.native_world_id,
            view.binding_version,
            view.revision_id,
        )
        or head
        and view.revision_id != view.head_revision_id
    ):
        raise ApplicationStateConflictError(
            "World contents changed; load creatures and confirm again"
        )
    actual = next(
        (item for item in view.targets if item.node_id == target.node_id), None
    )
    if (
        actual is None
        or actual.kind not in _ACTOR_KINDS.values()
        or actual.model_dump() != target.model_dump()
    ):
        raise ApplicationStateConflictError(
            "Selected creature identity is not valid in this World"
        )
    require_binding(view)
    return actual
