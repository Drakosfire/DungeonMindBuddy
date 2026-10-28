import {JOURNEY_STEPS,TOUR_DEFINITION,type Adventure,type StepId,type TargetKind} from './definition';
export interface TargetPin {kind:TargetKind;worldId:string;objectId:string;revision:number;digest:string;revisionId?:string}
export interface EncounterEvidence {kind:'encounter';sceneId:string;encounterId:string;revision:number;digest:string;operationId:string}
export interface Observation {
 step:StepId;target:TargetPin;observedAt:string;
 origin:'existing'|'acknowledged'|'reloaded';
 /** Owner-validated immutable result identity, not a click or optimistic update. */
 receiptId:string;
 /** Parent pins and specialized evidence are checked by the owning adapter. */
 parent?:TargetPin;
 proof?:EncounterEvidence;
}
export type StepState = 'pending'|'existing'|'completed'|'skipped'|'failed'|'unavailable';
export interface StepRecord {state:StepState;reason:string|null;evidence:Observation[]}
export interface Walkthrough {
 schema:'dmb_guided_journey_v1';definition:typeof TOUR_DEFINITION.id;version:1;
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
 return exact(value,['kind','worldId','objectId','revision','digest',...(record(value)&&value.kind==='plan'?['revisionId']:[])])&&['source','plan','run'].includes(String(value.kind))&&value.worldId===world&&text(value.objectId)&&Number.isSafeInteger(value.revision)&&Number(value.revision)>0&&digest(value.digest)&&(value.kind!=='plan'||text(value.revisionId));
}
export function validObservation(v:unknown,world:string):v is Observation {
 if(!record(v)||!exact(v,['step','target','observedAt','origin','receiptId',...('parent' in v?['parent']:[]),...('proof' in v?['proof']:[])]))return false;
 const definition=JOURNEY_STEPS.find(s=>s.id===v.step);
 if(v.step==='encounter'){const p=v.proof;if(!exact(p,['kind','sceneId','encounterId','revision','digest','operationId'])||p.kind!=='encounter'||!text(p.sceneId)||!text(p.encounterId)||!Number.isSafeInteger(p.revision)||Number(p.revision)<1||!text(p.digest)||!/^sha256:[a-f0-9]{64}$/.test(p.digest)||!text(p.operationId))return false;}
 else if('proof' in v)return false;
 return !!definition&&validPin(v.target,world)&&v.target.kind===definition.target&&text(v.observedAt)&&Number.isFinite(Date.parse(v.observedAt))
  &&['existing','acknowledged','reloaded'].includes(String(v.origin))&&text(v.receiptId)&&(!('parent' in v)||validPin(v.parent,world));
}
export function createWalkthrough(worldId:string,adventure:Adventure,id:string,now:string):Walkthrough {
 if(!text(worldId)||!text(id)||!Number.isFinite(Date.parse(now))||!Object.hasOwn({conks:1,sheep:1},adventure))throw new Error('Select a managed World and adventure before starting.');
 return {schema:'dmb_guided_journey_v1',definition:TOUR_DEFINITION.id,version:1,id,worldId,adventure,startedAt:now,phase:'running',index:0,bindings:{},steps:Object.fromEntries(JOURNEY_STEPS.map(s=>[s.id,{state:'pending',reason:null,evidence:[]}])) as unknown as Walkthrough['steps']};
}
export function decodeWalkthrough(bytes:string,world:string):Walkthrough {
 const v:unknown=JSON.parse(bytes);
 if(!exact(v,['schema','definition','version','id','worldId','adventure','startedAt','phase','index','bindings','steps'])||v.schema!=='dmb_guided_journey_v1'||v.definition!==TOUR_DEFINITION.id||v.version!==1||v.worldId!==world||!text(v.id)||!['conks','sheep'].includes(String(v.adventure))||!text(v.startedAt)||!Number.isFinite(Date.parse(v.startedAt))||!['running','paused','exited'].includes(String(v.phase))||!Number.isSafeInteger(v.index)||Number(v.index)<0||Number(v.index)>=JOURNEY_STEPS.length||!record(v.bindings)||!exact(v.steps,JOURNEY_STEPS.map(s=>s.id)))throw new Error('The saved walkthrough cannot be verified. Its original record was preserved.');
 for(const [kind,pin] of Object.entries(v.bindings))if(!['source','plan','run'].includes(kind)||!validPin(pin,world)||pin.kind!==kind)throw new Error('The walkthrough has a different target.');
 for(const step of JOURNEY_STEPS){const row=v.steps[step.id];if(!exact(row,['state','reason','evidence'])||!['pending','existing','completed','skipped','failed','unavailable'].includes(String(row.state))||!(row.reason===null||text(row.reason))||!Array.isArray(row.evidence)||!row.evidence.every(e=>validObservation(e,world)&&e.step===step.id))throw new Error('The walkthrough evidence cannot be verified.');}
 for(const step of JOURNEY_STEPS){
  const row=v.steps[step.id] as unknown as StepRecord;
  if(row.state==='completed'&&!row.evidence.some(e=>e.origin!=='existing'&&Date.parse(e.observedAt)>=Date.parse(v.startedAt as string)))throw new Error('Completion has no newly demonstrated evidence.');
  for(const e of row.evidence){const bound=v.bindings[e.target.kind];if(!validPin(bound,world)||bound.objectId!==e.target.objectId||e.target.revision===bound.revision&&!samePin(e.target,bound))throw new Error('Evidence belongs to a different target.');
   if(e.target.kind==='run'&&(!validPin(v.bindings.plan,world)||!e.parent||!samePin(v.bindings.plan,e.parent)))throw new Error('Run evidence has a different Plan pin.');}
 }
 return v as unknown as Walkthrough;
}
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
 const observation=action.observation;
 if(!validObservation(observation,current.worldId))throw new Error('The observation has no verified owner basis.');
 const bound=current.bindings[observation.target.kind];
 // A later revision of the same selected object is evidence, never a target replacement.
 if(!bound||bound.objectId!==observation.target.objectId||observation.target.revision<bound.revision
  ||observation.target.revision===bound.revision&&!samePin(observation.target,bound))return current;
 if(observation.target.kind==='run'&&(!current.bindings.plan||!observation.parent||!samePin(current.bindings.plan,observation.parent)))return current;
 const row=current.steps[observation.step];
 if(row.evidence.some(e=>e.receiptId===observation.receiptId&&samePin(e.target,observation.target)&&e.origin===observation.origin))return current;
 const isNew=observation.origin!=='existing'&&Date.parse(observation.observedAt)>=Date.parse(current.startedAt);
 const state:StepState=isNew?'completed':row.state==='completed'?'completed':'existing';
 return {...current,steps:{...current.steps,[observation.step]:{state,reason:null,evidence:[...row.evidence,observation]}}};
}
