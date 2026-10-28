import {createContext,useContext,type ReactNode} from 'react';
import type {WorldPlayRunRecordV2} from '../api/types';
import {runPins} from './ownerPins';
import type {TargetPin} from './protocol';
export interface TourRunScope {target:TargetPin;parent:TargetPin}
const Context=createContext<TourRunScope|null>(null);
/** Explicit bridge for projections mounted outside the owning page's React ancestry. */
export function TourRunScopeProvider({scope,children}:{scope:TourRunScope|null;children:ReactNode}){
 return <Context.Provider value={scope}>{children}</Context.Provider>;
}
export function TourRunProvider({run,children}:{run:WorldPlayRunRecordV2|null;children:ReactNode}){
 return <Context.Provider value={run?runPins(run):null}>{children}</Context.Provider>;
}
export const useTourRun=()=>useContext(Context);
