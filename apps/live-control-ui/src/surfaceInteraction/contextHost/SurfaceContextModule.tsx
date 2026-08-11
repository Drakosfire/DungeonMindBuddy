import type { ReactNode } from "react";

interface SurfaceContextModuleProps {
  label: string;
  children: ReactNode;
  className?: string;
}

export function SurfaceContextModule({
  label,
  children,
  className,
}: SurfaceContextModuleProps) {
  const moduleClassName = className
    ? `surface-context-module ${className}`
    : "surface-context-module";

  return (
    <div className={moduleClassName} data-testid="surface-context-module">
      <span className="surface-context-label">{label}</span>
      <div className="surface-context-module__body">{children}</div>
    </div>
  );
}
