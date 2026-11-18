"""Preserve legacy selection and scope managed Play selections by World."""

from alembic import op

revision = "20261117_0161"
down_revision = "20261117_0160"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE play.active_run DROP CONSTRAINT active_run_scope_key_check")
    op.execute("""
        UPDATE play.active_run AS active
        SET scope_key = 'world:' || run.world_id
        FROM play.run AS run
        WHERE active.run_id = run.run_id AND run.world_id IS NOT NULL
    """)
    op.execute("""
        ALTER TABLE play.active_run ADD CONSTRAINT active_run_scope_key_check
        CHECK (scope_key = 'local' OR (scope_key LIKE 'world:%' AND length(scope_key) > 6))
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF (SELECT count(*) FROM play.active_run) > 1 THEN
                RAISE EXCEPTION 'Cannot downgrade multiple active Play selections to one slot';
            END IF;
        END $$
    """)
    op.execute("ALTER TABLE play.active_run DROP CONSTRAINT active_run_scope_key_check")
    op.execute("UPDATE play.active_run SET scope_key = 'local'")
    op.execute("""
        ALTER TABLE play.active_run ADD CONSTRAINT active_run_scope_key_check
        CHECK (scope_key = 'local')
    """)
