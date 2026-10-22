import {describe,it,expect} from 'vitest';
import {Editor,generateHTML} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {semanticMarkdownSerializationDiagnostics} from '../tiptap/markdown/semanticMarkdownSafety';
import {parseTableJson} from './tableGrammar';

export const definition={schema_version:'dmb_roll_table_v1',table_id:'table:weather',title:'Weather',die_sides:6,rows:[{row_id:'row:dry',min:1,max:2,outcome:'Dry'},{row_id:'row:rain',min:3,max:6,outcome:'Rain <script> is plain text'}]};
const block='```dmb-roll-table-v1\n'+JSON.stringify(definition,null,2)+'\n```';
describe('shared typed table writing',()=>{
  it('round trips through the actual editor schema without fidelity warnings',()=>{
    const markdown='# Preparation\n\n'+block+'\n\nNext scene.';
    const imported=markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    expect(semanticMarkdownSerializationDiagnostics(imported.doc)).toEqual([]);
    const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:imported.doc});
    expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(markdown+"\n");
    const html=generateHTML(editor.getJSON(),DEFAULT_MARKDOWN_EDITOR_EXTENSIONS);
    expect(html).toContain('Weather · d6');expect(html).toContain('&lt;script&gt;');expect(html).not.toContain('<script>');editor.destroy();
  });
  it('blocks malformed, duplicate and unclosed tables instead of admitting lossy prose',()=>{
    for(const markdown of [block+'\n\n'+block,block.slice(0,-3),block.replace('"die_sides": 6','"die_sides": true'),block.replace('"title": "Weather"','"title": "Weather", "title":"dup"')]){
      expect(markdownToTiptapDoc(markdown).diagnostics.some(d=>d.level==='warning')).toBe(true);
    }
  });
  it('keeps ordinary fences protected and ignores nested typed examples',()=>{
    const generic=markdownToTiptapDoc('````markdown\n'+block+'\n````');
    expect(generic.doc.content?.some(n=>n.type==='preparedTable')).toBe(false);
    expect(generic.diagnostics.some(d=>d.level==='warning')).toBe(true);
  });
  it('rejects duplicate escaped keys and inaccurate numeric representations',()=>{
    expect(()=>parseTableJson(JSON.stringify(definition).replace('"title":"Weather"','"title":"Weather", "tit\\u006ce":"Again"'))).toThrow();
    expect(()=>parseTableJson(JSON.stringify({...definition,die_sides:9007199254740992}))).toThrow();
  });
});
