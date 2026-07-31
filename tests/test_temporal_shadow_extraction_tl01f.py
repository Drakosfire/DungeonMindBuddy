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
