import {createContext,useContext,type ReactNode} from 'react';
import type {WorldPlayRunRecordV2} from '../api/types';
import {runPins} from './ownerPins';
import type {TargetPin} from './protocol';
export interface TourRunScope {target:TargetPin;parent:TargetPin}
const Context=createContext<TourRunScope|null>(null);
export function TourRunProvider({run,children}:{run:WorldPlayRunRecordV2|null;children:ReactNode}){
 return <Context.Provider value={run?runPins(run):null}>{children}</Context.Provider>;
}
export const useTourRun=()=>useContext(Context);
