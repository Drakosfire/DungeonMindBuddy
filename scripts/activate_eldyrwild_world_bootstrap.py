#!/usr/bin/env python3
"""Headless operator wrapper for the PR006D2 bootstrap contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
for _path in (str(_REPO_ROOT), str(_SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from pydantic import ValidationError  # noqa: E402

from apps.live_control_server.models.world_graph_bootstrap import (  # noqa: E402
    WorldGraphBootstrapConfirmRequest,
    WorldGraphBootstrapErrorResponse,
    WorldGraphBootstrapPrepareRequest,
)
from apps.live_control_server.services.world_graph_bootstrap import (  # noqa: E402
    WorldGraphBootstrapError,
    confirm_world_graph_bootstrap,
    get_world_graph_bootstrap_status,
    prepare_world_graph_bootstrap,
)


class _ArgumentParseError(ValueError):
    pass


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentParseError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Activate the fixed approved Eldyrwild world bootstrap."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--root", type=Path)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--root", type=Path)
    prepare.add_argument("--actor", required=True)

    confirm = subparsers.add_parser("confirm")
    confirm.add_argument("--root", type=Path)
    confirm.add_argument("--actor", required=True)
    confirm.add_argument("--proposal-id", required=True)
    confirm.add_argument("--confirm-token", required=True)
    return parser


def _print_json(model: object) -> None:
    payload = (
        model.model_dump(mode="json", by_alias=True)
        if hasattr(model, "model_dump")
        else model
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))


def _error_model(
    *,
    code: str,
    message: str,
    status_code: int,
) -> WorldGraphBootstrapErrorResponse:
    return WorldGraphBootstrapErrorResponse(
        code=code,
        message=message,
        status_code=status_code,
        bootstrap_state="error",
    )


def _validation_code(error: ValidationError) -> str:
    if any(
        "actor" in {str(item) for item in entry.get("loc", ())}
        for entry in error.errors()
    ):
        return "invalid_actor"
    return "invalid_request"


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except _ArgumentParseError as exc:
        code = "invalid_actor" if "--actor" in str(exc) else "invalid_request"
        _print_json(
            _error_model(
                code=code,
                message="Bootstrap command arguments do not match the required contract.",
                status_code=422,
            )
        )
        return 1
    root = args.root
    try:
        if args.command == "status":
            _print_json(get_world_graph_bootstrap_status(root=root))
            return 0
        if args.command == "prepare":
            request = WorldGraphBootstrapPrepareRequest(actor=args.actor)
            _print_json(prepare_world_graph_bootstrap(request, root=root))
            return 0
        request = WorldGraphBootstrapConfirmRequest(
            actor=args.actor,
            proposal_id=args.proposal_id,
            confirm_token=args.confirm_token,
        )
        _print_json(confirm_world_graph_bootstrap(request, root=root))
        return 0
    except WorldGraphBootstrapError as exc:
        _print_json(exc.response())
        return 1
    except ValidationError as exc:
        code = _validation_code(exc)
        _print_json(
            _error_model(
                code=code,
                message="Bootstrap command arguments do not match the required contract.",
                status_code=422,
            )
        )
        return 1
    except Exception:
        _print_json(
            _error_model(
                code="bootstrap_internal_error",
                message="The Eldyrwild bootstrap operation failed unexpectedly.",
                status_code=500,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
