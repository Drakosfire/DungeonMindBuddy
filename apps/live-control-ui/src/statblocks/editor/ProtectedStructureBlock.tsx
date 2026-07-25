import type { ReactNode } from "react";

export type ProtectedStructureBlockProps = {
  path: string;
  title: string;
  value: unknown;
  /**
   * When set, this block discloses protected remainder fields while dedicated
   * controls above edit the named targets. Badge must not claim the whole
   * structure is non-editable.
   */
  editableFieldsAbove?: string;
  children?: ReactNode;
};

export function ProtectedStructureBlock({
  path,
  title,
  value,
  editableFieldsAbove,
  children,
}: ProtectedStructureBlockProps) {
  const valueText = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const badge = editableFieldsAbove
    ? `Protected remainder · ${editableFieldsAbove} editable above`
    : "Protected · not editable via dedicated controls";

  return (
    <section
      className="statblock-editor-protected"
      data-editor-region="protected"
      data-protected-path={path}
      data-protected-mode={editableFieldsAbove ? "remainder" : "fully_protected"}
      aria-label={`Protected structure: ${title}`}
    >
      <header className="statblock-editor-protected__header">
        <strong>{title}</strong>
        <span className="statblock-editor-protected__badge">{badge}</span>
      </header>
      <pre className="statblock-editor-protected__summary">{valueText}</pre>
      {children}
    </section>
  );
}
