"""Add immutable Run-local Markdown edition history; never copy Plan eagerly."""

from alembic import op

revision = "20261018_0035"
down_revision = "20261018_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE play.run_edition (
            run_id UUID PRIMARY KEY REFERENCES play.run(run_id),
            world_id TEXT NOT NULL CHECK (world_id <> '' AND world_id = btrim(world_id)),
            origin_artifact_id UUID NOT NULL,
            origin_revision_n INTEGER NOT NULL CHECK (origin_revision_n > 0),
            origin_work_revision_id UUID NOT NULL,
            origin_content_sha256 TEXT NOT NULL CHECK (origin_content_sha256 ~ '^[0-9a-f]{64}$'),
            grammar_version INTEGER NOT NULL CHECK (grammar_version = 2),
            structure_sha256 TEXT NOT NULL CHECK (structure_sha256 ~ '^[0-9a-f]{64}$'),
            head_revision INTEGER NOT NULL CHECK (head_revision > 0),
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE play.run_edition_revision (
            run_id UUID NOT NULL REFERENCES play.run_edition(run_id) DEFERRABLE INITIALLY DEFERRED,
            revision_n INTEGER NOT NULL CHECK (revision_n > 0),
            revision_id UUID NOT NULL UNIQUE,
            previous_revision INTEGER,
            markdown TEXT NOT NULL CHECK (octet_length(markdown) <= 1048576),
            content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
            committed_at TIMESTAMPTZ NOT NULL,
            command_id UUID NOT NULL,
            request_sha256 TEXT NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
            expected_revision INTEGER NOT NULL CHECK (expected_revision >= 0),
            expected_sha256 TEXT NOT NULL CHECK (expected_sha256 ~ '^[0-9a-f]{64}$'),
            observed_run_revision INTEGER NOT NULL CHECK (observed_run_revision > 0),
            PRIMARY KEY (run_id, revision_n),
            UNIQUE (run_id, command_id),
            CHECK (expected_revision = revision_n - 1),
            CHECK ((revision_n = 1 AND previous_revision IS NULL) OR
                   (revision_n > 1 AND previous_revision IS NOT NULL AND previous_revision = revision_n - 1)),
            FOREIGN KEY (run_id, previous_revision) REFERENCES play.run_edition_revision(run_id, revision_n)
                DEFERRABLE INITIALLY DEFERRED
        )
    """)
    op.execute("""ALTER TABLE play.run_edition ADD CONSTRAINT run_edition_head_fk
        FOREIGN KEY (run_id, head_revision) REFERENCES play.run_edition_revision(run_id, revision_n)
        DEFERRABLE INITIALLY DEFERRED""")


def downgrade() -> None:
    op.execute(
        "LOCK TABLE play.run_edition, play.run_edition_revision IN ACCESS EXCLUSIVE MODE"
    )
    if (
        op.get_bind()
        .exec_driver_sql("SELECT EXISTS (SELECT 1 FROM play.run_edition_revision)")
        .scalar_one()
    ):
        raise RuntimeError(
            "refusing to discard Run edition history and command receipts"
        )
    op.execute("ALTER TABLE play.run_edition DROP CONSTRAINT run_edition_head_fk")
    op.execute("DROP TABLE play.run_edition_revision")
    op.execute("DROP TABLE play.run_edition")
