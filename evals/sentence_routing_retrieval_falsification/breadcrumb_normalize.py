"""Normalize inline recap breadcrumbs into source-anchored session-memory records.

Fails closed when plain prose (tags stripped) drifts from the canonical recap body or
when tagged fragments cannot be aligned to ``SentenceUnit`` slices from
``capture_sentence_units``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import blake3

from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    ALLOWED_TAG_TYPES,
    TAG_RE,
    normalize_corpus_route,
    parse_frontmatter_and_body,
    parse_inline_tags,
    route_exists,
)
from evals.sentence_routing_retrieval_falsification.capture import (
    SentenceUnit,
    capture_sentence_units,
)

SCHEMA_RECORD_V1 = "dmb_session_memory_record_v1"

# Frontmatter metadata records concatenate many route-derived tokens; dedupe + cap keeps
# lexical_plain usable for humans and expands retrieval signal without endless repeats.
_METADATA_LEXICAL_MAX_PARTS = 96

_RE_SOURCE_RECAP = re.compile(
    r"^\s*source_recap_path:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE
)
_RE_CAMPAIGN_ID = re.compile(r"^\s*campaign_id:\s*(\S+)\s*$", re.MULTILINE)
_RE_SESSION_NUM = re.compile(r"^\s*number:\s*(\d+)\s*$", re.MULTILINE)
_RE_FM_ROUTE = re.compile(
    r"^\s*(?:route|proposed_route):\s*[\"']([^\"']+)[\"']\s*$", re.MULTILINE
)
_RE_PROPOSED_ROUTE_ONLY = re.compile(
    r"^\s*proposed_route:\s*[\"']([^\"']+)[\"']\s*$", re.MULTILINE
)
_PRONOUN_RE = re.compile(
    r"\b(she|her|hers|he|him|his|they|them|their|theirs|it|its)\b",
    re.IGNORECASE,
)
_PRONOUN_HANDLE_ELIGIBLE_SUBJECTS = {"PC", "NPC", "Party"}
_PRONOUN_HANDLE_MAX_TERMS = 8


class BreadcrumbNormalizeError(Exception):
    """Artifact cannot be normalized without violating alignment or closure rules."""


def normalize_for_alignment(text: str) -> str:
    """Whitespace + light punctuation normalization for recap vs breadcrumb equality."""
    s = unicodedata.normalize("NFKC", text)
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    # Recaps sometimes omit space after . or ! before a capital word at a segment
    # boundary; sentence-unit joints concatenate without whitespace, so this must
    # match full-body normalization (blank lines collapse to a single space).
    s = re.sub(r"([.!])([A-Z])", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_meta_from_frontmatter(frontmatter: str) -> dict[str, Any]:
    """Regex-only YAML subset (no PyYAML dependency)."""
    m_path = _RE_SOURCE_RECAP.search(frontmatter)
    if not m_path:
        raise BreadcrumbNormalizeError("frontmatter missing source_recap_path")
    m_cid = _RE_CAMPAIGN_ID.search(frontmatter)
    if not m_cid:
        raise BreadcrumbNormalizeError("frontmatter missing campaign_id")
    m_sess = _RE_SESSION_NUM.search(frontmatter)
    if not m_sess:
        raise BreadcrumbNormalizeError("frontmatter missing session.number")
    return {
        "source_recap_path": m_path.group(1).strip().strip('"').strip("'"),
        "campaign_id": m_cid.group(1).strip().strip('"').strip("'"),
        "session_number": int(m_sess.group(1)),
    }


def extract_frontmatter_route_allowlist(frontmatter: str) -> set[str]:
    """Routes declared in frontmatter (entity_index, parties, open questions)."""
    out: set[str] = set()
    for m in _RE_FM_ROUTE.finditer(frontmatter):
        out.add(normalize_corpus_route(m.group(1)))
    return out


def extract_frontmatter_proposed_routes(frontmatter: str) -> set[str]:
    """Hub paths only promised in YAML (``proposed_route``), may not exist on disk yet."""
    return {
        normalize_corpus_route(m.group(1)) for m in _RE_PROPOSED_ROUTE_ONLY.finditer(frontmatter)
    }


def _yaml_list_section(frontmatter: str, section_name: str, *, indent: int = 2) -> list[dict[str, str]]:
    """Extract a tiny YAML list-of-maps subset from a known frontmatter section.

    The breadcrumb artifact intentionally keeps its machine-facing indexes in simple
    YAML. A small parser here avoids adding a dependency while keeping query metadata
    grounded in ingested frontmatter, not benchmark gold.
    """
    lines = frontmatter.splitlines()
    header_re = re.compile(rf"^ {{{indent}}}{re.escape(section_name)}:\s*$")
    next_peer_re = re.compile(rf"^ {{{indent}}}[A-Za-z0-9_]+:\s*")
    item_re = re.compile(rf"^ {{{indent + 2}}}-\s+([A-Za-z0-9_]+):\s*(.+?)\s*$")
    child_re = re.compile(rf"^ {{{indent + 4}}}([A-Za-z0-9_]+):\s*(.+?)\s*$")
    in_section = False
    out: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in lines:
        if not in_section:
            if header_re.match(line):
                in_section = True
            continue
        if next_peer_re.match(line):
            break
        item = item_re.match(line)
        if item:
            if cur:
                out.append(cur)
            cur = {item.group(1): _clean_yaml_scalar(item.group(2))}
            continue
        child = child_re.match(line)
        if child and cur is not None:
            cur[child.group(1)] = _clean_yaml_scalar(child.group(2))
    if cur:
        out.append(cur)
    return out


def _clean_yaml_scalar(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _route_terms(route: str) -> list[str]:
    """Lexical route handles suitable for deterministic retrieval."""
    terms: list[str] = []
    cleaned = normalize_corpus_route(route).strip("/")
    for part in cleaned.split("/"):
        stem = Path(part).stem
        for raw in re.split(r"[_\-\s]+", stem):
            token = raw.strip().lower()
            if len(token) >= 2:
                terms.append(token)
        phrase = re.sub(r"[_\-]+", " ", stem).strip().lower()
        if phrase and phrase not in terms:
            terms.append(phrase)
    return terms


def _route_leaf_terms(route: str) -> list[str]:
    """Compact lexical handles from a route's leaf segment only."""
    cleaned = normalize_corpus_route(route).strip("/")
    if not cleaned:
        return []
    leaf = Path(cleaned.split("/")[-1]).stem
    parts = [p.strip().lower() for p in re.split(r"[_\-\s]+", leaf) if p.strip()]
    if not parts:
        return []
    terms: list[str] = []
    for token in parts:
        if len(token) >= 3:
            terms.append(token)
    phrase = " ".join(parts).strip()
    if len(parts) >= 2 and phrase and phrase not in terms:
        terms.append(phrase)
    return terms


def _dedupe_cap_lexical_parts(parts: Iterable[str], *, max_parts: int) -> list[str]:
    """Stable dedupe by normalized lowercase key, then cap count (metadata records only)."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in parts:
        piece = str(raw or "").strip()
        if not piece:
            continue
        normalized_piece = normalize_for_alignment(piece)
        key = normalized_piece.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized_piece)
        if len(out) >= max_parts:
            break
    return out


def _metadata_record(
    *,
    meta: dict[str, Any],
    source_path: str,
    unit_id: str,
    lexical_parts: list[str],
    routes: list[RouteAttachment],
) -> NormalizedRecord:
    capped = _dedupe_cap_lexical_parts(lexical_parts, max_parts=_METADATA_LEXICAL_MAX_PARTS)
    lexical_plain = normalize_for_alignment(" ".join(capped))
    return NormalizedRecord(
        campaign_id=meta["campaign_id"],
        session_number=meta["session_number"],
        source_recap_path=source_path,
        unit_id=unit_id,
        line_start=0,
        line_end=0,
        text_blake3=text_blake3_hex(lexical_plain),
        lexical_plain=lexical_plain,
        routes=routes,
    )


def build_frontmatter_metadata_records(
    *,
    frontmatter: str,
    meta: dict[str, Any],
    source_path: str,
) -> list[NormalizedRecord]:
    """Build session-level retrieval records from ingested frontmatter indexes.

    These records give natural GM questions a grounded first-pass target such as
    "locations" or "open loops" without using scenario gold or handwritten per-query
    aliases. The payload is derived from the breadcrumb artifact's own entity index.
    """
    out: list[NormalizedRecord] = []

    location_items = _yaml_list_section(frontmatter, "locations", indent=2)
    candidate_items = [
        item
        for item in _yaml_list_section(frontmatter, "new_hub_candidates", indent=2)
        if item.get("subject_type", "").strip().lower() == "location"
    ]
    location_routes: list[RouteAttachment] = []
    location_terms: list[str] = ["session", "locations", "location", "places", "place", "setting", "map"]
    seen_routes: set[str] = set()
    for item in location_items + candidate_items:
        raw_route = item.get("route") or item.get("proposed_route") or ""
        if not raw_route:
            continue
        norm_route = normalize_corpus_route(raw_route)
        if norm_route in seen_routes:
            continue
        seen_routes.add(norm_route)
        proposed = "proposed_route" in item
        location_routes.append(
            RouteAttachment(
                subject_class="Location",
                normalized_route=norm_route,
                proposed=proposed,
                tag_kind="frontmatter",
            )
        )
        location_terms.extend([item.get("slug", ""), item.get("rationale", "")])
        location_terms.extend(_route_terms(norm_route))
    if location_routes:
        out.append(
            _metadata_record(
                meta=meta,
                source_path=source_path,
                unit_id=f"meta-session-{meta['session_number']:04d}-locations",
                lexical_parts=location_terms,
                routes=location_routes,
            )
        )

    open_question_items = _yaml_list_section(frontmatter, "unresolved_open_questions", indent=0)
    open_routes: list[RouteAttachment] = []
    open_terms: list[str] = [
        "session",
        "unresolved",
        "open",
        "questions",
        "loops",
        "open loops",
        "actionable",
        "follow up",
        "next session",
    ]
    seen_open_routes: set[str] = set()
    for item in open_question_items:
        raw_route = item.get("proposed_route") or item.get("route") or ""
        if not raw_route:
            continue
        norm_route = normalize_corpus_route(raw_route)
        if norm_route in seen_open_routes:
            continue
        seen_open_routes.add(norm_route)
        open_routes.append(
            RouteAttachment(
                subject_class="NewHubCandidate",
                normalized_route=norm_route,
                proposed="proposed_route" in item,
                tag_kind="frontmatter",
            )
        )
        open_terms.extend([item.get("subject", ""), item.get("question", "")])
        open_terms.extend(_route_terms(norm_route))
    if open_routes:
        out.append(
            _metadata_record(
                meta=meta,
                source_path=source_path,
                unit_id=f"meta-session-{meta['session_number']:04d}-open-loops",
                lexical_parts=open_terms,
                routes=open_routes,
            )
        )
    return out


def record_has_pronoun(text: str) -> bool:
    return bool(_PRONOUN_RE.search(str(text or "")))


def enrich_record_pronoun_route_handles(record: NormalizedRecord) -> NormalizedRecord:
    """Append resolved route-name handles to pronoun-bearing records.

    The inline breadcrumb remains the authority: this does not infer new routes.
    It only makes already-attached entity routes searchable when source prose uses
    pronouns ("She tells Caelynn...") instead of repeating the entity name.
    """
    if record.line_start <= 0:
        return record
    if not record_has_pronoun(record.lexical_plain):
        return record
    seen_terms: set[str] = set()
    handle_terms: list[str] = []
    for route in record.routes:
        if route.subject_class not in _PRONOUN_HANDLE_ELIGIBLE_SUBJECTS:
            continue
        for term in _route_leaf_terms(route.normalized_route):
            key = term.strip().lower()
            if not key or key in seen_terms:
                continue
            seen_terms.add(key)
            handle_terms.append(key)
    if not handle_terms:
        return record

    text_lower = f" {normalize_for_alignment(record.lexical_plain).lower()} "
    missing_terms: list[str] = []
    for term in handle_terms:
        if f" {term} " in text_lower:
            continue
        missing_terms.append(term)
        if len(missing_terms) >= _PRONOUN_HANDLE_MAX_TERMS:
            break
    if not missing_terms:
        return record

    suffix = normalize_for_alignment(" ".join(missing_terms))
    if not suffix:
        return record
    enriched = normalize_for_alignment(f"{record.lexical_plain} resolved pronoun handles {suffix}")
    return NormalizedRecord(
        campaign_id=record.campaign_id,
        session_number=record.session_number,
        source_recap_path=record.source_recap_path,
        unit_id=record.unit_id,
        line_start=record.line_start,
        line_end=record.line_end,
        text_blake3=record.text_blake3,
        lexical_plain=enriched,
        routes=list(record.routes),
    )


def strip_first_markdown_h1(body_plain: str) -> str:
    lines = body_plain.splitlines()
    if lines and lines[0].strip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines)


def strip_leading_heading_lines(md_body: str) -> str:
    """Drop leading markdown heading lines (``capture_sentence_units`` skips them)."""
    lines = md_body.splitlines()
    while lines and lines[0].strip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines)


def split_line_into_tagged_spans(line: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Split one body line into (text_before_tags, [(type, route), ...]) chunks.

    Consecutive ``][`` groups separated only by whitespace attach to the same text span
    (tags accumulate on the previous non-empty prose chunk).
    """
    out: list[tuple[str, list[tuple[str, str]]]] = []
    i = 0
    buf: list[str] = []
    n = len(line)
    while i < n:
        if line[i] == "[":
            m = TAG_RE.match(line, i)
            if m:
                text_part = "".join(buf)
                buf = []
                tags = [(m.group(1), m.group(2))]
                i = m.end()
                while i < n:
                    m2 = TAG_RE.match(line, i)
                    if m2:
                        tags.append((m2.group(1), m2.group(2)))
                        i = m2.end()
                    else:
                        break
                if not text_part.strip() and out:
                    prev_text, prev_tags = out[-1]
                    out[-1] = (prev_text, prev_tags + tags)
                else:
                    out.append((text_part, tags))
                continue
        buf.append(line[i])
        i += 1
    if buf:
        tail = "".join(buf)
        if tail.strip():
            out.append((tail, []))
    return out


def iter_body_fragments(body: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """All (text, tags) fragments in reading order (line breaks preserved in text)."""
    frags: list[tuple[str, list[tuple[str, str]]]] = []
    lines = body.splitlines()
    for li, line in enumerate(lines):
        line_frags = split_line_into_tagged_spans(line)
        for j, (t, tags) in enumerate(line_frags):
            if li > 0 and j == 0 and frags:
                # newline between body lines belongs to first text chunk of next line
                t = "\n" + t
            frags.append((t, tags))
    return frags


def align_fragments_to_units(
    fragments: list[tuple[str, list[tuple[str, str]]]],
    units: list[SentenceUnit],
    *,
    u_joint: str,
    unit_ranges: list[tuple[int, int]],
) -> list[tuple[list[SentenceUnit], list[tuple[str, str]]]]:
    """Map prose fragments to units via spans in ``u_joint``.

    Normalization is **global** (``normalize_for_alignment`` collapses spaces across
    fragment boundaries). Matching each ``normalize(fragment)`` against a slice of
    ``u_joint`` is therefore wrong; we extend a cumulative raw string and take the new
    normalized suffix after each fragment.
    """
    pending_tags: list[tuple[str, str]] = []
    assignments: list[tuple[list[SentenceUnit], list[tuple[str, str]]]] = []
    pos = 0
    cumulative_raw = ""
    prev_full_norm = ""
    for text, tags in fragments:
        eff = pending_tags + tags
        pending_tags = []
        cumulative_raw += text
        full_norm = normalize_for_alignment(cumulative_raw)
        new_suffix = full_norm[len(prev_full_norm) :]
        prev_full_norm = full_norm
        if not new_suffix:
            pending_tags = eff
            continue
        end = pos + len(new_suffix)
        if end > len(u_joint) or u_joint[pos:end] != new_suffix:
            raise BreadcrumbNormalizeError(
                f"fragment does not match recap at normalized offset {pos}: {new_suffix[:80]!r}…"
            )
        hit: list[SentenceUnit] = []
        for i, u in enumerate(units):
            a, b = unit_ranges[i]
            if a < end and b > pos:
                hit.append(u)
        if eff:
            assignments.append((hit, eff))
        pos = end
    if pending_tags:
        raise BreadcrumbNormalizeError(f"trailing orphan tags without text: {pending_tags}")
    if pos != len(u_joint):
        raise BreadcrumbNormalizeError(
            f"fragments did not cover full recap text: consumed {pos}, expected {len(u_joint)}"
        )
    return assignments


def joint_normalized_from_units(units: list[SentenceUnit]) -> str:
    """Canonical joint text for breadcrumb alignment (matches tag-stripped breadcrumb normalization)."""
    inner = "".join(normalize_for_alignment(u.text) for u in units)
    return normalize_for_alignment(inner)


def unit_char_ranges_in_joint(units: list[SentenceUnit], u_joint: str) -> list[tuple[int, int]]:
    """Inclusive-exclusive ``[start, end)`` slices of ``u_joint`` per sentence unit."""
    acc = ""
    prev = 0
    ranges: list[tuple[int, int]] = []
    j_now = ""
    for u in units:
        acc += normalize_for_alignment(u.text)
        j_now = normalize_for_alignment(acc)
        ranges.append((prev, len(j_now)))
        prev = len(j_now)
    if j_now != u_joint:
        raise BreadcrumbNormalizeError("internal error: joint length mismatch building unit ranges")
    return ranges


def verify_global_text_equal(*, breadcrumb_body: str, recap_body: str) -> None:
    plain = TAG_RE.sub("", strip_leading_heading_lines(breadcrumb_body))
    units = capture_sentence_units(recap_text=recap_body, recap_relative_path="__verify__")
    u_joint = joint_normalized_from_units(units)
    p_full = normalize_for_alignment(plain)
    if u_joint != p_full:
        raise BreadcrumbNormalizeError(
            "breadcrumb plain text (tags stripped) does not match recap body after normalization"
        )


def text_blake3_hex(text: str) -> str:
    return blake3.blake3(text.encode("utf-8")).hexdigest()


@dataclass
class RouteAttachment:
    subject_class: str
    normalized_route: str
    proposed: bool
    tag_kind: str = "inline"


@dataclass
class NormalizedRecord:
    campaign_id: str
    session_number: int
    source_recap_path: str
    unit_id: str
    line_start: int
    line_end: int
    text_blake3: str
    """Whitespace-normal recap substring for deterministic lexical retrieval (local artifacts only)."""
    lexical_plain: str
    routes: list[RouteAttachment] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_RECORD_V1,
            "campaign_id": self.campaign_id,
            "session_number": self.session_number,
            "source_recap_path": self.source_recap_path,
            "unit_id": self.unit_id,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "text_blake3": self.text_blake3,
            "lexical_plain": self.lexical_plain,
            "routes": [
                {
                    "subject_class": r.subject_class,
                    "normalized_route": r.normalized_route,
                    "proposed": r.proposed,
                    "tag_kind": r.tag_kind,
                }
                for r in self.routes
            ],
        }


def normalize_breadcrumb_artifact(
    *,
    artifact_text: str,
    corpus_root: Path,
    strict_frontmatter_routes: bool = True,
    enrich_pronoun_route_handles: bool = False,
) -> tuple[list[NormalizedRecord], dict[str, Any]]:
    """Parse breadcrumb markdown and emit one record per SentenceUnit with merged routes."""
    frontmatter, body = parse_frontmatter_and_body(artifact_text)
    if frontmatter is None:
        raise BreadcrumbNormalizeError("missing YAML frontmatter")
    meta = extract_meta_from_frontmatter(frontmatter)
    source_path = meta["source_recap_path"]

    recap_full = (corpus_root / source_path).read_text(encoding="utf-8")
    rf_fm, recap_body = parse_frontmatter_and_body(recap_full)
    _ = rf_fm
    units = capture_sentence_units(recap_text=recap_body, recap_relative_path=source_path)

    body_for_units = strip_leading_heading_lines(body)

    verify_global_text_equal(breadcrumb_body=body, recap_body=recap_body)

    u_joint = joint_normalized_from_units(units)
    unit_ranges = unit_char_ranges_in_joint(units, u_joint)

    unknown = {
        t.tag_type for t in parse_inline_tags(body_for_units) if t.tag_type not in ALLOWED_TAG_TYPES
    }
    if unknown:
        raise BreadcrumbNormalizeError(f"unknown tag types: {sorted(unknown)}")

    fm_routes = extract_frontmatter_route_allowlist(frontmatter)
    proposed_routes = extract_frontmatter_proposed_routes(frontmatter)

    unit_routes: dict[str, list[RouteAttachment]] = defaultdict(list)
    assignments = align_fragments_to_units(
        iter_body_fragments(body_for_units),
        units,
        u_joint=u_joint,
        unit_ranges=unit_ranges,
    )
    for matched, raw_tags in assignments:
        seen_pair: set[tuple[str, str]] = set()
        attachments: list[RouteAttachment] = []
        for tt, route in raw_tags:
            if tt not in ALLOWED_TAG_TYPES:
                raise BreadcrumbNormalizeError(f"disallowed tag {tt}")
            norm_r = normalize_corpus_route(route)
            proposed = tt == "NewHubCandidate" or norm_r in proposed_routes
            if not proposed:
                exists = route_exists(corpus_root, norm_r)
                if not exists:
                    raise BreadcrumbNormalizeError(f"non-candidate route missing on disk: {norm_r}")
                if strict_frontmatter_routes and norm_r not in fm_routes:
                    # Party proposed hubs may appear only under parties.* in YAML — still listed as proposed_route
                    raise BreadcrumbNormalizeError(
                        f"route used in body but not listed in frontmatter index: {norm_r}"
                    )
            attachments.append(
                RouteAttachment(
                    subject_class=tt,
                    normalized_route=norm_r,
                    proposed=proposed,
                    tag_kind="inline",
                )
            )
            key = (tt, norm_r)
            if key in seen_pair:
                continue
            seen_pair.add(key)
        for u in matched:
            for att in attachments:
                unit_routes[u.unit_id].append(att)

    records: list[NormalizedRecord] = []
    for u in units:
        merged = unit_routes.get(u.unit_id, [])
        dedup: dict[tuple[str, str], RouteAttachment] = {}
        for a in merged:
            dedup[(a.subject_class, a.normalized_route)] = a
        routes = list(dedup.values())
        records.append(
            NormalizedRecord(
                campaign_id=meta["campaign_id"],
                session_number=meta["session_number"],
                source_recap_path=source_path,
                unit_id=u.unit_id,
                line_start=u.line_start,
                line_end=u.line_end,
                text_blake3=text_blake3_hex(u.text),
                lexical_plain=normalize_for_alignment(u.text),
                routes=routes,
            )
        )
    metadata_records = build_frontmatter_metadata_records(
        frontmatter=frontmatter,
        meta=meta,
        source_path=source_path,
    )
    records.extend(metadata_records)
    enriched_pronoun_record_count = 0
    if enrich_pronoun_route_handles:
        enriched_records: list[NormalizedRecord] = []
        for record in records:
            enriched = enrich_record_pronoun_route_handles(record)
            if enriched.lexical_plain != record.lexical_plain:
                enriched_pronoun_record_count += 1
            enriched_records.append(enriched)
        records = enriched_records

    meta_out = {
        "source_recap_path": source_path,
        "campaign_id": meta["campaign_id"],
        "session_number": meta["session_number"],
        "unit_count": len(units),
        "metadata_record_count": len(metadata_records),
        "pronoun_route_handle_enrichment_enabled": bool(enrich_pronoun_route_handles),
        "enriched_pronoun_record_count": enriched_pronoun_record_count,
        "records_with_routes": sum(1 for r in records if r.routes),
    }
    return records, meta_out


def write_records_jsonl(records: list[NormalizedRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r.to_json_dict(), ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def build_bundle_v1(
    *,
    records_path: Path,
    campaign_id: str,
    session_number: int,
    source_recap_path: str,
    breadcrumb_artifact_path: str,
) -> dict[str, Any]:
    return {
        "schema": "dmb_session_memory_bundle_v1",
        "campaign_id": campaign_id,
        "session_number": session_number,
        "source_recap_path": source_recap_path,
        "breadcrumb_artifact_path": breadcrumb_artifact_path,
        "records_path": str(records_path.resolve()),
        "query_contract": "candidate_mode_v1",
    }
