from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cli import DungeonBuddyCLI
from src.store import FactStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_store_canon_decisions_round_trip_and_projection(tmp_path: Path) -> None:
    root = _repo_root()
    evidence = json.loads(
        (root / "evals/canon_layering/scenarios/02_campaign_override/input/evidence_units.json").read_text(
            encoding="utf-8"
        )
    )
    facts = json.loads(
        (root / "evals/canon_layering/scenarios/02_campaign_override/input/facts.json").read_text(
            encoding="utf-8"
        )
    )
    decisions = json.loads(
        (
            root / "evals/canon_layering/scenarios/05_campaign_scoped_decision/input/canon_decisions.json"
        ).read_text(encoding="utf-8")
    )

    store_dir = tmp_path / "store"
    store = FactStore(store_dir)
    store.add_evidence_units(evidence)
    store.add_facts(facts)
    store.save()

    without = store.project("campaign_2")
    mental = without["entities"]["ent_lysandra_ironveil"]["attributes"]["mental_state"]
    assert mental["selected_fact_id"] == "fact_campaign_mental_020"

    store.add_canon_decisions(decisions)
    store.save()

    reloaded = FactStore(store_dir)
    reloaded.load()
    assert len(reloaded.canon_decisions) == 1

    with_decision = reloaded.project("campaign_2")
    mental2 = with_decision["entities"]["ent_lysandra_ironveil"]["attributes"]["mental_state"]
    assert mental2["selected_fact_id"] == "fact_world_mental_001"


def test_cli_canon_decision_add_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    evidence = json.loads(
        (root / "evals/canon_layering/scenarios/02_campaign_override/input/evidence_units.json").read_text(
            encoding="utf-8"
        )
    )
    facts = json.loads(
        (root / "evals/canon_layering/scenarios/02_campaign_override/input/facts.json").read_text(
            encoding="utf-8"
        )
    )
    decisions = json.loads(
        (
            root / "evals/canon_layering/scenarios/05_campaign_scoped_decision/input/canon_decisions.json"
        ).read_text(encoding="utf-8")
    )

    store_dir = tmp_path / "cli_store"
    store = FactStore(store_dir)
    store.add_evidence_units(evidence)
    store.add_facts(facts)
    store.save()

    dec_path = tmp_path / "decisions.json"
    dec_path.write_text(json.dumps(decisions), encoding="utf-8")

    monkeypatch.setattr("src.cli._load_env", lambda: None)
    cli = DungeonBuddyCLI(store_dir=store_dir, verbose=False)
    cli.handle_line(f'canon-decision add "{dec_path}"')

    again = FactStore(store_dir)
    again.load()
    assert len(again.canon_decisions) == 1
    proj = again.project("campaign_2")
    picked = proj["entities"]["ent_lysandra_ironveil"]["attributes"]["mental_state"]["selected_fact_id"]
    assert picked == "fact_world_mental_001"
