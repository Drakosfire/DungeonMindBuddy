import {useGuidedTour} from '../guidedTour/GuidedTour';
import { useCampaignTrashScope } from "../workspaceLifecycle/campaignTrashScope";
import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { useHostedAuthStatus } from "../auth/HostedAuthGate";
import { useLayoutEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { APP_NAV_ITEMS, type AppRouteKey } from "./appChromeConfig";
import { interceptPrimaryNavigationClick } from "./appNavigation";
import { AppChromeWorldGraphStatus } from "./AppChromeWorldGraphStatus";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { WorldSelector } from "../selectedWorld/WorldSelector";
import { worldScopedSurfaceHref } from "../selectedWorld/worldSelectionNavigation";
import { AppearanceControl } from "../ui/AppearanceControl";
import "./CompactAppNavigation.css";

export function CompactAppNavigation({ activeRoute, localOnly = false, primaryActionsRef }: { activeRoute: AppRouteKey; localOnly?: boolean; primaryActionsRef?: (element: HTMLDivElement | null) => void }) {
  const world = useSelectedWorld();
  const tour = useGuidedTour();
  const auth = useHostedAuthStatus();
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState(false);
  async function signOut() {
    setSigningOut(true);
    setSignOutError(false);
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST", credentials: "same-origin", redirect: "error", cache: "no-store",
      });
      if (response.status !== 204) throw new Error("Sign-out failed");
      window.location.replace("/");
    } catch {
      setSignOutError(true);
      setSigningOut(false);
    }
  }
  const campaignTrash = useCampaignTrashScope();
  const [expanded, setExpanded] = useState(true);
  const routesId = useId();
  const launcher = useRef<HTMLButtonElement>(null);
  const routes = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const strip = routes.current;
    const active = strip?.querySelector('[aria-current="page"]');
    if (!expanded || !strip || !active) return;

    const revealActiveRoute = () => {
      const visible = strip.getBoundingClientRect();
      const link = active.getBoundingClientRect();
      if (link.left < visible.left) strip.scrollLeft += link.left - visible.left;
      else if (link.right > visible.right) strip.scrollLeft += link.right - visible.right;
    };

    revealActiveRoute();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(revealActiveRoute);
    observer.observe(strip);
    observer.observe(active);
    return () => observer.disconnect();
  }, [activeRoute, expanded]);
  const current = APP_NAV_ITEMS.find((item) => item.route === activeRoute)?.label ?? "Buddy";
  const dismiss = (event: KeyboardEvent) => {
    if (event.key !== "Escape" || !expanded) return;
    event.preventDefault();
    setExpanded(false);
    launcher.current?.focus();
  };
  return <nav className="app-site-nav app-site-nav--compact" aria-label="Command board navigation" data-expanded={expanded}>
    <button ref={launcher} className="app-nav-compass" type="button" aria-label={expanded ? "Close navigation" : "Open navigation"}
      aria-expanded={expanded} aria-controls={routesId} title={expanded ? "Close navigation" : "Navigate Buddy"}
      onClick={() => setExpanded((open) => !open)} onKeyDown={dismiss}>
      <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
        <g className="app-nav-symbol__compass">
          <circle cx="16" cy="16" r="12" fill="none" stroke="currentColor" strokeWidth="1.3" />
          <path d="M20 8 18 18 8 24 14 14Z" fill="currentColor" />
          <circle cx="16" cy="16" r="2" fill="#151b22" />
          <path d="M16 1v3m0 24v3M1 16h3m24 0h3" stroke="currentColor" strokeWidth="1.3" />
        </g>
        <g className="app-nav-symbol__reticle" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="16" cy="16" r="9" />
          <path d="M16 2v8m0 12v8M2 16h8m12 0h8" />
          <circle cx="16" cy="16" r="1.5" />
        </g>
      </svg>
    </button>
    {!expanded ? <span className="app-nav-current">{current}</span> : null}
    <div id={routesId} ref={routes} className="app-site-nav__routes" hidden={!expanded} onKeyDown={dismiss}>
      {APP_NAV_ITEMS.map((item) => <a key={item.href}
        href={item.route && !localOnly && world.kind === "managed" ? worldScopedSurfaceHref(item.href, world.worldId) : item.href}
        className={item.route === activeRoute ? "active" : undefined} aria-current={item.route === activeRoute ? "page" : undefined}
        onClick={interceptPrimaryNavigationClick}>
        {item.label}
      </a>)}
    </div>
    {primaryActionsRef && <div className="app-nav-primary-actions" ref={primaryActionsRef} />}
    {tour?<button className="app-nav-tour" type="button" onClick={()=>{if(tour.entryLabel==='Start tour'||tour.entryLabel==='Resume tour')tour.teach();else tour.open();}}>{tour.entryLabel}</button>:null}
    {!localOnly ? <div className="app-nav-world-context">{campaignTrash ? <WorkspaceTrashControl campaignId={campaignTrash} current={null} onTrashed={() => undefined} /> : world.kind === "managed" ? <WorkspaceTrashControl worldId={world.worldId} current={null} onTrashed={() => undefined} /> : null}<WorldSelector compact creationPath={activeRoute === "graph" ? "/graph" : activeRoute === "index" ? "/" : "/plan"} /><AppChromeWorldGraphStatus activeRoute={activeRoute} /></div> : null}
    {localOnly && world.kind === "managed" && <span className="app-nav-guest-world">{world.name}</span>}
    <AppearanceControl key={activeRoute} />
    {auth.status === "authenticated" && <details>
      <summary aria-label={`Account: ${auth.displayName ?? auth.subject}`}>
        {auth.displayName ?? auth.subject}
      </summary>
      <button type="button" disabled={signingOut} onClick={() => void signOut()}>
        {signingOut ? "Signing out…" : "Sign out"}
      </button>
      {signOutError && <p role="alert">Sign-out failed. Try again.</p>}
    </details>}
  </nav>;
}
