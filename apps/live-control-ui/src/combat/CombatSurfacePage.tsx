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

/** Product host for the same native module used by configurable surfaces. */
export function CombatSurfacePage(){
  const world=useSelectedWorld(),worldId=world.kind==='managed'?world.worldId:null;
  const location=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot,getAppLocationSnapshot);
  const variant=readSavedConversationVariantTarget(location);
  const publication=useMemo<SurfaceInteractionPublication>(()=>({surfaceId:'combat',label:'Combat',
    identity:buildSurfaceInteractionIdentity({surfaceId:'combat',instanceParts:[worldId]}),
    canvas:null,agentContext:null,tools:[],editCommands:[],projections:[],projectionBindings:[]}),[worldId]);
  usePublishSurfaceInteraction(publication);
  return <AppChrome activeRoute="combat"><main className="native-combat-surface" aria-label="Combat encounters">
    <CombatRosterModule variant={variant?.worldId===worldId?variant:undefined}/>
  </main></AppChrome>;
}
