import type { ReactNode } from "react";

export type ProtectedStructureBlockProps = {
  path: string;
  title: string;
  value: unknown;
  children?: ReactNode;
};

export function ProtectedStructureBlock({ path, title, value, children }: ProtectedStructureBlockProps) {
  const valueText = typeof value === "string" ? value : JSON.stringify(value, null, 2);

  return (
    <section
      className="statblock-editor-protected"
      data-editor-region="protected"
      data-protected-path={path}
      aria-label={`Protected structure: ${title}`}
    >
      <header className="statblock-editor-protected__header">
        <strong>{title}</strong>
        <span className="statblock-editor-protected__badge">Protected · not editable via dedicated controls</span>
      </header>
      <pre className="statblock-editor-protected__summary">{valueText}</pre>
      {children}
    </section>
  );
}
