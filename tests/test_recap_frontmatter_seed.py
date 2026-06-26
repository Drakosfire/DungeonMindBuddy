from __future__ import annotations

import json
from pathlib import Path

from src.agent.recap_frontmatter_seed import build_frontmatter_seed
from src.session_memory.breadcrumb_normalize import (
    extract_frontmatter_route_allowlist,
    extract_meta_from_frontmatter,
)
from src.session_memory.breadcrumb_smoke import parse_frontmatter_and_body


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_frontmatter_seed_uses_known_vocab_and_validates_parser_contract(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    campaign = corpus / "Longmont Campaign/Campaign 2"
    _write(
        campaign / "Session Recaps/_normalized/Session 23 - Gate Battle.md",
        """---
title: "Session 23 - Gate Battle"
campaign_id: longmont-c2
session: 23
---
# Session 23 - Gate Battle

Caelynn and Bonogo meet Orric Tane at Mireward. The party holds the gate.
""",
    )
    _write(
        campaign / "PCs/caelynn/README.md",
        """---
title: "Caelynn — Campaign 2 (PC hub)"
subject_class: pc
subject_doc_kind: hub_index
---
# Caelynn
""",
    )
    _write(
        campaign / "PCs/bonogo/README.md",
        """---
title: "Bonogo — Campaign 2 (PC hub)"
subject_class: pc
subject_doc_kind: hub_index
---
# Bonogo
""",
    )
    (campaign / "_party_registry.json").write_text(
        json.dumps(
            {
                "schema": "party_registry_v1",
                "campaign_id": "longmont-c2",
                "session_pc_rosters": {"20": ["caelynn", "bonogo"]},
            }
        ),
        encoding="utf-8",
    )
    (campaign / "_npc_registry.json").write_text(
        json.dumps(
            [
                {
                    "slug": "orric_tane",
                    "display_name": "Orric Tane",
                    "aliases": ["Orik Tane"],
                    "hub_path": None,
                    "setting_hub_path": "Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/",
                },
                {
                    "slug": "unused_npc",
                    "display_name": "Unused NPC",
                    "aliases": [],
                    "hub_path": "Longmont Campaign/Campaign 2/NPCs/unused_npc/",
                    "setting_hub_path": None,
                },
            ]
        ),
        encoding="utf-8",
    )
    _write(
        corpus / "Elderwyld/Cities and Towns/Mireward/README.md",
        """---
title: "Mireward"
subject_class: location
subject_doc_kind: hub_index
---
# Mireward
""",
    )

    seed = build_frontmatter_seed(corpus_root=corpus, campaign_number=2, session=23)
    frontmatter, body = parse_frontmatter_and_body(seed)

    assert frontmatter is not None
    assert body.strip() == "### Session 23 - Gate Battle — frontmatter seed only"
    assert extract_meta_from_frontmatter(frontmatter) == {
        "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Gate Battle.md",
        "campaign_id": "longmont-c2",
        "session_number": 23,
    }
    routes = extract_frontmatter_route_allowlist(frontmatter)
    assert "Longmont Campaign/Campaign 2/PCs/caelynn/" in routes
    assert "Longmont Campaign/Campaign 2/PCs/bonogo/" in routes
    assert "Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/" in routes
    assert "Elderwyld/Cities and Towns/Mireward/" in routes
    assert "Longmont Campaign/Campaign 2/NPCs/unused_npc/" not in routes
