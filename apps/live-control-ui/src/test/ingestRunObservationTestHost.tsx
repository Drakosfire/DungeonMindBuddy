import { useEffect, useRef, useState, type ComponentProps } from 'react';
import { getExtractionRun } from '../api/liveApi';
import { useSelectedWorld } from '../selectedWorld/SelectedWorldContext';
import type { IngestInitialRunObservation } from '../ingestSurface/ingestInitialRunObservation';
import { GraphReviewWorkbenchModule } from '../planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule';
import { assertExactRunHandoff, parseGraphReviewRunHandoff } from '../planSurface/graphReviewWorkbench/graphReviewRunSelection';

/** Explicit test owner for direct module fixtures; production has only the page owner. */
export function IngestRunObservationTestHost(props: Omit<ComponentProps<typeof GraphReviewWorkbenchModule>, 'initialRunObservation'>) {
  const selected = useSelectedWorld();
  const worldId = selected.kind === 'managed' ? selected.worldId : null;
  const [, rerender] = useState(0);
  const search = props.locationSearch ?? window.location.search;
  const key = JSON.stringify([worldId, search]);
  const navigation = useRef({key, generation:0});
  if (navigation.current.key !== key) navigation.current = {key, generation:navigation.current.generation+1};
  const generation = navigation.current.generation;
  const owner = {worldId, search, generation, accessGeneration:0};
  const [saved, setSaved] = useState<IngestInitialRunObservation>({status:'loading',owner});
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const owner = {worldId, search, generation, accessGeneration:0};
    if (selected.kind === "loading" || selected.kind === "error") {setSaved({status:"loading",owner});return;}
    const handoff = parseGraphReviewRunHandoff(search);
    if (!handoff) {setSaved({status:'not_applicable',owner});return;}
    const errors = assertExactRunHandoff(handoff);
    if (errors.length) {setSaved({status:'error',owner,message:errors.join('; ')});return;}
    void getExtractionRun(handoff.extractionRunId,controller.signal).then(run=>{
      if(active&&!controller.signal.aborted&&navigation.current.generation===generation)setSaved({status:'ready',owner,run});
    }).catch(error=>{if(active&&!controller.signal.aborted)setSaved({status:'error',owner,message:String(error.message??error)})});
    return()=>{active=false;controller.abort()};
  },[worldId,search,generation,selected.kind]);
  const observation = saved.owner.worldId===worldId&&saved.owner.search===search&&saved.owner.generation===generation
    ? saved : {status:'loading' as const,owner};
  return <GraphReviewWorkbenchModule {...props} locationSearch={search} initialRunObservation={observation}
    onLocationSearchChange={value=>{props.onLocationSearchChange?.(value);rerender(n=>n+1)}} />;
}
