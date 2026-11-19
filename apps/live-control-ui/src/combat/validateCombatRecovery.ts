import generated from './combatRecoverySchema.json';
import type {ManualCombatRecord, ManualCombatDraft} from './ManualCombatTypes';
type Schema = Record<string, unknown>;
const root = generated as Schema;
const keywords = new Set(['$defs','$ref','type','anyOf','oneOf','const','enum','properties','required','additionalProperties','items','minItems','maxItems','minLength','maxLength','pattern','format','minimum','maximum','exclusiveMinimum','maxProperties','propertyNames','patternProperties']);
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);

/** Current generated schema vocabulary only; unsupported keywords fail closed. */
function valid(value: unknown, schema: Schema): boolean {
  if (Object.keys(schema).some(key => !keywords.has(key))) return false;
  if (typeof schema.$ref === 'string') {
    const name = schema.$ref.replace(/^#\/\$defs\//, '');
    const target = (root.$defs as Record<string, Schema>)[name];
    return !!target && valid(value, target);
  }
  if (Array.isArray(schema.anyOf) && !schema.anyOf.some(branch => valid(value, branch as Schema))) return false;
  if (Array.isArray(schema.oneOf) && schema.oneOf.filter(branch => valid(value, branch as Schema)).length !== 1) return false;
  if ('const' in schema && value !== schema.const) return false;
  if (Array.isArray(schema.enum) && !schema.enum.includes(value)) return false;
  switch (schema.type) {
    case 'null': return value === null;
    case 'string': {
      if (typeof value !== 'string') return false;
      const length = Array.from(value).length;
      if (typeof schema.minLength === 'number' && length < schema.minLength) return false;
      if (typeof schema.maxLength === 'number' && length > schema.maxLength) return false;
      if (typeof schema.pattern === 'string' && !new RegExp(schema.pattern).test(value)) return false;
      if (schema.format === 'uuid' && !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value)) return false;
      if (schema.format === 'date-time' && !Number.isFinite(Date.parse(value))) return false;
      return true;
    }
    case 'boolean': return typeof value === 'boolean';
    case 'integer': case 'number':
      return typeof value === 'number' && Number.isFinite(value) && (schema.type !== 'integer' || Number.isInteger(value))
        && !(typeof schema.minimum === 'number' && value < schema.minimum)
        && !(typeof schema.maximum === 'number' && value > schema.maximum)
        && !(typeof schema.exclusiveMinimum === 'number' && value <= schema.exclusiveMinimum);
    case 'array':
      return Array.isArray(value) && !(typeof schema.minItems === 'number' && value.length < schema.minItems)
        && !(typeof schema.maxItems === 'number' && value.length > schema.maxItems)
        && (!object(schema.items) || value.every(item => valid(item, schema.items as Schema)));
    case 'object': {
      if (!object(value)) return false;
      if(typeof schema.maxProperties==='number'&&Object.keys(value).length>schema.maxProperties)return false;
      if(object(schema.propertyNames)&&Object.keys(value).some(key=>!valid(key,schema.propertyNames as Schema)))return false;
      const patterns=object(schema.patternProperties)?Object.entries(schema.patternProperties):[];
      if(patterns.some(([pattern,child])=>Object.entries(value).some(([key,item])=>new RegExp(pattern).test(key)&&!valid(item,child as Schema))))return false;
      const properties = (schema.properties ?? {}) as Record<string, Schema>;
      if (Array.isArray(schema.required) && schema.required.some(key => typeof key !== 'string' || !Object.hasOwn(value,key))) return false;
      return Object.entries(value).every(([key,item]) => Object.hasOwn(properties,key) ? valid(item,properties[key])
        : patterns.some(([pattern])=>new RegExp(pattern).test(key)) ? true
        : schema.additionalProperties === false ? false : object(schema.additionalProperties) ? valid(item,schema.additionalProperties) : true);
    }
    default: return schema.type === undefined;
  }
}
export function validManualDraft(record:ManualCombatRecord, draft:ManualCombatDraft):boolean {
  if (!valid(draft, {$ref:'#/$defs/ManualEncounterDraft'})) return false;
  if(new TextEncoder().encode(JSON.stringify(draft)).byteLength>700*1024)return false;
  const unique = (ids:string[]) => new Set(ids).size === ids.length;
  const ids=draft.entities.map(actor=>actor.id), sides=draft.sides.map(side=>side.id);
  if (!unique(ids)||!unique(sides)||!unique(draft.groups.map(group=>group.id))) return false;
  if (record.ruleset.pacing.rounds !== (draft.turn.kind==='ordered_rounds')) return false;
  if ((record.ruleset.pacing.mode==='side') !== (draft.turn.kind==='side')) return false;
  if ((record.ruleset.pacing.mode==='spotlight') !== (draft.turn.kind==='spotlight')) return false;
  const fields=record.ruleset.stats.map(field=>field.field_id), resources=record.ruleset.resources.map(field=>field.field_id);
  const sameKeys=(value:object,keys:string[])=>Object.keys(value).length===keys.length&&keys.every(key=>Object.hasOwn(value,key));
  if (!unique([...fields,...resources])) return false;
  for (const field of record.ruleset.stats) {
    if (field.initial!==null && typeof field.initial!==(field.value_type==='integer'?'number':'string')) return false;
  }
  for (const actor of draft.entities) {
    if (actor.name!==actor.name.trim()||!unique(actor.statuses)||!unique(actor.tags)
      || (actor.side_id!==null&&!sides.includes(actor.side_id))
      || !sameKeys(actor.values.stats,fields)||!sameKeys(actor.values.resources,resources)) return false;
    for (const field of record.ruleset.stats) {
      const value=actor.values.stats[field.field_id];
      if (value!==null && (field.value_type==='integer' ? typeof value!=='number'||!Number.isInteger(value) : typeof value!=='string')) return false;
    }
    for (const resource of Object.values(actor.values.resources)) {
      if(resource.minimum!==null&&resource.maximum!==null&&resource.minimum>resource.maximum)return false;
    }
    if(actor.world_identity&&actor.world_identity.managed_world_id!==record.world_id)return false;
    const source=actor.mechanics_snapshot;
    if(source&&('target' in source?source.target.managed_world_id:source.managed_world_id)!==record.world_id)return false;
  }
  if(draft.groups.some(group=>!unique(group.member_ids)||group.member_ids.some(id=>!ids.includes(id))))return false;
  const memberships=draft.groups.flatMap(group=>group.member_ids);
  if(!unique(memberships))return false;
  const active=draft.turn.active_actor_id;
  if(active!==null&&!draft.entities.some(actor=>actor.id===active&&actor.participation==='in_action'))return false;
  if(draft.turn.kind==='side') {
    const {active_side_id:side,acted_actor_ids:acted}=draft.turn;
    if(side===null&&(active!==null||acted.length>0) || side!==null&&!sides.includes(side))return false;
    if(active!==null&&!draft.entities.some(actor=>actor.id===active&&actor.side_id===side))return false;
    if(!unique(acted)||acted.includes(active??'')||acted.some(id=>!draft.entities.some(actor=>actor.id===id&&actor.side_id===side)))return false;
  }
  if(draft.turn.kind==='ordered_rounds') {
    const anchor=draft.turn.round_start_actor_id;
    if(active!==null&&anchor===null || anchor!==null&&!ids.includes(anchor))return false;
  }
  return draft.title===draft.title.trim();
}
export const isCombatRecoveryRecord = (value: unknown) => valid(value, root)
  && (!object(value)||!object(value.ruleset)||value.ruleset.schema!=='dmb_combat_profile_v2'
    || validManualDraft(value as unknown as ManualCombatRecord,(value as unknown as ManualCombatRecord).draft));
export const isCombatRecoveryDraft = (value: unknown) => valid(value, {anyOf:[{$ref:'#/$defs/CombatEncounterDraft'},{$ref:'#/$defs/ManualEncounterDraft'}]});
