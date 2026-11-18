import { useEffect, useRef, useState } from 'react';
import {createPortal} from 'react-dom';
import type { CombatMechanicsSnapshot } from './combatTypes';
import { deferredComponent } from "../ui/deferredComponent";
export const CombatSavedStatblock = deferredComponent(() => import('../statblocks/render/StatblockRenderer').then(module => ({default: module.StatblockRenderer})), "mechanics display");

/** Saved resource only: opening inspection never fetches current mechanics. */
export function CombatMechanicsInspection({snapshot, presentation = 'inline'}: {snapshot: CombatMechanicsSnapshot; presentation?: 'inline' | 'dialog'}) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open && presentation === 'dialog') dialog.current?.showModal();
  }, [open, presentation]);
  if (presentation === 'dialog') return <>
    <button ref={trigger} type="button" onClick={() => setOpen(true)}>
      Saved mechanics · {snapshot.resource.definition.identity.name}
    </button>
    {open && createPortal(<dialog ref={dialog} className="combat-mechanics-dialog"
      aria-label={`Saved mechanics · ${snapshot.resource.definition.identity.name}`}
      onClose={() => {setOpen(false); trigger.current?.focus({preventScroll: true});}}
      onKeyDown={event => {if (event.key === 'Escape') event.stopPropagation();}}>
      <header><strong>Saved mechanics</strong><button type="button" onClick={() => dialog.current?.close()}>Close statblock</button></header>
      <CombatSavedStatblock revision={snapshot.resource} chrome="campaign" />
    </dialog>, document.body)}
  </>;
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Saved mechanics · {snapshot.resource.definition.identity.name}</summary>
    {open && <CombatSavedStatblock revision={snapshot.resource} chrome="campaign" />}
  </details>;
}
