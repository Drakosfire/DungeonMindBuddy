"""TL01F registry, proposition-type lane prompt, and freeze tests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from graph_memory.temporal_shadow_extraction import (
    FakeTemporalShadowExtractionClient,
    TL01B_PACKET_VERSION,
    TL01C_PACKET_VERSION,
    TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS,
    TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS,
    build_assertion_evidence_packets,
    compute_prompt_sha256,
    load_temporal_shadow_extraction_case,
    render_temporal_shadow_user_content_v2,
    resolve_prompt_spec,
    run_temporal_shadow_extraction,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

FROZEN_TL01E_PROMPT_SHA256 = (
    "8373cb2d40e532c648faff88064d95b0e862dfe947e9a0c80e72183bf48a7d4c"
)
# Frozen after TL01F candidate freeze — do NOT recompute from live instructions.
FROZEN_TL01F_PROMPT_SHA256 = (
    "7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143"
)

TL01F_RESERVED_VOCABULARY = (
    "Quenvar",
    "Seldric",
    "Thayle",
    "Moonpier Bridge",
    "Embercourt Synod",
    "Verdant Codex",
)

FORBIDDEN_PRIOR_FEWSHOT_AND_COHORT_TERMS = (
    "Ivara",
    "Kelren",
    "Mothe",
    "Starfall Viaduct",
    "Brasswater Council",
    "Cobalt Register",
    "Dessa",
    "Orun",
    "Caldrin",
    "Glass Causeway",
    "Lantern Court",
    "Ivory Ledger",
    "Rhelan",
    "Vosk",
    "Nyeth",
    "Ashglass Span",
    "Tideglass Synod",
    "Azure Index",
    "Jorin",
    "Pella",
    "Tovin",
    "Quill Harbor",
    "Ash Riders",
    "frost seal",
    "Nerys",
    "Bram",
    "Vell",
    "Saltspan Quay",
    "ember lock",
    "Pale Wardens",
    "Corin Vale",
    "Orik Tane",
    "Seraphine Bladewind",
    "Glimmering Globe",
)

REQUIRED_PROMPT_PHRASES = (
    "Identify the assertion proposition BEFORE selecting any temporal lane",
    "Classify proposition type into exactly one class BEFORE inspecting source_context.source_time",
    "Event or transition proposition",
    "Persistent-state proposition with an explicit start boundary",
    "Persistent-state proposition with an explicit end boundary",
    "Persistent-state observation or restatement without a new boundary",
    "Non-temporal identity, classification, containment, or structure",
    "Do NOT emit occurrence_time merely because the boundary is expressed with an eventive phrase",
    "A persistent-state start or end never appears only as occurrence_time",
    "source_context.source_time (provenance_only)",
    "Never copy source_time merely because it is available",
    "Every annotation MUST contain diagnostics with at least one nonblank string",
    "occurrence_time MUST be null AND valid_time MUST be null",
    "kind=textual",
    "raw_expression must be a verbatim contiguous substring",
)

DEV_TL01E_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01e.json"
)


def test_tl01f_resolves_through_registry_with_packet_and_renderer_v2() -> None:
    spec = resolve_prompt_spec("tl01f-v1")
    assert spec.version == "tl01f-v1"
    assert spec.packet_version == TL01C_PACKET_VERSION
    assert spec.packet_version != TL01B_PACKET_VERSION
    assert spec.render_user_content is render_temporal_shadow_user_content_v2
    assert spec.instructions == TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS


def test_tl01f_prompt_hash_is_frozen() -> None:
    assert compute_prompt_sha256("tl01f-v1") == FROZEN_TL01F_PROMPT_SHA256


def test_tl01e_control_hash_remains_frozen() -> None:
    assert compute_prompt_sha256("tl01e-v1") == FROZEN_TL01E_PROMPT_SHA256
    assert resolve_prompt_spec("tl01e-v1").instructions == TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS


def test_tl01f_instructions_contain_required_gates() -> None:
    text = TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS
    for phrase in REQUIRED_PROMPT_PHRASES:
        assert phrase in text, f"missing required phrase: {phrase!r}"


def test_tl01f_few_shots_have_exactly_one_expected_answer_each() -> None:
    text = TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS
    examples = re.findall(
        r"Example \d+ — .*?:\n(?:.*\n)*?→ ([^\n]+)",
        text,
    )
    assert len(examples) == 8
    ambiguous_answer_markers = (
        "not_applicable or",
        "resolved or",
        "ambiguous or",
        "unresolved or",
        "relative or",
        "textual or",
        " / ",
    )
    for answer in examples:
        lowered = answer.lower()
        assert not any(marker in lowered for marker in ambiguous_answer_markers), answer
        assert (
            "null" in lowered
            or "resolved" in lowered
            or "not_applicable" in lowered
            or "ambiguous" in lowered
        )


def test_tl01f_few_shots_use_reserved_vocabulary() -> None:
    text = TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS
    for term in TL01F_RESERVED_VOCABULARY:
        assert term in text


def test_tl01f_few_shots_exclude_prior_prompt_and_observed_terms() -> None:
    text = TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS
    for term in FORBIDDEN_PRIOR_FEWSHOT_AND_COHORT_TERMS:
        assert term not in text, f"tl01f few-shot contaminated by {term!r}"


def test_tl01f_reserved_vocabulary_absent_from_existing_cohorts() -> None:
    examples = REPO_ROOT / "evals/graph_memory_layer/examples"
    for path in examples.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for term in TL01F_RESERVED_VOCABULARY:
            assert not re.search(
                rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])",
                text,
            ), f"{term!r} found in existing cohort {path}"


def test_tl01e_and_tl01f_rendered_user_content_are_byte_identical() -> None:
    case = load_temporal_shadow_extraction_case(DEV_TL01E_CASE, repo_root=REPO_ROOT)
    from graph_memory.kernel.contribution_models import GraphContribution

    contribution = GraphContribution.model_validate(
        json.loads((REPO_ROOT / case.base_contribution_path).read_text(encoding="utf-8"))
    )
    packets = build_assertion_evidence_packets(
        contribution,
        case,
        repo_root=REPO_ROOT,
        packet_version=TL01C_PACKET_VERSION,
    )
    tl01e = resolve_prompt_spec("tl01e-v1")
    tl01f = resolve_prompt_spec("tl01f-v1")
    rendered_e = tl01e.render_user_content(packets, case.selected_assertion_ids)
    rendered_f = tl01f.render_user_content(packets, case.selected_assertion_ids)
    assert rendered_e == rendered_f
    assert hashlib.sha256(rendered_e.encode("utf-8")).hexdigest() == hashlib.sha256(
        rendered_f.encode("utf-8")
    ).hexdigest()


def test_unknown_prompt_version_still_fails_closed(tmp_path: Path) -> None:
    case_payload = json.loads(DEV_TL01E_CASE.read_text(encoding="utf-8"))
    case_payload["prompt_version"] = "tl01z-v9"
    case_payload["case_id"] = "tl01z-bad"
    bad_case = tmp_path / "bad-case.json"
    bad_case.write_text(json.dumps(case_payload), encoding="utf-8")

    class ExplodingClient(FakeTemporalShadowExtractionClient):
        def extract_annotations(self, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("provider must not be called")

    with pytest.raises(Exception) as excinfo:
        # load fails closed before provider when prompt_version is unsupported
        load_temporal_shadow_extraction_case(bad_case, repo_root=REPO_ROOT)
        run_temporal_shadow_extraction(
            case_path=bad_case,
            output_dir=tmp_path / "out",
            model_id="gpt-5.4-mini",
            client=ExplodingClient(),
            repo_root=REPO_ROOT,
        )
    message = str(excinfo.value).lower()
    assert "unsupported" in message or "prompt_version" in message


def _collect_ids(folder: Path) -> tuple[set[str], set[str]]:
    assertion_ids: set[str] = set()
    evidence_ids: set[str] = set()
    base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
    for assertion in base.get("candidate_assertions", []):
        assertion_ids.add(assertion["assertion_id"])
        evidence_ids.update(assertion.get("evidence_ref_ids", []))
    case_path = folder / "temporal-case-tl01f.json"
    if not case_path.is_file():
        case_path = folder / "temporal-case-tl01e.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    for entry in case.get("evidence_registry", []):
        evidence_ids.add(entry["evidence_ref_id"])
    return assertion_ids, evidence_ids


HOLDOUT_V6 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v6"
HOLDOUT_V7 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v7"
ADV_V5 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5"

PRIOR_COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_cohort",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v4",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v5",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v4",
)

# Prior dirs for adversarial V5 independence (excludes V6/V7, which are later).
ADV_V5_PRIOR_COHORT_DIRS = PRIOR_COHORT_DIRS

# Prior dirs for holdout V7 independence include sealed retired V6.
HOLDOUT_V7_PRIOR_COHORT_DIRS = (
    *PRIOR_COHORT_DIRS,
    HOLDOUT_V6,
    ADV_V5,
)

ADV_V5_VOCABULARY = (
    "Corveth",
    "Ysanna",
    "Pelloric",
    "Driftglass Causeway",
    "Amber Ledger Hall",
    "Nightspine Order",
)


def _union_ids(folders: tuple[Path, ...]) -> tuple[set[str], set[str]]:
    assertions: set[str] = set()
    evidence: set[str] = set()
    for folder in folders:
        a_ids, e_ids = _collect_ids(folder)
        assertions |= a_ids
        evidence |= e_ids
    return assertions, evidence


def _folder_text(folder: Path) -> str:
    chunks: list[str] = []
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md"}:
            chunks.append(path.read_text(encoding="utf-8"))
    return "".join(chunks)


def test_holdout_v6_retired_fixture_files_remain_sealed() -> None:
    for name in (
        "README.md",
        "GOLD-AUDIT.md",
        "base-contribution.json",
        "gold-overlay.json",
        "temporal-case-tl01e.json",
        "temporal-case-tl01f.json",
    ):
        assert (HOLDOUT_V6 / name).is_file(), name
    readme = (HOLDOUT_V6 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as TL01F promotion evidence" in readme
    tl01e = json.loads((HOLDOUT_V6 / "temporal-case-tl01e.json").read_text(encoding="utf-8"))
    tl01f = json.loads((HOLDOUT_V6 / "temporal-case-tl01f.json").read_text(encoding="utf-8"))
    assert tl01e["prompt_version"] == "tl01e-v1"
    assert tl01f["prompt_version"] == "tl01f-v1"
    assert len(tl01f["selected_assertion_ids"]) >= 8


def test_holdout_v7_fixture_files_and_prompt_versions() -> None:
    for name in (
        "README.md",
        "GOLD-AUDIT.md",
        "base-contribution.json",
        "gold-overlay.json",
        "temporal-case-tl01e.json",
        "temporal-case-tl01f.json",
    ):
        assert (HOLDOUT_V7 / name).is_file(), name
    tl01e = json.loads((HOLDOUT_V7 / "temporal-case-tl01e.json").read_text(encoding="utf-8"))
    tl01f = json.loads((HOLDOUT_V7 / "temporal-case-tl01f.json").read_text(encoding="utf-8"))
    assert tl01e["prompt_version"] == "tl01e-v1"
    assert tl01f["prompt_version"] == "tl01f-v1"
    assert len(tl01f["selected_assertion_ids"]) >= 8


def test_v6_v7_and_adv5_control_candidate_cases_are_exact_mirrors() -> None:
    from evals.graph_memory_layer.temporal_shadow_prompt_calibration import (
        validate_paired_case_equivalence,
    )

    for folder_name in (
        "temporal_shadow_holdout_v6",
        "temporal_shadow_holdout_v7",
        "temporal_shadow_adversarial_v5",
    ):
        folder = REPO_ROOT / "evals/graph_memory_layer/examples" / folder_name
        validate_paired_case_equivalence(
            baseline_case_path=folder / "temporal-case-tl01e.json",
            candidate_case_path=folder / "temporal-case-tl01f.json",
            repo_root=REPO_ROOT,
            pair_name=folder_name,
        )


def test_holdout_v6_ids_disjoint_from_prior_cohorts() -> None:
    new_a, new_e = _collect_ids(HOLDOUT_V6)
    prior_a, prior_e = _union_ids(PRIOR_COHORT_DIRS)
    assert new_a.isdisjoint(prior_a)
    assert new_e.isdisjoint(prior_e)


def test_adversarial_v5_ids_disjoint_from_prior_cohorts() -> None:
    adv_assertions, adv_evidence = _collect_ids(ADV_V5)
    prior_assertions, prior_evidence = _union_ids(ADV_V5_PRIOR_COHORT_DIRS)
    assert adv_assertions.isdisjoint(prior_assertions)
    assert adv_evidence.isdisjoint(prior_evidence)


def test_holdout_v6_ids_disjoint_from_adversarial_v5() -> None:
    v6_a, v6_e = _collect_ids(HOLDOUT_V6)
    adv_a, adv_e = _collect_ids(ADV_V5)
    assert v6_a.isdisjoint(adv_a)
    assert v6_e.isdisjoint(adv_e)


def test_holdout_v7_ids_disjoint_from_prior_cohorts_including_v6_and_adv_v5() -> None:
    new_a, new_e = _collect_ids(HOLDOUT_V7)
    prior_a, prior_e = _union_ids(HOLDOUT_V7_PRIOR_COHORT_DIRS)
    assert new_a.isdisjoint(prior_a)
    assert new_e.isdisjoint(prior_e)


def test_adversarial_v5_vocabulary_disjoint_from_prompt_prior_cohorts_and_holdouts() -> None:
    prompt = TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS
    for term in ADV_V5_VOCABULARY:
        assert term not in prompt
    prior_text = "".join(_folder_text(folder) for folder in PRIOR_COHORT_DIRS)
    holdout_v6_text = _folder_text(HOLDOUT_V6)
    holdout_v7_text = _folder_text(HOLDOUT_V7)
    for term in ADV_V5_VOCABULARY:
        assert term not in prior_text
        assert term not in holdout_v6_text
        assert term not in holdout_v7_text


def test_holdout_v7_promotion_gold_covers_required_lane_classes() -> None:
    gold = json.loads((HOLDOUT_V7 / "gold-overlay.json").read_text(encoding="utf-8"))
    anns = gold["annotations"]
    assert len(anns) >= 8

    def has_occurrence(ann: dict) -> bool:
        return ann.get("occurrence_time") is not None

    def has_valid_start(ann: dict) -> bool:
        vt = ann.get("valid_time") or {}
        return vt.get("start") is not None and vt.get("end") is None

    def has_valid_end(ann: dict) -> bool:
        vt = ann.get("valid_time") or {}
        return vt.get("end") is not None and vt.get("start") is None

    assert any(
        a["interpretation_status"] == "resolved" and has_occurrence(a) and a["valid_time"] is None
        for a in anns
    )
    assert any(
        a["interpretation_status"] == "resolved" and has_valid_start(a) and a["occurrence_time"] is None
        for a in anns
    )
    assert any(
        a["interpretation_status"] == "resolved" and has_valid_end(a) and a["occurrence_time"] is None
        for a in anns
    )
    assert any(a["interpretation_status"] == "not_applicable" for a in anns)
    assert any(a["interpretation_status"] == "unresolved" for a in anns)
    assert any(a["interpretation_status"] == "ambiguous" for a in anns)
    # source-different / forecast textual occurrence present
    assert any(
        a["interpretation_status"] == "resolved"
        and (a.get("occurrence_time") or {}).get("point", {}).get("kind") == "textual"
        for a in anns
    )
    # forest forecast must be resolved textual, not unresolved
    forest_phrase = "the forest is set to arrive at the town in 4-5 hours"
    forest = next(a for a in anns if a.get("source_phrase") == forest_phrase)
    assert forest["interpretation_status"] == "resolved"
    assert forest["occurrence_time"]["point"]["kind"] == "textual"
    assert forest["occurrence_time"]["point"]["raw_expression"] == forest_phrase
    for a in anns:
        assert any(str(d).strip() for d in a.get("diagnostics", []))
        if a["interpretation_status"] in {"not_applicable", "ambiguous", "unresolved"}:
            assert a["occurrence_time"] is None
            assert a["valid_time"] is None


def test_gold_audit_files_exist_for_promotion_cohorts() -> None:
    for folder in (HOLDOUT_V7, ADV_V5):
        audit = (folder / "GOLD-AUDIT.md").read_text(encoding="utf-8")
        assert "Audit result" in audit
        assert "Supported" in audit
        assert "Rejected alternative" in audit


def test_tl01f_regression_mirrors_exist() -> None:
    expected = [
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01f.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01f.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/temporal-case-tl01f.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3/temporal-case-tl01f.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3/temporal-case-tl01f.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v5/temporal-case-tl01f.json",
    ]
    for path in expected:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["prompt_version"] == "tl01f-v1"
        assert "tl01f" in payload["case_id"]
