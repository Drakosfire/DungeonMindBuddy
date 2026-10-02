from __future__ import annotations

import importlib.util
import json

import pytest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_graph_crawl_pairs", ROOT / "evals/hermes_tuning/run_graph_crawl_pairs.py"
)
assert SPEC and SPEC.loader
crawl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(crawl)


def execute_fake(fake: Any, arguments: dict[str, Any]) -> str:
    payload = {
        "retrievalSessionId": "offline-test-session",
        "worldId": "synthetic:world",
        "campaignId": "synthetic:campaign",
        "scopeMode": "campaign",
        "focus": {"kind": "none"},
        "admissibility": "gm",
        "revisionPin": "rev:synthetic-1",
        **arguments,
    }
    return fake.execute("expand_graph_retrieval", payload)


def test_six_synthetic_cases_hide_gold_from_model_inputs_and_balance_candidates() -> (
    None
):
    cases = crawl.load_cases()
    assert len(cases) == 6
    assert sum(c["candidate_mode"] == "supplied" for c in cases) == 3
    assert sum(c["candidate_mode"] == "discovered" for c in cases) == 3
    for case in cases:
        context = crawl.build_context(case) or ""
        question = case["question"]
        model_input = context + question
        visible_ids = {candidate["id"] for candidate in case["candidates"]} | set(
            case["requested_endpoint_node_ids"]
        )
        for node in case["nodes"]:
            if node["id"] not in visible_ids:
                assert node["label"].casefold() not in model_input.casefold()
        for attributes in case["identity_attributes"].values():
            for attribute in attributes:
                assert attribute["value"].casefold() not in model_input.casefold()
        for edge in case["edges"]:
            assert edge["id"] not in model_input
            assert edge["predicate"] not in model_input
        for expected_id in case["expected_edge_ids"]:
            assert expected_id not in context + question
        assert "expected_edge_ids" not in context + question


def test_actual_model_visible_schema_uses_targets_and_depth() -> None:
    contract = crawl.model_visible_tool_contract()["expand_graph_retrieval"][
        "parameters"
    ]
    props = contract["properties"]
    assert {"operation", "targets", "depth"} <= set(props)
    assert "seedNodeIds" not in props
    assert "maxDepth" not in props
    assert props["depth"]["enum"] == [1, 2]
    target_ref = props["targets"]["items"]["$ref"].rsplit("/", 1)[-1]
    assert contract["$defs"][target_ref]["properties"]["kind"]["const"] == "node"


def test_fake_rejects_executor_internal_fields_and_invalid_depth() -> None:
    case = crawl.load_cases()[0]
    fake = crawl.StatefulFakeDispatcher(case)
    bad_internal = json.loads(
        fake.execute(
            "expand_graph_retrieval",
            {
                "retrievalSessionId": "test",
                "operation": "neighborhood",
                "targets": [{"kind": "node", "id": "person:mira"}],
                "depth": 2,
                "maxDepth": 2,
            },
        )
    )
    assert bad_internal["code"] == "unexpected_request_fields"
    bad_depth = json.loads(
        execute_fake(
            fake,
            {
                "operation": "neighborhood",
                "targets": [{"kind": "node", "id": "person:mira"}],
                "depth": 3,
            },
        )
    )
    assert bad_depth["code"] == "invalid_model_visible_request"


def test_fake_requires_candidate_acceptance_and_withholds_relationships() -> None:
    case = next(c for c in crawl.load_cases() if c["case_id"] == "discovered-two-hop")
    fake = crawl.StatefulFakeDispatcher(case)
    invalid = json.loads(
        execute_fake(
            fake,
            {
                "operation": "neighborhood",
                "targets": [{"kind": "node", "id": "person:sella"}],
                "depth": 2,
            },
        )
    )
    assert invalid["code"] == "neighborhood_requires_accepted_targets_and_depth_1_or_2"
    first = json.loads(
        execute_fake(fake, {"operation": "search", "targets": [], "depth": 1})
    )
    assert first["relationships"] == []
    assert first["matchedNodeIds"] == ["person:sella"]
    result = json.loads(
        execute_fake(
            fake,
            {
                "operation": "neighborhood",
                "targets": [{"kind": "node", "id": "person:sella"}],
                "depth": 2,
            },
        )
    )
    assert [edge["edgeId"] for edge in result["relationships"]] == case[
        "expected_edge_ids"
    ]
    assert [r["operation"] for r in fake.reads] == [
        "neighborhood",
        "search",
        "neighborhood",
    ]


def test_search_and_object_never_return_relationships_and_depth_limits_path() -> None:
    case = next(
        c
        for c in crawl.load_cases()
        if c["case_id"] == "supplied-object-disambiguation"
    )
    fake = crawl.StatefulFakeDispatcher(case)
    obj = json.loads(
        execute_fake(
            fake,
            {
                "operation": "object",
                "targets": [{"kind": "node", "id": "person:oren-b"}],
            },
        )
    )
    assert obj["relationships"] == []
    assert obj["attributes"][0]["textValue"] == "potter"
    assert fake.reads[0]["returned_attributes"][0]["textValue"] == "potter"

    path_case = next(
        c for c in crawl.load_cases() if c["case_id"] == "supplied-two-hop"
    )
    shallow = crawl.StatefulFakeDispatcher(path_case)
    result = json.loads(
        execute_fake(
            shallow,
            {
                "operation": "neighborhood",
                "targets": [{"kind": "node", "id": "person:mira"}],
                "depth": 1,
            },
        )
    )
    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["edgeId"] != path_case["expected_edge_ids"][1]


def test_only_treatment_prompt_has_fixed_instruction_and_system_policy_is_external() -> (
    None
):
    case = crawl.load_cases()[0]
    control = crawl.build_question(case, "control")
    treatment = crawl.build_question(case, "treatment")
    assert treatment == control + "\n\n" + crawl.INSTRUCTION
    assert crawl.INSTRUCTION not in control


def test_status_and_traversal_gates_are_separate_and_fail_closed() -> None:
    case = next(c for c in crawl.load_cases() if c["case_id"] == "supplied-two-hop")
    fake = crawl.StatefulFakeDispatcher(case)
    fake.edges_returned[:] = case["expected_edge_ids"]
    gates = crawl.hard_gates(
        case,
        "Mira visits Lantern Yard, which opens toward the Brass Observatory.",
        "ok",
        fake,
    )
    assert gates["turn_status_ok"]
    assert gates["traversal_success"]
    assert gates["answer_gate_pass"]
    rejected = crawl.StatefulFakeDispatcher(case)
    rejected.reads.append({"result_status": "error"})
    rejected.edges_returned[:] = case["expected_edge_ids"]
    failed = crawl.hard_gates(
        case,
        "Mira visits Lantern Yard, which opens toward the Brass Observatory.",
        "ok",
        rejected,
    )
    assert failed["turn_status_ok"]
    assert not failed["no_failed_graph_operations"]
    assert not failed["traversal_success"]


def test_blind_packet_has_answers_evidence_and_no_arm_mapping_or_trace() -> None:
    cases = crawl.load_cases()
    answers = []
    for case in cases:
        answers.append(
            {
                "case_id": case["case_id"],
                "arms": {
                    "control": {"answer": "A raw answer."},
                    "treatment": {"answer": "Another raw answer."},
                },
            }
        )
    packet = crawl.blinded_packet(cases, answers)
    encoded = json.dumps(packet)
    for forbidden in (
        "control",
        "treatment",
        "fake_trace",
        "tool_events",
        "wall_ms",
        "estimated_cost",
        crawl.INSTRUCTION,
    ):
        assert forbidden not in encoded
    assert len(packet["items"]) == 6
    assert all("answer_A_evidence_seen" in item for item in packet["items"])
    assert all("answer_B_evidence_seen" in item for item in packet["items"])
    assert all("expected_answer_key" in item for item in packet["items"])


def test_blind_answer_hashes_map_to_exactly_one_raw_arm() -> None:
    raw_cases = [
        {
            "case_id": "case-1",
            "arms": {
                "control": {"answer": "Control answer."},
                "treatment": {"answer": "Treatment answer."},
            },
        }
    ]
    packet = {
        "items": [
            {
                "case_id": "case-1",
                "answer_A_sha256": crawl.sha("Treatment answer."),
                "answer_B_sha256": crawl.sha("Control answer."),
            }
        ]
    }
    assert crawl.map_blinded_answer_hashes(raw_cases, packet["items"]) == {
        "case-1": {"A": "treatment", "B": "control"}
    }
    packet["items"][0]["answer_A_sha256"] = crawl.sha("different answer")
    with pytest.raises(ValueError, match="exactly one unique raw arm"):
        crawl.map_blinded_answer_hashes(raw_cases, packet["items"])


def test_blind_packet_reports_only_evidence_returned_to_each_answer() -> None:
    case = next(c for c in crawl.load_cases() if c["case_id"] == "supplied-two-hop")
    rows = []
    for arm, depth in (("control", 1), ("treatment", 2)):
        fake = crawl.StatefulFakeDispatcher(case)
        execute_fake(
            fake,
            {
                "operation": "neighborhood",
                "targets": [{"kind": "node", "id": "person:mira"}],
                "depth": depth,
            },
        )
        rows.append((arm, fake.reads))
    result = {"case_id": case["case_id"], "arms": {}}
    for arm, trace in rows:
        result["arms"][arm] = {"answer": f"answer {arm}", "fake_trace": trace}
    item = crawl.blinded_packet([case], [result])["items"][0]
    counts = {
        len(item["answer_A_evidence_seen"]["relationships"]),
        len(item["answer_B_evidence_seen"]["relationships"]),
    }
    assert counts == {1, 2}
    assert len(item["expected_answer_key"]["supported_relationships"]) == 2
    assert "operation" not in json.dumps(item["answer_A_evidence_seen"])
    assert "operation" not in json.dumps(item["answer_B_evidence_seen"])


def test_blind_packet_includes_identity_attributes_only_when_object_returned_them() -> (
    None
):
    case = next(
        c
        for c in crawl.load_cases()
        if c["case_id"] == "supplied-object-disambiguation"
    )
    arms = {}
    for arm, node_id in (("control", "person:oren-a"), ("treatment", "person:oren-b")):
        fake = crawl.StatefulFakeDispatcher(case)
        execute_fake(
            fake,
            {"operation": "object", "targets": [{"kind": "node", "id": node_id}]},
        )
        arms[arm] = {"answer": f"Raw answer for {arm}.", "fake_trace": fake.reads}
    item = crawl.blinded_packet([case], [{"case_id": case["case_id"], "arms": arms}])[
        "items"
    ][0]
    returned_values = {
        answer["textValue"]
        for key in ("answer_A_evidence_seen", "answer_B_evidence_seen")
        for answer in item[key]["identity_attributes"]
    }
    assert returned_values == {"mapmaker", "potter"}
    assert "operation" not in json.dumps(item["answer_A_evidence_seen"])
    assert "operation" not in json.dumps(item["answer_B_evidence_seen"])


def test_no_path_gate_requires_lookup_scope_and_ambiguity_gate_rejects_asserted_chain() -> (
    None
):
    no_path = next(c for c in crawl.load_cases() if c["case_id"] == "supplied-no-path")
    fake = crawl.StatefulFakeDispatcher(no_path)
    execute_fake(
        fake,
        {
            "operation": "neighborhood",
            "targets": [{"kind": "node", "id": "person:pella"}],
            "depth": 2,
        },
    )
    bounded = crawl.hard_gates(
        no_path,
        "No path appears in this bounded lookup; that does not establish global absence.",
        "ok",
        fake,
    )
    unbounded = crawl.hard_gates(
        no_path, "There is no connection anywhere.", "ok", fake
    )
    assert bounded["required_abstention_explicit"]
    assert bounded["successful_no_path_neighborhood"]
    assert not unbounded["required_abstention_explicit"]
    assert unbounded["traversal_success"]
    assert not unbounded["answer_gate_pass"]

    ambiguous = next(
        c for c in crawl.load_cases() if c["case_id"] == "discovered-ambiguous-label"
    )
    amb_fake = crawl.StatefulFakeDispatcher(ambiguous)
    assert crawl.hard_gates(
        ambiguous,
        "It is ambiguous which Tavi; the records do not identify the person.",
        "ok",
        amb_fake,
    )["required_abstention_explicit"]
    assert crawl.hard_gates(
        ambiguous,
        "The graph has two distinct records named Tavi. One is linked to the Ember Gate; "
        "the records provide no further details to distinguish the two Tavis, so I can't "
        "identify which one that is.",
        "ok",
        amb_fake,
    )["required_abstention_explicit"]
    assert not crawl.hard_gates(
        ambiguous,
        "The records distinguish two people named Tavi. One Tavi (person:tavi-a) is "
        "connected to the Ember Gate by an approaches relationship. The retrieved "
        "neighborhood shows no connection for the other Tavi, so I can't attribute "
        "that relationship to them.",
        "ok",
        amb_fake,
    )["required_abstention_explicit"]
    assert not crawl.hard_gates(
        ambiguous, "Tavi approaches the Ember Gate.", "ok", amb_fake
    )["required_abstention_explicit"]


def test_no_path_requires_successful_empty_neighborhood() -> None:
    no_path = next(c for c in crawl.load_cases() if c["case_id"] == "supplied-no-path")
    fake = crawl.StatefulFakeDispatcher(no_path)
    gates = crawl.hard_gates(
        no_path, "No path appears in this bounded lookup.", "ok", fake
    )
    assert not gates["successful_no_path_neighborhood"]
    assert not gates["required_abstention_explicit"]
    assert not gates["traversal_success"]

    execute_fake(
        fake,
        {
            "operation": "neighborhood",
            "targets": [{"kind": "node", "id": "person:pella"}],
            "depth": 2,
        },
    )
    passed = crawl.hard_gates(
        no_path, "No path appears in this bounded lookup.", "ok", fake
    )
    assert passed["successful_no_path_neighborhood"]
    assert passed["required_abstention_explicit"]
    assert passed["traversal_success"]


def test_no_path_gate_accepts_bounded_failure_to_establish_connection() -> None:
    no_path = next(c for c in crawl.load_cases() if c["case_id"] == "supplied-no-path")
    fake = crawl.StatefulFakeDispatcher(no_path)
    execute_fake(
        fake,
        {
            "operation": "neighborhood",
            "targets": [{"kind": "node", "id": "person:pella"}],
            "depth": 2,
        },
    )
    gates = crawl.hard_gates(
        no_path,
        "The lookup matched Pella as a Person, but returned no relationships or attributes. "
        "It does not establish a connection between Pella and the Moss Archive.",
        "ok",
        fake,
    )
    assert gates["required_abstention_explicit"]
    assert gates["answer_gate_pass"]


def test_fresh_sessions_normalize_to_same_system_policy_hash() -> None:
    case = crawl.load_cases()[0]
    scope = crawl.HermesGraphScope(
        world_id="synthetic:hermes-crawl",
        campaign_id="synthetic:crawl",
        scope_mode="campaign",
        focus={"kind": "none"},
        admissibility="gm",
        revision_pin="rev:synthetic-crawl-1",
    )
    policy = crawl.default_graph_only_capability_policy(scope)
    request_a = crawl.build_request(
        case,
        "control",
        policy,
        scope,
        session_id="turn-a",
        retrieval_session_id="retrieval-a",
    )
    request_b = crawl.build_request(
        case,
        "treatment",
        policy,
        scope,
        session_id="turn-b",
        retrieval_session_id="retrieval-b",
    )
    system_a = crawl._build_ephemeral_system_prompt(
        policy, request_a, retrieval_session_packet=None
    )
    system_b = crawl._build_ephemeral_system_prompt(
        policy, request_b, retrieval_session_packet=None
    )
    assert crawl.sha(system_a) != crawl.sha(system_b)
    assert crawl.normalized_system_prompt_sha256(
        system_a, "retrieval-a"
    ) == crawl.normalized_system_prompt_sha256(system_b, "retrieval-b")


def test_policy_or_context_difference_rejects_normalized_parity() -> None:
    case = crawl.load_cases()[0]
    scope = crawl.HermesGraphScope(
        world_id="synthetic:hermes-crawl",
        campaign_id="synthetic:crawl",
        scope_mode="campaign",
        focus={"kind": "none"},
        admissibility="gm",
        revision_pin="rev:synthetic-crawl-1",
    )
    policy = crawl.default_graph_only_capability_policy(scope)
    base = crawl.build_request(
        case,
        "control",
        policy,
        scope,
        session_id="turn-a",
        retrieval_session_id="retrieval-a",
    )
    base_system = crawl._build_ephemeral_system_prompt(
        policy, base, retrieval_session_packet=None
    )
    changed_scope = crawl.HermesGraphScope(
        world_id="synthetic:other-world",
        campaign_id="synthetic:crawl",
        scope_mode="campaign",
        focus={"kind": "none"},
        admissibility="gm",
        revision_pin="rev:synthetic-crawl-1",
    )
    changed_policy = crawl.default_graph_only_capability_policy(changed_scope)
    changed_request = crawl.build_request(
        case,
        "treatment",
        changed_policy,
        changed_scope,
        session_id="turn-b",
        retrieval_session_id="retrieval-b",
    )
    changed_system = crawl._build_ephemeral_system_prompt(
        changed_policy, changed_request, retrieval_session_packet=None
    )
    assert crawl.normalized_system_prompt_sha256(
        base_system, "retrieval-a"
    ) != crawl.normalized_system_prompt_sha256(changed_system, "retrieval-b")

    changed_case = dict(case)
    changed_case["candidates"] = [
        {**case["candidates"][0], "label": "Different synthetic candidate"}
    ]
    changed_context_request = crawl.build_request(
        changed_case,
        "treatment",
        policy,
        scope,
        session_id="turn-c",
        retrieval_session_id="retrieval-c",
    )
    changed_context_system = crawl._build_ephemeral_system_prompt(
        policy, changed_context_request, retrieval_session_packet=None
    )
    assert crawl.normalized_system_prompt_sha256(
        base_system, "retrieval-a"
    ) != crawl.normalized_system_prompt_sha256(changed_context_system, "retrieval-c")


def test_checkpoint_survives_later_failure_and_resume_preserves_paid_arm(
    tmp_path: Path,
) -> None:
    cases = crawl.load_cases()
    rows = [
        {
            "case_id": cases[0]["case_id"],
            "arm_order": ["control", "treatment"],
            "arms": {
                "control": {
                    "answer": "raw synthetic answer",
                    "status": "ok",
                    "model_calls": [
                        {
                            "duration_ms": 123,
                            "usage": {"input_tokens": 10},
                            "cost": {"usd": 0.001},
                        }
                    ],
                    "fake_trace": [
                        {
                            "operation": "neighborhood",
                            "returned_edge_ids": ["edge:mira-yard"],
                        }
                    ],
                }
            },
        }
    ]
    record = {
        "schema": "hermes_synthetic_graph_crawl_pairs_v1",
        "provider": "openai-api",
        "model": "gpt-6-luna",
        "fixture_sha256": "fixture",
        "instruction_sha256": "instruction",
        "cohort_status": "pilot_in_progress",
        "cases": rows,
        "randomization_seed": 91073,
        "blind_randomization_seed": 47029,
    }
    path = tmp_path / "pilot.json"
    crawl.write_checkpoint(path, record)
    try:
        raise RuntimeError("simulated later arm failure")
    except RuntimeError:
        pass
    loaded = json.loads(path.read_text())
    assert loaded["cases"][0]["arms"]["control"]["answer"] == "raw synthetic answer"
    assert (
        loaded["cases"][0]["arms"]["control"]["model_calls"][0]["cost"]["usd"] == 0.001
    )
    resumed = crawl.load_resume_record(
        path,
        provider="openai-api",
        model="gpt-6-luna",
        fixture_sha="fixture",
        instruction_sha="instruction",
        cases=cases,
        prime_approval_reference=None,
        requested_stop_after=2,
    )
    assert "control" in resumed["cases"][0]["arms"]
    assert "treatment" not in resumed["cases"][0]["arms"]
    with pytest.raises(ValueError, match="first two cases"):
        crawl.load_resume_record(
            path,
            provider="openai-api",
            model="gpt-6-luna",
            fixture_sha="fixture",
            instruction_sha="instruction",
            cases=cases,
            prime_approval_reference=None,
            requested_stop_after=6,
        )


def test_resume_reuses_exact_pending_pilot_and_rejects_mutated_rows(
    tmp_path: Path,
) -> None:
    cases = crawl.load_cases()
    rows = [
        {
            "case_id": case["case_id"],
            "arm_order": ["treatment", "control"],
            "arms": {
                "control": {"answer": "unchanged raw"},
                "treatment": {"answer": "paired raw"},
            },
        }
        for case in cases[:2]
    ]
    record = {
        "schema": "hermes_synthetic_graph_crawl_pairs_v1",
        "provider": "openai-api",
        "model": "gpt-6-luna",
        "fixture_sha256": "fixture",
        "instruction_sha256": "instruction",
        "cohort_status": "pilot_pending_prime_checkin",
        "pilot_cases_sha256": crawl.pilot_rows_sha256(rows),
        "cases": rows,
        "randomization_seed": 91073,
        "blind_randomization_seed": 47029,
    }
    path = tmp_path / "pilot.json"
    crawl.write_checkpoint(path, record)
    with pytest.raises(ValueError, match="PRIME approval"):
        crawl.load_resume_record(
            path,
            provider="openai-api",
            model="gpt-6-luna",
            fixture_sha="fixture",
            instruction_sha="instruction",
            cases=cases,
            prime_approval_reference=None,
            requested_stop_after=6,
        )
    approval = "PRIME approved continuation for graph-crawl handoff"
    resumed = crawl.load_resume_record(
        path,
        provider="openai-api",
        model="gpt-6-luna",
        fixture_sha="fixture",
        instruction_sha="instruction",
        cases=cases,
        prime_approval_reference=approval,
        requested_stop_after=6,
    )
    assert resumed["cases"] == rows
    assert resumed["randomization_seed"] == 91073
    assert resumed["blind_randomization_seed"] == 47029
    resumed["cases"][0]["arms"]["control"]["answer"] = "changed"
    path.write_text(json.dumps(resumed))
    try:
        crawl.load_resume_record(
            path,
            provider="openai-api",
            model="gpt-6-luna",
            fixture_sha="fixture",
            instruction_sha="instruction",
            cases=cases,
            prime_approval_reference=approval,
            requested_stop_after=6,
        )
    except ValueError as exc:
        assert "hash/state mismatch" in str(exc)
    else:
        raise AssertionError("resume accepted modified pilot results")


def test_continuation_resume_validates_approval_and_keeps_partial_case(
    tmp_path: Path,
) -> None:
    cases = crawl.load_cases()
    rows = [
        {
            "case_id": case["case_id"],
            "arm_order": ["control", "treatment"],
            "arms": {
                "control": {"answer": f"pilot {i} control"},
                "treatment": {"answer": f"pilot {i} treatment"},
            },
        }
        for i, case in enumerate(cases[:2])
    ]
    rows.append(
        {
            "case_id": cases[2]["case_id"],
            "arm_order": ["treatment", "control"],
            "arms": {"treatment": {"answer": "paid third-case arm"}},
        }
    )
    approval = "PRIME approved remaining four pairs for pinned handoff"
    record = {
        "schema": "hermes_synthetic_graph_crawl_pairs_v1",
        "provider": "openai-api",
        "model": "gpt-6-luna",
        "fixture_sha256": "fixture",
        "instruction_sha256": "instruction",
        "cohort_status": "continuation_in_progress",
        "continuation_approval_reference": approval,
        "pilot_cases_sha256": crawl.pilot_rows_sha256(rows[:2]),
        "cases": rows,
    }
    path = tmp_path / "continuation.json"
    crawl.write_checkpoint(path, record)
    accepted = crawl.load_resume_record(
        path,
        provider="openai-api",
        model="gpt-6-luna",
        fixture_sha="fixture",
        instruction_sha="instruction",
        cases=cases,
        prime_approval_reference=approval,
        requested_stop_after=6,
    )
    assert accepted["cases"][2]["arms"]["treatment"]["answer"] == "paid third-case arm"
    with pytest.raises(ValueError, match="through the six-case cohort"):
        crawl.load_resume_record(
            path,
            provider="openai-api",
            model="gpt-6-luna",
            fixture_sha="fixture",
            instruction_sha="instruction",
            cases=cases,
            prime_approval_reference=approval,
            requested_stop_after=2,
        )
    with pytest.raises(ValueError, match="exact recorded PRIME approval"):
        crawl.load_resume_record(
            path,
            provider="openai-api",
            model="gpt-6-luna",
            fixture_sha="fixture",
            instruction_sha="instruction",
            cases=cases,
            prime_approval_reference="wrong approval",
            requested_stop_after=6,
        )


def test_fresh_output_guard_refuses_existing_pilot_path(tmp_path: Path) -> None:
    path = tmp_path / "existing.json"
    path.write_text("preserve")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        crawl.validate_fresh_output(path, resume=False)
    crawl.validate_fresh_output(path, resume=True)
    assert path.read_text() == "preserve"
