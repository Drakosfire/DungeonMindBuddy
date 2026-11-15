from types import SimpleNamespace

from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from tests.test_native_plan_assertions import lane, native_read_admission_probes


def test_ranked_passages_defer_full_source_offers_until_follow_up():
    section = RetrievalCandidate(handle="native-body:catalog:section", label="Section", kind="Section")
    documents = (
        RetrievalCandidate(handle="native-direct-source:source", label="Source", kind="Document"),
        RetrievalCandidate(handle="native-full-document:catalog", label="Catalog", kind="Document"),
    )
    ranked = (section, *(section.model_copy(update={"handle": f"native-body:catalog:{i}"}) for i in range(9)))
    candidates = (*documents, *ranked)
    driver = SimpleNamespace(
        discovered=True, catalog={}, attempted_nodes=set(), rules=None,
        saved_page_catalog={}, attempted_saved_pages=set(), dialogue=[],
        native_sources=SimpleNamespace(examined=lambda: ()),
        adapter=SimpleNamespace(), offered=lambda: candidates,
        _native_statement_examined=lambda: (), _native_assertion_examined=lambda: (),
    )

    assert PlanJevDriver.decision_arguments(driver, opening=True)["candidates"] == ranked[:8]
    assert PlanJevDriver.decision_arguments(driver)["candidates"] == (*documents[:1], *ranked[:8])
    driver.offered = lambda: documents
    assert PlanJevDriver.decision_arguments(driver, opening=True)["candidates"] == documents




def test_ordinary_plan_passes_ranked_offers_to_opening_dispatch(
    lane, tmp_path, monkeypatch, native_read_admission_probes,
):
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from tests.test_native_plan_assertions import _ordinary_native_case

    offered = PlanJevDriver.offered
    requested_work = PlanJevDispatch.requested_work
    openings = []
    section = RetrievalCandidate(handle="native-body:catalog:section", label="Ranked fixture passage", kind="Section")
    document = RetrievalCandidate(handle="native-direct-source:recap", label="Whole fixture recap", kind="Document")

    def with_source_offers(driver):
        return (*offered(driver), section, document)

    def capture_opening(cls, *args, **kwargs):
        dispatch = requested_work(*args, **kwargs)
        openings.append(dispatch.parent.candidates)
        return dispatch

    monkeypatch.setattr(PlanJevDriver, "offered", with_source_offers)
    monkeypatch.setattr(PlanJevDispatch, "requested_work", classmethod(capture_opening))
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False,
                          None, "context_capture", False, native_read_admission_probes)
    assert len(openings) == 1
    assert section in openings[0]
    assert document not in openings[0]
