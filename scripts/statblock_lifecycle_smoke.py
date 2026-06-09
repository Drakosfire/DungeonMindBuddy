#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.statblocks.lifecycle_commands import (  # noqa: E402
    STATBLOCK_DRAFT_GENERATE,
    STATBLOCK_DRAFT_RENDER,
    STATBLOCK_GENERATOR_HEALTH,
)
from src.statblocks.lifecycle_service import (  # noqa: E402
    StatblockLifecycleCommandRequest,
    StatblockLifecycleCommandResult,
    StatblockLifecycleService,
)
from src.statblocks.v2_client import (  # noqa: E402
    DungeonMindServerStatBlockGeneratorClient,
    MockStatBlockGeneratorProvider,
    StatBlockGeneratorClientConfigError,
    StatBlockGeneratorProvider,
)
from src.statblocks.v2_contract import ContractError  # noqa: E402

_FIXTURE_DIR = _REPO_ROOT / "tests" / "statblocks" / "fixtures"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run statblock lifecycle command smoke checks. Defaults to mock provider."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("health", "generate-fixture", "render-fixture"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument(
            "--provider",
            choices=("mock", "http"),
            default="mock",
            help="Provider to call. HTTP mode uses DungeonMindServer and requires server-side credentials.",
        )
        subparser.add_argument(
            "--allow-error",
            action="store_true",
            help="Exit zero even when the command result status is error or unsupported.",
        )
        subparser.add_argument(
            "--requested-by",
            default="agent",
            help="Command requester label used when mapping draft artifacts.",
        )
    subparsers.choices["generate-fixture"].add_argument(
        "--confirm-live-generate",
        action="store_true",
        help="Required with --provider http because live generation may call OpenAI through DungeonMindServer.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dungeonmindbuddy_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if (
        args.command == "generate-fixture"
        and args.provider == "http"
        and not args.confirm_live_generate
    ):
        result = StatblockLifecycleCommandResult(
            command_type=STATBLOCK_DRAFT_GENERATE,
            status="error",
            error=ContractError(
                code="live_generate_confirmation_required",
                message="Refusing live statblock generation without --confirm-live-generate.",
                details={
                    "safe_default": "mock",
                    "confirmation_flag": "--confirm-live-generate",
                },
            ),
            diagnostics=[
                "mock provider is safe for local smoke checks",
                "HTTP generate may call OpenAI through DungeonMindServer",
            ],
        )
        return _emit_result(result, allow_error=args.allow_error)

    provider: StatBlockGeneratorProvider | None = None
    try:
        provider = _build_provider(args.provider)
        service = StatblockLifecycleService(provider)
        result = service.execute(_request_from_args(args))
    except StatBlockGeneratorClientConfigError as exc:
        result = StatblockLifecycleCommandResult(
            command_type=_command_type_for_subcommand(args.command),
            status="error",
            error=ContractError(code="provider_config_error", message=str(exc)),
        )
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()

    return _emit_result(result, allow_error=args.allow_error)


def _build_provider(provider_name: str) -> StatBlockGeneratorProvider:
    if provider_name == "http":
        return DungeonMindServerStatBlockGeneratorClient()
    return MockStatBlockGeneratorProvider()


def _request_from_args(args: argparse.Namespace) -> StatblockLifecycleCommandRequest:
    command_type = _command_type_for_subcommand(args.command)
    payload: dict[str, Any] = {}
    if args.command == "generate-fixture":
        payload = _load_fixture("generate_draft_request.fixture.json")
    elif args.command == "render-fixture":
        payload = _load_fixture("render_draft_request.fixture.json")
    return StatblockLifecycleCommandRequest(
        command_type=command_type,
        payload=payload,
        requested_by=args.requested_by,
    )


def _command_type_for_subcommand(subcommand: str) -> str:
    if subcommand == "health":
        return STATBLOCK_GENERATOR_HEALTH
    if subcommand == "generate-fixture":
        return STATBLOCK_DRAFT_GENERATE
    if subcommand == "render-fixture":
        return STATBLOCK_DRAFT_RENDER
    return subcommand


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _emit_result(result: StatblockLifecycleCommandResult, *, allow_error: bool) -> int:
    print(result.model_dump_json(indent=2, exclude_none=True))
    if result.status in {"error", "unsupported"} and not allow_error:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
