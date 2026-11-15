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
  it('keeps generated identities stable across projection and rejects non-two-slot stored rows',()=>{
    const original=markdownToTiptapDoc(text).doc,doc=row();
    expect(projectPresentation(doc,text,original)).toEqual(projectPresentation(structuredClone(doc),text,original));
    const p=payload(),r=p.items[0];if(r.kind!=='row')throw new Error('fixture');
    r.slots=[{...r.slots[0],width:12,blocks:[...r.slots[0].blocks,...r.slots[1].blocks]}];
    expect(()=>hydratePresentation(text,p)).toThrow('two-slot');
  });
  it('never strips unknown nodes or permits nested composer containers',()=>{
    const unknown={type:'doc',content:[{type:'unrecognizedWidget'}]};
    expect(flattenPresentation(unknown)).toEqual(unknown);
    expect(()=>projectPresentation(unknown,text,markdownToTiptapDoc(text).doc)).toThrow();
    const bad=row();bad.content![0].content![0].content=[row().content![0]];
    expect(()=>flattenPresentation(bad)).toThrow();
  });
});
