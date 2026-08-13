#!/usr/bin/env python3
"""Seed the Of Conks & Cons world from manufactured local gold.

Reads ``~/Downloads/of-conks-cons-v21-gold/gold/inventory.json`` (no module prose
in-repo), compiles a Kernel contribution, initializes ``of-conks-cons`` under
this worktree's ``out/``, admits the campaign→world overlay, and imports the
prepared source + optional Plan packet.

Example::

  uv run python scripts/seed_of_conks_cons_world.py
  uv run python scripts/seed_of_conks_cons_world.py --gold-dir ~/Downloads/of-conks-cons-v21-gold
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import graph_memory.kernel as kernel
from apps.live_control_server.services.admitted_campaign_worlds import (
    upsert_admitted_campaign_world,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    list_workspace_documents,
)
from graph_memory.kernel.contribution_models import (
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import create_graph_contribution
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.world_supergraph.storage import (
    load_world_graph_revision,
    try_open_world_graph_head,
)

WORLD_ID = "of-conks-cons"
CAMPAIGN_ID = "of-conks-cons"
DEFAULT_GOLD_DIR = Path.home() / "Downloads" / "of-conks-cons-v21-gold"
CORPUS_SOURCE_REL = "corpus/of-conks-cons-markdown/Of-Conks-and-Cons-v21.md"
PREPARED_REL = "specimens/02-prepared.md"
INVENTORY_REL = "gold/inventory.json"
BUNDLE_ID = "of-conks-cons-gold-v0"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _node_id_for(entry_id: str, bucket: str) -> str:
    if bucket == "locations":
        return f"location:{entry_id}"
    if bucket == "actors":
        return f"npc:{entry_id}"
    if bucket == "creatures":
        if entry_id == "helix-child":
            return f"npc:{entry_id}"
        return f"threat:{entry_id}"
    if bucket == "items":
        return f"item:{entry_id}"
    if bucket == "collectives":
        return f"faction:{entry_id}"
    raise ValueError(f"unknown bucket {bucket!r}")


def _kind_for(entry_id: str, bucket: str) -> str:
    if bucket == "locations":
        return "location"
    if bucket == "actors":
        return "npc"
    if bucket == "creatures":
        if entry_id == "helix-child":
            return "npc"
        return "threat"
    if bucket == "items":
        return "item"
    if bucket == "collectives":
        return "faction"
    raise ValueError(f"unknown bucket {bucket!r}")


def _role_for(entry_id: str, bucket: str) -> str:
    if bucket == "locations":
        if entry_id == "hempholm":
            return "village"
        return "site"
    if bucket == "actors":
        return "npc"
    if bucket == "creatures":
        if entry_id == "helix-child":
            return "npc"
        return "encounter-threat"
    if bucket == "items":
        return "magic-item" if entry_id != "the-conk" else "plot-item"
    if bucket == "collectives":
        return "faction"
    return "unknown"


def _build_id_map(inventory: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for bucket in ("locations", "actors", "creatures", "items", "collectives"):
        for entry in inventory[bucket]["required"]:
            mapping[entry["id"]] = _node_id_for(entry["id"], bucket)
    return mapping


def compile_contribution(
    *,
    inventory: dict[str, Any],
    prepared_sha256: str,
    source_uri: str,
) -> GraphContribution:
    source_artifact_id = f"corpus:{WORLD_ID}:prepared-module"
    source_revision_id = f"sha256:{prepared_sha256}"
    id_map = _build_id_map(inventory)
    assertions: list[GraphContributionAssertion] = []

    def evidence_block(entry: dict[str, Any], evidence_ref_id: str) -> dict[str, Any]:
        return {
            "evidence_ref_id": evidence_ref_id,
            "locator": f"heading:{entry['heading']}",
            "source_artifact_id": source_artifact_id,
            "source_domain": "worldbuilding",
        }

    def source_artifact_block() -> dict[str, Any]:
        return {
            "campaign_id": CAMPAIGN_ID,
            "content_sha256": prepared_sha256,
            "source_artifact_id": source_artifact_id,
            "source_domain": "worldbuilding",
            "uri": source_uri,
        }

    for bucket in ("locations", "actors", "creatures", "items", "collectives"):
        for entry in inventory[bucket]["required"]:
            node_id = id_map[entry["id"]]
            evidence_ref_id = _stable_id("evidence", "node", node_id)
            aliases = list(entry.get("aliases") or [entry["label"]])
            if entry["label"] not in aliases:
                aliases.insert(0, entry["label"])
            assertions.append(
                GraphContributionAssertion.model_validate(
                    {
                        "acceptance_state": "accepted",
                        "assertion_id": "assertion:pending",
                        "assertion_kind": "node",
                        "campaign_scope": None,
                        "contribution_id": "pending",
                        "epistemic_kind": "fact",
                        "evidence_ref_ids": [evidence_ref_id],
                        "identity_resolution_outcome": "created_new",
                        "label": entry["label"],
                        "predicate": None,
                        "source_artifact_id": source_artifact_id,
                        "source_revision_id": source_revision_id,
                        "subject_node_id": node_id,
                        "target_node_id": None,
                        "temporal_scope": None,
                        "value": {
                            "aliases": aliases,
                            "approval_state": "accepted",
                            "canon_state": "worldbuilding_draft",
                            "evidence": [evidence_block(entry, evidence_ref_id)],
                            "kind": _kind_for(entry["id"], bucket),
                            "role": _role_for(entry["id"], bucket),
                            "source_artifacts": [source_artifact_block()],
                            "source_domains": ["worldbuilding"],
                        },
                        "visibility": "gm",
                    }
                )
            )

    for edge in inventory["edges"]["required"]:
        source_id = id_map[edge["from"]]
        target_id = id_map[edge["to"]]
        predicate = edge["type"]
        edge_id = f"edge:{source_id}:{predicate}:{target_id}"
        evidence_ref_id = _stable_id("evidence", "edge", edge_id)
        assertions.append(
            GraphContributionAssertion.model_validate(
                {
                    "acceptance_state": "accepted",
                    "assertion_id": "assertion:pending",
                    "assertion_kind": "edge",
                    "campaign_scope": None,
                    "contribution_id": "pending",
                    "epistemic_kind": "fact",
                    "evidence_ref_ids": [evidence_ref_id],
                    "identity_resolution_outcome": "created_new",
                    "label": predicate.replace("_", " "),
                    "predicate": predicate,
                    "source_artifact_id": source_artifact_id,
                    "source_revision_id": source_revision_id,
                    "subject_node_id": source_id,
                    "target_node_id": target_id,
                    "temporal_scope": None,
                    "value": {
                        "approval_state": "accepted",
                        "canon_state": "worldbuilding_draft",
                        "direction": "outbound",
                        "edge_id": edge_id,
                        "evidence": [
                            {
                                "evidence_ref_id": evidence_ref_id,
                                "locator": f"edge:{predicate}",
                                "source_artifact_id": source_artifact_id,
                                "source_domain": "worldbuilding",
                            }
                        ],
                        "source_artifacts": [source_artifact_block()],
                        "source_domains": ["worldbuilding"],
                    },
                    "visibility": "gm",
                }
            )
        )

    return create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile="of-conks-cons-gold-manual-v0",
        campaign_scope=None,
        accepted_assertions=assertions,
        authored_by="local-gold-seed",
        produced_at="2026-08-12T00:00:00Z",
        proposal_digest=_sha256_text(f"{BUNDLE_ID}:{prepared_sha256}"),
    )


def write_local_bundle(
    gold_dir: Path,
    contribution: GraphContribution,
) -> tuple[Path, str]:
    graph_dir = gold_dir / "graph"
    contrib_dir = graph_dir / "contributions"
    contrib_dir.mkdir(parents=True, exist_ok=True)
    contrib_path = contrib_dir / "001-hempholm-module-gold.json"
    payload = contribution.model_dump(mode="json")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    contrib_path.write_text(text, encoding="utf-8")
    digest = _sha256_text(text)

    required_node_ids = sorted(
        {
            a.subject_node_id
            for a in contribution.accepted_assertions
            if a.assertion_kind == "node" and a.subject_node_id
        }
    )
    required_edge_ids = sorted(
        {
            str(a.value.get("edge_id"))
            for a in contribution.accepted_assertions
            if a.assertion_kind == "edge" and a.value.get("edge_id")
        }
    )
    manifest = {
        "schema": "dmb_graph_contribution_bundle_v1",
        "version": "1.0",
        "bundle_id": BUNDLE_ID,
        "world_id": WORLD_ID,
        "primary_campaign_scope": CAMPAIGN_ID,
        "planning_focus": "hempholm-oneshot",
        "focus_sessions": ["oneshot"],
        "ordered_contributions": [
            {
                "contribution_id": contribution.contribution_id,
                "path": "contributions/001-hempholm-module-gold.json",
                "sha256": digest,
            }
        ],
        "identity_decisions": [],
        "required_node_ids": required_node_ids,
        "required_edge_ids": required_edge_ids,
        "expected_source_domains": ["worldbuilding"],
        "expected_shared_support": [],
        "non_claims": [
            "Local gold seed only; not an Eldyrwild contribution.",
            "Does not include AC/HP threat sheets.",
            "Does not commit module prose to git.",
            "canon_state is worldbuilding_draft.",
        ],
        "bundle_digest": digest,
    }
    (graph_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return contrib_path, digest


def initialize_world(contribution: GraphContribution, bundle_digest: str) -> None:
    out_root = ROOT / "out"
    out_root.mkdir(parents=True, exist_ok=True)
    existing = try_open_world_graph_head(out_root, WORLD_ID)
    if existing is not None:
        print(
            f"World {WORLD_ID!r} already exists at head {existing.head_revision_id}; skipping init."
        )
        return

    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id="oneshot",
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution.contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(contribution),
            )
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id=BUNDLE_ID,
            bundle_digest=bundle_digest,
            approved_bundle_merge_sha="local-gold-operator-attestation",
        ),
    )
    result = initialize_world_from_contributions(
        out_root,
        plan=plan,
        contributions=[contribution],
        actor="gm",
    )
    if not result.published:
        raise RuntimeError(f"world init failed: state={result.state} diagnostics={result.diagnostics}")
    print(
        f"Initialized world {WORLD_ID} head={result.initial_head_revision_id} "
        f"nodes={result.receipt.node_count if result.receipt else '?'} "
        f"edges={result.receipt.edge_count if result.receipt else '?'}"
    )


def ensure_corpus_prepared(gold_dir: Path) -> Path:
    prepared = gold_dir / PREPARED_REL
    if not prepared.is_file():
        raise FileNotFoundError(f"missing prepared source: {prepared}")
    dest = ROOT / CORPUS_SOURCE_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file() or _sha256_bytes(dest.read_bytes()) != _sha256_bytes(prepared.read_bytes()):
        shutil.copy2(prepared, dest)
        print(f"Copied prepared source → {dest.relative_to(ROOT)}")
    return dest


def import_prepared_source(prepared_path: Path) -> str:
    existing = [
        r
        for r in list_workspace_documents(
            ROOT,
            campaign_id=CAMPAIGN_ID,
            kind="worldbuilding_source",
            status="active",
        )
        if r.title == "Of Conks & Cons v2.1"
    ]
    if existing:
        print(f"Worldbuilding source already present: {existing[0].document_id}")
        return existing[0].document_id

    record = create_workspace_document(
        ROOT,
        title="Of Conks & Cons v2.1",
        campaign_id=CAMPAIGN_ID,
        kind="worldbuilding_source",
        world_id=WORLD_ID,
        source_domain="worldbuilding",
        document_class="adventure_module",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = prepared_path.read_text(encoding="utf-8")
    prepared = prepare_tiptap_markdown_write(
        root=ROOT,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    if not prepared.writer_ok or not prepared.writer_confirm_token:
        raise RuntimeError(f"source_import prepare failed: {prepared}")
    commit_tiptap_markdown_write(
        root=ROOT,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
            writer_confirm_token=prepared.writer_confirm_token,
            write_mode="source_import",
        ),
    )
    print(f"Imported prepared source as document {record.document_id}")
    return record.document_id


def import_plan_packet(gold_dir: Path) -> str | None:
    packet = gold_dir / "playable" / "hempholm-prep.md"
    if not packet.is_file():
        print("No playable/hempholm-prep.md; skipping Plan packet.")
        return None
    existing = [
        r
        for r in list_workspace_documents(
            ROOT,
            campaign_id=CAMPAIGN_ID,
            kind="plan",
            status="active",
        )
        if r.title == "Hempholm — run packet"
    ]
    if existing:
        print(f"Plan packet already present: {existing[0].document_id}")
        return existing[0].document_id

    record = create_workspace_document(
        ROOT,
        title="Hempholm — run packet",
        campaign_id=CAMPAIGN_ID,
        kind="plan",
        target_session=1,
    )
    markdown = packet.read_text(encoding="utf-8")
    prepared = prepare_tiptap_markdown_write(
        root=ROOT,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
            write_mode="authoring",
        ),
    )
    if not prepared.writer_ok or not prepared.writer_confirm_token:
        raise RuntimeError(f"plan prepare failed: {prepared}")
    commit_tiptap_markdown_write(
        root=ROOT,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
            writer_confirm_token=prepared.writer_confirm_token,
            write_mode="authoring",
        ),
    )
    print(f"Imported Plan packet as document {record.document_id}")
    return record.document_id


def verify_world(inventory: dict[str, Any]) -> None:
    out_root = ROOT / "out"
    head = try_open_world_graph_head(out_root, WORLD_ID)
    if head is None:
        raise RuntimeError(f"world head missing for {WORLD_ID}")
    store = load_world_graph_revision(out_root, WORLD_ID, head.head_revision_id)
    id_map = _build_id_map(inventory)
    missing = [nid for nid in id_map.values() if nid not in store.nodes]
    if missing:
        raise RuntimeError(f"missing nodes after init: {missing}")
    eldyrwild = try_open_world_graph_head(out_root, "eldyrwild")
    if eldyrwild is not None:
        print(f"Note: eldyrwild head present ({eldyrwild.head_revision_id}); left untouched.")
    print(
        f"Verified {len(id_map)} required nodes on {WORLD_ID} head={head.head_revision_id}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold-dir",
        type=Path,
        default=DEFAULT_GOLD_DIR,
        help="Local manufactured gold package (default: ~/Downloads/of-conks-cons-v21-gold)",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Only compile contribution + initialize world + admit campaign",
    )
    args = parser.parse_args()
    gold_dir = args.gold_dir.expanduser().resolve()
    inventory_path = gold_dir / INVENTORY_REL
    if not inventory_path.is_file():
        raise SystemExit(f"missing inventory: {inventory_path}")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    prepared_path = ensure_corpus_prepared(gold_dir)
    prepared_sha = _sha256_bytes(prepared_path.read_bytes())
    if inventory.get("source_sha256") and inventory["source_sha256"] != prepared_sha:
        print(
            f"WARNING: inventory source_sha256={inventory['source_sha256']} "
            f"!= prepared {prepared_sha}"
        )

    contribution = compile_contribution(
        inventory=inventory,
        prepared_sha256=prepared_sha,
        source_uri=f"repo://{CORPUS_SOURCE_REL}",
    )
    _, bundle_digest = write_local_bundle(gold_dir, contribution)
    print(f"Wrote local gold contribution bundle digest={bundle_digest[:16]}…")

    initialize_world(contribution, bundle_digest)
    verify_world(inventory)

    upsert_admitted_campaign_world(
        campaign_id=CAMPAIGN_ID,
        world_id=WORLD_ID,
        label="Of Conks & Cons",
        source="seed",
        root=ROOT,
    )
    print(f"Admitted campaign {CAMPAIGN_ID} → world {WORLD_ID}")

    if not args.skip_import:
        import_prepared_source(prepared_path)
        import_plan_packet(gold_dir)

    print("Done. Open /build?campaign=of-conks-cons against this worktree's out/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
