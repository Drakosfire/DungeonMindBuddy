import { useEffect, useRef, useState } from 'react';
import { listWorldMechanicsAssociations, postManagedWorldGraphProjection } from '../api/liveApi';
import type { ManagedWorldGraphProjectionResponse } from '../api/types';
import { previewWorldCombatMechanics } from './combatApi';
import { CombatMechanicsInspection } from './CombatMechanicsInspection';
import type { WorldMechanicsAssociation } from '../api/worldMechanicsTypes';
import type { CombatMechanicsSnapshot, CombatEntity, CombatGroup, CombatWorldIdentity } from './combatTypes';
import './combatAssembly.css';

const actorKinds = new Set(['npc', 'threat', 'creature', 'monster']);

/** A Surface-owned draft editor. Loading identity never invents or loads mechanics. */
export function CombatEncounterAssembly({ worldId, disabled, remainingSlots, onAdd }: {
  worldId: string; disabled: boolean; remainingSlots: number;
  onAdd: (entities: CombatEntity[], group: CombatGroup | null) => string | void;
}) {
  const [world, setWorld] = useState<ManagedWorldGraphProjectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<CombatWorldIdentity | null>(null);
  const [name, setName] = useState('');
  const [team, setTeam] = useState<CombatEntity['team']>('enemy');
  const [count, setCount] = useState('1');
  const [initiative, setInitiative] = useState('');
  const [ac, setAc] = useState('');
  const [hp, setHp] = useState('');
  const [associations, setAssociations] = useState<WorldMechanicsAssociation[]>([]);
  const [snapshot, setSnapshot] = useState<CombatMechanicsSnapshot | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const selectionGeneration = useRef(0);
  const alive = useRef(true);
  function discardPreview() { selectionGeneration.current++; setSnapshot(null); setPreviewing(false); }
  const association = associations.find(record => record.request.target.node_id === selected?.node_id);
  async function loadMechanics() {
    if (!selected || !association || previewing) return;
    const generation = ++selectionGeneration.current;
    setPreviewing(true); setError(null); setSnapshot(null);
    try {
      const result = await previewWorldCombatMechanics(worldId, {association_id: association.association_id,
        association_version: association.version, target: selected});
      if (!alive.current || selectionGeneration.current !== generation) return;
      if (result.association_id !== association.association_id || result.association_version !== association.version
          || !Object.entries(selected).every(([field,value]) => result.target[field as keyof CombatWorldIdentity] === value)) {
        throw new Error('Mechanics preview did not match the selected creature.');
      }
      setSnapshot(result);
    } catch (caught) { if (alive.current && selectionGeneration.current === generation) setError(String(caught)); }
    finally { if (alive.current && selectionGeneration.current === generation) setPreviewing(false); }
  }
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  async function loadWorld() {
    discardPreview(); setLoading(true); setError(null); setSelected(null); setWorld(null); setAssociations([]);
    try {
      const [result, records] = await Promise.all([postManagedWorldGraphProjection({
        schema: 'dmb_managed_world_graph_projection_request_v1', managedWorldId: worldId,
      }), listWorldMechanicsAssociations(worldId)]);
      if (!alive.current) return;
      if (result.managedWorldId !== worldId || result.nativeWorldId !== result.projection.snapshot.worldId
        || result.projection.snapshot.scopeMode !== 'world') throw new Error('World identity could not be verified.');
      if (records.some(record => record.request.target.managed_world_id !== worldId)) throw new Error('Foreign mechanics associations.');
      setWorld(result); setAssociations(records); setSelected(null);
    } catch (caught) {
      if (alive.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally { if (alive.current) setLoading(false); }
  }
  const candidates = world?.projection.nodes.filter(node =>
    (actorKinds.has(node.kind.toLowerCase()) || actorKinds.has(node.role.toLowerCase()))
    && [node.label, ...node.aliases].some(label => label.toLowerCase().includes(query.trim().toLowerCase()))) ?? [];
  const copies = Number(count);
  const optionalNumber = (value: string) => value.trim() === '' ? null : Number(value);
  const numeric = [initiative, ac, hp].every(value => value.trim() === '' || Number.isSafeInteger(Number(value)));
  // Mirror the existing owning draft/entity bounds; never append an unsaveable actor.
  const validationError = remainingSlots === 0 ? 'This encounter is full (100 combatants).'
    : !Number.isSafeInteger(copies) || copies < 1 || copies > Math.min(20, remainingSlots)
      ? `Choose between 1 and ${Math.min(20, remainingSlots)} copies.`
    : !numeric ? 'Use whole numbers for initiative, AC and HP.'
    : Math.abs(optionalNumber(initiative) ?? 0) > 999 ? 'Initiative must be between -999 and 999.'
    : Math.abs(optionalNumber(ac) ?? 0) > 999999 ? 'AC must be between -999999 and 999999.'
    : (optionalNumber(hp) ?? 0) < 0 || (optionalNumber(hp) ?? 0) > 999999 ? 'HP must be between 0 and 999999.'
    : name.trim().length + (copies > 1 ? ` ${copies}`.length : 0) > 160 ? 'The name, including any copy number, must fit within 160 characters.'
    : null;
  const canAdd = !disabled && !loading && !previewing && name.trim() !== '' && validationError === null;

  function add() {
    if (!canAdd) return;
    const entities: CombatEntity[] = Array.from({ length: copies }, (_, index) => ({
      id: crypto.randomUUID(), name: copies === 1 ? name.trim() : `${name.trim()} ${index + 1}`,
      team, order: index + 1, init: optionalNumber(initiative), ac: optionalNumber(ac),
      hp: optionalNumber(hp), max_hp: optionalNumber(hp), temp_hp: 0, defeated: false,
      conditions: [], notes: '', tags: [], source: 'manual', provenance: [],
      statblock_path: null, statblock_artifact_id: null, statblock_title: null, corpus_fingerprint: null,
      world_identity: selected, mechanics_snapshot: snapshot,
    }));
    const refusal = onAdd(entities, copies > 1 ? {group_key: crypto.randomUUID(), label: name.trim(),
      statblock_path: null, member_ids: entities.map(entity => entity.id), collapsed: false} : null);
    if (refusal) {setError(refusal); return;}
    setError(null); setName(''); setSelected(null); discardPreview();
  }
  return <details className="combat-assembly"><summary>Add combatants</summary>
    <p>Choose a World creature or enter a name. Enter the stats you want to track; World identity alone supplies no mechanics.</p>
    <div className="combat-assembly__world">
      <button type="button" disabled={disabled || loading} onClick={() => void loadWorld()}>{loading ? 'Loading creatures…' : world ? 'Refresh World creatures' : 'Find World creatures'}</button>
      {world && <>
        <label>Search creatures<input aria-label="Search World creatures" value={query} disabled={disabled} onChange={event => setQuery(event.target.value)} /></label>
        <ul aria-label="World creatures" className="combat-assembly__candidates">{candidates.map(node => <li key={node.nodeId}>
          <button type="button" disabled={disabled} aria-pressed={selected?.node_id === node.nodeId} onClick={() => {
            discardPreview(); setError(null);
            setSelected({managed_world_id: worldId, native_world_id: world.nativeWorldId, binding_version: world.bindingVersion,
              graph_revision_id: world.projection.snapshot.revisionId, node_id: node.nodeId, label: node.label, kind: node.kind, role: node.role, campaign_scope: node.campaignScope ?? null});
            setName(node.label);
          }}>{node.label} <small>{node.kind} · {node.campaignScope || 'World'} · {node.nodeId}</small></button>
        </li>)}</ul>
        {candidates.length === 0 && <p>No matching creatures. You can enter a manual combatant below.</p>}
      </>}
      {error && <p role="alert">{error}</p>}
    </div>
    {selected && <p>World identity: {selected.label} · Manual stats <button type="button" disabled={disabled} onClick={() => {setSelected(null); discardPreview();}}>Use name only</button></p>}
    {selected && association && <button type="button" disabled={disabled || previewing || loading}
      onClick={() => void loadMechanics()}>{previewing ? 'Loading exact mechanics…' : 'Load associated mechanics'}</button>}
    {snapshot && <>
      <p>Exact saved mechanics loaded. Tracker AC and HP stay manual.</p>
      <CombatMechanicsInspection snapshot={snapshot} />
      <button type="button" disabled={disabled} onClick={discardPreview}>Remove loaded mechanics</button>
    </>}
    <div className="combat-assembly__fields">
      <label>Name<input aria-label="Combatant name" value={name} disabled={disabled} onChange={event => setName(event.target.value)} /></label>
      <label>Team<select aria-label="Combatant team" value={team} disabled={disabled} onChange={event => setTeam(event.target.value as CombatEntity['team'])}>
        <option value="pc">PC</option><option value="ally">Ally</option><option value="enemy">Enemy</option><option value="neutral">Neutral</option>
      </select></label>
      <label>Copies<input aria-label="Combatant copies" type="number" min="1" max={Math.min(20, remainingSlots)} value={count} disabled={disabled} onChange={event => setCount(event.target.value)} /></label>
      <label>Initiative<input aria-label="Combatant initiative" type="number" value={initiative} disabled={disabled} onChange={event => setInitiative(event.target.value)} /></label>
      <label>AC<input aria-label="Combatant AC" type="number" value={ac} disabled={disabled} onChange={event => setAc(event.target.value)} /></label>
      <label>Max HP (starts full)<input aria-label="Combatant HP" type="number" min="0" value={hp} disabled={disabled} onChange={event => setHp(event.target.value)} /></label>
      <button type="button" disabled={!canAdd} onClick={add}>Add to encounter draft</button>
    </div>
    {validationError && <p role="status">{validationError}</p>}
    <p className="module-muted">Save the encounter to keep these combatants.</p>
  </details>;
}
