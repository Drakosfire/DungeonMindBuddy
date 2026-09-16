#!/usr/bin/env python3
"""Accepted-world C1S10 question gauntlet — oracle retrieval + real Hermes Agent.

Evaluation-only driver. Production code is read-only. Gold remains in
``evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md``.

Usage (after Terminal 1 FastAPI is up against the acceptance World):

    uv run python evals/graph_benchmark/run_current_corpus_question_gauntlet.py \\
        --base-url http://127.0.0.1:8000

    uv run python evals/graph_benchmark/run_current_corpus_question_gauntlet.py \\
        --base-url http://127.0.0.1:8000 --loadability-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

GOLD_PATH = (
    PROJECT_ROOT
    / "evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md"
)
BENCHMARK_ID = "longmont-c1-sessions-01-10-graph-query-v1"
ACCEPTANCE_RUN_ID = "execute-2026-09-16T020204Z-6e3b812a"
ACCEPTANCE_ARTIFACT_ROOT = (
    PROJECT_ROOT
    / "out/graph_memory/current_corpus_admission_acceptance_v1"
    / ACCEPTANCE_RUN_ID
)
SESSION_LEDGER_PATH = ACCEPTANCE_ARTIFACT_ROOT / "session_ledger.json"
WORLD_ID = "dogfood-current-corpus-acceptance-v1"
CAMPAIGN_ID = "longmont-c1"
TERMINAL_HEAD = "rev:cce8d24621d65a018d3e2922552f56f2"
DATABASE_NAME = "dmb_current_corpus_acceptance_v1"
DATABASE_HOST_PORT = "127.0.0.1:54329"
OUTER_CAMPAIGN_ID = "longmont-c2"
OUTER_SESSION = 22
SEED_LIVE_SESSION = PROJECT_ROOT / "evals/c2_live_prep/live/session_22"
DEFAULT_ARTIFACT_ROOT = (
    PROJECT_ROOT / "out/graph_benchmark/current_corpus_question_gauntlet_v1"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-question-gauntlet-v1.md"
)

AGENT_FORBIDDEN_KEYS = frozenset(
    {
        "gold_answer",
        "goldAnswer",
        "must_include",
        "mustInclude",
        "must_not_claim",
        "mustNotClaim",
        "oracle_plan",
        "oraclePlan",
        "expected_hops",
        "expectedHops",
        "failure_taxonomy",
        "failureTaxonomy",
        "evidence",
        "gold",
    }
)

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "to",
        "for",
        "and",
        "or",
        "is",
        "from",
        "with",
        "in",
        "on",
        "at",
        "his",
        "her",
        "their",
        "later",
        "that",
        "this",
        "was",
        "were",
        "be",
        "into",
        "about",
        "as",
        "by",
        "they",
        "them",
        "party",
        "what",
        "how",
        "why",
        "did",
        "does",
        "had",
        "have",
        "has",
        "who",
        "which",
        "when",
        "where",
    }
)


@dataclass(frozen=True)
class GoldQuestion:
    qid: str
    title: str
    difficulty: int | None
    connectivity: str | None
    min_hops: int | None
    available_through: str | None
    question: str
    gold_answer: str
    must_include: list[str]
    must_not_claim: list[str]
    evidence: list[str]


@dataclass
class ConceptMatchResult:
    concept: str
    matched: bool
    matched_via: str | None = None


# ---------------------------------------------------------------------------
# Gold parsing
# ---------------------------------------------------------------------------


def parse_gold_markdown(text: str) -> list[GoldQuestion]:
    """Parse the checked-in C1 S1–S10 gold Markdown into question records."""
    blocks = re.split(r"(?m)^## (Q\d{2}) — (.+)$", text)
    # blocks[0] = preamble; then triples (qid, title, body)...
    if len(blocks) < 4:
        raise ValueError("gold markdown contains no Q## sections")
    questions: list[GoldQuestion] = []
    for i in range(1, len(blocks), 3):
        qid = blocks[i].strip()
        title = blocks[i + 1].strip()
        body = blocks[i + 2]
        meta = _parse_meta(body)
        question = _section_text(body, "Question")
        gold_answer = _section_text(body, "Gold answer")
        must_include = _bullet_list(body, "Must include")
        must_not_claim = _bullet_list(body, "Must not claim")
        evidence = _bullet_list(body, "Evidence")
        if not question.strip():
            raise ValueError(f"{qid}: empty Question section")
        if not gold_answer.strip():
            raise ValueError(f"{qid}: empty Gold answer section")
        if not must_include:
            raise ValueError(f"{qid}: empty Must include section")
        questions.append(
            GoldQuestion(
                qid=qid,
                title=title,
                difficulty=meta.get("difficulty"),
                connectivity=meta.get("connectivity"),
                min_hops=meta.get("min_hops"),
                available_through=meta.get("available_through"),
                question=question.strip(),
                gold_answer=gold_answer.strip(),
                must_include=must_include,
                must_not_claim=must_not_claim,
                evidence=evidence,
            )
        )
    if len(questions) != 16:
        raise ValueError(f"expected 16 gold questions, got {len(questions)}")
    expected_ids = [f"Q{i:02d}" for i in range(1, 17)]
    got_ids = [q.qid for q in questions]
    if got_ids != expected_ids:
        raise ValueError(f"gold question IDs out of order: {got_ids}")
    return questions


def load_gold_questions(path: Path = GOLD_PATH) -> list[GoldQuestion]:
    return parse_gold_markdown(path.read_text(encoding="utf-8"))


def _parse_meta(body: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"\*\*Difficulty:\*\*\s*(\d+)", body)
    if m:
        out["difficulty"] = int(m.group(1))
    m = re.search(r"\*\*Connectivity:\*\*\s*(.+)", body)
    if m:
        out["connectivity"] = m.group(1).strip()
    m = re.search(r"\*\*Minimum graph hops:\*\*\s*(\d+)", body)
    if m:
        out["min_hops"] = int(m.group(1))
    m = re.search(r"\*\*Available through:\*\*\s*(.+)", body)
    if m:
        out["available_through"] = m.group(1).strip()
    return out


def _section_text(body: str, heading: str) -> str:
    pattern = rf"(?ms)^\*\*{re.escape(heading)}\*\*\s*\n\n(.+?)(?=\n\*\*[A-Z]|\n---|\Z)"
    m = re.search(pattern, body)
    if not m:
        return ""
    return m.group(1).strip()


def _bullet_list(body: str, heading: str) -> list[str]:
    pattern = rf"(?ms)^\*\*{re.escape(heading)}\*\*\s*\n\n(.+?)(?=\n\*\*[A-Z]|\n---|\Z)"
    m = re.search(pattern, body)
    if not m:
        return []
    items: list[str] = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


# ---------------------------------------------------------------------------
# Concept matching / grading
# ---------------------------------------------------------------------------


def _normalize_haystack(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _significant_tokens(phrase: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9']+", phrase.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


def concept_matched(haystack: str, concept: str) -> ConceptMatchResult:
    """Match a must-include concept; '/' alternatives are OR."""
    hay = _normalize_haystack(haystack)
    alternatives = [part.strip() for part in re.split(r"\s*/\s*", concept) if part.strip()]
    if not alternatives:
        alternatives = [concept.strip()]
    for alt in alternatives:
        # Nested "and/or" treated as OR of sides when present as a single alt.
        or_parts = [p.strip() for p in re.split(r"\band/or\b", alt, flags=re.I) if p.strip()]
        for part in or_parts or [alt]:
            tokens = _significant_tokens(part)
            if not tokens:
                if part.lower() in hay:
                    return ConceptMatchResult(concept=concept, matched=True, matched_via=part)
                continue
            if all(tok in hay for tok in tokens):
                return ConceptMatchResult(concept=concept, matched=True, matched_via=part)
    return ConceptMatchResult(concept=concept, matched=False)


def match_concepts(haystack: str, concepts: list[str]) -> list[ConceptMatchResult]:
    return [concept_matched(haystack, c) for c in concepts]


def grade_answer(
    *,
    answer_text: str,
    must_include: list[str],
    must_not_claim: list[str],
) -> dict[str, Any]:
    include_hits = match_concepts(answer_text, must_include)
    forbid_hits = match_concepts(answer_text, must_not_claim) if must_not_claim else []
    matched = [h for h in include_hits if h.matched]
    missed = [h for h in include_hits if not h.matched]
    forbidden_fired = [h for h in forbid_hits if h.matched]
    if forbidden_fired:
        grade = "FAIL"
    elif not missed and matched:
        grade = "FULL"
    elif matched:
        grade = "PARTIAL"
    else:
        grade = "FAIL"
    return {
        "grade": grade,
        "must_include_matched": [asdict(h) for h in matched],
        "must_include_missed": [asdict(h) for h in missed],
        "must_not_claim_fired": [asdict(h) for h in forbidden_fired],
        "match_ratio": (len(matched) / len(must_include)) if must_include else 0.0,
    }


# ---------------------------------------------------------------------------
# Request sealing (deterministic; no gold leakage)
# ---------------------------------------------------------------------------


def sealed_world_graph_context(benchmark_revision: str) -> dict[str, Any]:
    return {
        "schema": "dmb_agent_world_graph_query_context_request_v1",
        "world_id": WORLD_ID,
        "campaign_id": CAMPAIGN_ID,
        "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        "admissibility": "gm",
        "revision_pin": benchmark_revision,
        "scope_mode": "campaign",
        "selected_node_id": None,
    }


def build_agent_live_query_request(
    *,
    question_text: str,
    benchmark_revision: str,
    outer_campaign_id: str = OUTER_CAMPAIGN_ID,
    outer_session: int = OUTER_SESSION,
) -> dict[str, Any]:
    """Build a fresh Hermes Agent turn request with no gold/history/session carry."""
    request = {
        "campaign_id": outer_campaign_id,
        "session": outer_session,
        "mode": "live",
        "query_backend": "hermes",
        "text": question_text,
        "world_graph_context": sealed_world_graph_context(benchmark_revision),
        "trace_requested": True,
    }
    assert_agent_request_sanitized(request)
    return request


def assert_agent_request_sanitized(request: dict[str, Any]) -> None:
    """Prove Agent request contains no gold/evaluator hints or session carry."""
    blob = json.dumps(request, sort_keys=True)
    for key in AGENT_FORBIDDEN_KEYS:
        if key in request or f'"{key}"' in blob:
            # Allow ordinary product fields; forbid gold-shaped keys only at top
            # and nested levels when present as object keys.
            if _dict_contains_key(request, key):
                raise AssertionError(f"agent request leaks forbidden key: {key}")
    if request.get("hermes_session_id"):
        raise AssertionError("agent request must not carry hermes_session_id")
    if request.get("hermes_session_pointer"):
        raise AssertionError("agent request must not carry hermes_session_pointer")
    if request.get("agent_thread_id"):
        raise AssertionError("agent request must not carry agent_thread_id")
    history = request.get("conversation_history")
    if history not in (None, [], ()):
        raise AssertionError("agent request must not carry conversation_history")
    wgc = request.get("world_graph_context") or {}
    if wgc.get("campaign_id") != CAMPAIGN_ID:
        raise AssertionError("nested campaign_id must be longmont-c1")
    if wgc.get("revision_pin") in (None, "", TERMINAL_HEAD):
        raise AssertionError("revision_pin must be historical C1S10, not terminal head")


def _dict_contains_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_dict_contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_dict_contains_key(v, key) for v in obj)
    return False


def build_retrieval_search_request(
    *,
    query_text: str,
    benchmark_revision: str,
    seed_node_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_search_request_v1",
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "focus": {"kind": "none", "sessionId": None, "campaignId": None},
        "admissibility": "gm",
        "revisionPin": benchmark_revision,
        "scopeMode": "campaign",
        "queryText": query_text,
        "seedNodeIds": list(seed_node_ids or []),
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_retrieval_neighborhood_request(
    *,
    seed_node_ids: list[str],
    benchmark_revision: str,
    max_depth: int = 2,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_neighborhood_request_v1",
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "focus": {"kind": "none", "sessionId": None, "campaignId": None},
        "admissibility": "gm",
        "revisionPin": benchmark_revision,
        "scopeMode": "campaign",
        "seedNodeIds": seed_node_ids[:8],
        "maxDepth": max_depth,
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_retrieval_object_request(
    *,
    node_id: str,
    benchmark_revision: str,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_object_request_v1",
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "focus": {"kind": "none", "sessionId": None, "campaignId": None},
        "admissibility": "gm",
        "revisionPin": benchmark_revision,
        "scopeMode": "campaign",
        "nodeId": node_id,
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_source_anchor_read_request(
    *,
    anchor_id: str,
    benchmark_revision: str,
    max_chars: int = 4000,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_source_anchor_read_request_v1",
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "focus": {"kind": "none", "sessionId": None, "campaignId": None},
        "admissibility": "gm",
        "revisionPin": benchmark_revision,
        "scopeMode": "campaign",
        "anchorId": anchor_id,
        "maxChars": max_chars,
    }


# ---------------------------------------------------------------------------
# Authority / revision resolution
# ---------------------------------------------------------------------------


def resolve_ledger_session_row(
    campaign_id: str,
    session_id: str,
    ledger_path: Path = SESSION_LEDGER_PATH,
) -> dict[str, Any]:
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    sessions = payload.get("sessions") if isinstance(payload, dict) else payload
    if not isinstance(sessions, list):
        raise RuntimeError("session_ledger.json missing sessions list")
    matches = [
        row
        for row in sessions
        if isinstance(row, dict)
        and row.get("campaign_id") == campaign_id
        and row.get("session_id") == session_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one {campaign_id}/{session_id} ledger row, "
            f"got {len(matches)}"
        )
    row = matches[0]
    revision = row.get("receipt_child_revision")
    if not isinstance(revision, str) or not revision.startswith("rev:"):
        raise RuntimeError(
            f"{campaign_id}/{session_id} receipt_child_revision missing or invalid"
        )
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "receipt_child_revision": revision,
        "sealed_parent_revision": row.get("sealed_parent_revision"),
        "ordinal": row.get("ordinal"),
        "candidate_locator": row.get("candidate_locator"),
        "ledger_path": str(ledger_path),
    }


def resolve_benchmark_revision(
    ledger_path: Path = SESSION_LEDGER_PATH,
) -> dict[str, Any]:
    row = resolve_ledger_session_row(
        CAMPAIGN_ID, "session-10", ledger_path=ledger_path
    )
    if row["receipt_child_revision"] == TERMINAL_HEAD:
        raise RuntimeError("C1S10 revision unexpectedly equals terminal head")
    return row


def git_head_sha() -> str:
    return (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        )
        .strip()
    )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redacted_database_identity(dsn: str | None) -> dict[str, str]:
    if not dsn:
        return {
            "host_port": DATABASE_HOST_PORT,
            "database": DATABASE_NAME,
            "credentials": "redacted",
        }
    parsed = urlparse(dsn)
    host = parsed.hostname or "unknown"
    port = parsed.port or 5432
    db = (parsed.path or "/").lstrip("/") or "unknown"
    return {
        "host_port": f"{host}:{port}",
        "database": db,
        "credentials": "redacted",
    }


def read_world_head_via_psql() -> str:
    """Read accepted World head without embedding credentials in artifacts."""
    env = os.environ.copy()
    # Prefer already-exported PGPASSWORD; otherwise use known local-dev default
    # for the acceptance container (never written to artifacts).
    env.setdefault("PGPASSWORD", "dungeonmind-dev")
    cmd = [
        "psql",
        "-h",
        "127.0.0.1",
        "-p",
        "54329",
        "-U",
        "dungeonmind",
        "-d",
        DATABASE_NAME,
        "-Atc",
        f"SELECT head_revision_id FROM dungeonmind.world_graph_heads WHERE world_id = '{WORLD_ID}';",
    ]
    out = subprocess.check_output(cmd, env=env, text=True).strip()
    if not out.startswith("rev:"):
        raise RuntimeError(f"unexpected world head: {out!r}")
    return out


def verify_revision_is_ancestor(child: str, ancestor: str) -> bool:
    env = os.environ.copy()
    env.setdefault("PGPASSWORD", "dungeonmind-dev")
    sql = f"""
WITH RECURSIVE walk AS (
  SELECT revision_id, parent_revision_id, 0 AS depth
  FROM dungeonmind.graph_revisions
  WHERE world_id = '{WORLD_ID}' AND revision_id = '{child}'
  UNION ALL
  SELECT r.revision_id, r.parent_revision_id, walk.depth + 1
  FROM dungeonmind.graph_revisions r
  JOIN walk ON r.revision_id = walk.parent_revision_id
  WHERE r.world_id = '{WORLD_ID}' AND walk.depth < 200
)
SELECT depth FROM walk WHERE revision_id = '{ancestor}';
"""
    out = subprocess.check_output(
        [
            "psql",
            "-h",
            "127.0.0.1",
            "-p",
            "54329",
            "-U",
            "dungeonmind",
            "-d",
            DATABASE_NAME,
            "-Atc",
            sql,
        ],
        env=env,
        text=True,
    ).strip()
    return bool(out)


def build_authority_record(
    *,
    benchmark_revision: str,
    ledger_row: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    dsn = os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "")
    head = read_world_head_via_psql()
    if head != TERMINAL_HEAD:
        raise RuntimeError(
            f"acceptance terminal head mismatch: got {head}, expected {TERMINAL_HEAD}"
        )
    if not verify_revision_is_ancestor(TERMINAL_HEAD, benchmark_revision):
        raise RuntimeError(
            f"{benchmark_revision} is not an ancestor of {TERMINAL_HEAD}"
        )
    return {
        "schema": "dmb_current_corpus_question_gauntlet_authority_v1",
        "run_id": run_id,
        "runtime_git_sha": git_head_sha(),
        "acceptance_run_id": ACCEPTANCE_RUN_ID,
        "acceptance_world_id": WORLD_ID,
        "acceptance_database": redacted_database_identity(dsn),
        "acceptance_terminal_head": TERMINAL_HEAD,
        "benchmark_revision": benchmark_revision,
        "c1s10_ledger_row": {
            "campaign_id": ledger_row["campaign_id"],
            "session_id": ledger_row["session_id"],
            "receipt_child_revision": ledger_row["receipt_child_revision"],
            "sealed_parent_revision": ledger_row.get("sealed_parent_revision"),
            "ordinal": ledger_row.get("ordinal"),
        },
        "benchmark_id": BENCHMARK_ID,
        "gold_path": str(GOLD_PATH.relative_to(PROJECT_ROOT)),
        "gold_sha256": file_sha256(GOLD_PATH),
        "semantic_model_selection": "HOLD",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# HTTP helpers / retrieval flattening
# ---------------------------------------------------------------------------


def _post_json(
    client: httpx.Client,
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any] | Any]:
    response = client.post(path, json=payload, timeout=timeout)
    try:
        body = response.json()
    except Exception:
        body = {"raw_text": response.text}
    return response.status_code, body


def flatten_retrieval_text(result: dict[str, Any]) -> str:
    chunks: list[str] = []

    def walk(obj: Any, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in {"diagnostics", "trustBoundary", "coverage"}:
                    continue
                if isinstance(value, str) and value.strip():
                    chunks.append(value)
                else:
                    walk(value, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, depth + 1)

    walk(result)
    return "\n".join(chunks)


def collect_ids(result: dict[str, Any]) -> dict[str, list[str]]:
    nodes: list[str] = []
    relationships: list[str] = []
    attributes: list[str] = []
    anchors: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if "nodeId" in obj and isinstance(obj["nodeId"], str):
                nodes.append(obj["nodeId"])
            if "edgeId" in obj and isinstance(obj["edgeId"], str):
                relationships.append(obj["edgeId"])
            if "assertionId" in obj and isinstance(obj["assertionId"], str):
                attributes.append(obj["assertionId"])
            if "anchorId" in obj and isinstance(obj["anchorId"], str):
                anchors.append(obj["anchorId"])
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(result)
    return {
        "node_ids": sorted(set(nodes)),
        "relationship_ids": sorted(set(relationships)),
        "attribute_ids": sorted(set(attributes)),
        "source_anchor_ids": sorted(set(anchors)),
    }


def extract_revision_ids(payload: Any) -> set[str]:
    found: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in {
                    "revision_id",
                    "revisionId",
                    "revision_pin",
                    "revisionPin",
                } and isinstance(value, str):
                    found.add(value)
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload)
    return found


def extract_search_seeds(question: GoldQuestion) -> list[str]:
    """Oracle-only: choose sensible search strings from question + must-include."""
    seeds = [question.question]
    # Proper-noun-ish tokens from the question.
    proper = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", question.question)
    for name in proper:
        if name.lower() not in {"what", "where", "how", "why", "session"}:
            seeds.append(name)
    for concept in question.must_include[:4]:
        # Prefer left side of alternatives as a search hint.
        left = concept.split(" / ")[0].strip()
        if len(left) >= 4:
            seeds.append(left)
    # Deduplicate preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for s in seeds:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:6]


# ---------------------------------------------------------------------------
# Oracle + Agent execution
# ---------------------------------------------------------------------------


def run_oracle_for_question(
    client: httpx.Client,
    *,
    question: GoldQuestion,
    benchmark_revision: str,
) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    combined_text_parts: list[str] = []
    all_ids: dict[str, set[str]] = {
        "node_ids": set(),
        "relationship_ids": set(),
        "attribute_ids": set(),
        "source_anchor_ids": set(),
    }
    revision_ids_seen: set[str] = set()

    for seed in extract_search_seeds(question):
        req = build_retrieval_search_request(
            query_text=seed,
            benchmark_revision=benchmark_revision,
        )
        status, body = _post_json(
            client, "/api/live/world-graph/retrieval/search", req
        )
        operations.append(
            {
                "operation": "search",
                "request": req,
                "status_code": status,
                "response": body,
            }
        )
        if isinstance(body, dict):
            combined_text_parts.append(flatten_retrieval_text(body))
            ids = collect_ids(body)
            for k, vals in ids.items():
                all_ids[k].update(vals)
            revision_ids_seen |= extract_revision_ids(body)

    seed_nodes = sorted(all_ids["node_ids"])[:8]
    if seed_nodes:
        req = build_retrieval_neighborhood_request(
            seed_node_ids=seed_nodes,
            benchmark_revision=benchmark_revision,
            max_depth=2,
        )
        status, body = _post_json(
            client, "/api/live/world-graph/retrieval/neighborhood", req
        )
        operations.append(
            {
                "operation": "neighborhood",
                "request": req,
                "status_code": status,
                "response": body,
            }
        )
        if isinstance(body, dict):
            combined_text_parts.append(flatten_retrieval_text(body))
            ids = collect_ids(body)
            for k, vals in ids.items():
                all_ids[k].update(vals)
            revision_ids_seen |= extract_revision_ids(body)

    for node_id in sorted(all_ids["node_ids"])[:4]:
        req = build_retrieval_object_request(
            node_id=node_id,
            benchmark_revision=benchmark_revision,
        )
        status, body = _post_json(
            client, "/api/live/world-graph/retrieval/object", req
        )
        operations.append(
            {
                "operation": "object",
                "request": req,
                "status_code": status,
                "response": body,
            }
        )
        if isinstance(body, dict):
            combined_text_parts.append(flatten_retrieval_text(body))
            ids = collect_ids(body)
            for k, vals in ids.items():
                all_ids[k].update(vals)
            revision_ids_seen |= extract_revision_ids(body)

    opened_anchors: list[dict[str, Any]] = []
    for anchor_id in sorted(all_ids["source_anchor_ids"])[:4]:
        req = build_source_anchor_read_request(
            anchor_id=anchor_id,
            benchmark_revision=benchmark_revision,
        )
        status, body = _post_json(
            client, "/api/live/world-graph/retrieval/source-anchor/read", req
        )
        operations.append(
            {
                "operation": "source_anchor_read",
                "request": req,
                "status_code": status,
                "response": body,
            }
        )
        opened_anchors.append({"anchor_id": anchor_id, "status_code": status})
        if isinstance(body, dict):
            combined_text_parts.append(flatten_retrieval_text(body))
            revision_ids_seen |= extract_revision_ids(body)

    combined = "\n".join(combined_text_parts)
    coverage = grade_answer(
        answer_text=combined,
        must_include=question.must_include,
        must_not_claim=[],
    )
    # Oracle answerable requires full must-include coverage from production
    # retrieval material alone (no corpus Markdown fallback).
    oracle_answerable = coverage["grade"] == "FULL"

    primary_failure = None
    if not oracle_answerable:
        if not all_ids["node_ids"]:
            primary_failure = "A"
        elif coverage["match_ratio"] == 0:
            primary_failure = "A"
        elif coverage["match_ratio"] < 0.5:
            primary_failure = "B"
        else:
            primary_failure = "C"

    # headRevisionId may appear alongside pinned revisionId — allow terminal
    # head only as lineage metadata, never as an unexpected third revision.
    leakage = sorted(
        r
        for r in revision_ids_seen
        if isinstance(r, str)
        and r.startswith("rev:")
        and r not in {benchmark_revision, TERMINAL_HEAD}
    )

    return {
        "question_id": question.qid,
        "question_text": question.question,
        "benchmark_revision": benchmark_revision,
        "operations": operations,
        "matched_ids": {k: sorted(v) for k, v in all_ids.items()},
        "opened_source_anchors": opened_anchors,
        "coverage_vs_must_include": coverage,
        "oracle_answerable": oracle_answerable,
        "primary_failure_bucket": primary_failure,
        "revision_ids_seen": sorted(revision_ids_seen),
        "unexpected_revision_ids": leakage,
        "oracle_synthesis_notes": (
            "Oracle used production search→neighborhood→object→source-anchor-read "
            "only; concept coverage scored against must-include without corpus Markdown fallback."
        ),
    }


def run_agent_for_question(
    client: httpx.Client,
    *,
    question: GoldQuestion,
    benchmark_revision: str,
    timeout: float = 300.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    request = build_agent_live_query_request(
        question_text=question.question,
        benchmark_revision=benchmark_revision,
    )
    status, body = _post_json(
        client, "/api/live/query", request, timeout=timeout
    )
    response_record = {
        "status_code": status,
        "body": body,
    }
    return request, response_record


def count_tool_events(agent_body: dict[str, Any]) -> int:
    trace = agent_body.get("agent_trace") or {}
    for key in ("tool_events", "toolEvents", "steps", "events"):
        value = trace.get(key)
        if isinstance(value, list):
            return len(value)
    # Fallback: walk for tool-like events.
    count = 0

    def walk(obj: Any) -> None:
        nonlocal count
        if isinstance(obj, dict):
            if obj.get("type") in {"tool", "tool_call", "tool_result"} or "tool_name" in obj:
                count += 1
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(trace)
    return count


def count_source_anchors_in_agent(agent_body: dict[str, Any]) -> int:
    ids = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in {"anchor_id", "anchorId"} and isinstance(value, str):
                    ids.add(value)
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(agent_body)
    return len(ids)


def attribute_failure(
    *,
    question: GoldQuestion,
    oracle: dict[str, Any],
    agent_grade: str,
    agent_body: dict[str, Any],
) -> str | None:
    if agent_grade == "FULL":
        return None
    if not oracle.get("oracle_answerable"):
        return oracle.get("primary_failure_bucket") or "A"
    # Oracle succeeded → Agent-side failure.
    if question.qid in {"Q14", "Q16"}:
        return "E"
    tool_calls = count_tool_events(agent_body if isinstance(agent_body, dict) else {})
    if tool_calls <= 1:
        return "D"
    return "F"


def grade_agent_response(
    *,
    question: GoldQuestion,
    response_record: dict[str, Any],
    oracle: dict[str, Any],
) -> dict[str, Any]:
    body = response_record.get("body") or {}
    answer = ""
    if isinstance(body, dict):
        answer = str(body.get("answer") or "")
    scored = grade_answer(
        answer_text=answer,
        must_include=question.must_include,
        must_not_claim=question.must_not_claim,
    )
    primary = attribute_failure(
        question=question,
        oracle=oracle,
        agent_grade=scored["grade"],
        agent_body=body if isinstance(body, dict) else {},
    )
    revision_ids = extract_revision_ids(body) if isinstance(body, dict) else set()
    return {
        "question_id": question.qid,
        "agent_grade": scored["grade"],
        "must_include_matched": scored["must_include_matched"],
        "must_include_missed": scored["must_include_missed"],
        "must_not_claim_fired": scored["must_not_claim_fired"],
        "match_ratio": scored["match_ratio"],
        "primary_failure": primary,
        "secondary_failures": [],
        "tool_call_count": count_tool_events(body if isinstance(body, dict) else {}),
        "source_anchor_count": count_source_anchors_in_agent(
            body if isinstance(body, dict) else {}
        ),
        "revision_ids_seen": sorted(revision_ids),
        "answer_excerpt": answer[:500],
        "http_status": response_record.get("status_code"),
        "agent_status": (body.get("status") if isinstance(body, dict) else None),
        "agent_mode": (body.get("mode") if isinstance(body, dict) else None),
    }


# ---------------------------------------------------------------------------
# Readiness + report
# ---------------------------------------------------------------------------


def run_readiness(
    client: httpx.Client,
    *,
    benchmark_revision: str,
    skip_agent: bool = False,
) -> dict[str, Any]:
    search_req = build_retrieval_search_request(
        query_text="Torbin",
        benchmark_revision=benchmark_revision,
    )
    search_status, search_body = _post_json(
        client, "/api/live/world-graph/retrieval/search", search_req
    )
    snapshot = {}
    if isinstance(search_body, dict):
        snapshot = search_body.get("snapshot") or search_body.get("context") or {}
        if not snapshot and isinstance(search_body.get("result"), dict):
            snapshot = search_body["result"].get("snapshot") or {}

    revision_ok = False
    revision_ids = extract_revision_ids(search_body)
    if benchmark_revision in revision_ids:
        revision_ok = True
    for key in ("revisionId", "revision_id"):
        if isinstance(snapshot, dict) and snapshot.get(key) == benchmark_revision:
            revision_ok = True

    harness_ready = search_status == 200 and revision_ok
    agent_status: int | None = None
    agent_body: Any = None
    agent_revision_ok = False
    agent_mode_ok = False
    agent_skipped = skip_agent
    if not skip_agent:
        smoke_req = build_agent_live_query_request(
            question_text="Who is Torbin in Campaign 1?",
            benchmark_revision=benchmark_revision,
        )
        agent_status, agent_body = _post_json(
            client, "/api/live/query", smoke_req, timeout=300.0
        )
        if isinstance(agent_body, dict):
            agent_revision_ok = benchmark_revision in extract_revision_ids(agent_body)
            agent_mode_ok = agent_body.get("mode") == "hermes_graph_agent"
            wgc = agent_body.get("world_graph_context") or {}
            if isinstance(wgc, dict) and wgc.get("revision_id") == benchmark_revision:
                agent_revision_ok = True
    agent_ok = (
        not skip_agent
        and agent_status == 200
        and agent_revision_ok
        and agent_mode_ok
    )
    return {
        "ready": harness_ready,
        "harness_ready": harness_ready,
        "dogfood_agent_ok": agent_ok,
        "historical_projection": {
            "search_status": search_status,
            "revision_ok": revision_ok,
            "revision_ids_seen": sorted(revision_ids),
            "snapshot": snapshot,
        },
        "retrieval_smoke": {
            "query": "Torbin",
            "status_code": search_status,
            "ok": harness_ready,
        },
        "agent_smoke": {
            "skipped": agent_skipped,
            "status_code": agent_status,
            "mode": (agent_body.get("mode") if isinstance(agent_body, dict) else None),
            "status": (
                agent_body.get("status") if isinstance(agent_body, dict) else None
            ),
            "revision_ok": agent_revision_ok,
            "mode_ok": agent_mode_ok,
            "ok": agent_ok,
            "error": _agent_smoke_error(agent_body),
        },
        "benchmark_revision": benchmark_revision,
    }


def _agent_smoke_error(agent_body: Any) -> dict[str, Any] | None:
    if not isinstance(agent_body, dict):
        return None
    detail = agent_body.get("detail") or agent_body.get("message") or agent_body.get("error")
    if isinstance(detail, dict):
        detail = detail.get("message") or detail.get("code") or str(detail)
    text = str(detail or "").strip()
    if not text:
        return None
    return {
        "code": agent_body.get("code") or agent_body.get("error"),
        "status": agent_body.get("status"),
        "detail": text[:400],
    }


def _skipped_agent_grade(question: GoldQuestion, *, reason: str) -> dict[str, Any]:
    return {
        "question_id": question.qid,
        "agent_grade": "FAIL",
        "primary_failure": "D",
        "skip_reason": reason,
        "tool_call_count": 0,
        "source_anchor_count": 0,
        "answer_excerpt": "",
        "must_include_matched": [],
        "must_include_missed": [
            {"concept": c, "matched": False} for c in question.must_include
        ],
        "must_not_claim_fired": [],
        "match_ratio": 0.0,
        "revision_ids_seen": [],
        "http_status": None,
        "agent_status": "skipped",
        "agent_mode": None,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_report(
    *,
    authority: dict[str, Any],
    readiness: dict[str, Any],
    scorecard: dict[str, Any],
    question_rows: list[dict[str, Any]],
    run_id: str,
    loadability: dict[str, Any] | None = None,
    dogfood: dict[str, Any] | None = None,
) -> str:
    dogfood = dogfood or scorecard.get("dogfood") or {}
    dogfood_ready = bool(dogfood.get("dogfood_ready"))
    status = (
        "READY — operator can dogfood this World"
        if dogfood_ready
        else "NOT READY — operator cannot dogfood this World"
    )
    lines: list[str] = []
    lines.append("# REPORT — DOGFOOD-CONTINUITY: accepted-world question gauntlet v1")
    lines.append("")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Run ID:** `{run_id}`")
    lines.append(f"**Runtime git SHA:** `{authority.get('runtime_git_sha')}`")
    lines.append(f"**Acceptance run:** `{authority.get('acceptance_run_id')}`")
    lines.append(f"**World:** `{authority.get('acceptance_world_id')}`")
    lines.append(
        f"**BENCHMARK_REVISION (C1S10):** `{authority.get('benchmark_revision')}`"
    )
    lines.append(
        f"**Terminal head (lineage only):** `{authority.get('acceptance_terminal_head')}`"
    )
    lines.append(f"**Benchmark ID:** `{authority.get('benchmark_id')}`")
    lines.append("**SEMANTIC MODEL SELECTION:** `HOLD`")
    lines.append(
        "**Readiness law:** [`Docs/Design/ACCEPTANCE-dogfood-readiness.md`]"
        "(../Design/ACCEPTANCE-dogfood-readiness.md) — structural acceptance → "
        "product loadability → operator dogfoodability → semantic usefulness → "
        "Agent usefulness. A lower-layer PASS cannot override a higher-layer failure."
    )
    lines.append(
        "**Successor:** [`HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`]"
        "(../Plans/HANDOFF-DOGFOOD-CONTINUITY-published-object-addressability-v1.md) "
        "remains **BLOCKED** until this report is durable on `main`. "
        "No implementation PR from this evaluation."
    )
    lines.append("")
    lines.append("## Operator dogfood")
    lines.append("")
    lines.append(
        dogfood.get("rule")
        or (
            "If the operator cannot dogfood the accepted World, it is not ready. "
            "Structural retrieval PASS is not product readiness."
        )
    )
    lines.append("")
    lines.append(f"**dogfood_ready:** `{dogfood_ready}`")
    lines.append("")
    blockers = dogfood.get("blockers") or []
    if blockers:
        lines.append("Blockers:")
        lines.append("")
        for blocker in blockers:
            lines.append(f"- `{blocker.get('id')}` — {blocker.get('detail')}")
        lines.append("")
    else:
        lines.append("No dogfood blockers recorded.")
        lines.append("")
    if loadability:
        lines.append("### Ingested-object loadability (C2S22 Mireward)")
        lines.append("")
        lines.append("```text")
        lines.append(f"seed_status:     {loadability.get('seed_status')}")
        lines.append(f"openable:        {loadability.get('openable')}")
        lines.append(f"revision_pin:    {loadability.get('revision_pin')}")
        remap = loadability.get("identity_remap") or {}
        lines.append(
            f"identity_remap:  {remap.get('from_candidate_id')} -> "
            f"{remap.get('to_published_ids')}"
        )
        payload_ids = [
            row.get("object_id") for row in (loadability.get("payload_objects") or [])
        ]
        lines.append(f"payload_ids:     {payload_ids}")
        lines.append(
            "search_world:    "
            f"{(loadability.get('search_world') or {}).get('outcome')}"
        )
        lines.append(
            "search_campaign: "
            f"{(loadability.get('search_campaign') or {}).get('outcome')}"
        )
        for identity in loadability.get("identities") or []:
            lines.append(
                f"{identity.get('node_id')}: "
                f"payload={identity.get('payload_present')} "
                f"product_found={identity.get('product_found')} "
                f"status={identity.get('status')}"
            )
        lines.append("```")
        lines.append("")
        lines.append(
            "Graph Review `evidence[2]` quote-in-span cannot be validated until "
            "the published object is loadable. Candidate `loc:mireward` has two "
            "quotes; the third live extract is not a candidate evidence row."
        )
        lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append("```text")
    lines.append(
        f"oracle answerable: {scorecard['oracle_answerable']} / 16"
    )
    lines.append(f"Agent FULL:        {scorecard['agent_full']} / 16")
    lines.append(f"Agent PARTIAL:     {scorecard['agent_partial']} / 16")
    lines.append(f"Agent FAIL:        {scorecard['agent_fail']} / 16")
    for bucket in ("A", "B", "C", "D", "E", "F"):
        lines.append(
            f"{bucket}: {scorecard['failure_counts'].get(bucket, 0)}"
        )
    lines.append("```")
    lines.append("")
    lines.append("## Per-question results")
    lines.append("")
    lines.append(
        "| Q | Oracle answerable | Agent grade | Primary failure | Agent tool calls | Source anchors | Short finding |"
    )
    lines.append("|---:|---|---|---|---:|---:|---|")
    for row in question_rows:
        lines.append(
            f"| {row['qid']} | {row['oracle_answerable']} | {row['agent_grade']} | "
            f"{row['primary_failure'] or '—'} | {row['tool_calls']} | "
            f"{row['source_anchors']} | {row['finding']} |"
        )
    lines.append("")
    lines.append("## Qualitative findings")
    lines.append("")
    lines.append("### Identity continuity")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("identity_continuity", "_pending_"))
    lines.append("")
    lines.append("### Multi-hop connectivity")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("multi_hop", "_pending_"))
    lines.append("")
    lines.append("### Ordered path retrieval")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("ordered_path", "_pending_"))
    lines.append("")
    lines.append("### Learned encounter facts")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("learned_encounter", "_pending_"))
    lines.append("")
    lines.append("### Source / play-vs-plan authority")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("authority", "_pending_"))
    lines.append("")
    lines.append("### Broad campaign-state investigation")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("campaign_state", "_pending_"))
    lines.append("")
    lines.append("### Bounded inference / abstention quality")
    lines.append("")
    lines.append(scorecard.get("qualitative", {}).get("bounded_inference", "_pending_"))
    lines.append("")
    lines.append("## Safeguards")
    lines.append("")
    lines.append(f"- Readiness ready: `{readiness.get('ready')}`")
    lines.append(
        f"- Head before: `{scorecard.get('head_before')}`; head after: `{scorecard.get('head_after')}`"
    )
    lines.append(
        f"- Head unchanged: `{scorecard.get('head_before') == scorecard.get('head_after')}`"
    )
    lines.append(
        f"- Gold SHA256: `{authority.get('gold_sha256')}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Operator dogfood is the readiness gate. Oracle-answerable vs Agent FULL "
        "is diagnostic only: a large gap points to Agent orchestration/synthesis; "
        "a low oracle count points to graph coverage/publication/authority. "
        "Neither structural score can override a dogfood blocker. "
        "This report does not select a semantic model. "
        "Production defects discovered here are handbacks, not repairs in this lane."
    )
    lines.append("")
    lines.append("## Handbacks (production; not repaired in this evaluation lane)")
    lines.append("")
    lines.append(
        "- **Published objects are not product-loadable.** C2S22 Mireward exists "
        "in `graph_payload` as `node:location:mireward` but search/object/"
        "complete-object/evidence all return empty / `found: false`. Candidate "
        "IDs stay `loc:mireward`. Graph Review quote-in-span (`evidence[2]`) "
        "cannot be validated against a product object the UI cannot open."
    )
    lines.append(
        "- **Hermes did not use the graph.** Agent smoke was HTTP 200 / "
        "`hermes_graph_agent` / `partial`, but Q01–Q16 recorded 0 tool calls "
        "and 0 FULL answers. Several questions were oracle-answerable from "
        "production retrieval; Hermes still abstained. Smoke is not dogfood."
    )
    lines.append(
        "- **Default World targeting is `eldyrwild`.** The accepted World id is "
        "`dogfood-current-corpus-acceptance-v1`. Without an explicit world-id "
        "override the operator cannot open this World in the UI."
    )
    lines.append(
        "- **World-union projection rejects empty `campaignId`.** Selecting C1+C2 "
        "has historically failed with `Projection campaign does not match "
        "requested campaign longmont-c2`. That is a product verifier defect."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_qualitative(question_grades: list[dict[str, Any]]) -> dict[str, str]:
    by_id = {g["question_id"]: g for g in question_grades}

    def note(qid: str) -> str:
        g = by_id.get(qid, {})
        return f"{qid}={g.get('agent_grade')} (fail={g.get('primary_failure') or 'none'})"

    return {
        "identity_continuity": note("Q11"),
        "multi_hop": ", ".join(note(q) for q in ("Q06", "Q07", "Q08")),
        "ordered_path": note("Q09"),
        "learned_encounter": note("Q10"),
        "authority": ", ".join(note(q) for q in ("Q14", "Q16")),
        "campaign_state": note("Q15"),
        "bounded_inference": note("Q16"),
    }


def prepare_live_session_fixture(run_dir: Path) -> Path:
    dest = run_dir / "live_session_fixture"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SEED_LIVE_SESSION, dest)
    (dest / "event_log.jsonl").write_text("", encoding="utf-8")
    (dest / "job_queue.jsonl").write_text("", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--questions",
        default=None,
        help="Comma-separated Q IDs (default: all Q01-Q16)",
    )
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--readiness-only", action="store_true")
    parser.add_argument("--authority-only", action="store_true")
    parser.add_argument(
        "--loadability-only",
        action="store_true",
        help="Run the C2S22 loc:mireward loadability probe; skip Q01-Q16 and Agent.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
    )
    args = parser.parse_args(argv)

    run_id = args.run_id or datetime.now(timezone.utc).strftime(
        "gauntlet-%Y%m%dT%H%M%SZ"
    )
    run_dir = args.artifact_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    ledger_row = resolve_benchmark_revision()
    benchmark_revision = ledger_row["receipt_child_revision"]
    authority = build_authority_record(
        benchmark_revision=benchmark_revision,
        ledger_row=ledger_row,
        run_id=run_id,
    )
    write_json(run_dir / "AUTHORITY.json", authority)
    print(f"AUTHORITY written; BENCHMARK_REVISION={benchmark_revision}")

    if args.authority_only:
        return 0

    if args.loadability_only:
        from evals.graph_benchmark.loadability import (
            evaluate_dogfood_readiness,
            run_loadability_probe,
        )

        with httpx.Client(base_url=args.base_url) as client:
            loadability = run_loadability_probe(client)
        dogfood = evaluate_dogfood_readiness(
            harness_ready=True,
            agent_smoke_ok=False,
            loadability=loadability,
        )
        write_json(run_dir / "LOADABILITY.json", loadability)
        write_json(run_dir / "DOGFOOD.json", dogfood)
        print(
            "LOADABILITY "
            f"seed_status={loadability['seed_status']} "
            f"revision={loadability['revision_pin']} "
            f"openable={loadability['openable']}"
        )
        print(json.dumps({
            "dogfood_ready": dogfood["dogfood_ready"],
            "blockers": dogfood["blockers"],
            "seed_status": loadability["seed_status"],
            "identity_remap": loadability.get("identity_remap"),
            "payload_objects": loadability.get("payload_objects"),
            "identities": [
                {
                    "node_id": row["node_id"],
                    "status": row["status"],
                    "payload_present": row["payload_present"],
                    "product_found": row["product_found"],
                }
                for row in loadability.get("identities") or []
            ],
            "search_world_outcome": (loadability.get("search_world") or {}).get("outcome"),
            "search_campaign_outcome": (loadability.get("search_campaign") or {}).get("outcome"),
        }, indent=2))
        return 0 if dogfood["dogfood_ready"] else 3

    head_before = read_world_head_via_psql()
    questions = load_gold_questions()
    if args.questions:
        wanted = {q.strip().upper() for q in args.questions.split(",") if q.strip()}
        questions = [q for q in questions if q.qid in wanted]
        if not questions:
            raise SystemExit(f"no questions matched {wanted}")

    from evals.graph_benchmark.loadability import (
        evaluate_dogfood_readiness,
        run_loadability_probe,
    )

    with httpx.Client(base_url=args.base_url) as client:
        readiness = run_readiness(
            client,
            benchmark_revision=benchmark_revision,
            skip_agent=args.skip_agent,
        )
        write_json(run_dir / "READINESS.json", readiness)
        print(
            "READINESS "
            f"harness_ready={readiness['harness_ready']} "
            f"agent_ok={readiness['dogfood_agent_ok']}"
        )
        if not readiness["harness_ready"]:
            print(json.dumps(readiness, indent=2))
            return 2
        if args.readiness_only:
            return 0

        print("=== loadability C2S22 loc:mireward ===")
        loadability = run_loadability_probe(client)
        write_json(run_dir / "LOADABILITY.json", loadability)
        print(
            "LOADABILITY "
            f"seed_status={loadability['seed_status']} "
            f"openable={loadability['openable']}"
        )

        skip_agent = args.skip_agent or not readiness.get("dogfood_agent_ok")
        skip_reason = (
            "operator_skip_agent"
            if args.skip_agent
            else "hermes_agent_unusable"
        )

        question_rows: list[dict[str, Any]] = []
        grades: list[dict[str, Any]] = []
        for question in questions:
            qdir = run_dir / question.qid
            qdir.mkdir(parents=True, exist_ok=True)
            print(f"=== {question.qid} oracle ===")
            oracle = run_oracle_for_question(
                client,
                question=question,
                benchmark_revision=benchmark_revision,
            )
            write_json(qdir / "oracle.json", oracle)

            if skip_agent:
                agent_request = build_agent_live_query_request(
                    question_text=question.question,
                    benchmark_revision=benchmark_revision,
                )
                write_json(qdir / "agent-request.json", agent_request)
                agent_response = {
                    "status_code": None,
                    "body": {"answer": "", "skipped": True, "reason": skip_reason},
                }
                write_json(qdir / "agent-response.json", agent_response)
                grade = _skipped_agent_grade(question, reason=skip_reason)
            else:
                print(f"=== {question.qid} agent ===")
                agent_request, agent_response = run_agent_for_question(
                    client,
                    question=question,
                    benchmark_revision=benchmark_revision,
                )
                write_json(qdir / "agent-request.json", agent_request)
                write_json(qdir / "agent-response.json", agent_response)
                grade = grade_agent_response(
                    question=question,
                    response_record=agent_response,
                    oracle=oracle,
                )
            write_json(qdir / "grade.json", grade)
            grades.append(grade)
            finding = grade.get("answer_excerpt") or grade.get("skip_reason") or ""
            finding = re.sub(r"\s+", " ", finding)[:80]
            question_rows.append(
                {
                    "qid": question.qid.replace("Q", ""),
                    "oracle_answerable": "yes" if oracle["oracle_answerable"] else "no",
                    "agent_grade": grade["agent_grade"],
                    "primary_failure": grade.get("primary_failure"),
                    "tool_calls": grade.get("tool_call_count", 0),
                    "source_anchors": grade.get("source_anchor_count", 0),
                    "finding": finding or "(empty)",
                }
            )
            print(
                f"{question.qid}: oracle={oracle['oracle_answerable']} "
                f"agent={grade['agent_grade']} fail={grade.get('primary_failure')}"
            )

    head_after = read_world_head_via_psql()
    failure_counts = {k: 0 for k in "ABCDEF"}
    for g in grades:
        pf = g.get("primary_failure")
        if pf in failure_counts:
            failure_counts[pf] += 1

    oracle_yes = 0
    for question in questions:
        oracle_path = run_dir / question.qid / "oracle.json"
        if oracle_path.exists():
            if json.loads(oracle_path.read_text())["oracle_answerable"]:
                oracle_yes += 1

    dogfood = evaluate_dogfood_readiness(
        harness_ready=bool(readiness.get("harness_ready")),
        agent_smoke_ok=bool(readiness.get("dogfood_agent_ok")),
        loadability=loadability,
        agent_full=sum(1 for g in grades if g["agent_grade"] == "FULL"),
        agent_ran=not skip_agent,
        agent_tool_calls=sum(int(g.get("tool_call_count") or 0) for g in grades),
    )
    write_json(run_dir / "DOGFOOD.json", dogfood)

    scorecard = {
        "schema": "dmb_current_corpus_question_gauntlet_scorecard_v1",
        "run_id": run_id,
        "benchmark_revision": benchmark_revision,
        "oracle_answerable": oracle_yes,
        "agent_full": sum(1 for g in grades if g["agent_grade"] == "FULL"),
        "agent_partial": sum(1 for g in grades if g["agent_grade"] == "PARTIAL"),
        "agent_fail": sum(1 for g in grades if g["agent_grade"] == "FAIL"),
        "failure_counts": failure_counts,
        "head_before": head_before,
        "head_after": head_after,
        "head_unchanged": head_before == head_after == TERMINAL_HEAD,
        "question_count": len(grades),
        "qualitative": build_qualitative(grades),
        "semantic_model_selection": "HOLD",
        "dogfood": dogfood,
        "agent_skipped": skip_agent,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_dir / "SCORECARD.json", scorecard)

    if not args.skip_report:
        report = render_report(
            authority=authority,
            readiness=readiness,
            scorecard=scorecard,
            question_rows=question_rows,
            run_id=run_id,
            loadability=loadability,
            dogfood=dogfood,
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"REPORT written: {REPORT_PATH}")

    print(json.dumps({
        "dogfood_ready": dogfood["dogfood_ready"],
        "oracle_answerable": scorecard["oracle_answerable"],
        "agent_full": scorecard["agent_full"],
        "agent_partial": scorecard["agent_partial"],
        "agent_fail": scorecard["agent_fail"],
        "failure_counts": scorecard["failure_counts"],
        "head_unchanged": scorecard["head_unchanged"],
        "blockers": dogfood["blockers"],
    }, indent=2))
    if not scorecard["head_unchanged"] or not dogfood["dogfood_ready"]:
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
