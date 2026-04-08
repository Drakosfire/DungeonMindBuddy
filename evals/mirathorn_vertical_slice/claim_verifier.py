from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROVENANCE_LABELS = {"CANON", "OBSERVED", "PREP"}
_WORD_RE = re.compile(r"[a-z0-9']+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_MIN_CLAIM_WORDS = 4


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(_normalize(text)))


def _resolve_model(model: str | None) -> str:
    if model:
        return model
    policy_candidates = [
        Path(__file__).resolve().parents[2] / "MODEL_POLICY.json",
        Path(__file__).resolve().parents[3] / "MODEL_POLICY.json",
    ]
    for policy_path in policy_candidates:
        if policy_path.exists():
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            role = policy.get("actions", {}).get(
                "retrieval_synthesis", "retrieval_synthesis"
            )
            return policy.get("models", {}).get(role, "gpt-5.3-chat-latest")
    return "gpt-5.3-chat-latest"


def _load_api_key() -> str | None:
    project_root = Path(__file__).resolve().parents[2]
    env_candidates = [
        project_root / ".env.development",
        project_root.parents[0] / ".env.development",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(env_file, override=True)
    return os.getenv("OPENAI_API_KEY")


def _extract_provenance_label(text: str) -> str | None:
    upper = text.upper()
    for label in PROVENANCE_LABELS:
        if label in upper:
            return label
    return None


def _is_probably_non_factual(line: str) -> bool:
    low = line.strip().lower()
    if not low:
        return True
    if low.startswith(("tldr:", "tl;dr:", "key attributes")):
        return True
    if low.startswith(("##", "#", "-", "*")) and len(_WORD_RE.findall(low)) < _MIN_CLAIM_WORDS:
        return True
    if low.startswith(("note:", "summary:", "answer:", "question:")):
        return True
    return False


def extract_claims_heuristic(answer: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for raw in _SENTENCE_SPLIT_RE.split(answer):
        line = raw.strip(" -\t")
        if _is_probably_non_factual(line):
            continue
        words = _WORD_RE.findall(line.lower())
        if len(words) < _MIN_CLAIM_WORDS:
            continue
        claims.append(
            {
                "text": line,
                "type": "factual",
                "entity_refs": [],
                "provenance_label": _extract_provenance_label(line),
            }
        )
    return claims


def extract_claims_llm(
    answer: str,
    *,
    model: str | None = None,
    openai_client: Any | None = None,
) -> list[dict[str, Any]]:
    client = openai_client
    if client is None:
        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LLM claim extraction.")
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("OpenAI SDK is required for LLM claim extraction.") from exc
        client = OpenAI(api_key=api_key)

    schema = {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["factual", "interpretive", "structural"],
                        },
                        "entity_refs": {"type": "array", "items": {"type": "string"}},
                        "provenance_label": {
                            "type": ["string", "null"],
                            "enum": ["CANON", "OBSERVED", "PREP", None],
                        },
                    },
                    "required": ["text", "type", "entity_refs", "provenance_label"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["claims"],
        "additionalProperties": False,
    }
    prompt = (
        "Extract atomic claims from this GM assistant answer.\n"
        "Keep factual claims that can be checked against a fact store.\n"
        "Mark interpretive claims when they are judgment/inference.\n"
        "Mark structural claims for formatting-only lines.\n"
        "Return strict JSON matching the schema.\n\n"
        f"ANSWER:\n{answer}"
    )
    response = client.chat.completions.create(
        model=_resolve_model(model),
        messages=[
            {
                "role": "system",
                "content": "You extract factual claims for grounded-answer evaluation.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "claim_extraction", "schema": schema},
        },
    )
    raw = response.choices[0].message.content or "{}"
    payload = json.loads(raw)
    claims = payload.get("claims", [])
    if not isinstance(claims, list):
        return []
    return claims


def build_projection_fact_index(
    projection: dict[str, Any], entities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    entity_meta: dict[str, dict[str, Any]] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        entity_meta[entity_id] = {
            "display_name": str(entity.get("display_name", entity_id)).strip() or entity_id,
            "aliases": [str(a).strip() for a in (entity.get("aliases") or []) if str(a).strip()],
        }

    facts: list[dict[str, Any]] = []
    for entity_id, payload in (projection.get("entities", {}) or {}).items():
        meta = entity_meta.get(entity_id, {"display_name": entity_id, "aliases": []})
        for attribute, attr_payload in ((payload.get("attributes") or {})).items():
            value = str(attr_payload.get("value_label", "")).strip()
            if not value:
                continue
            truth_state = str(
                attr_payload.get("source_truth_state")
                or attr_payload.get("truth_state")
                or "UNKNOWN"
            ).upper()
            aliases = " ".join(meta.get("aliases") or [])
            search_text = (
                f"{meta['display_name']} {aliases} {attribute} {value} {truth_state}"
            )
            facts.append(
                {
                    "entity_id": entity_id,
                    "entity_name": meta["display_name"],
                    "attribute": str(attribute),
                    "value": value,
                    "truth_state": truth_state,
                    "search_text": _normalize(search_text),
                }
            )
    return facts


def _score_claim_to_fact(claim_text: str, fact_text: str) -> float:
    claim_tokens = _tokenize(claim_text)
    fact_tokens = _tokenize(fact_text)
    if not claim_tokens or not fact_tokens:
        return 0.0
    overlap = len(claim_tokens & fact_tokens)
    return overlap / max(1, len(claim_tokens))


def _is_potential_contradiction(claim: str, fact: str) -> bool:
    c = _normalize(claim)
    f = _normalize(fact)
    if (" alive" in f or f.startswith("alive")) and ("dead" in c or "killed" in c):
        return True
    if (" dead" in f or "killed" in f) and ("alive" in c):
        return True
    if "not corrupted" in f and "corrupted" in c and "not corrupted" not in c:
        return True
    if "corrupted" in f and "not corrupted" in c:
        return True
    return False


def verify_claims_against_projection(
    claims: list[dict[str, Any]],
    projection: dict[str, Any],
    entities: list[dict[str, Any]],
    *,
    grounded_threshold: float = 0.55,
    contradiction_threshold: float = 0.35,
) -> dict[str, Any]:
    facts = build_projection_fact_index(projection, entities)
    factual_claims = [c for c in claims if c.get("type", "factual") == "factual"]
    outcomes: list[dict[str, Any]] = []
    status_counts = {
        "grounded": 0,
        "unsupported": 0,
        "contradicted": 0,
        "provenance_mismatch": 0,
    }
    correct_provenance = 0
    claims_with_provenance = 0

    for claim in factual_claims:
        text = str(claim.get("text", "")).strip()
        if not text:
            continue
        best: dict[str, Any] | None = None
        best_score = 0.0
        for fact in facts:
            score = _score_claim_to_fact(text, fact["search_text"])
            if score > best_score:
                best_score = score
                best = fact

        provided_provenance = claim.get("provenance_label")
        if isinstance(provided_provenance, str) and provided_provenance.upper() in PROVENANCE_LABELS:
            claims_with_provenance += 1
            provided_provenance = provided_provenance.upper()
        else:
            provided_provenance = None

        status = "unsupported"
        if best and best_score >= grounded_threshold:
            status = "grounded"
            if provided_provenance and provided_provenance != best["truth_state"]:
                status = "provenance_mismatch"
            elif provided_provenance:
                correct_provenance += 1
        elif best and best_score >= contradiction_threshold and _is_potential_contradiction(
            text, f"{best['attribute']} {best['value']}"
        ):
            status = "contradicted"

        status_counts[status] += 1
        outcomes.append(
            {
                "claim": text,
                "status": status,
                "score": round(best_score, 4),
                "matched_fact": best,
                "provided_provenance": provided_provenance,
            }
        )

    total = sum(status_counts.values())
    hallucination_rate = (
        (status_counts["unsupported"] + status_counts["contradicted"]) / total
        if total
        else 0.0
    )
    completeness = (status_counts["grounded"] / total) if total else 0.0
    provenance_accuracy = (
        correct_provenance / claims_with_provenance if claims_with_provenance else 1.0
    )

    return {
        "total_factual_claims": total,
        "status_counts": status_counts,
        "hallucination_rate": round(hallucination_rate, 4),
        "completeness": round(completeness, 4),
        "provenance_accuracy": round(provenance_accuracy, 4),
        "claims_with_provenance": claims_with_provenance,
        "claim_outcomes": outcomes,
    }


def evaluate_answer_accuracy(
    *,
    answer: str,
    projection: dict[str, Any],
    entities: list[dict[str, Any]],
    use_llm_extractor: bool = False,
    model: str | None = None,
    openai_client: Any | None = None,
) -> dict[str, Any]:
    if use_llm_extractor:
        try:
            claims = extract_claims_llm(answer, model=model, openai_client=openai_client)
        except Exception:
            claims = extract_claims_heuristic(answer)
    else:
        claims = extract_claims_heuristic(answer)
    verification = verify_claims_against_projection(claims, projection, entities)
    verification["claims"] = claims
    verification["extractor"] = "llm" if use_llm_extractor else "heuristic"
    return verification


def aggregate_accuracy(results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "grounded": 0,
        "unsupported": 0,
        "contradicted": 0,
        "provenance_mismatch": 0,
    }
    total_claims = 0
    provenance_numerator = 0.0
    provenance_denominator = 0.0
    for item in results:
        counts = item.get("status_counts", {})
        for key in totals:
            totals[key] += int(counts.get(key, 0))
        total_claims += int(item.get("total_factual_claims", 0))
        claims_with_prov = float(item.get("claims_with_provenance", 0))
        provenance_denominator += claims_with_prov
        provenance_numerator += claims_with_prov * float(item.get("provenance_accuracy", 1.0))

    hallucination = (
        (totals["unsupported"] + totals["contradicted"]) / total_claims
        if total_claims
        else 0.0
    )
    completeness = (totals["grounded"] / total_claims) if total_claims else 0.0
    provenance_accuracy = (
        provenance_numerator / provenance_denominator if provenance_denominator else 1.0
    )
    return {
        "enabled": True,
        "total_factual_claims": total_claims,
        "status_counts": totals,
        "hallucination_rate": round(hallucination, 4),
        "completeness": round(completeness, 4),
        "provenance_accuracy": round(provenance_accuracy, 4),
    }
