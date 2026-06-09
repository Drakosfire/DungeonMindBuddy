from __future__ import annotations

from src.statblocks import lifecycle_commands as commands


def test_statblock_lifecycle_command_values() -> None:
    assert commands.STATBLOCK_GENERATOR_HEALTH == "statblock.generator.health"
    assert commands.STATBLOCK_DESCRIPTION_REQUEST == "statblock.description.request"
    assert commands.STATBLOCK_DESCRIPTION_APPROVE == "statblock.description.approve"
    assert commands.STATBLOCK_DRAFT_GENERATE == "statblock.draft.generate"
    assert commands.STATBLOCK_DRAFT_RENDER == "statblock.draft.render"
    assert commands.STATBLOCK_DRAFT_REVIEW == "statblock.draft.review"
    assert commands.STATBLOCK_DRAFT_STORE == "statblock.draft.store"
    assert (
        commands.STATBLOCK_CORPUS_PREVIEW_PROMOTE == "statblock.corpus.preview_promote"
    )
    assert (
        commands.STATBLOCK_CORPUS_CONFIRM_PROMOTE == "statblock.corpus.confirm_promote"
    )
    assert commands.STATBLOCK_CORPUS_INGEST == "statblock.corpus.ingest"
    assert commands.STATBLOCK_COMBAT_ADD == "statblock.combat.add"


def test_statblock_lifecycle_command_values_are_unique() -> None:
    assert len(commands.STATBLOCK_LIFECYCLE_COMMANDS) == len(
        set(commands.STATBLOCK_LIFECYCLE_COMMANDS)
    )
