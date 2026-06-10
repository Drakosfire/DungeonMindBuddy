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


def test_package_exports_agent_command_constants_and_status_types() -> None:
    import src.statblocks as statblocks

    assert statblocks.STATBLOCK_DRAFT_GENERATE == "statblock.draft.generate"
    assert "statblock.draft.render" in statblocks.STATBLOCK_LIFECYCLE_COMMANDS
    assert statblocks.StatblockLifecycleState is not None
    assert statblocks.StatblockReviewStatus is not None
    assert statblocks.StatblockStorageStatus is not None
    assert statblocks.StatblockCorpusStatus is not None
    assert statblocks.StatblockLifecycleService is not None
    assert statblocks.StatblockLifecycleCommandRequest is not None
    assert statblocks.StatblockLifecycleCommandResult is not None
    assert statblocks.CommandStatus is not None
