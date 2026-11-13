import { useState } from 'react';
import type { CombatMechanicsSnapshot } from './combatTypes';
import { deferredComponent } from "../ui/deferredComponent";
const Renderer = deferredComponent(() => import('../statblocks/render/StatblockRenderer').then(module => ({default: module.StatblockRenderer})), "mechanics display");

/** Saved resource only: opening inspection never fetches current mechanics. */
export function CombatMechanicsInspection({snapshot}: {snapshot: CombatMechanicsSnapshot}) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Saved mechanics · {snapshot.resource.definition.identity.name}</summary>
    {open && <Renderer revision={snapshot.resource} chrome="campaign" />}
  </details>;
}
