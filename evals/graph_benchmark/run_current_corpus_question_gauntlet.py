#!/usr/bin/env python3
"""Accepted-world C1S10 question gauntlet — oracle retrieval + real Hermes Agent.

Evaluation-only driver. Production code is read-only. Gold remains in
``evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md``.

Usage (after Terminal 1 FastAPI is up against the acceptance World):

    uv run python evals/graph_benchmark/run_current_corpus_question_gauntlet.py \\
        --base-url http://127.0.0.1:8000

    uv run python evals/graph_benchmark/run_current_corpus_question_gauntlet.py \\
        --serve --acceptance-dsn "$ACCEPTANCE_DSN" \\
        --live-session-dir "$LIVE_SESSION" --hermes-model gpt-5.6-luna
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
from typing import Any, Sequence

from urllib.parse import urlparse

import httpx

from graph_memory.anchor_quotes import find_anchor_quote_matches

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

UNRESOLVED_OWNING_BOUNDARY = "ABC-unresolved"
AGENT_STOPPED = "STOPPED"

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


def resolve_agent_runtime_identity() -> dict[str, Any]:
    """Bind the Agent provider/model actually configured for this process."""
    env_override = (os.environ.get("DUNGEONMIND_HERMES_GRAPH_MODEL") or "").strip() or None
    record: dict[str, Any] = {
        "query_backend": "hermes",
        "policy_action": "hermes_graph_agent",
        "provider": None,
        "model_id": env_override,
        "env_override": env_override,
        "source": "unresolved",
        "api_mode": None,
    }
    try:
        from apps.live_control_server.services.agent_graph_policy import (
            resolve_agent_graph_openai_inference,
        )

        resolved = resolve_agent_graph_openai_inference(require_api_key=False)
        if isinstance(resolved, tuple) and len(resolved) >= 2:
            record["provider"] = resolved[0]
            record["model_id"] = env_override or resolved[1]
            record["source"] = "env_override" if env_override else "model_policy"
        elif isinstance(resolved, str):
            record["source"] = "unresolved"
            record["resolve_error"] = resolved
    except Exception as exc:  # pragma: no cover - diagnostic only
        record["resolve_error"] = f"{type(exc).__name__}: {exc}"
    return record


def extract_agent_runtime_from_trace(body: Any) -> dict[str, Any]:
    payload = body if isinstance(body, dict) else {}
    trace = payload.get("agent_trace") if isinstance(payload.get("agent_trace"), dict) else {}
    calls = trace.get("model_calls") if isinstance(trace.get("model_calls"), list) else []
    first = calls[0] if calls and isinstance(calls[0], dict) else {}
    return {
        "provider": trace.get("provider") or first.get("provider"),
        "model_id": trace.get("model") or first.get("requested_model"),
        "api_mode": first.get("api_mode"),
        "runtime": trace.get("runtime"),
        "mode": trace.get("mode") or payload.get("mode"),
        "model_call_status": first.get("status"),
        "model_call_error_type": first.get("error_type"),
        "model_call_status_code": first.get("status_code"),
        "requested_model": first.get("requested_model"),
    }


def evaluate_agent_smoke(
    *,
    http_status: int | None,
    body: Any,
    benchmark_revision: str,
) -> dict[str, Any]:
    """Fail closed unless the Agent actually executed a usable investigation.

    HTTP 200 + hermes_graph_agent + revision pin is not Agent-ready when the
    wrapped model call errors or never runs. That is a STOP, not a D grade.
    """
    payload = body if isinstance(body, dict) else {}
    runtime = extract_agent_runtime_from_trace(payload)
    revision_ids = extract_revision_ids(payload)
    revision_ok = benchmark_revision in revision_ids
    wgc = payload.get("world_graph_context") or {}
    if isinstance(wgc, dict) and wgc.get("revision_id") == benchmark_revision:
        revision_ok = True
    trace = (
        payload.get("agent_trace")
        if isinstance(payload.get("agent_trace"), dict)
        else {}
    )
    context = trace.get("context_summary") if isinstance(trace, dict) else {}
    if isinstance(context, dict) and context.get("revision_id") == benchmark_revision:
        revision_ok = True
    mode_ok = payload.get("mode") == "hermes_graph_agent"
    calls = trace.get("model_calls") if isinstance(trace.get("model_calls"), list) else []
    call_statuses = [call.get("status") for call in calls if isinstance(call, dict)]
    has_ok_call = any(status == "ok" for status in call_statuses)
    has_error_call = any(status == "error" for status in call_statuses)
    provider_unavailable = bool(has_error_call and not has_ok_call)
    product_status = payload.get("status")
    truthful_outcome = product_status in {"ok", "abstained", "abstention"} or (
        product_status == "partial" and has_ok_call
    )
    trace_present = bool(trace)
    ok = (
        http_status == 200
        and mode_ok
        and revision_ok
        and trace_present
        and truthful_outcome
        and not provider_unavailable
    )
    error = _agent_smoke_error(payload)
    if provider_unavailable:
        error = {
            "code": runtime.get("model_call_error_type") or "model_call_error",
            "status": runtime.get("model_call_status"),
            "detail": " ".join(
                str(part)
                for part in (
                    runtime.get("model_call_status_code"),
                    runtime.get("model_call_error_type"),
                )
                if part not in (None, "")
            ),
        }
    return {
        "ok": ok,
        "status_code": http_status,
        "mode": payload.get("mode"),
        "mode_ok": mode_ok,
        "status": product_status,
        "revision_ok": revision_ok,
        "trace_present": trace_present,
        "truthful_outcome": truthful_outcome,
        "provider_unavailable": provider_unavailable,
        "has_ok_model_call": has_ok_call,
        "has_error_model_call": has_error_call,
        "runtime": runtime,
        "error": error,
    }


def merge_observed_agent_runtime(
    configured: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(configured)
    for key, value in observed.items():
        if value not in (None, "", []):
            merged[key] = value
    if observed.get("model_id") and configured.get("model_id"):
        merged["configured_model_id"] = configured.get("model_id")
        merged["observed_model_id"] = observed.get("model_id")
        if observed.get("model_id") != configured.get("model_id"):
            merged["model_identity_mismatch"] = True
    if observed.get("model_id") or observed.get("provider"):
        merged["source"] = "agent_trace"
    return merged


def serve_gauntlet_api(
    *,
    host: str,
    port: int,
    acceptance_dsn: str,
    live_session_dir: str,
    hermes_model: str | None,
) -> int:
    """Start FastAPI pinned to the acceptance World (evaluation-only)."""
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv
    import src.bootstrap_env as bootstrap_env

    load_dungeonmindbuddy_dotenv(override=True)
    bootstrap_env.load_dungeonmindbuddy_dotenv = lambda **_kwargs: None

    def _pin() -> None:
        os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY"] = "dungeonmind"
        os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = acceptance_dsn
        os.environ["DUNGEONMIND_DATABASE_URL"] = acceptance_dsn
        os.environ["DUNGEONMIND_LIVE_SESSION_DIR"] = live_session_dir
        if hermes_model:
            os.environ["DUNGEONMIND_HERMES_GRAPH_MODEL"] = hermes_model

    _pin()
    from apps.live_control_server.main import app
    _pin()
    from apps.live_control_server import config

    url = config.world_graph_authority_database_url() or ""
    if "dmb_current_corpus_acceptance_v1" not in url:
        print("refusing to start: acceptance DB not selected", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("refusing to start: OPENAI_API_KEY missing", file=sys.stderr)
        return 2
    print("authority_url_ok")
    print(
        "hermes_model",
        os.environ.get("DUNGEONMIND_HERMES_GRAPH_MODEL") or "(policy default)",
    )
    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=False)
    return 0


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
        "agent_runtime": resolve_agent_runtime_identity(),
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
    owning_boundary_status = "established" if oracle_answerable else "unresolved"
    owning_boundary_reason = None
    if not oracle_answerable:
        # Empty/partial retrieval cannot distinguish A (absent from World),
        # B (identity/connectivity), or C (bounded retrieval API).
        primary_failure = UNRESOLVED_OWNING_BOUNDARY
        owning_boundary_reason = (
            "Production retrieval did not expose gold must-include concepts. "
            "That outcome is compatible with A, B, or C; this evaluator does not "
            "inspect admitted payload/candidates for those propositions."
        )

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
        "owning_boundary_status": owning_boundary_status,
        "owning_boundary_reason": owning_boundary_reason,
        "retrieval_observation": {
            "node_count": len(all_ids["node_ids"]),
            "match_ratio": coverage["match_ratio"],
        },
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
    if agent_grade in {"FULL", AGENT_STOPPED}:
        if agent_grade == AGENT_STOPPED and not oracle.get("oracle_answerable"):
            return oracle.get("primary_failure_bucket") or UNRESOLVED_OWNING_BOUNDARY
        return None
    if not oracle.get("oracle_answerable"):
        return oracle.get("primary_failure_bucket") or UNRESOLVED_OWNING_BOUNDARY
    smoke = evaluate_agent_smoke(
        http_status=200,
        body=agent_body,
        benchmark_revision="",
    )
    if smoke.get("provider_unavailable") or not smoke.get("has_ok_model_call"):
        return None
    # Oracle succeeded → Agent-side failure after a completed model call.
    if question.qid in {"Q14", "Q16"}:
        return "E"
    tool_calls = count_tool_events(agent_body if isinstance(agent_body, dict) else {})
    if tool_calls <= 1:
        return "D"
    return "F"


def agent_stop_reason(smoke: dict[str, Any]) -> str:
    if not smoke.get("revision_ok"):
        return "agent_revision_mismatch"
    if smoke.get("provider_unavailable") or not smoke.get("has_ok_model_call"):
        return "agent_runtime_unavailable"
    return "agent_runtime_unavailable"


def pre_question_stop_reason(
    readiness: dict[str, Any],
    *,
    skip_agent: bool = False,
) -> str | None:
    """Return a STOP reason, or None if Q01 may begin.

    Handoff §5: do not begin Q01 until retrieval and Agent readiness are green.
    Provider unavailable is a STOP, not an oracle-only continuation.
    """
    if not readiness.get("harness_ready"):
        return "historical_retrieval"
    if skip_agent:
        return "operator_skip_agent"
    if not readiness.get("dogfood_agent_ok"):
        smoke = readiness.get("agent_smoke") or {}
        if smoke.get("provider_unavailable"):
            return "agent_runtime_unavailable"
        if smoke.get("revision_ok") is False:
            return "agent_revision_mismatch"
        return "agent_runtime_unavailable"
    return None


def grade_agent_response(
    *,
    question: GoldQuestion,
    response_record: dict[str, Any],
    oracle: dict[str, Any],
    benchmark_revision: str,
) -> dict[str, Any]:
    body = response_record.get("body") or {}
    if not isinstance(body, dict):
        body = {}
    smoke = evaluate_agent_smoke(
        http_status=response_record.get("status_code"),
        body=body,
        benchmark_revision=benchmark_revision,
    )
    if not smoke.get("ok"):
        return _stopped_agent_grade(
            question,
            reason=agent_stop_reason(smoke),
            oracle=oracle,
            agent_runtime=smoke.get("runtime") or extract_agent_runtime_from_trace(body),
        )
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
        agent_body=body,
    )
    agent_runtime = extract_agent_runtime_from_trace(body)
    revision_ids = extract_revision_ids(body)
    return {
        "question_id": question.qid,
        "agent_grade": scored["grade"],
        "must_include_matched": scored["must_include_matched"],
        "must_include_missed": scored["must_include_missed"],
        "must_not_claim_fired": scored["must_not_claim_fired"],
        "match_ratio": scored["match_ratio"],
        "primary_failure": primary,
        "secondary_failures": [],
        "tool_call_count": count_tool_events(body),
        "source_anchor_count": count_source_anchors_in_agent(body),
        "revision_ids_seen": sorted(revision_ids),
        "answer_excerpt": answer[:500],
        "http_status": response_record.get("status_code"),
        "agent_status": body.get("status"),
        "agent_mode": body.get("mode"),
        "agent_runtime": agent_runtime,
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
    agent_skipped = skip_agent
    smoke: dict[str, Any] = {
        "ok": False,
        "skipped": agent_skipped,
        "status_code": None,
        "mode": None,
        "mode_ok": False,
        "status": None,
        "revision_ok": False,
        "trace_present": False,
        "truthful_outcome": False,
        "provider_unavailable": False,
        "error": None,
    }
    if not skip_agent:
        smoke_req = build_agent_live_query_request(
            question_text="Who is Torbin in Campaign 1?",
            benchmark_revision=benchmark_revision,
        )
        agent_status, agent_body = _post_json(
            client, "/api/live/query", smoke_req, timeout=300.0
        )
        smoke = evaluate_agent_smoke(
            http_status=agent_status,
            body=agent_body,
            benchmark_revision=benchmark_revision,
        )
        smoke["skipped"] = False
    agent_ok = bool(smoke.get("ok"))
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
        "agent_smoke": smoke,
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


def diagnostic_finding(*, oracle: dict[str, Any], grade: dict[str, Any]) -> str:
    """Short per-question diagnostic; not a truncated answer excerpt."""
    runtime = grade.get("agent_runtime") or {}
    model = runtime.get("model_id") or runtime.get("requested_model")
    api_mode = runtime.get("api_mode")
    err = runtime.get("model_call_error_type")
    code = runtime.get("model_call_status_code")
    stopped = grade.get("agent_grade") == AGENT_STOPPED or bool(grade.get("skip_reason"))
    oracle_miss = not oracle.get("oracle_answerable")
    if oracle_miss:
        observation = oracle.get("retrieval_observation") or {}
        nodes = observation.get("node_count")
        if nodes is None:
            nodes = len((oracle.get("matched_ids") or {}).get("node_ids") or [])
        ratio = observation.get("match_ratio")
        if ratio is None:
            ratio = (oracle.get("coverage_vs_must_include") or {}).get("match_ratio")
        if isinstance(ratio, float):
            ratio = round(ratio, 2)
        miss = (
            f"oracle miss; retrieval nodes={nodes} match_ratio={ratio}; "
            f"{UNRESOLVED_OWNING_BOUNDARY}"
        )
        if stopped:
            return f"{miss}; Agent STOPPED"
        return miss
    if stopped:
        runtime_note = " ".join(
            str(part)
            for part in (model, api_mode, code, err)
            if part not in (None, "")
        )
        reason = grade.get("skip_reason") or "agent_runtime_unavailable"
        if runtime_note:
            return f"Agent STOPPED ({reason}); {runtime_note}"
        return f"Agent STOPPED ({reason})"
    tools = grade.get("tool_call_count", 0)
    return f"oracle yes; tools={tools}; agent={grade.get('agent_grade')}"


def _stopped_agent_grade(
    question: GoldQuestion,
    *,
    reason: str,
    oracle: dict[str, Any],
    agent_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    primary = None
    if not oracle.get("oracle_answerable"):
        primary = oracle.get("primary_failure_bucket") or UNRESOLVED_OWNING_BOUNDARY
    return {
        "question_id": question.qid,
        "agent_grade": AGENT_STOPPED,
        "primary_failure": primary,
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
        "agent_status": AGENT_STOPPED,
        "agent_mode": None,
        "agent_runtime": agent_runtime or {},
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
    runtime = (authority.get("agent_runtime") or {})
    lines.append(
        f"**Agent runtime:** provider=`{runtime.get('provider')}` "
        f"model=`{runtime.get('model_id')}` "
        f"api_mode=`{runtime.get('api_mode')}` "
        f"source=`{runtime.get('source')}`"
    )
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
    questions_started = scorecard.get("questions_started")
    if questions_started is False:
        lines.append("oracle answerable: not started (STOP before Q01)")
    else:
        lines.append(
            f"oracle answerable: {scorecard['oracle_answerable']} / 16"
        )
    agent_stopped = (
        scorecard.get("agent_suite") == AGENT_STOPPED
        or scorecard.get("agent_skipped")
        or int(scorecard.get("agent_stopped") or 0) == 16
    )
    if agent_stopped:
        lines.append("Agent suite:       STOPPED (not scored)")
        lines.append("Agent FULL:        —")
        lines.append("Agent PARTIAL:     —")
        lines.append("Agent FAIL:        —")
    else:
        lines.append(f"Agent FULL:        {scorecard['agent_full']} / 16")
        lines.append(f"Agent PARTIAL:     {scorecard['agent_partial']} / 16")
        lines.append(f"Agent FAIL:        {scorecard['agent_fail']} / 16")
    lines.append(
        f"A proven:          {scorecard['failure_counts'].get('A', 0)}"
    )
    lines.append(
        f"B proven:          {scorecard['failure_counts'].get('B', 0)}"
    )
    lines.append(
        f"C proven:          {scorecard['failure_counts'].get('C', 0)}"
    )
    lines.append(
        "ABC-unresolved:    "
        f"{scorecard.get('oracle_unresolved_owning_boundary', 0)}"
    )
    for bucket in ("D", "E", "F"):
        lines.append(
            f"{bucket}: {scorecard['failure_counts'].get(bucket, 0)}"
        )
    lines.append("```")
    lines.append("")
    lines.append(
        "A/B/C are only counted when the owning boundary is proven. "
        "An oracle miss from empty or partial retrieval is `ABC-unresolved`, "
        "not a graph-coverage claim."
    )
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
    lines.append(
        f"- Retrieval harness ready (C1S10 pin): `{readiness.get('harness_ready', readiness.get('ready'))}`"
    )
    lines.append(
        f"- Agent smoke ok: `{readiness.get('dogfood_agent_ok')}`"
    )
    lines.append(
        f"- dogfood_ready: `{scorecard.get('dogfood', {}).get('dogfood_ready')}`"
    )
    lines.append(
        f"- Head before: `{scorecard.get('head_before')}`; head after: `{scorecard.get('head_after')}`"
    )
    lines.append(
        f"- Head unchanged: `{scorecard.get('head_before') == scorecard.get('head_after')}`"
    )
    lines.append(
        f"- Gold SHA256: `{authority.get('gold_sha256')}`"
    )
    lines.append(
        "- Q01–Q16 started: "
        f"`{scorecard.get('questions_started', True)}` "
        "(handoff §5: STOP before Q01 unless Agent readiness is green)"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Operator dogfood is the readiness gate. Oracle-answerable vs Agent FULL "
        "is diagnostic only: a large gap points to Agent orchestration/synthesis; "
        "a low oracle count points to graph coverage/publication/authority. "
        "Neither structural score can override a dogfood blocker. "
        "The Agent suite is not scored when the runtime prerequisite fails. "
        "A failed Agent readiness gate STOPs before Q01; the runner does not "
        "walk oracle questions after that STOP. "
        "A low oracle-answerable count is not, by itself, a proven graph-coverage "
        "failure (A); those misses remain ABC-unresolved until an owning-boundary "
        "check exists. "
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
        "- **Agent runtime unavailable (STOP).** Hermes `/api/live/query` returned "
        "HTTP 200 / `hermes_graph_agent` wrapping `openai-api` / `gpt-5.6-luna` / "
        "`chat_completions` 400 `BadRequestError` before any tool call. The Agent "
        "suite is STOPPED and not scored. That is a provider/model prerequisite "
        "failure, not D. HTTP 200 / `hermes_graph_agent` / `partial` is not Agent-ready."
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
        grade = g.get("agent_grade")
        primary = g.get("primary_failure")
        if grade == AGENT_STOPPED:
            if primary == UNRESOLVED_OWNING_BOUNDARY:
                return f"{qid} oracle miss ({UNRESOLVED_OWNING_BOUNDARY}); Agent STOPPED"
            if primary:
                return f"{qid} Agent STOPPED (oracle {primary})"
            return f"{qid} Agent STOPPED (not scored)"
        fail = primary or "none"
        return f"{qid}={grade} (fail={fail})"

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


# ---------------------------------------------------------------------------
# Loadability probe (folded into the leased runner)
# ---------------------------------------------------------------------------

LOADABILITY_CAMPAIGN_ID = OUTER_CAMPAIGN_ID
LOADABILITY_SESSION_ID = "session-22"
CANDIDATE_NODE_ID = "loc:mireward"
PUBLISHED_OBJECT_ID = "node:location:mireward"
SEARCH_TEXT = "Mireward"
C2S22_REVISION = "rev:24268294e868b30034e247aa9e23087b"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9:_-]+$")

LoadabilityStatus = str

STATUS_AUTHORITY_ABSENT = "authority_absent"
STATUS_CANDIDATE_NOT_ADMITTED = "candidate_not_admitted"
STATUS_PRODUCT_UNRESOLVED = "product_unresolved"
STATUS_EXCERPT_READY = "excerpt_ready"
STATUS_QUOTE_MISMATCH = "quote_mismatch"
STATUS_SOURCE_NOT_DURABLE = "source_not_durable"
STATUS_SPAN_UNRESOLVABLE = "span_unresolvable"
STATUS_UNREADABLE_ANCHOR = "unreadable_anchor"

_STATUS_PRIORITY = (
    STATUS_QUOTE_MISMATCH,
    STATUS_PRODUCT_UNRESOLVED,
    STATUS_UNREADABLE_ANCHOR,
    STATUS_SOURCE_NOT_DURABLE,
    STATUS_SPAN_UNRESOLVABLE,
    STATUS_CANDIDATE_NOT_ADMITTED,
    STATUS_AUTHORITY_ABSENT,
    STATUS_EXCERPT_READY,
)


def _require_safe_id(value: str, *, what: str) -> str:
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"refusing to interpolate unsafe {what}: {value!r}")
    return value


def build_loadability_search_request(
    *,
    query_text: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    scope_mode: str = "world",
    seed_node_ids: list[str] | None = None,
    focus_session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_search_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "scopeMode": scope_mode,
        "queryText": query_text,
        "seedNodeIds": list(seed_node_ids or []),
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_loadability_object_request(
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    scope_mode: str = "world",
    focus_session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_object_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "scopeMode": scope_mode,
        "nodeId": node_id,
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_loadability_complete_object_request(
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    focus_session_id: str | None = None,
    origin_surface: str = "ingest",
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_object_projection_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "nodeId": node_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "originSurface": origin_surface,
    }


def build_loadability_evidence_request(
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    scope_mode: str = "world",
    focus_session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_evidence_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "scopeMode": scope_mode,
        "target": {"kind": "node", "id": node_id},
        "bounds": {"maxSourceAnchors": 32},
    }


def _focus(session_id: str | None, campaign_id: str) -> dict[str, Any]:
    if session_id:
        return {
            "kind": "session",
            "sessionId": session_id,
            "campaignId": campaign_id,
        }
    return {"kind": "none", "sessionId": None, "campaignId": None}


def classify_loadability(
    *,
    candidate_present: bool,
    payload_present: bool,
    product_found: bool,
    provenance_statuses: Sequence[str] = (),
    quotes_checked: bool = False,
    quotes_all_matched: bool = False,
) -> LoadabilityStatus:
    """Classify one identity: candidate vs admitted payload vs product read."""
    if product_found:
        if quotes_checked and not quotes_all_matched:
            return STATUS_QUOTE_MISMATCH
        statuses = [s for s in provenance_statuses if s]
        if statuses and all(s == "excerpt_ready" for s in statuses):
            return STATUS_EXCERPT_READY
        if statuses and all(s == "source_not_durable" for s in statuses):
            return STATUS_SOURCE_NOT_DURABLE
        if statuses and all(s == "span_unresolvable" for s in statuses):
            return STATUS_SPAN_UNRESOLVABLE
        if any(s == "excerpt_ready" for s in statuses):
            return STATUS_EXCERPT_READY
        return STATUS_UNREADABLE_ANCHOR
    if payload_present:
        return STATUS_PRODUCT_UNRESOLVED
    if candidate_present:
        return STATUS_CANDIDATE_NOT_ADMITTED
    return STATUS_AUTHORITY_ABSENT


def evaluate_dogfood_readiness(
    *,
    harness_ready: bool,
    agent_smoke_ok: bool,
    loadability: dict[str, Any] | None,
    agent_full: int | None = None,
    agent_ran: bool = False,
    agent_tool_calls: int | None = None,
) -> dict[str, Any]:
    """Operator dogfood is the readiness gate.

    Structural oracle PASS does not make the World ready. If the GM cannot
    load admitted objects or get a usable Hermes answer, the product is
    not ready.
    """
    blockers: list[dict[str, str]] = []
    if not harness_ready:
        blockers.append(
            {
                "id": "historical_retrieval",
                "detail": (
                    "C1S10 retrieval smoke did not pin BENCHMARK_REVISION; "
                    "the operator cannot even query the historical World."
                ),
            }
        )
    if not agent_smoke_ok:
        blockers.append(
            {
                "id": "hermes_agent",
                "detail": (
                    "Hermes Agent runtime was unavailable. HTTP 200 / "
                    "hermes_graph_agent wrapping a provider/model error is not "
                    "Agent-ready. The Agent suite STOPPED and is not scored."
                ),
            }
        )
    elif agent_ran and agent_full == 0:
        tool_note = (
            f" (tool_calls={agent_tool_calls})"
            if agent_tool_calls is not None
            else ""
        )
        blockers.append(
            {
                "id": "hermes_cannot_answer",
                "detail": (
                    "Hermes returned 0 FULL answers"
                    f"{tool_note}. HTTP 200 / hermes_graph_agent is not dogfood "
                    "if the operator cannot get a usable graph-backed answer."
                ),
            }
        )
    if loadability is None:
        blockers.append(
            {
                "id": "loadability_missing",
                "detail": "Ingested-object loadability was not probed.",
            }
        )
    elif not loadability.get("openable") or loadability.get("seed_status") != STATUS_EXCERPT_READY:
        seed_status = loadability.get("seed_status")
        remap = loadability.get("identity_remap") or {}
        blockers.append(
            {
                "id": "ingested_object_unreadable",
                "detail": (
                    "Admitted C2S22 Mireward is not loadable through product "
                    f"reads (seed_status={seed_status}; "
                    f"candidate={remap.get('from_candidate_id')}; "
                    f"published={remap.get('to_published_ids')})."
                ),
            }
        )
    return {
        "schema": "dmb_current_corpus_dogfood_readiness_v1",
        "rule": (
            "If the operator cannot dogfood the accepted World, it is not ready. "
            "Structural retrieval PASS is not product readiness."
        ),
        "dogfood_ready": not blockers,
        "blockers": blockers,
    }


def roll_up_seed_status(statuses: Sequence[str]) -> LoadabilityStatus:
    remaining = set(statuses)
    if not remaining:
        return STATUS_AUTHORITY_ABSENT
    for status in _STATUS_PRIORITY:
        if status in remaining:
            return status
    return next(iter(remaining))


def extract_candidate_node(
    candidate_path: Path,
    node_id: str,
) -> dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    nodes = payload.get("nodes") if isinstance(payload, dict) else None
    if not isinstance(nodes, list):
        raise RuntimeError(f"candidate missing nodes list: {candidate_path}")
    match = next(
        (
            node
            for node in nodes
            if isinstance(node, dict) and node.get("node_id") == node_id
        ),
        None,
    )
    if match is None:
        return {
            "present": False,
            "node_id": node_id,
            "label": None,
            "node_type": None,
            "evidence_ref_count": 0,
            "quotes": [],
        }
    quotes: list[dict[str, Any]] = []
    for index, evidence in enumerate(match.get("evidence_refs") or []):
        if not isinstance(evidence, dict):
            continue
        for quote_index, quote in enumerate(evidence.get("anchor_quotes") or []):
            if not isinstance(quote, str) or not quote.strip():
                continue
            quotes.append(
                {
                    "evidence_index": index,
                    "quote_index": quote_index,
                    "char_len": len(quote),
                    "text": quote,
                    "source_span_ref_id": evidence.get("source_span_ref_id"),
                    "source_artifact_id": evidence.get("source_artifact_id"),
                    "can_open_source": evidence.get("can_open_source"),
                    "can_highlight_span": evidence.get("can_highlight_span"),
                }
            )
    return {
        "present": True,
        "node_id": node_id,
        "label": match.get("label"),
        "node_type": match.get("node_type"),
        "proposed_action": match.get("proposed_action"),
        "evidence_ref_count": len(match.get("evidence_refs") or []),
        "quotes": quotes,
    }


def candidate_public_view(extracted: dict[str, Any]) -> dict[str, Any]:
    """Drop quote text before persisting artifacts."""
    quotes = [
        {
            "evidence_index": row["evidence_index"],
            "quote_index": row["quote_index"],
            "char_len": row["char_len"],
            "source_span_ref_id": row.get("source_span_ref_id"),
            "source_artifact_id": row.get("source_artifact_id"),
            "can_open_source": row.get("can_open_source"),
            "can_highlight_span": row.get("can_highlight_span"),
        }
        for row in extracted.get("quotes") or []
    ]
    return {
        "present": extracted.get("present"),
        "node_id": extracted.get("node_id"),
        "label": extracted.get("label"),
        "node_type": extracted.get("node_type"),
        "proposed_action": extracted.get("proposed_action"),
        "evidence_ref_count": extracted.get("evidence_ref_count"),
        "quote_count": len(quotes),
        "quotes": quotes,
    }


def lookup_payload_objects(
    *,
    revision_id: str,
    object_ids: Sequence[str],
    label_needle: str,
) -> list[dict[str, str]]:
    revision = _require_safe_id(revision_id, what="revision_id")
    world_id = _require_safe_id(WORLD_ID, what="world_id")
    safe_ids = [_require_safe_id(item, what="object_id") for item in object_ids]
    if not safe_ids:
        return []
    ids_sql = ", ".join(f"'{item}'" for item in safe_ids)
    needle = label_needle.replace("'", "''")
    sql = f"""
SELECT obj->>'object_id', coalesce(obj->>'kind',''), coalesce(obj->>'label','')
FROM dungeonmind.graph_revisions r,
LATERAL jsonb_array_elements(r.graph_payload->'objects') obj
WHERE r.world_id = '{world_id}'
  AND r.revision_id = '{revision}'
  AND (
    obj->>'object_id' IN ({ids_sql})
    OR obj->>'label' ILIKE '%{needle}%'
  );
"""
    env = os.environ.copy()
    env.setdefault("PGPASSWORD", "dungeonmind-dev")
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
    rows: list[dict[str, str]] = []
    if not out:
        return rows
    for line in out.splitlines():
        object_id, kind, label = (line.split("|") + ["", ""])[:3]
        rows.append({"object_id": object_id, "kind": kind, "label": label})
    return rows


def summarize_retrieval(status_code: int, body: Any) -> dict[str, Any]:
    payload = body if isinstance(body, dict) else {"non_object": True}
    ids = collect_ids(payload) if isinstance(body, dict) else {
        "node_ids": [],
        "relationship_ids": [],
        "attribute_ids": [],
        "source_anchor_ids": [],
    }
    snapshot = payload.get("snapshot") or {}
    if not snapshot and isinstance(payload.get("result"), dict):
        snapshot = payload["result"].get("snapshot") or {}
    coverage = payload.get("coverage") or {}
    return {
        "http_status": status_code,
        "outcome": payload.get("outcome"),
        "found": payload.get("found"),
        "requested_node_id": payload.get("requestedNodeId")
        or payload.get("requested_node_id"),
        "resolved_node_id": payload.get("resolvedNodeId")
        or payload.get("resolved_node_id"),
        "revision_id": (
            snapshot.get("revisionId") or snapshot.get("revision_id")
            if isinstance(snapshot, dict)
            else None
        ),
        "node_ids": ids["node_ids"],
        "source_anchor_ids": ids["source_anchor_ids"],
        "missing_seed_node_ids": coverage.get("missingSeedNodeIds")
        or coverage.get("missing_seed_node_ids")
        or [],
        "resolved_redirects": coverage.get("resolvedRedirects")
        or coverage.get("resolved_redirects")
        or {},
        "error_code": payload.get("code") or payload.get("error"),
    }


def summarize_complete_object(status_code: int, body: Any) -> dict[str, Any]:
    payload = body if isinstance(body, dict) else {}
    bindings = payload.get("sourceBindings") or payload.get("source_bindings") or []
    provenance: list[str] = []
    artifact_ids: list[str] = []
    session_ids: list[str] = []
    excerpts: list[str] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        status = binding.get("provenanceStatus") or binding.get("provenance_status")
        if isinstance(status, str):
            provenance.append(status)
        artifact = binding.get("sourceArtifactId") or binding.get("source_artifact_id")
        if isinstance(artifact, str):
            artifact_ids.append(artifact)
        session_id = binding.get("sessionId") or binding.get("session_id")
        if isinstance(session_id, str):
            session_ids.append(session_id)
        excerpt = binding.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            excerpts.append(excerpt)
    return {
        "http_status": status_code,
        "found": payload.get("found"),
        "requested_node_id": payload.get("requestedNodeId")
        or payload.get("requested_node_id"),
        "resolved_node_id": payload.get("resolvedNodeId")
        or payload.get("resolved_node_id"),
        "completeness": payload.get("completeness"),
        "assertion_count": len(payload.get("assertions") or []),
        "relationship_count": len(payload.get("relationships") or []),
        "provenance_statuses": provenance,
        "source_artifact_ids": sorted(set(artifact_ids)),
        "session_ids": sorted(set(session_ids)),
        "excerpt_count": len(excerpts),
        "excerpts": excerpts,
        "error_code": payload.get("code") or payload.get("error"),
    }


def match_quotes_against_excerpts(
    quotes: Sequence[dict[str, Any]],
    excerpts: Sequence[str],
) -> dict[str, Any]:
    if not quotes:
        return {
            "quotes_checked": False,
            "quotes_all_matched": False,
            "matched": [],
        }
    if not excerpts:
        return {
            "quotes_checked": False,
            "quotes_all_matched": False,
            "matched": [],
        }
    matched: list[dict[str, Any]] = []
    all_matched = True
    for quote in quotes:
        text = quote.get("text") or ""
        hits = False
        for excerpt in excerpts:
            if find_anchor_quote_matches(excerpt, [text]):
                hits = True
                break
        if not hits:
            all_matched = False
        matched.append(
            {
                "evidence_index": quote.get("evidence_index"),
                "quote_index": quote.get("quote_index"),
                "char_len": quote.get("char_len"),
                "matched": hits,
            }
        )
    return {
        "quotes_checked": True,
        "quotes_all_matched": all_matched,
        "matched": matched,
    }


def _product_found(complete_summaries: Sequence[dict[str, Any]], object_summaries: Sequence[dict[str, Any]]) -> bool:
    return any(row.get("found") is True for row in complete_summaries) or any(
        row.get("outcome") not in (None, "empty") and row.get("http_status") == 200
        and (row.get("node_ids") or row.get("found") is True)
        for row in object_summaries
    )


def probe_identity(
    client: httpx.Client,
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str,
    session_id: str,
    candidate_present: bool,
    payload_present: bool,
    candidate_quotes: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    complete_none_status, complete_none_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/complete-object",
        build_loadability_complete_object_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
        ),
    )
    complete_session_status, complete_session_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/complete-object",
        build_loadability_complete_object_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            focus_session_id=session_id,
        ),
    )
    object_status, object_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/object",
        build_loadability_object_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            focus_session_id=session_id,
        ),
    )
    evidence_status, evidence_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/evidence",
        build_loadability_evidence_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            focus_session_id=session_id,
        ),
    )

    complete_none = summarize_complete_object(complete_none_status, complete_none_body)
    complete_session = summarize_complete_object(
        complete_session_status, complete_session_body
    )
    object_summary = summarize_retrieval(object_status, object_body)
    evidence_summary = summarize_retrieval(evidence_status, evidence_body)

    excerpts = list(complete_none.get("excerpts") or []) + list(
        complete_session.get("excerpts") or []
    )
    quote_report = match_quotes_against_excerpts(candidate_quotes, excerpts)
    provenance = list(complete_none.get("provenance_statuses") or []) + list(
        complete_session.get("provenance_statuses") or []
    )
    found = _product_found(
        [complete_none, complete_session],
        [object_summary, evidence_summary],
    )
    status = classify_loadability(
        candidate_present=candidate_present,
        payload_present=payload_present,
        product_found=found,
        provenance_statuses=provenance,
        quotes_checked=quote_report["quotes_checked"],
        quotes_all_matched=quote_report["quotes_all_matched"],
    )
    complete_none.pop("excerpts", None)
    complete_session.pop("excerpts", None)
    return {
        "node_id": node_id,
        "candidate_present": candidate_present,
        "payload_present": payload_present,
        "product_found": found,
        "status": status,
        "quote_report": {
            "quotes_checked": quote_report["quotes_checked"],
            "quotes_all_matched": quote_report["quotes_all_matched"],
            "matched": quote_report["matched"],
        },
        "complete_object_focus_none": complete_none,
        "complete_object_focus_session": complete_session,
        "object": object_summary,
        "evidence": evidence_summary,
    }


def run_loadability_probe(
    client: httpx.Client,
    *,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    session_id: str = LOADABILITY_SESSION_ID,
    candidate_node_id: str = CANDIDATE_NODE_ID,
    search_text: str = SEARCH_TEXT,
    lookup_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    ids = list(lookup_ids or (candidate_node_id, PUBLISHED_OBJECT_ID))
    ledger_row = resolve_ledger_session_row(campaign_id, session_id)
    revision_pin = ledger_row["receipt_child_revision"]
    if revision_pin == TERMINAL_HEAD:
        raise RuntimeError(
            f"{campaign_id}/{session_id} unexpectedly equals terminal head"
        )
    if (
        campaign_id == LOADABILITY_CAMPAIGN_ID
        and session_id == LOADABILITY_SESSION_ID
        and revision_pin != C2S22_REVISION
    ):
        raise RuntimeError(
            f"C2S22 revision drifted: got {revision_pin}, expected {C2S22_REVISION}"
        )

    locator = ledger_row.get("candidate_locator")
    if not isinstance(locator, str) or not locator:
        raise RuntimeError("candidate_locator missing from ledger row")
    candidate_path = PROJECT_ROOT / locator
    extracted = extract_candidate_node(candidate_path, candidate_node_id)
    payload_rows = lookup_payload_objects(
        revision_id=revision_pin,
        object_ids=ids,
        label_needle=search_text,
    )
    payload_ids = {row["object_id"] for row in payload_rows}
    identity_remap = None
    if extracted["present"] and candidate_node_id not in payload_ids:
        published = sorted(
            item for item in payload_ids if item != candidate_node_id
        )
        if published:
            identity_remap = {
                "from_candidate_id": candidate_node_id,
                "to_published_ids": published,
            }

    search_world_status, search_world_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/search",
        build_loadability_search_request(
            query_text=search_text,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            scope_mode="world",
            focus_session_id=session_id,
        ),
    )
    search_campaign_status, search_campaign_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/search",
        build_loadability_search_request(
            query_text=search_text,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            scope_mode="campaign",
            focus_session_id=session_id,
        ),
    )

    identities = [
        probe_identity(
            client,
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            session_id=session_id,
            candidate_present=extracted["present"] and node_id == candidate_node_id,
            payload_present=node_id in payload_ids,
            candidate_quotes=extracted.get("quotes") or [],
        )
        for node_id in ids
    ]
    seed_status = roll_up_seed_status(row["status"] for row in identities)
    return {
        "schema": "dmb_current_corpus_loadability_probe_v1",
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "world_id": WORLD_ID,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "revision_pin": revision_pin,
        "terminal_head": TERMINAL_HEAD,
        "search_text": search_text,
        "candidate": candidate_public_view(extracted),
        "payload_objects": payload_rows,
        "identity_remap": identity_remap,
        "search_world": summarize_retrieval(search_world_status, search_world_body),
        "search_campaign": summarize_retrieval(
            search_campaign_status, search_campaign_body
        ),
        "identities": identities,
        "seed_status": seed_status,
        "openable": seed_status == STATUS_EXCERPT_READY,
        "notes": [
            "Read-only evaluator probe; not an admission gate.",
            "Quote text and source excerpts are not persisted.",
        ],
    }



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
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--acceptance-dsn", default=None)
    parser.add_argument("--live-session-dir", default=None)
    parser.add_argument(
        "--hermes-model",
        default=None,
        help="Optional DUNGEONMIND_HERMES_GRAPH_MODEL override for --serve.",
    )
    args = parser.parse_args(argv)
    if args.serve:
        if not args.acceptance_dsn or not args.live_session_dir:
            raise SystemExit(
                "--serve requires --acceptance-dsn and --live-session-dir"
            )
        return serve_gauntlet_api(
            host=args.host,
            port=args.port,
            acceptance_dsn=args.acceptance_dsn,
            live_session_dir=args.live_session_dir,
            hermes_model=args.hermes_model,
        )

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

        stop_reason = pre_question_stop_reason(
            readiness, skip_agent=args.skip_agent
        )
        skip_agent = stop_reason is not None
        skip_reason = stop_reason
        questions_started = stop_reason is None

        question_rows: list[dict[str, Any]] = []
        grades: list[dict[str, Any]] = []
        if stop_reason:
            print(f"STOP before Q01: {stop_reason}")
        else:
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
                    benchmark_revision=benchmark_revision,
                )
                write_json(qdir / "grade.json", grade)
                grades.append(grade)
                finding = diagnostic_finding(oracle=oracle, grade=grade)
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
    unresolved_owning_boundary = 0
    observed_runtimes: list[dict[str, Any]] = []
    for g in grades:
        pf = g.get("primary_failure")
        if pf in failure_counts:
            failure_counts[pf] += 1
        elif pf == UNRESOLVED_OWNING_BOUNDARY:
            unresolved_owning_boundary += 1
        runtime = g.get("agent_runtime")
        if isinstance(runtime, dict):
            observed_runtimes.append(runtime)
    if observed_runtimes:
        authority["agent_runtime"] = merge_observed_agent_runtime(
            authority.get("agent_runtime") or {},
            observed_runtimes[0],
        )
        write_json(run_dir / "AUTHORITY.json", authority)

    oracle_yes = 0
    if questions_started:
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
        "agent_stopped": sum(1 for g in grades if g["agent_grade"] == AGENT_STOPPED),
        "agent_suite": AGENT_STOPPED if skip_agent else "SCORED",
        "agent_stop_reason": skip_reason if skip_agent else None,
        "questions_started": questions_started,
        "failure_counts": failure_counts,
        "oracle_unresolved_owning_boundary": unresolved_owning_boundary,
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
