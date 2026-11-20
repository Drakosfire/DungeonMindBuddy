import {useEffect,useState} from 'react';
import {previewSession,type PreparationPreview,type SessionSource,type WorldSessionRequest} from './runEncountersApi';
import {exactIntent} from './exactIntent';

export function WorldSessionPreparation({worldId,source,entrySceneId,onChange,disabled=false}:{worldId:string;source:SessionSource;entrySceneId?:string|null;onChange:(request:WorldSessionRequest|null)=>void;disabled?:boolean}){
 const [preview,setPreview]=useState<PreparationPreview|null>(null),[message,setMessage]=useState('');
 const sourceKey=exactIntent(source);
 useEffect(()=>{let live=true;onChange(null);setPreview(null);setMessage('Loading saved preparation…');
  previewSession(worldId,source,entrySceneId).then(result=>{if(!live)return;setPreview(result);setMessage('');onChange(result.request);}).catch(error=>{if(live)setMessage(String(error));});
  return()=>{live=false;};
 },[worldId,sourceKey,entrySceneId]);
 return <section aria-label="Session preparation"><h3>Prepare this session</h3>
 <p>Capture these saved encounters for this session. Combat starts only when you choose it in Play.</p>
 {message&&<p role="status">{message}</p>}
 {preview&&<><label>Begin at <select disabled={disabled} value={preview.request.entry_scene_id??''} onChange={event=>{const next={...preview,request:{...preview.request,entry_scene_id:event.target.value||null}};setPreview(next);onChange(next.request);}}>
 {!preview.scenes.length&&<option value="">Opening Beat</option>}{preview.scenes.map(scene=><option key={scene.scene_id} value={scene.scene_id}>{scene.name}</option>)}</select></label>
 <ul>{preview.scenes.map(scene=><li key={scene.scene_id}><strong>{scene.name}</strong>{scene.template?<label><input type="checkbox" disabled={disabled} checked={!!preview.request.encounters.find(choice=>choice.scene_id===scene.scene_id)?.template} onChange={event=>{const next={...preview,request:{...preview.request,encounters:preview.request.encounters.map(choice=>choice.scene_id===scene.scene_id?{...choice,template:event.target.checked?scene.template:null}:choice)}};setPreview(next);onChange(next.request);}}/>{scene.encounter_name} · version {scene.template.revision}{scene.enemies.length?` · ${scene.enemies.join(', ')}`:''}</label>:<span> · No prepared encounter</span>}</li>)}</ul>
 {preview.excluded_orphan_count>0&&<p>{preview.excluded_orphan_count} encounter links belong to scenes absent from this saved source and are excluded.</p>}</>}
 </section>;
}
