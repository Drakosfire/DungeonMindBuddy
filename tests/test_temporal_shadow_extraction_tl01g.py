"""TL01G registry, resolution-proof abstention prompt, and freeze tests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from graph_memory.kernel.contributions import semantic_assertion_value
from graph_memory.temporal_shadow_extraction import (
    FakeTemporalShadowExtractionClient,
    TL01B_PACKET_VERSION,
    TL01C_PACKET_VERSION,
    TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS,
    TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS,
    build_assertion_evidence_packets,
    compute_prompt_sha256,
    load_temporal_shadow_extraction_case,
    render_temporal_shadow_user_content_v2,
    resolve_prompt_spec,
    run_temporal_shadow_extraction,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

FROZEN_TL01F_PROMPT_SHA256 = (
    "7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143"
)
# Frozen after TL01G candidate freeze — do NOT recompute from live instructions.
FROZEN_TL01G_PROMPT_SHA256 = (
    "3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013"
)

TL01G_RESERVED_VOCABULARY = (
    "Vespera",
    "Kaelith",
    "Rondel",
    "Brinegate Wharf",
    "Lanternreef Compact",
    "Ashlock Primers",
)

# Whole-prompt anti-oracle: prior prompt reserved terms + high-signal observed cohort phrases.
FORBIDDEN_PRIOR_PROMPT_AND_OBSERVED_TERMS = (
    # Prior prompt reserved vocabularies
    "Ivara",
    "Kelren",
    "Mothe",
    "Starfall Viaduct",
    "Brasswater Council",
    "Cobalt Register",
    "Quenvar",
    "Seldric",
    "Thayle",
    "Moonpier Bridge",
    "Embercourt Synod",
    "Verdant Codex",
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
    "Nerys",
    "Bram",
    "Vell",
    "Saltspan Quay",
    "Pale Wardens",
    # Observed V5 / V7 high-signal entities and phrases (Matrix B / promotion history)
    "Corveth",
    "Ysanna",
    "Pelloric",
    "Driftglass Causeway",
    "Amber Ledger",
    "Nightspine Order",
    "Lysandra",
    "Dustwalker",
    "Mossford",
    "migrating forest",
    "abandoned restaurant",
    "search her contacts",
    "search their contacts",
    "As archivist, Ysanna",
)

REQUIRED_PROMPT_PHRASES = (
    "resolved requires completing ALL of Gates A–F below",
    "Gate A — Proposition proof",
    "Gate B — Temporal-eligibility proof",
    "Gate C — Unique-lane proof",
    "Gate D — Grounded-value proof",
    "Gate E — Source-time licensing proof",
    "Gate F — Copy-and-grounding proof",
    "Source time is never a substitute for missing fictional time",
    "Future commitment without an execution-time expression → unresolved",
    "Future forecast with an explicit relative or textual temporal phrase",
    "Missing value is unresolved, not ambiguous",
    "Temporal ambiguity is epistemic, not branch divergence",
    "A statement made during Session N is not evidence that a promised future action happens in Session N",
    "A persistent-state start or end never appears only as occurrence_time",
    "Surrounding consequences in evidence",
    "holds or recovered the Ashlock Primers",
    "occurrence_time MUST be null AND valid_time MUST be null",
    "raw_expression must be a verbatim contiguous substring",
)

DEV_TL01F_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01f.json"
)

REGRESSION_MIRROR_DIRS = (
    "temporal_shadow_cohort",
    "temporal_shadow_holdout",
    "temporal_shadow_holdout_v5",
    "temporal_shadow_holdout_v7",
    "temporal_shadow_adversarial_v2",
    "temporal_shadow_adversarial_v3",
    "temporal_shadow_adversarial_v5",
)

HOLDOUT_V8 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v8"
ADV_V6 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v6"

PRIOR_CANONICAL_COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_cohort",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v4",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v5",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v6",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v7",
)

PRIOR_ADVERSARIAL_COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v4",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5",
)

ADV_V6_VOCABULARY = (
    "Kestrel Vale",
    "Briarwick",
    "Nymera",
    "Ironreed Causeway",
    "Saltglass Register",
    "Dawnspine Compact",
)


def test_tl01g_resolves_through_registry_with_packet_and_renderer_v2() -> None:
    spec = resolve_prompt_spec("tl01g-v1")
    assert spec.version == "tl01g-v1"
    assert spec.packet_version == TL01C_PACKET_VERSION
    assert spec.packet_version != TL01B_PACKET_VERSION
    assert spec.render_user_content is render_temporal_shadow_user_content_v2
    assert spec.instructions == TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS


def test_tl01g_prompt_hash_is_frozen() -> None:
    assert compute_prompt_sha256("tl01g-v1") == FROZEN_TL01G_PROMPT_SHA256


def test_tl01f_control_hash_remains_frozen() -> None:
    assert compute_prompt_sha256("tl01f-v1") == FROZEN_TL01F_PROMPT_SHA256
    assert resolve_prompt_spec("tl01f-v1").instructions == TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS


def test_tl01g_instructions_contain_required_gates() -> None:
    text = TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS
    for phrase in REQUIRED_PROMPT_PHRASES:
        assert phrase in text, f"missing required phrase: {phrase!r}"


def test_tl01g_few_shots_have_exactly_one_expected_answer_each() -> None:
    text = TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS
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
            or "unresolved" in lowered
        )


def test_tl01g_few_shots_use_reserved_vocabulary() -> None:
    text = TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS
    for term in TL01G_RESERVED_VOCABULARY:
        assert term in text


def test_tl01g_whole_prompt_excludes_prior_and_observed_terms() -> None:
    text = TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS
    for term in FORBIDDEN_PRIOR_PROMPT_AND_OBSERVED_TERMS:
        assert term not in text, f"tl01g prompt contaminated by {term!r}"


def test_tl01g_reserved_vocabulary_absent_from_existing_cohorts() -> None:
    examples = REPO_ROOT / "evals/graph_memory_layer/examples"
    for path in examples.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".md"}:
            continue
        # Fresh V8/V6 may be authored after freeze; still forbid reserved vocab there.
        text = path.read_text(encoding="utf-8")
        for term in TL01G_RESERVED_VOCABULARY:
            assert not re.search(
                rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])",
                text,
            ), f"{term!r} found in existing cohort {path}"


def test_tl01f_and_tl01g_rendered_user_content_are_byte_identical() -> None:
    case = load_temporal_shadow_extraction_case(DEV_TL01F_CASE, repo_root=REPO_ROOT)
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
    tl01f = resolve_prompt_spec("tl01f-v1")
    tl01g = resolve_prompt_spec("tl01g-v1")
    rendered_f = tl01f.render_user_content(packets, case.selected_assertion_ids)
    rendered_g = tl01g.render_user_content(packets, case.selected_assertion_ids)
    assert rendered_f == rendered_g
    assert hashlib.sha256(rendered_f.encode("utf-8")).hexdigest() == hashlib.sha256(
        rendered_g.encode("utf-8")
    ).hexdigest()


def test_unknown_prompt_version_still_fails_closed(tmp_path: Path) -> None:
    case_payload = json.loads(DEV_TL01F_CASE.read_text(encoding="utf-8"))
    case_payload["prompt_version"] = "tl01z-v9"
    case_payload["case_id"] = "tl01z-bad"
    bad_case = tmp_path / "bad-case.json"
    bad_case.write_text(json.dumps(case_payload), encoding="utf-8")

    class ExplodingClient(FakeTemporalShadowExtractionClient):
        def extract_annotations(self, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("provider must not be called")

    with pytest.raises(Exception) as excinfo:
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


def test_tl01g_regression_mirrors_exist() -> None:
    for name in REGRESSION_MIRROR_DIRS:
        folder = REPO_ROOT / "evals/graph_memory_layer/examples" / name
        path = folder / "temporal-case-tl01g.json"
        assert path.is_file(), path
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["prompt_version"] == "tl01g-v1"
        assert "tl01g" in payload["case_id"]
        control = json.loads((folder / "temporal-case-tl01f.json").read_text(encoding="utf-8"))
        for key, value in control.items():
            if key in {"case_id", "prompt_version"}:
                continue
            assert payload[key] == value, (name, key)


def _collect_ids(folder: Path) -> tuple[set[str], set[str]]:
    assertion_ids: set[str] = set()
    evidence_ids: set[str] = set()
    base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
    for assertion in base.get("candidate_assertions", []):
        assertion_ids.add(assertion["assertion_id"])
        evidence_ids.update(assertion.get("evidence_ref_ids", []))
    for case_name in (
        "temporal-case-tl01g.json",
        "temporal-case-tl01f.json",
        "temporal-case-tl01e.json",
    ):
        case_path = folder / case_name
        if case_path.is_file():
            case = json.loads(case_path.read_text(encoding="utf-8"))
            for entry in case.get("evidence_registry", []):
                evidence_ids.add(entry["evidence_ref_id"])
            break
    return assertion_ids, evidence_ids


def _union_ids(folders: tuple[Path, ...]) -> tuple[set[str], set[str]]:
    assertions: set[str] = set()
    evidence: set[str] = set()
    for folder in folders:
        if not folder.is_dir():
            continue
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


def _case_evidence_by_id(folder: Path) -> dict[str, dict]:
    for case_name in (
        "temporal-case-tl01g.json",
        "temporal-case-tl01f.json",
        "temporal-case-tl01e.json",
    ):
        case_path = folder / case_name
        if case_path.is_file():
            case = json.loads(case_path.read_text(encoding="utf-8"))
            return {e["evidence_ref_id"]: e for e in case.get("evidence_registry", [])}
    return {}


def _semantic_proposition_fingerprint(assertion: dict) -> tuple:
    value = assertion.get("value") or {}
    semantic = semantic_assertion_value(value) if isinstance(value, dict) else value
    return (
        assertion.get("assertion_kind"),
        assertion.get("subject_node_id"),
        assertion.get("target_node_id"),
        assertion.get("predicate"),
        json.dumps(semantic, sort_keys=True, ensure_ascii=True),
    )


def _source_evidence_fingerprints(assertion: dict, evidence_by_id: dict[str, dict]) -> set[tuple]:
    fps: set[tuple] = set()
    for eid in assertion.get("evidence_ref_ids", []):
        entry = evidence_by_id.get(eid)
        if not entry:
            continue
        path = entry.get("source_artifact_path") or ""
        content_sha = entry.get("content_sha256") or ""
        start = entry.get("start_line")
        end = entry.get("end_line")
        span_key = f"{path}|{content_sha}|{start}|{end}"
        span_hash = hashlib.sha256(span_key.encode("utf-8")).hexdigest()
        fps.add((path, content_sha, start, end, span_hash))
    return fps


def _require_fresh_cohort(folder: Path) -> None:
    if not folder.is_dir():
        pytest.skip(f"fresh cohort not authored yet: {folder.name}")


def test_holdout_v8_fixture_files_and_prompt_versions() -> None:
    _require_fresh_cohort(HOLDOUT_V8)
    for name in (
        "README.md",
        "GOLD-AUDIT.md",
        "base-contribution.json",
        "gold-overlay.json",
        "temporal-case-tl01f.json",
        "temporal-case-tl01g.json",
    ):
        assert (HOLDOUT_V8 / name).is_file(), name
    tl01f = json.loads((HOLDOUT_V8 / "temporal-case-tl01f.json").read_text(encoding="utf-8"))
    tl01g = json.loads((HOLDOUT_V8 / "temporal-case-tl01g.json").read_text(encoding="utf-8"))
    assert tl01f["prompt_version"] == "tl01f-v1"
    assert tl01g["prompt_version"] == "tl01g-v1"
    assert len(tl01g["selected_assertion_ids"]) >= 12


def test_holdout_v8_semantic_and_source_fingerprints_disjoint_from_prior() -> None:
    _require_fresh_cohort(HOLDOUT_V8)
    v8_base = json.loads((HOLDOUT_V8 / "base-contribution.json").read_text(encoding="utf-8"))
    v8_evidence = _case_evidence_by_id(HOLDOUT_V8)
    v8_semantic = {
        _semantic_proposition_fingerprint(a) for a in v8_base.get("candidate_assertions", [])
    }
    v8_source: set[tuple] = set()
    for assertion in v8_base.get("candidate_assertions", []):
        v8_source |= _source_evidence_fingerprints(assertion, v8_evidence)

    prior_semantic: set[tuple] = set()
    prior_source: set[tuple] = set()
    for folder in PRIOR_CANONICAL_COHORT_DIRS:
        if not folder.is_dir():
            continue
        base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
        evidence = _case_evidence_by_id(folder)
        for assertion in base.get("candidate_assertions", []):
            prior_semantic.add(_semantic_proposition_fingerprint(assertion))
            prior_source |= _source_evidence_fingerprints(assertion, evidence)

    assert v8_semantic.isdisjoint(prior_semantic), sorted(v8_semantic & prior_semantic)[:5]
    assert v8_source.isdisjoint(prior_source), sorted(v8_source & prior_source)[:5]


def test_adversarial_v6_ids_and_vocab_disjoint() -> None:
    _require_fresh_cohort(ADV_V6)
    adv_a, adv_e = _collect_ids(ADV_V6)
    prior_a, prior_e = _union_ids(PRIOR_ADVERSARIAL_COHORT_DIRS)
    assert adv_a.isdisjoint(prior_a)
    assert adv_e.isdisjoint(prior_e)
    for term in ADV_V6_VOCABULARY:
        assert term in _folder_text(ADV_V6)
    prompt = TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS
    for term in ADV_V6_VOCABULARY:
        assert term not in prompt
    prior_text = "".join(_folder_text(folder) for folder in PRIOR_ADVERSARIAL_COHORT_DIRS)
    for term in ADV_V6_VOCABULARY:
        assert term not in prior_text
    holdout_text = _folder_text(HOLDOUT_V8) if HOLDOUT_V8.is_dir() else ""
    for term in ADV_V6_VOCABULARY:
        assert term not in holdout_text


def test_v8_and_v6_ids_mutually_disjoint() -> None:
    _require_fresh_cohort(HOLDOUT_V8)
    _require_fresh_cohort(ADV_V6)
    v8_a, v8_e = _collect_ids(HOLDOUT_V8)
    v6_a, v6_e = _collect_ids(ADV_V6)
    assert v8_a.isdisjoint(v6_a)
    assert v8_e.isdisjoint(v6_e)


def test_fresh_cohorts_exclude_evaluation_cohort_tag() -> None:
    for folder in (HOLDOUT_V8, ADV_V6):
        _require_fresh_cohort(folder)
        base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
        for assertion in base.get("candidate_assertions", []):
            value = assertion.get("value") or {}
            assert "cohort_tag" not in value


def test_holdout_v8_promotion_gold_covers_required_lane_classes() -> None:
    _require_fresh_cohort(HOLDOUT_V8)
    gold = json.loads((HOLDOUT_V8 / "gold-overlay.json").read_text(encoding="utf-8"))
    annotations = gold.get("annotations", [])
    assert len(annotations) >= 12

    def status_of(ann: dict) -> str:
        return str(ann.get("interpretation_status") or "")

    def has_occurrence(ann: dict) -> bool:
        return ann.get("occurrence_time") is not None

    def has_valid_start(ann: dict) -> bool:
        vt = ann.get("valid_time") or {}
        return isinstance(vt, dict) and vt.get("start") is not None

    def has_valid_end(ann: dict) -> bool:
        vt = ann.get("valid_time") or {}
        return isinstance(vt, dict) and vt.get("end") is not None

    assert any(status_of(a) == "resolved" and has_occurrence(a) for a in annotations)
    assert any(status_of(a) == "resolved" and has_valid_start(a) for a in annotations)
    assert any(status_of(a) == "resolved" and has_valid_end(a) for a in annotations)
    assert any(status_of(a) == "not_applicable" for a in annotations)
    assert any(status_of(a) == "unresolved" for a in annotations)
    assert any(status_of(a) == "ambiguous" for a in annotations)
    for ann in annotations:
        assert any(str(d).strip() for d in (ann.get("diagnostics") or []))
        if status_of(ann) in {"not_applicable", "unresolved", "ambiguous"}:
            assert ann.get("occurrence_time") is None
            assert ann.get("valid_time") is None


def test_gold_audit_files_exist_for_fresh_promotion_cohorts() -> None:
    for folder in (HOLDOUT_V8, ADV_V6):
        _require_fresh_cohort(folder)
        assert (folder / "GOLD-AUDIT.md").is_file()
