import {createContext,useContext,useLayoutEffect,useRef,useState,useSyncExternalStore,type ReactNode} from 'react';
import {navigatePrimaryAppHref,subscribeAppLocation,getAppLocationSnapshot,appRouteFromLocationSnapshot} from '../chrome/appNavigation';
import {JOURNEY_STEPS,type StepId} from './definition';
import {samePin,type TargetPin,type Walkthrough} from './protocol';
export type TourSurface='build'|'plan'|'play';
export type NavigationImpact='departure'|'projection';
export interface NavigationScope {worldId:string;walkthroughId:string;epoch:number;step:StepId;index:number;bindings:Walkthrough['bindings'];sceneId?:string;draftId?:string}
/** Transient intent only; callbacks and navigation never enter retained evidence. */
export function navigationScope(walk:Walkthrough|null,epoch:number):NavigationScope|null {
 const proof=walk?.steps[JOURNEY_STEPS[walk.index].id].evidence.at(-1)?.proof;
 return !walk||walk.phase!=='running'?null:{worldId:walk.worldId,walkthroughId:walk.id,epoch,step:JOURNEY_STEPS[walk.index].id,index:walk.index,bindings:structuredClone(walk.bindings),...(proof&&'sceneId' in proof?{sceneId:proof.sceneId}:{}),...(proof?.kind==='mechanics'?{draftId:proof.draftId}:{})};
}
export function sameNavigationScope(a:NavigationScope|null,b:NavigationScope|null):boolean {
 if(!a||!b||a.worldId!==b.worldId||a.walkthroughId!==b.walkthroughId||a.epoch!==b.epoch||a.step!==b.step||a.index!==b.index||a.sceneId!==b.sceneId||a.draftId!==b.draftId)return false;
 return (['source','page','plan','run'] as const).every(kind=>{const x=a.bindings[kind],y=b.bindings[kind];return x&&y?samePin(x,y):x===y;});
}
export function tourDestination(scope:NavigationScope):{surface:TourSurface;pin:TargetPin|null;href:string} {
 const surface:TourSurface=scope.step==='source'||scope.step==='authoring'?'build'
  :['progress','roll','combat','recovery','reflection','memory'].includes(scope.step)||scope.step==='play'&&!!scope.bindings.run?'play':'plan';
 const pin=surface==='build'?scope.bindings[scope.step==='source'?'source':'page']??null:surface==='play'?scope.bindings.run??null:scope.bindings.plan??null;
 if(pin&&pin.worldId!==scope.worldId)throw new Error('The bound object belongs to another World.');
 const params=new URLSearchParams({world:scope.worldId});if(pin)params.set(surface==='play'?'run':'documentId',pin.objectId);else if(surface==='play')params.set('choose','1');
 return {surface,pin,href:`/${surface}?${params}`};
}
export interface InspectionRequest {scope:NavigationScope;/** Check immediately before each post-await presentation change. */isCurrent:()=>boolean;reservation:symbol}
export interface TourInspection {id:string;label:string;step:StepId;target:TargetPin|null;unavailable?:string;ownedReservation?:symbol;impact:NavigationImpact;perform:(request:InspectionRequest)=>void|Promise<void>}
export interface NavigationOwner {role?:'surface'|'panel';worldId:string;surface:TourSurface;objectId:string|null;parent?:TargetPin;inspections:readonly TourInspection[];select?:(pin:TargetPin,request:InspectionRequest)=>void|Promise<void>}
export interface NavigationGuard {worldId:string|null;reason:(impact:NavigationImpact,reservation?:symbol)=>string|null}
/** Presentation permissions, separate from result observations and domain execution. */
export class TourNavigationRegistry {
 private listeners=new Set<()=>void>();
 private version=0;
 subscribe=(listener:()=>void)=>{this.listeners.add(listener);return ()=>{this.listeners.delete(listener);};};
 snapshot=()=>this.version;
 notify=()=>{this.version++;for(const listener of this.listeners)listener();};
 private owners=new Map<symbol,()=>NavigationOwner|null>();
 private guards=new Map<symbol,()=>NavigationGuard|null>();
 isCurrentScope=(scope:NavigationScope)=>sameNavigationScope(scope,this.currentScope());
 constructor(private currentScope:()=>NavigationScope|null){}
 registerOwner(read:()=>NavigationOwner|null){const token=Symbol('tour-navigation-owner');this.owners.set(token,read);this.notify();return {token,release:()=>{this.owners.delete(token);this.notify();}};}
 registerGuard(read:()=>NavigationGuard|null){const token=Symbol('tour-navigation-guard');this.guards.set(token,read);this.notify();return ()=>{this.guards.delete(token);this.notify();};}
 departureReason(scope:NavigationScope,impact:NavigationImpact,reservation?:symbol):string|null {
  if(!sameNavigationScope(scope,this.currentScope()))return 'The guidance changed. Open its current step before navigating.';
  for(const read of this.guards.values()){const guard=read();if(guard&&(guard.worldId===null||guard.worldId===scope.worldId)){const reason=guard.reason(impact,reservation);if(reason)return reason;}}return null;
 }
 inspections(scope:NavigationScope):{owner:symbol;inspection:TourInspection}[] {
  if(!sameNavigationScope(scope,this.currentScope()))return [];
  return Array.from(this.owners,([token,read])=>{const owner=read();return !owner||owner.worldId!==scope.worldId?[]:owner.inspections.filter(action=>action.step===scope.step).map(inspection=>({owner:token,inspection}));}).flat();
 }
 surfaceOwners(worldId:string,surface:string){return Array.from(this.owners,([token,read])=>({token,owner:read()})).filter((item):item is {token:symbol;owner:NavigationOwner}=>!!item.owner&&item.owner.worldId===worldId&&item.owner.surface===surface&&item.owner.role!=='panel');}
 async select(scope:NavigationScope,token:symbol,pin:TargetPin):Promise<void>{
  const read=this.owners.get(token),original=read?.(),reservation=Symbol('selection-reservation');
  const current=()=>{
   if(!read||!original||this.owners.get(token)!==read||this.departureReason(scope,'departure',reservation))return null;
   const owner=read(),destination=tourDestination(scope);
   if(!owner||owner.worldId!==scope.worldId||owner.surface!==destination.surface||owner.objectId!==original.objectId||!destination.pin||!samePin(destination.pin,pin))return null;
   if(this.surfaceOwners(scope.worldId,owner.surface).length!==1)return null;
   return owner.select??null;
  };
  const select=current();if(!select)throw new Error('The destination is unavailable or unfinished work needs attention.');
  await select(structuredClone(pin),{scope:structuredClone(scope),isCurrent:()=>current()!==null,reservation});
 }
 async inspect(scope:NavigationScope,token:symbol,id:string):Promise<void> {
  const read=this.owners.get(token);if(!read)throw new Error('The inspection owner is no longer available.');
  const original=read(),reservation=Symbol('inspection-reservation');if(!original)throw new Error('The inspection owner is no longer available.');
  const find=()=>{
   if(this.owners.get(token)!==read||!sameNavigationScope(scope,this.currentScope()))return null;
   const owner=read();if(!owner||owner.worldId!==scope.worldId||owner.surface!==original.surface||owner.objectId!==original.objectId)return null;
   const actions=this.inspections(scope).filter(item=>item.inspection.id===id);
   if(actions.length!==1||actions[0].owner!==token)return null;
   const action=actions[0].inspection,pin=tourDestination(scope).pin;
   if(action.target?.kind==='run'&&scope.bindings.plan&&(!owner.parent||!samePin(owner.parent,scope.bindings.plan)))return null;
   if(action.target&&(action.target.worldId!==scope.worldId||pin&&!samePin(pin,action.target)))return null;
   if(pin&&(!action.target||action.target.objectId!==owner.objectId))return null;
   if(action.unavailable&&action.ownedReservation!==reservation||this.departureReason(scope,action.impact,reservation))return null;return action;
  };
  const action=find();if(!action)throw new Error('The intended object or controls changed, or unfinished work needs attention.');
  await action.perform({scope:structuredClone(scope),isCurrent:()=>find()!==null,reservation});
 }
}
const Context=createContext<TourNavigationRegistry|null>(null);
export function TourNavigationProvider({registry,children}:{registry:TourNavigationRegistry;children:ReactNode}){return <Context.Provider value={registry}>{children}</Context.Provider>;}
/** Incidental busy renders refresh live refs without replacing an owner registration. */
export function useTourNavigationOwner(owner:NavigationOwner|null){
 const registry=useContext(Context),live=useRef(owner);live.current=owner;
 const world=owner?.worldId,surface=owner?.surface,objectId=owner?.objectId,signature=JSON.stringify(owner);
 useLayoutEffect(()=>registry?.notify(),[registry,signature]);
 useLayoutEffect(()=>{if(!registry||!live.current)return;const registration=registry.registerOwner(()=>live.current!);return registration.release;},[registry,world,surface,objectId]);
}
export function useTourNavigationGuard(guard:NavigationGuard|null){
 const registry=useContext(Context),live=useRef(guard);live.current=guard;const world=guard?.worldId;
 useLayoutEffect(()=>{if(!registry||!live.current)return;return registry.registerGuard(()=>live.current!);},[registry,world]);
}

/** Explicit stages: route/selection first, then the destination owner opens inspection. */
export function TourNavigationActions({scope,onOpened}:{scope:NavigationScope|null;onOpened:()=>void}){
 const registry=useContext(Context),[error,setError]=useState<{scope:NavigationScope;message:string}|null>(null);
 useSyncExternalStore(registry?.subscribe??emptySubscribe,registry?.snapshot??emptySnapshot);
 const location=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot);
 if(!registry||!scope)return null;
 let destination:ReturnType<typeof tourDestination>;
 try{destination=tourDestination(scope);}catch(cause){return <p role="alert">{String(cause instanceof Error?cause.message:cause)}</p>;}
 const route=appRouteFromLocationSnapshot(location),owners=registry.surfaceOwners(scope.worldId,destination.surface);
 const run=async(action:()=>void|Promise<void>)=>{setError(null);try{await action();}catch(cause){setError({scope,message:cause instanceof Error?cause.message:'The controls could not be opened.'});}};
 const navigation=route!==destination.surface?<button type="button" onClick={()=>void run(()=>{
  const reason=registry.departureReason(scope,'departure');if(reason)throw new Error(reason);
  if(['build','plan','play'].includes(route)&&registry.surfaceOwners(scope.worldId,route).length!==1)throw new Error('Wait for the current surface to finish opening.');
  navigatePrimaryAppHref(destination.href);
 })}>Open {destination.surface==='build'?'Build':destination.surface==='plan'?'Plan':'Play'}</button>
 :owners.length!==1?<p>Waiting for one intended {destination.surface} view to finish opening.</p>
 :destination.pin&&owners[0].owner.objectId!==destination.pin.objectId?<button type="button" onClick={()=>void run(()=>registry.select(scope,owners[0].token,destination.pin!))}>Open the bound {destination.pin.kind}</button>:null;
 const actions=route===destination.surface&&owners.length===1&&(!destination.pin||owners[0].owner.objectId===destination.pin.objectId)?registry.inspections(scope):[];
 return <section aria-label="Open this capability">{navigation}{actions.map(({owner,inspection},index)=><button key={`${inspection.id}:${index}`} type="button" disabled={!!inspection.unavailable} title={inspection.unavailable} onClick={()=>void run(async()=>{await registry.inspect(scope,owner,inspection.id);if(registry.isCurrentScope(scope))onOpened();})}>{inspection.label}</button>)}{actions.filter(item=>item.inspection.unavailable).map(({inspection},index)=><p key={`reason:${inspection.id}:${index}`}>{inspection.unavailable}</p>)}{error&&sameNavigationScope(error.scope,scope)&&<p role="alert">{error.message}</p>}</section>;
}
const emptySubscribe=()=>()=>{};
const emptySnapshot=()=>0;
