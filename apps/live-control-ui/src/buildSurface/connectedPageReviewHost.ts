import {useSyncExternalStore} from 'react';
import type {ConversationConnectedPageProposal} from '../api/types';
import type {SavedExcerptOrigin} from '../api/connectedPageApi';
export type ConnectedPageReviewSeed={worldId:string;ownerDocumentId:string;sourceTurnId:string;proposal:ConversationConnectedPageProposal;origin:SavedExcerptOrigin};
export type ConnectedPageReviewHost={worldId:string;documentId:string;open:(seed:ConnectedPageReviewSeed)=>void};
let host:ConnectedPageReviewHost|null=null;
const listeners=new Set<()=>void>();
const notify=()=>listeners.forEach(f=>f());
export function publishConnectedPageReviewHost(value:ConnectedPageReviewHost){host=value;notify();return()=>{if(host===value){host=null;notify();}};}
export function useConnectedPageReviewHost(){return useSyncExternalStore(f=>{listeners.add(f);return()=>{listeners.delete(f);};},()=>host,()=>null);}
