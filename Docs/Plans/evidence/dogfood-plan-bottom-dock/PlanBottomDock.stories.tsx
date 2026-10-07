import { useLayoutEffect, useState } from "react";
import { PlanSurfacePage } from "../../../../apps/live-control-ui/src/planSurface/PlanSurfacePage";
import { AgentInteractionProvider } from "../../../../apps/live-control-ui/src/agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../../../../apps/live-control-ui/src/agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "../../../../apps/live-control-ui/src/agentInteraction/AgentInteractionChrome";
import { SelectedWorldProvider } from "../../../../apps/live-control-ui/src/selectedWorld/SelectedWorldContext";
import { SurfaceContextProvider } from "../../../../apps/live-control-ui/src/surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../../../../apps/live-control-ui/src/surfaceInteraction/peekHost";
import "../../../../apps/live-control-ui/src/styles.css";
import "../../../../apps/live-control-ui/src/tiptap/prepMarkdownThemes.css";

const world="dogfood-layout-fixture",doc="00000000-0000-4000-8000-000000000029",revision="00000000-0000-4000-8000-000000000004";
const markdown="# Campaign 2 — Session 29\n\n<!-- dmb-playable-element:v2 kind=beat id=beat:siege beat_kind=spine -->\n## The Last Hands of the Siege\nEnd the immediate danger and give the players room to choose.\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:warehouse-tail -->\n### Something Is Still Moving\n#### Situation\nThe main assault has broken. Two transformed refugees are escaping with sleeping victims.\n\n> [!READ-ALOUD]\n> Smoke hangs in the warehouse yard. Someone calls for help.\n\n#### Do now\nWhat do you do?\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:count -->\n### Count the Living\nCount the survivors together.\n";
const record={schema_version:"dmb_world_owned_plan_record_v2",scope_mode:"world",document_id:doc,title:"Campaign 2 — Session 29",campaign_id:null,world_id:world,target_session:null,kind:"plan",target_relpath:"out/fixture.md",status:"active",content_status:"committed",revision:4,created_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z"};
const basis={schema_version:"dmb_workspace_committed_revision_v2",scope_mode:"world",world_id:world,campaign_id:null,document_id:doc,kind:"plan",title:record.title,status:"active",object_revision:4,work_revision_id:revision,revision_n:4,markdown,content_sha256:"b".repeat(64),has_divergent_working_copy:false,target_relpath:record.target_relpath};
const primary={resolution:"resolved",kind:"plan",object_id:doc,revision:null,content_sha256:null,object_revision:4,work_revision_id:revision,revision_n:4};
const empty={resolution:"absent",kind:null,object_id:null,revision:null,content_sha256:null,object_revision:null,work_revision_id:null,revision_n:null};
function Preview(){
  const [ready,setReady]=useState(false);
  useLayoutEffect(()=>{
    const original=window.fetch,href=window.location.href;
    const params=new URLSearchParams(window.location.search);params.set("world",world);params.set("documentId",doc);
    window.history.replaceState({},"",`${window.location.pathname}?${params}`);
    window.fetch=async(input,options)=>{
      const url=new URL(typeof input==="string"?input:input instanceof URL?input.href:input.url,window.location.href);let value:unknown;let status=200;
      if(url.pathname==="/api/live/agent/local-session")value={status:"active",csrf_token:"isolated-fixture-only"};
      else if(url.pathname==="/api/live/world-containers")value={schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:world,name:"Elderwyld · isolated fixture",source_root_relpath:"corpus/fixture",created_at:"2026-01-01T00:00:00Z"}]};
      else if(url.pathname.endsWith("world-plans"))value={schema_version:"dmb_workspace_document_registry_v2",scope_mode:"world",world_id:world,records:[record]};
      else if(url.pathname.endsWith("committed-revision"))value=basis;
      else if(url.pathname.endsWith("snapshot"))value={schema_version:"dmb_workspace_document_snapshot_v2",record,markdown,content_sha256:"b".repeat(64),file_fingerprint:"fixture",file_exists:true,loaded_revision:4};
      else if(url.pathname.endsWith(`/workspace-documents/${doc}`))value=record;
      else if(url.pathname.endsWith("plan-view"))value={schema_version:"dmb_managed_world_plan_context_v2",scope_mode:"world",world_id:world,campaign_id:null,session:null,authoritative:false,generated_at:"2026-01-01T00:00:00Z",derived_from:["fixture"],timeline:[]};
      else if(url.pathname.endsWith("conversation"))value={schema:"dmb_agent_conversation_history_v1",world_id:world,conversation_state:"active",conversation_id:"00000000-0000-4000-8000-000000000031",active_conversation_id:"00000000-0000-4000-8000-000000000031",pointer_revision:1,next_before_sequence:null,turns:[{turn_id:"00000000-0000-4000-8000-000000000032",sequence:1,lifecycle_status:"completed",user_text:"How can we resolve this quickly?",assistant_text:"Isolated reply fixture: let the players organize a fast rescue line. Keep the saved preparation distinct from any proposed outcome.",provenance:{world_id:world,surface_resolution:"resolved",surface_id:"plan",surface_instance_id:"fixture-instance",primary_work:primary,supporting_work:[],selected_object:empty}}]};
      else {status=503;value={error:"Isolated route unavailable; no backend or provider request was forwarded."};}
      return new Response(JSON.stringify(value),{status,headers:{"Content-Type":"application/json"}});
    };
    setReady(true);return()=>{window.fetch=original;window.history.replaceState({},"",href);};
  },[]);
  if(!ready)return null;
  return <div style={{height:"calc(100vh - 48px)",minHeight:0}} data-fixture-no-network="true"><SelectedWorldProvider locationSnapshot={`/plan?world=${world}&documentId=${doc}`}><AgentInteractionProvider><AskPluginSlotProvider><SurfaceContextProvider><PeekRegionProvider><PlanSurfacePage/><AgentInteractionChrome/></PeekRegionProvider></SurfaceContextProvider></AskPluginSlotProvider></AgentInteractionProvider></SelectedWorldProvider></div>;
}
export const SavedPlan=()=> <Preview/>;
