import {useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode} from 'react';
import type {CombatEncounterDraft, CombatEntity} from './combatTypes';
import {CombatRosterTable} from './CombatRosterTable';
import {CombatSavedStatblock} from './CombatMechanicsInspection';
import {MarkdownDocumentReader} from '../markdownReader/MarkdownDocumentReader';
import {getWorldCombatCorpusSheet} from './combatApi';

export type CombatProjectionControl = {
  available: boolean;
  selected: boolean;
  regionId: string;
  open: (trigger: HTMLButtonElement) => void;
};

/** The caller keys this workspace by the full World/encounter/run scope. */
export function CombatRosterWorkspace({draft, disabled, onToggleGroup, renderRow, corpusScope}: {
  draft: CombatEncounterDraft;
  disabled: boolean;
  onToggleGroup: (key: string) => void;
  renderRow: (entity: CombatEntity, hidden: boolean, projection: CombatProjectionControl) => ReactNode;
  corpusScope?: {worldId: string; encounterId: string};
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
  const {worldId, encounterId} = corpusScope ?? {};
  const actorId = selected?.id;
  const sourceId = selected && !snapshot && corpusScope && hasCorpusSheet(selected)
    ? selected.statblock_artifact_id : null;
  const digest = sourceId ? selected?.corpus_fingerprint : null;
  const sourceKey = sourceId ? JSON.stringify([worldId, encounterId, actorId, sourceId, digest]) : null;
  const [corpus, setCorpus] = useState<{key: string; markdown?: string; error?: string} | null>(null);
  const currentCorpus = corpus?.key === sourceKey ? corpus : null;
  const hasSource = Boolean(snapshot || sourceId);
  useEffect(() => {
    if (!worldId || !encounterId || !actorId || !sourceId || !digest || !sourceKey) return;
    const controller = new AbortController();
    void getWorldCombatCorpusSheet(worldId, encounterId, actorId, sourceId, digest, controller.signal)
      .then(markdown => {
        if (!controller.signal.aborted) setCorpus({key: sourceKey, markdown});
      }).catch(error => {
        if (!controller.signal.aborted) setCorpus({key: sourceKey, error: String(error)});
      });
    return () => controller.abort();
  }, [worldId, encounterId, actorId, sourceId, digest, sourceKey]);
  useLayoutEffect(() => {
    if (hasSource && modal && dialog.current && !dialog.current.open) dialog.current.showModal();
    if (hasSource && !modal && panel.current) {
      panel.current.focus({preventScroll: true});
      panel.current.scrollIntoView?.({block: 'nearest'});
    }
  }, [selection, modal, hasSource]);
  useEffect(() => {
    if (selection && !hasSource) {
      setSelection(null);
      setCorpus(null);
      workspace.current?.focus({preventScroll: true});
    }
  }, [selection, hasSource]);

  function close() {
    const trigger = selection?.trigger;
    dialog.current?.close();
    setSelection(null);
    setCorpus(null);
    if (trigger?.isConnected && !trigger.closest('[hidden]') && !trigger.disabled) trigger.focus({preventScroll: true});
    else workspace.current?.focus({preventScroll: true});
  }

  const sheet = hasSource && selected && <>
    <header>
      <div><strong>{selected.name}</strong><p>{snapshot ? 'Exact saved statblock' : 'Original corpus sheet'} · tracker edits stay separate</p></div>
      <button type="button" onClick={() => {
        dialog.current?.close();
        setModal(!modal);
      }}>{modal ? 'Dock statblock' : 'Open as modal'}</button>
      <button type="button" onClick={close}>Close projected statblock</button>
    </header>
    {snapshot ? <CombatSavedStatblock revision={snapshot.resource} chrome="campaign" />
      : currentCorpus?.error ? <p role="alert">{currentCorpus.error}</p>
      : currentCorpus?.markdown !== undefined ? <div className="combat-corpus-paper"><MarkdownDocumentReader markdown={currentCorpus.markdown}/></div>
      : <p role="status">Opening the original corpus sheet…</p>}
  </>;

  return <div ref={workspace} tabIndex={-1} role="region" aria-label="Combat roster and statblock" className="combat-roster-workspace">
    <div className={`combat-roster-workspace-layout${hasSource && !modal ? ' has-projection' : ''}`}>
      {sheet && (modal
        ? <dialog ref={dialog} id={regionId} className="combat-mechanics-dialog"
            aria-label={`Projected statblock for ${selected?.name}`}
            onKeyDown={event => {if (event.key === "Escape") event.stopPropagation();}}
            onCancel={event => {event.preventDefault(); close();}}>
            {sheet}
          </dialog>
        : <aside ref={panel} tabIndex={-1} id={regionId} className="combat-statblock-projection"
            aria-label={`Projected statblock for ${selected?.name}`}>
            {sheet}
          </aside>)}
      <CombatRosterTable draft={draft} disabled={disabled} onToggleGroup={onToggleGroup}
        renderRow={(entity, hidden) => renderRow(entity, hidden, {
          available: Boolean(entity.mechanics_snapshot || (corpusScope && hasCorpusSheet(entity))),
          selected: entity.id === selected?.id && hasSource, regionId,
          open: trigger => {
            if (selection?.id !== entity.id) setCorpus(null);
            setSelection({id: entity.id, trigger});
          },
        })}/>
    </div>
  </div>;
}

function hasCorpusSheet(entity: CombatEntity): boolean {
  return entity.source === 'imported' &&
    Boolean(entity.statblock_artifact_id?.startsWith('artifact:worldbuilding:') && entity.corpus_fingerprint);
}
