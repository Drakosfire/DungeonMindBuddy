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
HOLDOUT_V9 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v9"
HOLDOUT_V10 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v10"
HOLDOUT_V11 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v11"
HOLDOUT_V12 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v12"
HOLDOUT_V13 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v13"
ADV_V6 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v6"
ADV_V7 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v7"
ADV_V8 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v8"
ADV_V9 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v9"
ADV_V10 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v10"
ADV_V11 = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v11"

PRIOR_CANONICAL_COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_cohort",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v4",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v5",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v6",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v7",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v8",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v9",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v10",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v11",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v12",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_holdout_v13",
)

PRIOR_ADVERSARIAL_COHORT_DIRS = (
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v4",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v6",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v7",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v8",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v9",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v10",
    REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v11",
)

LAST_RETIRED_ADVERSARIAL_VERSION = 11
LAST_RETIRED_HOLDOUT_VERSION = 13

ADV_V6_VOCABULARY = (
    "Kestrel Vale",
    "Briarwick",
    "Nymera",
    "Ironreed Causeway",
    "Saltglass Register",
    "Dawnspine Compact",
)

ADV_V7_VOCABULARY = (
    "Hollowmere",
    "Sablewick",
    "Torren Vale",
    "Glassfen Causeway",
    "Moonshard Index",
    "Ashen Compact",
)

ADV_V8_VOCABULARY = (
    "Rookhaven",
    "Merridan",
    "Calyx Thorne",
    "Stormglass Causeway",
    "Emberleaf Index",
    "Cinder Compact",
)

ADV_V9_VOCABULARY = (
    "Thornwick",
    "Velessa Mar",
    "Quorin Hale",
    "Frostmere Causeway",
    "Amberquill Codex",
    "Ironroot Compact",
)

ADV_V10_VOCABULARY = (
    "Cairnwick",
    "Sable Quay",
    "Liora Venn",
    "Mistglass Causeway",
    "Thornledger Atlas",
    "Paleoak Compact",
)

ADV_V11_VOCABULARY = (
    "Glimmerfen",
    "Brinearch Quay",
    "Orla Fenwick",
    "Driftglass Causeway",
    "Glasspetal Codex",
    "Rootward Compact",
)

# Approved V11 draft requires Driftglass Causeway despite legacy adv5 use.
ADV_V11_PRIOR_VOCABULARY_ALLOWED = ("Driftglass Causeway",)

_PROPOSITION_TEMPLATE_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "has",
        "have",
        "had",
        "will",
        "that",
        "this",
        "their",
        "they",
        "them",
        "when",
        "what",
        "must",
        "still",
        "every",
        "each",
        "also",
        "about",
        "into",
        "from",
        "by",
        "as",
        "it",
        "its",
        "he",
        "she",
        "his",
        "her",
        "not",
        "only",
        "then",
        "after",
        "before",
        "following",
        "without",
        "while",
        "during",
        "until",
        "since",
        "no",
        "longer",
        "all",
        "any",
        "other",
        "one",
        "another",
        "maybe",
        "just",
        "now",
        "there",
        "here",
        "who",
        "which",
        "where",
        "how",
        "do",
        "does",
        "did",
        "can",
        "could",
        "would",
        "should",
        "may",
        "might",
        "than",
        "so",
        "if",
        "but",
        "up",
        "out",
        "off",
        "over",
        "under",
        "again",
        "once",
        "both",
        "few",
        "most",
        "such",
        "through",
        "between",
        "among",
        "toward",
        "towards",
        "upon",
        "within",
        "across",
        "along",
        "against",
        "near",
        "past",
        "per",
        "via",
        "yet",
        "already",
        "even",
        "own",
        "same",
        "too",
        "very",
    }
)

_PROPOSITION_ENTITY_TOKENS = (
    "Lysandra",
    "Mirathorn",
    "Questionable",
    "Grobnok",
    "Thalia",
    "Bonogo",
    "Caelynn",
    "Karsemine",
    "Shepherd",
    "Wolf",
    "Storm Elemental",
    "Ogonob",
    "Ashenvale",
    "Glimmerfen",
    "Brinearch Quay",
    "Orla Fenwick",
    "Driftglass Causeway",
    "Glasspetal Codex",
    "Rootward Compact",
)

# Forbidden adversarial sentence templates (normalized) from V5/V6 — Adv V7 must not reuse.
FORBIDDEN_ADVERSARIAL_TEMPLATES = (
    "race past {npc} as {pronoun} continues to hold the {object}",
    "couriers race past",
    "wardens race past",
    "continues to hold the",
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


def _normalize_span_text(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _resolved_span_text(entry: dict) -> str:
    rel = entry.get("source_artifact_path") or ""
    if not rel:
        raise AssertionError("evidence entry missing source_artifact_path")
    path = REPO_ROOT / rel
    if not path.is_file():
        raise AssertionError(f"missing evidence source artifact: {rel}")
    lines = path.read_text(encoding="utf-8").splitlines()
    start_raw = entry.get("start_line")
    end_raw = entry.get("end_line")
    if start_raw is None or end_raw is None:
        raise AssertionError(f"evidence entry missing line range: {entry.get('evidence_ref_id')}")
    start = int(start_raw)
    end = int(end_raw)
    if start < 1 or end < start:
        raise AssertionError(
            f"invalid evidence line range for {entry.get('evidence_ref_id')}: {start}-{end}"
        )
    if start > len(lines) or end > len(lines):
        raise AssertionError(
            f"evidence line range beyond EOF for {entry.get('evidence_ref_id')}: "
            f"{start}-{end} vs {len(lines)} lines"
        )
    chunk = chr(10).join(lines[start - 1 : end])
    normalized = _normalize_span_text(chunk)
    if not normalized:
        raise AssertionError(
            f"empty normalized span text for {entry.get('evidence_ref_id')}: {start}-{end}"
        )
    return normalized


def _source_evidence_fingerprints(assertion: dict, evidence_by_id: dict[str, dict]) -> set[tuple]:
    """Source/evidence fingerprints keyed by resolved span text identity.

    Path/content_sha/line metadata is supporting only; independence is owned by
    the SHA256 of the exact normalized resolved span text.
    """
    fps: set[tuple] = set()
    evidence_ref_ids = assertion.get("evidence_ref_ids") or []
    if not evidence_ref_ids:
        raise AssertionError(
            f"assertion {assertion.get('assertion_id')} has zero evidence_ref_ids"
        )
    for eid in evidence_ref_ids:
        entry = evidence_by_id.get(eid)
        if entry is None:
            raise AssertionError(
                f"missing evidence registry entry {eid!r} for {assertion.get('assertion_id')}"
            )
        path = entry.get("source_artifact_path") or ""
        content_sha = entry.get("content_sha256") or ""
        start = entry.get("start_line")
        end = entry.get("end_line")
        span_text = _resolved_span_text(entry)
        span_text_sha = hashlib.sha256(span_text.encode("utf-8")).hexdigest()
        fps.add((span_text_sha, path, content_sha, start, end))
    if not fps:
        raise AssertionError(
            f"assertion {assertion.get('assertion_id')} produced zero span fingerprints"
        )
    return fps


def _source_span_text_fingerprints(assertion: dict, evidence_by_id: dict[str, dict]) -> set[str]:
    return {
        fp[0]
        for fp in _source_evidence_fingerprints(assertion, evidence_by_id)
    }


def _normalize_template(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Drop reserved proper nouns to catch noun-substituted replays.
    for vocab in (
        *ADV_V6_VOCABULARY,
        *ADV_V7_VOCABULARY,
        *ADV_V8_VOCABULARY,
        *ADV_V9_VOCABULARY,
        *ADV_V10_VOCABULARY,
        *ADV_V11_VOCABULARY,
    ):
        t = t.replace(vocab.lower(), "NAME")
    for token in (
        "corveth", "ysanna", "pelloric", "nymera", "briarwick", "kestrel",
        "hollowmere", "sablewick", "torren", "amber ledger", "saltglass",
        "moonshard", "nightspine", "dawnspine", "ashen compact",
    ):
        t = t.replace(token, "NAME")
    return t


def _proposition_template_tokens(assertion: dict) -> set[str]:
    label = str(assertion.get("label") or "")
    predicate = str(assertion.get("predicate") or "")
    combined = f"{label} {predicate}"
    text = combined.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    for entity in _PROPOSITION_ENTITY_TOKENS:
        text = text.replace(entity.lower(), "name")
    for match in re.findall(r"\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b", combined):
        text = text.replace(match.lower(), "name")
    tokens: set[str] = set()
    for token in text.split():
        if token in _PROPOSITION_TEMPLATE_STOPWORDS:
            continue
        if token == "name":
            tokens.add("NAME")
        else:
            tokens.add(token)
    return tokens


def _proposition_template_jaccard(left: dict, right: dict) -> float:
    left_tokens = _proposition_template_tokens(left)
    right_tokens = _proposition_template_tokens(right)
    if not left_tokens and not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


_RESULTING_STATE_MARKERS = ("no longer", "still ", "continues to", "remains")
_BOUNDARY_NARRATION_CUES = (
    "became",
    "stopped",
    "ceased",
    "ended",
    "began to",
    "started to",
    "when they",
)


def _source_narrates_boundary(source_text: str) -> bool:
    """True when prose narrates a state/event transition (positive Gate E3 grounding)."""
    text = source_text.lower()
    return any(cue in text for cue in _BOUNDARY_NARRATION_CUES)


def _any_evidence_narrates_boundary(sources: list[str]) -> bool:
    """Acceptance: at least one resolved evidence span narrates the boundary transition."""
    return any(_source_narrates_boundary(source) for source in sources)


def _source_reports_resulting_state_without_narrated_boundary(source_text: str) -> bool:
    """Diagnostic: resulting attitude/state without narrated transition (not acceptance)."""
    text = source_text.lower()
    return any(m in text for m in _RESULTING_STATE_MARKERS) and not _source_narrates_boundary(
        source_text
    )


def _postponement_occurrence_uses_reschedule_time(
    proposition: str, raw_expression: str | None
) -> bool:
    """True when occurrence value is the future reschedule target of a postponement proposition."""
    prop = proposition.lower()
    expr = (raw_expression or "").lower()
    if "postpon" not in prop:
        return False
    if not expr:
        return False
    # dawn/dusk/morning etc. used as occurrence of postponement decision
    return ("until " in expr) or expr.startswith("postponed until")


def _template_token_set(text: str) -> set[str]:
    return set(_normalize_template(text).split())


def _template_jaccard(a: str, b: str) -> float:
    left = _template_token_set(a)
    right = _template_token_set(b)
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _cohort_version(path: Path, *, prefix: str) -> int:
    suffix = path.name[len(prefix) :]
    if not suffix.isdigit():
        raise AssertionError(
            f"unknown or non-numeric versioned cohort suffix: {path.name!r}"
        )
    return int(suffix)


def _sorted_by_version(dirs: list[Path], *, prefix: str) -> list[Path]:
    return sorted(dirs, key=lambda p: _cohort_version(p, prefix=prefix))


def _load_assertions(folder: Path) -> list[dict]:
    base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
    return list(base.get("candidate_assertions", []))


def _assert_proposition_jaccard_below_threshold(
    fresh_assertions: list[dict],
    comparison: list[tuple[str, dict]],
    *,
    threshold: float = 0.40,
    cohort_kind: str,
) -> None:
    for fresh_assertion in fresh_assertions:
        for prior_name, prior_assertion in comparison:
            score = _proposition_template_jaccard(fresh_assertion, prior_assertion)
            if score >= threshold:
                raise AssertionError(
                    f"proposition-template Jaccard >= {threshold:.2f} vs {cohort_kind}: "
                    f"{fresh_assertion.get('label')!r} vs {prior_name} "
                    f"{prior_assertion.get('label')!r} ({score:.3f})"
                )


def _assert_successors_proposition_jaccard_cumulative(
    *,
    successors: list[Path],
    retired_dirs: tuple[Path, ...],
    prefix: str,
    threshold: float = 0.40,
    cohort_kind: str,
) -> None:
    comparison: list[tuple[str, dict]] = []
    for folder in retired_dirs:
        if not folder.is_dir():
            continue
        for assertion in _load_assertions(folder):
            comparison.append((folder.name, assertion))
    for successor in _sorted_by_version(successors, prefix=prefix):
        fresh_assertions = _load_assertions(successor)
        _assert_proposition_jaccard_below_threshold(
            fresh_assertions,
            comparison,
            threshold=threshold,
            cohort_kind=cohort_kind,
        )
        for assertion in fresh_assertions:
            comparison.append((successor.name, assertion))


def _all_evidence_is_resulting_state_without_boundary(sources: list[str]) -> bool:
    """Diagnostic helper: every resolved source is a resulting-state report without boundary."""
    if not sources:
        return False
    return all(
        _source_reports_resulting_state_without_narrated_boundary(source)
        for source in sources
    )


def _discover_cohorts_above_retired_cutoff(
    *,
    prefix: str,
    last_retired_version: int,
    examples_root: Path | None = None,
) -> list[Path]:
    """Discover on-disk versioned cohorts with version > last_retired_version.

    Ignores PRIOR_* membership. Non-numeric suffixes under ``prefix*`` fail closed.
    """
    examples = examples_root or (REPO_ROOT / "evals/graph_memory_layer/examples")
    found: list[Path] = []
    for path in sorted(examples.glob(f"{prefix}*")):
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix) :]
        if not suffix or not suffix.isdigit():
            raise AssertionError(
                f"unknown or non-numeric versioned cohort suffix: {name!r}"
            )
        if int(suffix) > last_retired_version:
            found.append(path)
    return found


def _require_fresh_cohort(folder: Path) -> None:
    if not folder.is_dir():
        pytest.skip(f"fresh cohort not authored yet: {folder.name}")


def test_holdout_v8_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(HOLDOUT_V8)
    readme = (HOLDOUT_V8 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "holdout V11" in readme or "V11" in readme
    assert (HOLDOUT_V8 / "base-contribution.json").is_file()
    assert (HOLDOUT_V8 / "gold-overlay.json").is_file()


def test_holdout_v9_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(HOLDOUT_V9)
    readme = (HOLDOUT_V9 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "holdout V11" in readme or "V11" in readme
    assert (HOLDOUT_V9 / "base-contribution.json").is_file()
    assert (HOLDOUT_V9 / "gold-overlay.json").is_file()


def test_holdout_v10_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(HOLDOUT_V10)
    readme = (HOLDOUT_V10 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "holdout V11" in readme or "V11" in readme
    assert (HOLDOUT_V10 / "base-contribution.json").is_file()
    assert (HOLDOUT_V10 / "gold-overlay.json").is_file()


def test_adversarial_v6_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(ADV_V6)
    readme = (ADV_V6 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "adversarial V9" in readme or "V9" in readme
    # Prove template overlap with V5-style race/hold construction remains in V6 sources.
    sources = "\n".join(
        p.read_text(encoding="utf-8") for p in (ADV_V6 / "sources").glob("*.md")
    ).lower()
    assert "race past" in sources and "continues to hold" in sources


def test_adversarial_v7_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(ADV_V7)
    readme = (ADV_V7 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "adversarial V9" in readme or "V9" in readme
    assert (ADV_V7 / "base-contribution.json").is_file()
    assert (ADV_V7 / "gold-overlay.json").is_file()


def test_adversarial_v8_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(ADV_V8)
    readme = (ADV_V8 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "adversarial V9" in readme or "V9" in readme
    assert (ADV_V8 / "base-contribution.json").is_file()
    assert (ADV_V8 / "gold-overlay.json").is_file()


def test_holdout_v11_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(HOLDOUT_V11)
    readme = (HOLDOUT_V11 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "holdout V12" in readme or "V12" in readme
    assert (HOLDOUT_V11 / "base-contribution.json").is_file()
    assert (HOLDOUT_V11 / "gold-overlay.json").is_file()


def test_adversarial_v9_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(ADV_V9)
    readme = (ADV_V9 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "adversarial V10" in readme or "V10" in readme
    assert (ADV_V9 / "base-contribution.json").is_file()
    assert (ADV_V9 / "gold-overlay.json").is_file()


def test_holdout_v12_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(HOLDOUT_V12)
    readme = (HOLDOUT_V12 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "holdout V13" in readme or "V13" in readme
    assert (HOLDOUT_V12 / "base-contribution.json").is_file()
    assert (HOLDOUT_V12 / "gold-overlay.json").is_file()


def test_adversarial_v10_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(ADV_V10)
    readme = (ADV_V10 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "adversarial V11" in readme or "V11" in readme
    assert (ADV_V10 / "base-contribution.json").is_file()
    assert (ADV_V10 / "gold-overlay.json").is_file()


def test_holdout_v13_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(HOLDOUT_V13)
    readme = (HOLDOUT_V13 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    assert "Gate E3" in readme or "no longer feel represented" in readme
    assert (HOLDOUT_V13 / "base-contribution.json").is_file()
    assert (HOLDOUT_V13 / "gold-overlay.json").is_file()


def test_adversarial_v11_retired_as_observed_regression_not_promotion() -> None:
    _require_fresh_cohort(ADV_V11)
    readme = (ADV_V11 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    lowered = readme.lower()
    assert "adv v10" in lowered or "adversarial v10" in lowered or "v10" in lowered
    assert "proposition" in lowered or "jaccard" in lowered
    assert (ADV_V11 / "base-contribution.json").is_file()
    assert (ADV_V11 / "gold-overlay.json").is_file()


def test_holdout_v13_fixture_files_and_prompt_versions() -> None:
    _require_fresh_cohort(HOLDOUT_V13)
    for name in (
        "README.md",
        "GOLD-AUDIT.md",
        "base-contribution.json",
        "gold-overlay.json",
        "temporal-case-tl01f.json",
        "temporal-case-tl01g.json",
    ):
        assert (HOLDOUT_V13 / name).is_file(), name
    readme = (HOLDOUT_V13 / "README.md").read_text(encoding="utf-8")
    assert "RETIRED as independent TL01G promotion evidence" in readme
    tl01f = json.loads((HOLDOUT_V13 / "temporal-case-tl01f.json").read_text(encoding="utf-8"))
    tl01g = json.loads((HOLDOUT_V13 / "temporal-case-tl01g.json").read_text(encoding="utf-8"))
    assert tl01f["prompt_version"] == "tl01f-v1"
    assert tl01g["prompt_version"] == "tl01g-v1"
    assert len(tl01g["selected_assertion_ids"]) >= 12


def test_holdout_v13_semantic_and_source_text_fingerprints_disjoint_from_prior() -> None:
    _require_fresh_cohort(HOLDOUT_V13)
    v13_base = json.loads((HOLDOUT_V13 / "base-contribution.json").read_text(encoding="utf-8"))
    v13_evidence = _case_evidence_by_id(HOLDOUT_V13)
    v13_semantic = {
        _semantic_proposition_fingerprint(a) for a in v13_base.get("candidate_assertions", [])
    }
    v13_span_text = set()
    for assertion in v13_base.get("candidate_assertions", []):
        v13_span_text |= _source_span_text_fingerprints(assertion, v13_evidence)

    prior_semantic: set[tuple] = set()
    prior_span_text: set[str] = set()
    for folder in PRIOR_CANONICAL_COHORT_DIRS:
        if folder == HOLDOUT_V13 or not folder.is_dir():
            continue
        base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
        evidence = _case_evidence_by_id(folder)
        for assertion in base.get("candidate_assertions", []):
            prior_semantic.add(_semantic_proposition_fingerprint(assertion))
            prior_span_text |= _source_span_text_fingerprints(assertion, evidence)

    assert v13_semantic.isdisjoint(prior_semantic), sorted(v13_semantic & prior_semantic)[:5]
    assert v13_span_text.isdisjoint(prior_span_text), sorted(
        v13_span_text & prior_span_text
    )[:5]
    assert all(sha for sha in v13_span_text), "resolved span text SHA must be non-empty"


def test_holdout_v13_proposition_template_jaccard_disjoint_from_prior() -> None:
    _require_fresh_cohort(HOLDOUT_V13)
    v13_base = json.loads((HOLDOUT_V13 / "base-contribution.json").read_text(encoding="utf-8"))
    v13_assertions = v13_base.get("candidate_assertions", [])
    prior_assertions: list[tuple[str, dict]] = []
    for folder in PRIOR_CANONICAL_COHORT_DIRS:
        if folder == HOLDOUT_V13 or not folder.is_dir():
            continue
        base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
        for assertion in base.get("candidate_assertions", []):
            prior_assertions.append((folder.name, assertion))

    for v13_assertion in v13_assertions:
        for prior_name, prior_assertion in prior_assertions:
            score = _proposition_template_jaccard(v13_assertion, prior_assertion)
            if score >= 0.40:
                raise AssertionError(
                    "proposition-template Jaccard >= 0.40: "
                    f"{v13_assertion.get('label')!r} vs {prior_name} "
                    f"{prior_assertion.get('label')!r} ({score:.3f})"
                )


def test_adversarial_v11_ids_vocab_and_template_disjoint() -> None:
    _require_fresh_cohort(ADV_V11)
    adv_a, adv_e = _collect_ids(ADV_V11)
    prior_dirs = tuple(f for f in PRIOR_ADVERSARIAL_COHORT_DIRS if f != ADV_V11)
    prior_a, prior_e = _union_ids(prior_dirs)
    assert adv_a.isdisjoint(prior_a)
    assert adv_e.isdisjoint(prior_e)
    folder_text = _folder_text(ADV_V11)
    for term in ADV_V11_VOCABULARY:
        assert term in folder_text
    prompt = TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS
    for term in ADV_V11_VOCABULARY:
        assert term not in prompt
    prior_text = "".join(_folder_text(folder) for folder in prior_dirs)
    for term in ADV_V11_VOCABULARY:
        if term in ADV_V11_PRIOR_VOCABULARY_ALLOWED:
            continue
        assert term not in prior_text
    holdout_text = _folder_text(HOLDOUT_V13) if HOLDOUT_V13.is_dir() else ""
    for term in ADV_V11_VOCABULARY:
        assert term not in holdout_text
    sources = "\n".join(p.read_text(encoding="utf-8") for p in (ADV_V11 / "sources").glob("*.md"))
    lowered = sources.lower()
    assert "race past" not in lowered
    assert "continues to hold" not in lowered
    assert " now" not in lowered and not lowered.startswith("now")
    prior_sources = []
    for folder in prior_dirs:
        src = folder / "sources"
        if src.is_dir():
            prior_sources.extend(p.read_text(encoding="utf-8") for p in src.glob("*.md"))
    prior_templates = {_normalize_template(s) for s in prior_sources if s.strip()}
    for src in (ADV_V11 / "sources").glob("*.md"):
        text = src.read_text(encoding="utf-8")
        tmpl = _normalize_template(text)
        assert tmpl not in prior_templates, f"exact template overlap: {src.name}"
        for prior in prior_sources:
            if _template_jaccard(text, prior) >= 0.40:
                raise AssertionError(
                    f"Jaccard template overlap >= 0.40: {src.name} vs prior source"
                )


def test_adversarial_v11_proposition_template_jaccard_replays_adv_v10() -> None:
    _require_fresh_cohort(ADV_V11)
    _require_fresh_cohort(ADV_V10)
    v11_base = json.loads((ADV_V11 / "base-contribution.json").read_text(encoding="utf-8"))
    v10_base = json.loads((ADV_V10 / "base-contribution.json").read_text(encoding="utf-8"))
    v11_assertions = v11_base.get("candidate_assertions", [])
    v10_assertions = v10_base.get("candidate_assertions", [])

    high_overlap_count = 0
    for v11_assertion in v11_assertions:
        for v10_assertion in v10_assertions:
            if _proposition_template_jaccard(v11_assertion, v10_assertion) >= 0.40:
                high_overlap_count += 1
                break
    assert high_overlap_count >= 5, (
        f"expected >=5 V11 assertions with proposition-template Jaccard >= 0.40 vs V10; "
        f"got {high_overlap_count}"
    )

    def _find_by_label_fragment(base: dict, fragment: str) -> dict:
        for assertion in base.get("candidate_assertions", []):
            if fragment in str(assertion.get("label") or "").lower():
                return assertion
        raise AssertionError(f"no assertion with label fragment {fragment!r}")

    elected_v11 = _find_by_label_fragment(v11_base, "elected chancellor")
    elected_v10 = _find_by_label_fragment(v10_base, "elected chancellor")
    assert _proposition_template_jaccard(elected_v11, elected_v10) >= 0.99

    coast_v11 = _find_by_label_fragment(v11_base, "left the coast three winters earlier")
    coast_v10 = _find_by_label_fragment(v10_base, "left the coast three winters earlier")
    assert _proposition_template_jaccard(coast_v11, coast_v10) >= 0.99


def test_adversarial_cohort_proposition_template_jaccard_must_be_below_threshold_vs_prior() -> None:
    """Fail-closed guard for fresh adversarial promotion cohorts (V12+)."""
    successors = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_adversarial_v",
        last_retired_version=LAST_RETIRED_ADVERSARIAL_VERSION,
    )
    if not successors:
        return
    for successor in successors:
        _require_fresh_cohort(successor)
    _assert_successors_proposition_jaccard_cumulative(
        successors=successors,
        retired_dirs=PRIOR_ADVERSARIAL_COHORT_DIRS,
        prefix="temporal_shadow_adversarial_v",
        cohort_kind="prior adversarial",
    )


def test_holdout_cohort_proposition_template_jaccard_must_be_below_threshold_vs_prior() -> None:
    """Fail-closed guard for fresh holdout promotion cohorts (V14+)."""
    successors = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_holdout_v",
        last_retired_version=LAST_RETIRED_HOLDOUT_VERSION,
    )
    if not successors:
        return
    for successor in successors:
        _require_fresh_cohort(successor)
    _assert_successors_proposition_jaccard_cumulative(
        successors=successors,
        retired_dirs=PRIOR_CANONICAL_COHORT_DIRS,
        prefix="temporal_shadow_holdout_v",
        cohort_kind="prior canonical holdout",
    )


def test_cumulative_successor_proposition_jaccard_rejects_high_overlap_vs_earlier_successor(
    tmp_path: Path,
) -> None:
    """V13 must fail cumulative Jaccard when it replays V12 labels."""
    shared_label = "The chancellor left the coast three winters earlier"
    for version, folder_name in ((12, "temporal_shadow_holdout_v12"), (13, "temporal_shadow_holdout_v13")):
        cohort = tmp_path / folder_name
        cohort.mkdir()
        payload = {
            "candidate_assertions": [
                {
                    "assertion_id": f"assertion:v{version}",
                    "label": shared_label,
                    "predicate": "left_coast",
                }
            ]
        }
        (cohort / "base-contribution.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    successors = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_holdout_v",
        last_retired_version=11,
        examples_root=tmp_path,
    )
    with pytest.raises(AssertionError, match="Jaccard >= 0.40"):
        _assert_successors_proposition_jaccard_cumulative(
            successors=successors,
            retired_dirs=(),
            prefix="temporal_shadow_holdout_v",
            cohort_kind="prior canonical holdout",
        )


def test_fresh_holdout_span_and_semantic_fingerprints_disjoint_from_retired_and_earlier_successors() -> (
    None
):
    """Fresh holdout successors must stay disjoint from retired dirs and earlier successors."""
    successors = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_holdout_v",
        last_retired_version=LAST_RETIRED_HOLDOUT_VERSION,
    )
    if not successors:
        return
    prior_semantic: set[tuple] = set()
    prior_span_text: set[str] = set()
    for folder in PRIOR_CANONICAL_COHORT_DIRS:
        if not folder.is_dir():
            continue
        evidence = _case_evidence_by_id(folder)
        for assertion in _load_assertions(folder):
            prior_semantic.add(_semantic_proposition_fingerprint(assertion))
            prior_span_text |= _source_span_text_fingerprints(assertion, evidence)

    for successor in _sorted_by_version(successors, prefix="temporal_shadow_holdout_v"):
        _require_fresh_cohort(successor)
        evidence = _case_evidence_by_id(successor)
        successor_semantic = {
            _semantic_proposition_fingerprint(a) for a in _load_assertions(successor)
        }
        successor_span_text: set[str] = set()
        for assertion in _load_assertions(successor):
            successor_span_text |= _source_span_text_fingerprints(assertion, evidence)

        semantic_overlap = successor_semantic & prior_semantic
        assert not semantic_overlap, sorted(semantic_overlap)[:5]
        span_overlap = successor_span_text & prior_span_text
        assert not span_overlap, sorted(span_overlap)[:5]

        prior_semantic |= successor_semantic
        prior_span_text |= successor_span_text


def test_fresh_holdout_overlays_reject_gate_e3_and_postponement_value_defects() -> None:
    """Fresh holdout gold overlays must not encode Gate E3 or postponement-value defects."""
    fresh_dirs = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_holdout_v",
        last_retired_version=LAST_RETIRED_HOLDOUT_VERSION,
    )
    if not fresh_dirs:
        return
    for fresh_dir in fresh_dirs:
        _require_fresh_cohort(fresh_dir)
        gold = json.loads((fresh_dir / "gold-overlay.json").read_text(encoding="utf-8"))
        base = json.loads((fresh_dir / "base-contribution.json").read_text(encoding="utf-8"))
        by_id = {a["assertion_id"]: a for a in base.get("candidate_assertions", [])}
        evidence = _case_evidence_by_id(fresh_dir)
        for ann in gold.get("annotations", []):
            if ann.get("interpretation_status") != "resolved":
                continue
            valid_time = ann.get("valid_time") or {}
            valid_start = valid_time.get("start")
            valid_end = valid_time.get("end")
            assertion_id = ann.get("base_assertion_id")
            assertion = by_id.get(assertion_id) if isinstance(assertion_id, str) else None
            if assertion is not None and (valid_start is not None or valid_end is not None):
                resolved_sources: list[str] = []
                for evidence_id in assertion.get("evidence_ref_ids") or []:
                    entry = evidence.get(evidence_id)
                    if entry is None:
                        continue
                    resolved_sources.append(_resolved_span_text(entry))
                if valid_start is not None and resolved_sources:
                    if not _any_evidence_narrates_boundary(resolved_sources):
                        raise AssertionError(
                            f"{fresh_dir.name}: Gate E3 defect on {assertion_id!r} — "
                            "valid_time.start lacks any evidence span that narrates "
                            "the boundary transition"
                        )
                if valid_end is not None and resolved_sources:
                    if not _any_evidence_narrates_boundary(resolved_sources):
                        raise AssertionError(
                            f"{fresh_dir.name}: Gate E3 defect on {assertion_id!r} — "
                            "valid_time.end lacks any evidence span that narrates "
                            "the boundary transition"
                        )
            occ_time = ann.get("occurrence_time") or {}
            occ_point = occ_time.get("point") or {}
            raw_expression = str(occ_point.get("raw_expression") or "")
            if raw_expression and assertion is not None:
                proposition = str(assertion.get("label") or "")
                if _postponement_occurrence_uses_reschedule_time(
                    proposition, raw_expression
                ):
                    raise AssertionError(
                        f"{fresh_dir.name}: postponement-value defect on "
                        f"{assertion_id!r} — occurrence uses reschedule time "
                        f"{raw_expression!r}"
                    )


def test_discover_cohorts_above_retired_cutoff_ignores_prior_membership(
    tmp_path: Path,
) -> None:
    """PRIOR tuple membership must not disable fresh-cohort guards."""
    (tmp_path / "temporal_shadow_adversarial_v11").mkdir()
    v12 = tmp_path / "temporal_shadow_adversarial_v12"
    v12.mkdir()
    discovered = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_adversarial_v",
        last_retired_version=LAST_RETIRED_ADVERSARIAL_VERSION,
        examples_root=tmp_path,
    )
    assert discovered == [v12]

    (tmp_path / "temporal_shadow_adversarial_v12b").mkdir()
    with pytest.raises(AssertionError, match="non-numeric"):
        _discover_cohorts_above_retired_cutoff(
            prefix="temporal_shadow_adversarial_v",
            last_retired_version=LAST_RETIRED_ADVERSARIAL_VERSION,
            examples_root=tmp_path,
        )


def test_discover_cohorts_above_retired_cutoff_empty_when_only_retired_versions() -> None:
    """Real examples tree with no versions above cutoff yields an empty list."""
    discovered = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_holdout_v",
        last_retired_version=LAST_RETIRED_HOLDOUT_VERSION,
    )
    assert discovered == []


def test_v13_and_v11_ids_mutually_disjoint() -> None:
    _require_fresh_cohort(HOLDOUT_V13)
    _require_fresh_cohort(ADV_V11)
    v13_a, v13_e = _collect_ids(HOLDOUT_V13)
    v11_a, v11_e = _collect_ids(ADV_V11)
    assert v13_a.isdisjoint(v11_a)
    assert v13_e.isdisjoint(v11_e)


def test_regression_cohorts_exclude_evaluation_cohort_tag() -> None:
    """Retired regression cohorts (V13/Adv V11) must still exclude cohort_tag."""
    for folder in (HOLDOUT_V13, ADV_V11):
        _require_fresh_cohort(folder)
        base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
        for assertion in base.get("candidate_assertions", []):
            value = assertion.get("value") or {}
            assert "cohort_tag" not in value


_AMBIGUOUS_TEMPORAL_CUES = (
    "holds",
    "recovered",
    "opened",
    "sealed",
    "emerges",
    "arrived",
    "began",
    "became",
    "schedule",
    "broke",
    "imprisoned",
    "performed",
    "tracking",
    "charm",
    "followed",
    "proposed",
    "voted",
    "warden",
    "elected",
    "announced",
)
_IDENTITY_ONLY_MARKERS = (
    "is from",
    "or from a",
    "entity mention",
    "origin_is",
    "classification",
    "porcelain",
    "fake",
    "extinct lineage",
)


def test_holdout_v13_regression_gold_covers_required_lane_classes() -> None:
    """Regression fixture lane coverage for sealed V13 gold — not promotion authority."""
    _require_fresh_cohort(HOLDOUT_V13)
    gold = json.loads((HOLDOUT_V13 / "gold-overlay.json").read_text(encoding="utf-8"))
    annotations = gold.get("annotations", [])
    assert len(annotations) >= 12
    base = json.loads((HOLDOUT_V13 / "base-contribution.json").read_text(encoding="utf-8"))
    by_id = {a["assertion_id"]: a for a in base.get("candidate_assertions", [])}

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
        if status_of(ann) != "ambiguous":
            continue
        assertion = by_id[ann["base_assertion_id"]]
        blob = " ".join(
            str(assertion.get(k) or "") for k in ("label", "predicate", "assertion_kind")
        ).lower()
        assert (" or " in blob) or ("either" in blob) or ("/" in blob), assertion.get("label")
        assert any(cue in blob for cue in _AMBIGUOUS_TEMPORAL_CUES), assertion.get("label")
        assert not any(marker in blob for marker in _IDENTITY_ONLY_MARKERS), assertion.get("label")
    for ann in annotations:
        assert any(str(d).strip() for d in (ann.get("diagnostics") or []))
        if status_of(ann) in {"not_applicable", "unresolved", "ambiguous"}:
            assert ann.get("occurrence_time") is None
            assert ann.get("valid_time") is None


def test_gold_audit_files_exist_for_retired_regression_cohorts() -> None:
    for folder in (HOLDOUT_V13, ADV_V11):
        _require_fresh_cohort(folder)
        assert (folder / "GOLD-AUDIT.md").is_file()


def _parse_gold_audit_assertion_ids(audit_text: str) -> set[str]:
    return set(re.findall(r"`(assertion:[0-9a-f]+)`", audit_text))


def _gold_status_from_audit_row(row: str) -> str:
    cells = [cell.strip() for cell in row.split("|") if cell.strip()]
    # Table columns: ID, proposition, Gate B, class, Gold status, ...
    return cells[4]


def _gold_audit_row_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.split("|") if cell.strip()]


def _audit_backtick_phrase(cell: str) -> str:
    match = re.search(r"`([^`]+)`", cell)
    assert match is not None, cell
    return match.group(1)


def test_retired_regression_gold_audit_matches_base_and_overlay() -> None:
    """Binding proves fixture consistency only — not Gate-faithfulness."""
    for folder in (HOLDOUT_V13, ADV_V11):
        _require_fresh_cohort(folder)
        audit_text = (folder / "GOLD-AUDIT.md").read_text(encoding="utf-8")
        audit_ids = _parse_gold_audit_assertion_ids(audit_text)
        base = json.loads((folder / "base-contribution.json").read_text(encoding="utf-8"))
        gold = json.loads((folder / "gold-overlay.json").read_text(encoding="utf-8"))
        base_by_id = {a["assertion_id"]: a for a in base.get("candidate_assertions", [])}
        base_ids = set(base_by_id)
        overlay_by_id = {a["base_assertion_id"]: a for a in gold.get("annotations", [])}

        assert audit_ids, folder.name
        assert audit_ids.issubset(base_ids), sorted(audit_ids - base_ids)
        assert base_ids.issubset(audit_ids), sorted(base_ids - audit_ids)

        for row in audit_text.splitlines():
            if not row.startswith("| `assertion:"):
                continue
            cells = _gold_audit_row_cells(row)
            aid_match = re.search(r"`(assertion:[0-9a-f]+)`", row)
            assert aid_match is not None, row
            aid = aid_match.group(1)
            status = cells[4]
            overlay = overlay_by_id[aid]
            base_assertion = base_by_id[aid]
            assert overlay["interpretation_status"] == status, (folder.name, aid, status)
            assert cells[1] == base_assertion.get("label"), (folder.name, aid, cells[1])

            lane_cell = cells[5].lower()
            has_occurrence = overlay.get("occurrence_time") is not None
            vt = overlay.get("valid_time") or {}
            has_valid_start = isinstance(vt, dict) and vt.get("start") is not None
            has_valid_end = isinstance(vt, dict) and vt.get("end") is not None
            if "occurrence" in lane_cell:
                assert has_occurrence, (folder.name, aid, lane_cell)
            if "valid-start" in lane_cell:
                assert has_valid_start, (folder.name, aid, lane_cell)
            if "valid-end" in lane_cell:
                assert has_valid_end, (folder.name, aid, lane_cell)
            if lane_cell.strip() == "none":
                assert not has_occurrence and not has_valid_start and not has_valid_end, (
                    folder.name,
                    aid,
                    lane_cell,
                )

            phrase = _audit_backtick_phrase(cells[6])
            source_phrase = str(overlay.get("source_phrase") or "")
            assert phrase == source_phrase or phrase in source_phrase, (
                folder.name,
                aid,
                phrase,
                source_phrase,
            )


def test_gate_e3_audit_requires_positive_boundary_narration() -> None:
    """Acceptance is positive boundary proof, not absence of resulting-state markers."""
    boundary = "When they became mayor, the council stopped meeting at dawn."
    state_only = (
        "They are a group of humans that no longer feel represented in the city "
        "and want to cause as much trouble as possible."
    )
    # Neutral restatement: neither resulting-state marker nor boundary cue.
    neutral = "The treaty is in effect during Session 8."

    assert _source_narrates_boundary(boundary)
    assert not _source_narrates_boundary(state_only)
    assert not _source_narrates_boundary(neutral)

    assert _any_evidence_narrates_boundary([boundary, state_only])
    assert _any_evidence_narrates_boundary([boundary, neutral])
    assert not _any_evidence_narrates_boundary([state_only])
    assert not _any_evidence_narrates_boundary([neutral])
    assert not _any_evidence_narrates_boundary([state_only, neutral])
    assert not _any_evidence_narrates_boundary([])

    # Diagnostic heuristic may remain, but must not be the acceptance condition.
    assert not _all_evidence_is_resulting_state_without_boundary([boundary, state_only])
    assert _all_evidence_is_resulting_state_without_boundary([state_only])
    # Neutral prose fails positive proof even though it is not a "resulting-state" hit.
    assert not _all_evidence_is_resulting_state_without_boundary([neutral])
    assert not _any_evidence_narrates_boundary([neutral])


def test_gate_e3_audit_rejects_source_time_for_resulting_state_report() -> None:
    source = (
        "They are a group of humans that no longer feel represented in the city "
        "and want to cause as much trouble as possible."
    )
    assert _source_reports_resulting_state_without_narrated_boundary(source)
    assert not _source_narrates_boundary(source)
    # Resolving valid_end=session for this phrase is NOT Gate-E3-faithful.


def test_proposition_first_value_audit_rejects_reschedule_as_postponement_occurrence() -> None:
    proposition = "The council raid on the compromised guardhouse has been postponed until dawn"
    raw_expression = "postponed until dawn"
    assert _postponement_occurrence_uses_reschedule_time(proposition, raw_expression)


def test_holdout_v13_retains_observed_gate_e3_and_postponement_value_defects() -> None:
    """Retained as regression evidence; do not patch gold."""
    _require_fresh_cohort(HOLDOUT_V13)
    gold = json.loads((HOLDOUT_V13 / "gold-overlay.json").read_text(encoding="utf-8"))
    base = json.loads((HOLDOUT_V13 / "base-contribution.json").read_text(encoding="utf-8"))
    by_id = {a["assertion_id"]: a for a in base.get("candidate_assertions", [])}
    overlay_by_id = {a["base_assertion_id"]: a for a in gold.get("annotations", [])}
    evidence = _case_evidence_by_id(HOLDOUT_V13)

    rebels_id = "assertion:f59b518d7e4767f6"
    rebels_ann = overlay_by_id[rebels_id]
    assert rebels_ann["interpretation_status"] == "resolved"
    valid_end = (rebels_ann.get("valid_time") or {}).get("end") or {}
    assert valid_end.get("session_id") == "session-7"
    assert "no longer feel represented" in str(rebels_ann.get("source_phrase") or "")

    rebels_evidence_id = (by_id[rebels_id].get("evidence_ref_ids") or [None])[0]
    rebels_source = _resolved_span_text(evidence[rebels_evidence_id])
    assert _source_reports_resulting_state_without_narrated_boundary(rebels_source)
    assert not _source_narrates_boundary(rebels_source)
    assert not _any_evidence_narrates_boundary([rebels_source])

    postpone_id = "assertion:d25ec476e8268f16"
    postpone_ann = overlay_by_id[postpone_id]
    assert postpone_ann["interpretation_status"] == "resolved"
    occ_point = ((postpone_ann.get("occurrence_time") or {}).get("point") or {})
    raw_expression = str(occ_point.get("raw_expression") or "")
    assert "postponed until dawn" in raw_expression

    postpone_assertion = by_id[postpone_id]
    proposition = str(postpone_assertion.get("label") or "")
    assert _postponement_occurrence_uses_reschedule_time(proposition, raw_expression)


def test_resolved_span_text_rejects_line_beyond_eof() -> None:
    fixture_dir = REPO_ROOT / "tests" / "_span_eof_fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    source = fixture_dir / "two-line.md"
    source.write_text("alpha\nbeta\n", encoding="utf-8")
    rel = source.relative_to(REPO_ROOT).as_posix()
    try:
        entry = {
            "evidence_ref_id": "evidence:test:beyond-eof",
            "source_artifact_path": rel,
            "start_line": 3,
            "end_line": 3,
        }
        with pytest.raises(AssertionError, match="beyond EOF"):
            _resolved_span_text(entry)

        entry_start = {
            "evidence_ref_id": "evidence:test:start-beyond-eof",
            "source_artifact_path": rel,
            "start_line": 4,
            "end_line": 4,
        }
        with pytest.raises(AssertionError, match="beyond EOF"):
            _resolved_span_text(entry_start)

        # Valid start with end past EOF must fail closed (no silent slice truncate).
        entry_end = {
            "evidence_ref_id": "evidence:test:end-beyond-eof",
            "source_artifact_path": rel,
            "start_line": 1,
            "end_line": 5,
        }
        with pytest.raises(AssertionError, match="beyond EOF"):
            _resolved_span_text(entry_end)
    finally:
        source.unlink(missing_ok=True)
        if fixture_dir.is_dir() and not any(fixture_dir.iterdir()):
            fixture_dir.rmdir()
