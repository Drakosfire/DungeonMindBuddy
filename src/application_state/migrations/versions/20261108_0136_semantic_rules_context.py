"""Admit sealed Rules map commitments and fence obsolete semantic readers."""
from alembic import op

revision = '20261108_0136'
down_revision = '20261108_0135'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE agent.turn_rules_execution DROP CONSTRAINT rules_execution_accepted_binding_check")
    op.execute("""ALTER TABLE agent.turn_rules_execution
        ADD CONSTRAINT rules_execution_accepted_binding_check CHECK (
          (accepted_binding IS NULL AND accepted_binding_sha256 IS NULL
            AND payload->>'state' <> 'accepted')
          OR COALESCE(
            jsonb_typeof(accepted_binding) = 'object'
            AND (accepted_binding->>'schema' = 'dmb_rules_accepted_binding_v1'
              OR (accepted_binding->>'schema' = 'dmb_rules_accepted_binding_v2'
                AND jsonb_typeof(accepted_binding->'producing_support_refs_sha256') = 'string'
                AND accepted_binding->>'producing_support_refs_sha256' ~ '^[a-f0-9]{64}$'))
            AND accepted_binding->>'turn_id' = turn_id::text
            AND accepted_binding->>'product_attempt' = product_attempt::text
            AND payload->>'state' = 'accepted'
            AND accepted_binding_sha256 ~ '^[a-f0-9]{64}$'
            AND octet_length(accepted_binding::text) <= 40960, FALSE))""")


def downgrade():
    raise RuntimeError('Older readers cannot reconstruct semantic Rules bindings')
