"""Append-only Play receipts for entered physical table rolls."""
from alembic import op
revision = "20261022_0044"
down_revision = "20261022_0043"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE play.prepared_table_receipt (
      run_id UUID NOT NULL REFERENCES play.run(run_id),
      resulting_run_revision BIGINT NOT NULL CHECK (resulting_run_revision > 1),
      command_id UUID NOT NULL,
      request_sha256 TEXT NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
      payload JSONB NOT NULL,
      PRIMARY KEY (run_id, resulting_run_revision), UNIQUE (run_id, command_id)
    )""")
    op.execute("""CREATE FUNCTION play.reject_prepared_table_receipt_mutation() RETURNS trigger
      LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'prepared table receipts are append-only'; END $$""")
    op.execute("""CREATE TRIGGER prepared_table_receipt_immutable
      BEFORE UPDATE OR DELETE OR TRUNCATE ON play.prepared_table_receipt
      FOR EACH STATEMENT EXECUTE FUNCTION play.reject_prepared_table_receipt_mutation()""")


def downgrade():
    op.execute("LOCK TABLE play.prepared_table_receipt IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().exec_driver_sql("SELECT EXISTS(SELECT 1 FROM play.prepared_table_receipt)").scalar_one():
        raise RuntimeError("refusing to discard recorded table receipts")
    op.execute("DROP TABLE play.prepared_table_receipt")
    op.execute("DROP FUNCTION play.reject_prepared_table_receipt_mutation()")
