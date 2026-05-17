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
