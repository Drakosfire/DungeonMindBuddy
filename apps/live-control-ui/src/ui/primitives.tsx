import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

import "./primitives.css";

type SurfaceTone = "chrome" | "paper" | "ops";
type ButtonTone = "quiet" | "action" | "danger";
type BadgeTone = "neutral" | "current" | "danger";

function classes(...parts: Array<string | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export interface SurfaceProps extends HTMLAttributes<HTMLElement> {
  tone?: SurfaceTone;
}

export function Surface({ tone = "chrome", className, children, ...rest }: SurfaceProps) {
  return (
    <section {...rest} className={classes("ui-surface", `ui-surface--${tone}`, className)}>
      {children}
    </section>
  );
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: ButtonTone;
}

export function Button({ tone = "quiet", type = "button", className, children, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      className={classes("ui-button", `ui-button--${tone}`, className)}
    >
      {children}
    </button>
  );
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ tone = "neutral", className, children, ...rest }: BadgeProps) {
  return (
    <span {...rest} className={classes("ui-badge", `ui-badge--${tone}`, className)}>
      {children}
    </span>
  );
}

export interface StackProps extends HTMLAttributes<HTMLDivElement> {
  direction?: "row" | "column";
  gap?: "small" | "medium" | "large";
  wrap?: boolean;
}

export function Stack({
  direction = "column",
  gap = "medium",
  wrap = false,
  className,
  children,
  ...rest
}: StackProps) {
  return (
    <div
      {...rest}
      className={classes(
        "ui-stack",
        `ui-stack--${direction}`,
        `ui-stack--gap-${gap}`,
        wrap ? "ui-stack--wrap" : undefined,
        className,
      )}
    >
      {children}
    </div>
  );
}
