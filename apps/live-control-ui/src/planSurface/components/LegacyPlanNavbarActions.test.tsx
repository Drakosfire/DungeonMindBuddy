import {fireEvent,render,screen} from "@testing-library/react";
import {expect,it,vi} from "vitest";
import {SurfaceContextProvider,SurfaceContextHost} from "../../surfaceInteraction/contextHost";
import {LegacyPlanNavbarActions} from "./LegacyPlanNavbarActions";
import {fixtureWorkspaceDocumentRecord} from "../config/planSessionDescriptor";
import type {WorkspaceDocumentAuthoringValue} from "../../workspaceDocument/useWorkspaceDocumentAuthoring";
function mount(dirty=false){
 const saveMarkdown=vi.fn();const record=fixtureWorkspaceDocumentRecord();
 const authoring={record,documentKey:record.document_id,phase:"ready_clean",dirty,error:null,saveDisabled:false,saveMarkdown,snapshot:{loaded_revision:record.revision}} as unknown as WorkspaceDocumentAuthoringValue;
 render(<SurfaceContextProvider><LegacyPlanNavbarActions authoring={authoring} liveSession={22} memorySession={null}/><SurfaceContextHost/></SurfaceContextProvider>);
 return saveMarkdown;
}
it("publishes root Plan save and delete without Draft metadata",()=>{
 const save=mount();fireEvent.click(screen.getByRole("button",{name:"Save Plan"}));
 expect(save).toHaveBeenCalledOnce();expect(screen.getByRole("button",{name:"Delete",exact:true})).toBeEnabled();
 expect(screen.queryByText("Draft")).not.toBeInTheDocument();expect(screen.queryByText("Saved")).not.toBeInTheDocument();
});
it("blocks deletion while authoring has a local edit",()=>{mount(true);expect(screen.getByRole("button",{name:"Delete",exact:true})).toBeDisabled();});
