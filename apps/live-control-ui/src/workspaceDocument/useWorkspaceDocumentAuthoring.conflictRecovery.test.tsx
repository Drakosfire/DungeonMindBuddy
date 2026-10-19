import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { getWorkspaceDocumentSnapshot, commitTiptapMarkdownWrite, prepareTiptapMarkdownWrite } from "../api/liveApi";
import type { WorkspaceDocumentSnapshot } from "../api/types";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import { buildInitialWorkspaceDocumentLocalState, workspaceDocumentStorageKey } from "../tiptap/state/tiptapLocalState";
import { conflictCopiesKey } from "./workspaceConflictRecovery";
import { useWorkspaceDocumentAuthoring } from "./useWorkspaceDocumentAuthoring";
vi.mock("../api/liveApi", () => ({ getWorkspaceDocumentSnapshot:vi.fn(), prepareTiptapMarkdownWrite:vi.fn(), commitTiptapMarkdownWrite:vi.fn() }));
const id = "11111111-1111-4111-8111-111111111111";
const snapshot: WorkspaceDocumentSnapshot = { schema_version:"dmb_workspace_document_snapshot_v1",
  record:fixtureWorkspaceDocumentRecord({document_id:id,kind:"worldbuilding_source",revision:2,content_status:"committed"}),
  loaded_revision:2, content_sha256:"server-sha", markdown:"# Saved town\n", file_fingerprint:"fingerprint", file_exists:true };
function draft() {
  return { ...buildInitialWorkspaceDocumentLocalState({documentId:id,title:"Town",campaignId:"elderwyld",targetSession:null,kind:"worldbuilding_source",surface:"build",baseRevision:1,baseContentSha256:"old",starterContent:{type:"doc",content:[{type:"paragraph",content:[{type:"text",text:"local change"}]}]}}),
    exported_markdown:"# Browser draft\n", exported_markdown_authoritative:true, dirty:true };
}
beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); vi.mocked(getWorkspaceDocumentSnapshot).mockReset().mockResolvedValue(snapshot); localStorage.setItem(workspaceDocumentStorageKey(id),JSON.stringify(draft())); });
async function open(storage?: Pick<Storage,"getItem"|"setItem"|"removeItem">) {
  const hook=renderHook(() => useWorkspaceDocumentAuthoring({documentId:id,kind:"worldbuilding_source",surface:"build",storage}));
  await waitFor(() => expect(hook.result.current.phase).toBe("conflict"));
  expect(hook.result.current.editor).toBeNull();
  return hook;
}
it.each(["saved","local"] as const)("resolves %s without an editor, protecting full copies before changing the working state",async choice => {
  const h=await open(); const before=JSON.parse(localStorage.getItem(workspaceDocumentStorageKey(id))!);
  const review=h.result.current.conflictRecovery!.prepare();
  await act(async()=>h.result.current.conflictRecovery!.resolve(review,choice));
  const stored=JSON.parse(localStorage.getItem(workspaceDocumentStorageKey(id))!);
  const copies=JSON.parse(localStorage.getItem(conflictCopiesKey(id))!);
  expect(copies.copies[0].local).toEqual(before); expect(copies.copies[0].saved).toEqual(snapshot);
  expect(stored.base_revision).toBe(2); expect(stored.base_content_sha256).toBe("server-sha");
  expect(h.result.current.phase).toBe(choice==="saved"?"ready_clean":"ready_dirty");
  if(choice==="saved") expect(stored.exported_markdown).toBe(snapshot.markdown);
  else { expect(stored.tiptap_json).toEqual(before.tiptap_json); expect(stored.exported_markdown).toBe(before.exported_markdown); expect(stored.exported_markdown_authoritative).toBe(true); }
  expect(h.result.current.conflictRecovery!.protectedCopies).toBeTruthy();
  expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled(); expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
});
it("refuses a saved version that advanced after comparison",async()=>{
 const h=await open(); const review=h.result.current.conflictRecovery!.prepare(); const raw=localStorage.getItem(workspaceDocumentStorageKey(id));
 vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue({...snapshot,loaded_revision:3});
 await expect(h.result.current.conflictRecovery!.resolve(review,"saved")).rejects.toThrow(/changed/);
 expect(localStorage.getItem(workspaceDocumentStorageKey(id))).toBe(raw); expect(localStorage.getItem(conflictCopiesKey(id))).toBeNull(); expect(h.result.current.phase).toBe("conflict");
});
it("refuses another tab's edits without replacing either copy",async()=>{
 const h=await open(); const review=h.result.current.conflictRecovery!.prepare(); const other={...draft(),exported_markdown:"newer tab"}; localStorage.setItem(workspaceDocumentStorageKey(id),JSON.stringify(other));
 await expect(h.result.current.conflictRecovery!.resolve(review,"local")).rejects.toThrow(/another tab/); expect(JSON.parse(localStorage.getItem(workspaceDocumentStorageKey(id))!)).toEqual(other);
});
it("keeps the draft intact when backup storage fails",async()=>{
 const raw=localStorage.getItem(workspaceDocumentStorageKey(id));
 const storage={getItem:(key:string)=>localStorage.getItem(key),removeItem:(key:string)=>localStorage.removeItem(key),setItem:()=>{throw new Error("Quota exceeded");}};
 const h=await open(storage); const review=h.result.current.conflictRecovery!.prepare();
 await expect(h.result.current.conflictRecovery!.resolve(review,"saved")).rejects.toThrow(/Quota/); expect(localStorage.getItem(workspaceDocumentStorageKey(id))).toBe(raw); expect(h.result.current.phase).toBe("conflict");
});
it("refuses confirmation after unmount, including an in-flight server check",async()=>{
 const h=await open(); const review=h.result.current.conflictRecovery!.prepare(); const raw=localStorage.getItem(workspaceDocumentStorageKey(id));
 let finish!:(value:WorkspaceDocumentSnapshot)=>void; vi.mocked(getWorkspaceDocumentSnapshot).mockReturnValue(new Promise(resolve=>{finish=resolve;}));
 const result=h.result.current.conflictRecovery!.resolve(review,"local"); h.unmount(); finish(snapshot);
 await expect(result).rejects.toThrow(/document changed/); expect(localStorage.getItem(workspaceDocumentStorageKey(id))).toBe(raw);
});

it("retains both protected copies if replacing the working draft cannot be verified",async()=>{
 const raw=localStorage.getItem(workspaceDocumentStorageKey(id));
 const storage={getItem:(key:string)=>localStorage.getItem(key),removeItem:(key:string)=>localStorage.removeItem(key),setItem:(key:string,value:string)=>{if(key!==workspaceDocumentStorageKey(id))localStorage.setItem(key,value);}};
 const h=await open(storage); const review=h.result.current.conflictRecovery!.prepare();
 await expect(h.result.current.conflictRecovery!.resolve(review,"saved")).rejects.toThrow(/verify/);
 expect(localStorage.getItem(workspaceDocumentStorageKey(id))).toBe(raw); expect(JSON.parse(localStorage.getItem(conflictCopiesKey(id))!).copies[0].local).toEqual(JSON.parse(raw!)); expect(h.result.current.phase).toBe("conflict");
});
it("refuses unreadable existing backups rather than overwriting them",async()=>{
 const h=await open(); const raw=localStorage.getItem(workspaceDocumentStorageKey(id));localStorage.setItem(conflictCopiesKey(id),"null");
 await expect(h.result.current.conflictRecovery!.resolve(h.result.current.conflictRecovery!.prepare(),"saved")).rejects.toThrow(/could not be read/);
 expect(localStorage.getItem(conflictCopiesKey(id))).toBe("null");expect(localStorage.getItem(workspaceDocumentStorageKey(id))).toBe(raw);
});

it("refuses a comparison belonging to a different mounted document",async()=>{
 const h=renderHook(({documentId})=>useWorkspaceDocumentAuthoring({documentId,kind:"worldbuilding_source",surface:"build"}),{initialProps:{documentId:id}});
 await waitFor(()=>expect(h.result.current.phase).toBe("conflict")); const recovery=h.result.current.conflictRecovery!;const review=recovery.prepare();const raw=localStorage.getItem(workspaceDocumentStorageKey(id));
 h.rerender({documentId:"22222222-2222-4222-8222-222222222222"});
 await expect(recovery.resolve(review,"saved")).rejects.toThrow(/document changed/);expect(localStorage.getItem(workspaceDocumentStorageKey(id))).toBe(raw);
});
