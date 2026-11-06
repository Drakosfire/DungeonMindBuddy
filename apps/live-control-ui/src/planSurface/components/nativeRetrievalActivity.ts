import type { BuddyTraceObservation } from '../../api/buddyContextTraceTypes'

/** Display-only projections of the native owner's issued operation. */
export function nativeRetrievalActivity(event: BuddyTraceObservation): string | null {
  if (event.kind !== 'context_decision' || event.item_ids.length !== 1) return null
  const subjects: Record<string, string> = {
    native_source_search_progress_v1: 'retained source search',
    native_source_section_read_progress_v1: 'selected source section',
    native_source_document_read_progress_v1: 'selected source document',
    native_assertion_read_progress_v1: 'selected Graph assertions',
    native_statement_read_progress_v1: 'selected Graph statements',
  }
  const subject = subjects[event.policy_version]
  if (!subject) return null
  if (event.reason_code === 'unavailable') return event.policy_version === 'native_source_search_progress_v1'
    ? 'Retained source search was unavailable.' : `The ${subject} read returned incomplete support.`
  if (event.action === 'expanded') return event.policy_version === 'native_source_search_progress_v1'
    ? 'Searching retained source sections…' : `Reading ${subject}…`
  if (event.action === 'retrieved') return event.policy_version === 'native_source_search_progress_v1'
    ? 'Retained source search completed.' : `Read ${subject}.`
  return null
}
