import {createPortal} from "react-dom";
import {useEffect,useState,useSyncExternalStore} from 'react';
import {openSavedConversationVariant,saveConversationVariantPortrait,type VariantPortraitSave} from '../api/conversationDraftApi';
import type {MechanicsLocatorV1} from '../api/types';
import {getThreatDraft,openSavedMechanicsVersion} from '../api/liveApi';
import {AppChrome} from '../chrome/AppChrome';
import {getAppLocationSnapshot,navigatePrimaryAppHref,subscribeAppLocation} from '../chrome/appNavigation';
import {DeferredMediaImageWizard} from '../media/DeferredMediaImageWizard';
import {SavedMediaImage} from '../media/SavedMediaImage';
import {MEDIA_ASSET_ID} from '../media/mediaReferences';
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

function VariantPortraitControls({target, base, name}: {
 target: SavedConversationVariantTarget; base: MechanicsLocatorV1; name: string;
}) {
 const key = 'buddy:variant-portrait:' + JSON.stringify([target.worldId, target.conversationId, target.turnId, target.reviewId]);
 const [studio, setStudio] = useState(false);
 const [busy, setBusy] = useState(false);
 const [notice, setNotice] = useState('');
 const [asset, setAsset] = useState<string>();
 const [pending, setPending] = useState<VariantPortraitSave>();
 const [recoveryReady, setRecoveryReady] = useState(false);
 useEffect(() => {
  try {
   const raw = window.localStorage.getItem(key);
   if (raw) {
    const command: VariantPortraitSave = JSON.parse(raw);
    if (!MEDIA_ASSET_ID.test(command.operation_id) || !MEDIA_ASSET_ID.test(command.portrait_asset_id)
        || command.base.revision_id !== base.revision_id) {
     throw new Error('The retained portrait Save belongs to a different source.');
    }
    setPending(command);
   }
   setRecoveryReady(true);
  } catch {
   setNotice('Could not read the retained portrait Save. This page cannot start another Save.');
  }
 }, [key, base.revision_id]);

 async function save() {
  if (busy || !recoveryReady || (!pending && !asset)) return;
  try {
   const command = pending ?? {operation_id: crypto.randomUUID(), base, portrait_asset_id: asset!};
   window.localStorage.setItem(key, JSON.stringify(command));
   setPending(command);
   setBusy(true);
   setNotice('');
   const result = await saveConversationVariantPortrait(target, target.reviewId, command);
   if (result.statblock_id !== base.statblock_id || result.revision_id === base.revision_id
       || result.definition_digest !== base.definition_digest) {
    throw new Error('The saved portrait revision could not be verified. Retry the same Save.');
   }
   const reopened = await openSavedConversationVariant(target, target.reviewId, command.operation_id);
   if (reopened.locator.statblock_id !== result.statblock_id
       || reopened.locator.revision_id !== result.revision_id
       || reopened.locator.definition_digest !== result.definition_digest) {
    throw new Error('The portrait revision could not be reopened. Retry the same Save.');
   }
   const href = savedConversationVariantHref({...target, portraitOperationId: command.operation_id});
   // A different tab may have retained its own operation while this one was saving.
   if (window.localStorage.getItem(key) === JSON.stringify(command)) window.localStorage.removeItem(key);
   navigatePrimaryAppHref(href);
  } catch (error) {
   setNotice(error instanceof Error ? error.message : 'Could not save the portrait. Retry the same Save.');
  } finally {
   setBusy(false);
  }
 }

 return <section aria-label="Variant portrait">
  <button type="button" disabled={!recoveryReady || !!pending || studio} onClick={() => setStudio(true)}>Generate or choose portrait</button>
  {studio && <DeferredMediaImageWizard selectionOnly requireSaved chooseLabel="Use as portrait"
   initialPrompt={`Portrait of ${name}.`} onClose={() => setStudio(false)}
   onChoose={(image, _result, placement) => {
    if (placement.signal.aborted) return;
    if (!MEDIA_ASSET_ID.test(image.asset_id)) throw new Error('Choose an image with a saved reference.');
    setAsset(image.asset_id);
    setStudio(false);
   }}/>}
  {(pending || asset) && <>
   <SavedMediaImage assetId={pending?.portrait_asset_id ?? asset!} alt="Selected portrait"/>
   <button type="button" disabled={busy || studio} onClick={() => void save()}>
    {busy ? 'Saving portrait…' : pending ? 'Retry portrait Save' : 'Save new portrait version'}
   </button>
  </>}
  {notice && <p role="alert">{notice}</p>}
 </section>;
}

function SavedConversationVariantView({target}: {target: SavedConversationVariantTarget}) {
 const [saved, setSaved] = useState<Awaited<ReturnType<typeof openSavedConversationVariant>>>();
 const [error, setError] = useState("");
 useEffect(() => {
  let active = true;
  void openSavedConversationVariant(target, target.reviewId, target.portraitOperationId).then(result => {
   if (active) setSaved(result);
  }).catch(failure => {
   if (active) setError(failure instanceof Error ? failure.message : "The saved variant is unavailable.");
  });
  return () => { active = false; };
 }, [target.worldId, target.conversationId, target.turnId, target.reviewId, target.portraitOperationId]);
 return <main className="saved-statblock-page" aria-label="Saved conversation variant">
  {error ? <p role="alert">{error}</p> : saved
   ? <>
      {!target.portraitOperationId && <>
       <a href={savedConversationVariantHref(target).replace(/^\/statblock\?/, '/combat?')}>Open in Combat</a>
       <VariantPortraitControls target={target} base={saved.locator} name={saved.revision.definition.identity.name}/>
      </>}
      <StatblockRenderer revision={saved.revision} mode="full" chrome="campaign"/>
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
