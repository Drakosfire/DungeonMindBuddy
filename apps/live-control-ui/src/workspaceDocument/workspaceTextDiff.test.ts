import {expect,it} from "vitest";
import {diffWithContext,workspaceTextDiff} from "./workspaceTextDiff";
it("shows precisely which saved lines were removed and local lines were added",()=>{
 const rows=workspaceTextDiff("Title\nOld NPC\nEnd","Title\nNew NPC\nEnd");
 expect(rows).toEqual([{kind:"same",text:"Title"},{kind:"removed",text:"Old NPC"},{kind:"added",text:"New NPC"},{kind:"same",text:"End"}]);
});
it("never invents a text difference for identical Markdown",()=>expect(workspaceTextDiff("# Same\n","# Same\n").every(row=>row.kind==="same")).toBe(true));
it("preserves both complete texts even when the large-edit allocation bound is exceeded",()=>{
 const a=Array.from({length:500},(_,i)=>`old${i}`).join("\n"), b=Array.from({length:500},(_,i)=>`new${i}`).join("\n");const rows=workspaceTextDiff(a,b);
 expect(rows.filter(row=>row.kind!=="added").map(row=>row.text).join("\n")).toBe(a);expect(rows.filter(row=>row.kind!=="removed").map(row=>row.text).join("\n")).toBe(b);
});
it("collapses unchanged passages while retaining nearby context and every change",()=>{
 const a=Array.from({length:25},(_,i)=>`line${i}`).join("\n");const rows=diffWithContext(workspaceTextDiff(a,a.replace("line12","new12")));
 expect(rows.some(row=>row.kind==="omitted")).toBe(true);expect(rows).toContainEqual({kind:"removed",text:"line12"});expect(rows).toContainEqual({kind:"added",text:"new12"});expect(rows).toContainEqual({kind:"same",text:"line11"});
});
