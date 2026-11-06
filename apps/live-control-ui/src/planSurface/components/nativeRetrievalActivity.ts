import type { BuddyTraceObservation } from '../../api/buddyContextTraceTypes'

/** Display-only projections of the native owner's issued operation. */
export function nativeRetrievalActivity(event: BuddyTraceObservation): string | null {
  if (event.kind !== 'context_decision') return null
  const named = event.policy_version.startsWith('native_source_') && event.policy_version.endsWith('_progress_v2')
  if (event.item_ids.length !== (named ? 2 : 1)) return null
  const subjects: Record<string, string> = {
    native_source_search_progress_v1: 'retained source search',
    native_source_section_read_progress_v1: 'selected source section',
    native_source_document_read_progress_v1: 'selected source document',
    native_assertion_read_progress_v1: 'selected Graph assertions',
    native_statement_read_progress_v1: 'selected Graph statements',
  }
  const subject = subjects[named ? event.policy_version.replace(/_v2$/, '_v1') : event.policy_version]
  if (!subject) return null
  if (named) {
    const label = event.item_ids[1]
    if (!label.trim()) return null
    const search = event.policy_version === 'native_source_search_progress_v2'
    if (event.reason_code === 'unavailable') return search
      ? `Source search unavailable for “${label}”.` : `Could not read complete support from ${label}.`
    if (event.action === 'expanded') return search ? `Searching sources for “${label}”…` : `Reading ${label}…`
    if (event.action === 'retrieved') return search ? `Finished source search for “${label}”.` : `Read ${label}.`
    return null
  }
  if (event.reason_code === 'unavailable') return event.policy_version === 'native_source_search_progress_v1'
    ? 'Retained source search was unavailable.' : `The ${subject} read returned incomplete support.`
  if (event.action === 'expanded') return event.policy_version === 'native_source_search_progress_v1'
    ? 'Searching retained source sections…' : `Reading ${subject}…`
  if (event.action === 'retrieved') return event.policy_version === 'native_source_search_progress_v1'
    ? 'Retained source search completed.' : `Read ${subject}.`
  return null
}
