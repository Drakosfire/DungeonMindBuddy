#!/usr/bin/env python3
"""Inspect by default; explicitly resume a pinned, already-reviewed packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument(
        "--packet-sha256",
        required=True,
        help="Externally pinned reviewed-file digest; no approval is inferred.",
    )
    parser.add_argument(
        "--managed-world",
        required=True,
        help="Actual selected Buddy World; must match its active native binding.",
    )
    parser.add_argument("--journal-directory", type=Path, required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Resume existing stage identities; default performs read-only receipt inspection.",
    )
    parser.add_argument(
        "--schema-ready",
        action="store_true",
        help="Caller attests the separately completed owning schema prerequisite; never migrates.",
    )
    parser.add_argument(
        "--backup-verified",
        action="store_true",
        help="Caller attests separately completed backup/restore verification; never creates a backup.",
    )
    args = parser.parse_args(argv)
    try:
        from src.bootstrap_env import load_dungeonmindbuddy_dotenv
        from starlette.requests import Request
        from apps.live_control_server.services.agent_graph_auth import (
            authenticate_native_graph_principal,
        )
        from apps.live_control_server.config import (
            artifact_data_root,
            world_graph_authority_database_url,
            world_graph_authority_mode,
        )
        from apps.live_control_server.services.reviewed_corpus_publication import (
            CorePublicationBackend,
            ReviewedCorpusPacket,
            ReviewedCorpusPublicationProcedure,
        )
        from apps.live_control_server.services.reviewed_corpus_publication_store import (
            PublicationProgressStore,
        )
        from dungeonmind.infrastructure.postgres import (
            PostgresDatabase,
            PostgresRepositoryBundle,
        )

        raw = args.packet.read_bytes()
        if (
            len(raw) > 4_194_304
            or hashlib.sha256(raw).hexdigest() != args.packet_sha256
        ):
            raise ValueError("packet_digest_mismatch")
        packet = ReviewedCorpusPacket.model_validate_json(raw)
        load_dungeonmindbuddy_dotenv()
        token = os.environ.get("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "")
        principal = authenticate_native_graph_principal(
            Request(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/",
                    "query_string": b"",
                    "client": ("127.0.0.1", 0),
                    "headers": [(b"authorization", ("Bearer " + token).encode())],
                }
            )
        )
        if principal.role != "gm" or world_graph_authority_mode() != "dungeonmind":
            raise ValueError("governed_authority_required")
        dsn = world_graph_authority_database_url()
        if not dsn:
            raise ValueError("native_authority_unavailable")
        backend = CorePublicationBackend(
            PostgresRepositoryBundle(PostgresDatabase(dsn)),
            artifact_root=artifact_data_root(),
        )
        result = ReviewedCorpusPublicationProcedure(
            backend, PublicationProgressStore(args.journal_directory)
        ).run(
            packet,
            selected_world_id=args.managed_world,
            execute=args.execute,
            schema_ready=args.schema_ready,
            backup_verified=args.backup_verified,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in ("verified", "published", "pending") else 2
    except Exception as exc:
        from apps.live_control_server.services.reviewed_corpus_publication import (
            ProcedureStopped,
        )
        from apps.live_control_server.services.reviewed_corpus_publication_store import (
            ProgressConflict,
        )

        code = (
            str(exc)
            if isinstance(exc, (ProcedureStopped, ProgressConflict))
            else "procedure_input_or_authority_rejected"
        )
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "code": code,
                    "next_action": "resolve_external_authority; do_not_rebase_or_create_new_ids",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
