"""Offline verification for documented Scope-B perturbation scenarios."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest

from evals.session_recap_ingest_vertical_slice.scope_b_grader import (
    collect_scope_b_recap_ingest_report_extras,
    collect_scope_b_recap_ingest_violations,
)
from evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run import (
    load_scope_b_scenario,
)
from src.agent.planner import PlanningTurnDetail
from src.agent.recap_context import RecapContext, resolve_recap_context
from tests.test_recap_write_output_schema import _valid_payload

_SCENARIO_DIR = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "session_recap_ingest_vertical_slice"
    / "scope_b_scenarios"
)
_CAMPAIGN_HUB = "Longmont Campaign/Campaign 2"
_CAMPAIGN_ID = "longmont-c2"
_TARGET_RECAP_PATH = f"{_CAMPAIGN_HUB}/Session Recaps/Session 20 - Recap.md"


def _scenario_paths() -> list[Path]:
    return sorted(p for p in _SCENARIO_DIR.glob("*.json") if p.is_file())


def _write_recap(
    corpus_root: Path,
    *,
    filename: str,
    session: int,
    campaign_hub: str = _CAMPAIGN_HUB,
    campaign_id: str = _CAMPAIGN_ID,
) -> None:
    title = f"Session {session} - Recap"
    body = textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        document_class: play
        canon_layer: campaign
        campaign_id: {campaign_id}
        temporal_scope: session_specific
        session: {session}
        origin_session: {session}
        last_updated_session: {session}
        source_class: observed_session_recap
        ---
        # {title}

        Body of session {session}.
        """
    )
    recaps_dir = corpus_root / campaign_hub / "Session Recaps"
    recaps_dir.mkdir(parents=True, exist_ok=True)
    (recaps_dir / filename).write_text(body, encoding="utf-8")


def _seed_campaign_2(root: Path) -> None:
    for n in (15, 16, 17, 18, 19):
        _write_recap(root, filename=f"Session {n} - Recap.md", session=n)


def _seed_single_recap_no_prep(root: Path) -> None:
    _write_recap(root, filename="Session 19 - Recap.md", session=19)


def _write_prep(root: Path, *, filename: str, text: str) -> None:
    prep_dir = root / _CAMPAIGN_HUB / "Session Prep"
    prep_dir.mkdir(parents=True, exist_ok=True)
    (prep_dir / filename).write_text(text, encoding="utf-8")


def _seed_for_scenario(root: Path, scenario: dict[str, Any]) -> None:
    setup = scenario.get("perturbation_setup") or {}
    seed_kind = str(setup.get("seed_kind", "campaign_2_happy_path"))
    if seed_kind == "campaign_2_happy_path":
        _seed_campaign_2(root)
    elif seed_kind == "single_recap_no_prep":
        _seed_single_recap_no_prep(root)
    else:
        raise AssertionError(f"unknown seed_kind {seed_kind!r}")

    prep_variant = str(setup.get("prep_variant", "")).strip()
    if prep_variant == "malformed_frontmatter":
        _write_prep(
            root,
            filename="session_20_ref.md",
            text=textwrap.dedent(
                """\
                ---
                title: "Session 20 prep"
                document_class prep
                campaign_id: longmont-c2
                ---
                Prep body with malformed frontmatter.
                """
            ),
        )
    elif prep_variant:
        raise AssertionError(f"unknown prep_variant {prep_variant!r}")
    elif seed_kind == "campaign_2_happy_path":
        _write_prep(root, filename="session_20_ref.md", text="prep")


def _write_raw_notes(root: Path, scenario: dict[str, Any]) -> str:
    rel = str(
        scenario.get("ingest_raw_notes_relpath")
        or "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"
    ).strip()
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Notes.\n", encoding="utf-8")
    return rel


def _final_text_with_recap_field() -> str:
    return json.dumps(
        {
            "user_intent": "status_or_recap_request",
            "message": "Recap drafted; preview ready for review.",
            "unsure_queue": None,
            "recap_write": _valid_payload(),
        }
    )


def _guard_blocked_excerpt(path: str) -> str:
    return (
        f"Error: recap-write skill blocked read_corpus_file for path {path!r}: not in "
        f"recent_recaps ∪ prep_doc_path. Use only paths returned by `get_recap_context`."
    )


def _committed_response() -> dict[str, Any]:
    return {
        "ok": True,
        "phase": "committed",
        "path": _TARGET_RECAP_PATH,
        "mode": "create",
        "bytes_written": 1234,
        "new_corpus_fingerprint": "deadbeef" * 4,
        "fingerprint_reminder": "Corpus changed; new fingerprint = ...",
    }


def _existing_target_rejected_response() -> dict[str, Any]:
    return {
        "ok": False,
        "error": (
            "write_corpus_file create mode refused: target already exists at "
            f"{_TARGET_RECAP_PATH}"
        ),
    }


def _write_row(*, dry_run: bool, response: dict[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "tool": "write_corpus_file",
        "arguments": {
            "path": _TARGET_RECAP_PATH,
            "mode": "create",
            "dry_run": dry_run,
        },
    }
    if response is not None:
        excerpt = json.dumps(response, ensure_ascii=False)
        row["output_excerpt"] = excerpt
        row["output_chars"] = len(excerpt)
    return row


def _build_trace(
    scenario: dict[str, Any],
    snapshot: RecapContext,
    ingest_rel: str,
) -> list[dict[str, Any]]:
    setup = scenario.get("perturbation_setup") or {}
    trace_variant = str(setup.get("trace_variant", "baseline_preview_commit"))
    trace: list[dict[str, Any]] = [{"tool": "get_recap_context", "arguments": {}}]
    for entry in snapshot.recent_recaps:
        trace.append({"tool": "read_corpus_file", "arguments": {"path": entry.path}})
    if snapshot.prep_doc_path:
        trace.append({"tool": "read_corpus_file", "arguments": {"path": snapshot.prep_doc_path}})

    if trace_variant == "guarded_staging_read_then_recover":
        trace.append(
            {
                "tool": "read_corpus_file",
                "arguments": {"path": ingest_rel},
                "output_excerpt": _guard_blocked_excerpt(ingest_rel),
            }
        )

    raw_notes_path = ingest_rel
    if trace_variant == "assemble_raw_notes_path_traversal":
        raw_notes_path = (
            "Longmont Campaign/Campaign 2/_ingest_staging/../private_notes/"
            "session_20_raw_notes.md"
        )

    trace.append(
        {
            "tool": "assemble_recap_draft",
            "arguments": {
                "raw_notes_path": raw_notes_path,
                "target_session": snapshot.target_session,
                "campaign_id": snapshot.campaign_id,
            },
        }
    )

    trace.append(_write_row(dry_run=True))
    if trace_variant == "commit_rejected_existing_target":
        trace.append(
            _write_row(dry_run=False, response=_existing_target_rejected_response())
        )
    else:
        trace.append(_write_row(dry_run=False, response=_committed_response()))
    return trace


def _prepare_detail_and_snapshot(
    tmp_path: Path, scenario: dict[str, Any]
) -> tuple[PlanningTurnDetail, Path, RecapContext]:
    _seed_for_scenario(tmp_path, scenario)
    ingest_rel = _write_raw_notes(tmp_path, scenario)
    snapshot = resolve_recap_context(tmp_path)

    setup = scenario.get("perturbation_setup") or {}
    if setup.get("inject_existing_target_recap_after_snapshot"):
        _write_recap(
            tmp_path,
            filename="Session 20 - Recap.md",
            session=int(snapshot.target_session),
        )

    detail = PlanningTurnDetail(
        final_text=_final_text_with_recap_field(),
        last_response_id="r1",
        tool_trace=_build_trace(scenario, snapshot, ingest_rel),
    )
    return detail, tmp_path, snapshot


def _combined_soft_observations(extras: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in (
        "read_allowlist_soft_observations",
        "write_corpus_file_soft_observations",
    ):
        rows = extras.get(key) or []
        out.extend(str(row) for row in rows)
    return out


def _assert_expected_substrings(messages: list[str], expected: list[str], *, label: str) -> None:
    if not expected:
        assert messages == [], f"Expected no {label}, got {messages!r}"
        return
    joined = "\n".join(messages)
    for needle in expected:
        assert needle in joined, f"Missing {label} substring {needle!r} in {messages!r}"


@pytest.mark.parametrize("scenario_path", _scenario_paths(), ids=lambda p: p.stem)
def test_scope_b_perturbation_scenarios_match_documented_expectations(
    tmp_path: Path, scenario_path: Path
) -> None:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    detail, corpus_root, snapshot = _prepare_detail_and_snapshot(tmp_path, scenario)

    violations = collect_scope_b_recap_ingest_violations(
        scenario,
        detail,
        corpus_root,
        precomputed_recap_context=snapshot,
    )
    extras = collect_scope_b_recap_ingest_report_extras(
        scenario,
        detail,
        corpus_root,
        recap_context_snapshot=snapshot,
    )

    expected = scenario["documented_expectations"]
    gates_passed = not bool(violations)
    tool_trace_gates_passed = not bool(violations.get("scope_b_tool"))
    payload_gates_passed = not bool(violations.get("scope_b_payload"))
    soft = _combined_soft_observations(extras)

    assert gates_passed is expected["gates_passed"]
    assert tool_trace_gates_passed is expected["tool_trace_gates_passed"]
    assert payload_gates_passed is expected["payload_gates_passed"]
    _assert_expected_substrings(
        [str(msg) for msg in violations.get("scope_b_tool", [])],
        [str(msg) for msg in expected.get("scope_b_tool_substrings", [])],
        label="scope_b_tool",
    )
    _assert_expected_substrings(
        [str(msg) for msg in violations.get("scope_b_payload", [])],
        [str(msg) for msg in expected.get("scope_b_payload_substrings", [])],
        label="scope_b_payload",
    )
    _assert_expected_substrings(
        soft,
        [str(msg) for msg in expected.get("soft_observation_substrings", [])],
        label="soft observations",
    )


def test_runner_loads_custom_scope_b_scenario_json() -> None:
    scenario_path = _SCENARIO_DIR / "guarded_staging_read_recovery.json"
    scenario = load_scope_b_scenario(scenario_path)
    assert scenario["scenario_id"] == "scope_b_perturbation_guarded_staging_read_recovery"
