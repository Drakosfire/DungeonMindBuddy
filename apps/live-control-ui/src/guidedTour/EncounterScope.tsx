import {createContext,useContext,type ReactNode} from 'react';
import {samePin,type TargetPin} from './protocol';
/** Presentation identity supplied by the admitted scene owner; never a write grant. */
export interface TourEncounterScope {plan:TargetPin;sceneId:string;encounterId:string}
const Context=createContext<TourEncounterScope|null>(null);
export function TourEncounterProvider({scope,children}:{scope:TourEncounterScope|null;children:ReactNode}){
 return <Context.Provider value={scope}>{children}</Context.Provider>;
}
export const useTourEncounter=()=>useContext(Context);
export const sameEncounterScope=(a:TourEncounterScope|null,b:TourEncounterScope|null)=>!!a&&!!b&&samePin(a.plan,b.plan)&&a.sceneId===b.sceneId&&a.encounterId===b.encounterId;
