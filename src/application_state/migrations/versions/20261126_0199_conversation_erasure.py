"""Erase chat-owned records while retaining independently committed World work."""

from alembic import op

revision = "20261126_0199"
down_revision = "20261126_0198"
branch_labels = None
depends_on = None

_TURN_CHILDREN = (
    "conversation_variant_save",
    "conversation_variant_review",
    "conversation_draft_revision",
    "lore_page_save_review",
    "lore_page_confirmation",
    "turn_context_trace",
    "turn_reviewed_action",
    "turn_rules_execution",
)

_CONVERSATION_CHILDREN = (
    "build_graph_reference_review",
    "build_image_move_review",
    "build_proposal",
    "composer_draft",
    "conversation_name",
    "work_plan",
    "turn",
)


def upgrade() -> None:
    op.execute("""
        CREATE TABLE agent.conversation_erasure_file (
            conversation_id uuid NOT NULL REFERENCES agent.conversation_identity(conversation_id),
            evidence_id uuid NOT NULL,
            kind text NOT NULL CHECK (kind IN ('prompt', 'failure')),
            retry_after timestamptz NOT NULL DEFAULT '-infinity',
            PRIMARY KEY (conversation_id, kind, evidence_id)
        );
        CREATE FUNCTION agent.lock_conversation_erasure_files(target_conversation uuid)
        RETURNS TABLE (conversation_id uuid, kind text, evidence_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS $$
            SELECT item.conversation_id, item.kind, item.evidence_id
            FROM agent.conversation_erasure_file AS item
            WHERE (target_conversation IS NULL AND item.retry_after <= clock_timestamp())
               OR item.conversation_id = target_conversation
            ORDER BY item.conversation_id, item.kind, item.evidence_id
            LIMIT 64 FOR UPDATE SKIP LOCKED
        $$;
        REVOKE EXECUTE ON FUNCTION agent.lock_conversation_erasure_files(uuid) FROM PUBLIC;

        DO $$
        BEGIN
            -- Hosted migrations and the hosted app use separate DB roles.
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'dmb_app_runtime') THEN
                GRANT SELECT, DELETE ON agent.conversation_erasure_file TO dmb_app_runtime;
                GRANT UPDATE (retry_after) ON agent.conversation_erasure_file TO dmb_app_runtime;
                GRANT EXECUTE ON FUNCTION agent.lock_conversation_erasure_files(uuid)
                    TO dmb_app_runtime;
            END IF;
        END;
        $$;
    """)
    # Removing a turn removes its retry edges. Direct edits or deletes of a live
    # edge remain prohibited, including on a trashed conversation.
    for turn in ("predecessor_id", "successor_id", "root_id"):
        key = f"turn_retry_{turn}_world_id_conversation_id_fkey"
        op.execute(f"""
            ALTER TABLE agent.turn_retry
                DROP CONSTRAINT {key},
                ADD CONSTRAINT {key} FOREIGN KEY ({turn}, world_id, conversation_id)
                REFERENCES agent.turn (turn_id, world_id, conversation_id) ON DELETE CASCADE
        """)
    op.execute("""
        CREATE FUNCTION agent.guard_turn_retry_erasure() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM agent.conversation
                WHERE world_id = OLD.world_id AND conversation_id = OLD.conversation_id
                      AND status = 'trashed')
                OR (SELECT count(*) FROM agent.turn
                    WHERE turn_id IN (OLD.predecessor_id, OLD.successor_id, OLD.root_id))
                    = (CASE WHEN OLD.predecessor_id = OLD.root_id THEN 2 ELSE 3 END)
            THEN
                RAISE EXCEPTION 'Retry lineage is immutable';
            END IF;
            RETURN OLD;
        END;
        $$;
        DROP TRIGGER immutable_turn_retry ON agent.turn_retry;
        CREATE TRIGGER immutable_turn_retry BEFORE INSERT OR UPDATE ON agent.turn_retry
            FOR EACH ROW EXECUTE FUNCTION agent.validate_turn_retry();
        CREATE TRIGGER turn_retry_delete_only_with_turn BEFORE DELETE ON agent.turn_retry
            FOR EACH ROW EXECUTE FUNCTION agent.guard_turn_retry_erasure();
    """)

    turn_deletes = "\n".join(f"DELETE FROM agent.{table} WHERE turn_id = ANY(turns);"
                             for table in _TURN_CHILDREN)
    conversation_deletes = "\n".join(
        f"DELETE FROM agent.{table} WHERE world_id = OLD.world_id AND conversation_id = OLD.conversation_id;"
        for table in _CONVERSATION_CHILDREN
    )
    # The trigger owns the restricted child deletes. It cannot be invoked as a
    # function, accepts no caller arguments, and acts on one verified parent row.
    op.execute(f"""
        CREATE FUNCTION agent.erase_trashed_conversation() RETURNS trigger
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $erase$
        DECLARE
            turns uuid[];
            actions uuid[];
        BEGIN
            SELECT ARRAY(SELECT turn_id FROM agent.turn
                WHERE world_id = OLD.world_id AND conversation_id = OLD.conversation_id
                ORDER BY turn_id FOR UPDATE) INTO turns;
            SELECT ARRAY(SELECT action_id FROM plan_action.action
                WHERE world_id = OLD.world_id AND (
                    authoring_origin->>'conversation_id' = OLD.conversation_id::text
                    OR consultation #>> '{{receipt,origin_conversation_id}}' = OLD.conversation_id::text
                ) ORDER BY action_id FOR UPDATE) INTO actions;

            IF EXISTS (SELECT 1 FROM agent.turn WHERE turn_id = ANY(turns)
                         AND (status = 'accepted' OR
                              (status = 'running' AND claim_expires_at > clock_timestamp())))
               OR EXISTS (SELECT 1 FROM plan_action.action WHERE action_id = ANY(actions)
                         AND status = 'pending' AND lease_expires_at > clock_timestamp())
               OR EXISTS (SELECT 1 FROM agent.build_proposal WHERE world_id = OLD.world_id
                         AND conversation_id = OLD.conversation_id
                         AND payload->>'state' IN ('reserved', 'authorized', 'sdk_entered', 'response_received')
                         AND (payload->>'claim_expires_at')::timestamptz > clock_timestamp())
               OR EXISTS (SELECT 1 FROM agent.conversation_variant_save WHERE turn_id = ANY(turns)
                         AND receipt IS NULL)
               OR EXISTS (SELECT 1 FROM agent.conversation_variant_portrait AS portrait
                         JOIN agent.conversation_variant_review AS review USING (review_id)
                         WHERE review.turn_id = ANY(turns)
                           AND portrait.receipt IS NULL AND portrait.refusal IS NULL)
               OR EXISTS (SELECT 1 FROM agent.build_graph_reference_review WHERE world_id = OLD.world_id
                         AND conversation_id = OLD.conversation_id AND payload->>'state' = 'applying')
               OR EXISTS (SELECT 1 FROM agent.build_image_move_review WHERE world_id = OLD.world_id
                         AND conversation_id = OLD.conversation_id AND payload->>'state' = 'claimed')
            THEN
                RAISE check_violation USING CONSTRAINT = 'conversation_erasure_in_flight',
                    MESSAGE = 'The conversation has a reply or save still in progress';
            END IF;

            -- Retire diagnostic file handles before ripping out their owners.
            INSERT INTO agent.conversation_erasure_file (conversation_id, evidence_id, kind)
            SELECT OLD.conversation_id, (event->>'evidence_id')::uuid, 'prompt'
              FROM agent.turn_context_trace AS trace
              CROSS JOIN LATERAL jsonb_array_elements(trace.payload->'observations') AS event
              WHERE trace.turn_id = ANY(turns) AND event->>'kind' = 'prompt_reference'
            UNION ALL
            SELECT OLD.conversation_id, (event->>'diagnostic_id')::uuid, 'failure'
              FROM agent.turn_context_trace AS trace
              CROSS JOIN LATERAL jsonb_array_elements(trace.payload->'observations') AS event
              WHERE trace.turn_id = ANY(turns) AND event->>'kind' = 'failure'
                AND event->>'diagnostic_id' IS NOT NULL
            UNION ALL
            SELECT OLD.conversation_id, (payload #>> '{{authorization,evidence_id}}')::uuid, 'prompt'
              FROM agent.build_proposal
              WHERE world_id = OLD.world_id AND conversation_id = OLD.conversation_id
                AND payload #>> '{{authorization,evidence_id}}' IS NOT NULL
            UNION ALL
            SELECT OLD.conversation_id, (reference->>'evidence_id')::uuid, 'prompt'
              FROM plan_action.action AS action
              CROSS JOIN LATERAL jsonb_array_elements(action.consultation->'prompt_references') AS reference
              WHERE action_id = ANY(actions)
            ON CONFLICT DO NOTHING;

            DELETE FROM agent.conversation_variant_portrait
                WHERE review_id IN (SELECT review_id FROM agent.conversation_variant_review
                                    WHERE turn_id = ANY(turns));
            {turn_deletes}

            DELETE FROM agent.build_proposal_review
                WHERE world_id = OLD.world_id AND action_id IN (
                    SELECT action_id FROM agent.build_proposal
                    WHERE world_id = OLD.world_id AND conversation_id = OLD.conversation_id
                );
            DELETE FROM plan_action.action WHERE action_id = ANY(actions);
            {conversation_deletes}
            RETURN OLD;
        END;
        $erase$;
        REVOKE EXECUTE ON FUNCTION agent.erase_trashed_conversation() FROM PUBLIC;
        CREATE TRIGGER erase_trashed_conversation BEFORE DELETE ON agent.conversation
            FOR EACH ROW WHEN (OLD.status = 'trashed' AND OLD.world_id NOT LIKE 'guest-%')
            EXECUTE FUNCTION agent.erase_trashed_conversation();
    """)


def downgrade() -> None:
    raise RuntimeError("Use forward recovery. Erased conversations cannot be reconstructed.")
