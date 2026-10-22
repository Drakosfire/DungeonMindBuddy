"""Generate client recovery shape checks from the two owning runtime contracts.

The client schema is render safety, not Save authority; APP/HTTP still validate
all semantic invariants and exact mechanics proofs. No provider IO occurs here.
"""
from pathlib import Path
import json
from application_state.combat_encounters.types import CombatEncounterRecord
from apps.live_control_server.integrations.dungeonmind_statblocks.models import ExactRevisionResourceV1


def build_schema():
    schema = CombatEncounterRecord.model_json_schema(by_alias=True)
    # Recovery stores complete model_dump records, not input bodies with omitted
    # defaults. The renderer's APP DTO requires these fields to be present.
    for node in [schema, *schema['$defs'].values()]:
        if 'properties' in node: node['required'] = list(node['properties'])
    resource = ExactRevisionResourceV1.model_json_schema(by_alias=True)
    assert not set(schema['$defs']) & set(resource['$defs'])
    schema['$defs'].update(resource.pop('$defs'))
    for name in ('CombatMechanicsSnapshot', 'AcceptedCombatMechanicsSnapshot'):
        schema['$defs'][name]['properties']['resource'] = {'$ref': '#/$defs/ExactRevisionResourceV1'}
    schema['$defs']['ExactRevisionResourceV1'] = resource
    annotations = {'title', 'description', 'default', 'examples', 'discriminator'}
    def compact(value):
        if isinstance(value, list): return [compact(item) for item in value]
        if not isinstance(value, dict): return value
        return {key: ({name: compact(child) for name, child in item.items()}
                      if key in {'properties', '$defs'} else compact(item))
                for key, item in value.items() if key not in annotations}
    return compact(schema)


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'apps/live-control-ui/src/combat/combatRecoverySchema.json'
    path.write_text(json.dumps(build_schema(), ensure_ascii=False, separators=(',', ':')) + '\n')
