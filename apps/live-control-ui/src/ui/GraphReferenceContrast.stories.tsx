import { useMemo, useState } from "react";
import { GraphNodeChipRuntimeProvider, GraphNodeHoverToken, presentationForNodeId } from "../graphReference";
import type { GraphProjectionNodeView } from "../api/types";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { PlanSurfaceCanvasFrame } from "../planSurface/components/PlanSurfaceCanvas";
import "../styles.css";
import "../planSurface/planSurface.css";
import "../tiptap/prepMarkdownThemes.css";

const roles = [
  ["location", "Ironveil Warehouse"], ["person", "Lysandra"], ["pc", "Thrin"],
  ["faction", "Questionable Company"], ["item", "Sleeping potion"], ["node", "Reference"],
] as const;
const nodeViews: Record<string, GraphProjectionNodeView> = Object.fromEntries(roles.map(([role,label]) => [role, {
  node_id:role,label,kind:role,role,summary:"Isolated styling fixture, not native Graph data.",
  aliases:[],source_domains:[],evidence_badges:[],adjacency:[],anchored_to_focus_session:false,
}]));
const markdown = "## Existing Graph references\n\n" + roles.map(([role,label]) => `[${label}](dmb-node:${role})`).join(" · ") + "\n\nInline references retain their role tint and normal activation.";
const content = markdownToTiptapDoc(markdown,{parseGraphNodeLinks:true}).doc;

function ContrastFixture({paper}:{paper:boolean}) {
  const [selected,setSelected]=useState<string|null>(null);
  const runtime=useMemo(()=>({nodeViews,activeNodeId:selected,onSelectNode:setSelected}),[selected]);
  const control=presentationForNodeId(nodeViews,"location","Ironveil Warehouse");
  return <div style={{padding:16,maxWidth:"100%"}}>
    <GraphNodeChipRuntimeProvider value={runtime}>
      <div className={paper?"world-owned-plan":""} data-contrast-surface={paper?"paper":"slate"}>
        <div className="world-plan-document-view">
        <PlanSurfaceCanvasFrame identityLabel={paper?"Existing parchment Plan surface":"Existing slate Markdown surface"}
          themeId={paper?"mireward-runbook":"command"} className={paper?"world-owned-plan__canvas":""}>
          <MarkdownEditorCore content={content} editable={false} documentKey={paper?"paper-fixture":"slate-fixture"}/>
          <div className="recap-node-hover-card" data-contrast-control="dark-hover" style={{display:"block",position:"relative",transform:"none",margin:16}}>
            <GraphNodeHoverToken presentation={control} label="Dark hover reference" pinned={false} onSelect={()=>setSelected("hover-control")}/>
          </div>
        </PlanSurfaceCanvasFrame>
        </div>
      </div>
      <div data-contrast-control="non-themed" style={{background:"#151b25",padding:16,marginTop:16}}>
        <GraphNodeHoverToken presentation={control} label="Unthemed slate reference" pinned={false} onSelect={()=>setSelected("un-themed-control")}/>
      </div>
      <p role="status">{selected?`Selected ${selected}`:"No reference selected"}</p>
    </GraphNodeChipRuntimeProvider>
  </div>;
}
export const Parchment = () => <ContrastFixture paper/>;
export const Slate = () => <ContrastFixture paper={false}/>;
