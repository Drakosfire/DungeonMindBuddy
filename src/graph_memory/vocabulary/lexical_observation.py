from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import re
from typing import Any, Iterable

from .model import EntityKind, EvidenceRef, LexicalObservation, SourceDomain

EXTRACTION_METHOD = "deterministic_lexical_observation_v1"
_MAX_EVIDENCE_QUOTE_CHARS = 240
_WRAPPING_PUNCTUATION = " \t\n\r\f\v\"'`“”‘’()[]{}<>.,;:!?"
_TITLE_TOKEN_RE = re.compile(r"[A-Z][A-Za-z]*(?:[-'][A-Z][A-Za-z]*)?")
_TITLE_PHRASE_RE = re.compile(r"\b[A-Z][A-Za-z]*(?:[-'][A-Z][A-Za-z]*)?(?:\s+[A-Z][A-Za-z]*(?:[-'][A-Z][A-Za-z]*)?)+\b")

_STOPWORDS = {
    "The",
    "A",
    "An",
    "And",
    "But",
    "Then",
    "When",
    "After",
    "Before",
    "During",
    "This",
    "That",
    "They",
    "Their",
    "North",
    "South",
    "East",
    "West",
}
_ENCOUNTER_TERMS = ("defense", "ambush", "siege", "battle", "fight", "assault", "rescue", "escape")
_COLLECTIVE_TERMS = ("council", "company", "guard", "cult", "chorus", "guild", "order", "clan", "faction")


@dataclass(slots=True)
class VocabularySourceSpan:
    source_artifact_id: str
    text: str
    source_span_ref_id: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    source_domain: SourceDomain | None = None
    scope: str | None = None
    campaign_id: str | None = None
    world_id: str | None = None

    def validate(self) -> None:
        if not self.source_artifact_id.strip():
            raise ValueError("source_artifact_id must be non-empty")
        if self.line_start is not None and self.line_end is not None and self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")


@dataclass(slots=True)
class LexicalObservationPassResult:
    observations: list[LexicalObservation]
    diagnostics: dict[str, Any]


def normalize_observed_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip()).strip(_WRAPPING_PUNCTUATION)
    return normalized.lower()


def _add_surface(result: list[str], seen: set[str], surface: str) -> None:
    cleaned = re.sub(r"\s+", " ", surface.strip()).strip(_WRAPPING_PUNCTUATION)
    normalized = normalize_observed_text(cleaned)
    if cleaned and normalized and normalized not in seen:
        seen.add(normalized)
        result.append(cleaned)


def _phrase_is_candidate(phrase: str) -> bool:
    tokens = phrase.split()
    if not tokens:
        return False
    if len(tokens) > 1:
        directional_starts = {"North", "South", "East", "West"}
        if tokens[0] in _STOPWORDS and tokens[0] not in directional_starts:
            return False
        return all(token not in _STOPWORDS or token in directional_starts for token in tokens)
    return len(tokens[0]) >= 4 and tokens[0] not in _STOPWORDS


def extract_candidate_surfaces(text: str) -> list[str]:
    candidates: list[tuple[int, int, str, bool]] = []
    occupied: list[tuple[int, int]] = []

    for match in _TITLE_PHRASE_RE.finditer(text):
        phrase = match.group(0)
        phrase_start = match.start()
        tokens = phrase.split()
        if tokens and tokens[0] in {"The", "A", "An"} and len(tokens) > 1:
            phrase_start += len(tokens[0]) + 1
            phrase = " ".join(tokens[1:])
        if not _phrase_is_candidate(phrase):
            continue
        candidates.append((phrase_start, match.end(), phrase, True))
        occupied.append((phrase_start, match.end()))

    for match in _TITLE_TOKEN_RE.finditer(text):
        if any(start <= match.start() and match.end() <= end for start, end in occupied):
            continue
        token = match.group(0)
        if len(token) >= 4 and token not in _STOPWORDS:
            candidates.append((match.start(), match.end(), token, False))

    surfaces: list[str] = []
    seen: set[str] = set()
    for _, _, surface, _ in sorted(candidates, key=lambda item: (item[0], item[1])):
        _add_surface(surfaces, seen, surface)
    return surfaces


def _contains_term(normalized_surface: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", normalized_surface) for term in terms)


def infer_observed_kind_hint(surface_text: str, context_text: str = "") -> EntityKind:
    normalized = normalize_observed_text(surface_text)
    context = normalize_observed_text(context_text)

    if _contains_term(normalized, _ENCOUNTER_TERMS):
        return "combat_encounter"
    if _contains_term(normalized, _COLLECTIVE_TERMS):
        return "collective"

    escaped_surface = re.escape(normalized)
    place_patterns = [
        rf"\b(?:at|in|to|from|reached)\s+{escaped_surface}\b",
        rf"\b{escaped_surface}\s+(?:gate|town)\b",
    ]
    if context and any(re.search(pattern, context) for pattern in place_patterns):
        return "place"
    return "unknown"


def make_observation_id(source_artifact_id: str, source_span_ref_id: str | None, surface_text: str, occurrence_index: int) -> str:
    payload = "\n".join(
        [source_artifact_id, source_span_ref_id or "", normalize_observed_text(surface_text), str(occurrence_index)]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"obs:detlex:{digest}"


def _evidence_quote(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= _MAX_EVIDENCE_QUOTE_CHARS:
        return cleaned
    return cleaned[: _MAX_EVIDENCE_QUOTE_CHARS - 1].rstrip() + "…"


def build_lexical_observations_from_spans(
    spans: Iterable[VocabularySourceSpan],
    *,
    extraction_method: str = EXTRACTION_METHOD,
) -> LexicalObservationPassResult:
    observations: list[LexicalObservation] = []
    span_count = 0
    skipped_empty_span_count = 0
    kind_counts: Counter[str] = Counter()
    artifact_counts: Counter[str] = Counter()

    for span in spans:
        span_count += 1
        span.validate()
        if not span.text.strip():
            skipped_empty_span_count += 1
            continue

        seen_in_span: set[tuple[str, EntityKind]] = set()
        occurrence_index = 0
        for surface in extract_candidate_surfaces(span.text):
            kind = infer_observed_kind_hint(surface, span.text)
            normalized = normalize_observed_text(surface)
            dedupe_key = (normalized, kind)
            if dedupe_key in seen_in_span:
                continue
            seen_in_span.add(dedupe_key)

            evidence = EvidenceRef(
                source_artifact_id=span.source_artifact_id,
                source_span_ref_id=span.source_span_ref_id,
                quote=_evidence_quote(span.text),
                line_start=span.line_start,
                line_end=span.line_end,
                confidence=0.75 if kind != "unknown" else 0.55,
            )
            observations.append(
                LexicalObservation(
                    observation_id=make_observation_id(
                        span.source_artifact_id, span.source_span_ref_id, surface, occurrence_index
                    ),
                    source_artifact_id=span.source_artifact_id,
                    source_span_ref_id=span.source_span_ref_id,
                    surface_text=surface,
                    normalized_text=normalized,
                    observed_kind_hint=kind,
                    evidence_refs=[evidence],
                    extraction_method=extraction_method,
                    confidence=0.75 if kind != "unknown" else 0.55,
                )
            )
            occurrence_index += 1
            kind_counts[kind] += 1
            artifact_counts[span.source_artifact_id] += 1

    diagnostics = {
        "span_count": span_count,
        "skipped_empty_span_count": skipped_empty_span_count,
        "observation_count": len(observations),
        "observed_kind_counts": dict(sorted(kind_counts.items())),
        "source_artifact_counts": dict(sorted(artifact_counts.items())),
        "extraction_method": extraction_method,
    }
    return LexicalObservationPassResult(observations=observations, diagnostics=diagnostics)


def observations_to_artifact_payload(observations: Iterable[LexicalObservation]) -> list[dict[str, Any]]:
    return [observation.to_dict() for observation in observations]
