import {createContext,useContext,type ReactNode} from 'react';
import type {WorkPlan,WorkDispatch} from '../../api/conversationWorkPlanApi';
import type {ReviewedStepReference} from '../../api/types';
export interface WorkPlanHost {
  worldId:string;documentId:string;editable:boolean;busy:boolean;
  canContinue?:boolean;beginContinuation?:(plan:WorkPlan)=>()=>boolean;
  conversationId:string|null;activeConversationId:string|null;
  onContinue:(plan:WorkPlan,dispatch:WorkDispatch,reference:ReviewedStepReference|null)=>void;
  openReply?:(turnId:string)=>void;
  openConversation?:(conversationId:string)=>void;
}
const Context=createContext<WorkPlanHost|null>(null);
export function WorkPlanHostProvider({host,children}:{host:WorkPlanHost;children:ReactNode}){
  return <Context.Provider value={host}>{children}</Context.Provider>;
}
export const useWorkPlanHost=()=>useContext(Context);
