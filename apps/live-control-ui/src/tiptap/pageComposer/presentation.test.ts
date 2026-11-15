import { describe, expect, it } from "vitest";
import { createHash } from "node:crypto";
import type { JSONContent } from "@tiptap/core";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import { admittedPresentationBlocks, flattenPresentation, hasPresentation, hydratePresentation, presentationEligibility, presentationFingerprint, presentationSha256, projectPresentation, type PagePresentation } from "./presentation";

const text = 'Café 🌲\n\n![Art](dmb-media:11111111-1111-4111-8111-111111111111)\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n> [!GM-NOTE]\n> A note.\n';
function row(markdown=text): JSONContent {
  const doc=markdownToTiptapDoc(markdown).doc;
  return {type:'doc',content:[{type:'pageRow',attrs:{id:'row-a',min_height:0,line_mode:'guide'},content:[{type:'pageSlot',attrs:{id:'left',width:6},content:doc.content?.slice(0,1)},{type:'pageSlot',attrs:{id:'right',width:6},content:doc.content?.slice(1)}]}]};
}
function payload(markdown=text):PagePresentation {return projectPresentation(row(markdown),markdown,markdownToTiptapDoc(markdown).doc).presentation!;}
describe('Page presentation exact-source mapper',()=>{
  it.each(['','abc','Café 🌲','a'.repeat(1000)])('hashes exact UTF8 bytes %s',s=>expect(presentationSha256(s)).toBe(createHash('sha256').update(s).digest('hex')));
  it.each([text,'---\ntitle: Café\n---\n\n'+text,text.replaceAll('\n','\r\n')])('reconstructs real mixed blocks with exact whitespace and YAML',source=>{
    const p=payload(source),doc=hydratePresentation(source,p);
    expect(hasPresentation(doc)).toBe(true);
    expect(flattenPresentation(doc)).toEqual(markdownToTiptapDoc(source).doc);
    expect(projectPresentation(doc,source,doc)).toEqual({markdown:source,presentation:p});
    expect(admittedPresentationBlocks(source).map(b=>b.node.type)).toEqual(['paragraph','paragraph','table','callout']);
    const raw=Buffer.from(source);
    for(const b of admittedPresentationBlocks(source)) expect(b.sha256).toBe(createHash('sha256').update(raw.subarray(b.byte_start,b.byte_end)).digest('hex'));
  });
  it('keeps exact Markdown through width-only changes and unwrap',()=>{
    const p=payload(),doc=hydratePresentation(text,p),next=structuredClone(doc);
    next.content![0].content![0].attrs!.width=4;next.content![0].content![1].attrs!.width=8;
    const changed=projectPresentation(next,text,doc);
    expect(changed.markdown).toBe(text);expect(presentationFingerprint(changed.presentation)).not.toBe(presentationFingerprint(p));
    expect(projectPresentation(flattenPresentation(doc),text,doc)).toEqual({markdown:text,presentation:null});
  });
  it('updates exact byte spans after a text edit, preserving IDs and YAML',()=>{
    const source='---\ntitle: 🌲\n---\n\n'+text,p=payload(source),doc=hydratePresentation(source,p),next=structuredClone(doc);
    next.content![0].content![0].content![0].content![0].text='New words';
    const result=projectPresentation(next,source,doc);
    expect(result.markdown).toMatch(/^---\ntitle: 🌲\n---\n/);
    const reopened=hydratePresentation(result.markdown,result.presentation);
    expect(reopened.content![0].attrs!.id).toBe('row-a');
    expect(reopened.content![0].content![0].content![0].attrs!.pageBlockId).toBe(doc.content![0].content![0].content![0].attrs!.pageBlockId);
    expect(flattenPresentation(reopened).content![0].content![0].text).toBe('New words');
  });
  it('fingerprints exactly the backend canonical JSON convention',()=>{
    const p=payload();const canonical=(v:unknown):unknown=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,canonical(x)])):v;
    expect(presentationFingerprint(p)).toBe(createHash('sha256').update(JSON.stringify(canonical(p))).digest('hex'));
    expect(presentationFingerprint(null)).toBeNull();expect(presentationFingerprint(undefined)).toBeNull();
  });
  it.each(['![Bird][bird]\n\nOther.\n\n[bird]: dmb-media:11111111-1111-4111-8111-111111111111\n','```js\nx\n```','<div>raw</div>','Text <i>inline</i>',''])('disables composition without changing unsupported source %s',source=>{
    expect(presentationEligibility(source).eligible).toBe(false);
    expect(()=>payload(source)).toThrow();
  });
  it.each(['digest','span','identity','extra','order','width','omitted'])('rejects malformed stored %s data',damage=>{
    const p=payload();const r=p.items[0];if(r.kind!=='row') throw new Error('fixture');
    if(damage==='digest') p.markdown_sha256='0'.repeat(64);
    if(damage==='span') r.slots[0].blocks[0].byte_start=1;
    if(damage==='identity') r.slots[0].id=r.id;
    if(damage==='extra') Object.assign(p,{unexpected:true});
    if(damage==='order') r.slots.reverse();
    if(damage==='width') r.slots[0].width=5;
    if(damage==='omitted') r.slots[1].blocks.pop();
    expect(()=>hydratePresentation(text,p)).toThrow();
  });
  it('keeps generated identities stable across projection',()=>{
    const original=markdownToTiptapDoc(text).doc,doc=row();
    expect(projectPresentation(doc,text,original)).toEqual(projectPresentation(structuredClone(doc),text,original));
  });
  const tableArtTable='---\ntitle: Café 🌲\n---\n\n| Left | Value |\n| --- | --- |\n| One | 1 |\n\n![Art](dmb-media:11111111-1111-4111-8111-111111111111)\n\n| Right | Value |\n| --- | --- |\n| Two | 2 |\n';
  function wideRow(slots:number,source=tableArtTable):JSONContent {
    const content=markdownToTiptapDoc(source).doc.content!;
    return {type:'doc',content:[{type:'pageRow',attrs:{id:'mixed-row',min_height:0,line_mode:'guide'},content:Array.from({length:slots},(_,i)=>({type:'pageSlot',attrs:{id:`mixed-slot-${i}`,width:12/slots},content:slots===1?content:[content[i]]}))}]};
  }
  it.each([1,3])('roundtrips %i-slot table/art/table with exact UTF8/YAML/source order',slots=>{
    const doc=wideRow(slots),original=markdownToTiptapDoc(tableArtTable).doc;
    const projected=projectPresentation(doc,tableArtTable,original);
    expect(projected.markdown).toBe(tableArtTable);
    const hydrated=hydratePresentation(projected.markdown,projected.presentation);
    expect(flattenPresentation(hydrated)).toEqual(original);
    expect(hydrated.content![0].content).toHaveLength(slots);
    expect(projectPresentation(hydrated,tableArtTable,hydrated)).toEqual(projected);
    expect(admittedPresentationBlocks(tableArtTable).map(block=>block.node.type)).toEqual(['table','paragraph','table']);
  });
  it.each(['guide','border','clean'])('keeps source bytes and binding identities through %s controls-only edits',line_mode=>{
    const initial=projectPresentation(wideRow(3),tableArtTable,markdownToTiptapDoc(tableArtTable).doc);
    const original=hydratePresentation(tableArtTable,initial.presentation),next=structuredClone(original);
    next.content![0].attrs!.min_height=640;next.content![0].attrs!.line_mode=line_mode;
    [2,4,6].forEach((width,i)=>{next.content![0].content![i].attrs!.width=width;});
    const result=projectPresentation(next,tableArtTable,original);
    expect(result.markdown).toBe(tableArtTable);
    expect(flattenPresentation(hydratePresentation(result.markdown,result.presentation))).toEqual(markdownToTiptapDoc(tableArtTable).doc);
    const before=initial.presentation!.items[0],after=result.presentation!.items[0];
    if(before.kind!=='row'||after.kind!=='row')throw new Error('fixture');
    expect(after.slots.flatMap(slot=>slot.blocks)).toEqual(before.slots.flatMap(slot=>slot.blocks));
    expect(presentationFingerprint(result.presentation)).not.toBe(presentationFingerprint(initial.presentation));
    next.content![0].attrs!.min_height=0;
    expect(projectPresentation(next,tableArtTable,original).markdown).toBe(tableArtTable);
  });
  it.each(['zero','four','empty','tooNarrow','fractionalWidth','badSum','negativeHeight','largeHeight','fractionalHeight','unsnappedHeight','unknownMode'])('rejects malformed row control %s',damage=>{
    const p=projectPresentation(wideRow(3),tableArtTable,markdownToTiptapDoc(tableArtTable).doc).presentation!;
    const r=p.items[0];if(r.kind!=='row')throw new Error('fixture');
    if(damage==='zero')r.slots=[];
    if(damage==='four')r.slots.push({id:'extra-slot',width:2,blocks:[]});
    if(damage==='empty')r.slots.forEach(slot=>{slot.blocks=[];});
    if(damage==='tooNarrow'){r.slots[0].width=1;r.slots[1].width=7;}
    if(damage==='fractionalWidth'){r.slots[0].width=3.5;r.slots[1].width=4.5;}
    if(damage==='badSum')r.slots[0].width=3;
    if(damage==='negativeHeight')r.min_height=-8;
    if(damage==='largeHeight')r.min_height=648;
    if(damage==='fractionalHeight')r.min_height=8.5;
    if(damage==='unsnappedHeight')r.min_height=7;
    if(damage==='unknownMode')Object.assign(r,{line_mode:'dotted'});
    expect(()=>hydratePresentation(tableArtTable,p)).toThrow();
  });
  it('never strips unknown nodes or permits nested composer containers',()=>{
    const unknown={type:'doc',content:[{type:'unrecognizedWidget'}]};
    expect(flattenPresentation(unknown)).toEqual(unknown);
    expect(()=>projectPresentation(unknown,text,markdownToTiptapDoc(text).doc)).toThrow();
    const bad=row();bad.content![0].content![0].content=[row().content![0]];
    expect(()=>flattenPresentation(bad)).toThrow();
  });
});
