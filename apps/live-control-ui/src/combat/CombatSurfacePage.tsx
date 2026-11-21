import {getAppLocationSnapshot,subscribeAppLocation} from '../chrome/appNavigation';
import {readSavedConversationVariantTarget} from '../statblocks/savedStatblockLocation';
import {useMemo,useSyncExternalStore} from 'react';
import './CombatSurfacePage.css';
import {AppChrome} from '../chrome/AppChrome';
import {usePublishSurfaceInteraction} from '../agentInteraction/usePublishSurfaceInteraction';
import {useSelectedWorld} from '../selectedWorld/SelectedWorldContext';
import {CombatRosterModule} from '../surface/modules/CombatRosterModule';
import {buildSurfaceInteractionIdentity} from '../surfaceInteraction/surfaceIdentity';
import type {SurfaceInteractionPublication} from '../surfaceInteraction/types';
import {readCombatEncounterTarget} from './combatEncounterLocation';

/** Product host for the same native module used by configurable surfaces. */
export function CombatSurfacePage(){
  const world=useSelectedWorld(),worldId=world.kind==='managed'?world.worldId:null;
  const location=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot,getAppLocationSnapshot);
  const variant=readSavedConversationVariantTarget(location);
  const target=readCombatEncounterTarget(location);
  const encounterId=target && target!=='invalid' && target.worldId===worldId ? target.encounterId : null;
  const publication=useMemo<SurfaceInteractionPublication>(()=>({surfaceId:'combat',label:'Combat',
    identity:buildSurfaceInteractionIdentity({surfaceId:'combat',instanceParts:encounterId?[worldId,encounterId]:[worldId]}),
    canvas:null,agentContext:null,tools:[],editCommands:[],projections:[],projectionBindings:[]}),[worldId,encounterId]);
  usePublishSurfaceInteraction(publication);
  const encounterListHref=worldId ? '/combat?'+new URLSearchParams({world:worldId}) : '/combat';
  const admittedVariant=variant?.worldId===worldId?variant:undefined;
  return <AppChrome activeRoute="combat"><main className="native-combat-surface" aria-label="Combat encounters">
    {target && !encounterId && <a href={encounterListHref}>All encounters</a>}
    {target === 'invalid' ? <p role="alert">This encounter link is invalid.</p>
      : target && worldId && encounterId ? <CombatRosterModule
          scope={{worldId,encounterId,label:'Saved encounter'}} variant={admittedVariant} encounterListHref={encounterListHref}/>
      : target ? <p role="status">Open this link in its World to view the encounter.</p>
      : <CombatRosterModule variant={admittedVariant}/>}
  </main></AppChrome>;
}
