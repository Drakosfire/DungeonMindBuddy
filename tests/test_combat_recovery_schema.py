"""The lazy client recovery validator follows current owning contract shapes."""
import json
from pathlib import Path
from scripts.generate_combat_recovery_schema import build_schema


def test_generated_combat_recovery_schema_matches_owners():
    schema = build_schema()
    path = Path(__file__).parents[1] / "apps/live-control-ui/src/combat/combatRecoverySchema.json"
    assert json.loads(path.read_text()) == schema
    assert "title" in schema["$defs"]["CombatEncounterDraft"]["properties"]
    assert "conditions" in schema["$defs"]["CombatEntity"]["required"]
    assert schema["$defs"]["CombatMechanicsSnapshot"]["properties"]["resource"] == {"$ref": "#/$defs/ExactRevisionResourceV1"}
