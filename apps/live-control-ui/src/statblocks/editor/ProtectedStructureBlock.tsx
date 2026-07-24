import type { ReactNode } from "react";

export type ProtectedStructureBlockProps = {
  path: string;
  title: string;
  summary: Record<string, unknown> | string;
  children?: ReactNode;
};

export function ProtectedStructureBlock({ path, title, summary, children }: ProtectedStructureBlockProps) {
  const summaryText = typeof summary === "string" ? summary : JSON.stringify(summary, null, 2);

  return (
    <section
      className="statblock-editor-protected"
      data-editor-region="protected"
      data-protected-path={path}
      aria-label={`Protected structure: ${title}`}
    >
      <header className="statblock-editor-protected__header">
        <strong>{title}</strong>
        <span className="statblock-editor-protected__badge">Protected</span>
      </header>
      <pre className="statblock-editor-protected__summary">{summaryText}</pre>
      {children}
    </section>
  );
}
