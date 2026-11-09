import {useSyncExternalStore} from 'react';
import type {ConversationConnectedPageProposal} from '../api/types';
import type {SavedExcerptOrigin} from '../api/connectedPageApi';
export type ConnectedPageReviewSeed={worldId:string;ownerDocumentId:string;sourceTurnId:string;proposal:ConversationConnectedPageProposal;origin:SavedExcerptOrigin};
export type ConnectedPageReviewHost={worldId:string;documentId:string;open:(seed:ConnectedPageReviewSeed)=>void};
// Ephemeral scoped registrations: opening a source reader must not replace the
// Plan's review owner. This contains no proposal, publication or recovery state.
const hosts=new Map<string,ConnectedPageReviewHost[]>();
const key=(worldId:string,documentId:string)=>JSON.stringify([worldId,documentId]);
const listeners=new Set<()=>void>();
const notify=()=>listeners.forEach(f=>f());
export function publishConnectedPageReviewHost(value:ConnectedPageReviewHost){
 const scope=key(value.worldId,value.documentId),values=hosts.get(scope)??[];
 hosts.set(scope,[...values,value]);notify();
 return()=>{const retained=(hosts.get(scope)??[]).filter(v=>v!==value);if(retained.length)hosts.set(scope,retained);else hosts.delete(scope);notify();};
}
export function useConnectedPageReviewHost(worldId:string,documentId:string){
 return useSyncExternalStore(f=>{listeners.add(f);return()=>{listeners.delete(f);};},()=>hosts.get(key(worldId,documentId))?.at(-1)??null,()=>null);
}
