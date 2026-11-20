import {useEffect,useRef,useState} from 'react';
import {listWorldCreatures,listWorldMechanicsAssociations} from '../api/liveApi';
import {worldCreatureChoiceKey,type WorldCreatureCatalog,type WorldMechanicsAssociation} from '../api/worldMechanicsTypes';
import {previewWorldCombatMechanics} from './combatApi';
import type {CombatWorldIdentity,CombatMechanicsSnapshot} from './combatTypes';
import {CombatMechanicsInspection} from './CombatMechanicsInspection';

/** Governed identity/source selection never hydrates named tracker values. */
export function ManualCombatSourcePicker({worldId,disabled,onAdd}:{worldId:string;disabled:boolean;onAdd:(identity:CombatWorldIdentity,source:CombatMechanicsSnapshot|null)=>boolean}) {
  const [catalog,setCatalog]=useState<WorldCreatureCatalog|null>(null),[associations,setAssociations]=useState<WorldMechanicsAssociation[]>([]);
  const [selected,setSelected]=useState<CombatWorldIdentity|null>(null),[snapshot,setSnapshot]=useState<CombatMechanicsSnapshot|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[query,setQuery]=useState('');
  const generation=useRef(0),alive=useRef(true);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;generation.current++;};},[]);
  async function load() {
    const epoch=++generation.current;setBusy(true);setError(null);setSnapshot(null);setSelected(null);
    try {
      const [view,records]=await Promise.all([listWorldCreatures(worldId),listWorldMechanicsAssociations(worldId)]);
      if(!alive.current||generation.current!==epoch)return;
      if(records.some(record=>record.request.target.managed_world_id!==worldId))throw new Error('Source associations belong to another World.');
      setCatalog(view);setAssociations(records);
    }catch(caught){if(alive.current&&generation.current===epoch)setError(String(caught));}
    finally{if(alive.current&&generation.current===epoch)setBusy(false);}
  }
  const association=associations.find(item=>item.request.target.node_id===selected?.node_id&&item.request.target.campaign_scope===selected?.campaign_scope);
  async function preview() {
    if(!selected||!association)return;
    const epoch=++generation.current;setBusy(true);setError(null);setSnapshot(null);
    try {
      const result=await previewWorldCombatMechanics(worldId,{association_id:association.association_id,association_version:association.version,target:selected});
      if(!alive.current||generation.current!==epoch)return;
      if(result.association_id!==association.association_id||result.association_version!==association.version
        ||!Object.entries(selected).every(([key,value])=>result.target[key as keyof CombatWorldIdentity]===value))throw new Error('Source differs from the selected World creature.');
      setSnapshot(result);
    }catch(caught){if(alive.current&&generation.current===epoch)setError(String(caught));}
    finally{if(alive.current&&generation.current===epoch)setBusy(false);}
  }
  return <details><summary>Add from Graph</summary><p>Choose a World creature. Exact source is optional and stays separate from this profile’s tracker values.</p>
    <button disabled={disabled||busy} onClick={()=>void load()}>{busy?'Loading…':'Find World creatures'}</button>
    {error&&<p role="alert">{error}</p>}
    {catalog&&<><label>Filter creatures<input value={query} onChange={event=>setQuery(event.target.value)}/></label>
      {catalog.completeness==='partial'&&<p>The current creature list is partial.</p>}
      <select aria-label="World creature" disabled={disabled||busy} value={selected?worldCreatureChoiceKey(selected):''} onChange={event=>{generation.current++;setSnapshot(null);setSelected(catalog.targets.find(target=>worldCreatureChoiceKey(target)===event.target.value)??null);}}>
        <option value="">Choose a creature…</option>{catalog.targets.filter(target=>target.label.toLowerCase().includes(query.toLowerCase())).map(target=><option key={worldCreatureChoiceKey(target)} value={worldCreatureChoiceKey(target)}>{target.label}</option>)}
      </select>
      {selected&&<><button disabled={disabled||busy||!association} onClick={()=>void preview()}>Preview exact source</button>
        {!association&&<p>No exact mechanics association is available for this creature.</p>}
        {snapshot&&<CombatMechanicsInspection snapshot={snapshot}/>}
        <button disabled={disabled||busy} onClick={()=>{if(onAdd(selected,snapshot)){setSelected(null);setSnapshot(null);}}}>Add {selected.label}{snapshot?' with exact source':' as identity only'}</button>
      </>}
    </>}
  </details>;
}
