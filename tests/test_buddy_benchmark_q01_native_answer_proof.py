"""Provider-free guards for the selected-subject answer assessment."""

from copy import deepcopy
import json

import pytest
from evals.buddy_benchmark import q01_native_answer_proof as proof


@pytest.mark.parametrize(
    "field,value",
    [
        ("database", "primary"),
        ("database_oid", "1"),
        ("system_identifier", "other"),
        ("server_port", 54331),
    ],
)
def test_wrong_database_identity_refuses(field, value):
    identity = {
        "database": proof.fixture.APP_DATABASE,
        "database_oid": "148024",
        "system_identifier": proof.fixture.SYSTEM_ID,
        "server_address": "172.17.0.5/32",
        "server_port": 5432,
    }
    proof.validate_identity(identity)
    identity[field] = value
    with pytest.raises(ValueError):
        proof.validate_identity(identity)


@pytest.mark.parametrize("mutation", ["pointer", "old_identity", "status"])
def test_exact_prior_conversation_and_pointer(mutation):
    pointer = {
        "world_id": proof.fixture.WORLD,
        "active_conversation_id": proof.OLD_CONVERSATION,
        "pointer_revision": 72,
    }
    old = {
        "world_id": proof.fixture.WORLD,
        "conversation_id": proof.OLD_CONVERSATION,
        "status": "active",
    }
    proof.validate_pointer(pointer, old)
    if mutation == "pointer":
        pointer["pointer_revision"] = 73
    elif mutation == "old_identity":
        old["conversation_id"] = "another"
    else:
        old["status"] = "archived"
    with pytest.raises(ValueError):
        proof.validate_pointer(pointer, old)


def test_immutable_checkpoint_preserves_original(tmp_path):
    proof.immutable_save(tmp_path, "original", {"value": 1})
    proof.immutable_save(tmp_path, "original", {"value": 1})
    with pytest.raises(ValueError, match="collision"):
        proof.immutable_save(tmp_path, "original", {"value": 2})
    assert json.loads((tmp_path / "original.json").read_text()) == {"value": 1}


@pytest.mark.parametrize("mutation", ["row", "head", "new_table"])
def test_migration_does_not_admit_other_row_changes(mutation):
    before = {
        "application_state.schema_migrations": [
            {"sha256": "old", "keys": {"version_num": proof.START_SCHEMA}}
        ],
        "agent.turn": [{"sha256": "unchanged", "keys": {}}],
    }
    after = deepcopy(before)
    after["application_state.schema_migrations"] = [
        {"sha256": "new", "keys": {"version_num": proof.END_SCHEMA}}
    ]
    proof.migration_conservation(before, after)
    if mutation == "row":
        after["agent.turn"][0]["sha256"] = "mutated"
    elif mutation == "head":
        after["application_state.schema_migrations"][0]["keys"]["version_num"] = "later"
    else:
        after["unrelated.table"] = []
    with pytest.raises(ValueError):
        proof.migration_conservation(before, after)


def test_exact_original_question_and_explicit_native_selector():
    request = proof.request_body()
    assert (
        request["message"]
        == "What did the party's arcana check reveal about the strange meat found beneath the guardhouse?"
    )
    assert request["graph_request"] == {"mode": "none"}
    assert request["native_statement_selection"]["subjectId"] == proof.SUBJECT


def delivered_sample():
    frame = {
        "subject_id": proof.SUBJECT,
        "revision_id": proof.READ_REVISION,
        "role": "gm",
        "supports": [{"qualified": "exact support"}],
    }
    request = {
        "model": "gpt-6-luna",
        "input": [
            {
                "content": json.dumps(
                    {"question": proof.QUESTION, "native_statement_context": frame}
                )
            }
        ],
    }
    raw = json.dumps(request)
    citation = {
        "read_revision_id": proof.READ_REVISION,
        "body_sha256": proof.fixture.BODY_SHA,
        "clause_sha256": proof.fixture.CLAUSE_SHA,
        "start_byte": 4868,
        "end_byte": 4939,
    }
    citation.update(
        segment_index=0,
        statement_id="ent:statement",
        provider_attempt_id="00000000-0000-0000-0000-000000000001",
        envelope_sha256=proof.fixture.sha(raw.encode()),
        context_receipt_sha256="0" * 64,
        managed_world_id=proof.fixture.WORLD,
        native_world_id=proof.fixture.WORLD,
        campaign_id=proof.fixture.CAMPAIGN,
        publication_revision_id=proof.READ_REVISION,
        source_artifact_id="source",
        source_revision_id="source-version",
        semantic_digest="0" * 64,
    )
    completion = {
        "schema": "dmb_native_statement_completion_v1",
        "context_receipt_sha256": "0" * 64,
        "answer_context_status": "source_attributed",
        "answer_segments": [
            {
                "kind": "source_report",
                "text": "the meat came from another plane.",
                "statement_ids": ["ent:statement"],
            }
        ],
        "native_clause_citations": [citation],
    }
    turn = {
        "turn_id": "one-turn",
        "status": "completed",
        "assistant_text": "Source reports: the meat came from another plane.",
        "graph_context_receipt": {"frame": frame},
        "completion": completion,
        "graph_context_execution": {
            "events": [
                {"kind": "provider_attempt_authorized"},
                {"kind": "provider_outcome", "outcome": "sdk_entered"},
                {
                    "kind": "native_statement_input_v1",
                    "prepared_request_json": raw,
                    "envelope_sha256": proof.fixture.sha(raw.encode()),
                },
            ]
        },
    }
    reply = {
        "native_statement_context": {"completion": completion},
        "answer": {
            "status": "ok",
            "text": "Source reports: the meat came from another plane.",
        },
    }
    history = {
        "turns": [
            {
                "turn_id": "one-turn",
                "assistant_text": turn["assistant_text"],
                "native_statement_context": {"completion": completion},
            }
        ]
    }
    opened = [{"content": proof.fixture.QUOTE, "citation": citation}]
    return turn, reply, history, opened, deepcopy(reply), deepcopy(turn)


@pytest.mark.parametrize(
    "mutation", ["inclusion", "citation", "extent", "replay_dispatch", "unknown"]
)
def test_missing_delivery_evidence_or_replay_dispatch_refuses(mutation):
    sample = list(delivered_sample())
    proof.require_delivered(*sample)
    if mutation == "inclusion":
        sample[0]["graph_context_execution"]["events"].pop()
    elif mutation == "citation":
        sample[3].clear()
    elif mutation == "extent":
        sample[0]["completion"]["native_clause_citations"][0]["end_byte"] = 4940
    elif mutation == "replay_dispatch":
        sample[5]["graph_context_execution"]["events"].append(
            {"kind": "provider_attempt_authorized"}
        )
    else:
        sample[0]["status"] = "interrupted"
    with pytest.raises(ValueError):
        proof.require_delivered(*sample)


def test_unsupported_semantics_never_gets_integrity_pass_as_semantic_verdict():
    sample = list(delivered_sample())
    text = "the meat came from the Abyss because of the Academy."
    sample[0]["completion"]["answer_segments"][0]["text"] = text
    sample[0]["assistant_text"] = "Source reports: " + text
    sample[1]["answer"]["text"] = sample[0]["assistant_text"]
    sample[2]["turns"][0]["assistant_text"] = sample[0]["assistant_text"]
    sample[4] = deepcopy(sample[1])
    sample[5] = deepcopy(sample[0])
    verdict = proof.require_delivered(*sample)
    assert verdict["semantic_support"] == "unassessed"
    assert verdict["autonomous_discovery"] == "unassessed"


@pytest.mark.parametrize(
    "field", ["next_turn_sequence", "world_id", "revision", "status"]
)
def test_archive_exception_cannot_change_content_or_wrong_transition(field):
    old = {
        "conversation_id": proof.OLD_CONVERSATION,
        "world_id": proof.fixture.WORLD,
        "status": "active",
        "revision": 5,
        "next_turn_sequence": 12,
        "archived_at": None,
        "updated_at": "old",
    }
    after = old | {
        "status": "archived",
        "revision": 6,
        "archived_at": "new",
        "updated_at": "new",
    }
    proof.validate_archive(old, after)
    after[field] = "invalid"
    with pytest.raises(ValueError):
        proof.validate_archive(old, after)


def test_explicit_provider_switches_required_before_loading_checkpoint(tmp_path):
    root = tmp_path / "working"
    root.mkdir()
    with pytest.raises(ValueError, match="switches"):
        proof.main(["--clone-root", str(root), "--apply"])


def app_rows():
    def row(sha, **keys):
        return {"sha256": sha, "keys": keys}

    world = proof.fixture.WORLD
    before = {
        "agent.conversation": [
            row(
                "old-conversation",
                conversation_id=proof.OLD_CONVERSATION,
                world_id=world,
            )
        ],
        "agent.world_state": [row("old-pointer", world_id=world)],
        "agent.command_receipt": [],
        "agent.turn": [
            row(
                "old-turn",
                world_id=world,
                conversation_id=proof.OLD_CONVERSATION,
                turn_id="prior",
            )
        ],
        "agent.turn_reference": [],
        "content.document": [row("preserved-document")],
    }
    after = deepcopy(before)
    after["agent.conversation"] = [
        row("archived", conversation_id=proof.OLD_CONVERSATION, world_id=world),
        row("new", conversation_id="owned", world_id=world),
    ]
    after["agent.world_state"] = [row("new-pointer", world_id=world)]
    after["agent.command_receipt"] = [
        row(
            "receipt",
            world_id=world,
            conversation_id="owned",
            command_id=proof.COMMAND_ID,
        )
    ]
    after["agent.turn"].append(
        row("new-turn", world_id=world, conversation_id="owned", turn_id="own-turn")
    )
    after["agent.turn_reference"] = [
        row("ref-" + str(i), turn_id="own-turn", reference_role=role, ordinal=0)
        for i, role in enumerate(("primary", "supporting", "selected"))
    ]
    return before, after


@pytest.mark.parametrize(
    "mutation", ["old_turn", "document", "wrong_command", "unrelated_reference"]
)
def test_exact_app_allowlist_rejects_unrelated_or_unbound_changes(mutation):
    before, after = app_rows()
    proof.app_conservation(
        before,
        after,
        conversation="owned",
        turn="own-turn",
        old_conversation=proof.OLD_CONVERSATION,
    )
    if mutation == "old_turn":
        after["agent.turn"][0]["sha256"] = "mutated-old-turn"
    elif mutation == "document":
        after["content.document"][0]["sha256"] = "mutated-document"
    elif mutation == "wrong_command":
        after["agent.command_receipt"][0]["keys"]["command_id"] = "other"
    else:
        after["agent.turn_reference"][0]["keys"]["turn_id"] = "other"
    with pytest.raises(ValueError):
        proof.app_conservation(
            before,
            after,
            conversation="owned",
            turn="own-turn",
            old_conversation=proof.OLD_CONVERSATION,
        )


def test_retained_keyword_connection_converts_without_changing_target():
    from psycopg.conninfo import conninfo_to_dict

    raw = "host=127.0.0.1 port=55447 dbname=benchmark_ingestion_app_e785f5a2e2 user=test password='synthetic @ secret' options='-c default_transaction_read_only=on'"
    assert conninfo_to_dict(proof.app_connection_url(raw)) == conninfo_to_dict(raw)


def test_unknown_or_entered_operation_refuses_before_configuration(tmp_path):
    (tmp_path / "provider-operation-intent.json").write_text("{}")
    with pytest.raises(ValueError, match="no automatic redispatch"):
        proof.apply_answer(tmp_path / "unavailable-root", tmp_path, {})


@pytest.mark.parametrize("target", [1, 4])
@pytest.mark.parametrize("mutation", ["empty", "error", "divergent"])
def test_http_answer_must_be_successful_nonblank_exact_completion(target, mutation):
    sample = list(delivered_sample())
    if mutation == "empty":
        sample[target]["answer"]["text"] = ""
    elif mutation == "error":
        sample[target]["answer"]["status"] = "error"
    else:
        sample[target]["answer"]["text"] = "Another answer"
    with pytest.raises(ValueError, match="HTTP answer"):
        proof.require_delivered(*sample)


def test_matching_empty_error_replies_are_not_delivery():
    sample = list(delivered_sample())
    sample[1]["answer"] = sample[4]["answer"] = {"status": "error", "text": ""}
    with pytest.raises(ValueError, match="HTTP answer"):
        proof.require_delivered(*sample)


def test_persisted_text_must_match_normalized_completion():
    sample = list(delivered_sample())
    sample[0]["assistant_text"] = "Unrelated persisted answer"
    sample[5] = deepcopy(sample[0])
    with pytest.raises(ValueError, match="persisted answer"):
        proof.require_delivered(*sample)


@pytest.fixture
def actual_v2_wire(tmp_path, monkeypatch):
    from tests.test_source_statements import lane as native_lane, commit, GM
    from tests.test_agent_native_statement_answers import selection_for
    from apps.live_control_server.services.native_statement_answer_context import (
        build_frame,
    )
    from application_state.agent_conversation.native_statement_input import (
        NativeStatementContextReceiptV1,
        NativeStatementWriterPolicyV2,
        canonical,
        digest,
    )
    from application_state.agent_conversation.native_statement_answer import (
        writer_contract,
    )

    lane = native_lane.__wrapped__(tmp_path, monkeypatch)
    commit(lane)
    frame = build_frame(selection_for(lane), GM)
    payload = {
        "schema": "dmb_native_statement_context_receipt_v1",
        "selection": selection_for(lane).model_dump(mode="json", by_alias=True),
        "frame": frame.model_dump(mode="json", by_alias=True),
        "user_text": proof.QUESTION,
        "provenance_sha256": "0" * 64,
    }
    receipt = NativeStatementContextReceiptV1.model_validate(
        payload | {"context_receipt_sha256": digest(payload)}
    )
    policy = NativeStatementWriterPolicyV2(
        model="gpt-6-luna", output_token_reserve=8192, context_limit_tokens=1050000
    )
    instructions, schema = writer_contract(receipt, policy)
    body = {
        "model": policy.model,
        "input": [
            {
                "role": "user",
                "content": canonical(
                    {
                        "question": proof.QUESTION,
                        "native_statement_context": frame.model_dump(
                            mode="json", by_alias=True
                        ),
                    }
                ),
            }
        ],
        "instructions": instructions,
        "max_output_tokens": 8192,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "native_statement_answer",
                "strict": True,
                "schema": schema,
            }
        },
        "tools": [],
        "stream": False,
        "reasoning": {"effort": "none"},
        "service_tier": "fast",
    }
    raw = canonical(body)
    turn = {
        "graph_context_receipt": receipt.model_dump(mode="json", by_alias=True),
        "graph_context_execution": {
            "policy": policy.model_dump(mode="json"),
            "events": [
                {
                    "kind": "native_statement_input_v1",
                    "prepared_request_json": raw,
                    "envelope_sha256": proof.fixture.sha(raw.encode()),
                }
            ],
        },
    }
    return turn, [s.statement_id for s in frame.supports]


@pytest.mark.parametrize("mutation", ["subject_enum", "wrong_policy", "wrong_hash"])
def test_actual_v2_contract_rejects_wrong_policy_selector_or_hash(
    actual_v2_wire, mutation
):
    turn, ids = actual_v2_wire
    assert proof.verify_v2_wire(turn, ids)["allowed_statement_ids"] == ids
    if mutation == "wrong_policy":
        turn["graph_context_execution"]["policy"]["policy_version"] = (
            "native_statement_writer_v1"
        )
    elif mutation == "wrong_hash":
        turn["graph_context_execution"]["events"][0]["envelope_sha256"] = "0" * 64
    else:
        event = turn["graph_context_execution"]["events"][0]
        body = json.loads(event["prepared_request_json"])
        body["text"]["format"]["schema"]["properties"]["segments"]["items"][
            "properties"
        ]["statement_ids"]["items"]["enum"] = [proof.SUBJECT]
        event["prepared_request_json"] = json.dumps(body)
        event["envelope_sha256"] = proof.fixture.sha(
            event["prepared_request_json"].encode()
        )
    with pytest.raises(ValueError):
        proof.verify_v2_wire(turn, ids)


def v2_rows():
    def row(sha, **keys):
        return {"sha256": sha, "keys": keys}

    before = {
        "agent.conversation": [
            row("old-owned", conversation_id=proof.OWNED_CONVERSATION)
        ],
        "agent.turn": [row("failed", turn_id=proof.ORIGINAL_FAILED_TURN)],
        "agent.turn_reference": [],
        "agent.world_state": [row("fixed-pointer")],
        "agent.command_receipt": [],
    }
    after = deepcopy(before)
    after["agent.conversation"] = [
        row("advanced-owned", conversation_id=proof.OWNED_CONVERSATION)
    ]
    after["agent.turn"].append(
        row(
            "new-turn",
            turn_id="v2",
            conversation_id=proof.OWNED_CONVERSATION,
            world_id=proof.fixture.WORLD,
        )
    )
    after["agent.turn_reference"] = [
        row("ref" + str(i), turn_id="v2", reference_role=role, ordinal=0)
        for i, role in enumerate(("primary", "supporting", "selected"))
    ]
    return before, after


@pytest.mark.parametrize(
    "mutation", ["old_turn", "pointer", "command", "other_conversation"]
)
def test_v2_cannot_change_failed_turn_pointer_or_create_conversation(mutation):
    before, after = v2_rows()
    proof.v2_app_conservation(
        before, after, conversation=proof.OWNED_CONVERSATION, turn="v2"
    )
    if mutation == "old_turn":
        after["agent.turn"][0]["sha256"] = "rewritten"
    elif mutation == "pointer":
        after["agent.world_state"][0]["sha256"] = "rewritten"
    elif mutation == "command":
        after["agent.command_receipt"] = [{"sha256": "new-command", "keys": {}}]
    else:
        after["agent.conversation"][0]["keys"]["conversation_id"] = "other"
    with pytest.raises(ValueError):
        proof.v2_app_conservation(
            before, after, conversation=proof.OWNED_CONVERSATION, turn="v2"
        )


def test_v2_new_turn_preserves_original_client_thread_binding():
    request = proof.request_body()
    assert request["client_thread_id"] == "q01-native-answer-v1"
    assert request["turn_id"] == "q01-native-answer-v2-q01"
