"""Tests for authored graph gold/eval export foundation."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphOverlay,
    GraphAuthoringProvenance,
    GraphAuthoringSourceAnchor,
    GraphVisibilityPolicy,
    UnsafeCampaignRelError,
    hash_text,
)
from apps.live_control_server.services.graph_authoring_gold_eval_export import (
    AUTHORED_GRAPH_GOLD_EVAL_EXPORT_SCHEMA,
    AuthoredGraphGoldEvalExportOptions,
    build_authored_graph_gold_eval_export,
    export_authored_graph_gold_eval,
    gold_eval_eligible_assertions,
    write_authored_graph_gold_eval_export,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    EXPORTS_DIR,
    GRAPH_AUTHORING_DIR,
    GraphAuthoringOverlayStore,
)
from tests.test_graph_authoring_overlay_models import (
    CAMPAIGN_ID,
    STAMP,
    link_existing_assertion,
    object_assertion,
    relationship_assertion,
)

TEST_CAMPAIGN_REL = "Test Campaign/A9"
SESSION_ID = "session-23"


def _source_anchor(**overrides) -> GraphAuthoringSourceAnchor:
    data = {
        "anchor_kind": "text_span",
        "selected_text": "gang",
        "normalized_selected_text": "gang",
        "source_span_ref_id": "span-gang-1",
        "selected_text_sha256": hash_text("gang"),
        "context_sha256": hash_text("the gang marched"),
    }
    data.update(overrides)
    return GraphAuthoringSourceAnchor.model_validate(data)


def _overlay(*assertions) -> AuthoredGraphOverlay:
    return AuthoredGraphOverlay(
        campaign_id=CAMPAIGN_ID,
        overlay_id=f"overlay-{CAMPAIGN_ID}",
        created_at=STAMP,
        updated_at=STAMP,
        assertions=list(assertions),
    )


def _export_options(**overrides) -> AuthoredGraphGoldEvalExportOptions:
    data = {
        "campaign_id": CAMPAIGN_ID,
        "session_id": SESSION_ID,
    }
    data.update(overrides)
    return AuthoredGraphGoldEvalExportOptions.model_validate(data)


def test_export_filters_to_include_in_gold_eval_true() -> None:
    flagged = object_assertion(
        assertion_id="assert-flagged",
        include_in_gold_eval=True,
    )
    unflagged = object_assertion(
        assertion_id="assert-unflagged",
        include_in_gold_eval=False,
    )
    overlay = _overlay(flagged, unflagged)

    eligible = gold_eval_eligible_assertions(overlay)
    assert [item.assertion_id for item in eligible] == ["assert-flagged"]

    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(created_at=STAMP),
    )
    assert export is not None
    assert len(export.assertions) == 1
    assert export.assertions[0].assertion_id == "assert-flagged"
    assert export.source_overlay.assertion_count == 2
    assert export.source_overlay.included_assertion_count == 1


def test_export_excludes_retracted_or_superseded_assertions() -> None:
    active = object_assertion(
        assertion_id="assert-active",
        include_in_gold_eval=True,
    )
    retracted = object_assertion(
        assertion_id="assert-retracted",
        include_in_gold_eval=True,
        status="retracted",
    )
    superseded = object_assertion(
        assertion_id="assert-superseded",
        include_in_gold_eval=True,
        status="superseded",
    )
    overlay = _overlay(active, retracted, superseded)

    eligible = gold_eval_eligible_assertions(overlay)
    assert [item.assertion_id for item in eligible] == ["assert-active"]


def test_export_includes_object_link_existing_and_relationship_assertions() -> None:
    obj = object_assertion(
        assertion_id="assert-object",
        include_in_gold_eval=True,
        object_ref={
            "ref_kind": "manual_ref",
            "label": "Questionable Company",
            "kind": "party",
        },
    )
    link = link_existing_assertion(
        assertion_id="assert-link",
        include_in_gold_eval=True,
    )
    rel = relationship_assertion(
        assertion_id="assert-rel",
        include_in_gold_eval=True,
    )
    overlay = _overlay(obj, link, rel)

    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(created_at=STAMP),
    )
    assert export is not None
    kinds = {item.assertion_kind for item in export.assertions}
    assert kinds == {"object", "link_existing", "relationship"}


def test_export_preserves_source_anchor_visibility_scope_and_provenance() -> None:
    anchor = _source_anchor()
    visibility = GraphVisibilityPolicy(
        visibility="gm_private",
        reveal_state="unrevealed",
        visible_to_player_ids=[],
        visible_to_character_ids=[],
        visibility_note="test note",
    )
    prov = GraphAuthoringProvenance(
        origin="human_authored",
        authoring_surface="memory_ingest_graph_authoring",
        created_at=STAMP,
        updated_at=STAMP,
        source_run_id="run-123",
        source_graph_id="graph-456",
        source_projection_id="proj-789",
    )
    assertion = object_assertion(
        assertion_id="assert-rich",
        include_in_gold_eval=True,
        source_anchor=anchor.model_dump(),
        visibility=visibility.model_dump(),
        graph_scope=["recap_graph", "campaign_memory_graph"],
        provenance=prov.model_dump(),
        gold_eval_notes="Retrospective party alias",
        object_ref={
            "ref_kind": "manual_ref",
            "label": "Questionable Company",
            "kind": "party",
        },
    )
    overlay = _overlay(assertion)

    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(created_at=STAMP),
    )
    assert export is not None
    exported = export.assertions[0]
    assert exported.assertion_kind == "object"
    assert exported.source_anchor is not None
    assert exported.source_anchor.source_span_ref_id == "span-gang-1"
    assert exported.source_anchor.selected_text_sha256 == hash_text("gang")
    assert exported.visibility.visibility == "gm_private"
    assert exported.visibility.visibility_note == "test note"
    assert exported.graph_scope == ["recap_graph", "campaign_memory_graph"]
    assert exported.provenance.source_run_id == "run-123"
    assert exported.provenance.source_graph_id == "graph-456"
    assert exported.provenance.source_projection_id == "proj-789"
    assert exported.gold_eval_notes == "Retrospective party alias"


def test_export_records_knowledge_scope() -> None:
    assertion = object_assertion(include_in_gold_eval=True)
    overlay = _overlay(assertion)

    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(
            created_at=STAMP,
            knowledge_scope="campaign_retrospective",
        ),
    )
    assert export is not None
    assert export.knowledge_scope == "campaign_retrospective"


def test_export_does_not_mutate_overlay() -> None:
    assertion = object_assertion(include_in_gold_eval=True)
    overlay = _overlay(assertion)
    before = overlay.model_dump(mode="json")
    before_count = len(overlay.assertions)

    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(created_at=STAMP),
    )
    assert export is not None
    assert overlay.model_dump(mode="json") == before
    assert len(overlay.assertions) == before_count
    assert all(not item.include_in_gold_eval or item.status == "authored" for item in overlay.assertions)


def test_write_export_under_graph_authoring_exports(tmp_path: Path) -> None:
    assertion = object_assertion(include_in_gold_eval=True)
    overlay = _overlay(assertion)
    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(
            created_at=STAMP,
            campaign_rel=TEST_CAMPAIGN_REL,
            overlay_path="Test Campaign/A9/_graph_authoring/overlays/authored_graph_overlay.json",
        ),
    )
    assert export is not None

    path = write_authored_graph_gold_eval_export(
        export,
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=tmp_path,
    )
    assert GRAPH_AUTHORING_DIR in path.parts
    assert EXPORTS_DIR in path.parts
    assert path.name.startswith("authored_graph_gold_eval_export.")
    assert path.is_file()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == AUTHORED_GRAPH_GOLD_EVAL_EXPORT_SCHEMA
    assert payload["diagnostics"]["overlay_mutated"] is False
    assert payload["diagnostics"]["candidate_graph_gold_mutated"] is False


def test_no_included_assertions_returns_diagnostic_without_file(tmp_path: Path) -> None:
    overlay = _overlay(object_assertion(include_in_gold_eval=False))
    store = GraphAuthoringOverlayStore(tmp_path)
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    result = export_authored_graph_gold_eval(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=tmp_path,
        created_at=STAMP,
    )
    assert result.exported is False
    assert result.diagnostic_code == "no_gold_eval_assertions"
    assert result.export_path is None
    assert result.export is None

    exports_dir = store.exports_dir(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert not exports_dir.exists() or not any(exports_dir.iterdir())


def test_export_rejects_unsafe_campaign_rel(tmp_path: Path) -> None:
    assertion = object_assertion(include_in_gold_eval=True)
    overlay = _overlay(assertion)
    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(created_at=STAMP),
    )
    assert export is not None

    with pytest.raises(UnsafeCampaignRelError):
        write_authored_graph_gold_eval_export(
            export,
            campaign_id=CAMPAIGN_ID,
            campaign_rel="../outside",
            corpus_root=tmp_path,
        )


def test_export_helper_roundtrip_writes_file(tmp_path: Path) -> None:
    overlay = _overlay(
        object_assertion(
            assertion_id="assert-export",
            include_in_gold_eval=True,
            session_id=SESSION_ID,
        )
    )
    store = GraphAuthoringOverlayStore(tmp_path)
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    result = export_authored_graph_gold_eval(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        session_id=SESSION_ID,
        knowledge_scope="campaign_retrospective",
        corpus_root=tmp_path,
        created_at=STAMP,
        operator_note="manual developer export",
    )
    assert result.exported is True
    assert result.export_path is not None
    assert result.export is not None
    assert result.export.session_id == SESSION_ID
    assert result.export.knowledge_scope == "campaign_retrospective"
    assert result.export.diagnostics.operator_note == "manual developer export"

    payload = json.loads(Path(result.export_path).read_text(encoding="utf-8"))
    assert payload["assertions"][0]["assertion_id"] == "assert-export"


def test_build_returns_none_without_writing_when_no_eligible_assertions() -> None:
    overlay = _overlay(object_assertion(include_in_gold_eval=False))
    export = build_authored_graph_gold_eval_export(
        overlay,
        options=_export_options(created_at=STAMP),
    )
    assert export is None


def test_overlay_deep_copy_unchanged_after_export_helper(tmp_path: Path) -> None:
    overlay = _overlay(object_assertion(include_in_gold_eval=True))
    store = GraphAuthoringOverlayStore(tmp_path)
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    before = copy.deepcopy(store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL))

    export_authored_graph_gold_eval(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=tmp_path,
        created_at=STAMP,
    )

    after = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert after.model_dump(mode="json") == before.model_dump(mode="json")
