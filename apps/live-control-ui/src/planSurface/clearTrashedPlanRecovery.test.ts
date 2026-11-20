import { beforeEach, expect, it, vi } from "vitest";
import { clearTrashedPlanRecovery } from "./clearTrashedPlanRecovery";
const world="elderwyld", key=`dmb:world-plan-local-draft:v2:${world}`;
const basis={document_id:"plan-a",revision:7,title:"Disposable",markdown:"# Exact source\r\n",edit_generation:3};
const draft={schema_version:"dmb_plan_promotion_recovery_v2",scope_mode:"world",world_id:world,...basis,pending_write:null,create_uncertain:false,uncertain_create_draft:null};
beforeEach(()=>{localStorage.clear();vi.restoreAllMocks();});
it("retires only the exact clean recovery cache after confirmed Trash",()=>{
 localStorage.setItem(key,JSON.stringify(draft));expect(clearTrashedPlanRecovery(world,basis)).toBe(true);expect(localStorage.getItem(key)).toBeNull();
});
it.each([
 {document_id:"other-plan"},{world_id:"other-world"},{revision:8},{title:"New title"},{markdown:"Newer unsaved prose"},
 {edit_generation:4},{pending_write:{phase:"commit"}},{create_uncertain:true},{uncertain_create_draft:{markdown:"Recovered"}},
])("preserves a changed, pending or uncertain cache: %j",change=>{
 const raw=JSON.stringify({...draft,...change});localStorage.setItem(key,raw);
 expect(clearTrashedPlanRecovery(world,basis)).toBe(false);expect(localStorage.getItem(key)).toBe(raw);
});
it("preserves a cache changed while it is checked",()=>{
 const newer=JSON.stringify({...draft,edit_generation:4});const getter=vi.spyOn(Storage.prototype,"getItem").mockReturnValueOnce(JSON.stringify(draft)).mockReturnValueOnce(newer);
 const remove=vi.spyOn(Storage.prototype,"removeItem");expect(clearTrashedPlanRecovery(world,basis)).toBe(false);expect(remove).not.toHaveBeenCalled();getter.mockRestore();
});
it("preserves unrecognized recovery data",()=>{
 localStorage.setItem(key,"not json");expect(clearTrashedPlanRecovery(world,basis)).toBe(false);expect(localStorage.getItem(key)).toBe("not json");
});
