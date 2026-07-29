"""File-based CLI for temporal shadow preview (TL01).

Reads one candidate GraphContribution and one TemporalAnnotationOverlayV1,
writes one TemporalShadowPreviewV1. Never touches graph runtime stores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.temporal_shadow import (
    TemporalShadowBuildError,
    build_temporal_shadow_preview,
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TemporalShadowBuildError(
            f"Input file not found: {path}",
            code="invalid_base_contribution",
            diagnostics=[str(exc)],
        ) from exc
    except json.JSONDecodeError as exc:
        raise TemporalShadowBuildError(
            f"Input JSON is malformed: {path}",
            code="invalid_base_contribution",
            diagnostics=[str(exc)],
        ) from exc
    if not isinstance(payload, dict):
        raise TemporalShadowBuildError(
            f"Input JSON root must be an object: {path}",
            code="invalid_base_contribution",
        )
    return payload


def _print_error(exc: TemporalShadowBuildError) -> None:
    lines = [
        f"code={exc.code}",
        f"message={exc}",
    ]
    if exc.affected_assertion_id is not None:
        lines.append(f"affected_assertion_id={exc.affected_assertion_id}")
    for item in exc.diagnostics:
        if item != str(exc):
            lines.append(f"diagnostic={item}")
    print("\n".join(lines), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m graph_memory.temporal_shadow_cli",
        description=(
            "Build a non-authoritative TemporalShadowPreviewV1 from a candidate "
            "GraphContribution and TemporalAnnotationOverlayV1."
        ),
    )
    parser.add_argument(
        "--contribution",
        required=True,
        type=Path,
        help="Path to candidate-only GraphContribution JSON",
    )
    parser.add_argument(
        "--overlay",
        required=True,
        type=Path,
        help="Path to TemporalAnnotationOverlayV1 JSON",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write TemporalShadowPreviewV1 JSON",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file",
    )
    args = parser.parse_args(argv)

    try:
        contribution_payload = _load_json(args.contribution)
        overlay_payload = _load_json(args.overlay)
        try:
            contribution = GraphContribution.model_validate(contribution_payload)
        except Exception as exc:  # noqa: BLE001 - surface as typed build error
            raise TemporalShadowBuildError(
                f"Invalid base contribution: {exc}",
                code="invalid_base_contribution",
                diagnostics=[str(exc)],
            ) from exc

        preview = build_temporal_shadow_preview(contribution, overlay_payload)
    except TemporalShadowBuildError as exc:
        _print_error(exc)
        return 1

    output_path: Path = args.output
    if output_path.exists() and not args.overwrite:
        print(
            "code=output_exists\n"
            f"message=Output path already exists: {output_path}\n"
            "diagnostic=pass --overwrite to replace",
            file=sys.stderr,
        )
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(preview.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    if preview.verdict == "partial":
        print(
            f"warning=partial preview: skipped_count={preview.summary.skipped_count}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
