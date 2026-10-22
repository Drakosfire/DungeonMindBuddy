import generated from './combatRecoverySchema.json';
type Schema = Record<string, unknown>;
const root = generated as Schema;
const keywords = new Set(['$defs','$ref','type','anyOf','oneOf','const','enum','properties','required','additionalProperties','items','minItems','maxItems','minLength','maxLength','pattern','format','minimum','maximum','exclusiveMinimum']);
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
      const properties = (schema.properties ?? {}) as Record<string, Schema>;
      if (Array.isArray(schema.required) && schema.required.some(key => typeof key !== 'string' || !Object.hasOwn(value,key))) return false;
      return Object.entries(value).every(([key,item]) => Object.hasOwn(properties,key) ? valid(item,properties[key])
        : schema.additionalProperties === false ? false : object(schema.additionalProperties) ? valid(item,schema.additionalProperties) : true);
    }
    default: return schema.type === undefined;
  }
}
export const isCombatRecoveryRecord = (value: unknown) => valid(value, root);
export const isCombatRecoveryDraft = (value: unknown) => valid(value, {$ref:'#/$defs/CombatEncounterDraft'});
