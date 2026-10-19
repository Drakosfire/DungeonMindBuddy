import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { Editor } from "@tiptap/core";
import { afterEach, expect, it } from "vitest";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../tiptap/MarkdownEditorCore";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { PlanCardEditing, exportPlanCardMarkdown, planCardRange, setPlanCardScope } from "./planCardEditing";
const source = `<!-- dmb-playable-element:v2 kind=beat id=beat:road beat_kind=spine -->
## Road
Keep watch.
<!-- dmb-playable-element:v2 kind=scene id=scene:a -->
### Scene A
Alpha body.
#### Ordinary heading
More body.
<!-- dmb-playable-element:v2 kind=scene id=scene:b -->
### Scene B
Beta body.
`;
let editor: Editor;
afterEach(() => editor?.destroy());
function setup() { return editor = new Editor({ extensions: [...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, PlanCardEditing], content: markdownToTiptapDoc(source).doc }); }
it("edits the current scene body while rejecting prefix/suffix, select-all, duplicate markers and multi-step attacks", () => {
  const ed = setup(); setPlanCardScope(ed, {active:true,sceneId:"scene:a"});
  const a = planCardRange(ed.state.doc,"scene:a")!;
  ed.commands.insertContentAt(a.from+1,"Edited ");
  expect(ed.getText()).toContain("Edited Alpha");
  const safe = ed.getJSON();
  ed.commands.insertContentAt(ed.state.doc.content.size-1," hidden"); expect(ed.getJSON()).toEqual(safe);
  ed.commands.selectAll(); ed.commands.deleteSelection(); expect(ed.getJSON()).toEqual(safe);
  ed.commands.insertContentAt(a.from,markdownToTiptapDoc('<!-- dmb-playable-element:v2 kind=scene id=scene:new -->\n### New\nNo').doc.content!); expect(ed.getJSON()).toEqual(safe);
  ed.view.dispatch(ed.state.tr.insertText("safe",a.from+1).insertText("unsafe",1)); expect(ed.getJSON()).toEqual(safe);
  setPlanCardScope(ed,{active:true,sceneId:"missing"});ed.commands.insertContent("blocked");expect(ed.getJSON()).toEqual(safe);
});
it("keeps scene/view history groups distinct and rejected undo/redo leaves stacks usable", () => {
  const ed=setup();setPlanCardScope(ed,{active:true,sceneId:"scene:a"});
  ed.commands.insertContentAt(planCardRange(ed.state.doc,"scene:a")!.from+1,"A edit ");
  setPlanCardScope(ed,{active:true,sceneId:"scene:b"});
  ed.commands.insertContentAt(planCardRange(ed.state.doc,"scene:b")!.from+1,"B edit ");
  ed.commands.undo();expect(ed.getText()).not.toContain("B edit");expect(ed.getText()).toContain("A edit");
  const before=ed.getJSON();ed.commands.undo();expect(ed.getJSON()).toEqual(before);
  setPlanCardScope(ed,{active:false,sceneId:null});ed.commands.undo();expect(ed.getText()).not.toContain("A edit");
  ed.commands.redo();expect(ed.getText()).toContain("A edit");
  setPlanCardScope(ed,{active:true,sceneId:"scene:a"});const after=ed.getJSON();ed.commands.redo();expect(ed.getJSON()).toEqual(after);
});

it("exports only the selected body and preserves exact prefix/suffix Markdown bytes", () => {
  const ed=setup();setPlanCardScope(ed,{active:true,sceneId:"scene:a"});
  ed.commands.insertContentAt(planCardRange(ed.state.doc,"scene:a")!.from+1,"Edited ");
  const canonical = tiptapJsonToSemanticMarkdown(ed.getJSON());
  const result = exportPlanCardMarkdown(ed,source,canonical);
  const boundary="<!-- dmb-playable-element:v2 kind=scene id=scene:b -->";
  expect(result.split(boundary)[1]).toBe(source.split(boundary)[1]);
  expect(result.slice(0,result.indexOf("### Scene A")+11)).toBe(source.slice(0,source.indexOf("### Scene A")+11));
  expect(result).toContain("Edited Alpha body.");
});
it("preserves scoped media and tables through export", () => {
  const ed=setup();setPlanCardScope(ed,{active:true,sceneId:"scene:a"});
  ed.commands.insertContentAt(planCardRange(ed.state.doc,"scene:a")!.from+1,markdownToTiptapDoc('![Map](dmb-media:73b40978-e638-4ab3-992d-5dc493e8d229)\n\n| A | B |\n| --- | --- |\n| one | two |').doc.content!);
  const canonical=tiptapJsonToSemanticMarkdown(ed.getJSON());
  const output=exportPlanCardMarkdown(ed,source,canonical);
  expect(output).toContain("dmb-media:73b40978");expect(output).toContain("| one | two |");
});
it("allows intermediate trailing whitespace while preserving sibling source",()=>{
 const ed=setup();setPlanCardScope(ed,{active:true,sceneId:"scene:a"});
 const range=planCardRange(ed.state.doc,"scene:a")!;ed.commands.insertContentAt(range.to-1," ");
 expect(()=>exportPlanCardMarkdown(ed,source,tiptapJsonToSemanticMarkdown(ed.getJSON()))).not.toThrow();
});
it("owns frontmatter once in both Cards and Document exports",()=>{
 const ed=setup();const withYaml="---\ntitle: Retained\n---\n\n"+source;
 const canonical=tiptapJsonToSemanticMarkdown(ed.getJSON());
 setPlanCardScope(ed,{active:true,sceneId:"scene:a"});
 expect(exportPlanCardMarkdown(ed,withYaml,canonical).match(/title: Retained/g)).toHaveLength(1);
 setPlanCardScope(ed,{active:false,sceneId:null});
 expect(exportPlanCardMarkdown(ed,withYaml,canonical).match(/title: Retained/g)).toHaveLength(1);
});
