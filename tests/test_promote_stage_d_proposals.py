"""Offline tests for ``scripts.promote_stage_d_proposals``.

Pure offline — no OpenAI calls. Uses synthetic per-run sidecars + a synthetic
cohort proposals file written to ``tmp_path`` plus a synthetic registry that
provokes one slug-collision flag.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.promote_stage_d_proposals import (  # noqa: E402
    aggregate_sources,
    collision_flags_for_alias,
    collision_flags_for_slug,
    run_promotion,
)
from src.contracts.npc_registry import NpcRegistryRecord  # noqa: E402


def _write_per_run_sidecar(
    path: Path,
    *,
    scenario_id: str,
    proposed: list[dict],
    aliases: list[dict] | None = None,
    unresolvable: list[dict] | None = None,
) -> Path:
    payload = {
        "schema": "stage_d_run_report_v1",
        "iso_utc": "2026-04-22T23:35:36Z",
        "scenario_id": scenario_id,
        "runner_version": "stage_d_runner_v0_deterministic",
        "stage_d_output": {
            "resolved_entities": [],
            "proposed_aliases": aliases or [],
            "proposed_new_records": proposed,
            "unresolvable": unresolvable or [],
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_cohort_proposals(
    path: Path,
    *,
    scenario_id: str,
    proposed: list[dict],
    aliases: list[dict] | None = None,
    unresolvable: list[dict] | None = None,
) -> Path:
    payload = {
        "schema": "stage_d_cohort_proposals_v1",
        "generated_at": "2026-04-22T23:35:36+00:00",
        "campaign_id": "synthetic",
        "scenario_id": scenario_id,
        "runner_version": "stage_d_runner_v0_deterministic",
        "source_run_count": 1,
        "proposed_records": proposed,
        "proposed_aliases": aliases or [],
        "unresolvable": unresolvable or [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_synthetic_registry(path: Path, records: list[dict]) -> Path:
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return path


def _foo_record(session: int) -> dict:
    return {
        "slug": "foo",
        "display_name": "Foo",
        "aliases": [],
        "status": "candidate",
        "first_session": session,
        "last_session": session,
        "hub_path": None,
        "setting_hub_path": None,
        "notes": (
            f"Proposed by Stage D deterministic v0; descriptor 'Foo'; "
            f"evidence event indices [{session}]."
        ),
    }


def _bar_record(session: int) -> dict:
    return {
        "slug": "bar",
        "display_name": "Bar",
        "aliases": [],
        "status": "candidate",
        "first_session": session,
        "last_session": session,
        "hub_path": None,
        "setting_hub_path": None,
        "notes": (
            f"Proposed by Stage D deterministic v0; descriptor 'Bar'; "
            f"evidence event indices [0]."
        ),
    }


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #


def test_aggregate_cross_source_min_max_session(tmp_path: Path) -> None:
    """foo seen in per-run (session 1) AND cohort (session 3) → first=1 last=3, 2 evidence rows."""
    per_run = _write_per_run_sidecar(
        tmp_path / "stage_d--scenario_session1--PASS--A.json",
        scenario_id="stage_d_live_from_c_session1",
        proposed=[_foo_record(1)],
    )
    cohort = _write_cohort_proposals(
        tmp_path / "campaign_stage_d_proposals_T1.json",
        scenario_id="stage_d_live_from_c_session3",
        proposed=[_foo_record(3), _bar_record(3)],
    )

    result = aggregate_sources(cohort_paths=[cohort], per_run_paths=[per_run])

    assert set(result.new_records.keys()) == {"foo", "bar"}
    foo = result.new_records["foo"]
    assert foo.first_session == 1
    assert foo.last_session == 3
    assert foo.appearance_runs == 2
    assert sorted(foo.session_appearances) == [1, 3]
    assert len(foo.evidence) == 2
    bar = result.new_records["bar"]
    assert bar.first_session == 3
    assert bar.appearance_runs == 1


def test_aggregate_extracts_descriptors_and_event_indices(tmp_path: Path) -> None:
    cohort = _write_cohort_proposals(
        tmp_path / "campaign_stage_d_proposals_T2.json",
        scenario_id="stage_d_session5",
        proposed=[
            {
                **_foo_record(5),
                "notes": (
                    "Proposed by Stage D deterministic v0; descriptor 'Foo the Mighty'; "
                    "evidence event indices [2, 4, 7]."
                ),
            }
        ],
    )
    result = aggregate_sources(cohort_paths=[cohort], per_run_paths=[])
    foo = result.new_records["foo"]
    assert foo.evidence[0].descriptors_seen == ["Foo the Mighty"]
    assert foo.evidence[0].evidence_event_indices == [2, 4, 7]
    assert foo.evidence[0].session_number == 5


def test_aggregate_ingests_aliases_and_unresolvable(tmp_path: Path) -> None:
    per_run = _write_per_run_sidecar(
        tmp_path / "stage_d--session2--PASS--A.json",
        scenario_id="stage_d_session2",
        proposed=[],
        aliases=[
            {"target_slug": "captain_lysandra_ironveil", "alias_text": "the captain"}
        ],
        unresolvable=[
            {
                "source_kind": "unresolved_descriptor",
                "source_index": 0,
                "descriptor": "mysterious cat owl",
                "reason": "generic",
            }
        ],
    )
    result = aggregate_sources(cohort_paths=[], per_run_paths=[per_run])
    assert ("captain_lysandra_ironveil", "the captain") in result.aliases
    assert "mysterious cat owl" in result.unresolvables
    assert result.aliases[
        ("captain_lysandra_ironveil", "the captain")
    ].appearance_runs == 1


# --------------------------------------------------------------------------- #
# collision detection
# --------------------------------------------------------------------------- #


def _registry(records: list[dict]) -> list[NpcRegistryRecord]:
    return [NpcRegistryRecord.model_validate(r) for r in records]


def test_collision_detects_existing_slug() -> None:
    reg = _registry(
        [
            {
                "slug": "foo",
                "display_name": "Foo",
                "aliases": [],
                "status": "candidate",
                "first_session": 1,
                "last_session": 1,
                "hub_path": None,
                "setting_hub_path": None,
                "notes": "",
            }
        ]
    )
    flags = collision_flags_for_slug(
        slug="foo",
        display_name="Foo",
        aliases=[],
        registry=reg,
        pc_slugs={"bonogo"},
    )
    assert flags["slug_collision"] is True
    assert flags["pc_collision"] is False


def test_collision_detects_display_name_overlap() -> None:
    reg = _registry(
        [
            {
                "slug": "captain_lysandra_ironveil",
                "display_name": "Captain Lysandra Ironveil",
                "aliases": ["Lysandra", "the captain"],
                "status": "tracked",
                "first_session": 1,
                "last_session": 5,
                "hub_path": "Foo/captain_lysandra_ironveil/",
                "setting_hub_path": None,
                "notes": "",
            }
        ]
    )
    flags = collision_flags_for_slug(
        slug="lysandra_alias_proposal",
        display_name="Lysandra",
        aliases=[],
        registry=reg,
        pc_slugs=set(),
    )
    assert flags["slug_collision"] is False
    assert flags["display_name_overlap"] == "captain_lysandra_ironveil"


def test_collision_detects_pc_slug() -> None:
    flags = collision_flags_for_slug(
        slug="bonogo",
        display_name="Bonogo",
        aliases=[],
        registry=[],
        pc_slugs={"bonogo"},
    )
    assert flags["pc_collision"] is True


def test_alias_collision_detects_already_present() -> None:
    reg = _registry(
        [
            {
                "slug": "captain_lysandra_ironveil",
                "display_name": "Captain Lysandra Ironveil",
                "aliases": ["Lysandra", "the captain"],
                "status": "tracked",
                "first_session": 1,
                "last_session": 5,
                "hub_path": "Foo/captain_lysandra_ironveil/",
                "setting_hub_path": None,
                "notes": "",
            }
        ]
    )
    flags = collision_flags_for_alias(
        target_slug="captain_lysandra_ironveil",
        alias_text="the captain",
        registry=reg,
    )
    assert flags["target_exists"] is True
    assert flags["alias_already_present"] is True


# --------------------------------------------------------------------------- #
# end-to-end (no-llm)
# --------------------------------------------------------------------------- #


def test_no_llm_run_writes_deterministic_only_sidecar(tmp_path: Path) -> None:
    """``--no-llm`` mode emits null recommendations + recommendation_source='deterministic_only'."""
    per_run = _write_per_run_sidecar(
        tmp_path / "stage_d--session1--PASS--A.json",
        scenario_id="stage_d_session1",
        proposed=[_foo_record(1)],
    )
    cohort = _write_cohort_proposals(
        tmp_path / "synthetic_stage_d_proposals_T.json",
        scenario_id="stage_d_session3",
        proposed=[_foo_record(3), _bar_record(3)],
        aliases=[
            {"target_slug": "existing", "alias_text": "Existing One"}
        ],
        unresolvable=[
            {"descriptor": "the elderly fisherman", "reason": "generic"}
        ],
    )
    registry_path = _write_synthetic_registry(
        tmp_path / "_npc_registry.json",
        [
            {
                "slug": "existing",
                "display_name": "Existing",
                "aliases": ["Existing One"],
                "status": "tracked",
                "first_session": 1,
                "last_session": 5,
                "hub_path": "Foo/existing/",
                "setting_hub_path": None,
                "notes": "",
            },
            {
                "slug": "foo",
                "display_name": "Foo",
                "aliases": [],
                "status": "candidate",
                "first_session": 1,
                "last_session": 1,
                "hub_path": None,
                "setting_hub_path": None,
                "notes": "",
            },
        ],
    )
    out_dir = tmp_path / "promotions"

    result = run_promotion(
        campaign_id="synthetic-c1",
        proposals_pattern=str(cohort),
        per_run_pattern=str(per_run),
        registry_path=registry_path,
        out_dir=out_dir,
        use_llm=False,
        quiet=True,
        when=datetime(2026, 4, 22, 23, 35, 36, tzinfo=timezone.utc),
    )

    assert result["json_path"].exists()
    assert result["md_path"].exists()
    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))

    assert payload["llm_enabled"] is False
    assert payload["model_id"] is None
    assert payload["cost"]["calls"] == 0

    new_rows = {row["slug"]: row for row in payload["proposed_new_records"]}
    assert set(new_rows.keys()) == {"foo", "bar"}

    foo_row = new_rows["foo"]
    assert foo_row["recommendation"] is None
    assert foo_row["recommendation_source"] == "deterministic_only"
    assert foo_row["registry_collision_flags"]["slug_collision"] is True
    assert foo_row["first_session"] == 1
    assert foo_row["last_session"] == 3

    bar_row = new_rows["bar"]
    assert bar_row["registry_collision_flags"]["slug_collision"] is False

    alias_rows = payload["proposed_aliases"]
    assert len(alias_rows) == 1
    assert alias_rows[0]["recommendation"] is None
    assert alias_rows[0]["recommendation_source"] == "deterministic_only"
    assert alias_rows[0]["registry_flags"]["target_exists"] is True
    assert alias_rows[0]["registry_flags"]["alias_already_present"] is True

    unres_rows = payload["unresolvable"]
    assert len(unres_rows) == 1
    assert unres_rows[0]["recommendation"] is None
    assert unres_rows[0]["recommendation_source"] == "deterministic_only"


def test_no_llm_does_not_call_openai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity check: ``--no-llm`` must not import / call openai."""
    per_run = _write_per_run_sidecar(
        tmp_path / "stage_d--session1--PASS--A.json",
        scenario_id="stage_d_session1",
        proposed=[_foo_record(1)],
    )
    registry_path = _write_synthetic_registry(tmp_path / "_npc_registry.json", [])

    sentinel = {"called": False}

    def _explode(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        sentinel["called"] = True
        raise AssertionError("openai client was built in --no-llm mode")

    monkeypatch.setattr(
        "scripts.promote_stage_d_proposals._build_openai_client", _explode
    )

    run_promotion(
        campaign_id="synthetic-c1",
        proposals_pattern="",
        per_run_pattern=str(per_run),
        registry_path=registry_path,
        out_dir=tmp_path / "promotions",
        use_llm=False,
        quiet=True,
        when=datetime(2026, 4, 22, 23, 35, 36, tzinfo=timezone.utc),
    )

    assert sentinel["called"] is False


def test_run_promotion_errors_when_no_sources_match(tmp_path: Path) -> None:
    registry_path = _write_synthetic_registry(tmp_path / "_npc_registry.json", [])
    with pytest.raises(ValueError, match="no proposals or per-run sidecars"):
        run_promotion(
            campaign_id="synthetic",
            proposals_pattern="evals/no/such/path/*.json",
            per_run_pattern="evals/no/such/path/*.json",
            registry_path=registry_path,
            out_dir=tmp_path / "promotions",
            use_llm=False,
            quiet=True,
        )
