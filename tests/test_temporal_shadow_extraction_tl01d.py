"""TL01D registry, conservative gate prompt, and freeze tests."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from graph_memory.temporal_shadow_extraction import (
    TL01B_PACKET_VERSION,
    TL01C_PACKET_VERSION,
    TL01C_SOURCE_AWARE_INSTRUCTIONS,
    TL01D_CONSERVATIVE_INSTRUCTIONS,
    baseline_prompt_fingerprint,
    compute_prompt_sha256,
    render_temporal_shadow_user_content_v2,
    resolve_prompt_spec,
)
from graph_memory.temporal_shadow_extraction_schema import TEMPORAL_SHADOW_PROMPT_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]

# Frozen at TL01B merge — do NOT recompute from live instructions.
FROZEN_TL01B_INSTRUCTIONS_SHA256 = (
    "c036558b52b8a44e5358fb7f3062dbf9db5b7f5bf86cb7fa2d986e7fddd0ceec"
)
FROZEN_TL01B_PROMPT_SHA256 = (
    "c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51"
)
FROZEN_TL01C_PROMPT_SHA256 = (
    "86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3"
)
# Frozen after TL01D candidate freeze — do NOT recompute from live instructions.
FROZEN_TL01D_PROMPT_SHA256 = (
    "410a2d1ba1f497dc1dcc4904f04f09b119586205533e925ff3d060e21a600bae"
)

TL01D_RESERVED_VOCABULARY = (
    "Dessa",
    "Orun",
    "Caldrin",
    "Glass Causeway",
    "Lantern Court",
    "Ivory Ledger",
)

# Must not appear in TL01D few-shots (observed / prior cohort contamination).
FORBIDDEN_OBSERVED_TERMS = (
    "Stafl",
    "Caelynn",
    "Lysandra",
    "Maelthor",
    "Hybrid",
    "Copper and Quartz",
    "Arin",
    "Nera",
    "Mara",
    "Veyra",
    "Red Company",
    "Jorin",
    "Pella",
    "Tovin",
    "Quill Harbor",
    "Ash Riders",
    "frost seal",
)

REQUIRED_PROMPT_PHRASES = (
    "occurrence_time MUST be null AND valid_time MUST be null",
    "BEFORE inspecting source_context.source_time",
    "Bounded event or change",
    "Persistent state with an explicit boundary",
    "Static structure or topology",
    "Scene, section, or observation framing",
    "Mention or identity ambiguity",
    "reject source_context.source_time",
    "Never reconstruct a session",
    "kind=textual",
    "raw_expression must be a verbatim contiguous substring",
    "valid_time.start",
    "valid_time.end",
)


def test_tl01d_resolves_through_registry_with_packet_and_renderer_v2() -> None:
    spec = resolve_prompt_spec("tl01d-v1")
    assert spec.version == "tl01d-v1"
    assert spec.packet_version == TL01C_PACKET_VERSION
    assert spec.packet_version != TL01B_PACKET_VERSION
    assert spec.render_user_content is render_temporal_shadow_user_content_v2
    assert spec.instructions == TL01D_CONSERVATIVE_INSTRUCTIONS


def test_tl01d_prompt_hash_is_frozen() -> None:
    assert compute_prompt_sha256("tl01d-v1") == FROZEN_TL01D_PROMPT_SHA256


def test_tl01b_and_tl01c_fingerprints_remain_unchanged() -> None:
    fingerprint = baseline_prompt_fingerprint()
    assert fingerprint["prompt_version"] == TEMPORAL_SHADOW_PROMPT_VERSION
    assert fingerprint["instructions_sha256"] == FROZEN_TL01B_INSTRUCTIONS_SHA256
    assert compute_prompt_sha256("tl01b-v1") == FROZEN_TL01B_PROMPT_SHA256
    assert compute_prompt_sha256("tl01c-v1") == FROZEN_TL01C_PROMPT_SHA256
    # Ensure TL01C instructions themselves were not mutated by TL01D work.
    assert (
        hashlib.sha256(TL01C_SOURCE_AWARE_INSTRUCTIONS.encode("utf-8")).hexdigest()
        == "77e6673bab46b06898478cc7ff66d8e15f1ac0701f126120a6606bfbc16504bc"
    )


def test_tl01d_instructions_contain_required_decision_gate_phrases() -> None:
    text = TL01D_CONSERVATIVE_INSTRUCTIONS
    for phrase in REQUIRED_PROMPT_PHRASES:
        assert phrase in text, f"missing required phrase: {phrase!r}"


def test_tl01d_few_shots_have_exactly_one_expected_answer_each() -> None:
    text = TL01D_CONSERVATIVE_INSTRUCTIONS
    examples = re.findall(
        r"Example \d+ — .*?:\n(?:.*\n)*?→ ([^\n]+)",
        text,
    )
    assert len(examples) == 8
    ambiguous_markers = (" or ", " / ", "either")
    for answer in examples:
        lowered = answer.lower()
        assert not any(marker in lowered for marker in ambiguous_markers), answer
        assert "null" in lowered or "resolved" in lowered or "not_applicable" in lowered or "ambiguous" in lowered


def test_tl01d_few_shots_use_reserved_vocabulary() -> None:
    text = TL01D_CONSERVATIVE_INSTRUCTIONS
    for term in TL01D_RESERVED_VOCABULARY:
        assert term in text


def test_tl01d_few_shots_exclude_observed_and_prior_cohort_terms() -> None:
    text = TL01D_CONSERVATIVE_INSTRUCTIONS
    for term in FORBIDDEN_OBSERVED_TERMS:
        assert term not in text, f"tl01d few-shot contaminated by {term!r}"
