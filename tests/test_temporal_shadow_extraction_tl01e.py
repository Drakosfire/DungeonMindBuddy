"""TL01E registry, grounded-abstention prompt, and freeze tests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from graph_memory.temporal_shadow_extraction import (
    TL01B_PACKET_VERSION,
    TL01C_PACKET_VERSION,
    TL01C_SOURCE_AWARE_INSTRUCTIONS,
    TL01D_CONSERVATIVE_INSTRUCTIONS,
    TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS,
    baseline_prompt_fingerprint,
    compute_prompt_sha256,
    render_temporal_shadow_user_content_v2,
    resolve_prompt_spec,
)
from graph_memory.temporal_shadow_extraction_schema import TEMPORAL_SHADOW_PROMPT_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]

FROZEN_TL01B_INSTRUCTIONS_SHA256 = (
    "c036558b52b8a44e5358fb7f3062dbf9db5b7f5bf86cb7fa2d986e7fddd0ceec"
)
FROZEN_TL01B_PROMPT_SHA256 = (
    "c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51"
)
FROZEN_TL01C_PROMPT_SHA256 = (
    "86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3"
)
FROZEN_TL01D_PROMPT_SHA256 = (
    "410a2d1ba1f497dc1dcc4904f04f09b119586205533e925ff3d060e21a600bae"
)
# Frozen after TL01E candidate freeze — do NOT recompute from live instructions.
FROZEN_TL01E_PROMPT_SHA256 = (
    "8373cb2d40e532c648faff88064d95b0e862dfe947e9a0c80e72183bf48a7d4c"
)

TL01E_RESERVED_VOCABULARY = (
    "Ivara",
    "Kelren",
    "Mothe",
    "Starfall Viaduct",
    "Brasswater Council",
    "Cobalt Register",
)

FORBIDDEN_PRIOR_FEWSHOT_AND_COHORT_TERMS = (
    "Dessa",
    "Orun",
    "Caldrin",
    "Glass Causeway",
    "Lantern Court",
    "Ivory Ledger",
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
    "Every annotation MUST contain diagnostics with at least one nonblank string",
    "Final response checklist",
    "diagnostics contains at least one nonblank string",
    "A persistent state, role, ownership, membership, or relationship receives valid_time only when the evidence explicitly establishes a start or end boundary",
    'As mayor, X...',
    "If the proposition is itself a bounded event",
    "it remains an occurrence event",
    "BEFORE inspecting source_context.source_time",
    "occurrence_time MUST be null AND valid_time MUST be null",
    "kind=textual",
    "raw_expression must be a verbatim contiguous substring",
)

COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_cohort",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3",
)


def test_tl01e_resolves_through_registry_with_packet_and_renderer_v2() -> None:
    spec = resolve_prompt_spec("tl01e-v1")
    assert spec.version == "tl01e-v1"
    assert spec.packet_version == TL01C_PACKET_VERSION
    assert spec.packet_version != TL01B_PACKET_VERSION
    assert spec.render_user_content is render_temporal_shadow_user_content_v2
    assert spec.instructions == TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS


def test_tl01e_prompt_hash_is_frozen() -> None:
    assert compute_prompt_sha256("tl01e-v1") == FROZEN_TL01E_PROMPT_SHA256


def test_prior_prompt_hashes_remain_frozen() -> None:
    fingerprint = baseline_prompt_fingerprint()
    assert fingerprint["prompt_version"] == TEMPORAL_SHADOW_PROMPT_VERSION
    assert fingerprint["instructions_sha256"] == FROZEN_TL01B_INSTRUCTIONS_SHA256
    assert compute_prompt_sha256("tl01b-v1") == FROZEN_TL01B_PROMPT_SHA256
    assert compute_prompt_sha256("tl01c-v1") == FROZEN_TL01C_PROMPT_SHA256
    assert compute_prompt_sha256("tl01d-v1") == FROZEN_TL01D_PROMPT_SHA256
    assert (
        hashlib.sha256(TL01C_SOURCE_AWARE_INSTRUCTIONS.encode("utf-8")).hexdigest()
        == "77e6673bab46b06898478cc7ff66d8e15f1ac0701f126120a6606bfbc16504bc"
    )
    # Byte-stable TL01D via prompt SHA (authoritative freeze; do not mutate).
    assert compute_prompt_sha256("tl01d-v1") == FROZEN_TL01D_PROMPT_SHA256


def test_tl01e_instructions_contain_required_gates() -> None:
    text = TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS
    for phrase in REQUIRED_PROMPT_PHRASES:
        assert phrase in text, f"missing required phrase: {phrase!r}"


def test_tl01e_few_shots_have_exactly_one_expected_answer_each() -> None:
    text = TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS
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


def test_tl01e_few_shots_use_reserved_vocabulary() -> None:
    text = TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS
    for term in TL01E_RESERVED_VOCABULARY:
        assert term in text


def test_tl01e_few_shots_exclude_prior_prompt_and_observed_terms() -> None:
    text = TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS
    for term in FORBIDDEN_PRIOR_FEWSHOT_AND_COHORT_TERMS:
        assert term not in text, f"tl01e few-shot contaminated by {term!r}"


def test_tl01e_reserved_vocabulary_absent_from_existing_cohorts() -> None:
    for cohort_dir in COHORT_DIRS:
        for path in cohort_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".json", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for term in TL01E_RESERVED_VOCABULARY:
                assert not re.search(
                    rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])",
                    text,
                ), f"{term!r} found in existing cohort {path}"


def test_tl01e_regression_case_mirrors_exist() -> None:
    expected = [
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01e.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01e.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/temporal-case-tl01e.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3/temporal-case-tl01e.json",
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3/temporal-case-tl01e.json",
    ]
    for path in expected:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["prompt_version"] == "tl01e-v1"
        assert "tl01e" in payload["case_id"]


def test_retired_holdout_v2_not_referenced_by_tl01e_case_mirrors() -> None:
    mirrors = list(
        (REPO_ROOT / "evals/graph_memory_layer/examples").glob(
            "**/temporal-case-tl01e.json"
        )
    )
    assert mirrors
    for path in mirrors:
        text = path.read_text(encoding="utf-8")
        assert "temporal_shadow_holdout_v2" not in text


def _collect_ids(folder: Path) -> tuple[set[str], set[str]]:
    assertion_ids: set[str] = set()
    evidence_ids: set[str] = set()
    base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
    for assertion in base.get("candidate_assertions", []):
        assertion_ids.add(assertion["assertion_id"])
        evidence_ids.update(assertion.get("evidence_ref_ids", []))
    case = json.loads((folder / "temporal-case-tl01e.json").read_text(encoding="utf-8"))
    for entry in case.get("evidence_registry", []):
        evidence_ids.add(entry["evidence_ref_id"])
    return assertion_ids, evidence_ids


PRIOR_COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_cohort",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3",
)

ADV_V4_VOCABULARY = (
    "Rhelan",
    "Vosk",
    "Nyeth",
    "Ashglass Span",
    "Tideglass Synod",
    "Azure Index",
)


def test_holdout_v4_ids_disjoint_from_prior_cohorts() -> None:
    holdout_v4 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v4"
    new_assertions, new_evidence = _collect_ids(holdout_v4)
    prior_assertions: set[str] = set()
    prior_evidence: set[str] = set()
    for folder in PRIOR_COHORT_DIRS:
        a_ids, e_ids = _collect_ids(folder)
        prior_assertions |= a_ids
        prior_evidence |= e_ids
    assert new_assertions.isdisjoint(prior_assertions)
    assert new_evidence.isdisjoint(prior_evidence)


def test_adversarial_v4_vocabulary_disjoint_from_prompt_and_prior() -> None:
    prompt = TL01E_GROUNDED_ABSTENTION_INSTRUCTIONS
    for term in ADV_V4_VOCABULARY:
        assert term not in prompt
    prior_text = ""
    for folder in (
        *PRIOR_COHORT_DIRS,
        REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v4",
    ):
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".md"}:
                prior_text += path.read_text(encoding="utf-8")
    for term in ADV_V4_VOCABULARY:
        assert term not in prior_text, f"{term!r} leaked into prior/holdout fixtures"


def test_v4_control_candidate_cases_are_exact_mirrors() -> None:
    from evals.graph_memory_layer.temporal_shadow_prompt_calibration import (
        validate_paired_case_equivalence,
    )

    for folder_name in (
        "temporal_shadow_holdout_v4",
        "temporal_shadow_adversarial_v4",
    ):
        folder = REPO_ROOT / "evals/graph_memory_layer/examples" / folder_name
        validate_paired_case_equivalence(
            baseline_case_path=folder / "temporal-case-tl01d.json",
            candidate_case_path=folder / "temporal-case-tl01e.json",
            repo_root=REPO_ROOT,
            pair_name=folder_name,
        )


def test_v4_non_resolved_gold_has_null_extents_and_nonblank_diagnostics() -> None:
    for folder_name in (
        "temporal_shadow_holdout_v4",
        "temporal_shadow_adversarial_v4",
    ):
        gold = json.loads(
            (
                REPO_ROOT
                / "evals/graph_memory_layer/examples"
                / folder_name
                / "gold-overlay.json"
            ).read_text(encoding="utf-8")
        )
        for ann in gold["annotations"]:
            assert any(str(d).strip() for d in ann.get("diagnostics", []))
            if ann["interpretation_status"] in {
                "not_applicable",
                "ambiguous",
                "unresolved",
            }:
                assert ann["occurrence_time"] is None
                assert ann["valid_time"] is None
