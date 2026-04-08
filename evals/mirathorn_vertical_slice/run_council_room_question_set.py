from __future__ import annotations

import io
import importlib
import json
import os
import re
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DungeonBuddyCLI = importlib.import_module("src.cli").DungeonBuddyCLI
format_projection_context = importlib.import_module(
    "src.agent.context_formatter"
).format_projection_context
attach_scope_relevance_metadata = importlib.import_module(
    "src.reducer.canon_projection"
).attach_scope_relevance_metadata
filter_projection = importlib.import_module(
    "src.agent.retriever"
).filter_projection
DEFAULT_CAMPAIGN_ID = "longmont-c1"
GOLD_QUESTIONS_PATH = Path(__file__).resolve().parent / "gold" / "gold_questions.json"
# Artifact writes are opt-in so dry runs / CI / unset shell keys cannot clobber trusted
# bench output when dotenv (e.g. .env.development) repopulates OPENAI_API_KEY.
WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV = (
    "DMB_WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS"
)
RETRIEVAL_ENV = "DMB_RETRIEVAL"
RETRIEVAL_TOP_K_ENV = "DMB_RETRIEVAL_TOP_K"
SEMANTIC_RERANK_ENV = "DMB_SEMANTIC_RERANK"
SEMANTIC_RERANK_TOP_K_ENV = "DMB_SEMANTIC_RERANK_TOP_K"
SEMANTIC_RERANK_WEIGHT_ENV = "DMB_SEMANTIC_RERANK_WEIGHT"
SEMANTIC_RERANK_MODEL_ENV = "DMB_SEMANTIC_RERANK_MODEL"
EVIDENCE_FIRST_ENV = "DMB_EVIDENCE_FIRST"
EVIDENCE_TOP_K_ENV = "DMB_EVIDENCE_TOP_K"
EVIDENCE_NEIGHBOR_WINDOW_ENV = "DMB_EVIDENCE_NEIGHBOR_WINDOW"
EVIDENCE_MAX_NEIGHBORS_ENV = "DMB_EVIDENCE_MAX_NEIGHBORS"
EVIDENCE_ENTITY_BOOST_ENV = "DMB_EVIDENCE_ENTITY_BOOST"
CONTEXT_MAX_ENTITIES_ENV = "DMB_CONTEXT_MAX_ENTITIES"
CONTEXT_MAX_CHARS_ENV = "DMB_CONTEXT_MAX_CHARS"
COMPARE_EVIDENCE_FIRST_ENV = "DMB_COMPARE_EVIDENCE_FIRST"
EMBEDDING_SCORING_ENV = "DMB_EMBEDDING_SCORING"
EMBEDDING_USE_TLDR_ONLY_ENV = "DMB_EMBEDDING_USE_TLDR_ONLY"
CLAIM_VERIFICATION_ENV = "DMB_CLAIM_VERIFICATION"
CLAIM_VERIFICATION_USE_LLM_EXTRACTOR_ENV = "DMB_CLAIM_VERIFICATION_USE_LLM_EXTRACTOR"
EMBEDDING_WATCH_THRESHOLD = 0.55
GLOBAL_STALE_PATTERNS = (
    "nothing changed",
    "no changes",
    "no observed or prep",
    "no observed updates",
    "no observed facts",
    "architecturally unchanged",
)
UPDATE_SIGNAL_TOKENS = (
    "observed",
    "disheveled",
    "activated",
    "fireball",
    "killing blow",
    "decapitated",
    "dead",
    "fades",
)

SEMANTIC_EQUIVALENCES: dict[str, list[str]] = {
    "killing blow": ["decapitated", "head removed", "struck down", "killed"],
    "dead": ["decapitated", "head removed", "death", "killed"],
    "oily sheen fades": ["oily sheen", "sheen fades", "corruption.*fades"],
    "oily sheen": ["oily sheen"],
    "arched ceilings": ["arched", "vaulted ceiling"],
    "floating chandelier": ["chandelier"],
    "secret passage": ["secret passage", "hidden passage", "concealed passage"],
    "chandelier": ["chandelier"],
    "before": ["before", "prior to", "pre-fight"],
    "after": ["after", "post-fight"],
    "arcane lockdown": ["magical lockdown", "ward lockdown"],
    "tradeoff": ["drawback", "cost"],
    # Answers often use Unicode apostrophe (’); must_hit token uses ASCII '
    "wizards' college": [
        "wizards\u2019 college",
        "wizards college",
        "headmaster tinkerbright",
    ],
}


def _normalize_text(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _load_gold_questions(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in payload:
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "expected_answer_summary": item.get("expected_answer_summary", ""),
                "core_claims": item.get("core_claims", []),
                "must": item.get("must_hit_tokens", item.get("must", [])),
                "stale": item.get("stale_tokens", item.get("stale", [])),
                "semantic_equivalences": item.get("semantic_equivalences", {}),
                "update_signal_tokens": item.get(
                    "update_signal_tokens", list(UPDATE_SIGNAL_TOKENS)
                ),
                "must_not_cooccur": item.get("must_not_cooccur", {}),
            }
        )
    if not rows:
        raise ValueError(f"No gold questions loaded from {path}")
    return rows


def _extract_tldr_line(answer: str) -> str:
    """Extract the first TL;DR line from an answer, else empty string."""
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("tl;dr:") or lowered.startswith("tldr:"):
            return line
    return ""


def _token_negated_by_cooccurrence(
    *,
    token: str,
    answer_lower: str,
    must_not_cooccur: dict[str, list[str]] | None,
) -> bool:
    if not must_not_cooccur:
        return False
    normalized_token = _normalize_text(token).lower()
    for key, negations in must_not_cooccur.items():
        if _normalize_text(key).lower() != normalized_token:
            continue
        for phrase in negations:
            if _normalize_text(phrase).lower() in answer_lower:
                return True
    return False


def classify_answer(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
    update_signal_tokens: list[str] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    lower_answer = _normalize_text(answer).lower()
    must_hits: list[str] = []
    for token in must_tokens:
        if _normalize_text(token).lower() not in lower_answer:
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_answer,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        must_hits.append(token)
    stale_hits = [
        token for token in stale_tokens if _normalize_text(token).lower() in lower_answer
    ]
    global_stale_hits = [
        pattern
        for pattern in GLOBAL_STALE_PATTERNS
        if _normalize_text(pattern).lower() in lower_answer
    ]
    effective_update_tokens = update_signal_tokens or list(UPDATE_SIGNAL_TOKENS)
    update_signal_hits = [
        token
        for token in effective_update_tokens
        if _normalize_text(token).lower() in lower_answer
    ]

    # Stale should indicate globally stale state, not localized unchanged traits.
    stale_state = bool(global_stale_hits) or (
        bool(stale_hits) and not must_hits and not update_signal_hits
    )
    if has_error:
        verdict = "fail_error"
    elif (
        len(must_hits) >= max(1, len(must_tokens) - 1)
        and not stale_state
    ):
        verdict = "pass_updated"
    elif stale_state:
        verdict = "fail_stale"
    else:
        verdict = "fail_incomplete"

    return verdict, must_hits, stale_hits, global_stale_hits


def _semantic_token_present(
    token: str,
    answer_lower: str,
    question_equivalences: dict[str, list[str]] | None = None,
) -> bool:
    """Check if *token* or any of its semantic equivalents appear in *answer_lower*."""
    normalized_token = _normalize_text(token).lower()
    if normalized_token in answer_lower:
        return True
    for key, values in (question_equivalences or {}).items():
        if _normalize_text(key).lower() != normalized_token:
            continue
        for equiv in values:
            if re.search(_normalize_text(equiv), answer_lower, re.IGNORECASE):
                return True
    for equiv in SEMANTIC_EQUIVALENCES.get(normalized_token, []):
        if re.search(_normalize_text(equiv), answer_lower, re.IGNORECASE):
            return True
    return False


def classify_answer_semantic(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
    question_equivalences: dict[str, list[str]] | None = None,
    update_signal_tokens: list[str] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    """Semantic scoring pass: uses equivalence groups instead of literal matching."""
    lower_answer = _normalize_text(answer).lower()
    must_hits: list[str] = []
    for token in must_tokens:
        if not _semantic_token_present(token, lower_answer, question_equivalences):
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_answer,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        must_hits.append(token)
    stale_hits = [
        token for token in stale_tokens if _normalize_text(token).lower() in lower_answer
    ]
    global_stale_hits = [
        pattern
        for pattern in GLOBAL_STALE_PATTERNS
        if _normalize_text(pattern).lower() in lower_answer
    ]
    effective_update_tokens = update_signal_tokens or list(UPDATE_SIGNAL_TOKENS)
    update_signal_hits = [
        token
        for token in effective_update_tokens
        if _normalize_text(token).lower() in lower_answer
    ]

    stale_state = bool(global_stale_hits) or (
        bool(stale_hits) and not must_hits and not update_signal_hits
    )
    if has_error:
        verdict = "fail_error"
    elif (
        len(must_hits) >= max(1, len(must_tokens) - 1)
        and not stale_state
    ):
        verdict = "pass_updated"
    elif stale_state:
        verdict = "fail_stale"
    else:
        verdict = "fail_incomplete"

    return verdict, must_hits, stale_hits, global_stale_hits


def score_context_support(
    *,
    must_tokens: list[str],
    context: str,
    question_equivalences: dict[str, list[str]] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[list[str], float]:
    """Measure whether required tokens are present in retrieved context.

    This isolates retrieval coverage from synthesis phrasing quality.
    """
    lower_context = _normalize_text(context).lower()
    if not must_tokens:
        return [], 1.0
    hits: list[str] = []
    for token in must_tokens:
        if not _semantic_token_present(token, lower_context, question_equivalences):
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_context,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        hits.append(token)
    return hits, len(hits) / max(1, len(must_tokens))


def classify_failure_surface(
    *,
    semantic_verdict: str,
    context_support_ratio: float,
) -> str:
    if semantic_verdict == "pass_updated":
        return "pass"
    if context_support_ratio < 0.5:
        return "retrieval_gap"
    return "synthesis_gap"


def _projection_search_text(
    projection: dict[str, Any],
    entity_meta_by_id: dict[str, dict[str, Any]],
) -> str:
    parts: list[str] = []
    for entity_id, payload in (projection.get("entities") or {}).items():
        meta = entity_meta_by_id.get(entity_id, {})
        name = str(meta.get("display_name", entity_id)).strip()
        aliases = " ".join(
            str(a).strip() for a in (meta.get("aliases") or []) if str(a).strip()
        )
        attr_blob: list[str] = []
        for attr_name, attr_payload in ((payload or {}).get("attributes") or {}).items():
            value_label = str((attr_payload or {}).get("value_label", "")).strip()
            if value_label:
                attr_blob.append(f"{attr_name} {value_label}")
        if attr_blob:
            parts.append(f"{name} {aliases} {' '.join(attr_blob)}")
    return _normalize_text("\n".join(parts)).lower()


def run() -> dict:
    store = Path("evals/mirathorn_vertical_slice/output/phase_d_store")
    outdir = Path("evals/mirathorn_vertical_slice/output")
    outdir.mkdir(parents=True, exist_ok=True)

    questions = _load_gold_questions(GOLD_QUESTIONS_PATH)

    cli = DungeonBuddyCLI(store_dir=store, verbose=False)
    results: list[dict] = []

    retrieval_mode = os.environ.get(RETRIEVAL_ENV, "1").strip()
    retrieval_flag = "" if retrieval_mode == "1" else " --no-retrieval"
    retrieval_top_k = os.environ.get(RETRIEVAL_TOP_K_ENV, "").strip()
    if retrieval_top_k:
        retrieval_flag += f" --retrieval-top-k {retrieval_top_k}"

    semantic_rerank_mode = os.environ.get(SEMANTIC_RERANK_ENV, "").strip()
    semantic_rerank_flag = ""
    if semantic_rerank_mode == "1":
        semantic_rerank_flag = " --semantic-rerank"
        semantic_top_k = os.environ.get(SEMANTIC_RERANK_TOP_K_ENV, "").strip()
        if semantic_top_k:
            semantic_rerank_flag += f" --semantic-rerank-top-k {semantic_top_k}"
        semantic_weight = os.environ.get(SEMANTIC_RERANK_WEIGHT_ENV, "").strip()
        if semantic_weight:
            semantic_rerank_flag += f" --semantic-rerank-weight {semantic_weight}"
        semantic_model = os.environ.get(SEMANTIC_RERANK_MODEL_ENV, "").strip()
        if semantic_model:
            semantic_rerank_flag += f" --semantic-rerank-model {semantic_model}"

    evidence_first_mode = os.environ.get(EVIDENCE_FIRST_ENV, "").strip()
    evidence_first_flag = ""
    if evidence_first_mode == "1":
        evidence_first_flag = " --evidence-first"
        evidence_top_k = os.environ.get(EVIDENCE_TOP_K_ENV, "").strip()
        if evidence_top_k:
            evidence_first_flag += f" --evidence-top-k {evidence_top_k}"
        evidence_neighbor_window = os.environ.get(EVIDENCE_NEIGHBOR_WINDOW_ENV, "").strip()
        if evidence_neighbor_window:
            evidence_first_flag += f" --evidence-neighbor-window {evidence_neighbor_window}"
        evidence_max_neighbors = os.environ.get(EVIDENCE_MAX_NEIGHBORS_ENV, "").strip()
        if evidence_max_neighbors:
            evidence_first_flag += f" --evidence-max-neighbors {evidence_max_neighbors}"
        evidence_entity_boost = os.environ.get(EVIDENCE_ENTITY_BOOST_ENV, "").strip()
        if evidence_entity_boost:
            evidence_first_flag += f" --evidence-entity-boost {evidence_entity_boost}"
        context_max_entities = os.environ.get(CONTEXT_MAX_ENTITIES_ENV, "").strip()
        if context_max_entities:
            evidence_first_flag += f" --context-max-entities {context_max_entities}"
        context_max_chars = os.environ.get(CONTEXT_MAX_CHARS_ENV, "").strip()
        if context_max_chars:
            evidence_first_flag += f" --context-max-chars {context_max_chars}"

    compare_evidence_first = (
        os.environ.get(COMPARE_EVIDENCE_FIRST_ENV, "").strip() == "1"
        and evidence_first_mode == "1"
    )

    config_flags = f"{retrieval_flag}{semantic_rerank_flag}{evidence_first_flag}".strip()
    if config_flags:
        print(f"Pipeline config: {config_flags}", file=sys.stderr, flush=True)

    trace_rows: list[dict[str, Any]] = []
    stage_loss_counts: dict[str, int] = {
        "store_gap": 0,
        "evidence_gap": 0,
        "retriever_gap": 0,
        "synthesis_gap": 0,
        "hit": 0,
    }
    base_projection = cli.store.project(DEFAULT_CAMPAIGN_ID)
    entities = cli.store.list_entities()
    entity_meta_by_id: dict[str, dict[str, Any]] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        entity_meta_by_id[entity_id] = {
            "display_name": str(entity.get("display_name", entity_id)).strip() or entity_id,
            "aliases": [str(a).strip() for a in (entity.get("aliases") or []) if str(a).strip()],
        }
    full_projection_text = _projection_search_text(base_projection, entity_meta_by_id)
    evidence_by_id = {
        str(unit.get("evidence_id", "")).strip(): str(unit.get("text", "")).strip()
        for unit in cli.store.evidence_units
        if str(unit.get("evidence_id", "")).strip()
    }
    baseline_shadow_rows: list[dict[str, Any]] = []

    for idx, row in enumerate(questions):
        q_label = f"[{idx + 1}/{len(questions)}] {row['id']}"
        print(f"\n{'=' * 60}", file=sys.stderr, flush=True)
        print(f"{q_label}", file=sys.stderr, flush=True)
        print(f"  Q: {row['question']}", file=sys.stderr, flush=True)

        capture = io.StringIO()
        with redirect_stdout(capture):
            cli.handle_line(
                f'ask "{row["question"]}" --campaign {DEFAULT_CAMPAIGN_ID}'
                f' --require-campaign{retrieval_flag}{semantic_rerank_flag}{evidence_first_flag}'
            )
        answer = capture.getvalue().strip()
        has_error = bool(re.search(r"Error:\s*(.*)", answer, re.IGNORECASE))

        ask_meta = getattr(cli, "_last_ask_meta", {}) or {}
        context_text = str(ask_meta.get("context_text", "") or "")

        retrieval_info = ask_meta.get("retrieval", {})
        evidence_stage = retrieval_info.get("evidence_first") or {}

        if retrieval_info.get("enabled"):
            print(
                f"  Retrieval: {retrieval_info.get('post_filter_count', '?')}"
                f"/{retrieval_info.get('pre_filter_count', '?')} entities"
                f" ({retrieval_info.get('duration_ms', '?')}ms)",
                file=sys.stderr, flush=True,
            )
            top5 = retrieval_info.get("top_5", [])
            if top5:
                top_names = ", ".join(f"{eid}({s:.2f})" for eid, s in top5[:5])
                print(f"    top-5: {top_names}", file=sys.stderr, flush=True)
            sem_rerank = retrieval_info.get("semantic_rerank") or {}
            if sem_rerank.get("enabled"):
                print(
                    "    semantic-rerank: "
                    f"top_k={sem_rerank.get('top_k', '?')}"
                    f" weight={sem_rerank.get('weight', '?')}"
                    f" model={sem_rerank.get('model', '?')}"
                    f" ({sem_rerank.get('duration_ms', '?')}ms)",
                    file=sys.stderr,
                    flush=True,
                )
            if evidence_stage.get("enabled"):
                print(
                    "    evidence-first: "
                    f"selected={evidence_stage.get('selected_count', '?')}"
                    f" seeded={evidence_stage.get('seeded_count', '?')}"
                    f" ({evidence_stage.get('duration_ms', '?')}ms)",
                    file=sys.stderr,
                    flush=True,
                )

        ctx_chars = ask_meta.get("context_chars", 0)
        total_ms = ask_meta.get("duration_ms", 0)
        print(
            f"  Context: {ctx_chars:,} chars | Total: {total_ms}ms",
            file=sys.stderr, flush=True,
        )

        answer_preview = answer[:200].replace("\n", " ")
        print(f"  Answer: {answer_preview}...", file=sys.stderr, flush=True)

        trace_rows.append({
            "id": row["id"],
            "question": row["question"],
            "answer": answer,
            "has_error": has_error,
            "retrieval": retrieval_info,
            "context_chars": ctx_chars,
            "duration_ms": total_ms,
        })

        verdict, must_hits, stale_hits, global_stale_hits = classify_answer(
            must_tokens=row["must"],
            stale_tokens=row["stale"],
            answer=answer,
            has_error=has_error,
            update_signal_tokens=row.get("update_signal_tokens"),
            must_not_cooccur=row.get("must_not_cooccur"),
        )

        sem_verdict, sem_must_hits, sem_stale_hits, sem_global_stale = classify_answer_semantic(
            must_tokens=row["must"],
            stale_tokens=row["stale"],
            answer=answer,
            has_error=has_error,
            question_equivalences=row.get("semantic_equivalences"),
            update_signal_tokens=row.get("update_signal_tokens"),
            must_not_cooccur=row.get("must_not_cooccur"),
        )
        context_hits, context_support_ratio = score_context_support(
            must_tokens=row["must"],
            context=context_text,
            question_equivalences=row.get("semantic_equivalences"),
            must_not_cooccur=row.get("must_not_cooccur"),
        )
        failure_surface = classify_failure_surface(
            semantic_verdict=sem_verdict,
            context_support_ratio=context_support_ratio,
        )
        retr_proj = filter_projection(
            base_projection,
            set(retrieval_info.get("selected_entity_ids", [])),
        )
        retr_text = _projection_search_text(retr_proj, entity_meta_by_id)
        evidence_text = ""
        if evidence_stage.get("enabled"):
            selected_evidence_ids = evidence_stage.get("selected_evidence_ids", [])
            evidence_text = _normalize_text(
                " ".join(
                    evidence_by_id.get(str(evidence_id).strip(), "")
                    for evidence_id in selected_evidence_ids
                )
            ).lower()
        else:
            evidence_text = full_projection_text
        answer_text = _normalize_text(answer).lower()
        token_stage: dict[str, str] = {}
        for token in row["must"]:
            if not _semantic_token_present(token, full_projection_text, row.get("semantic_equivalences")):
                token_stage[token] = "store_gap"
            elif not _semantic_token_present(token, evidence_text, row.get("semantic_equivalences")):
                token_stage[token] = "evidence_gap"
            elif not _semantic_token_present(token, retr_text, row.get("semantic_equivalences")):
                token_stage[token] = "retriever_gap"
            elif not _semantic_token_present(token, answer_text, row.get("semantic_equivalences")):
                token_stage[token] = "synthesis_gap"
            else:
                token_stage[token] = "hit"
            stage_loss_counts[token_stage[token]] += 1

        if compare_evidence_first:
            base_capture = io.StringIO()
            with redirect_stdout(base_capture):
                cli.handle_line(
                    f'ask "{row["question"]}" --campaign {DEFAULT_CAMPAIGN_ID}'
                    f" --require-campaign{retrieval_flag}{semantic_rerank_flag}"
                )
            baseline_answer = base_capture.getvalue().strip()
            baseline_meta = getattr(cli, "_last_ask_meta", {}) or {}
            baseline_semantic, *_ = classify_answer_semantic(
                must_tokens=row["must"],
                stale_tokens=row["stale"],
                answer=baseline_answer,
                has_error=False,
                question_equivalences=row.get("semantic_equivalences"),
                update_signal_tokens=row.get("update_signal_tokens"),
                must_not_cooccur=row.get("must_not_cooccur"),
            )
            baseline_shadow_rows.append(
                {
                    "id": row["id"],
                    "context_chars": int(baseline_meta.get("context_chars", 0) or 0),
                    "semantic_verdict": baseline_semantic,
                }
            )

        results.append(
            {
                "id": row["id"],
                "question": row["question"],
                "strict_verdict": verdict,
                "semantic_verdict": sem_verdict,
                "must_hits": must_hits,
                "semantic_must_hits": sem_must_hits,
                "context_must_hits": context_hits,
                "context_support_ratio": round(context_support_ratio, 4),
                "failure_surface": failure_surface,
                "stage_loss_tokens": token_stage,
                "stale_hits": stale_hits,
                "global_stale_hits": global_stale_hits,
                "answer": answer,
            }
        )

    # --- Embedding similarity scoring (opt-in) ---
    embedding_enabled = (
        os.environ.get(EMBEDDING_SCORING_ENV, "").strip() == "1"
    )
    embedding_scores: list[float | None] = [None] * len(results)
    embedding_skipped_reason = ""

    if embedding_enabled:
        try:
            from evals.mirathorn_vertical_slice.embedding_scorer import (
                embedding_available,
                load_embedding_model,
                score_batch,
            )

            if not embedding_available():
                embedding_skipped_reason = (
                    "sentence-transformers not installed; skipping embedding scoring."
                )
                print(f"WARNING: {embedding_skipped_reason}", file=sys.stderr)
            else:
                expected_summaries: list[str] = []
                for row in questions:
                    core_claims = row.get("core_claims")
                    if isinstance(core_claims, list):
                        joined = " ".join(
                            str(claim).strip() for claim in core_claims if str(claim).strip()
                        ).strip()
                        expected_summaries.append(
                            joined or str(row.get("expected_answer_summary", "")).strip()
                        )
                    else:
                        expected_summaries.append(str(row.get("expected_answer_summary", "")).strip())
                answers = [r["answer"] for r in results]
                use_tldr_only = (
                    os.environ.get(EMBEDDING_USE_TLDR_ONLY_ENV, "").strip() == "1"
                )
                tldr_fallback_count = 0
                if use_tldr_only:
                    embedding_answers: list[str] = []
                    for ans in answers:
                        tldr = _extract_tldr_line(ans)
                        if tldr:
                            embedding_answers.append(tldr)
                        else:
                            # Fallback avoids blank embeddings when prompt noncompliance happens.
                            embedding_answers.append(ans)
                            tldr_fallback_count += 1
                else:
                    embedding_answers = answers
                has_all_summaries = all(s.strip() for s in expected_summaries)
                if not has_all_summaries:
                    embedding_skipped_reason = (
                        "Some questions missing expected_answer_summary; "
                        "skipping embedding scoring."
                    )
                    print(f"WARNING: {embedding_skipped_reason}", file=sys.stderr)
                else:
                    print("Loading embedding model...", file=sys.stderr, flush=True)
                    t_load = time.perf_counter()
                    emb_model = load_embedding_model()
                    print(
                        f"INFO: Embedding model loaded in {time.perf_counter() - t_load:.1f}s",
                        file=sys.stderr,
                        flush=True,
                    )
                    print("Scoring answers via embedding similarity...", file=sys.stderr, flush=True)
                    t_score = time.perf_counter()
                    embedding_scores = [
                        float(s)
                        for s in score_batch(
                            emb_model, expected_summaries, embedding_answers
                        )
                    ]
                    print(
                        f"INFO: Embedding scoring completed in "
                        f"{time.perf_counter() - t_score:.1f}s",
                        file=sys.stderr,
                        flush=True,
                    )
                    for i, score in enumerate(embedding_scores):
                        qid = questions[i]["id"]
                        if score is not None:
                            flag = (
                                " (!)"
                                if score < EMBEDDING_WATCH_THRESHOLD
                                else ""
                            )
                            print(
                                f"  [{qid}] embedding similarity: {score:.3f}{flag}",
                                file=sys.stderr,
                                flush=True,
                            )
                        else:
                            print(
                                f"  [{qid}] embedding similarity: (skipped)",
                                file=sys.stderr,
                                flush=True,
                            )
                    if use_tldr_only:
                        print(
                            "INFO: Embedding used TL;DR-only mode "
                            f"(fallback_to_full_answer={tldr_fallback_count})",
                            file=sys.stderr,
                            flush=True,
                        )
        except Exception as exc:
            embedding_skipped_reason = f"Embedding scoring failed: {exc}"
            print(f"WARNING: {embedding_skipped_reason}", file=sys.stderr)
    else:
        embedding_skipped_reason = (
            f"{EMBEDDING_SCORING_ENV} is not set to 1; skipping embedding scoring."
        )
        print(f"INFO: {embedding_skipped_reason}", file=sys.stderr, flush=True)

    def _embedding_tally() -> dict[str, Any]:
        scored = [s for s in embedding_scores if s is not None]
        tldr_mode_enabled = (
            os.environ.get(EMBEDDING_USE_TLDR_ONLY_ENV, "").strip() == "1"
        )
        if not scored:
            return {"enabled": embedding_enabled, "scored_count": 0,
                    "skipped_reason": embedding_skipped_reason,
                    "tldr_only_mode": tldr_mode_enabled}
        scored_sorted = sorted(scored)
        n = len(scored_sorted)
        return {
            "enabled": True,
            "tldr_only_mode": tldr_mode_enabled,
            "scored_count": n,
            "mean": round(sum(scored_sorted) / n, 4),
            "min": round(scored_sorted[0], 4),
            "p25": round(scored_sorted[max(0, n // 4 - 1)], 4),
            "median": round(scored_sorted[n // 2], 4),
            "max": round(scored_sorted[-1], 4),
            "below_watch_threshold": sum(
                1 for s in scored_sorted if s < EMBEDDING_WATCH_THRESHOLD
            ),
            "watch_threshold": EMBEDDING_WATCH_THRESHOLD,
        }

    for i, score in enumerate(embedding_scores):
        results[i]["embedding_similarity"] = score

    claim_verification_enabled = (
        os.environ.get(CLAIM_VERIFICATION_ENV, "").strip() == "1"
    )
    claim_verification_skipped_reason = ""
    claim_results: list[dict[str, Any]] = []
    if claim_verification_enabled:
        try:
            from evals.mirathorn_vertical_slice.claim_verifier import (
                aggregate_accuracy,
                evaluate_answer_accuracy,
            )

            use_llm_extractor = (
                os.environ.get(CLAIM_VERIFICATION_USE_LLM_EXTRACTOR_ENV, "").strip() == "1"
            )
            projection = cli.store.project(DEFAULT_CAMPAIGN_ID)
            entities = cli.store.list_entities()
            for row_result in results:
                claim_eval = evaluate_answer_accuracy(
                    answer=row_result["answer"],
                    projection=projection,
                    entities=entities,
                    use_llm_extractor=use_llm_extractor,
                )
                row_result["claim_verification"] = claim_eval
                claim_results.append(claim_eval)
            claim_summary = aggregate_accuracy(claim_results)
            claim_summary["extractor"] = "llm" if use_llm_extractor else "heuristic"
        except Exception as exc:
            claim_verification_skipped_reason = f"Claim verification failed: {exc}"
            print(f"WARNING: {claim_verification_skipped_reason}", file=sys.stderr, flush=True)
            claim_summary = {
                "enabled": False,
                "skipped_reason": claim_verification_skipped_reason,
            }
    else:
        claim_verification_skipped_reason = (
            f"{CLAIM_VERIFICATION_ENV} is not set to 1; skipping claim verification."
        )
        print(f"INFO: {claim_verification_skipped_reason}", file=sys.stderr, flush=True)
        claim_summary = {
            "enabled": False,
            "skipped_reason": claim_verification_skipped_reason,
        }

    def _tally(key: str) -> dict[str, int]:
        return {
            "pass_updated": sum(1 for r in results if r[key] == "pass_updated"),
            "fail_stale": sum(1 for r in results if r[key] == "fail_stale"),
            "fail_incomplete": sum(1 for r in results if r[key] == "fail_incomplete"),
            "fail_error": sum(1 for r in results if r[key] == "fail_error"),
        }

    def _context_support_summary() -> dict[str, Any]:
        if not results:
            return {
                "avg_support_ratio": 0.0,
                "full_support_count": 0,
                "support_ge_0_75_count": 0,
                "questions": 0,
            }
        ratios = [float(r.get("context_support_ratio", 0.0)) for r in results]
        return {
            "avg_support_ratio": round(sum(ratios) / len(ratios), 4),
            "full_support_count": sum(1 for x in ratios if x >= 0.999),
            "support_ge_0_75_count": sum(1 for x in ratios if x >= 0.75),
            "questions": len(ratios),
        }

    def _failure_surface_summary() -> dict[str, int]:
        keys = ("pass", "retrieval_gap", "synthesis_gap")
        return {k: sum(1 for r in results if r.get("failure_surface") == k) for k in keys}

    summary = {
        "pipeline_config": config_flags or "(defaults)",
        "overall_strict": _tally("strict_verdict"),
        "overall_semantic": _tally("semantic_verdict"),
        "overall_embedding": _embedding_tally(),
        "overall_accuracy": claim_summary,
        "overall_context_support": _context_support_summary(),
        "overall_failure_surface": _failure_surface_summary(),
        "stage_loss_report": {
            "overall_counts": stage_loss_counts,
            "evidence_stage_enabled": bool(evidence_first_mode == "1"),
            "questions": [
                {
                    "id": r["id"],
                    "stage_loss_tokens": r.get("stage_loss_tokens", {}),
                }
                for r in results
            ],
        },
        "results": results,
    }
    if compare_evidence_first and baseline_shadow_rows:
        summary["evidence_first_comparison"] = {
            "enabled": True,
            "baseline_context_chars_avg": round(
                sum(row["context_chars"] for row in baseline_shadow_rows)
                / max(1, len(baseline_shadow_rows))
            ),
            "current_context_chars_avg": round(
                sum(int(tr.get("context_chars", 0) or 0) for tr in trace_rows)
                / max(1, len(trace_rows))
            ),
            "baseline_semantic_pass": sum(
                1 for row in baseline_shadow_rows if row["semantic_verdict"] == "pass_updated"
            ),
            "current_semantic_pass": sum(
                1 for row in results if row.get("semantic_verdict") == "pass_updated"
            ),
            "rows": baseline_shadow_rows,
        }
    elif compare_evidence_first:
        summary["evidence_first_comparison"] = {"enabled": False}

    projection = cli.store.project(DEFAULT_CAMPAIGN_ID)
    scope_cases = [
        {
            "id": "scope_precision_elric_excluded",
            "question": "Catch me up on the council room battle",
            "scope_document_ids": ["doc_battle_with_the_wolf_and_aftermath"],
            "must_include_entities": ["ent_the_wolf", "ent_council_room"],
            "must_exclude_entities": ["ent_commander_elric_vane"],
            "scope_confidence": 1.0,
            "hard_exclude_out_of_scope": True,
        },
        {
            "id": "scope_precision_cold_start_safety",
            "question": "I am starting a fresh world and need anchors",
            "scope_document_ids": ["doc_new_world_bootstrap"],
            "must_include_entities": ["ent_the_wolf"],
            "must_exclude_entities": [],
            "scope_confidence": 0.2,
            "hard_exclude_out_of_scope": True,
        },
        {
            "id": "scope_precision_ambiguous_safety",
            "question": "What happened in that room with Elric?",
            "scope_document_ids": ["doc_unknown_room_reference"],
            "must_include_entities": ["ent_commander_elric_vane"],
            "must_exclude_entities": [],
            "scope_confidence": 0.55,
            "hard_exclude_out_of_scope": True,
        },
    ]

    scope_precision_results: list[dict] = []
    for case in scope_cases:
        scoped_projection = attach_scope_relevance_metadata(
            projection=projection,
            evidence_units=cli.store.evidence_units,
            scope_document_ids=case["scope_document_ids"],
            scope_confidence=float(case["scope_confidence"]),
            min_scope_confidence=0.75,
            min_entity_evidence_count=2,
        )
        context = format_projection_context(
            scoped_projection,
            cli.store.list_entities(),
            question=case["question"],
            evidence_units=cli.store.evidence_units,
            scope_document_ids=case["scope_document_ids"],
            scope_confidence=float(case["scope_confidence"]),
            min_scope_confidence=0.75,
            min_entity_evidence_count=2,
            hard_exclude_out_of_scope=bool(case["hard_exclude_out_of_scope"]),
            unknown_exploration_quota=10,
            include_scope_annotations=True,
        )
        lower_context = context.lower()
        include_pass = all(
            entity_id.replace("ent_", "").replace("_", " ") in lower_context
            for entity_id in case["must_include_entities"]
        )
        exclude_pass = all(
            entity_id.replace("ent_", "").replace("_", " ") not in lower_context
            for entity_id in case["must_exclude_entities"]
        )
        pruning_candidates = (
            scoped_projection.get("scope_relevance", {}).get("pruning_candidates", [])
        )
        scope_precision_results.append(
            {
                "id": case["id"],
                "pass": include_pass and exclude_pass,
                "must_include_entities": case["must_include_entities"],
                "must_exclude_entities": case["must_exclude_entities"],
                "pruning_candidates": pruning_candidates,
            }
        )

    summary["scope_precision_gate"] = {
        "pass": all(item["pass"] for item in scope_precision_results),
        "cases": scope_precision_results,
    }

    def _artifact_write_ok() -> tuple[bool, str]:
        opt = (os.environ.get(WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV) or "").strip()
        if opt != "1":
            return (
                False,
                f"{WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV} is not set to 1; refusing "
                "to write council_room_question_set artifacts (explicit opt-in required).",
            )
        if all(not (row.get("answer") or "").strip() for row in results):
            return (
                False,
                "All answers empty; refusing to overwrite council_room_question_set artifacts.",
            )
        return True, ""

    write_ok, write_reason = _artifact_write_ok()
    if not write_ok:
        summary["artifact_write_skipped"] = True
        summary["artifact_write_reason"] = write_reason
        print(f"WARNING: {write_reason}", file=sys.stderr)
    else:
        summary["artifact_write_skipped"] = False
        summary["artifact_write_reason"] = ""

    if write_ok:
        (outdir / "council_room_question_set.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        if trace_rows:
            (outdir / "council_room_trace.jsonl").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in trace_rows) + "\n",
                encoding="utf-8",
            )

    s = summary["overall_strict"]
    sem = summary["overall_semantic"]
    emb = summary["overall_embedding"]
    lines = ["# Council Room Question Set Results", ""]
    lines.append(f"**Pipeline:** {summary.get('pipeline_config', '(defaults)')}")
    lines.append("")
    lines.append("## Strict scoring")
    lines.append(f"- pass_updated: {s['pass_updated']}")
    lines.append(f"- fail_stale: {s['fail_stale']}")
    lines.append(f"- fail_incomplete: {s['fail_incomplete']}")
    lines.append(f"- fail_error: {s['fail_error']}")
    lines.append("")
    lines.append("## Semantic scoring")
    lines.append(f"- pass_updated: {sem['pass_updated']}")
    lines.append(f"- fail_stale: {sem['fail_stale']}")
    lines.append(f"- fail_incomplete: {sem['fail_incomplete']}")
    lines.append(f"- fail_error: {sem['fail_error']}")
    lines.append("")
    ctx_sum = summary["overall_context_support"]
    fail_surface = summary["overall_failure_surface"]
    lines.append("## Retrieval-context support")
    lines.append(f"- avg_support_ratio: {ctx_sum.get('avg_support_ratio', 0.0)}")
    lines.append(
        f"- full_support_count: {ctx_sum.get('full_support_count', 0)}/{ctx_sum.get('questions', 0)}"
    )
    lines.append(
        f"- support_ge_0_75_count: {ctx_sum.get('support_ge_0_75_count', 0)}/{ctx_sum.get('questions', 0)}"
    )
    lines.append("")
    lines.append("## Failure surface split")
    lines.append(f"- pass: {fail_surface.get('pass', 0)}")
    lines.append(f"- retrieval_gap: {fail_surface.get('retrieval_gap', 0)}")
    lines.append(f"- synthesis_gap: {fail_surface.get('synthesis_gap', 0)}")
    lines.append("")

    lines.append("## Embedding similarity scoring")
    if emb.get("scored_count", 0) > 0:
        lines.append(f"- scored: {emb['scored_count']}")
        lines.append(f"- mean: {emb['mean']}")
        lines.append(f"- min: {emb['min']}")
        lines.append(f"- p25: {emb['p25']}")
        lines.append(f"- median: {emb['median']}")
        lines.append(f"- max: {emb['max']}")
        lines.append(f"- below watch threshold ({emb['watch_threshold']}): {emb['below_watch_threshold']}")
    else:
        lines.append(f"- skipped: {emb.get('skipped_reason', 'not enabled')}")
    lines.append("")
    stage_report = summary["stage_loss_report"]["overall_counts"]
    lines.append("## Stage loss report")
    lines.append(f"- store_gap: {stage_report.get('store_gap', 0)}")
    lines.append(f"- evidence_gap: {stage_report.get('evidence_gap', 0)}")
    lines.append(f"- retriever_gap: {stage_report.get('retriever_gap', 0)}")
    lines.append(f"- synthesis_gap: {stage_report.get('synthesis_gap', 0)}")
    lines.append(f"- hit: {stage_report.get('hit', 0)}")
    lines.append("")
    comparison = summary.get("evidence_first_comparison")
    if isinstance(comparison, dict) and comparison.get("enabled"):
        lines.append("## Evidence-first comparison")
        lines.append(
            f"- baseline_context_chars_avg: {comparison.get('baseline_context_chars_avg', 0):,}"
        )
        lines.append(
            f"- current_context_chars_avg: {comparison.get('current_context_chars_avg', 0):,}"
        )
        lines.append(
            f"- baseline_semantic_pass: {comparison.get('baseline_semantic_pass', 0)}"
        )
        lines.append(
            f"- current_semantic_pass: {comparison.get('current_semantic_pass', 0)}"
        )
        lines.append("")
    lines.append("## Claim verification accuracy")
    if summary["overall_accuracy"].get("enabled"):
        accuracy = summary["overall_accuracy"]
        lines.append(
            f"- total factual claims: {accuracy.get('total_factual_claims', 0)}"
        )
        lines.append(
            f"- hallucination_rate: {accuracy.get('hallucination_rate', 0.0)}"
        )
        lines.append(f"- completeness: {accuracy.get('completeness', 0.0)}")
        lines.append(
            f"- provenance_accuracy: {accuracy.get('provenance_accuracy', 0.0)}"
        )
        lines.append(
            "- status_counts: "
            + ", ".join(
                f"{k}={v}"
                for k, v in (accuracy.get("status_counts", {}) or {}).items()
            )
        )
    else:
        lines.append(
            f"- skipped: {summary['overall_accuracy'].get('skipped_reason', 'not enabled')}"
        )
    lines.append("")

    if not write_ok:
        lines.append("## Artifact write")
        lines.append(f"- skipped: {write_reason}")
        lines.append("")

    trace_by_id: dict[str, dict[str, Any]] = {}
    for tr in trace_rows:
        trace_by_id[tr["id"]] = tr

    for row in results:
        emb_label = ""
        if row.get("embedding_similarity") is not None:
            sim = row["embedding_similarity"]
            flag = " (!)" if sim < EMBEDDING_WATCH_THRESHOLD else ""
            emb_label = f" | emb: {sim:.3f}{flag}"
        lines.append(
            f"## {row['id']} — strict: {row['strict_verdict']}"
            f" | semantic: {row['semantic_verdict']}{emb_label}"
        )
        lines.append(f"- question: {row['question']}")

        tr = trace_by_id.get(row["id"], {})
        ret = tr.get("retrieval", {})
        if ret.get("enabled"):
            lines.append(
                f"- retrieval: {ret.get('post_filter_count', '?')}"
                f"/{ret.get('pre_filter_count', '?')} entities"
                f" ({ret.get('duration_ms', '?')}ms)"
            )
        if tr.get("context_chars"):
            lines.append(f"- context_chars: {tr['context_chars']:,}")
        if tr.get("duration_ms"):
            lines.append(f"- total_ms: {tr['duration_ms']}")

        lines.append(
            "- strict must_hits: "
            + (", ".join(row["must_hits"]) if row["must_hits"] else "(none)")
        )
        lines.append(
            "- semantic must_hits: "
            + (", ".join(row["semantic_must_hits"]) if row["semantic_must_hits"] else "(none)")
        )
        lines.append(
            "- context must_hits: "
            + (", ".join(row["context_must_hits"]) if row["context_must_hits"] else "(none)")
        )
        lines.append(
            f"- context_support_ratio: {row.get('context_support_ratio', 0.0)}"
        )
        lines.append(f"- failure_surface: {row.get('failure_surface', 'unknown')}")
        lines.append(
            "- stage_loss_tokens: "
            + json.dumps(row.get("stage_loss_tokens", {}), ensure_ascii=False, sort_keys=True)
        )
        lines.append(
            "- stale_hits: "
            + (", ".join(row["stale_hits"]) if row["stale_hits"] else "(none)")
        )
        claim_eval = row.get("claim_verification")
        if isinstance(claim_eval, dict):
            lines.append(
                f"- claim_verification: total={claim_eval.get('total_factual_claims', 0)}, "
                f"hallucination_rate={claim_eval.get('hallucination_rate', 0.0)}, "
                f"completeness={claim_eval.get('completeness', 0.0)}"
            )
        lines.append("")
        lines.append("### answer")
        lines.append(row["answer"])
        lines.append("")

    if write_ok:
        (outdir / "council_room_question_set.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    return summary


if __name__ == "__main__":
    out = run()
    print("=== STRICT ===", file=sys.stderr, flush=True)
    print(json.dumps(out["overall_strict"], indent=2), file=sys.stderr, flush=True)
    print("=== SEMANTIC ===", file=sys.stderr, flush=True)
    print(json.dumps(out["overall_semantic"], indent=2), file=sys.stderr, flush=True)
    print("=== EMBEDDING ===", file=sys.stderr, flush=True)
    print(json.dumps(out["overall_embedding"], indent=2), file=sys.stderr, flush=True)
