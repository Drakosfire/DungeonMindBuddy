import type { CitationSourceResponse } from "../../api/types";

export const SOURCE_PREVIEW_CHAR_LIMIT = 6000;

export interface SelectedObjectSourcePreviewProps {
  source: CitationSourceResponse;
  uiClipped: boolean;
}

function clipContent(content: string): string {
  if (content.length <= SOURCE_PREVIEW_CHAR_LIMIT) return content;
  return content.slice(0, SOURCE_PREVIEW_CHAR_LIMIT);
}

export function SelectedObjectSourcePreview({
  source,
  uiClipped,
}: SelectedObjectSourcePreviewProps) {
  const excerpt = source.highlight.text_excerpt?.trim();
  const clippedContent = clipContent(source.content);
  const lineStart = source.highlight.line_start;
  const lineEnd = source.highlight.line_end;
  const hasLineRange = lineStart != null && lineEnd != null;

  return (
    <div className="plan-selected-object-source-preview" aria-label="Source preview">
      <p className="plan-selected-object-source-preview-heading">Source preview</p>
      <code className="plan-selected-object-source-preview-path">{source.path}</code>

      {excerpt ? (
        <div className="plan-selected-object-source-preview-highlight">
          <p className="plan-selected-object-source-preview-highlight-label">Highlighted excerpt</p>
          {hasLineRange ? (
            <p className="plan-selected-object-source-preview-lines">
              Lines {lineStart}–{lineEnd}
            </p>
          ) : null}
          <pre className="plan-selected-object-source-preview-content">{excerpt}</pre>
        </div>
      ) : null}

      {excerpt ? (
        <details className="plan-selected-object-source-preview-full">
          <summary>Full preview</summary>
          <pre className="plan-selected-object-source-preview-content">{clippedContent}</pre>
        </details>
      ) : (
        <pre className="plan-selected-object-source-preview-content">{clippedContent}</pre>
      )}

      {source.truncated ? (
        <p className="plan-selected-object-source-preview-warning">
          Preview truncated by source reader.
        </p>
      ) : null}
      {uiClipped ? (
        <p className="plan-selected-object-source-preview-warning">
          UI preview clipped. Source reader may also have truncated the file.
        </p>
      ) : null}

      {source.diagnostics.length > 0 ? (
        <p className="plan-selected-object-source-preview-diagnostics">
          {source.diagnostics.join(" · ")}
        </p>
      ) : null}

      <p className="plan-selected-object-source-preview-footer">
        Read-only source lookup · no events or jobs written
      </p>
    </div>
  );
}
