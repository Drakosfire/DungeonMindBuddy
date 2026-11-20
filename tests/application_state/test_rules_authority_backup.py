"""Current-head accepted-turn/Rules restoration closure, not all Agent coverage."""

from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
import os
import subprocess
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
import pytest

from application_state.authority import (
    compute_fingerprint,
    compare_fingerprints,
    verify_parity,
    database_has_app_state_schema,
    restore_authority,
)
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_passages import (
    RulesHistoricalPassageRequestV1,
)
from application_state.agent_conversation.rules_authority_store import (
    open_execution_locked,
)
from application_state.errors import ApplicationStateIntegrityError
from tests.application_state.conftest import (
    _create_database,
    _drop_database,
    _replace_database,
)
from tests.application_state.test_rules_authority_store import admitted
from tests.application_state.test_rules_authority_completion import (
    ready_rules,
    ready_build_mixed,
)


@contextmanager
def empty_target(source):
    name = "dungeonbuddy_app_state_test_" + uuid4().hex[:12]
    admin = _replace_database(source, "postgres")
    target = _replace_database(source, name)
    _create_database(admin, name)
    try:
        yield name, target
    finally:
        _drop_database(admin, name)


def test_real_dump_restore_preserves_mixed_base_rules_replay_and_exact_citation(
    application_state_dsn, monkeypatch
):
    service = AgentConversationService()
    build, result, _ = ready_build_mixed(application_state_dsn)
    completed = service.complete_mixed_turn(result)
    # Include multiple Rules attempt rows for one Turn to exercise full PK order.
    pending, scope = admitted()
    with psycopg.connect(application_state_dsn) as conn:
        open_execution_locked(conn, scope, expected_turn_revision=pending.revision)
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (pending.turn_id,),
        )
    claimed = service.claim_turn(
        pending.world_id,
        pending.conversation_id,
        pending.turn_id,
        expected_revision=pending.revision,
    ).turn
    _, second = ready_rules(application_state_dsn, claimed)
    service.complete_mixed_turn(second)
    expected = compute_fingerprint(application_state_dsn)
    assert expected == compute_fingerprint(application_state_dsn)
    domains = {item.name: item for item in expected.domains}
    assert (
        domains["agent.turn_rules_execution"].row_count == 3
        and domains["agent.turn"].row_count == 2
    )
    # Old sidecars do not silently acquire newly enumerated verification domains.
    old = replace(
        expected,
        domains=tuple(
            item for item in expected.domains if not item.name.startswith("agent.")
        ),
    )
    assert len(compare_fingerprints(old, expected)) == 4
    parsed = urlparse(application_state_dsn)
    assert parsed.hostname == "127.0.0.1" and parsed.port == 54329
    env = {**os.environ, "PGUSER": parsed.username, "PGPASSWORD": parsed.password}
    prefix = [
        "docker",
        "exec",
        "-i",
        "-e",
        "PGUSER",
        "-e",
        "PGPASSWORD",
        "dungeonbuddy-review-fixture-pg",
    ]
    dump = subprocess.run(
        prefix
        + ["pg_dump", "--format=custom", "--no-owner", "--dbname", parsed.path[1:]],
        env=env,
        capture_output=True,
        check=True,
    ).stdout
    assert dump.startswith(b"PGDMP")
    with empty_target(application_state_dsn) as (name, target):
        subprocess.run(
            prefix
            + [
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                name,
            ],
            input=dump,
            env=env,
            capture_output=True,
            check=True,
        )
        ready, mismatches, source_fp, restored_fp = verify_parity(
            source_dsn=application_state_dsn, target_dsn=target
        )
        assert (
            ready
            and not mismatches
            and source_fp.digest == restored_fp.digest == expected.digest
        )
        ref = completed.accepted_binding.support_table[0]
        selector = RulesHistoricalPassageRequestV1(
            world_id=build.world_id,
            conversation_id=build.conversation_id,
            turn_id=build.turn_id,
            attempt=build.attempt,
            support_id=ref.support_id,
            support_sha256=ref.support_sha256,
        )
        original_passage = service.inspect_rules_passage(selector)
        with monkeypatch.context() as patched:
            patched.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", target)
            restored = AgentConversationService()
            assert (
                restored.inspect_turn(world_id=build.world_id, turn_id=build.turn_id)
                == completed
            )
            assert restored.complete_mixed_turn(result) == completed
            assert restored.inspect_rules_passage(selector) == original_passage
        # Reinsert the two composite-key domains in reverse physical order.
        with psycopg.connect(target) as conn:
            for table, order in [
                ("turn_reference", "turn_id DESC,reference_role DESC,ordinal DESC"),
                ("turn_rules_execution", "turn_id DESC,product_attempt DESC"),
            ]:
                conn.execute(
                    sql.SQL(
                        "CREATE TEMP TABLE copy_rows AS SELECT * FROM agent.{}"
                    ).format(sql.Identifier(table))
                )
                conn.execute(
                    sql.SQL("DELETE FROM agent.{}").format(sql.Identifier(table))
                )
                conn.execute(
                    sql.SQL(
                        "INSERT INTO agent.{} SELECT * FROM copy_rows ORDER BY " + order
                    ).format(sql.Identifier(table))
                )
                conn.execute("DROP TABLE copy_rows")
        assert compute_fingerprint(target).digest == expected.digest
        with psycopg.connect(target) as conn:
            row = conn.execute(
                "SELECT revision,payload,accepted_binding,accepted_binding_sha256 FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",
                (build.turn_id, build.attempt),
            ).fetchone()
        for corruption, domain in [
            ("text", "agent.turn"),
            ("marker", "agent.turn"),
            ("binding", "agent.turn_rules_execution"),
            ("source", "agent.turn_rules_execution"),
            ("missing", "agent.turn_rules_execution"),
        ]:
            with psycopg.connect(target) as conn:
                if corruption == "text":
                    conn.execute(
                        "UPDATE agent.turn SET assistant_text=assistant_text||%s WHERE turn_id=%s",
                        (" altered", build.turn_id),
                    )
                elif corruption == "marker":
                    conn.execute(
                        "UPDATE agent.turn SET answer_composition_kind='base' WHERE turn_id=%s",
                        (build.turn_id,),
                    )
                elif corruption == "binding":
                    conn.execute(
                        "UPDATE agent.turn_rules_execution SET accepted_binding=jsonb_set(accepted_binding,'{support_table,0,source_label}',to_jsonb('changed'::text)) WHERE turn_id=%s",
                        (build.turn_id,),
                    )
                elif corruption == "source":
                    conn.execute(
                        "UPDATE agent.turn_rules_execution SET payload=jsonb_set(payload,%s,to_jsonb('changed'::text)) WHERE turn_id=%s",
                        (
                            [
                                "supports",
                                str(ref.support_id),
                                "support",
                                "excerpt_text",
                            ],
                            build.turn_id,
                        ),
                    )
                else:
                    conn.execute(
                        "DELETE FROM agent.turn_rules_execution WHERE turn_id=%s",
                        (build.turn_id,),
                    )
            changed = compute_fingerprint(target)
            assert changed.digest != expected.digest and any(
                domain in message for message in compare_fingerprints(expected, changed)
            )
            with psycopg.connect(target) as conn:
                conn.execute(
                    "UPDATE agent.turn SET assistant_text=%s,answer_composition_kind='rules_mixed_v1' WHERE turn_id=%s",
                    (completed.assistant_text, build.turn_id),
                )
                conn.execute(
                    "DELETE FROM agent.turn_rules_execution WHERE turn_id=%s",
                    (build.turn_id,),
                )
                conn.execute(
                    "INSERT INTO agent.turn_rules_execution(turn_id,product_attempt,revision,payload,accepted_binding,accepted_binding_sha256) VALUES(%s,%s,%s,%s,%s,%s)",
                    (
                        build.turn_id,
                        build.attempt,
                        row[0],
                        Jsonb(row[1]),
                        Jsonb(row[2]),
                        row[3],
                    ),
                )
            assert compute_fingerprint(target).digest == expected.digest


def test_agent_only_restore_target_is_refused_before_pg_restore(
    application_state_dsn, tmp_path
):
    expected = compute_fingerprint(application_state_dsn)
    data = b"guard probe, not an actual dump"
    backup = tmp_path / "guard.dump"
    backup.write_bytes(data)
    with empty_target(application_state_dsn) as (_, target):
        with psycopg.connect(target) as conn:
            conn.execute("CREATE SCHEMA agent")
        assert database_has_app_state_schema(target)
        with pytest.raises(
            ApplicationStateIntegrityError, match="already contains APP-STATE"
        ):
            restore_authority(
                target_dsn=target,
                backup_path=backup,
                source_dsn=application_state_dsn,
                expect_fingerprint=expected,
                expected_sha256=sha256(data).hexdigest(),
            )
