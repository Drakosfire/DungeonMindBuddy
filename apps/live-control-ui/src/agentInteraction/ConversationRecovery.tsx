import {useRef,useState} from 'react';
import type {TurnRetryContext} from '../api/conversationRetryApi';

export function retryUnavailableMessage(context: TurnRetryContext | null | undefined): string {
  switch (context?.reason) {
    case 'not_terminal': return 'This request has not finished. Check its status before retrying. Nothing was sent.';
    case 'unknown_outcome': return 'Buddy cannot confirm the earlier request’s outcome. Check its details before trying again. Nothing was sent.';
    case 'existing_result': return 'This request already has a result. Inspect it before continuing. Nothing was sent.';
    case 'reviewed_step': return 'This request belongs to a reviewed plan step. Continue from that plan. Nothing was sent.';
    case 'retried': return 'This request already has a later attempt. Open the later attempt to continue. Nothing was sent.';
    case 'inactive': return 'This conversation is no longer active. Open it as the active conversation before continuing. Nothing was sent.';
    case 'unverified': return 'Buddy cannot verify the earlier request’s state. Inspect its details before continuing. Nothing was sent.';
    default: return 'Buddy cannot verify whether this saved request can be retried. Refresh the conversation and inspect its details. Nothing was sent.';
  }
}

/** Explicitly send a terminal question through the current sender, not its old request. */
export function ConversationRecovery({question,blocked,onRetry,label}: {
  question:string;blocked:boolean;label?:string;onRetry:(question:string)=>Promise<void>;
}) {
  const running=useRef(false);const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);
  async function retry(){
    if(blocked||running.current)return;
    running.current=true;setBusy(true);setError(null);
    try{await onRetry(question);}catch(reason){setError(reason instanceof Error?reason.message:'The question could not be retried.');}
    finally{running.current=false;setBusy(false);}
  }
  return <span className="conversation-recovery">
    <button type="button" className={label ? undefined : "conversation-recovery__retry"} aria-label={label ?? "Retry question"} aria-busy={busy}
      disabled={blocked||busy} onClick={()=>{void retry();}} title={blocked?'This request is not ready to continue.':label ?? 'Retry question'}>
      {label ?? <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 7v5h-5M20 12a8 8 0 1 0-2.3 5.7M20 12l-3-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>}
    </button>
    {error?<span role="alert">{error}</span>:null}
  </span>;
}
