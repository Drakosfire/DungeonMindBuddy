import { Editor } from '@tiptap/core';
import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { markdownToTiptapDoc } from '../markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../markdown/calloutMarkdown';
import { semanticMarkdownSerializationDiagnostics } from '../markdown/semanticMarkdownSafety';

describe('mounted web source link fidelity', () => {
  it.each([
    '# Arrival\n\nRead [**the source**](http://127.0.0.1:5202/build?world=elderwyld&documentId=source).',
    '> Read [the source](https://example.com/source?q=a&rev=2).',
    '| Source | Detail |\n| --- | --- |\n| [map](https://example.com/map\\(1\\)) | Draft |',
    '> [!GM-NOTE]\n> Read [the source](https://example.com/source).',
  ])('roundtrips through the actual default editor and reimport: %s', source => {
    const imported = markdownToTiptapDoc(source);
    expect(imported.diagnostics).toEqual([]);
    const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: imported.doc });
    try {
      const actual = editor.getJSON();
      expect(semanticMarkdownSerializationDiagnostics(actual)).toEqual([]);
      const exported = tiptapJsonToSemanticMarkdown(actual);
      const reopened = markdownToTiptapDoc(exported);
      expect(reopened.diagnostics).toEqual([]);
      expect(tiptapJsonToSemanticMarkdown(reopened.doc)).toBe(exported);
      const link = editor.view.dom.querySelector('a');
      expect(link).not.toBeNull();
      expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
      expect(link?.getAttribute('href')).toMatch(/^https?:\/\//);
    } finally { editor.destroy(); }
  });

  it.each(['javascript:alert(1)', 'data:text/html,test', '//example.com', 'https://user:secret@example.com', '../source.md', 'mailto:test@example.com'])('protects unsupported source href %s', href => {
    const imported = markdownToTiptapDoc(`[Source](${href})`);
    expect(imported.diagnostics.some(d => d.level === 'warning')).toBe(true);
    const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: `<p><a href="${href}">Source</a></p>` });
    try { expect(editor.view.dom.querySelector('a')).toBeNull(); } finally { editor.destroy(); }
    expect(semanticMarkdownSerializationDiagnostics({ type: 'doc', content: [{type: 'paragraph',content: [{type:'text',text:'Source',marks:[{type:'link',attrs:{href}}]}]}] })).not.toEqual([]);
  });

  it('roundtrips recognized root-relative document references without admitting arbitrary local paths', () => {
    const href = '/build?world=elderwyld&documentId=bba72416-9dfe-49bb-add0-21a346e9a421&revision=8';
    const imported = markdownToTiptapDoc(`[Edge](${href})`);
    expect(imported.diagnostics).toEqual([]);
    const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: imported.doc });
    try {
      expect(editor.view.dom.querySelector('a')?.getAttribute('href')).toBe(href);
      expect(semanticMarkdownSerializationDiagnostics(editor.getJSON())).toEqual([]);
      expect(markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(editor.getJSON())).diagnostics).toEqual([]);
      expect(markdownToTiptapDoc('[Unsupported](/build?documentId=unknown)').diagnostics.length).toBeGreaterThan(0);
    } finally { editor.destroy(); }
  });

  it('protects non-text labels instead of losing them', () => {
    for (const source of ['[![image](https://example.com/image)](https://example.com)']) {
      expect(markdownToTiptapDoc(source).diagnostics.some(d => d.level === 'warning')).toBe(true);
    }
  });
});


describe('explicit source link activation', () => {
  function mount(editable = true) {
    const element = document.createElement('div'); document.body.append(element);
    const onUpdate = vi.fn();
    const editor = new Editor({element, editorProps:{handleScrollToSelection:()=>true}, extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, editable,
      content: markdownToTiptapDoc('Read [**Edge**](http://127.0.0.1:5202/build?world=elderwyld&documentId=edge#place).').doc, onUpdate});
    return {editor, onUpdate, anchor:editor.view.dom.querySelector('a')!, destroy:()=>{editor.destroy();element.remove();}};
  }
  it.each([true,false])('opens nested source link once without changing editable=%s draft', editable=>{
    const open=vi.spyOn(window,'open').mockReturnValue(null);const m=mount(editable);
    try {
      const before=m.editor.getJSON(), markdown=tiptapJsonToSemanticMarkdown(before), selection=m.editor.state.selection.toJSON();
      m.anchor.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
      expect(open).toHaveBeenCalledExactlyOnceWith('http://127.0.0.1:5202/build?world=elderwyld&documentId=edge#place','_blank','noopener,noreferrer');
      expect(m.editor.getJSON()).toEqual(before);expect(tiptapJsonToSemanticMarkdown(m.editor.getJSON())).toBe(markdown);
      expect(m.editor.state.selection.toJSON()).toEqual(selection);expect(m.onUpdate).not.toHaveBeenCalled();
    } finally {m.destroy();open.mockRestore();}
  });
  it('opens keyboard-focused anchor with Enter, without capturing prose Enter',()=>{
    const open=vi.spyOn(window,'open').mockReturnValue(null);const m=mount();
    try {
      expect(m.anchor.getAttribute('tabindex')).toBe('0');m.anchor.focus();
      m.anchor.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
      expect(open).toHaveBeenCalledTimes(1);
      m.editor.view.dom.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
      expect(open).toHaveBeenCalledTimes(1);
    } finally {m.destroy();open.mockRestore();}
  });
  it.each(['javascript:alert(1)','data:text/html,test','//example.com','https://user:secret@example.com','mailto:a@example.com'])('denies mutable unsafe href %s',href=>{
    const open=vi.spyOn(window,'open').mockReturnValue(null);const m=mount();
    try {m.anchor.setAttribute('href',href);const e=new MouseEvent('click',{bubbles:true,cancelable:true});m.anchor.dispatchEvent(e);expect(e.defaultPrevented).toBe(true);expect(open).not.toHaveBeenCalled();}
    finally {m.destroy();open.mockRestore();}
  });
  it('leaves modifiers, non-primary clicks and unrelated anchors untouched',()=>{
    const open=vi.spyOn(window,'open').mockReturnValue(null);const m=mount();
    try {
      for(const init of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1},{button:2}]) m.anchor.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,...init}));
      m.anchor.removeAttribute('data-web-source-link');m.anchor.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));expect(open).not.toHaveBeenCalled();
    } finally {m.destroy();open.mockRestore();}
  });
  it('does not accumulate handlers across mounts',()=>{
    const open=vi.spyOn(window,'open').mockReturnValue(null);
    try {for(let i=0;i<3;i++){const m=mount();try{m.anchor.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));}finally{m.destroy();}}expect(open).toHaveBeenCalledTimes(3);}
    finally {open.mockRestore();}
  });
});

describe('ordinary link title fidelity',()=>{
 it('preserves escaped quotes, backslashes and inert HTML-like title text in Markdown and HTML',()=>{
  const title='Notes "quoted" \\ <b>inert</b>';
  const element=document.createElement('div');const a=document.createElement('a');a.href='https://example.com/source';a.title=title;a.textContent='Source';element.append(a);
  const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:element.innerHTML});
  try {
   expect(editor.view.dom.querySelector('a')?.getAttribute('title')).toBe(title);
   expect(editor.view.dom.querySelector('b')).toBeNull();
   expect(semanticMarkdownSerializationDiagnostics(editor.getJSON())).toEqual([]);
   const exported=tiptapJsonToSemanticMarkdown(editor.getJSON());
   const imported=markdownToTiptapDoc(exported);expect(imported.diagnostics).toEqual([]);
   const reopened=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:imported.doc});
   try {expect(reopened.view.dom.querySelector('a')?.getAttribute('title')).toBe(title);expect(tiptapJsonToSemanticMarkdown(reopened.getJSON())).toBe(exported)} finally {reopened.destroy()}
  } finally {editor.destroy()}
 });
 it.each(['line\nbreak','nul\0title','c1\u0085title','c1\u009ftitle',42,{},['title']])('refuses unsupported title metadata %s',title=>{
  const doc={type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Source',marks:[{type:'link',attrs:{href:'https://example.com',title}}]}]}]};
  expect(semanticMarkdownSerializationDiagnostics(doc)).not.toEqual([]);
 });
});

it.each(['\u0085','\u009f'])('refuses C1 title controls through actual Markdown and HTML import',control=>{
 const title='Source'+control+'notes';
 expect(markdownToTiptapDoc(`[Source](https://example.com "${title}")`).diagnostics.some(d=>d.level==='warning')).toBe(true);
 const element=document.createElement('div'),a=document.createElement('a');a.href='https://example.com';a.title=title;a.textContent='Source';element.append(a);
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:element.innerHTML});
 try {expect(editor.view.dom.querySelector('a')).toBeNull()} finally {editor.destroy()}
});
