import { useLayoutEffect, useMemo } from 'react';
import { MarkdownDocumentReader } from '../markdownReader/MarkdownDocumentReader';
import { ReadOnlyBodyContent } from '../markdownReader/ReadOnlyBodyContent';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';

/** Presentation only; the provider owns reference admission, history and scroll. */
export default function DocumentReferenceBody({ markdown, onReady }: { markdown: string; onReady: () => void }) {
  const imported = useMemo(() => markdownToTiptapDoc(markdown), [markdown]);
  // Suspense can temporarily shorten the pane and clamp its scroll position.
  // Restore only after the current body has actually committed its DOM.
  useLayoutEffect(onReady, [markdown, onReady]);
  return imported.diagnostics.length === 0
    ? <ReadOnlyBodyContent content={imported.doc.content} />
    : <><p role="status">Some content uses source rendering.</p><MarkdownDocumentReader markdown={markdown} /></>;
}
