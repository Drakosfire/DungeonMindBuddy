import { MarkdownDocumentReader } from "../markdownReader/MarkdownDocumentReader";

export interface BuildSourceReaderProps {
  /** Exact accepted workspace-document title. */
  title: string;
  /** Exact saved `snapshot.markdown` — never TipTap serialization. */
  markdown: string;
  /** When true, Read is showing saved source while local edits exist. */
  dirty: boolean;
}

/**
 * Build binding of exact session snapshot/title/dirty truth to the generic Markdown reader.
 */
export function BuildSourceReader({ title, markdown, dirty }: BuildSourceReaderProps) {
  return (
    <article className="build-source-reader" data-testid="build-source-reader">
      <header className="build-source-reader__header">
        <h1 className="build-source-reader__title">{title}</h1>
        {dirty ? (
          <p
            className="build-source-reader__dirty-warning"
            role="status"
            data-testid="build-source-reader-dirty-warning"
          >
            Reading the last saved source. Unsaved edits are not shown.
          </p>
        ) : null}
      </header>
      <MarkdownDocumentReader markdown={markdown} />
    </article>
  );
}
