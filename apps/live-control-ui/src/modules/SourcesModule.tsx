import {useSelectedWorld} from "../selectedWorld/SelectedWorldContext";

export function SourcesModule({campaignId}: {campaignId:string;session:number}) {
  const world = useSelectedWorld();
  const query = world.kind === "managed" ? new URLSearchParams({world:world.worldId,campaign:campaignId}) : null;
  return <section className="module-panel sources-module" data-module-id="sources">
    <h2 className="module-title">Sources</h2>
    <p>Read source material and inspect exact saved extraction work in Ingest. Extraction and reviewed Graph publication are separate steps.</p>
    {query ? <a href={"/ingest?"+query}>Open Ingest</a> : <p>Select a World to inspect its sources.</p>}
  </section>;
}
