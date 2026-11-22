from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation import native_corpus
from application_state.agent_conversation import authored_graph_references
from application_state.agent_conversation import writer_evidence_selection as selection
from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
from application_state.agent_conversation.model_markdown import project_model_markdown
from application_state.agent_conversation.native_build_work_view import semantic_frame


def test_projects_managed_images_and_preserves_source_line_addresses():
    source = (
        "# Survey\r\n"
        "\r\n"
        "Before ![North *gate*](dmb-media:private-asset\r\n"
        ' "dmb-image:v1 width=80 collapsed=false") after.\r\n'
        "\r\n"
        "![South door][survey-image]\r\n"
        "\r\n"
        "[survey-image]: dmb-media&#58;second-private-asset\r\n"
        "\r\n"
        "Last source line.\r\n"
    )

    assert project_model_markdown(source) == (
        "# Survey\r\n"
        "\r\n"
        "Before [Image: North gate] after.\r\n"
        "\r\n"
        "\r\n"
        "[Image: South door]\r\n"
        "\r\n"
        "\r\n"
        "\r\n"
        "Last source line.\r\n"
    )


def test_preserves_literal_documentation_and_plain_markdown():
    source = (
        "Keep **these words** and [the reference](https://example.org).\n\n"
        "`![Example](dmb-media:literal)`\n\n"
        "![Public](https://example.org/image.png)\n"
    )

    assert project_model_markdown(source) == source


def test_native_selection_binds_projected_bytes_before_dispatch(monkeypatch):
    text = "![Survey](dmb-media:private-asset)\n"
    catalog = {"host-source": {"kind": "saved_section", "section": {
        "text": text, "source_class": "authored", "line_start": 11, "line_end": 11,
    }}}
    turn = SimpleNamespace(
        user_text="What does the survey show?",
        graph_context_execution=SimpleNamespace(policy=object()),
    )
    monkeypatch.setattr(native_corpus, "acquired_body_catalogs", lambda _: {})
    monkeypatch.setattr(selection, "native_build", lambda _: True)
    monkeypatch.setattr(selection, "enabled", lambda _: True)
    monkeypatch.setattr(selection, "acquired_catalog", lambda *args, **kwargs: catalog)
    monkeypatch.setattr(selection, "selection_history", lambda *args: {})
    monkeypatch.setattr(selection, "native_terminal", lambda *args, **kwargs: {})

    def request(*, retained_raw_markdown=False):
        wire = selection.canonical({
            "model": "test-model",
            "state": selection.semantic_state(turn, catalog, retained_raw_markdown=retained_raw_markdown),
            "questions": selection.questions(catalog, semantic=True),
        })
        return wire, SimpleNamespace(model="test-model", sequence=2, envelope_sha256=sha256(wire.encode()).hexdigest())

    projected, authorization = request()
    admitted, acquired = selection.validate_prepared_selection(turn, authorization, projected, {})
    assert admitted["state"]["sources"]["s0"]["text"] == "[Image: Survey]\n"
    assert admitted["state"]["sources"]["s0"]["line_start"] == 11
    assert acquired["host-source"]["section"]["text"] == text

    historical, historical_authorization = request(retained_raw_markdown=True)
    with pytest.raises(ValueError, match="catalog"):
        selection.validate_prepared_selection(turn, historical_authorization, historical, {})
    selection.validate_prepared_selection(
        turn, historical_authorization, historical, {}, retained_proof=True,
    )


def test_build_writer_keeps_source_aliases_and_projects_author_visible_images(monkeypatch):
    monkeypatch.setattr(authored_graph_references, "model_reference_choices", lambda _: None)
    source = "![Survey](dmb-media:private-asset)\n"
    host = {
        "schema": NATIVE_WORK_SCHEMA,
        "source_basis": {"visibility": "internal"},
        "artifact_under_edit": {"sections": [
            {"read_id": str(uuid4()), "line_start": 7, "line_end": 7, "text": source},
        ]},
        "working_draft_context": {"record_id": str(uuid4()), "draft_markdown": source},
        "captured_editor": {"basis": {}, "draft_markdown": source},
        "related_authored_pages": {"availability": [], "pages": [
            {"read_id": str(uuid4()), "page": {"title": "Second survey", "visibility": "internal"},
             "markdown": source},
        ]},
    }

    current = semantic_frame(host, None)["build_work"]
    retained = semantic_frame(host, None, retained_raw_markdown=True)["build_work"]
    assert current["saved_sections"] == [
        {**retained["saved_sections"][0], "text": "[Image: Survey]\n"},
    ]
    assert current["current_draft"] == {"selection": "draft0", "markdown": "[Image: Survey]\n"}
    assert current["editor_markdown"] == "[Image: Survey]\n"
    assert current["related_pages"][0] == {**retained["related_pages"][0], "markdown": "[Image: Survey]\n"}
    assert host["artifact_under_edit"]["sections"][0]["text"] == source
