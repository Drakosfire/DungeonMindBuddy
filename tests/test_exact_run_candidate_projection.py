from __future__ import annotations
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from fastapi import FastAPI
from apps.live_control_server.services import exact_run_candidate_projection as service
from apps.live_control_server.services.managed_world_graph_projection import (
    VerifiedManagedWorldBinding,
)
from apps.live_control_server.services.graph_run_registry import get_extraction_run
from src.graph_memory.extraction import graph_preview_runner
from tests import test_recap_quote_integrity as fixture


@pytest.fixture
def produced(tmp_path, monkeypatch, application_state_dsn, request):
    from apps.live_control_server.config import ARTIFACT_DATA_ROOT_ENV

    monkeypatch.setenv(ARTIFACT_DATA_ROOT_ENV, str(tmp_path))
    config = getattr(request, "param", {})
    if "text" in config:
        path = tmp_path / "corpus" / "session-29.md"
        path.parent.mkdir(parents=True)
        path.write_bytes(config["text"].encode("utf-8"))
        artifact = fixture.create_recap_source_artifact(
            tmp_path,
            world_id="world:elderwyld",
            campaign_id="longmont-c2",
            session_id="session-29",
            recap_path=path,
        )
        registered, text = fixture.load_registered_source_artifact_text(
            tmp_path, artifact.source_artifact_id
        )
        source = fixture.NormalizedExtractionSource(
            source_artifact_id=registered.source_artifact_id,
            source_domain=str(registered.source_domain),
            source_text=text,
            source_sha256=registered.content_sha256 or "",
            source_uri=registered.uri,
            campaign_id=registered.campaign_id,
            session_id=registered.session_id,
            document_class=registered.document_class,
            source_span_index=fixture.source_span_index_to_dict(
                fixture.build_source_span_index_for_text(
                    source_artifact_id=registered.source_artifact_id,
                    content_sha256=registered.content_sha256 or "",
                    text=text,
                )
            ),
        )
    else:
        source = fixture._admit_recap(tmp_path)

    def extract(options, *, client):
        spans = {
            int(s["start_line"]): s["source_span_id"]
            for s in options.source_span_index["spans"]
        }
        graph = fixture._run_graph(source.source_artifact_id, spans)
        graph["version"] = "0.1"
        graph.pop("source_observations", None)
        graph["nodes"] = graph["nodes"][:1]
        if "labels" in config:
            graph["nodes"] = [
                fixture._node(
                    node_id,
                    label,
                    fixture._ref(
                        source.source_artifact_id,
                        spans[1],
                        config.get("quote", "Frank and Sara live in Mirathorn"),
                    ),
                )
                for node_id, label in config["labels"]
            ]
        for k in ["edges", "beats", "proposed_writes"]:
            graph[k] = []
        private = json.dumps(
            {
                "schema": "dmb_private_extraction_review_bundle_v1",
                "profile": "recap_category_v1@1.0",
                "source_artifact_id": source.source_artifact_id,
                "source_sha256": source.source_sha256,
            }
        )
        return SimpleNamespace(
            candidate_graph=graph,
            consolidation_diagnostics={},
            private_response_evidence=private,
            known_entity_mentions=None,
        )

    monkeypatch.setattr(
        graph_preview_runner, "extract_category_candidate_graph", extract
    )
    result = graph_preview_runner.run_production_extraction(
        graph_preview_runner.ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id="recap_category_v1",
            profile_version="1.0",
            allow_llm=True,
            output_dir=tmp_path / "runs",
            initial_lineage={
                "native_world_id": "world:elderwyld",
                "campaign_id": "longmont-c2",
            },
        )
    )
    run = get_extraction_run(tmp_path, result.run.run_id)
    assert str(run.status) == "reviewable", result.diagnostics
    binding = VerifiedManagedWorldBinding(
        "managed-a", "world:elderwyld", 1, "corpus/managed-a-markdown"
    )
    monkeypatch.setattr(
        service,
        "resolve_managed_world_binding",
        lambda world: (
            binding
            if world == "managed-a"
            else replace(binding, native_world_id="foreign")
        ),
    )
    return tmp_path, source, run


def snapshot(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_actual_production_run_reads_all_local_candidates_without_mutation(
    produced, monkeypatch
):
    root, source, run = produced
    before = snapshot(root)
    from application_state.ingest import service as ingest
    from application_state.source import service as sources

    for owner, name in [
        (ingest, "create_extraction_run"),
        (ingest, "update_extraction_run_status"),
        (sources, "persist_source_markdown"),
    ]:
        if hasattr(owner, name):
            monkeypatch.setattr(
                owner,
                name,
                lambda *a, **k: pytest.fail("reader attempted domain mutation"),
            )
    result = service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")
    assert result.trust_boundary == "unpublished_candidate"
    assert result.run_world_binding_status == "source_only"
    assert result.source_markdown == fixture.SOURCE
    assert len(result.nodes) == 1 and result.mentions_count == 1
    node = result.nodes[0]
    assert node.view_key.startswith(f"candidate:{run.run_id}:")
    assert node.candidate_node_id == "node:frank-sara"
    assert f"dmb-node:{node.view_key}" in result.projected_markdown
    assert result.node_views[node.view_key].role == "unpublished_candidate"
    assert get_extraction_run(root, run.run_id) == run
    assert snapshot(root) == before
    assert not list(root.rglob("promote_seals"))


@pytest.mark.parametrize(
    "component", ["source_artifact", "candidate_graph", "source_span_index"]
)
def test_exact_component_hash_drift_rejected(produced, component):
    root, _, run = produced
    path = root / run.components[component].uri.removeprefix("repo://")
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(service.CandidateProjectionError):
        service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")


def test_foreign_world_rejected(produced):
    root, _, run = produced
    with pytest.raises(service.CandidateProjectionError):
        service.build_exact_run_candidate_projection(root, run.run_id, "foreign")


def test_symlink_component_rejected_even_if_bytes_match(produced):
    root, _, run = produced
    path = root / run.components["candidate_graph"].uri.removeprefix("repo://")
    copy = root / "same-candidate.json"
    copy.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(copy)
    with pytest.raises(service.CandidateProjectionError):
        service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")


def test_canonical_source_outside_ingest_roots_never_sealed(produced, monkeypatch):
    from apps.live_control_server.services.graph_run_registry import (
        create_extraction_run,
        update_extraction_run_status,
    )

    root, source, old = produced
    components = dict(old.components)
    components["source_artifact"] = components["source_artifact"].model_copy(
        update={"uri": source.source_uri}
    )
    run = create_extraction_run(
        root,
        source_artifact_id=old.source_artifact_id,
        source_domain="recap",
        campaign_id=old.campaign_id,
        session_id=old.session_id,
        profile_id=old.profile_id,
        components=components,
        lineage=old.lineage,
    )
    for status in ["prepared", "extracted", "validated", "reviewable"]:
        run = update_extraction_run_status(
            root,
            run.run_id,
            status=fixture.ExtractionRunStatus(status),
            expected_revision=run.revision,
        )
    before = snapshot(root)

    def forbidden(*a, **k):
        pytest.fail("GET attempted a filesystem write")

    for name in ["write_bytes", "write_text", "mkdir", "rename", "replace", "unlink"]:
        monkeypatch.setattr(Path, name, forbidden)
    result = service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")
    assert result.source_markdown == fixture.SOURCE
    assert snapshot(root) == before
    assert not list(root.rglob("promote_seals"))


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_duplicate_normalization_projection_preserves_raw_coordinates(newline):
    head = newline.join(
        [
            "---",
            "title: Session 29",
            "document_class: play",
            "campaign_id: longmont-c2",
            "session: 29",
            "subject_doc_kind: recap",
            "normalization_schema: dmb_recap_normalized_v1",
            "---",
            "# Session 29 Recap",
        ]
    )
    duplicate = " ".join(head.split())
    raw = head + newline * 2 + duplicate + newline * 2 + "Élodie meets Mara." + newline
    projected, segments, diagnostics = service.narrative_segments(
        raw, campaign_id="longmont-c2", session_id="session-29"
    )
    assert projected.startswith("# Session 29 Recap")
    assert duplicate not in projected and "Élodie meets Mara." in projected
    assert "recognized_duplicate_normalization_envelope_hidden" in diagnostics
    start = raw.index("Élodie")
    mapped = service._map_span(start, start + len("Élodie"), segments)
    assert mapped and projected[mapped[0] : mapped[1]] == "Élodie"
    assert (
        service._map_span(
            raw.index("normalization_schema"),
            raw.index("normalization_schema") + 20,
            segments,
        )
        is None
    )
    for segment in segments:
        assert (
            raw[segment.source_start : segment.source_end]
            == projected[segment.display_start : segment.display_end]
        )


@pytest.mark.parametrize(
    "suffix", [" changed-heading", "# extra story", " normalization_schema: story"]
)
def test_near_duplicate_or_story_prefix_never_deleted(suffix):
    head = "---\ndocument_class: play\ncampaign_id: longmont-c2\nsession: 29\nsubject_doc_kind: recap\nnormalization_schema: dmb_recap_normalized_v1\n---\n# Session 29 Recap"
    duplicate = " ".join(head.split()) + suffix
    raw = head + "\n\n" + duplicate + "\n\nMara travels.\n"
    projected, _, _ = service.narrative_segments(
        raw, campaign_id="longmont-c2", session_id="session-29"
    )
    assert duplicate in projected


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?managed_world_id=managed-a&managed_world_id=other",
        "?managed_world_id=managed-a&path=secret",
    ],
)
def test_route_rejects_ambiguous_selectors_before_resolution(monkeypatch, query):
    from apps.live_control_server.routes.graph_preview import router

    app = FastAPI()
    app.include_router(router)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    token = "synthetic-candidate-test-credential-000000"
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    monkeypatch.setattr(
        service,
        "build_exact_run_candidate_projection",
        lambda *a, **k: pytest.fail("invalid selector resolved source"),
    )

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://test",
        ) as client:
            return await client.get(
                "/api/live/graph-preview/extraction-runs/run/candidate-projection"
                + query,
                headers={"Authorization": "Bearer " + token},
            )

    assert asyncio.run(request()).status_code == 422


def test_real_http_auth_and_read_only_exact_run(produced, monkeypatch):
    from apps.live_control_server.routes import graph_preview
    from apps.live_control_server.services.agent_graph_auth import (
        authenticate_native_graph_principal,
        NativeGraphPrincipal,
    )

    root, _, run = produced
    monkeypatch.setattr(graph_preview, "repo_root", lambda: root)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    token = "synthetic-candidate-test-credential-000000"
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    app = FastAPI()
    app.include_router(graph_preview.router)
    url = f"/api/live/graph-preview/extraction-runs/{run.run_id}/candidate-projection?managed_world_id=managed-a"

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://test",
        ) as client:
            assert (await client.get(url)).status_code == 401
            response = await client.get(
                url, headers={"Authorization": "Bearer " + token}
            )
            assert response.status_code == 200, response.text
            assert response.json()["trustBoundary"] == "unpublished_candidate"
            app.dependency_overrides[authenticate_native_graph_principal] = lambda: (
                NativeGraphPrincipal("player", "player", "local_operator")
            )
            assert (await client.get(url)).status_code == 403

    asyncio.run(check())


@pytest.mark.parametrize(
    "produced",
    [
        {
            "labels": [
                ("loc_3", "Frank"),
                ("threat:loc_3", "Sara"),
                ("node:lysandro", "Lysandro"),
                ("node:lysandra", "Lysandra"),
            ]
        }
    ],
    indirect=True,
)
def test_native_looking_ids_remain_local_and_absent_labels_not_guessed(produced):
    root, _, run = produced
    result = service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")
    assert result.mentions_count == 2 and result.unlinked_node_count == 2
    assert {n.candidate_node_id for n in result.nodes} == {
        "loc_3",
        "threat:loc_3",
        "node:lysandro",
        "node:lysandra",
    }
    assert all(
        v.node_id.startswith("candidate:") and v.kind == "candidate"
        for v in result.node_views.values()
    )
    assert all(n.view_key in result.projected_markdown for n in result.nodes[:2])
    assert all(n.view_key not in result.projected_markdown for n in result.nodes[2:])


@pytest.mark.parametrize(
    "produced",
    [
        {
            "labels": [
                ("node:a", "Frank"),
                ("node:b", "Frank"),
                ("node:c", "Frank and Sara"),
            ]
        }
    ],
    indirect=True,
)
def test_duplicate_and_overlapping_labels_stay_plain(produced):
    root, _, run = produced
    result = service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")
    assert result.mentions_count == 0 and result.unlinked_node_count == 3
    assert "ambiguous_candidate_mention_not_linked" in result.diagnostics
    assert "dmb-node:" not in result.projected_markdown


@pytest.mark.parametrize(
    "change",
    [
        {"status": "draft"},
        {"status": "failed"},
        {"profile_id": "gazetteer@1.10"},
        {"campaign_id": "foreign"},
        {"session_id": "session-28"},
        {"lineage": {"native_world_id": "foreign"}},
        {"lineage": {"world_campaign_ingest_context": {}}},
    ],
)
def test_ineligible_or_conflicting_stored_run_never_downgrades_to_source_only(
    produced, monkeypatch, change
):
    root, _, run = produced
    altered = run.model_copy(update=change)
    monkeypatch.setattr(service, "get_extraction_run", lambda *a, **k: altered)
    with pytest.raises(service.CandidateProjectionError):
        service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")


def test_changed_binding_during_capture_rejected(produced, monkeypatch):
    root, _, run = produced
    binding = service.resolve_managed_world_binding("managed-a")
    calls = iter([binding, replace(binding, binding_version=2)])
    monkeypatch.setattr(
        service, "resolve_managed_world_binding", lambda *a: next(calls)
    )
    with pytest.raises(service.CandidateProjectionError):
        service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")


def test_astral_character_codepoint_coordinates_survive_recognized_envelope_cut():
    raw = "---\ndocument_class: play\ncampaign_id: longmont-c2\nsession: 29\nsubject_doc_kind: recap\nnormalization_schema: dmb_recap_normalized_v1\n---\n# Session 29 Recap\n\n😀 Élodie meets Mara.\r\n"
    projected, segments, _ = service.narrative_segments(
        raw, campaign_id="longmont-c2", session_id="session-29"
    )
    start = raw.index("Élodie")
    mapped = service._map_span(start, start + len("Élodie"), segments)
    assert mapped and projected[mapped[0] : mapped[1]] == "Élodie"
    assert raw.endswith("\r\n") and projected.endswith("\r\n")


@pytest.mark.parametrize(
    "produced",
    [
        {
            "text": "😀 Lysandro supplies potions. Lysandra leads. Lysandros is another name.\n\n`Lysandro` and [Lysandro](https://example.com) and ![Lysandro](picture.png).\n",
            "labels": [("node:lysandro", "Lysandro"), ("node:lysandra", "Lysandra")],
            "quote": "Lysandro supplies potions.",
        }
    ],
    indirect=True,
)
def test_distinct_names_prefixes_unicode_and_commonmark_protection(produced):
    root, _, run = produced
    result = service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")
    assert result.mentions_count == 2
    assert "Lysandros is another name." in result.projected_markdown
    assert (
        "`Lysandro` and [Lysandro](https://example.com) and ![Lysandro](picture.png)."
        in result.projected_markdown
    )
    assert result.projected_markdown.startswith("😀 [Lysandro](dmb-node:candidate:")
    assert result.source_markdown.startswith("😀 Lysandro supplies potions.")


@pytest.mark.parametrize(
    "produced",
    [
        {
            "text": "Frank and Sara live in Mirathorn. `Frank` [Sara](https://example.com) ![Sara](picture.png).\n",
            "labels": [("node:frank", "Frank"), ("node:sara", "Sara")],
            "quote": "Frank and Sara live in Mirathorn.",
        }
    ],
    indirect=True,
)
def test_protected_mentions_in_same_verified_paragraph_are_not_rewritten(produced):
    root, _, run = produced
    result = service.build_exact_run_candidate_projection(root, run.run_id, "managed-a")
    assert result.mentions_count == 2
    assert (
        "`Frank` [Sara](https://example.com) ![Sara](picture.png)."
        in result.projected_markdown
    )


def test_real_session_get_is_read_only_without_csrf_and_remote_peer_is_rejected(
    produced, monkeypatch
):
    from apps.live_control_server.routes import graph_preview, agent_graph_local_session

    root, _, run = produced
    monkeypatch.setattr(graph_preview, "repo_root", lambda: root)
    for key, value in {
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "development",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": "synthetic-candidate-session-credential-000000",
        "DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN": "http://127.0.0.1:5202",
        "DMB_AGENT_GRAPH_LOCAL_API_HOST": "127.0.0.1:8000",
        "DMB_AGENT_GRAPH_SESSION_STORE": str(root / "private" / "sessions.json"),
    }.items():
        monkeypatch.setenv(key, value)
    app = FastAPI()
    app.include_router(graph_preview.router)
    app.include_router(agent_graph_local_session.router)
    url = f"/api/live/graph-preview/extraction-runs/{run.run_id}/candidate-projection?managed_world_id=managed-a"

    async def check():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://127.0.0.1:8000",
        ) as client:
            boot = await client.post(
                "/api/live/agent/local-session",
                headers={
                    "Origin": "http://127.0.0.1:5202",
                    "Sec-Fetch-Site": "same-origin",
                },
            )
            assert boot.status_code == 200, boot.text
            before = snapshot(root)
            response = await client.get(url)
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "no-store"
            assert snapshot(root) == before
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=("192.0.2.1", 1234)),
                base_url="http://127.0.0.1:8000",
                cookies=client.cookies,
            ) as remote:
                assert (await remote.get(url)).status_code == 403

    asyncio.run(check())
