"""Create durable World-owned Combat encounter records."""

from alembic import op

revision = "20261017_0031"
down_revision = "20261017_0030"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA combat")
    op.execute(
        """
        CREATE TABLE combat.encounter (
            encounter_id UUID PRIMARY KEY,
            world_id TEXT NOT NULL CHECK (world_id ~ '^[a-z][a-z0-9_-]{0,62}$'),
            campaign_id TEXT CHECK (campaign_id IS NULL OR (btrim(campaign_id) <> '' AND length(campaign_id) <= 128)),
            session_n INTEGER CHECK (session_n IS NULL OR session_n BETWEEN 1 AND 9999),
            revision INTEGER NOT NULL CHECK (revision > 0),
            ruleset_snapshot JSONB NOT NULL CHECK (
                jsonb_typeof(ruleset_snapshot) = 'object'
                AND ruleset_snapshot->>'schema' = 'dmb_combat_ruleset_v1'
                AND octet_length(ruleset_snapshot::text) <= 32768
            ),
            ruleset_digest TEXT NOT NULL CHECK (ruleset_digest ~ '^[a-f0-9]{64}$'),
            draft JSONB NOT NULL CHECK (
                jsonb_typeof(draft) = 'object'
                AND draft->>'schema' = 'dmb_combat_encounter_draft_v1'
                AND octet_length(draft::text) <= 1048576
            ),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            CHECK (session_n IS NULL OR campaign_id IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE INDEX combat_encounter_world_recent ON combat.encounter(world_id, updated_at DESC, encounter_id ASC)"
    )


def downgrade():
    if op.get_bind().exec_driver_sql(
        "SELECT EXISTS(SELECT 1 FROM combat.encounter)"
    ).scalar_one():
        raise RuntimeError("Cannot downgrade while durable Combat encounters exist")
    op.execute("DROP INDEX combat.combat_encounter_world_recent")
    op.execute("DROP TABLE combat.encounter")
    op.execute("DROP SCHEMA combat")
