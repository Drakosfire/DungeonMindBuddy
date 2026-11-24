"""Derive a red/green Build HTTP clarification witness from the owner test.

Generate only into a disposable checkout. The owner fixture uses synthetic
provider replies and an injected native repository; this witness is not a live
model benchmark or a deployment test. Use a uniquely owned App database rather
than the default multi-clone pytest fixture.
"""
from pathlib import Path


def generate(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Witness output must not replace the owner fixture")
    text = source.read_text()
    start_marker = '    if contextual in {"ambiguous", "missing", "different"}:\n'
    end_marker = '    assert response.status_code == 200, response.text + str(classic_calls)\n'
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise ValueError("Build clarification owner fixture changed")
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    replacement = '''    if contextual in {"ambiguous", "missing", "different"}:
        from application_state.build_proposal.service import BuildProposalService

        # A required clarification is a completed typed reply, not a 409.
        assert response.status_code == 200, response.text
        payload = response.json()
        completion = payload["knowledge_context"]["completion"]
        assert completion["collaboration"]["kind"] == "questions"
        questions = completion["collaboration"]["questions"]
        assert questions and all(isinstance(row["text"], str) and row["text"].strip() for row in questions)
        assert BuildProposalService().list(world, cap.conversation_id) == []
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        return
'''
    test = '''

def test_negative_retrieval_ambiguous_placement_http_witness(lane, tmp_path, monkeypatch):
    """Real HTTP/APP route; synthetic votes and native repository, not model quality."""
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners

    records = []
    try:
        with observe_related_page_owners() as records:
            _fresh_case(lane, tmp_path, monkeypatch, None, True, False, True,
                        contextual="ambiguous", source_need="anchored", read_optional_page=True,
                        message="After the orchid paragraph, add a line about a copper lamp.")
    finally:
        # Records contain host identities only, never source body or model input.
        print("negative_retrieval_related_owners:", records)
    assert not [row for row in records if row["owner"] == "related_page_materialization"]
'''
    output.write_text(text[:start] + replacement + text[end:] + test)
