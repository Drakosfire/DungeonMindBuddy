import {useCallback,useRef,useState,type Dispatch,type SetStateAction} from 'react';

export const COMPOSER_DRAFT_WRITE_WARNING = 'This tab couldn’t save your unsent text. Keep a copy before reloading.';
export const COMPOSER_DRAFT_READ_WARNING = 'Saved unsent text couldn’t be read. Keep a copy of new typing before reloading.';
const schema = 'dmb_conversation_composer_drafts_v1';
export const composerDraftStorageKey = (worldId:string) => `dmb:conversation-composer-drafts:v1:${encodeURIComponent(worldId)}`;
type Drafts = Record<string,string>;
interface Snapshot {worldId:string|null;drafts:Drafts;warning:string|null;readBlocked:boolean}

function load(worldId:string|null):Snapshot {
  const empty:Snapshot={worldId,drafts:{},warning:null,readBlocked:false};
  if(!worldId)return empty;
  try {
    const raw=window.sessionStorage.getItem(composerDraftStorageKey(worldId));
    if(raw===null)return empty;
    const value=JSON.parse(raw);
    if(!value||value.schema!==schema||value.world_id!==worldId||!value.drafts
      ||typeof value.drafts!=='object'||Array.isArray(value.drafts)
      ||!Object.entries(value.drafts).every(([key,text])=>/^(build|plan|play):.+$/.test(key)&&typeof text==='string'))
      throw new Error('Invalid composer recovery scope or shape');
    return {...empty,drafts:value.drafts};
  } catch {
    // Unknown bytes remain intact. New typing must not erase a failed recovery.
    return {...empty,warning:COMPOSER_DRAFT_READ_WARNING,readBlocked:true};
  }
}

/** One shared owner, one browsing-tab session; no cross-tab draft writer. */
export function useConversationComposerDrafts(worldId:string|null): {
  composerDrafts:Drafts;setComposerDrafts:Dispatch<SetStateAction<Drafts>>;composerDraftWarning:string|null;
} {
  const [saved,setSaved]=useState(()=>load(worldId));
  let snapshot=saved;
  if(saved.worldId!==worldId){snapshot=load(worldId);setSaved(snapshot);}
  const current=useRef(snapshot);current.current=snapshot;
  const setComposerDrafts=useCallback<Dispatch<SetStateAction<Drafts>>>(action=>{
    const before=current.current;
    if(before.worldId!==worldId)return; // A retired World's async callback has no write authority.
    const drafts=typeof action==='function'?action(before.drafts):action;
    if(drafts===before.drafts)return;
    let warning=before.warning;
    if(worldId&&!before.readBlocked){
      try {
        const retained=Object.fromEntries(Object.entries(drafts).filter(([,text])=>text!==''));
        const key=composerDraftStorageKey(worldId);
        const bytes=Object.keys(retained).length?JSON.stringify({schema,world_id:worldId,drafts:retained}):null;
        if(bytes!==null)window.sessionStorage.setItem(key,bytes);
        else window.sessionStorage.removeItem(key);
        if(window.sessionStorage.getItem(key)!==bytes)throw new Error('Composer recovery write was not retained');
        warning=null;
      } catch {warning=COMPOSER_DRAFT_WRITE_WARNING;}
    }
    const next={...before,drafts,warning};
    current.current=next;
    setSaved(next);
  },[worldId]);
  return {composerDrafts:snapshot.drafts,setComposerDrafts,composerDraftWarning:snapshot.warning};
}
