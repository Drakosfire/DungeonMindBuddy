import {useEffect,useState,useSyncExternalStore} from 'react';
import {getThreatDraft,openSavedMechanicsVersion} from '../api/liveApi';
import {AppChrome} from '../chrome/AppChrome';
import {getAppLocationSnapshot,subscribeAppLocation} from '../chrome/appNavigation';
import {useSelectedWorld} from '../selectedWorld/SelectedWorldContext';
import type {OpenSavedMechanicsVersion} from './revision/savedMechanicsRevisionTypes';
import {StatblockRenderer} from './render/StatblockRenderer';
import {readSavedStatblockTarget,type SavedStatblockTarget} from './savedStatblockLocation';
import './StatblockPage.css';
import type {ThreatDraftV2} from '../api/types';
import {NativeThreatCreationPanel} from './NativeThreatCreationPanel';
import {WorldMechanicsAssociationPanel} from './WorldMechanicsAssociationPanel';
import {SavedStatblockButton} from './SavedStatblockSession';

function SavedCreatureReview({target,packet}:{target:SavedStatblockTarget;packet:OpenSavedMechanicsVersion}) {
 const [draft,setDraft]=useState<ThreatDraftV2>();
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 async function loadDraft() {
  setBusy(true);setError('');
  try {
   const result=await getThreatDraft(target.draftId);
   if(result.schema!=='dmb_threat_draft_v2'||result.world_id!==target.worldId
    ||result.draft_id!==target.draftId||result.workflow_state!=='mechanics_saved'
    ||packet.world_id!==target.worldId||packet.draft_id!==target.draftId
    ||packet.locator.revision_id!==target.revisionId) {
    throw new Error('The saved statblock and creature draft no longer match.');
   }
   setDraft(result);
  } catch(error) {
   setError(error instanceof Error?error.message:'The creature draft is unavailable.');
  } finally {
   setBusy(false);
  }
 }
 return draft?<NativeThreatCreationPanel draft={draft} mechanics={packet.locator}/>:<>
  <button type="button" disabled={busy} onClick={()=>void loadDraft()}>Open creature review</button>
  {error&&<p role="alert">{error}</p>}
 </>;
}

/** One exact native read. It never consults the Workbench's selected-version hint. */
export function SavedStatblockFullView({target}:{target:SavedStatblockTarget}) {
 const key=JSON.stringify([target.worldId,target.draftId,target.revisionId]);
 const [attempt,setAttempt]=useState(0);
 const [state,setState]=useState<{key:string;packet:OpenSavedMechanicsVersion|null;error:string|null}|null>(null);
 useEffect(()=>{
  let active=true;setState({key,packet:null,error:null});
  void openSavedMechanicsVersion(target.draftId,target.worldId,target.revisionId).then(packet=>{
   if(!active)return;
   setState({key,packet,error:null});
  }).catch(error=>{if(active)setState({key,packet:null,error:error instanceof Error?error.message:'The saved statblock is unavailable.'});});
  return()=>{active=false;};
 },[key,attempt]);
 const current=state?.key===key?state:null;
 return <main className="saved-statblock-page" aria-label="Full saved statblock">
  {current?.error?<><p role="alert">{current.error}</p><button type="button" onClick={()=>setAttempt(value=>value+1)}>Retry statblock</button></>
   :current?.packet?<><SavedStatblockButton {...target} label="Edit this version"/><SavedCreatureReview key={key} target={target} packet={current.packet}/><WorldMechanicsAssociationPanel worldId={target.worldId} draftId={target.draftId} locator={current.packet.locator}/><StatblockRenderer revision={current.packet.resource} mode="full" chrome="campaign"/></>
   :<p role="status">Opening saved statblock…</p>}
 </main>;
}

export function StatblockPage() {
 const snapshot=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot,getAppLocationSnapshot);
 const target=readSavedStatblockTarget(snapshot),world=useSelectedWorld();
 return <AppChrome activeRoute="statblock">
  {target&&world.kind==='managed'&&world.worldId===target.worldId?<SavedStatblockFullView target={target}/>
   :<main className="saved-statblock-page"><h1>Statblock unavailable</h1><p role="alert">Open a saved statblock link with its World, creature and revision.</p></main>}
 </AppChrome>;
}
