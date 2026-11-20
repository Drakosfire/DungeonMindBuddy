import {useCallback,useEffect,useRef,useState} from 'react';
import {constructionPlacementId,type BuildObjectConstructionProgress} from '../api/buildConstructionStream';
import type {BuildComposeBridge,CapturedBuildInsertion} from './buildComposeBridge';
import {SurfacePageProposal} from '../surface/SurfacePageProposal';
import {SurfacePlanConstructionPreview} from '../surface/SurfacePlanConstructionPreview';
import {SurfaceConstructionPreview} from '../surface/SurfaceConstructionPreview';

export function BuildConstructionPreview({progress,bridge,sourceKey,onVisible}:{progress:BuildObjectConstructionProgress;bridge:BuildComposeBridge;sourceKey:string;onVisible?:()=>void}){
  const [placement,setPlacement]=useState<CapturedBuildInsertion|null>(null);
  const stale=useRef(false);
  const [revealed,setRevealed]=useState(false);
  const reveal=useCallback(()=>{setRevealed(true);onVisible?.();},[onVisible]);
  const identity=JSON.stringify([progress.schema,constructionPlacementId(progress),progress.schema==='dmb_build_construction_v1'?progress.origin:progress.durable_turn_id,progress.provider_attempt_id]);
  useEffect(()=>{
    let active=true;stale.current=false;setPlacement(null);setRevealed(false);
    void bridge.restore(progress.basis).then(value=>{if(active&&!stale.current)setPlacement(value);}).catch(()=>undefined);
    return()=>{active=false;};
  },[bridge,sourceKey,identity]);
  if(!placement)return null;
  return <SurfacePageProposal editor={placement.editor} position={placement.basis.caret} editorJson={placement.editorJson}
    placementId={`construction:${constructionPlacementId(progress)}`} revealKey={revealed?1:0} busy focusOnReveal={false} onStale={()=>{stale.current=true;setPlacement(null);}}>
    {progress.schema!=='dmb_build_construction_v1'?<SurfacePlanConstructionPreview objective={progress.schema==='dmb_build_plan_construction_v2'?progress.objective:null} steps={progress.steps} status={progress.status} onVisible={reveal}/>:<SurfaceConstructionPreview markdown={progress.markdown} status={progress.status} onVisible={reveal}/>}
  </SurfacePageProposal>;
}
