import type {
  ButtonHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

interface SurfaceContextLabelProps {
  children: ReactNode;
  className?: string;
}

export function SurfaceContextLabel({ children, className }: SurfaceContextLabelProps) {
  const labelClassName = className
    ? `surface-context-label ${className}`
    : "surface-context-label";

  return <span className={labelClassName}>{children}</span>;
}

interface SurfaceContextValueProps {
  children: ReactNode;
  title?: string;
  className?: string;
}

export function SurfaceContextValue({ children, title, className }: SurfaceContextValueProps) {
  const valueClassName = className
    ? `surface-context-value ${className}`
    : "surface-context-value";

  return (
    <span className={valueClassName} title={title}>
      {children}
    </span>
  );
}

interface SurfaceContextBadgeProps {
  children: ReactNode;
  className?: string;
}

export function SurfaceContextBadge({ children, className }: SurfaceContextBadgeProps) {
  const badgeClassName = className
    ? `surface-context-badge ${className}`
    : "surface-context-badge";

  return <span className={badgeClassName}>{children}</span>;
}

export function SurfaceContextAction({
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  const actionClassName = className
    ? `surface-context-action ${className}`
    : "surface-context-action";

  return <button type={type} className={actionClassName} {...props} />;
}

interface SurfaceContextStatusProps {
  children: ReactNode;
  tone?: "neutral" | "warning" | "error";
  className?: string;
  "data-testid"?: string;
}

export function SurfaceContextStatus({
  children,
  tone = "neutral",
  className,
  "data-testid": dataTestId,
}: SurfaceContextStatusProps) {
  const statusClassName = className
    ? `surface-context-status surface-context-status--${tone} ${className}`
    : `surface-context-status surface-context-status--${tone}`;

  return (
    <span className={statusClassName} data-testid={dataTestId}>
      {children}
    </span>
  );
}

export function SurfaceContextSelect({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  const selectClassName = className
    ? `surface-context-select ${className}`
    : "surface-context-select";

  return <select className={selectClassName} {...props} />;
}

interface SurfaceContextPopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trigger: ReactNode;
  title?: string;
  children: ReactNode;
  /** Horizontal anchor when placement is below, or preferred side when beside. */
  align?: "start" | "end";
  /** below = under the trigger (default); beside = to the side of the trigger. */
  placement?: "below" | "beside";
  className?: string;
}

export function SurfaceContextPopover({
  open,
  onOpenChange,
  trigger,
  title,
  children,
  align = "start",
  placement = "below",
  className,
}: SurfaceContextPopoverProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [resolvedAlign, setResolvedAlign] = useState(align);

  useEffect(() => {
    setResolvedAlign(align);
  }, [align, open, placement]);

  useLayoutEffect(() => {
    if (!open || placement !== "beside") {
      return;
    }
    const panel = panelRef.current;
    if (!panel) {
      return;
    }
    const rect = panel.getBoundingClientRect();
    const margin = 12;
    if (align === "end" && rect.right > window.innerWidth - margin) {
      setResolvedAlign("start");
      return;
    }
    if (align === "start" && rect.left < margin) {
      setResolvedAlign("end");
    }
  }, [align, open, placement, children]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      const root = rootRef.current;
      if (root && !root.contains(event.target as Node)) {
        onOpenChange(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onOpenChange]);

  const popoverClassName = [
    "surface-context-popover",
    `surface-context-popover--align-${resolvedAlign}`,
    `surface-context-popover--placement-${placement}`,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div ref={rootRef} className={popoverClassName}>
      {trigger}
      {open ? (
        <div
          ref={panelRef}
          className="surface-context-popover__panel"
          data-testid="surface-context-popover"
          data-placement={placement}
          data-align={resolvedAlign}
          role="dialog"
        >
          {title ? <div className="surface-context-popover__title">{title}</div> : null}
          <div className="surface-context-popover__body">{children}</div>
        </div>
      ) : null}
    </div>
  );
}
