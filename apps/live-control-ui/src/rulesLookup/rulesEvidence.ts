import type { RulesHistoricalPassage, RulesPassageTarget } from '../api/rulesLookupTypes';
const digest = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
const record = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value);
function keys(value: unknown, expected: string[]): value is Record<string, unknown> {
  return record(value) && Object.keys(value).length === expected.length && expected.every(key => Object.hasOwn(value, key));
}
export function rulesCanonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(rulesCanonical).join(',') + ']';
  if (record(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + rulesCanonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
export async function rulesDigest(value: string): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), byte => byte.toString(16).padStart(2, '0')).join('');
}
export async function verifyHistoricalRulesPassage(value: unknown, target: RulesPassageTarget): Promise<RulesHistoricalPassage> {
  const invalid = () => new Error('This exact saved Rules excerpt could not be verified.');
  if (!keys(value, ['schema','world_id','conversation_id','turn_id','accepted_attempt','support','support_sha256'])
    || value.schema !== 'dmb_rules_historical_passage_v1' || value.world_id !== target.worldId
    || value.conversation_id !== target.conversationId || value.turn_id !== target.turnId
    || value.accepted_attempt !== target.attempt || !Number.isSafeInteger(value.accepted_attempt) || target.attempt < 1
    || value.support_sha256 !== target.supportSha256 || !digest(value.support_sha256)
    || new TextEncoder().encode(rulesCanonical(value)).length > 32768) throw invalid();
  const support = value.support;
  if (!keys(support, ['schema','support_id','corpus_sha256','ruleset_id','unit_id','full_text_sha256',
    'excerpt_start','excerpt_end','excerpt_text','excerpt_sha256','source_title','section','source_uri',
    'source_sha256','page_fingerprint','pdf_page_index','printed_page'])
    || support.schema !== 'dmb_rules_support_v1' || !uuid(support.support_id) || support.support_id !== target.supportId
    || !['corpus_sha256','unit_id','full_text_sha256','excerpt_sha256','source_sha256','page_fingerprint'].every(key => digest(support[key]))
    || typeof support.ruleset_id !== 'string' || !/^[a-z0-9_]{1,80}$/.test(support.ruleset_id)
    || !['source_title','section'].every(key => typeof support[key] === 'string' && support[key].length >= 1 && support[key].length <= 500)
    || typeof support.source_uri !== 'string' || !/^https:\/\/[^\s]+$/.test(support.source_uri) || support.source_uri.length > 1000
    || !Number.isSafeInteger(support.excerpt_start) || typeof support.excerpt_start !== 'number' || support.excerpt_start < 0
    || !Number.isSafeInteger(support.excerpt_end) || typeof support.excerpt_end !== 'number' || support.excerpt_end > 8192
    || typeof support.excerpt_text !== 'string' || !support.excerpt_text.length
    || support.excerpt_end - support.excerpt_start !== Array.from(support.excerpt_text).length
    || new TextEncoder().encode(support.excerpt_text).length > 16384
    || !Number.isSafeInteger(support.pdf_page_index) || typeof support.pdf_page_index !== 'number' || support.pdf_page_index < 0 || support.pdf_page_index > 100000
    || !(support.printed_page === null || (typeof support.printed_page === 'number' && Number.isSafeInteger(support.printed_page) && support.printed_page >= 1 && support.printed_page <= 100000))) throw invalid();
  if (await rulesDigest(support.excerpt_text) !== support.excerpt_sha256 || await rulesDigest(rulesCanonical(support)) !== target.supportSha256) throw invalid();
  return value as unknown as RulesHistoricalPassage;
}
