import { expect, it } from 'vitest';
import { buildProposalMarkdown } from './buildProposalMarkdown';
import { admitMarkdownInsertion } from '../documentEditing/markdownInsertion';

it('adapts only proven table alignment for the real insertion boundary, preserving words and original bytes', () => {
  const original = '## Soldiers\n\n| d20 | Name |\n|---:|:---|\n| 1 | Mara: gate guard |\n';
  const result = buildProposalMarkdown(original);
  expect(result.alignmentAdjusted).toBe(true);
  expect(result.markdown).toBe(original.replace('|---:|:---|', '|---|---|'));
  expect(admitMarkdownInsertion(result.markdown).content.some(node => node.type === 'table')).toBe(true);
  expect(original).toContain('|---:|:---|');
});
it('does not reinterpret fenced examples or make unsafe proposals admissible', () => {
  const fenced = '```md\n| d20 | Name |\n|---:|:---|\n| 1 | Mara |\n```';
  expect(buildProposalMarkdown(fenced)).toEqual({ markdown: fenced, alignmentAdjusted: false });
  expect(() => admitMarkdownInsertion(buildProposalMarkdown('<script>bad()</script>').markdown)).toThrow();
});
