interface UnsupportedModuleProps {
  moduleId: string;
  title: string;
}

export function UnsupportedModule({ moduleId, title }: UnsupportedModuleProps) {
  return (
    <div className="module-panel unsupported-module" data-module-id={moduleId}>
      <p className="module-title">{title}</p>
      <p className="module-muted">
        Module <code>{moduleId}</code> is in the catalog but not implemented in this UI build.
      </p>
    </div>
  );
}
