#!/usr/bin/env python3
"""Hermes small-slice runner for Of Conks Grotesque Tree gold.

Modes:
  score-file   Score a recorded trial JSON against gold (no LLM).
  live         Run Hermes graph agent turns (≥1 trial) and score.
  authoring-dogfood
               One authoring Ask with canvas work object; score canvas proposal.

Examples:
  uv run python evals/hermes_small_slice/run_small_slice.py score-file \\
    --trial evals/hermes_small_slice/artifacts/baseline_observed_vague_talk.json

  uv run python evals/hermes_small_slice/run_small_slice.py live \\
    --question-ids vague_talk,prep_gm_facing,authoring_gm_note --trials 3
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = REPO_ROOT / "src"
for _path in (str(REPO_ROOT), str(_SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from evals.hermes_small_slice.score import (  # noqa: E402
    aggregate_question_trials,
    score_trial,
)

GOLD_DEFAULT = (
    REPO_ROOT / "evals/hermes_small_slice/gold/of_conks_grotesque_tree_v1.json"
)
ARTIFACTS = REPO_ROOT / "evals/hermes_small_slice/artifacts"


def _utc_stamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_gold(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_of_conks_envelope(*, question: str, root: Path) -> dict[str, Any]:
    from graph_memory.world_supergraph.storage import load_current_world_graph

    head, revision, store = load_current_world_graph(root, "of-conks-cons")
    revision_id = (
        getattr(store, "revision_id", None)
        or getattr(revision, "revision_id", None)
        or head.head_revision_id
    )
    store_nodes = getattr(store, "nodes", {}) or {}
    if not isinstance(store_nodes, dict):
        store_nodes = {}
    preferred = [
        "threat:grotesque-tree",
        "location:grotesque-tree-site",
        "location:jove-home",
        "location:hempholm",
        "item:metal-leaves",
    ]
    matched = [nid for nid in preferred if nid in store_nodes]
    if not matched:
        matched = list(store_nodes)[:5]
    return {
        "schema": "dmb_agent_world_graph_query_context_v1",
        "status": "ready",
        "world_id": "of-conks-cons",
        "campaign_id": "of-conks-cons",
        "revision_id": revision_id,
        "head_revision_id": head.head_revision_id,
        "is_head": True,
        "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        "admissibility": "gm",
        "query_text": question,
        "matched_node_ids": matched,
        "nodes": [
            {
                "node_id": nid,
                "label": getattr(store_nodes[nid], "label", None)
                if not isinstance(store_nodes[nid], dict)
                else store_nodes[nid].get("label", nid),
            }
            for nid in matched
        ],
        "relationships": [],
        "attributes": [],
        "projection_truncated": False,
        "diagnostics": [],
        "warning_codes": [],
        "trust_boundary": {
            "graph_role": "structured_campaign_memory_and_navigation",
            "citation_authority": "corpus_source_evidence",
            "graph_citations_permitted": False,
        },
    }


def _project_live_result(response: MappingLike) -> dict[str, Any]:
    """Normalize product envelope into score_trial inputs."""
    answer = str(
        response.get("answer")
        or response.get("final_response")
        or response.get("text")
        or ""
    )
    tool_events = response.get("tool_events") or response.get("toolEvents") or []
    if not tool_events:
        trace = response.get("agent_trace") or response.get("agentTrace") or {}
        if isinstance(trace, dict):
            tool_events = trace.get("tool_events") or trace.get("toolEvents") or []
    acceptance = {}
    grounding = response.get("grounding") or {}
    if isinstance(grounding, dict):
        acceptance = {
            "accepted_claim_ids": grounding.get("accepted_claim_ids")
            or grounding.get("acceptedClaimIds")
            or [],
            "source_citations_opened": grounding.get("source_citations_opened")
            or grounding.get("source_anchor_count")
            or 0,
            "source_citations": response.get("source_citations")
            or response.get("citations")
            or [],
        }
    support = response.get("support") or {}
    if isinstance(support, dict):
        if not acceptance.get("accepted_claim_ids"):
            acceptance["accepted_claim_ids"] = (
                support.get("accepted_claim_ids") or support.get("acceptedClaimIds") or []
            )
    return {
        "answer": answer,
        "tool_events": tool_events if isinstance(tool_events, list) else [],
        "result": {
            "acceptance": acceptance,
            "mutations": response.get("mutations") or [],
            "raw": {
                "status": response.get("status"),
                "mode": response.get("mode"),
                "grounding": grounding,
                "diagnostics": response.get("diagnostics"),
            },
        },
    }


MappingLike = dict[str, Any]


def run_live_turn(
    *,
    question: str,
    root: Path,
    canvas_work_object: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from apps.live_control_server.services.hermes_graph_query import run_hermes_graph_query
    from bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    envelope = build_of_conks_envelope(question=question, root=root)
    # Live packet identity remains longmont-c2 session 22 for continuity/store;
    # graph lens is of-conks-cons via envelope.
    packet = {"campaign_id": "longmont-c2", "session": 22}
    response = run_hermes_graph_query(
        text=question,
        packet=packet,
        graph_envelope=envelope,
        agent_thread_id=f"small-slice-{uuid.uuid4().hex[:12]}",
        turn_id=f"turn-{uuid.uuid4().hex[:8]}",
        root=root,
        corpus_root=REPO_ROOT,
        canvas_work_object=canvas_work_object,
    )
    projected = _project_live_result(response)
    return {
        "question": question,
        "envelope_revision_id": envelope.get("revision_id"),
        "matched_node_ids": envelope.get("matched_node_ids"),
        **projected,
        "product_response": response,
    }


def score_recorded(
    *,
    gold: dict[str, Any],
    question: dict[str, Any],
    trial: dict[str, Any],
) -> dict[str, Any]:
    return score_trial(
        gold=gold,
        question=question,
        answer=str(trial.get("answer") or ""),
        tool_events=trial.get("tool_events") or [],
        result=trial.get("result") or trial,
    )


def cmd_score_file(args: argparse.Namespace) -> int:
    gold = load_gold(args.gold)
    trial = json.loads(Path(args.trial).read_text(encoding="utf-8"))
    qid = args.question_id or trial.get("question_id")
    question = next((q for q in gold["questions"] if q["id"] == qid), None)
    if question is None:
        raise SystemExit(f"unknown question_id {qid!r}")
    scored = score_recorded(gold=gold, question=question, trial=trial)
    out = {
        "scored_at": _utc_stamp(),
        "question_id": qid,
        "score": scored,
        "trial_path": str(args.trial),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    if args.write:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        path = ARTIFACTS / f"score_{qid}_{Path(args.trial).stem}.json"
        path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {path}", file=sys.stderr)
    return 0 if scored.get("structural_pass") else 1


def cmd_live(args: argparse.Namespace) -> int:
    gold = load_gold(args.gold)
    root = (args.root or (REPO_ROOT / "out")).resolve()
    wanted = (
        [s.strip() for s in args.question_ids.split(",") if s.strip()]
        if args.question_ids
        else [q["id"] for q in gold["questions"] if q["id"] != "identity_only_control"]
    )
    questions = [q for q in gold["questions"] if q["id"] in wanted]
    trials_n = max(1, int(args.trials))
    run_id = args.run_id or f"live_{_utc_stamp().replace(':', '')}"
    run_dir = ARTIFACTS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schema": "dmb_hermes_small_slice_run_v1",
        "run_id": run_id,
        "started_at": _utc_stamp(),
        "gold_id": gold.get("id"),
        "revision_hint": None,
        "questions": {},
    }
    all_ok = True
    for question in questions:
        q_scores: list[dict[str, Any]] = []
        for trial_i in range(1, trials_n + 1):
            canvas = None
            if question.get("expect_canvas_proposal"):
                canvas = {
                    "documentId": args.document_id or "doc:small-slice-dogfood",
                    "surfaceId": "plan",
                    "expectedContentSha256": args.content_sha256,
                }
            print(
                f"[{question['id']}] trial {trial_i}/{trials_n} …",
                file=sys.stderr,
                flush=True,
            )
            try:
                trial = run_live_turn(
                    question=str(question["prompt"]),
                    root=root,
                    canvas_work_object=canvas,
                )
            except Exception as exc:  # noqa: BLE001 — capture for artifact
                trial = {
                    "question": question["prompt"],
                    "answer": "",
                    "tool_events": [],
                    "result": {"acceptance": {}, "mutations": [], "error": str(exc)},
                    "error": str(exc),
                }
            trial["question_id"] = question["id"]
            trial["trial_index"] = trial_i
            scored = score_recorded(gold=gold, question=question, trial=trial)
            trial["score"] = scored
            q_scores.append(scored)
            trial_path = run_dir / f"{question['id']}_t{trial_i}.json"
            # Drop huge product_response optionally
            to_write = dict(trial)
            if not args.keep_full_response:
                to_write.pop("product_response", None)
            trial_path.write_text(
                json.dumps(to_write, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
            if report["revision_hint"] is None:
                report["revision_hint"] = trial.get("envelope_revision_id")
            print(
                f"  structural={scored['structural_pass']} "
                f"source_reads={scored['source_reads']} "
                f"buckets={scored['required_bucket_pass']} "
                f"-> {trial_path.name}",
                file=sys.stderr,
            )
        agg = aggregate_question_trials(q_scores, threshold_pass=2 if trials_n >= 3 else 1)
        report["questions"][question["id"]] = {
            "aggregate": agg,
            "human_rubric": {
                "expand_ready": None,
                "notes": "Fill after reviewing frontstage prose in trial artifacts.",
            },
        }
        if not agg["structural_ok"]:
            all_ok = False

    report["completed_at"] = _utc_stamp()
    report["structural_ok"] = all_ok
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"wrote {summary_path}", file=sys.stderr)
    return 0 if all_ok else 1


def cmd_authoring_dogfood(args: argparse.Namespace) -> int:
    """Single authoring trial focused on propose_canvas_block + gate hygiene."""
    args.question_ids = "authoring_gm_note"
    args.trials = 1
    args.run_id = args.run_id or f"authoring_dogfood_{_utc_stamp().replace(':', '')}"
    return cmd_live(args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold",
        type=Path,
        default=GOLD_DEFAULT,
        help="Gold packet path",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_score = sub.add_parser("score-file", help="Score a recorded trial JSON")
    p_score.add_argument("--trial", type=Path, required=True)
    p_score.add_argument("--question-id", default=None)
    p_score.add_argument("--write", action="store_true")
    p_score.set_defaults(func=cmd_score_file)

    p_live = sub.add_parser("live", help="Run live Hermes turns and score")
    p_live.add_argument("--root", type=Path, default=None)
    p_live.add_argument("--question-ids", default=None)
    p_live.add_argument("--trials", type=int, default=3)
    p_live.add_argument("--run-id", default=None)
    p_live.add_argument("--document-id", default=None)
    p_live.add_argument("--content-sha256", default=None)
    p_live.add_argument("--keep-full-response", action="store_true")
    p_live.set_defaults(func=cmd_live)

    p_auth = sub.add_parser(
        "authoring-dogfood",
        help="One authoring Ask with canvas work object",
    )
    p_auth.add_argument("--root", type=Path, default=None)
    p_auth.add_argument("--run-id", default=None)
    p_auth.add_argument("--document-id", default=None)
    p_auth.add_argument("--content-sha256", default=None)
    p_auth.add_argument("--keep-full-response", action="store_true")
    p_auth.set_defaults(func=cmd_authoring_dogfood)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
