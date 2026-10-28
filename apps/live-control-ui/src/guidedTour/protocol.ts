import {JOURNEY_STEPS,TOUR_DEFINITION,type Adventure,type StepId,type TargetKind} from './definition';
export interface TargetPin {kind:TargetKind;worldId:string;objectId:string;revision:number;digest:string;revisionId?:string}
export interface EncounterEvidence {kind:'encounter';sceneId:string;encounterId:string;revision:number;digest:string;operationId:string}
export interface MechanicsLocatorEvidence {provider:'dungeonmind';statblock_id:string;revision_id:string;contract:string;contract_version:string;definition_digest:string}
export interface MechanicsEvidence {kind:'mechanics';sceneId:string;encounterId:string;draftId:string;operationId:string;locator:MechanicsLocatorEvidence}
export interface AdoptionEvidence {kind:'adoption';sceneId:string;encounterId:string;operationId:string;encounterRevision:number;locator:MechanicsLocatorEvidence;actors:{actorId:string;beforeDigest:string;afterDigest:string;acPolicy:string;hpPolicy:string}[]}
export interface RunStateEvidence {kind:'run-state';stateDigest:string;pageInstanceId:string;contentRevision:number;contentRevisionId:string|null;contentDigest:string}
export interface SessionReviewEvidence {kind:'session-review';reviewRevision:number;checkpointRunRevision:number;contentRevision:number;contentRevisionId:string|null;contentDigest:string;commandId:string|null}
export interface RecordedRollEvidence {kind:'recorded-roll';commandId:string;tableId:string;tableDigest:string;dieSides:number;physicalValue:number;rowId:string;expectedRunRevision:number;resultingRunRevision:number}
export interface CombatTrackerEvidence {kind:'combat-tracker';sceneId:string;encounterId:string;baseRevision:number;savedRevision:number;roundChanged:boolean;activeTurnChanged:boolean;actors:{actorId:string;fields:string[]}[]}
export interface ImageEvidence {kind:'generated-image';assetId:string;generation:'observed'|'existing-library';model:string|null;generationObservedAt:string|null;placementObservedAt:string;savedPlanVersionId:string}
export interface MemoryEntryEvidence {kind:'scene_note'|'closing_reflections';elementId:string|null;sourceOrdinal:number;entryIdentity:string;bodyDigest:string;packetDigest:string}
export interface MemoryEvidence {kind:'session-memory';turnId:string;reviewRevision:number;checkpointContentDigest:string;contextReceiptDigest:string;entries:MemoryEntryEvidence[]}
export interface RunCreationEvidence {kind:'run-creation';entrySceneId:string|null;preparedSceneIds:string[]}
export interface Observation {
 step:StepId;target:TargetPin;observedAt:string;
 origin:'existing'|'acknowledged'|'reloaded';
 /** Owner-validated immutable result identity, not a click or optimistic update. */
 receiptId:string;
 /** Parent pins and specialized evidence are checked by the owning adapter. */
 parent?:TargetPin;
 proof?:EncounterEvidence|MechanicsEvidence|AdoptionEvidence|RunStateEvidence|SessionReviewEvidence|RecordedRollEvidence|CombatTrackerEvidence|ImageEvidence|MemoryEvidence|RunCreationEvidence;
}
export type StepState = 'pending'|'existing'|'completed'|'skipped'|'failed'|'unavailable';
export interface StepRecord {state:StepState;reason:string|null;evidence:Observation[]}
export interface Walkthrough {
 schema:'dmb_guided_journey_v2';definition:typeof TOUR_DEFINITION.id;version:2;
 upgradedFrom?:{id:string;version:1};
 id:string;worldId:string;adventure:Adventure;startedAt:string;phase:'running'|'paused'|'exited';index:number;
 bindings:Partial<Record<TargetKind,TargetPin>>;
 steps:Record<StepId,StepRecord>;
}
export const samePin=(a:TargetPin,b:TargetPin)=>a.kind===b.kind&&a.worldId===b.worldId&&a.objectId===b.objectId&&a.revision===b.revision&&a.digest===b.digest&&a.revisionId===b.revisionId;
const digest=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const text=(v:unknown):v is string=>typeof v==='string'&&!!v.trim();
const record=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
const exact=(v:unknown,keys:string[]):v is Record<string,unknown>=>record(v)&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
export function validPin(value:unknown,world:string):value is TargetPin {
 return exact(value,['kind','worldId','objectId','revision','digest',...(record(value)&&value.kind==='plan'?['revisionId']:[])])&&['source','page','plan','run'].includes(String(value.kind))&&value.worldId===world&&text(value.objectId)&&Number.isSafeInteger(value.revision)&&Number(value.revision)>0&&digest(value.digest)&&(value.kind!=='plan'||text(value.revisionId));
}
function validLocator(v:unknown):v is MechanicsLocatorEvidence {
 return exact(v,['provider','statblock_id','revision_id','contract','contract_version','definition_digest'])&&v.provider==='dungeonmind'&&[v.statblock_id,v.revision_id,v.contract,v.contract_version].every(text)&&text(v.definition_digest)&&/^sha256:[a-f0-9]{64}$/.test(v.definition_digest);
}
function checkObservation(v:unknown,world:string,legacy=false):v is Observation {
 if(!record(v)||!exact(v,['step','target','observedAt','origin','receiptId',...('parent' in v?['parent']:[]),...('proof' in v?['proof']:[])]))return false;
 const definition=JOURNEY_STEPS.find(s=>s.id===v.step);
 if(v.step==='recovery'&&v.origin==='acknowledged')return false;
 if(v.step==='encounter'){const p=v.proof;if(!exact(p,['kind','sceneId','encounterId','revision','digest','operationId'])||p.kind!=='encounter'||!text(p.sceneId)||!text(p.encounterId)||!Number.isSafeInteger(p.revision)||Number(p.revision)<1||!text(p.digest)||!/^sha256:[a-f0-9]{64}$/.test(p.digest)||!text(p.operationId))return false;}
 else if(v.step==='mechanics'){const p=v.proof;if(!exact(p,['kind','sceneId','encounterId','draftId','operationId','locator'])||p.kind!=='mechanics'||![p.sceneId,p.encounterId,p.draftId,p.operationId].every(text)||!validLocator(p.locator))return false;}
 else if(v.step==='adoption'){const p=v.proof;if(!exact(p,['kind','sceneId','encounterId','operationId','encounterRevision','locator','actors'])||p.kind!=='adoption'||![p.sceneId,p.encounterId,p.operationId].every(text)||!Number.isSafeInteger(p.encounterRevision)||Number(p.encounterRevision)<1||!validLocator(p.locator)||!Array.isArray(p.actors)||!p.actors.length||!p.actors.every(a=>exact(a,['actorId','beforeDigest','afterDigest','acPolicy','hpPolicy'])&&[a.actorId,a.beforeDigest,a.afterDigest].every(text)&&['keep','use_saved'].includes(String(a.acPolicy))&&['keep','preserve_current','clamp_current','reset_full'].includes(String(a.hpPolicy)))||new Set(p.actors.map(a=>(a as {actorId:string}).actorId)).size!==p.actors.length)return false;}
 else if(v.step==='progress'||v.step==='recovery'){const p=v.proof;if(!exact(p,['kind','stateDigest','pageInstanceId','contentRevision','contentRevisionId','contentDigest'])||p.kind!=='run-state'||!digest(p.stateDigest)||!text(p.pageInstanceId)||!Number.isSafeInteger(p.contentRevision)||Number(p.contentRevision)<0||(p.contentRevision===0?p.contentRevisionId!==null:!text(p.contentRevisionId))||!digest(p.contentDigest))return false;}
 else if(v.step==='reflection'){const p=v.proof;if(!exact(p,['kind','reviewRevision','checkpointRunRevision','contentRevision','contentRevisionId','contentDigest','commandId'])||p.kind!=='session-review'||!Number.isSafeInteger(p.reviewRevision)||Number(p.reviewRevision)<1||!Number.isSafeInteger(p.checkpointRunRevision)||Number(p.checkpointRunRevision)<1||!Number.isSafeInteger(p.contentRevision)||Number(p.contentRevision)<0||(p.contentRevision===0?p.contentRevisionId!==null:!text(p.contentRevisionId))||!digest(p.contentDigest)||(p.commandId!==null&&!text(p.commandId))||(v.origin==='acknowledged'&&!text(p.commandId)))return false;}
 else if(v.step==='roll'){const p=v.proof;if(!exact(p,['kind','commandId','tableId','tableDigest','dieSides','physicalValue','rowId','expectedRunRevision','resultingRunRevision'])||p.kind!=='recorded-roll'||![p.commandId,p.tableId,p.rowId].every(text)||!digest(p.tableDigest)||!Number.isSafeInteger(p.dieSides)||Number(p.dieSides)<1||!Number.isSafeInteger(p.physicalValue)||Number(p.physicalValue)<1||Number(p.physicalValue)>Number(p.dieSides)||!Number.isSafeInteger(p.expectedRunRevision)||Number(p.expectedRunRevision)<1||p.resultingRunRevision!==Number(p.expectedRunRevision)+1)return false;}
 else if(v.step==='combat'){const p=v.proof;if(!exact(p,['kind','sceneId','encounterId','baseRevision','savedRevision','roundChanged','activeTurnChanged','actors'])||p.kind!=='combat-tracker'||![p.sceneId,p.encounterId].every(text)||!Number.isSafeInteger(p.baseRevision)||Number(p.baseRevision)<1||p.savedRevision!==Number(p.baseRevision)+1||typeof p.roundChanged!=='boolean'||typeof p.activeTurnChanged!=='boolean'||!Array.isArray(p.actors)||!p.actors.every(a=>exact(a,['actorId','fields'])&&text(a.actorId)&&Array.isArray(a.fields)&&a.fields.length>0&&a.fields.every(f=>['hp','max_hp','temp_hp','ac','conditions','defeated','init'].includes(String(f))))||!p.roundChanged&&!p.activeTurnChanged&&!p.actors.length)return false;}
 else if(v.step==='image'){const p=v.proof;if(!exact(p,['kind','assetId','generation','model','generationObservedAt','placementObservedAt','savedPlanVersionId'])||p.kind!=='generated-image'||![p.assetId,p.savedPlanVersionId,p.placementObservedAt].every(text)||!['observed','existing-library'].includes(String(p.generation))||(p.model!==null&&!text(p.model))||(p.generationObservedAt!==null&&(!text(p.generationObservedAt)||!Number.isFinite(Date.parse(p.generationObservedAt))))||!Number.isFinite(Date.parse(String(p.placementObservedAt)))||!record(v.target)||v.target.revisionId!==p.savedPlanVersionId||(p.generation==='observed'&&(!text(p.model)||!text(p.generationObservedAt)))||(v.origin==='acknowledged'&&p.generation!=='observed'))return false;}
 else if(v.step==='memory'){const p=v.proof;const entries=record(p)?p.entries:undefined;if(!exact(p,['kind','turnId','reviewRevision','checkpointContentDigest','contextReceiptDigest','entries'])||p.kind!=='session-memory'||!text(p.turnId)||!Number.isSafeInteger(p.reviewRevision)||Number(p.reviewRevision)<1||!digest(p.checkpointContentDigest)||!digest(p.contextReceiptDigest)||!Array.isArray(entries)||!entries.every(e=>exact(e,['kind','elementId','sourceOrdinal','entryIdentity','bodyDigest','packetDigest'])&&['scene_note','closing_reflections'].includes(String(e.kind))&&(e.kind==='scene_note'?text(e.elementId):e.elementId===null)&&Number.isSafeInteger(e.sourceOrdinal)&&Number(e.sourceOrdinal)>=0&&[e.entryIdentity,e.bodyDigest,e.packetDigest].every(digest))||!['scene_note','closing_reflections'].every(kind=>entries.some(e=>(e as {kind:string}).kind===kind)))return false;}
 else if(v.step==='play'&&('proof' in v||v.origin==='acknowledged')){const p=v.proof;if(!exact(p,['kind','entrySceneId','preparedSceneIds'])||p.kind!=='run-creation'||!(p.entrySceneId===null||text(p.entrySceneId))||!Array.isArray(p.preparedSceneIds)||!p.preparedSceneIds.every(text)||(p.entrySceneId!==null&&!p.preparedSceneIds.includes(p.entrySceneId)))return false;}
 else if('proof' in v)return false;
 return !!definition&&validPin(v.target,world)&&v.target.kind===(legacy&&v.step==='authoring'?'source':definition.target)&&text(v.observedAt)&&Number.isFinite(Date.parse(v.observedAt))
  &&['existing','acknowledged','reloaded'].includes(String(v.origin))&&text(v.receiptId)&&(!('parent' in v)||validPin(v.parent,world));
}
export const validObservation=(v:unknown,world:string):v is Observation=>checkObservation(v,world);
export function createWalkthrough(worldId:string,adventure:Adventure,id:string,now:string):Walkthrough {
 if(!text(worldId)||!text(id)||!Number.isFinite(Date.parse(now))||!Object.hasOwn({conks:1,sheep:1},adventure))throw new Error('Select a managed World and adventure before starting.');
 return {schema:'dmb_guided_journey_v2',definition:TOUR_DEFINITION.id,version:2,id,worldId,adventure,startedAt:now,phase:'running',index:0,bindings:{},steps:Object.fromEntries(JOURNEY_STEPS.map(s=>[s.id,{state:'pending',reason:null,evidence:[]}])) as unknown as Walkthrough['steps']};
}
function decodeRecord(bytes:string,world:string,legacy=false):Walkthrough {
 const v:unknown=JSON.parse(bytes);
 if(!exact(v,['schema','definition','version','id','worldId','adventure','startedAt','phase','index','bindings','steps',...(record(v)&&'upgradedFrom' in v?['upgradedFrom']:[])])||v.schema!==(legacy?'dmb_guided_journey_v1':'dmb_guided_journey_v2')||v.definition!==TOUR_DEFINITION.id||v.version!==(legacy?1:2)||v.worldId!==world||!text(v.id)||!['conks','sheep'].includes(String(v.adventure))||!text(v.startedAt)||!Number.isFinite(Date.parse(v.startedAt))||!['running','paused','exited'].includes(String(v.phase))||!Number.isSafeInteger(v.index)||Number(v.index)<0||Number(v.index)>=JOURNEY_STEPS.length||!record(v.bindings)||!exact(v.steps,JOURNEY_STEPS.map(s=>s.id)))throw new Error('The saved walkthrough cannot be verified. Its original record was preserved.');
 if('upgradedFrom' in v&&(legacy||!exact(v.upgradedFrom,['id','version'])||!text(v.upgradedFrom.id)||v.upgradedFrom.version!==1||v.id!==v.upgradedFrom.id+'-v2'))throw new Error('The guidance upgrade has an invalid predecessor.');
 for(const [kind,pin] of Object.entries(v.bindings))if(!(legacy?['source','plan','run']:['source','page','plan','run']).includes(kind)||!validPin(pin,world)||pin.kind!==kind)throw new Error('The walkthrough has a different target.');
 for(const step of JOURNEY_STEPS){const row=v.steps[step.id];if(!exact(row,['state','reason','evidence'])||!['pending','existing','completed','skipped','failed','unavailable'].includes(String(row.state))||!(row.reason===null||text(row.reason))||!Array.isArray(row.evidence)||!row.evidence.every(e=>checkObservation(e,world,legacy)&&e.step===step.id))throw new Error('The walkthrough evidence cannot be verified.');}
 for(const step of JOURNEY_STEPS){
  const row=v.steps[step.id] as unknown as StepRecord;
  if(row.state==='completed'&&!row.evidence.some(e=>e.origin!=='existing'&&Date.parse(e.observedAt)>=Date.parse(v.startedAt as string)))throw new Error('Completion has no newly demonstrated evidence.');
  if(step.id==='recovery'&&row.state==='completed'&&!row.evidence.some((e,index)=>e.origin==='reloaded'&&e.proof?.kind==='run-state'&&row.evidence.slice(0,index).some(prior=>prior.proof?.kind==='run-state'&&samePin(prior.target,e.target)&&prior.proof.stateDigest===(e.proof as RunStateEvidence).stateDigest&&prior.proof.pageInstanceId!==(e.proof as RunStateEvidence).pageInstanceId)))throw new Error('Recovery has no matching saved-state observation from an earlier page instance.');
  for(const e of row.evidence){const bound=v.bindings[e.target.kind];if(!validPin(bound,world)||bound.objectId!==e.target.objectId||e.target.revision===bound.revision&&!samePin(e.target,bound))throw new Error('Evidence belongs to a different target.');
   if(e.target.kind==='run'&&(!validPin(v.bindings.plan,world)||!e.parent||!samePin(v.bindings.plan,e.parent)))throw new Error('Run evidence has a different Plan pin.');}
 }
 return v as unknown as Walkthrough;
}
/** Strict one-way stored-data conversion. The old record is never executed or overwritten. */
export function upgradeWalkthroughV1(bytes:string,world:string):Walkthrough {
 const old=decodeRecord(bytes,world,true);
 const page=old.bindings.source?{...old.bindings.source,kind:'page' as const}:undefined;
 const next:Walkthrough={...old,schema:'dmb_guided_journey_v2',version:2,id:old.id+'-v2',upgradedFrom:{id:old.id,version:1},
  bindings:{...old.bindings,...(page?{page}:{})},steps:{...old.steps,authoring:{...old.steps.authoring,
   evidence:old.steps.authoring.evidence.map(e=>({...e,target:{...e.target,kind:'page' as const}}))}}};
 return decodeWalkthrough(JSON.stringify(next),world);
}
export const decodeWalkthrough=(bytes:string,world:string):Walkthrough=>decodeRecord(bytes,world);
export type TourAction = {kind:'move';index:number}|{kind:'phase';phase:Walkthrough['phase']}|{kind:'disposition';step:StepId;state:'skipped'|'failed'|'unavailable';reason:string}|{kind:'bind';pin:TargetPin;parent?:TargetPin}|{kind:'observe';observation:Observation};
/** This reducer has no IO and cannot execute any product operation. */
export function reduceTour(current:Walkthrough,action:TourAction):Walkthrough {
 if(action.kind==='move')return Number.isSafeInteger(action.index)&&action.index>=0&&action.index<JOURNEY_STEPS.length?{...current,index:action.index}:current;
 if(action.kind==='phase')return {...current,phase:action.phase};
 if(current.phase!=='running')return current;
 if(action.kind==='bind'){
  const pin=action.pin;
  if(!validPin(pin,current.worldId))throw new Error('The selected target belongs to another World or has no verified basis.');
  const bound=current.bindings[pin.kind];
  if(bound&&!samePin(bound,pin)&&(bound.objectId!==pin.objectId||pin.revision<=bound.revision||pin.kind==='run'||pin.kind==='plan'&&!!current.bindings.run))throw new Error('This walkthrough already has a different target or a Run pinned to that Plan. Start a separate walkthrough to keep its evidence.');
  if(pin.kind==='run'&&(!current.bindings.plan||!action.parent||!samePin(current.bindings.plan,action.parent)))throw new Error('Select the exact saved Plan that owns this Run before binding it.');
  return {...current,bindings:{...current.bindings,[pin.kind]:pin}};
 }
 if(action.kind==='disposition'){
  if(!text(action.reason))throw new Error('Explain why this step was skipped or unavailable.');
  return {...current,steps:{...current.steps,[action.step]:{...current.steps[action.step],state:action.state,reason:action.reason}}};
 }
 let observation=action.observation;
 if(!validObservation(observation,current.worldId))throw new Error('The observation has no verified owner basis.');
 const bound=current.bindings[observation.target.kind];
 // A later revision of the same selected object is evidence, never a target replacement.
 if(!bound||bound.objectId!==observation.target.objectId||observation.target.revision<bound.revision
  ||observation.target.revision===bound.revision&&!samePin(observation.target,bound))return current;
 if(observation.target.kind==='run'&&(!current.bindings.plan||!observation.parent||!samePin(current.bindings.plan,observation.parent)))return current;
 const row=current.steps[observation.step];
 if(observation.step==='recovery'){
  const proof=observation.proof;
  const recovered=proof?.kind==='run-state'&&row.evidence.some(prior=>prior.proof?.kind==='run-state'&&samePin(prior.target,observation.target)&&prior.proof.stateDigest===proof.stateDigest&&prior.proof.pageInstanceId!==proof.pageInstanceId);
  if(observation.origin==='reloaded'&&!recovered)return current;
  if(recovered)observation={...observation,origin:'reloaded'};
 }

 if(row.evidence.some(e=>e.receiptId===observation.receiptId&&samePin(e.target,observation.target)&&e.origin===observation.origin))return current;
 const isNew=observation.origin!=='existing'&&Date.parse(observation.observedAt)>=Date.parse(current.startedAt);
 const state:StepState=isNew?'completed':row.state==='completed'?'completed':'existing';
 return {...current,steps:{...current.steps,[observation.step]:{state,reason:null,evidence:[...row.evidence,observation]}}};
}
