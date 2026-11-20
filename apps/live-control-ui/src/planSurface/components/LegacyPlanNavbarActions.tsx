import { useMemo } from "react";
import type { WorkspaceDocumentAuthoringValue } from "../../workspaceDocument/useWorkspaceDocumentAuthoring";
import { SurfaceContextModule, useOptionalSurfaceContext, useSurfaceContextContribution } from "../../surfaceInteraction/contextHost";
import { SurfaceNavbarIconButton } from "../../surfaceInteraction/contextHost/SurfaceNavbarIconButton";
import { buildPlanSurfaceIdentity } from "../../agentInteraction/projectionSurfacePublication";
import { DurableSaveStatus, type DurableSaveState } from "../../components/DurableSaveStatus";
import { WorkspaceTrashControl } from "../../workspaceLifecycle/WorkspaceTrashControl";

export function LegacyPlanNavbarActions(props: {authoring:WorkspaceDocumentAuthoringValue;liveSession:number;memorySession:number|null}) {
  const host=useOptionalSurfaceContext();
  return host ? <Actions {...props} /> : null;
}
function Actions({authoring:a,liveSession,memorySession}:{authoring:WorkspaceDocumentAuthoringValue;liveSession:number;memorySession:number|null}) {
  const record=a.record;
  const identity=useMemo(()=>buildPlanSurfaceIdentity({documentId:record?.document_id ?? a.documentKey,campaignId:record?.campaign_id ?? "",liveSession,memorySession}),[record?.document_id,record?.campaign_id,a.documentKey,liveSession,memorySession]);
  const content=useMemo(()=>{
    const busy=["preparing","committing"].includes(a.phase);
    const state:DurableSaveState=a.phase==="conflict" || a.phase==="load_error" || a.phase==="save_error" || a.error ? "needs-attention"
      : busy?"saving":a.dirty?"unsaved":a.phase==="loading" || a.phase==="unloaded" || a.phase==="committed_verification_pending"?"checking":"saved";
    const showStatus=state!=="saved" || record?.content_status==="committed";
    return <SurfaceContextModule className="plan-surface-context"><div className="plan-surface-context__row">
      {showStatus?<span className="world-plan-context-toolbar__save"><DurableSaveStatus state={state} savedAt={record?.updated_at ?? null}/></span>:null}
      <SurfaceNavbarIconButton icon="save" label="Save Plan" title={a.saveDisabledReason ?? "Save Plan"} disabled={a.saveDisabled} onClick={()=>{void a.saveMarkdown();}}/>
      {record && !record.world_id && record.kind==="plan" ? <WorkspaceTrashControl campaignId={record.campaign_id} showTrash={false}
        current={{kind:"document",id:record.document_id,title:record.title,surface:"plan",revision:record.revision}}
        blocked={a.dirty || a.exportedMarkdownAuthoritative || Boolean(a.error) || !["ready_clean","committed"].includes(a.phase) || a.snapshot?.loaded_revision!==record.revision}
        onTrashed={()=>window.location.assign(`/plan?campaign=${encodeURIComponent(record.campaign_id)}`)}/> : null}
    </div></SurfaceContextModule>;
  },[a.phase,a.error,a.dirty,a.exportedMarkdownAuthoritative,a.snapshot?.loaded_revision,a.saveDisabled,a.saveDisabledReason,a.saveMarkdown,record]);
  useSurfaceContextContribution({id:"legacy-plan-document-actions",order:20,surfaceIdentity:identity,content});
  return null;
}
