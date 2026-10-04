import { describe, expect, it } from "vitest";
import { adaptFocusedPlan } from "./components/FocusedPlanAdapter";
import type { WorldPlanCardNode } from "./components/WorldPlanCardProjection";
const node = (id: string, kind: WorldPlanCardNode['kind'], children: WorldPlanCardNode[] = []): WorldPlanCardNode => ({id,kind,children,title:id,bodyText:'',order:0,parentId:null});
const heading = (id: string) => ({type:'heading',attrs:{playableElementId:id,level:3}});
const label = (text: string) => ({type:'paragraph',content:[{type:'text',text,marks:[{type:'bold'}]}]});
describe('Buddy focused presentation adapter', () => {
  it('keeps original rich blocks and atom identities while separating authored lenses', () => {
    const rich = {type:'paragraph',content:[{type:'graphNodeReference',attrs:{nodeId:'npc:ly',label:'Lysandra'}}]};
    const result = adaptFocusedPlan({status:'ready',version:'v2',roots:[node('beat:a','beat',[node('scene:a','scene')])]}, {type:'doc',content:[heading('scene:a'),label('Situation'),rich,label('Read aloud'),{type:'blockquote',content:[{type:'paragraph',content:[{type:'text',text:'Smoke.'}]}]}]});
    expect(result[0]?.lenses.map(l=>l.title)).toEqual(['Situation','Read aloud']);
    expect(result[0]?.lenses[0]?.nodes[0]).toBe(rich);
  });
  it('keeps v2 sibling choices attached only to their declared scene', () => {
    const choice={...node('choice:a','choice'),sceneId:'scene:a'};
    const result=adaptFocusedPlan({status:'ready',version:'v2',roots:[node('beat:a','beat',[node('scene:a','scene'),choice,node('scene:b','scene')])]}, {type:'doc',content:[heading('scene:a'),heading('scene:b')]});
    expect(result[0]?.choices).toEqual([choice]);expect(result[1]?.choices).toEqual([]);
  });
  it('stops a scene body before unmarked document-level instructions', () => {
    const result=adaptFocusedPlan({status:'ready',version:'v1',roots:[node('scene:a','scene')]},{type:'doc',content:[heading('scene:a'),{type:'paragraph',content:[{type:'text',text:'Scene'}]},{type:'heading',attrs:{level:1}},{type:'paragraph',content:[{type:'text',text:'Global notes'}]}]});
    expect(result[0]?.lenses[0]?.nodes).toHaveLength(1);
  });
});
