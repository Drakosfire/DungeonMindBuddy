"""Reserve disabled-by-default hosted World creation policy and receipts."""

from alembic import op

revision = "20261120_0170"
down_revision = "20261119_0169"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE workspace.hosted_world_creation_policy (
            singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
            enabled boolean NOT NULL DEFAULT false,
            owner_world_limit integer,
            global_world_limit integer,
            owner_rate_limit integer,
            global_rate_limit integer,
            rate_window_seconds integer,
            CHECK (NOT enabled OR COALESCE(
                owner_world_limit > 0 AND global_world_limit > 0
                AND owner_rate_limit > 0 AND global_rate_limit > 0
                AND rate_window_seconds BETWEEN 1 AND 86400, false))
        )
    """)
    op.execute("INSERT INTO workspace.hosted_world_creation_policy (singleton) VALUES (true)")
    op.execute("""
        CREATE TABLE workspace.hosted_world_admission (
            world_id text PRIMARY KEY REFERENCES workspace.managed_world(world_id) ON DELETE RESTRICT,
            creator_subject text NOT NULL CHECK (length(creator_subject) > 0),
            created_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz
        )
    """)
    op.execute("""
        CREATE TABLE workspace.hosted_world_creation_receipt (
            creator_subject text NOT NULL CHECK (length(creator_subject) > 0),
            request_key text NOT NULL CHECK (length(request_key) BETWEEN 1 AND 128),
            request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[a-f0-9]{64}$'),
            world_id text NOT NULL REFERENCES workspace.hosted_world_admission(world_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (creator_subject, request_key)
        )
    """)
    op.execute("""
        CREATE TABLE workspace.hosted_world_creation_attempt (
            attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            creator_subject text NOT NULL CHECK (length(creator_subject) > 0),
            attempted_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX hosted_world_creation_attempt_time_idx ON workspace.hosted_world_creation_attempt (attempted_at)")
    op.execute("CREATE INDEX hosted_world_creation_attempt_subject_time_idx ON workspace.hosted_world_creation_attempt (creator_subject, attempted_at)")


def downgrade():
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM workspace.hosted_world_admission)
                OR EXISTS (SELECT 1 FROM workspace.hosted_world_creation_receipt)
                OR EXISTS (SELECT 1 FROM workspace.hosted_world_creation_attempt)
                OR EXISTS (SELECT 1 FROM workspace.hosted_world_creation_policy WHERE enabled)
            THEN RAISE EXCEPTION 'Cannot discard hosted World admission or creation history'; END IF;
        END $$
    """)
    op.drop_table("hosted_world_creation_attempt", schema="workspace")
    op.drop_table("hosted_world_creation_receipt", schema="workspace")
    op.drop_table("hosted_world_admission", schema="workspace")
    op.drop_table("hosted_world_creation_policy", schema="workspace")
