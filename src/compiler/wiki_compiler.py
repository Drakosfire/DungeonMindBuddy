"""LLM-authored wiki pages compiled from projected entity state (Karpathy-style wiki layer)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.llm.api_client import DungeonMindApiClient
from src.reducer.canon_projection import project_entity_state
from src.store import FactStore

logger = logging.getLogger(__name__)

WIKI_COMPILE_MODEL_ENV = "DMB_WIKI_COMPILE_MODEL"

# Lowercase display names that are extraction artifacts or too generic for a dedicated page.
_GENERIC_DISPLAY_NAMES = frozenset(
    {
        "she",
        "he",
        "they",
        "it",
        "we",
        "you",
        "me",
        "her",
        "him",
        "them",
        "someone",
        "something",
        "group",
        "meat",
        "food",
        "light",
        "key",
        "river",
        "the city",
        "the town",
        "the ground",
        "the cult",
        "cultists",
        "insight",
        "voice",
        "canopy",
    }
)

WIKI_SYSTEM_PROMPT = """You are writing a reference article about one entity in a tabletop RPG campaign.
The reader will be another AI answering GM questions. Write clear, factual prose — not a bullet list of raw fields.

Rules:
- Open with identity: canonical name, type/class, and aliases if useful.
- State current operational status early (alive, dead, active threat, unknown, etc.) when facts support it.
- Describe important relationships using other entities' proper names (not "he" / "she" without antecedent).
- Separate layers when relevant: established world truth vs what happened in play vs GM prep that may not have occurred.
- When facts include terminal outcomes (death, decapitation, corruption lifting, etc.), quote the exact canonical phrases verbatim in quotes.
- Do NOT invent facts. If evidence is thin, say what is unknown.
- Omit meta-noise attributes (source_comments, unresolved_questions).
- Target 150–400 words unless the entity has very few facts (then be shorter).
- Write in third person. No meta commentary about the extraction process.
"""


def should_skip_entity_for_wiki(display_name: str) -> bool:
    """Skip obviously generic / pronoun-like entity names."""
    raw = (display_name or "").strip()
    if len(raw) < 2:
        return True
    key = raw.lower()
    if key in _GENERIC_DISPLAY_NAMES:
        return True
    # Single very short token often a pronoun or noise
    if " " not in key and len(key) <= 3:
        return True
    return False


def score_entity_connectivity(store: FactStore) -> dict[str, float]:
    """Composite connectivity: fact mass + document spread + evidence co-occurrence (0..~3)."""
    facts = store.facts
    evidence_units = store.evidence_units
    fact_count: Counter[str] = Counter()
    for fact in facts:
        sid = str(fact.get("subject_entity_id", "")).strip()
        if sid:
            fact_count[sid] += 1

    ev_doc: dict[str, str] = {}
    for u in evidence_units:
        eid = str(u.get("evidence_id", "")).strip()
        if eid:
            ev_doc[eid] = str(u.get("document_id", "")).strip()

    entity_docs: dict[str, set[str]] = defaultdict(set)
    entity_evidence: dict[str, set[str]] = defaultdict(set)
    for fact in facts:
        sid = str(fact.get("subject_entity_id", "")).strip()
        if not sid:
            continue
        for ev_id in fact.get("evidence_ids") or []:
            ev_id = str(ev_id).strip()
            if not ev_id:
                continue
            entity_evidence[sid].add(ev_id)
            doc = ev_doc.get(ev_id, "")
            if doc:
                entity_docs[sid].add(doc)

    evidence_entities: dict[str, set[str]] = defaultdict(set)
    for eid, ev_ids in entity_evidence.items():
        for ev_id in ev_ids:
            evidence_entities[ev_id].add(eid)

    weighted_degree: Counter[str] = Counter()
    for _ev_id, ent_set in evidence_entities.items():
        ent_list = list(ent_set)
        n = len(ent_list)
        for e in ent_list:
            weighted_degree[e] += max(0, n - 1)

    all_ids = set(fact_count.keys()) | set(entity_docs.keys()) | set(weighted_degree.keys())
    if not all_ids:
        return {}

    max_facts = max(fact_count.get(eid, 0) for eid in all_ids) or 1
    max_docs = max(len(entity_docs.get(eid, ())) for eid in all_ids) or 1
    max_deg = max(weighted_degree.get(eid, 0) for eid in all_ids) or 1

    composite: dict[str, float] = {}
    for eid in all_ids:
        f = fact_count.get(eid, 0) / max_facts
        d = len(entity_docs.get(eid, ())) / max_docs
        g = weighted_degree.get(eid, 0) / max_deg
        composite[eid] = f + d + g
    return composite


def facts_fingerprint_for_entity(store: FactStore, entity_id: str) -> str:
    """Stable hash of all facts for this subject (for incremental compile)."""
    rows: list[dict[str, Any]] = []
    for fact in store.facts:
        if str(fact.get("subject_entity_id", "")).strip() != entity_id:
            continue
        rows.append(fact)
    rows.sort(key=lambda f: str(f.get("fact_id", "")))
    blob = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _format_facts_for_prompt(projection_entity: dict[str, Any]) -> str:
    lines: list[str] = []
    attrs = (projection_entity or {}).get("attributes") or {}
    for attr in sorted(attrs.keys()):
        if attr in ("source_comments", "unresolved_questions"):
            continue
        payload = attrs[attr]
        if not isinstance(payload, dict):
            continue
        label = str(payload.get("value_label", "") or "").strip()
        truth = str(payload.get("source_truth_state", "") or "").strip()
        layer = str(payload.get("source_layer", "") or "").strip()
        if not label:
            continue
        meta = f"{truth or layer}".strip()
        if meta:
            lines.append(f"- {attr}: {label} [{meta}]")
        else:
            lines.append(f"- {attr}: {label}")
    return "\n".join(lines) if lines else "(no projected attributes)"


def _resolve_wiki_model() -> str:
    """Env override, then Buddy MODEL_POLICY actions.wiki_compile (else structured_generation), then models.cheapest."""
    env_model = os.environ.get(WIKI_COMPILE_MODEL_ENV, "").strip()
    if env_model:
        return env_model
    from src.model_policy import load_buddy_model_policy

    policy = load_buddy_model_policy()
    if policy:
        models = policy.get("models") or {}
        actions = policy.get("actions") or {}
        role = (
            actions.get("wiki_compile")
            or actions.get("structured_generation")
            or ""
        )
        if isinstance(role, str) and role.strip():
            mid = models.get(role.strip())
            if isinstance(mid, str) and mid.strip():
                return mid.strip()
        cheapest = models.get("cheapest")
        if isinstance(cheapest, str) and cheapest.strip():
            return cheapest.strip()
    return "gpt-5.4-nano"


def compile_entity_page(
    *,
    entity_id: str,
    entity_meta: dict[str, Any],
    projection_entity: dict[str, Any],
    client: OpenAI | None = None,
    model: str | None = None,
) -> str:
    """Single LLM call: projected facts -> prose wiki article."""
    display = str(entity_meta.get("display_name", entity_id)).strip() or entity_id
    cls = str(entity_meta.get("entity_class", entity_meta.get("entity_type", "concept"))).strip()
    aliases = [str(a).strip() for a in (entity_meta.get("aliases") or []) if str(a).strip()]
    alias_line = ", ".join(aliases[:8]) if aliases else "(none listed)"
    facts_block = _format_facts_for_prompt(projection_entity)

    user_msg = f"""Entity ID: {entity_id}
Display name: {display}
Class: {cls}
Aliases: {alias_line}

Projected facts (from the knowledge graph):
{facts_block}

Write the wiki article."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for compile_entity_page.")
    oc = client or OpenAI(api_key=api_key)
    api_client = DungeonMindApiClient.wrap(oc)
    mid = model or _resolve_wiki_model()
    resp = api_client.chat_completions_create(
        action="wiki_compiler.entity_page",
        model=mid,
        messages=[
            {"role": "system", "content": WIKI_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.35,
    ).response
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError(f"Empty wiki article for {entity_id}")
    return text


def compile_wiki(
    store: FactStore,
    campaign_id: str | None,
    *,
    entity_ids: list[str] | None = None,
    min_connectivity: float = 0.3,
    full: bool = False,
    incremental: bool = True,
    max_workers: int = 8,
    skip_generic_names: bool = True,
) -> dict[str, str]:
    """
    Compile wiki pages for selected entities and merge into store.wiki_pages / wiki_manifest.

    Returns the newly written pages (may be a subset when incremental skips unchanged).
    """
    projection = project_entity_state(
        evidence_units=store.evidence_units,
        facts=store.facts,
        conflicts=[],
        canon_decisions=store.canon_decisions,
        campaign_id=campaign_id,
    )
    proj_entities = projection.get("entities") or {}
    meta_by_id = {str(e.get("entity_id", "")).strip(): e for e in store.entities if e.get("entity_id")}

    scores = score_entity_connectivity(store)
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    targets: list[str] = []
    if entity_ids:
        targets = [str(e).strip() for e in entity_ids if str(e).strip()]
    elif full:
        targets = sorted(proj_entities.keys())
    else:
        for eid, sc in scores.items():
            if sc >= min_connectivity and eid in proj_entities:
                targets.append(eid)
        targets.sort()

    # Explicit --entity list: always compile requested IDs (user override).
    if skip_generic_names and not entity_ids:
        filtered: list[str] = []
        for eid in targets:
            meta = meta_by_id.get(eid, {})
            dn = str(meta.get("display_name", eid)).strip()
            if should_skip_entity_for_wiki(dn):
                logger.info("Skipping wiki compile for generic name: %s (%s)", dn, eid)
                continue
            filtered.append(eid)
        targets = filtered

    to_compile: list[str] = []
    manifest = dict(store.wiki_manifest) if isinstance(store.wiki_manifest, dict) else {}
    pages = dict(store.wiki_pages) if isinstance(store.wiki_pages, dict) else {}

    for eid in targets:
        if eid not in proj_entities:
            continue
        fp = facts_fingerprint_for_entity(store, eid)
        prev = manifest.get(eid) if isinstance(manifest.get(eid), dict) else {}
        prev_fp = str(prev.get("fact_hash", "")).strip() if isinstance(prev, dict) else ""
        if incremental and prev_fp == fp and eid in pages and pages.get(eid):
            continue
        to_compile.append(eid)

    if not to_compile:
        logger.info("compile_wiki: nothing to compile (incremental up to date).")
        return {}

    model = _resolve_wiki_model()
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    new_pages: dict[str, str] = {}

    def _one(eid: str) -> tuple[str, str]:
        meta = meta_by_id.get(eid, {"display_name": eid, "entity_id": eid})
        body = proj_entities.get(eid, {})
        text = compile_entity_page(
            entity_id=eid,
            entity_meta=meta,
            projection_entity=body,
            client=client,
            model=model,
        )
        return eid, text

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_one, eid): eid for eid in to_compile}
        for fut in as_completed(futures):
            eid = futures[fut]
            try:
                eid_done, article = fut.result()
                new_pages[eid_done] = article
            except Exception as exc:
                logger.exception("Wiki compile failed for %s: %s", eid, exc)
                raise

    for eid, article in new_pages.items():
        pages[eid] = article
        fp = facts_fingerprint_for_entity(store, eid)
        manifest[eid] = {
            "compiled_at": now_iso,
            "fact_hash": fp,
            "connectivity": scores.get(eid, 0.0),
            "model": model,
        }

    store.wiki_pages = pages
    store.wiki_manifest = manifest
    return new_pages


def list_wiki_targets(
    store: FactStore,
    *,
    campaign_id: str | None = None,
    min_connectivity: float = 0.3,
    full: bool = False,
    skip_generic_names: bool = True,
) -> list[tuple[str, float, str]]:
    """Return (entity_id, score, display_name) rows that would be compiled."""
    projection = project_entity_state(
        evidence_units=store.evidence_units,
        facts=store.facts,
        conflicts=[],
        canon_decisions=store.canon_decisions,
        campaign_id=campaign_id,
    )
    proj_entities = projection.get("entities") or {}
    scores = score_entity_connectivity(store)
    meta_by_id = {str(e.get("entity_id", "")).strip(): e for e in store.entities if e.get("entity_id")}

    if full:
        candidates = sorted(proj_entities.keys())
    else:
        candidates = sorted(eid for eid, sc in scores.items() if sc >= min_connectivity and eid in proj_entities)

    rows: list[tuple[str, float, str]] = []
    for eid in candidates:
        meta = meta_by_id.get(eid, {})
        dn = str(meta.get("display_name", eid)).strip()
        if skip_generic_names and should_skip_entity_for_wiki(dn):
            continue
        rows.append((eid, scores.get(eid, 0.0), dn))
    rows.sort(key=lambda r: -r[1])
    return rows
