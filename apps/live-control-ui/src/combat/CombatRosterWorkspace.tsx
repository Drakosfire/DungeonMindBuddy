import {useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode} from 'react';
import type {CombatEncounterDraft, CombatEntity} from './combatTypes';
import {CombatRosterTable} from './CombatRosterTable';
import {CombatSavedStatblock} from './CombatMechanicsInspection';

export type CombatProjectionControl = {
  selected: boolean;
  regionId: string;
  open: (trigger: HTMLButtonElement) => void;
};

/** The caller keys this workspace by the full World/encounter/run scope. */
export function CombatRosterWorkspace({draft, disabled, onToggleGroup, renderRow}: {
  draft: CombatEncounterDraft;
  disabled: boolean;
  onToggleGroup: (key: string) => void;
  renderRow: (entity: CombatEntity, hidden: boolean, projection: CombatProjectionControl) => ReactNode;
}) {
  const [selection, setSelection] = useState<{id: string; trigger: HTMLButtonElement} | null>(null);
  const [modal, setModal] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const workspace = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLElement>(null);
  const regionId = useId();
  // Resolve live draft ownership; never retain a second copy of source mechanics.
  const selected = draft.entities.find(entity => entity.id === selection?.id);
  const snapshot = selected?.mechanics_snapshot;
  useLayoutEffect(() => {
    if (snapshot && modal && dialog.current && !dialog.current.open) dialog.current.showModal();
    if (snapshot && !modal && panel.current) {
      panel.current.focus({preventScroll: true});
      panel.current.scrollIntoView?.({block: 'nearest'});
    }
  }, [selection?.id, modal, snapshot]);
  useEffect(() => {
    if (selection && !snapshot) {
      setSelection(null);
      workspace.current?.focus({preventScroll: true});
    }
  }, [selection, snapshot]);

  function close() {
    const trigger = selection?.trigger;
    dialog.current?.close();
    setSelection(null);
    if (trigger?.isConnected && !trigger.closest('[hidden]') && !trigger.disabled) trigger.focus({preventScroll: true});
    else workspace.current?.focus({preventScroll: true});
  }

  const sheet = snapshot && selected && <>
    <header>
      <div><strong>{selected.name}</strong><p>Exact saved statblock · tracker edits stay separate</p></div>
      <button type="button" onClick={() => {
        dialog.current?.close();
        setModal(!modal);
      }}>{modal ? 'Dock statblock' : 'Open as modal'}</button>
      <button type="button" onClick={close}>Close projected statblock</button>
    </header>
    <CombatSavedStatblock revision={snapshot.resource} chrome="campaign" />
  </>;

  return <div ref={workspace} tabIndex={-1} role="region" aria-label="Combat roster and statblock" className="combat-roster-workspace">
    <div className={`combat-roster-workspace-layout${snapshot && !modal ? ' has-projection' : ''}`}>
      {sheet && (modal
        ? <dialog ref={dialog} id={regionId} className="combat-mechanics-dialog"
            aria-label={`Projected statblock for ${selected?.name}`}
            onCancel={event => {event.preventDefault(); close();}}>
            {sheet}
          </dialog>
        : <aside ref={panel} tabIndex={-1} id={regionId} className="combat-statblock-projection"
            aria-label={`Projected statblock for ${selected?.name}`}>
            {sheet}
          </aside>)}
      <CombatRosterTable draft={draft} disabled={disabled} onToggleGroup={onToggleGroup}
        renderRow={(entity, hidden) => renderRow(entity, hidden, {
          selected: entity.id === selected?.id && !!snapshot, regionId,
          open: trigger => setSelection({id: entity.id, trigger}),
        })}/>
    </div>
  </div>;
}
