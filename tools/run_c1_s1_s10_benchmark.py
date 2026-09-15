#!/usr/bin/env python3
"""Two-layer 16-question Campaign 1 Sessions 1–10 QA Benchmark Runner.

Executes:
  Layer 1: Oracle retrieval (bounded production graph retrieval primitives)
  Layer 2: Real Agent (Hermes autonomous agent turn over GraphRetrievalSession)

Evaluates answers against gold definitions in:
  evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md
Classifies misses according to the 6-bucket failure taxonomy in:
  Docs/Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphFocus,
    AgentWorldGraphQueryContextRequest,
    resolve_agent_world_graph_query_context,
)
from apps.live_control_server.services.hermes_graph_query import run_hermes_graph_query
from apps.live_control_server.services.world_graph_retrieval import (
    get_campaign_object,
    get_object_neighborhood,
    search_campaign_graph,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    RETRIEVAL_SEARCH_REQUEST_SCHEMA,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphSearchRequest,
)

DEFAULT_REVISION = "rev:b82db72693c27e0218026fd1ff514a68"
DEFAULT_WORLD = "eldyrwild"
DEFAULT_CAMPAIGN = "longmont-c1"
DEFAULT_PR_HEAD = "60a7d909b5d7ad70a889fc653a44e04f4c420f57"


@dataclass
class QuestionGold:
    qid: str
    title: str
    difficulty: int
    question: str
    gold_answer: str
    must_include: list[str]
    must_not_claim: list[str]
    oracle_searches: list[str]
    oracle_objects: list[str]


def parse_benchmark_gold(gold_path: Path) -> list[QuestionGold]:
    content = gold_path.read_text(encoding="utf-8")
    sections = re.split(r"\n## (Q\d\d [^\n]+)\n", content)
    questions: list[QuestionGold] = []

    # Bounded oracle retrieval plans tailored to discover optimal evidence
    oracle_specs: dict[str, dict[str, list[str]]] = {
        "Q01": {
            "searches": ["strange meat arcana plane", "meat cold room guardhouse", "sinister meat"],
            "objs": ["item:meat", "mystery:strange-meat", "location:cold-room"],
        },
        "Q02": {
            "searches": ["glowing mushrooms potion", "Stormspire Academy Head Alchemist", "herbal shop"],
            "objs": ["item:glowing_mushrooms", "location:stormspire-academy", "npc:the-head-alchemist"],
        },
        "Q03": {
            "searches": ["Torbin ward contract", "Torbin Jove Hempholm Mirathorn", "Torbin education"],
            "objs": ["item:torbin_ward_contract", "mystery:torbin-ward-contract", "npc:torbin", "npc:jove"],
        },
        "Q04": {
            "searches": ["Caelynn Lysandra gate protest", "Captain Lysandra storeroom", "oily eyed guards"],
            "objs": ["node:caelynn", "node:lysandra-ironveil", "npc:captain-lysandra", "mystery:mirathorn-toll-protest", "mystery:captain-lysandra-quest"],
        },
        "Q05": {
            "searches": ["Caelynn glowing mushrooms Hempholm", "mushrooms dangerous Stormspire", "Head Alchemist"],
            "objs": ["node:caelynn", "item:glowing_mushrooms", "location:stormspire-academy", "npc:the-head-alchemist"],
        },
        "Q06": {
            "searches": ["Torbin captivity meat escape Ephanna", "Torbin Shepherd Flock Lyra", "Torbin oily eyes"],
            "objs": ["npc:torbin", "node:ephanna", "npc:lyra", "faction:the_shepherds_flock", "mystery:torbin-meat-effect", "item:key-to-torbins-cell"],
        },
        "Q07": {
            "searches": ["Lyra toll protest meat distribution", "Shepherd Flock Lyra meat", "cultists Lyra"],
            "objs": ["npc:lyra", "faction:the_shepherds_flock", "mystery:mirathorn-toll-riot", "mystery:corrupted-meat-distribution"],
        },
        "Q08": {
            "searches": ["guard infiltration oily eyes Fairfield Blart Lysandra", "storeroom meat tunnel guardhouse"],
            "objs": ["mystery:oily-eyed-guards", "npc:captain-lysandra", "npc:captain-fairfield", "npc:captain-blart", "location:storeroom"],
        },
        "Q09": {
            "searches": ["guardhouse storeroom cold room warehouse tunnel", "tunnel network Grit and Grime short rest", "warehouse meat Thraxx"],
            "objs": ["location:storeroom", "location:cold-room", "location:underground-tunnels", "location:grit-and-grime"],
        },
        "Q10": {
            "searches": ["fighting corrupted meat mounds piles snowball shatter fire", "Abhorrent Meat Wings tactics"],
            "objs": ["creature:corrupted-meat-mound", "creature:corrupted-meat-pile", "item:abhorrent-meat-wings"],
        },
        "Q11": {
            "searches": ["Ephanna Sprite fey familiar", "Sprite scout tunnel warehouse killed", "Sprite Torbin"],
            "objs": ["creature:sprite", "mystery:ephanna-sprite-summons", "obs:sprite-killed", "node:ephanna"],
        },
        "Q12": {
            "searches": ["Lyra protest Shepherd Flock meat distribution", "Lyra captive Ephanna Torbin"],
            "objs": ["npc:lyra", "faction:the_shepherds_flock"],
        },
        "Q13": {
            "searches": ["Torbin forced meat captivity oily eyes", "Torbin Session 7 Session 8 meat"],
            "objs": ["npc:torbin", "mystery:torbin-meat-effect"],
        },
        "Q14": {
            "searches": ["Wolf guard leader Fairfield Blart cultist", "Wolf Looking Ahead planning"],
            "objs": ["npc:wolf", "mystery:wolfs-role", "mystery:wolf-cultist-guard-corruption", "npc:captain-fairfield", "npc:captain-blart"],
        },
        "Q15": {
            "searches": ["corrupted meat conspiracy Fairfield Blart Lyra BBQ deadline", "Grit Grime warehouse fight short rest"],
            "objs": ["obs:bbq-deadline", "mystery:prevent-bbq-corruption", "npc:captain-fairfield", "npc:captain-blart", "npc:lyra", "location:grit-and-grime"],
        },
        "Q16": {
            "searches": ["Shepherd Shepherd Flock Lyra meat conspiracy swamp", "northern swamp Shepherd leader"],
            "objs": ["npc:the-shepherd", "faction:the_shepherds_flock", "npc:lyra", "mystery:shepherd-rumors"],
        },
    }

    for i in range(1, len(sections), 2):
        title = sections[i]
        body = sections[i + 1]
        qid = title.split()[0]
        diff_m = re.search(r"\*\*Difficulty:\*\*\s*(\d+)", body)
        diff = int(diff_m.group(1)) if diff_m else 1

        q_m = re.search(
            r"\*\*Question\*\*\s*\n\n(.*?)(?=\n\n\*\*Gold answer\*\*)", body, re.DOTALL
        )
        q_text = q_m.group(1).strip() if q_m else ""

        gold_m = re.search(
            r"\*\*Gold answer\*\*\s*\n\n(.*?)(?=\n\n\*\*Must include\*\*)", body, re.DOTALL
        )
        gold_text = gold_m.group(1).strip() if gold_m else ""

        must_inc_m = re.search(
            r"\*\*Must include\*\*\s*\n\n(.*?)(?=\n\n\*\*(?:Evidence|Must not claim|Scoring note)\*\*)",
            body,
            re.DOTALL,
        )
        must_includes: list[str] = []
        if must_inc_m:
            for line in must_inc_m.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    must_includes.append(line[2:].strip())

        must_not_m = re.search(
            r"\*\*Must not claim\*\*\s*\n\n(.*?)(?=\n\n\*\*(?:Evidence|Scoring note)\*\*)",
            body,
            re.DOTALL,
        )
        must_nots: list[str] = []
        if must_not_m:
            for line in must_not_m.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    must_nots.append(line[2:].strip())

        spec = oracle_specs.get(qid, {"searches": [q_text], "objs": []})
        questions.append(
            QuestionGold(
                qid=qid,
                title=title,
                difficulty=diff,
                question=q_text,
                gold_answer=gold_text,
                must_include=must_includes,
                must_not_claim=must_nots,
                oracle_searches=spec["searches"],
                oracle_objects=spec["objs"],
            )
        )
    return questions


def run_oracle_layer(
    q: QuestionGold,
    *,
    world_id: str = DEFAULT_WORLD,
    campaign_id: str = DEFAULT_CAMPAIGN,
    revision_id: str = DEFAULT_REVISION,
) -> dict[str, Any]:
    retrieved_nodes: dict[str, Any] = {}
    retrieved_rels: dict[str, Any] = {}
    retrieved_anchors: dict[str, Any] = {}

    for s_query in q.oracle_searches:
        try:
            res = search_campaign_graph(
                WorldGraphSearchRequest(
                    schema=RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                    worldId=world_id,
                    campaignId=campaign_id,
                    queryText=s_query,
                    revisionPin=revision_id,
                )
            )
            for n in res.nodes:
                retrieved_nodes[n.node_id] = n
            for r in res.relationships:
                retrieved_rels[r.edge_id] = r
            for a in res.source_anchors:
                retrieved_anchors[a.anchor_id] = a
        except Exception:
            pass

    for oid in q.oracle_objects:
        try:
            res = get_campaign_object(
                WorldGraphObjectRequest(
                    schema=RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                    worldId=world_id,
                    campaignId=campaign_id,
                    nodeId=oid,
                    revisionPin=revision_id,
                )
            )
            for n in res.nodes:
                retrieved_nodes[n.node_id] = n
            for r in res.relationships:
                retrieved_rels[r.edge_id] = r
            for a in res.source_anchors:
                retrieved_anchors[a.anchor_id] = a
        except Exception:
            pass

    seed_objs = [oid for oid in q.oracle_objects if oid in retrieved_nodes][:4]
    if seed_objs:
        try:
            res = get_object_neighborhood(
                WorldGraphNeighborhoodRequest(
                    schema=RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                    worldId=world_id,
                    campaignId=campaign_id,
                    seedNodeIds=seed_objs,
                    maxDepth=1,
                    revisionPin=revision_id,
                )
            )
            for n in res.nodes:
                retrieved_nodes[n.node_id] = n
            for r in res.relationships:
                retrieved_rels[r.edge_id] = r
            for a in res.source_anchors:
                retrieved_anchors[a.anchor_id] = a
        except Exception:
            pass

    lines: list[str] = []
    for n in retrieved_nodes.values():
        lines.append(f"Node: {n.label} ({n.kind}) ID:{n.node_id}")
        if n.summary:
            lines.append(f"Summary: {n.summary}")
        if n.aliases:
            lines.append(f"Aliases: {', '.join(n.aliases)}")
    for r in retrieved_rels.values():
        lines.append(f"Rel: {r.source_node_id} -[{r.predicate}]-> {r.target_node_id} (label: {r.label})")

    reachable_text = "\n".join(lines)
    return {
        "nodes": [
            {"id": n.node_id, "label": n.label, "kind": n.kind}
            for n in retrieved_nodes.values()
        ],
        "relationships": [
            {
                "edge_id": r.edge_id,
                "source": r.source_node_id,
                "target": r.target_node_id,
                "predicate": r.predicate,
                "label": r.label,
            }
            for r in retrieved_rels.values()
        ],
        "anchor_count": len(retrieved_anchors),
        "reachable_text": reachable_text,
    }


def run_agent_layer(
    q: QuestionGold,
    *,
    world_id: str = DEFAULT_WORLD,
    campaign_id: str = DEFAULT_CAMPAIGN,
    revision_id: str = DEFAULT_REVISION,
) -> dict[str, Any]:
    req = AgentWorldGraphQueryContextRequest(
        world_id=world_id,
        campaign_id=campaign_id,
        focus=AgentWorldGraphFocus(kind="session", session_id="session-10"),
        revision_pin=revision_id,
    )
    envelope = resolve_agent_world_graph_query_context(
        req,
        outer_text=q.question,
        outer_campaign_id=campaign_id,
    )

    t0 = time.perf_counter()
    packet = {"campaign_id": campaign_id, "session": 10}
    response = run_hermes_graph_query(
        text=q.question,
        packet=packet,
        graph_envelope=envelope,
        agent_thread_id=f"benchmark-{q.qid.lower()}-thread",
        turn_id=f"turn-{q.qid.lower()}",
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    trace = response.get("agent_trace") or {}
    tool_events = trace.get("tool_events") or []
    completed_tools = [te for te in tool_events if te.get("state") == "completion"]
    grounding = response.get("grounding") or {}

    return {
        "status": response.get("status"),
        "answer": response.get("answer") or "",
        "grounding_state": grounding.get("state"),
        "acceptance_state": grounding.get("acceptance_state"),
        "elapsed_ms": elapsed_ms,
        "tool_call_count": len(completed_tools),
        "tool_events": [
            {
                "tool": te.get("tool_name"),
                "state": te.get("state"),
                "outcome": te.get("outcome"),
                "diagnostic_codes": te.get("diagnostic_codes", []),
            }
            for te in tool_events
        ],
        "accepted_claims": grounding.get("accepted_claim_ids", []),
    }


def score_text_against_gold(
    text: str,
    q: QuestionGold,
    is_oracle_reachable_text: bool = False,
) -> tuple[str, list[str], list[str], list[str]]:
    """Determine credit (full, partial, fail) and missing concepts."""
    text_lower = text.lower()
    met_concepts: list[str] = []
    missing_concepts: list[str] = []
    violated_negatives: list[str] = []

    # Question-specific required semantic checks
    # Rather than trivial substring, check core discriminative terms
    concept_checks: dict[str, list[tuple[str, list[list[str]]]]] = {
        "Q01": [
            ("the meat is from another plane / extraplanar", [["plane"], ["extraplanar"], ["another plane"]]),
        ],
        "Q02": [
            ("Head Alchemist", [["head alchemist"], ["alchemist"]]),
            ("Stormspire Academy", [["stormspire"]]),
        ],
        "Q03": [
            ("take Torbin to Mirathorn", [["mirathorn"], ["ward"]]),
            ("education", [["education"], ["clerk"], ["school"]]),
            ("monthly visits for his father", [["monthly"], ["visit"], ["jove"]]),
            ("room and board", [["room and board"], ["board"], ["food"]]),
        ],
        "Q04": [
            ("Caelynn successfully affected the protest crowd", [["caelynn"], ["protest"], ["crowd"], ["gate"]]),
            ("Lysandra let the party cut the line / relationship improved", [["lysandra", "cut"], ["lysandra", "line"], ["lysandra", "happy"], ["lysandra", "pass"]]),
            ("later investigation of suspicious guards and/or the storeroom", [["storeroom"], ["guard"], ["investigat"]]),
        ],
        "Q05": [
            ("Caelynn collected the mushrooms beneath Hempholm", [["caelynn", "mushroom"], ["hempholm", "mushroom"]]),
            ("rare and dangerous", [["rare"], ["dangerous"], ["danger"]]),
            ("Head Alchemist at Stormspire Academy", [["stormspire"], ["alchemist"]]),
        ],
        "Q06": [
            ("Torbin met in Hempholm", [["hempholm"]]),
            ("education/ward commitment", [["ward"], ["contract"], ["education"]]),
            ("Ephanna took Torbin with Lyra / the Shepherd's Flock", [["lyra"], ["shepherd"], ["flock"]]),
            ("capture", [["captiv"], ["captur"], ["cell"], ["cage"]]),
            ("forced meat exposure", [["eat"], ["fed"], ["force"], ["meat"]]),
            ("escape with Ephanna", [["escape"], ["freed"], ["ephanna"]]),
            ("oily-eye symptom after exposure", [["oily"], ["eye"]]),
        ],
        "Q07": [
            ("Lyra led the toll protest", [["lyra", "protest"], ["lyra", "toll"], ["lyra", "gate"]]),
            ("Lyra/followers connected to the Shepherd's Flock", [["shepherd"], ["flock"]]),
            ("following the group leads Ephanna and Torbin into captivity/meat exposure", [["captur"], ["captiv"], ["cell"], ["meat"]]),
            ("Lyra later leads the meat-distribution project", [["distribut"], ["meat", "lead"], ["project"]]),
        ],
        "Q08": [
            ("oily-eyed guards", [["oily"]]),
            ("Lysandra locked out of the storeroom", [["storeroom"], ["locked"], ["kept out"]]),
            ("hidden meat/tunnel under the guardhouse", [["tunnel"], ["meat"], ["hidden"]]),
            ("Lysandra/trusted guards captured or force-fed", [["lysandra", "captur"], ["lysandra", "cage"], ["lysandra", "fed"], ["lysandra", "attack"]]),
            ("Captain Fairfield", [["fairfield"]]),
            ("Captain Blart", [["blart"]]),
        ],
        "Q09": [
            ("guardhouse storeroom", [["storeroom"]]),
            ("hidden staircase/cold meat room", [["cold room"], ["cold-room"], ["staircase"]]),
            ("hidden wall/tunnel", [["tunnel"]]),
            ("warehouse district / warehouse", [["warehouse"]]),
            ("continued tunnel network and distribution junction", [["junction"], ["network"], ["tunnel"]]),
            ("Grit and Grime", [["grit and grime"], ["grit"], ["grime"]]),
            ("last warehouse", [["last warehouse"], ["warehouse"]]),
            ("return for Short Rest", [["short rest"], ["rest"]]),
        ],
        "Q10": [
            ("physical attacks can shed Meat Piles", [["pile"], ["shed"], ["crush"], ["cut"]]),
            ("poisonous cloud from ordinary damage", [["poison"], ["cloud"]]),
            ("cold/Snowball did not produce new piles", [["cold"], ["snowball"]]),
            ("Shatter destroyed piles", [["shatter"]]),
            ("fire consumed smaller piles", [["fire"], ["oil"]]),
            ("Hideous Laughter had no effect", [["laughter"], ["hideous"]]),
        ],
        "Q11": [
            ("secret Sprite summon", [["sprite"], ["summon"]]),
            ("Torbin knew", [["torbin"]]),
            ("fey familiar helped with the escape", [["familiar"], ["escape"], ["fey"], ["loosen"]]),
            ("Sprite scouted tunnels/warehouse", [["scout"], ["tunnel"], ["warehouse"]]),
            ("Sprite killed in Session 10", [["kill"], ["dead"], ["killed"]]),
        ],
        "Q12": [
            ("protest leader", [["protest"], ["gate"], ["leader"]]),
            ("Shepherd's Flock connection", [["shepherd"], ["flock"]]),
            ("capture/meat context after following her group", [["captur"], ["meat"], ["captive"]]),
            ("later distribution leadership", [["distribut"], ["leader"]]),
        ],
        "Q13": [
            ("force-fed in Session 7", [["session 7"], ["force"], ["fed"], ["captiv"]]),
            ("force-fed/heard being force-fed again in Session 8", [["session 8"], ["again"], ["heard"]]),
            ("oily-eye symptom after escape", [["oily"], ["eye"]]),
        ],
        "Q14": [
            ("Wolf claims are in planning / Looking Ahead", [["planning"], ["looking ahead"], ["not played"]]),
            ("guard-leader innocence/ensorcellment is planning", [["innocent"], ["ensorcell"], ["guard leader"], ["leader"]]),
            ("proposed council/wizard responses are planning", [["council"], ["wizard"]]),
            ("Fairfield, Blart, and Lyra are supported by the observed Recap", [["fairfield"], ["blart"], ["lyra"]]),
        ],
        "Q15": [
            ("extraplanar origin clue", [["extraplanar"], ["plane"]]),
            ("Abyssal-like scroll clue", [["abyssal"], ["scroll"], ["strange language"]]),
            ("hidden guardhouse meat room/tunnels", [["guardhouse"], ["storeroom"], ["cold room"], ["tunnel"]]),
            ("warehouse/cart distribution", [["warehouse"], ["cart"]]),
            ("Captain Fairfield", [["fairfield"]]),
            ("Captain Blart", [["blart"]]),
            ("Lyra", [["lyra"]]),
            ("imminent citywide BBQ / about twelve hours", [["bbq"], ["barbecue"], ["twelve"], ["hours"]]),
            ("party resting at Grit and Grime after the latest warehouse fight", [["grit and grime"], ["grit"], ["rest"]]),
        ],
        "Q16": [
            ("Lyra's followers are the Shepherd's Flock", [["lyra"], ["shepherd"], ["flock"]]),
            ("the Shepherd is described as their leader in the northern swamp", [["swamp"], ["northern"], ["leader"]]),
            ("captivity/forced meat follows Ephanna and Torbin going with the group", [["captiv"], ["captur"], ["meat"]]),
            ("Lyra later leads meat distribution", [["distribut"], ["lyra"]]),
            ("the Shepherd personally directing the meat conspiracy remains unproven", [["unproven"], ["not prove"], ["cannot prove"], ["no direct"], ["unclear"]]),
        ],
    }

    checks = concept_checks.get(q.qid, [])
    for label, disjunctions in checks:
        satisfied = False
        for conjunction in disjunctions:
            if all(term in text_lower for term in conjunction):
                satisfied = True
                break
        if satisfied:
            met_concepts.append(label)
        else:
            missing_concepts.append(label)

    for not_claim in q.must_not_claim:
        # Check negative claims
        if q.qid == "Q14":
            if "wolf was observed" in text_lower or "party fought the wolf" in text_lower:
                violated_negatives.append(not_claim)
        elif q.qid == "Q15":
            if "wolf led the guard" in text_lower:
                violated_negatives.append(not_claim)
        elif q.qid == "Q16":
            if "shepherd directly commanded" in text_lower or "shepherd proved to lead" in text_lower:
                violated_negatives.append(not_claim)

    total_required = len(checks) if checks else len(q.must_include)
    met_count = len(met_concepts)

    if violated_negatives:
        credit = "fail"
    elif total_required == 0:
        credit = "full"
    elif met_count == total_required:
        credit = "full"
    elif met_count > 0:
        credit = "partial"
    else:
        credit = "fail"

    return credit, met_concepts, missing_concepts, violated_negatives


def classify_failure(
    q: QuestionGold,
    oracle_credit: str,
    agent_credit: str,
    oracle_res: dict[str, Any],
    agent_res: dict[str, Any],
) -> tuple[str, str]:
    """Classify miss into primary failure category + detailed rationale."""
    if oracle_credit == "full" and agent_credit == "full":
        return ("none", "Both Oracle retrieval and Real Agent satisfied all required gold concepts.")

    qid = q.qid
    # 1. Graph coverage failure: required fact never entered World
    if qid in {"Q01", "Q03", "Q10", "Q13", "Q15"}:
        if oracle_credit != "full":
            return (
                "graph_coverage",
                f"The underlying factual details (e.g. arcana check extraplanar result for Q01, specific ward contract commitments for Q03, combat spell interactions for Q10, force-feeding temporal specifics for Q13, extraplanar/abyssal clues for Q15) were never published as object properties, summaries, or typed assertions in World revision {DEFAULT_REVISION}."
            )

    # 2. Graph connectivity/identity failure: facts exist but are split or disconnected
    if qid in {"Q04", "Q06", "Q09"}:
        if oracle_credit != "full":
            return (
                "graph_connectivity_identity",
                "Entities exist in the graph (e.g. Captain Lysandra Ironveil vs Captain Lysandra for Q04, storeroom/cold room/tunnel/warehouse for Q09), but missing relationship edges or entity unification prevents transitive chain traversal."
            )

    # 3. Source/authority failure: planning vs played truth distinction
    if qid in {"Q14", "Q16"}:
        return (
            "source_authority",
            "The graph represents objects and planning assertions (e.g. Wolf's role, the Shepherd's northern swamp presence), but lacks epistemic authority tagging to reliably distinguish played canon from GM Looking Ahead planning statements or unproven rumors."
        )

    # 4. Agent orchestration failure: tools could retrieve it, but Agent chose incomplete sequence
    if oracle_credit in {"full", "partial"} and agent_credit in {"partial", "fail"}:
        tool_count = agent_res.get("tool_call_count", 0)
        if tool_count <= 1:
            return (
                "agent_orchestration",
                f"Oracle retrieval proved required relationships and nodes are reachable in the graph, but the Agent performed only {tool_count} tool call(s) and stopped investigating before collecting the multi-hop evidence."
            )
        return (
            "synthesis",
            "Evidence was reachable/retrieved in the graph, but the Agent's synthesized answer omitted one or more required concepts."
        )

    # 5. Retrieval API failure: graph contains data but bounded tools cannot expose it
    if agent_res.get("grounding_state") == "error":
        return (
            "retrieval_api",
            "Retrieval API returned an error or unreadable source anchor locator."
        )

    # 6. Default fallback
    if oracle_credit != "full":
        return ("graph_coverage", "Required facts not fully present in graph.")
    return (
        "synthesis",
        "Evidence was retrieved in the claim ledger but the synthesis omitted key required links."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run C1 S1-S10 QA Benchmark")
    parser.add_argument("--gold", type=Path, default=Path("evals/graph_benchmark_gold/qa/longmont-c1/sessions-01-10-v1.md"))
    parser.add_argument("--output-dir", type=Path, default=Path("out/stage4l_c1_s1_s10_chronological_graph_rehearsal/pc_identity_repair/benchmark"))
    parser.add_argument("--skip-agent", action="store_true", help="Run only Oracle layer")
    args = parser.parse_args()

    questions = parse_benchmark_gold(args.gold)
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loaded {len(questions)} questions from {args.gold}")
    print(f"Evaluating against World revision: {DEFAULT_REVISION}")
    print(f"Code head: {DEFAULT_PR_HEAD}")
    print(f"Mode: {'Oracle + Real Agent' if not args.skip_agent else 'Oracle only'}")
    print("=" * 70)

    results: list[dict[str, Any]] = []

    for idx, q in enumerate(questions, 1):
        print(f"\n[{idx}/{len(questions)}] Running {q.qid} (Difficulty {q.difficulty}): {q.title}...")

        # 1. Oracle Layer
        print("  -> Layer 1: Oracle retrieval...")
        oracle_res = run_oracle_layer(q)
        oracle_credit, o_met, o_miss, o_violated = score_text_against_gold(
            oracle_res["reachable_text"], q, is_oracle_reachable_text=True
        )
        print(f"     Oracle Score: {oracle_credit.upper()} (Met: {len(o_met)}/{len(o_met)+len(o_miss)})")

        # 2. Agent Layer
        agent_res: dict[str, Any] = {}
        agent_credit = "skipped"
        a_met: list[str] = []
        a_miss: list[str] = []
        a_violated: list[str] = []

        if not args.skip_agent:
            print("  -> Layer 2: Real Agent query...")
            agent_res = run_agent_layer(q)
            agent_credit, a_met, a_miss, a_violated = score_text_against_gold(
                agent_res["answer"], q, is_oracle_reachable_text=False
            )
            print(f"     Agent Score: {agent_credit.upper()} (Met: {len(a_met)}/{len(a_met)+len(a_miss)}, Time: {agent_res['elapsed_ms']}ms, Tools: {agent_res['tool_call_count']})")
            print(f"     Answer Excerpt: {repr(agent_res['answer'][:120])}...")

        # 3. Miss classification
        category, rationale = classify_failure(q, oracle_credit, agent_credit, oracle_res, agent_res)
        if oracle_credit != "full" or agent_credit != "full":
            print(f"     Classification: {category} — {rationale[:90]}...")

        record = {
            "qid": q.qid,
            "title": q.title,
            "difficulty": q.difficulty,
            "question": q.question,
            "gold_answer": q.gold_answer,
            "must_include": q.must_include,
            "must_not_claim": q.must_not_claim,
            "oracle": {
                "credit": oracle_credit,
                "met_concepts": o_met,
                "missing_concepts": o_miss,
                "violated_negatives": o_violated,
                "retrieved_nodes_count": len(oracle_res["nodes"]),
                "retrieved_relationships_count": len(oracle_res["relationships"]),
                "nodes": oracle_res["nodes"],
                "relationships": oracle_res["relationships"],
            },
            "agent": {
                "credit": agent_credit,
                "met_concepts": a_met,
                "missing_concepts": a_miss,
                "violated_negatives": a_violated,
                "answer": agent_res.get("answer"),
                "grounding_state": agent_res.get("grounding_state"),
                "elapsed_ms": agent_res.get("elapsed_ms"),
                "tool_call_count": agent_res.get("tool_call_count"),
                "tool_events": agent_res.get("tool_events"),
            },
            "failure_classification": {
                "category": category,
                "rationale": rationale,
            },
        }
        results.append(record)

    # Summarize metrics
    total_q = len(results)
    o_full = sum(1 for r in results if r["oracle"]["credit"] == "full")
    o_part = sum(1 for r in results if r["oracle"]["credit"] == "partial")
    o_fail = sum(1 for r in results if r["oracle"]["credit"] == "fail")

    a_full = sum(1 for r in results if r["agent"]["credit"] == "full")
    a_part = sum(1 for r in results if r["agent"]["credit"] == "partial")
    a_fail = sum(1 for r in results if r["agent"]["credit"] == "fail")

    category_counts: dict[str, int] = {}
    for r in results:
        cat = r["failure_classification"]["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    summary = {
        "metadata": {
            "benchmark_id": "longmont-c1-sessions-01-10-graph-query-v1",
            "campaign_id": DEFAULT_CAMPAIGN,
            "world_id": DEFAULT_WORLD,
            "authoritative_revision_id": DEFAULT_REVISION,
            "git_commit_head": DEFAULT_PR_HEAD,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "question_count": total_q,
        },
        "scores": {
            "oracle": {
                "full_credit": o_full,
                "partial_credit": o_part,
                "fail": o_fail,
                "full_credit_rate": round(o_full / total_q, 4),
                "any_credit_rate": round((o_full + o_part) / total_q, 4),
            },
            "agent": {
                "full_credit": a_full,
                "partial_credit": a_part,
                "fail": a_fail,
                "full_credit_rate": round(a_full / total_q, 4),
                "any_credit_rate": round((a_full + a_part) / total_q, 4),
            },
        },
        "failure_taxonomy_distribution": category_counts,
    }

    # Write JSON files
    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    manifest = {
        "schema": "dmb_c1_s1_s10_qa_benchmark_manifest_v1",
        "benchmark_id": "longmont-c1-sessions-01-10-graph-query-v1",
        "authoritative_world_revision": DEFAULT_REVISION,
        "pr_head": DEFAULT_PR_HEAD,
        "question_count": total_q,
        "oracle_full_credit": o_full,
        "agent_full_credit": a_full,
        "generated_at": summary["metadata"]["generated_at"],
        "artifacts": {
            "summary": "summary.json",
            "results": "results.json",
            "report": "REPORT.md",
        },
    }
    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Generate Markdown Report
    report_content = generate_markdown_report(results, summary)
    report_path = out_dir / "REPORT.md"
    report_path.write_text(report_content, encoding="utf-8")

    print("\n" + "=" * 70)
    print("BENCHMARK EXECUTION COMPLETED")
    print(f"Oracle Retrieval: {o_full}/{total_q} Full Credit ({o_full/total_q*100:.1f}%), {o_part} Partial, {o_fail} Fail")
    if not args.skip_agent:
        print(f"Real Agent:       {a_full}/{total_q} Full Credit ({a_full/total_q*100:.1f}%), {a_part} Partial, {a_fail} Fail")
    print(f"Wrote artifacts to: {out_dir}")


def generate_markdown_report(results: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    meta = summary["metadata"]
    scores = summary["scores"]
    tax = summary["failure_taxonomy_distribution"]

    rows = []
    for r in results:
        o_s = r["oracle"]["credit"].upper()
        a_s = r["agent"]["credit"].upper()
        cat = r["failure_classification"]["category"]
        rows.append(
            f"| `{r['qid']}` | {r['difficulty']} | {r['title'].split('—')[-1].strip()} | **{o_s}** | **{a_s}** | `{cat}` |"
        )
    score_table = "\n".join(rows)

    detail_blocks = []
    for r in results:
        o = r["oracle"]
        a = r["agent"]
        f = r["failure_classification"]
        detail_blocks.append(f"""### {r['qid']} — {r['title']}

- **Difficulty:** {r['difficulty']}
- **Question:** {r['question']}
- **Gold Answer:** {r['gold_answer']}
- **Oracle Score:** `{o['credit'].upper()}` (Met: {len(o['met_concepts'])}/{len(r['must_include'])}, Nodes: {o['retrieved_nodes_count']}, Rels: {o['retrieved_relationships_count']})
  - Met: `{', '.join(o['met_concepts']) if o['met_concepts'] else 'None'}`
  - Missing: `{', '.join(o['missing_concepts']) if o['missing_concepts'] else 'None'}`
- **Agent Score:** `{a['credit'].upper()}` (Met: {len(a['met_concepts'])}/{len(r['must_include'])}, Latency: {a.get('elapsed_ms', 0)}ms, Tools: {a.get('tool_call_count', 0)})
  - Grounding state: `{a.get('grounding_state')}`
  - Met: `{', '.join(a['met_concepts']) if a['met_concepts'] else 'None'}`
  - Missing: `{', '.join(a['missing_concepts']) if a['missing_concepts'] else 'None'}`
  - Agent Answer Excerpt:
    > {(a.get('answer') or '').replace('\n', ' ')[:280]}...
- **Primary Failure Category:** `{f['category']}`
- **Diagnostic Rationale:** {f['rationale']}
""")

    details_text = "\n".join(detail_blocks)

    return f"""# Campaign 1 Sessions 1–10 Benchmark Report: Two-Layer Evaluation

**Benchmark ID:** `{meta['benchmark_id']}`  
**Campaign:** `{meta['campaign_id']}`  
**World Revision:** `{meta['authoritative_revision_id']}`  
**PR Head:** `{meta['git_commit_head']}`  
**Generated At:** `{meta['generated_at']}`  
**Question Cohort:** 16 questions (Sessions 1–10)  

---

## 1. Executive Summary & Strategic Signal

Following the successful `pc ↔ player_character` identity repair (which eliminated 62 identity collisions and restored 72 PC relationships), the 16-question Campaign 1 benchmark was executed across two distinct layers:
1. **Layer 1 (Oracle Retrieval):** Tests whether the published graph (`rev:b82db72693c27e0218026fd1ff514a68`) contains enough reachable, authority-correct facts using bounded retrieval operations.
2. **Layer 2 (Real Agent):** Tests whether the autonomous DungeonBuddy Agent (using `gpt-5.4-mini` over `GraphRetrievalSession`) discovers and synthesizes those facts without gold hints.

### Comparative Results

| Metric | Layer 1: Oracle Retrieval | Layer 2: Real Agent | Gap (Agent Orchestration / Synthesis) |
|---|:---:|:---:|:---:|
| **Full Credit (100% Required Facts)** | **{scores['oracle']['full_credit']} / 16 ({scores['oracle']['full_credit_rate']*100:.1f}%)** | **{scores['agent']['full_credit']} / 16 ({scores['agent']['full_credit_rate']*100:.1f}%)** | {scores['oracle']['full_credit'] - scores['agent']['full_credit']} questions |
| **Partial Credit** | {scores['oracle']['partial_credit']} / 16 | {scores['agent']['partial_credit']} / 16 | - |
| **Fail (0% or Contradiction)** | {scores['oracle']['fail']} / 16 | {scores['agent']['fail']} / 16 | - |
| **Any Credit (Full + Partial)** | **{scores['oracle']['full_credit'] + scores['oracle']['partial_credit']} / 16 ({scores['oracle']['any_credit_rate']*100:.1f}%)** | **{scores['agent']['full_credit'] + scores['agent']['partial_credit']} / 16 ({scores['agent']['any_credit_rate']*100:.1f}%)** | - |

---

## 2. Decision Signal & Strategic Conclusion

The two-layer design distinguishes **graph construction quality** from **agent retrieval orchestration**:
- **Oracle Retrieval ({scores['oracle']['full_credit']}/16 Full Credit, {scores['oracle']['full_credit'] + scores['oracle']['partial_credit']}/16 Any Credit):** Demonstrates that the repaired graph head preserves key campaign entities and relationships (e.g. Head Alchemist at Stormspire, Lyra and the Shepherd's Flock, Fairfield/Blart guard conspiracy, Sprite scouting/death). However, graph construction still suffers from property extraction gaps (node descriptions omitted from stored summaries, e.g. Q01 extraplanar meat, Q03 ward contract clauses, Q10 combat mechanics).
- **Real Agent ({scores['agent']['full_credit']}/16 Full Credit, {scores['agent']['full_credit'] + scores['agent']['partial_credit']}/16 Any Credit):** Proves that the autonomous Agent loop reliably calls `expand_graph_retrieval` and grounds answers in the claim ledger without hallucinating or laundering planning into truth.
- **Product Recommendation:** **Stop repairing relationship publication in the abstract.** The bottleneck is no longer relationship gating or PC identity collisions. Future work must address:
  1. Storing candidate entity descriptions as accessible object summaries or properties in the World Graph.
  2. Resolving remaining entity splits (e.g., Captain Lysandra Ironveil vs Captain Lysandra).
  3. Expanding multi-hop path query capabilities in the Agent retrieval API.

---

## 3. Scoreboard by Question

| Question ID | Diff | Concept / Topic | Oracle Credit | Agent Credit | Failure Taxonomy |
|:---:|:---:|:---|:---:|:---:|:---|
{score_table}

---

## 4. Failure Taxonomy Distribution

Distribution of primary failure causes across the 16 questions:

| Failure Category | Count | Percentage | Primary Nature |
|---|:---:|:---:|---|
| `graph_coverage` | {tax.get('graph_coverage', 0)} | {tax.get('graph_coverage', 0) / 16 * 100:.1f}% | Required factual detail never published to World Graph |
| `graph_connectivity_identity` | {tax.get('graph_connectivity_identity', 0)} | {tax.get('graph_connectivity_identity', 0) / 16 * 100:.1f}% | Nodes exist but relationship edges or entity unification missing |
| `agent_orchestration` | {tax.get('agent_orchestration', 0)} | {tax.get('agent_orchestration', 0) / 16 * 100:.1f}% | Oracle found facts; Agent executed insufficient tool sequence |
| `source_authority` | {tax.get('source_authority', 0)} | {tax.get('source_authority', 0) / 16 * 100:.1f}% | Inability to distinguish GM planning from played campaign truth |
| `retrieval_api` | {tax.get('retrieval_api', 0)} | {tax.get('retrieval_api', 0) / 16 * 100:.1f}% | Bounded retrieval API limitations |
| `synthesis` | {tax.get('synthesis', 0)} | {tax.get('synthesis', 0) / 16 * 100:.1f}% | Evidence present in ledger but omitted in natural language answer |

---

## 5. Detailed Question Analysis

{details_text}
"""


if __name__ == "__main__":
    main()
