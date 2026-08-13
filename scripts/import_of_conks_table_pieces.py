#!/usr/bin/env python3
"""Import Of Conks table-ready Plan pieces from local manufactured gold.

Copies threat / item / table cards into Plan workspace documents and rewrites
the Hempholm run packet so every navigable mention uses graph-native
``[label](dmb-node:…)`` chips. No heading-fragment or ``#dmb-ref`` links.
Does not commit module prose. Does not extract.

Example::

  uv run python scripts/import_of_conks_table_pieces.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document,
    list_workspace_documents,
)

CAMPAIGN_ID = "of-conks-cons"
DEFAULT_GOLD_DIR = Path.home() / "Downloads" / "of-conks-cons-v21-gold"
PACKET_TITLE = "Hempholm — run packet"
SOURCE_DOC_TITLE = "Of Conks & Cons v2.1"

SATELLITES: list[tuple[str, Path]] = [
    ("Grotesque Tree — mechanics", Path("threats/grotesque-tree.md")),
    ("Guardian — mechanics", Path("threats/guardian.md")),
    ("Caretakers — tactics (twig blight MM 32)", Path("threats/caretakers.md")),
    ("Maglubiyet’s Statue — item", Path("items/maglubiyets-statue.md")),
    ("Belly’s Mouthwash — item", Path("items/bellys-mouthwash.md")),
]


def _upsert_plan_markdown(*, title: str, markdown: str, target_session: int | None = 1) -> str:
    existing = [
        r
        for r in list_workspace_documents(
            ROOT,
            campaign_id=CAMPAIGN_ID,
            kind="plan",
            status="active",
        )
        if r.title == title
    ]
    if existing:
        record = get_workspace_document(ROOT, existing[0].document_id)
        action = "Updated"
    else:
        record = create_workspace_document(
            ROOT,
            title=title,
            campaign_id=CAMPAIGN_ID,
            kind="plan",
            target_session=target_session,
        )
        action = "Created"

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
        raise RuntimeError(f"prepare failed for {title!r}: {prepared}")
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
    print(f"{action} plan doc {record.document_id[:8]}… title={title!r}")
    return record.document_id


def _extract_appendix_c(prepared: str) -> str:
    match = re.search(
        r"# Appendix C: Tables\n(?P<body>.*?)(?:\n---\n|\n# Credits)",
        prepared,
        flags=re.S,
    )
    if not match:
        raise RuntimeError("Appendix C tables not found in prepared source")
    body = match.group("body").strip()
    return (
        "---\n"
        "title: Hempholm names\n"
        "kind: roll-table\n"
        "source_module: Of Conks & Cons v2.1\n"
        "source_heading: Appendix C: Tables\n"
        "authority: playable_layer\n"
        "---\n\n"
        "# Hempholm names\n\n"
        "Improvisation tool only. Do not promote rolled names into graph actors "
        "unless the table names that villager in play.\n\n"
        "Open from the **Roll** tab (`/roll`) as **Hempholm names — roll table**.\n\n"
        f"{body}\n"
    )


def build_rewritten_packet() -> str:
    """Lean table hub: play beats + graph chips. Mechanics expand from chips."""
    return """---
title: Hempholm — run packet
document_class: planning
source_module: Of Conks & Cons v2.1
authority: playable_layer
canon_state: not_campaign_canon
world: of-conks-cons
campaign: of-conks-cons
---

# Hempholm

> [!GM-NOTE]
> Pick **one** hook. Do not run Korden, the stolen guild package, and the hill arrival as simultaneous canon.

## At-table intent

A hemp village has a two-story attacking tree in the Jove garden. The tree is the visible problem. It is not the whole problem.

## Opening frame

> [!READ-ALOUD]
> Overlooking the village from a small hill, you cannot help but notice a grotesque tree growing in one of the gardens which towers above all other trees and buildings in the area. When a bird tries to perch on one of its branches, the tree lashes out and turns the bird into minced meat.

> [!GM-NOTE]
> If you used a different hook, skip this boxed text and start in [The Shacks](dmb-node:location:the-shacks) or at [the Jove home](dmb-node:location:jove-home).

## Clocks

> [!WARNING]
> Advance a clock when the table stalls or leaves the tree alone.

### Tree growth

- 0: Two stories; garden only.
- 1: 30 feet; smashes the Jove home and two neighbors.
- 2: Fire risk if they burn it (d20 even = houses catch).
- 3: If they leave town: later news of a 300-foot tree on the Uldoon Trail.

### False victory

- After the **surface** tree dies: celebration in [The Shacks](dmb-node:location:the-shacks) **or** firefighting.
- Some hours later: [Caretakers](dmb-node:threat:caretakers).

## Combat handoff

Click a threat chip for the sheet, then Add to combat.

### Expected — surface tree

[Grotesque Tree](dmb-node:threat:grotesque-tree)

> [!WARNING]
> Site tactics (Area 5): attacks anyone within 30 feet; retaliates against ranged; nearest target; ceases when not threatened. Can Snare (bonus, DC 13) and Sling grappled targets.

### Unexpected — caretakers (CR-U14)

[Caretakers](dmb-node:threat:caretakers)

- **Count:** 20 total, roam in **groups of 5** (twig blight / MM 32).
- **Timing:** hours after the surface tree dies (celebration or firefighting).
- **Behavior:** attack villagers and structures; flee after ~15 dead or return underground after a few hours; **afraid of fire**.
- **Treasure:** 1 gp quality root-wood per corpse (woodcarver’s / carpenter’s tools).

### Descent — Marrow

[Guardian](dmb-node:threat:guardian) + **2** caretakers

> [!RULES]
> Safe resin 200 gp. Greedy +200 gp → collapse risk → DC 10 Athletics or the village falls in.

## Area 1: The Shacks

[Nar Granitetooth](dmb-node:npc:nar-granitetooth) · Bill the Belly (prose only) · [Hempholm](dmb-node:location:hempholm)

> [!READ-ALOUD]
> You stand in front of the village’s largest building when a peasant with an oddly noggin-shaped nose flies through the door out into the cold. Following this display, you hear the sweet sound of a cursing dwarf who demands more ale.

> [!RULES]
> Nar: DC 20 Charisma (Persuasion) + Religion proficiency to pull her back toward Sharindlar. Later, wounded villagers: DC 15 Persuasion, or DC 10 Religion if they appeal to her faith. She helps freely if already won over.

> [!GM-NOTE]
> Sharindlar: dwarven goddess of healing, fertility, life, mercy. Priests: Thalornor. Symbol: burning needle.

## Area 2: The Store

[Morwin Blackwell](dmb-node:npc:morwin-blackwell) · [Morwin's](dmb-node:location:morwins-store)

> [!READ-ALOUD]
> The store’s interior is dusty and untidy much like its proprietor. Bundles of hair shoot out of the old man’s nose and ears and he appears to be sleeping behind the counter.

Gear ≤ 10 gp, farm tools, household hemp. He hates Saladin. Optional: gem-cutting job (two of ten stones are tourmalines).

## Area 3: Saladin’s Wagon

[Saladin](dmb-node:npc:saladin) · [Saladin's Mobile Emporium](dmb-node:location:saladins-wagon) · [Maglubiyet’s Statue](dmb-node:item:maglubiyets-statue)

> [!READ-ALOUD]
> A wagon stands smack in the middle of Hempholm’s village square… considerably larger on the inside than on the outside.

> [!GM-NOTE]
> Optional recurring NPC. Sold out except the statue (500 gp). Bag of holding, ~10,000 gp. Unbidden thoughts are GM color, not a puzzle.

## Area 4: The Jove's Home

[Mark Jove](dmb-node:npc:mark-jove) · [Torbin Jove](dmb-node:npc:torbin-jove) · [The Jove's Home](dmb-node:location:jove-home)

> [!READ-ALOUD]
> The menacing tree stands right in the center of this house’s garden.

> [!READ-ALOUD]
> **Mark Jove.** …My stupid boy brought this bewitched 'tato home…

> [!READ-ALOUD]
> **Torbin Jove.** …this strange 'tato will be enough to feed my whole family…

## Area 5: The Grotesque Tree

[Grotesque Tree](dmb-node:threat:grotesque-tree) · [The Grotesque Tree (garden)](dmb-node:location:grotesque-tree-site)

> [!READ-ALOUD]
> The further you approach the tree, the stranger it appears. The tree’s bark looks as tough as any armor you’ve seen and the branches are covered in thick thorns.

> [!RULES]
> Passive Perception 15: metal leaves. Passive Arcana 12: aura. DC 17 Arcana: roots under the village.

> [!WARNING]
> Attacks anyone within 30 feet; retaliates at range; nearest target; stops when the threat leaves. Fire can save the village or burn it.

Treasure if they search: 100 gp [precious metal leaves](dmb-node:item:metal-leaves).

## If they wait

Growth spurt. Villagers with axes get mauled. Carry them to Nar.

## If they win (surface)

Celebration in the Shacks. Children, ale.

> [!RULES]
> Drinking: DC 10 Con / hour or poisoned.

> [!WARNING]
> Do not telegraph the second fight. See **Combat handoff → Unexpected — caretakers**.

## Descent / Marrow

> [!READ-ALOUD]
> The air down in these tunnels is dank… hollow roots are warm… more like stone or metal than wood.

[Hollow root corridors](dmb-node:location:root-corridors) · [The Marrow](dmb-node:location:the-marrow) · [Guardian](dmb-node:threat:guardian) + 2 caretakers.

## The child

GM-only until they cut the sack. Metal-eater, blank slate. Village wants it gone. Nar or Saladin will take it. [Paelias Sian](dmb-node:npc:paelias-sian) ([Baldur’s Gate mages’ guild](dmb-node:faction:baldurs-gate-mages-guild)) comes later to erase evidence. [Child in the helix](dmb-node:npc:helix-child).

> [!WARNING]
> Do not read the child’s nature as boxed text at the garden.

## Background pins (optional open)

[Lord Fiddlestick](dmb-node:npc:lord-fiddlestick) · [the conk](dmb-node:item:the-conk) · [The Shacks](dmb-node:location:the-shacks)
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold-dir",
        type=Path,
        default=DEFAULT_GOLD_DIR,
        help="Local manufactured gold package",
    )
    args = parser.parse_args()
    gold_dir = args.gold_dir.expanduser().resolve()
    if not gold_dir.is_dir():
        raise SystemExit(f"gold dir missing: {gold_dir}")

    for title, rel in SATELLITES:
        path = gold_dir / rel
        if not path.is_file():
            raise SystemExit(f"missing satellite: {path}")
        _upsert_plan_markdown(title=title, markdown=path.read_text(encoding="utf-8"))

    prepared = gold_dir / "specimens" / "02-prepared.md"
    if not prepared.is_file():
        raise SystemExit(f"missing prepared source: {prepared}")
    names_md = _extract_appendix_c(prepared.read_text(encoding="utf-8"))
    _upsert_plan_markdown(title="Hempholm names — roll table", markdown=names_md)

    packet_id = _upsert_plan_markdown(
        title=PACKET_TITLE,
        markdown=build_rewritten_packet(),
    )
    print(f"Done. Packet document_id={packet_id}")
    print(f"Plan URL: http://127.0.0.1:5173/plan?campaign={CAMPAIGN_ID}&documentId={packet_id}")
    print(f"Source remains Build doc title={SOURCE_DOC_TITLE!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
