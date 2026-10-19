import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, afterAll, expect, it, vi } from "vitest";
import { WorkspaceConflictRecovery } from "./WorkspaceConflictRecovery";
import type { WorkspaceConflictReview } from "./workspaceConflictRecovery";
const proto=Object.getPrototypeOf(document.createElement("dialog"));
const original=Object.getOwnPropertyDescriptor(proto,"showModal");
const originalCreate=Object.getOwnPropertyDescriptor(URL,"createObjectURL");
const originalRevoke=Object.getOwnPropertyDescriptor(URL,"revokeObjectURL");
beforeAll(()=>{
 Object.defineProperty(proto,"showModal",{configurable:true,value(this:HTMLDialogElement){this.setAttribute("open","");}});
 Object.defineProperty(URL,"createObjectURL",{configurable:true,value:()=>"blob:test"});
 Object.defineProperty(URL,"revokeObjectURL",{configurable:true,value:()=>{}});
});
afterAll(()=>{
 for(const [object,key,descriptor] of [[proto,"showModal",original],[URL,"createObjectURL",originalCreate],[URL,"revokeObjectURL",originalRevoke]] as const){ if(descriptor)Object.defineProperty(object,key,descriptor);else Reflect.deleteProperty(object,key); }
});
const review={documentId:"one",fence:"frozen",local:{base_revision:1,exported_markdown:"Unsaved local NPC",tiptap_json:{type:"doc"},exported_markdown_authoritative:true},saved:{loaded_revision:2,markdown:"Saved NPC"}} as WorkspaceConflictReview;
it("opens an enabled comparison in conflict with cancel leaving both copies alone",()=>{
 const resolve=vi.fn();render(<WorkspaceConflictRecovery recovery={{prepare:()=>review,resolve,protectedCopies:null}}/>);
 fireEvent.click(screen.getByRole("button",{name:"Review conflicting copies"}));
 const dialog=screen.getByRole("dialog",{name:"Choose a working copy"});
 expect(within(dialog).getByText("Unsaved local NPC")).toBeInTheDocument(); expect(within(dialog).getByText("Saved NPC")).toBeInTheDocument();
 expect(within(dialog).getByRole("button",{name:"Use saved version"})).toBeEnabled();expect(within(dialog).getByRole("button",{name:"Use browser draft"})).toBeEnabled();
 expect(within(dialog).getByRole("link",{name:"Download protected copies"})).toHaveAttribute("download");
 fireEvent.click(within(dialog).getByRole("button",{name:"Cancel"}));expect(screen.queryByRole("dialog")).not.toBeInTheDocument();expect(resolve).not.toHaveBeenCalled();
});
it("passes the frozen review and explicit choice to the owner and shows a refusal",async()=>{
 const resolve=vi.fn().mockRejectedValue(new Error("Saved version changed"));render(<WorkspaceConflictRecovery recovery={{prepare:()=>review,resolve,protectedCopies:null}}/>);
 fireEvent.click(screen.getByRole("button",{name:"Review conflicting copies"}));fireEvent.click(screen.getByRole("button",{name:"Use saved version"}));
 expect(await screen.findByRole("alert")).toHaveTextContent("Saved version changed");expect(resolve).toHaveBeenCalledWith(review,"saved");expect(screen.getByRole("dialog")).toBeInTheDocument();
});
