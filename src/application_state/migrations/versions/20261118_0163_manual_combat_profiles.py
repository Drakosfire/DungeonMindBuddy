"""Admit paired versioned manual Combat records without rewriting legacy data."""

from alembic import op

revision = "20261118_0163"
down_revision = "20261118_0162"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("encounter_ruleset_snapshot_check", "encounter", schema="combat")
    op.drop_constraint("encounter_draft_check", "encounter", schema="combat")
    op.create_check_constraint("encounter_ruleset_snapshot_check", "encounter", """
        jsonb_typeof(ruleset_snapshot) = 'object'
        AND (ruleset_snapshot->>'schema' IN ('dmb_combat_ruleset_v1', 'dmb_combat_profile_v2')) IS TRUE
        AND octet_length(ruleset_snapshot::text) <= 32768
    """, schema="combat")
    op.create_check_constraint("encounter_draft_check", "encounter", """
        jsonb_typeof(draft) = 'object'
        AND (draft->>'schema' IN ('dmb_combat_encounter_draft_v1', 'dmb_combat_encounter_draft_v2')) IS TRUE
        AND octet_length(draft::text) <= 1048576
    """, schema="combat")
    op.create_check_constraint("encounter_version_pair_check", "encounter", """
        ((ruleset_snapshot->>'schema' = 'dmb_combat_ruleset_v1' AND draft->>'schema' = 'dmb_combat_encounter_draft_v1')
        OR (ruleset_snapshot->>'schema' = 'dmb_combat_profile_v2' AND draft->>'schema' = 'dmb_combat_encounter_draft_v2')) IS TRUE
    """, schema="combat")


def downgrade():
    # Hold the refusal proof through constraint replacement; cancellation writers
    # need not insert an encounter and must not race this retained-history check.
    op.get_bind().exec_driver_sql("LOCK TABLE combat.encounter, combat.scene_template_version, combat.scene_template_cancellation, combat.run_scene_cancellation IN ACCESS EXCLUSIVE MODE")
    retained = op.get_bind().exec_driver_sql("""
        SELECT EXISTS(SELECT 1 FROM combat.encounter
            WHERE ruleset_snapshot->>'schema' = 'dmb_combat_profile_v2'
               OR draft->>'schema' = 'dmb_combat_encounter_draft_v2')
        OR EXISTS(SELECT 1 FROM combat.scene_template_version
            WHERE payload->'ruleset'->>'schema' = 'dmb_combat_profile_v2'
               OR payload->'ruleset'->>'schema_' = 'dmb_combat_profile_v2'
               OR payload->'draft'->>'schema' = 'dmb_combat_encounter_draft_v2'
               OR payload->'draft'->>'schema_' = 'dmb_combat_encounter_draft_v2')
        OR EXISTS(SELECT 1 FROM combat.scene_template_cancellation
            WHERE request->'encounter'->>'schema_version' = 'dmb_manual_combat_create_v2')
        OR EXISTS(SELECT 1 FROM combat.run_scene_cancellation
            WHERE request->'request'->>'schema_version' = 'dmb_scene_encounter_materialize_v2')
    """).scalar_one()
    if retained:
        raise RuntimeError("Cannot downgrade while manual Combat records or history exist")
    op.drop_constraint("encounter_version_pair_check", "encounter", schema="combat")
    op.drop_constraint("encounter_ruleset_snapshot_check", "encounter", schema="combat")
    op.drop_constraint("encounter_draft_check", "encounter", schema="combat")
    op.create_check_constraint("encounter_ruleset_snapshot_check", "encounter", """
        jsonb_typeof(ruleset_snapshot) = 'object'
        AND ruleset_snapshot->>'schema' = 'dmb_combat_ruleset_v1'
        AND octet_length(ruleset_snapshot::text) <= 32768
    """, schema="combat")
    op.create_check_constraint("encounter_draft_check", "encounter", """
        jsonb_typeof(draft) = 'object'
        AND draft->>'schema' = 'dmb_combat_encounter_draft_v1'
        AND octet_length(draft::text) <= 1048576
    """, schema="combat")
