import {useState,type ReactNode} from 'react';
import './SurfaceObjectMenu.css';

/** Shared home for object diagnostics. Recovery actions remain with the author. */
export function SurfaceObjectMenu({label,children}:{label:string;children:ReactNode}){
 const [open,setOpen]=useState(false),[developer,setDeveloper]=useState(false);
 return <details className="surface-object-menu" onToggle={event=>setOpen(event.currentTarget.open)}>
  <summary aria-label={label} title={label}><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></summary>
  {open&&<div className="surface-object-menu__panel"><label><input type="checkbox" checked={developer} onChange={event=>setDeveloper(event.target.checked)}/> Developer</label>
   {developer&&children}
  </div>}
 </details>;
}
