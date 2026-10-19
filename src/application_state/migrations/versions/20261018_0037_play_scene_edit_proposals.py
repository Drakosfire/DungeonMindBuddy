"""Persist inert, World and Run scoped Play scene edit proposals."""

from alembic import op

revision = "20261018_0037"
down_revision = "20261018_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE play.run_edition_revision ADD COLUMN expected_run_revision BIGINT CHECK (expected_run_revision IS NULL OR expected_run_revision > 0)")
    op.execute("ALTER TABLE play.run ADD CONSTRAINT play_run_id_world_unique UNIQUE (run_id, world_id)")
    op.execute("""
        CREATE TABLE play.scene_edit_proposal (
            world_id TEXT NOT NULL CHECK (world_id <> '' AND world_id = btrim(world_id)),
            run_id UUID NOT NULL,
            proposal_id UUID NOT NULL,
            request_sha256 TEXT NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
            request JSONB NOT NULL,
            context_receipt JSONB NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending','ready','failed')),
            result JSONB,
            failure_code TEXT,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (world_id, run_id, proposal_id),
            FOREIGN KEY (run_id, world_id) REFERENCES play.run(run_id, world_id),
            CHECK (octet_length(request::text) <= 262144),
            CHECK (octet_length(context_receipt::text) <= 262144),
            CHECK (result IS NULL OR octet_length(result::text) <= 1048576),
            CHECK (COALESCE(jsonb_typeof(request) = 'object' AND request->>'schema_version' = 'dmb_play_scene_edit_request_v1'
                AND request ?& ARRAY['schema_version','run_revision','content_basis','scene_id','instruction'], FALSE)),
            CHECK (COALESCE(jsonb_typeof(context_receipt) = 'object' AND context_receipt->>'schema' = 'dmb_play_run_turn_context_receipt_v2'
                AND context_receipt->>'world_id' = world_id AND context_receipt->>'run_id' = run_id::text
                AND context_receipt ?& ARRAY['run_revision','runbook_object_id','runbook_object_revision','runbook_work_revision_id','runbook_revision_n','runbook_content_sha256','beat_id','scene_id','marker_grammar_version','edition_revision','edition_revision_id','content_sha256','scene_note','scene_note_sha256'], FALSE)),
            CHECK (
                (status = 'pending' AND result IS NULL AND failure_code IS NULL)
                OR (status = 'ready' AND result IS NOT NULL AND failure_code IS NULL
                    AND COALESCE(jsonb_typeof(result) = 'object' AND result->>'schema_version' = 'dmb_play_scene_edit_result_v1'
                        AND result ?& ARRAY['schema_version','before_markdown','replacement_markdown','candidate_markdown','candidate_sha256','summary','assumptions','model','model_observed','model_latency_ms','wall_latency_ms'], FALSE))
                OR (status = 'failed' AND result IS NULL AND COALESCE(failure_code ~ '^[a-z][a-z0-9_]{0,63}$', FALSE))
            )
        )
    """)
    op.execute("""
        CREATE FUNCTION play.reject_terminal_scene_edit_proposal_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status <> 'pending' THEN
                RAISE EXCEPTION 'terminal Play scene edit proposals are immutable';
            END IF;
            IF NEW.status = 'pending'
               OR NEW.world_id IS DISTINCT FROM OLD.world_id
               OR NEW.run_id IS DISTINCT FROM OLD.run_id
               OR NEW.proposal_id IS DISTINCT FROM OLD.proposal_id
               OR NEW.request_sha256 IS DISTINCT FROM OLD.request_sha256
               OR NEW.request IS DISTINCT FROM OLD.request
               OR NEW.context_receipt IS DISTINCT FROM OLD.context_receipt
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'Play scene edit proposal reservation is immutable';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER scene_edit_proposal_terminal_immutable
        BEFORE UPDATE ON play.scene_edit_proposal
        FOR EACH ROW EXECUTE FUNCTION play.reject_terminal_scene_edit_proposal_update()
    """)
    op.execute("CREATE INDEX scene_edit_proposal_run_created ON play.scene_edit_proposal(world_id, run_id, created_at DESC, proposal_id DESC)")


def downgrade() -> None:
    op.execute("LOCK TABLE play.scene_edit_proposal, play.run_edition_revision IN ACCESS EXCLUSIVE MODE")
    if (op.get_bind().exec_driver_sql("SELECT EXISTS (SELECT 1 FROM play.scene_edit_proposal)").scalar_one()
            or op.get_bind().exec_driver_sql("SELECT EXISTS (SELECT 1 FROM play.run_edition_revision WHERE expected_run_revision IS NOT NULL)").scalar_one()):
        raise RuntimeError("refusing to discard Play scene edit proposal records or freshness guards")
    op.execute("DROP TABLE play.scene_edit_proposal")
    op.execute("DROP FUNCTION play.reject_terminal_scene_edit_proposal_update()")
    op.execute("ALTER TABLE play.run DROP CONSTRAINT play_run_id_world_unique")
    op.execute("ALTER TABLE play.run_edition_revision DROP COLUMN expected_run_revision")
