type CombatEncounterTarget = {worldId: string; encounterId: string};

const WORLD_ID = /^[a-z][a-z0-9_-]{0,62}$/;
const ENCOUNTER_ID = /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i;

export function combatEncounterHref({worldId, encounterId}: CombatEncounterTarget): string {
  return '/combat?' + new URLSearchParams({world: worldId, encounter: encounterId});
}

export function readCombatEncounterTarget(location: string): CombatEncounterTarget | 'invalid' | null {
  const params = new URL(location, 'http://localhost').searchParams;
  if (!params.has('encounter')) return null;
  const worlds = params.getAll('world');
  const encounters = params.getAll('encounter');
  const [worldId = ''] = worlds;
  const [encounterId = ''] = encounters;
  if (worlds.length !== 1 || encounters.length !== 1 || !WORLD_ID.test(worldId) || !ENCOUNTER_ID.test(encounterId)) {
    return 'invalid';
  }
  return {worldId, encounterId: encounterId.toLowerCase()};
}
