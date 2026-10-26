import {constructionPlacementId,type BuildObjectConstructionProgress} from '../../api/buildConstructionStream';
import {BuildConstructionPreview} from '../../buildSurface/BuildConstructionPreview';
import { proposalReview, type BuildProposalReview } from '../../api/buildProposalReviewApi';
import { BuildPageProposal, RetiredPlacementHistory } from '../../buildSurface/BuildPageProposal';
import { PreparedBuildImage, listPreparedImages, type PreparedImage } from "../../media/PreparedBuildImage";
import { useEffect, useRef, useState } from 'react';
import { composeBuildProposal, getBuildProposal, getBuildProposalPrompt, listBuildProposals,
  type BuildProposalRecord } from '../../api/buildDocumentProposalApi';
import { getWorldAgentConversationHistory, postWorldAgentNewConversation, getWorldAgentNewConversationStatus } from '../../api/liveApi';
import type { WorldAgentConversationHistoryResponse } from '../../api/types';
import type { BuildComposeBridge, CapturedBuildInsertion } from '../../buildSurface/buildComposeBridge';
import { admitMarkdownInsertion } from '../../documentEditing/markdownInsertion';
import { WorldPlanAgentAnswer } from './WorldPlanAgentAnswer';
import { ResponseEvidenceTabs } from './ResponseEvidenceTabs';
import { PreparedRequestInspector } from './PreparedRequestInspector';
import './BuildComposeProposal.css';
import { buildProposalMarkdown } from '../../buildSurface/buildProposalMarkdown';

export function useBuildCompose({ worldId, history, bridge, enabled, onHistory, pageDocumentId, onReviewOnPage, onConstructionVisible, sourceKey = '' }: {
  worldId: string; history: WorldAgentConversationHistoryResponse | null; bridge: BuildComposeBridge | null;
  onReviewOnPage?:()=>void; onConstructionVisible?:()=>void; enabled: boolean; pageDocumentId: string | null; sourceKey?: string; onHistory: (history: WorldAgentConversationHistoryResponse) => void;
}) {
  const scope = enabled ? `${worldId}:${history?.conversation_id ?? ''}` : '';
  const generation = useRef({ scope, epoch: 0 });
  if (generation.current.scope !== scope) generation.current = { scope, epoch: generation.current.epoch + 1 };
  const current = useRef({ scope, epoch: generation.current.epoch, worldId, history, bridge, enabled, onHistory, pageDocumentId, sourceKey });
  current.current = { scope, epoch: generation.current.epoch, worldId, history, bridge, enabled, onHistory, pageDocumentId, sourceKey };
  const constructionScope=JSON.stringify([scope,history?.active_conversation_id,history?.pointer_revision]);
  const constructionView=useRef({sourceKey,pageDocumentId,bridge,scope:constructionScope,epoch:0});
  if(constructionView.current.sourceKey!==sourceKey||constructionView.current.pageDocumentId!==pageDocumentId
    ||constructionView.current.bridge!==bridge||constructionView.current.scope!==constructionScope)
    constructionView.current={sourceKey,pageDocumentId,bridge,scope:constructionScope,epoch:constructionView.current.epoch+1};
  const [records, setRecords] = useState<{ scope: string; values: BuildProposalRecord[] }>({ scope: '', values: [] });
  const [imageRecords,setImageRecords] = useState<{scope:string;values:PreparedImage[]}>({scope:'',values:[]});
  const [construction,setConstruction]=useState<{scope:string;sourceKey:string;viewEpoch:number;progress:BuildObjectConstructionProgress}|null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const running = useRef(false);
  const captures = useRef(new Map<string, CapturedBuildInsertion>());
  const [opened,setOpened]=useState<{action:string;generation:number;documentId:string}|null>(null);
  const [reviewStatus,setReviewStatus]=useState<Record<string,string>>({});
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    setError(null);
    if (!enabled || !history?.conversation_id) return;
    const controller = new AbortController(); let active = true;
    listPreparedImages(worldId,history.conversation_id,controller.signal)
      .then(values=>{if(active)setImageRecords({scope,values});})
      .catch(()=>{if(active)setError('Earlier image directions could not be loaded.');});
    listBuildProposals(worldId, history.conversation_id, controller.signal)
      .then(values => { if (active) setRecords(previous => ({ scope,
        values: [...values, ...(previous.scope === scope ? previous.values.filter(item => !values.some(saved => saved.action_id === item.action_id)) : [])]
          .sort((a, b) => a.created_at.localeCompare(b.created_at)) })); })
      .catch(() => { if (active) setError('Earlier page proposals could not be loaded.'); });
    return () => { active = false; controller.abort(); };
  }, [scope, worldId, enabled, history?.conversation_id, refreshNonce]);
  function put(record: BuildProposalRecord, ownerScope: string, epoch = current.current.epoch, previousScope?: string) {
    if (mounted.current && ((current.current.scope === ownerScope && current.current.epoch === epoch)
      || (previousScope !== undefined && current.current.scope === previousScope && current.current.epoch === epoch - 1))) setRecords(previous => ({ scope: ownerScope,
      values: [...(previous.scope === ownerScope ? previous.values.filter(item => item.action_id !== record.action_id) : []), record]
        .sort((a, b) => a.created_at.localeCompare(b.created_at)) }));
  }
  async function submit(instruction: string): Promise<boolean> {
    const start = current.current;
    if (running.current || !start.enabled || !start.bridge || !start.history) return false;
    running.current = true; setBusy(true); setError(null);
    let action: string | null = null; let ownerScope = start.scope; let epoch = start.epoch;
    try {
      const captured = await start.bridge.capture();
      let pointer = start.history;
      if (!pointer.conversation_id) {
        const created = await postWorldAgentNewConversation(start.worldId, { schema: 'dmb_agent_new_conversation_v1',
          command_id: crypto.randomUUID(), expected_pointer_revision: pointer.pointer_revision, expected_active_conversation_id: null });
        pointer = await getWorldAgentConversationHistory(start.worldId,{includeTurnCorrelation:true});
        if (created.world_id !== start.worldId || pointer.world_id !== start.worldId
          || pointer.conversation_id !== created.conversation_id || pointer.active_conversation_id !== created.conversation_id
          || pointer.pointer_revision !== created.pointer_revision) throw new Error('The active conversation changed. Try again.');
        if (!mounted.current || current.current.scope !== start.scope || current.current.epoch !== start.epoch) return false;
        start.onHistory(pointer);
        ownerScope = `${start.worldId}:${pointer.conversation_id}`;
        epoch = start.epoch + 1;
      }
      if (!pointer.conversation_id || pointer.conversation_id !== pointer.active_conversation_id) throw new Error('Open the current World conversation first.');
      action = crypto.randomUUID();
      captures.current.set(action, captured);
      const result = await composeBuildProposal({ idempotency_key: action, conversation_id: pointer.conversation_id,
        expected_pointer_revision: pointer.pointer_revision, basis: captured.basis, instruction, draft_markdown: captured.draftMarkdown });
      if (result.proposal) admitMarkdownInsertion(buildProposalMarkdown(result.proposal.replacement_markdown).markdown);
      put(result, ownerScope, epoch, ownerScope === start.scope ? undefined : start.scope);
      return true;
    } catch (reason) {
      if (action) {
        try { put(await getBuildProposal(start.worldId, action), ownerScope, epoch, ownerScope === start.scope ? undefined : start.scope); } catch { /* Never replay an uncertain provider request. */ }
      }
      if (mounted.current && ((current.current.scope === ownerScope && current.current.epoch === epoch) || (current.current.scope === start.scope && current.current.epoch === start.epoch))) setError(reason instanceof Error ? reason.message : 'The proposal outcome is unknown.');
      return false;
    } finally { running.current = false; if (mounted.current) setBusy(false); }
  }
  async function prepareHarnessTurn(turnId:string,discussionOnly=false) {
    const start=current.current;
    if(!start.enabled||!start.bridge||!start.history)throw new Error('Open the current page and conversation before sending.');
    const snapshot=await start.bridge.captureContext();
    let captured:CapturedBuildInsertion|undefined;
    if(!discussionOnly){
      try{captured=await start.bridge.capture();}
      catch(reason){return {placementError:reason instanceof Error?reason.message:'Choose where this writing should go.'};}
      if(captured.basis.world_id!==snapshot.world_id||captured.basis.document_id!==snapshot.document_id
        ||captured.basis.registry_revision!==snapshot.registry_revision||captured.basis.content_sha256!==snapshot.content_sha256
        ||captured.basis.visibility!==snapshot.visibility||captured.basis.draft_sha256!==snapshot.draft_sha256
        ||captured.basis.editor_sha256!==snapshot.editor_sha256||captured.basis.draft_generation!==snapshot.draft_generation)throw new Error('The page changed while preparing this request. Send again.');
    }
    if(!mounted.current||current.current.scope!==start.scope||current.current.epoch!==start.epoch
      ||current.current.bridge!==start.bridge)throw new Error('The page or conversation changed before sending.');
    let pointer=start.history;
    const initializedConversation=!pointer.conversation_id;
    if(!pointer.conversation_id){
      const key=`dmb:build-initial-conversation:${start.worldId}`;
      const previous=window.localStorage.getItem(key);
      const command={schema:'dmb_agent_new_conversation_v1' as const,command_id:turnId,
        expected_pointer_revision:pointer.pointer_revision,expected_active_conversation_id:null};
      let pending=command;
      if(previous){
        const value:unknown=JSON.parse(previous);
        if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('The saved conversation start needs recovery.');
        const row=value as Record<string,unknown>;
        if(Object.keys(row).sort().join(',')!=='command_id,expected_active_conversation_id,expected_pointer_revision,schema'
          ||row.schema!==command.schema||typeof row.command_id!=='string'
          ||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(row.command_id)
          ||!Number.isSafeInteger(row.expected_pointer_revision)||(row.expected_pointer_revision as number)<0||row.expected_active_conversation_id!==null)
          throw new Error('The saved conversation start needs recovery.');
        pending={...command,command_id:row.command_id,expected_pointer_revision:row.expected_pointer_revision as number};
      }
      const bytes=JSON.stringify(pending);
      window.localStorage.setItem(key,bytes);
      if(window.localStorage.getItem(key)!==bytes)throw new Error('The conversation start could not be preserved.');
      let confirmed:Awaited<ReturnType<typeof postWorldAgentNewConversation>>|undefined;
      if(previous){
        const status=await getWorldAgentNewConversationStatus(start.worldId,pending);
        if(status.schema!=='dmb_agent_new_conversation_status_v1'||status.world_id!==start.worldId
          ||status.command_id!==pending.command_id||status.command_kind!=='new'
          ||status.expected_pointer_revision!==pending.expected_pointer_revision||status.expected_active_conversation_id!==null
          ||!['confirmed','absent'].includes(status.status)||!/^[a-f0-9]{64}$/.test(status.request_fingerprint))
          throw new Error('The saved conversation start could not be verified.');
        if(status.status==='confirmed'){
          if(status.receipt?.schema!=='dmb_agent_new_conversation_receipt_v1')throw new Error('The saved conversation start has no receipt.');
          confirmed={schema:'dmb_agent_new_conversation_response_v1',world_id:start.worldId,conversation_id:status.receipt.conversation_id,
            active_conversation_id:status.receipt.active_conversation_id,pointer_revision:status.receipt.pointer_revision};
        }else{
          if(status.receipt!==null)throw new Error('The conversation start status is inconsistent.');
          const observed=await getWorldAgentConversationHistory(start.worldId,{includeTurnCorrelation:true});
          if(observed.world_id!==start.worldId)throw new Error('The current conversation could not be verified.');
          if(observed.pointer_revision!==pending.expected_pointer_revision||observed.active_conversation_id!==null){
            if(window.localStorage.getItem(key)===bytes)window.localStorage.removeItem(key);
            if(mounted.current&&current.current.scope===start.scope&&current.current.epoch===start.epoch)start.onHistory(observed);
            throw new Error('The active conversation changed. Send again to use the current conversation.');
          }
        }
      }
      const created=confirmed??await postWorldAgentNewConversation(start.worldId,pending);
      if(created.schema!=='dmb_agent_new_conversation_response_v1'||created.world_id!==start.worldId
        ||typeof created.conversation_id!=='string'||!created.conversation_id
        ||!Number.isSafeInteger(created.pointer_revision)||created.pointer_revision<1)
        throw new Error('The conversation start response could not be verified.');
      pointer=await getWorldAgentConversationHistory(start.worldId,{includeTurnCorrelation:true});
      if(pointer.world_id!==start.worldId)throw new Error('The current conversation could not be verified.');
      if(!mounted.current||current.current.scope!==start.scope||current.current.epoch!==start.epoch
        ||current.current.bridge!==start.bridge)throw new Error('The page or conversation changed before sending.');
      if(window.localStorage.getItem(key)===bytes)window.localStorage.removeItem(key);
      start.onHistory(pointer);
      if(pointer.conversation_id!==created.conversation_id||pointer.active_conversation_id!==created.conversation_id
        ||pointer.pointer_revision!==created.pointer_revision)throw new Error('The active conversation changed. Send again to use the current conversation.');
    }
    if(!pointer.conversation_id||pointer.conversation_id!==pointer.active_conversation_id)throw new Error('Open the current World conversation first.');
    const action=crypto.randomUUID();
    if(captured)captures.current.set(action,captured);
    return {history:pointer,initializedConversation,draftContext:{snapshot,conversation_id:pointer.conversation_id,expected_pointer_revision:pointer.pointer_revision},
      capability:captured?{idempotency_key:action,conversation_id:pointer.conversation_id,expected_pointer_revision:pointer.pointer_revision,
        basis:captured.basis,draft_markdown:captured.draftMarkdown}:undefined};
  }
  const values=records.scope===scope?records.values:[];
  const selected=opened?.documentId===pageDocumentId?opened:null;
  const latest=[...values].reverse().find(record=>record.proposal&&record.reservation.basis.editor_sha256&&record.reservation.basis.document_id===pageDocumentId);
  const active=values.find(record=>record.action_id===(selected?.action??latest?.action_id)&&record.reservation.basis.document_id===pageDocumentId);
  const building=construction?.scope===scope&&construction.sourceKey===sourceKey&&construction.viewEpoch===constructionView.current.epoch
    &&construction.progress.basis.document_id===pageDocumentId
    &&!values.some(value=>value.action_id===constructionPlacementId(construction.progress)&&value.proposal)?construction.progress:null;
  return { busy, error, submit, prepareHarnessTurn,
    observeConstruction:(progress:BuildObjectConstructionProgress)=>{
      if(!mounted.current||!current.current.enabled||progress.basis.world_id!==current.current.worldId
        ||progress.basis.document_id!==current.current.pageDocumentId||progress.conversation_id!==current.current.history?.conversation_id)return;
      setConstruction({scope:current.current.scope,sourceKey:current.current.sourceKey,viewEpoch:constructionView.current.epoch,progress});
    },
    completePlanConstruction:(clientTurnId:string)=>setConstruction(value=>value!==null&&value.progress.schema!=='dmb_build_construction_v1'&&value.progress.client_turn_id===clientTurnId?null:value),
    finishConstruction:(action:string|undefined)=>setConstruction(value=>value!==null&&constructionPlacementId(value.progress)===action&&value.progress.status==='building'
      ?{...value,progress:{...value.progress,status:'incomplete'}}:value),
    refresh: () => setRefreshNonce(value => value + 1),
    pageElement: enabled&&bridge&&building
      ? <BuildConstructionPreview progress={building} bridge={bridge} sourceKey={sourceKey} onVisible={building.status==='incomplete'?undefined:onConstructionVisible}/>
      : enabled&&bridge&&active?.proposal&&!active.inserted_in_draft&&active.reservation.basis.editor_sha256
      &&history?.active_conversation_id===active.reservation.conversation_id
      &&history.pointer_revision===active.reservation.expected_pointer_revision
      // Durable review lifetime follows page identity; its own save advances sourceKey.
      ? <BuildPageProposal key={`${scope}:${active.action_id}`} record={active} bridge={bridge} sourceKey={JSON.stringify([worldId,pageDocumentId])}
          requestKey={selected?.generation??0} inspector={<BuildPrompt record={active}/>} onStatus={text=>setReviewStatus(previous=>({...previous,[active.action_id]:text}))}
          onComplete={state=>{if(state==='applied')setRecords(previous=>previous.scope===scope?{...previous,values:previous.values.map(value=>value.action_id===active.action_id?{...value,inserted_in_draft:true}:value)}:previous);}}/>:null,
    items: [...values.map(record=>({key:record.action_id,afterSequence:Math.max(record.after_turn_sequence,
      history?.turns.find(turn=>turn.turn_id===record.reservation.origin?.durable_turn_id)?.sequence??record.after_turn_sequence),
      element:record.proposal&&bridge&&record.reservation.basis.editor_sha256&&record.reservation.basis.document_id===pageDocumentId&&!record.inserted_in_draft&&reviewStatus[record.action_id]!=='Suggestion discarded'
        ? <button type="button" key={record.action_id} onClick={()=>{setOpened(previous=>({action:record.action_id,documentId:record.reservation.basis.document_id,generation:(previous?.generation??0)+1}));onReviewOnPage?.();}}>
            {reviewStatus[record.action_id]??(record.inserted_in_draft?'Kept on page':'Review suggestion on page')}
          </button>
        : <EarlierBuildProposal key={record.action_id} record={record} label={reviewStatus[record.action_id]}/>})),
      ...(imageRecords.scope===scope?imageRecords.values.map(record=>({key:record.action_id,afterSequence:Math.max(record.after_turn_sequence,history?.turns.find(turn=>turn.turn_id===record.reservation.origin?.durable_turn_id)?.sequence??record.after_turn_sequence),
        element:<PreparedBuildImage key={record.action_id} record={record} bridge={bridge}
          active={history?.active_conversation_id===record.reservation.conversation_id&&history.pointer_revision===record.reservation.expected_pointer_revision}/>})):[])]};
}

function EarlierBuildProposal({record,label}:{record:BuildProposalRecord;label?:string}) {
  const [open,setOpen]=useState(false);
  return <details onToggle={event=>setOpen(event.currentTarget.open)}><summary>{label??(record.inserted_in_draft?'Kept page suggestion':'Earlier page suggestion')}</summary>
    {open?<SavedProposalHistory record={record}/>:null}
  </details>;
}

function SavedProposalHistory({record}:{record:BuildProposalRecord}) {
  const [saved,setSaved]=useState<BuildProposalReview|null>(null);
  const [originalOpen,setOriginalOpen]=useState(false);
  const [unavailable,setUnavailable]=useState(false);
  useEffect(()=>{
    if(!record.reservation.basis.editor_sha256)return;
    let active=true;
    proposalReview(record.reservation.basis.world_id,record.action_id).then(value=>{
      if(value.reservation_sha256!==record.request_fingerprint)throw new Error('Review basis differs');
      if(active)setSaved(value);
    }).catch(()=>{if(active)setUnavailable(true);});
    return()=>{active=false;};
  },[record.action_id,record.request_fingerprint,record.reservation.basis.world_id,record.reservation.basis.editor_sha256]);
  return saved?<section aria-label="Saved suggestion review"><p>{saved.state==='discarded'?'Discarded suggestion':saved.state==='applied'?'Kept suggestion':'Saved review text'}</p>
    <WorldPlanAgentAnswer answer={saved.markdown}/><RetiredPlacementHistory review={saved}/><details onToggle={event=>setOriginalOpen(event.currentTarget.open)}><summary>Original generated suggestion and prompt</summary>{originalOpen?<BuildComposeProposal record={record}/>:null}</details></section>
    : <>{unavailable?<p>The saved review is unavailable. The original generated suggestion follows.</p>:null}<BuildComposeProposal record={record}/></>;
}

function BuildPrompt({ record }: { record: BuildProposalRecord }) {
  const [payload, setPayload] = useState<string | null>(null); const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    if (!record.authorization?.evidence_id) return;
    getBuildProposalPrompt(record.reservation.basis.world_id, record.action_id, controller.signal).then(value => {
      const auth = record.authorization!;
      if (value.schema !== 'dmb_build_proposal_prompt_v1' || value.world_id !== record.reservation.basis.world_id
        || value.action_id !== record.action_id || value.reference.evidence_id !== auth.evidence_id
        || value.reference.provider_attempt_id !== auth.provider_attempt_id || value.reference.payload_sha256 !== auth.payload_sha256
        || value.reference.payload_utf8_bytes !== auth.payload_utf8_bytes) throw new Error('binding');
      const body = JSON.parse(value.payload_json);
      if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('envelope');
      if (active) setPayload(value.payload_json);
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; controller.abort(); };
  }, [record]);
  return !record.authorization?.evidence_id ? <p>No complete request was captured for this proposal.</p>
    : error ? <p role="alert">The captured request is unavailable.</p>
    : payload ? <PreparedRequestInspector payloadJson={payload} /> : <p role="status">Loading captured request…</p>;
}
export function BuildComposeProposal({ record }: { record: BuildProposalRecord }) {
  return <article className="build-compose-proposal" aria-label="Page proposal">
    <div className="build-compose-proposal__request">{record.reservation.origin
      ? <details><summary>Writing details</summary><p>{record.reservation.instruction}</p></details>
      : <p><strong>You</strong> {record.reservation.instruction}</p>}</div>
    {record.proposal ? <div className="world-plan-agent-conversation__message--assistant">
      <p>Authored suggestion for your page</p>
      <WorldPlanAgentAnswer answer={record.proposal.replacement_markdown} />
      {buildProposalMarkdown(record.proposal.replacement_markdown).alignmentAdjusted ? <p>Column alignment will use the page’s default when inserted.</p> : null}
      {record.proposal.assumptions.length ? <details><summary>Creative assumptions</summary><ul>{record.proposal.assumptions.map((text, i) => <li key={i}>{text}</li>)}</ul></details> : null}
      {record.inserted_in_draft ? <p role="status">Inserted into the draft. Save the page when you’re ready.</p>
        : <p>This earlier proposal remains available to read. Ask again to choose a new insertion point.</p>}
    </div> : <p role="status">{record.state === 'unknown' ? 'The request outcome is uncertain. It will not be repeated automatically.'
      : record.state === 'failed' ? 'The proposal could not be prepared.' : 'The proposal has not completed. It will not be repeated automatically.'}</p>}
    <details><summary>Inspect this proposal</summary><ResponseEvidenceTabs evidence={<p>Proposed authored lore for this page. This does not publish Graph facts or save the document.</p>}
      prompt={<BuildPrompt key={`${record.action_id}:${record.authorization?.evidence_id}`} record={record} />} /></details>
  </article>;
}
