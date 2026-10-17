import { Editor } from '@tiptap/core';
import { describe, expect, it } from 'vitest';
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

  it('protects link titles and non-text labels instead of losing them', () => {
    for (const source of ['[Source](https://example.com "Caption")', '[![image](https://example.com/image)](https://example.com)']) {
      expect(markdownToTiptapDoc(source).diagnostics.some(d => d.level === 'warning')).toBe(true);
    }
  });
});
