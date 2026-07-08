from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionIdentityRedirect
from graph_memory.union_supergraph.redirects import (
    active_identity_redirect_map,
    collect_redirect_diagnostics,
    is_redirected_node_id,
    redirect_chain,
    resolve_union_node_id,
    validate_identity_redirects,
)
from graph_memory.union_supergraph.validate import (
    UnionSupergraphValidationError,
    validate_union_supergraph_fixture,
)


def _redirect(
    *,
    redirect_id: str,
    from_node_id: str,
    to_node_id: str,
    status: str = "active",
) -> UnionIdentityRedirect:
    return UnionIdentityRedirect(
        redirect_id=redirect_id,
        campaign_id="longmont-c2",
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        assertion_id=f"assertion:{redirect_id}",
        created_at="2026-07-08T00:00:00Z",
        status=status,  # type: ignore[arg-type]
        materialization_pass_id="pass:test",
    )


@pytest.fixture
def fixture() -> dict:
    return load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)


def test_store_loads_empty_identity_redirects_by_default(fixture: dict) -> None:
    store = parse_union_supergraph_store(fixture)

    assert store.identity_redirects == []


def test_store_loads_identity_redirects_when_present(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["identity_redirects"] = [
        {
            "redirect_id": "redirect:lysandra",
            "campaign_id": "longmont-c2",
            "from_node_id": "node:lysandra",
            "to_node_id": "party:captain_lysandra_ironveil",
            "assertion_id": "assertion:merge:lysandra",
            "event_id": "event:merge:lysandra",
            "merge_reason": "Same character across party anchor and ingest node",
            "created_at": "2026-07-08T00:00:00Z",
            "status": "active",
            "materialization_pass_id": "pass:2026-07-08",
        }
    ]

    store = parse_union_supergraph_store(payload)

    assert len(store.identity_redirects) == 1
    redirect = store.identity_redirects[0]
    assert redirect.from_node_id == "node:lysandra"
    assert redirect.to_node_id == "party:captain_lysandra_ironveil"


def test_direct_redirect_resolves() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra",
            from_node_id="node:lysandra",
            to_node_id="party:captain_lysandra_ironveil",
        )
    ]

    assert (
        resolve_union_node_id("node:lysandra", redirects)
        == "party:captain_lysandra_ironveil"
    )


def test_no_redirect_returns_original() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra",
            from_node_id="node:lysandra",
            to_node_id="party:captain_lysandra_ironveil",
        )
    ]

    assert resolve_union_node_id("location:mireward", redirects) == "location:mireward"


def test_retracted_redirect_is_ignored() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra",
            from_node_id="node:lysandra",
            to_node_id="party:captain_lysandra_ironveil",
            status="retracted",
        )
    ]

    assert resolve_union_node_id("node:lysandra", redirects) == "node:lysandra"


def test_transitive_redirect_resolves_to_final_survivor() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra:legacy",
            from_node_id="node:lysandra",
            to_node_id="character_lysandra",
        ),
        _redirect(
            redirect_id="redirect:lysandra:party",
            from_node_id="character_lysandra",
            to_node_id="party:captain_lysandra_ironveil",
        ),
    ]

    assert (
        resolve_union_node_id("node:lysandra", redirects)
        == "party:captain_lysandra_ironveil"
    )


def test_cycle_safe_resolution_returns_original_node_id() -> None:
    redirects = [
        _redirect(redirect_id="redirect:a", from_node_id="a", to_node_id="b"),
        _redirect(redirect_id="redirect:b", from_node_id="b", to_node_id="a"),
    ]

    assert resolve_union_node_id("a", redirects) == "a"
    assert resolve_union_node_id("b", redirects) == "b"


def test_active_identity_redirect_map_ignores_retracted() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra",
            from_node_id="node:lysandra",
            to_node_id="party:captain_lysandra_ironveil",
            status="retracted",
        )
    ]

    assert active_identity_redirect_map(redirects) == {}


def test_redirect_chain_reports_transitive_path() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra:legacy",
            from_node_id="node:lysandra",
            to_node_id="character_lysandra",
        ),
        _redirect(
            redirect_id="redirect:lysandra:party",
            from_node_id="character_lysandra",
            to_node_id="party:captain_lysandra_ironveil",
        ),
    ]

    assert redirect_chain("node:lysandra", redirects) == [
        "node:lysandra",
        "character_lysandra",
        "party:captain_lysandra_ironveil",
    ]


def test_is_redirected_node_id() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra",
            from_node_id="node:lysandra",
            to_node_id="party:captain_lysandra_ironveil",
        )
    ]

    assert is_redirected_node_id("node:lysandra", redirects) is True
    assert is_redirected_node_id("location:mireward", redirects) is False


def test_duplicate_active_redirect_conflict_is_reported() -> None:
    redirects = [
        _redirect(
            redirect_id="redirect:lysandra:party",
            from_node_id="node:lysandra",
            to_node_id="party:captain_lysandra_ironveil",
        ),
        _redirect(
            redirect_id="redirect:lysandra:character",
            from_node_id="node:lysandra",
            to_node_id="character_lysandra",
        ),
    ]

    diagnostics = collect_redirect_diagnostics(redirects)
    assert any(item["kind"] == "duplicate_active_from_node_id" for item in diagnostics)
    assert validate_identity_redirects(redirects)


def test_self_redirect_rejected_by_model() -> None:
    with pytest.raises(ValidationError, match="from_node_id and to_node_id must differ"):
        _redirect(
            redirect_id="redirect:self",
            from_node_id="node:lysandra",
            to_node_id="node:lysandra",
        )


def test_fixture_validation_rejects_duplicate_active_redirects(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["identity_redirects"] = [
        {
            "redirect_id": "redirect:lysandra:party",
            "campaign_id": "longmont-c2",
            "from_node_id": "node:lysandra",
            "to_node_id": "party:captain_lysandra_ironveil",
            "assertion_id": "assertion:merge:lysandra:party",
            "created_at": "2026-07-08T00:00:00Z",
            "status": "active",
            "materialization_pass_id": "pass:2026-07-08",
        },
        {
            "redirect_id": "redirect:lysandra:character",
            "campaign_id": "longmont-c2",
            "from_node_id": "node:lysandra",
            "to_node_id": "character_lysandra",
            "assertion_id": "assertion:merge:lysandra:character",
            "created_at": "2026-07-08T00:00:00Z",
            "status": "active",
            "materialization_pass_id": "pass:2026-07-08",
        },
    ]

    with pytest.raises(UnionSupergraphValidationError, match="multiple active identity redirects"):
        validate_union_supergraph_fixture(payload)
