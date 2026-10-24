import {useRef,useState} from 'react';

/** Explicitly send a terminal question through the current sender, not its old request. */
export function ConversationRecovery({question,blocked,onRetry}: {
  question:string;blocked:boolean;onRetry:(question:string)=>Promise<void>;
}) {
  const running=useRef(false);const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);
  async function retry(){
    if(blocked||running.current)return;
    running.current=true;setBusy(true);setError(null);
    try{await onRetry(question);}catch(reason){setError(reason instanceof Error?reason.message:'The question could not be retried.');}
    finally{running.current=false;setBusy(false);}
  }
  return <span className="conversation-recovery">
    <button type="button" className="conversation-recovery__retry" aria-label="Retry question" aria-busy={busy}
      disabled={blocked||busy} onClick={()=>{void retry();}} title={blocked?'Another request is still being checked.':'Retry question'}>
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 7v5h-5M20 12a8 8 0 1 0-2.3 5.7M20 12l-3-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
    </button>
    {error?<span role="alert">{error}</span>:null}
  </span>;
}
