"""Immutable, bounded rules evidence lookup. No inference or World graph authority."""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Label = Annotated[str, Field(min_length=1, max_length=500)]
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_EXCERPT_BYTES = 16 * 1024
SEED_DIGEST = "ce1e7319873eab278c305a102c91f1691006b63bc636fe5cabd3fe37d3cf5493"
# New corpus admission changes this reviewed allowlist; callers never supply paths.
ADMITTED_BUNDLES = ((SEED_DIGEST, Path(__file__).resolve().parents[1] / "resources/rules/srd_occupancy_v1.json"),)

class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

class SourceExport(ClosedModel):
    repository: Label
    revision: Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]

class RulesUnit(ClosedModel):
    unit_id: Digest
    text: Annotated[str, Field(min_length=1, max_length=8192)]
    text_sha256: Digest
    stage_b_content_hash: Digest
    page_fingerprint: Digest
    gate_passed: Literal[True]
    section: Label
    source_title: Label
    source_uri: Annotated[str, Field(pattern=r"^https://[^\s]+$", max_length=1000)]
    source_sha256: Digest
    pdf_page_index: Annotated[int, Field(ge=0, le=100000)]
    printed_page: Annotated[int, Field(ge=1, le=100000)] | None

    @field_validator("gate_passed", mode="before")
    @classmethod
    def passed_gate(cls, value):
        if value is not True:
            raise ValueError("Rules evidence must pass extraction gates")
        return value

class RulesBundle(ClosedModel):
    schema_: Literal["dmb_rules_evidence_bundle_v1"] = Field(alias="schema")
    ruleset_id: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,80}$")]
    title: Label
    coverage: Annotated[str, Field(min_length=1, max_length=1000)]
    source_export: SourceExport
    attribution: Annotated[str, Field(min_length=1, max_length=2000)]
    units: Annotated[list[RulesUnit], Field(min_length=1, max_length=10000)]

class RulesCorpusUnavailable(Exception):
    pass

@lru_cache(maxsize=8)
def load_bundle(digest: str, path: Path) -> RulesBundle:
    try:
        # Bound the actual read, not only a potentially racy preceding stat.
        with path.open("rb") as stream:
            raw = stream.read(MAX_BUNDLE_BYTES + 1)
        if len(raw) > MAX_BUNDLE_BYTES or sha256(raw).hexdigest() != digest:
            raise ValueError("bundle integrity")
        bundle = RulesBundle.model_validate_json(raw)
        ids = set()
        for unit in bundle.units:
            if unit.unit_id in ids or sha256(unit.text.encode()).hexdigest() != unit.text_sha256:
                raise ValueError("unit integrity")
            ids.add(unit.unit_id)
        return bundle
    except (OSError, ValueError, ValidationError) as exc:
        raise RulesCorpusUnavailable from exc

def admitted_bundle(corpus: str) -> RulesBundle:
    if not 1 <= len(ADMITTED_BUNDLES) <= 8 or len({d for d, _ in ADMITTED_BUNDLES}) != len(ADMITTED_BUNDLES):
        raise RulesCorpusUnavailable
    for digest, path in ADMITTED_BUNDLES:
        if corpus == digest:
            return load_bundle(digest, path)
    raise RulesCorpusUnavailable

def catalog() -> dict:
    entries = []
    if not 1 <= len(ADMITTED_BUNDLES) <= 8:
        raise RulesCorpusUnavailable
    for digest, _ in ADMITTED_BUNDLES:
        try:
            bundle = admitted_bundle(digest)
            entries.append({"corpus": digest, "available": True, "ruleset_id": bundle.ruleset_id,
                            "title": bundle.title, "coverage": bundle.coverage, "unit_count": len(bundle.units)})
        except RulesCorpusUnavailable:
            entries.append({"corpus": digest, "available": False})
    return {"schema": "dmb_rules_catalog_v1", "sources": entries}

def normalize_query(question: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", question).casefold().split())

_STOP_WORDS = frozenset("a an the i my me you your can could would should is are was were be been do does did to of in on at by for with as and or if it its they them their that this what how when which rule rules".split())
def _terms(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", normalize_query(text), re.UNICODE)) - _STOP_WORDS

def citation_id(corpus: str, unit: RulesUnit) -> str:
    return sha256(json.dumps([corpus, unit.unit_id, unit.text_sha256], separators=(",", ":")).encode()).hexdigest()

def _identity(corpus: str, bundle: RulesBundle, unit: RulesUnit) -> dict:
    return {"citation_id": citation_id(corpus, unit), "corpus": corpus, "ruleset_id": bundle.ruleset_id,
            "unit_id": unit.unit_id, "text_sha256": unit.text_sha256, "section": unit.section,
            "source_title": unit.source_title, "source_uri": unit.source_uri, "source_sha256": unit.source_sha256,
            "page_fingerprint": unit.page_fingerprint, "pdf_page_index": unit.pdf_page_index, "printed_page": unit.printed_page}

def query_rules(corpus: str, question: str, limit: int = 4) -> dict:
    if not isinstance(question, str) or not 1 <= len(question) <= 800 or not question.strip() or not 1 <= limit <= 8:
        raise ValueError("Invalid rules query")
    return _query_rules(corpus, question, limit)


def query_plan_rules(corpus: str, question: str) -> dict:
    """Internal Plan decision reader, called only after typed APP authorization.

    This is not exposed by the HTTP route or native tool. Their existing input
    contracts remain at query_rules/LookupRulesArguments. Exact Plan question
    identity, ledger and packet storage are checked by the authorizing broker.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Invalid Plan Rules query")
    return _query_rules(corpus, question, 4)


def _query_rules(corpus: str, question: str, limit: int) -> dict:
    bundle = admitted_bundle(corpus)
    normalized = normalize_query(question)
    terms = _terms(normalized)
    # Conservative lexical discovery. No match and truncated coverage are explicit.
    ranked = []
    for unit in bundle.units:
        matched = terms & _terms(unit.text + " " + unit.section)
        if matched:
            score = len(matched) + len(terms & _terms(unit.section))
            ranked.append((-score, unit.unit_id, unit))
    ranked.sort(key=lambda item: (item[0], item[1]))
    hits = []
    remaining = MAX_EXCERPT_BYTES
    for _, _, unit in ranked[:limit]:
        excerpt = unit.text[:1400]
        if len(excerpt.encode()) > remaining:
            break
        remaining -= len(excerpt.encode())
        hits.append({**_identity(corpus, bundle, unit), "excerpt": excerpt, "excerpt_start": 0,
                     "excerpt_end": len(excerpt), "excerpt_complete": len(excerpt) == len(unit.text)})
    return {"schema": "dmb_rules_lookup_packet_v1", "corpus": corpus, "ruleset_id": bundle.ruleset_id,
            "query_id": sha256(json.dumps([corpus, normalized, limit], ensure_ascii=False).encode()).hexdigest(),
            "normalized_query": normalized, "status": "evidence" if hits else "no_evidence",
            "coverage": bundle.coverage, "coverage_status": "limited", "hits": hits,
            "additional_matches": len(ranked) > len(hits)}

def inspect_passage(corpus: str, citation: str) -> dict | None:
    bundle = admitted_bundle(corpus)
    for unit in bundle.units:
        if citation_id(corpus, unit) == citation:
            return {"schema": "dmb_rules_passage_v1", **_identity(corpus, bundle, unit),
                    "text": unit.text, "attribution": bundle.attribution}
    return None
