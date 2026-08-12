import { MarkdownDocumentReader } from "../markdownReader/MarkdownDocumentReader";

export type BuildSourceNavigationTargetStatus =
  | "none"
  | "pending"
  | "exact"
  | "stale"
  | "document_mismatch"
  | "error";

export interface BuildSourceNavigationTarget {
  status: BuildSourceNavigationTargetStatus;
  startLine?: number;
  endLine?: number;
  message?: string;
  /** Stable A:S identity for scroll-once in the markdown reader. */
  targetKey?: string;
}

export interface BuildSourceReaderProps {
  /** Exact accepted workspace-document title. */
  title: string;
  /** Exact saved `snapshot.markdown` — never TipTap serialization. */
  markdown: string;
  /** When true, Read is showing saved source while local edits exist. */
  dirty: boolean;
  /** Server re-resolved graph evidence target; never trusted from URL alone. */
  navigationTarget?: BuildSourceNavigationTarget;
}

function navigationStatusMessage(target: BuildSourceNavigationTarget): string | null {
  switch (target.status) {
    case "pending":
      return "Resolving cited source passage…";
    case "stale":
      return target.message
        ?? "Source has changed since this evidence was admitted. The cited line range cannot be highlighted exactly.";
    case "document_mismatch":
      return target.message
        ?? "This source passage belongs to a different Build document than the one currently open.";
    case "error":
      return target.message ?? "Source navigation could not be resolved.";
    default:
      return null;
  }
}

/**
 * Build binding of exact session snapshot/title/dirty truth to the generic Markdown reader.
 */
export function BuildSourceReader({
  title,
  markdown,
  dirty,
  navigationTarget = { status: "none" },
}: BuildSourceReaderProps) {
  const statusMessage = navigationStatusMessage(navigationTarget);
  const canPassHighlight =
    navigationTarget.status === "exact"
    && navigationTarget.startLine != null
    && navigationTarget.endLine != null
    && navigationTarget.targetKey != null;

  const sourceLineTarget = canPassHighlight
    ? {
        startLine: navigationTarget.startLine!,
        endLine: navigationTarget.endLine!,
        targetKey: navigationTarget.targetKey!,
      }
    : null;

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
        {navigationTarget.status !== "none" && dirty ? (
          <p
            className="build-source-reader__navigation-dirty-notice"
            role="status"
            data-testid="build-source-reader-navigation-dirty-notice"
          >
            Graph evidence refers to the last saved source.
          </p>
        ) : null}
        {statusMessage ? (
          <p
            className={[
              "build-source-reader__navigation-status",
              navigationTarget.status === "stale" || navigationTarget.status === "document_mismatch"
                ? "build-source-reader__navigation-status--stale"
                : null,
              navigationTarget.status === "error"
                ? "build-source-reader__navigation-status--error"
                : null,
            ].filter(Boolean).join(" ")}
            role="status"
            data-testid="build-source-reader-navigation-status"
            data-navigation-status={navigationTarget.status}
          >
            {statusMessage}
          </p>
        ) : null}
      </header>
      <MarkdownDocumentReader markdown={markdown} sourceLineTarget={sourceLineTarget} />
    </article>
  );
}
