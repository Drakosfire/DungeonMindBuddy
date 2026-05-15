from evals.c1s4_preplanning_vertical_slice.validate_beat_question_targets import (
    ORACLE_TERMS,
    iter_questions,
    load_targets,
    validate_targets,
)


def test_beat_question_targets_validate():
    assert validate_targets(load_targets()) == []


def test_beat_question_targets_have_expected_sessions():
    targets = load_targets()
    assert targets["source_sessions_allowed_for_planner"] == [1, 2, 3]
    assert targets["heldout_session"] == 4
    assert targets["planner_visibility"] == "forbidden"


def test_beat_question_targets_include_q1_to_q38():
    nums = sorted(q["question_number"] for q in iter_questions(load_targets()))
    assert nums == list(range(1, 39))


def test_context_gap_questions_are_labeled_correctly():
    qmap = {q["question_number"]: q for q in iter_questions(load_targets())}
    assert "Stone Bridge-to-Mirathorn" in " ".join(qmap[3]["known_context_gaps"])
    assert qmap[3]["authority_label"] == "worldbuilding_required"
    assert qmap[4]["authority_label"] == "support_knowledge_required"
    assert qmap[5]["authority_label"] == "support_knowledge_required"
    assert qmap[6]["authority_label"] == "mixed"


def test_oracle_sensitive_terms_are_not_prior_only_context():
    for q in iter_questions(load_targets()):
        if q["authority_label"] == "prior_recap_supported":
            prior_ctx = " ".join(q.get("expected_retrieval_context_eval_only", []))
            assert all(term.lower() not in prior_ctx.lower() for term in ORACLE_TERMS)


def test_target_artifact_is_not_planner_visible():
    targets = load_targets()
    assert targets["planner_visibility"] == "forbidden"
    # Future retrieval code must not load this target artifact as planner context.


def test_meta_questions_exist():
    nums = {q["question_number"] for q in load_targets()["meta_questions"]}
    assert nums == {34, 35, 36, 37, 38}


def test_support_required_questions_do_not_expect_prior_only_full_answer():
    for q in iter_questions(load_targets()):
        if q["authority_label"] == "support_knowledge_required":
            assert q["expected_retrieval_modes"]["prior_only"] != "should_answer_well"
