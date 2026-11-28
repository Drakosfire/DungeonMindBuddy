"""Accept typed image review completion on the deferred Build lifecycle."""

from importlib import import_module

from alembic import op

revision = "20261128_0203"
down_revision = "20261128_0202"
branch_labels = None
depends_on = None


def upgrade():
    pending = import_module(
        "application_state.migrations.versions.20261127_0201_pending_build_records"
    )
    image = import_module(
        "application_state.migrations.versions.20261122_0184_build_image_move_native_fence"
    )
    signature = pending._FUNCTION + "(" + ",".join(kind for _, kind in pending._ARGS) + ")"
    conn = op.get_bind()
    definition = conn.exec_driver_sql(
        "SELECT pg_get_functiondef(to_regprocedure(%s))", (signature,)
    ).scalar_one()
    if definition is None:
        raise RuntimeError("Expected deferred Build storage owner")
    conn.exec_driver_sql(image.extend_native_storage_shape(definition))


def downgrade():
    raise RuntimeError("Saved deferred image review requires a compatible forward reader")
