import {act, renderHook} from "@testing-library/react";
import {expect,it} from "vitest";
import {announceWorkspaceInventoryChange,useWorkspaceInventoryVersion} from "./workspaceInventoryChange";
it("invalidates only the selected World inventory, with no editor or selection mutation",()=>{
 const hook=renderHook(({world})=>useWorkspaceInventoryVersion(world),{initialProps:{world:"elderwyld"}});
 act(()=>announceWorkspaceInventoryChange("other"));expect(hook.result.current).toBe(0);
 act(()=>announceWorkspaceInventoryChange("elderwyld"));expect(hook.result.current).toBe(1);
 hook.rerender({world:"other"});expect(hook.result.current).toBe(0);
 act(()=>announceWorkspaceInventoryChange("elderwyld"));expect(hook.result.current).toBe(0);
 act(()=>announceWorkspaceInventoryChange("other"));expect(hook.result.current).toBe(1);
 hook.unmount();
});
