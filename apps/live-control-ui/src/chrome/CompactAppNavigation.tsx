import {useGuidedTour} from '../guidedTour/GuidedTour';
import { useCampaignTrashScope } from "../workspaceLifecycle/campaignTrashScope";
import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { APP_NAV_ITEMS, type AppRouteKey } from "./appChromeConfig";
import { interceptPrimaryNavigationClick } from "./appNavigation";
import { AppChromeWorldGraphStatus } from "./AppChromeWorldGraphStatus";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { WorldSelector } from "../selectedWorld/WorldSelector";
import { worldScopedSurfaceHref } from "../selectedWorld/worldSelectionNavigation";
import "./CompactAppNavigation.css";

export function CompactAppNavigation({ activeRoute }: { activeRoute: AppRouteKey }) {
  const world = useSelectedWorld();
  const tour = useGuidedTour();
  const campaignTrash = useCampaignTrashScope();
  const [expanded, setExpanded] = useState(false);
  const routesId = useId();
  const launcher = useRef<HTMLButtonElement>(null);
  const current = APP_NAV_ITEMS.find((item) => item.route === activeRoute)?.label ?? "Buddy";
  useEffect(() => setExpanded(false), [activeRoute]);
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
        <circle cx="16" cy="16" r="12" fill="none" stroke="currentColor" strokeWidth="1.3" />
        <path d="M20 8 18 18 8 24 14 14Z" fill="currentColor" />
        <circle cx="16" cy="16" r="2" fill="#151b22" />
        <path d="M16 1v3m0 24v3M1 16h3m24 0h3" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    </button>
    {!expanded ? <span className="app-nav-current">{current}</span> : null}
    <div id={routesId} className="app-site-nav__routes" hidden={!expanded} onKeyDown={dismiss}>
      {APP_NAV_ITEMS.map((item) => <a key={item.href}
        href={item.route && world.kind === "managed" ? worldScopedSurfaceHref(item.href, world.worldId) : item.href}
        className={item.route === activeRoute ? "active" : undefined} aria-current={item.route === activeRoute ? "page" : undefined}
        onClick={(event) => { interceptPrimaryNavigationClick(event); if (event.defaultPrevented) setExpanded(false); }}>
        {item.label}
      </a>)}
    </div>
    {tour?<button className="app-nav-tour" type="button" onClick={()=>{setExpanded(false);if(tour.entryLabel==='Start tour'||tour.entryLabel==='Resume tour')tour.teach();else tour.open();}}>{tour.entryLabel}</button>:null}
    <div className="app-nav-world-context">{campaignTrash ? <WorkspaceTrashControl campaignId={campaignTrash} current={null} onTrashed={() => undefined} /> : world.kind === "managed" ? <WorkspaceTrashControl worldId={world.worldId} current={null} onTrashed={() => undefined} /> : null}<WorldSelector compact /><AppChromeWorldGraphStatus /></div>
  </nav>;
}
