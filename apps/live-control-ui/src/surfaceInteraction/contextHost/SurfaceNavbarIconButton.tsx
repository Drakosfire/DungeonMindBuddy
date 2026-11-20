import type { ButtonHTMLAttributes } from "react";
import "./surfaceNavbar.css";

/** Shared compact authoring actions; owners retain callbacks and admission rules. */
export function SurfaceNavbarIconButton({ icon, label, className = "", title, ...props }: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label"> & {
  icon: "save" | "new" | "import" | "play" | "move" | "remove";
  label: string;
}) {
  return <button {...props} type="button" className={`surface-context-action surface-navbar-icon surface-navbar-icon--${icon} ${className}`}
    aria-label={label} title={title ?? label}>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {icon === "move" ? <g fill="currentColor" stroke="none">{[6,12,18].flatMap(y=>[8,16].map(x=><circle key={`${x}-${y}`} cx={x} cy={y} r="1.5"/>))}</g> : icon === "remove" ? <path d="M5 12h14"/> : icon === "play" ? <path d="m8 4 12 8-12 8Z" fill="currentColor" stroke="none" /> : icon === "new" ? <path d="M12 5v14M5 12h14" /> : icon === "import" ? <path d="M12 3v12M7 8l5-5 5 5M4 15v6h16v-6" /> : <><path d="M4 3h13l4 4v14H3V3h1ZM7 3v6h10V3M7 21v-8h10v8" /><path d="M14 5v2" /></>}
    </svg>
  </button>;
}
