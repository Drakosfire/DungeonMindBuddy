"""Accept truthful Build source variants in the shared governed Graph ledger."""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0024"
down_revision = "20261013_0023"
branch_labels = None
depends_on = None

# Exact prior constraints; preserve existing Plan rows without rewriting them.
_PLAN_RECEIPT = "graph_context_receipt IS NULL OR (\n                submitted_intent_fingerprint_v2 IS NOT NULL\n                AND jsonb_typeof(graph_context_receipt) = 'object'\n                AND graph_context_receipt ?& ARRAY[\n                    'schema', 'receipt_serializer_version', 'context_receipt_sha256',\n                    'plan_context_policy', 'plan_basis', 'playable_target',\n                    'graph_authority', 'graph_packet', 'assembled_input',\n                    'evidence_mode', 'source_opened'\n                ]\n                AND graph_context_receipt->>'schema' = 'dmb_agent_plan_world_graph_context_receipt_v1'\n                AND graph_context_receipt->>'receipt_serializer_version' = 'canonical-json-utf8-v1'\n                AND graph_context_receipt->>'context_receipt_sha256' ~ '^[0-9a-f]{64}$'\n                AND graph_context_receipt->>'evidence_mode' = 'metadata_only'\n                AND graph_context_receipt->>'source_opened' = 'false'\n                AND jsonb_typeof(graph_context_receipt->'plan_basis') = 'object'\n                AND jsonb_typeof(graph_context_receipt->'graph_authority') = 'object'\n                AND jsonb_typeof(graph_context_receipt->'graph_packet') = 'object'\n                AND jsonb_typeof(graph_context_receipt->'assembled_input') = 'object'\n            )"
_PLAN_COMPLETION = '(\n            completion IS NULL OR (\n                graph_context_receipt IS NOT NULL\n                AND jsonb_typeof(completion) = \'object\'\n                AND completion ?& ARRAY[\n                    \'schema\', \'context_receipt_sha256\', \'answer_basis\',\n                    \'answer_context_status\', \'answer_segments\', \'citation_map\'\n                ]\n                AND completion->>\'schema\' = \'dmb_plan_world_graph_completion_v1\'\n                AND completion->>\'context_receipt_sha256\' =\n                    graph_context_receipt->>\'context_receipt_sha256\'\n                AND completion->>\'answer_context_status\' IN (\n                    \'graph_grounded\', \'graph_grounded_partial\',\n                    \'plan_only_insufficient_evidence\', \'plan_only_graph_unused\'\n                )\n                AND jsonb_typeof(completion->\'answer_segments\') = \'array\'\n                AND jsonb_array_length(completion->\'answer_segments\') > 0\n                AND (\n                    (completion->>\'answer_context_status\' IN (\n                        \'plan_only_insufficient_evidence\', \'plan_only_graph_unused\'\n                    )\n                        AND completion->>\'answer_basis\' = \'committed_plan\'\n                        AND jsonb_typeof(completion->\'citation_map\') = \'null\'\n                        AND NOT jsonb_path_exists(\n                            completion->\'answer_segments\',\n                            \'$[*] ? (@.kind == "graph_claim")\'\n                        ))\n                    OR\n                    (completion->>\'answer_context_status\' IN (\n                        \'graph_grounded\', \'graph_grounded_partial\'\n                    )\n                        AND completion->>\'answer_basis\' = \'committed_plan_plus_world_graph\'\n                        AND jsonb_typeof(completion->\'citation_map\') = \'object\'\n                        AND jsonb_typeof(completion->\'citation_map\'->\'entries\') = \'array\'\n                        AND jsonb_array_length(completion->\'citation_map\'->\'entries\') > 0\n                        AND jsonb_path_exists(\n                            completion->\'answer_segments\',\n                            \'$[*] ? (@.kind == "graph_claim")\'\n                        ))\n                )\n            )\n        ) OR ((completion IS NULL) OR (graph_context_receipt IS NOT NULL AND (\ncompletion IS NOT NULL\nAND graph_context_receipt IS NOT NULL\nAND jsonb_typeof(completion) = \'object\'\nAND completion ?& ARRAY[\'schema\',\'context_receipt_sha256\',\'answer_basis\',\'answer_context_status\',\'answer_segments\',\'citation_map\']\nAND completion->>\'schema\' = \'dmb_plan_world_graph_completion_v2\'\nAND completion->>\'context_receipt_sha256\' = graph_context_receipt->>\'context_receipt_sha256\'\nAND completion->>\'context_receipt_sha256\' ~ \'^[0-9a-f]{64}$\'\nAND completion->>\'answer_context_status\' IN (\'graph_grounded\',\'graph_grounded_partial\',\'plan_only_insufficient_evidence\',\'plan_only_graph_unused\')\nAND jsonb_typeof(completion->\'answer_segments\') = \'array\'\nAND jsonb_array_length(completion->\'answer_segments\') BETWEEN 1 AND 128\nAND octet_length(completion::text) <= 1048576\nAND (\n (completion->>\'answer_context_status\' IN (\'plan_only_insufficient_evidence\',\'plan_only_graph_unused\')\n  AND completion->>\'answer_basis\'=\'committed_plan\'\n  AND jsonb_typeof(completion->\'citation_map\')=\'null\'\n  AND NOT jsonb_path_exists(completion->\'answer_segments\',\'$[*] ? (@.kind == "graph_claim")\'))\n OR\n (completion->>\'answer_context_status\' IN (\'graph_grounded\',\'graph_grounded_partial\')\n  AND completion->>\'answer_basis\'=\'committed_plan_plus_world_graph\'\n  AND jsonb_typeof(completion->\'citation_map\')=\'object\'\n  AND completion->\'citation_map\'->>\'schema\'=\'dmb_graph_citation_map_v2\'\n  AND completion->\'citation_map\'->>\'context_receipt_sha256\'=completion->>\'context_receipt_sha256\'\n  AND jsonb_typeof(completion->\'citation_map\'->\'entries\')=\'array\'\n  AND jsonb_array_length(completion->\'citation_map\'->\'entries\')>0\n  AND jsonb_path_exists(completion->\'answer_segments\',\'$[*] ? (@.kind == "graph_claim")\'))\n)\n)))'

_BUILD_RECEIPT = """
    graph_context_receipt->>'schema' = 'dmb_build_graph_context_receipt_v1'
    AND submitted_intent_fingerprint_v2 IS NOT NULL
    AND surface_resolution = 'resolved' AND surface_id = 'build'
    AND graph_context_execution IS NOT NULL
    AND graph_context_execution->>'schema' IN ('dmb_agent_plan_world_graph_execution_v2', 'dmb_agent_plan_world_graph_execution_v3')
    AND graph_context_receipt ?& ARRAY['receipt_serializer_version', 'context_receipt_sha256',
        'source_basis', 'graph_authority', 'graph_packet', 'assembled_input', 'evidence_mode', 'source_opened']
    AND graph_context_receipt->>'receipt_serializer_version' = 'canonical-json-utf8-v1'
    AND graph_context_receipt->>'context_receipt_sha256' ~ '^[0-9a-f]{64}$'
    AND graph_context_receipt->>'evidence_mode' = 'metadata_only'
    AND graph_context_receipt->'source_opened' = 'false'::jsonb
    AND jsonb_typeof(graph_context_receipt->'source_basis') = 'object'
    AND graph_context_receipt->'source_basis' ?& ARRAY['world_id', 'document_id', 'registry_revision', 'content_sha256', 'visibility']
    AND graph_context_receipt->'source_basis'->>'world_id' = world_id
    AND length(graph_context_receipt->'source_basis'->>'document_id') BETWEEN 1 AND 256
    AND graph_context_receipt->'source_basis'->>'content_sha256' ~ '^[0-9a-f]{64}$'
    AND graph_context_receipt->'source_basis'->>'visibility' IN ('internal', 'player_safe')
    AND CASE WHEN jsonb_typeof(graph_context_receipt->'source_basis'->'registry_revision') = 'number'
        AND graph_context_receipt->'source_basis'->>'registry_revision' ~ '^[0-9]+$'
        THEN (graph_context_receipt->'source_basis'->>'registry_revision')::numeric >= 1 ELSE FALSE END
    AND NOT graph_context_receipt ?| ARRAY['plan_basis', 'plan_context_policy', 'playable_target']
    AND jsonb_typeof(graph_context_receipt->'graph_authority') = 'object'
    AND graph_context_receipt->'graph_authority'->>'managed_world_id' = world_id
    AND jsonb_typeof(graph_context_receipt->'graph_packet') = 'object'
    AND jsonb_typeof(graph_context_receipt->'assembled_input') = 'object'
"""
_BUILD_COMPLETION = """
    completion->>'schema' = 'dmb_build_graph_completion_v1'
    AND graph_context_receipt->>'schema' = 'dmb_build_graph_context_receipt_v1'
    AND completion ?& ARRAY['context_receipt_sha256', 'answer_basis', 'answer_context_status', 'answer_segments', 'citation_map']
    AND completion->>'context_receipt_sha256' = graph_context_receipt->>'context_receipt_sha256'
    AND jsonb_typeof(completion->'answer_segments') = 'array'
    AND CASE WHEN jsonb_typeof(completion->'answer_segments') = 'array'
        THEN jsonb_array_length(completion->'answer_segments') BETWEEN 1 AND 128 ELSE FALSE END
    AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (!exists(@.kind) || (@.kind != "saved_source_claim" && @.kind != "graph_claim" && @.kind != "connective"))')
    AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "saved_source_claim" && (!exists(@.content_sha256) || @.content_sha256 != $hash))', jsonb_build_object('hash', graph_context_receipt->'source_basis'->'content_sha256'))
    AND ((completion->>'answer_context_status' IN ('source_only_insufficient_evidence', 'source_only_graph_unused')
        AND completion->>'answer_basis' = 'saved_source'
        AND completion->'citation_map' = 'null'::jsonb
        AND NOT jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "graph_claim")'))
        OR (completion->>'answer_context_status' IN ('graph_grounded', 'graph_grounded_partial')
        AND completion->>'answer_basis' = 'saved_source_plus_world_graph'
        AND jsonb_typeof(completion->'citation_map') = 'object'
        AND completion->'citation_map'->>'context_receipt_sha256' = completion->>'context_receipt_sha256'
        AND jsonb_path_exists(completion, '$.answer_segments[*] ? (@.kind == "graph_claim")')))
"""


def _replace(name, expression):
    op.execute(f"ALTER TABLE agent.turn DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE agent.turn ADD CONSTRAINT {name} CHECK ({expression})")


def upgrade():
    _replace("agent_turn_graph_context_receipt_check", f"({_PLAN_RECEIPT}) OR COALESCE(({_BUILD_RECEIPT}), FALSE)")
    _replace("agent_turn_graph_completion_check", f"((completion IS NULL OR graph_context_receipt->>'schema' = 'dmb_agent_plan_world_graph_context_receipt_v1') AND ({_PLAN_COMPLETION})) OR COALESCE(({_BUILD_COMPLETION}), FALSE)")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM agent.turn WHERE graph_context_receipt->>'schema' = 'dmb_build_graph_context_receipt_v1')")).scalar():
        raise RuntimeError("Cannot downgrade while retained Build Graph receipts exist")
    _replace("agent_turn_graph_completion_check", _PLAN_COMPLETION)
    _replace("agent_turn_graph_context_receipt_check", _PLAN_RECEIPT)
