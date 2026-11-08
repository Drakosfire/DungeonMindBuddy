import {useEffect,useRef,useState} from 'react';
import {SavedMechanicsRevisionEditor} from './revision/SavedMechanicsRevisionEditor';
import './SavedStatblockDialog.css';

/** One existing editor survives dialog visibility changes; no second working copy. */
export function SavedStatblockDialog({worldId,draftId}:{worldId:string;draftId:string}) {
  const dialog=useRef<HTMLDialogElement>(null);
  const [open,setOpen]=useState(false),[openedOnce,setOpenedOnce]=useState(false),[expanded,setExpanded]=useState(false);
  useEffect(()=>{
    const node=dialog.current;
    if(open&&node&&!node.open)node.showModal();
    else if(!open&&node?.open)node.close();
  },[open]);
  return <>
    <button type="button" onClick={()=>{setOpenedOnce(true);setOpen(true);}}>Open statblock</button>
    <dialog ref={dialog} className={`saved-statblock-dialog${expanded?' saved-statblock-dialog--expanded':''}`}
      aria-label="Saved statblock editor" onClose={()=>setOpen(false)}
      onKeyDown={event=>{if(event.key==='Escape')event.stopPropagation();}}>
      <header>
        <strong>Statblock</strong>
        <div>
          <button type="button" aria-pressed={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded?'Restore size':'Expand statblock'}</button>
          <button type="button" autoFocus aria-label="Close statblock" onClick={()=>setOpen(false)}>×</button>
        </div>
      </header>
      <div className="saved-statblock-dialog__body">
        {openedOnce&&<SavedMechanicsRevisionEditor key={`${worldId}:${draftId}`} worldId={worldId} draftId={draftId} autoLoad/>}
      </div>
    </dialog>
  </>;
}
