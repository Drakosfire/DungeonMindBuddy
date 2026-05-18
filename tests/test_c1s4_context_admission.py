from evals.c1s4_preplanning_vertical_slice.context_admission import build_budgeted_admission


def _cand(ref, kind, snippet):
    return {"ref": ref, "unit_id": ref, "source_kind": kind, "source_layer": "source_module" if kind == "support_knowledge_card" else None, "snippet": snippet, "title": ref}


def test_prior_only_excludes_support():
    out = build_budgeted_admission(question_text="Hempholm metallic tree", retrieval_mode="prior_only", candidates=[_cand("support:1", "support_knowledge_card", "Hempholm metallic tree")])
    assert all(i["source_kind"] != "support_knowledge_card" for i in out["admitted_context"])


def test_support_mode_admits_relevant_support_with_metadata():
    cands = [_cand(f"s{i}", "session_memory", "filler") for i in range(12)] + [_cand("support:hempholm", "support_knowledge_card", "Hempholm metallic tree merchant")]
    out = build_budgeted_admission(question_text="What about Hempholm metallic tree merchant", retrieval_mode="prior_plus_support_content_only", candidates=cands)
    hit = next(i for i in out["admitted_context"] if i["ref"] == "support:hempholm")
    assert hit["presentation_lane"] == "support_knowledge"
    assert hit["admission_reason"] == "support_budget_relevant_candidate"
    assert "candidate_rank" in hit and "admitted_rank" in hit and "estimated_chars" in hit and "estimated_tokens" in hit


def test_support_mode_excludes_irrelevant_support():
    out = build_budgeted_admission(question_text="Stone bridge route", retrieval_mode="prior_plus_support_content_only", candidates=[_cand("support:1", "support_knowledge_card", "Hempholm metallic tree")])
    assert out["admitted_context"] == []

from evals.c1s4_preplanning_vertical_slice.context_admission import build_lane_budgeted_admission
from evals.c1s4_preplanning_vertical_slice.query_lane_router import build_lane_plan


def test_prior_only_never_admits_support_under_lane_budgeted_policy():
    cands = [_cand('support:1', 'support_knowledge_card', 'Hempholm metallic tree'), _cand('u-L1', 'session_memory', 'party recap')]
    plan = build_lane_plan(question_text='Describe Hempholm tree', retrieval_mode='prior_only')
    out = build_lane_budgeted_admission(question_text='Describe Hempholm tree', retrieval_mode='prior_only', candidates=cands, lane_plan=plan)
    assert all(i['source_kind'] != 'support_knowledge_card' for i in out['admitted_context'])


def test_lane_budgeted_admission_reduces_support_burial_for_support_profile():
    cands = [_cand(f's{i}', 'session_memory', 'filler '*20) for i in range(1, 30)]
    cands.append(_cand('support:late', 'support_knowledge_card', 'Hempholm magical metallic merchant tree ' + ('lore '*500)))
    plan = build_lane_plan(question_text='Describe Hempholm magical metallic merchant tree', retrieval_mode='prior_plus_support_content_only')
    out = build_lane_budgeted_admission(question_text='Describe Hempholm magical metallic merchant tree', retrieval_mode='prior_plus_support_content_only', candidates=cands, lane_plan=plan)
    hit = next(i for i in out['admitted_context'] if i['source_kind'] == 'support_knowledge_card')
    # flat budgeted_v1 would exclude this late support entirely for this fixture; lane budget should admit it
    flat = build_budgeted_admission(question_text='Describe Hempholm magical metallic merchant tree', retrieval_mode='prior_plus_support_content_only', candidates=cands)
    assert not any(i['source_kind'] == 'support_knowledge_card' for i in flat['admitted_context'])
    assert hit['admitted_rank'] is not None


def test_lane_budgeted_admission_keeps_location_and_npc_artifacts():
    candidates = [
        {
            "unit_id": "loc1",
            "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md",
            "snippet": "Stone Bridge location hub",
        },
        {
            "unit_id": "npc1",
            "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/pippa/README.md",
            "snippet": "Pippa NPC hub",
        },
    ]
    plan = build_lane_plan(question_text="Where in Stone Bridge and what about Pippa?", retrieval_mode="prior_only")
    out = build_lane_budgeted_admission(
        question_text="Where in Stone Bridge and what about Pippa?",
        retrieval_mode="prior_only",
        candidates=candidates,
        lane_plan=plan,
    )
    admitted_ids = {i.get("unit_id") for i in out["admitted_context"]}
    assert {"loc1", "npc1"}.issubset(admitted_ids)
