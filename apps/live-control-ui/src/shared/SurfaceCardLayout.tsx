import type { HTMLAttributes } from "react";
import "./surfaceCardLayout.css";

/** Stable surface paper: enabled by card views without remounting their contents. */
export function SurfaceCardLayout({ as: Tag = "div", active = true, className = "", ...props }:
  HTMLAttributes<HTMLElement> & { as?: "div" | "section" | "article"; active?: boolean }) {
  return <Tag {...props} className={`${active ? "surface-card-layout " : ""}${className}`} />;
}
