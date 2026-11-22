"""Persist ordered events separately while a readonly Plan session owns the turn."""

from alembic import op

revision = "20261122_0186"
down_revision = "20261122_0185"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent.plan_execution_checkpoint (
            turn_id uuid PRIMARY KEY REFERENCES agent.turn(turn_id) ON DELETE CASCADE,
            revision bigint NOT NULL CHECK (revision > 0),
            attempt integer NOT NULL CHECK (attempt > 0),
            base_count integer NOT NULL CHECK (base_count >= 0),
            event_count integer NOT NULL CHECK (event_count >= base_count)
        )
    """)
    op.execute("""
        CREATE TABLE agent.plan_execution_event (
            turn_id uuid NOT NULL REFERENCES agent.plan_execution_checkpoint(turn_id)
                ON DELETE CASCADE,
            sequence integer NOT NULL CHECK (sequence >= 0),
            payload jsonb NOT NULL CHECK (
                jsonb_typeof(payload) = 'object'
                AND (payload->'sequence' = to_jsonb(sequence)) IS TRUE
            ),
            PRIMARY KEY (turn_id, sequence)
        )
    """)

    op.execute("""
        CREATE FUNCTION agent.reconstruct_plan_execution(
            requested_turn uuid,
            requested_revision bigint,
            requested_attempt integer,
            base jsonb,
            provider_attempt text DEFAULT NULL
        ) RETURNS jsonb
        LANGUAGE plpgsql STABLE
        SET search_path = pg_catalog
        AS $$
        DECLARE
            checkpoint agent.plan_execution_checkpoint%ROWTYPE;
            suffix jsonb;
            selected_base jsonb;
            suffix_count bigint;
            first_sequence integer;
            last_sequence integer;
        BEGIN
            SELECT * INTO checkpoint FROM agent.plan_execution_checkpoint
            WHERE turn_id = requested_turn;
            IF NOT FOUND AND provider_attempt IS NULL THEN
                RETURN base;
            END IF;

            IF checkpoint.turn_id IS NOT NULL THEN
                IF (checkpoint.revision, checkpoint.attempt)
                        IS DISTINCT FROM (requested_revision, requested_attempt)
                   OR jsonb_typeof(base->'events') IS DISTINCT FROM 'array'
                   OR jsonb_array_length(base->'events') <> checkpoint.base_count THEN
                    RAISE EXCEPTION 'Plan execution checkpoint differs from its turn'
                        USING ERRCODE = '23514';
                END IF;
                SELECT count(*), min(sequence), max(sequence),
                       coalesce(jsonb_agg(payload ORDER BY sequence) FILTER (
                           WHERE provider_attempt IS NULL
                              OR payload->>'provider_attempt_id' = provider_attempt
                       ), '[]'::jsonb)
                INTO suffix_count, first_sequence, last_sequence, suffix
                FROM agent.plan_execution_event WHERE turn_id = requested_turn;
                IF suffix_count <> checkpoint.event_count - checkpoint.base_count
                   OR (suffix_count > 0 AND (first_sequence, last_sequence)
                       IS DISTINCT FROM (checkpoint.base_count, checkpoint.event_count - 1)) THEN
                    RAISE EXCEPTION 'Plan execution suffix is not contiguous'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            IF provider_attempt IS NULL THEN
                RETURN jsonb_set(base, '{events}', (base->'events') || suffix);
            END IF;
            IF jsonb_typeof(base->'events') IS DISTINCT FROM 'array' THEN
                RETURN base;
            END IF;
            SELECT coalesce(jsonb_agg(event ORDER BY ordinal), '[]'::jsonb)
            INTO selected_base
            FROM jsonb_array_elements(base->'events') WITH ORDINALITY AS item(event, ordinal)
            WHERE event->>'provider_attempt_id' = provider_attempt;
            RETURN jsonb_build_object('events', selected_base || coalesce(suffix, '[]'::jsonb));
        END;
        $$
    """)


def downgrade():
    raise RuntimeError(
        "Use forward recovery. An active Plan turn can have committed suffix events."
    )
