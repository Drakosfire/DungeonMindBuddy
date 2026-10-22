import { lazy, Suspense, useState } from 'react';
import type { CombatMechanicsSnapshot } from './combatTypes';
const Renderer = lazy(() => import('../statblocks/render/StatblockRenderer').then(module => ({default: module.StatblockRenderer})));

/** Saved resource only: opening inspection never fetches current mechanics. */
export function CombatMechanicsInspection({snapshot}: {snapshot: CombatMechanicsSnapshot}) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Saved mechanics · {snapshot.resource.definition.identity.name}</summary>
    {open && <Suspense fallback={<p>Loading mechanics display…</p>}><Renderer revision={snapshot.resource} chrome="campaign" /></Suspense>}
  </details>;
}
