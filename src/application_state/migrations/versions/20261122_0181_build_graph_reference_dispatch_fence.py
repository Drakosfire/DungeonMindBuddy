"""Fence readers that cannot decode native Build Graph reference decisions."""

from importlib import import_module

from alembic import op

revision = "20261122_0181"
down_revision = "20261122_0180"
branch_labels = None
depends_on = None


def upgrade():
    # Extend the existing native lifecycle owner while retaining its common
    # receipt, execution, and row checks for every completion shape.
    owner = import_module("application_state.migrations.versions.20261109_0142_native_storage_json_owner")
    conn = op.get_bind()
    definition = conn.exec_driver_sql(
        f"SELECT pg_get_functiondef('{owner._SIGNATURE}'::regprocedure)"
    ).scalar_one()
    conn.exec_driver_sql(extend_native_storage_shape(definition))


def extend_native_storage_shape(definition: str) -> str:
    anchor = "ELSE CASE WHEN completion->>'schema'='dmb_build_authoring_completion_v1' THEN"
    lifecycle_anchor = "AND CASE WHEN status='completed' THEN"
    if definition.count(anchor) != 1 or definition.count(lifecycle_anchor) != 1:
        raise RuntimeError("Native Build turn storage predicate changed")
    binding = "jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == \"build_graph_reference_completion_binding_v1\")')"
    definition = definition.replace(lifecycle_anchor, f"""
AND ({binding} = COALESCE(completion->>'schema'='dmb_build_graph_reference_completion_v1', FALSE))
{lifecycle_anchor}""", 1)
    return definition.replace(anchor, f"""ELSE CASE WHEN completion->>'schema'='dmb_build_graph_reference_completion_v1' THEN
   surface_id='build' AND answer_composition_kind='base' AND btrim(assistant_text)<>''
   AND jsonb_typeof(completion)='object'
   AND completion ?& ARRAY['schema','context_receipt_sha256','disposition','action_id','placement_sha256']
   AND completion - ARRAY['schema','context_receipt_sha256','disposition','action_id','placement_sha256']='{{}}'::jsonb
   AND completion->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
   AND CASE WHEN completion->>'disposition'='ready' THEN
       completion->>'action_id' ~ '^[0-9a-f-]{{36}}$' AND completion->>'placement_sha256' ~ '^[a-f0-9]{{64}}$'
       ELSE completion->>'disposition' IN ('discussion','new_object','different_page','ambiguous_identity',
            'wrong_kind','missing_identity','ambiguous_boundary','missing_boundary','unresolved')
          AND completion->'action_id'='null'::jsonb AND completion->'placement_sha256'='null'::jsonb END
   AND graph_context_execution->'events'->-1->>'kind'='build_graph_reference_completion_binding_v1'
   AND NOT jsonb_path_exists(graph_context_execution,'$.events[*] ? (@.kind == "completion_binding")')
 WHEN completion->>'schema'='dmb_build_authoring_completion_v1' THEN""", 1)


def downgrade():
    raise RuntimeError("Use forward recovery. Older Build readers cannot decode native Graph reference decisions.")
