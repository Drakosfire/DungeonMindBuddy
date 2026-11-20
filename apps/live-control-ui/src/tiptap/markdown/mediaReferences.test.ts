import { describe,it,expect } from 'vitest';
import { mediaMarkdown,mediaAssetId } from '../../media/mediaReferences';
import { markdownToTiptapDoc } from './markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from './calloutMarkdown';
import { semanticMarkdownSerializationDiagnostics } from './semanticMarkdownSafety';
const id='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
describe('saved media references',()=>{
 it('roundtrips stable ID and escaped alt without provider URL or settings',()=>{
  const markdown=mediaMarkdown(id,'Edge [at] dusk *quiet*');const loaded=markdownToTiptapDoc(markdown);
  expect(loaded.diagnostics.filter(item=>item.level==='warning')).toEqual([]);
  expect(loaded.doc.content?.[0].content?.[0]).toEqual({type:'mediaImage',attrs:{assetId:id,alt:'Edge [at] dusk *quiet*'}});
  expect(tiptapJsonToSemanticMarkdown(loaded.doc)).toBe(markdown+"\n");
  expect(semanticMarkdownSerializationDiagnostics(loaded.doc)).toEqual([]);
 });
 it('rejects URLs, script schemes and fabricated IDs',()=>{
  for(const url of ['https://example.com/image.png','javascript:alert(1)','dmb-media:other','dmb-media:'+id+'?url=evil'])expect(mediaAssetId(url)).toBeNull();
  expect(markdownToTiptapDoc('![Map](https://example.com/image.png)').diagnostics.some(item=>item.level==='warning')).toBe(true);
  expect(()=>mediaMarkdown('bad','Map')).toThrow();
 });
});

it('roundtrips explicit size and collapse without altering stable identity', () => {
 for (const width of [20, 55, 100]) for (const collapsed of [true, false]) {
  const source = mediaMarkdown(id, 'Edge map', width, collapsed);
  const parsed = markdownToTiptapDoc(source);
  expect(parsed.diagnostics).toEqual([]);
  expect(parsed.doc.content?.[0].content?.[0]).toEqual({type:'mediaImage',attrs:{assetId:id,alt:'Edge map',width,collapsed}});
  expect(tiptapJsonToSemanticMarkdown(parsed.doc)).toBe(source + '\n');
 }
});
it('blocks malformed image presentation rather than silently losing it', () => {
 for (const title of ['dmb-image:v1 width=19 collapsed=false','dmb-image:v1 width=101 collapsed=true','dmb-image:v1 width=40 collapsed=1','ordinary title']) {
  expect(markdownToTiptapDoc(`![Map](dmb-media:${id} "${title}")`).diagnostics.some(item => item.level === 'warning')).toBe(true);
 }
 expect(() => mediaMarkdown(id, 'Map', 25.5, false)).toThrow();
 expect(() => mediaMarkdown(id, 'Map', 50, 'false')).toThrow();
});
