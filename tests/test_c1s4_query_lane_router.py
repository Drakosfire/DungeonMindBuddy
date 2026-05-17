from evals.c1s4_preplanning_vertical_slice.query_lane_router import build_lane_plan, extract_query_features


def test_query_features_detect_prior_npc_context():
    plan = build_lane_plan(question_text='Who are the NPCs encountered at Stone Bridge with Pippa?', retrieval_mode='prior_only')
    assert plan['profile'] == 'prior_npc_context'
    assert plan['lanes']['support_knowledge']['target_chars'] == 0


def test_query_features_detect_route_or_distance_gap():
    plan = build_lane_plan(question_text='How far is the route between Stone Bridge and Mirathorn?', retrieval_mode='prior_only')
    assert plan['profile'] == 'route_or_distance_gap'
    assert plan['lanes']['known_gaps']['priority'] == 0
    assert plan['lanes']['known_gaps']['target_chars'] >= 1000


def test_query_features_detect_support_description():
    plan = build_lane_plan(question_text='Describe the magical metallic merchant tree in Hempholm', retrieval_mode='prior_plus_support_content_only')
    assert plan['profile'] == 'support_description'
    assert plan['lanes']['support_knowledge']['target_chars'] >= 3500
