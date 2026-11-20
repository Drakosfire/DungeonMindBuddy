import {useSyncExternalStore} from 'react';
import type {DocumentRelationshipIntent} from '../api/graphDocumentRelationshipApi';
export type RelationshipReviewHost={worldId:string;documentId:string;open:(intent:DocumentRelationshipIntent)=>Promise<void>};
let host:RelationshipReviewHost|null=null;
const listeners=new Set<()=>void>();
const notify=()=>listeners.forEach(f=>f());
export function publishRelationshipReviewHost(value:RelationshipReviewHost){host=value;notify();return()=>{if(host===value){host=null;notify();}};}
export function useRelationshipReviewHost(){return useSyncExternalStore(f=>{listeners.add(f);return()=>{listeners.delete(f);};},()=>host,()=>null);}
