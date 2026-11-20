"""Retain immutable extraction output bytes in their existing ingest owner."""
from alembic import op

revision = "20261030_0098"
down_revision = "20261030_0097"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE ingest.component_payload (
        run_id TEXT NOT NULL REFERENCES ingest.run(run_id),
        kind TEXT NOT NULL,
        content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
        payload BYTEA NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (run_id, kind, content_sha256),
        CHECK (kind IN ('source_span_index', 'candidate_graph', 'validation_report',
            'pass_outputs', 'pass_telemetry', 'consolidation_diagnostics',
            'raw_model_response', 'provenance_index'))
    )""")


def downgrade():
    raise RuntimeError("Extraction output persistence requires recovery forward")
