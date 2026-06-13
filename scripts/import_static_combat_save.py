#!/usr/bin/env python3
"""Bridge the static command-board combat save into the live-control surface.

Reads static command-board combat saves (``mireward_combat_state_v1`` or legacy
``mireward_north_reach_gate_combat_state_v1``) exported from the Mireward prep UI and writes it as a named live save slot
(``<session-dir>/combat/saves/<save-id>.json``) in the
``dmb_combat_encounter_state_v1`` schema. Optionally loads it straight into the
session's ``current_combat.json`` (preserving any prior state via a preload
backup).

Examples:
    uv run python scripts/import_static_combat_save.py
    uv run python scripts/import_static_combat_save.py --load
    uv run python scripts/import_static_combat_save.py \
        --static evals/c2_live_prep/mireward-prep/saves/combat/longmont-c2__session_22__north_reach_gate__combat_state_v1.json \
        --session-dir evals/c2_live_prep/live/session_23 \
        --save-id mireward-north-reach-gate --load
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.live_control_server.services.combat_saves import (  # noqa: E402
    convert_static_mireward_save,
    load_combat_save,
    write_combat_save,
)

DEFAULT_STATIC = (
    REPO_ROOT
    / "evals/c2_live_prep/mireward-prep/saves/combat/"
    "longmont-c2__session_22__north_reach_gate__combat_state_v1.json"
)
DEFAULT_SESSION_DIR = REPO_ROOT / "evals/c2_live_prep/live/session_23"
DEFAULT_SAVE_ID = "mireward-north-reach-gate"


def _resolve_packet(session_dir: Path, campaign_id: str | None, session: int | None) -> dict:
    if campaign_id and session is not None:
        return {"campaign_id": campaign_id, "session": session}
    packet_path = session_dir / "live_packet.json"
    if packet_path.is_file():
        data = json.loads(packet_path.read_text(encoding="utf-8"))
        return {
            "campaign_id": campaign_id or str(data.get("campaign_id", "longmont-c2")),
            "session": session if session is not None else int(data.get("session", 0)),
        }
    raise SystemExit(
        f"could not resolve packet metadata; pass --campaign-id/--session "
        f"(no live_packet.json under {session_dir})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR)
    parser.add_argument("--save-id", default=DEFAULT_SAVE_ID)
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--session", type=int, default=None)
    parser.add_argument(
        "--load",
        action="store_true",
        help="Also load the imported save into current_combat.json (preserves prior state).",
    )
    args = parser.parse_args()

    if not args.static.is_file():
        raise SystemExit(f"static save not found: {args.static}")

    static = json.loads(args.static.read_text(encoding="utf-8"))
    packet = _resolve_packet(args.session_dir, args.campaign_id, args.session)
    encounter = convert_static_mireward_save(static=static, packet=packet)

    target = write_combat_save(base=args.session_dir, save_id=args.save_id, encounter=encounter)
    print(f"wrote save slot: {target.relative_to(REPO_ROOT)}")
    print(
        f"  entities={len(encounter.entities)} round={encounter.round} "
        f"active={encounter.active_turn_entity_id} round_start={encounter.round_start_entity_id}"
    )

    if args.load:
        response = load_combat_save(
            base=args.session_dir, packet=packet, save_id=args.save_id
        )
        for line in response.diagnostics:
            print(f"  {line}")
        print(f"  current_combat now has {len(response.encounter.entities)} entities")


if __name__ == "__main__":
    main()
