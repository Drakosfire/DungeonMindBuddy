import {createContext,createElement,useCallback,useContext,useLayoutEffect,useRef,useState,useSyncExternalStore,type Dispatch,type ReactNode,type SetStateAction} from 'react';

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
    if(!value||Object.keys(value).sort().join(',')!=='drafts,schema,world_id'||value.schema!==schema||value.world_id!==worldId||!value.drafts
      ||typeof value.drafts!=='object'||Array.isArray(value.drafts)
      ||!Object.entries(value.drafts).every(([key,text])=>/^(build|plan|play):.+$/.test(key)&&typeof text==='string'))
      throw new Error('Invalid composer recovery scope or shape');
    return {...empty,drafts:value.drafts};
  } catch {
    // Unknown bytes remain intact. New typing must not erase a failed recovery.
    return {...empty,warning:COMPOSER_DRAFT_READ_WARNING,readBlocked:true};
  }
}

/** Page lifetime owns memory; sessionStorage owns only the reload copy. */
class DraftStore {
  private worlds=new Map<string|null,Snapshot>();
  private listeners=new Set<()=>void>();
  subscribe=(listener:()=>void)=>{this.listeners.add(listener);return()=>{this.listeners.delete(listener);};};
  snapshot=(worldId:string|null):Snapshot=>{
    let value=this.worlds.get(worldId);
    if(!value){value=load(worldId);this.worlds.set(worldId,value);}
    return value;
  };
  update(worldId:string|null,action:SetStateAction<Drafts>){
    const before=this.snapshot(worldId);
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
    this.worlds.set(worldId,{...before,drafts,warning});
    for(const listener of [...this.listeners])listener();
  }
}
const DraftOwner=createContext<DraftStore|null>(null);
export function ConversationComposerDraftProvider({children}:{children:ReactNode}){
  const [owner]=useState(()=>new DraftStore());
  return createElement(DraftOwner.Provider,{value:owner},children);
}

/** One active writer, retired consumer callbacks never regain authority. */
export function useConversationComposerDrafts(worldId:string|null): {
  composerDrafts:Drafts;setComposerDrafts:Dispatch<SetStateAction<Drafts>>;composerDraftWarning:string|null;
} {
  const shared=useContext(DraftOwner);
  const [isolated]=useState(()=>new DraftStore());
  const owner=shared??isolated;
  const lifecycle=useRef({owner,worldId,epoch:0,mounted:true});
  if(lifecycle.current.owner!==owner||lifecycle.current.worldId!==worldId)
    lifecycle.current={owner,worldId,epoch:lifecycle.current.epoch+1,mounted:lifecycle.current.mounted};
  const epoch=lifecycle.current.epoch;
  useLayoutEffect(()=>{lifecycle.current.mounted=true;return()=>{lifecycle.current.mounted=false;};},[owner]);
  const snapshot=useSyncExternalStore(owner.subscribe,()=>owner.snapshot(worldId),()=>owner.snapshot(worldId));
  const setComposerDrafts=useCallback<Dispatch<SetStateAction<Drafts>>>(action=>{
    const current=lifecycle.current;
    if(!current.mounted||current.owner!==owner||current.worldId!==worldId||current.epoch!==epoch)return;
    owner.update(worldId,action);
  },[owner,worldId,epoch]);
  return {composerDrafts:snapshot.drafts,setComposerDrafts,composerDraftWarning:snapshot.warning};
}
