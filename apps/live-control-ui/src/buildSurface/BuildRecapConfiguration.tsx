import {lazy,Suspense} from 'react';
import type {SessionEvidenceRef} from '../playSurface/review/sessionEvidenceApi';
const SessionEvidencePicker=lazy(()=>import('../playSurface/review/SessionEvidencePicker').then(m=>({default:m.SessionEvidencePicker})));
export function BuildRecapConfiguration({documentId,worldId,campaignId,session,evidence,onCampaign,onSession,onEvidence,disabled}:{
  documentId:string;worldId:string|null;campaignId:string;session:string;evidence:SessionEvidenceRef[];
  onCampaign:(value:string)=>void;onSession:(value:string)=>void;onEvidence:(refs:SessionEvidenceRef[])=>void;disabled:boolean;
}){
  return <fieldset disabled={disabled}><legend>Recap source</legend>
    <p>The saved document is your external recap. Choose its source campaign and session; the selected World is the destination.</p>
    <label>Source campaign<input aria-label="Recap source campaign" value={campaignId} onChange={e=>onCampaign(e.target.value)}/></label>
    <label>Source session<input aria-label="Recap source session" type="number" min="1" step="1" value={session} onChange={e=>onSession(e.target.value)}/></label>
    {worldId?<Suspense fallback={<p>Opening session evidence…</p>}><SessionEvidencePicker
      worldId={worldId} targetKey={`build:${documentId}`} onChange={onEvidence} disabled={disabled}/></Suspense>
      :<p>Select a verified World to extract this recap.</p>}
    {evidence.length>0&&<p>{evidence.length} session evidence attachment(s) will stay separate from the external recap.</p>}
  </fieldset>;
}
