import type { NativeAssertion, NativeGraphEntity } from '../api/nativeGraphInspection';
import type { NativeGraphNode } from './nativeGraphDemoApi';

export interface ExplorerRecord { assertion: NativeAssertion; text: string; contexts: string[] }
export interface ExplorerRelationship {
  id: string; neighborId: string; text: string; predicate: string;
  direction: 'outgoing' | 'incoming' | 'self'; assertions: NativeAssertion[]; contexts: string[];
}
export interface ExplorerGroup { id: string; title: string; rows: ExplorerRelationship[] }
export interface NodeExplorerModel {
  recordedNames: string[]; identityAssertions: NativeAssertion[]; groups: ExplorerGroup[];
  summaries: ExplorerRecord[]; otherRecords: ExplorerRecord[];
  distinctNeighborCount: number; relationshipRecordCount: number; commonStatus: string | null;
}
const compare = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;
/** A recorded display label only, never a preferred/canonical name decision. */
export function compactNodeLabel(node: NativeGraphNode): string {
  const names = [...new Set(node.presentation?.recorded_names.filter(n => n.trim()) ?? [])];
  if (!names.length || names.includes(node.name)) return node.name;
  const support = (name: string) => names.filter(other => (` ${other} `).includes(` ${name} `)).length;
  return names.sort((a, b) => support(b) - support(a) || a.length - b.length || compare(a, b))[0]!;
}
const local = (predicate: string) => predicate.split(':').at(-1)!;
const knownNamespace = (predicate: string) => /^(dnd5e|dungeonbuddy|dungeonbuddy\.custom):/.test(predicate);
export function assertionStatus(a: NativeAssertion): string {
  return `${a.metadata.claim_mode.replace(/^dungeonbuddy\.claim:/, '')} · ${a.metadata.epistemic_basis} · ${a.metadata.standing}`;
}
function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null;
}
export function sourceContexts(a: NativeAssertion): string[] {
  // Display-only aliases for the established source identifiers. Exact metadata stays on each assertion.
  const scopes = a.metadata.scope.map(s => {
    if (s.axis !== 'dungeonbuddy.scope:campaign') return `${s.axis}: ${s.value}`;
    const campaign = /^longmont-c([1-9][0-9]*)$/.exec(s.value);
    return `Campaign ${campaign?.[1] ?? s.value}`;
  }).sort(compare);
  const temporal = record(a.metadata.temporal_scope);
  const payload = record(temporal?.payload);
  if (temporal?.schema === 'dungeonbuddy.time:fictional_anchor_v1' && typeof payload?.episode === 'string') {
    const session = /^session-([1-9][0-9]*)$/.exec(payload.episode);
    scopes.push(session ? `Session ${session[1]}` : `Source episode ${payload.episode}`);
  }
  return scopes.length ? [scopes.join(' · ')] : ['Source episode unspecified'];
}
const groupTitles = {
  family: 'Family', affiliation: 'Affiliation and command', people: 'Working relationships',
  places: 'Places mentioned', goals: 'Missions and threats', objects: 'Held objects', knowledge: 'Knowledge', other: 'Other connections',
} as const;
type GroupId = keyof typeof groupTitles;
const rules: Record<string, { group: GroupId; outgoing: string; incoming: string }> = {
  parent_of: { group: 'family', outgoing: 'Parent of', incoming: 'Child of' },
  child_of: { group: 'family', outgoing: 'Child of', incoming: 'Parent of' },
  member_of: { group: 'affiliation', outgoing: 'Member of', incoming: 'Has member' },
  leads: { group: 'affiliation', outgoing: 'Leads', incoming: 'Led by' },
  commands: { group: 'affiliation', outgoing: 'Commands', incoming: 'Commanded by' },
  works_with: { group: 'people', outgoing: 'Works with', incoming: 'Works with' },
  cooperates_with: { group: 'people', outgoing: 'Cooperates with', incoming: 'Cooperates with' },
  located_in: { group: 'places', outgoing: 'Located in', incoming: 'Location of' },
  travels_to: { group: 'places', outgoing: 'Travels to', incoming: 'Destination for' },
  mission_focus: { group: 'goals', outgoing: 'Mission focus', incoming: 'Mission focus of' },
  threatens: { group: 'goals', outgoing: 'Threatens', incoming: 'Threatened by' },
  holds: { group: 'objects', outgoing: 'Holds', incoming: 'Held by' },
  knows_about: { group: 'knowledge', outgoing: 'Knows about', incoming: 'Known about by' },
  aware_of: { group: 'knowledge', outgoing: 'Aware of', incoming: 'Subject of awareness of' },
};
// Canonical object-key ordering; preserve all list order except evidence IDs, whose order is not evidentiary.
function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort(compare).map(k => `${JSON.stringify(k)}:${stable((value as Record<string, unknown>)[k])}`).join(',')}}`;
  return JSON.stringify(value) ?? 'undefined';
}
function metadataKey(a: NativeAssertion): string {
  return stable({ ...a.metadata, evidence_ref_ids: [...a.metadata.evidence_ref_ids].sort(compare) });
}
function valueText(a: NativeAssertion, labels: ReadonlyMap<string, string>): string {
  return a.value.kind === 'entity_ref' ? labels.get(a.value.entity_id) ?? `Unlisted object (${a.value.entity_id})`
    : a.value.kind === 'term_ref' ? a.value.term
      : typeof a.value.value === 'string' ? a.value.value : JSON.stringify(a.value.value) ?? String(a.value.value);
}
export function buildNodeExplorer(detail: NativeGraphEntity, entityId: string, labels: ReadonlyMap<string, string>): NodeExplorerModel {
  const model: NodeExplorerModel = { recordedNames: [], identityAssertions: [], groups: [], summaries: [], otherRecords: [], distinctNeighborCount: 0, relationshipRecordCount: 0, commonStatus: null };
  const grouped = new Map<GroupId, ExplorerRelationship[]>();
  const family = new Map<string, ExplorerRelationship[]>();
  const neighbors = new Set<string>();
  const assertions = [...detail.entity.assertions].sort((a, b) => compare(a.assertion_id, b.assertion_id));
  const statuses = new Set(assertions.map(assertionStatus));
  model.commonStatus = statuses.size === 1 ? [...statuses][0]! : null;
  for (const a of assertions) {
    const own = a.subject_entity_id === entityId;
    const p = local(a.predicate), known = knownNamespace(a.predicate);
    if (own && known && (p === 'name' || p === 'classification')) {
      model.identityAssertions.push(a);
      if (p === 'name' && a.value.kind === 'literal' && typeof a.value.value === 'string') model.recordedNames.push(a.value.value);
      continue;
    }
    if (a.value.kind !== 'entity_ref' || (!own && a.value.entity_id !== entityId)) {
      const item = { assertion: a, text: own && known && p === 'summary' ? valueText(a, labels) : `${own ? '' : `${labels.get(a.subject_entity_id) ?? a.subject_entity_id} · `}${known ? p.replaceAll('_', ' ') : a.predicate}: ${valueText(a, labels)}`, contexts: sourceContexts(a) };
      (own && known && p === 'summary' ? model.summaries : model.otherRecords).push(item);
      continue;
    }
    const neighborId = own ? a.value.entity_id : a.subject_entity_id;
    if (neighborId !== entityId) neighbors.add(neighborId);
    model.relationshipRecordCount++;
    const direction = neighborId === entityId ? 'self' : own ? 'outgoing' : 'incoming';
    const rule = known ? rules[p] : undefined;
    const neighbor = labels.get(neighborId) ?? `Unlisted object (${neighborId})`;
    const text = direction === 'self' ? `${rule ? p.replaceAll('_', ' ') : a.predicate} → self`
      : rule ? `${own ? rule.outgoing : rule.incoming} ${neighbor}`
        : own ? `${a.predicate} → ${neighbor}` : `${neighbor} → ${a.predicate} → this object`;
    const group = rule?.group ?? 'other';
    const row: ExplorerRelationship = { id: a.assertion_id, neighborId, text, predicate: a.predicate, direction, assertions: [a], contexts: sourceContexts(a) };
    // Only explicit inverse parent/child assertions with identical qualifications and nonempty evidence.
    if (group === 'family' && direction !== 'self' && a.metadata.evidence_ref_ids.length) {
      const key = `${neighborId}:${own ? p : p === 'parent_of' ? 'child_of' : 'parent_of'}:${metadataKey(a)}`;
      const previous = family.get(key)?.find(r => r.direction !== direction && local(r.predicate) !== p && r.assertions.length === 1);
      if (previous) { previous.assertions.push(a); continue; }
      family.set(key, [...(family.get(key) ?? []), row]);
    }
    grouped.set(group, [...(grouped.get(group) ?? []), row]);
  }
  model.recordedNames = [...new Set(model.recordedNames)].sort(compare);
  model.distinctNeighborCount = neighbors.size;
  model.groups = (Object.keys(groupTitles) as GroupId[]).filter(id => grouped.has(id)).map(id => ({ id, title: groupTitles[id], rows: grouped.get(id)!.sort((a, b) => compare(a.text, b.text) || compare(a.id, b.id)) }));
  return model;
}
