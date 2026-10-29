import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import './ContextualAgentMenu.css';

/** Presentation primitive. The owning object supplies authorization and execution. */
export function ContextualAgentMenu({ label, open, onOpen, onClose, disabled, mode, modes, onMode,
  instructions, onInstructions, onSubmit, busy, canSubmit, submitLabel, busyLabel, children }: {
  label:string; open:boolean; onOpen:()=>void; onClose:()=>void; disabled?:boolean;
  mode:string; modes:{value:string;label:string}[]; onMode:(mode:string)=>void;
  instructions:string; onInstructions:(text:string)=>void; onSubmit:()=>void;
  busy:boolean; canSubmit:boolean; submitLabel:string; busyLabel:string; children?:ReactNode;
}) {
  const closeAction=useRef(onClose);closeAction.current=onClose;
  const trigger=useRef<HTMLButtonElement>(null);const panel=useRef<HTMLDivElement>(null);const id=useId();
  const [position,setPosition]=useState({top:0,left:0});
  function close(){onClose();trigger.current?.focus();}
  useEffect(()=>{
    if(!open)return;
    const place=()=>{const box=trigger.current?.getBoundingClientRect();if(box)setPosition({top:Math.max(8,Math.min(box.bottom+6,window.innerHeight-440)),left:Math.max(8,Math.min(box.right-360,window.innerWidth-376))});};
    const outside=(event:PointerEvent)=>{if(event.target instanceof window.Node&&!panel.current?.contains(event.target)&&!trigger.current?.contains(event.target)){closeAction.current();trigger.current?.focus();}};
    place();window.addEventListener('resize',place);window.addEventListener('scroll',place,true);document.addEventListener('pointerdown',outside,true);
    panel.current?.focus();
    return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);document.removeEventListener('pointerdown',outside,true);trigger.current?.focus();};
  },[open]);
  return <span className="contextual-agent-action">
    <button ref={trigger} type="button" className="contextual-agent-action__trigger" aria-label={`Edit ${label}`} title={`Edit ${label}`}
      aria-haspopup="dialog" aria-expanded={open} aria-controls={open?id:undefined} disabled={disabled}
      onMouseDown={event=>event.preventDefault()} onClick={()=>open?close():onOpen()}>✎</button>
    {open&&createPortal(<div ref={panel} id={id} role="dialog" aria-label={`Edit ${label}`} tabIndex={-1}
      className="contextual-agent-menu" style={position} onKeyDown={event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}}}>
      <header><strong>Edit {label}</strong><button type="button" aria-label="Close edit menu" onClick={close}>×</button></header>
      <label>Action<select value={mode} disabled={busy||!canSubmit} onChange={event=>onMode(event.target.value)}>{modes.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <label>Instructions<textarea rows={3} maxLength={16000} value={instructions} disabled={busy||!canSubmit} onChange={event=>onInstructions(event.target.value)} placeholder="Describe what you want…"/></label>
      <button type="button" disabled={busy||!canSubmit||!instructions.trim()} onClick={onSubmit}>{busy?busyLabel:submitLabel}</button>
      {children}
    </div>,document.body)}
  </span>;
}
