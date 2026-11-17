import {createPortal} from "react-dom";
import {useEffect,useState,useSyncExternalStore} from 'react';
import {openSavedConversationVariant} from '../api/conversationDraftApi';
import type {StatblockRevisionResourceV1} from '../contracts/dungeonbuddy-statblocks-v1/client';
import {getThreatDraft,openSavedMechanicsVersion} from '../api/liveApi';
import {AppChrome} from '../chrome/AppChrome';
import {getAppLocationSnapshot,subscribeAppLocation} from '../chrome/appNavigation';
import {useSelectedWorld} from '../selectedWorld/SelectedWorldContext';
import type {OpenSavedMechanicsVersion} from './revision/savedMechanicsRevisionTypes';
import {StatblockRenderer} from './render/StatblockRenderer';
import {savedConversationVariantHref,readSavedConversationVariantTarget,readSavedStatblockTarget,type SavedConversationVariantTarget,type SavedStatblockTarget} from './savedStatblockLocation';
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
export function SavedStatblockFullView({target, toolbarHost}:{target:SavedStatblockTarget; toolbarHost?: HTMLElement | null}) {
 const key=JSON.stringify([target.worldId,target.draftId,target.revisionId,target.sourceReviewId]);
 const [attempt,setAttempt]=useState(0);
 const [state,setState]=useState<{key:string;packet:OpenSavedMechanicsVersion|null;error:string|null}|null>(null);
 useEffect(()=>{
  let active=true;setState({key,packet:null,error:null});
  const read = target.sourceReviewId
   ? openSavedMechanicsVersion(target.draftId,target.worldId,target.revisionId,target.sourceReviewId)
   : openSavedMechanicsVersion(target.draftId,target.worldId,target.revisionId);
  void read.then(packet=>{
   if(!active)return;
   setState({key,packet,error:null});
  }).catch(error=>{if(active)setState({key,packet:null,error:error instanceof Error?error.message:'The saved statblock is unavailable.'});});
  return()=>{active=false;};
 },[key,attempt]);
 const current=state?.key===key?state:null;
 const packet=current?.packet;
 const tools=packet&&<>
  <SavedCreatureReview key={key} target={target} packet={packet}/>
  <WorldMechanicsAssociationPanel worldId={target.worldId} draftId={target.draftId} locator={packet.locator}/>
 </>;
 const edit=packet&&<SavedStatblockButton {...target} label="Edit this version"/>;
 const buildToolbar=toolbarHost&&createPortal(
  <div className="saved-statblock-navbar">
   {edit}
   <details><summary>Creature tools</summary><div className="saved-statblock-navbar__tools">{tools}</div></details>
  </div>,toolbarHost);
 return <main className="saved-statblock-page" aria-label="Full saved statblock">
  {current?.error?<><p role="alert">{current.error}</p><button type="button" onClick={()=>setAttempt(value=>value+1)}>Retry statblock</button></>
   :packet?<>{toolbarHost===undefined?<>{edit}{tools}</>:buildToolbar}
    <StatblockRenderer revision={packet.resource} pdfPortrait={packet.pdf_portrait} mode="full" chrome="campaign"/></>
   :<p role="status">Opening saved statblock…</p>}
 </main>;
}

function SavedConversationVariantView({target}: {target: SavedConversationVariantTarget}) {
 const [revision, setRevision] = useState<StatblockRevisionResourceV1>();
 const [error, setError] = useState("");
 useEffect(() => {
  let active = true;
  void openSavedConversationVariant(target, target.reviewId).then(result => {
   if (active) setRevision(result.revision);
  }).catch(failure => {
   if (active) setError(failure instanceof Error ? failure.message : "The saved variant is unavailable.");
  });
  return () => { active = false; };
 }, [target.worldId, target.conversationId, target.turnId, target.reviewId]);
 return <main className="saved-statblock-page" aria-label="Saved conversation variant">
  {error ? <p role="alert">{error}</p> : revision
   ? <>
      <a href={savedConversationVariantHref(target).replace(/^\/statblock\?/, '/combat?')}>Open in Combat</a>
      <StatblockRenderer revision={revision} mode="full" chrome="campaign"/>
     </>
   : <p role="status">Opening saved variant…</p>}
 </main>;
}

export function StatblockPage() {
 const snapshot=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot,getAppLocationSnapshot);
 const target=readSavedStatblockTarget(snapshot),world=useSelectedWorld();
 const variant = readSavedConversationVariantTarget(snapshot);
 return <AppChrome activeRoute="statblock">
  {variant && world.kind === 'managed' && world.worldId === variant.worldId
   ? <SavedConversationVariantView key={snapshot} target={variant}/>
   : target&&world.kind==='managed' &&world.worldId===target.worldId?<SavedStatblockFullView target={target}/>
   :<main className="saved-statblock-page"><h1>Statblock unavailable</h1><p role="alert">Open a saved statblock link with its World, creature and revision.</p></main>}
 </AppChrome>;
}
