import {useState, type ReactNode} from 'react';
import type {ManualCombatProfile} from './ManualCombatTypes';

/** Profile descriptors are frozen by creation, so every participant shares them. */
export function ManualCombatProfileForm({disabled,onCreate,inline=false}:{disabled:boolean;inline?:boolean;onCreate:(title:string,profile:ManualCombatProfile)=>Promise<void>}) {
  const [title,setTitle]=useState('Crossing under pressure');
  const [system,setSystem]=useState('Crossing');
  const [rounds,setRounds]=useState(false);
  const [pacing,setPacing]=useState<'ordered'|'side'|'spotlight'>('ordered');
  const [stats,setStats]=useState([{id:'position',label:'Position',type:'text' as 'text'|'integer'},{id:'resolve',label:'Resolve',type:'integer' as 'text'|'integer'}]);
  const [resources,setResources]=useState([{id:'stress',label:'Stress'},{id:'momentum',label:'Momentum'}]);
  const [error,setError]=useState<string|null>(null),[busy,setBusy]=useState(false);
  const [expanded,setExpanded]=useState(false);
  async function create() {
    if(!title.trim()||!system.trim()||[...stats,...resources].some(field=>!field.label.trim()))return;
    setBusy(true);setError(null);
    try {await onCreate(title.trim(),{
      schema:'dmb_combat_profile_v2',profile_id:crypto.randomUUID(),name:system.trim(),system_id:crypto.randomUUID(),revision:1,
      stats:stats.map(field=>({field_id:field.id,label:field.label.trim(),value_type:field.type,initial:null})),
      resources:resources.map(field=>({field_id:field.id,label:field.label.trim(),initial:{current:null,minimum:null,maximum:null}})),
      pacing:pacing==='ordered'?{mode:'ordered',rounds}:{mode:pacing,rounds:false},
    });setExpanded(false);}catch(caught){setError(String(caught));}finally{setBusy(false);}
  }
  const fields: ReactNode = <>
    <p>Choose the values your table uses. This profile is pinned when the encounter is created; participant values remain editable.</p>
    <fieldset disabled={disabled||busy}><legend>Encounter profile</legend>
      <label>Encounter name<input maxLength={160} value={title} onChange={event=>setTitle(event.target.value)}/></label>
      <label>System name<input maxLength={80} value={system} onChange={event=>setSystem(event.target.value)}/></label>
      <label>Turn structure<select value={pacing} onChange={event=>setPacing(event.target.value as 'ordered'|'side'|'spotlight')}>
        <option value="ordered">Ordered participants</option><option value="side">Side turns · choose who acts</option>
        <option value="spotlight">Free spotlight · no fixed sequence</option>
      </select></label>
      {pacing==='ordered'?<label><input type="checkbox" checked={rounds} onChange={event=>setRounds(event.target.checked)}/>Count rounds</label>
        :pacing==='side'?<p>Sides take turns. Choose participants within each side and pass explicitly; no rounds or action budget are inferred.</p>
        :<p>Choose any participant who is in action. Finish their spotlight whenever the fiction changes; no sequence, sides or rounds are required.</p>}
      <h4>Stats</h4>
      {stats.map((field,index)=><div key={field.id}><label>Stat {index+1}<input maxLength={80} value={field.label} onChange={event=>setStats(items=>items.map(item=>item.id===field.id?{...item,label:event.target.value}:item))}/></label>
        <select aria-label={`Type for stat ${index+1}`} value={field.type} onChange={event=>setStats(items=>items.map(item=>item.id===field.id?{...item,type:event.target.value as 'text'|'integer'}:item))}><option value="text">Text</option><option value="integer">Whole number</option></select>
        <button type="button" onClick={()=>setStats(items=>items.filter(item=>item.id!==field.id))}>Remove stat {index+1}</button></div>)}
      <button type="button" disabled={stats.length>=32} onClick={()=>setStats(items=>[...items,{id:crypto.randomUUID(),label:'',type:'integer'}])}>Add stat</button>
      <h4>Resources</h4><p>Each resource has an editable current value and optional minimum and maximum.</p>
      {resources.map((field,index)=><div key={field.id}><label>Resource {index+1}<input maxLength={80} value={field.label} onChange={event=>setResources(items=>items.map(item=>item.id===field.id?{...item,label:event.target.value}:item))}/></label><button type="button" onClick={()=>setResources(items=>items.filter(item=>item.id!==field.id))}>Remove resource {index+1}</button></div>)}
      <button type="button" disabled={resources.length>=16} onClick={()=>setResources(items=>[...items,{id:crypto.randomUUID(),label:''}])}>Add resource</button>
      <button type="button" disabled={!title.trim()||!system.trim()||[...stats,...resources].some(field=>!field.label.trim())} onClick={()=>void create()}>{busy?'Creating…':'Create manual encounter'}</button>
    </fieldset>{error&&<p role="alert">{error}</p>}
  </>;
  if (inline) return <div className="manual-combat-profile">{fields}</div>;
  return <details className="manual-combat-profile" open={expanded} onToggle={event=>setExpanded(event.currentTarget.open)}>
    <summary>Create for another system</summary>
    {fields}
  </details>;
}
